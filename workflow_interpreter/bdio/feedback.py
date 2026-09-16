"""Read-only causal validation for engine-produced verification inputs."""

from collections.abc import Sequence
from typing import Final

from workflow_interpreter.bdio.carriers import GateReason, GateState, MintReason
from workflow_interpreter.bdio.errors import CarrierIntegrityError
from workflow_interpreter.bdio.records import ActivationRecord, GateRecord, RootRecord
from workflow_interpreter.bdio.wire import MintRequest, NodeSetting, resolved_settings
from workflow_interpreter.schema.models import EngineProducer, Outcome

DEVIATION_VERIFY_UNPINNED: Final[str] = "verify_feedback_unpinned"

MSG_BINDING: Final[str] = (
    "verify_failure binding does not match its causal host failure"
)
MSG_CONSUMER: Final[str] = "engine:verify_failure requires an effective writer consumer"


def causal_failure(
    root: RootRecord,
    request: MintRequest,
    activations: Sequence[ActivationRecord],
    gates: Sequence[GateRecord],
) -> ActivationRecord | None:
    """Prove a fail_code edge, including its verified rebudget continuation."""
    if request.mint_reason is not MintReason.EDGE:
        return None
    source_id = request.predecessor_activation_id
    gate = None
    if request.predecessor_gate_id is not None:
        gate = next(
            (g for g in gates if g.gate_id == request.predecessor_gate_id), None
        )
        if gate is None or (
            gate.metadata.wf_root_id != root.root_id
            or gate.metadata.state is not GateState.CLOSED
            or gate.metadata.outcome is not Outcome.REBUDGET
            or gate.metadata.opening_outcome is not Outcome.FAIL_CODE
            or not gate.metadata.verified_fingerprint
            or not gate.metadata.payload_digest
            or gate.metadata.gate_reason
            not in {GateReason.EXHAUSTION, GateReason.TRANSITION}
        ):
            return None
        source_id = gate.metadata.source_activation_id
        if not any(
            e.from_node == gate.metadata.gate_node
            and e.on is Outcome.REBUDGET
            and e.to == request.node
            for e in root.definition.document.edge
        ):
            return None
    source = next((a for a in activations if a.activation_id == source_id), None)
    if source is None or (
        source.metadata.wf_root_id != root.root_id
        or not source.metadata.is_completed
        or source.metadata.outcome is not Outcome.FAIL_CODE
        or source.metadata.evidence is None
        or not any(check.exit_code != 0 for check in source.metadata.evidence.verify)
    ):
        return None
    target = request.node
    if gate is not None:
        if gate.metadata.gate_reason is GateReason.TRANSITION:
            target = gate.metadata.gate_node
        else:
            if source.metadata.region is None:
                return None
            region = root.index.regions[source.metadata.region]
            if (
                region.on_exhausted != gate.metadata.gate_node
                or region.entry_node != request.node
            ):
                return None
    if not any(
        e.from_node == source.metadata.node
        and e.on is Outcome.FAIL_CODE
        and e.to == target
        for e in root.definition.document.edge
    ):
        return None
    return source


def validate_feedback_bindings(
    root: RootRecord,
    request: MintRequest,
    activations: Sequence[ActivationRecord],
    gates: Sequence[GateRecord],
) -> None:
    """Reject forged identities and require retry/steer to preserve their input pin."""
    names = {
        name
        for name in root.index.nodes[request.node].inputs or ()
        if root.index.sources[name].producer == EngineProducer.VERIFY_FAILURE
    }
    bound = tuple(
        b for b in request.inputs if b.name in names or b.verify_failure is not None
    )
    if not names and not bound:
        return
    if not resolved_settings(root.metadata).get(
        NodeSetting.WRITES.at(request.node), root.index.nodes[request.node].writes
    ):
        raise CarrierIntegrityError(MSG_CONSUMER)
    if request.mint_reason in {MintReason.INFRA_RETRY, MintReason.STEER_CONTINUATION}:
        predecessor = next(
            (
                a
                for a in activations
                if a.activation_id == request.predecessor_activation_id
            ),
            None,
        )
        expected = (
            ()
            if predecessor is None
            else tuple(b for b in predecessor.metadata.inputs if b.name in names)
        )
        if bound != expected:
            raise CarrierIntegrityError(MSG_BINDING)
        return
    source = causal_failure(root, request, activations, gates)
    if source is None:
        if bound:
            raise CarrierIntegrityError(MSG_BINDING)
        return
    if not bound and any(
        d.kind == DEVIATION_VERIFY_UNPINNED for d in request.deviations
    ):
        return
    if {b.name for b in bound} != names or len(bound) != len(names):
        raise CarrierIntegrityError(MSG_BINDING)
    for binding in bound:
        proof = binding.verify_failure
        if proof is None or (
            proof.root_id != root.root_id
            or proof.source_activation_id != source.activation_id
            or binding.producer_activation_id != source.activation_id
            or binding.digest != proof.payload_digest
            or binding.artifact_ref != proof.ref
        ):
            raise CarrierIntegrityError(MSG_BINDING)
