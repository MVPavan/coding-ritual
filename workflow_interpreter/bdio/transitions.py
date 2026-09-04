"""The §5.1 activation transitions — delta-only writes over a re-read carrier.

Split out of `api.py` the way `roots`, `gates`, `canary`, `finalize` and
`supervision` already are: `WorkflowStore` keeps the methods — it is still the
only public surface (§0.1) — and the write mechanics live here.

**Every transition writes ONLY the keys it owns.** The earlier version re-emitted
the WHOLE carrier from the read the method opened with, on the argument that a
full re-write is idempotent because bd merges metadata. That argument holds for
one writer and fails for two, and B5 made the supervisor a RESIDENT process:
`record_dispatch`, `record_exit` and `record_evidence` are all issued by it,
concurrently with foreman ticks by design. A whole-carrier merge from a stale
read then re-emits every OTHER key as it stood at read time, so a foreman that
closed the activation in between (a §8.1 steer) had its `deviations`, `evidence`
and `usage` silently rolled back to their pre-close values — and `lifecycle`
dragged behind a bd row already marked closed (probed).

bd offers no compare-and-set, so three things replace one:

1. **Delta-only.** Each transition emits `lifecycle` plus its own record and
   nothing else, so no key it does not own can travel with a stale read.
2. **A fresh load, re-checked at the write.** `apply` re-reads the activation
   and re-asserts the states this transition is legal from, as close to the
   write as bd allows. It narrows the window; it cannot close it, because the
   interleaving can still land between that check and the merge.
3. **A recorded outcome is TERMINAL, whatever the lifecycle says.** That is what
   makes the residue harmless. The one key a losing race can still drag
   backwards is `lifecycle`, and every guard that protects §3.3 routing truth
   now keys on `ActivationMetadata.is_settled` — the recorded outcome — rather
   than on a lifecycle a later write can move. `repair_forward` then restores
   the terminal lifecycle the race wrote over, so the inconsistent row does not
   survive the call that created it.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Final

import structlog

from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.errors import (
    CarrierIntegrityError,
    LifecycleConflictError,
)
from workflow_interpreter.bdio.finalize import close_forward
from workflow_interpreter.bdio.records import ActivationRecord, parse_activation
from workflow_interpreter.bdio.wire import (
    KEY_LIFECYCLE,
    ActivationMetadata,
    Deviation,
    Evidence,
    Lifecycle,
    Metadata,
    Usage,
    metadata_dict,
)

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

OPEN_LIFECYCLES: Final[frozenset[Lifecycle]] = frozenset(
    {
        Lifecycle.MINTED,
        Lifecycle.DISPATCHED,
        Lifecycle.EXIT_RECORDED,
        Lifecycle.EVIDENCE_RECORDED,
    }
)
"""The states a terminal transition (close, supersede) may still be applied
from. `CLOSED` and `SUPERSEDED` are the terminals themselves."""

_MSG_LIFECYCLE: Final[str] = (
    "activation {activation_id} is {found}, cannot apply {wanted} "
    "(the recorded state wins; §5.1)"
)
_MSG_SETTLED: Final[str] = (
    "activation {activation_id} already recorded outcome {outcome} at lifecycle "
    "{found}; writing {wanted} over it would rewrite the §3.3 routing truth a "
    "successor was minted from"
)
_MSG_RACED: Final[str] = (
    "activation {activation_id} moved to {found} between this transition's "
    "guard and its write; refusing to apply {wanted} (§5.1)"
)
_MSG_SESSION_DRIFT: Final[str] = (
    "activation {activation_id} recorded session {recorded!r} at dispatch and "
    "this dispatch carries {found!r}; renaming it would point every "
    "continuation and infra retry at a session the child never ran (§5.2)"
)
_MSG_CLOSE_PAYLOAD: Final[str] = (
    "activation {activation_id} is already closed {outcome}; this close "
    "carries a different {field}, which the recorded close would silently drop "
    "(§3.3)"
)

ActivationLoader = Callable[[str], ActivationRecord]
"""Reads one activation through the carrier contract (`WorkflowReads`). Passed
in rather than a pre-loaded record so the re-read happens HERE, immediately
before the guard and the write."""


def assert_lifecycle(
    record: ActivationRecord, expected: Lifecycle, wanted: Lifecycle
) -> None:
    """Refuse a state write that contradicts the recorded state (§5.1)."""
    if record.metadata.lifecycle is not expected:
        raise LifecycleConflictError(
            _MSG_LIFECYCLE.format(
                activation_id=record.activation_id,
                found=record.metadata.lifecycle.value,
                wanted=wanted.value,
            )
        )


def assert_not_settled(record: ActivationRecord, wanted: Lifecycle) -> None:
    """Refuse any state write past a RECORDED outcome (§3.3).

    Deliberately not a lifecycle check. A losing race can drag `lifecycle`
    backwards under a bd row that is already closed — leaving, for instance,
    `status=closed lifecycle=exit-recorded outcome=steered` — and the lifecycle
    guard then waves the next write straight through: `record_evidence` was
    legal on that row, and the close after it overwrote the `steered` a
    continuation had already been minted from (probed, round 3). The outcome is
    the routing truth, so the outcome is what the refusal keys on.
    """
    if not record.metadata.is_settled:
        return
    raise LifecycleConflictError(
        _MSG_SETTLED.format(
            activation_id=record.activation_id,
            outcome=None
            if record.metadata.outcome is None
            else record.metadata.outcome.value,
            found=record.metadata.lifecycle.value,
            wanted=wanted.value,
        )
    )


def assert_same_session(activation_id: str, recorded: str, found: str) -> None:
    """A recorded session id is the one the child ran; a second one contradicts it.

    Silently keeping the first would be the quiet half of the same bug §5.2
    exists to prevent: every continuation and infra retry copies this id, so a
    dispatch carrying a DIFFERENT non-empty session means one of the two rows
    describes a child nobody can resume. Fails loud, like every other guard
    here; an empty id on either side is simply nothing to compare.
    """
    if recorded and found and recorded != found:
        raise LifecycleConflictError(
            _MSG_SESSION_DRIFT.format(
                activation_id=activation_id, recorded=recorded, found=found
            )
        )


def assert_same(
    activation_id: str, found: object, wanted: object, state: Lifecycle
) -> None:
    """Re-applying a recorded state is a no-op; contradicting it is an error."""
    if found != wanted:
        raise LifecycleConflictError(
            _MSG_LIFECYCLE.format(
                activation_id=activation_id,
                found=f"{state.value} with a different record",
                wanted=state.value,
            )
        )


def assert_close_payload(
    record: ActivationRecord,
    evidence: Evidence | None,
    usage: Usage | None,
    deviations: Sequence[Deviation],
) -> None:
    """A repeated close must carry the SAME payload, or it is dropping data.

    The recorded close wins (§5.1), so re-closing with new evidence, usage
    or deviations used to succeed while writing none of them — a caller
    could believe its late evidence was recorded (probed, phase-2 r3). The
    same payload is idempotent; a different one fails loud.
    """
    recorded = record.metadata
    mismatches = (
        ("evidence", evidence is not None and evidence != recorded.evidence),
        ("usage", usage is not None and usage != recorded.usage),
        (
            "deviations",
            any(deviation not in recorded.deviations for deviation in deviations),
        ),
    )
    for field, differs in mismatches:
        if differs:
            raise CarrierIntegrityError(
                _MSG_CLOSE_PAYLOAD.format(
                    activation_id=record.activation_id,
                    outcome=None
                    if recorded.outcome is None
                    else recorded.outcome.value,
                    field=field,
                )
            )


def apply(
    client: BdClient,
    load: ActivationLoader,
    activation_id: str,
    *,
    lifecycle: Lifecycle,
    allowed: frozenset[Lifecycle],
    **changes: object,
) -> ActivationRecord:
    """Move the §5.1 state, writing ONLY this transition's own keys.

    `allowed` is re-asserted against a FRESH read rather than against whatever
    the caller loaded: the caller's guards ran before a bd round-trip, and the
    supervisor is not serialised by the §4 tick. What remains after that is the
    merge itself, which `repair_forward` cleans up.

    The recorded outcome is re-asserted with it, and here rather than in each
    caller: `allowed` is a set of LIFECYCLES, so a row whose lifecycle a losing
    race dragged back under a recorded outcome still sits in it (probed, r4 —
    `supersede_activation` walked through on `lifecycle=exit-recorded
    outcome=steered`). Every transition that reaches this writer is refused past
    a settled outcome, whatever the caller checked before the round-trip.
    """
    fresh = load(activation_id)
    assert_not_settled(fresh, lifecycle)
    if fresh.metadata.lifecycle not in allowed:
        raise LifecycleConflictError(
            _MSG_RACED.format(
                activation_id=activation_id,
                found=fresh.metadata.lifecycle.value,
                wanted=lifecycle.value,
            )
        )
    owned: dict[str, object] = {KEY_LIFECYCLE: lifecycle, **changes}
    metadata = fresh.metadata.model_copy(update=owned)
    merged = client._merge_metadata(activation_id, _delta(metadata, owned))
    return repair_forward(client, parse_activation(merged))


def repair_forward(client: BdClient, record: ActivationRecord) -> ActivationRecord:
    """Restore the terminal lifecycle a losing race wrote over (§5.1, §3.3).

    A transition whose merge landed after a concurrent close leaves a recorded
    outcome under a non-terminal `lifecycle`. Nothing routes on `lifecycle`
    where it matters any more, but the inconsistency is real and it is this
    call's residue, so this call cleans it up rather than leaving it for §5.6
    to interpret. The transition's OWN record (the exit, the evidence) is kept:
    it is a true observation, and bd cannot clear a key anyway.
    """
    metadata = record.metadata
    if metadata.outcome is None:
        return record
    terminal = Lifecycle.SUPERSEDED if metadata.is_superseded else Lifecycle.CLOSED
    if metadata.lifecycle is terminal:
        return record
    _LOG.warning(
        "wf.activation.lifecycle_repaired",
        activation_id=record.activation_id,
        found=metadata.lifecycle.value,
        outcome=metadata.outcome.value,
        restored=terminal.value,
    )
    return parse_activation(
        client._merge_metadata(record.activation_id, {KEY_LIFECYCLE: terminal.value})
    )


def finish(client: BdClient, record: ActivationRecord, reason: str) -> ActivationRecord:
    """Drive this activation's bd close to completion, idempotently."""
    return parse_activation(close_forward(client, record.bead, reason))


def _delta(metadata: ActivationMetadata, owned: dict[str, object]) -> Metadata:
    """The owned keys alone, rendered exactly as bd stores the whole carrier.

    Built by dumping the model and then SELECTING, rather than by serializing
    each value by hand: the read-back verification in `client.py` compares what
    bd stored against what was written, so a delta has to be JSON-typed by the
    same code path the full carrier is.
    """
    full = metadata_dict(metadata)
    keys = {_wire_key(name) for name in owned}
    return {key: value for key, value in full.items() if key in keys}


def _wire_key(field: str) -> str:
    """The bd metadata key one `ActivationMetadata` field serializes to."""
    info = ActivationMetadata.model_fields[field]
    return info.serialization_alias or info.alias or field


__all__ = [
    "OPEN_LIFECYCLES",
    "ActivationLoader",
    "apply",
    "assert_close_payload",
    "assert_lifecycle",
    "assert_not_settled",
    "assert_same",
    "assert_same_session",
    "finish",
    "repair_forward",
]
