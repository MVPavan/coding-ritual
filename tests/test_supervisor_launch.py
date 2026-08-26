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
from workflow_interpreter.supervisor import (
    Dispatcher,
    ExecLedger,
    ExecLedgerEntry,
    ExecLedgerError,
    ForkBarrierError,
    ForkBarrierLauncher,
    LaunchOutcome,
    LaunchReceipt,
    SupervisorConfig,
    WrapperPaths,
    channels_for,
)
from workflow_interpreter.supervisor import launch as launch_module
from workflow_interpreter.supervisor.paths import read_record, write_record

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

    launch_module._abandon(pid)
    os.waitpid(pid, 0)

    _await(lambda: not _alive(grandchild_pid))


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
