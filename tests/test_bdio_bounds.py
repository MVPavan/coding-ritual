"""Unit tests for the §10 pre-mint predicates.

The §10.1 worked example is asserted verbatim: with `max_entries = 3`, rounds
1, 2 and 3 execute and the 4th back-edge arrival exhausts.
"""

from __future__ import annotations

import pytest

from workflow_interpreter.bdio import bounds
from workflow_interpreter.bdio.bounds import ActivationView, BoundKind
from workflow_interpreter.bdio.errors import BoundEvaluationError
from workflow_interpreter.bdio.wire import (
    ActivationMetadata,
    BeadRecord,
    Lifecycle,
    MintReason,
    WfKind,
)
from workflow_interpreter.schema.models import Outcome

REGION = "build-review"
NODE = "implement"
MAX_ENTRIES = 3


def _view(
    bead_id: str,
    *,
    round_no: int,
    node: str = NODE,
    region: str | None = REGION,
    outcome: Outcome | None = None,
    lifecycle: Lifecycle = Lifecycle.CLOSED,
    seq: int = 0,
    superseded_by: str | None = None,
) -> ActivationView:
    """One activation as the bound predicates see it."""
    return ActivationView(
        bead_id=bead_id,
        metadata=ActivationMetadata(
            wf_root_id="wf-root",
            node=node,
            region=region,
            round_no=round_no,
            seq=seq,
            idempotency_key=bead_id,
            mint_reason=MintReason.EDGE,
            runner_profile="p",
            model="m",
            session_id="s",
            intended_base_commit="c",
            lifecycle=lifecycle,
            outcome=outcome,
            superseded_by=superseded_by,
        ),
    )


def _bead(bead_id: str, kind: WfKind, **metadata: object) -> BeadRecord:
    """A bd row carrying only what the ceiling count reads."""
    return BeadRecord(
        id=bead_id,
        title=bead_id,
        status="open",
        issue_type="task",
        metadata={"wf_kind": kind.value} | metadata,
    )


# --- §10.1 region rounds -------------------------------------------------


@pytest.mark.parametrize(
    ("used_rounds", "target_round", "expected_refusal"),
    [
        (frozenset(), 1, False),  # round 1 executes
        (frozenset({1}), 2, False),  # round 2 executes
        (frozenset({1, 2}), 3, False),  # round 3 executes
        (frozenset({1, 2, 3}), 4, True),  # the 4th back-edge arrival exhausts
    ],
)
def test_worked_example_max_entries_three(
    used_rounds: frozenset[int], target_round: int, expected_refusal: bool
) -> None:
    refusal = bounds.region_round_refusal(
        region=REGION,
        distinct_rounds=used_rounds,
        target_round=target_round,
        max_entries=MAX_ENTRIES,
    )
    assert (refusal is not None) is expected_refusal
    if refusal is not None:
        assert refusal.bound is BoundKind.REGION_ROUNDS
        assert refusal.observed == len(used_rounds)
        assert refusal.limit == MAX_ENTRIES


def test_a_mint_into_an_already_entered_round_is_never_a_new_round() -> None:
    # Infra retries and steer continuations inherit `round_no` (§10.1).
    assert (
        bounds.region_round_refusal(
            region=REGION,
            distinct_rounds=frozenset({1, 2, 3}),
            target_round=3,
            max_entries=MAX_ENTRIES,
        )
        is None
    )


def test_max_entries_one_still_executes_round_one() -> None:
    # Drill 21: `max_entries = 1` → round 1 EXECUTES, the first back-edge exhausts.
    assert (
        bounds.region_round_refusal(
            region=REGION,
            distinct_rounds=frozenset(),
            target_round=1,
            max_entries=1,
        )
        is None
    )
    assert (
        bounds.region_round_refusal(
            region=REGION,
            distinct_rounds=frozenset({1}),
            target_round=2,
            max_entries=1,
        )
        is not None
    )


def test_distinct_rounds_excludes_superseded_and_other_regions() -> None:
    views = (
        _view("a", round_no=1),
        _view("b", round_no=2, superseded_by="a"),
        _view("c", round_no=3, region="other"),
        _view("d", round_no=1),
    )
    assert bounds.distinct_rounds(views, REGION) == frozenset({1})


def test_an_unreadable_round_refuses_rather_than_guesses() -> None:
    with pytest.raises(BoundEvaluationError):
        bounds.distinct_rounds((_view("a", round_no=0),), REGION)


# --- §10.3 instance ceiling ---------------------------------------------


@pytest.mark.parametrize(
    ("count", "limit", "refused"), [(4, 5, False), (5, 5, True), (6, 5, True)]
)
def test_ceiling_refuses_at_or_above_the_limit(
    count: int, limit: int, refused: bool
) -> None:
    refusal = bounds.instance_ceiling_refusal(
        bead_count=count, max_total_activations=limit
    )
    assert (refusal is not None) is refused


def test_ceiling_count_includes_gates_and_unclassified_but_not_events() -> None:
    beads = (
        _bead("a", WfKind.ACTIVATION),
        _bead("g", WfKind.GATE),
        _bead("e", WfKind.EVENT),
        _bead("r", WfKind.ROOT),
        BeadRecord(
            id="u", title="u", status="open", issue_type="task", metadata={"seq": 9}
        ),
    )
    assert bounds.ceiling_count(beads) == 3


def test_no_metadata_flag_can_remove_a_bead_from_the_count() -> None:
    # §10.3 ruling: the halt gate is exempt from the PREDICATE (applied at the
    # halt-gate call site), never from the COUNT. A bead that could hide behind
    # a metadata flag would make the one auditable boundedness statement
    # under-report — the opposite of fail-closed.
    beads = (
        _bead("a", WfKind.ACTIVATION),
        _bead("halt", WfKind.GATE, gate_reason="halt"),
        _bead("flagged", WfKind.GATE, exempt_from_ceiling=True),
    )
    assert bounds.ceiling_count(beads) == 3


# --- §10.2 system-outcome caps ------------------------------------------


@pytest.mark.parametrize(
    ("used", "max_infra_retries", "refused"),
    [(0, 2, False), (1, 2, False), (2, 2, False), (3, 2, True)],
)
def test_infra_retries_allow_one_plus_n_attempts(
    used: int, max_infra_retries: int, refused: bool
) -> None:
    # Drill 22: exactly `1 + max_infra_retries` attempts, then the fallback.
    refusal = bounds.infra_retry_refusal(
        node=NODE,
        round_no=1,
        consecutive_infra_closes=used,
        max_infra_retries=max_infra_retries,
    )
    assert (refusal is not None) is refused


def test_consecutive_infra_closes_restart_after_a_non_infra_close() -> None:
    views = (
        _view("a", round_no=1, seq=1, outcome=Outcome.ERROR_RUNNER),
        _view("b", round_no=1, seq=2, outcome=Outcome.FAIL_CODE),
        _view("c", round_no=1, seq=3, outcome=Outcome.ERROR_TRANSPORT),
    )
    assert bounds.consecutive_infra_closes(views, NODE, 1) == 1


def test_open_activations_do_not_consume_the_infra_budget() -> None:
    views = (
        _view("a", round_no=1, seq=1, outcome=Outcome.ERROR_RUNNER),
        _view("b", round_no=1, seq=2, lifecycle=Lifecycle.DISPATCHED),
    )
    assert bounds.consecutive_infra_closes(views, NODE, 1) == 1


@pytest.mark.parametrize(("used", "limit", "refused"), [(0, 2, False), (2, 2, True)])
def test_steers_are_capped_separately(used: int, limit: int, refused: bool) -> None:
    refusal = bounds.steer_refusal(
        node=NODE, round_no=1, steer_closes=used, max_steers=limit
    )
    assert (refusal is not None) is refused


def test_steer_closes_counts_only_steered_outcomes_at_this_node_and_round() -> None:
    views = (
        _view("a", round_no=1, outcome=Outcome.STEERED),
        _view("b", round_no=2, outcome=Outcome.STEERED),
        _view("c", round_no=1, node="review", outcome=Outcome.STEERED),
        _view("d", round_no=1, outcome=Outcome.ERROR_RUNNER),
    )
    assert bounds.steer_closes(views, NODE, 1) == 1
