"""Accounting snapshots for one activation, distinct from vendor thread totals."""

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class TokenCounts(BaseModel):
    """Input includes cached input; None means unreported or underivable."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    input: int | None = Field(default=None, ge=0)
    cached_input: int | None = Field(default=None, ge=0)
    output: int | None = Field(default=None, ge=0)
    unknown: dict[str, JsonValue] = Field(default_factory=dict)


class UsageSnapshot(BaseModel):
    """Latest totals replace previous totals; activation usage is a baseline delta."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    per_turn: TokenCounts = TokenCounts()
    cumulative: TokenCounts = TokenCounts()
    last_reported: TokenCounts = TokenCounts()
    envelope_bytes: int = Field(default=0, ge=0)
