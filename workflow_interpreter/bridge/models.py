"""Typed durable records for one phase-bridge stage admission."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from workflow_interpreter.bridge.verification import VerificationPolicy

type PhaseBridgeSchema = Literal["phase-bridge/3"]
PHASE_BRIDGE_SCHEMA: Final[PhaseBridgeSchema] = "phase-bridge/3"
INSTANCE_KEY_TEMPLATE: Final[str] = (
    "phase-bridge:{epic_id}:{stage_id}:attempt:{attempt}"
)
MSG_INSTANCE_KEY: Final[str] = "phase bridge instance_key is not derived from identity"
MSG_PREVIOUS_ATTEMPTS_COUNT: Final[str] = (
    "phase bridge previous_attempts does not match attempt count"
)
MSG_PREVIOUS_ATTEMPTS_UNIQUE: Final[str] = (
    "phase bridge previous_attempts must contain unique identities"
)
MSG_PREPARED_NOT_FIRST_ATTEMPT: Final[str] = (
    "phase bridge prepared records must be the first attempt"
)

CommitOid = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
NonEmptyText = Annotated[str, StringConstraints(min_length=1)]


class PhaseBridgeState(StrEnum):
    """The complete phase-bridge lifecycle vocabulary."""

    PREPARED = "prepared"
    ADMITTED = "admitted"
    # Read compatibility for the existing phase-bridge/3 wire vocabulary.
    # No producer writes this state; removing it requires an explicit migration.
    LANDING = "landing"
    LANDED = "landed"
    GATE_RED = "gate-red"
    CLOSED = "closed"


class PhaseBridgeRecord(BaseModel):
    """Persist one stage's bridge identity without duplicating root facts."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: PhaseBridgeSchema = Field(
        alias="schema",
        serialization_alias="schema",
        frozen=True,
    )
    state: PhaseBridgeState
    epic_id: NonEmptyText
    stage_id: NonEmptyText
    attempt: int = Field(ge=1)
    instance_key: NonEmptyText
    target_ref: NonEmptyText
    expected_base_commit: CommitOid
    verification_policy: VerificationPolicy | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    integration_digest: str | None = Field(default=None, exclude_if=lambda v: v is None)
    integration_owner: str | None = Field(default=None, exclude_if=lambda v: v is None)
    integration_slot: str | None = Field(default=None, exclude_if=lambda v: v is None)
    integration_generation: int | None = Field(
        default=None, exclude_if=lambda v: v is None
    )
    successor_owner: str | None = Field(default=None, exclude_if=lambda v: v is None)
    successor_key: str | None = Field(default=None, exclude_if=lambda v: v is None)
    execution_base_commit: CommitOid | None = Field(
        default=None, exclude_if=lambda v: v is None
    )
    root_id: NonEmptyText | None = None
    landed_oid: CommitOid | None = None
    tree: CommitOid | None = None
    gate_receipt_digest: NonEmptyText | None = None
    landing_receipt_digest: NonEmptyText | None = None
    previous_attempts: tuple[NonEmptyText, ...]

    @model_validator(mode="after")
    def _assert_attempt_identity(self) -> PhaseBridgeRecord:
        """Require one derived current key and one unique key for each prior attempt."""
        expected_key = INSTANCE_KEY_TEMPLATE.format(
            epic_id=self.epic_id, stage_id=self.stage_id, attempt=self.attempt
        )
        if self.instance_key != expected_key:
            raise ValueError(MSG_INSTANCE_KEY)
        if len(self.previous_attempts) != self.attempt - 1:
            raise ValueError(MSG_PREVIOUS_ATTEMPTS_COUNT)
        if len(set(self.previous_attempts)) != len(self.previous_attempts):
            raise ValueError(MSG_PREVIOUS_ATTEMPTS_UNIQUE)
        return self

    @classmethod
    def prepared(
        cls,
        *,
        epic_id: str,
        stage_id: str,
        attempt: int,
        target_ref: str,
        expected_base_commit: str,
        verification_policy: VerificationPolicy | None = None,
    ) -> PhaseBridgeRecord:
        """Build a new pre-claim admission intent."""
        if attempt != 1:
            raise ValueError(MSG_PREPARED_NOT_FIRST_ATTEMPT)
        return cls(
            schema=PHASE_BRIDGE_SCHEMA,
            state=PhaseBridgeState.PREPARED,
            epic_id=epic_id,
            stage_id=stage_id,
            attempt=attempt,
            instance_key=INSTANCE_KEY_TEMPLATE.format(
                epic_id=epic_id, stage_id=stage_id, attempt=attempt
            ),
            target_ref=target_ref,
            expected_base_commit=expected_base_commit,
            previous_attempts=(),
            verification_policy=verification_policy,
        )

    def next_attempt(self) -> PhaseBridgeRecord:
        """Mint the next distinct root identity after an eligible retry."""
        return PhaseBridgeRecord(
            schema=PHASE_BRIDGE_SCHEMA,
            state=PhaseBridgeState.PREPARED,
            epic_id=self.epic_id,
            stage_id=self.stage_id,
            attempt=self.attempt + 1,
            instance_key=INSTANCE_KEY_TEMPLATE.format(
                epic_id=self.epic_id, stage_id=self.stage_id, attempt=self.attempt + 1
            ),
            target_ref=self.target_ref,
            expected_base_commit=self.expected_base_commit,
            previous_attempts=(*self.previous_attempts, self.instance_key),
            verification_policy=self.verification_policy,
        )

    def admitted(self, root_id: str) -> PhaseBridgeRecord:
        """Attach the converged root to an admitted stage record."""
        return self.model_copy(
            update={"state": PhaseBridgeState.ADMITTED, "root_id": root_id}
        )

    def landed(
        self,
        artifact_oid: str,
        tree: str,
        gate_receipt_digest: str,
        receipt_digest: str,
    ) -> PhaseBridgeRecord:
        """Record the signed artifact that won the one landing CAS."""
        return self.model_copy(
            update={
                "state": PhaseBridgeState.LANDED,
                "landed_oid": artifact_oid,
                "tree": tree,
                "gate_receipt_digest": gate_receipt_digest,
                "landing_receipt_digest": receipt_digest,
            }
        )

    def closed(self) -> PhaseBridgeRecord:
        """Mark a relation closed immediately before its verified bead close."""
        return self.model_copy(update={"state": PhaseBridgeState.CLOSED})
