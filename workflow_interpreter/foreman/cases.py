"""Stateful per-lifecycle actions selected by one foreman tick."""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import (
    ActivationRecord,
    GateReason,
    GateRecord,
    GateState,
    Lifecycle,
    MintReason,
    MintRequest,
    RootRecord,
)
from workflow_interpreter.bdio.client import STATUS_CLOSED
from workflow_interpreter.bdio.errors import BoundExceededError
from workflow_interpreter.bdio.preflight import steer_ancestor
from workflow_interpreter.foreman.bounds import refusal_route
from workflow_interpreter.foreman.close import settle
from workflow_interpreter.foreman.compose import (
    Composition,
    InstanceWiring,
    WrapperLaunch,
)
from workflow_interpreter.foreman.constants import (
    DISPATCH_REQUEST,
    GATES_DIR,
    HALT_BRANCH_DIVERGED,
    HALT_CEILING,
    HALT_FAIL_CLOSED,
    HALT_FAIL_CODE,
    HALT_NODE,
    HALT_PRECONDITION_REFUSED,
)
from workflow_interpreter.foreman.frontier import DeadEndKind
from workflow_interpreter.foreman.gates import (
    IntakeResult,
    exhaustion_gate,
    halt_gate,
    intake,
    no_progress_gate,
    transition_gate,
)
from workflow_interpreter.foreman.inputs import select_bindings
from workflow_interpreter.foreman.routing import RouteKind, retry_kind, route
from workflow_interpreter.foreman.supervise import wrapper_alive
from workflow_interpreter.schema.models import NodeKind
from workflow_interpreter.supervisor.paths import write_record


class CaseResult(BaseModel):
    """The small, reportable result of advancing one lifecycle case."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dispatched: str | None = None
    blocked: bool = False
    settled: str | None = None
    stalled: str | None = None
    opened_gates: tuple[str, ...] = ()
    terminal: bool = False


class IntakeBatch(BaseModel):
    """The closed gates and refusals observed during one intake pass."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    closed: tuple[GateRecord, ...] = ()
    refusals: tuple[str, ...] = ()


def intake_all(
    wiring: InstanceWiring, root: RootRecord, gates: Iterable[GateRecord]
) -> IntakeBatch:
    """Intake open gates and repair carrier-closed gates with open beads first."""
    ordered = sorted(
        (
            gate
            for gate in gates
            if gate.metadata.state is GateState.OPEN
            or (
                gate.metadata.state is GateState.CLOSED
                and gate.bead.status != STATUS_CLOSED
            )
        ),
        key=lambda gate: (gate.metadata.gate_node != HALT_NODE, gate.metadata.seq),
    )
    closed: list[GateRecord] = []
    refusals: list[str] = []
    for gate in ordered:
        result: IntakeResult = intake(
            wiring.store, root, gate, wiring.paths.instance_dir / GATES_DIR
        )
        if result.gate is not None:
            closed.append(result.gate)
        if result.refusal is not None:
            refusals.append(result.refusal)
    return IntakeBatch(closed=tuple(closed), refusals=tuple(refusals))


def _request(
    composition: Composition,
    root: RootRecord,
    activation: ActivationRecord,
) -> MintRequest:
    """Reconstruct the durable request shape needed by the wrapper."""
    meta = activation.metadata
    return MintRequest(
        node=meta.node,
        mint_reason=meta.mint_reason,
        runner_profile=meta.runner_profile,
        model=meta.model,
        session_id=meta.session_id,
        predecessor_activation_id=meta.predecessor_activation_id,
        predecessor_gate_id=meta.predecessor_gate_id,
        inputs=meta.inputs,
    )


def dispatch_minted(
    composition: Composition,
    wiring: InstanceWiring,
    root: RootRecord,
    activation: ActivationRecord,
) -> CaseResult:
    """Persist the launch intent then invoke the configured spawner once."""
    request = _request(composition, root, activation)
    path = wiring.paths.activation_dir(activation.activation_id) / DISPATCH_REQUEST
    write_record(
        path,
        WrapperLaunch(
            root_id=root.root_id,
            activation_id=activation.activation_id,
            request=request,
        ),
    )
    composition.spawner.launch(
        WrapperLaunch(
            root_id=root.root_id,
            activation_id=activation.activation_id,
            request=request,
        ),
        wiring=wiring,
    )
    return CaseResult(dispatched=activation.activation_id)


def _successor_request(
    composition: Composition,
    wiring: InstanceWiring,
    root: RootRecord,
    target: str,
    *,
    predecessor_activation_id: str | None = None,
    predecessor_gate_id: str | None = None,
    round_no: int,
) -> MintRequest | None:
    """Build the one graph-edge request permitted by a completed head."""
    node = root.index.nodes[target]
    role_name = (node.runner or "").removeprefix("profile:")
    binding = composition.config.roles.get(role_name)
    if binding is None:
        return None
    return MintRequest(
        node=target,
        mint_reason=MintReason.EDGE,
        predecessor_activation_id=predecessor_activation_id,
        predecessor_gate_id=predecessor_gate_id,
        runner_profile=binding.profile,
        model=binding.model,
        session_id=str(uuid.uuid4()) if binding.profile == "claude" else "",
        inputs=select_bindings(
            root.index,
            root,
            node,
            wiring.store.reads.list_activations(root.root_id),
            round_no,
        ),
    )


def _mint_successor(
    composition: Composition,
    wiring: InstanceWiring,
    root: RootRecord,
    target: str,
    *,
    predecessor_activation_id: str | None = None,
    predecessor_gate_id: str | None = None,
    round_no: int,
) -> CaseResult:
    """Mint then dispatch one graph successor, or report a closed refusal."""
    request = _successor_request(
        composition,
        wiring,
        root,
        target,
        predecessor_activation_id=predecessor_activation_id,
        predecessor_gate_id=predecessor_gate_id,
        round_no=round_no,
    )
    if request is None:
        return CaseResult(stalled=f"unknown runner role for {target!r}")
    try:
        minted = wiring.store.mint_activation(root.root_id, request).activation
    except BoundExceededError as exc:
        return _refusal_case(composition, wiring, root, target, request, exc)
    return dispatch_minted(composition, wiring, root, minted)


def _refusal_case(
    composition: Composition,
    wiring: InstanceWiring,
    root: RootRecord,
    node_name: str,
    request: MintRequest,
    error: BoundExceededError,
) -> CaseResult:
    """Turn a bounded refusal into its declared halt, exhaustion, or fallback."""
    node = root.index.nodes[node_name]
    decision = refusal_route(root.index, node, error.refusal)
    source: ActivationRecord | None = None
    if request.predecessor_activation_id is not None:
        source = wiring.store.reads.load_activation(request.predecessor_activation_id)
    elif request.predecessor_gate_id is not None:
        gate = wiring.store.reads.load_gate(request.predecessor_gate_id)
        if gate.metadata.source_activation_id is not None:
            source = wiring.store.reads.load_activation(
                gate.metadata.source_activation_id
            )
    if (
        decision.kind is RouteKind.EXHAUSTED
        and decision.target is not None
        and source is not None
    ):
        gate = wiring.store.open_gate(
            root.root_id, exhaustion_gate(root.index, source, decision.target)
        )
        return CaseResult(opened_gates=(gate.gate_id,))
    if decision.kind is RouteKind.FALLBACK and decision.target is not None:
        target = root.index.nodes[decision.target]
        if target.kind.value == "gate" and source is not None:
            opening_outcome = source.metadata.outcome or source.metadata.outcome_taken
            if opening_outcome is not None:
                gate = wiring.store.open_gate(
                    root.root_id,
                    transition_gate(
                        composition.git,
                        wiring.repo_root,
                        root.index,
                        decision.target,
                        source,
                        opening_outcome,
                    ),
                )
                return CaseResult(opened_gates=(gate.gate_id,))
    gate = wiring.store.open_gate(
        root.root_id, halt_gate(HALT_CEILING.format(detail=str(error)))
    )
    return CaseResult(opened_gates=(gate.gate_id,))


def mint_entry(
    composition: Composition, wiring: InstanceWiring, root: RootRecord
) -> CaseResult:
    """Mint and dispatch the graph entry with bindings derived from the pin."""
    node_name = root.definition.document.graph.entry
    node = root.index.nodes[node_name]
    role_name = (node.runner or "").removeprefix("profile:")
    binding = composition.config.roles.get(role_name)
    if binding is None:
        return CaseResult(stalled=f"unknown runner role {role_name!r}")
    request = MintRequest(
        node=node_name,
        mint_reason=MintReason.ENTRY,
        runner_profile=binding.profile,
        model=binding.model,
        session_id=str(uuid.uuid4()) if binding.profile == "claude" else "",
        inputs=select_bindings(root.index, root, node, (), 1),
    )
    try:
        minted = wiring.store.mint_activation(root.root_id, request).activation
    except BoundExceededError as exc:
        return _refusal_case(composition, wiring, root, node_name, request, exc)
    return dispatch_minted(composition, wiring, root, minted)


def advance_lifecycle(
    composition: Composition,
    wiring: InstanceWiring,
    root: RootRecord,
    activation: ActivationRecord,
) -> CaseResult:
    """Advance one open activation without mixing routing into lifecycle work."""
    lifecycle = activation.metadata.lifecycle
    if lifecycle is Lifecycle.MINTED:
        if wrapper_alive(wiring, activation.activation_id):
            return CaseResult(blocked=True)
        return dispatch_minted(composition, wiring, root, activation)
    if lifecycle is Lifecycle.DISPATCHED:
        if wrapper_alive(wiring, activation.activation_id):
            return CaseResult(blocked=True)
        resolution = wiring.recovery.resolve(
            activation, root.index.nodes[activation.metadata.node]
        )
        classification = getattr(resolution, "classification", None)
        exit_record = None if classification is None else classification.exit_record
        if exit_record is not None:
            recorded = wiring.store.record_exit(activation.activation_id, exit_record)
            profile = composition.profiles.profile_for(recorded.metadata.runner_profile)
            result = settle(
                wiring,
                root,
                root.index.nodes[recorded.metadata.node],
                recorded,
                profile,
            )
            return CaseResult(
                settled=result.activation.activation_id
                if result.activation.metadata.is_completed
                else None,
                stalled=result.stalled,
            )
        return CaseResult(
            settled=None
            if resolution.closed is None
            else resolution.closed.activation_id,
            stalled=resolution.halted,
        )
    if lifecycle in {Lifecycle.EXIT_RECORDED, Lifecycle.EVIDENCE_RECORDED}:
        profile = composition.profiles.profile_for(activation.metadata.runner_profile)
        result = settle(
            wiring,
            root,
            root.index.nodes[activation.metadata.node],
            activation,
            profile,
        )
        return CaseResult(
            settled=result.activation.activation_id
            if result.activation.metadata.is_completed
            else None,
            stalled=result.stalled,
        )
    return CaseResult()


def route_head(
    composition: Composition,
    wiring: InstanceWiring,
    root: RootRecord,
    head: ActivationRecord | GateRecord,
) -> CaseResult:
    """Apply one graph-routing decision to a completed activation or gate."""
    if isinstance(head, GateRecord):
        outcome = head.metadata.outcome
        if outcome is None:
            return CaseResult(stalled="gate head has no outcome")
        if (
            head.metadata.gate_reason is GateReason.HALT
            and head.metadata.source_activation_id is not None
        ):
            source = wiring.store.reads.load_activation(
                head.metadata.source_activation_id
            )
            return _mint_successor(
                composition,
                wiring,
                root,
                source.metadata.node,
                predecessor_gate_id=head.gate_id,
                round_no=head.metadata.round_no or source.metadata.round_no,
            )
        node = root.index.nodes[head.metadata.gate_node]
        result = route(root.index, node, outcome)
        if result.kind is RouteKind.TASK and result.target is not None:
            return _mint_successor(
                composition,
                wiring,
                root,
                result.target,
                predecessor_gate_id=head.gate_id,
                round_no=head.metadata.round_no or 1,
            )
        if result.kind is RouteKind.TERMINAL:
            return CaseResult(terminal=True)
        return CaseResult(stalled=result.reason or "gate route is not a task")

    outcome = head.metadata.outcome
    if outcome is None:
        return CaseResult(stalled="completed activation has no outcome")
    node = root.index.nodes[head.metadata.node]
    retry = retry_kind(outcome)
    if retry is not None:
        if retry is MintReason.STEER_CONTINUATION:
            resolution = wiring.recovery.resolve(head, node)
            return CaseResult(
                settled=None
                if resolution.closed is None
                else resolution.closed.activation_id,
                stalled=resolution.halted,
            )
        # Built field by field rather than copied from `_request`: a retry's
        # only predecessor is the activation it re-attempts, never the gate that
        # originally minted it, and `MintRequest` refuses both at once
        # (`wire.py` `_validate_predecessors`). `model_copy(update=…)` skips
        # after-validators, so a copy carried the stale `predecessor_gate_id`
        # into a non-EDGE mint and stranded the instance (cr-o85.33.8).
        head_meta = head.metadata
        request = MintRequest(
            node=head_meta.node,
            mint_reason=retry,
            runner_profile=head_meta.runner_profile,
            model=head_meta.model,
            session_id=head_meta.session_id,
            predecessor_activation_id=head.activation_id,
            inputs=head_meta.inputs,
        )
        if steer_ancestor(wiring.store.reads, request) is not None:
            fallback = node.fallback or root.definition.document.fallback
            if root.index.nodes[fallback.to].kind.value == "gate":
                gate = wiring.store.open_gate(
                    root.root_id,
                    transition_gate(
                        composition.git,
                        wiring.repo_root,
                        root.index,
                        fallback.to,
                        head,
                        outcome,
                    ),
                )
                return CaseResult(opened_gates=(gate.gate_id,))
            return CaseResult(stalled="infra retry of a steer continuation is refused")
        try:
            minted = wiring.store.mint_activation(root.root_id, request).activation
        except BoundExceededError as exc:
            return _refusal_case(
                composition, wiring, root, head.metadata.node, request, exc
            )
        return dispatch_minted(composition, wiring, root, minted)
    evidence = head.metadata.evidence
    decision = route(
        root.index,
        node,
        outcome,
        claimed_outcome=None if evidence is None else evidence.claimed_outcome,
        no_progress=False if evidence is None else evidence.breaker is not None,
    )
    if decision.kind is RouteKind.TASK and decision.target is not None:
        return _mint_successor(
            composition,
            wiring,
            root,
            decision.target,
            predecessor_activation_id=head.activation_id,
            round_no=head.metadata.round_no,
        )
    if decision.kind is RouteKind.GATE and decision.target is not None:
        gate = wiring.store.open_gate(
            root.root_id,
            transition_gate(
                composition.git,
                wiring.repo_root,
                root.index,
                decision.target,
                head,
                outcome,
            ),
        )
        return CaseResult(opened_gates=(gate.gate_id,))
    if decision.kind is RouteKind.EXHAUSTED and decision.target is not None:
        gate = wiring.store.open_gate(
            root.root_id, exhaustion_gate(root.index, head, decision.target)
        )
        return CaseResult(opened_gates=(gate.gate_id,))
    if decision.kind is RouteKind.NO_PROGRESS:
        target = (node.fallback or root.definition.document.fallback).to
        gate = wiring.store.open_gate(
            root.root_id, no_progress_gate(root.index, head, target)
        )
        return CaseResult(opened_gates=(gate.gate_id,))
    if decision.kind is RouteKind.FALLBACK and decision.target is not None:
        target_node = root.index.nodes[decision.target]
        if target_node.kind is NodeKind.GATE:
            gate = wiring.store.open_gate(
                root.root_id,
                transition_gate(
                    composition.git,
                    wiring.repo_root,
                    root.index,
                    decision.target,
                    head,
                    outcome,
                ),
            )
            return CaseResult(opened_gates=(gate.gate_id,))
        if target_node.kind is NodeKind.TASK:
            return _mint_successor(
                composition,
                wiring,
                root,
                decision.target,
                predecessor_activation_id=head.activation_id,
                round_no=head.metadata.round_no,
            )
        if target_node.kind is NodeKind.TERMINAL:
            return CaseResult(terminal=True)
    if decision.kind in {RouteKind.FALLBACK, RouteKind.FAIL_CLOSED}:
        reason = HALT_FAIL_CLOSED.format(reason=decision.reason or "fallback")
        gate = wiring.store.open_gate(root.root_id, halt_gate(reason))
        return CaseResult(opened_gates=(gate.gate_id,))
    if decision.kind is RouteKind.DEAD_END:
        gate = wiring.store.open_gate(
            root.root_id,
            halt_gate(
                HALT_FAIL_CODE.format(node=node.name, activation_id=head.activation_id),
                source=head,
            ),
        )
        return CaseResult(opened_gates=(gate.gate_id,))
    if decision.kind is RouteKind.TERMINAL:
        return CaseResult(terminal=True)
    return CaseResult(stalled=decision.reason or "route is unsupported")


def halt_dead_end(
    wiring: InstanceWiring,
    root: RootRecord,
    kind: DeadEndKind,
    activation: ActivationRecord,
) -> CaseResult:
    """Open the typed halt that prevents a dead-end activation from routing."""
    reason = {
        DeadEndKind.FAIL_CODE: HALT_FAIL_CODE,
        DeadEndKind.BRANCH_DIVERGED: HALT_BRANCH_DIVERGED,
        DeadEndKind.PRECONDITION_REFUSED: HALT_PRECONDITION_REFUSED,
    }[kind].format(
        node=activation.metadata.node, activation_id=activation.activation_id
    )
    gate = wiring.store.open_gate(root.root_id, halt_gate(reason, source=activation))
    return CaseResult(opened_gates=(gate.gate_id,))
