"""DRILL-27: the forced-rejection feature run, killed and rebuilt at every §13
crash-drill injection point, end to end.

Spec anchors: docs/specs/workflow-interpreter.md:929-935 (the drill itself)
and :851-861 (the six injection points). `test_drill_27_...` drives ONE
continuous flagged run through implement -> review(reject) -> rework ->
review(accept) -> ship, injecting a kill-and-`lab.rebuild()` at each of the
six points along the way, then proves the row's five final invariants.
`test_drill_27_control_case_...` is the row's control sub-case: the SAME
brief-composition check against the unmutated fixture, where the clause must
appear in neither brief.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._foreman import ForemanLab, LockedPersistentBd
from tests._helpers import VALID_FIXTURE, mutate, write
from tests._supervisor import ChildScript, handle_for
from tests.conftest import Signer
from workflow_interpreter.bdio import Lifecycle, Outcome, SigningConfig, bounds
from workflow_interpreter.bdio.carriers import ExitRecord
from workflow_interpreter.foreman.constants import FORCED_FIRST_REJECT
from workflow_interpreter.supervisor import LaunchReceipt
from workflow_interpreter.supervisor.paths import ExecLedger, read_record, write_record

# Every test in this file is a §5 drill row (DRILL-27 and its control).
pytestmark = pytest.mark.acceptance

# The exit-record mirror is the 3rd `update` call of a fresh dispatch attempt
# (mint's `create` does not count): `record_precondition` (1), `record_dispatch`
# (3), with envelope persistence (2), then the exit-record mirror itself (4). `crash_on` is relative to when
# it is armed, so this offset holds regardless of the lab's prior history.
_EXIT_MIRROR_UPDATE_OFFSET = 4

# `record_precondition` is the FIRST `update` call of a dispatch attempt —
# armed here, its own write never lands, even though the real git reset it
# reports on already ran in-process just before it (drill 5's premise).
_PRECONDITION_UPDATE_OFFSET = 1

REWORK_MARKER = '{"outcome":"done"}\n'

REJECT_SCRIPT = ChildScript(
    marker='{"outcome":"reject"}\n',
    effects='{"paths":[]}',
    artifact_path="review.md",
    artifact_body="request a rework",
)

REWORK_SCRIPT = ChildScript(
    marker=REWORK_MARKER,
    effects='{"paths":["src/feature.py"]}',
    write_path="src/feature.py",
    write_body="value = 3\n",
    commit=True,
    # spec:857-859, injection point 4: the CHILD itself asserts its worktree
    # is clean before it writes or commits anything — the runner's own
    # observation, not a report about it from outside (see the comment at
    # the assertion site below for why an outside diff cannot cover this).
    assert_clean_tree=True,
)


def test_drill_27_pins_the_opt_in_and_forces_only_the_first_review_brief(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """DRILL-27: kill and rebuild the foreman at all six §13 injection points
    across one forced-rejection run, then prove its five final invariants."""
    flagged = write(
        tmp_path,
        mutate(
            VALID_FIXTURE.read_text(encoding="utf-8"),
            (("test_force_first_reject = false", "test_force_first_reject = true"),),
        ),
    )
    state = tmp_path / "persistent-bd.json"

    def persistent(workspace: str) -> LockedPersistentBd:
        return LockedPersistentBd(workspace, state)

    lab = ForemanLab(
        tmp_path,
        toml=flagged,
        allow_test_flags=True,
        signing=signing_config,
        signer=sign_payload,
        bd_factory=persistent,
    )
    root = lab.instantiate()

    # --- injection point 1: after mint / before exec (implement, round 1) --
    lab.spawner.fail_next()
    with pytest.raises(Exception, match="inline spawn failed"):
        lab.tick()
    minted = lab.beads("activation")
    assert len(minted) == 1
    implement_id = str(minted[0]["id"])
    assert (
        lab.store.reads.load_activation(implement_id).metadata.lifecycle
        is Lifecycle.MINTED
    )
    assert ExecLedger(lab.wiring().paths.ledger(implement_id)).count() == 0

    lab.rebuild()
    rebuilt_root = lab.store.reads.load_root(root.root_id)
    assert (
        rebuilt_root.metadata.allow_test_flags is True
    )  # P8: re-read on every rebuild

    # --- injection point 3: after child exit / before the bd exit mirror ---
    # (this same dispatch attempt: precondition and dispatch succeed, and the
    # exit-mirror write — the 4th `update` of a fresh attempt — is what dies)
    lab.fake_bd.crash_on("update", _EXIT_MIRROR_UPDATE_OFFSET)
    with pytest.raises(Exception, match="bd update died"):
        lab.tick()
    assert len(lab.beads("activation")) == 1  # same idempotency key, no second mint
    assert ExecLedger(lab.wiring().paths.ledger(implement_id)).count() == 1
    exit_record = read_record(lab.wiring().paths.exit_file(implement_id), ExitRecord)
    assert exit_record is not None
    assert (
        lab.store.reads.load_activation(implement_id).metadata.lifecycle
        is Lifecycle.DISPATCHED
    )
    implement_task = next(
        task
        for task in lab.profiles.profile.tasks
        if task.activation_id == implement_id
    )
    assert FORCED_FIRST_REJECT not in implement_task.brief

    lab.rebuild()
    settle_report = lab.tick()
    assert settle_report.settled == implement_id
    first_attempt = lab.store.reads.load_activation(implement_id)
    assert first_attempt.metadata.lifecycle is Lifecycle.CLOSED
    assert first_attempt.metadata.outcome is Outcome.DONE
    assert first_attempt.metadata.exit_record is not None
    assert first_attempt.metadata.exit_record.ended_at == exit_record.ended_at
    assert first_attempt.metadata.pre_attempt_commit is not None

    ceiling_after_point_1_and_3 = bounds.ceiling_count(
        lab.store.reads.instance_beads(root.root_id)
    )

    # --- injection point 2: after receipt durable / before child exec ------
    # (fork barrier): taking implement(1)'s edge mints AND dispatches review,
    # round 1 (the forced-rejection round), in the same tick. The reject
    # script is queued only after every rebuild below: `_build_fresh` starts
    # a new `_Profiles` with an empty queue on each `lab.rebuild()`.
    lab.spawner.fail_next()
    with pytest.raises(Exception, match="inline spawn failed"):
        lab.tick()
    review_activation = next(
        activation
        for activation in lab.store.reads.list_activations(root.root_id)
        if activation.metadata.node == "review"
    )
    review_id = review_activation.activation_id
    assert review_activation.metadata.lifecycle is Lifecycle.MINTED
    assert ExecLedger(lab.wiring().paths.ledger(review_id)).count() == 0

    wiring = lab.wiring()
    wiring.paths.ensure_activation_dir(review_id)
    stale_receipt = LaunchReceipt(
        launch_id="never-crossed",
        root_id=root.root_id,
        activation_id=review_id,
        argv=("/bin/false",),
        cwd=str(lab.repo),
        handle=handle_for(1, log_path=str(wiring.paths.log(review_id))),
    )
    write_record(wiring.paths.receipt(review_id), stale_receipt)
    assert ExecLedger(wiring.paths.ledger(review_id)).count() == 0

    lab.rebuild()
    lab.profiles.next_script(REJECT_SCRIPT)
    report = lab.tick()
    assert report.dispatched == review_id
    review_ledger = ExecLedger(lab.wiring().paths.ledger(review_id))
    assert review_ledger.count() == 1  # relaunch appends exactly one
    assert not review_ledger.has_launch("never-crossed")
    review_task = next(
        task for task in lab.profiles.profile.tasks if task.activation_id == review_id
    )
    assert FORCED_FIRST_REJECT in review_task.brief

    assert lab.tick().settled == review_id
    reviewed_first = lab.store.reads.load_activation(review_id)
    assert reviewed_first.metadata.outcome is Outcome.REJECT

    ceiling_after_point_2 = bounds.ceiling_count(
        lab.store.reads.instance_beads(root.root_id)
    )

    # --- injection point 4: after outcome close / before reset (rework) ----
    lab.spawner.fail_next()
    with pytest.raises(Exception, match="inline spawn failed"):
        lab.tick()
    rework = next(
        activation
        for activation in lab.store.reads.list_activations(root.root_id)
        if activation.metadata.node == "implement"
        and activation.activation_id != implement_id
    )
    rework_id = rework.activation_id
    assert rework.metadata.lifecycle is Lifecycle.MINTED

    lab.rebuild()

    # --- injection point 5: mid-reset (the same rework dispatch, 2nd try) --
    # The real git reset already ran in-process before `record_precondition`;
    # crashing that write proves the precondition is idempotent on rerun.
    lab.fake_bd.crash_on("update", _PRECONDITION_UPDATE_OFFSET)
    with pytest.raises(Exception, match="bd update died"):
        lab.tick()
    mid_reset = lab.store.reads.load_activation(rework_id)
    assert mid_reset.metadata.lifecycle is Lifecycle.MINTED
    assert mid_reset.metadata.pre_attempt_commit is None

    lab.rebuild()
    lab.profiles.next_script(REWORK_SCRIPT)
    report = lab.tick()
    assert report.dispatched == rework_id
    dispatched_rework = lab.store.reads.load_activation(rework_id)
    assert (
        dispatched_rework.metadata.intended_base_commit
        == first_attempt.metadata.pre_attempt_commit
    )
    assert (
        dispatched_rework.metadata.pre_attempt_commit
        == first_attempt.metadata.pre_attempt_commit
    )
    assert (
        dispatched_rework.metadata.reset_verified_commit
        == first_attempt.metadata.pre_attempt_commit
    )

    assert lab.tick().settled == rework_id
    rework_settled = lab.store.reads.load_activation(rework_id)
    assert rework_settled.metadata.outcome is Outcome.DONE
    assert rework_settled.metadata.evidence is not None
    assert rework_settled.metadata.evidence.artifact is not None
    # spec:857-859, the runner's OWN view rather than its self-reported
    # metadata: `git commit` records the tree it actually started from as
    # the new commit's PARENT, so reading that parent back from the real
    # object store is the rework runner observing its own starting HEAD.
    # `diff_names(base, head)` below only proves the COMMIT is scoped to
    # exactly the one write the child made — it sees committed differences
    # only, so it cannot by itself rule out an untracked or unstaged leftover
    # that the child never touched (REWORK_SCRIPT's own `git add -- <path>`
    # stages only its one write_path). The clean-tree half of the clause is
    # instead covered by `assert_clean_tree` on REWORK_SCRIPT itself: the
    # child runs `git status --porcelain` before writing or committing
    # anything and fails loudly if that worktree it is about to work in is
    # not already clean — reaching this line at all is the runner's own
    # proof that its observation passed.
    rework_artifact = rework_settled.metadata.evidence.artifact
    assert (
        lab.git.rev_parse(f"{rework_artifact.commit_oid}^", cwd=lab.repo)
        == first_attempt.metadata.pre_attempt_commit
    )
    assert lab.git.diff_names(
        first_attempt.metadata.pre_attempt_commit,
        rework_artifact.commit_oid,
        cwd=lab.repo,
    ) == ("src/feature.py",)
    assert first_attempt.metadata.evidence is not None
    assert first_attempt.metadata.evidence.artifact is not None
    # clause (b): the rework artifact's tree_oid != the rejected artifact's
    assert (
        rework_settled.metadata.evidence.artifact.tree_oid
        != first_attempt.metadata.evidence.artifact.tree_oid
    )

    ceiling_after_points_4_and_5 = bounds.ceiling_count(
        lab.store.reads.instance_beads(root.root_id)
    )

    # --- review, round 2: accept, no injection ------------------------------
    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
    )
    review_round_2 = lab.tick().dispatched
    assert review_round_2 is not None
    assert lab.tick().settled == review_round_2
    accepted_activation = lab.store.reads.load_activation(review_round_2)
    assert accepted_activation.metadata.outcome is Outcome.ACCEPT

    # --- injection point 6a: after gate-open / before first notification ---
    # spec:861-863: the crash belongs between the gate's OWN persistence and
    # its first notification, not after `Foreman.tick()` has already
    # returned the opened gate to its caller — by then the notification-
    # bearing `TickReport` has already gone out. The durable notification
    # this tick would make is the transition EVENT it backfills right after
    # `open_gate` returns (`foreman/tick.py`, `self._backfill`): a fresh
    # `create` for the review->ship edge intent. Ordering within one tick is
    # `startup_canary` (1st create), `open_gate` (2nd), backfill event
    # (3rd) — `crash_on_tick_create(2)` (relative, +1 for the canary; see
    # EVENT-B) kills the 3rd, landing exactly between the two.
    events_before = len(lab.beads("event"))
    lab.crash_on_tick_create(2)
    with pytest.raises(Exception, match="bd create died"):
        lab.tick()
    persisted_gates = lab.store.reads.list_gates(root.root_id)
    assert len(persisted_gates) == 1  # the gate itself landed before the crash
    ship = persisted_gates[0].gate_id
    assert len(lab.beads("event")) == events_before  # ...its notification did not

    lab.rebuild()
    no_dupe_report = lab.tick()
    assert no_dupe_report.opened_gate is None  # re-tick converges: no new gate
    # RECOVERY/REDELIVERY, AS FOUND (not as assumed): the missed notification
    # is NOT redelivered by this immediate re-tick. `self._backfill` only
    # runs inside `route_head`/`halt_dead_end`/the abandoned-halt path — i.e.
    # only when a NEW routing decision is being taken — and review_round_2 is
    # already consumed by the gate that landed before the crash, so there is
    # no decision left here to trigger it. The event stays durably absent,
    # not duplicated, until some LATER tick takes one.
    assert no_dupe_report.events_backfilled == 0
    assert len(lab.beads("event")) == events_before  # still outstanding
    assert len(lab.beads("gate")) == 1
    reopened_ship = lab.store.reads.load_gate(ship)
    assert reopened_ship.metadata.state.value == "open"

    # --- injection point 6b: after payload verification / before edge-taking
    lab.approve(ship, Outcome.APPROVE)
    lab.fake_bd.crash_on("close")
    with pytest.raises(Exception, match="bd close died"):
        lab.tick()
    verified_not_closed = lab.store.reads.load_gate(ship)
    assert verified_not_closed.metadata.state.value == "closed"
    assert verified_not_closed.bead.status == "open"

    lab.rebuild()
    repaired = lab.tick()
    assert repaired.closed_gates == (ship,)
    assert len(lab.beads("gate")) == 1  # no duplicate gate (same key)
    # `intake_all`'s gate-close branch doesn't call `_backfill` either — the
    # 6a notification is STILL outstanding after the gate is verified closed.
    assert repaired.events_backfilled == 0
    assert len(lab.beads("event")) == events_before

    # only the NEXT tick that takes a routing decision — here, the closed
    # ship gate itself becoming the frontier head and routing on to
    # terminal — recomputes every outstanding intent and backfills them all:
    # the missed 6a edge (review round 2 -> ship) alongside this tick's own
    # (ship -> terminal). Redelivered exactly once, never duplicated.
    terminal_report = lab.tick()
    assert terminal_report.terminal is True
    assert terminal_report.events_backfilled == 2
    events_at_terminal = len(lab.beads("event"))
    assert events_at_terminal == events_before + 2

    idle_report = lab.tick()  # re-tick past terminal: converges, no duplicate edge
    assert idle_report.terminal is True
    assert len(lab.beads("event")) == events_at_terminal

    # --- final invariant (a): one activation per idempotency key -----------
    by_key: dict[str, int] = {}
    for raw in lab.fake_bd.rows.values():
        if raw["metadata"].get("wf_kind") != "activation":
            continue
        key = str(raw["metadata"]["idempotency_key"])
        by_key[key] = by_key.get(key, 0) + 1
    assert all(count == 1 for count in by_key.values())

    # --- final invariant (c): reviewed identity == verified identity -------
    # "The accepted activation's evidence.artifact" cannot literally be
    # review's OWN evidence: spec §7 point 4 scopes `evidence.artifact` to
    # WRITING attempts ("every writing attempt ends in a commit"), and
    # review is `writes = false` — confirmed below. The identity the ship
    # gate carries is traced instead to the WRITE activation whose artifact
    # review accepted (rework): that is what "the reviewed identity" is.
    ship_gate = lab.store.reads.load_gate(ship)
    assert accepted_activation.metadata.evidence is not None
    assert accepted_activation.metadata.evidence.artifact is None
    assert rework_settled.metadata.evidence is not None
    reviewed_artifact = rework_settled.metadata.evidence.artifact
    assert reviewed_artifact is not None
    assert ship_gate.metadata.artifact_ref == reviewed_artifact.commit_oid
    assert ship_gate.metadata.artifact_digest == reviewed_artifact.tree_oid

    # --- final invariant (d): every bead carries wf_root_id -----------------
    # Excludes the startup canary: `CanaryMetadata` (bdio/wire.py) has no
    # `wf_root_id` field at all — "the one permitted decision-irrelevant
    # wisp", by design unscoped to any instance — so it is not one of the
    # instance's own beads the row means.
    for raw in lab.fake_bd.rows.values():
        if raw["metadata"].get("wf_kind") == "canary":
            continue
        assert raw["metadata"].get("wf_root_id") == root.root_id

    # --- final invariant (e): ceiling arithmetic is consistent, monotone ---
    final_ceiling = bounds.ceiling_count(lab.store.reads.instance_beads(root.root_id))
    assert final_ceiling == len(lab.beads("activation")) + len(lab.beads("gate"))
    ceilings_across_restarts = (
        ceiling_after_point_1_and_3,
        ceiling_after_point_2,
        ceiling_after_points_4_and_5,
        final_ceiling,
    )
    assert list(ceilings_across_restarts) == sorted(ceilings_across_restarts)


def test_drill_27_control_case_never_forces_a_reject_without_the_flag(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """The row's control sub-case: the unmutated fixture, no opt-in, forces
    nothing — the clause must appear in neither the implement nor the review
    brief, unlike the flagged run where it fires on review alone."""
    lab = ForemanLab(
        tmp_path,
        toml=VALID_FIXTURE,
        allow_test_flags=False,
        signing=signing_config,
        signer=sign_payload,
    )
    lab.instantiate()

    implement_id = lab.tick().dispatched
    assert implement_id is not None
    assert lab.tick().settled == implement_id
    implement_task = next(
        task
        for task in lab.profiles.profile.tasks
        if task.activation_id == implement_id
    )
    assert FORCED_FIRST_REJECT not in implement_task.brief

    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
    )
    review_id = lab.tick().dispatched
    assert review_id is not None
    review_task = next(
        task for task in lab.profiles.profile.tasks if task.activation_id == review_id
    )
    assert FORCED_FIRST_REJECT not in review_task.brief
