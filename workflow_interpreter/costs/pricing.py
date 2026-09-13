"""Strict dated pricebooks and exact API-equivalent repricing."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from workflow_interpreter.costs.models import UsageObservation

PRICE_MODEL = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)
NonnegativeDecimal = Annotated[Decimal, Field(ge=Decimal(0), allow_inf_nan=False)]


class Rates(BaseModel):
    """Per-million-token rates for mutually exclusive billable categories."""

    model_config = PRICE_MODEL

    input: NonnegativeDecimal | None
    cache_read: NonnegativeDecimal | None
    cache_write_5m: NonnegativeDecimal | None
    cache_write_1h: NonnegativeDecimal | None
    output: NonnegativeDecimal | None

    @field_validator("*", mode="before")
    @classmethod
    def _decimal_strings_only(cls, value: object) -> object:
        """Refuse binary floats and non-finite or negative decimal strings."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("rates must be decimal strings or null")
        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("rate is not a decimal") from exc
        if not parsed.is_finite() or parsed < 0:
            raise ValueError("rate must be finite and nonnegative")
        return parsed


class ModelRate(BaseModel):
    """One exact provider/model/tier rate mapping with provenance."""

    model_config = PRICE_MODEL

    model: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    service_tier: str = Field(min_length=1)
    mapping_provenance: str = Field(min_length=1)
    per_million: Rates


class PriceSnapshot(BaseModel):
    """Rates retrieved together on one documented date."""

    model_config = PRICE_MODEL

    retrieved_at: date
    sources: tuple[str, ...] = Field(min_length=1)
    rates: tuple[ModelRate, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_rate_keys(self) -> PriceSnapshot:
        """Refuse aliases or duplicate rate rows that make lookup ambiguous."""
        keys = [(rate.provider, rate.model, rate.service_tier) for rate in self.rates]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate provider/model/service tier rate")
        return self


class PriceBook(BaseModel):
    """Versioned USD pricebook containing one or more dated snapshots."""

    model_config = PRICE_MODEL

    schema_version: Literal["task-cost-pricebook/1"] = Field(
        alias="schema", serialization_alias="schema"
    )
    currency: Literal["USD"]
    snapshots: tuple[PriceSnapshot, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_snapshot_dates(self) -> PriceBook:
        """Require a single unambiguous snapshot per retrieval date."""
        dates = [snapshot.retrieved_at for snapshot in self.snapshots]
        if len(dates) != len(set(dates)):
            raise ValueError("duplicate pricebook snapshot date")
        return self

    @classmethod
    def load(cls, path: Path) -> PriceBook:
        """Load and strictly validate a local JSON pricebook."""
        return cls.model_validate_json(path.read_bytes())

    def digest(self) -> str:
        """Return the stable hash of the validated pricebook representation."""
        raw = json.dumps(
            self.model_dump(mode="json", by_alias=True),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(raw).hexdigest()

    def snapshot(self, as_of: str | date | None = None) -> PriceSnapshot:
        """Select an exact date or the latest available snapshot."""
        if as_of is None:
            return max(self.snapshots, key=lambda item: item.retrieved_at)
        wanted = date.fromisoformat(as_of) if isinstance(as_of, str) else as_of
        matches = [item for item in self.snapshots if item.retrieved_at == wanted]
        if len(matches) != 1:
            raise ValueError(f"no price snapshot for {wanted.isoformat()}")
        return matches[0]


class PricedUsage(BaseModel):
    """One deduplicated observation's known price and missing rate categories."""

    model_config = PRICE_MODEL

    observation: UsageObservation
    known_cost_usd: Decimal
    missing_rates: tuple[str, ...]


class PricingResult(BaseModel):
    """Deterministic repricing result for a set of observations."""

    model_config = PRICE_MODEL

    observations: tuple[PricedUsage, ...]
    known_subtotal_usd: Decimal
    complete: bool
    missing_usage: tuple[str, ...]
    missing_rates: tuple[str, ...]
    snapshot_date: date
    pricebook_hash: str
    source_urls: tuple[str, ...]
    pricing_basis: str


def price_observations(
    observations: tuple[UsageObservation, ...],
    pricebook: PriceBook,
    *,
    as_of: str | date | None = None,
    normalize_standard: bool = False,
) -> PricingResult:
    """Deduplicate observations and price every known billable token category."""
    snapshot = pricebook.snapshot(as_of)
    deduplicated = _deduplicate(observations)
    priced: list[PricedUsage] = []
    all_missing_usage: set[str] = set()
    all_missing: set[str] = set()
    subtotal = Decimal(0)
    for observation in deduplicated:
        all_missing_usage.update(
            f"{observation.identity}:{category}"
            for category in _missing_token_categories(observation)
        )
        row = _find_rate(snapshot, observation, normalize_standard=normalize_standard)
        known = Decimal(0)
        missing: list[str] = []
        for category, count in observation.tokens.additive().items():
            if count is None:
                continue
            rate = (
                None
                if row is None or category == "cache_write"
                else getattr(row.per_million, category)
            )
            if count == 0:
                continue
            if rate is None:
                missing.append(category)
                continue
            known += Decimal(count) * rate / Decimal(1_000_000)
        identity_missing = [f"{observation.identity}:{name}" for name in missing]
        all_missing.update(identity_missing)
        subtotal += known
        priced.append(
            PricedUsage(
                observation=observation,
                known_cost_usd=known,
                missing_rates=tuple(sorted(missing)),
            )
        )
    return PricingResult(
        observations=tuple(priced),
        known_subtotal_usd=subtotal,
        complete=not all_missing_usage and not all_missing,
        missing_usage=tuple(sorted(all_missing_usage)),
        missing_rates=tuple(sorted(all_missing)),
        snapshot_date=snapshot.retrieved_at,
        pricebook_hash=pricebook.digest(),
        source_urls=snapshot.sources,
        pricing_basis=(
            "standard-rate-normalization" if normalize_standard else "observed-tier"
        ),
    )


def _missing_token_categories(observation: UsageObservation) -> tuple[str, ...]:
    """Name billable counters that telemetry left unreported rather than zero."""
    tokens = observation.tokens
    missing = [
        category
        for category in ("input", "cache_read", "output")
        if getattr(tokens, category) is None
    ]
    if tokens.cache_write is None:
        ttl_values = {
            "cache_write_5m": tokens.cache_write_5m,
            "cache_write_1h": tokens.cache_write_1h,
        }
        if all(value is None for value in ttl_values.values()):
            missing.append("cache_write")
        else:
            missing.extend(
                category for category, value in ttl_values.items() if value is None
            )
    return tuple(missing)


def _find_rate(
    snapshot: PriceSnapshot,
    observation: UsageObservation,
    *,
    normalize_standard: bool,
) -> ModelRate | None:
    """Return the one exact rate row for an observation, if available."""
    tier = (
        "standard"
        if observation.service_tier is None and normalize_standard
        else observation.service_tier
    )
    if tier is None:
        return None
    for row in snapshot.rates:
        if (
            row.provider == observation.provider
            and row.model == observation.model
            and row.service_tier == tier
        ):
            return row
    return None


def _deduplicate(
    observations: tuple[UsageObservation, ...],
) -> tuple[UsageObservation, ...]:
    """Dedupe identical stable identities and reject conflicting observations."""
    by_identity: dict[str, UsageObservation] = {}
    for observation in observations:
        existing = by_identity.get(observation.identity)
        if existing is not None and existing != observation:
            raise ValueError(f"conflicting usage identity {observation.identity!r}")
        by_identity[observation.identity] = observation
    return tuple(by_identity[key] for key in sorted(by_identity))
