"""Strict explicit attribution for usage outside durable workflow activations."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from workflow_interpreter.costs.collection import TaskCollection
from workflow_interpreter.costs.models import (
    COST_MODEL,
    Measurement,
    TokenUsage,
    UsageObservation,
)


class SupplementRecord(BaseModel):
    """One explicitly owned external usage record with stable identity."""

    model_config = COST_MODEL

    record_id: str = Field(min_length=1)
    usage_identity: str = Field(min_length=1)
    owner_task_id: str = Field(min_length=1)
    parent_task_id: str | None = None
    source_reference: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    profile: str = Field(min_length=1)
    model: str = Field(min_length=1)
    service_tier: str = Field(min_length=1)
    measurement: Measurement
    role: str = Field(min_length=1)
    effort: str | None = None
    tokens: TokenUsage

    @model_validator(mode="after")
    def _delta_has_stable_identity(self) -> SupplementRecord:
        """Require explicit ownership and a nonempty measurable token record."""
        if all(value is None for value in self.tokens.additive().values()):
            raise ValueError(
                "supplement record must report at least one token category"
            )
        return self

    def observation(self) -> UsageObservation:
        """Convert explicit attribution into the common observation model."""
        common = {
            "identity": self.usage_identity,
            "provider": self.provider,
            "profile": self.profile,
            "root_id": f"supplement:{self.owner_task_id}",
            "activation_id": self.record_id,
            "role": self.role,
            "model": self.model,
            "effort": self.effort,
            "service_tier": self.service_tier,
            "measurement": self.measurement,
            "tokens": self.tokens,
            "source": self.source_reference,
        }
        if self.measurement is Measurement.STEP_DELTA:
            common["event_id"] = self.usage_identity
        else:
            common["exec_id"] = self.usage_identity
            common["session_id"] = self.usage_identity
        return UsageObservation.model_validate(
            common
            | {
                "model_mapping_provenance": (
                    "explicit supplement model identity and source reference"
                )
            }
        )


class ScopeDeclaration(BaseModel):
    """Explicit evidence that external attribution categories are exhaustive."""

    model_config = COST_MODEL

    task_id: str = Field(min_length=1)
    source_reference: str = Field(min_length=1)
    coordinator_complete: bool
    children_complete: bool


class UsageSupplement(BaseModel):
    """Versioned local usage attribution with strict, closed schemas."""

    model_config = COST_MODEL

    schema_version: Literal["task-cost-supplement/1"] = Field(
        alias="schema", serialization_alias="schema"
    )
    records: tuple[SupplementRecord, ...]
    scope_declarations: tuple[ScopeDeclaration, ...]

    @model_validator(mode="after")
    def _identities_are_unique(self) -> UsageSupplement:
        """Refuse conflicting record, usage, or scope identities globally."""
        task_ids = [item.task_id for item in self.scope_declarations]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("duplicate supplement scope declaration")
        by_record_id: dict[str, SupplementRecord] = {}
        by_usage_identity: dict[str, SupplementRecord] = {}
        for record in self.records:
            prior_record = by_record_id.get(record.record_id)
            if prior_record is not None and prior_record != record:
                raise ValueError(
                    f"conflicting supplement record_id {record.record_id!r}"
                )
            prior_usage = by_usage_identity.get(record.usage_identity)
            if prior_usage is not None and prior_usage != record:
                raise ValueError(
                    f"conflicting supplement usage identity {record.usage_identity!r}"
                )
            by_record_id[record.record_id] = record
            by_usage_identity[record.usage_identity] = record
        return self

    @classmethod
    def load(cls, path: Path) -> UsageSupplement:
        """Load a strict local supplement without network access."""
        return cls.model_validate_json(path.read_bytes())

    def records_for(self, task_id: str) -> tuple[SupplementRecord, ...]:
        """Dedupe exact record IDs and reject conflicting duplicate identities."""
        selected: dict[str, SupplementRecord] = {}
        usage_identities: dict[str, SupplementRecord] = {}
        for record in self.records:
            if record.owner_task_id != task_id and record.parent_task_id != task_id:
                continue
            prior = selected.get(record.record_id)
            if prior is not None and prior != record:
                raise ValueError(
                    f"conflicting supplement record_id {record.record_id!r}"
                )
            usage_prior = usage_identities.get(record.usage_identity)
            if usage_prior is not None and usage_prior != record:
                raise ValueError(
                    f"conflicting supplement usage identity {record.usage_identity!r}"
                )
            selected[record.record_id] = record
            usage_identities[record.usage_identity] = record
        return tuple(selected[key] for key in sorted(selected))

    def scope_for(self, task_id: str) -> ScopeDeclaration | None:
        """Return the task's unique explicit coverage declaration, if present."""
        return next(
            (item for item in self.scope_declarations if item.task_id == task_id),
            None,
        )


def apply_supplement(
    collection: TaskCollection, supplement: UsageSupplement
) -> TaskCollection:
    """Add explicitly owned usage and update external-scope coverage."""
    records = supplement.records_for(collection.task_id)
    observations = [*collection.observations]
    by_identity = {item.identity: item for item in observations}
    for record in records:
        observation = record.observation()
        prior = by_identity.get(observation.identity)
        if prior is not None and prior != observation:
            raise ValueError(
                f"conflicting usage identity {observation.identity!r} across sources"
            )
        by_identity[observation.identity] = observation
    declaration = supplement.scope_for(collection.task_id)
    external_complete = bool(
        declaration is not None
        and declaration.coordinator_complete
        and declaration.children_complete
    )
    uncovered = (
        ()
        if external_complete
        else (
            "coordinator, planning, and child usage needs explicit supplement attribution",
        )
    )
    return collection.model_copy(
        update={
            "observations": tuple(by_identity[key] for key in sorted(by_identity)),
            "uncovered_scope": uncovered,
            "coverage_complete": (
                collection.completion.verified
                and collection.usage_complete
                and external_complete
            ),
        }
    )
