"""Claude terminal-result and auxiliary-model usage adapter."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

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
    """Prefer Claude `modelUsage` rows and never add top-level totals twice."""
    from workflow_interpreter.costs.profiles import LogContext

    if not isinstance(context, LogContext):
        raise TypeError("context must be LogContext")
    terminal_events: dict[str, tuple[int, dict[str, object]]] = {}
    for line_number, event in events:
        if event.get("type") != "result":
            continue
        event_id = event.get("uuid")
        if not isinstance(event_id, str):
            continue
        prior = terminal_events.get(event_id)
        if prior is not None and prior[1] != event:
            return (), (
                Diagnostic(
                    code="usage-identity-conflict",
                    source=f"{source}:{line_number}",
                    detail="Claude result identity carries conflicting terminal events",
                ),
            )
        terminal_events[event_id] = (line_number, event)
    if len(terminal_events) > 1:
        return (), (
            Diagnostic(
                code="cumulative-boundary-ambiguous",
                source=source,
                detail="multiple Claude cumulative results lack proven exec boundaries",
            ),
        )
    observations: list[UsageObservation] = []
    diagnostics: list[Diagnostic] = []
    for line_number, event in terminal_events.values():
        if event.get("type") != "result":
            continue
        line_source = f"{source}:{line_number}"
        event_id = event.get("uuid")
        session = event.get("session_id")
        if not isinstance(event_id, str) or not isinstance(session, str):
            diagnostics.append(_invalid(line_source, "stable result/session identity"))
            continue
        model_usage = event.get("modelUsage")
        if isinstance(model_usage, dict) and model_usage:
            for model, raw_usage in sorted(model_usage.items()):
                model_id = str(model)
                observation = _observation(
                    raw_usage,
                    model=model_id,
                    event_id=event_id,
                    session=session,
                    line_source=line_source,
                    context=context,
                    camel_case=True,
                    service_tier=(
                        _service_tier(event) if model_id == context.model else None
                    ),
                )
                if observation is None:
                    diagnostics.append(
                        _invalid(line_source, "valid modelUsage counters")
                    )
                else:
                    observations.append(observation)
            continue
        observation = _observation(
            event.get("usage"),
            model=context.model,
            event_id=event_id,
            session=session,
            line_source=line_source,
            context=context,
            camel_case=False,
            vendor_cost=event.get("total_cost_usd"),
            service_tier=_service_tier(event),
        )
        if observation is None:
            diagnostics.append(_invalid(line_source, "valid terminal usage counters"))
        else:
            observations.append(observation)
    return tuple(observations), tuple(diagnostics)


def _observation(
    raw: object,
    *,
    model: str,
    event_id: str,
    session: str,
    line_source: str,
    context: object,
    camel_case: bool,
    vendor_cost: object = None,
    service_tier: str | None = None,
) -> UsageObservation | None:
    """Build one Claude model observation, returning None on invalid input."""
    from workflow_interpreter.costs.profiles import LogContext

    if not isinstance(context, LogContext) or not isinstance(raw, dict):
        return None
    keys = (
        (
            "inputTokens",
            "cacheReadInputTokens",
            "cacheCreationInputTokens",
            "outputTokens",
            "thinkingTokens",
            "costUSD",
        )
        if camel_case
        else (
            "input_tokens",
            "cache_read_input_tokens",
            "cache_creation_input_tokens",
            "output_tokens",
            "thinking_tokens",
            "cost_usd",
        )
    )
    cost = raw.get(keys[5], vendor_cost)
    cache_write = raw.get(keys[2])
    cache_write_5m = None
    cache_write_1h = None
    if not camel_case and isinstance(raw.get("cache_creation"), dict):
        cache_creation = raw["cache_creation"]
        cache_write_5m = cache_creation.get("ephemeral_5m_input_tokens")
        cache_write_1h = cache_creation.get("ephemeral_1h_input_tokens")
        if (
            isinstance(cache_write, int)
            and not isinstance(cache_write, bool)
            and isinstance(cache_write_5m, int)
            and not isinstance(cache_write_5m, bool)
            and isinstance(cache_write_1h, int)
            and not isinstance(cache_write_1h, bool)
            and cache_write_5m + cache_write_1h == cache_write
        ):
            cache_write = None
        else:
            cache_write_5m = None
            cache_write_1h = None
    try:
        return UsageObservation(
            identity=(
                f"{context.root_id}/{context.activation_id}/{context.launch_id}/"
                f"{event_id}/{model}"
            ),
            provider="anthropic",
            profile=context.profile,
            root_id=context.root_id,
            activation_id=context.activation_id,
            launch_id=context.launch_id,
            session_id=session,
            event_id=event_id,
            role=context.role,
            model=model,
            requested_model=context.requested_model,
            observed_model=(
                str(raw["canonicalModel"])
                if camel_case and isinstance(raw.get("canonicalModel"), str)
                else None
            ),
            model_mapping_provenance=(
                "price identity is the raw modelUsage key; canonicalModel is telemetry only"
                if camel_case
                else "terminal result uses the requested model; observed identity unavailable"
            ),
            effort=context.effort,
            service_tier=service_tier,
            measurement=Measurement.TERMINAL_CUMULATIVE,
            tokens=TokenUsage(
                input=raw.get(keys[0]),
                cache_read=raw.get(keys[1]),
                cache_write=cache_write,
                cache_write_5m=cache_write_5m,
                cache_write_1h=cache_write_1h,
                output=raw.get(keys[3]),
                reasoning=raw.get(keys[4]),
            ),
            source=line_source,
            vendor_cost_usd=None if cost is None else Decimal(str(cost)),
            started_at=context.started_at,
            ended_at=context.ended_at,
        )
    except (ValidationError, ArithmeticError):
        return None


def _invalid(source: str, missing: str) -> Diagnostic:
    """Return a transcript-free Claude validation diagnostic."""
    return Diagnostic(
        code="usage-event-invalid",
        source=source,
        detail=f"Claude terminal event lacks {missing}",
    )


def _service_tier(event: dict[str, object]) -> str | None:
    """Return Claude's observed service tier from the terminal usage object."""
    usage = event.get("usage")
    if isinstance(usage, dict) and isinstance(usage.get("service_tier"), str):
        return str(usage["service_tier"])
    return None
