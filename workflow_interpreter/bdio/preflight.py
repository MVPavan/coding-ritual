"""Read-only launch preflights shared with the foreman."""

from __future__ import annotations

from typing import Protocol

from workflow_interpreter.bdio.records import ActivationRecord
from workflow_interpreter.bdio.wire import MintReason, MintRequest


class WorkflowReads(Protocol):
    """The activation lookup preflight requires."""

    def load_activation(self, activation_id: str) -> ActivationRecord:
        """Load one activation by its durable identifier."""


def steer_ancestor(
    reads: WorkflowReads,
    request: MintRequest,
) -> str | None:
    """Return the §8.1 continuation an infra retry WOULD descend from, if any.

    The mint-time question, asked of a request that has no activation yet.
    """
    return _walk(reads, request.mint_reason, request.predecessor_activation_id)


def steer_ancestor_of(
    reads: WorkflowReads,
    activation: ActivationRecord,
) -> str | None:
    """Return the §8.1 continuation a MINTED infra retry descends from, if any.

    The dispatch-time question. Separate from `steer_ancestor` because the
    caller holds the activation itself: fabricating a `MintRequest` around it
    just to reuse one walker put empty required fields on the happy path of
    every launch (cr-o85.19 review).
    """
    metadata = activation.metadata
    return _walk(reads, metadata.mint_reason, metadata.predecessor_activation_id)


def _walk(
    reads: WorkflowReads, mint_reason: MintReason, predecessor: str | None
) -> str | None:
    """Walk a retry's whole ancestry to the continuation behind it.

    The WHOLE ancestry, never one hop: a retry may itself fail in transport, so
    the continuation can sit several `infra-retry` links back (cr-o85.19).
    """
    if mint_reason is not MintReason.INFRA_RETRY or predecessor is None:
        return None
    current = reads.load_activation(predecessor)
    seen = {predecessor}
    while current.metadata.mint_reason is MintReason.INFRA_RETRY:
        predecessor = current.metadata.predecessor_activation_id
        if predecessor is None or predecessor in seen:
            return None
        seen.add(predecessor)
        current = reads.load_activation(predecessor)
    if current.metadata.mint_reason is MintReason.STEER_CONTINUATION:
        return current.activation_id
    return None
