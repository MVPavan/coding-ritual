"""Gate and event writes (§3.3, §3.4, §9).

A gate is a plain bead: v1 does not use native `bd gate` machinery, whose
resolve/close paths are unauthenticated (§3.4). The only transition is
`close_gate_verified`, and every refusal on the way there leaves the gate
OPEN — an unverified close is tampering the §10.6 audit sweep must be able
to see.
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Final, NoReturn

import structlog

from workflow_interpreter.bdio import bounds, finalize, keys, reads
from workflow_interpreter.bdio.capabilities import ArtifactReader
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.errors import (
    BdConfigError,
    BoundExceededError,
    CarrierIntegrityError,
    LifecycleConflictError,
    NonceReplayError,
    PayloadMismatchError,
    StaleApprovalError,
)
from workflow_interpreter.bdio.records import GateRecord, RootRecord, parse_gate
from workflow_interpreter.bdio.signing import (
    GatePayload,
    GateVerifier,
    VerifiedApproval,
)
from workflow_interpreter.bdio.wire import (
    BeadRecord,
    BoundSetting,
    EventMetadata,
    EventPayload,
    GateMetadata,
    GateOpenRequest,
    GateReason,
    GateState,
    IssueType,
    ScopedBound,
    metadata_dict,
    parse_bound_key,
)
from workflow_interpreter.schema.models import SYSTEM_OUTCOMES, BindsMode

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

_TITLE_GATE: Final[str] = "wf gate {gate_node} #{seq}"
_TITLE_EVENT: Final[str] = "wf event {from_node} -{outcome}-> {to_node}"
_REASON_GATE: Final[str] = "gate outcome={outcome} signer={fingerprint}"

_MSG_GATE_CLOSED: Final[str] = (
    "gate {gate_id} is already closed {found}, refusing to close it again"
)
_MSG_GATE_MISMATCH: Final[str] = (
    "payload {field}={found!r} does not match gate {gate_id} ({expected!r})"
)
_MSG_GATE_OUTCOME: Final[str] = (
    "payload outcome {outcome} is not declared by gate {gate_id} ({declared})"
)
_MSG_NONCE_REPLAY: Final[str] = (
    "nonce {nonce!r} was already consumed by bead {gate_id} (§9)"
)
_MSG_STALE: Final[str] = (
    "gate {gate_id} binds a mutable document: approved sha256 {approved!r}, "
    "current {current!r} — the gate stays open (§9)"
)
_MSG_UNREADABLE: Final[str] = (
    "gate {gate_id} binds mutable artifact {artifact_ref!r}, which could not "
    "be read at close ({reason}) — the gate stays open (§9)"
)
_MSG_NO_ARTIFACT_REF: Final[str] = (
    "gate {gate_id} binds a mutable document but records no artifact_ref to "
    "re-hash — the gate stays open (§9)"
)
_MSG_NO_ARTIFACT_READER: Final[str] = (
    "gate {gate_id} binds a mutable document; no artifact_reader was injected, "
    "so the wrapper cannot re-hash it and will not take the caller's word (§9)"
)
_MSG_ARTIFACT_SHAPE: Final[str] = (
    "gate {gate_id} binds={binds}, so its approval payload needs {fields} (§9)"
)
_MSG_MUTATION_UNPARSEABLE: Final[str] = (
    "bound_mutation key {key!r} did not re-parse against the closed bound "
    "vocabulary; the payload validator should have refused it (§9)"
)
_MSG_MUTATION_SCOPE: Final[str] = (
    "bound_mutation scope {scope!r} (key {key!r}) names no {kind} the pinned "
    "graph declares; this setting is scoped to {kind}s ({declared}) (§10.4)"
)
_MSG_MUTATION_LOWERS: Final[str] = (
    "bound_mutation {key!r}={value} does not raise the effective bound "
    "{current}; rebudgets are raise-only (§10.4)"
)
_MSG_GATE_HALF_CLOSED: Final[str] = (
    "gate {gate_id} is marked closed but records no outcome and signer; its "
    "close cannot be repaired forward (§9)"
)
_DECLARED_GRAPH_OUTCOMES: Final[str] = "graph outcomes only"

_SCOPE_REGION: Final[str] = "region"
_SCOPE_NODE: Final[str] = "node"
_SCOPE_KIND: Final[dict[BoundSetting, str]] = {
    BoundSetting.MAX_TOTAL_ACTIVATIONS: _SCOPE_REGION,
    BoundSetting.MAX_ENTRIES: _SCOPE_REGION,
    BoundSetting.MAX_INFRA_RETRIES: _SCOPE_NODE,
    BoundSetting.MAX_STEERS: _SCOPE_NODE,
}
"""What each §10.4 bound's scope names. `max_total_activations` is unscoped —
its entry exists only so the lookup is total."""

_MSG_MISSING_PART: Final[str] = "a gate key part is missing"

_MSG_GATE_REFIND_CLOSED: Final[str] = (
    "gate {gate_id} at key {gate_key} is already CLOSED {outcome!r}; a closed "
    "gate is never re-found as a freshly opened one (§10.3)"
)
_MSG_GATE_REFIND_MISMATCH: Final[str] = (
    "gate {gate_id} was opened with {field}={found!r}, this request asks for "
    "{wanted!r}; the gate at this key is not the gate being requested (§3.4)"
)


def _required[PartT](part: PartT | None) -> PartT:
    """A gate-key part that must be present — `GateOpenRequest` guarantees it."""
    if part is None:  # pragma: no cover - guarded by the request validator
        raise CarrierIntegrityError(_MSG_MISSING_PART)
    return part


def gate_key_for(root_id: str, request: GateOpenRequest, halt_ordinal: int = 0) -> str:
    """The §3.4 deterministic key for this gate — re-ticking re-finds it.

    Every part is required by `GateOpenRequest`'s validator, so nothing here
    substitutes a default: two gates that differ only in a missing part must
    not hash alike. `halt_ordinal` is the count of the root's existing halt
    gates and is read from the trace by `open_gate` (§10.3).
    """
    if request.gate_reason is GateReason.EXHAUSTION:
        return keys.exhaustion_gate_key(
            root_id, _required(request.region), _required(request.round_no)
        )
    if request.gate_reason is GateReason.HALT:
        return keys.halt_gate_key(root_id, halt_ordinal)
    return keys.gate_key(
        root_id,
        request.gate_node,
        _required(request.source_activation_id),
        _required(request.opening_outcome),
    )


def open_gate(client: BdClient, root_id: str, request: GateOpenRequest) -> GateRecord:
    """Open a gate under its deterministic key, or re-find it (drill 6).

    Gate beads count toward the §10.3 ceiling — every one of them, halt gate
    included. The halt gate is exempt from the PREDICATE (it must be mintable
    at the ceiling) and the exemption is applied HERE, where it is visible in
    the refusal decision, never by removing a bead from the count.

    Re-find applies to OPEN gates only, and only to a request that describes
    the gate it re-finds (§10.3 ruling): silently returning a CLOSED gate made
    a later halt or a corrected exhaustion approval unreachable, and silently
    returning a gate whose shape contradicts the request handed the caller an
    `immutable` gate it had asked to bind `mutable` (both probed, phase-2 r3).
    """
    if request.gate_reason is GateReason.HALT:
        halt_gates = _halt_gates(client, root_id)
        still_open = next(
            (gate for gate in halt_gates if gate.metadata.state is GateState.OPEN), None
        )
        if still_open is not None:
            return _refound(still_open, request)
        # Every prior halt gate was closed by a §9-verified approval, so this
        # breach gets its own bead under the next ordinal (§10.3).
        gate_key = gate_key_for(root_id, request, halt_ordinal=len(halt_gates))
    else:
        gate_key = gate_key_for(root_id, request)
        existing = reads.find_gate(client, root_id, gate_key)
        if existing is not None:
            return _refound(existing, request)
    beads = reads.instance_beads(client, root_id)
    root = reads.load_root(client, root_id)
    refusal = bounds.instance_ceiling_refusal(
        bead_count=bounds.ceiling_count(beads),
        # ONE fetch: the ceiling count and the §10.4 rebudget gates that may
        # have raised the ceiling come from the same instance read.
        max_total_activations=bounds.effective_bound(
            root, reads.gates_of(beads), BoundSetting.MAX_TOTAL_ACTIVATIONS
        )
        or 0,
    )
    if refusal is not None and request.gate_reason is not GateReason.HALT:
        raise BoundExceededError(refusal)
    seq = reads.next_seq(beads)
    metadata = GateMetadata(
        wf_root_id=root_id,
        gate_key=gate_key,
        gate_node=request.gate_node,
        gate_type=request.gate_type,
        binds=request.binds,
        gate_reason=request.gate_reason,
        outcomes=request.outcomes,
        source_activation_id=request.source_activation_id,
        opening_outcome=request.opening_outcome,
        region=request.region,
        round_no=request.round_no,
        halt_reason=request.halt_reason,
        seq=seq,
        resume_hint=request.resume_hint,
        artifact_ref=request.artifact_ref,
        artifact_digest=request.artifact_digest,
    )
    record = client._create_bead(
        title=_TITLE_GATE.format(gate_node=request.gate_node, seq=seq),
        metadata=metadata_dict(metadata),
    )
    _LOG.info(
        "wf.gate.opened",
        root_id=root_id,
        gate_id=record.id,
        gate_node=request.gate_node,
        gate_key=gate_key,
    )
    return parse_gate(record)


def _halt_gates(client: BdClient, root_id: str) -> tuple[GateRecord, ...]:
    """Every halt gate of this instance, in `seq` order (§10.3 ordinal source)."""
    return tuple(
        gate
        for gate in reads.list_gates(client, root_id)
        if gate.metadata.gate_reason is GateReason.HALT
    )


def _refound(gate: GateRecord, request: GateOpenRequest) -> GateRecord:
    """Return an OPEN gate the request re-finds, or refuse loudly (§3.4, §10.3).

    Two refusals, both of which used to be silent successes. A CLOSED gate is a
    decision already taken: handing it back as a freshly opened gate wedges the
    §10.4 corrected approval and defeats the §10.6 halt sweep. And a request
    that contradicts the recorded gate is not the same gate: the caller asked
    for outcomes, a `binds` mode or an artifact this bead does not carry, and
    would otherwise proceed believing it got them.

    `halt_reason` and `resume_hint` are excluded on purpose — they are
    descriptive metadata (§10.3), and a second tick describing the same open
    halt in different words must still re-find it rather than wedge the halt.
    """
    if gate.metadata.state is GateState.CLOSED:
        raise LifecycleConflictError(
            _MSG_GATE_REFIND_CLOSED.format(
                gate_id=gate.gate_id,
                gate_key=gate.metadata.gate_key,
                outcome=None
                if gate.metadata.outcome is None
                else gate.metadata.outcome.value,
            )
        )
    recorded = gate.metadata
    for field, found, wanted in (
        ("gate_node", recorded.gate_node, request.gate_node),
        ("gate_type", recorded.gate_type, request.gate_type),
        ("binds", recorded.binds, request.binds),
        ("gate_reason", recorded.gate_reason, request.gate_reason),
        ("outcomes", recorded.outcomes, request.outcomes),
        (
            "source_activation_id",
            recorded.source_activation_id,
            request.source_activation_id,
        ),
        ("opening_outcome", recorded.opening_outcome, request.opening_outcome),
        ("region", recorded.region, request.region),
        ("round_no", recorded.round_no, request.round_no),
        ("artifact_ref", recorded.artifact_ref, request.artifact_ref),
        ("artifact_digest", recorded.artifact_digest, request.artifact_digest),
    ):
        if found != wanted:
            raise CarrierIntegrityError(
                _MSG_GATE_REFIND_MISMATCH.format(
                    gate_id=gate.gate_id, field=field, found=found, wanted=wanted
                )
            )
    return gate


def close_gate_verified(
    client: BdClient,
    verifier: GateVerifier,
    root_id: str,
    gate_id: str,
    *,
    payload_bytes: bytes,
    signature: bytes,
    artifact_reader: ArtifactReader | None = None,
) -> GateRecord:
    """Take a gate's edge — only after a §9 signature verifies.

    Order: verify the signature, then the payload describes THIS gate of THIS
    instance, then the nonce is unused, then a mutable artifact still hashes to
    what was approved. Only after all four does anything get written.

    A `rebudget` bound is part of THAT ONE WRITE — `bound_key`/`bound_value`
    land in the same `model_copy` as the outcome, the fingerprint and the
    payload digest (§9). Nothing is written to the root, so there is no
    apply/close window to crash in, and two rebudgets closing concurrently
    write two different beads instead of racing one whole-object root merge
    that provably lost one of them (probed, phase-2 r3/r4).

    An already-closed gate is repaired forward, never refused: the carrier is
    written before the bd close, so a crash between them leaves a gate whose
    decision is recorded and whose bead is open. Re-submitting the SAME payload
    finishes it. Only a different payload against a closed gate is a conflict.

    Verification runs FIRST, before any carrier state is read or repaired: the
    repair path has the payload and the signature in hand, so there is no
    reason for it to trust mutable metadata about a decision it can check
    itself (§0.3 defence in depth, phase-2 review).
    """
    with tempfile.TemporaryDirectory() as work_dir:
        approval = verifier.verify(
            payload_bytes=payload_bytes,
            signature=signature,
            work_dir=Path(work_dir),
        )
    gate = reads.load_gate(client, gate_id)
    if gate.metadata.state is GateState.CLOSED:
        return _repair_closed_gate(client, gate, approval)
    root = reads.load_root(client, root_id)
    _assert_payload_matches(root, gate, approval)
    _assert_nonce_unused(client, root_id, gate_id, approval.payload.nonce)
    _assert_raises_bound(client, root, approval)
    _assert_fresh_artifact(client, gate, approval, artifact_reader)

    mutation = approval.payload.bound_mutation
    metadata = gate.metadata.model_copy(
        update={
            "state": GateState.CLOSED,
            "outcome": approval.payload.outcome,
            "verified_fingerprint": approval.fingerprint,
            "nonce": approval.payload.nonce,
            "payload_digest": approval.payload_digest,
            # The §10.4 raise, bound to the decision that authorized it.
            "bound_key": None if mutation is None else mutation.key,
            "bound_value": None if mutation is None else mutation.value,
        }
    )
    updated = client._merge_metadata(gate_id, metadata_dict(metadata))
    closed = finalize.close_forward(client, updated, _gate_close_reason(approval))
    _LOG.info(
        "wf.gate.closed",
        gate_id=gate_id,
        outcome=approval.payload.outcome.value,
        signer=approval.fingerprint,
    )
    return parse_gate(closed)


def _gate_close_reason(approval: VerifiedApproval) -> str:
    """The structured close reason recording who approved what."""
    return _REASON_GATE.format(
        outcome=approval.payload.outcome.value, fingerprint=approval.fingerprint
    )


def _repair_closed_gate(
    client: BdClient,
    gate: GateRecord,
    approval: VerifiedApproval,
) -> GateRecord:
    """Finish (or confirm) a gate whose carrier already recorded its decision.

    Identity is the payload digest of an approval that ALREADY verified, so the
    re-submission is checked both against the §9 allow-list and against the
    bytes that actually closed the gate.

    Only the bd close can still be owed. A `rebudget` bound is recorded in the
    same carrier write as the decision, so a gate whose carrier says CLOSED
    already carries its raise — there is nothing left to converge, and no
    window in which a closed gate's signed raise is not in effect.
    """
    recorded = gate.metadata.payload_digest
    if recorded is not None and recorded != approval.payload_digest:
        raise LifecycleConflictError(
            _MSG_GATE_CLOSED.format(gate_id=gate.gate_id, found=gate.metadata.outcome)
        )
    outcome = gate.metadata.outcome
    fingerprint = gate.metadata.verified_fingerprint
    if outcome is None or fingerprint is None:
        raise CarrierIntegrityError(_MSG_GATE_HALF_CLOSED.format(gate_id=gate.gate_id))
    reason = _REASON_GATE.format(outcome=outcome.value, fingerprint=fingerprint)
    repaired = finalize.close_forward(client, gate.bead, reason)
    _LOG.info("wf.gate.repaired", gate_id=gate.gate_id, outcome=outcome.value)
    return parse_gate(repaired)


def append_event(
    client: BdClient, root_id: str, payload: EventPayload, *, seq: int | None = None
) -> BeadRecord:
    """Append one transition event, idempotently (§3.3).

    Events are an audit projection: backfilling after a crash must not
    duplicate, so the event carries a deterministic key and a re-append
    re-finds it. The payload is INLINE JSON — `--event-payload @file` stores
    the literal string `"@file"` and exits 0 (probed 2026-08-25).
    """
    event_key = keys.event_key(
        root_id,
        payload.activation_id,
        payload.from_node,
        payload.outcome,
        payload.to_node,
    )
    existing = reads.find_event(client, root_id, event_key)
    if existing is not None:
        return existing
    beads = reads.instance_beads(client, root_id)
    metadata = EventMetadata(
        wf_root_id=root_id,
        event_key=event_key,
        seq=reads.next_seq(beads) if seq is None else seq,
    )
    record = client._create_bead(
        title=_TITLE_EVENT.format(
            from_node=payload.from_node,
            outcome=payload.outcome.value,
            to_node=payload.to_node,
        ),
        metadata=metadata_dict(metadata),
        issue_type=IssueType.EVENT,
        event_payload=metadata_dict(payload),
    )
    _LOG.debug("wf.event.appended", root_id=root_id, event_id=record.id)
    return record


def _assert_payload_matches(
    root: RootRecord, gate: GateRecord, approval: VerifiedApproval
) -> None:
    """§9 cross-checks: the payload must describe THIS gate of THIS instance.

    Gate OWNERSHIP is one of them: a payload naming this root is worthless if
    the gate bead it is being applied to belongs to another instance. That
    check is also what makes per-root nonce scope sufficient (§9 ruling) — a
    cross-root replay fails here, before the nonce is consulted.
    """
    payload = approval.payload
    for field, found, expected in (
        ("wf_root_id", gate.metadata.wf_root_id, root.root_id),
        ("root_id", payload.root_id, root.root_id),
        ("graph_id", payload.graph_id, root.metadata.graph_id),
        ("gate_key", payload.gate_key, gate.metadata.gate_key),
    ):
        if found != expected:
            raise PayloadMismatchError(
                _MSG_GATE_MISMATCH.format(
                    field=field, found=found, gate_id=gate.gate_id, expected=expected
                )
            )
    if payload.outcome in SYSTEM_OUTCOMES:
        raise PayloadMismatchError(
            _MSG_GATE_OUTCOME.format(
                outcome=payload.outcome.value,
                gate_id=gate.gate_id,
                declared=_DECLARED_GRAPH_OUTCOMES,
            )
        )
    if payload.outcome not in gate.metadata.outcomes:
        raise PayloadMismatchError(
            _MSG_GATE_OUTCOME.format(
                outcome=payload.outcome.value,
                gate_id=gate.gate_id,
                declared=", ".join(outcome.value for outcome in gate.metadata.outcomes),
            )
        )
    _assert_artifact_shape(gate, payload)
    if gate.metadata.binds is BindsMode.IMMUTABLE:
        if (
            gate.metadata.artifact_ref is not None
            and payload.artifact.commit_oid != gate.metadata.artifact_ref
        ):
            raise PayloadMismatchError(
                _MSG_GATE_MISMATCH.format(
                    field="commit_oid",
                    found=payload.artifact.commit_oid,
                    gate_id=gate.gate_id,
                    expected=gate.metadata.artifact_ref,
                )
            )
        if (
            gate.metadata.artifact_digest is not None
            and payload.artifact.tree_oid != gate.metadata.artifact_digest
        ):
            raise PayloadMismatchError(
                _MSG_GATE_MISMATCH.format(
                    field="tree_oid",
                    found=payload.artifact.tree_oid,
                    gate_id=gate.gate_id,
                    expected=gate.metadata.artifact_digest,
                )
            )


def _assert_artifact_shape(gate: GateRecord, payload: GatePayload) -> None:
    """§9: the artifact members the gate's `binds` mode makes the authority.

    `immutable` — the signature is over the commit and tree OIDs, so both must
    be there or there is nothing the human actually approved. `mutable` — the
    sha256 is what gets re-hashed at close; without it the freshness check is
    vacuous.
    """
    required = (
        (("sha256", payload.artifact.sha256),)
        if gate.metadata.binds is BindsMode.MUTABLE
        else (
            ("commit_oid", payload.artifact.commit_oid),
            ("tree_oid", payload.artifact.tree_oid),
        )
    )
    missing = [name for name, value in required if not value]
    if missing:
        raise PayloadMismatchError(
            _MSG_ARTIFACT_SHAPE.format(
                gate_id=gate.gate_id,
                binds=gate.metadata.binds.value,
                fields=", ".join(missing),
            )
        )


def _assert_raises_bound(
    client: BdClient, root: RootRecord, approval: VerifiedApproval
) -> None:
    """§10.4: a `rebudget` may only RAISE a bound, and only a declared one.

    The key vocabulary and positivity are checked on the payload itself; this
    is the part that needs the instance — the value must exceed what is
    currently effective (creation config ⊕ the closed rebudget gates), and a
    scoped key must name a region or node the pinned graph actually declares.

    The gates are fetched HERE rather than by the caller, after the
    mutation-is-`None` return: an ordinary approval carries no bound and owes
    bd no extra query.

    Raise-only arithmetic is checked on VALUE, so a re-submission of an
    approval whose raise already landed would compare the mutation against
    itself ("9 does not raise 9") and wedge the gate. That used to be
    reachable, because the bound was written to the root in a separate write
    from the gate's close; it no longer is, since the raise and the CLOSED
    state are one write and a re-submission is routed to the repair path
    before reaching here. The IDENTITY check stays as §0.3 defence in depth
    against that window reopening, and stays scoped to identity: a DIFFERENT
    approval carrying the same number is a second human decision that raises
    nothing, and is refused.
    """
    mutation = approval.payload.bound_mutation
    if mutation is None:
        return
    instance_gates = reads.list_gates(client, root.root_id)
    if approval.payload_digest in bounds.applied_digests(
        instance_gates
    ):  # pragma: no cover - the close is atomic, so this window is closed
        return
    parsed = parse_bound_key(mutation.key)
    if parsed is None:  # pragma: no cover - guarded by the payload validator
        raise PayloadMismatchError(_MSG_MUTATION_UNPARSEABLE.format(key=mutation.key))
    _assert_known_scope(root, parsed, mutation.key)
    current = bounds.effective_bound(root, instance_gates, parsed.setting, parsed.scope)
    if current is not None and mutation.value <= current:
        raise PayloadMismatchError(
            _MSG_MUTATION_LOWERS.format(
                key=mutation.key, value=mutation.value, current=current
            )
        )


def _assert_known_scope(root: RootRecord, parsed: ScopedBound, key: str) -> None:
    """§10.4: the mutation's scope must name a thing ITS OWN setting is scoped to.

    `max_entries` lives on regions, `max_infra_retries` and `max_steers` on
    nodes. Accepting either vocabulary for either setting let a region-scoped
    key name a node (and the reverse): the entry landed in `resolved_config`,
    matched no real bound, and the gate took its `rebudget` edge while the
    signed approval changed nothing (probed, phase-2 r3).
    """
    index = root.index
    declared: frozenset[str]
    if parsed.setting is BoundSetting.MAX_TOTAL_ACTIVATIONS:
        declared = frozenset()
    elif parsed.setting is BoundSetting.MAX_ENTRIES:
        declared = frozenset(index.regions)
    else:
        declared = frozenset(index.nodes)
    if parsed.scope and parsed.scope not in declared:
        raise PayloadMismatchError(
            _MSG_MUTATION_SCOPE.format(
                scope=parsed.scope,
                key=key,
                kind=_SCOPE_KIND[parsed.setting],
                declared=", ".join(sorted(declared)) or "none",
            )
        )


def _assert_nonce_unused(
    client: BdClient, root_id: str, gate_id: str, nonce: str
) -> None:
    """Refuse a replayed nonce (§9): a nonce is consumed by the gate it closed."""
    for bead in reads.beads_with_nonce(client, root_id, nonce):
        if bead.id != gate_id:
            raise NonceReplayError(
                _MSG_NONCE_REPLAY.format(nonce=nonce, gate_id=bead.id)
            )


def _assert_fresh_artifact(
    client: BdClient,
    gate: GateRecord,
    approval: VerifiedApproval,
    artifact_reader: ArtifactReader | None,
) -> None:
    """`binds = "mutable"`: re-hash at close, or refuse with an edit receipt (§9).

    The digest is computed HERE, from bytes the injected workspace-scoped
    reader returns — never accepted from the caller. A caller-echoed digest is
    not a re-hash: the party the check constrains would be asserting its own
    compliance (§9 ruling, phase-2 review).

    Every failure on this path leaves the gate OPEN and writes the edit receipt
    first, including the unreadable-artifact case: "the document could not be
    read" is exactly the kind of thing the §10.6 sweep must be able to see.
    """
    if gate.metadata.binds is not BindsMode.MUTABLE:
        return
    if artifact_reader is None:
        raise BdConfigError(_MSG_NO_ARTIFACT_READER.format(gate_id=gate.gate_id))
    artifact_ref = gate.metadata.artifact_ref
    if artifact_ref is None:
        _refuse_stale(client, gate, _MSG_NO_ARTIFACT_REF.format(gate_id=gate.gate_id))
    try:
        current = hashlib.sha256(artifact_reader(artifact_ref)).hexdigest()
    except Exception as exc:  # noqa: BLE001 - any reader failure fails closed
        _refuse_stale(
            client,
            gate,
            _MSG_UNREADABLE.format(
                gate_id=gate.gate_id, artifact_ref=artifact_ref, reason=exc
            ),
        )
    if approval.payload.artifact.sha256 == current:
        return
    _refuse_stale(
        client,
        gate,
        _MSG_STALE.format(
            gate_id=gate.gate_id,
            approved=approval.payload.artifact.sha256,
            current=current,
        ),
    )


def _refuse_stale(client: BdClient, gate: GateRecord, receipt: str) -> NoReturn:
    """Record the edit receipt on the still-open gate, then refuse (§9)."""
    metadata = gate.metadata.model_copy(
        update={
            "stale_approval_receipts": (*gate.metadata.stale_approval_receipts, receipt)
        }
    )
    client._merge_metadata(gate.gate_id, metadata_dict(metadata))
    _LOG.warning("wf.gate.stale_approval", gate_id=gate.gate_id, receipt=receipt)
    raise StaleApprovalError(receipt)
