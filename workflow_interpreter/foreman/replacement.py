"""One original-owner successor journal for trusted and P2 replacement."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager, nullcontext
from pathlib import Path

from pydantic import TypeAdapter

from workflow_interpreter.bdio import InstanceInput, ResolvedSetting
from workflow_interpreter.bdio.rows import RowQuery
from workflow_interpreter.contractor.integration import IntegrationGuard, target_key
from workflow_interpreter.contractor.models import ContractorRecord, ContractorState
from workflow_interpreter.contractor.tracker_wiring import adapter_of
from workflow_interpreter.foreman.compose import Composition, instance_head
from workflow_interpreter.foreman.execution import effective_node
from workflow_interpreter.inspector import procfs
from workflow_interpreter.inspector.band import BandLock
from workflow_interpreter.inspector.models import Liveness
from workflow_interpreter.ledger import records as ledger_records
from workflow_interpreter.ledger.records import ContractorRecordRow
from workflow_interpreter.ledger.tasks import task_epic
from workflow_interpreter.schema.decisions import (
    ChildRecord,
    CoordinationError,
    MemberAdmission,
    MemberCapacity,
    MemberReceipt,
    TrustedReplacementIntent,
    TrustedReplacementRequest,
    digest_record,
)
from workflow_interpreter.schema.loader import load_pinned_body
from workflow_interpreter.schema.models import GraphDocument, Node, NodeKind, Outcome


def obligations(admission: MemberAdmission) -> str:
    """Protect the existing graph's authority, allowing instructions/model changes.

    Existing source/node/gate contracts remain exact; task edges may change
    only while the successful-path proof preserves review and ship obligations.
    """
    graph = load_pinned_body(admission.graph_body.encode()).document
    settings = {
        s.key: s.value
        for s in TypeAdapter(tuple[ResolvedSetting, ...]).validate_json(
            admission.config_json
        )
    }
    nodes = []
    effective = tuple(effective_node(n, settings) for n in graph.node)
    _verify_success_paths(graph, effective)
    for pinned in graph.node:
        node = effective_node(pinned, settings)
        fields = node.model_dump(mode="json")
        for key in (
            "instructions",
            "crew",
            "model",
            "effort",
            "description",
            "decision",
        ):
            fields.pop(key, None)
        nodes.append(fields)
    protected = {
        "entry": graph.graph.entry,
        "fallback": graph.fallback.model_dump(mode="json"),
        "sources": [s.model_dump(mode="json") for s in graph.source],
        "nodes": nodes,
        "gate_edges": [
            e.model_dump(mode="json")
            for e in graph.edge
            if next(n for n in effective if n.name == e.from_node).kind is NodeKind.GATE
        ],
        "verifier_pins": {k: v for k, v in settings.items() if "sha256" in k},
    }
    return hashlib.sha256(
        json.dumps(protected, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _save(composition: Composition, intent: TrustedReplacementIntent) -> None:
    store = composition.coordination_for_root(intent.owner_id, composition=composition)
    state = store.state(intent.owner_id)
    store._save(
        state.model_copy(
            update={"successors": {**state.successors, intent.request_key: intent}}
        )
    )


def advance_successor(
    composition: Composition, intent: TrustedReplacementIntent
) -> MemberReceipt:
    store = composition.coordination_for_root(intent.owner_id, composition=composition)
    saved = store.state(intent.owner_id).successors.get(intent.request_key)
    if saved is not None:
        intent = intent.model_copy(
            update={
                "predecessor_contractor_json": saved.predecessor_contractor_json,
                "successor_contractor_json": saved.successor_contractor_json,
            }
        )
    elif intent.predecessor_contractor_json is None:
        # Discovery asks the LEDGER which task owns this root (§3.2, R4): the
        # record is a row now, `root_id` is one of its projected columns, and
        # what used to be a scan over every bead's metadata is a lookup.
        matches = [
            ContractorRecord.model_validate_json(found.record_json)
            for found in _records_by_root(composition, intent.predecessor_id)
        ]
        if len(matches) > 1:
            raise CoordinationError("ambiguous predecessor contractor")
        if matches:
            matched = matches[0]
            successor = matched.next_attempt().model_copy(
                update={
                    "successor_owner": intent.owner_id,
                    "successor_key": intent.request_key,
                    "execution_base_commit": intent.admission.base_commit,
                }
            )
            intent = intent.model_copy(
                update={
                    "predecessor_contractor_json": matched.model_dump_json(
                        by_alias=True
                    ),
                    "successor_contractor_json": successor.model_dump_json(
                        by_alias=True
                    ),
                }
            )
    previous = (
        ContractorRecord.model_validate_json(intent.predecessor_contractor_json)
        if intent.predecessor_contractor_json
        else None
    )
    context = (
        BandLock(store.target_lock_path(target_key(composition, previous.target_ref)))
        if previous
        else nullcontext()
    )
    with context:
        return _advance(composition, intent)


def _advance(
    composition: Composition, intent: TrustedReplacementIntent
) -> MemberReceipt:
    """Save intent/reservation before fencing; replay repairs one immutable root."""
    store = composition.coordination_for_root(intent.owner_id, composition=composition)
    with store._locked(intent.owner_id):
        state = store.state(intent.owner_id)
        saved = state.successors.get(intent.request_key)
        if saved is not None:
            if saved.model_copy(
                update={"receipt": None, "state": "prepared"}
            ) != intent.model_copy(update={"receipt": None, "state": "prepared"}):
                raise CoordinationError("successor request payload changed")
            intent = saved
            if intent.state == "admitted" and intent.receipt is not None:
                return intent.receipt
        else:
            competing = next(
                (
                    prior
                    for prior in state.successors.values()
                    if prior.predecessor_id == intent.predecessor_id
                ),
                None,
            )
            if competing is not None:
                raise CoordinationError(
                    f"predecessor already has successor intent {competing.request_key!r}; replay that key"
                )
        predecessor = composition.reads_for_root(intent.predecessor_id).load_root(
            intent.predecessor_id
        )
        link = predecessor.metadata.coordination
        if link is None or (link.owner_id, link.slot, link.generation) != (
            intent.owner_id,
            intent.slot,
            intent.expected_generation,
        ):
            raise CoordinationError(
                "successor requires pre-admitted original owner linkage"
            )
        if (
            intent.admission.predecessor_id != predecessor.root_id
            or intent.admission.request_id != intent.request_key
            or intent.admission.slot != intent.slot
            or intent.admission.generation != link.generation + 1
        ):
            raise CoordinationError("successor admission lineage mismatch")
        with ExitStack() as members:
            process_roots = {
                predecessor.root_id,
                *(
                    r.decision_root_id
                    for r in state.requests.values()
                    if r.boundary.root_id == predecessor.root_id
                    and r.decision_root_id is not None
                ),
            }
            roots = set(process_roots)
            if intent.predecessor_contractor_json:
                contractor = ContractorRecord.model_validate_json(
                    intent.predecessor_contractor_json
                )
                if contractor.integration_digest:
                    association = IntegrationGuard(composition).association(contractor)
                    roots.update(
                        store.child_record(intent.owner_id, slot, generation).root_id
                        for slot, generation, _ in association.request.sources
                    )
            for root_id in sorted(roots):
                members.enter_context(BandLock(store.member_lock_path(root_id)))
            state = store.state(intent.owner_id)
            if state.active.get(intent.slot) != predecessor.root_id and saved is None:
                raise CoordinationError("stale successor generation")
            row = state.children.get(intent.slot)
            if row is not None and row.cancellation is not None:
                raise CoordinationError("cancelled child cannot replace")
            if any(
                any(
                    slot == intent.slot and generation == link.generation
                    for slot, generation, _ in a.request.sources
                )
                for a in state.integrations.values()
            ):
                raise CoordinationError("source receipt is bound to integration")
            if row is not None and row.collection is not None:
                raise CoordinationError("collected child cannot replace")
            for pending in state.requests.values():
                if (
                    pending.state
                    in (
                        "requested",
                        "admitted",
                        "awaiting_output",
                        "consumed",
                        "human_attention",
                    )
                    and pending.request_id != intent.decision_id
                ):
                    raise CoordinationError("unrelated decision prevents replacement")
            gates = composition.reads_for_root(predecessor.root_id).list_gates(
                predecessor.root_id
            )
            if any(
                g.status != "closed"
                or g.metadata.outcome is not None
                and (
                    g.metadata.outcome.value == "abandon"
                    or (
                        g.metadata.gate_node == "ship"
                        and g.metadata.outcome.value == "approve"
                    )
                )
                for g in gates
            ):
                raise CoordinationError("human gate prevents replacement")
            for activation in (
                a
                for root_id in process_roots
                for a in composition.reads_for_root(root_id).list_activations(root_id)
            ):
                if not activation.metadata.is_completed:
                    raise CoordinationError(
                        "replacement predecessor execution is not settled"
                    )
                from workflow_interpreter.inspector.models import LaunchReceipt
                from workflow_interpreter.inspector.paths import read_record

                paths = composition.for_root(activation.metadata.wf_root_id).paths
                launch_receipt = read_record(
                    paths.receipt(activation.activation_id), LaunchReceipt
                )
                handle = activation.metadata.handle or (
                    launch_receipt.handle if launch_receipt else None
                )
                if handle is not None:
                    proof = procfs.prove_liveness(composition.inspector_config, handle)
                    if proof.status in (Liveness.ALIVE, Liveness.INDETERMINATE):
                        raise CoordinationError(
                            "replacement predecessor process death is unproved"
                        )
            from workflow_interpreter.foreman.decisions import admission_of

            before = admission_of(
                predecessor, slot=intent.slot, generation=link.generation
            )
            if (
                obligations(before) != intent.obligation_digest
                or obligations(intent.admission) != intent.obligation_digest
            ):
                raise CoordinationError("replacement changes protected obligations")
            before_inputs = TypeAdapter(tuple[InstanceInput, ...]).validate_json(
                before.inputs_json
            )
            after_inputs = TypeAdapter(tuple[InstanceInput, ...]).validate_json(
                intent.admission.inputs_json
            )
            advisory = set()
            if intent.decision_id:
                request = state.requests.get(intent.decision_id)
                if (
                    request is None
                    or request.state not in ("consumed", "applied")
                    or request.response is None
                    or request.response.action != "replace"
                ):
                    raise CoordinationError("matching replacement decision is absent")
                if (
                    request.boundary.root_id != predecessor.root_id
                    or request.response_digest != intent.request_digest
                ):
                    raise CoordinationError("replacement decision identity mismatch")
                if saved is None:
                    from workflow_interpreter.foreman.decisions import _assert_current

                    _assert_current(composition, request)
                source = composition.reads_for_root(
                    predecessor.root_id
                ).load_activation(request.boundary.source_activation_id)
                policy = predecessor.index.nodes[source.metadata.node].decision
                if policy and policy.replacement_input:
                    advisory.add(policy.replacement_input)
                if (
                    before.graph_body != intent.admission.graph_body
                    or before.config_json != intent.admission.config_json
                ):
                    raise CoordinationError(
                        "P2 replacement cannot change graph/config pins"
                    )
            if {i.name: i for i in before_inputs if i.name not in advisory} != {
                i.name: i for i in after_inputs if i.name not in advisory
            }:
                raise CoordinationError("replacement changes required source inputs")
            _check_contractor(composition, intent)
            current = predecessor_artifact(composition, predecessor.root_id)
            if (
                intent.predecessor_contractor_json
                and ContractorRecord.model_validate_json(
                    intent.predecessor_contractor_json
                ).integration_digest
            ):
                current = ContractorRecord.model_validate_json(
                    intent.predecessor_contractor_json
                ).expected_base_commit
            if current != intent.admission.base_commit:
                raise CoordinationError("replacement base is not predecessor artifact")
            store._reserve(
                intent.owner_id,
                digest_record(intent.admission),
                MemberCapacity(
                    ceiling=store._capacity(intent.admission), kind="replacement"
                ),
                intent.admission,
                successor=intent,
            )
            _save(composition, intent)
            intent = _prepare_contractor(composition, intent)
            state = store.state(intent.owner_id)
            if state.active.get(intent.slot) == predecessor.root_id:
                store._save(
                    state.model_copy(
                        update={"active": {**state.active, intent.slot: ""}}
                    )
                )
    receipt = store.admit_member(
        intent.owner_id,
        intent.slot,
        intent.admission.generation,
        intent.admission,
        kind="replacement",
    )
    from workflow_interpreter.foreman.resolve import ensure_instance_branch

    ensure_instance_branch(
        composition,
        composition.reads_for_root(receipt.root_id).load_root(receipt.root_id),
    )
    with store._locked(intent.owner_id):
        state = store.state(intent.owner_id)
        durable = state.successors[intent.request_key]
        if durable.state == "admitted" and durable.receipt is not None:
            return durable.receipt
        prior = state.children.get(intent.slot)
        if prior is not None:
            store._save(
                state.model_copy(
                    update={
                        "children": {
                            **state.children,
                            intent.slot: ChildRecord(
                                root_id=receipt.root_id,
                                slot=intent.slot,
                                generation=intent.admission.generation,
                                wrapper_root=prior.wrapper_root,
                            ),
                        }
                    }
                )
            )
        state = store.state(intent.owner_id)
        store._save(
            state.model_copy(
                update={"active": {**state.active, intent.slot: receipt.root_id}}
            )
        )
        intent = intent.model_copy(update={"receipt": receipt})
        _save(composition, intent)
        _admit_contractor(composition, intent)
        _save(composition, intent.model_copy(update={"state": "admitted"}))
    return receipt


def replace_checked(
    composition: Composition,
    owner: str,
    slot: str,
    generation: int,
    request: TrustedReplacementRequest,
) -> MemberReceipt:
    from workflow_interpreter.foreman.children import checked_admission
    from workflow_interpreter.foreman.decisions import admission_of

    store = composition.coordination_for_root(owner, composition=composition)
    saved = store.state(owner).successors.get(request.request_key)
    if saved is not None:
        if saved.request_digest != digest_record(request):
            raise CoordinationError("successor request payload changed")
        if (saved.owner_id, saved.slot, saved.expected_generation) != (
            owner,
            slot,
            generation,
        ):
            raise CoordinationError(
                "saved successor scope differs from requested owner/slot/generation"
            )
        return advance_successor(composition, saved)
    admission = checked_admission(
        composition,
        Path(request.graph),
        slot,
        {k: Path(v) for k, v in request.inputs.items()},
    )
    predecessor_id = store.state(owner).active.get(slot)
    if not predecessor_id:
        raise CoordinationError("active predecessor missing")
    predecessor = composition.reads_for_root(predecessor_id).load_root(predecessor_id)
    before = admission_of(predecessor, slot=slot, generation=generation)
    admission = admission.model_copy(
        update={
            "generation": generation + 1,
            "base_commit": instance_head(
                composition.git, composition.config.repo_root, predecessor_id
            ),
            "predecessor_id": predecessor_id,
            "request_id": request.request_key,
            "essential_inputs": before.essential_inputs,
            "essential_consumers": before.essential_consumers,
        }
    )
    intent = TrustedReplacementIntent(
        request_key=request.request_key,
        request_digest=digest_record(request),
        reason=request.reason,
        owner_id=owner,
        slot=slot,
        expected_generation=generation,
        predecessor_id=predecessor_id,
        admission=admission,
        obligation_digest=obligations(before),
    )
    integration = next(
        (
            a
            for a in store.state(owner).integrations.values()
            if a.receipt and a.receipt.root_id == predecessor_id
        ),
        None,
    )
    if integration is not None:
        from workflow_interpreter.contractor.integration import replace_integration

        return replace_integration(composition, integration, intent)
    return advance_successor(composition, intent)


def _check_contractor(
    composition: Composition, intent: TrustedReplacementIntent
) -> None:
    if intent.predecessor_contractor_json is None:
        return
    from workflow_interpreter.contractor.landing import (
        LANDING_INTENT_FILE,
        LANDING_RECEIPT_FILE,
    )

    previous = ContractorRecord.model_validate_json(intent.predecessor_contractor_json)
    paths = composition.for_root(intent.predecessor_id).paths
    if previous.state is ContractorState.LANDED or any(
        (paths.instance_dir / name).exists()
        for name in (LANDING_INTENT_FILE, LANDING_RECEIPT_FILE)
    ):
        raise CoordinationError(
            "uncertain or observed landing must recover before replacement"
        )
    if (
        composition.git.ref_target(
            previous.target_ref, cwd=composition.config.repo_root
        )
        != previous.expected_base_commit
    ):
        raise CoordinationError("replacement lost contractor target base")
    adapter = adapter_of(composition)
    root = composition.reads_for_root(intent.predecessor_id).load_root(
        intent.predecessor_id
    )
    # The LEDGER answers which epic this stage was minted under (§3.7, R8).
    # It used to be a bd `show` from inside `foreman/` — a tracker read on the
    # wrong side of §3.1, reachable from replacement coordination — and the
    # ledger already holds the pair prepare wrote, so no tracker is needed to
    # answer it at all. A task with no row is not contradicted by one.
    stage_epic = (
        None
        if composition.ledger is None
        else task_epic(composition.ledger, previous.stage_id)
    )
    if previous.root_id != root.root_id or (
        stage_epic is not None and stage_epic != previous.epic_id
    ):
        raise CoordinationError("contractor stage/member ownership mismatch")
    if (
        previous.integration_digest is None
        and previous.successor_key is None
        and (
            root.metadata.instance_key != previous.instance_key
            or root.metadata.instance_base_commit != previous.expected_base_commit
        )
    ):
        raise CoordinationError("legacy contractor key/base ownership mismatch")
    current = adapter.record(previous.stage_id)
    if current != previous and (current.successor_owner, current.successor_key) != (
        intent.owner_id,
        intent.request_key,
    ):
        raise CoordinationError("contractor predecessor association changed")
    if previous.integration_digest:
        guard = IntegrationGuard(composition)
        association = guard.binding(previous, current=False)
        existing = (
            guard.coordination(intent.owner_id)
            .state(intent.owner_id)
            .integrations.get(intent.request_key)
        )
        if existing is not None and (
            existing.predecessor_digest != association.identity_digest
            or existing.admission != intent.admission
        ):
            raise CoordinationError(
                "integration successor key conflicts with an existing association"
            )
        guard.sources(association.request)
        if association.authorization:
            raise CoordinationError("integration landing authority already observed")


def _prepare_contractor(
    composition: Composition, intent: TrustedReplacementIntent
) -> TrustedReplacementIntent:
    if (
        intent.successor_contractor_json is None
        or intent.predecessor_contractor_json is None
    ):
        return intent
    previous = ContractorRecord.model_validate_json(intent.predecessor_contractor_json)
    successor = ContractorRecord.model_validate_json(intent.successor_contractor_json)
    adapter = adapter_of(composition)
    adapter.integration_guard = IntegrationGuard(composition)
    if previous.integration_digest:
        from workflow_interpreter.schema.decisions import (
            IntegrationAssociation,
            IntegrationTargetClaim,
        )

        guard = adapter.integration_guard
        association = guard.association(previous)
        request = association.request.model_copy(
            update={"request_key": intent.request_key}
        )
        candidate = IntegrationAssociation(
            request=request,
            request_digest=digest_record(request),
            target_key=association.target_key,
            target_ref=association.target_ref,
            base_commit=association.base_commit,
            admission=intent.admission,
            admission_digest=digest_record(intent.admission),
            manifest_digest=association.manifest_digest,
            verification_policy_json=association.verification_policy_json,
            attempt=successor.attempt,
            previous_attempts=successor.previous_attempts,
            predecessor_digest=association.identity_digest,
        )
        existing = (
            guard.coordination(intent.owner_id)
            .state(intent.owner_id)
            .integrations.get(intent.request_key)
        )
        if (
            existing is not None
            and existing.identity_digest != candidate.identity_digest
        ):
            raise CoordinationError("integration successor payload changed")
        claim = guard.claim(association.target_key)
        if (
            claim is None
            or claim[1].disposition != "active"
            or claim[1].key != association.target_key
            or claim[1].owner_id != intent.owner_id
            or claim[1].stage_id != previous.stage_id
            or claim[1].association_digest
            not in (association.identity_digest, candidate.identity_digest)
        ):
            raise CoordinationError("integration successor lost target claim")
        successor = successor.model_copy(
            update={
                "integration_digest": candidate.identity_digest,
                "integration_owner": intent.owner_id,
                "integration_slot": intent.slot,
                "integration_generation": intent.admission.generation,
            }
        )
        candidate = candidate.model_copy(
            update={"contractor_digest": digest_record(successor)}
        )
        if existing is None:
            guard.save(candidate)
        guard.write_claim(
            IntegrationTargetClaim(
                key=candidate.target_key,
                owner_id=intent.owner_id,
                stage_id=previous.stage_id,
                request_digest=candidate.request_digest,
                association_digest=candidate.identity_digest,
                attempt=candidate.attempt,
            )
        )
        guard.save(association.model_copy(update={"state": "stale"}))
        intent = intent.model_copy(
            update={
                "successor_contractor_json": successor.model_dump_json(by_alias=True)
            }
        )
        _save(composition, intent)
    current = adapter.record(previous.stage_id)
    if current == previous:
        adapter.prepare(previous.stage_id, successor)
    elif (
        current.model_copy(update={"state": ContractorState.PREPARED, "root_id": None})
        != successor
    ):
        raise CoordinationError("successor contractor binding differs")
    return intent


def _admit_contractor(
    composition: Composition, intent: TrustedReplacementIntent
) -> None:
    if intent.successor_contractor_json is None:
        return
    assert intent.receipt is not None
    successor = ContractorRecord.model_validate_json(intent.successor_contractor_json)
    adapter = adapter_of(composition)
    guard = IntegrationGuard(composition)
    adapter.integration_guard = guard
    if successor.integration_digest:
        association = guard.association(successor)
        guard.save(
            association.model_copy(
                update={"receipt": intent.receipt, "state": "root_bound"}
            )
        )
    current = adapter.record(successor.stage_id)
    if current.state is ContractorState.PREPARED:
        adapter.admit(successor.stage_id, successor, root_id=intent.receipt.root_id)
    elif current != successor.admitted(intent.receipt.root_id):
        raise CoordinationError("admitted successor contractor differs")
    if successor.integration_digest:
        guard.save(
            guard.association(successor).model_copy(update={"state": "admitted"})
        )


def guard_contractor(composition: Composition, record: ContractorRecord) -> None:
    """Fence stale predecessors and bind B (CAS) separately from A (execution)."""
    if record.root_id:
        root = composition.reads_for_root(record.root_id).load_root(record.root_id)
        link = root.metadata.coordination
        if link is not None:
            state = composition.coordination_for_root(
                link.owner_id, composition=composition
            ).state(link.owner_id)
            current_intent = state.successors.get(link.request_id or "")
            if (
                current_intent
                and current_intent.successor_contractor_json
                and (record.successor_owner, record.successor_key)
                != (link.owner_id, link.request_id)
            ):
                raise CoordinationError("cannot strip successor contractor authority")
            if any(
                i.predecessor_id == record.root_id for i in state.successors.values()
            ):
                raise CoordinationError("contractor predecessor was superseded")
    if record.successor_key is None:
        if (
            record.successor_owner is not None
            or record.execution_base_commit is not None
        ):
            raise CoordinationError("incomplete successor contractor authority")
        return
    if record.successor_owner is None:
        raise CoordinationError("successor owner missing")
    store = composition.coordination_for_root(
        record.successor_owner, composition=composition
    )
    intent = store.state(record.successor_owner).successors.get(record.successor_key)
    if (
        intent is None
        or intent.successor_contractor_json is None
        or intent.receipt is None
    ):
        raise CoordinationError("successor contractor receipt missing")
    prepared = ContractorRecord.model_validate_json(intent.successor_contractor_json)
    normalized = record.model_copy(
        update={
            "state": ContractorState.PREPARED,
            "root_id": None,
            "landed_oid": None,
            "tree": None,
            "gate_receipt_digest": None,
            "landing_receipt_digest": None,
        }
    )
    if normalized != prepared or record.root_id != intent.receipt.root_id:
        raise CoordinationError("successor contractor binding mismatch")
    root = composition.reads_for_root(intent.receipt.root_id).load_root(
        intent.receipt.root_id
    )
    # `validate_member` reads the OWNER's ledger about this member, so both it
    # and the reservation lookup belong on the owner's store, not the member's.
    owner_store = composition.coordination_for_root(
        intent.owner_id, composition=composition
    )
    reservation = owner_store.state(intent.owner_id).reservations.get(
        digest_record(intent.admission)
    )
    if (
        reservation is None
        or reservation.root_id != root.root_id
        or root.metadata.coordination != intent.receipt.link
        or root.metadata.instance_base_commit != intent.admission.base_commit
        or record.execution_base_commit != intent.admission.base_commit
        or root.definition.content_hash
        != hashlib.sha256(intent.admission.graph_body.encode()).hexdigest()
        or TypeAdapter(tuple[ResolvedSetting, ...])
        .dump_json(root.metadata.resolved_config)
        .decode()
        != intent.admission.config_json
        or TypeAdapter(tuple[InstanceInput, ...])
        .dump_json(root.metadata.instance_inputs)
        .decode()
        != intent.admission.inputs_json
    ):
        raise CoordinationError("successor admission receipt mismatch")
    if not record.integration_digest:
        owner_store.validate_member(root)


@contextmanager
def contractor_landing_locks(
    composition: Composition, record: ContractorRecord
) -> Iterator[None]:
    shared = composition.store.coordination_store(composition=composition)
    if record.root_id is None:
        raise CoordinationError("contractor root missing")
    root = composition.reads_for_root(record.root_id).load_root(record.root_id)
    link = root.metadata.coordination
    if link is None:
        yield
        return
    owner_store = composition.coordination_for_root(
        link.owner_id, composition=composition
    )
    with (
        BandLock(shared.target_lock_path(target_key(composition, record.target_ref))),
        owner_store._locked(link.owner_id),
        BandLock(shared.member_lock_path(root.root_id, root=root)),
    ):
        guard_contractor(composition, record)
        yield


def repair_contractor_successor(composition: Composition, stage_id: str) -> None:
    """Repair saved successor intent from the normal stage handle after a crash."""
    from workflow_interpreter.schema.decisions import CoordinationState

    store = composition.store.coordination_store(composition=composition)
    for row in store._client.find_rows(RowQuery(metadata_filters={"wf_kind": "root"})):
        raw = row.metadata.get("coordination_state")
        if raw is None:
            continue
        state = CoordinationState.model_validate(raw)
        for intent in state.successors.values():
            if intent.state == "prepared" and intent.predecessor_contractor_json:
                previous = ContractorRecord.model_validate_json(
                    intent.predecessor_contractor_json
                )
                if previous.stage_id == stage_id:
                    advance_successor(composition, intent)


def predecessor_artifact(composition: Composition, root_id: str) -> str:
    """An instance branch name alone is not artifact authority."""
    reads = composition.reads_for_root(root_id)
    root = reads.load_root(root_id)
    acts = reads.list_activations(root_id)
    artifacts = [
        (a.metadata.seq, a.metadata.evidence.artifact)
        for a in acts
        if a.metadata.evidence is not None and a.metadata.evidence.artifact is not None
    ]
    expected = root.metadata.instance_base_commit
    if artifacts:
        _, artifact = max(artifacts, key=lambda pair: pair[0])
        if (
            composition.git.tree_oid(
                artifact.commit_oid, cwd=composition.config.repo_root
            )
            != artifact.tree_oid
        ):
            raise CoordinationError("predecessor artifact tree mismatch")
        expected = artifact.commit_oid
    current = instance_head(composition.git, composition.config.repo_root, root_id)
    if (
        current != expected
        or root.metadata.instance_base_commit is None
        or not composition.git.is_ancestor(
            root.metadata.instance_base_commit,
            current,
            cwd=composition.config.repo_root,
        )
    ):
        raise CoordinationError("predecessor branch lacks computed artifact authority")
    return current


def _verify_success_paths(graph: GraphDocument, nodes: tuple[Node, ...]) -> None:
    """Prove the existing reviewer/ship obligations on successful writer paths."""
    index = {node.name: node for node in nodes}
    writers = {node.name for node in nodes if node.writes}
    produced = {
        source.name
        for source in graph.source
        if source.producer in {"node:" + name for name in writers}
    }
    reviewers = {
        node.name
        for node in nodes
        if Outcome.ACCEPT in (node.outcomes or ())
        and produced.intersection(node.inputs or ())
    }
    ship = index.get("ship")
    protect_ship = ship is not None and ship.kind is NodeKind.GATE
    if not reviewers and not protect_ship:
        return
    abandoned = {edge.to for edge in graph.edge if edge.on is Outcome.ABANDON}
    if index[graph.fallback.to].kind is NodeKind.TERMINAL:
        abandoned.add(graph.fallback.to)
    edges = {
        name: tuple(edge for edge in graph.edge if edge.from_node == name)
        for name in index
    }
    for writer in writers:
        writer_sources = {
            source.name
            for source in graph.source
            if source.producer == "node:" + writer
        }
        required_reviewers = {
            name
            for name in reviewers
            if writer_sources.intersection(index[name].inputs or ())
        }
        pending = [
            (edge.to, False, False)
            for edge in edges[writer]
            if edge.on in (Outcome.DONE, Outcome.NO_DIFF)
        ]
        visited = set()
        while pending:
            name, reviewed, approved = pending.pop()
            state = (name, reviewed, approved)
            if state in visited or name in abandoned:
                continue
            visited.add(state)
            node = index[name]
            if node.kind is NodeKind.TERMINAL:
                if (required_reviewers and not reviewed) or (
                    protect_ship and not approved
                ):
                    raise CoordinationError(
                        "successful writer path bypasses protected review/ship obligations"
                    )
                continue
            if name == writer:
                reviewed = approved = False
            elif name in writers:
                approved = False
            for edge in edges[name]:
                if edge.on is Outcome.ABANDON:
                    continue
                next_reviewed = reviewed or (
                    name in required_reviewers and edge.on is Outcome.ACCEPT
                )
                next_approved = approved or (
                    name == "ship"
                    and edge.on is Outcome.APPROVE
                    and (next_reviewed or not required_reviewers)
                )
                pending.append((edge.to, next_reviewed, next_approved))


def _records_by_root(
    composition: Composition, root_id: str
) -> tuple[ContractorRecordRow, ...]:
    """Every contractor record naming this root, or none without a ledger.

    A wiring with no ledger holds no records at all, and discovery answering
    "nothing owns this root" is the same thing it answered before S4 when no
    bead carried one.
    """
    if composition.ledger is None:
        return ()
    return ledger_records.by_root(composition.ledger, root_id)
