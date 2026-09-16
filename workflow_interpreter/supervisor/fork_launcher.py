"""Supervisor-owned fork barrier, launch receipts, and process I/O ownership."""

from __future__ import annotations

import os
import select
import shutil
import signal
from collections.abc import Mapping
from pathlib import Path
from typing import Final

import structlog

from workflow_interpreter.bdio import (
    ProcessHandle,
)
from workflow_interpreter.contracts.execution import (
    ExecutionGrants,
)
from workflow_interpreter.contracts.transport import RunnerTransport
from workflow_interpreter.supervisor import procfs
from workflow_interpreter.supervisor.clock import Clock, to_iso
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.errors import (
    ForkBarrierAbortError,
    ForkBarrierError,
    WrapperDirError,
)
from workflow_interpreter.supervisor.models import (
    ExecLedgerEntry,
    LaunchReceipt,
    LaunchReceiptState,
    TerminationProof,
)
from workflow_interpreter.supervisor.paths import (
    ExecLedger,
    WrapperPaths,
    read_record,
    write_all,
    write_record,
)
from workflow_interpreter.supervisor.profile import (
    RunnerCommand,
)
from workflow_interpreter.supervisor.rpc_pipes import RpcPipes
from workflow_interpreter.supervisor.sandbox import (
    ENV_UV_CACHE_DIR,
    ENV_UV_OFFLINE,
    ENV_UV_PYTHON_INSTALL_DIR,
    UV_PYTHON_DIRECTORY,
    SandboxMode,
    SandboxPlan,
    wrap,
)
from workflow_interpreter.supervisor.toolchain_models import SeedReceipt

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

READY: Final[bytes] = b"R"
ACK: Final[bytes] = b"A"
LENGTH_BYTES: Final[int] = 4
LENGTH_ORDER: Final = "big"

EXIT_SETUP_FAILED: Final[int] = 120
EXIT_BARRIER_CLOSED: Final[int] = 121
EXIT_NO_RECEIPT: Final[int] = 122
EXIT_EXEC_FAILED: Final[int] = 127
_ENV_PATH: Final[str] = "PATH"

_MSG_NO_READY: Final[str] = (
    "child {pid} never reached the fork barrier within {timeout_s}s"
)
_MSG_NO_IDENTITY: Final[str] = (
    "child {pid} crossed the barrier but its §5.3 identity could not be read "
    "from /proc ({missing}); a handle that cannot prove liveness later is worse "
    "than no child at all, so this one is killed rather than recorded"
)
MSG_NO_ACK: Final[str] = (
    "child {pid} was released but never acknowledged its exec-ledger append"
)


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
        plan: SandboxPlan,
        sandbox: SandboxMode,
        seed_receipts: tuple[SeedReceipt, ...] = (),
        execution_grants: ExecutionGrants | None = None,
    ) -> None:
        self._config = config
        self._paths = paths
        self._clock = clock
        self._activation_id = activation_id
        self._launch_id = launch_id
        self._plan = plan
        self._seed_receipts = seed_receipts
        self._execution_grants = execution_grants
        self._sandbox = sandbox
        self._rpc_pipes: RpcPipes | None = None
        """The §2 mount bound, injected rather than computed here: `plan_for`
        needs the `TaskSpec`, and this class is deliberately handed a built
        `RunnerCommand` and nothing else. Both are REQUIRED keywords — a default
        would let a caller launch unbounded by forgetting an argument, which is
        the one failure mode O1 exists to prevent."""

    def take_rpc_pipes(self) -> RpcPipes | None:
        """Transfer parent pipe ownership after the barrier succeeds."""
        pipes, self._rpc_pipes = self._rpc_pipes, None
        return pipes

    @property
    def launch_id(self) -> str:
        """The nonce tying this launch's receipt to its exec-ledger line."""
        return self._launch_id

    def __call__(self, command: RunnerCommand) -> ProcessHandle:
        """Start the child behind the barrier and return its durable handle.

        The mount bound is the LAST transform before the receipt: everything a
        profile built is already decided, and the WRAPPED argv is what the
        receipt records, because `handle.pid` names `bwrap` rather than the
        vendor (bwrap forks). The inner argv would describe a process the handle
        does not name, and the wrapped one is the durable audit record of the
        exact bound this child ran under.

        The launcher rewrites the uv cache paths in both modes, so `off` and
        `bwrap` runs use the same private layout; only `wrap` emits a bind.
        """
        receipt_path = self._paths.receipt(self._activation_id)
        ledger_path = self._paths.ledger(self._activation_id)
        log_path = self._paths.log(self._activation_id)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # Resolved BEFORE wrapping, because `bwrap` makes argv[0] always exist:
        # a vanished vendor CLI inside the box would grade as a plain non-zero
        # exit and drill 22's exit-127 sentinel would stop meaning anything.
        vendor_missing = not _vendor_resolves(command.argv[0], command.env)
        env = dict(command.env)
        env[ENV_UV_OFFLINE] = "1"
        env[ENV_UV_CACHE_DIR] = str(self._plan.toolchain_cache[0])
        env[ENV_UV_PYTHON_INSTALL_DIR] = str(
            self._plan.toolchain_cache[0] / UV_PYTHON_DIRECTORY
        )
        wrapped = command.model_copy(
            update={
                "argv": wrap(command.argv, self._plan, mode=self._sandbox),
                "env": env,
            }
        )

        pipes = RpcPipes() if command.transport is RunnerTransport.STDIO_RPC else None
        self._rpc_pipes = pipes
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
                command=wrapped,
                vendor_missing=vendor_missing,
                rpc_pipes=pipes,
            )
        os.close(ready_write)
        os.close(go_read)
        if pipes is not None:
            pipes.parent_setup()
        try:
            return self._parent(
                pid,
                ready_read=ready_read,
                go_write=go_write,
                command=wrapped,
                log_path=str(log_path),
            )
        except BaseException:
            if pipes is not None:
                pipes.close()
            raise
        finally:
            os.close(ready_read)
            os.close(go_write)

    def _owner_handle(self) -> ProcessHandle:
        """Bind RPC ownership before exec so recovery can prove wrapper loss."""
        pid = os.getpid()
        start = procfs.read_start_time(self._config, pid)
        boot = procfs.read_boot_id(self._config)
        if start is None or boot is None:
            raise ForkBarrierError(_MSG_NO_IDENTITY.format(pid=pid, missing="owner"))
        return ProcessHandle(
            pid=pid,
            pgid=os.getpgrp(),
            host=self._config.host,
            host_boot_id=boot,
            proc_start_time=start,
            started_at=to_iso(self._clock.now()),
            log_path="",
            session_id="",
        )

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
            _abandon(self._config, self._clock, pid)
            raise ForkBarrierError(
                _MSG_NO_READY.format(pid=pid, timeout_s=self._config.barrier_timeout_s)
            )
        start_time = procfs.read_start_time(self._config, pid)
        boot_id = procfs.read_boot_id(self._config)
        if start_time is None or boot_id is None:
            # Both are halves of the §5.3 identity §5.6 proves liveness with.
            # `read_boot_id` answers `None` rather than raising now (§8.2's
            # INDETERMINATE contract), so the refusal has to be made here.
            _abandon(self._config, self._clock, pid)
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
                transport=command.transport,
                owner=self._owner_handle()
                if command.transport is RunnerTransport.STDIO_RPC
                else None,
                vendor_state=command.env.get("CODEX_HOME")
                if command.transport is RunnerTransport.STDIO_RPC
                else None,
                launch_id=self._launch_id,
                root_id=self._paths.root_id,
                activation_id=self._activation_id,
                argv=command.argv,
                cwd=command.cwd,
                handle=handle,
                sandbox=self._sandbox,
                seed_receipts=self._seed_receipts,
                execution_grants=self._execution_grants,
                tool_network=(
                    self._execution_grants.policy.tool_network
                    if self._execution_grants
                    else None
                ),
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
            _abort_child(
                self._config,
                self._clock,
                self._paths.receipt(self._activation_id),
                handle,
            )
            raise ForkBarrierAbortError(MSG_NO_ACK.format(pid=pid))
        _LOG.info(
            "wf.child.launched",
            activation_id=self._activation_id,
            launch_id=self._launch_id,
            pid=pid,
        )
        return handle


def _vendor_resolves(program: str, env: Mapping[str, str]) -> bool:
    """Whether the vendor `argv[0]` names something the CHILD could exec.

    Against `command.env`, never `os.environ`: `_child` execs with
    `dict(command.env)` and nothing else, so a vendor the profile put on a
    private `PATH` is perfectly runnable and a vendor on the WRAPPER's `PATH`
    alone is not. Resolving against the wrapper's environment answers a
    different question and gets it wrong in both directions.

    `shutil.which` first (it applies `PATH` and the executable bit), then a bare
    `os.stat`, so a path-shaped `argv[0]` that exists but is on no `PATH` is not
    mistaken for a vanished CLI.
    """
    if shutil.which(program, path=env.get(_ENV_PATH)) is not None:
        return True
    try:
        os.stat(program)
    except OSError:
        return False
    return True


def _abandon(config: SupervisorConfig, clock: Clock, pid: int) -> None:
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

    Both callers run before the parent writes either the receipt or the release:
    the no-READY path has no handle, and the no-identity path refuses to create
    one. That child therefore cannot have appended an exec-ledger line or become
    a reattachable runner, so no later monitor or §5.6 recovery observer needs
    its wait status. After SIGKILL, this path waits one short, identity-proven
    interval before collecting so the wrapper does not carry a zombie; without
    an identity it keeps `collect` non-blocking rather than guessing.
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
    start_time = procfs.read_start_time(config, pid)
    boot_id = procfs.read_boot_id(config)
    if start_time is not None and boot_id is not None:
        handle = ProcessHandle(
            pid=pid,
            pgid=pid if owns_group else os.getpgrp(),
            host=config.host,
            host_boot_id=boot_id,
            proc_start_time=start_time,
            started_at=to_iso(clock.now()),
            log_path="",
            session_id="",
        )
        procfs.await_death(config, handle, clock, config.kill_grace_s)
    # `collect` consumes a status only when the kernel has already confirmed death.
    procfs.collect(pid)


def _abort_child(
    config: SupervisorConfig,
    clock: Clock,
    receipt_path: Path,
    handle: ProcessHandle,
) -> TerminationProof:
    """Terminate an ACK-timeout child and make its receipt say what was proven.

    `terminate` alone is allowed to reap, and only after handle identity proves
    death. If that proof is unavailable, `abort-pending` preserves the durable
    handle solely for recovery to finish the kill; dispatch never adopts it.
    """
    termination = procfs.terminate(config, handle, clock)
    try:
        receipt = read_record(receipt_path, LaunchReceipt)
    except WrapperDirError as exc:
        _LOG.warning(
            "wf.abort.receipt_malformed", path=str(receipt_path), error=str(exc)
        )
        receipt = None
    if receipt is not None and receipt.handle == handle:
        state = (
            LaunchReceiptState.ABORTED
            if termination.confirmed_dead
            else LaunchReceiptState.ABORT_PENDING
        )
        write_record(
            receipt_path,
            receipt.model_copy(
                update={"state": state, "abort_exit_code": termination.exit_code}
            ),
        )
    return termination


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
    vendor_missing: bool,
    rpc_pipes: RpcPipes | None = None,
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
        if rpc_pipes is not None:
            log = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            os.close(log)
            rpc_pipes.child_setup()
        else:
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
    # The sentinel fires HERE and never on the parent path: the receipt is
    # already durable, and an `os._exit` in the parent would kill the wrapper
    # mid-dispatch. This is the status `execvpe` itself would have produced
    # without the box, so drill 22 keeps observing what it always observed.
    if vendor_missing:
        os._exit(EXIT_EXEC_FAILED)
    try:
        os.execvpe(command.argv[0], list(command.argv), dict(command.env))
    except OSError:
        os._exit(EXIT_EXEC_FAILED)
