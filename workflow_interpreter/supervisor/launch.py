"""§5.2 two-phase activation — the crash-atomic core of the wrapper.

Phase A is `bdio`'s idempotent mint. Phase B is here, and it exists to make one
sentence true under an arbitrarily-timed kill: **a launch either left no child
at all, or left a durable receipt naming the child it started.**

The mechanism is a fork barrier with a positive release:

```
parent                                   child
------                                   -----
pipe(ready), pipe(go)
fork ─────────────────────────────────▶  setsid()               (own process group)
                                         write "R" ────────────▶
read "R" (bounded)
read /proc/<pid>/stat  (start time)
write receipt: temp → fsync → rename → fsync(dir)
write GO = the exec-ledger line ───────▶ read GO (EOF ⇒ exit, never exec)
                                         assert the receipt exists
                                         append line, fsync   (O_APPEND)
                        ◀───────────────  write "A"
read "A" (bounded)                       execve
verify receipt + ledger
record_dispatch(handle)
```

Why each piece is load-bearing:

- **The release is a positive message, not a closed pipe.** If the parent dies
  before releasing, the child's `read` returns EOF, and EOF means EXIT — it
  must never be mistaken for "go". A barrier that opened on parent death would
  exec a child whose receipt was never written (drill 2).
- **The ledger line travels ON the release.** The parent knows the pid, so it
  renders the line; the child appends it. The append therefore happens only
  in a child that got past the barrier, and never in a parent that merely
  intended to start one — which is what makes `wc -l` count EXECS.
- **The ack closes the window before the parent's own verification.** Without
  it the parent would race the child's append and could not check the ledger
  at all.
- **The receipt is written before the release and read back after it.** A
  profile that ignored the injected launcher would be caught by that check,
  because it could not produce a receipt with this launch's id (§6).

The one window that remains is between the child's exec and `record_dispatch`:
bd still says `minted` while a process runs. The receipt closes it — a redispatch
that finds a receipt with a matching ledger line REATTACHES instead of exec'ing
a second time. The reverse residue (a ledger line the receipt cannot explain)
refuses loudly rather than risk a second child.

**The §5.4 precondition runs INSIDE this sequence**, between the mint and the
launch, and its §3.2 carry-forward trio is written to bd before `profile.launch`
is even called. That ordering is the point: `pre_attempt_commit` is what a later
rework's `intended_base_commit` is derived from, and an activation that ran
without it recorded silently reworks on top of the branch head — which after a
reject IS the rejected artifact (§3.2). It is skipped on the REATTACH and
already-dispatched paths for the same reason it exists: a child is running, and
resetting its tree is the last thing to do.

Linux-only: `os.fork`, `os.setsid` and process groups.
"""

from __future__ import annotations

import os
import select
import signal
import uuid
from typing import Final, Protocol

import structlog
from pydantic import BaseModel

from workflow_interpreter.bdio import (
    ActivationRecord,
    Lifecycle,
    MintReason,
    MintRequest,
    ProcessHandle,
    WorkflowStore,
)
from workflow_interpreter.supervisor import procfs
from workflow_interpreter.supervisor.clock import Clock, to_iso
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.errors import (
    ContinuationRefused,
    ExecLedgerError,
    ForkBarrierError,
    WrapperDirError,
)
from workflow_interpreter.supervisor.models import (
    RECORD_MODEL,
    ExecLedgerEntry,
    LaunchOutcome,
    LaunchReceipt,
    PreconditionResult,
    SteerIntent,
)
from workflow_interpreter.supervisor.paths import (
    ExecLedger,
    WrapperPaths,
    read_record,
    write_all,
    write_record,
)
from workflow_interpreter.supervisor.profile import (
    Profile,
    RunnerChannels,
    RunnerCommand,
    TaskSpec,
    channels_for,
)

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

READY: Final[bytes] = b"R"
ACK: Final[bytes] = b"A"
LENGTH_BYTES: Final[int] = 4
LENGTH_ORDER: Final = "big"

EXIT_SETUP_FAILED: Final[int] = 120
EXIT_BARRIER_CLOSED: Final[int] = 121
EXIT_NO_RECEIPT: Final[int] = 122
EXIT_EXEC_FAILED: Final[int] = 127

_MSG_NO_READY: Final[str] = (
    "child {pid} never reached the fork barrier within {timeout_s}s"
)
_MSG_NO_IDENTITY: Final[str] = (
    "child {pid} crossed the barrier but its §5.3 identity could not be read "
    "from /proc ({missing}); a handle that cannot prove liveness later is worse "
    "than no child at all, so this one is killed rather than recorded"
)
_MSG_NO_ACK: Final[str] = (
    "child {pid} was released but never acknowledged its exec-ledger append"
)
_MSG_NO_RECEIPT: Final[str] = (
    "no durable launch receipt for launch {launch_id} after launch; the profile "
    "did not exec through the supervisor's launcher (§5.2, §6)"
)
_MSG_HANDLE_DRIFT: Final[str] = (
    "the durable receipt for launch {launch_id} names a different process than "
    "the handle returned; the fork barrier was bypassed"
)
_MSG_LEDGER_COUNT: Final[str] = (
    "exec ledger for {activation_id} moved from {before} to {after} lines across "
    "one launch; exactly one exec must be appended (§5.2)"
)
_MSG_UNEXPLAINED: Final[str] = (
    "exec ledger for {activation_id} holds {count} line(s) that no durable "
    "receipt explains; refusing to exec a second child (§5.2)"
)
_MSG_NO_INSTRUCTIONS: Final[str] = (
    "activation {activation_id} was minted as a {reason} but dispatch was given "
    "no steer instructions; §8.1 continues a session via build_resume_command, "
    "and launching it fresh would discard the guidance the steer was for"
)
_MSG_RETRY_OF_CONTINUATION: Final[str] = (
    "activation {activation_id} is an {reason} descended from {predecessor}, a "
    "{continuation}; only a continuation reads the steer back, so this retry "
    "would relaunch the node's original brief in a fresh session and drop the "
    "guidance silently — refused until the retry can carry the steer forward "
    "(bead cr-o85.19)"
)
_MSG_NOT_A_CONTINUATION: Final[str] = (
    "dispatch was given steer instructions for activation {activation_id}, whose "
    "mint reason is {reason}; only a {expected} may resume another session (§8.1)"
)


class DispatchResult(BaseModel):
    """What one `dispatch()` did, and the evidence for it."""

    model_config = RECORD_MODEL

    activation: ActivationRecord
    outcome: LaunchOutcome
    idempotency_key: str
    minted: bool
    exec_count: int
    session_id: str = ""
    """What `Profile.prepare` pre-assigned for this launch (§5.2).

    Reported because it is not always what the mint carried: `prepare` is
    idempotent but may MINT the id for a vendor that can pre-assign one, and the
    caller that later steers this activation needs the id the child actually
    ran under. It is durable through `handle.session_id`, which
    `record_dispatch` writes to bd."""
    handle: ProcessHandle | None = None
    receipt: LaunchReceipt | None = None
    precondition: PreconditionResult | None = None
    """What §5.4 proved before this child was allowed to exec. `None` on the
    REATTACH and already-dispatched paths, where a child is already running and
    its tree is the last thing to touch."""


class TaskBuilder(Protocol):
    """Builds the §6 task for a freshly minted activation (foreman-owned)."""

    def __call__(
        self, activation: ActivationRecord, channels: RunnerChannels
    ) -> TaskSpec: ...  # pragma: no cover - protocol


class Precondition(Protocol):
    """Proves the §5.4 worktree precondition for a freshly minted activation."""

    def __call__(
        self, activation: ActivationRecord
    ) -> PreconditionResult: ...  # pragma: no cover - protocol


def append_ledger_line(ledger_path: str, line: bytes) -> None:
    """Append one exec-ledger line and make BOTH the bytes and the entry durable.

    `os.*` only: this runs in the forked child, between `fork` and `execve`.

    Two flushes, not one. `fsync` on the file descriptor guarantees the bytes;
    it says nothing about the DIRECTORY ENTRY that names the file, so a power
    loss right after the first exec could leave a durable launch receipt and no
    ledger at all — and a redispatch that finds a receipt with no matching
    ledger line relaunches, which is a second child for one activation. The
    receipt's own write already does temp → fsync → rename → fsync(dir); this
    is the same guarantee for the file the child creates (§5.2).
    """
    descriptor = os.open(ledger_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        write_all(descriptor, line)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(os.path.dirname(ledger_path), os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _read_exact(descriptor: int, size: int) -> bytes:
    """Read exactly `size` bytes, or fewer when the writer closed (EOF)."""
    chunks: list[bytes] = []
    remaining = size
    while remaining > 0:
        chunk = os.read(descriptor, remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _await_byte(descriptor: int, expected: bytes, timeout_s: float) -> bool:
    """Wait for one specific byte from the child, or give up after `timeout_s`."""
    readable, _, _ = select.select([descriptor], [], [], timeout_s)
    if not readable:
        return False
    return _read_exact(descriptor, len(expected)) == expected


class ForkBarrierLauncher:
    """The supervisor-owned exec: fork, barrier, ledger append, `execve` (§5.2)."""

    def __init__(
        self,
        config: SupervisorConfig,
        paths: WrapperPaths,
        clock: Clock,
        *,
        activation_id: str,
        launch_id: str,
    ) -> None:
        self._config = config
        self._paths = paths
        self._clock = clock
        self._activation_id = activation_id
        self._launch_id = launch_id

    @property
    def launch_id(self) -> str:
        """The nonce tying this launch's receipt to its exec-ledger line."""
        return self._launch_id

    def __call__(self, command: RunnerCommand) -> ProcessHandle:
        """Start the child behind the barrier and return its durable handle."""
        receipt_path = self._paths.receipt(self._activation_id)
        ledger_path = self._paths.ledger(self._activation_id)
        log_path = self._paths.log(self._activation_id)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        ready_read, ready_write = os.pipe()
        go_read, go_write = os.pipe()
        pid = os.fork()
        if pid == 0:  # pragma: no cover - the child never returns to pytest
            _child(
                ready_write=ready_write,
                ready_read=ready_read,
                go_read=go_read,
                go_write=go_write,
                receipt_path=str(receipt_path),
                ledger_path=str(ledger_path),
                log_path=str(log_path),
                command=command,
            )
        os.close(ready_write)
        os.close(go_read)
        try:
            return self._parent(
                pid,
                ready_read=ready_read,
                go_write=go_write,
                command=command,
                log_path=str(log_path),
            )
        finally:
            os.close(ready_read)
            os.close(go_write)

    def _parent(
        self,
        pid: int,
        *,
        ready_read: int,
        go_write: int,
        command: RunnerCommand,
        log_path: str,
    ) -> ProcessHandle:
        """Prove the child is parked, make the receipt durable, then release it."""
        if not _await_byte(ready_read, READY, self._config.barrier_timeout_s):
            _abandon(pid)
            raise ForkBarrierError(
                _MSG_NO_READY.format(pid=pid, timeout_s=self._config.barrier_timeout_s)
            )
        start_time = procfs.read_start_time(self._config, pid)
        boot_id = procfs.read_boot_id(self._config)
        if start_time is None or boot_id is None:
            # Both are halves of the §5.3 identity §5.6 proves liveness with.
            # `read_boot_id` answers `None` rather than raising now (§8.2's
            # INDETERMINATE contract), so the refusal has to be made here.
            _abandon(pid)
            missing = "start time" if start_time is None else "boot id"
            raise ForkBarrierError(_MSG_NO_IDENTITY.format(pid=pid, missing=missing))
        handle = ProcessHandle(
            pid=pid,
            pgid=os.getpgid(pid),
            host=self._config.host,
            host_boot_id=boot_id,
            proc_start_time=start_time,
            started_at=to_iso(self._clock.now()),
            log_path=log_path,
            session_id=command.session_id,
        )
        write_record(
            self._paths.receipt(self._activation_id),
            LaunchReceipt(
                launch_id=self._launch_id,
                root_id=self._paths.root_id,
                activation_id=self._activation_id,
                argv=command.argv,
                cwd=command.cwd,
                handle=handle,
            ),
        )
        line = ExecLedger.line(
            ExecLedgerEntry(
                launch_id=self._launch_id,
                activation_id=self._activation_id,
                pid=pid,
                at=to_iso(self._clock.now()),
            )
        )
        os.write(go_write, len(line).to_bytes(LENGTH_BYTES, LENGTH_ORDER) + line)
        if not _await_byte(ready_read, ACK, self._config.barrier_timeout_s):
            _abandon(pid)
            raise ForkBarrierError(_MSG_NO_ACK.format(pid=pid))
        _LOG.info(
            "wf.child.launched",
            activation_id=self._activation_id,
            launch_id=self._launch_id,
            pid=pid,
        )
        return handle


def _abandon(pid: int) -> None:
    """Kill and reap a child that never became a runner. Best effort by design.

    The GROUP, not the pid, whenever the child got as far as `setsid` — which
    is before it writes READY, so a child that timed out at the ACK has one for
    certain. Killing the leader alone leaves its own children running: a
    barrier failure would abandon a live process tree with no handle, no
    receipt anybody trusts, and nothing that will ever come back for it.

    `getpgid(pid) == pid` is the test for "it owns a group". A child that died
    before `setsid` is still in the SUPERVISOR's group, and `killpg` on its pid
    would then either hit nothing or hit a group that is not ours — so that
    case gets a plain `kill`.
    """
    try:
        owns_group = os.getpgid(pid) == pid
    except (ProcessLookupError, PermissionError):
        owns_group = False
    try:
        if owns_group:
            os.killpg(pid, signal.SIGKILL)
        else:
            os.kill(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        return
    procfs.reap(pid)


def _child(
    *,
    ready_write: int,
    ready_read: int,
    go_read: int,
    go_write: int,
    receipt_path: str,
    ledger_path: str,
    log_path: str,
    command: RunnerCommand,
) -> None:  # pragma: no cover - executed only in the forked child
    """The barrier side of the fork. Never returns: it execs or `_exit`s.

    Deliberately `os.*` only — no logging, no pydantic, no allocation-heavy
    library call between `fork` and `execve`.
    """
    try:
        os.close(ready_read)
        os.close(go_write)
        os.setsid()
        os.write(ready_write, READY)
        header = _read_exact(go_read, LENGTH_BYTES)
        if len(header) != LENGTH_BYTES:
            os._exit(EXIT_BARRIER_CLOSED)
        line = _read_exact(go_read, int.from_bytes(header, LENGTH_ORDER))
        if not line:
            os._exit(EXIT_BARRIER_CLOSED)
        os.stat(receipt_path)
        append_ledger_line(ledger_path, line)
        os.write(ready_write, ACK)
        os.close(ready_write)
        os.close(go_read)
        log = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        os.dup2(log, 1)
        os.dup2(log, 2)
        os.close(log)
        # fd 0 is the WRAPPER's stdin, and every CLI probed reads or waits on
        # it: claude stalls 3s per launch and then warns, codex announces
        # "Reading additional input from stdin...", and a runner given no prompt
        # argument blocks on it outright. Left connected, a headless child also
        # competes with the supervisor for a terminal it must never own.
        devnull = os.open(os.devnull, os.O_RDONLY)
        os.dup2(devnull, 0)
        os.close(devnull)
        os.chdir(command.cwd)
    except FileNotFoundError:
        os._exit(EXIT_NO_RECEIPT)
    except OSError:
        os._exit(EXIT_SETUP_FAILED)
    try:
        os.execvpe(command.argv[0], list(command.argv), dict(command.env))
    except OSError:
        os._exit(EXIT_EXEC_FAILED)


class Dispatcher:
    """§5.2 phase A + phase B for one instance: mint, then launch behind the barrier."""

    def __init__(
        self,
        paths: WrapperPaths,
        store: WorkflowStore,
        clock: Clock,
    ) -> None:
        self._paths = paths
        self._store = store
        self._clock = clock

    def dispatch(
        self,
        request: MintRequest,
        profile: Profile,
        build_task: TaskBuilder,
        precondition: Precondition | None = None,
        *,
        instructions: str | None = None,
    ) -> DispatchResult:
        """Mint (idempotent), prove the precondition, then exec at most once.

        `instructions` turns the launch into a §8.1 CONTINUATION: the invocation
        comes from `build_resume_command`, so the child rejoins the session its
        predecessor was steered out of instead of starting a new one. It is
        required for a `steer-continuation` mint and refused for any other, so
        neither half of §8.1's "exactly one continuation, via
        `build_resume_command`" can be lost by a caller forgetting an argument.

        A caller that does not hold the text does not have to: for a
        `steer-continuation` it is READ from the predecessor's persisted steer
        intent (`_steer_instructions`). That is what makes the continuation
        dispatchable through `Supervisor.run` — the only entry point that also
        watches the child and records its exit — without threading a human's
        prose through every foreman signature, and it is the same file §5.6
        recovery resumes a crashed steer from. bd never sees the prose at all.
        """
        minted = self._store.mint_activation(self._paths.root_id, request)
        activation = minted.activation
        activation_id = activation.activation_id
        ledger = ExecLedger(self._paths.ledger(activation_id))
        if activation.metadata.lifecycle is not Lifecycle.MINTED:
            return DispatchResult(
                activation=activation,
                outcome=LaunchOutcome.ALREADY_DISPATCHED,
                idempotency_key=minted.idempotency_key,
                minted=minted.created,
                exec_count=ledger.count(),
                handle=activation.metadata.handle,
            )
        self._paths.ensure_activation_dir(activation_id)
        reattached = self._reattach(activation_id, ledger)
        if reattached is not None:
            record = self._store.record_dispatch(activation_id, reattached.handle)
            _LOG.warning(
                "wf.dispatch.reattached",
                activation_id=activation_id,
                launch_id=reattached.launch_id,
            )
            return DispatchResult(
                activation=record,
                outcome=LaunchOutcome.REATTACHED,
                idempotency_key=minted.idempotency_key,
                minted=minted.created,
                exec_count=ledger.count(),
                handle=reattached.handle,
                receipt=reattached,
            )
        self._refuse_retry_of_continuation(activation)
        instructions = self._steer_instructions(activation, instructions)
        self._assert_continuation(activation, instructions)
        activation, prepared = self._prepare(activation, precondition)
        return self._launch(
            activation,
            minted.idempotency_key,
            minted.created,
            profile,
            build_task,
            ledger,
            prepared,
            instructions,
        )

    def _steer_instructions(
        self, activation: ActivationRecord, instructions: str | None
    ) -> str | None:
        """Recover a continuation's steer text from the predecessor's intent file.

        The caller's value always wins; this only fills the gap. It is narrow on
        purpose — a `steer-continuation` mint, a predecessor to read, and that
        predecessor's own `steer-intent.json`, which `Steerer.steer` wrote
        durably before it killed anything. Nothing else can reach
        `build_resume_command` this way.

        A malformed intent classifies as ABSENT rather than raising, for the
        reason `_reattach` gives: the refusal that follows is deterministic and
        recoverable, while a parse error out of `dispatch` wedges the activation
        on every subsequent tick (drill 18).
        """
        if instructions is not None:
            return instructions
        metadata = activation.metadata
        predecessor = metadata.predecessor_activation_id
        if metadata.mint_reason is not MintReason.STEER_CONTINUATION or not predecessor:
            return None
        try:
            intent = read_record(self._paths.steer_intent(predecessor), SteerIntent)
        except WrapperDirError as exc:
            _LOG.warning(
                "wf.dispatch.steer_intent_malformed",
                activation_id=activation.activation_id,
                predecessor_activation_id=predecessor,
                error=str(exc),
            )
            return None
        return None if intent is None else intent.instructions

    def _refuse_retry_of_continuation(self, activation: ActivationRecord) -> None:
        """Fail closed on an infra retry descended from a §8.1 continuation.

        `_steer_instructions` keys on the mint reason, so a retry of a
        continuation passes every continuation check and takes the fresh-launch
        branch with the node's ORIGINAL brief — the steer evaporating with no
        refusal and no log line. The WHOLE retry ancestry is walked: a refused
        retry is never dispatched but stays `minted`, and a minted activation
        may still be closed `error_transport`, so a retry behind it has an
        `infra-retry` predecessor and a one-hop check would let it through.
        How a retry carries the steer forward is bead cr-o85.19.
        """
        metadata = activation.metadata
        if metadata.mint_reason is not MintReason.INFRA_RETRY:
            return
        seen: set[str] = {activation.activation_id}
        predecessor_id = metadata.predecessor_activation_id
        while predecessor_id and predecessor_id not in seen:
            seen.add(predecessor_id)
            predecessor = self._store.reads.load_activation(predecessor_id)
            reason = predecessor.metadata.mint_reason
            if reason is MintReason.STEER_CONTINUATION:
                raise ContinuationRefused(
                    _MSG_RETRY_OF_CONTINUATION.format(
                        activation_id=activation.activation_id,
                        reason=MintReason.INFRA_RETRY.value,
                        predecessor=predecessor_id,
                        continuation=MintReason.STEER_CONTINUATION.value,
                    )
                )
            if reason is not MintReason.INFRA_RETRY:
                return
            predecessor_id = predecessor.metadata.predecessor_activation_id

    @staticmethod
    def _assert_continuation(
        activation: ActivationRecord, instructions: str | None
    ) -> None:
        """Refuse a §8.1 mismatch between the mint reason and the invocation."""
        is_continuation = (
            activation.metadata.mint_reason is MintReason.STEER_CONTINUATION
        )
        if is_continuation and instructions is None:
            raise ContinuationRefused(
                _MSG_NO_INSTRUCTIONS.format(
                    activation_id=activation.activation_id,
                    reason=MintReason.STEER_CONTINUATION.value,
                )
            )
        if not is_continuation and instructions is not None:
            raise ContinuationRefused(
                _MSG_NOT_A_CONTINUATION.format(
                    activation_id=activation.activation_id,
                    reason=activation.metadata.mint_reason.value,
                    expected=MintReason.STEER_CONTINUATION.value,
                )
            )

    def _prepare(
        self, activation: ActivationRecord, precondition: Precondition | None
    ) -> tuple[ActivationRecord, PreconditionResult | None]:
        """Prove §5.4 and make its §3.2 carry-forward durable, before any exec.

        The bd write happens here rather than after the launch on purpose: it
        is the one fact about this attempt that a LATER activation reads, so a
        crash between the exec and it would leave a rework deriving its base
        from the branch head instead of from what this attempt started on
        (§3.2, §5.4).
        """
        if precondition is None:
            return activation, None
        prepared = precondition(activation)
        record = self._store.record_precondition(
            activation.activation_id, prepared.carry_forward()
        )
        return record, prepared

    def _reattach(self, activation_id: str, ledger: ExecLedger) -> LaunchReceipt | None:
        """Decide whether an exec already happened for this activation (§5.2).

        Fail-closed in both directions: a receipt whose launch never reached the
        ledger means no child ran (relaunch); a ledger line no receipt explains
        means a child DID run and cannot be identified — refuse rather than
        start a second one.

        A receipt that does not PARSE is treated as absent, and the ledger then
        decides. It used to raise `WrapperDirError` straight out of `dispatch`,
        so a receipt torn by a crash wedged the activation on every subsequent
        tick — even in the case where the ledger is empty and therefore no
        child can possibly have run. Malformed input classifies here for the
        same reason it does in §5.6: a crash loop is strictly worse than a
        deterministic answer (drill 18).
        """
        receipt = self._read_receipt(activation_id)
        if receipt is not None and ledger.has_launch(receipt.launch_id):
            return receipt
        count = ledger.count()
        if count:
            raise ExecLedgerError(
                _MSG_UNEXPLAINED.format(activation_id=activation_id, count=count)
            )
        return None

    def _read_receipt(self, activation_id: str) -> LaunchReceipt | None:
        """The durable receipt, or `None` when there is none the wrapper can read."""
        try:
            return read_record(self._paths.receipt(activation_id), LaunchReceipt)
        except WrapperDirError as exc:
            _LOG.warning(
                "wf.dispatch.receipt_malformed",
                activation_id=activation_id,
                error=str(exc),
            )
            return None

    def _launch(
        self,
        activation: ActivationRecord,
        idempotency_key: str,
        created: bool,
        profile: Profile,
        build_task: TaskBuilder,
        ledger: ExecLedger,
        prepared: PreconditionResult | None = None,
        instructions: str | None = None,
    ) -> DispatchResult:
        """Build the command, exec behind the barrier, verify, record the handle."""
        activation_id = activation.activation_id
        channels = channels_for(
            self._paths.activation_dir(activation_id),
            self._paths.log(activation_id),
            activation_id,
        )
        task = build_task(activation, channels)
        # §5.2: the session id is PRE-ASSIGNED by the profile and never
        # discovered from output. Nothing used to call `prepare`, so the id was
        # whatever the mint request happened to carry — for claude, a value the
        # CLI refuses unless the caller had already minted a UUID by hand, and
        # for a continuation, no link to the session being resumed at all.
        session_id = profile.prepare(activation)
        command = (
            profile.build_command(task, session_id)
            if instructions is None
            else profile.build_resume_command(session_id, instructions, task)
        )
        launcher = ForkBarrierLauncher(
            self._paths.config,
            self._paths,
            self._clock,
            activation_id=activation_id,
            launch_id=uuid.uuid4().hex,
        )
        before = ledger.count()
        handle = profile.launch(command, launcher)
        self._assert_barrier_held(activation_id, launcher, handle, ledger, before)
        record = self._store.record_dispatch(activation_id, handle)
        return DispatchResult(
            activation=record,
            outcome=LaunchOutcome.LAUNCHED,
            idempotency_key=idempotency_key,
            minted=created,
            exec_count=ledger.count(),
            session_id=session_id,
            handle=handle,
            receipt=self._read_receipt(activation_id),
            precondition=prepared,
        )

    def _assert_barrier_held(
        self,
        activation_id: str,
        launcher: ForkBarrierLauncher,
        handle: ProcessHandle,
        ledger: ExecLedger,
        before: int,
    ) -> None:
        """Verify the launch went through the barrier — never assume it did (§6)."""
        receipt = read_record(self._paths.receipt(activation_id), LaunchReceipt)
        if receipt is None or receipt.launch_id != launcher.launch_id:
            raise ForkBarrierError(_MSG_NO_RECEIPT.format(launch_id=launcher.launch_id))
        if receipt.handle != handle:
            raise ForkBarrierError(
                _MSG_HANDLE_DRIFT.format(launch_id=launcher.launch_id)
            )
        after = ledger.count()
        if after != before + 1 or not ledger.has_launch(launcher.launch_id):
            raise ExecLedgerError(
                _MSG_LEDGER_COUNT.format(
                    activation_id=activation_id, before=before, after=after
                )
            )
