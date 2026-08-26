"""§8.1 steer: intent first, death proven, one continuation.

Drill 19 (a TERM-resistant child escalated to KILL, with the ledger and handle
still consistent) runs against a real trapping `/bin/sh` and is marked `proc`.
The ordering tests use a fake `/proc`, because "the child refuses to die" is a
state, not a race, and expressing it as data is what makes it assertable.
"""

from __future__ import annotations

import os
import signal
from pathlib import Path

import pytest

from tests._supervisor import (
    IMPLEMENT,
    SESSION_ID,
    ChildScript,
    FakeProfile,
    FrozenClock,
    dead_pid,
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
    write_proc_entry,
)
from workflow_interpreter.bdio import (
    ActivationRecord,
    ExitRecord,
    Lifecycle,
    MintReason,
    MintRequest,
    Outcome,
    ProcessHandle,
)
from workflow_interpreter.supervisor import (
    Dispatcher,
    ExecLedger,
    Steerer,
    SteerIntent,
    SupervisorConfig,
    TerminationFailed,
    WrapperPaths,
)
from workflow_interpreter.supervisor.paths import read_record
from workflow_interpreter.supervisor.steer import instructions_digest

REASON = "the runner is looping on the same test"
INSTRUCTIONS = "stop rewriting the fixture; fix the assertion"


class Lab:
    """One dispatched activation, ready to be steered."""

    def __init__(self, tmp_path: Path, *, fake_proc: bool = True) -> None:
        self.repo = make_repo(tmp_path)
        self.config: SupervisorConfig = make_config(
            self.repo, tmp_path, fake_proc=fake_proc
        )
        _, self.store = make_store(tmp_path, head_of(self.repo))
        self.root = make_root(self.store, self.repo, "steer-instance")
        self.paths: WrapperPaths = make_paths(self.config, self.root.root_id)
        self.clock = FrozenClock(real_sleep_s=0.0 if fake_proc else 0.05)
        self.node = node_of(self.root.definition.document, IMPLEMENT)
        self.steerer = Steerer(self.config, self.paths, self.store, self.clock)

    def dispatched(self, handle: ProcessHandle) -> ActivationRecord:
        """Mint and record a dispatch without exec'ing anything."""
        minted = self.store.mint_activation(self.root.root_id, entry_mint())
        self.paths.ensure_activation_dir(minted.activation.activation_id)
        return self.store.record_dispatch(minted.activation.activation_id, handle)

    def continuation(self, predecessor: str) -> MintRequest:
        """The §8.1 continuation request for a steered activation."""
        return entry_mint(
            mint_reason=MintReason.STEER_CONTINUATION,
            predecessor_activation_id=predecessor,
        )


def _steer(lab: Lab, activation: ActivationRecord) -> object:
    return lab.steerer.steer(
        activation,
        reason=REASON,
        instructions=INSTRUCTIONS,
        continuation=lab.continuation(activation.activation_id),
    )


def test_steer_persists_intent_kills_closes_and_mints_one_continuation(
    tmp_path: Path,
) -> None:
    """§8.1's four steps, in order, with exactly one continuation."""
    lab = Lab(tmp_path)
    activation = lab.dispatched(handle_for(dead_pid()))

    result = _steer(lab, activation)

    intent = read_record(lab.paths.steer_intent(activation.activation_id), SteerIntent)
    assert intent is not None
    assert intent.instructions_digest == instructions_digest(INSTRUCTIONS)
    assert intent.reason == REASON
    assert result.termination.confirmed_dead is True
    assert result.closed.metadata.outcome is Outcome.STEERED
    assert result.closed.metadata.lifecycle is Lifecycle.CLOSED
    assert result.continuation.created is True
    assert (
        result.continuation.activation.metadata.mint_reason
        is MintReason.STEER_CONTINUATION
    )
    assert result.continuation.activation.metadata.session_id == SESSION_ID


def test_steer_records_the_deliberate_death_on_disk(tmp_path: Path) -> None:
    """The exit file distinguishes a steer from a §5.6 case-3 disappearance."""
    lab = Lab(tmp_path)
    activation = lab.dispatched(handle_for(dead_pid()))

    _steer(lab, activation)

    recorded = read_record(lab.paths.exit_file(activation.activation_id), ExitRecord)
    assert recorded is not None
    assert recorded.reason == "steered"


def test_steer_is_idempotent(tmp_path: Path) -> None:
    """A re-run re-finds the continuation instead of minting a second one."""
    lab = Lab(tmp_path)
    activation = lab.dispatched(handle_for(dead_pid()))

    first = _steer(lab, activation)
    second = _steer(lab, lab.store.reads.load_activation(activation.activation_id))

    assert second.continuation.created is False
    assert (
        second.continuation.activation.activation_id
        == first.continuation.activation.activation_id
    )


def test_a_child_that_will_not_die_refuses_the_steer(tmp_path: Path) -> None:
    """§8.1: no `steered` close while the process group may still be writing."""
    lab = Lab(tmp_path)
    pid = dead_pid()
    write_proc_entry(lab.config.proc_root, pid)
    activation = lab.dispatched(handle_for(pid))

    with pytest.raises(TerminationFailed, match="survived TERM and KILL"):
        _steer(lab, activation)

    reloaded = lab.store.reads.load_activation(activation.activation_id)
    assert reloaded.metadata.lifecycle is Lifecycle.DISPATCHED
    assert reloaded.metadata.outcome is None


def test_steering_an_activation_with_no_handle_refuses(tmp_path: Path) -> None:
    """§5.3: without a handle there is no identity to prove death against."""
    lab = Lab(tmp_path)
    minted = lab.store.mint_activation(lab.root.root_id, entry_mint())

    with pytest.raises(TerminationFailed, match="no recorded handle"):
        _steer(lab, minted.activation)


@pytest.mark.proc
def test_term_resistant_child_is_killed_with_proof(tmp_path: Path) -> None:
    """Drill 19: TERM ignored → KILL escalation; ledger and handle stay consistent."""
    lab = Lab(tmp_path, fake_proc=False)
    profile = FakeProfile(ChildScript(ignore_term=True))
    dispatcher = Dispatcher(lab.paths, lab.store, lab.clock)
    dispatched = dispatcher.dispatch(
        entry_mint(), profile, task_builder(lab.repo, lab.node)
    )
    activation_id = dispatched.activation.activation_id
    handle = dispatched.handle
    assert handle is not None

    try:
        result = _steer(lab, dispatched.activation)

        assert result.termination.signals_sent == ("SIGTERM", "SIGKILL")
        assert result.termination.confirmed_dead is True
        assert result.termination.pid == handle.pid
        assert ExecLedger(lab.paths.ledger(activation_id)).count() == 1
    finally:
        _kill_group(handle)


def _kill_group(handle: ProcessHandle) -> None:
    """End this child's whole group and reap its leader, whatever the test did.

    Sol#14: the reap used to be the test's last STATEMENT, so it ran only when
    every assertion passed — and this child TRAPS TERM. A failure before the
    steer's own escalation therefore left a process looping over `sleep` on the
    developer's machine for as long as it stayed up, and a failing test that
    leaks is a failing test nobody can re-run cleanly. SIGKILL cannot be
    trapped; `ESRCH` means the group is already gone, which is the normal path.
    """
    try:
        os.killpg(handle.pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        os.waitpid(handle.pid, 0)
    except ChildProcessError:
        return
