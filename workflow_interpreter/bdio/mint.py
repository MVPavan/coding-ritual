"""§3.2 mint facts — derived from the pinned graph and the recorded trace.

The caller states INTENT: which node, why, and from which predecessor.
Everything the bounds and the identity key are computed from is derived here,
because a caller that can state those facts can dodge the bound that reads
them — labeling an infra retry an `edge` mint to escape `max_infra_retries`,
or naming a region whose `max_entries` is not the one being consumed (probed,
phase-2 review; §3.2 'Mint facts are DERIVED by the wrapper').

The mint reason is not exempt either: it must be CONSISTENT with the
predecessor's recorded close. An `edge` mint whose predecessor closed
`error_runner` is a mislabeled infra retry and is refused, not silently
counted against the wrong bound.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from pydantic import BaseModel

from workflow_interpreter.bdio import bounds, keys
from workflow_interpreter.bdio.capabilities import BranchHeadReader
from workflow_interpreter.bdio.constants import _MSG_ENTRY_PREDECESSOR
from workflow_interpreter.bdio.errors import BdConfigError, CarrierIntegrityError
from workflow_interpreter.bdio.records import ActivationRecord, GateRecord, RootRecord
from workflow_interpreter.bdio.wire import (
    WIRE_MODEL,
    GateReason,
    GateState,
    Lifecycle,
    MintReason,
    MintRequest,
    NodeSetting,
)
from workflow_interpreter.schema.models import (
    GRAPH_OUTCOMES,
    Node,
    NodeKind,
    Outcome,
)

FIRST_ROUND: Final[int] = 1

_SAME_NODE_REASONS: Final[frozenset[MintReason]] = frozenset(
    {MintReason.INFRA_RETRY, MintReason.STEER_CONTINUATION}
)
"""Re-dispatches of the SAME node: they inherit `round_no` (§10.1) and their
predecessor is the attempt being retried, not a different node."""

_MSG_UNKNOWN_NODE: Final[str] = (
    "node {node!r} is not declared by the pinned graph; its region and bounds "
    "cannot be derived, so the mint is refused (§3.2)"
)
_MSG_NOT_A_TASK: Final[str] = (
    "node {node!r} is kind={kind!r}; only task nodes are dispatchable, so no "
    "activation is minted at one (§2, §3.2)"
)
_MSG_ENTRY_NODE: Final[str] = (
    "an entry mint must target the graph's entry node {entry!r}, not {node!r}"
)
_MSG_NO_PREDECESSOR: Final[str] = (
    "a {reason} mint into {node!r} needs a predecessor activation to derive "
    "its outcome and idempotency key (§3.2)"
)
_MSG_WRITE_MODE: Final[str] = "node {node!r} has a non-boolean pinned write mode"
_MSG_PREDECESSOR_MISSING: Final[str] = (
    "predecessor {predecessor!r} is not an activation of this instance"
)
_MSG_PREDECESSOR_OPEN: Final[str] = (
    "predecessor {predecessor!r} is {lifecycle} with outcome {outcome}; the "
    "outcome taken is read from the recorded close, so an unclosed "
    "predecessor cannot be minted from (§3.2)"
)
_MSG_WRONG_REASON: Final[str] = (
    "a {reason} mint requires its predecessor to have closed {expected}, but "
    "{predecessor} closed {outcome} — a mislabeled mint would be counted "
    "against the wrong §10.2 bound"
)
_MSG_WRONG_NODE: Final[str] = (
    "a {reason} mint re-dispatches the SAME node; predecessor {predecessor} "
    "ran {found!r}, this mint targets {node!r}"
)
_MSG_NO_HEAD_READER: Final[str] = (
    "no branch_head_reader was injected; §3.2 resolves intended_base_commit "
    "at mint and will not take it from the caller"
)
_MSG_GATE_PREDECESSOR_MISSING: Final[str] = (
    "predecessor gate {gate_id!r} is not this instance"
)
_MSG_GATE_PREDECESSOR_UNVERIFIED: Final[str] = (
    "predecessor gate {gate_id!r} is not verified closed"
)
_MSG_GATE_ROUND_MISMATCH: Final[str] = (
    "predecessor gate region or round does not match target"
)


class MintFacts(BaseModel):
    """Everything about a mint that the store derived rather than accepted."""

    model_config = WIRE_MODEL

    node: str
    region: str | None
    round_no: int
    mint_reason: MintReason
    predecessor_activation_id: str | None
    predecessor_gate_id: str | None
    outcome_taken: Outcome | None
    intended_base_commit: str
    idempotency_key: str


def derive_mint_facts(
    root: RootRecord,
    request: MintRequest,
    activations: Sequence[ActivationRecord],
    branch_head_reader: BranchHeadReader | None,
    gates: Sequence[GateRecord] = (),
) -> MintFacts:
    """Resolve a mint's §3.2 facts from the pinned graph and recorded trace."""
    node = _assert_declared_node(root, request.node)
    gate = _resolve_gate_predecessor(request, gates)
    predecessor = _resolve_predecessor(request, activations)
    outcome_taken = (
        predecessor.metadata.outcome
        if predecessor is not None
        else None
        if gate is None
        else gate.metadata.outcome
    )
    _assert_reason_matches(request, predecessor, outcome_taken)
    region = node.region
    round_no = _derive_round(root, request, region, predecessor, gate, activations)
    return MintFacts(
        node=request.node,
        region=region,
        round_no=round_no,
        mint_reason=request.mint_reason,
        predecessor_activation_id=request.predecessor_activation_id,
        predecessor_gate_id=request.predecessor_gate_id,
        outcome_taken=outcome_taken,
        intended_base_commit=_derive_base_commit(
            root, request.node, region, activations, branch_head_reader
        ),
        idempotency_key=_derive_key(root, request, outcome_taken),
    )


def _assert_declared_node(root: RootRecord, node: str) -> Node:
    """The pinned graph's declaration of `node`, or a fail-closed refusal.

    Only `task` nodes are dispatchable. A gate bead is minted by `open_gate`
    under its own §3.4 key and a terminal node runs nothing, so an activation
    at either is a bead consuming the §10.3 ceiling under no region bound
    (probed, phase-2 review).
    """
    declared = root.index.nodes.get(node)
    if declared is None:
        raise CarrierIntegrityError(_MSG_UNKNOWN_NODE.format(node=node))
    if declared.kind is not NodeKind.TASK:
        raise CarrierIntegrityError(
            _MSG_NOT_A_TASK.format(node=node, kind=declared.kind.value)
        )
    return declared


def _resolve_predecessor(
    request: MintRequest, activations: Sequence[ActivationRecord]
) -> ActivationRecord | None:
    """The recorded predecessor bead this mint claims to follow."""
    predecessor_id = request.predecessor_activation_id
    if request.mint_reason is MintReason.ENTRY:
        if predecessor_id is not None or request.predecessor_gate_id is not None:
            raise CarrierIntegrityError(
                _MSG_ENTRY_PREDECESSOR.format(
                    predecessor=predecessor_id or request.predecessor_gate_id
                )
            )
        return None
    if predecessor_id is None:
        if request.predecessor_gate_id is not None:
            return None
        raise CarrierIntegrityError(
            _MSG_NO_PREDECESSOR.format(
                reason=request.mint_reason.value, node=request.node
            )
        )
    found = next(
        (record for record in activations if record.activation_id == predecessor_id),
        None,
    )
    if found is None:
        raise CarrierIntegrityError(
            _MSG_PREDECESSOR_MISSING.format(predecessor=predecessor_id)
        )
    if (
        found.metadata.lifecycle is not Lifecycle.CLOSED
        or found.metadata.outcome is None
    ):
        raise CarrierIntegrityError(
            _MSG_PREDECESSOR_OPEN.format(
                predecessor=predecessor_id,
                lifecycle=found.metadata.lifecycle.value,
                outcome=found.metadata.outcome,
            )
        )
    return found


def _resolve_gate_predecessor(
    request: MintRequest, gates: Sequence[GateRecord]
) -> GateRecord | None:
    """Return a verified closed gate predecessor, when the request names one."""
    gate_id = request.predecessor_gate_id
    if gate_id is None:
        return None
    found = next((gate for gate in gates if gate.gate_id == gate_id), None)
    if found is None:
        raise CarrierIntegrityError(
            _MSG_GATE_PREDECESSOR_MISSING.format(gate_id=gate_id)
        )
    metadata = found.metadata
    if (
        metadata.state is not GateState.CLOSED
        or metadata.outcome is None
        or metadata.verified_fingerprint is None
        or metadata.payload_digest is None
    ):
        raise CarrierIntegrityError(
            _MSG_GATE_PREDECESSOR_UNVERIFIED.format(gate_id=gate_id)
        )
    return found


def _assert_reason_matches(
    request: MintRequest,
    predecessor: ActivationRecord | None,
    outcome_taken: Outcome | None,
) -> None:
    """Refuse a mint whose reason contradicts the predecessor's recorded close."""
    if request.predecessor_gate_id is not None:
        if request.mint_reason is not MintReason.EDGE:
            raise CarrierIntegrityError(
                _MSG_WRONG_REASON.format(
                    reason=request.mint_reason.value,
                    expected=MintReason.EDGE.value,
                    predecessor=request.predecessor_gate_id,
                    outcome=("none" if outcome_taken is None else outcome_taken.value),
                )
            )
        return
    if predecessor is None or outcome_taken is None:
        return
    if request.mint_reason is MintReason.INFRA_RETRY:
        expected: frozenset[Outcome] = bounds.INFRA_OUTCOMES
    elif request.mint_reason is MintReason.STEER_CONTINUATION:
        expected = frozenset({Outcome.STEERED})
    else:
        expected = GRAPH_OUTCOMES
    if outcome_taken not in expected:
        raise CarrierIntegrityError(
            _MSG_WRONG_REASON.format(
                reason=request.mint_reason.value,
                expected=", ".join(sorted(outcome.value for outcome in expected)),
                predecessor=predecessor.activation_id,
                outcome=outcome_taken.value,
            )
        )
    if (
        request.mint_reason in _SAME_NODE_REASONS
        and predecessor.metadata.node != request.node
    ):
        raise CarrierIntegrityError(
            _MSG_WRONG_NODE.format(
                reason=request.mint_reason.value,
                predecessor=predecessor.activation_id,
                found=predecessor.metadata.node,
                node=request.node,
            )
        )


def _derive_round(
    root: RootRecord,
    request: MintRequest,
    region: str | None,
    predecessor: ActivationRecord | None,
    gate: GateRecord | None,
    activations: Sequence[ActivationRecord],
) -> int:
    """§10.1: `round_no` increments on entry into the region's `entry_node`.

    Infra retries and steer continuations INHERIT the predecessor's round —
    system outcomes never consume rounds. Anything else that lands on a
    region's entry node is an entry into that region (initial or back-edge)
    and opens the next round; a mint further into a region stays in the round
    its predecessor was running.

    Inheritance is REGION-LOCAL. A legal forward edge that crosses a region
    boundary used to carry the source region's counter into the target, where
    it was counted against a `max_entries` it never consumed — one foreign
    arrival could exhaust a region that had never been entered (probed,
    phase-2 review). Every cross-region arrival lands on the target region's
    `entry_node` (§2 rule 6, enforced by the validator over the pinned graph),
    so it opens that region's next round through the branch above; a mint that
    is neither an entry-node arrival nor a continuation of its predecessor's
    region has no round to inherit and starts at the first.
    """
    if request.mint_reason in _SAME_NODE_REASONS and predecessor is not None:
        return predecessor.metadata.round_no
    if gate is not None:
        if gate.metadata.region != region or gate.metadata.round_no is None:
            raise CarrierIntegrityError(_MSG_GATE_ROUND_MISMATCH)
        if (
            gate.metadata.gate_reason in {GateReason.TRANSITION, GateReason.EXHAUSTION}
            and region is not None
            and root.index.regions.get(region) is not None
            and root.index.regions[region].entry_node == request.node
        ):
            return _next_round(activations, region)
        return gate.metadata.round_no
    declared_region = None if region is None else root.index.regions.get(region)
    if (
        region is not None
        and declared_region is not None
        and declared_region.entry_node == request.node
    ):
        return _next_round(activations, region)
    if predecessor is not None and predecessor.metadata.region == region:
        return predecessor.metadata.round_no
    return FIRST_ROUND


def _next_round(activations: Sequence[ActivationRecord], region: str) -> int:
    """The round a fresh arrival into `region` opens — its counter, never another's."""
    used = bounds.distinct_rounds(views_of(activations), region)
    return max(used, default=FIRST_ROUND - 1) + 1


def _derive_base_commit(
    root: RootRecord,
    node: str,
    region: str | None,
    activations: Sequence[ActivationRecord],
    branch_head_reader: BranchHeadReader | None,
) -> str:
    """§3.2 `intended_base_commit`, resolved AT MINT.

    The `pre_attempt_commit` of the most recent WRITING activation at this
    node in this region (the rework case), else the instance branch head.
    Never derived through `predecessor_activation_id`: on a reject edge the
    predecessor is the reviewer, whose base IS the rejected commit.
    """
    declared = root.index.nodes.get(node)
    settings = {item.key: item.value for item in root.metadata.resolved_config}
    writes = settings.get(
        NodeSetting.WRITES.at(node), declared.writes if declared is not None else False
    )
    if not isinstance(writes, bool):
        raise CarrierIntegrityError(_MSG_WRITE_MODE.format(node=node))
    # Base selection must use the same pinned write mode as execution.
    if writes:
        for record in reversed(list(activations)):
            metadata = record.metadata
            if (
                metadata.node == node
                and metadata.region == region
                and not metadata.is_superseded
                and metadata.pre_attempt_commit is not None
            ):
                return metadata.pre_attempt_commit
    if branch_head_reader is None:
        raise BdConfigError(_MSG_NO_HEAD_READER)
    return branch_head_reader()


def _derive_key(
    root: RootRecord, request: MintRequest, outcome_taken: Outcome | None
) -> str:
    """The §3.2 natural key for this mint."""
    if request.mint_reason is MintReason.ENTRY:
        entry = root.definition.document.graph.entry
        if request.node != entry:
            raise CarrierIntegrityError(
                _MSG_ENTRY_NODE.format(entry=entry, node=request.node)
            )
        return keys.entry_idempotency_key(root.root_id)
    predecessor_id = request.predecessor_activation_id
    gate_id = request.predecessor_gate_id
    if gate_id is not None and outcome_taken is not None:
        return keys.idempotency_key(root.root_id, gate_id, outcome_taken, request.node)
    if predecessor_id is None or outcome_taken is None:  # pragma: no cover - guarded
        raise CarrierIntegrityError(
            _MSG_NO_PREDECESSOR.format(
                reason=request.mint_reason.value, node=request.node
            )
        )
    return keys.idempotency_key(
        root.root_id, predecessor_id, outcome_taken, request.node
    )


def views_of(
    activations: Sequence[ActivationRecord],
) -> tuple[bounds.ActivationView, ...]:
    """Activations reduced to what the §10 predicates read."""
    return tuple(
        bounds.ActivationView(bead_id=record.bead.id, metadata=record.metadata)
        for record in activations
    )
