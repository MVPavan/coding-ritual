"""Resident one-turn RPC lifecycle with protected registration and bounded polling."""

import time
from collections.abc import Callable
from enum import StrEnum
from typing import Final

from pydantic import JsonValue, ValidationError

from workflow_interpreter.bdio import WorkflowStore
from workflow_interpreter.bdio.errors import StoreError
from workflow_interpreter.bdio.rpc_control import ControlBusy
from workflow_interpreter.bdio.rpc_records import (
    ControlRegistration,
    SessionCompletion,
    SessionRegistration,
)
from workflow_interpreter.contracts.rpc_control import MSG_CONTROL, ControlState
from workflow_interpreter.contracts.rpc_usage import TokenCounts, UsageSnapshot
from workflow_interpreter.contracts.sessions import execution_policy_digest
from workflow_interpreter.inspector import procfs
from workflow_interpreter.inspector.clock import Clock
from workflow_interpreter.inspector.config import InspectorConfig
from workflow_interpreter.inspector.launch_record import LaunchReceipt
from workflow_interpreter.inspector.models import (
    ExitReason,
    MonitorResult,
    MonitorVerdict,
)
from workflow_interpreter.inspector.monitor import TERMINAL_VERDICTS, Monitor
from workflow_interpreter.inspector.paths import (
    WrapperPaths,
    read_record,
    write_record,
)
from workflow_interpreter.inspector.profile import CrewEvent, EventType, TaskSpec
from workflow_interpreter.inspector.rpc_control import (
    INTERRUPT_FILE,
    control_path,
    interrupt,
    next_intent,
)
from workflow_interpreter.inspector.rpc_pipes import RpcPipes
from workflow_interpreter.inspector.rpc_records import (
    SESSION_FILE,
    TURN_FILE,
    InitializeReply,
    ThreadIdentity,
    ThreadReply,
    TurnCompleted,
    TurnIdentity,
    TurnPhase,
    TurnRecord,
    TurnReply,
    VendorThread,
)
from workflow_interpreter.inspector.rpc_usage import (
    USAGE_FILE,
    UsageNotification,
    protected_baseline,
    updated_usage,
)
from workflow_interpreter.profiles.codex_appserver_config import thread_config
from workflow_interpreter.profiles.codex_rpc import (
    CODEX_VERSION,
    Notification,
    RpcClient,
    RpcFailure,
    RpcFrame,
    RpcMethod,
)

MSG_REPLY: Final[str] = "app-server rejected or malformed a required response"
MSG_IDENTITY: Final[str] = "app-server thread or turn identity mismatch"
MSG_TURN: Final[str] = "app-server turn did not complete successfully"
MSG_SHUTDOWN: Final[str] = "app-server shutdown deadline exceeded"
MSG_EXIT: Final[str] = "app-server exited without confirmed turn completion"
SHUTDOWN_S: Final[float] = 1.0


class SessionPhase(StrEnum):
    """One request in flight, and exactly one possible turn submission."""

    INITIALIZE = "initialize"
    THREAD = "thread"
    TURN = "turn"
    ACTIVE = "active"
    CONTROL = "control"
    SHUTDOWN = "shutdown"


class RpcSession:
    """Own the pipes only in the wrapper that launched them; never adopt stdio."""

    def __init__(
        self,
        config: InspectorConfig,
        paths: WrapperPaths,
        store: WorkflowStore,
        clock: Clock,
        receipt: LaunchReceipt,
        task: TaskSpec,
        pipes: RpcPipes,
    ) -> None:
        self._config, self._paths, self._store, self._clock = (
            config,
            paths,
            store,
            clock,
        )
        self._receipt, self._task, self._pipes = receipt, task, pipes
        self._directory = paths.activation_dir(receipt.activation_id)
        self._phase = SessionPhase.INITIALIZE
        self._turn: TurnRecord | None = None
        self._early: TurnCompleted | None = None
        self._shutdown_at = 0.0
        activation = store.reads.load_activation(receipt.activation_id)
        source = activation.metadata.session_reuse_source
        self._baseline = TokenCounts(input=0, cached_input=0, output=0)
        if source is not None:
            previous = store.reads.load_activation(
                source.activation_id
            ).metadata.session_completion
            self._baseline = (
                previous.usage.cumulative
                if previous
                else protected_baseline(
                    paths.activation_dir(source.activation_id), source
                )
            )
        self._usage = UsageSnapshot(envelope_bytes=len(task.brief.encode()))
        self._pending_usage: UsageNotification | None = None
        self._control: ControlRegistration | None = None
        self._control_sequence = 1
        self._interrupted = False
        self._announced_thread: str | None = None
        self._announced_turn: str | None = None
        self._exit: MonitorResult | None = None
        self._drain_deadline = 0.0

    def _save(self) -> None:
        """Persist turn intent or progress before any subsequent external action."""
        if self._turn is not None:
            write_record(self._directory / TURN_FILE, self._turn)

    def _thread_params(self) -> dict[str, JsonValue]:
        """Every process gets explicit current permissions; history is not authority."""
        task = self._task
        params: dict[str, JsonValue] = {
            "model": task.model,
            "cwd": task.cwd,
            "approvalPolicy": "never",
            "sandbox": "workspace-write",
            "approvalsReviewer": "user",
            "config": thread_config(),
        }
        if self._receipt.handle.session_id:
            params["threadId"] = self._receipt.handle.session_id
        return params

    def _start_turn(self, client: RpcClient, frame: RpcFrame) -> None:
        """Register the correlated thread in both stores before authorizing a turn."""
        reply = ThreadReply.model_validate(frame.result)
        if reply.cwd != self._task.cwd or reply.model != self._task.model:
            raise RpcFailure(MSG_IDENTITY)
        thread = reply.thread.id
        if self._announced_thread is not None and self._announced_thread != thread:
            raise RpcFailure(MSG_IDENTITY)
        expected = self._receipt.handle.session_id
        if expected and thread != expected:
            raise RpcFailure(MSG_IDENTITY)
        task = self._task
        registration = SessionRegistration(
            root_id=task.root_id,
            activation_id=task.activation_id,
            launch_id=self._receipt.launch_id,
            handle=self._receipt.handle,
            thread_id=thread,
            model=task.model,
            effort=task.effort or "",
            state_path=task.vendor_state or "",
            policy_digest=execution_policy_digest(
                task.execution_policy.model_dump_json()
                if task.execution_policy
                else "legacy"
            ),
            crew_version=CODEX_VERSION,
        )
        write_record(self._directory / SESSION_FILE, registration)
        self._store.register_session(task.activation_id, registration)
        self._turn = TurnRecord(registration=registration, phase=TurnPhase.INTENT)
        self._save()
        roots: list[JsonValue] = (
            [str(path) for path in task.execution_grants.writable_directories]
            if task.execution_grants
            else self._legacy_roots()
        )
        client.request(
            RpcMethod.TURN_START,
            {
                "threadId": thread,
                "cwd": task.cwd,
                "model": task.model,
                "effort": task.effort,
                "approvalPolicy": "never",
                "input": [{"type": "text", "text": task.brief, "text_elements": []}],
                "sandboxPolicy": {
                    "type": "workspaceWrite",
                    "writableRoots": roots,
                    "networkAccess": False,
                    "excludeSlashTmp": True,
                    "excludeTmpdirEnvVar": False,
                },
            },
        )
        self._phase = SessionPhase.TURN

    def _legacy_roots(self) -> list[JsonValue]:
        """Legacy callers retain the same Codex writable-root translation."""
        # Profile initialization imports Inspector; defer this legacy adapter.
        from workflow_interpreter.profiles.codex import _writable_roots

        return list(_writable_roots(self._task, self._task.cwd))

    def _completed(self, completion: TurnCompleted) -> None:
        """Only a matching successful terminal notification authorizes shutdown."""
        if self._turn is None or self._turn.registration is None:
            raise RpcFailure(MSG_IDENTITY)
        if (
            completion.threadId != self._turn.registration.thread_id
            or completion.turn.id != self._turn.turn_id
        ):
            raise RpcFailure(MSG_IDENTITY)
        if completion.turn.status != "completed":
            raise RpcFailure(MSG_TURN)
        if self._turn.phase is TurnPhase.COMPLETED:
            return
        self._turn = self._turn.model_copy(update={"phase": TurnPhase.COMPLETED})
        self._save()
        self._phase = SessionPhase.SHUTDOWN
        self._shutdown_at = time.monotonic() + SHUTDOWN_S

    def _frame(self, client: RpcClient, frame: RpcFrame) -> None:
        """Advance the handshake state machine or process a known notification."""
        if frame.method is not None:
            self._notification_identity(frame)
            if frame.method == Notification.TURN_COMPLETED:
                completion = TurnCompleted.model_validate(frame.params)
                if self._phase in (SessionPhase.TURN, SessionPhase.CONTROL):
                    if self._early is not None:
                        raise RpcFailure(MSG_IDENTITY)
                    self._early = completion
                else:
                    self._completed(completion)
            elif frame.method == Notification.USAGE:
                self._accept_usage(UsageNotification.model_validate(frame.params))
            elif frame.method == Notification.ERROR:
                raise RpcFailure(MSG_REPLY)
            with self._paths.log(self._task.activation_id).open("ab") as stream:
                stream.write(
                    CrewEvent(type=EventType.MESSAGE, text=frame.method)
                    .model_dump_json()
                    .encode()
                    + b"\n"
                )
            return
        if frame.error is not None:
            raise RpcFailure(MSG_REPLY)
        if self._phase is SessionPhase.INITIALIZE:
            initialized = InitializeReply.model_validate(frame.result)
            if initialized.codexHome != self._task.vendor_state:
                raise RpcFailure(MSG_IDENTITY)
            client.notify(RpcMethod.INITIALIZED)
            client.request(
                RpcMethod.THREAD_RESUME
                if self._receipt.handle.session_id
                else RpcMethod.THREAD_START,
                self._thread_params(),
            )
            self._phase = SessionPhase.THREAD
        elif self._phase is SessionPhase.THREAD:
            self._start_turn(client, frame)
        elif self._phase is SessionPhase.CONTROL:
            if self._control is None or frame.result != {
                "turnId": self._control.turn_id
            }:
                raise RpcFailure(MSG_CONTROL)
            control = self._control
            intent = next_intent(self._directory, control.sequence)
            if intent is None:
                raise RpcFailure(MSG_CONTROL)
            write_record(
                control_path(self._directory, control.sequence),
                intent.model_copy(
                    update={
                        "control": control.model_copy(
                            update={"state": ControlState.ACKNOWLEDGED}
                        )
                    }
                ),
            )
            self._control = None
            try:
                self._store.record_control_state(
                    self._task.activation_id, control, ControlState.ACKNOWLEDGED
                )
            except ControlBusy:
                # Protected ack is authoritative; the next driver tick mirrors it.
                pass
            self._control_sequence += 1
            self._phase = SessionPhase.ACTIVE
            if self._early is not None:
                self._completed(self._early)
                self._early = None
        elif self._phase is SessionPhase.TURN:
            reply = TurnReply.model_validate(frame.result)
            if (
                self._announced_turn is not None
                and self._announced_turn != reply.turn.id
            ):
                raise RpcFailure(MSG_IDENTITY)
            if self._turn is None:
                raise RpcFailure(MSG_IDENTITY)
            self._turn = self._turn.model_copy(
                update={"phase": TurnPhase.ACTIVE, "turn_id": reply.turn.id}
            )
            self._save()
            self._phase = SessionPhase.ACTIVE
            if self._pending_usage is not None:
                self._accept_usage(self._pending_usage)
                self._pending_usage = None
            if self._early is not None:
                self._completed(self._early)
        else:
            raise RpcFailure(MSG_REPLY)

    def _notification_identity(self, frame: RpcFrame) -> None:
        """Validate progress identities without granting them registration authority."""
        if frame.method in (
            Notification.ERROR,
            Notification.WARNING,
            Notification.CONFIG_WARNING,
            Notification.DEPRECATION,
        ):
            return
        turn_id = None
        if frame.method == Notification.THREAD_STARTED:
            params = frame.params or {}
            thread_id = VendorThread.model_validate(params.get("thread")).id
        elif frame.method == Notification.THREAD_STATUS:
            thread_id = ThreadIdentity.model_validate(frame.params).threadId
        elif frame.method in (Notification.TURN_STARTED, Notification.TURN_COMPLETED):
            notice = TurnCompleted.model_validate(frame.params)
            thread_id, turn_id = notice.threadId, notice.turn.id
        else:
            identity = TurnIdentity.model_validate(frame.params)
            thread_id, turn_id = identity.threadId, identity.turnId
        expected_thread = (
            self._turn.registration.thread_id
            if self._turn is not None and self._turn.registration is not None
            else self._announced_thread
        )
        expected_turn = (
            self._turn.turn_id if self._turn is not None else None
        ) or self._announced_turn
        if (
            expected_thread is not None
            and thread_id != expected_thread
            or turn_id is not None
            and expected_turn is not None
            and turn_id != expected_turn
        ):
            raise RpcFailure(MSG_IDENTITY)
        self._announced_thread = thread_id
        if turn_id is not None:
            self._announced_turn = turn_id

    def _poll_control(self, client: RpcClient) -> None:
        """Persist submission before send; only this living pipe owner can deliver it."""
        if not self._interrupted and (self._directory / INTERRUPT_FILE).exists():
            registration = read_record(
                self._directory / INTERRUPT_FILE, SessionRegistration
            )
            if self._turn is None or registration != self._turn.registration:
                raise RpcFailure(MSG_CONTROL)
            self._interrupted = True
            interrupt(client, self._turn)
            return
        if self._phase is not SessionPhase.ACTIVE:
            return
        intent = next_intent(self._directory, self._control_sequence)
        if intent is None:
            return
        if (
            self._turn is None
            or intent.control.registration != self._turn.registration
            or intent.control.turn_id != self._turn.turn_id
            or intent.control.state is not ControlState.INTENT
        ):
            raise RpcFailure(MSG_CONTROL)
        try:
            self._control = self._store.record_control_state(
                self._task.activation_id,
                intent.control,
                ControlState.SUBMITTING,
            )
        except ControlBusy:
            return
        write_record(
            control_path(self._directory, self._control_sequence),
            intent.model_copy(update={"control": self._control}),
        )
        client.request(
            RpcMethod.TURN_STEER,
            {
                "threadId": self._control.registration.thread_id,
                "expectedTurnId": self._control.turn_id,
                "input": [
                    {"type": "text", "text": intent.instructions, "text_elements": []}
                ],
            },
        )
        self._phase = SessionPhase.CONTROL

    def _accept_usage(self, notification: UsageNotification) -> None:
        """Correlate telemetry before replacing the current snapshot."""
        if self._turn is None or self._turn.registration is None:
            raise RpcFailure(MSG_IDENTITY)
        if notification.threadId != self._turn.registration.thread_id:
            raise RpcFailure(MSG_IDENTITY)
        if self._turn.turn_id is None:
            self._pending_usage = notification
            return
        if notification.turnId != self._turn.turn_id:
            raise RpcFailure(MSG_IDENTITY)
        self._usage = updated_usage(
            notification.model_dump(mode="json"),
            self._baseline,
            envelope_bytes=len(self._task.brief.encode()),
        )
        write_record(self._directory / USAGE_FILE, self._usage)

    def _fail(self, reason: str) -> None:
        """Keep bounded failure evidence even when handshake never made a thread."""
        self._turn = (self._turn or TurnRecord(phase=TurnPhase.FAILED)).model_copy(
            update={"phase": TurnPhase.FAILED, "error": reason[:1024]}
        )
        self._save()
        if self._control is not None:
            try:
                self._store.record_control_state(
                    self._task.activation_id, self._control, ControlState.UNCERTAIN
                )
            except ControlBusy:
                # Recovery derives uncertainty from owner death and the intent.
                pass

    def watch(
        self, monitor: Monitor, on_cycle: Callable[[MonitorResult], None]
    ) -> MonitorResult:
        """Poll RPC and enforcement together; a blocked request cannot suspend limits."""
        with RpcClient(*self._pipes.detach()) as client:
            monitor.before_terminate(lambda: interrupt(client, self._turn))
            client.request(
                RpcMethod.INITIALIZE,
                {
                    "clientInfo": {"name": "workflow-interpreter", "version": "1"},
                    "capabilities": {"experimentalApi": False},
                },
            )
            try:
                while True:
                    for frame in client.poll(0.02):
                        self._frame(client, frame)
                    self._poll_control(client)
                    if self._phase is SessionPhase.SHUTDOWN:
                        if not client.output_pending:
                            client.close_input()
                        if time.monotonic() > self._shutdown_at:
                            raise RpcFailure(MSG_SHUTDOWN)
                    result = self._exit or monitor.observe()
                    on_cycle(result)
                    if result.verdict in TERMINAL_VERDICTS:
                        if self._exit is None:
                            self._exit = result
                            self._drain_deadline = time.monotonic() + SHUTDOWN_S
                        if not client.eof:
                            if time.monotonic() > self._drain_deadline:
                                raise RpcFailure(MSG_SHUTDOWN)
                            continue
                        if (
                            self._phase is not SessionPhase.SHUTDOWN
                            or result.exit_code != 0
                        ):
                            self._fail(MSG_EXIT)
                        elif (
                            self._turn is not None
                            and self._turn.registration is not None
                            and self._turn.turn_id
                        ):
                            self._store.record_session_completion(
                                self._task.activation_id,
                                SessionCompletion(
                                    registration=self._turn.registration,
                                    turn_id=self._turn.turn_id,
                                    usage=self._usage,
                                ),
                            )
                        return result
                    if client.eof and self._phase is not SessionPhase.SHUTDOWN:
                        raise RpcFailure(MSG_EXIT)
            except (RpcFailure, ValidationError, StoreError, OSError) as error:
                self._fail(str(error) if isinstance(error, RpcFailure) else MSG_REPLY)
                interrupt(client, self._turn)
                proof = procfs.terminate(
                    self._config, self._receipt.handle, self._clock
                )
                if not proof.confirmed_dead:
                    return monitor.watch(on_cycle)
                return monitor.observe().model_copy(
                    update={
                        "verdict": MonitorVerdict.EXITED,
                        "exit_code": proof.exit_code,
                        "reason": ExitReason.TERMINATED,
                    }
                )
