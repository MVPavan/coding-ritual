"""The two writes the phase-3 supervisor owns (§3.2 carry-forward, §8.2 stale).

Split out of `api.py` the way `roots`, `gates`, `canary` and `finalize` already
are: `WorkflowStore` keeps the method — it is still the only public surface
(§0.1) — and the rule lives here.

Neither write moves the §5.1 lifecycle. Both are FACTS the supervisor observed
about a running attempt rather than states of it, which is exactly why each
needs its own guard instead of the usual `_assert_lifecycle` transition:

- the carry-forward trio may be re-proven while the activation is `minted` and
  is frozen from `dispatched` onward, because by then it describes a tree the
  child has already worked in and a later rework derives its base from it;
- the stale flag is written once, keeping the FIRST timestamp, because §8.2
  makes staleness a hint for a tier-2 decision and rewriting when it started
  destroys the only thing the hint carries.

**Both writes are DELTA-ONLY, over a freshly read activation.** The earlier
version wrote the whole merged carrier, on the argument that these keysets are
single-writer inside the §4 tick. That argument is void: B5 made the supervisor
a RESIDENT process that outlives the tick, so its stale mirror runs concurrently
with foreman ticks by design. A whole-carrier merge from a stale read then
re-emits every OTHER key as it stood at read time — and a foreman that closed
the activation in between (a §8.1 steer, which is exactly what a stale flag is
supposed to provoke) had `lifecycle` dragged back to `dispatched` under a bd row
already marked closed. §5.6 then read a closed activation as recoverable and
`record_exit` became legal again (probed).

bd offers no compare-and-set, so what remains is: read fresh, re-check the
lifecycle as close to the write as bd allows, and write only the keys this
module owns. The residual window — the activation closing between that check
and the merge landing — can then cost at most a stale-flag key on a closed
activation, which no rule routes on. It cannot move the lifecycle, the handle,
the exit record or the outcome, because those keys are never in the payload.

The §5.1 transitions themselves reached the same conclusion one round later,
from the other direction: they DO own `lifecycle`, so they cannot leave it out
of the payload, and `transitions.py` carries what that costs and how a losing
race is repaired.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

import structlog

from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.errors import LifecycleConflictError
from workflow_interpreter.bdio.records import ActivationRecord, parse_activation
from workflow_interpreter.bdio.wire import (
    Lifecycle,
    Metadata,
    PreconditionRecord,
    StaleFlagRecord,
    metadata_dict,
)

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

KEY_STALE_FLAG: Final[str] = "stale_flag"

_MSG_PRECONDITION_LATE: Final[str] = (
    "activation {activation_id} is {found}; the §3.2 carry-forward describes "
    "the tree the child ALREADY ran against, so rewriting it after dispatch "
    "would change the base a later rework derives from (§3.2, §5.4)"
)
_MSG_STALE_LIFECYCLE: Final[str] = (
    "activation {activation_id} is {found}, not dispatched; a stale flag is a "
    "statement about a RUNNING child (§8.2)"
)

ActivationLoader = Callable[[str], ActivationRecord]
"""Reads one activation through the carrier contract (`WorkflowReads`). Passed
in rather than a pre-loaded record so the read happens HERE, immediately before
the guard and the write."""


def recorded_precondition(record: ActivationRecord) -> PreconditionRecord | None:
    """The §3.2 trio as bd holds it, or `None` when bd holds none of it.

    `None` and "a record of empty strings" are different answers, and conflating
    them broke idempotence in the dangerous direction: an activation with
    nothing recorded compared equal to an all-empty carrier, so the write that
    should have established the trio was skipped as already done.
    """
    metadata = record.metadata
    if metadata.pre_attempt_commit is None or metadata.reset_verified_commit is None:
        return None
    return PreconditionRecord(
        pre_attempt_commit=metadata.pre_attempt_commit,
        reset_verified_commit=metadata.reset_verified_commit,
        pre_attempt_dirty_state=metadata.pre_attempt_dirty_state,
    )


def record_precondition(
    client: BdClient,
    load: ActivationLoader,
    activation_id: str,
    wanted: PreconditionRecord,
) -> ActivationRecord:
    """Write the §3.2 carry-forward trio the §5.4 precondition proved."""
    record = load(activation_id)
    if recorded_precondition(record) == wanted:
        return record
    if record.metadata.lifecycle is not Lifecycle.MINTED:
        raise LifecycleConflictError(
            _MSG_PRECONDITION_LATE.format(
                activation_id=activation_id,
                found=record.metadata.lifecycle.value,
            )
        )
    return _merge(client, activation_id, metadata_dict(wanted))


def record_stale_flag(
    client: BdClient,
    load: ActivationLoader,
    activation_id: str,
    flag: StaleFlagRecord,
) -> ActivationRecord:
    """Mirror the §8.2 stale flag into bd; the FIRST raise wins.

    The lifecycle guard runs BEFORE the first-raise short-circuit. The other
    order let a re-assertion against an exited or closed activation succeed
    silently by returning the stored flag — a documented "dispatched only"
    refusal that a caller could step around simply by asking twice.

    **"First raise wins" holds for ONE writer, and that is the §0.3 assumption
    it rests on.** Two mirrors that both read "no flag yet" both write, and the
    later write lands second, so the LATER timestamp survives (probed,
    Opus#24). bd offers no compare-and-set, so there is no read-modify-write
    this module can make atomic — the honest statement is that this is the
    cooperative single-writer case §0.3 already assumes, not a race that has
    been closed. It costs a timestamp on a hint for a tier-2 decision, and
    nothing routes on it; the §5.1 states, which DO route, are protected
    structurally instead — this write never carries a `lifecycle` key at all.
    """
    record = load(activation_id)
    if record.metadata.lifecycle is not Lifecycle.DISPATCHED:
        raise LifecycleConflictError(
            _MSG_STALE_LIFECYCLE.format(
                activation_id=activation_id,
                found=record.metadata.lifecycle.value,
            )
        )
    if record.metadata.stale_flag is not None:
        return record
    _LOG.warning(
        "wf.activation.stale_recorded",
        activation_id=activation_id,
        last_activity_at=flag.last_activity_at,
    )
    return _merge(client, activation_id, {KEY_STALE_FLAG: metadata_dict(flag)})


def _merge(client: BdClient, activation_id: str, delta: Metadata) -> ActivationRecord:
    """Write ONLY `delta`'s keys and parse what bd read back.

    Deliberately not `transitions.apply`, which is the same discipline for a
    §5.1 STATE: it emits `lifecycle` plus its own record, re-checks the state it
    is moving from against a fresh read, and repairs the lifecycle forward if a
    concurrent close beat it. Neither of those applies to a fact written beside
    a state — there is no lifecycle to move and none to re-check — so this stays
    the narrower call. bd merges metadata per top-level key, and
    `client._merge_metadata` verifies exactly the keys it was handed, so a delta
    is read-back-verified like any other write.
    """
    return parse_activation(client._merge_metadata(activation_id, delta))


__all__ = ["record_precondition", "record_stale_flag", "recorded_precondition"]
