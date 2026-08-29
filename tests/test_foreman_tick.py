"""C2b ordering and catch-surface contracts for one foreman tick."""

from collections.abc import Iterable
from pathlib import Path
from time import monotonic
from typing import NoReturn

import pytest

from tests._bdio import entry_request, handle, race_residue
from tests._fake_bd import InjectedCrash
from tests._foreman import ForemanLab
from tests._helpers import VALID_FIXTURE, mutate, write
from tests._supervisor import ChildScript
from tests.conftest import Signer
from workflow_interpreter.bdio import ArtifactIdentity, Evidence, ExitRecord
from workflow_interpreter.bdio.bounds import BoundKind, BoundRefusal
from workflow_interpreter.bdio.client import STATUS_CLOSED
from workflow_interpreter.bdio.config import SigningConfig
from workflow_interpreter.bdio.errors import (
    BoundExceededError,
    CanaryFailedError,
    CarrierIntegrityError,
    GateVerificationError,
    LifecycleConflictError,
    PinnedGraphMismatchError,
)
from workflow_interpreter.bdio.records import RootRecord
from workflow_interpreter.bdio.wire import BeadRecord, EventPayload
from workflow_interpreter.foreman import tick as tick_module
from workflow_interpreter.foreman.audit import AuditResult, audit
from workflow_interpreter.foreman.cases import CaseResult
from workflow_interpreter.foreman.compose import InstanceBranchMissing
from workflow_interpreter.foreman.frontier import Frontier, build_frontier
from workflow_interpreter.foreman.gates import halt_gate
from workflow_interpreter.schema.models import Outcome
from workflow_interpreter.supervisor.errors import (
    ContinuationRefused,
    GitCommandError,
    LockUnavailable,
)
from workflow_interpreter.supervisor.gitcmd import GitSubcommand


def test_tick_reconciles_before_it_mints(tmp_path: Path) -> None:
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    branch = "refs/heads/wf/" + root.root_id
    lab.git.run(GitSubcommand.UPDATE_REF, "-d", branch, cwd=lab.repo)
    report = lab.tick()
    assert report.stalled == "instance branch missing"
    assert lab.beads("activation") == []


def test_tick_audits_before_building_the_frontier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The audit must inspect the durable trace before routing interprets it."""
    lab = ForemanLab(tmp_path)
    lab.instantiate()
    order: list[str] = []

    def observed_audit(root: RootRecord, beads: Iterable[BeadRecord]) -> AuditResult:
        order.append("audit")
        return audit(root, beads)

    def observed_frontier(root: RootRecord, beads: Iterable[BeadRecord]) -> Frontier:
        order.append("frontier")
        return build_frontier(root, beads)

    monkeypatch.setattr("workflow_interpreter.foreman.tick.audit", observed_audit)
    monkeypatch.setattr(
        "workflow_interpreter.foreman.tick.build_frontier", observed_frontier
    )

    lab.tick()

    assert order[:2] == ["audit", "frontier"]


def test_tick_checks_an_open_halt_before_advancing_a_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An open halt serializes the instance before a wrapper can be advanced."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    lab.tick()
    lab.store.open_gate(root.root_id, halt_gate("ceiling:20"))
    advanced: list[str] = []

    def observed_advance(*_args: object) -> CaseResult:
        advanced.append("lifecycle")
        return CaseResult()

    monkeypatch.setattr(tick_module, "advance_lifecycle", observed_advance)

    assert lab.tick().halted is True
    assert advanced == []


def test_tick_maps_band_contention_to_the_listed_stalled_result(tmp_path: Path) -> None:
    """The first ordered operation has no acquired lock to release on refusal."""
    lab = ForemanLab(tmp_path)
    lab.instantiate()
    held = lab.wiring().band
    held.acquire()
    try:
        assert lab.tick().stalled is not None
    finally:
        held.release()


def test_tick_reports_a_live_wrapper_as_blocked(tmp_path: Path) -> None:
    """A held activation lock is distinct from a tick with no work to do."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    lock = lab.hold_wrapper_lock(activation.activation_id)
    try:
        assert lab.tick().blocked is True
    finally:
        lock.release()


def test_tick_mints_the_successor_before_backfilling_its_event(tmp_path: Path) -> None:
    """A routed head creates its successor bead before its derived trace event."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    entry = lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    activation = lab.store.record_dispatch(entry.activation_id, handle())
    activation = lab.store.record_exit(
        activation.activation_id,
        ExitRecord(exit_code=0, ended_at="2026-08-29T00:00:00Z", reason="ok"),
    )
    commit = lab.git.head_commit(cwd=lab.repo)
    lab.git.update_ref(
        f"refs/wf/{root.root_id}/artifact/{activation.activation_id}",
        commit,
        cwd=lab.repo,
    )
    lab.store.close_activation(
        activation.activation_id,
        Outcome.DONE,
        evidence=Evidence(
            artifact=ArtifactIdentity(
                commit_oid=commit, tree_oid=lab.git.tree_oid(commit, cwd=lab.repo)
            )
        ),
    )
    known = set(lab.fake_bd.rows)

    report = lab.tick()

    created = [row for bead_id, row in lab.fake_bd.rows.items() if bead_id not in known]
    assert report.dispatched is not None
    assert [row["metadata"]["wf_kind"] for row in created[-2:]] == [
        "activation",
        "event",
    ]


def test_tick_drives_the_fixture_from_entry_to_shipped(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """The fixture's real happy path reaches a terminal event, not a stall."""
    lab = ForemanLab(
        tmp_path,
        signing=signing_config,
        signer=sign_payload,
    )
    lab.instantiate()
    implement = lab.tick().dispatched
    assert implement is not None
    assert lab.tick().settled == implement

    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
    )
    review = lab.tick().dispatched
    assert review is not None
    assert lab.tick().settled == review

    ship = lab.tick().opened_gate
    assert ship is not None
    lab.approve(ship, Outcome.APPROVE)
    assert lab.tick().closed_gates == (ship,)
    report = lab.tick()

    assert report.terminal is True
    assert report.events_backfilled == 1
    events: list[EventPayload] = []
    for row in lab.beads("event"):
        payload = row["payload"]
        assert isinstance(payload, str)
        events.append(EventPayload.model_validate_json(payload))
    assert [(event.from_node, event.to_node) for event in events] == [
        ("implement", "review"),
        ("review", "ship"),
        ("ship", "shipped"),
    ]


def test_tick_distinguishes_absent_refused_and_verified_gate_intake(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """A refused signed approval remains open and is visible to the caller."""
    lab = ForemanLab(tmp_path, signing=signing_config, signer=sign_payload)
    root = lab.instantiate()
    gate = lab.store.open_gate(root.root_id, halt_gate("ceiling:20"))

    absent = lab.tick()
    lab.refuse(gate.gate_id)
    refused = lab.tick()
    refusal = lab.refusal(gate.gate_id)
    lab.approve(gate.gate_id, Outcome.APPROVE)
    verified = lab.tick()

    assert absent.halted is True
    assert absent.closed_gates == ()
    assert absent.refusals == ()
    assert refused.halted is True
    assert refused.closed_gates == ()
    assert refused.refusals == (refusal,)
    assert verified.halted is False
    assert verified.closed_gates == (gate.gate_id,)
    assert verified.refusals == ()


def test_tick_backfills_an_activation_terminal_edge_without_a_gate(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """A task outcome can reach a terminal directly and still emits its event."""
    toml = write(
        tmp_path,
        mutate(
            VALID_FIXTURE.read_text(encoding="utf-8"),
            (
                (
                    """[[node]]
name      = "ship"
kind      = "gate"
gate_type = "human"
binds     = "immutable"
outcomes  = ["approve", "abandon"]

""",
                    "",
                ),
                (
                    '''[[edge]]
from = "review"
on   = "accept"
to   = "ship"''',
                    '''[[edge]]
from = "review"
on   = "accept"
to   = "shipped"''',
                ),
                (
                    """[[edge]]
from = "ship"
on   = "approve"
to   = "shipped"

[[edge]]
from = "ship"
on   = "abandon"
to   = "abandoned"

""",
                    "",
                ),
            ),
        ),
    )
    lab = ForemanLab(tmp_path, toml=toml, signing=signing_config, signer=sign_payload)
    lab.instantiate()
    implement = lab.tick().dispatched
    assert implement is not None
    assert lab.tick().settled == implement
    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
    )
    review = lab.tick().dispatched
    assert review is not None
    assert lab.tick().settled == review

    report = lab.tick()

    assert report.terminal is True
    assert report.events_backfilled == 1
    events = [
        EventPayload.model_validate_json(row["payload"])
        for row in lab.beads("event")
        if isinstance(row["payload"], str)
    ]
    assert ("review", "shipped") in [
        (event.from_node, event.to_node) for event in events
    ]


def test_tick_retries_a_close_that_crashed_after_recording_its_outcome(
    tmp_path: Path,
) -> None:
    """A completed carrier on an open bd row is repaired before routing it."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    activation = lab.wiring().store.record_dispatch(activation.activation_id, handle())
    lab.fake_bd.crash_on("close")
    with pytest.raises(InjectedCrash, match="bd close died"):
        lab.wiring().store.close_activation(activation.activation_id, Outcome.DONE)
    wedged = lab.wiring().store.reads.load_activation(activation.activation_id)
    assert wedged.bead.status == "open"
    before = lab.count("close")

    report = lab.tick()

    repaired = lab.wiring().store.reads.load_activation(activation.activation_id)
    assert report.settled == activation.activation_id
    assert repaired.bead.status == STATUS_CLOSED
    assert lab.count("close") == before + 1


def test_tick_ignores_an_open_superseded_race_residue(tmp_path: Path) -> None:
    """Only a completed non-superseded close is eligible for repair-forward."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    loser = race_residue(lab.store._client, activation)
    lab.fake_bd.crash_on("close")
    with pytest.raises(InjectedCrash, match="bd close died"):
        lab.wiring().store.supersede_activation(
            loser.activation_id, activation.activation_id
        )
    before = lab.count("close")

    lab.tick()

    assert lab.count("close") == before


def test_tick_audits_before_repairing_a_completed_open_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An invalid trace halts before the repair loop performs a durable write."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    activation = lab.wiring().store.record_dispatch(activation.activation_id, handle())
    lab.fake_bd.crash_on("close")
    with pytest.raises(InjectedCrash, match="bd close died"):
        lab.wiring().store.close_activation(activation.activation_id, Outcome.DONE)
    before = lab.count("close")
    monkeypatch.setattr(
        tick_module,
        "audit",
        lambda *_args: AuditResult(violation="corrupt trace"),
    )

    report = lab.tick()

    assert report.halted is True
    assert report.opened_gate is not None
    assert lab.count("close") == before


def test_tick_reconciles_before_repairing_a_completed_open_row(tmp_path: Path) -> None:
    """A missing branch halts before a repair could write against it."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    activation = lab.wiring().store.record_dispatch(activation.activation_id, handle())
    lab.fake_bd.crash_on("close")
    with pytest.raises(InjectedCrash, match="bd close died"):
        lab.wiring().store.close_activation(activation.activation_id, Outcome.DONE)
    lab.git.run(
        GitSubcommand.UPDATE_REF,
        "-d",
        f"refs/heads/wf/{root.root_id}",
        cwd=lab.repo,
    )
    before = lab.count("close")

    report = lab.tick()

    assert report.stalled == "instance branch missing"
    assert lab.count("close") == before


def test_lab_consumes_a_queued_script_only_for_the_child_it_launches(
    tmp_path: Path,
) -> None:
    """Settlement profile lookup cannot silently spend a later child script."""
    lab = ForemanLab(tmp_path)
    lab.instantiate()
    implement = lab.tick().dispatched
    assert implement is not None
    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
    )

    assert lab.tick().settled == implement
    assert lab.profiles.profile.script.marker == '{"outcome":"done"}\n'
    review = lab.tick().dispatched

    assert review is not None
    assert lab.tick().settled == review
    assert lab.store.reads.load_activation(review).metadata.outcome is Outcome.ACCEPT


def test_lab_spawner_fail_next_is_not_a_fail_plan_child(tmp_path: Path) -> None:
    """The drill-one injection fails spawning before any wrapper report exists."""
    lab = ForemanLab(tmp_path)
    lab.instantiate()
    lab.spawner.fail_next()

    with pytest.raises(InjectedCrash, match="inline spawn failed"):
        lab.tick()

    activation = lab.beads("activation")[0]
    metadata = activation["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["lifecycle"] == "minted"


def test_inline_in_repo_dispatch_uses_the_tick_wiring(tmp_path: Path) -> None:
    """The lab does not contend with the band its enclosing tick already holds."""
    toml = write(
        tmp_path,
        mutate(
            VALID_FIXTURE.read_text(encoding="utf-8"),
            (
                (
                    'runner        = "profile:implementer"\nmodel         = "default"\nisolation     = "worktree"',
                    'runner        = "profile:implementer"\nmodel         = "default"\nisolation     = "in-repo"',
                ),
            ),
        ),
    )
    lab = ForemanLab(tmp_path, toml=toml, band_wait_s=0.01)
    lab.instantiate()

    started = monotonic()
    activation_id = lab.tick().dispatched
    elapsed = monotonic() - started

    assert activation_id is not None
    activation = lab.store.reads.load_activation(activation_id)
    assert elapsed < 1.0
    assert activation.metadata.lifecycle.value == "exit-recorded"
    assert lab.tick().settled == activation_id
    assert (
        lab.store.reads.load_activation(activation_id).metadata.outcome is Outcome.DONE
    )


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            BoundExceededError(
                BoundRefusal(
                    bound=BoundKind.INSTANCE_CEILING,
                    observed=2,
                    limit=1,
                    operator="count",
                    detail="bound",
                )
            ),
            "bound",
        ),
        (ContinuationRefused("continuation"), "continuation"),
        (GateVerificationError("gate"), "gate"),
        (LockUnavailable("lock"), "lock"),
        (CanaryFailedError("canary"), "canary"),
        (PinnedGraphMismatchError("pin"), "pin"),
        (InstanceBranchMissing("branch"), "branch"),
        (GitCommandError("show-ref", 128, "bad"), "git: ('show-ref', 128, 'bad')"),
    ],
    ids=(
        "bound-exceeded",
        "continuation-refused",
        "gate-verification",
        "lock-unavailable",
        "canary-failed",
        "pinned-graph-mismatch",
        "instance-branch-missing",
        "git-command",
    ),
)
def test_tick_stalls_on_each_listed_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception, expected: str
) -> None:
    """Only the explicit operational failures are converted to stalled state."""
    lab = ForemanLab(tmp_path)
    lab.instantiate()

    def fail(*_args: object, **_kwargs: object) -> NoReturn:
        raise error

    monkeypatch.setattr(tick_module, "audit", fail)
    assert lab.tick().stalled == expected


@pytest.mark.parametrize(
    "error",
    (
        LifecycleConflictError("lifecycle conflict"),
        CarrierIntegrityError("carrier corrupt"),
        RuntimeError("corrupt"),
    ),
    ids=("lifecycle-conflict", "carrier-integrity", "runtime"),
)
def test_tick_propagates_every_unlisted_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    """Carrier corruption must never be turned into an apparently healthy tick."""
    lab = ForemanLab(tmp_path)
    lab.instantiate()
    monkeypatch.setattr(
        tick_module,
        "audit",
        lambda *_args: (_ for _ in ()).throw(error),
    )
    with pytest.raises(type(error), match=str(error)):
        lab.tick()


def test_tick_releases_its_band_when_an_unlisted_exception_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A corrupt carrier cannot leak the tick lock after the error escapes."""
    lab = ForemanLab(tmp_path)
    lab.instantiate()
    monkeypatch.setattr(
        tick_module,
        "audit",
        lambda *_args: (_ for _ in ()).throw(CarrierIntegrityError("corrupt")),
    )

    with pytest.raises(CarrierIntegrityError, match="corrupt"):
        lab.tick()

    held = lab.wiring().band
    held.acquire()
    held.release()
