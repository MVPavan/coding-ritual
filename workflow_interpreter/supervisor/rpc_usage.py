"""Validate pinned token telemetry and derive deltas without double counting."""

from typing import Final

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from workflow_interpreter.contracts.rpc_usage import TokenCounts, UsageSnapshot

USAGE_FILE: Final[str] = "rpc-usage.json"


class VendorCounts(BaseModel):
    """Retain unknown bounded fields without treating them as additional spend."""

    model_config = ConfigDict(frozen=True, extra="allow", strict=True)
    inputTokens: int | None = Field(default=None, ge=0)
    cachedInputTokens: int | None = Field(default=None, ge=0)
    outputTokens: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def coherent(self) -> "VendorCounts":
        """Cached input is a subset, so contradictory counts are malformed telemetry."""
        if (
            self.inputTokens is not None
            and self.cachedInputTokens is not None
            and self.cachedInputTokens > self.inputTokens
        ):
            raise ValueError("cached input exceeds total input")
        return self

    def counts(self) -> TokenCounts:
        """Normalize names while preserving vendor extensions for inspection."""
        return TokenCounts(
            input=self.inputTokens,
            cached_input=self.cachedInputTokens,
            output=self.outputTokens,
            unknown=self.model_extra or {},
        )


class VendorUsage(BaseModel):
    """The last vendor report and the thread's cumulative total are different."""

    model_config = ConfigDict(frozen=True, extra="ignore", strict=True)
    total: VendorCounts
    last: VendorCounts


class UsageNotification(BaseModel):
    """Usage belongs to the registered thread and the current acknowledged turn."""

    model_config = ConfigDict(frozen=True, extra="ignore", strict=True)
    threadId: str
    turnId: str
    tokenUsage: VendorUsage


def _delta(current: int | None, previous: int | None) -> int | None:
    """Missing baselines and counter resets cannot prove activation expenditure."""
    if current is None or previous is None or current < previous:
        return None
    return current - previous


def updated_usage(
    payload: dict[str, JsonValue], baseline: TokenCounts, *, envelope_bytes: int
) -> UsageSnapshot:
    """Replace telemetry with this snapshot, subtracting the fixed turn baseline."""
    notification = UsageNotification.model_validate(payload)
    total = notification.tokenUsage.total.counts()
    return UsageSnapshot(
        per_turn=TokenCounts(
            input=_delta(total.input, baseline.input),
            cached_input=_delta(total.cached_input, baseline.cached_input),
            output=_delta(total.output, baseline.output),
        ),
        cumulative=total,
        last_reported=notification.tokenUsage.last.counts(),
        envelope_bytes=envelope_bytes,
    )
