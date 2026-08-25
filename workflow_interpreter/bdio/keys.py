"""Deterministic natural keys for activations, gates and events (§3.2–§3.4).

Every key is a sha256 over domain-tagged, separator-joined parts. The domain
tag makes cross-kind collision impossible (an exhaustion gate key can never
equal an activation's idempotency key), and the separator makes the join
injective — plain concatenation would let `("ab", "c")` and `("a", "bc")`
hash alike.

Re-deriving a key is how a re-tick re-finds work it already minted: the
lookup by key is the only thing standing between a crash and a duplicate
activation (drill 1) or a duplicate gate (drill 6).
"""

from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Final

from workflow_interpreter.schema.models import Outcome

# ASCII unit separator: cannot occur in a bead id, node name or outcome.
_PART_SEPARATOR: Final[str] = "\x1f"
_ENTRY_SENTINEL: Final[str] = "entry"
_NONE_SENTINEL: Final[str] = "\x00none"


class KeyDomain(StrEnum):
    """The tag prefixed to every key's pre-image."""

    ACTIVATION = "wf-activation/1"
    GATE = "wf-gate/1"
    EXHAUSTION_GATE = "wf-exhaustion-gate/1"
    HALT_GATE = "wf-halt-gate/1"
    EVENT = "wf-event/1"


def _key(domain: KeyDomain, *parts: str | None) -> str:
    """sha256 over the domain tag and the separator-joined parts."""
    rendered = _PART_SEPARATOR.join(
        [domain.value, *(_NONE_SENTINEL if part is None else part for part in parts)]
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def entry_idempotency_key(root_id: str) -> str:
    """`hash(root_id, "entry")` — the instance's first activation (§3.2)."""
    return _key(KeyDomain.ACTIVATION, root_id, _ENTRY_SENTINEL)


def idempotency_key(
    root_id: str,
    predecessor_activation_id: str,
    outcome_taken: Outcome,
    target_node: str,
) -> str:
    """`hash(root_id, predecessor, outcome_taken, target_node)` (§3.2)."""
    return _key(
        KeyDomain.ACTIVATION,
        root_id,
        predecessor_activation_id,
        outcome_taken.value,
        target_node,
    )


def gate_key(
    root_id: str, gate_node: str, source_activation_id: str, outcome: Outcome
) -> str:
    """The opening transition's key — re-ticking re-finds, never re-mints (§3.4)."""
    return _key(KeyDomain.GATE, root_id, gate_node, source_activation_id, outcome.value)


def exhaustion_gate_key(root_id: str, region: str, round_no_at_exhaustion: int) -> str:
    """`hash(root_id, region, round_no_at_exhaustion)` (§3.4, §10.4)."""
    return _key(KeyDomain.EXHAUSTION_GATE, root_id, region, str(round_no_at_exhaustion))


def halt_gate_key(root_id: str, halt_ordinal: int) -> str:
    """`hash(root_id, halt_ordinal)` — one halt gate per breach (§10.3).

    The reason is deliberately NOT a key part: the halt gate is exempt from the
    §10.3 ceiling predicate, so a key that varies with a caller-supplied string
    makes the exemption unbounded — every distinct reason mints another exempt
    bead (probed, phase-2 r2).

    The ordinal is the count of the root's existing halt gates, and a new halt
    gate may only be minted when every prior one is CLOSED (`gates.open_gate`).
    A static per-root key made the gate one-shot instead: once the first halt
    closed, a later ceiling breach re-found the closed bead and the instance
    could never halt again (probed, phase-2 r3). The exemption stays bounded
    because each additional exempt bead costs one human-verified close.
    """
    return _key(KeyDomain.HALT_GATE, root_id, str(halt_ordinal))


def event_key(
    root_id: str,
    activation_id: str,
    from_node: str,
    outcome: Outcome,
    to_node: str,
) -> str:
    """The transition event's key, so backfill after a crash cannot duplicate (§3.3)."""
    return _key(
        KeyDomain.EVENT, root_id, activation_id, from_node, outcome.value, to_node
    )
