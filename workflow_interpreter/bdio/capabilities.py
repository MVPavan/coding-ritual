"""Capabilities the wrapper must own rather than accept as caller assertions.

Two facts the §3/§9 rules require are not recorded in bd and cannot be derived
from it: the current bytes of a `binds = "mutable"` gate artifact, and the
instance branch head used as the `intended_base_commit` floor. A caller-echoed
value for either is not a check — it is the constrained party stating its own
compliance (§9 ruling, phase-2 review).

So they arrive as injected, workspace-scoped capabilities: the caller supplies
the mechanism once at construction, and the wrapper — not the caller — decides
when to call it and what the answer means. A missing capability fails closed:
the operation that needs it refuses rather than trusting an input.
"""

from __future__ import annotations

from typing import Protocol


class ArtifactReader(Protocol):
    """Reads a gate artifact's current bytes, workspace-scoped (§9 re-hash).

    Raises any exception when the artifact is missing or unreadable; the gate
    path turns that into a `StaleApprovalError` with an edit receipt.
    """

    def __call__(self, artifact_ref: str) -> bytes: ...  # pragma: no cover


class BranchHeadReader(Protocol):
    """The instance branch head — §3.2's `intended_base_commit` floor.

    Consulted only when no recorded WRITING activation at the target node
    carries a `pre_attempt_commit` (the rework case derives from bd instead).
    """

    def __call__(self) -> str: ...  # pragma: no cover
