"""The closed Beads surface used by phase admission."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from pydantic import ValidationError

from workflow_interpreter.bdio import finalize
from workflow_interpreter.bdio.client import BdClient, DependencyRecord, DependencyType
from workflow_interpreter.bdio.config import BdConfig
from workflow_interpreter.bdio.reads import WorkflowReads
from workflow_interpreter.bdio.wire import BeadRecord
from workflow_interpreter.contractor.models import (
    MSG_BACKEND_IMMUTABLE,
    ContractorRecord,
    ContractorState,
)
from workflow_interpreter.contractor.records import ContractorRecords, StoredRecord
from workflow_interpreter.ledger.closure import ClosureProbe

if TYPE_CHECKING:
    from workflow_interpreter.contractor.integration import IntegrationGuard

MSG_NO_STORED_RECORD: Final[str] = (
    "task {stage_id!r} has no contractor record: it is a ledger row written "
    "at prepare (store-restructure §3.2, R4), and an operation that needs one "
    "is not one a task that never prepared can have"
)
MSG_ABANDON_LANDED: Final[str] = (
    "task {stage_id!r} has landed, so it is not abandoned: the work is on the "
    "target ref and what it owes is a pinned export, not a retirement (§3.8)"
)
MSG_ABANDON_LANDING: Final[str] = (
    "task {stage_id!r} journalled the landing intent of attempt {attempt}, so "
    "its landing has begun and its work may already be on the target ref: what "
    "it owes is the recovery `wf contract` performs, not a retirement that "
    "would delete the worktree and pin no export (§3.8, D17)"
)
MSG_ABANDON_CLOSED: Final[str] = (
    "task {stage_id!r} is closed — its whole record is durable in git — and a "
    "closed task is not abandoned (§3.5, §3.8)"
)
MSG_STORED_RECORD_UNREADABLE: Final[str] = (
    "stored contractor record is unreadable: {reason}"
)
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
MSG_CLOSE_REASON: Final[str] = "contractor landing receipt={digest}"
MSG_NOT_CLOSABLE: Final[str] = (
    "stage {stage_id!r} does not derive closed: a task must have its whole "
    "record durable in git — exported and anchored — before its bead closes "
    "(store-restructure §3.5, D5)"
)
STATUS_CLOSED: Final[str] = "closed"


class ContractorAdapterError(ValueError):
    """A phase operation was requested with incompatible durable evidence."""


class ContractorAdapter:
    """Perform only fixed Beads operations needed to admit one named stage."""

    def __init__(
        self,
        client: BdClient,
        reads: WorkflowReads | None = None,
        *,
        closure: ClosureProbe,
        records: ContractorRecords,
    ) -> None:
        self._client = client
        self._reads = WorkflowReads(client) if reads is None else reads
        self.integration_guard: IntegrationGuard | None = None
        self.records: ContractorRecords = records
        """Where this task's record lives (§3.2, R4).

        The record is a LEDGER row since S4, not bead metadata, and that is
        what makes admission possible with the tracker unreachable. Injected
        and required for `closure`'s reason: the adapter owns the record and
        may not open a database, and a construction site that supplied nothing
        would quietly lose every transition it wrote."""
        self.closure: ClosureProbe = closure
        """Whether this task's record is already durable in git (§3.5).

        Injected like the integration guard, because the adapter owns bead
        writes and must not construct a ledger — but REQUIRED, unlike it: the
        close refusal and the succession refusal are both decided here, and a
        construction site that supplied nothing used to skip the succession
        one silently. A wiring with no ledger passes `NoLedgerClosure`, which
        answers the question rather than leaving it unasked."""

    @classmethod
    def from_config(
        cls,
        config: BdConfig,
        reads: WorkflowReads | None = None,
        *,
        closure: ClosureProbe,
        records: ContractorRecords,
    ) -> ContractorAdapter:
        """Build the contractor's read/write adapter without exposing bd transport.

        `reads` is the store the engine's roots live in. The adapter owns the
        TASK bead (§3.2 authoritative writes) and nothing else, so a root
        lookup is somebody else's read; without one injected it falls back to
        its own transport, which is the same store today.

        `closure` is the ledger's answer about this task (`ledger.closure`),
        and it has no default for the reason §3.5 gives: every caller that can
        reach a close or a succession has to have decided what answers it.
        """
        return cls(BdClient(config), reads, closure=closure, records=records)

    def guard_integration(
        self, record: ContractorRecord, *, post_cas: bool = False
    ) -> None:
        """Integration records are unusable without their runtime authority."""
        if self.integration_guard is not None:
            from workflow_interpreter.foreman.replacement import guard_contractor

            guard_contractor(self.integration_guard.composition, record)
        elif record.successor_key is not None:
            raise ContractorAdapterError("successor contractor requires runtime guard")
        held = self.stored(record.stage_id)
        if held is not None:
            self._assert_authority_kept(held.record, record)
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

    def stored(self, stage_id: str) -> StoredRecord | None:
        """This task's record and the version a transition must state.

        The one read every transition starts from: the version is not an
        attribute of the record, it is the evidence that the record has not
        moved since it was read (§3.2).

        A stored row that will not validate is named HERE, as an adapter
        refusal: the record moved into the ledger in S4, but whose error
        boundary a corrupt one lands behind did not. Every transition reads
        through this method, so wrapping it once covers all five.
        """
        try:
            return self.records.read(stage_id)
        except ValidationError as unreadable:
            raise ContractorAdapterError(
                MSG_STORED_RECORD_UNREADABLE.format(reason=unreadable)
            ) from unreadable

    def stored_record(self, stage_id: str) -> ContractorRecord | None:
        """The stored relation, or nothing when this task never prepared.

        What the call sites that used to read `bead.metadata['contractor']`
        ask now. Absence is an ANSWER here, not a failure: "has this stage a
        contractor?" is a question admission and the trace view both ask about
        stages that never had one.
        """
        held = self.stored(stage_id)
        return None if held is None else held.record

    def record(self, stage_id: str) -> ContractorRecord:
        """Read the complete contractor relation currently persisted for a task."""
        return self._required(stage_id).record

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

    def prepare(
        self, stage_id: str, record: ContractorRecord, *, brief: str | None = None
    ) -> ContractorRecord:
        """Persist and read back a complete pre-claim admission intent.

        `brief` is the task brief SNAPSHOT (§3.3, R4), written once with the
        record. Every later admission — a recovery, a retry, an admission
        with the tracker gone — reads it from here rather than from the
        tracker's description, which is what makes those admissions possible
        at all. A prepare that states none keeps the snapshot already stored:
        the brief belongs to the task, not to the attempt.
        """
        self._assert_stage(stage_id, record)
        self._assert_state(record, ContractorState.PREPARED, MSG_WRONG_INCOMING_STATE)
        existing = self.stored(stage_id)
        if existing is None:
            return self.records.create(record, brief=brief).record
        stored_record = existing.record
        if (
            stored_record.integration_digest is not None
            and record.integration_digest is None
        ):
            raise ContractorAdapterError("cannot strip stored integration authority")
        if (
            stored_record.successor_key is not None
            and record.successor_key is None
            and record.integration_digest is None
        ):
            raise ContractorAdapterError("cannot strip stored successor authority")
        self._assert_prepare_shape(stored_record, record)
        return self._write(record, existing, brief=brief).record

    def admit(
        self, stage_id: str, record: ContractorRecord, *, root_id: str
    ) -> ContractorRecord:
        """Atomically claim a stage while writing its complete admitted relation."""
        self._assert_stage(stage_id, record)
        self._assert_state(record, ContractorState.PREPARED, MSG_WRONG_INCOMING_STATE)
        admitted = record.admitted(root_id)
        self.guard_integration(admitted)
        # The transition is the ledger transaction now, not a claim on a bead
        # row: the tracker's own claim is placed before it, by the caller,
        # and never inside it (§3.4, R2 — no I/O in a store method).
        return self._write(admitted, self._required(stage_id)).record

    def gate_red(self, stage_id: str, record: ContractorRecord) -> ContractorRecord:
        """Keep a failed verification eligible only for the explicit retry contract."""
        self._assert_stage(stage_id, record)
        self.guard_integration(record)
        updated = record.model_copy(update={"state": ContractorState.GATE_RED})
        return self._write(updated, self._required(stage_id)).record

    def land(self, stage_id: str, record: ContractorRecord) -> ContractorRecord:
        """Persist and read back the artifact relation after a successful CAS."""
        self._assert_stage(stage_id, record)
        self._assert_state(record, ContractorState.LANDED, MSG_WRONG_INCOMING_STATE)
        self.guard_integration(record, post_cas=True)
        return self._write(record, self._required(stage_id)).record

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
        if not self.closure.closed(stage_id):
            raise ContractorAdapterError(MSG_NOT_CLOSABLE.format(stage_id=stage_id))
        result = self._write(record, self._required(stage_id)).record
        # The tracker mirror, after the ledger transition and never inside it
        # (§3.1): the ledger is the truth, and the bead is the copy a human
        # reads. S5 moves this onto the outbox so an unreachable tracker
        # cannot fail a close that has already happened.
        reason = MSG_CLOSE_REASON.format(digest=receipt_digest)
        if not finalize.is_finished(self.show(stage_id), reason):
            self._client._close_row(stage_id, reason)
        if result.integration_digest is not None and self.integration_guard is not None:
            self.integration_guard.finished(result)
        return result

    def abandon(self, stage_id: str) -> ContractorRecord:
        """Retire a task the graph never took to `shipped` (§3.8).

        The orchestrator's third verb, beside continue and retry. Idempotent,
        because abandoning is a decision rather than an event: a second
        `wf phase abandon` on the same task answers the same record instead of
        refusing, which is what lets an interrupted abandon be repeated.

        Refused for a task that LANDED or that derives `closed()`: its work is
        on the target ref, and what an unpinned export owes is recovery, not
        retirement. The record's own state is checked first, because a landed
        task that has not pinned yet is not closed and must still be refused.

        Refused for a task whose landing merely BEGAN, too, and on the same
        evidence `wf contract`'s recovery reads: the record is still ADMITTED
        for the whole landing window — journalled intent, fast-forward CAS,
        receipt — so a crash inside it would otherwise be abandonable while the
        commit sits on the target ref (D17).
        """
        held = self._required(stage_id)
        if held.record.state is ContractorState.ABANDONED:
            return held.record
        if held.record.state is ContractorState.LANDED:
            raise ContractorAdapterError(MSG_ABANDON_LANDED.format(stage_id=stage_id))
        if self.closure.closed(stage_id):
            raise ContractorAdapterError(MSG_ABANDON_CLOSED.format(stage_id=stage_id))
        if self.closure.landing_begun(stage_id, held.record.attempt):
            raise ContractorAdapterError(
                MSG_ABANDON_LANDING.format(
                    stage_id=stage_id, attempt=held.record.attempt
                )
            )
        abandoned = held.record.model_copy(update={"state": ContractorState.ABANDONED})
        result = self._write(abandoned, held).record
        # After the transition and never before it, exactly as the close
        # releases through `finished`: a claim freed for an abandon that then
        # failed to record would hand the target to a second attempt while the
        # first one was still live (R11).
        if result.integration_digest is not None and self.integration_guard is not None:
            self.integration_guard.release(result)
        return result

    def _required(self, stage_id: str) -> StoredRecord:
        """The stored record a transition is about, refusing when there is none."""
        held = self.stored(stage_id)
        if held is None:
            raise ContractorAdapterError(MSG_NO_STORED_RECORD.format(stage_id=stage_id))
        return held

    def _write(
        self,
        record: ContractorRecord,
        held: StoredRecord,
        *,
        brief: str | None = None,
    ) -> StoredRecord:
        """Move the record forward from the version this call read (§3.2).

        The version travels with the read rather than being re-fetched here:
        re-reading it would make the guard a formality, since the write would
        then be guarded by whatever the state had just become.
        """
        return self.records.update(
            record,
            expected_version=held.version,
            brief=held.brief if brief is None else brief,
        )

    @staticmethod
    def _assert_authority_kept(
        stored: ContractorRecord, record: ContractorRecord
    ) -> None:
        """Refuse a write that strips or moves stored runtime authority."""
        if (
            stored.integration_digest is not None
            and stored.integration_digest != record.integration_digest
        ):
            raise ContractorAdapterError(
                "cannot strip or change stored integration authority"
            )
        if stored.successor_key is not None and (
            stored.successor_owner,
            stored.successor_key,
        ) != (record.successor_owner, record.successor_key):
            raise ContractorAdapterError(
                "cannot strip or change stored successor authority"
            )

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
