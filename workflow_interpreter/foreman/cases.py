"""Stateful per-lifecycle actions selected by one foreman tick."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import Final

import structlog
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
from workflow_interpreter.bdio.errors import BoundExceededError
from workflow_interpreter.bdio.keys import entry_idempotency_key, idempotency_key
from workflow_interpreter.bdio.rows import STATUS_CLOSED
from workflow_interpreter.bdio.wire import (
    ActivationMetadata,
    mint_request_from_activation,
)
from workflow_interpreter.contracts.sessions import SessionFreshReason, SessionMode
from workflow_interpreter.foreman.bounds import refusal_route
from workflow_interpreter.foreman.close import settle
from workflow_interpreter.foreman.compose import (
    Composition,
    InstanceWiring,
    WrapperLaunch,
)
from workflow_interpreter.foreman.config import (
    BindingApply,
    CrewBinding,
    load_role_bindings,
    read_role_apply,
)
from workflow_interpreter.foreman.constants import (
    DISPATCH_REQUEST,
    GATES_DIR,
    HALT_BOUND_VIOLATED,
    HALT_BRANCH_DIVERGED,
    HALT_CEILING,
    HALT_FAIL_CLOSED,
    HALT_FAIL_CODE,
    HALT_INPUTS_UNAVAILABLE,
    HALT_NODE,
    HALT_PRECONDITION_REFUSED,
    HALT_SANDBOX_UNAVAILABLE,
    HALT_UNUSABLE_RESOLUTION,
)
from workflow_interpreter.foreman.errors import LiveProbeRequired, ResolutionError
from workflow_interpreter.foreman.events import EventIntent
from workflow_interpreter.foreman.execution import (
    ResolvedNode,
    resolved_invocation,
    resolved_node,
    resolved_static_node,
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
from workflow_interpreter.foreman.inspector import wrapper_alive
from workflow_interpreter.foreman.ledger_render import bind_render
from workflow_interpreter.foreman.model_catalog import (
    VerificationStatus,
    resolve_role_binding,
)
from workflow_interpreter.foreman.routing import RouteKind, retry_kind, route
from workflow_interpreter.foreman.verify_feedback import bind_feedback
from workflow_interpreter.foreman.wake_constants import DEFAULT_EVENT_CAP
from workflow_interpreter.inspector.models import RecoveryCase
from workflow_interpreter.inspector.paths import write_record
from workflow_interpreter.profiles.config import CREW_PREFIX
from workflow_interpreter.schema.models import NodeKind, Outcome

_STALL_ABORT_PENDING = "barrier abort cleanup is still pending"
MSG_ROLE_EDIT_IGNORED: Final[str] = "wf.roles.edit_ignored"
_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)


def probed_crew_version(composition: Composition, crew_profile: str) -> str | None:
    """The CLI version THIS process probed, never the root's historical pin.

    Carried on the mint request so `choose_source` can compare a source's
    registered version against the running CLI (finding 4): after an upgrade the
    root's pin is stale, so reusing it would keep resuming incompatible history.
    A vendor with no resumable CLI has no version to probe and the comparison is
    skipped; a resolver that cannot answer at all is a type error, not silence.
    """
    return composition.profiles.version_for(crew_profile)


def startup_invocation(
    composition: Composition,
    root: RootRecord,
    node_name: str,
    *,
    wiring: InstanceWiring | None = None,
) -> ResolvedNode:
    """Resolve a new mint from the current qualified role binding."""
    node = root.index.nodes[node_name]
    binding = None
    if node.crew and node.crew.startswith(CREW_PREFIX):
        role = node.crew.removeprefix(CREW_PREFIX)
        prior = None
        if wiring is not None:
            prior = next(
                (
                    activation.metadata
                    for activation in reversed(
                        wiring.store.reads.list_activations(root.root_id)
                    )
                    if activation.metadata.role == role
                    and activation.metadata.effort is not None
                ),
                None,
            )
        role_path = composition.config.role_bindings_path
        if role_path is not None and prior is not None:
            try:
                apply = read_role_apply(role_path, role)
            except (OSError, ValueError, TypeError) as error:
                _LOG.warning(MSG_ROLE_EDIT_IGNORED, role=role, reason=str(error))
                apply = BindingApply.NEXT_TASK
            if apply is BindingApply.NEXT_TASK:
                binding = _pinned_binding(prior, root, node_name)
            else:
                try:
                    binding = _live_binding(composition, role, role_path)
                except LiveProbeRequired:
                    raise
                except (OSError, ValueError, TypeError) as error:
                    _LOG.warning(MSG_ROLE_EDIT_IGNORED, role=role, reason=str(error))
                    binding = _pinned_binding(prior, root, node_name)
        elif role_path is not None:
            try:
                binding = _live_binding(composition, role, role_path)
            except LiveProbeRequired:
                raise
            except (OSError, ValueError, TypeError) as error:
                raise ResolutionError(f"roles.toml: {error}") from error
        else:
            binding = _qualified_live_binding(
                composition, role, composition.config.roles[role]
            )
        if (
            prior is not None
            and binding is not None
            and binding.apply is BindingApply.NOW
            and (binding.profile, binding.model, binding.effort)
            == (prior.crew_profile, prior.model, prior.effort)
        ):
            # Mode and cap edits apply when the role starts its next task.
            binding = binding.model_copy(
                update={
                    "session_mode": _role_session_mode(
                        prior, root, node_name, binding.session_mode
                    ),
                    "context_cap_tokens": prior.context_cap_tokens,
                }
            )
    view = resolved_invocation(root, node_name, composition.profiles, binding=binding)
    return (
        view
        if binding is None
        else view.model_copy(update={"binding_apply": binding.apply})
    )


def _role_session_mode(
    prior: ActivationMetadata,
    root: RootRecord,
    node_name: str,
    role_mode: SessionMode | None,
) -> SessionMode | None:
    """Copy a prior mode only when it has no other node's declaration in it."""
    if (
        prior.node != node_name
        and root.index.nodes[prior.node].session_mode is not None
    ):
        return role_mode
    return prior.session_mode


def _pinned_binding(
    prior: ActivationMetadata, root: RootRecord, node_name: str
) -> CrewBinding:
    """Recover the role binding recorded on an earlier activation in this root."""
    if prior.effort is None:
        raise ResolutionError(f"role {prior.role!r}: activation has no effort pin")
    return CrewBinding(
        profile=prior.crew_profile,
        model=prior.model,
        effort=prior.effort,
        session_mode=_role_session_mode(prior, root, node_name, None),
        context_cap_tokens=prior.context_cap_tokens,
    )


def _live_binding(composition: Composition, role: str, path: Path) -> CrewBinding:
    """Read and qualify a role's edited binding against the active catalog."""
    live = load_role_bindings(path)
    if role not in live:
        raise ResolutionError(f"role {role!r}: missing from roles.toml")
    return _qualified_live_binding(composition, role, live[role])


def _qualified_live_binding(
    composition: Composition, role: str, binding: CrewBinding
) -> CrewBinding:
    """Validate a live choice only when this mint can use it."""
    if not binding.profile:
        binding = resolve_role_binding(
            role,
            binding,
            composition.active_catalog,
            composition.catalog_provenance,
        )
    if composition.active_catalog is not None and binding.profile == "claude":
        family = next(
            (
                details
                for name, details in composition.active_catalog.families.items()
                if name.value == "claude"
            ),
            None,
        )
        selected = (
            None
            if family is None
            else next(
                (model for model in family.models if model.id == binding.model),
                None,
            )
        )
        if (
            selected is not None
            and selected.verification is VerificationStatus.SEED_UNPROBED
            and binding.model not in composition.live_probes
        ):
            raise LiveProbeRequired(role, binding.model, binding.effort)
    return binding


def _live_change(
    wiring: InstanceWiring, root: RootRecord, view: ResolvedNode
) -> SessionFreshReason | None:
    """Mark an immediate role edit against the task's latest role pin."""
    if view.binding_apply is not BindingApply.NOW:
        return None
    crew = view.node.crew or ""
    if not crew.startswith(CREW_PREFIX):
        return None
    role = crew.removeprefix(CREW_PREFIX)
    previous = next(
        (
            record.metadata
            for record in reversed(wiring.store.reads.list_activations(root.root_id))
            if record.metadata.role == role
        ),
        None,
    )
    if previous is None:
        return None
    if (
        view.crew_profile,
        view.model,
        view.effort,
    ) != (
        previous.crew_profile,
        previous.model,
        previous.effort,
    ):
        return SessionFreshReason.MODEL_CHANGED
    return None


def _replayed(
    composition: Composition, wiring: InstanceWiring, root: RootRecord, key: str
) -> CaseResult | None:
    """Return a prior mint before any mutable role file is opened."""
    existing = wiring.store.reads.find_by_idempotency_key(root.root_id, key)
    if not existing:
        return None
    if len(existing) != 1:
        replay = wiring.store.mint_activation(
            root.root_id, mint_request_from_activation(existing[0].metadata)
        ).activation
        return CaseResult(dispatched=replay.activation_id)
    return CaseResult(dispatched=existing[0].activation_id)


class CaseResult(BaseModel):
    """The small, reportable result of advancing one lifecycle case."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dispatched: str | None = None
    blocked: bool = False
    settled: str | None = None
    stalled: str | None = None
    opened_gates: tuple[str, ...] = ()
    terminal: bool = False
    terminal_node: str | None = None
    """The terminal this route entered — the name the tick settles the root
    with (§3.1); `terminal` without it is not a routable end."""
    event_intents: tuple[EventIntent, ...] = ()
    """Audit events proven by this stateful routing decision."""


class IntakeBatch(BaseModel):
    """The closed gates and refusals observed during one intake pass."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    closed: tuple[GateRecord, ...] = ()
    refusals: tuple[str, ...] = ()


def intake_all(
    wiring: InstanceWiring,
    root: RootRecord,
    gates: Iterable[GateRecord],
    *,
    refusal_limit: int = DEFAULT_EVENT_CAP,
) -> IntakeBatch:
    """Intake open gates and repair carrier-closed gates with open beads first."""
    ordered = sorted(
        (
            gate
            for gate in gates
            if gate.metadata.state is GateState.OPEN
            or (
                gate.metadata.state is GateState.CLOSED and gate.status != STATUS_CLOSED
            )
        ),
        key=lambda gate: (gate.metadata.gate_node != HALT_NODE, gate.metadata.seq),
    )
    closed: list[GateRecord] = []
    refusals: list[str] = []
    for gate in ordered:
        result: IntakeResult = intake(
            wiring.store,
            root,
            gate,
            wiring.paths.instance_dir / GATES_DIR,
            journal_dir=wiring.paths.instance_dir,
            refusal_limit=refusal_limit,
        )
        if result.gate is not None:
            closed.append(result.gate)
        if result.refusal is not None:
            refusals.append(result.refusal)
    return IntakeBatch(closed=tuple(closed), refusals=tuple(refusals))


def dispatch_minted(
    composition: Composition,
    wiring: InstanceWiring,
    root: RootRecord,
    activation: ActivationRecord,
) -> CaseResult:
    """Persist the launch intent then invoke the configured spawner once."""
    request = mint_request_from_activation(activation.metadata)
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
) -> MintRequest:
    """Build the one graph-edge request permitted by a completed head."""
    view = startup_invocation(composition, root, target, wiring=wiring)
    return MintRequest(
        node=target,
        mint_reason=MintReason.EDGE,
        predecessor_activation_id=predecessor_activation_id,
        predecessor_gate_id=predecessor_gate_id,
        crew_profile=view.crew_profile,
        model=view.model,
        effort=view.effort,
        context_cap_tokens=view.context_cap_tokens,
        execution_policy=view.execution_policy,
        catalog_digest=None
        if composition.active_catalog is None
        else composition.active_catalog.digest,
        crew_version=probed_crew_version(composition, view.crew_profile),
        # §5.2: `Profile.prepare` is the only minter of session ids, and it
        # runs at launch; the dispatch writes the one the child ran under back
        # onto this activation (`record_dispatch`).
        session_id="",
        session_mode=view.node.session_mode or SessionMode.FRESH,
        fresh_reason_override=_live_change(wiring, root, view),
        inputs=select_bindings(
            root.index,
            root,
            view.node,
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
    predecessor = predecessor_activation_id or predecessor_gate_id
    if predecessor is not None:
        outcome = (
            wiring.store.reads.load_activation(predecessor).metadata.outcome
            if predecessor_activation_id is not None
            else wiring.store.reads.load_gate(predecessor).metadata.outcome
        )
        if outcome is not None:
            replay = _replayed(
                composition,
                wiring,
                root,
                idempotency_key(root.root_id, predecessor, outcome, target),
            )
            if replay is not None:
                return replay
    request = _successor_request(
        composition,
        wiring,
        root,
        target,
        predecessor_activation_id=predecessor_activation_id,
        predecessor_gate_id=predecessor_gate_id,
        round_no=round_no,
    )
    request = bind_feedback(composition.git, wiring, root, request, composition.clock)
    # After the feedback pin and before the mint, for the same reason: the
    # render an activation is recorded as reading must already be a git object
    # (run-ledger §3.7).
    request = bind_render(composition.git, wiring, root, request, round_no=round_no)
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
    if request.predecessor_activation_id is not None:
        from workflow_interpreter.foreman.decisions import queue_boundary

        boundary_source = wiring.store.reads.load_activation(
            request.predecessor_activation_id
        )
        if queue_boundary(
            composition,
            wiring,
            root,
            boundary_source,
            "allowance_exhausted",
            route_digest=hashlib.sha256(request.model_dump_json().encode()).hexdigest(),
        ):
            return CaseResult(blocked=True)
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
        if target.kind is NodeKind.TERMINAL:
            opening_outcome = (
                None
                if source is None
                else source.metadata.outcome or source.metadata.outcome_taken
            )
            intents = (
                ()
                if opening_outcome is None or source is None
                else (
                    EventIntent(
                        from_node=source.metadata.node,
                        outcome=opening_outcome,
                        to_node=decision.target,
                        activation_id=source.activation_id,
                    ),
                )
            )
            return CaseResult(
                terminal=True, terminal_node=decision.target, event_intents=intents
            )
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
    replay = _replayed(composition, wiring, root, entry_idempotency_key(root.root_id))
    if replay is not None:
        return replay
    view = startup_invocation(composition, root, node_name, wiring=wiring)
    request = MintRequest(
        node=node_name,
        mint_reason=MintReason.ENTRY,
        crew_profile=view.crew_profile,
        model=view.model,
        effort=view.effort,
        context_cap_tokens=view.context_cap_tokens,
        execution_policy=view.execution_policy,
        catalog_digest=None
        if composition.active_catalog is None
        else composition.active_catalog.digest,
        crew_version=probed_crew_version(composition, view.crew_profile),
        session_id="",  # minted by `Profile.prepare` at launch (§5.2)
        session_mode=view.node.session_mode or SessionMode.FRESH,
        inputs=select_bindings(root.index, root, view.node, (), 1),
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
        # Grading uses the activation invocation with the root's static safety
        # settings, including effective writes and isolation (cr-7h8 review).
        resolution = wiring.recovery.resolve(
            activation,
            resolved_static_node(root, activation.metadata.node),
        )
        classification = getattr(resolution, "classification", None)
        exit_record = None if classification is None else classification.exit_record
        if exit_record is not None:
            recorded = wiring.store.record_exit(activation.activation_id, exit_record)
            view = resolved_node(
                root, recorded.metadata.node, activation=recorded.metadata
            )
            profile = composition.profiles.profile_for(view.crew_profile)
            result = settle(
                wiring,
                root,
                view.node,
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
        view = resolved_node(
            root, activation.metadata.node, activation=activation.metadata
        )
        profile = composition.profiles.profile_for(view.crew_profile)
        result = settle(
            wiring,
            root,
            view.node,
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
            return CaseResult(terminal=True, terminal_node=result.target)
        return CaseResult(stalled=result.reason or "gate route is not a task")

    outcome = head.metadata.outcome
    if outcome is None:
        return CaseResult(stalled="completed activation has no outcome")
    node = resolved_static_node(root, head.metadata.node)
    if outcome in (Outcome.FAIL_PLAN, Outcome.DOUBT):
        from workflow_interpreter.foreman.decisions import queue_boundary

        if queue_boundary(
            composition,
            wiring,
            root,
            head,
            "doubt" if outcome is Outcome.DOUBT else "fail_plan",
        ):
            return CaseResult(blocked=True)
    retry = retry_kind(outcome)
    if retry is not None:
        if retry is MintReason.STEER_CONTINUATION:
            classification = wiring.recovery.classify(head)
            try:
                resolution = wiring.recovery.resolve(head, node)
            except BoundExceededError as exc:
                intent = classification.steer_intent
                if intent is None:  # pragma: no cover - only resume can raise this
                    raise
                return _refusal_case(
                    composition,
                    wiring,
                    root,
                    head.metadata.node,
                    intent.continuation,
                    exc,
                )
            return CaseResult(
                settled=None
                if resolution.closed is None
                else resolution.closed.activation_id,
                stalled=resolution.halted,
            )
        classification = wiring.recovery.classify(head)
        if classification.case is RecoveryCase.ABORT_PENDING:
            resolution = wiring.recovery.resolve(head, node)
            if (
                resolution.termination is None
                or not resolution.termination.confirmed_dead
            ):
                return CaseResult(stalled=_STALL_ABORT_PENDING)
        # Built field by field rather than copied from `_request`: a retry's
        # only predecessor is the activation it re-attempts, never the gate that
        # originally minted it, and `MintRequest` refuses both at once
        # (`wire.py` `_validate_predecessors`). `model_copy(update=…)` skips
        # after-validators, so a copy carried the stale `predecessor_gate_id`
        # into a non-EDGE mint and stranded the instance (cr-o85.33.8).
        head_meta = head.metadata
        if head_meta.outcome is not None:
            replay = _replayed(
                composition,
                wiring,
                root,
                idempotency_key(
                    root.root_id, head.activation_id, head_meta.outcome, head_meta.node
                ),
            )
            if replay is not None:
                return replay
        view = startup_invocation(composition, root, head_meta.node, wiring=wiring)
        request = MintRequest(
            node=head_meta.node,
            mint_reason=retry,
            crew_profile=view.crew_profile,
            model=view.model,
            effort=view.effort,
            context_cap_tokens=view.context_cap_tokens,
            execution_policy=view.execution_policy,
            catalog_digest=None
            if composition.active_catalog is None
            else composition.active_catalog.digest,
            crew_version=probed_crew_version(composition, view.crew_profile),
            session_id=head_meta.session_id,
            session_mode=view.node.session_mode or SessionMode.FRESH,
            fresh_reason_override=_live_change(wiring, root, view),
            predecessor_activation_id=head.activation_id,
            inputs=head_meta.inputs,
        )
        # A retry descended from a §8.1 continuation is minted like any other
        # (and capped the same way): the dispatcher resumes the steered session
        # with the same instructions rather than relaunching the original brief
        # (§8.1, §10.2 — cr-o85.19).
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
            return CaseResult(terminal=True, terminal_node=decision.target)
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
        return CaseResult(terminal=True, terminal_node=decision.target)
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
        DeadEndKind.INPUTS_UNAVAILABLE: HALT_INPUTS_UNAVAILABLE,
        DeadEndKind.SANDBOX_UNAVAILABLE: HALT_SANDBOX_UNAVAILABLE,
        DeadEndKind.UNUSABLE_RESOLUTION: HALT_UNUSABLE_RESOLUTION,
        DeadEndKind.BOUND_VIOLATED: HALT_BOUND_VIOLATED,
    }[kind].format(
        node=activation.metadata.node, activation_id=activation.activation_id
    )
    gate = wiring.store.open_gate(root.root_id, halt_gate(reason, source=activation))
    return CaseResult(opened_gates=(gate.gate_id,))
