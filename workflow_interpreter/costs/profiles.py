"""Bounded raw-log routing for supported crew profiles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field

from workflow_interpreter.costs import claude, codex, opencode
from workflow_interpreter.costs.models import COST_MODEL, Diagnostic, UsageObservation

DEFAULT_MAX_LOG_BYTES = 32 * 1024 * 1024
DEFAULT_MAX_LOG_EVENTS = 100_000
PositiveInt = Annotated[int, Field(gt=0)]


class LogContext(BaseModel):
    """Trusted activation identity supplied to a profile-specific parser."""

    model_config = COST_MODEL

    profile: str = Field(min_length=1)
    root_id: str = Field(min_length=1)
    activation_id: str = Field(min_length=1)
    launch_id: str = Field(min_length=1)
    requested_model: str = Field(min_length=1)
    model: str = Field(min_length=1)
    role: str | None = None
    effort: str | None = None
    started_at: str | None = None
    ended_at: str | None = None


class LogParseResult(BaseModel):
    """Safe observations and structural diagnostics from one bounded log."""

    model_config = COST_MODEL

    observations: tuple[UsageObservation, ...]
    diagnostics: tuple[Diagnostic, ...]
    complete: bool


def parse_log(
    path: Path,
    context: LogContext,
    *,
    max_bytes: PositiveInt = DEFAULT_MAX_LOG_BYTES,
    max_events: PositiveInt = DEFAULT_MAX_LOG_EVENTS,
) -> LogParseResult:
    """Stream a crew JSONL file within finite byte and event ceilings."""
    source = _safe_source(path)
    try:
        size = path.stat().st_size
    except OSError:
        return _failure("log-unavailable", source, "crew log is unavailable")
    if size > max_bytes:
        return _failure("log-too-large", source, "crew log exceeds byte limit")

    events: list[tuple[int, dict[str, object]]] = []
    diagnostics: list[Diagnostic] = []
    consumed = 0
    try:
        with path.open("rb") as handle:
            for line_number, line in enumerate(handle, start=1):
                consumed += len(line)
                line_source = f"{source}:{line_number}"
                if consumed > max_bytes:
                    diagnostics.append(
                        Diagnostic(
                            code="log-too-large",
                            source=line_source,
                            detail="crew log exceeds byte limit",
                        )
                    )
                    break
                if not line.strip():
                    continue
                if len(events) >= max_events:
                    diagnostics.append(
                        Diagnostic(
                            code="too-many-events",
                            source=line_source,
                            detail="crew log exceeds event limit",
                        )
                    )
                    break
                try:
                    value = json.loads(line)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    diagnostics.append(
                        Diagnostic(
                            code="malformed-json",
                            source=line_source,
                            detail="crew log line is not a complete JSON object",
                        )
                    )
                    continue
                if not isinstance(value, dict):
                    diagnostics.append(
                        Diagnostic(
                            code="malformed-event",
                            source=line_source,
                            detail="crew log event is not an object",
                        )
                    )
                    continue
                events.append((line_number, value))
    except OSError:
        return _failure("log-unavailable", source, "crew log could not be read")

    adapter = {
        "claude": claude.parse_events,
        "codex": codex.parse_events,
        "opencode": opencode.parse_events,
    }.get(context.profile)
    if adapter is None:
        diagnostics.append(
            Diagnostic(
                code="unsupported-profile",
                source=source,
                detail=f"profile {context.profile!r} has no usage adapter",
            )
        )
        return LogParseResult(
            observations=(), diagnostics=tuple(diagnostics), complete=False
        )
    observations, adapter_diagnostics = adapter(events, context, source)
    diagnostics.extend(adapter_diagnostics)
    return LogParseResult(
        observations=observations,
        diagnostics=tuple(diagnostics),
        complete=bool(observations) and not diagnostics,
    )


def _failure(code: str, source: str, detail: str) -> LogParseResult:
    """Build one safe, incomplete parser result."""
    return LogParseResult(
        observations=(),
        diagnostics=(Diagnostic(code=code, source=source, detail=detail),),
        complete=False,
    )


def _safe_source(path: Path) -> str:
    """Identify only the file name so diagnostics cannot disclose host paths."""
    return path.name or "run.jsonl"
