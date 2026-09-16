"""Resident one-turn RPC lifecycle with protected registration and bounded polling."""

import time
from collections.abc import Callable
from enum import StrEnum
from typing import Final

from pydantic import JsonValue, ValidationError

from workflow_interpreter.bdio import WorkflowStore
from workflow_interpreter.bdio.errors import BdioError
from workflow_interpreter.bdio.rpc_records import SessionRegistration
from workflow_interpreter.profiles.codex_rpc import (
    CODEX_VERSION,
    Notification,
    RpcClient,
    RpcFailure,
    RpcFrame,
    RpcMethod,
)
from workflow_interpreter.supervisor import procfs
from workflow_interpreter.supervisor.clock import Clock
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.launch_record import LaunchReceipt
from workflow_interpreter.supervisor.models import (
    ExitReason,
    MonitorResult,
    MonitorVerdict,
)
from workflow_interpreter.supervisor.monitor import TERMINAL_VERDICTS, Monitor
from workflow_interpreter.supervisor.paths import WrapperPaths, write_record
from workflow_interpreter.supervisor.profile import EventType, RunnerEvent, TaskSpec
from workflow_interpreter.supervisor.rpc_pipes import RpcPipes
from workflow_interpreter.supervisor.rpc_records import (
    SESSION_FILE,
    TURN_FILE,
    InitializeReply,
    ThreadReply,
    TurnCompleted,
    TurnPhase,
    TurnRecord,
    TurnReply,
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
    SHUTDOWN = "shutdown"


class RpcSession:
    """Own the pipes only in the wrapper that launched them; never adopt stdio."""

    def __init__(
        self,
        config: SupervisorConfig,
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

    def _save(self) -> None:
        """Persist turn intent or progress before any subsequent external action."""
        if self._turn is not None:
            write_record(self._directory / TURN_FILE, self._turn)

    def _thread_params(self) -> dict[str, JsonValue]:
        """Every process gets explicit current permissions; history is not authority."""
        task = self._task
        config: dict[str, JsonValue] = {
            "sandbox_workspace_write.network_access": False,
            "sandbox_workspace_write.exclude_slash_tmp": True,
            "mcp_servers": {},
        }
        params: dict[str, JsonValue] = {
            "model": task.model,
            "cwd": task.cwd,
            "approvalPolicy": "never",
            "sandbox": "workspace-write",
            "approvalsReviewer": "user",
            "config": config,
        }
        if self._receipt.handle.session_id:
            params["threadId"] = self._receipt.handle.session_id
        else:
            params["dynamicTools"] = []
        return params

    def _start_turn(self, client: RpcClient, frame: RpcFrame) -> None:
        """Register the correlated thread in both stores before authorizing a turn."""
        reply = ThreadReply.model_validate(frame.result)
        if reply.cwd != self._task.cwd or reply.model != self._task.model:
            raise RpcFailure(MSG_IDENTITY)
        thread = reply.thread.id
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
            policy_digest=(
                task.execution_policy.model_dump_json()
                if task.execution_policy
                else "legacy"
            ),
            runner_version=CODEX_VERSION,
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
        # Profile initialization imports Supervisor; defer this legacy adapter.
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
        self._turn = self._turn.model_copy(update={"phase": TurnPhase.COMPLETED})
        self._save()
        self._phase = SessionPhase.SHUTDOWN
        self._shutdown_at = time.monotonic() + SHUTDOWN_S

    def _frame(self, client: RpcClient, frame: RpcFrame) -> None:
        """Advance the handshake state machine or process a known notification."""
        if frame.method is not None:
            if frame.method == Notification.TURN_COMPLETED:
                completion = TurnCompleted.model_validate(frame.params)
                if self._phase is SessionPhase.TURN:
                    if self._early is not None:
                        raise RpcFailure(MSG_IDENTITY)
                    self._early = completion
                else:
                    self._completed(completion)
            elif frame.method == Notification.ERROR:
                raise RpcFailure(MSG_REPLY)
            with self._paths.log(self._task.activation_id).open("ab") as stream:
                stream.write(
                    RunnerEvent(type=EventType.MESSAGE, text=frame.method)
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
        elif self._phase is SessionPhase.TURN:
            reply = TurnReply.model_validate(frame.result)
            if self._turn is None:
                raise RpcFailure(MSG_IDENTITY)
            self._turn = self._turn.model_copy(
                update={"phase": TurnPhase.ACTIVE, "turn_id": reply.turn.id}
            )
            self._save()
            self._phase = SessionPhase.ACTIVE
            if self._early is not None:
                self._completed(self._early)
        else:
            raise RpcFailure(MSG_REPLY)

    def _fail(self, reason: str) -> None:
        """Keep bounded failure evidence even when handshake never made a thread."""
        self._turn = (self._turn or TurnRecord(phase=TurnPhase.FAILED)).model_copy(
            update={"phase": TurnPhase.FAILED, "error": reason[:1024]}
        )
        self._save()

    def watch(
        self, monitor: Monitor, on_cycle: Callable[[MonitorResult], None]
    ) -> MonitorResult:
        """Poll RPC and enforcement together; a blocked request cannot suspend limits."""
        with RpcClient(*self._pipes.detach()) as client:
            client.request(
                RpcMethod.INITIALIZE,
                {
                    "clientInfo": {"name": "workflow-interpreter", "version": "1"},
                    "capabilities": {"experimentalApi": True},
                },
            )
            try:
                while True:
                    for frame in client.poll(0.02):
                        self._frame(client, frame)
                    if self._phase is SessionPhase.SHUTDOWN:
                        if not client.output_pending:
                            client.close_input()
                        if time.monotonic() > self._shutdown_at:
                            raise RpcFailure(MSG_SHUTDOWN)
                    result = monitor.observe()
                    on_cycle(result)
                    if result.verdict in TERMINAL_VERDICTS:
                        if (
                            self._phase is not SessionPhase.SHUTDOWN
                            or result.exit_code != 0
                        ):
                            self._fail(MSG_EXIT)
                        return result
                    if client.eof and self._phase is not SessionPhase.SHUTDOWN:
                        raise RpcFailure(MSG_EXIT)
            except (RpcFailure, ValidationError, BdioError, OSError) as error:
                self._fail(str(error) if isinstance(error, RpcFailure) else MSG_REPLY)
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
