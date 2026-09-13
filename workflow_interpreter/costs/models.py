"""Strict value objects shared by task-cost collection and reporting."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

COST_MODEL = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)
TokenCount = Annotated[StrictInt, Field(ge=0)]


class Measurement(StrEnum):
    """How an observation's counters relate to other observations."""

    TERMINAL_CUMULATIVE = "terminal-cumulative"
    STEP_DELTA = "step-delta"


class TokenUsage(BaseModel):
    """Nullable token categories where zero remains a measured value."""

    model_config = COST_MODEL

    input: TokenCount | None = None
    cache_read: TokenCount | None = None
    cache_write: TokenCount | None = None
    cache_write_5m: TokenCount | None = None
    cache_write_1h: TokenCount | None = None
    output: TokenCount | None = None
    reasoning: TokenCount | None = None

    @model_validator(mode="after")
    def _cache_write_representation_is_exclusive(self) -> TokenUsage:
        """Refuse totals that could overlap with explicit TTL buckets."""
        if self.cache_write is not None and (
            self.cache_write_5m is not None or self.cache_write_1h is not None
        ):
            raise ValueError(
                "generic cache write and cache write TTL buckets are mutually exclusive"
            )
        return self

    def additive(self) -> dict[str, int | None]:
        """Return mutually exclusive billable categories only."""
        return {
            "input": self.input,
            "cache_read": self.cache_read,
            "cache_write": self.cache_write,
            "cache_write_5m": self.cache_write_5m,
            "cache_write_1h": self.cache_write_1h,
            "output": self.output,
        }


class TokenTotals(BaseModel):
    """Cross-observation totals that may contain both cache-write representations."""

    model_config = COST_MODEL

    input: TokenCount | None = None
    cache_read: TokenCount | None = None
    cache_write: TokenCount | None = None
    cache_write_5m: TokenCount | None = None
    cache_write_1h: TokenCount | None = None
    output: TokenCount | None = None
    reasoning: TokenCount | None = None


class UsageObservation(BaseModel):
    """One provenance-bound usage measurement from baseline or raw telemetry."""

    model_config = COST_MODEL

    identity: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    profile: str = Field(min_length=1)
    root_id: str = Field(min_length=1)
    activation_id: str = Field(min_length=1)
    launch_id: str | None = None
    session_id: str | None = None
    event_id: str | None = None
    exec_id: str | None = None
    role: str | None = None
    model: str = Field(min_length=1)
    requested_model: str | None = None
    observed_model: str | None = None
    model_mapping_provenance: str | None = None
    effort: str | None = None
    service_tier: str | None = None
    measurement: Measurement
    tokens: TokenUsage
    source: str = Field(min_length=1)
    vendor_cost_usd: Decimal | None = None
    started_at: str | None = None
    ended_at: str | None = None

    @model_validator(mode="after")
    def _identity_is_proven(self) -> UsageObservation:
        """Require the identity dimensions needed by the measurement kind."""
        if self.measurement is Measurement.TERMINAL_CUMULATIVE:
            if (
                self.launch_id is None and self.exec_id is None
            ) or self.session_id is None:
                raise ValueError(
                    "terminal cumulative usage needs execution and session"
                )
        elif self.event_id is None and self.exec_id is None:
            raise ValueError("step delta usage needs event_id or exec_id")
        if all(value is None for value in self.tokens.additive().values()):
            raise ValueError(
                "usage observation needs a reported billable token category"
            )
        if self.vendor_cost_usd is not None and (
            not self.vendor_cost_usd.is_finite() or self.vendor_cost_usd < 0
        ):
            raise ValueError("vendor cost must be finite and nonnegative")
        return self


class Diagnostic(BaseModel):
    """A safe diagnostic that never carries raw transcript content."""

    model_config = COST_MODEL

    code: str = Field(min_length=1)
    source: str = Field(min_length=1)
    detail: str = Field(min_length=1)
