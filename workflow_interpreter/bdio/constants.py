"""Shared bdio constants that must not create a wire-to-mint import cycle."""

from __future__ import annotations

from typing import Final

DEVIATION_UNDECLARED_EFFECTS_ACCEPTED: Final[str] = "undeclared_effects_accepted"
DEVIATION_UNDECLARED_EFFECTS_DISCARDED: Final[str] = "undeclared_effects_discarded"
DEVIATION_INSTANCE_BRANCH_DIVERGED: Final[str] = "instance_branch_diverged"
DEVIATION_PRECONDITION_REFUSED: Final[str] = "precondition_refused"
_MSG_ENTRY_PREDECESSOR: Final[str] = (
    "an entry mint has no predecessor; {predecessor!r} was supplied (§3.2)"
)
_MSG_BOTH_PREDECESSORS: Final[str] = (
    "a successor mint cannot name both an activation and a gate predecessor"
)
