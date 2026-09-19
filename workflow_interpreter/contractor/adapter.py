"""The closed Beads surface used by phase admission."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Final

from pydantic import ValidationError

from workflow_interpreter.bdio import finalize
from workflow_interpreter.bdio.client import BdClient, DependencyRecord, DependencyType
from workflow_interpreter.bdio.config import BdConfig
from workflow_interpreter.bdio.reads import WorkflowReads
from workflow_interpreter.bdio.wire import BeadRecord, Metadata
from workflow_interpreter.contractor.models import (
    MSG_BACKEND_IMMUTABLE,
    ContractorRecord,
    ContractorState,
)
from workflow_interpreter.ledger.closure import ClosureProbe

if TYPE_CHECKING:
    from workflow_interpreter.contractor.integration import IntegrationGuard

CONTRACTOR_METADATA_KEY: Final[str] = "contractor"
MSG_WRONG_STAGE: Final[str] = "contractor record belongs to stage {stage_id!r}"
MSG_WRONG_INCOMING_STATE: Final[str] = (
    "incoming contractor record expected state {state!r}, got {actual!r}"
)
MSG_IDEMPOTENT_STATE: Final[str] = (
    "idempotent contractor re-prepare requires stored state prepared, got {actual!r}"
)
MSG_IDEMPOTENT_RECORD: Final[str] = (
    "idempotent contractor re-prepare requires an incoming record identical to stored"
)
MSG_SUCCESSION_CLOSED: Final[str] = (
    "valid contractor succession refuses a closed stored record"
)
MSG_SUCCESSION_RETIRED: Final[str] = (
    "valid contractor succession refuses a retired task: it was abandoned, and "
    "an abandoned task is not retried (store-restructure §3.8)"
)
MSG_SUCCESSION_LANDED: Final[str] = (
    "valid contractor succession refuses a landed stored record: the work is on "
    "the target ref, and what an unpinned export needs is recovery, not a "
    "second attempt (store-restructure §3.5)"
)
MSG_SUCCESSION_ATTEMPT: Final[str] = (
    "valid contractor succession requires incoming attempt {expected}, got {actual}"
)
MSG_SUCCESSION_HISTORY: Final[str] = (
    "valid contractor succession requires incoming previous_attempts to extend stored"
)
MSG_STORED_RECORD_UNREADABLE: Final[str] = (
    "stored contractor record is unreadable: {reason}"
)
MSG_CLOSE_REASON: Final[str] = "contractor landing receipt={digest}"
MSG_NOT_CLOSABLE: Final[str] = (
    "stage {stage_id!r} does not derive closed: a task must have its whole "
    "record durable in git — exported and anchored — before its bead closes "
    "(store-restructure §3.5, D5)"
)
MSG_NO_CLOSURE_PROBE: Final[str] = (
    "stage {stage_id!r} cannot close without a ledger to derive closure from: "
    "the close would be recorded on evidence nothing anchors (§3.5, D5)"
)
STATUS_CLOSED: Final[str] = "closed"


class ContractorAdapterError(ValueError):
    """A phase operation was requested with incompatible durable evidence."""


class ContractorAdapter:
    """Perform only fixed Beads operations needed to admit one named stage."""

    def __init__(self, client: BdClient, reads: WorkflowReads | None = None) -> None:
        self._client = client
        self._reads = WorkflowReads(client) if reads is None else reads
        self.integration_guard: IntegrationGuard | None = None
        self.closure: ClosureProbe | None = None
        """Whether this task's record is already durable in git (§3.5).

        Injected like the integration guard, and for the same reason: the
        adapter owns bead writes and must not construct a ledger. Absent only
        for a wiring with no ledger at all — where the close refuses, because
        no export can exist, and succession is decided by the stored record
        alone."""

    @classmethod
    def from_config(
        cls, config: BdConfig, reads: WorkflowReads | None = None
    ) -> ContractorAdapter:
        """Build the contractor's read/write adapter without exposing bd transport.

        `reads` is the store the engine's roots live in. The adapter owns the
        TASK bead (§3.2 authoritative writes) and nothing else, so a root
        lookup is somebody else's read; without one injected it falls back to
        its own transport, which is the same store today.
        """
        return cls(BdClient(config), reads)

    def guard_integration(
        self, record: ContractorRecord, *, post_cas: bool = False
    ) -> None:
        """Integration records are unusable without their runtime authority."""
        if self.integration_guard is not None:
            from workflow_interpreter.foreman.replacement import guard_contractor

            guard_contractor(self.integration_guard.composition, record)
        elif record.successor_key is not None:
            raise ContractorAdapterError("successor contractor requires runtime guard")
        stored = self.show(record.stage_id).metadata.get(CONTRACTOR_METADATA_KEY)
        if (
            isinstance(stored, dict)
            and stored.get("integration_digest") is not None
            and stored.get("integration_digest") != record.integration_digest
        ):
            raise ContractorAdapterError(
                "cannot strip or change stored integration authority"
            )
        if (
            isinstance(stored, dict)
            and stored.get("successor_key") is not None
            and (stored.get("successor_owner"), stored.get("successor_key"))
            != (record.successor_owner, record.successor_key)
        ):
            raise ContractorAdapterError(
                "cannot strip or change stored successor authority"
            )
        if record.integration_digest is None:
            if any(
                (
                    record.integration_owner,
                    record.integration_slot,
                    record.integration_generation is not None,
                )
            ):
                raise ContractorAdapterError("incomplete integration binding")
            return
        if self.integration_guard is None:
            raise ContractorAdapterError("integration requires runtime guard")
        if post_cas:
            self.integration_guard.post_cas(record)
        else:
            self.integration_guard.binding(record)

    def show(self, stage_id: str) -> BeadRecord:
        """Read one resolved stage by id."""
        return self._client.show(stage_id)

    def direct_children(self, epic_id: str) -> tuple[BeadRecord, ...]:
        """List only rows whose persisted parent is the named epic."""
        return tuple(
            bead
            for bead in self._client.list_children(epic_id)
            if bead.parent == epic_id
        )

    def dependencies(self, stage_id: str) -> tuple[DependencyRecord, ...]:
        """Inspect the selected stage's declared dependencies."""
        return self._client.list_dependencies(stage_id)

    def blocking_dependencies(self, stage_id: str) -> tuple[DependencyRecord, ...]:
        """Return only unfinished blocking dependencies for a selected stage."""
        return tuple(
            dependency
            for dependency in self.dependencies(stage_id)
            if dependency.dependency_type is DependencyType.BLOCKS
            and dependency.status != STATUS_CLOSED
        )

    def record(self, stage_id: str) -> ContractorRecord:
        """Read the complete contractor relation currently persisted on a stage."""
        return self._record(self.show(stage_id).metadata)

    def owns_root(self, instance_key: str, root_id: str) -> bool:
        """Require a uniquely persisted root, not an inferred key-shaped owner."""
        roots = self._reads.roots_by_instance_key(instance_key)
        return (
            len(roots) == 1
            and roots[0].id == root_id
            and roots[0].metadata.get("wf_root_id") == root_id
        )

    def has_root(self, instance_key: str) -> bool:
        """Report whether durable evidence exists for one contractor identity."""
        return bool(self._reads.roots_by_instance_key(instance_key))

    def prepare(self, stage_id: str, record: ContractorRecord) -> ContractorRecord:
        """Persist and read back a complete pre-claim admission intent."""
        self._assert_stage(stage_id, record)
        self._assert_state(record, ContractorState.PREPARED, MSG_WRONG_INCOMING_STATE)
        existing = self.show(stage_id).metadata.get(CONTRACTOR_METADATA_KEY)
        if existing is not None:
            try:
                stored_record = ContractorRecord.model_validate(existing)
            except ValidationError as exc:
                raise ContractorAdapterError(
                    MSG_STORED_RECORD_UNREADABLE.format(reason=exc)
                ) from exc
            if (
                stored_record.integration_digest is not None
                and record.integration_digest is None
            ):
                raise ContractorAdapterError(
                    "cannot strip stored integration authority"
                )
            if (
                stored_record.successor_key is not None
                and record.successor_key is None
                and record.integration_digest is None
            ):
                raise ContractorAdapterError("cannot strip stored successor authority")
            self._assert_prepare_shape(stored_record, record)
        stored = self._client._merge_metadata(stage_id, self._metadata(record))
        return self._record(stored.metadata)

    def admit(
        self, stage_id: str, record: ContractorRecord, *, root_id: str
    ) -> ContractorRecord:
        """Atomically claim a stage while writing its complete admitted relation."""
        self._assert_stage(stage_id, record)
        self._assert_state(record, ContractorState.PREPARED, MSG_WRONG_INCOMING_STATE)
        admitted = record.admitted(root_id)
        self.guard_integration(admitted)
        stored = self._client._claim_and_merge_metadata(
            stage_id, self._metadata(admitted)
        )
        return self._record(stored.metadata)

    def gate_red(self, stage_id: str, record: ContractorRecord) -> ContractorRecord:
        """Keep a failed verification eligible only for the explicit retry contract."""
        self._assert_stage(stage_id, record)
        self.guard_integration(record)
        updated = record.model_copy(update={"state": ContractorState.GATE_RED})
        stored = self._client._merge_metadata(stage_id, self._metadata(updated))
        return self._record(stored.metadata)

    def land(self, stage_id: str, record: ContractorRecord) -> ContractorRecord:
        """Persist and read back the artifact relation after a successful CAS."""
        self._assert_stage(stage_id, record)
        self._assert_state(record, ContractorState.LANDED, MSG_WRONG_INCOMING_STATE)
        self.guard_integration(record, post_cas=True)
        stored = self._client._merge_metadata(stage_id, self._metadata(record))
        return self._record(stored.metadata)

    def close(
        self, stage_id: str, record: ContractorRecord, receipt_digest: str
    ) -> ContractorRecord:
        """Close and read back a stage whose durable relation names its receipt.

        §3.5: the bead is closed immediately after the metadata merge below,
        so a task that does not derive `closed()` would close on a record only
        `.wf/` holds — and `git clean` can delete that. The refusal is here,
        at the one write that closes, rather than at the composition that
        called it; the record itself stays at LANDED, because nothing writes
        CLOSED any more.
        """
        self._assert_stage(stage_id, record)
        self._assert_state(record, ContractorState.LANDED, MSG_WRONG_INCOMING_STATE)
        self.guard_integration(record, post_cas=True)
        if record.landing_receipt_digest != receipt_digest:
            raise ContractorAdapterError("close receipt does not match landed relation")
        # Last, immediately before the write: every other refusal is about the
        # record this call was handed, and this one is about the world it is
        # being written into.
        if self.closure is None:
            raise ContractorAdapterError(MSG_NO_CLOSURE_PROBE.format(stage_id=stage_id))
        if not self.closure.closed(stage_id):
            raise ContractorAdapterError(MSG_NOT_CLOSABLE.format(stage_id=stage_id))
        stored = self._client._merge_metadata(stage_id, self._metadata(record))
        closed = finalize.close_forward(
            self._client,
            stored,
            MSG_CLOSE_REASON.format(digest=receipt_digest),
        )
        result = self._record(closed.metadata)
        if result.integration_digest is not None and self.integration_guard is not None:
            self.integration_guard.finished(result)
        return result

    @staticmethod
    def _metadata(record: ContractorRecord) -> Metadata:
        """Serialize the whole nested record because bd replaces nested objects."""
        return {CONTRACTOR_METADATA_KEY: record.model_dump(by_alias=True, mode="json")}

    @staticmethod
    def _record(metadata: Mapping[str, object]) -> ContractorRecord:
        """Parse the durable contractor record read back from a stage."""
        return ContractorRecord.model_validate(metadata[CONTRACTOR_METADATA_KEY])

    @staticmethod
    def _assert_stage(stage_id: str, record: ContractorRecord) -> None:
        """Refuse to write a record for a different stage."""
        if record.stage_id != stage_id:
            raise ContractorAdapterError(MSG_WRONG_STAGE.format(stage_id=stage_id))

    @staticmethod
    def _assert_state(
        record: ContractorRecord, state: ContractorState, message: str
    ) -> None:
        """Refuse a contractor record that is not in an expected lifecycle state."""
        if record.state is not state:
            raise ContractorAdapterError(
                message.format(state=state.value, actual=record.state.value)
            )

    def _assert_prepare_shape(
        self, stored: ContractorRecord, incoming: ContractorRecord
    ) -> None:
        """Allow only exact recovery or one successor over unfinished work.

        A SUCCESSOR may change `root_backend`, because a new attempt root is
        exactly what the `store` switch applies to (D18); re-preparing THIS
        attempt may not, because its root may already exist on the backend the
        stored record pinned (§3.2).

        What ENDS succession used to be a stored CLOSED, and nothing writes
        one after S2 (§3.5). Three refusals replace it, in the order that
        names the finished task most precisely: the task derives `closed()`,
        the task is `retired()` — abandoned, which is never retried (§3.8) —
        or the stored record already landed, which is the crash-before-pin
        shape, where what is owed is recovery of the pin rather than a second
        attempt at work already on the target ref.
        """
        if incoming.attempt == stored.attempt:
            if incoming.root_backend is not stored.root_backend:
                raise ContractorAdapterError(
                    MSG_BACKEND_IMMUTABLE.format(
                        stored=stored.root_backend.value,
                        incoming=incoming.root_backend.value,
                    )
                )
            if stored.state is not ContractorState.PREPARED:
                raise ContractorAdapterError(
                    MSG_IDEMPOTENT_STATE.format(actual=stored.state.value)
                )
            if incoming != stored:
                raise ContractorAdapterError(MSG_IDEMPOTENT_RECORD)
            return
        if self.closure is not None:
            if self.closure.closed(stored.stage_id):
                raise ContractorAdapterError(MSG_SUCCESSION_CLOSED)
            if self.closure.retired(stored.stage_id):
                raise ContractorAdapterError(MSG_SUCCESSION_RETIRED)
        if stored.state is ContractorState.LANDED:
            raise ContractorAdapterError(MSG_SUCCESSION_LANDED)
        expected_attempt = stored.attempt + 1
        if incoming.attempt != expected_attempt:
            raise ContractorAdapterError(
                MSG_SUCCESSION_ATTEMPT.format(
                    expected=expected_attempt, actual=incoming.attempt
                )
            )
        if (
            incoming.epic_id != stored.epic_id
            or incoming.stage_id != stored.stage_id
            or incoming.target_ref != stored.target_ref
            or (
                incoming.integration_digest is None
                and incoming.expected_base_commit != stored.expected_base_commit
            )
            or incoming.verification_policy != stored.verification_policy
        ):
            raise ContractorAdapterError(
                "successor changes admitted identity or policy"
            )
        expected_history = (*stored.previous_attempts, stored.instance_key)
        if incoming.previous_attempts != expected_history:
            raise ContractorAdapterError(MSG_SUCCESSION_HISTORY)
