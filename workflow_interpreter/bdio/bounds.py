"""§10 pre-mint predicates — total by construction, evaluated before any mint.

Every predicate is a pure function with an explicit operator, so the refusal
carries the arithmetic that produced it and the §10.1 worked example can be
asserted verbatim. Counting is fail-closed throughout: what cannot be
classified still consumes the ceiling, and a round that cannot be counted
refuses the mint rather than allowing it.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio.constants import (
    DEVIATION_INPUTS_UNAVAILABLE,
    DEVIATION_PRECONDITION_REFUSED,
)
from workflow_interpreter.bdio.errors import BoundEvaluationError
from workflow_interpreter.bdio.records import GateRecord, RootRecord
from workflow_interpreter.bdio.wire import (
    KEY_WF_KIND,
    ActivationMetadata,
    BeadRecord,
    BoundSetting,
    GateState,
    Lifecycle,
    WfKind,
)
from workflow_interpreter.schema.models import Outcome

INFRA_OUTCOMES: Final[frozenset[Outcome]] = frozenset(
    {Outcome.ERROR_RUNNER, Outcome.ERROR_TRANSPORT}
)
"""§10.2: the system outcomes `max_infra_retries` counts."""

_RETRY_EXEMPT_DEVIATIONS: Final[frozenset[str]] = frozenset(
    {DEVIATION_PRECONDITION_REFUSED, DEVIATION_INPUTS_UNAVAILABLE}
)
"""Deviations whose close is a dead end, not a spent §10.2 retry: the runner
never ran, and the frontier sends both of them to a halt gate.

`continuation_refused` is deliberately NOT here. A refused §8.1 continuation
(no session to rejoin, or a steer intent that has gone) is a real infra close
and must consume the budget: exempt, it would never reach the fallback gate and
the instance would re-dispatch the same refusal forever (cr-o85.19)."""

_UNCOUNTED_KINDS: Final[frozenset[str]] = frozenset(
    {WfKind.EVENT.value, WfKind.ROOT.value}
)
"""The only two kinds outside the §10.3 count: the derived audit projection
and the instance record itself."""

_OP_CEILING: Final[str] = "count(activation+gate) >= max_total_activations"
_OP_ROUNDS: Final[str] = "distinct_round_no(region) >= max_entries"
_OP_INFRA: Final[str] = "consecutive_infra_closes >= max_infra_retries + 1"
_OP_STEERS: Final[str] = "steer_closes >= max_steers"

_MSG_CEILING: Final[str] = (
    "instance ceiling reached: {observed} activation+gate beads "
    "(limit {limit}) — refuse every mint, open the halt gate (§10.3)"
)
_MSG_ROUNDS: Final[str] = (
    "region {scope!r} has used {observed} of {limit} rounds; round {target} "
    "would be a new one — exhausted (§10.1)"
)
_MSG_INFRA: Final[str] = (
    "node {scope!r} round {target} already used {observed} consecutive infra "
    "attempts (1 + max_infra_retries = {limit}) — route to fallback (§10.2)"
)
_MSG_STEERS: Final[str] = (
    "node {scope!r} round {target} already used {observed} of {limit} steer "
    "continuations (§10.2)"
)
_MSG_MISSING_ROUND: Final[str] = (
    "activation {bead_id} in region {region!r} carries no usable round_no — "
    "the round bound cannot be evaluated, so the mint is refused (§10)"
)


class BoundKind(StrEnum):
    """Which §10 bound refused."""

    INSTANCE_CEILING = "instance_ceiling"
    REGION_ROUNDS = "region_rounds"
    INFRA_RETRIES = "infra_retries"
    STEERS = "steers"


class BoundRefusal(BaseModel):
    """A refused pre-mint predicate, carrying its arithmetic."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    bound: BoundKind
    observed: int
    limit: int
    operator: str
    detail: str


class ActivationView(BaseModel):
    """An activation bead reduced to what the bound predicates need."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    bead_id: str
    metadata: ActivationMetadata


# --- the effective bound ------------------------------------------------


def effective_bound(
    root: RootRecord,
    gates: Iterable[GateRecord],
    setting: BoundSetting,
    scope: str = "",
) -> int | None:
    """The bound in force: creation config ⊕ closed rebudget gates, max per key.

    Three layers (§3.1, §10.4). The pinned graph is the floor. The root's
    resolved config — fixed at create and never written again — overrides it,
    in either direction, because a resolution is a deliberate statement about
    this instance. Every §9 `rebudget` then RAISES, and its raise lives on the
    gate bead whose approval carried it.

    Max, not last-writer, is what makes the concurrent case total: two gates
    closed in one window are two independent bead writes that cannot clobber
    each other, and reading them back as a maximum means neither signed raise
    can be lost by the order they landed in. A whole-object merge on the root
    lost one of them outright, and no read-back check could see it — the
    writer never held the data it was overwriting (probed, phase-2 r3/r4).

    A gate contributes ONLY when it is closed with outcome `rebudget` and
    carries a bound: an open gate is a decision not yet taken.
    """
    key = setting.at(scope)
    override = next(
        (
            entry.value
            for entry in root.metadata.resolved_config
            if entry.key == key and isinstance(entry.value, int)
        ),
        None,
    )
    base = override if override is not None else _pinned_bound(root, setting, scope)
    values = [value for value in (base, *_gate_raises(gates, key)) if value is not None]
    return max(values) if values else None


def _gate_raises(gates: Iterable[GateRecord], key: str) -> tuple[int, ...]:
    """Every bound this key was raised to by a CLOSED rebudget gate (§10.4).

    Requires the gate's signature evidence: a bound on a gate that carries no
    verified fingerprint or payload digest was never written by
    `close_gate_verified` (which records all of them in one write) — counting
    it would let raw metadata tampering raise a bound (§0.3 hardening,
    phase-2 micro-confirm).
    """
    return tuple(
        gate.metadata.bound_value
        for gate in gates
        if gate.metadata.state is GateState.CLOSED
        and gate.metadata.outcome is Outcome.REBUDGET
        and gate.metadata.bound_key == key
        and gate.metadata.bound_value is not None
        and gate.metadata.verified_fingerprint is not None
        and gate.metadata.payload_digest is not None
    )


def _pinned_bound(root: RootRecord, setting: BoundSetting, scope: str) -> int | None:
    """The bound as the root's pinned graph body declares it."""
    index = root.index
    if setting is BoundSetting.MAX_TOTAL_ACTIVATIONS:
        return root.definition.document.instance.max_total_activations
    if setting is BoundSetting.MAX_ENTRIES:
        region = index.regions.get(scope)
        return None if region is None else region.max_entries
    node = index.nodes.get(scope)
    if node is None:
        return None
    if setting is BoundSetting.MAX_INFRA_RETRIES:
        return node.max_infra_retries
    return node.max_steers


def applied_digests(gates: Iterable[GateRecord]) -> frozenset[str]:
    """Payload digests of the approvals that already CLOSED a gate (§10.4).

    The identity half of the raise-only rule: "this exact approval already
    landed" is now a closed gate bead carrying its digest, not a receipt list
    on the root. Value arithmetic alone cannot tell a re-submission of our own
    approval from a second human granting the same number.
    """
    return frozenset(
        digest
        for gate in gates
        if gate.metadata.state is GateState.CLOSED
        and (digest := gate.metadata.payload_digest) is not None
    )


def instance_ceiling_refusal(
    *, bead_count: int, max_total_activations: int
) -> BoundRefusal | None:
    """§10.3: refuse ANY mint at or above the ceiling. No outcome class is exempt."""
    if bead_count >= max_total_activations:
        return BoundRefusal(
            bound=BoundKind.INSTANCE_CEILING,
            observed=bead_count,
            limit=max_total_activations,
            operator=_OP_CEILING,
            detail=_MSG_CEILING.format(
                observed=bead_count, limit=max_total_activations
            ),
        )
    return None


def region_round_refusal(
    *, region: str, distinct_rounds: frozenset[int], target_round: int, max_entries: int
) -> BoundRefusal | None:
    """§10.1: refuse a mint that would open a NEW round once `max_entries` are used.

    Worked example (`max_entries = 3`): rounds 1, 2 and 3 execute — while
    minting round 3 the region has used {1, 2}, and 2 >= 3 is false — and the
    4th back-edge arrival, minting round 4 with {1, 2, 3} used, exhausts. A
    mint into a round the region has already entered (an infra retry or steer
    continuation, which inherit `round_no`) is never refused here.
    """
    if target_round in distinct_rounds:
        return None
    used = len(distinct_rounds)
    if used >= max_entries:
        return BoundRefusal(
            bound=BoundKind.REGION_ROUNDS,
            observed=used,
            limit=max_entries,
            operator=_OP_ROUNDS,
            detail=_MSG_ROUNDS.format(
                scope=region, observed=used, limit=max_entries, target=target_round
            ),
        )
    return None


def infra_retry_refusal(
    *,
    node: str,
    round_no: int,
    consecutive_infra_closes: int,
    max_infra_retries: int,
) -> BoundRefusal | None:
    """§10.2: `1 + max_infra_retries` attempts per node per round, then fallback."""
    limit = max_infra_retries + 1
    if consecutive_infra_closes >= limit:
        return BoundRefusal(
            bound=BoundKind.INFRA_RETRIES,
            observed=consecutive_infra_closes,
            limit=limit,
            operator=_OP_INFRA,
            detail=_MSG_INFRA.format(
                scope=node,
                target=round_no,
                observed=consecutive_infra_closes,
                limit=limit,
            ),
        )
    return None


def steer_refusal(
    *, node: str, round_no: int, steer_closes: int, max_steers: int
) -> BoundRefusal | None:
    """§10.2: steer continuations are capped separately from infra retries."""
    if steer_closes >= max_steers:
        return BoundRefusal(
            bound=BoundKind.STEERS,
            observed=steer_closes,
            limit=max_steers,
            operator=_OP_STEERS,
            detail=_MSG_STEERS.format(
                scope=node, target=round_no, observed=steer_closes, limit=max_steers
            ),
        )
    return None


# --- counting over the instance's beads ---------------------------------


def ceiling_count(beads: Iterable[BeadRecord]) -> int:
    """§10.3 count: every activation and gate bead of the instance.

    Open, closed, superseded and UNCLASSIFIED all count — a bead carrying the
    instance's `wf_root_id` whose kind cannot be read is counted, because
    fail-closed here means over-counting, never under-counting. Events are a
    derived audit projection and are excluded, and the root is not one of the
    things being counted.

    NOTHING else is excluded, and no metadata flag can remove a bead from the
    count (§10.3 ruling, phase-2 review). The halt gate is exempt from the
    PREDICATE — at the halt-gate call site, where the exemption is visible —
    never from the count, or the one auditable boundedness statement quietly
    under-reports.
    """
    counted = 0
    for bead in beads:
        kind = bead.metadata.get(KEY_WF_KIND)
        if kind in _UNCOUNTED_KINDS:
            continue
        counted += 1
    return counted


def distinct_rounds(
    activations: Sequence[ActivationView], region: str
) -> frozenset[int]:
    """Distinct `round_no` in `region`, superseded activations excluded (§3.2).

    Raises rather than guessing: an in-region activation whose round cannot be
    read makes the §10.1 predicate unevaluable, and §10 is fail-closed.
    """
    rounds: set[int] = set()
    for view in activations:
        if view.metadata.region != region or view.metadata.is_superseded:
            continue
        round_no = view.metadata.round_no
        if round_no < 1:
            raise BoundEvaluationError(
                _MSG_MISSING_ROUND.format(bead_id=view.bead_id, region=region)
            )
        rounds.add(round_no)
    return frozenset(rounds)


def _at_node_round(
    activations: Sequence[ActivationView], node: str, round_no: int
) -> list[ActivationView]:
    """Activations at one node in one round, in `seq` order (never timestamps).

    bd timestamps are second-granularity in read paths (probed), so `seq` — the
    foreman-assigned monotonic counter — is the only ordering.
    """
    selected = [
        view
        for view in activations
        if view.metadata.node == node
        and view.metadata.round_no == round_no
        and not view.metadata.is_superseded
    ]
    return sorted(selected, key=lambda view: (view.metadata.seq, view.bead_id))


def consecutive_infra_closes(
    activations: Sequence[ActivationView], node: str, round_no: int
) -> int:
    """Trailing run of infra closes at `(node, round_no)`.

    §10.2 counts *consecutive* infra failures: a non-infra close in between
    means the node made progress, and the retry budget starts over. Only
    closed activations count — an open one is the attempt being recovered, not
    a consumed retry.
    """
    run = 0
    for view in reversed(_at_node_round(activations, node, round_no)):
        if view.metadata.lifecycle is not Lifecycle.CLOSED:
            continue
        # A refusal the wrapper recorded before the runner could work is a
        # halt-gate dead end (§10.6), never a consumed infra retry.
        if any(
            deviation.kind in _RETRY_EXEMPT_DEVIATIONS
            for deviation in view.metadata.deviations
        ):
            continue
        if view.metadata.outcome in INFRA_OUTCOMES:
            run += 1
            continue
        break
    return run


def steer_closes(
    activations: Sequence[ActivationView], node: str, round_no: int
) -> int:
    """How many activations at `(node, round_no)` were closed `steered` (§8.1)."""
    return sum(
        1
        for view in _at_node_round(activations, node, round_no)
        if view.metadata.outcome is Outcome.STEERED
    )
