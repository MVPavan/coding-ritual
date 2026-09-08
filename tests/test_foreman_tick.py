"""C2b ordering and catch-surface contracts for one foreman tick."""

from collections.abc import Iterable
from pathlib import Path
from time import monotonic
from typing import Final, NoReturn

import pytest

from tests._bdio import handle, race_residue
from tests._fake_bd import InjectedCrash
from tests._foreman import ForemanLab, entry_request
from tests._helpers import VALID_FIXTURE, mutate, write
from tests._supervisor import ChildScript
from tests.conftest import Signer
from workflow_interpreter.bdio import ArtifactIdentity, Evidence, ExitRecord
from workflow_interpreter.bdio.bounds import BoundKind, BoundRefusal
from workflow_interpreter.bdio.client import STATUS_CLOSED
from workflow_interpreter.bdio.config import SigningConfig
from workflow_interpreter.bdio.constants import DEVIATION_INPUTS_UNAVAILABLE
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
from workflow_interpreter.foreman.constants import (
    HALT_INPUTS,
    HALT_INPUTS_UNAVAILABLE,
)
from workflow_interpreter.foreman.frontier import Frontier, build_frontier
from workflow_interpreter.foreman.gates import halt_gate
from workflow_interpreter.schema.models import Outcome
from workflow_interpreter.supervisor import activation_ref
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


def test_tick_maps_band_contention_to_a_contended_result(tmp_path: Path) -> None:
    """The first ordered operation has no acquired lock to release on refusal.

    Contention is reported as its own field rather than as a stall: it is the
    one "nothing happened" a later tick may simply win (`Foreman.run` polls
    past it), while `stalled` is a condition a human has to clear.
    """
    lab = ForemanLab(tmp_path)
    lab.instantiate()
    held = lab.wiring().band
    held.acquire()
    try:
        report = lab.tick()
    finally:
        held.release()

    assert report.contended is True
    assert report.stalled is None


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


def test_the_reached_terminal_settles_and_closes_the_root_and_a_re_tick_is_inert(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """cr-o85.34.24: the terminal must be durable on the ROOT, not tick-log-only.

    Before this, an instance that reached `shipped` left its root bead OPEN
    with nothing naming the terminal — the live build-loop run's D4 — so the
    only way to learn how an instance ended was to read the tick transcript.
    """
    lab = ForemanLab(tmp_path, signing=signing_config, signer=sign_payload)
    root = lab.instantiate()
    assert lab.tick().dispatched is not None
    lab.tick()
    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
    )
    assert lab.tick().dispatched is not None
    lab.tick()
    ship = lab.tick().opened_gate
    assert ship is not None
    lab.approve(ship, Outcome.APPROVE)
    assert lab.tick().closed_gates == (ship,)

    report = lab.tick()
    settled = lab.store.reads.load_root(root.root_id)

    # The §11 canary round-trips a wisp on EVERY tick, so "wrote nothing" is
    # counted over the workflow rows and the two mutating surfaces, not over
    # every `bd create` the tick issued.
    def durable() -> tuple[int, ...]:
        return (
            len(lab.beads("activation")),
            len(lab.beads("gate")),
            len(lab.beads("event")),
            lab.count("update"),
            lab.count("close"),
        )

    writes = durable()
    again = lab.tick()

    assert report.terminal is True
    assert report.terminal_node == "shipped"
    assert settled.metadata.terminal == "shipped"
    assert settled.bead.status == STATUS_CLOSED
    assert settled.bead.close_reason == "outcome=terminal terminal=shipped"
    # A re-tick against a settled root writes NOTHING and still reports the
    # terminal: no re-mint of the entry, no dead end, no second close.
    assert again.terminal is True
    assert again.terminal_node == "shipped"
    assert durable() == writes


def test_a_crash_between_the_terminal_record_and_the_root_close_repairs_forward(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """The §3.1 settle is metadata first, close second — so it has a crash window.

    The half-written state (root names its terminal, bead still open) is the
    one every §5.1 transition leaves, and the answer is the same: the next tick
    FINISHES it rather than refusing or re-writing it.
    """
    lab = ForemanLab(tmp_path, signing=signing_config, signer=sign_payload)
    root = lab.instantiate()
    assert lab.tick().dispatched is not None
    lab.tick()
    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
    )
    assert lab.tick().dispatched is not None
    lab.tick()
    ship = lab.tick().opened_gate
    assert ship is not None
    lab.approve(ship, Outcome.APPROVE)
    assert lab.tick().closed_gates == (ship,)

    # The root close is the first `bd close` this tick issues; the gate's own
    # close landed on the tick before.
    lab.fake_bd.crash_on("close", 1)
    with pytest.raises(InjectedCrash):
        lab.tick()
    half_written = lab.store.reads.load_root(root.root_id)

    repaired = lab.tick()
    closes = lab.count("close")
    inert = lab.tick()

    assert half_written.metadata.terminal == "shipped"
    assert half_written.bead.status != STATUS_CLOSED
    assert repaired.terminal_node == "shipped"
    settled = lab.store.reads.load_root(root.root_id)
    assert settled.bead.status == STATUS_CLOSED
    assert settled.bead.close_reason == "outcome=terminal terminal=shipped"
    assert inert.terminal_node == "shipped"
    assert lab.count("close") == closes


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
                    'isolation     = "worktree"               # worktree | in-repo',
                    'isolation     = "in-repo"                # worktree | in-repo',
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
        (CanaryFailedError("canary"), "canary"),
        (PinnedGraphMismatchError("pin"), "pin"),
        (InstanceBranchMissing("branch"), "branch"),
        (GitCommandError("show-ref", 128, "bad"), "git: ('show-ref', 128, 'bad')"),
    ],
    ids=(
        "bound-exceeded",
        "continuation-refused",
        "gate-verification",
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


def test_a_lock_miss_deeper_in_the_tick_is_contended_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`LockUnavailable` is the same transient wherever the tick meets it."""
    lab = ForemanLab(tmp_path)
    lab.instantiate()

    def fail(*_args: object, **_kwargs: object) -> NoReturn:
        raise LockUnavailable("lock")

    monkeypatch.setattr(tick_module, "audit", fail)

    report = lab.tick()

    assert report.contended is True
    assert report.stalled is None


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


CROSS_REGION_INPUTS_GRAPH: Final[str] = """
[graph]
id = "cross-region-inputs"
version = "1.0.0"
entry = "implement"
description = "one region produces what the other region consumes"

[instance]
max_total_activations = 20

[[region]]
name = "build"
mode = "bounded-cycle"
entry_node = "implement"
max_entries = 2
on_exhausted = "triage"

[[region]]
name = "audit"
mode = "bounded-cycle"
entry_node = "review"
max_entries = 2
on_exhausted = "triage"

[[node]]
name = "implement"
kind = "task"
region = "build"
runner = "profile:implementer"
model = "default"
instructions = "Implement what task_brief describes."
isolation = "worktree"
writes = true
allowed_paths = ["src/**"]
inputs = ["task_brief"]
verify = [{ cmd = "scripts/verify-feature.sh", timeout = "10m" }]
token_budget = 1000
max_wall = "10m"
stale_after = "5m"
max_infra_retries = 1
max_steers = 1
outcomes = ["done"]

[[node]]
name = "review"
kind = "task"
region = "audit"
runner = "profile:critic"
model = "default"
instructions = "Read diff_artifact and report done."
isolation = "worktree"
writes = false
allowed_paths = []
inputs = ["task_brief", "diff_artifact"]
verify = [{ cmd = "scripts/verify-feature.sh", timeout = "10m" },
          { cmd = "scripts/review-checks.sh", timeout = "5m" }]
token_budget = 1000
max_wall = "10m"
stale_after = "5m"
max_infra_retries = 1
max_steers = 1
outcomes = ["done"]

[[node]]
name = "triage"
kind = "gate"
gate_type = "human"
binds = "immutable"
outcomes = ["rebudget", "abandon"]

[[node]]
name = "finished"
kind = "terminal"

[[edge]]
from = "implement"
on = "done"
to = "review"

[[edge]]
from = "review"
on = "done"
to = "finished"

[[edge]]
from = "triage"
on = "rebudget"
to = "implement"

[[edge]]
from = "triage"
on = "abandon"
to = "finished"

[fallback]
to = "triage"

[[source]]
name = "task_brief"
producer = "instance"
optional = false
trim_priority = 1

[[source]]
name = "diff_artifact"
producer = "node:implement"
optional = false
trim_priority = 1
"""
"""The §2 fixture's two task nodes split across two bounded-cycle regions, so
`review` declares a required input produced in the OTHER region — the shape D1's
binding rule exists for. Node names are the fixture's because the lab pins its
§7.3 verify digests by node name (`tests/_supervisor.py:388-400`)."""


def _cross_region_lab(tmp_path: Path) -> ForemanLab:
    """A lab on the two-region graph, with the fixture's verify script."""
    return ForemanLab(
        tmp_path,
        toml=write(tmp_path, CROSS_REGION_INPUTS_GRAPH, "cross-region-inputs.toml"),
    )


def _closed_producer(lab: ForemanLab) -> str:
    """Drive the producing region's only node to a completed close."""
    produce = lab.tick().dispatched
    assert produce is not None
    assert lab.tick().settled == produce
    return produce


def test_tick_binds_a_cross_region_producer_when_it_mints_the_consumer(
    tmp_path: Path,
) -> None:
    """D1 on the real seam: the consumer binds a producer from another region."""
    lab = _cross_region_lab(tmp_path)
    lab.instantiate()
    produce = _closed_producer(lab)
    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"done"}\n', effects='{"paths":[]}')
    )

    consume = lab.tick().dispatched

    assert consume is not None
    metadata = lab.store.reads.load_activation(consume).metadata
    assert metadata.node == "review"
    assert metadata.region != lab.store.reads.load_activation(produce).metadata.region
    assert tuple(binding.name for binding in metadata.inputs) == (
        "task_brief",
        "diff_artifact",
    )
    assert metadata.inputs[1].producer_activation_id == produce


def test_tick_halts_on_a_gate_when_a_bound_input_is_unavailable(
    tmp_path: Path,
) -> None:
    """D2: an unprovable input opens a halt gate instead of escaping the tick."""
    lab = _cross_region_lab(tmp_path)
    lab.instantiate()
    produce = _closed_producer(lab)
    lab.fake_bd.rows[produce]["metadata"]["evidence"] = {}

    report = lab.tick()

    assert report.halted is True
    assert report.opened_gate is not None
    gate = lab.store.reads.load_gate(report.opened_gate)
    assert gate.metadata.halt_reason == HALT_INPUTS.format(
        reason="writing input producer has no artifact"
    )


def test_wrapper_close_of_an_unmaterializable_input_halts_without_redispatch(
    tmp_path: Path,
) -> None:
    """The BLOCKER case: the binder succeeds at mint and the WRAPPER cannot read it.

    The wrapper is a separate process in production, so an escaping
    `InputsUnavailable` would leave the activation MINTED and let every later
    tick re-dispatch it. `InlineSpawner` still enters through `run_wrapper`,
    which is where the close lives; the out-of-process spawner adds only the
    fork, so the seam under test is the same one.
    """
    lab = _cross_region_lab(tmp_path)
    root = lab.instantiate()
    produce = _closed_producer(lab)
    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"done"}\n', effects='{"paths":[]}')
    )
    # The binding still names a live activation; only the artifact it pins is
    # gone, which is exactly what `materialize` refuses to read past.
    lab.git.run(
        GitSubcommand.UPDATE_REF,
        "-d",
        activation_ref(root.root_id, produce),
        cwd=lab.repo,
    )

    consume = lab.tick().dispatched

    assert consume is not None
    closed = lab.store.reads.load_activation(consume)
    assert closed.metadata.outcome is Outcome.ERROR_TRANSPORT
    assert [item.kind for item in closed.metadata.deviations] == [
        DEVIATION_INPUTS_UNAVAILABLE
    ]
    assert "artifact" in closed.metadata.deviations[0].reason

    halt = lab.tick().opened_gate

    assert halt is not None
    assert lab.store.reads.load_gate(halt).metadata.halt_reason == (
        HALT_INPUTS_UNAVAILABLE.format(node="review", activation_id=consume)
    )
    launches = len(lab.spawner.launches)
    lab.tick()
    assert len(lab.spawner.launches) == launches
    assert len(lab.beads("activation")) == 2
