"""Typed durable records for one contractor stage admission."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.contractor.verification import VerificationPolicy

type ContractorSchema = Literal["contract/3"]
CONTRACTOR_SCHEMA: Final[ContractorSchema] = "contract/3"
INSTANCE_KEY_PREFIX: Final[str] = "contract:"
"""What makes a root CONTRACTOR-owned, readable from the root itself (§3.9).

Terminal cleanup has to know whether the task that owns a root closes through
the contractor — and therefore owes an export before anything is deleted — without
a bd round trip per tick. The instance key is pinned on the root record, so the
answer is already in hand."""
INSTANCE_KEY_TEMPLATE: Final[str] = (
    INSTANCE_KEY_PREFIX + "{epic_id}:{stage_id}:attempt:{attempt}"
)
MSG_INSTANCE_KEY: Final[str] = "contractor instance_key is not derived from identity"
MSG_PREVIOUS_ATTEMPTS_COUNT: Final[str] = (
    "contractor previous_attempts does not match attempt count"
)
MSG_PREVIOUS_ATTEMPTS_UNIQUE: Final[str] = (
    "contractor previous_attempts must contain unique identities"
)
MSG_PREPARED_NOT_FIRST_ATTEMPT: Final[str] = (
    "contractor prepared records must be the first attempt"
)
MSG_BACKEND_IMMUTABLE: Final[str] = (
    "contractor root_backend is pinned at prepare and cannot change from "
    "{stored!r} to {incoming!r}"
)

CommitOid = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
NonEmptyText = Annotated[str, StringConstraints(min_length=1)]


class ContractorState(StrEnum):
    """The complete contractor lifecycle vocabulary."""

    PREPARED = "prepared"
    ADMITTED = "admitted"
    # Retained as dead vocabulary: pre-S0 `phase-bridge/3` records carried it, and
    # no such record can validate against `contract/3` (R12: no read shim). Removing
    # it is safe once S4 replaces this record with `contractor_records`.
    LANDING = "landing"
    LANDED = "landed"
    GATE_RED = "gate-red"
    # The orchestrator's third verb (§3.8). A task the graph never took to
    # `shipped` and that will never be retried: it is `retired()` rather than
    # closed, so cleanup and archive proceed on what exists while succession
    # is refused. Nothing derives it — `wf phase abandon` writes it.
    ABANDONED = "abandoned"
    # The same retirement, decided by somebody ELSE (§3.8, S5). A tracker item
    # closed outside this engine surfaces as a `Conflict` at the next tracker
    # contact; the record records what was OBSERVED rather than guessing that
    # the work is done, and a distinct state is what keeps "we abandoned it"
    # from being confused with "it was taken away from us".
    ABANDONED_EXTERNAL = "abandoned-external"


class ContractorRecord(BaseModel):
    """Persist one stage's contractor identity without duplicating root facts."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: ContractorSchema = Field(
        alias="schema",
        serialization_alias="schema",
        frozen=True,
    )
    state: ContractorState
    epic_id: NonEmptyText
    stage_id: NonEmptyText
    attempt: int = Field(ge=1)
    instance_key: NonEmptyText
    root_backend: BackendKind = Field(default=BackendKind.BD, frozen=True)
    """The backend this ATTEMPT root is pinned to (§3.2, D18).

    Written at PREPARE, before admission creates the root or its branch, so
    the store a root is served by can be chosen before the root is loaded. It
    defaults to bd because a missing pin only ever appeared on pre-S0
    `phase-bridge/3` records, which describe bd roots and which S0 makes
    unloadable anyway — so the default has one true reading rather than an
    ambiguous one."""
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
    blockers_checked: bool = True
    """Whether this task's blockers were actually looked at (R9).

    False when the tracker declared no `BLOCKERS` capability and the wiring did
    not require one, so the trace can answer which policy applied rather than
    leaving "nothing blocked it" and "nobody asked" indistinguishable. True by
    default, which is what every record written before S5 means.
    """
    previous_attempts: tuple[NonEmptyText, ...]

    @model_validator(mode="after")
    def _assert_attempt_identity(self) -> ContractorRecord:
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
        root_backend: BackendKind = BackendKind.BD,
        blockers_checked: bool = True,
    ) -> ContractorRecord:
        """Build a new pre-claim admission intent on the selected backend."""
        if attempt != 1:
            raise ValueError(MSG_PREPARED_NOT_FIRST_ATTEMPT)
        return cls(
            schema=CONTRACTOR_SCHEMA,
            state=ContractorState.PREPARED,
            epic_id=epic_id,
            stage_id=stage_id,
            attempt=attempt,
            instance_key=INSTANCE_KEY_TEMPLATE.format(
                epic_id=epic_id, stage_id=stage_id, attempt=attempt
            ),
            root_backend=root_backend,
            target_ref=target_ref,
            expected_base_commit=expected_base_commit,
            previous_attempts=(),
            verification_policy=verification_policy,
            blockers_checked=blockers_checked,
        )

    def next_attempt(self, root_backend: BackendKind | None = None) -> ContractorRecord:
        """Mint the next distinct root identity after an eligible retry.

        A retry is a NEW attempt root, so the `store` switch applies to it
        (D18): the caller passes the value in force now, and only a caller
        with nothing to say keeps this attempt's pin.
        """
        return ContractorRecord(
            schema=CONTRACTOR_SCHEMA,
            state=ContractorState.PREPARED,
            epic_id=self.epic_id,
            stage_id=self.stage_id,
            attempt=self.attempt + 1,
            instance_key=INSTANCE_KEY_TEMPLATE.format(
                epic_id=self.epic_id, stage_id=self.stage_id, attempt=self.attempt + 1
            ),
            root_backend=self.root_backend if root_backend is None else root_backend,
            target_ref=self.target_ref,
            expected_base_commit=self.expected_base_commit,
            previous_attempts=(*self.previous_attempts, self.instance_key),
            verification_policy=self.verification_policy,
            blockers_checked=self.blockers_checked,
        )

    def admitted(self, root_id: str) -> ContractorRecord:
        """Attach the converged root to an admitted stage record."""
        return self.model_copy(
            update={"state": ContractorState.ADMITTED, "root_id": root_id}
        )

    def landed(
        self,
        artifact_oid: str,
        tree: str,
        gate_receipt_digest: str,
        receipt_digest: str,
    ) -> ContractorRecord:
        """Record the signed artifact that won the one landing CAS."""
        return self.model_copy(
            update={
                "state": ContractorState.LANDED,
                "landed_oid": artifact_oid,
                "tree": tree,
                "gate_receipt_digest": gate_receipt_digest,
                "landing_receipt_digest": receipt_digest,
            }
        )

    # There is deliberately no `closed()`: closure is derived from the ledger
    # and its git anchor (§3.5), so the record's last state is LANDED and the
    # blob it used to carry is `tasks.export_oid`, the latch nothing exports.
