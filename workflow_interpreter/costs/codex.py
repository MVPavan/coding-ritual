"""Codex terminal-turn usage adapter."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import ValidationError

from workflow_interpreter.costs.models import (
    Diagnostic,
    Measurement,
    TokenUsage,
    UsageObservation,
)


def parse_events(
    events: Sequence[tuple[int, dict[str, object]]], context: object, source: str
) -> tuple[tuple[UsageObservation, ...], tuple[Diagnostic, ...]]:
    """Parse Codex `turn.completed` totals as per-terminal-turn deltas."""
    from workflow_interpreter.costs.profiles import LogContext

    if not isinstance(context, LogContext):
        raise TypeError("context must be LogContext")
    session: str | None = None
    observations: list[UsageObservation] = []
    diagnostics: list[Diagnostic] = []
    for line_number, event in events:
        if event.get("type") == "thread.started" and isinstance(
            event.get("thread_id"), str
        ):
            session = str(event["thread_id"])
            continue
        if event.get("type") != "turn.completed":
            continue
        line_source = f"{source}:{line_number}"
        usage = event.get("usage")
        event_id = event.get("turn_id")
        if not isinstance(usage, dict) or not isinstance(event_id, str):
            diagnostics.append(
                Diagnostic(
                    code="usage-event-invalid",
                    source=line_source,
                    detail="Codex terminal event lacks usage or stable turn identity",
                )
            )
            continue
        total_input = _strict_token(usage.get("input_tokens"))
        cached = _strict_token(usage.get("cached_input_tokens"))
        if total_input is None or cached is None or cached > total_input:
            diagnostics.append(
                Diagnostic(
                    code="usage-event-invalid",
                    source=line_source,
                    detail="Codex input counters are invalid or contradictory",
                )
            )
            continue
        try:
            observed_model = event.get("model")
            price_model = (
                str(observed_model)
                if isinstance(observed_model, str)
                else context.model
            )
            tokens = TokenUsage(
                input=total_input - cached,
                cache_read=cached,
                cache_write=usage.get("cache_write_input_tokens"),
                output=usage.get("output_tokens"),
                reasoning=usage.get("reasoning_output_tokens"),
            )
        except ValidationError:
            diagnostics.append(
                Diagnostic(
                    code="usage-event-invalid",
                    source=line_source,
                    detail="Codex usage contains an invalid token counter",
                )
            )
            continue
        observations.append(
            UsageObservation(
                identity=(
                    f"{context.root_id}/{context.activation_id}/{context.launch_id}/"
                    f"{event_id}/{price_model}"
                ),
                provider="openai",
                profile=context.profile,
                root_id=context.root_id,
                activation_id=context.activation_id,
                launch_id=context.launch_id,
                session_id=session,
                event_id=event_id,
                role=context.role,
                model=price_model,
                requested_model=context.requested_model,
                observed_model=(
                    str(observed_model) if isinstance(observed_model, str) else None
                ),
                model_mapping_provenance=(
                    "exact model from turn event"
                    if isinstance(observed_model, str)
                    else "requested model used; observed identity unavailable"
                ),
                effort=context.effort,
                service_tier=(
                    str(usage["service_tier"])
                    if isinstance(usage.get("service_tier"), str)
                    else None
                ),
                measurement=Measurement.STEP_DELTA,
                tokens=tokens,
                source=line_source,
                started_at=context.started_at,
                ended_at=context.ended_at,
            )
        )
    return tuple(observations), tuple(diagnostics)


def _strict_token(value: object) -> int | None:
    """Return a strict nonnegative integer token count, or None."""
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None
