"""Conservative OpenCode adapter pending proven step-delta semantics."""

from __future__ import annotations

from collections.abc import Sequence

from workflow_interpreter.costs.models import Diagnostic, UsageObservation


def parse_events(
    events: Sequence[tuple[int, dict[str, object]]], context: object, source: str
) -> tuple[tuple[UsageObservation, ...], tuple[Diagnostic, ...]]:
    """Mark OpenCode telemetry unsupported instead of summing ambiguous steps."""
    del events, context
    return (), (
        Diagnostic(
            code="unsupported-profile-semantics",
            source=source,
            detail="OpenCode step usage boundaries are not proven for costing",
        ),
    )
