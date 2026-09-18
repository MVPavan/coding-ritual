"""Fail-closed audit checks over the durable workflow trace."""

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio.records import InstanceRecord, RootRecord
from workflow_interpreter.foreman.frontier import (
    FrontierConflict,
    FrontierViolation,
    build_frontier,
)


class AuditResult(BaseModel):
    """The result of a read-only audit sweep."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    violation: str | None = None


def audit(root: RootRecord, rows: Iterable[InstanceRecord]) -> AuditResult:
    """Validate routing-critical carrier facts without writing any row."""
    try:
        build_frontier(root, rows)
    except (FrontierConflict, FrontierViolation) as exc:
        return AuditResult(violation=str(exc))
    return AuditResult()
