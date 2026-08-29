"""Instance-branch advancement results."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class BranchAdvanceOutcome(StrEnum):
    """The four observable outcomes of an instance-ref advance."""

    ADVANCED = "advanced"
    UNCHANGED = "unchanged"
    DIVERGED = "diverged"
    MISSING = "missing"


class BranchAdvance(BaseModel):
    """The ref value observed before attempting the branch advance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    outcome: BranchAdvanceOutcome
    target: str
    previous: str | None = None
