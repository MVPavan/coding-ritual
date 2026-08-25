"""§3.2 derived mint facts — what the caller can no longer state.

Driven through the real `WorkflowStore` against the in-memory bd, so these
assert the facts that actually land on the bead, not a pure function's return
value. No bd binary is involved.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pytest

from tests._bdio import (
    NODE_A1,
    NODE_B1,
    NODE_B2,
    REGION,
    REGION_A,
    REGION_B,
    REVIEW,
    entry_request,
    load_cross_region,
    load_definition,
    make_root,
    run_to_close,
)
from tests.conftest import BRANCH_HEAD
from workflow_interpreter import GraphDefinition
from workflow_interpreter.bdio import bounds, mint
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.errors import (
    BdConfigError,
    BoundExceededError,
    CarrierIntegrityError,
)
from workflow_interpreter.bdio.records import ActivationRecord
from workflow_interpreter.bdio.wire import Lifecycle, MintReason, metadata_dict
from workflow_interpreter.schema.models import Outcome

PRE_ATTEMPT: Final[str] = "a" * 40


@pytest.fixture(scope="session")
def definition() -> GraphDefinition:
    """The §2 canonical fixture, loaded and hashed once."""
    return load_definition()


# --- region and round ----------------------------------------------------


def test_region_comes_from_the_pinned_graph_not_the_caller(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    root = make_root(fake_store, definition)
    minted = fake_store.mint_activation(root.root_id, entry_request())
    assert minted.activation.metadata.region == REGION
    assert minted.activation.metadata.round_no == 1


def test_a_node_the_pinned_graph_does_not_declare_is_refused(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # Without a declaration there is no region and no bounds to evaluate.
    root = make_root(fake_store, definition)
    with pytest.raises(CarrierIntegrityError, match="not declared by the pinned graph"):
        fake_store.mint_activation(root.root_id, entry_request(node="nowhere"))


@pytest.mark.parametrize("node", ["ship", "shipped"], ids=["gate", "terminal"])
def test_only_a_task_node_is_dispatchable(
    fake_store: WorkflowStore, definition: GraphDefinition, node: str
) -> None:
    # A gate bead is minted by `open_gate` under its own §3.4 key and a terminal
    # runs nothing; an activation at either was a bead consuming the §10.3
    # ceiling under no region bound (probed, round-2 review).
    root = make_root(fake_store, definition)
    first = fake_store.mint_activation(root.root_id, entry_request()).activation
    run_to_close(fake_store, first.activation_id, Outcome.DONE)
    with pytest.raises(CarrierIntegrityError, match="only task nodes"):
        fake_store.mint_activation(
            root.root_id,
            entry_request(
                node=node,
                mint_reason=MintReason.EDGE,
                predecessor_activation_id=first.activation_id,
            ),
        )


def test_an_entry_mint_must_target_the_graphs_entry_node(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    root = make_root(fake_store, definition)
    with pytest.raises(CarrierIntegrityError, match="entry node"):
        fake_store.mint_activation(root.root_id, entry_request(node=REVIEW))


def test_a_mid_region_edge_inherits_its_predecessors_round(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # `review` is not the region's entry node, so it runs in round 1 with the
    # implementation it is reviewing.
    root = make_root(fake_store, definition)
    first = fake_store.mint_activation(root.root_id, entry_request()).activation
    run_to_close(fake_store, first.activation_id, Outcome.DONE)
    review = fake_store.mint_activation(
        root.root_id,
        entry_request(
            node=REVIEW,
            mint_reason=MintReason.EDGE,
            predecessor_activation_id=first.activation_id,
        ),
    ).activation
    assert review.metadata.round_no == 1
    assert review.metadata.outcome_taken is Outcome.DONE


def test_a_back_edge_onto_the_entry_node_opens_the_next_round(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # §10.1: `round_no` increments on entry into the region's entry_node.
    root = make_root(fake_store, definition)
    first = fake_store.mint_activation(root.root_id, entry_request()).activation
    run_to_close(fake_store, first.activation_id, Outcome.DONE)
    review = fake_store.mint_activation(
        root.root_id,
        entry_request(
            node=REVIEW,
            mint_reason=MintReason.EDGE,
            predecessor_activation_id=first.activation_id,
        ),
    ).activation
    run_to_close(fake_store, review.activation_id, Outcome.REJECT)
    rework = fake_store.mint_activation(
        root.root_id,
        entry_request(
            mint_reason=MintReason.EDGE,
            predecessor_activation_id=review.activation_id,
        ),
    ).activation
    assert rework.metadata.round_no == 2
    assert rework.metadata.outcome_taken is Outcome.REJECT


def test_an_infra_retry_inherits_the_round_it_is_retrying(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # System outcomes never consume rounds (§10.2).
    root = make_root(fake_store, definition)
    first = fake_store.mint_activation(root.root_id, entry_request()).activation
    run_to_close(fake_store, first.activation_id, Outcome.ERROR_RUNNER)
    retry = fake_store.mint_activation(
        root.root_id,
        entry_request(
            mint_reason=MintReason.INFRA_RETRY,
            predecessor_activation_id=first.activation_id,
        ),
    ).activation
    assert retry.metadata.round_no == 1
    assert retry.metadata.outcome_taken is Outcome.ERROR_RUNNER


def test_a_cross_region_arrival_starts_the_target_regions_own_round(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    # The defect: a LEGAL forward edge into a second region carried the SOURCE
    # region's counter across, so `rb` — arriving for the FIRST time — was
    # already counting round 3 (probed, round-2 review). Rounds are
    # region-local; a foreign counter is not evidence about this region's
    # budget. `rb` declares max_entries = 2, and both of them must still be
    # spendable after the arrival (probed, round-3 review).
    definition = load_cross_region(tmp_path)
    root = make_root(fake_store, definition)
    third = _run_region_a_to_round_three(fake_store, root.root_id)
    assert third.metadata.round_no == 3

    arrival = fake_store.mint_activation(
        root.root_id,
        entry_request(
            node=NODE_B1,
            mint_reason=MintReason.EDGE,
            predecessor_activation_id=third.activation_id,
        ),
    ).activation
    assert arrival.metadata.region == REGION_B
    assert arrival.metadata.round_no == 1

    run_to_close(fake_store, arrival.activation_id, Outcome.REJECT)
    back = fake_store.mint_activation(
        root.root_id,
        entry_request(
            node=NODE_B1,
            mint_reason=MintReason.EDGE,
            predecessor_activation_id=arrival.activation_id,
        ),
    ).activation
    assert back.metadata.round_no == 2
    assert _rounds(fake_store, root.root_id, REGION_A) == frozenset({1, 2, 3})
    assert _rounds(fake_store, root.root_id, REGION_B) == frozenset({1, 2})

    # And the budget is exactly what `rb` declared: the third entry exhausts.
    run_to_close(fake_store, back.activation_id, Outcome.REJECT)
    with pytest.raises(BoundExceededError, match="exhausted"):
        fake_store.mint_activation(
            root.root_id,
            entry_request(
                node=NODE_B1,
                mint_reason=MintReason.EDGE,
                predecessor_activation_id=back.activation_id,
            ),
        )


def test_an_arrival_deeper_in_a_region_stays_in_its_predecessors_round(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """A non-entry member is reached from INSIDE its region and inherits."""
    definition = load_cross_region(tmp_path)
    root = make_root(fake_store, definition)
    first = _run_region_a_to_round_three(fake_store, root.root_id)
    entry = fake_store.mint_activation(
        root.root_id,
        entry_request(
            node=NODE_B1,
            mint_reason=MintReason.EDGE,
            predecessor_activation_id=first.activation_id,
        ),
    ).activation
    run_to_close(fake_store, entry.activation_id, Outcome.DONE)

    deeper = fake_store.mint_activation(
        root.root_id,
        entry_request(
            node=NODE_B2,
            mint_reason=MintReason.EDGE,
            predecessor_activation_id=entry.activation_id,
        ),
    ).activation

    assert deeper.metadata.region == REGION_B
    assert deeper.metadata.round_no == entry.metadata.round_no
    assert _rounds(fake_store, root.root_id, REGION_B) == frozenset({1})


def _run_region_a_to_round_three(
    store: WorkflowStore, root_id: str
) -> ActivationRecord:
    """Three entries into `ra` via its self-loop, the third closed `done`."""
    record = store.mint_activation(root_id, entry_request(node=NODE_A1)).activation
    for outcome in (Outcome.REJECT, Outcome.REJECT):
        run_to_close(store, record.activation_id, outcome)
        record = store.mint_activation(
            root_id,
            entry_request(
                node=NODE_A1,
                mint_reason=MintReason.EDGE,
                predecessor_activation_id=record.activation_id,
            ),
        ).activation
    run_to_close(store, record.activation_id, Outcome.DONE)
    return store.reads.load_activation(record.activation_id)


def _rounds(store: WorkflowStore, root_id: str, region: str) -> frozenset[int]:
    """The distinct rounds the §10.1 predicate sees in `region`."""
    return bounds.distinct_rounds(
        mint.views_of(store.reads.list_activations(root_id)), region
    )


# --- outcome_taken and mint reason --------------------------------------


def test_a_mislabeled_infra_retry_cannot_dodge_its_cap(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # The probe that made this a blocker: calling an infra failure an `edge`
    # mint used to be accepted, and `max_infra_retries` never saw it.
    root = make_root(fake_store, definition)
    first = fake_store.mint_activation(root.root_id, entry_request()).activation
    run_to_close(fake_store, first.activation_id, Outcome.ERROR_RUNNER)
    with pytest.raises(CarrierIntegrityError, match="wrong §10.2 bound"):
        fake_store.mint_activation(
            root.root_id,
            entry_request(
                node=REVIEW,
                mint_reason=MintReason.EDGE,
                predecessor_activation_id=first.activation_id,
            ),
        )


def test_an_infra_retry_of_a_graph_outcome_is_refused(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # The mirror image: a clean `done` relabeled as infra noise.
    root = make_root(fake_store, definition)
    first = fake_store.mint_activation(root.root_id, entry_request()).activation
    run_to_close(fake_store, first.activation_id, Outcome.DONE)
    with pytest.raises(CarrierIntegrityError, match="wrong §10.2 bound"):
        fake_store.mint_activation(
            root.root_id,
            entry_request(
                mint_reason=MintReason.INFRA_RETRY,
                predecessor_activation_id=first.activation_id,
            ),
        )


def test_a_retry_must_re_dispatch_the_same_node(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    root = make_root(fake_store, definition)
    first = fake_store.mint_activation(root.root_id, entry_request()).activation
    run_to_close(fake_store, first.activation_id, Outcome.ERROR_RUNNER)
    with pytest.raises(CarrierIntegrityError, match="SAME node"):
        fake_store.mint_activation(
            root.root_id,
            entry_request(
                node=REVIEW,
                mint_reason=MintReason.INFRA_RETRY,
                predecessor_activation_id=first.activation_id,
            ),
        )


def test_minting_from_an_unclosed_predecessor_is_refused(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # `outcome_taken` IS the predecessor's recorded close; there is nothing to
    # read from an activation that is still running.
    root = make_root(fake_store, definition)
    first = fake_store.mint_activation(root.root_id, entry_request()).activation
    with pytest.raises(CarrierIntegrityError, match="unclosed"):
        fake_store.mint_activation(
            root.root_id,
            entry_request(
                node=REVIEW,
                mint_reason=MintReason.EDGE,
                predecessor_activation_id=first.activation_id,
            ),
        )


def test_an_unknown_predecessor_is_refused(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    root = make_root(fake_store, definition)
    with pytest.raises(CarrierIntegrityError, match="not an activation"):
        fake_store.mint_activation(
            root.root_id,
            entry_request(
                node=REVIEW,
                mint_reason=MintReason.EDGE,
                predecessor_activation_id="wf-999",
            ),
        )


def test_an_entry_mint_may_not_carry_a_predecessor(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    root = make_root(fake_store, definition)
    first = fake_store.mint_activation(root.root_id, entry_request()).activation
    with pytest.raises(CarrierIntegrityError, match="no predecessor"):
        fake_store.mint_activation(
            root.root_id,
            entry_request(predecessor_activation_id=first.activation_id),
        )


# --- intended_base_commit (§3.2) ----------------------------------------


def test_the_first_mint_bases_on_the_injected_branch_head(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    root = make_root(fake_store, definition)
    minted = fake_store.mint_activation(root.root_id, entry_request())
    assert minted.activation.metadata.intended_base_commit == BRANCH_HEAD


def test_a_rework_mint_bases_on_the_last_writing_attempts_pre_attempt_commit(
    fake_store: WorkflowStore, fake_client, definition: GraphDefinition
) -> None:
    # §3.2: the rework edge bases on `pre_attempt_commit`, NOT on anything
    # reachable through `predecessor_activation_id` — on a reject edge the
    # predecessor is the reviewer, whose base IS the rejected commit.
    root = make_root(fake_store, definition)
    first = fake_store.mint_activation(root.root_id, entry_request()).activation
    # The phase-3 supervisor records this; phase 2 only carries the field.
    fake_client._merge_metadata(
        first.activation_id,
        metadata_dict(
            first.metadata.model_copy(update={"pre_attempt_commit": PRE_ATTEMPT})
        ),
    )
    run_to_close(fake_store, first.activation_id, Outcome.DONE)
    review = fake_store.mint_activation(
        root.root_id,
        entry_request(
            node=REVIEW,
            mint_reason=MintReason.EDGE,
            predecessor_activation_id=first.activation_id,
        ),
    ).activation
    run_to_close(fake_store, review.activation_id, Outcome.REJECT)
    rework = fake_store.mint_activation(
        root.root_id,
        entry_request(
            mint_reason=MintReason.EDGE,
            predecessor_activation_id=review.activation_id,
        ),
    ).activation
    assert rework.metadata.intended_base_commit == PRE_ATTEMPT


def test_a_non_writing_node_never_reuses_a_pre_attempt_commit(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # `review` declares `writes = false`, so its base is the branch head.
    root = make_root(fake_store, definition)
    first = fake_store.mint_activation(root.root_id, entry_request()).activation
    run_to_close(fake_store, first.activation_id, Outcome.DONE)
    review = fake_store.mint_activation(
        root.root_id,
        entry_request(
            node=REVIEW,
            mint_reason=MintReason.EDGE,
            predecessor_activation_id=first.activation_id,
        ),
    ).activation
    assert review.metadata.intended_base_commit == BRANCH_HEAD


def test_without_a_branch_head_reader_the_mint_refuses(
    fake_client, definition: GraphDefinition
) -> None:
    # Fail closed: §3.2 resolves the base at mint and will not take it from
    # the caller, so a store with no way to resolve it cannot mint at all.
    store = WorkflowStore(fake_client)
    root = make_root(store, definition)
    with pytest.raises(BdConfigError, match="branch_head_reader"):
        store.mint_activation(root.root_id, entry_request())


def test_a_re_mint_of_one_key_is_the_same_bead(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # Derivation must be STABLE: the derived key has to re-find the bead a
    # crashed tick already minted (drill 1).
    root = make_root(fake_store, definition)
    first = fake_store.mint_activation(root.root_id, entry_request())
    second = fake_store.mint_activation(root.root_id, entry_request())
    assert first.created is True
    assert second.created is False
    assert first.activation.activation_id == second.activation.activation_id
    assert second.activation.metadata.lifecycle is Lifecycle.MINTED
    assert len(fake_store.reads.list_activations(root.root_id)) == 1


def test_one_mint_reads_the_instance_beads_exactly_once(
    fake_store: WorkflowStore, fake_bd, definition: GraphDefinition
) -> None:
    # The derivation, the ceiling count, the key lookup and the round count
    # all read the same fetch; a mint is not worth a bd call per predicate.
    root = make_root(fake_store, definition)
    before = fake_bd.command_count("list")
    fake_store.mint_activation(root.root_id, entry_request())
    # One instance-beads fetch plus the post-create read-after-write lookup.
    assert fake_bd.command_count("list") - before == 2
