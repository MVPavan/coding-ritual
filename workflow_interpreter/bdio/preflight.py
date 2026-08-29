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
    """Return a continuation ancestor before an infra retry is minted."""
    if request.mint_reason is not MintReason.INFRA_RETRY:
        return None
    predecessor = request.predecessor_activation_id
    if predecessor is None:
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
