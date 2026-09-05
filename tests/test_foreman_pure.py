"""Small pure-unit contracts for Slice C1 foreman primitives."""

import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from tests._bdio import entry_request, load_definition, make_root
from workflow_interpreter.bdio import (
    BdConfig,
    Deviation,
    Evidence,
    GateReason,
    GateState,
    Lifecycle,
    MintReason,
)
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.bounds import (
    instance_ceiling_refusal as bdio_instance_ceiling_refusal,
)
from workflow_interpreter.bdio.records import (
    ActivationRecord,
    parse_activation,
    parse_gate,
)
from workflow_interpreter.bdio.wire import BeadRecord, EventPayload, GateMetadata
from workflow_interpreter.foreman.bounds import (
    infra_retry_refusal,
    instance_ceiling_refusal,
    region_round_refusal,
    steer_refusal,
)
from workflow_interpreter.foreman.config import (
    ForemanConfig,
    load_config,
)
from workflow_interpreter.foreman.constants import EFFECTS_NODE, INSTANCE_BRANCH
from workflow_interpreter.foreman.events import EventIntent, backfill, expected_intents
from workflow_interpreter.foreman.finalize import decide
from workflow_interpreter.foreman.frontier import (
    FrontierConflict,
    FrontierViolation,
    build_frontier,
)
from workflow_interpreter.foreman.routing import (
    Route,
    RouteKind,
    abandon_target,
    exhausted,
    retry_kind,
    route,
)
from workflow_interpreter.foreman.transcript import bounded_tail
from workflow_interpreter.schema.graph_index import build_index
from workflow_interpreter.schema.loader import content_hash
from workflow_interpreter.schema.models import (
    BindsMode,
    Edge,
    FallbackRoute,
    GraphDefinition,
    Outcome,
)
from workflow_interpreter.supervisor import INSTANCE_BRANCH_REF
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.models import CompletionEvidence


@pytest.mark.parametrize(
    ("text", "limit", "expected"),
    [
        ("abc", 8, "abc"),
        ("abcdef", 3, "def"),
        ("😀", 3, ""),
        ("x", 0, ""),
        ("x", -1, ""),
        ("", 1, ""),
    ],
)
def test_bounded_tail_is_a_utf8_safe_suffix(
    text: str, limit: int, expected: str
) -> None:
    """K1b: cap emitted bytes, including the zero-limit slice trap."""
    result = bounded_tail(text, limit)
    assert result == expected
    assert len(result.encode("utf-8")) <= max(limit, 0)
    assert text.endswith(result)


def test_bounded_tail_drops_partial_astral_codepoint() -> None:
    """K1b: slicing four-byte UTF-8 cannot emit a broken codepoint."""
    assert bounded_tail("😀x", 4) == "x"
    assert bounded_tail("a😀", 5) == "a😀"


def test_bounded_tail_caps_replacement_character_emission() -> None:
    """K1b: a lenient raw decode can expand each invalid byte to three bytes."""
    result = bounded_tail("�" * 2048, 2048)
    assert len(result.encode("utf-8")) <= 2048
    assert result == "�" * (2048 // 3)


def test_event_intent_key_changes_with_outcome() -> None:
    """Events use the closed key vocabulary rather than a lossy tuple."""
    first = EventIntent(
        from_node="a", outcome=Outcome.ACCEPT, to_node="b", activation_id="x"
    )
    second = first.model_copy(update={"outcome": Outcome.REJECT})
    assert first.key_for("root") != second.key_for("root")


def test_instance_branch_constant_uses_the_supervisor_contract() -> None:
    """Foreman has one branch spelling and inherits it from supervisor."""
    assert INSTANCE_BRANCH == INSTANCE_BRANCH_REF


def test_expected_intents_recovers_an_activation_edge(
    fake_store: WorkflowStore,
) -> None:
    """An EDGE successor implies one predecessor-origin audit transition."""
    root = make_root(fake_store, load_definition())
    predecessor = fake_store.mint_activation(root.root_id, entry_request()).activation
    successor = predecessor.model_copy(
        update={
            "bead": predecessor.bead.model_copy(update={"id": "successor"}),
            "metadata": predecessor.metadata.model_copy(
                update={
                    "node": "review",
                    "mint_reason": MintReason.EDGE,
                    "predecessor_activation_id": predecessor.activation_id,
                    "outcome_taken": Outcome.DONE,
                }
            ),
        }
    )
    assert expected_intents(root, (predecessor, successor), ()) == (
        EventIntent(
            from_node="implement",
            outcome=Outcome.DONE,
            to_node="review",
            activation_id=predecessor.activation_id,
        ),
    )


def test_expected_intents_does_not_bypass_a_branch_divergence_halt(
    fake_store: WorkflowStore,
) -> None:
    """A diverged completed activation cannot synthesize a terminal event."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    diverged = activation.model_copy(
        update={
            "metadata": activation.metadata.model_copy(
                update={
                    "node": "ship",
                    "lifecycle": Lifecycle.CLOSED,
                    "outcome": Outcome.APPROVE,
                    "deviations": (
                        Deviation(
                            kind="instance_branch_diverged",
                            reason="moved",
                            recorded_at="now",
                        ),
                    ),
                }
            ),
        }
    )

    assert expected_intents(root, (diverged,), ()) == ()


def test_expected_intents_covers_gate_transition_exhaustion_and_via(
    fake_store: WorkflowStore,
) -> None:
    """Every non-terminal durable transition reconstructs its audit intent."""
    root = make_root(fake_store, load_definition())
    source = fake_store.mint_activation(root.root_id, entry_request()).activation
    via = source.model_copy(
        update={
            "metadata": source.metadata.model_copy(
                update={
                    "deviations": (
                        Deviation(
                            kind="undeclared_effects_accepted",
                            reason="ok",
                            recorded_at="now",
                            gate_id="effects-gate",
                        ),
                    )
                }
            )
        }
    )
    transition = parse_gate(
        _halt_gate(root.root_id, state=GateState.OPEN).model_copy(
            update={
                "id": "transition",
                "metadata": {
                    **_halt_gate(root.root_id, state=GateState.OPEN).metadata,
                    "gate_reason": "transition",
                    "gate_node": "ship",
                    "source_activation_id": source.activation_id,
                    "opening_outcome": "done",
                },
            }
        )
    )
    successor = source.model_copy(
        update={
            "bead": source.bead.model_copy(update={"id": "successor"}),
            "metadata": source.metadata.model_copy(
                update={
                    "node": "review",
                    "mint_reason": MintReason.EDGE,
                    "predecessor_gate_id": transition.gate_id,
                    "predecessor_activation_id": None,
                    "outcome_taken": Outcome.APPROVE,
                }
            ),
        }
    )
    exhaustion_bead = _halt_gate(root.root_id, state=GateState.OPEN).model_copy(
        update={
            "id": "exhaustion",
            "metadata": {
                **_halt_gate(root.root_id, state=GateState.OPEN).metadata,
                "gate_reason": "exhaustion",
                "gate_node": "triage",
                "source_activation_id": source.activation_id,
                "opening_outcome": "no_diff",
            },
        }
    )
    exhaustion = parse_gate(exhaustion_bead)
    intents = expected_intents(root, (via, successor), (transition, exhaustion))
    assert (
        EventIntent(
            from_node="ship",
            outcome=Outcome.APPROVE,
            to_node="review",
            activation_id="transition",
            origin="gate",
        )
        in intents
    )
    assert (
        EventIntent(
            from_node="implement",
            outcome=Outcome.DONE,
            to_node="ship",
            activation_id=source.activation_id,
            via_gate_id="effects-gate",
        )
        in intents
    )
    assert (
        EventIntent(
            from_node="implement",
            outcome=Outcome.NO_DIFF,
            to_node="triage",
            activation_id=source.activation_id,
            via_gate_id="effects-gate",
        )
        in intents
    )
    assert any(item.via_gate_id == "effects-gate" for item in intents)


def test_expected_intents_excludes_effects_gates(
    fake_store: WorkflowStore,
) -> None:
    """Effects gates are bookkeeping, never an event to the pseudo-node."""
    root = make_root(fake_store, load_definition())
    source = fake_store.mint_activation(root.root_id, entry_request()).activation
    effects = _transition_gate(
        root.root_id,
        gate_id="effects",
        source=source.activation_id,
        state=GateState.OPEN,
        gate_node=EFFECTS_NODE,
    )

    assert expected_intents(root, (source,), (parse_gate(effects),)) == ()


def test_expected_intents_suppresses_a_non_abandoned_dead_end_halt(
    fake_store: WorkflowStore,
) -> None:
    """A dead-end halt opens no event until a human abandons it."""
    root = make_root(fake_store, load_definition())
    gate = parse_gate(
        _halt_gate(root.root_id, state=GateState.CLOSED, outcome=Outcome.APPROVE)
    )
    assert expected_intents(root, (), (gate,)) == ()


def test_route_declared_task_and_fail_code_dead_end() -> None:
    """Routing honours declared edges but refuses an undeclared fail-code close."""
    definition = load_definition()
    index = build_index(definition.document, allow_test_flags=False)
    node = index.nodes["implement"]
    undeclared = node.model_copy(
        update={
            "outcomes": tuple(
                outcome
                for outcome in node.outcomes or ()
                if outcome is not Outcome.FAIL_CODE
            )
        }
    )
    assert route(index, node, Outcome.DONE).kind is RouteKind.TASK
    assert route(index, undeclared, Outcome.FAIL_CODE).kind is RouteKind.DEAD_END


def test_route_rejects_an_unused_carrier_argument() -> None:
    """Routing has no carrier input because every decision is graph-only."""
    index = build_index(load_definition().document, allow_test_flags=False)
    call = cast(Callable[..., object], route)
    with pytest.raises(TypeError):
        call(index, index.nodes["implement"], object(), Outcome.DONE)


def test_route_handles_gate_and_no_progress_branches() -> None:
    """An explicit gate edge and the breaker route through distinct branches."""
    definition = load_definition()
    index = build_index(definition.document, allow_test_flags=False)
    node = index.nodes["implement"]
    assert route(index, node, Outcome.NO_DIFF).kind is RouteKind.GATE
    assert (
        route(index, node, Outcome.DONE, no_progress=True).kind is RouteKind.NO_PROGRESS
    )
    exhausted_route = exhausted(index, node)
    assert exhausted_route == Route(kind=RouteKind.EXHAUSTED, target="triage")
    assert retry_kind(Outcome.ERROR_RUNNER) is MintReason.INFRA_RETRY
    assert retry_kind(Outcome.STEERED) is MintReason.STEER_CONTINUATION


def test_route_terminal_fallback_declared_fail_code_and_gate_refusals() -> None:
    """Route kinds distinguish terminal, fallback, declared fail-code and unsafe gates."""
    definition = load_definition()
    index = build_index(definition.document, allow_test_flags=False)
    ship = index.nodes["ship"]
    assert route(index, ship, Outcome.APPROVE).kind is RouteKind.TERMINAL
    assert route(index, ship, Outcome.REBUDGET).kind is RouteKind.FALLBACK
    declared = index.nodes["implement"].model_copy(
        update={"outcomes": (Outcome.FAIL_CODE,)}
    )
    declared_index = index.model_copy(
        update={
            "nodes": {**index.nodes, "implement": declared},
            "document": index.document.model_copy(
                update={
                    "edge": (
                        *index.edges,
                        Edge(
                            **{"from": "implement"}, on=Outcome.FAIL_CODE, to="review"
                        ),
                    )
                }
            ),
        }
    )
    assert route(declared_index, declared, Outcome.FAIL_CODE).kind is RouteKind.TASK
    gate_source = ship.model_copy(update={"outcomes": (Outcome.ACCEPT,)})
    gate_index = index.model_copy(
        update={
            "nodes": {**index.nodes, "ship": gate_source},
            "document": index.document.model_copy(
                update={
                    "edge": (
                        *index.edges,
                        Edge(**{"from": "ship"}, on=Outcome.ACCEPT, to="triage"),
                    )
                }
            ),
        }
    )
    assert route(gate_index, gate_source, Outcome.ACCEPT).kind is RouteKind.FAIL_CLOSED
    mutable = index.nodes["triage"].model_copy(update={"binds": BindsMode.MUTABLE})
    mutable_index = index.model_copy(
        update={"nodes": {**index.nodes, "triage": mutable}}
    )
    assert (
        route(mutable_index, index.nodes["implement"], Outcome.NO_DIFF).kind
        is RouteKind.FAIL_CLOSED
    )


def test_abandon_target_is_unique() -> None:
    """The terminal abandon target is derived only when graph data is unique."""
    definition = load_definition()
    assert (
        abandon_target(build_index(definition.document, allow_test_flags=False))
        == "abandoned"
    )


def test_abandon_target_refuses_none_or_multiple() -> None:
    """A terminal abandon event is safe only for one declared target."""
    definition = load_definition()
    index = build_index(definition.document, allow_test_flags=False)
    none = index.model_copy(
        update={
            "document": index.document.model_copy(
                update={
                    "edge": tuple(
                        edge for edge in index.edges if edge.on is not Outcome.ABANDON
                    )
                }
            )
        }
    )
    multiple = index.model_copy(
        update={
            "document": index.document.model_copy(
                update={
                    "edge": (
                        *index.edges,
                        Edge(**{"from": "implement"}, on=Outcome.ABANDON, to="shipped"),
                    )
                }
            )
        }
    )
    assert abandon_target(none) is None
    assert abandon_target(multiple) is None


def test_each_bound_refusal_uses_its_documented_operator() -> None:
    """§10 thresholds refuse at equality and leave a known round alone."""
    assert instance_ceiling_refusal(bead_count=2, max_total_activations=2) is not None
    assert (
        region_round_refusal(
            region="r", distinct_rounds=frozenset({1}), target_round=1, max_entries=1
        )
        is None
    )
    assert (
        region_round_refusal(
            region="r", distinct_rounds=frozenset({1}), target_round=2, max_entries=1
        )
        is not None
    )
    assert (
        infra_retry_refusal(
            node="n", round_no=1, consecutive_infra_closes=2, max_infra_retries=1
        )
        is not None
    )
    assert steer_refusal(node="n", round_no=1, steer_closes=1, max_steers=1) is not None


def test_frontier_marks_a_fresh_instance_empty(fake_store: WorkflowStore) -> None:
    """F3: no activation, live gate, or terminal event is an entry-mint frontier."""
    root = make_root(fake_store, load_definition())
    assert (
        build_frontier(root, fake_store.reads.instance_beads(root.root_id)).empty
        is True
    )


def test_frontier_marks_a_minted_activation_nonempty(fake_store: WorkflowStore) -> None:
    """The empty rule cannot re-entry-mint beside an already minted activation."""
    root = make_root(fake_store, load_definition())
    fake_store.mint_activation(root.root_id, entry_request())
    frontier = build_frontier(root, fake_store.reads.instance_beads(root.root_id))
    assert frontier.empty is False
    assert len(frontier.minted) == 1


def _halt_gate(
    root_id: str,
    *,
    state: GateState,
    outcome: Outcome | None = None,
    source: str | None = None,
) -> BeadRecord:
    metadata = GateMetadata(
        wf_root_id=root_id,
        gate_key="gate-key",
        gate_node="halt",
        outcomes=(Outcome.APPROVE, Outcome.REBUDGET, Outcome.ABANDON),
        gate_reason=GateReason.HALT,
        source_activation_id=source,
        halt_reason="halt",
        seq=1,
        state=state,
        outcome=outcome,
        verified_fingerprint="fingerprint" if outcome is not None else None,
        payload_digest="digest" if outcome is not None else None,
    )
    return BeadRecord(
        id="gate",
        title="gate",
        status="open",
        issue_type="task",
        metadata=metadata.model_dump(mode="json"),
    )


def _activation_bead(
    activation: object,
    bead_id: str,
    **updates: object,
) -> BeadRecord:
    """Copy a parsed activation into a distinct trace row for frontier tests."""
    record = cast(ActivationRecord, activation)
    return record.bead.model_copy(
        update={
            "id": bead_id,
            "metadata": record.metadata.model_copy(update=updates).model_dump(
                mode="json", exclude_none=True
            ),
        }
    )


def _transition_gate(
    root_id: str,
    *,
    gate_id: str,
    source: str | None,
    state: GateState,
    gate_node: str = "ship",
) -> BeadRecord:
    """Build a transition-shaped row without a transport write."""
    metadata = GateMetadata(
        wf_root_id=root_id,
        gate_key=f"gate-{gate_id}",
        gate_node=gate_node,
        outcomes=(Outcome.APPROVE,),
        gate_reason=GateReason.TRANSITION,
        source_activation_id=source,
        opening_outcome=Outcome.DONE,
        seq=1,
        state=state,
        outcome=Outcome.APPROVE if state is GateState.CLOSED else None,
        verified_fingerprint="fingerprint" if state is GateState.CLOSED else None,
        payload_digest="digest" if state is GateState.CLOSED else None,
    )
    return BeadRecord(
        id=gate_id,
        title=gate_id,
        status="open",
        issue_type="task",
        metadata=metadata.model_dump(mode="json", exclude_none=True),
    )


def _closed_activation(store: WorkflowStore, root_id: str) -> ActivationRecord:
    """Create a completed entry activation for pure frontier fixtures."""
    activation = store.mint_activation(root_id, entry_request()).activation
    return store.close_activation(
        activation.activation_id, Outcome.DONE, evidence=Evidence()
    )


def test_frontier_consumption_table_keeps_only_the_unconsumed_head(
    fake_store: WorkflowStore,
) -> None:
    """Every activation/gate predecessor form consumes exactly its source row."""
    root = make_root(fake_store, load_definition())
    source = _closed_activation(fake_store, root.root_id)
    successor = _activation_bead(
        source,
        "successor",
        node="review",
        mint_reason=MintReason.EDGE,
        predecessor_activation_id=source.activation_id,
        outcome_taken=Outcome.DONE,
        lifecycle=Lifecycle.MINTED,
        outcome=None,
        evidence=None,
    )
    assert build_frontier(root, (source.bead, successor)).head is None

    transition = _transition_gate(
        root.root_id,
        gate_id="open-transition",
        source=source.activation_id,
        state=GateState.OPEN,
    )
    assert build_frontier(root, (source.bead, transition)).head is None

    halt = _halt_gate(
        root.root_id,
        state=GateState.CLOSED,
        outcome=Outcome.APPROVE,
        source=source.activation_id,
    )
    assert build_frontier(root, (source.bead, halt)).head_gate is not None


def test_frontier_effects_gate_cannot_consume_its_source(
    fake_store: WorkflowStore,
) -> None:
    """Effects gates are bookkeeping, never a transition that consumes routing."""
    root = make_root(fake_store, load_definition())
    source = _closed_activation(fake_store, root.root_id)
    effects = _transition_gate(
        root.root_id,
        gate_id="effects",
        source=source.activation_id,
        state=GateState.OPEN,
        gate_node=EFFECTS_NODE,
    )
    frontier = build_frontier(root, (source.bead, effects))
    assert frontier.head_activation is not None
    assert frontier.head_activation.activation_id == source.activation_id


def test_frontier_terminal_and_gate_successors_consume_their_origins(
    fake_store: WorkflowStore,
) -> None:
    """Terminal audit rows and activation gate predecessors leave no second head."""
    root = make_root(fake_store, load_definition())
    source = _closed_activation(fake_store, root.root_id)
    terminal = BeadRecord(
        id="terminal",
        title="terminal",
        status="open",
        issue_type="event",
        metadata={"wf_kind": "event"},
        payload=EventPayload(
            **{"from": "implement"},
            outcome=Outcome.DONE,
            to="shipped",
            activation_id=source.activation_id,
            seq=2,
            actor="actor",
            origin="activation",
        ).model_dump_json(by_alias=True),
    )
    assert build_frontier(root, (source.bead, terminal)).head is None

    gate = _transition_gate(
        root.root_id,
        gate_id="gate",
        source=None,
        state=GateState.CLOSED,
    )
    successor = _activation_bead(
        source,
        "gate-successor",
        node="review",
        mint_reason=MintReason.EDGE,
        predecessor_activation_id=None,
        predecessor_gate_id="gate",
        outcome_taken=Outcome.APPROVE,
        lifecycle=Lifecycle.MINTED,
        outcome=None,
        evidence=None,
    )
    assert build_frontier(root, (gate, successor)).head is None


def test_frontier_candidates_use_unconsumed_completed_non_effects_records(
    fake_store: WorkflowStore,
) -> None:
    """Candidate heads exclude consumed, incomplete, dead-end and effects rows."""
    root = make_root(fake_store, load_definition())
    source = _closed_activation(fake_store, root.root_id)
    successor = _activation_bead(
        source,
        "completed-successor",
        node="review",
        mint_reason=MintReason.EDGE,
        predecessor_activation_id=source.activation_id,
        outcome_taken=Outcome.DONE,
        lifecycle=Lifecycle.CLOSED,
        outcome=Outcome.DONE,
    )
    frontier = build_frontier(root, (source.bead, successor))
    assert frontier.head_activation is not None
    assert frontier.head_activation.activation_id == "completed-successor"

    incomplete = _activation_bead(
        source, "incomplete", lifecycle=Lifecycle.MINTED, outcome=None, evidence=None
    )
    assert build_frontier(root, (incomplete,)).head is None

    effects = _transition_gate(
        root.root_id,
        gate_id="closed-effects",
        source=None,
        state=GateState.CLOSED,
        gate_node=EFFECTS_NODE,
    )
    assert build_frontier(root, (effects,)).head is None

    open_gate = _transition_gate(
        root.root_id, gate_id="open", source=None, state=GateState.OPEN
    )
    assert build_frontier(root, (open_gate,)).head is None

    closed_gate = _transition_gate(
        root.root_id, gate_id="closed", source=None, state=GateState.CLOSED
    )
    assert build_frontier(root, (closed_gate,)).head_gate is not None


def test_frontier_rejects_unverified_closes_ignores_superseded_and_conflicts(
    fake_store: WorkflowStore,
) -> None:
    """Unsafe closed rows fail loud while superseded rows cannot route again."""
    root = make_root(fake_store, load_definition())
    source = _closed_activation(fake_store, root.root_id)
    superseded = _activation_bead(
        source,
        "superseded",
        lifecycle=Lifecycle.MINTED,
        outcome=None,
        superseded_by="winner",
    )
    superseded_frontier = build_frontier(root, (superseded,))
    assert superseded_frontier.head is None
    assert superseded_frontier.minted == ()

    unverified = _transition_gate(
        root.root_id, gate_id="unverified", source=None, state=GateState.CLOSED
    ).model_copy(
        update={
            "metadata": {
                **_transition_gate(
                    root.root_id,
                    gate_id="unverified",
                    source=None,
                    state=GateState.CLOSED,
                ).metadata,
                "verified_fingerprint": None,
            }
        }
    )
    with pytest.raises(FrontierViolation, match="gate_close_unverified"):
        build_frontier(root, (unverified,))

    first = _transition_gate(
        root.root_id, gate_id="first", source=None, state=GateState.CLOSED
    )
    second = _transition_gate(
        root.root_id, gate_id="second", source=None, state=GateState.CLOSED
    )
    with pytest.raises(FrontierConflict, match="more than one"):
        build_frontier(root, (first, second))


@pytest.mark.parametrize(
    ("state", "outcome", "source", "empty"),
    [
        (GateState.CLOSED, Outcome.APPROVE, None, True),
        (GateState.OPEN, None, None, False),
        (GateState.CLOSED, Outcome.APPROVE, "source", False),
        (GateState.CLOSED, Outcome.REBUDGET, "source", False),
        (GateState.CLOSED, Outcome.ABANDON, None, False),
    ],
)
def test_frontier_empty_gate_variants(
    fake_store: WorkflowStore,
    state: GateState,
    outcome: Outcome | None,
    source: str | None,
    empty: bool,
) -> None:
    """F3 keeps each source-less/living/abandoned halt shape distinct."""
    root = make_root(fake_store, load_definition())
    frontier = build_frontier(
        root, (_halt_gate(root.root_id, state=state, outcome=outcome, source=source),)
    )
    assert frontier.empty is empty
    if source is not None:
        assert frontier.head_gate is not None
    if outcome is Outcome.ABANDON:
        assert frontier.abandoned_halt is not None


def test_frontier_head_is_the_public_single_head(fake_store: WorkflowStore) -> None:
    """Consumers do not need to branch on two internal head fields."""
    root = make_root(fake_store, load_definition())
    gate = _halt_gate(
        root.root_id, state=GateState.CLOSED, outcome=Outcome.APPROVE, source="source"
    )
    frontier = build_frontier(root, (gate,))
    assert frontier.head is frontier.head_gate


def test_expected_intents_includes_closed_abandoned_halt(
    fake_store: WorkflowStore,
) -> None:
    """A closed abandonment is an audit event even without a successor mint."""
    root = make_root(fake_store, load_definition())
    gate = parse_gate(
        _halt_gate(root.root_id, state=GateState.CLOSED, outcome=Outcome.ABANDON)
    )
    intents = expected_intents(root, (), (gate,))
    assert intents[0].from_node == "halt"
    assert intents[0].outcome is Outcome.ABANDON


@pytest.mark.parametrize(
    ("state", "fingerprint", "digest"),
    [
        (GateState.OPEN, "fingerprint", "digest"),
        (GateState.CLOSED, None, "digest"),
        (GateState.CLOSED, "fingerprint", None),
    ],
)
def test_expected_intents_excludes_open_or_unverified_abandon_halts(
    fake_store: WorkflowStore,
    state: GateState,
    fingerprint: str | None,
    digest: str | None,
) -> None:
    """Only a verified close is an abandonment decision worth auditing."""
    root = make_root(fake_store, load_definition())
    bead = _halt_gate(root.root_id, state=state, outcome=Outcome.ABANDON)
    gate = parse_gate(
        bead.model_copy(
            update={
                "metadata": {
                    **bead.metadata,
                    "verified_fingerprint": fingerprint,
                    "payload_digest": digest,
                }
            }
        )
    )
    assert expected_intents(root, (), (gate,)) == ()


def test_frontier_terminal_event_never_reopens_an_empty_instance(
    fake_store: WorkflowStore,
) -> None:
    """A terminal event is consumption, even if no activation remains."""
    root = make_root(fake_store, load_definition())
    event = BeadRecord(
        id="event",
        title="event",
        status="open",
        issue_type="event",
        metadata={"wf_kind": "event"},
        payload=EventPayload(
            **{"from": "halt"},
            outcome=Outcome.ABANDON,
            to="abandoned",
            activation_id="gate",
            seq=1,
            actor="actor",
            origin="gate",
        ).model_dump_json(by_alias=True),
    )
    frontier = build_frontier(root, (event,))
    assert frontier.terminal is True
    assert frontier.empty is False


def test_frontier_consumes_an_abandoned_halt_only_at_its_terminal_event(
    fake_store: WorkflowStore,
) -> None:
    """The durable abandon marker disappears only after its terminal audit row."""
    root = make_root(fake_store, load_definition())
    gate = _halt_gate(root.root_id, state=GateState.CLOSED, outcome=Outcome.ABANDON)
    event = BeadRecord(
        id="event",
        title="event",
        status="open",
        issue_type="event",
        metadata={"wf_kind": "event"},
        payload=EventPayload(
            **{"from": "halt"},
            outcome=Outcome.ABANDON,
            to="abandoned",
            activation_id="gate",
            seq=1,
            actor="actor",
            origin="gate",
        ).model_dump_json(by_alias=True),
    )
    frontier = build_frontier(root, (gate, event))
    assert frontier.terminal is True
    assert frontier.abandoned_halt is None


def test_frontier_does_not_consume_a_non_terminal_event(
    fake_store: WorkflowStore,
) -> None:
    """Only terminal audit events consume a completed routing head."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    fake_store.close_activation(
        activation.activation_id, Outcome.DONE, evidence=Evidence()
    )
    event = BeadRecord(
        id="event",
        title="event",
        status="open",
        issue_type="event",
        metadata={"wf_kind": "event"},
        payload=EventPayload(
            **{"from": "implement"},
            outcome=Outcome.DONE,
            to="review",
            activation_id=activation.activation_id,
            seq=1,
            actor="actor",
            origin="activation",
        ).model_dump_json(by_alias=True),
    )
    frontier = build_frontier(
        root, (*fake_store.reads.instance_beads(root.root_id), event)
    )
    assert frontier.head_activation is not None
    assert frontier.head_activation.activation_id == activation.activation_id


def _undeclared_fail_code(definition: GraphDefinition) -> GraphDefinition:
    """The fixture with `implement` no longer declaring `fail_code`.

    Slice A made `fail_code` a declared outcome of the shipped graph, so the
    dead-end clause now needs a graph that withholds it.
    """
    document = definition.document.model_copy(
        update={
            "node": tuple(
                node.model_copy(
                    update={
                        "outcomes": tuple(
                            outcome
                            for outcome in node.outcomes or ()
                            if outcome is not Outcome.FAIL_CODE
                        )
                    }
                )
                if node.name == "implement"
                else node
                for node in definition.document.node
            ),
            "edge": tuple(
                edge
                for edge in definition.document.edge
                if not (edge.from_node == "implement" and edge.on is Outcome.FAIL_CODE)
            ),
        }
    )
    return definition.model_copy(
        update={"document": document, "content_hash": content_hash(document)}
    )


@pytest.mark.parametrize(
    ("outcome", "evidence", "kinds", "expected"),
    [
        (Outcome.FAIL_CODE, Evidence(claimed_outcome=Outcome.DONE), (), "fail-code"),
        (Outcome.DONE, Evidence(), ("instance_branch_diverged",), "branch-diverged"),
        (
            Outcome.ERROR_TRANSPORT,
            Evidence(),
            ("precondition_refused",),
            "precondition-refused",
        ),
        (
            Outcome.ERROR_TRANSPORT,
            Evidence(),
            ("inputs_unavailable",),
            "inputs-unavailable",
        ),
    ],
)
def test_frontier_classifies_every_dead_end_kind(
    fake_store: WorkflowStore,
    outcome: Outcome,
    evidence: Evidence,
    kinds: tuple[str, ...],
    expected: str,
) -> None:
    """Dead ends win before ordinary retry handling can consume them."""
    root = make_root(fake_store, _undeclared_fail_code(load_definition()))
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    fake_store.close_activation(
        activation.activation_id,
        outcome,
        evidence=evidence,
        deviations=tuple(
            Deviation(kind=kind, reason=kind, recorded_at="now") for kind in kinds
        ),
    )
    frontier = build_frontier(root, fake_store.reads.instance_beads(root.root_id))
    assert frontier.dead_end is not None
    assert frontier.dead_end.kind.value == expected


def test_frontier_excludes_a_dead_end_from_routing_heads(
    fake_store: WorkflowStore,
) -> None:
    """An undeclared fail-code close must stop at its halt rather than route."""
    root = make_root(fake_store, _undeclared_fail_code(load_definition()))
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    fake_store.close_activation(
        activation.activation_id,
        Outcome.FAIL_CODE,
        evidence=Evidence(claimed_outcome=Outcome.DONE),
    )

    frontier = build_frontier(root, fake_store.reads.instance_beads(root.root_id))

    assert frontier.dead_end is not None
    assert frontier.head is None


def test_frontier_does_not_dead_end_a_declared_fail_code(
    fake_store: WorkflowStore,
) -> None:
    """A verified fail-code is ordinary routing only when the node declares it."""
    root = make_root(fake_store, load_definition())
    document = root.definition.document.model_copy(
        update={
            "node": tuple(
                node.model_copy(
                    update={"outcomes": (*(node.outcomes or ()), Outcome.FAIL_CODE)}
                )
                if node.name == "implement"
                else node
                for node in root.definition.document.node
            )
        }
    )
    declared_root = root.model_copy(
        update={"definition": root.definition.model_copy(update={"document": document})}
    )
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    fake_store.close_activation(
        activation.activation_id,
        Outcome.FAIL_CODE,
        evidence=Evidence(claimed_outcome=Outcome.FAIL_CODE),
    )
    frontier = build_frontier(
        declared_root, fake_store.reads.instance_beads(root.root_id)
    )
    assert frontier.dead_end is None
    assert frontier.head is not None


@pytest.mark.parametrize("claimed_outcome", [Outcome.DONE, Outcome.FAIL_CODE])
@pytest.mark.parametrize("declares_fail_code", [True, False])
def test_frontier_fail_code_depends_only_on_the_declaration(
    fake_store: WorkflowStore,
    declares_fail_code: bool,
    claimed_outcome: Outcome,
) -> None:
    """The claim no longer decides: only the node's own vocabulary does."""
    definition = load_definition()
    root = make_root(
        fake_store,
        definition if declares_fail_code else _undeclared_fail_code(definition),
    )
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    fake_store.close_activation(
        activation.activation_id,
        Outcome.FAIL_CODE,
        evidence=Evidence(claimed_outcome=claimed_outcome),
    )
    frontier = build_frontier(root, fake_store.reads.instance_beads(root.root_id))
    assert (frontier.dead_end is None) is declares_fail_code


@pytest.mark.parametrize(
    ("evidence", "node_name"),
    [
        (None, "implement"),
        (Evidence(claimed_outcome=Outcome.DONE), "implement"),
        (Evidence(claimed_outcome=Outcome.FAIL_CODE), "missing"),
        (Evidence(claimed_outcome=Outcome.FAIL_CODE), "implement"),
    ],
)
def test_frontier_fail_code_requires_every_dead_end_clause(
    fake_store: WorkflowStore,
    evidence: Evidence | None,
    node_name: str,
) -> None:
    """Fail-code routing requires completion and a node that declares it.

    `missing` covers the unknown-node clause; the rest cover a node whose
    vocabulary withholds `fail_code`, whatever the runner claimed.
    """
    root = make_root(fake_store, _undeclared_fail_code(load_definition()))
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    fake_store.close_activation(
        activation.activation_id, Outcome.FAIL_CODE, evidence=evidence
    )
    bead = _activation_bead(
        fake_store.reads.load_activation(activation.activation_id),
        activation.activation_id,
        node=node_name,
        evidence=evidence,
    )
    frontier = build_frontier(root, (bead,))
    assert frontier.dead_end is not None


def test_frontier_exhaustion_gate_consumes_its_completed_source(
    fake_store: WorkflowStore,
) -> None:
    """An exhaustion gate is a consumption edge, not a second routing head."""
    root = make_root(fake_store, load_definition())
    source = _closed_activation(fake_store, root.root_id)
    gate = _transition_gate(
        root.root_id,
        gate_id="exhaustion",
        source=source.activation_id,
        state=GateState.OPEN,
    ).model_copy(
        update={
            "metadata": {
                **_transition_gate(
                    root.root_id,
                    gate_id="exhaustion",
                    source=source.activation_id,
                    state=GateState.OPEN,
                ).metadata,
                "gate_reason": GateReason.EXHAUSTION.value,
            }
        }
    )
    assert build_frontier(root, (source.bead, gate)).head is None


@pytest.mark.parametrize("field", ["outcome", "verified_fingerprint", "payload_digest"])
def test_frontier_refuses_each_missing_closed_gate_proof(
    fake_store: WorkflowStore, field: str
) -> None:
    """A closed gate needs all three proof fields independently."""
    root = make_root(fake_store, load_definition())
    gate = _transition_gate(
        root.root_id, gate_id="closed", source=None, state=GateState.CLOSED
    )
    with pytest.raises(FrontierViolation, match="gate_close_unverified"):
        build_frontier(
            root,
            (gate.model_copy(update={"metadata": {**gate.metadata, field: None}}),),
        )


def test_finalize_blocks_undeclared_effects(fake_store: WorkflowStore) -> None:
    """Finalization keeps wrapper evidence's effects block durable and visible."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    completion = CompletionEvidence(
        outcome=Outcome.DONE,
        claimed_outcome=Outcome.DONE,
        evidence=Evidence(undeclared_effects=("outside.txt",)),
    )
    decision = decide(root.index.nodes["implement"], activation, completion)
    assert decision.blocked is True
    assert decision.claimed_outcome is Outcome.DONE


def test_finalize_preserves_an_unblocked_completion_and_deviations(
    fake_store: WorkflowStore,
) -> None:
    """A clean completion is returned unchanged rather than reinterpreted."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    completion = CompletionEvidence(
        outcome=Outcome.FAIL_PLAN,
        claimed_outcome=Outcome.FAIL_PLAN,
        evidence=Evidence(),
    )
    decision = decide(root.index.nodes["implement"], activation, completion)
    assert decision.blocked is False
    assert decision.outcome is Outcome.FAIL_PLAN
    assert decision.claimed_outcome is Outcome.FAIL_PLAN
    assert decision.deviations == ()


def test_finalize_preserves_the_claim_and_adds_no_prior_deviation(
    fake_store: WorkflowStore,
) -> None:
    """Finalization does not replace a runner claim, nor re-return prior deviations.

    `decide` returns what THIS close ADDS and nothing else, because
    `WorkflowStore.close_activation` stores `(*record.metadata.deviations,
    *deviations)` — returning the carried ones made the store record each of
    them twice (cr-n2z.9). Nothing is lost: they are already on the record, and
    the merge keeps them ahead of whatever this close adds.
    """
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation = activation.model_copy(
        update={
            "metadata": activation.metadata.model_copy(
                update={
                    "deviations": (
                        Deviation(kind="prior", reason="kept", recorded_at="now"),
                    )
                }
            )
        }
    )
    completion = CompletionEvidence(
        outcome=Outcome.FAIL_PLAN,
        claimed_outcome=Outcome.DONE,
        evidence=Evidence(),
    )
    decision = decide(root.index.nodes["implement"], activation, completion)
    assert decision.claimed_outcome is Outcome.DONE
    assert decision.outcome is Outcome.FAIL_PLAN
    assert decision.deviations == ()


def test_config_derives_wrapper_root_from_the_real_repo_path(tmp_path: Path) -> None:
    """Distinct repositories cannot share their observation cache by accident."""
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    repo.mkdir()
    wrapper_root = (
        home / hashlib.sha256(str(repo.resolve()).encode("utf-8")).hexdigest()[:16]
    )
    config = ForemanConfig(
        repo_root=repo,
        wrapper_home=home,
        bd=BdConfig(workspace=tmp_path / "bd", actor="test"),
        host="host",
        actor="test",
        supervisor=SupervisorConfig(
            repo_root=repo, wrapper_root=wrapper_root, host="host"
        ),
    )
    assert config.wrapper_root.parent == home
    assert config.wrapper_root != home
    sibling = tmp_path / "other" / "repo"
    sibling.mkdir(parents=True)
    sibling_wrapper = (
        home / hashlib.sha256(str(sibling.resolve()).encode("utf-8")).hexdigest()[:16]
    )
    sibling_config = ForemanConfig(
        repo_root=sibling,
        wrapper_home=home,
        bd=BdConfig(workspace=tmp_path / "other-bd", actor="test"),
        host="host",
        actor="test",
        supervisor=SupervisorConfig(
            repo_root=sibling, wrapper_root=sibling_wrapper, host="host"
        ),
    )
    assert sibling_config.wrapper_root != config.wrapper_root


def test_route_pins_declared_fail_code_retry_and_distinct_fallbacks() -> None:
    """A declared fail-code takes its edge; retries and fallback scopes stay distinct."""
    definition = load_definition()
    document = definition.document.model_copy(
        update={
            "node": tuple(
                node.model_copy(update={"fallback": FallbackRoute(to="abandoned")})
                if node.name == "implement"
                else node
                for node in definition.document.node
            ),
            "region": tuple(
                region.model_copy(update={"on_exhausted": "shipped"})
                for region in definition.document.region
            ),
        }
    )
    index = build_index(document, allow_test_flags=False)
    node = index.nodes["implement"]
    assert route(index, node, Outcome.FAIL_CODE) == Route(
        kind=RouteKind.TASK, target="implement"
    )
    assert retry_kind(Outcome.ERROR_TRANSPORT) is MintReason.INFRA_RETRY
    assert exhausted(index, node).target == "shipped"
    assert route(index, node, Outcome.ACCEPT).target == "abandoned"


def test_exhausted_uses_the_declared_fallback_when_no_region_exit_exists() -> None:
    """The non-region arm returns the graph fallback, not an arbitrary route."""
    index = build_index(load_definition().document, allow_test_flags=False)
    node = index.nodes["implement"].model_copy(
        update={"region": None, "fallback": None}
    )
    assert exhausted(index, node) == Route(kind=RouteKind.EXHAUSTED, target="triage")


def test_events_ignore_non_edge_retries_and_backfill_once(
    fake_store: WorkflowStore,
) -> None:
    """Only EDGE successors emit audit events, with an idempotent allocation."""
    root = make_root(fake_store, load_definition())
    source = _closed_activation(fake_store, root.root_id)
    retry = source.model_copy(
        update={
            "bead": source.bead.model_copy(update={"id": "retry"}),
            "metadata": source.metadata.model_copy(
                update={"mint_reason": MintReason.INFRA_RETRY}
            ),
        }
    )
    assert expected_intents(root, (source, retry), ()) == ()
    intent = EventIntent(
        from_node="implement",
        outcome=Outcome.DONE,
        to_node="review",
        activation_id=source.activation_id,
    )
    assert (
        backfill(fake_store, root.root_id, (intent,), actor="actor", existing=set())
        == 1
    )
    assert (
        backfill(
            fake_store,
            root.root_id,
            (intent,),
            actor="actor",
            existing={intent.key_for(root.root_id)},
        )
        == 0
    )


def test_events_ignore_a_retry_that_otherwise_looks_like_an_edge(
    fake_store: WorkflowStore,
) -> None:
    """The mint reason, independently of predecessor data, gates audit events."""
    root = make_root(fake_store, load_definition())
    source = _closed_activation(fake_store, root.root_id)
    retry = parse_activation(
        _activation_bead(
            source,
            "retry",
            node="review",
            mint_reason=MintReason.INFRA_RETRY,
            predecessor_activation_id=source.activation_id,
            outcome_taken=Outcome.DONE,
            lifecycle=Lifecycle.MINTED,
            outcome=None,
            evidence=None,
        )
    )
    assert expected_intents(root, (source, retry), ()) == ()


def test_load_config_constructs_the_injected_models(tmp_path: Path) -> None:
    """Loading comes from its selected file, not ambient process state."""
    repo = tmp_path / "repo"
    repo.mkdir()
    wrapper_root = (
        tmp_path
        / "home"
        / hashlib.sha256(str(repo.resolve()).encode("utf-8")).hexdigest()[:16]
    )
    path = tmp_path / "foreman.toml"
    path.write_text(
        f'''repo_root = "{repo}"
wrapper_home = "{tmp_path / "home"}"
host = "host"
actor = "actor"

[bd]
workspace = "{tmp_path / "bd"}"
actor = "actor"

[supervisor]
repo_root = "{repo}"
wrapper_root = "{wrapper_root}"
host = "host"
''',
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.actor == "actor"
    assert config.config_path == path


@pytest.mark.parametrize("field", ["from_node", "outcome", "to_node"])
def test_event_intent_key_retains_each_transition_component(field: str) -> None:
    """The event key changes for each component of its transition identity."""
    first = EventIntent(
        from_node="from", outcome=Outcome.ACCEPT, to_node="to", activation_id="x"
    )
    replacement: object = {
        "from_node": "other-from",
        "outcome": Outcome.REJECT,
        "to_node": "other-to",
    }[field]
    assert first.key_for("root") != first.model_copy(
        update={field: replacement}
    ).key_for("root")


def test_expected_intents_carries_the_activation_edge_via_gate(
    fake_store: WorkflowStore,
) -> None:
    """An activation edge preserves only its undeclared-effects approval gate."""
    root = make_root(fake_store, load_definition())
    predecessor = fake_store.mint_activation(root.root_id, entry_request()).activation
    predecessor = predecessor.model_copy(
        update={
            "metadata": predecessor.metadata.model_copy(
                update={
                    "deviations": (
                        Deviation(
                            kind="unrelated",
                            reason="ignore",
                            recorded_at="now",
                            gate_id="wrong-gate",
                        ),
                        Deviation(
                            kind="undeclared_effects_accepted",
                            reason="approved",
                            recorded_at="now",
                            gate_id="effects-gate",
                        ),
                    )
                }
            )
        }
    )
    successor = predecessor.model_copy(
        update={
            "bead": predecessor.bead.model_copy(update={"id": "successor"}),
            "metadata": predecessor.metadata.model_copy(
                update={
                    "node": "review",
                    "mint_reason": MintReason.EDGE,
                    "predecessor_activation_id": predecessor.activation_id,
                    "outcome_taken": Outcome.DONE,
                }
            ),
        }
    )
    assert expected_intents(root, (predecessor, successor), ()) == (
        EventIntent(
            from_node="implement",
            outcome=Outcome.DONE,
            to_node="review",
            activation_id=predecessor.activation_id,
            via_gate_id="effects-gate",
        ),
    )


def test_expected_intents_ignores_a_sourced_halt_transition_shape(
    fake_store: WorkflowStore,
) -> None:
    """Only transition and exhaustion gates produce activation-origin events."""
    root = make_root(fake_store, load_definition())
    source = fake_store.mint_activation(root.root_id, entry_request()).activation
    raw_halt = _halt_gate(
        root.root_id,
        state=GateState.CLOSED,
        outcome=Outcome.APPROVE,
        source=source.activation_id,
    )
    halt = parse_gate(
        raw_halt.model_copy(
            update={
                "metadata": {
                    **raw_halt.metadata,
                    "opening_outcome": Outcome.DONE.value,
                }
            }
        )
    )
    assert expected_intents(root, (source,), (halt,)) == ()


def test_backfill_refetches_the_sequence_for_each_missing_intent(
    fake_store: WorkflowStore,
) -> None:
    """Each event allocation sees the prior append before selecting its sequence."""
    root = make_root(fake_store, load_definition())
    intents = (
        EventIntent(
            from_node="implement",
            outcome=Outcome.DONE,
            to_node="review",
            activation_id="one",
        ),
        EventIntent(
            from_node="review",
            outcome=Outcome.ACCEPT,
            to_node="ship",
            activation_id="two",
        ),
    )
    assert (
        backfill(fake_store, root.root_id, intents, actor="actor", existing=set()) == 2
    )
    events = [
        row
        for row in fake_store.reads.instance_beads(root.root_id)
        if row.metadata.get("wf_kind") == "event"
    ]
    assert len(events) == 2
    assert (
        cast(int, events[1].metadata["seq"]) == cast(int, events[0].metadata["seq"]) + 1
    )


@pytest.mark.parametrize(
    ("state", "gate_reason"),
    [(GateState.OPEN, GateReason.HALT), (GateState.CLOSED, GateReason.TRANSITION)],
)
def test_frontier_abandoned_halt_requires_closed_halt(
    fake_store: WorkflowStore, state: GateState, gate_reason: GateReason
) -> None:
    """An abandon outcome alone is not an abandoned halt decision."""
    root = make_root(fake_store, load_definition())
    raw_gate = _halt_gate(root.root_id, state=state, outcome=Outcome.ABANDON)
    gate = raw_gate.model_copy(
        update={"metadata": {**raw_gate.metadata, "gate_reason": gate_reason.value}}
    )
    assert build_frontier(root, (gate,)).abandoned_halt is None


def test_frontier_does_not_route_an_abandoned_halt_as_a_head(
    fake_store: WorkflowStore,
) -> None:
    """An abandoned halt waits for its terminal event rather than re-minting work."""
    root = make_root(fake_store, load_definition())
    halt = _halt_gate(
        root.root_id,
        state=GateState.CLOSED,
        outcome=Outcome.ABANDON,
        source="dead-end",
    )
    frontier = build_frontier(root, (halt,))
    assert frontier.abandoned_halt is not None
    assert frontier.head is None


def test_frontier_exposes_halt_and_lifecycle_partitions(
    fake_store: WorkflowStore,
) -> None:
    """Consumers can observe every pending lifecycle and both halt partitions."""
    root = make_root(fake_store, load_definition())
    source = fake_store.mint_activation(root.root_id, entry_request()).activation
    rows = (
        _activation_bead(source, "minted", lifecycle=Lifecycle.MINTED),
        _activation_bead(source, "dispatched", lifecycle=Lifecycle.DISPATCHED),
        _activation_bead(source, "exit", lifecycle=Lifecycle.EXIT_RECORDED),
        _activation_bead(source, "evidence", lifecycle=Lifecycle.EVIDENCE_RECORDED),
        _halt_gate(root.root_id, state=GateState.OPEN),
        _transition_gate(
            root.root_id, gate_id="decided", source=None, state=GateState.CLOSED
        ),
    )
    frontier = build_frontier(root, rows)
    assert tuple(item.activation_id for item in frontier.minted) == ("minted",)
    assert tuple(item.activation_id for item in frontier.dispatched) == ("dispatched",)
    assert tuple(item.activation_id for item in frontier.exit_recorded) == ("exit",)
    assert tuple(item.activation_id for item in frontier.evidence_recorded) == (
        "evidence",
    )
    assert frontier.open_halt is not None
    assert tuple(item.gate_id for item in frontier.decided_gates) == ("decided",)


def test_frontier_ignores_a_fail_code_that_is_not_completed(
    fake_store: WorkflowStore,
) -> None:
    """A fail-code cannot become a dead end until its activation is completed."""
    root = make_root(fake_store, load_definition())
    source = fake_store.mint_activation(root.root_id, entry_request()).activation
    incomplete = _activation_bead(
        source,
        "not-completed",
        lifecycle=Lifecycle.DISPATCHED,
        outcome=Outcome.FAIL_CODE,
        evidence=Evidence(claimed_outcome=Outcome.DONE),
    )
    assert build_frontier(root, (incomplete,)).dead_end is None


def test_frontier_forgets_a_dead_end_consumed_by_an_approved_halt(
    fake_store: WorkflowStore,
) -> None:
    """A re-minted, approved dead end cannot open a second halt loop."""
    root = make_root(fake_store, load_definition())
    source = fake_store.mint_activation(root.root_id, entry_request()).activation
    source = fake_store.close_activation(
        source.activation_id,
        Outcome.FAIL_CODE,
        evidence=Evidence(claimed_outcome=Outcome.DONE),
    )
    halt = _halt_gate(
        root.root_id,
        state=GateState.CLOSED,
        outcome=Outcome.APPROVE,
        source=source.activation_id,
    )
    remint = _activation_bead(
        source,
        "remint",
        lifecycle=Lifecycle.MINTED,
        outcome=None,
        evidence=None,
        predecessor_gate_id="gate",
        predecessor_activation_id=None,
        mint_reason=MintReason.EDGE,
        outcome_taken=Outcome.APPROVE,
    )
    assert build_frontier(root, (source.bead, halt, remint)).dead_end is None


def test_route_requires_a_declared_fail_code() -> None:
    """An undeclared fail-code is a dead end, not a fallback."""
    index = build_index(load_definition().document, allow_test_flags=False)
    node = index.nodes["implement"]

    result = route(
        index,
        node.model_copy(update={"outcomes": (Outcome.DONE,)}),
        Outcome.FAIL_CODE,
    )
    assert result.kind is RouteKind.DEAD_END


def test_exhausted_prefers_the_node_fallback_over_the_document_fallback() -> None:
    """The node fallback is a distinct contract from the document fallback."""
    index = build_index(load_definition().document, allow_test_flags=False)
    node = index.nodes["implement"].model_copy(
        update={"region": None, "fallback": FallbackRoute(to="abandoned")}
    )
    assert exhausted(index, node) == Route(kind=RouteKind.EXHAUSTED, target="abandoned")


def test_foreman_ceiling_predicate_is_the_bdio_predicate() -> None:
    """The foreman boundary re-exports, rather than re-wraps, the shared rule."""
    assert instance_ceiling_refusal is bdio_instance_ceiling_refusal
