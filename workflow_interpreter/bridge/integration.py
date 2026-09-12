"""Explicit source-set admission and forward-only integration authority.

The only scheduler is Foreman; the only capacity ledger is CoordinationStore.
A durable target claim outlives short locks and execution processes.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from workflow_interpreter.schema.decisions import (
        MemberReceipt,
        TrustedReplacementIntent,
    )

from pydantic import TypeAdapter

from workflow_interpreter.bdio import InstanceInput, ResolvedSetting
from workflow_interpreter.bdio.roots import MAX_INSTANCE_INPUT_BYTES
from workflow_interpreter.bdio.wire import Metadata
from workflow_interpreter.bridge.adapter import PhaseAdapter
from workflow_interpreter.bridge.errors import BridgeRefusal
from workflow_interpreter.bridge.models import PhaseBridgeRecord, PhaseBridgeState
from workflow_interpreter.bridge.verification import VerificationPolicy
from workflow_interpreter.foreman.compose import Composition
from workflow_interpreter.foreman.execution import resolved_node
from workflow_interpreter.foreman.resolve import _resolved_config
from workflow_interpreter.schema.decisions import (
    CollectedChildResult,
    IntegrationAssociation,
    IntegrationRequest,
    IntegrationTargetClaim,
    MemberAdmission,
    digest_record,
)
from workflow_interpreter.schema.loader import canonical_bytes, load_graph
from workflow_interpreter.supervisor.band import BandLock
from workflow_interpreter.supervisor.gitcmd import GitSubcommand

ESSENTIAL = ("integration_sources", "stage_brief", "target_base")
CLAIM_KEY = "integration_target_key"


def _sha(body: str) -> str:
    return hashlib.sha256(body.encode()).hexdigest()


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _status_view(
    association: IntegrationAssociation,
    record: PhaseBridgeRecord | None,
    children: object,
) -> dict[str, object]:
    """Render stable operator identities without re-emitting pinned bulky bodies."""
    from workflow_interpreter.schema.decisions import ChildCoordinationView

    if not isinstance(children, ChildCoordinationView):
        raise BridgeRefusal("integration child status has an invalid shape")
    receipt = association.receipt
    states: dict[str, int] = {}
    for child in children.children:
        states[child.state] = states.get(child.state, 0) + 1
    target = {
        "key": association.target_key,
        "ref": association.target_ref,
        "base_commit": association.base_commit,
    }
    bridge = None
    if record is not None:
        bridge = {
            "state": record.state,
            "root_id": record.root_id,
            "epic_id": record.epic_id,
            "stage_id": record.stage_id,
            "attempt": record.attempt,
            "instance_key": record.instance_key,
            "target_ref": record.target_ref,
            "expected_base_commit": record.expected_base_commit,
            "execution_base_commit": record.execution_base_commit,
            "landed_oid": record.landed_oid,
            "tree": record.tree,
            "integration": {
                "digest": record.integration_digest,
                "owner_id": record.integration_owner,
                "slot": record.integration_slot,
                "generation": record.integration_generation,
            },
            "verification_policy": {
                "omitted": True,
                "reference": f"sha256:{_sha(association.verification_policy_json)}",
            },
        }
    return {
        "association": {
            "identity_digest": association.identity_digest,
            "request_digest": association.request_digest,
            "state": association.state,
            "root_id": receipt.root_id if receipt is not None else None,
            "receipt": (
                {
                    "root_id": receipt.root_id,
                    "owner_id": receipt.link.owner_id,
                    "slot": receipt.link.slot,
                    "generation": receipt.link.generation,
                    "reservation_id": receipt.link.reservation_id,
                }
                if receipt is not None
                else None
            ),
            "request": {
                "owner_id": association.request.owner_id,
                "epic_id": association.request.epic_id,
                "stage_id": association.request.stage_id,
                "request_key": association.request.request_key,
                "source_count": len(association.request.sources),
            },
            "target": target,
        },
        "bridge": bridge,
        "target": target,
        "children": {
            "owner_id": children.owner_id,
            "count": len(children.children),
            "states": dict(sorted(states.items())),
            "reserved_activation_capacity": children.reserved_activation_capacity,
            "reserved_decision_attempt_capacity": (
                children.reserved_decision_attempt_capacity
            ),
            "timed_out": children.timed_out,
            "contended_slot_count": len(children.contended_slots),
            "omitted": (
                "records",
                "attention",
                "collection",
                "cancellation",
                "contended_slots",
            ),
        },
    }


def target_key(composition: Composition, ref: str) -> str:
    repo = composition.config.repo_root
    common = composition.git.run(
        GitSubcommand.REV_PARSE, "--git-common-dir", cwd=repo
    ).text
    return _sha(str((repo / common).resolve()) + "\n" + ref)


class IntegrationGuard:
    """Validate source identity before CAS, durable authorization after CAS."""

    def __init__(self, composition: Composition) -> None:
        self.composition = composition
        self.store = composition.store.coordination_store(composition=composition)

    def association(self, record: PhaseBridgeRecord) -> IntegrationAssociation:
        if record.integration_owner is None:
            raise BridgeRefusal("integration owner missing")
        state = self.store.state(record.integration_owner)
        matches = [
            a
            for a in state.integrations.values()
            if a.identity_digest == record.integration_digest
        ]
        if len(matches) != 1:
            raise BridgeRefusal("integration association missing or ambiguous")
        association = matches[0]
        if (
            association.request.stage_id != record.stage_id
            or association.request.epic_id != record.epic_id
            or association.attempt != record.attempt
            or association.previous_attempts != record.previous_attempts
            or association.target_ref != record.target_ref
            or association.base_commit != record.expected_base_commit
            or association.admission.slot != record.integration_slot
            or association.admission.generation != record.integration_generation
            or association.admission_digest != digest_record(association.admission)
            or association.request_digest != digest_record(association.request)
            or association.target_key != target_key(self.composition, record.target_ref)
            or record.verification_policy is None
            or record.verification_policy
            != VerificationPolicy.model_validate_json(
                association.verification_policy_json
            )
        ):
            raise BridgeRefusal("integration association identity mismatch")
        return association

    def save(self, association: IntegrationAssociation) -> None:
        state = self.store.state(association.request.owner_id)
        self.store._save(
            state.model_copy(
                update={
                    "integrations": {
                        **state.integrations,
                        association.request.request_key: association,
                    }
                }
            )
        )
        if (
            self.store.state(state.owner_id).integrations[
                association.request.request_key
            ]
            != association
        ):
            raise BridgeRefusal("integration association readback mismatch")

    def claim(self, key: str) -> tuple[str, IntegrationTargetClaim] | None:
        rows = self.store._client.list_beads(metadata_filters={CLAIM_KEY: key})
        if len(rows) > 1:
            raise BridgeRefusal("ambiguous integration target claim")
        if not rows:
            return None
        return rows[0].id, IntegrationTargetClaim.model_validate(
            rows[0].metadata["integration_target_claim"]
        )

    def write_claim(self, claim: IntegrationTargetClaim) -> None:
        prior = self.claim(claim.key)
        data: Metadata = {
            CLAIM_KEY: claim.key,
            "integration_target_claim": claim.model_dump(mode="json"),
        }
        if prior is None:
            self.store._client._create_bead(
                title="Integration target claim", metadata=data
            )
        else:
            self.store._client._merge_metadata(prior[0], data)

    def binding(
        self, record: PhaseBridgeRecord, *, current: bool = True
    ) -> IntegrationAssociation:
        association = self.association(record)
        prepared = record.model_copy(
            update={
                "state": PhaseBridgeState.PREPARED,
                "root_id": None,
                "landed_oid": None,
                "tree": None,
                "gate_receipt_digest": None,
                "landing_receipt_digest": None,
            }
        )
        if association.bridge_digest != digest_record(prepared):
            raise BridgeRefusal("integration prepared bridge digest mismatch")
        receipt = association.receipt
        if receipt is None or receipt.root_id != record.root_id:
            raise BridgeRefusal("integration root receipt mismatch")
        state = self.store.state(association.request.owner_id)
        reservation = state.reservations.get(association.admission_digest)
        root = self.composition.store.reads.load_root(receipt.root_id)
        if (
            reservation is None
            or reservation.root_id != receipt.root_id
            or reservation.admission != association.admission
            or root.metadata.coordination != receipt.link
            or root.definition.content_hash != _sha(association.admission.graph_body)
            or root.metadata.instance_base_commit != association.base_commit
            or root.metadata.essential_inputs != association.admission.essential_inputs
            or root.metadata.essential_consumers
            != association.admission.essential_consumers
            or receipt.link.owner_id != association.request.owner_id
            or receipt.link.slot != association.admission.slot
            or receipt.link.generation != association.admission.generation
            or TypeAdapter(tuple[ResolvedSetting, ...])
            .dump_json(root.metadata.resolved_config)
            .decode()
            != association.admission.config_json
            or TypeAdapter(tuple[InstanceInput, ...])
            .dump_json(root.metadata.instance_inputs)
            .decode()
            != association.admission.inputs_json
        ):
            raise BridgeRefusal("integration pinned root mismatch")
        if current and association.state == "stale":
            raise BridgeRefusal("integration association is stale")
        if current:
            row = self.store.child_record(
                state.owner_id, receipt.link.slot, receipt.link.generation
            )
            if (
                state.active.get(receipt.link.slot) != receipt.root_id
                or row.cancellation is not None
            ):
                raise BridgeRefusal("integration member cancelled or stale")
        return association

    def sources(self, request: IntegrationRequest) -> tuple[dict[str, object], ...]:
        if len({slot for slot, _, _ in request.sources}) != len(request.sources):
            raise BridgeRefusal("duplicate integration source")
        entries: list[dict[str, object]] = []
        for slot, generation, digest in request.sources:
            row = self.store.child_record(request.owner_id, slot, generation)
            receipt = row.collection
            if row.cancellation or receipt is None or receipt.receipt_digest != digest:
                raise BridgeRefusal(
                    "source cancelled, uncollected, or receipt mismatch"
                )
            if self.store.state(request.owner_id).active.get(slot) != row.root_id:
                raise BridgeRefusal("source generation is stale")
            self._source_evidence(receipt)
            root = self.composition.store.reads.load_root(row.root_id)
            self.store.validate_member(root)
            if (
                root.metadata.coordination is None
                or root.metadata.coordination.owner_id != request.owner_id
            ):
                raise BridgeRefusal("source belongs to a different owner")
            writes = []
            for activation in self.composition.store.reads.list_activations(
                row.root_id
            ):
                if not resolved_node(root, activation.metadata.node).node.writes:
                    continue
                evidence = activation.metadata.evidence
                if evidence is None or evidence.artifact is None:
                    raise BridgeRefusal("source writer artifact evidence missing")
                artifact = evidence.artifact
                if self.composition.git.tree_oid(
                    artifact.commit_oid, cwd=self.composition.config.repo_root
                ) != artifact.tree_oid or not self.composition.git.is_ancestor(
                    artifact.commit_oid,
                    receipt.artifact_commit,
                    cwd=self.composition.config.repo_root,
                ):
                    raise BridgeRefusal("source writer artifact mismatch")
                writes.append(activation.activation_id)
            entries.append(
                {
                    "receipt": receipt.model_dump(mode="json"),
                    "writer_activations": writes,
                    "repository_contribution": bool(writes),
                }
            )
        return tuple(entries)

    def _source_evidence(self, receipt: CollectedChildResult) -> None:
        from workflow_interpreter.bdio import Lifecycle, Outcome

        root = self.composition.store.reads.load_root(receipt.root_id)
        self.composition.for_root(
            receipt.root_id
        )  # Enforce the persisted wrapper/repository binding.
        repo = self.composition.config.repo_root
        latest = max(
            self.composition.store.reads.list_activations(receipt.root_id),
            key=lambda a: a.metadata.seq,
        )
        evidence = latest.metadata.evidence
        actual_commit = (
            evidence.artifact.commit_oid
            if evidence and evidence.artifact
            else latest.metadata.intended_base_commit
        )
        actual_source = (
            "computed-output" if evidence and evidence.artifact else "activation-input"
        )
        if (
            actual_commit != receipt.artifact_commit
            or actual_source != receipt.artifact_source
            or evidence is None
            or evidence.outputs_ref != receipt.outputs_ref
            or evidence.outputs_tree_oid != receipt.outputs_tree
            or receipt.receipt_digest
            != digest_record(receipt.model_copy(update={"receipt_digest": ""}))
            or root.definition.content_hash != receipt.graph_hash
            or root.metadata.config_signature != receipt.config_signature
            or root.metadata.instance_base_commit != receipt.base_commit
            or root.bead.status != "closed"
            or root.metadata.terminal != receipt.terminal
            or latest.metadata.lifecycle is not Lifecycle.CLOSED
            or latest.metadata.outcome
            not in (Outcome.DONE, Outcome.ACCEPT, Outcome.NO_DIFF)
            or latest.activation_id != receipt.activation_id
            or evidence is None
            or digest_record(evidence) != receipt.evidence_digest
            or self.composition.git.ref_target(receipt.outputs_ref, cwd=repo)
            != receipt.outputs_commit
            or self.composition.git.tree_oid(receipt.outputs_commit, cwd=repo)
            != receipt.outputs_tree
            or self.composition.git.tree_oid(receipt.artifact_commit, cwd=repo)
            != receipt.artifact_tree
            or not self.composition.git.is_ancestor(
                receipt.base_commit, receipt.artifact_commit, cwd=repo
            )
        ):
            raise BridgeRefusal("source immutable evidence mismatch")

    @contextmanager
    def ordered(self, association: IntegrationAssociation) -> Iterator[None]:
        with ExitStack() as stack:
            stack.enter_context(
                BandLock(self.store.target_lock_path(association.target_key))
            )
            stack.enter_context(self.store._locked(association.request.owner_id))
            state = self.store.state(association.request.owner_id)
            roots = {
                state.children[slot].root_id
                for slot, _, _ in association.request.sources
            }
            if association.receipt:
                roots.add(association.receipt.root_id)
            for root in sorted(roots):
                stack.enter_context(BandLock(self.store.member_lock_path(root)))
            yield

    def finished(self, record: PhaseBridgeRecord) -> None:
        """Release only after the stage close was read back, including replay."""
        association = self.association(record)
        with (
            BandLock(self.store.target_lock_path(association.target_key)),
            self.store._locked(association.request.owner_id),
        ):
            self.post_cas(record)
            self.save(association.model_copy(update={"state": "landed"}))
            claim = self.claim(association.target_key)
            if (
                claim is not None
                and claim[1].association_digest == association.identity_digest
            ):
                self.write_claim(
                    claim[1].model_copy(update={"disposition": "released"})
                )

    def candidate(self, record: PhaseBridgeRecord, commit: str, tree: str) -> None:
        """Prove review consumed the actual writer artifact, independent of text."""
        from workflow_interpreter.bdio import Lifecycle, Outcome

        assert record.root_id is not None
        activations = self.composition.store.reads.list_activations(record.root_id)
        writers = [a for a in activations if a.metadata.node == "integrate"]
        reviewers = [a for a in activations if a.metadata.node == "review"]
        if len(writers) != 1 or len(reviewers) != 1:
            raise BridgeRefusal("integration needs one fresh writer and review")
        writer, reviewer = writers[0], reviewers[0]
        artifact = (
            writer.metadata.evidence.artifact if writer.metadata.evidence else None
        )
        binding = next(
            (i for i in reviewer.metadata.inputs if i.name == "candidate_diff"), None
        )
        if (
            artifact is None
            or artifact.commit_oid != commit
            or artifact.tree_oid != tree
            or writer.metadata.lifecycle is not Lifecycle.CLOSED
            or writer.metadata.outcome is not Outcome.DONE
            or reviewer.metadata.lifecycle is not Lifecycle.CLOSED
            or reviewer.metadata.outcome is not Outcome.ACCEPT
            or reviewer.metadata.intended_base_commit != commit
            or binding is None
            or binding.producer_activation_id != writer.activation_id
            or binding.digest != tree
        ):
            raise BridgeRefusal("integration review does not prove candidate artifact")

    def pre_cas(self, record: PhaseBridgeRecord) -> None:
        from workflow_interpreter.bridge.authority import BeadGateAuthority

        association = self.binding(record)
        claim = self.claim(association.target_key)
        if (
            claim is None
            or claim[1].association_digest != association.identity_digest
            or claim[1].disposition != "active"
            or claim[1].key != association.target_key
            or claim[1].owner_id != association.request.owner_id
            or claim[1].stage_id != association.request.stage_id
            or claim[1].request_digest != association.request_digest
            or claim[1].attempt != association.attempt
        ):
            raise BridgeRefusal("integration target claim is not active")
        entries = self.sources(association.request)
        if _sha(_json(entries)) != association.manifest_digest:
            raise BridgeRefusal("integration manifest changed")
        if (
            self.composition.git.ref_target(
                record.target_ref, cwd=self.composition.config.repo_root
            )
            != association.base_commit
        ):
            raise BridgeRefusal("branch-moved")
        assert record.root_id is not None
        evidence = BeadGateAuthority(self.composition.store.reads).verify(
            record.root_id
        )
        self.candidate(record, evidence.artifact_oid, evidence.tree)
        # Pin actual artifact authority, never the child collection or slot alone.
        updated = association.model_copy(
            update={
                "state": "landing_authorized",
                "candidate_commit": evidence.artifact_oid,
                "candidate_tree": evidence.tree,
                "authorization": _sha(
                    association.identity_digest + digest_record(evidence)
                ),
            }
        )
        self.save(updated)

    def post_cas(self, record: PhaseBridgeRecord) -> None:
        from workflow_interpreter.bridge.authority import BeadGateAuthority
        from workflow_interpreter.bridge.landing import (
            LANDING_INTENT_FILE,
            LandingIntent,
        )
        from workflow_interpreter.supervisor.paths import read_record

        association = self.binding(record, current=False)
        assert record.root_id is not None
        evidence = BeadGateAuthority(self.composition.store.reads).verify(
            record.root_id
        )
        intent = read_record(
            self.composition.for_root(record.root_id).paths.instance_dir
            / LANDING_INTENT_FILE,
            LandingIntent,
        )
        target = self.composition.git.ref_target(
            record.target_ref, cwd=self.composition.config.repo_root
        )
        if (
            association.authorization
            != _sha(association.identity_digest + digest_record(evidence))
            or association.candidate_commit != evidence.artifact_oid
            or association.candidate_tree != evidence.tree
            or intent is None
            or intent.root_id != record.root_id
            or intent.stage != record.stage_id
            or intent.attempt != record.attempt
            or intent.artifact_oid != evidence.artifact_oid
            or intent.tree != evidence.tree
            or intent.gate_receipt_digest != evidence.digest
            or intent.expected_base != association.base_commit
            or intent.ref != association.target_ref
            or target is None
            or not self.composition.git.is_ancestor(
                evidence.artifact_oid, target, cwd=self.composition.config.repo_root
            )
        ):
            raise BridgeRefusal("integration lacks matching observed CAS authorization")
        if record.state in (PhaseBridgeState.LANDED, PhaseBridgeState.CLOSED):
            from workflow_interpreter.bridge.landing import (
                LANDING_RECEIPT_FILE,
                LandingReceipt,
                _digest_record,
            )

            receipt = read_record(
                self.composition.for_root(record.root_id).paths.instance_dir
                / LANDING_RECEIPT_FILE,
                LandingReceipt,
            )
            if (
                receipt is None
                or record.landing_receipt_digest != _digest_record(receipt)
                or record.landed_oid != evidence.artifact_oid
                or record.tree != evidence.tree
                or receipt.intent_digest != _digest_record(intent)
                or record.gate_receipt_digest != evidence.digest
            ):
                raise BridgeRefusal("integration close lacks matching landing receipt")


def prepare_integration(
    composition: Composition, request: IntegrationRequest
) -> PhaseBridgeRecord:
    """Persist fixed intent before admitting exactly one P3 child root."""
    guard = IntegrationGuard(composition)
    adapter = PhaseAdapter.from_config(composition.config.bd)
    adapter.integration_guard = guard
    stage = adapter.show(request.stage_id)
    if (
        stage.parent != request.epic_id
        or not stage.description
        or not stage.description.strip()
    ):
        raise BridgeRefusal("integration stage identity or brief missing")
    if adapter.blocking_dependencies(request.stage_id):
        raise BridgeRefusal("integration stage is blocked")
    target = composition.git.attached_branch_ref(cwd=composition.config.repo_root)
    if target is None:
        raise BridgeRefusal("detached integration target")
    key = target_key(composition, target)
    with BandLock(guard.store.target_lock_path(key)):
        prior = guard.store.state(request.owner_id).integrations.get(
            request.request_key
        )
        if prior is not None and prior.request != request:
            raise BridgeRefusal("integration request-key payload changed")
        if prior is not None and prior.state == "landed":
            record = adapter.record(request.stage_id)
            guard.post_cas(record)
            return record
        if prior is not None and prior.target_key != key:
            raise BridgeRefusal("integration request changed repository or target")
        claim = guard.claim(key)
        if (
            claim
            and claim[1].disposition == "active"
            and (claim[1].owner_id, claim[1].stage_id, claim[1].request_digest)
            != (request.owner_id, request.stage_id, digest_record(request))
        ):
            raise BridgeRefusal("integration target busy")
        if prior is None:
            if stage.metadata.get("phase_bridge") is not None:
                raise BridgeRefusal(
                    "stage already has bridge; use explicit integration retry"
                )
            guard.sources(request)
            guard.write_claim(
                IntegrationTargetClaim(
                    key=key,
                    owner_id=request.owner_id,
                    stage_id=request.stage_id,
                    request_digest=digest_record(request),
                )
            )
            base = composition.git.ref_target(target, cwd=composition.config.repo_root)
            if base is None or composition.git.status_paths(
                cwd=composition.config.repo_root
            ):
                raise BridgeRefusal("integration target must be clean and present")
            entries = guard.sources(request)
            definition = load_graph(
                Path(__file__).resolve().parents[2] / "workflows/integration.toml"
            )
            settings = _resolved_config(composition, definition, {})
            bodies = dict(
                zip(ESSENTIAL, (_json(entries), stage.description, base), strict=True)
            )
            if (
                sum(len(body.encode()) for body in bodies.values())
                > MAX_INSTANCE_INPUT_BYTES
            ):
                raise BridgeRefusal(
                    "integration essential inputs exceed root byte limit"
                )
            from workflow_interpreter.foreman.envelope import EnvelopeRefusal
            from workflow_interpreter.foreman.execution import effective_node

            resolved = {item.key: item.value for item in settings}
            for pinned in definition.document.node:
                if pinned.name not in ("integrate", "review"):
                    continue
                node = effective_node(pinned, resolved)
                # Reserve framing room before IDs exist. Actual envelopes are
                # independently byte-checked by the ordinary TaskBuilder.
                minimum = (
                    sum(len(body.encode()) for body in bodies.values())
                    + len((node.instructions or "").encode())
                    + 4096
                )
                if minimum > (node.context_budget_bytes or 262144):
                    raise EnvelopeRefusal(
                        minimum, node.context_budget_bytes or 262144, exact=False
                    )
            inputs = tuple(
                InstanceInput(name=name, body=body, sha256=_sha(body))
                for name, body in bodies.items()
            )
            admission = MemberAdmission(
                graph_body=canonical_bytes(definition.document).decode(),
                config_json=TypeAdapter(tuple[ResolvedSetting, ...])
                .dump_json(settings)
                .decode(),
                inputs_json=TypeAdapter(tuple[InstanceInput, ...])
                .dump_json(inputs)
                .decode(),
                base_commit=base,
                slot=f"integration.{request.stage_id}.1",
                generation=0,
                essential_inputs=ESSENTIAL,
                essential_consumers={
                    name: ("integrate", "review") for name in ESSENTIAL
                },
            )
            prior = IntegrationAssociation(
                request=request,
                request_digest=digest_record(request),
                target_key=key,
                target_ref=target,
                base_commit=base,
                admission=admission,
                admission_digest=digest_record(admission),
                manifest_digest=_sha(bodies["integration_sources"]),
                verification_policy_json=VerificationPolicy.pin(
                    composition.config.bridge_checks or (), composition.config.repo_root
                ).model_dump_json(),
                attempt=1,
            )
            with guard.store._locked(request.owner_id):
                guard.save(prior)
        guard.write_claim(
            IntegrationTargetClaim(
                key=key,
                owner_id=request.owner_id,
                stage_id=request.stage_id,
                request_digest=digest_record(request),
                association_digest=prior.identity_digest,
                attempt=prior.attempt,
            )
        )
    return resume_integration(composition, prior)


def resume_integration(
    composition: Composition, association: IntegrationAssociation
) -> PhaseBridgeRecord:
    guard = IntegrationGuard(composition)
    adapter = PhaseAdapter.from_config(composition.config.bd)
    adapter.integration_guard = guard
    with BandLock(guard.store.target_lock_path(association.target_key)):
        association = guard.store.state(association.request.owner_id).integrations[
            association.request.request_key
        ]
        claim = guard.claim(association.target_key)
        if claim is None or (
            claim[1].owner_id,
            claim[1].stage_id,
            claim[1].request_digest,
        ) != (
            association.request.owner_id,
            association.request.stage_id,
            association.request_digest,
        ):
            raise BridgeRefusal("integration prepared intent lost target claim")
        if claim[1].attempt != association.attempt:
            raise BridgeRefusal("integration prepared claim attempt mismatch")
        if claim[1].association_digest is None:
            guard.write_claim(
                claim[1].model_copy(
                    update={"association_digest": association.identity_digest}
                )
            )
        elif claim[1].association_digest != association.identity_digest:
            raise BridgeRefusal("integration prepared claim digest mismatch")
        raw = adapter.show(association.request.stage_id).metadata.get("phase_bridge")
        record = PhaseBridgeRecord.model_validate(raw) if raw else None
        predecessor = (
            record
            if record is not None and record.attempt + 1 == association.attempt
            else None
        )
        if (
            predecessor is not None
            and association.predecessor_digest == predecessor.integration_digest
        ):
            record = None
        if (
            record is not None
            and record.integration_digest != association.identity_digest
        ):
            raise BridgeRefusal("integration bridge association mismatch")
        if record is None:
            record = PhaseBridgeRecord.prepared(
                epic_id=association.request.epic_id,
                stage_id=association.request.stage_id,
                attempt=1,
                target_ref=association.target_ref,
                expected_base_commit=association.base_commit,
                verification_policy=VerificationPolicy.model_validate_json(
                    association.verification_policy_json
                ),
            ).model_copy(
                update={
                    "integration_digest": association.identity_digest,
                    "integration_owner": association.request.owner_id,
                    "integration_slot": association.admission.slot,
                    "integration_generation": 0,
                }
            )
            if predecessor is not None:
                record = record.model_copy(
                    update={
                        "attempt": association.attempt,
                        "instance_key": predecessor.next_attempt().instance_key,
                        "previous_attempts": association.previous_attempts,
                    }
                )
            record = adapter.prepare(record.stage_id, record)
        if record.state is not PhaseBridgeState.PREPARED:
            guard.binding(
                record,
                current=record.state
                not in (PhaseBridgeState.LANDED, PhaseBridgeState.CLOSED),
            )
            if association.state == "root_bound":
                with guard.store._locked(association.request.owner_id):
                    guard.save(
                        association.model_copy(
                            update={
                                "state": "admitted",
                            }
                        )
                    )
            return record
        if association.bridge_digest is None:
            with guard.store._locked(association.request.owner_id):
                association = association.model_copy(
                    update={"bridge_digest": digest_record(record)}
                )
                guard.save(association)
        guard.sources(association.request)
        receipt = guard.store.start_child(
            association.request.owner_id,
            association.admission.slot,
            association.admission,
        )
        with guard.store._locked(association.request.owner_id):
            association = association.model_copy(
                update={"receipt": receipt, "state": "root_bound"}
            )
            guard.save(association)
        record = adapter.admit(record.stage_id, record, root_id=receipt.root_id)
        with guard.store._locked(association.request.owner_id):
            guard.save(association.model_copy(update={"state": "admitted"}))
        return record


def retry_integration(
    composition: Composition, record: PhaseBridgeRecord
) -> PhaseBridgeRecord:
    """Explicit ordinary retry, same source set/config and original owner budget."""
    from workflow_interpreter.bridge.landing import (
        LANDING_INTENT_FILE,
        LANDING_RECEIPT_FILE,
    )

    guard = IntegrationGuard(composition)
    association = guard.binding(record, current=False)
    assert record.root_id is not None
    with guard.ordered(association):
        root = composition.store.reads.load_root(record.root_id)
        paths = composition.for_root(record.root_id).paths
        if (
            (paths.instance_dir / LANDING_INTENT_FILE).exists()
            or (paths.instance_dir / LANDING_RECEIPT_FILE).exists()
            or association.authorization
        ):
            raise BridgeRefusal(
                "uncertain or observed landing must recover before retry"
            )
        if root.bead.status != "closed" or root.metadata.terminal not in (
            "shipped",
            "abandoned",
        ):
            raise BridgeRefusal("integration retry requires settled human-gated root")
        base = composition.git.ref_target(
            record.target_ref, cwd=composition.config.repo_root
        )
        if base is None or composition.git.status_paths(
            cwd=composition.config.repo_root
        ):
            raise BridgeRefusal("integration retry requires clean target")
        if (
            base == association.base_commit
            and record.state is not PhaseBridgeState.GATE_RED
            and root.metadata.terminal == "shipped"
        ):
            raise BridgeRefusal("approved integration remains landing-recoverable")
        claim = guard.claim(association.target_key)
        guard.sources(association.request)
        attempt = record.attempt + 1
        request = association.request.model_copy(
            update={"request_key": f"retry-{association.identity_digest}-{attempt}"}
        )
        existing = guard.store.state(request.owner_id).integrations.get(
            request.request_key
        )
        permitted = {association.identity_digest}
        if existing is not None:
            permitted.add(existing.identity_digest)
        if (
            claim is None
            or claim[1].association_digest not in permitted
            or claim[1].disposition != "active"
        ):
            raise BridgeRefusal("integration retry lost target claim")
        if existing is None:
            inputs = TypeAdapter(tuple[InstanceInput, ...]).validate_json(
                association.admission.inputs_json
            )
            inputs = tuple(
                InstanceInput(name=i.name, body=base, sha256=_sha(base))
                if i.name == "target_base"
                else i
                for i in inputs
            )
            admission = association.admission.model_copy(
                update={
                    "base_commit": base,
                    "slot": f"integration.{record.stage_id}.{attempt}",
                    "generation": 0,
                    "predecessor_id": None,
                    "request_id": None,
                    "inputs_json": TypeAdapter(tuple[InstanceInput, ...])
                    .dump_json(inputs)
                    .decode(),
                }
            )
            existing = IntegrationAssociation(
                request=request,
                request_digest=digest_record(request),
                target_key=association.target_key,
                target_ref=record.target_ref,
                base_commit=base,
                admission=admission,
                admission_digest=digest_record(admission),
                manifest_digest=association.manifest_digest,
                verification_policy_json=association.verification_policy_json,
                attempt=attempt,
                previous_attempts=(*record.previous_attempts, record.instance_key),
                predecessor_digest=association.identity_digest,
            )
            guard.save(existing)
        # No unlocked gap: durable claim is transferred, never removed.
        guard.write_claim(
            IntegrationTargetClaim(
                key=existing.target_key,
                owner_id=request.owner_id,
                stage_id=request.stage_id,
                request_digest=digest_record(request),
                association_digest=existing.identity_digest,
                attempt=existing.attempt,
            )
        )
        guard.save(association.model_copy(update={"state": "stale"}))
    return resume_integration(composition, existing)


def prepared_for_stage(
    composition: Composition, epic_id: str, stage_id: str
) -> IntegrationAssociation | None:
    """Recover the association-before-bridge window from the existing Beads ledger."""
    from workflow_interpreter.schema.decisions import CoordinationState

    coordinator = composition.store.coordination_store(composition=composition)
    matches: list[IntegrationAssociation] = []
    for bead in coordinator._client.list_beads(metadata_filters={"wf_kind": "root"}):
        raw = bead.metadata.get("coordination_state")
        if raw is None:
            continue
        state = CoordinationState.model_validate(raw)
        matches.extend(
            a
            for a in state.integrations.values()
            if a.request.epic_id == epic_id
            and a.request.stage_id == stage_id
            and a.state != "stale"
        )
    if len(matches) > 1:
        # During retry journaling both records can exist until claim transfer.
        predecessors = {a.predecessor_digest for a in matches}
        matches = [a for a in matches if a.identity_digest not in predecessors]
    if len(matches) > 1:
        raise BridgeRefusal("ambiguous prepared integration for stage")
    return matches[0] if matches else None


def command(composition: Composition, args: object) -> str:
    """Public integration commands delegate to the durable P4 admission APIs."""
    from argparse import Namespace

    from workflow_interpreter.foreman.identifiers import validate_bead_id

    if not isinstance(args, Namespace):
        raise BridgeRefusal("invalid integration command")
    if args.integration_command == "prepare":
        with args.request.open("rb") as stream:
            body = stream.read(1_048_577)
        if len(body) > 1_048_576:
            raise BridgeRefusal("integration request exceeds 1 MiB")
        prepared = prepare_integration(
            composition, IntegrationRequest.model_validate_json(body)
        )
        return prepared.model_dump_json(by_alias=True)
    validate_bead_id(args.epic_id)
    validate_bead_id(args.stage_id)
    guard = IntegrationGuard(composition)
    association = prepared_for_stage(composition, args.epic_id, args.stage_id)
    if association is None:
        raise BridgeRefusal("integration association is absent")
    adapter = PhaseAdapter.from_config(composition.config.bd)
    raw = adapter.show(args.stage_id).metadata.get("phase_bridge")
    record = adapter.record(args.stage_id) if raw is not None else None
    if args.integration_command == "retry":
        if record is None:
            raise BridgeRefusal("integration bridge is absent")
        return retry_integration(composition, record).model_dump_json(by_alias=True)
    if record is not None:
        association = guard.association(record)
    return _json(
        _status_view(
            association,
            record,
            guard.store.child_status(association.request.owner_id),
        )
    )


def replace_integration(
    composition: Composition,
    association: IntegrationAssociation,
    intent: TrustedReplacementIntent,
) -> MemberReceipt:
    """Changed-pins successor keeps P4's exact source/brief/base/target authority."""
    from workflow_interpreter.foreman.replacement import advance_successor

    if (
        intent.owner_id != association.request.owner_id
        or intent.slot != association.admission.slot
        or intent.expected_generation != association.admission.generation
        or intent.admission.inputs_json != association.admission.inputs_json
    ):
        raise BridgeRefusal(
            "integration replacement changes fixed source/slot authority"
        )
    admission = intent.admission.model_copy(
        update={"base_commit": association.base_commit}
    )
    return advance_successor(
        composition, intent.model_copy(update={"admission": admission})
    )
