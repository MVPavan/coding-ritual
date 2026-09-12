"""Reconcile decision intent, then tick an ordinary independently pinned task."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import TYPE_CHECKING

from pydantic import TypeAdapter, ValidationError

from workflow_interpreter.bdio.carriers import InstanceInput, ResolvedSetting
from workflow_interpreter.bdio.client import STATUS_CLOSED
from workflow_interpreter.bdio.records import ActivationRecord, RootRecord
from workflow_interpreter.foreman.compose import (
    Composition,
    InstanceWiring,
    instance_head,
)
from workflow_interpreter.foreman.envelope import InputsUnavailable
from workflow_interpreter.foreman.execution import resolved_node
from workflow_interpreter.foreman.routing import route
from workflow_interpreter.schema.decisions import (
    BoundaryIdentity,
    CoordinationError,
    DecisionConsumption,
    DecisionRequest,
    DecisionResponse,
    MemberAdmission,
    digest_record,
    parse_response,
)
from workflow_interpreter.schema.loader import canonical_bytes
from workflow_interpreter.schema.models import DecisionTrigger, Outcome
from workflow_interpreter.supervisor.errors import GitCommandError, LockUnavailable
from workflow_interpreter.supervisor.gitcmd import GitSubcommand

if TYPE_CHECKING:
    from workflow_interpreter.foreman.tick import TickReport


def admission_of(root: RootRecord, *, slot: str, generation: int) -> MemberAdmission:
    """Reusable complete admission body for initial/replacement/P3 child runs."""
    if root.metadata.instance_base_commit is None:
        raise CoordinationError("member has no pinned base")
    return MemberAdmission(
        graph_body=canonical_bytes(root.definition.document).decode(),
        config_json=TypeAdapter(tuple[ResolvedSetting, ...])
        .dump_json(root.metadata.resolved_config)
        .decode(),
        inputs_json=TypeAdapter(tuple[InstanceInput, ...])
        .dump_json(root.metadata.instance_inputs)
        .decode(),
        base_commit=root.metadata.instance_base_commit,
        slot=slot,
        generation=generation,
        templates=root.metadata.decision_templates or {},
        essential_inputs=root.metadata.essential_inputs or (),
        essential_consumers=root.metadata.essential_consumers or {},
    )


def queue_boundary(
    composition: Composition,
    wiring: InstanceWiring,
    root: RootRecord,
    source: ActivationRecord,
    kind: DecisionTrigger,
    *,
    route_digest: str = "",
) -> bool:
    """Called with member band held; no owner writes or locks here."""
    policy = resolved_node(root, source.metadata.node).node.decision
    if policy is None or kind not in policy.triggers:
        return False
    link = root.metadata.coordination
    if link is None:
        raise CoordinationError("decision member is not initialized")
    graph_route = route(
        root.index,
        root.index.nodes[source.metadata.node],
        source.metadata.outcome or Outcome.FAIL_PLAN,
    )
    commit = instance_head(composition.git, wiring.repo_root, root.root_id)
    boundary = BoundaryIdentity(
        owner_id=link.owner_id,
        root_id=root.root_id,
        generation=link.generation,
        graph_hash=root.definition.content_hash,
        config_signature=root.metadata.config_signature,
        source_activation_id=source.activation_id,
        kind=kind,
        route_digest=route_digest or digest_record(graph_route),
        artifact_commit=commit,
        artifact_tree=composition.git.tree_oid(commit, cwd=wiring.repo_root),
        policy_digest=digest_record(policy),
    )
    coordinator = wiring.store.coordination_store()
    prior = coordinator.state(link.owner_id).requests.get(digest_record(boundary))
    if (
        prior is not None
        and prior.state == "applied"
        and prior.response is not None
        and prior.response.action == "continue_declared"
    ):
        return False
    wiring.store.queue_decision(root.root_id, boundary)
    return True


def _assert_current(composition: Composition, request: DecisionRequest) -> RootRecord:
    """State/artifact/authority check repeated immediately before consumption."""
    boundary = request.boundary
    root = composition.store.reads.load_root(boundary.root_id)
    composition.store.coordination_store().validate_member(root)
    if root.metadata.decision_boundary != boundary:
        raise CoordinationError("stale boundary")
    if (
        root.definition.content_hash != boundary.graph_hash
        or root.metadata.config_signature != boundary.config_signature
    ):
        raise CoordinationError("stale graph/config")
    if any(
        g.metadata.state.value == "open"
        for g in composition.store.reads.list_gates(root.root_id)
    ):
        raise CoordinationError("human gate prevents decision consumption")
    source = composition.store.reads.load_activation(boundary.source_activation_id)
    policy = root.index.nodes[source.metadata.node].decision
    if (
        policy is None
        or digest_record(policy) != boundary.policy_digest
        or not source.metadata.is_completed
    ):
        raise CoordinationError("stale source/policy")
    acts = composition.store.reads.list_activations(root.root_id)
    if (
        max(acts, key=lambda a: int(a.metadata.seq)).activation_id
        != source.activation_id
    ):
        raise CoordinationError("source is not current head")
    commit = instance_head(composition.git, composition.config.repo_root, root.root_id)
    if (
        commit != boundary.artifact_commit
        or composition.git.tree_oid(commit, cwd=composition.config.repo_root)
        != boundary.artifact_tree
    ):
        raise CoordinationError("source artifact changed")
    return root


def _request_body(request: DecisionRequest) -> str:
    boundary = request.boundary
    content = {
        "request_id": request.request_id,
        "request_digest": digest_record(boundary),
        "parent_generation": boundary.generation,
        "artifact_digest": boundary.artifact_tree,
        "actions": request.actions,
        "boundary": boundary.model_dump(mode="json"),
    }
    return (
        "Write one strict JSON object to $WF_ARTIFACT_DIR/decision.json. Fields: "
        "version=1, request_id, request_digest, parent_generation, artifact_digest, "
        "producing_root_id and producing_activation_id (from the execution identity below), "
        "action, rationale, optional revision. Use only permitted actions. "
        "Revision is required for replace; it is advisory and cannot change requirements or authority. "
        "Then emit no_diff and empty effects using the normal channel protocol.\n"
        "DECISION_REQUEST_JSON\n"
        + json.dumps(content, sort_keys=True)
        + "\nEND_DECISION_REQUEST_JSON"
    )


def _admit_decision(composition: Composition, request: DecisionRequest) -> None:
    root = _assert_current(composition, request)
    source = composition.store.reads.load_activation(
        request.boundary.source_activation_id
    )
    template = (root.metadata.decision_templates or {})[source.metadata.node]
    body = _request_body(request)
    input_item = InstanceInput(
        name="decision_request",
        body=body,
        sha256=hashlib.sha256(body.encode()).hexdigest(),
    )
    admission = MemberAdmission(
        graph_body=template.graph_body,
        config_json=template.config_json,
        inputs_json=TypeAdapter(tuple[InstanceInput, ...])
        .dump_json((input_item,))
        .decode(),
        base_commit=request.boundary.artifact_commit,
        slot=f"decision-{request.request_id}",
        generation=0,
        request_id=request.request_id,
    )
    coordinator = composition.store.coordination_store()
    receipt = coordinator.admit_member(
        request.boundary.owner_id, admission.slot, 0, admission, kind="decision"
    )
    from workflow_interpreter.foreman.resolve import ensure_instance_branch

    ensure_instance_branch(
        composition, composition.store.reads.load_root(receipt.root_id)
    )
    with coordinator._locked(request.boundary.owner_id):
        current = coordinator.state(request.boundary.owner_id).requests[
            request.request_id
        ]
        coordinator._update_request(
            request.boundary.owner_id,
            current.model_copy(
                update={"state": "admitted", "decision_root_id": receipt.root_id}
            ),
        )


def _read_response(
    composition: Composition, request: DecisionRequest
) -> DecisionResponse:
    if request.decision_root_id is None or request.attempt_id is None:
        raise CoordinationError("missing decision attempt")
    decision_root = composition.store.reads.load_root(request.decision_root_id)
    composition.store.coordination_store().validate_member(decision_root)
    activation = composition.store.reads.load_activation(request.attempt_id)
    evidence = activation.metadata.evidence
    if (
        activation.metadata.wf_root_id != decision_root.root_id
        or not activation.metadata.is_completed
        or activation.bead.status != STATUS_CLOSED
        or activation.metadata.outcome is not Outcome.NO_DIFF
        or evidence is None
        or evidence.outputs_ref is None
        or evidence.outputs_tree_oid is None
    ):
        raise CoordinationError("decision lacks successful immutable output evidence")
    latest = max(
        composition.store.reads.list_activations(decision_root.root_id),
        key=lambda a: int(a.metadata.seq),
    )
    if latest.activation_id != activation.activation_id:
        raise CoordinationError("decision output belongs to stale attempt")
    if (
        composition.git.tree_oid(evidence.outputs_ref, cwd=composition.config.repo_root)
        != evidence.outputs_tree_oid
    ):
        raise CoordinationError("decision output reference changed")
    body = composition.git.bounded_text(
        GitSubcommand.CAT_FILE,
        "blob",
        f"{evidence.outputs_tree_oid}:decision.json",
        cwd=composition.config.repo_root,
        limit=16384,
    )
    return parse_response(body)


def _apply(composition: Composition, request: DecisionRequest) -> None:
    """Saved consumption is the action intent; repair it without another model."""
    coordinator = composition.store.coordination_store()
    response = request.response
    if response is None:
        raise CoordinationError("consumed request lost its response")
    owner = request.boundary.owner_id
    replacement_id = None
    if response.action == "human":
        child = next(
            (
                r
                for r in coordinator.state(owner).children.values()
                if r.root_id == request.boundary.root_id
            ),
            None,
        )
        if child is None:
            coordinator.attention(owner, response.rationale)
        else:
            coordinator.update_child(
                owner,
                child.model_copy(
                    update={
                        "attention": response.rationale[:2048],
                        "attention_source": "decision",
                    }
                ),
            )
    elif response.action == "replace":
        predecessor = composition.store.reads.load_root(request.boundary.root_id)
        source = composition.store.reads.load_activation(
            request.boundary.source_activation_id
        )
        policy = predecessor.index.nodes[source.metadata.node].decision
        if (
            policy is None
            or policy.replacement_input is None
            or not response.revision
            or not response.revision.strip()
        ):
            raise CoordinationError("replacement requires essential advisory input")
        assert predecessor.metadata.coordination is not None
        base = admission_of(
            predecessor,
            slot=predecessor.metadata.coordination.slot,
            generation=request.boundary.generation + 1,
        )
        # Preserve original inputs/requirements; revision only replaces the designated advisory source.
        item = InstanceInput(
            name=policy.replacement_input,
            body=response.revision,
            sha256=hashlib.sha256(response.revision.encode()).hexdigest(),
        )
        inputs = tuple(
            x for x in predecessor.metadata.instance_inputs if x.name != item.name
        ) + (item,)
        admission = base.model_copy(
            update={
                "base_commit": request.boundary.artifact_commit,
                "inputs_json": TypeAdapter(tuple[InstanceInput, ...])
                .dump_json(inputs)
                .decode(),
                "essential_inputs": tuple(
                    dict.fromkeys((*base.essential_inputs, item.name))
                ),
                "essential_consumers": {
                    **base.essential_consumers,
                    item.name: tuple(
                        n.name
                        for n in predecessor.definition.document.node
                        if item.name in (n.inputs or ())
                    ),
                },
                "predecessor_id": predecessor.root_id,
                "request_id": request.request_id,
            }
        )
        # Replacement advice is runtime-essential. Refuse known essential overflow before fencing.
        from workflow_interpreter.foreman.inputs import DefaultComposer, Materialized

        preview = predecessor.model_copy(
            update={
                "metadata": predecessor.metadata.model_copy(
                    update={
                        "instance_inputs": inputs,
                        "essential_inputs": admission.essential_inputs,
                    }
                )
            }
        )
        for consumer in predecessor.definition.document.node:
            if item.name not in (consumer.inputs or ()):
                continue
            task = source.model_copy(
                update={
                    "metadata": source.metadata.model_copy(
                        update={"node": consumer.name}
                    )
                }
            )
            available = tuple(
                Materialized(name=i.name, producer="instance", text=i.body)
                for i in inputs
                if i.name in (consumer.inputs or ())
            )
            DefaultComposer().envelope(preview, task, available)
        from workflow_interpreter.foreman.replacement import (
            advance_successor,
            obligations,
        )
        from workflow_interpreter.schema.decisions import TrustedReplacementIntent

        receipt = advance_successor(
            composition,
            TrustedReplacementIntent(
                request_key=request.request_id,
                request_digest=request.response_digest or "",
                reason=response.rationale,
                owner_id=owner,
                slot=base.slot,
                expected_generation=request.boundary.generation,
                predecessor_id=predecessor.root_id,
                admission=admission,
                obligation_digest=obligations(base),
                decision_id=request.request_id,
            ),
        )
        replacement_id = receipt.root_id
    with coordinator._locked(owner):
        current = coordinator.state(owner).requests[request.request_id]
        coordinator._update_request(
            owner,
            current.model_copy(
                update={"state": "applied", "replacement_id": replacement_id}
            ),
        )


def reconcile_action(
    composition: Composition, owner_id: str, request_id: str
) -> DecisionConsumption:
    """Repair only a saved consumption intent; reusable by bridge orchestration."""
    coordinator = composition.store.coordination_store()
    request = coordinator.state(owner_id).requests[request_id]
    if (
        request.state not in ("consumed", "applied")
        or request.response is None
        or request.response_digest is None
    ):
        raise CoordinationError("action has no durable consumption intent")
    if request.state == "consumed":
        _apply(composition, request)
        request = coordinator.state(owner_id).requests[request_id]
    assert request.response is not None and request.response_digest is not None
    return DecisionConsumption(
        request_id=request_id,
        response_digest=request.response_digest,
        action=request.response.action,
        applied=request.state == "applied",
        replacement_id=request.replacement_id,
    )


def advance_decision(
    composition: Composition, root_id: str, tick_local: Callable[[str], TickReport]
) -> TickReport:
    """Public Foreman tick: reconcile at most one action or ordinary member tick."""
    from workflow_interpreter.foreman.tick import TickReport

    root = composition.store.reads.load_root(root_id)
    coordinator = composition.store.coordination_store()
    link = root.metadata.coordination
    if link is None:
        return tick_local(root_id)
    owner = link.owner_id
    pending: DecisionRequest | None = None
    child_slot: str | None = None

    def attention(reason: str) -> None:
        if child_slot is None:
            coordinator.attention(owner, reason)
        else:
            row = coordinator.child_record(owner, child_slot, link.generation)
            coordinator.update_child(
                owner,
                row.model_copy(
                    update={"attention": reason[:2048], "attention_source": "runtime"}
                ),
            )

    try:
        state = coordinator.state(owner)
        repair = next(
            (
                i
                for i in state.successors.values()
                if i.state == "prepared"
                and (root_id == owner or i.predecessor_id == root_id)
            ),
            None,
        )
        if repair is not None:
            from workflow_interpreter.foreman.replacement import advance_successor

            advance_successor(composition, repair)
            if repair.decision_id:
                reconcile_action(composition, owner, repair.decision_id)
            return TickReport(blocked=True)
        if state.human_attention:
            return TickReport(halted=True, stalled=state.human_attention)
        child = state.children.get(link.slot)
        if child is not None and child.root_id == root_id:
            child_slot = link.slot
            if child.cancellation is not None or child.collection is not None:
                return TickReport(
                    halted=True, stalled="child is cancelled or collected"
                )
            if child.attention and not child.attention.startswith("waiting at gate "):
                return TickReport(halted=True, stalled=child.attention)
        # Explicit commands to stale children refuse; the original owner is the durable run handle.
        if root_id != owner:
            coordinator.validate_member(root)
        pending = next(
            (
                r
                for r in state.requests.values()
                if r.state not in ("applied", "human_attention", "invalidated")
                and (
                    r.boundary.root_id == state.active.get(child_slot or "work")
                    or (r.state == "consumed" and r.request_id in state.successors)
                )
            ),
            None,
        )
        if pending is not None:
            if pending.state == "requested":
                _admit_decision(composition, pending)
                return TickReport(blocked=True)
            if pending.state == "consumed":
                reconcile_action(composition, owner, pending.request_id)
                return TickReport(blocked=True)
            if pending.decision_root_id is None:
                raise CoordinationError("missing admitted decision root")
            decision = composition.store.reads.load_root(pending.decision_root_id)
            acts = composition.store.reads.list_activations(decision.root_id)
            latest = max(acts, key=lambda a: int(a.metadata.seq), default=None)
            if latest is not None and pending.attempt_id != latest.activation_id:
                with coordinator._locked(owner):
                    current = coordinator.state(owner).requests[pending.request_id]
                    coordinator._update_request(
                        owner,
                        current.model_copy(
                            update={
                                "attempt_id": latest.activation_id,
                                "state": "awaiting_output",
                                "envelope_reference": f"wf-activation://{latest.activation_id}/envelope",
                                "envelope_sha256": (latest.metadata.envelope or {}).get(
                                    "sha256"
                                ),
                            }
                        ),
                    )
                return TickReport(blocked=True)
            if decision.metadata.terminal is not None:
                if decision.metadata.terminal != "decision_done":
                    raise CoordinationError("ordinary decision execution failed")

                # Serialize validation against parent fencing and dispatch.
                def verify(current: DecisionRequest) -> DecisionResponse:
                    with composition.for_root(current.boundary.root_id).band:
                        _assert_current(composition, current)
                        return _read_response(composition, current)

                response = _read_response(composition, pending)
                composition.store.coordination_store(
                    verify_decision=verify
                ).consume_decision(owner, pending.request_id, response)
                return TickReport(blocked=True)
            report = tick_local(decision.root_id)
            if (
                report.halted
                or report.stalled
                or report.opened_gate
                or report.waiting_gate
            ):
                raise CoordinationError(
                    f"decision execution needs human attention: {report.model_dump_json()}"
                )
            return report.model_copy(update={"terminal": False, "terminal_node": None})
        active_id = state.active.get(child_slot or "work")
        if not active_id:
            raise CoordinationError("active member admission is incomplete")
        active = composition.store.reads.load_root(active_id)
        boundary = active.metadata.decision_boundary
        if boundary is not None and digest_record(boundary) not in state.requests:
            source = composition.store.reads.load_activation(
                boundary.source_activation_id
            )
            policy = active.index.nodes[source.metadata.node].decision
            if policy is None:
                raise CoordinationError("boundary has no policy")
            actions = tuple(
                a
                for a in policy.actions
                if a != "continue_declared" or boundary.kind in ("fail_plan", "doubt")
            )
            if not actions:
                raise CoordinationError("boundary has no authorized action")
            coordinator.open_decision(boundary, actions)
            return TickReport(blocked=True)
        report = tick_local(active_id)
        if report.stalled is not None:
            attention(report.stalled)
        return report
    except LockUnavailable:
        return TickReport(contended=True)
    except (
        CoordinationError,
        ValidationError,
        InputsUnavailable,
        json.JSONDecodeError,
        GitCommandError,
    ) as exc:
        with coordinator._locked(owner):
            if pending is not None:
                current = coordinator.state(owner).requests[pending.request_id]
                rejected_tree = None
                if current.attempt_id is not None:
                    evidence = composition.store.reads.load_activation(
                        current.attempt_id
                    ).metadata.evidence
                    rejected_tree = (
                        None if evidence is None else evidence.outputs_tree_oid
                    )
                coordinator._update_request(
                    owner,
                    current.model_copy(
                        update={
                            "state": "human_attention",
                            "reason": str(exc),
                            "rejected_output_tree": rejected_tree,
                        }
                    ),
                )
        attention(str(exc))
        return TickReport(halted=True, stalled=str(exc))
