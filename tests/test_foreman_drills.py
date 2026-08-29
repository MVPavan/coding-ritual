"""D1 crash, lock, event, and halt drills at the real foreman seams."""

from __future__ import annotations

import json
import multiprocessing
import os
import signal
import time
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from tests._bdio import entry_request, race_residue
from tests._foreman import (
    ForemanLab,
    InlineSpawner,
    LockedPersistentBd,
    ProcSpawner,
)
from tests._helpers import VALID_FIXTURE, write
from tests._supervisor import ChildScript
from tests.conftest import Signer
from workflow_interpreter.bdio import (
    BoundMutation,
    Evidence,
    Lifecycle,
    Outcome,
    SigningConfig,
)
from workflow_interpreter.bdio.carriers import ExitRecord
from workflow_interpreter.bdio.wire import EventPayload
from workflow_interpreter.foreman.frontier import build_frontier
from workflow_interpreter.foreman.gates import halt_gate
from workflow_interpreter.foreman.supervise import WrapperExit, run_wrapper
from workflow_interpreter.foreman.tick import Foreman
from workflow_interpreter.supervisor.band import BandLock
from workflow_interpreter.supervisor.paths import ExecLedger, read_record


def _persistent_lab(
    tmp_path: Path,
    *,
    signing: SigningConfig | None = None,
    signer: Signer | None = None,
) -> ForemanLab:
    """Build a lab whose restart reads every workflow fact from disk."""
    state = tmp_path / "persistent-bd.json"

    def persistent(workspace: str) -> LockedPersistentBd:
        return LockedPersistentBd(workspace, state)

    return ForemanLab(tmp_path, bd_factory=persistent, signing=signing, signer=signer)


def _install_spawner(lab: ForemanLab, spawner: InlineSpawner | ProcSpawner) -> None:
    """Replace only the outer process boundary for one injected crash."""
    lab.spawner = cast(InlineSpawner, spawner)
    lab.composition = replace(lab.composition, spawner=spawner)
    spawner.bind(lab.composition)
    lab.foreman = Foreman(lab.composition)


def _tick_in_process(lab: ForemanLab) -> None:
    """Run one tick in the parent process LOCK-C kills after it spawns."""
    lab.tick()


def _close_implement(lab: ForemanLab) -> str:
    """Reach the completed entry head through the public tick path."""
    activation_id = lab.tick().dispatched
    assert activation_id is not None
    assert lab.tick().settled == activation_id
    return activation_id


def _drive_to_ship(lab: ForemanLab) -> str:
    """Reach the fixture's human ship gate through real wrapper settlement."""
    _close_implement(lab)
    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
    )
    review = lab.tick().dispatched
    assert review is not None
    assert lab.tick().settled == review
    gate_id = lab.tick().opened_gate
    assert gate_id is not None
    return gate_id


def _halt_from_fail_code(lab: ForemanLab) -> tuple[str, str]:
    """Create the fail-code dead end used by the halt re-budget drill."""
    assert lab.root is not None
    activation_id = (
        lab.wiring()
        .store.mint_activation(lab.root.root_id, entry_request())
        .activation.activation_id
    )
    lab.store.close_activation(
        activation_id,
        Outcome.FAIL_CODE,
        evidence=Evidence(claimed_outcome=Outcome.DONE),
    )
    gate_id = lab.tick().opened_gate
    assert gate_id is not None
    return activation_id, gate_id


def test_lock_a1_wrapper_refuses_before_receipt_or_ledger(tmp_path: Path) -> None:
    """LOCK-A1 catches a wrapper that reads or starts despite its activation lock."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    lock = lab.hold_wrapper_lock(activation.activation_id)
    before_updates = lab.count("update")
    try:
        result = run_wrapper(lab.composition, root.root_id, activation.activation_id)
    finally:
        lock.release()

    assert result is WrapperExit.LOCKED
    assert (
        lab.store.reads.load_activation(activation.activation_id).metadata.lifecycle
        is Lifecycle.MINTED
    )
    assert lab.count("update") == before_updates
    assert not lab.wiring().paths.ledger(activation.activation_id).exists()
    assert not (
        lab.wiring().paths.activation_dir(activation.activation_id) / "dispatch.json"
    ).exists()


def test_lock_a2_tick_reports_blocked_then_dispatches_after_release(
    tmp_path: Path,
) -> None:
    """LOCK-A2 distinguishes a held wrapper lock from a no-work tick."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    lock = lab.hold_wrapper_lock(activation.activation_id)
    before_updates = lab.count("update")
    try:
        blocked = lab.tick()
    finally:
        lock.release()

    assert blocked.blocked is True
    assert blocked.dispatched is None
    assert lab.count("update") == before_updates
    assert lab.tick().dispatched == activation.activation_id
    assert (
        lab.store.reads.load_activation(activation.activation_id).metadata.lifecycle
        is Lifecycle.EXIT_RECORDED
    )
    assert ExecLedger(lab.wiring().paths.ledger(activation.activation_id)).count() == 1


def test_lock_b_rebuild_settles_an_exit_recorded_before_crash(tmp_path: Path) -> None:
    """LOCK-B catches a restart that launches a second child after an exit record."""
    lab = _persistent_lab(tmp_path)
    lab.instantiate()
    crashing = InlineSpawner(crash_after_start=True)
    _install_spawner(lab, crashing)

    with pytest.raises(Exception, match="inline wrapper crashed after start"):
        lab.tick()

    activation_id = crashing.launches[0].activation_id
    assert not (
        lab.wiring().paths.activation_dir(activation_id) / "wrapper.json"
    ).exists()
    assert (
        lab.store.reads.load_activation(activation_id).metadata.lifecycle
        is Lifecycle.EXIT_RECORDED
    )
    lab.rebuild()
    report = lab.tick()

    assert report.settled == activation_id
    assert lab.spawner.launches == []
    assert ExecLedger(lab.wiring().paths.ledger(activation_id)).count() == 1


def test_lock_stale_wrapper_returns_stale_without_durable_side_effects(
    tmp_path: Path,
) -> None:
    """LOCK-STALE catches a late wrapper that records a receipt or ledger entry."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    lab.fake_bd.rows[activation.activation_id]["metadata"]["lifecycle"] = "dispatched"
    before_updates = lab.count("update")

    result = run_wrapper(lab.composition, root.root_id, activation.activation_id)

    directory = lab.wiring().paths.activation_dir(activation.activation_id)
    assert result is WrapperExit.STALE
    assert lab.count("update") == before_updates
    assert not lab.wiring().paths.ledger(activation.activation_id).exists()
    assert sorted(path.name for path in directory.iterdir()) == ["wrapper.lock"]


@pytest.mark.proc
def test_lock_c_killed_tick_leaves_one_wrapper_writer(tmp_path: Path) -> None:
    """LOCK-C catches a replacement tick that runs beside a surviving wrapper."""
    lab = _persistent_lab(tmp_path)
    lab.instantiate()
    spawner = ProcSpawner()
    _install_spawner(lab, spawner)
    process = multiprocessing.get_context("fork").Process(
        target=_tick_in_process, args=(lab,)
    )
    process.start()
    spawned = lab.wiring().paths.instance_dir
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline and not tuple(spawned.glob("*/spawned")):
        time.sleep(0.01)
    markers = tuple(spawned.glob("*/spawned"))
    try:
        assert markers
        assert process.pid is not None
        os.kill(process.pid, signal.SIGKILL)
        process.join(timeout=5)
        assert process.exitcode is not None

        activation_id = markers[0].parent.name
        lab.rebuild()
        replacement = ProcSpawner()
        _install_spawner(lab, replacement)
        lab.tick()
        replacement.await_barrier(lab.wiring(), activation_id)
    finally:
        if process.is_alive():
            process.kill()
            process.join(timeout=5)

    activation = lab.store.reads.load_activation(activation_id)
    state = json.loads((tmp_path / "persistent-bd.json").read_text(encoding="utf-8"))
    calls = state["calls"]
    spawned_pids = {
        int(raw)
        for raw in (spawned / activation_id / "spawned.pids")
        .read_text(encoding="ascii")
        .splitlines()
    }
    exit_writes = [
        call
        for call in calls
        if call["argv"][5] == "update"
        and any("exit_record" in argument for argument in call["argv"])
    ]
    spawned_writers = {
        call["pid"]
        for call in calls
        if call["argv"][5] in {"create", "update", "close"}
    } & spawned_pids

    assert ExecLedger(lab.wiring().paths.ledger(activation_id)).count() == 1
    assert len(lab.beads("activation")) == 1
    assert activation.metadata.lifecycle in {
        Lifecycle.EXIT_RECORDED,
        Lifecycle.EVIDENCE_RECORDED,
        Lifecycle.CLOSED,
    }
    assert len(exit_writes) == 1
    assert spawned_writers == {exit_writes[0]["pid"]}


def test_event_a_rebuilds_after_crashing_before_successor_mint(tmp_path: Path) -> None:
    """EVENT-A catches a crash path that never reaches the successor mint."""
    lab = _persistent_lab(tmp_path)
    lab.instantiate()
    _close_implement(lab)
    lab.crash_on_tick_create(1)

    with pytest.raises(Exception, match="bd create died"):
        lab.tick()
    lab.rebuild()
    report = lab.tick()

    assert report.dispatched is not None
    assert len(lab.beads("activation")) == 2
    assert len(lab.beads("event")) == 1


def test_event_b_backfills_once_after_successor_mint_crash(tmp_path: Path) -> None:
    """EVENT-B catches a crash gap between the durable successor and its event."""
    lab = _persistent_lab(tmp_path)
    root = lab.instantiate()
    implement_id = _close_implement(lab)
    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
    )
    lab.crash_on_tick_create(2)

    with pytest.raises(Exception, match="bd create died"):
        lab.tick()
    lab.rebuild()
    frontier = build_frontier(root, lab.store.reads.instance_beads(root.root_id))
    assert frontier.head is None
    assert len(lab.beads("activation")) == 2
    assert lab.beads("event") == []

    assert lab.tick().settled is not None
    report = lab.tick()

    events = [
        EventPayload.model_validate_json(row["payload"])
        for row in lab.beads("event")
        if isinstance(row["payload"], str)
    ]
    assert report.events_backfilled == 2
    assert len(lab.beads("activation")) == 2
    assert sum(event.activation_id == implement_id for event in events) == 1


def test_event_c_rebuilds_terminal_event_from_closed_abandon_gate(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """EVENT-C catches terminal completion that trusts an absent event projection."""
    lab = _persistent_lab(tmp_path, signing=signing_config, signer=sign_payload)
    lab.instantiate()
    gate_id = _drive_to_ship(lab)
    lab.approve(gate_id, Outcome.ABANDON)
    assert lab.tick().closed_gates == (gate_id,)
    lab.crash_on_tick_create(1)

    with pytest.raises(Exception, match="bd create died"):
        lab.tick()
    lab.rebuild()
    report = lab.tick()
    events = len(lab.beads("event"))
    third = lab.tick()

    assert report.terminal is True
    assert events == 3
    assert third.terminal is True
    assert len(lab.beads("event")) == events


def test_drill_6_repairs_a_closed_abandon_carrier_after_its_bead_close_crashes(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """Drill 6 catches terminal routing that loses a carrier-before-close decision."""
    lab = _persistent_lab(tmp_path, signing=signing_config, signer=sign_payload)
    lab.instantiate()
    gate_id = _drive_to_ship(lab)
    lab.approve(gate_id, Outcome.ABANDON)
    lab.fake_bd.crash_on("close")

    with pytest.raises(Exception, match="bd close died"):
        lab.tick()

    carrier_closed = lab.store.reads.load_gate(gate_id)
    assert carrier_closed.metadata.state.value == "closed"
    assert carrier_closed.bead.status == "open"

    lab.rebuild()
    repaired = lab.tick()
    terminal = lab.tick()

    assert lab.store.reads.load_gate(gate_id).bead.status == "closed"
    assert repaired.closed_gates == (gate_id,)
    assert terminal.terminal is True
    assert len(lab.beads("event")) == 3


def test_halt_intake_closes_each_signed_outcome_before_dispatch(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """HALT-INTAKE catches a tick that confuses absent, refused, and closed gates."""
    for outcome in (Outcome.APPROVE, Outcome.REBUDGET, Outcome.ABANDON):
        lab = ForemanLab(
            tmp_path / outcome.value, signing=signing_config, signer=sign_payload
        )
        root = lab.instantiate()
        gate = lab.store.open_gate(root.root_id, halt_gate("ceiling:20"))
        mutation = (
            BoundMutation(key="region.build-review.max_entries", value=4)
            if outcome is Outcome.REBUDGET
            else None
        )
        lab.approve(gate.gate_id, outcome, mutation=mutation)
        report = lab.tick()
        closed = lab.store.reads.load_gate(gate.gate_id)

        assert report.closed_gates == (gate.gate_id,)
        assert report.halted is False
        assert closed.metadata.outcome is outcome
        assert report.dispatched is None
        if outcome is Outcome.REBUDGET:
            assert closed.metadata.bound_key == "region.build-review.max_entries"
        if outcome is Outcome.ABANDON:
            terminal = lab.tick()
            assert terminal.terminal is True
            assert len(lab.beads("event")) == 1


def test_halt_rebudget_restarts_the_fail_code_node_without_a_new_round(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """HALT-REBUDGET catches a re-mint that loses the halt provenance or round."""
    lab = ForemanLab(tmp_path, signing=signing_config, signer=sign_payload)
    lab.instantiate()
    failed_id, gate_id = _halt_from_fail_code(lab)
    failed = lab.store.reads.load_activation(failed_id)
    mutation = BoundMutation(key="region.build-review.max_entries", value=4)
    lab.approve(gate_id, Outcome.REBUDGET, mutation=mutation)

    closed = lab.tick()
    remint = lab.tick().dispatched
    assert remint is not None
    reminted = lab.store.reads.load_activation(remint)
    gate = lab.store.reads.load_gate(gate_id)

    assert closed.closed_gates == (gate_id,)
    assert closed.halted is False
    assert reminted.metadata.node == failed.metadata.node
    assert reminted.metadata.predecessor_gate_id == gate_id
    assert reminted.metadata.outcome_taken is Outcome.REBUDGET
    assert reminted.metadata.round_no == failed.metadata.round_no
    assert gate.metadata.bound_key == "region.build-review.max_entries"
    assert gate.metadata.bound_value == 4
    assert len(lab.beads("event")) == 1


def test_halt_rebudget_without_a_mutation_is_refused_and_reported(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """HALT-REBUDGET rejects a carrier that violates the mutation biconditional."""
    lab = ForemanLab(tmp_path, signing=signing_config, signer=sign_payload)
    lab.instantiate()
    _, gate_id = _halt_from_fail_code(lab)
    lab.approve(gate_id, Outcome.REBUDGET)

    report = lab.tick()
    gate = lab.store.reads.load_gate(gate_id)
    refusal = json.loads(
        (
            lab.wiring().paths.instance_dir
            / "gates"
            / gate.metadata.gate_key
            / "refusal.json"
        ).read_text(encoding="utf-8")
    )

    assert report.closed_gates == ()
    assert report.halted is True
    assert gate.metadata.state.value == "open"
    assert report.refusals == (lab.refusal(gate_id),)
    assert refusal["error"] == "PayloadMismatchError"
    assert "bound_mutation absent" in report.refusals[0]


def test_drill_1_spawn_failure_leaves_one_minted_activation_for_the_next_tick(
    tmp_path: Path,
) -> None:
    """Drill 1 catches a spawned-child failure being mistaken for spawn failure."""
    lab = ForemanLab(tmp_path)
    lab.instantiate()
    lab.spawner.fail_next()

    with pytest.raises(Exception, match="inline spawn failed"):
        lab.tick()

    minted = lab.beads("activation")
    assert len(minted) == 1
    activation_id = str(minted[0]["id"])
    assert (
        lab.store.reads.load_activation(activation_id).metadata.lifecycle
        is Lifecycle.MINTED
    )
    assert lab.tick().dispatched == activation_id
    assert ExecLedger(lab.wiring().paths.ledger(activation_id)).count() == 1


def test_drill_3_replays_the_exit_file_after_the_bd_exit_mirror_crashes(
    tmp_path: Path,
) -> None:
    """Drill 3 catches a dispatched tick that never enters exit-file replay."""
    lab = _persistent_lab(tmp_path)
    lab.instantiate()
    lab.fake_bd.crash_on("update", 3)

    with pytest.raises(Exception, match="bd update died"):
        lab.tick()

    activation_id = str(lab.beads("activation")[0]["id"])
    exit_record = read_record(lab.wiring().paths.exit_file(activation_id), ExitRecord)
    assert exit_record is not None
    assert (
        lab.store.reads.load_activation(activation_id).metadata.lifecycle
        is Lifecycle.DISPATCHED
    )

    lab.rebuild()
    report = lab.tick()
    recovered = lab.store.reads.load_activation(activation_id)

    assert report.settled == activation_id
    assert recovered.metadata.lifecycle is Lifecycle.CLOSED
    assert recovered.metadata.outcome is Outcome.DONE
    assert recovered.metadata.exit_record is not None
    assert recovered.metadata.exit_record.ended_at == exit_record.ended_at


def test_drill_4_rework_resets_to_the_rejected_attempts_pre_attempt_commit(
    tmp_path: Path,
) -> None:
    """Drill 4 catches a rework precondition that inherits rejected work."""
    lab = ForemanLab(tmp_path)
    lab.instantiate()
    first = lab.tick().dispatched
    assert first is not None
    assert lab.tick().settled == first
    first_attempt = lab.store.reads.load_activation(first)
    assert first_attempt.metadata.pre_attempt_commit is not None
    lab.profiles.next_script(
        ChildScript(
            marker='{"outcome":"reject"}\n',
            effects='{"paths":[]}',
            artifact_path="findings.md",
            artifact_body="change this\n",
        )
    )
    review = lab.tick().dispatched
    assert review is not None
    assert lab.tick().settled == review
    assert lab.store.reads.load_activation(review).metadata.outcome is Outcome.REJECT

    lab.spawner.fail_next()
    with pytest.raises(Exception, match="inline spawn failed"):
        lab.tick()

    assert lab.root is not None
    rework = next(
        activation
        for activation in lab.store.reads.list_activations(lab.root.root_id)
        if activation.metadata.node == "implement" and activation.activation_id != first
    )
    assert rework.metadata.lifecycle is Lifecycle.MINTED
    assert lab.tick().dispatched == rework.activation_id
    dispatched = lab.store.reads.load_activation(rework.activation_id)

    assert (
        dispatched.metadata.intended_base_commit
        == first_attempt.metadata.pre_attempt_commit
    )
    assert (
        dispatched.metadata.pre_attempt_commit
        == first_attempt.metadata.pre_attempt_commit
    )
    assert (
        dispatched.metadata.reset_verified_commit
        == first_attempt.metadata.pre_attempt_commit
    )
    assert (
        lab.git.ref_target(
            f"refs/wf/{lab.root.root_id}/prereset/{rework.activation_id}",
            cwd=lab.repo,
        )
        is not None
    )


def test_drill_9_keeps_routing_from_the_pinned_graph_after_authoring_changes(
    tmp_path: Path,
) -> None:
    """Drill 9 catches a tick that reparses the mutable authoring TOML."""
    toml = write(tmp_path, VALID_FIXTURE.read_text(encoding="utf-8"))
    lab = ForemanLab(tmp_path, toml=toml)
    lab.instantiate()
    toml.write_text("[graph]\nid = 'changed'\n", encoding="utf-8")

    report = lab.tick()

    assert report.dispatched is not None
    activation = lab.store.reads.load_activation(report.dispatched)
    assert activation.metadata.node == "implement"


def test_drill_10_supersedes_race_residue_before_dispatching_one_wrapper(
    tmp_path: Path,
) -> None:
    """Drill 10 catches a race loser that survives to launch a second child."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    winner = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    loser = race_residue(lab.store._client, winner)

    report = lab.tick()

    assert report.dispatched == winner.activation_id
    assert lab.store.reads.load_activation(loser.activation_id).metadata.is_superseded
    assert len(lab.spawner.launches) == 1
    assert ExecLedger(lab.wiring().paths.ledger(winner.activation_id)).count() == 1

    band = BandLock(lab.wiring().paths.band_lock)
    band.acquire()
    try:
        blocked = lab.tick()
    finally:
        band.release()

    assert blocked.stalled is not None


def test_drill_12_halts_on_a_missing_intended_base_commit(tmp_path: Path) -> None:
    """Drill 12 catches reconciliation that dispatches a nonexistent commit."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    lab.fake_bd.rows[activation.activation_id]["metadata"]["intended_base_commit"] = (
        "f" * 40
    )

    report = lab.tick()

    assert report.halted is True
    assert report.opened_gate is not None
    gate = lab.store.reads.load_gate(report.opened_gate)
    assert (
        gate.metadata.halt_reason == "missing_commit intended_base_commit " + "f" * 40
    )
