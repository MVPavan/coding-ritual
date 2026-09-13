"""Deterministic task and explicit-cohort cost reports."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from statistics import median

from pydantic import BaseModel

from workflow_interpreter.costs.collection import (
    ActivationSummary,
    CompletionEvidence,
    RootSummary,
    TaskCollection,
)
from workflow_interpreter.costs.models import (
    COST_MODEL,
    Diagnostic,
    TokenTotals,
    TokenUsage,
)
from workflow_interpreter.costs.pricing import (
    PriceBook,
    PricedUsage,
    price_observations,
)


class TaskCostReport(BaseModel):
    """Stable, transcript-free report for one explicit task stage."""

    model_config = COST_MODEL

    task_id: str
    epic_id: str | None
    completion: CompletionEvidence
    coverage_complete: bool
    cost_basis: str
    whole_task_cost_usd: Decimal | None
    known_priced_subtotal_usd: Decimal
    missing_usage: tuple[str, ...]
    missing_rates: tuple[str, ...]
    uncovered_scope: tuple[str, ...]
    diagnostics: tuple[Diagnostic, ...]
    roots: tuple[RootSummary, ...]
    activations: tuple[ActivationSummary, ...]
    priced_usage: tuple[PricedUsage, ...]
    raw_tokens: TokenTotals
    role_model_subtotals: tuple[RoleModelSubtotal, ...]
    vendor_reported_costs: tuple[VendorReportedCost, ...]
    vendor_reported_cost_total_usd: Decimal | None
    measurable_durations: tuple[MeasuredDuration, ...]
    pricebook_date: str
    pricebook_hash: str
    price_sources: tuple[str, ...]
    pricing_basis: str
    price_snapshot_selection: str


class RoleModelSubtotal(BaseModel):
    """Token and known-price subtotal for one role/model pairing."""

    model_config = COST_MODEL

    role: str
    model: str
    tokens: TokenTotals
    known_priced_subtotal_usd: Decimal


class VendorReportedCost(BaseModel):
    """One vendor-reported cost retained separately from repricing."""

    model_config = COST_MODEL

    identity: str
    model: str
    amount_usd: Decimal
    source: str


class MeasuredDuration(BaseModel):
    """One activation duration computed only from two recorded timestamps."""

    model_config = COST_MODEL

    activation_id: str
    seconds: Decimal


class CohortReport(BaseModel):
    """Rollup for an explicitly supplied finite set of task reports."""

    model_config = COST_MODEL

    task_ids: tuple[str, ...]
    task_count: int
    completed_count: int
    completely_measured_completed_count: int
    completed_task_cost_denominator: int
    excluded_from_cost_statistics: int
    success_rate: Decimal | None
    mean_completed_task_cost_usd: Decimal | None
    median_completed_task_cost_usd: Decimal | None
    total_observed_spend_usd: Decimal
    observed_spend_partial: bool
    pricing_basis: str | None
    completed_cost_statistics_pricing_basis: str | None
    total_observed_spend_pricing_basis: str | None
    price_snapshot_selection: str | None
    pricebook_dates: tuple[str, ...]


def build_task_report(
    collection: TaskCollection,
    pricebook: PriceBook,
    *,
    as_of: str | None = None,
    normalize_standard: bool = False,
) -> TaskCostReport:
    """Price one collection and gate whole-task cost on every coverage condition."""
    pricing = price_observations(
        collection.observations,
        pricebook,
        as_of=as_of,
        normalize_standard=normalize_standard,
    )
    complete = collection.coverage_complete and pricing.complete
    vendor_costs = tuple(
        VendorReportedCost(
            identity=item.identity,
            model=item.model,
            amount_usd=item.vendor_cost_usd,
            source=item.source,
        )
        for item in collection.observations
        if item.vendor_cost_usd is not None
    )
    return TaskCostReport(
        task_id=collection.task_id,
        epic_id=collection.epic_id,
        completion=collection.completion,
        coverage_complete=complete,
        cost_basis="whole-task" if complete else "partial-observed-spend",
        whole_task_cost_usd=pricing.known_subtotal_usd if complete else None,
        known_priced_subtotal_usd=pricing.known_subtotal_usd,
        missing_usage=pricing.missing_usage,
        missing_rates=pricing.missing_rates,
        uncovered_scope=collection.uncovered_scope,
        diagnostics=collection.diagnostics,
        roots=collection.roots,
        activations=collection.activations,
        priced_usage=pricing.observations,
        raw_tokens=_sum_tokens(tuple(item.tokens for item in collection.observations)),
        role_model_subtotals=_role_model_subtotals(pricing.observations),
        vendor_reported_costs=vendor_costs,
        vendor_reported_cost_total_usd=(
            None
            if not vendor_costs
            else sum((item.amount_usd for item in vendor_costs), Decimal(0))
        ),
        measurable_durations=_durations(collection.activations),
        pricebook_date=pricing.snapshot_date.isoformat(),
        pricebook_hash=pricing.pricebook_hash,
        price_sources=pricing.source_urls,
        pricing_basis=pricing.pricing_basis,
        price_snapshot_selection=(
            "latest-available" if as_of is None else "explicit-as-of"
        ),
    )


def _role_model_subtotals(
    priced: tuple[PricedUsage, ...],
) -> tuple[RoleModelSubtotal, ...]:
    """Group observations by explicit role and price model identity."""
    grouped: dict[tuple[str, str], list[PricedUsage]] = defaultdict(list)
    for item in priced:
        grouped[
            (item.observation.role or "unattributed", item.observation.model)
        ].append(item)
    return tuple(
        RoleModelSubtotal(
            role=role,
            model=model,
            tokens=_sum_tokens(tuple(item.observation.tokens for item in items)),
            known_priced_subtotal_usd=sum(
                (item.known_cost_usd for item in items), Decimal(0)
            ),
        )
        for (role, model), items in sorted(grouped.items())
    )


def _sum_tokens(tokens: tuple[TokenUsage, ...]) -> TokenTotals:
    """Aggregate categories while retaining null when every source is unreported."""
    fields = (
        "input",
        "cache_read",
        "cache_write",
        "cache_write_5m",
        "cache_write_1h",
        "output",
        "reasoning",
    )
    values: dict[str, int | None] = {}
    for field in fields:
        reported = [
            value for token in tokens if (value := getattr(token, field)) is not None
        ]
        values[field] = None if not reported else sum(reported)
    return TokenTotals.model_validate(values)


def _durations(
    activations: tuple[ActivationSummary, ...],
) -> tuple[MeasuredDuration, ...]:
    """Compute nonnegative durations from activation timestamps when both exist."""
    result: list[MeasuredDuration] = []
    for activation in activations:
        if activation.started_at is None or activation.ended_at is None:
            continue
        try:
            started = datetime.fromisoformat(activation.started_at)
            ended = datetime.fromisoformat(activation.ended_at)
        except ValueError:
            continue
        seconds = Decimal(str((ended - started).total_seconds()))
        if seconds >= 0:
            result.append(
                MeasuredDuration(
                    activation_id=activation.activation_id, seconds=seconds
                )
            )
    return tuple(result)


def cohort_report(reports: tuple[TaskCostReport, ...]) -> CohortReport:
    """Roll up explicit tasks while unioning underlying usage identities."""
    ordered = tuple(sorted(reports, key=lambda item: item.task_id))
    completed = [report for report in ordered if report.completion.verified]
    comparable = [
        report
        for report in completed
        if report.coverage_complete and report.whole_task_cost_usd is not None
    ]
    costs = [report.whole_task_cost_usd for report in comparable]
    concrete_costs = [cost for cost in costs if cost is not None]
    unique_usage: dict[str, PricedUsage] = {}
    partial = False
    for report in ordered:
        partial = partial or not report.coverage_complete
        for item in report.priced_usage:
            prior = unique_usage.get(item.observation.identity)
            if prior is not None and prior != item:
                raise ValueError(
                    f"conflicting cohort usage identity {item.observation.identity!r}"
                )
            unique_usage[item.observation.identity] = item
    total = sum(
        (item.known_cost_usd for item in unique_usage.values()), start=Decimal(0)
    )
    denominator = len(concrete_costs)
    return CohortReport(
        task_ids=tuple(report.task_id for report in ordered),
        task_count=len(ordered),
        completed_count=len(completed),
        completely_measured_completed_count=denominator,
        completed_task_cost_denominator=denominator,
        excluded_from_cost_statistics=len(ordered) - denominator,
        success_rate=(
            None if not ordered else Decimal(len(completed)) / Decimal(len(ordered))
        ),
        mean_completed_task_cost_usd=(
            None
            if not concrete_costs
            else sum(concrete_costs, Decimal(0)) / denominator
        ),
        median_completed_task_cost_usd=(
            None if not concrete_costs else Decimal(median(concrete_costs))
        ),
        total_observed_spend_usd=total,
        observed_spend_partial=partial,
        pricing_basis=_combined_value([report.pricing_basis for report in ordered]),
        completed_cost_statistics_pricing_basis=_combined_value(
            [report.pricing_basis for report in comparable]
        ),
        total_observed_spend_pricing_basis=_combined_value(
            [report.pricing_basis for report in ordered if report.priced_usage]
        ),
        price_snapshot_selection=_combined_value(
            [report.price_snapshot_selection for report in ordered]
        ),
        pricebook_dates=tuple(sorted({report.pricebook_date for report in ordered})),
    )


def _combined_value(values: list[str]) -> str | None:
    """Return one cohort provenance value, or mark heterogeneous inputs mixed."""
    distinct = set(values)
    if not distinct:
        return None
    if len(distinct) == 1:
        return next(iter(distinct))
    return "mixed"


def text_report(report: TaskCostReport) -> str:
    """Render a concise human report without raw log content."""
    lines = [
        f"task: {report.task_id}",
        f"completion verified: {str(report.completion.verified).lower()}",
        f"coverage complete: {str(report.coverage_complete).lower()}",
        "cost interpretation: API-equivalent estimate; not actual billing",
        f"cost basis: {report.cost_basis}",
        f"pricing basis: {report.pricing_basis}",
        f"known priced subtotal USD: {report.known_priced_subtotal_usd}",
        f"whole task cost USD: {report.whole_task_cost_usd}",
        f"attempts: {len(report.roots)}; activations: {len(report.activations)}",
        f"pricebook: {report.pricebook_date} sha256:{report.pricebook_hash}",
        (
            f"price snapshot: {report.price_snapshot_selection} "
            f"({report.pricebook_date})"
        ),
    ]
    if report.missing_usage:
        lines.append(f"missing usage: {', '.join(report.missing_usage)}")
    if report.missing_rates:
        lines.append(f"missing rates: {', '.join(report.missing_rates)}")
    if report.uncovered_scope:
        lines.append(f"uncovered scope: {'; '.join(report.uncovered_scope)}")
    lines.extend(
        f"diagnostic: {item.code}: {item.detail}" for item in report.diagnostics
    )
    return "\n".join(lines) + "\n"


def cohort_text_report(report: CohortReport) -> str:
    """Render cohort statistics with their API repricing provenance."""
    dates = ", ".join(report.pricebook_dates) or "none"
    return (
        "\n".join(
            (
                f"tasks: {report.task_count}",
                f"completed: {report.completed_count}",
                "cost interpretation: API-equivalent estimate; not actual billing",
                f"pricing basis: {report.pricing_basis}",
                (
                    "completed cost statistics pricing basis: "
                    f"{report.completed_cost_statistics_pricing_basis}"
                ),
                (
                    "total observed spend pricing basis: "
                    f"{report.total_observed_spend_pricing_basis}"
                ),
                f"price snapshot: {report.price_snapshot_selection} ({dates})",
                (
                    "completely measured completed denominator: "
                    f"{report.completed_task_cost_denominator}"
                ),
                f"success rate: {report.success_rate}",
                f"mean completed task cost USD: {report.mean_completed_task_cost_usd}",
                (
                    "median completed task cost USD: "
                    f"{report.median_completed_task_cost_usd}"
                ),
                f"total observed spend USD: {report.total_observed_spend_usd}",
                (
                    "observed spend partial: "
                    f"{str(report.observed_spend_partial).lower()}"
                ),
            )
        )
        + "\n"
    )
