"""§5.2 two-phase activation: the fork barrier and the exec ledger, for real.

Marked `proc` because every test here forks an actual child and execs an actual
`/bin/sh` under `tmp_path`. That is deliberate: the property under test is
"exactly one exec happened, and the receipt naming it was durable first", and
a mocked launcher cannot exhibit it.

Drills: 1 (crash after mint / before exec — `wc -l == 1` across the drill),
2 (crash after the receipt is durable / before the child execs), plus the
exec→`record_dispatch` window the receipt exists to close.
"""

from __future__ import annotations

import os
import signal
import sys
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from tests._supervisor import (
    IMPLEMENT,
    SESSION_ID,
    ChildScript,
    FakeProfile,
    FrozenClock,
    entry_mint,
    handle_for,
    head_of,
    make_config,
    make_paths,
    make_repo,
    make_root,
    make_store,
    node_of,
    task_builder,
)
from workflow_interpreter.bdio import Lifecycle
from workflow_interpreter.bdio.errors import LifecycleConflictError
from workflow_interpreter.supervisor import (
    Dispatcher,
    ExecLedger,
    ExecLedgerEntry,
    ExecLedgerError,
    ForkBarrierAbortError,
    ForkBarrierError,
    ForkBarrierLauncher,
    LaunchOutcome,
    LaunchReceipt,
    SupervisorConfig,
    WrapperPaths,
    channels_for,
)
from workflow_interpreter.supervisor import launch as launch_module
from workflow_interpreter.supervisor.models import LaunchReceiptState
from workflow_interpreter.supervisor.paths import read_record, write_record
from workflow_interpreter.supervisor.profile import RunnerCommand
from workflow_interpreter.supervisor.sandbox import (
    ENV_UV_CACHE_DIR,
    ENV_UV_PYTHON_INSTALL_DIR,
    UV_CACHE_DIRECTORY,
    UV_PYTHON_DIRECTORY,
    SandboxMode,
    SandboxPlan,
    wrap,
)

pytestmark = pytest.mark.proc

MARKER_JSON = '{"outcome":"done"}'
WAIT_TIMEOUT_S = 20.0
FSYNC_FILE_AND_DIR = 2
"""The ledger append must flush the bytes AND the directory entry (§5.2)."""


class Lab:
    """A repo, an in-memory bd instance, a wrapper dir and a fake runner."""

    def __init__(self, tmp_path: Path, script: ChildScript | None = None) -> None:
        self.repo = make_repo(tmp_path)
        self.base = head_of(self.repo)
        self.config: SupervisorConfig = make_config(
            self.repo, tmp_path, fake_proc=False
        )
        self.fake_bd, self.store = make_store(tmp_path, self.base)
        self.root = make_root(self.store, self.repo, "launch-instance")
        self.paths: WrapperPaths = make_paths(self.config, self.root.root_id)
        self.clock = FrozenClock()
        self.node = node_of(self.root.definition.document, IMPLEMENT)
        self.profile = FakeProfile(script or ChildScript(marker=MARKER_JSON))
        self.dispatcher = Dispatcher(self.paths, self.store, self.clock)
        self.build_task = task_builder(self.repo, self.node)

    def dispatch(self) -> object:
        """Run one dispatch through the whole §5.2 sequence."""
        return self.dispatcher.dispatch(entry_mint(), self.profile, self.build_task)

    def ledger_for(self, activation_id: str) -> ExecLedger:
        """That activation's exec ledger."""
        return ExecLedger(self.paths.ledger(activation_id))

    def wc_l(self, activation_id: str) -> int:
        """`wc -l` on the exec ledger — the drills' instrumentation."""
        return self.ledger_for(activation_id).count()


@pytest.fixture
def lab(tmp_path: Path) -> Lab:
    """A launch lab with a fake runner that writes a `done` marker and exits."""
    return Lab(tmp_path)


def _wait(pid: int) -> int:
    """Reap the launched child and return its exit status."""
    _, status = os.waitpid(pid, 0)
    return status


def test_launch_records_a_durable_receipt_and_exactly_one_exec(lab: Lab) -> None:
    """§5.2: receipt durable BEFORE exec; one ledger line per real exec."""
    result = lab.dispatch()

    assert result.outcome is LaunchOutcome.LAUNCHED
    assert result.handle is not None
    activation_id = result.activation.activation_id
    receipt = read_record(lab.paths.receipt(activation_id), LaunchReceipt)
    assert receipt is not None
    assert receipt.handle == result.handle
    assert lab.wc_l(activation_id) == 1
    assert lab.ledger_for(activation_id).has_launch(receipt.launch_id)
    _wait(result.handle.pid)


def test_handle_carries_the_liveness_facts(lab: Lab) -> None:
    """§5.3: pid, its own pgid, the boot id and `/proc` start time, all recorded."""
    result = lab.dispatch()
    handle = result.handle
    assert handle is not None

    assert handle.pgid == handle.pid
    assert handle.session_id == SESSION_ID
    assert (
        handle.host_boot_id
        == Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
    )
    assert handle.proc_start_time.isdigit()
    assert result.activation.metadata.lifecycle is Lifecycle.DISPATCHED
    assert result.activation.metadata.handle == handle
    _wait(handle.pid)


def test_dispatch_makes_the_prepared_session_id_durable_on_the_activation(
    lab: Lab,
) -> None:
    """§5.2: `prepare()` is the only minter of ids, and dispatch records it.

    The mint carries no session id at all — the foreman used to pre-assign a
    UUID for one hard-coded profile name — so the id a continuation resumes
    exists only because the same bd write that records the handle also writes
    it back onto the activation (cr-o85.34.9).
    """
    result = lab.dispatcher.dispatch(
        entry_mint(session_id=""), lab.profile, lab.build_task
    )

    assert result.session_id == SESSION_ID
    assert result.activation.metadata.session_id == SESSION_ID
    assert (
        lab.store.reads.load_activation(
            result.activation.activation_id
        ).metadata.session_id
        == SESSION_ID
    )
    assert result.handle is not None
    _wait(result.handle.pid)


def test_a_second_dispatch_never_renames_a_recorded_session(lab: Lab) -> None:
    """The recorded id wins, and a contradicting one fails loud (§5.1, §5.2).

    Re-dispatching short-circuits before the guard, so the guard is exercised
    where a REATTACH would reach it: `record_dispatch` called again on the
    dispatched row with a handle naming another session. Silently keeping the
    first would leave two rows describing a child nobody can resume.
    """
    first = lab.dispatcher.dispatch(
        entry_mint(session_id=""), lab.profile, lab.build_task
    )
    assert first.handle is not None
    _wait(first.handle.pid)
    activation_id = first.activation.activation_id

    again = lab.dispatcher.dispatch(
        entry_mint(session_id=""),
        FakeProfile(session_id="a-different-session"),
        lab.build_task,
    )
    assert again.outcome is LaunchOutcome.ALREADY_DISPATCHED
    assert again.activation.metadata.session_id == SESSION_ID

    assert (
        lab.store.record_dispatch(activation_id, first.handle).metadata.session_id
        == SESSION_ID
    )
    with pytest.raises(LifecycleConflictError, match="a-different-session"):
        lab.store.record_dispatch(
            activation_id,
            first.handle.model_copy(update={"session_id": "a-different-session"}),
        )
    assert (
        lab.store.reads.load_activation(activation_id).metadata.session_id == SESSION_ID
    )


def test_a_handle_that_renames_a_minted_session_is_refused(tmp_path: Path) -> None:
    """The silent case: a MINTED session and a handle naming another one.

    Nothing raises on this path — the lifecycle is legal and the handle is the
    first one recorded — so the divergent id used to be simply dropped, leaving
    the row claiming a session the child never ran (§5.2).
    """
    lab = Lab(tmp_path)
    minted = lab.store.mint_activation(
        lab.paths.root_id, entry_mint(session_id="minted-session")
    ).activation

    with pytest.raises(LifecycleConflictError, match="minted-session"):
        lab.store.record_dispatch(
            minted.activation_id,
            handle_for(1, log_path=str(lab.paths.log(minted.activation_id))).model_copy(
                update={"session_id": "a-different-session"}
            ),
        )

    assert (
        lab.store.reads.load_activation(minted.activation_id).metadata.lifecycle
        is Lifecycle.MINTED
    )


def test_child_writes_through_the_runner_channels(lab: Lab) -> None:
    """§6: the wrapper-provided channels are what the child actually writes to."""
    result = lab.dispatch()
    assert result.handle is not None
    _wait(result.handle.pid)

    activation_id = result.activation.activation_id
    assert lab.paths.outcome(activation_id).read_text(encoding="utf-8") == MARKER_JSON


def test_mint_then_crash_then_dispatch_execs_once(lab: Lab) -> None:
    """Drill 1: a restart after the mint re-finds the key and execs exactly once."""
    first = lab.store.mint_activation(lab.root.root_id, entry_mint())

    result = lab.dispatch()

    assert result.minted is False
    assert result.activation.activation_id == first.activation.activation_id
    assert lab.wc_l(result.activation.activation_id) == 1
    assert result.handle is not None
    _wait(result.handle.pid)


def test_receipt_without_a_ledger_line_relaunches_once(lab: Lab) -> None:
    """Drill 2: the child never crossed the barrier, so relaunch appends ONE line."""
    minted = lab.store.mint_activation(lab.root.root_id, entry_mint())
    activation_id = minted.activation.activation_id
    lab.paths.ensure_activation_dir(activation_id)
    stale = LaunchReceipt(
        launch_id="never-crossed",
        root_id=lab.root.root_id,
        activation_id=activation_id,
        argv=("/bin/false",),
        cwd=str(lab.repo),
        handle=minted.activation.metadata.handle
        or _placeholder_handle(lab, activation_id),
    )
    write_record(lab.paths.receipt(activation_id), stale)
    assert lab.wc_l(activation_id) == 0

    result = lab.dispatch()

    assert result.outcome is LaunchOutcome.LAUNCHED
    assert lab.wc_l(activation_id) == 1
    assert not lab.ledger_for(activation_id).has_launch("never-crossed")
    assert result.handle is not None
    _wait(result.handle.pid)


def test_aborted_receipt_never_reattaches_even_with_a_ledger_line(
    lab: Lab,
) -> None:
    """A barrier abort is never adopted as a launched runner.

    The concrete input includes a ledger line because a child can append before
    its ACK is lost. Neither an `aborted` receipt nor that line authorizes
    `record_dispatch` or a second child.
    """
    minted = lab.store.mint_activation(lab.root.root_id, entry_mint())
    activation_id = minted.activation.activation_id
    lab.paths.ensure_activation_dir(activation_id)
    receipt = LaunchReceipt(
        launch_id="abort-pending",
        root_id=lab.root.root_id,
        activation_id=activation_id,
        argv=("/bin/false",),
        cwd=str(lab.repo),
        handle=handle_for(1, log_path=str(lab.paths.log(activation_id))),
        state=LaunchReceiptState.ABORTED,
        abort_exit_code=-signal.SIGKILL,
    )
    write_record(lab.paths.receipt(activation_id), receipt)
    lab.paths.ledger(activation_id).write_bytes(
        ExecLedger.line(
            ExecLedgerEntry(
                launch_id=receipt.launch_id,
                activation_id=activation_id,
                pid=receipt.handle.pid,
                at="2026-09-07T00:00:00Z",
            )
        )
    )

    with pytest.raises(ForkBarrierAbortError, match="never acknowledged"):
        lab.dispatch()

    assert (
        lab.store.reads.load_activation(activation_id).metadata.lifecycle
        is Lifecycle.MINTED
    )
    assert lab.wc_l(activation_id) == 1


def test_exec_without_record_dispatch_reattaches(lab: Lab) -> None:
    """The §5.2 residual window: a child ran, bd never heard — never exec twice."""
    minted = lab.store.mint_activation(lab.root.root_id, entry_mint())
    activation_id = minted.activation.activation_id
    lab.paths.ensure_activation_dir(activation_id)
    launcher = ForkBarrierLauncher(
        lab.config,
        lab.paths,
        lab.clock,
        activation_id=activation_id,
        launch_id="crashed-before-bd",
        plan=SandboxPlan(
            toolchain_cache=(lab.config.wrapper_root / UV_CACHE_DIRECTORY,)
        ),
        sandbox=SandboxMode.OFF,
    )
    channels = channels_for(
        lab.paths.activation_dir(activation_id), lab.paths.log(activation_id)
    )
    command = lab.profile.build_command(
        lab.build_task(minted.activation, channels), SESSION_ID
    )
    handle = launcher(command)
    _wait(handle.pid)

    result = lab.dispatch()

    assert result.outcome is LaunchOutcome.REATTACHED
    assert result.handle == handle
    assert lab.wc_l(activation_id) == 1
    assert result.activation.metadata.lifecycle is Lifecycle.DISPATCHED


def test_off_mode_uses_the_shared_uv_cache_without_a_bwrap_bind(lab: Lab) -> None:
    """`sandbox=off` replaces scratch `UV_CACHE_DIR`, not leaving it cold."""
    minted = lab.store.mint_activation(lab.root.root_id, entry_mint())
    activation_id = minted.activation.activation_id
    lab.paths.ensure_activation_dir(activation_id)
    channels = channels_for(
        lab.paths.activation_dir(activation_id), lab.paths.log(activation_id)
    )
    task = lab.build_task(minted.activation, channels)
    off_config = lab.config.model_copy(update={"sandbox": SandboxMode.OFF})
    off_paths = WrapperPaths(off_config, lab.root.root_id)
    plan, mode = Dispatcher(off_paths, lab.store, lab.clock)._sandbox(
        activation_id, task
    )
    scratch_cache = Path(channels.scratch_dir) / UV_CACHE_DIRECTORY
    command = lab.profile.build_command(task, SESSION_ID)
    command = command.model_copy(
        update={
            "argv": (
                "/bin/sh",
                "-c",
                (
                    'mkdir -p "$WF_ARTIFACT_DIR"; '
                    'printf "%s\\n%s\\n" "$UV_CACHE_DIR" '
                    '"$UV_PYTHON_INSTALL_DIR" '
                    '> "$WF_ARTIFACT_DIR/toolchain-env"'
                ),
            ),
            "env": {
                **command.env,
                ENV_UV_CACHE_DIR: str(scratch_cache),
                ENV_UV_PYTHON_INSTALL_DIR: str(scratch_cache / UV_PYTHON_DIRECTORY),
            },
        }
    )

    handle = ForkBarrierLauncher(
        off_config,
        off_paths,
        lab.clock,
        activation_id=activation_id,
        launch_id="off-shared-cache",
        plan=plan,
        sandbox=mode,
    )(command)
    _wait(handle.pid)

    assert mode is SandboxMode.OFF
    assert wrap(command.argv, plan, mode=mode) == command.argv
    assert (Path(channels.artifact_dir) / "toolchain-env").read_text(
        encoding="utf-8"
    ).splitlines() == [
        str(off_config.wrapper_root / UV_CACHE_DIRECTORY),
        str(off_config.wrapper_root / UV_CACHE_DIRECTORY / UV_PYTHON_DIRECTORY),
    ]


def test_unexplained_ledger_line_refuses_to_exec_again(lab: Lab) -> None:
    """§5.2 fail-closed: a ledger line no receipt explains blocks a second child."""
    minted = lab.store.mint_activation(lab.root.root_id, entry_mint())
    activation_id = minted.activation.activation_id
    lab.paths.ensure_activation_dir(activation_id)
    lab.paths.ledger(activation_id).write_bytes(
        ExecLedger.line(
            ExecLedgerEntry(
                launch_id="orphan",
                activation_id=activation_id,
                pid=1,
                at="2026-08-25T12:00:00Z",
            )
        )
    )

    with pytest.raises(ExecLedgerError, match="no durable"):
        lab.dispatch()

    assert lab.wc_l(activation_id) == 1


def test_a_profile_that_skips_the_launcher_is_caught(lab: Lab) -> None:
    """§6: the fork barrier is not delegable, and bypassing it is detected."""
    lab.profile.bypass_launcher = True

    with pytest.raises(ForkBarrierError, match="did not exec through"):
        lab.dispatch()


def test_second_dispatch_is_a_noop(lab: Lab) -> None:
    """§5.1: a recorded `dispatched` state wins; nothing is exec'd again."""
    first = lab.dispatch()
    assert first.handle is not None
    _wait(first.handle.pid)

    second = lab.dispatch()

    assert second.outcome is LaunchOutcome.ALREADY_DISPATCHED
    assert second.exec_count == 1
    assert lab.wc_l(first.activation.activation_id) == 1


def test_a_corrupt_receipt_with_no_ledger_line_relaunches(lab: Lab) -> None:
    """m17: a receipt torn by a crash CLASSIFIES; it does not wedge the dispatch.

    `read_record` raised `WrapperDirError` straight out of `dispatch`, so every
    later tick died on the same bad file — even here, where the ledger is empty
    and therefore no child can possibly have run. The `recover.py` docstring
    already claimed an unreadable receipt was classified; now it is.
    """
    minted = lab.store.mint_activation(lab.root.root_id, entry_mint())
    activation_id = minted.activation.activation_id
    lab.paths.ensure_activation_dir(activation_id)
    lab.paths.receipt(activation_id).write_bytes(b'{"launch_id": "trunc')

    result = lab.dispatch()

    assert result.outcome is LaunchOutcome.LAUNCHED
    assert lab.wc_l(activation_id) == 1
    assert result.handle is not None
    _wait(result.handle.pid)


def test_a_corrupt_receipt_beside_a_ledger_line_still_refuses(lab: Lab) -> None:
    """m17's other half: classifying is not the same as forgiving.

    A ledger line means a child DID exec. With no receipt that can identify it,
    the only safe answer is still a refusal — never a second child (§5.2).
    """
    minted = lab.store.mint_activation(lab.root.root_id, entry_mint())
    activation_id = minted.activation.activation_id
    lab.paths.ensure_activation_dir(activation_id)
    lab.paths.receipt(activation_id).write_bytes(b'{"launch_id": "trunc')
    lab.paths.ledger(activation_id).write_bytes(
        ExecLedger.line(
            ExecLedgerEntry(
                launch_id="orphan",
                activation_id=activation_id,
                pid=1,
                at="2026-08-25T12:00:00Z",
            )
        )
    )

    with pytest.raises(ExecLedgerError, match="no durable"):
        lab.dispatch()

    assert lab.wc_l(activation_id) == 1


def test_the_ledger_append_flushes_the_file_and_its_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M8: a flushed file whose DIRECTORY ENTRY was not flushed can vanish.

    The receipt path already does temp → fsync → rename → fsync(dir); the
    ledger is created by the child and had only the first flush, so a power
    loss could leave a durable receipt with no ledger — and a redispatch that
    finds a receipt with no matching line relaunches. That is a second child.
    """
    ledger = tmp_path / "act" / "exec.ledger"
    ledger.parent.mkdir(parents=True)
    flushed: list[int] = []
    real_fsync = os.fsync
    monkeypatch.setattr(
        launch_module.os,
        "fsync",
        lambda fd: (flushed.append(fd), real_fsync(fd))[1],
    )

    launch_module.append_ledger_line(str(ledger), b'{"launch_id": "a"}\n')

    assert len(flushed) == FSYNC_FILE_AND_DIR
    assert ledger.read_bytes() == b'{"launch_id": "a"}\n'


def test_abandoning_a_stuck_child_kills_its_whole_group(tmp_path: Path) -> None:
    """m19: the barrier's cleanup SIGKILLed the pid, orphaning grandchildren.

    The child `setsid`s before it signals READY, so a barrier failure after
    that point is failing a process that owns a group. Killing only its leader
    leaves whatever it started running, with no handle and nothing that will
    ever come back for it.
    """
    marker = tmp_path / "grandchild.pid"
    pid = os.fork()
    if pid == 0:  # pragma: no cover - the child never returns to pytest
        os.setsid()
        grandchild = os.fork()
        if grandchild == 0:
            marker.write_text(str(os.getpid()), encoding="utf-8")
            while True:
                time.sleep(0.05)
        while True:
            time.sleep(0.05)
    _await(lambda: marker.exists() and marker.read_text(encoding="utf-8").isdigit())
    grandchild_pid = int(marker.read_text(encoding="utf-8"))
    assert os.getpgid(pid) == pid
    assert _alive(grandchild_pid)

    repo = tmp_path / "repo"
    repo.mkdir()
    config = make_config(repo, tmp_path, fake_proc=False)
    launch_module._abandon(config, FrozenClock(real_sleep_s=0.01), pid)
    with pytest.raises(ChildProcessError):
        os.waitpid(pid, os.WNOHANG)

    _await(lambda: not _alive(grandchild_pid))


def test_abort_child_that_exits_on_term_reaps_once_and_marks_the_receipt_aborted(
    tmp_path: Path,
) -> None:
    """A SIGTERM-exiting child used to leave a live-looking receipt after abort.

    The concrete input is a real launcher child blocked in `sleep 60`; the
    wrong output is a receipt still claiming `started`, or a second successful
    `waitpid` after the abort already consumed the child's status.
    """
    lab = Lab(tmp_path, ChildScript(sleep_s=60))
    lab.config = lab.config.model_copy(
        update={"term_grace_s": 0.2, "kill_grace_s": 0.2, "poll_interval_s": 0.01}
    )
    lab.paths = WrapperPaths(lab.config, lab.root.root_id)
    lab.clock = FrozenClock(real_sleep_s=0.01)
    activation = lab.store.mint_activation(lab.root.root_id, entry_mint()).activation
    activation_id = activation.activation_id
    launcher = ForkBarrierLauncher(
        lab.config,
        lab.paths,
        lab.clock,
        activation_id=activation_id,
        launch_id="abort-term-launch",
        plan=SandboxPlan(
            toolchain_cache=(lab.config.wrapper_root / UV_CACHE_DIRECTORY,)
        ),
        sandbox=SandboxMode.OFF,
    )
    lab.paths.ensure_activation_dir(activation_id)
    command = lab.profile.build_command(
        lab.build_task(
            activation,
            channels_for(
                lab.paths.activation_dir(activation_id), lab.paths.log(activation_id)
            ),
        ),
        SESSION_ID,
    )
    handle = launcher(command)

    proof = launch_module._abort_child(
        lab.config, lab.clock, lab.paths.receipt(activation_id), handle
    )

    receipt = read_record(lab.paths.receipt(activation_id), LaunchReceipt)
    assert proof.confirmed_dead is True
    assert proof.exit_code == -signal.SIGTERM
    assert signal.SIGTERM.name in proof.signals_sent
    assert receipt is not None
    assert receipt.state.value == "aborted"
    with pytest.raises(ChildProcessError):
        os.waitpid(handle.pid, os.WNOHANG)


def test_ack_timeout_aborts_and_marks_the_real_launch_receipt(tmp_path: Path) -> None:
    """A child blocked before ACK used to be reaped without recording its abort.

    The concrete input is a real child blocked opening a FIFO exec ledger; the
    wrong output is a receipt still marked `started`, which makes a later
    observer mistake this launch cleanup for a reattached child.
    """
    lab = Lab(tmp_path, ChildScript(sleep_s=60))
    lab.config = lab.config.model_copy(
        update={
            "barrier_timeout_s": 0.1,
            "term_grace_s": 0.2,
            "kill_grace_s": 0.2,
            "poll_interval_s": 0.01,
        }
    )
    lab.paths = WrapperPaths(lab.config, lab.root.root_id)
    lab.clock = FrozenClock(real_sleep_s=0.01)
    activation = lab.store.mint_activation(lab.root.root_id, entry_mint()).activation
    activation_id = activation.activation_id
    lab.paths.ensure_activation_dir(activation_id)
    os.mkfifo(lab.paths.ledger(activation_id))
    launcher = ForkBarrierLauncher(
        lab.config,
        lab.paths,
        lab.clock,
        activation_id=activation_id,
        launch_id="abort-ack-timeout-launch",
        plan=SandboxPlan(
            toolchain_cache=(lab.config.wrapper_root / UV_CACHE_DIRECTORY,)
        ),
        sandbox=SandboxMode.OFF,
    )
    command = lab.profile.build_command(
        lab.build_task(
            activation,
            channels_for(
                lab.paths.activation_dir(activation_id), lab.paths.log(activation_id)
            ),
        ),
        SESSION_ID,
    )

    with pytest.raises(ForkBarrierAbortError, match="never acknowledged"):
        launcher(command)

    receipt = read_record(lab.paths.receipt(activation_id), LaunchReceipt)
    assert receipt is not None
    assert receipt.state is LaunchReceiptState.ABORTED
    with pytest.raises(ChildProcessError):
        os.waitpid(receipt.handle.pid, os.WNOHANG)


def test_abort_child_ignoring_term_escalates_without_reattached_status(
    tmp_path: Path,
) -> None:
    """A TERM-trapping real child must be KILLed, not reclassified as reattached.

    The concrete input is a real Python runner which has installed a SIGTERM
    trap; the wrong output is an unconsumed status or a receipt left
    `abort-pending` after the bounded TERM → KILL escalation.
    """
    lab = Lab(tmp_path)
    lab.config = lab.config.model_copy(
        update={"term_grace_s": 0.2, "kill_grace_s": 0.2, "poll_interval_s": 0.01}
    )
    lab.paths = WrapperPaths(lab.config, lab.root.root_id)
    lab.clock = FrozenClock(real_sleep_s=0.01)
    activation = lab.store.mint_activation(lab.root.root_id, entry_mint()).activation
    activation_id = activation.activation_id
    launcher = ForkBarrierLauncher(
        lab.config,
        lab.paths,
        lab.clock,
        activation_id=activation_id,
        launch_id="abort-ignore-term-launch",
        plan=SandboxPlan(
            toolchain_cache=(lab.config.wrapper_root / UV_CACHE_DIRECTORY,)
        ),
        sandbox=SandboxMode.OFF,
    )
    lab.paths.ensure_activation_dir(activation_id)
    channels = channels_for(
        lab.paths.activation_dir(activation_id), lab.paths.log(activation_id)
    )
    term_ready = tmp_path / "term-ready"
    command = RunnerCommand(
        argv=(
            sys.executable,
            "-c",
            (
                "import pathlib, signal, time; "
                "signal.signal(signal.SIGTERM, lambda *_: None); "
                f"pathlib.Path({str(term_ready)!r}).write_text('ready'); "
                "exec('while True: time.sleep(0.01)')"
            ),
        ),
        env={"PATH": "/usr/bin:/bin", **channels.env()},
        cwd=str(lab.repo),
        log_path=str(lab.paths.log(activation_id)),
        session_id=SESSION_ID,
    )
    handle = launcher(command)
    _await(term_ready.exists)

    proof = launch_module._abort_child(
        lab.config, lab.clock, lab.paths.receipt(activation_id), handle
    )

    receipt = read_record(lab.paths.receipt(activation_id), LaunchReceipt)
    assert proof.confirmed_dead is True
    assert proof.exit_code == -signal.SIGKILL
    assert proof.signals_sent == (signal.SIGTERM.name, signal.SIGKILL.name)
    assert receipt is not None
    assert receipt.state.value == "aborted"
    with pytest.raises(ChildProcessError):
        os.waitpid(handle.pid, os.WNOHANG)


def _alive(pid: int) -> bool:
    """Whether a process that is NOT our child still exists.

    A grandchild the wrapper never adopted is reparented on its parent's death
    and reaped by init once it dies, so this goes false for real rather than
    sticking on a zombie the way the leader's own pid would.
    """
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _await(predicate: Callable[[], bool], timeout_s: float = 10.0) -> None:
    """Poll `predicate` until it holds, or fail the test."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError("condition never held")


def _placeholder_handle(lab: Lab, activation_id: str) -> object:
    """A handle for a launch that never happened (drill 2's stale receipt)."""
    from tests._supervisor import handle_for

    return handle_for(1, log_path=str(lab.paths.log(activation_id)))
