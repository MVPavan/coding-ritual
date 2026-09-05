"""Derive the next durable workflow frontier from parsed bd records."""

import json
from collections.abc import Iterable
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import (
    ActivationRecord,
    GateReason,
    GateRecord,
    GateState,
    Lifecycle,
)
from workflow_interpreter.bdio.constants import (
    DEVIATION_BOUND_VIOLATED,
    DEVIATION_INPUTS_UNAVAILABLE,
    DEVIATION_INSTANCE_BRANCH_DIVERGED,
    DEVIATION_PRECONDITION_REFUSED,
    DEVIATION_SANDBOX_UNAVAILABLE,
)
from workflow_interpreter.bdio.records import RootRecord, parse_activation, parse_gate
from workflow_interpreter.bdio.wire import BeadRecord, EventPayload, WfKind
from workflow_interpreter.foreman.constants import EFFECTS_NODE
from workflow_interpreter.schema.graph_index import GraphIndex
from workflow_interpreter.schema.models import NodeKind, Outcome


class FrontierViolation(ValueError):
    """A durable row is too incomplete to route safely."""


class FrontierConflict(ValueError):
    """More than one unconsumed routing head exists."""


class DeadEndKind(StrEnum):
    """The durable reason an otherwise completed activation cannot route."""

    FAIL_CODE = "fail-code"
    BRANCH_DIVERGED = "branch-diverged"
    PRECONDITION_REFUSED = "precondition-refused"
    INPUTS_UNAVAILABLE = "inputs-unavailable"
    SANDBOX_UNAVAILABLE = "sandbox-unavailable"
    BOUND_VIOLATED = "bound-violated"


class DeadEnd(BaseModel):
    """An unconsumed completed activation that needs a halt gate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    activation: ActivationRecord
    kind: DeadEndKind


class Frontier(BaseModel):
    """The trace partition used by the stateful later foreman slices."""

    model_config = ConfigDict(
        frozen=True, extra="forbid", arbitrary_types_allowed=False
    )

    minted: tuple[ActivationRecord, ...] = ()
    dispatched: tuple[ActivationRecord, ...] = ()
    exit_recorded: tuple[ActivationRecord, ...] = ()
    evidence_recorded: tuple[ActivationRecord, ...] = ()
    open_gates: tuple[GateRecord, ...] = ()
    decided_gates: tuple[GateRecord, ...] = ()
    open_halt: GateRecord | None = None
    abandoned_halt: GateRecord | None = None
    dead_end: DeadEnd | None = None
    head_activation: ActivationRecord | None = None
    head_gate: GateRecord | None = None
    terminal: bool = False
    empty: bool = False

    @property
    def head(self) -> ActivationRecord | GateRecord | None:
        """The sole unconsumed routing head, whatever durable kind owns it."""
        return self.head_activation or self.head_gate


def _event_payloads(beads: Iterable[BeadRecord]) -> tuple[EventPayload, ...]:
    payloads: list[EventPayload] = []
    for bead in beads:
        if bead.metadata.get("wf_kind") != WfKind.EVENT.value or bead.payload is None:
            continue
        payloads.append(EventPayload.model_validate(json.loads(bead.payload)))
    return tuple(payloads)


def _is_decided(gate: GateRecord) -> bool:
    meta = gate.metadata
    if meta.state is GateState.CLOSED and not (
        meta.outcome and meta.verified_fingerprint and meta.payload_digest
    ):
        raise FrontierViolation("gate_close_unverified")
    return meta.state is GateState.CLOSED and meta.outcome is not None


def _dead_end(index: GraphIndex, activation: ActivationRecord) -> DeadEndKind | None:
    meta = activation.metadata
    if not meta.is_completed:
        return None
    if any(item.kind == DEVIATION_INSTANCE_BRANCH_DIVERGED for item in meta.deviations):
        return DeadEndKind.BRANCH_DIVERGED
    if any(item.kind == DEVIATION_PRECONDITION_REFUSED for item in meta.deviations):
        return DeadEndKind.PRECONDITION_REFUSED
    if any(item.kind == DEVIATION_INPUTS_UNAVAILABLE for item in meta.deviations):
        return DeadEndKind.INPUTS_UNAVAILABLE
    if any(item.kind == DEVIATION_SANDBOX_UNAVAILABLE for item in meta.deviations):
        return DeadEndKind.SANDBOX_UNAVAILABLE
    if any(item.kind == DEVIATION_BOUND_VIOLATED for item in meta.deviations):
        return DeadEndKind.BOUND_VIOLATED
    node = index.nodes.get(meta.node)
    # Kept in step with `routing.route`: a `fail_code` dead-ends only where the
    # node does not declare it, whatever the runner claimed (ADR 0004). A
    # computed `fail_code` on a declaring node is a routing head like any other.
    if meta.outcome is Outcome.FAIL_CODE and (
        node is None or Outcome.FAIL_CODE not in (node.outcomes or ())
    ):
        return DeadEndKind.FAIL_CODE
    return None


def build_frontier(root: RootRecord, beads: Iterable[BeadRecord]) -> Frontier:
    """Build a frontier, refusing ambiguous or unauthenticated trace state."""
    records = tuple(beads)
    activations = tuple(
        record
        for record in records
        if record.metadata.get("wf_kind") == WfKind.ACTIVATION.value
    )
    gates = tuple(
        record
        for record in records
        if record.metadata.get("wf_kind") == WfKind.GATE.value
    )
    parsed_activations = tuple(parse_activation(record) for record in activations)
    parsed_gates = tuple(parse_gate(record) for record in gates)
    index = root.index
    events = _event_payloads(records)
    live_activations = tuple(
        item for item in parsed_activations if not item.metadata.is_superseded
    )
    live_gates = tuple(
        item
        for item in parsed_gates
        if _is_decided(item) or item.metadata.state is GateState.OPEN
    )
    terminal_events = tuple(
        event
        for event in events
        if (node := index.nodes.get(event.to_node)) is not None
        and node.kind is NodeKind.TERMINAL
    )
    consumed_activations = (
        {item.metadata.predecessor_activation_id for item in live_activations}
        | {
            item.metadata.source_activation_id
            for item in live_gates
            if item.metadata.gate_reason
            in {GateReason.TRANSITION, GateReason.EXHAUSTION, GateReason.HALT}
            and item.metadata.gate_node != EFFECTS_NODE
        }
        | {event.activation_id for event in terminal_events}
    )
    consumed_gates = {
        item.metadata.predecessor_gate_id for item in live_activations
    } | {event.activation_id for event in terminal_events}
    terminal = bool(terminal_events)
    unconsumed_activations = tuple(
        item
        for item in live_activations
        if item.activation_id not in consumed_activations
    )
    unconsumed_gates = tuple(
        item for item in live_gates if item.gate_id not in consumed_gates
    )
    open_gates = tuple(
        item for item in parsed_gates if item.metadata.state is GateState.OPEN
    )
    decided = tuple(item for item in parsed_gates if _is_decided(item))
    dead = next(
        (
            DeadEnd(activation=item, kind=kind)
            for item in unconsumed_activations
            if (kind := _dead_end(index, item)) is not None
        ),
        None,
    )
    candidates_a = [
        item
        for item in unconsumed_activations
        if item.metadata.is_completed and _dead_end(index, item) is None
    ]
    candidates_g = [
        item
        for item in unconsumed_gates
        if _is_decided(item)
        and (
            (
                item.metadata.gate_reason
                in {GateReason.TRANSITION, GateReason.EXHAUSTION}
                and item.metadata.gate_node != EFFECTS_NODE
            )
            or (
                item.metadata.gate_reason is GateReason.HALT
                and item.metadata.source_activation_id is not None
                and item.metadata.outcome in {Outcome.APPROVE, Outcome.REBUDGET}
            )
        )
    ]
    heads = [*candidates_a, *candidates_g]
    if len(heads) > 1:
        raise FrontierConflict("more than one unconsumed routing head")
    abandoned = next(
        (
            item
            for item in unconsumed_gates
            if item.metadata.gate_reason is GateReason.HALT
            and item.metadata.state is GateState.CLOSED
            and item.metadata.outcome is Outcome.ABANDON
        ),
        None,
    )
    open_halt = next(
        (item for item in open_gates if item.metadata.gate_reason is GateReason.HALT),
        None,
    )
    live_gate_exists = bool(open_gates or candidates_g or abandoned)
    return Frontier(
        minted=tuple(
            item
            for item in live_activations
            if item.metadata.lifecycle is Lifecycle.MINTED
        ),
        dispatched=tuple(
            item
            for item in live_activations
            if item.metadata.lifecycle is Lifecycle.DISPATCHED
        ),
        exit_recorded=tuple(
            item
            for item in live_activations
            if item.metadata.lifecycle is Lifecycle.EXIT_RECORDED
        ),
        evidence_recorded=tuple(
            item
            for item in live_activations
            if item.metadata.lifecycle is Lifecycle.EVIDENCE_RECORDED
        ),
        open_gates=open_gates,
        decided_gates=decided,
        open_halt=open_halt,
        abandoned_halt=abandoned,
        dead_end=dead,
        head_activation=heads[0]
        if heads and isinstance(heads[0], ActivationRecord)
        else None,
        head_gate=heads[0] if heads and isinstance(heads[0], GateRecord) else None,
        terminal=terminal,
        empty=not live_activations and not live_gate_exists and not terminal,
    )
