"""Pure reconstruction and idempotent backfill of transition events."""

from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import (
    ActivationRecord,
    EventPayload,
    GateReason,
    GateRecord,
    GateState,
    MintReason,
    WorkflowStore,
)
from workflow_interpreter.bdio.constants import (
    DEVIATION_INPUTS_UNAVAILABLE,
    DEVIATION_INSTANCE_BRANCH_DIVERGED,
    DEVIATION_PRECONDITION_REFUSED,
    DEVIATION_UNDECLARED_EFFECTS_ACCEPTED,
)
from workflow_interpreter.bdio.keys import event_key
from workflow_interpreter.bdio.reads import next_seq
from workflow_interpreter.bdio.records import RootRecord
from workflow_interpreter.foreman.constants import EFFECTS_NODE, HALT_NODE
from workflow_interpreter.foreman.routing import RouteKind, abandon_target, route
from workflow_interpreter.schema.graph_index import GraphIndex
from workflow_interpreter.schema.models import Outcome


class EventIntent(BaseModel):
    """One trace transition that must exist eventually in the audit projection."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    from_node: str
    outcome: Outcome
    to_node: str
    activation_id: str
    origin: Literal["activation", "gate"] = "activation"
    via_gate_id: str | None = None

    def key_for(self, root_id: str) -> str:
        """Return this intent's deterministic event key."""
        return event_key(
            root_id, self.activation_id, self.from_node, self.outcome, self.to_node
        )


def _via_gate(activation: ActivationRecord) -> str | None:
    return next(
        (
            item.gate_id
            for item in activation.metadata.deviations
            if item.kind == DEVIATION_UNDECLARED_EFFECTS_ACCEPTED
        ),
        None,
    )


def expected_intents(
    root: RootRecord,
    activations: Iterable[ActivationRecord],
    gates: Iterable[GateRecord],
) -> tuple[EventIntent, ...]:
    """Return the events implied by an immutable activation/gate trace."""
    activation_rows = tuple(activations)
    gate_rows = tuple(gates)
    by_id = {item.activation_id: item for item in activation_rows}
    intents: list[EventIntent] = []
    for successor in activation_rows:
        meta = successor.metadata
        if meta.mint_reason is not MintReason.EDGE or meta.outcome_taken is None:
            continue
        if meta.predecessor_activation_id is not None:
            predecessor = by_id.get(meta.predecessor_activation_id)
            if predecessor is not None:
                intents.append(
                    EventIntent(
                        from_node=predecessor.metadata.node,
                        outcome=meta.outcome_taken,
                        to_node=meta.node,
                        activation_id=predecessor.activation_id,
                        via_gate_id=_via_gate(predecessor),
                    )
                )
        elif meta.predecessor_gate_id is not None:
            gate = next(
                (
                    item
                    for item in gate_rows
                    if item.gate_id == meta.predecessor_gate_id
                ),
                None,
            )
            if gate is not None:
                intents.append(
                    EventIntent(
                        from_node=gate.metadata.gate_node,
                        outcome=meta.outcome_taken,
                        to_node=meta.node,
                        activation_id=gate.gate_id,
                        origin="gate",
                    )
                )
    for gate in gate_rows:
        gate_meta = gate.metadata
        if (
            gate_meta.gate_reason in {GateReason.TRANSITION, GateReason.EXHAUSTION}
            and gate_meta.gate_node != EFFECTS_NODE
            and gate_meta.source_activation_id
            and gate_meta.opening_outcome
        ):
            source = by_id.get(gate_meta.source_activation_id)
            if source is not None:
                intents.append(
                    EventIntent(
                        from_node=source.metadata.node,
                        outcome=gate_meta.opening_outcome,
                        to_node=gate_meta.gate_node,
                        activation_id=source.activation_id,
                        via_gate_id=_via_gate(source),
                    )
                )
        if (
            gate_meta.gate_reason is GateReason.HALT
            and gate_meta.state is GateState.CLOSED
            and gate_meta.outcome is Outcome.ABANDON
            and gate_meta.verified_fingerprint is not None
            and gate_meta.payload_digest is not None
        ):
            intent = abandon_intent(root.index, gate)
            if intent is not None:
                intents.append(intent)
    for activation in activation_rows:
        meta = activation.metadata
        if not meta.is_completed or meta.outcome is None:
            continue
        if any(
            deviation.kind
            in {
                DEVIATION_INSTANCE_BRANCH_DIVERGED,
                DEVIATION_PRECONDITION_REFUSED,
                DEVIATION_INPUTS_UNAVAILABLE,
            }
            for deviation in meta.deviations
        ):
            continue
        decision = route(
            root.index,
            root.index.nodes[meta.node],
            meta.outcome,
            no_progress=False
            if meta.evidence is None
            else meta.evidence.breaker is not None,
        )
        if decision.kind is RouteKind.TERMINAL and decision.target is not None:
            intents.append(
                EventIntent(
                    from_node=meta.node,
                    outcome=meta.outcome,
                    to_node=decision.target,
                    activation_id=activation.activation_id,
                )
            )
    for gate in gate_rows:
        gate_meta = gate.metadata
        if (
            gate_meta.state is not GateState.CLOSED
            or gate_meta.outcome is None
            or gate_meta.gate_reason is GateReason.HALT
            or gate_meta.verified_fingerprint is None
            or gate_meta.payload_digest is None
        ):
            continue
        decision = route(
            root.index, root.index.nodes[gate_meta.gate_node], gate_meta.outcome
        )
        if decision.kind is RouteKind.TERMINAL and decision.target is not None:
            intents.append(
                EventIntent(
                    from_node=gate_meta.gate_node,
                    outcome=gate_meta.outcome,
                    to_node=decision.target,
                    activation_id=gate.gate_id,
                    origin="gate",
                )
            )
    return tuple(intents)


def abandon_intent(index: GraphIndex, gate: GateRecord) -> EventIntent | None:
    """Return the terminal event implied by a decided abandoned halt gate."""
    target = abandon_target(index)
    if gate.metadata.outcome is not Outcome.ABANDON or target is None:
        return None
    return EventIntent(
        from_node=HALT_NODE,
        outcome=Outcome.ABANDON,
        to_node=target,
        activation_id=gate.gate_id,
        origin="gate",
    )


def backfill(
    store: WorkflowStore,
    root_id: str,
    intents: Iterable[EventIntent],
    *,
    actor: str,
    existing: set[str],
    first_seq: int | None = None,
) -> int:
    """Append absent audit events, allocating a fresh sequence for each one."""
    count = 0
    for intent in intents:
        key = intent.key_for(root_id)
        if key in existing:
            continue
        seq = (
            next_seq(store.reads.instance_beads(root_id))
            if first_seq is None
            else first_seq + count
        )
        payload = EventPayload(
            **{"from": intent.from_node},
            outcome=intent.outcome,
            to=intent.to_node,
            activation_id=intent.activation_id,
            seq=seq,
            actor=actor,
            origin=intent.origin,
            via_gate_id=intent.via_gate_id,
        )
        store.append_event(root_id, payload, seq=seq)
        existing.add(key)
        count += 1
    return count
