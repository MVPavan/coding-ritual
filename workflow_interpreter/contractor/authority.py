"""Read-only authority for signed human-gate evidence at phase landing."""

from __future__ import annotations

from typing import Final, Protocol

from workflow_interpreter.bdio.records import GateRecord, RootRecord
from workflow_interpreter.bdio.wire import GateState
from workflow_interpreter.bridge.errors import BridgeRefusal
from workflow_interpreter.bridge.landing import SHIP_GATE, GateEvidence
from workflow_interpreter.schema.models import BindsMode, NodeKind, Outcome

MSG_SHIP_GATE_MISSING: Final[str] = (
    "ship gate authority missing for root {root_id}; gate_id=<none>"
)
MSG_SHIP_GATE_AMBIGUOUS: Final[str] = (
    "ship gate authority is ambiguous for root {root_id}; gate_ids={gate_ids}"
)
MSG_SHIP_GATE_NOT_CLOSED: Final[str] = (
    "ship gate {gate_id} is not CLOSED; it cannot authorize landing"
)
MSG_SHIP_GATE_NOT_IMMUTABLE: Final[str] = (
    "ship gate {gate_id} is not IMMUTABLE; it cannot authorize landing"
)
MSG_SHIP_GATE_MISSING_MARK: Final[str] = (
    "ship gate {gate_id} is CLOSED but lacks verified {field}; it cannot authorize landing"
)
MSG_SHIP_GATE_UNDECLARED_OUTCOME: Final[str] = (
    "ship gate {gate_id} records an outcome it did not declare; it cannot authorize landing"
)
MSG_SHIP_GATE_ACCEPTANCE_UNDECLARED: Final[str] = (
    "ship gate {gate_id} has no graph-declared landing-authorizing outcome"
)


class GateReads(Protocol):
    """Expose the gate records available to landing without any write capability."""

    def load_root(self, root_id: str) -> RootRecord:
        """Read the canonical pinned graph that declared this gate."""

    def list_gates(self, root_id: str) -> tuple[GateRecord, ...]:
        """Return every gate record belonging to the requested workflow root."""


class BeadGateAuthority:
    """Derive landing evidence only from a closed immutable ship gate bead."""

    def __init__(self, reads: GateReads) -> None:
        self._reads = reads

    def verify(self, root_id: str) -> GateEvidence:
        """Refuse any ship gate whose recorded verification evidence is incomplete."""
        gates = tuple(
            sorted(
                (
                    gate
                    for gate in self._reads.list_gates(root_id)
                    if gate.metadata.wf_root_id == root_id
                    and gate.metadata.gate_node == SHIP_GATE
                ),
                key=lambda gate: gate.gate_id,
            )
        )
        if not gates:
            raise BridgeRefusal(MSG_SHIP_GATE_MISSING.format(root_id=root_id))
        if len(gates) != 1:
            raise BridgeRefusal(
                MSG_SHIP_GATE_AMBIGUOUS.format(
                    root_id=root_id,
                    gate_ids=",".join(gate.gate_id for gate in gates),
                )
            )
        gate = gates[0]
        metadata = gate.metadata
        if metadata.state is not GateState.CLOSED:
            raise BridgeRefusal(MSG_SHIP_GATE_NOT_CLOSED.format(gate_id=gate.gate_id))
        if metadata.binds is not BindsMode.IMMUTABLE:
            raise BridgeRefusal(
                MSG_SHIP_GATE_NOT_IMMUTABLE.format(gate_id=gate.gate_id)
            )

        outcome = _required(gate, "outcome", metadata.outcome)
        fingerprint = _required(
            gate, "verified_fingerprint", metadata.verified_fingerprint
        )
        digest = _required(gate, "payload_digest", metadata.payload_digest)
        artifact_ref = _required(gate, "artifact_ref", metadata.artifact_ref)
        artifact_digest = _required(gate, "artifact_digest", metadata.artifact_digest)
        if outcome not in metadata.outcomes:
            raise BridgeRefusal(
                MSG_SHIP_GATE_UNDECLARED_OUTCOME.format(gate_id=gate.gate_id)
            )

        root = self._reads.load_root(root_id)
        index = root.index
        node = index.nodes.get(SHIP_GATE)
        approved_targets = tuple(
            edge.to
            for edge in index.edges
            if edge.from_node == SHIP_GATE and edge.on is Outcome.APPROVE
        )
        if (
            root.root_id != root_id
            or approved_targets != ("shipped",)
            or "shipped" not in index.nodes
            or index.nodes["shipped"].kind is not NodeKind.TERMINAL
            or node is None
            or node.kind is not NodeKind.GATE
            or node.binds != metadata.binds
            or node.gate_type != metadata.gate_type
            or node.outcomes != metadata.outcomes
            or Outcome.APPROVE not in metadata.outcomes
        ):
            raise BridgeRefusal(
                MSG_SHIP_GATE_ACCEPTANCE_UNDECLARED.format(gate_id=gate.gate_id)
            )
        return GateEvidence(
            root_id=root_id,
            gate_node=metadata.gate_node,
            closed=metadata.state is GateState.CLOSED,
            immutable=metadata.binds is BindsMode.IMMUTABLE,
            accepted=metadata.outcome is Outcome.APPROVE,
            artifact_oid=artifact_ref,
            tree=artifact_digest,
            fingerprint=fingerprint,
            digest=digest,
        )


def _required[ValueT](gate: GateRecord, field: str, value: ValueT | None) -> ValueT:
    """Return one recorded verification mark or refuse its incomplete closure."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise BridgeRefusal(
            MSG_SHIP_GATE_MISSING_MARK.format(gate_id=gate.gate_id, field=field)
        )
    return value
