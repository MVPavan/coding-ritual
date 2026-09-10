"""Typed durable records for one phase-bridge stage admission."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Final

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

PHASE_BRIDGE_SCHEMA: Final[str] = "phase-bridge/3"
INSTANCE_KEY_TEMPLATE: Final[str] = (
    "phase-bridge:{epic_id}:{stage_id}:attempt:{attempt}"
)

CommitOid = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
NonEmptyText = Annotated[str, StringConstraints(min_length=1)]


class PhaseBridgeState(StrEnum):
    """The complete phase-bridge lifecycle vocabulary."""

    PREPARED = "prepared"
    ADMITTED = "admitted"
    LANDING = "landing"
    LANDED = "landed"
    GATE_RED = "gate-red"
    CLOSED = "closed"


class PhaseBridgeRecord(BaseModel):
    """Persist one stage's bridge identity without duplicating root facts."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = Field(
        default=PHASE_BRIDGE_SCHEMA,
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
    root_id: NonEmptyText | None = None
    landed_oid: CommitOid | None = None
    tree: CommitOid | None = None
    gate_receipt_digest: NonEmptyText | None = None
    landing_receipt_digest: NonEmptyText | None = None
    previous_attempts: tuple[NonEmptyText, ...] = ()

    @classmethod
    def prepared(
        cls,
        *,
        epic_id: str,
        stage_id: str,
        attempt: int,
        target_ref: str,
        expected_base_commit: str,
    ) -> PhaseBridgeRecord:
        """Build a new pre-claim admission intent."""
        return cls(
            state=PhaseBridgeState.PREPARED,
            epic_id=epic_id,
            stage_id=stage_id,
            attempt=attempt,
            instance_key=INSTANCE_KEY_TEMPLATE.format(
                epic_id=epic_id, stage_id=stage_id, attempt=attempt
            ),
            target_ref=target_ref,
            expected_base_commit=expected_base_commit,
        )

    def next_attempt(self) -> PhaseBridgeRecord:
        """Mint the next distinct root identity after an eligible retry."""
        return self.prepared(
            epic_id=self.epic_id,
            stage_id=self.stage_id,
            attempt=self.attempt + 1,
            target_ref=self.target_ref,
            expected_base_commit=self.expected_base_commit,
        ).model_copy(
            update={"previous_attempts": (*self.previous_attempts, self.instance_key)}
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
