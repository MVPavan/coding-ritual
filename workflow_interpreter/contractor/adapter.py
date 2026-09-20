"""The closed Beads surface used by phase admission."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Final

import structlog
from pydantic import ValidationError

from workflow_interpreter.bdio.reads import WorkflowReads
from workflow_interpreter.contractor.models import (
    ContractorRecord,
    ContractorState,
)
from workflow_interpreter.contractor.records import ContractorRecords, StoredRecord
from workflow_interpreter.ledger.closure import ClosureProbe
from workflow_interpreter.tracker import (
    Blocker,
    Claim,
    Close,
    TrackerCapability,
    TrackerIntent,
    TrackerRef,
    WorkItem,
)
from workflow_interpreter.tracker.outbox import TrackerOutbox
from workflow_interpreter.tracker.port import TrackerPort

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
MSG_ABANDON_REASON: Final[str] = "contractor task abandoned (store-restructure §3.8)"
MSG_NOT_CLOSABLE: Final[str] = (
    "stage {stage_id!r} does not derive closed: a task must have its whole "
    "record durable in git — exported and anchored — before its bead closes "
    "(store-restructure §3.5, D5)"
)
MSG_NO_OUTBOX: Final[str] = (
    "this wiring has no tracker outbox, so the mirror for {stage_id!r} has "
    "nowhere durable to wait: a mirror write is never issued directly, because "
    "an unrecorded tracker call is what the outbox exists to prevent "
    "(store-restructure §3.1, §3.3)"
)
_RETIRED_STATES: Final[frozenset[ContractorState]] = frozenset(
    {ContractorState.ABANDONED, ContractorState.ABANDONED_EXTERNAL}
)
"""The two states `abandon` is idempotent over — ours and the tracker's."""
_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)


MSG_NO_ROOT_READS: Final[str] = (
    "this contractor adapter was given no root store, so it cannot answer "
    "which root owns an instance key: supply `reads` at construction "
    "(store-restructure R1)"
)


class ContractorAdapterError(ValueError):
    """A phase operation was requested with incompatible durable evidence."""


class ContractorAdapter:
    """Perform only fixed Beads operations needed to admit one named stage."""

    def __init__(
        self,
        reads: WorkflowReads | None = None,
        *,
        closure: ClosureProbe,
        records: ContractorRecords,
        tracker: TrackerPort,
        outbox: TrackerOutbox | None = None,
    ) -> None:
        self._reads = reads
        """The store the engine's ROOTS live in, when this caller has one.

        Optional, and no longer defaultable: the adapter used to build a
        `WorkflowReads` over its own bd transport when nobody supplied one,
        and S6 deleted that transport's record-store half (R1). The two reads
        that need it refuse by name instead of reading an empty store —
        `wf ledger reconcile` builds an adapter to release a stranded claim
        and never asks about roots."""
        self.tracker: TrackerPort = tracker
        """The contractor's ONE tracker surface (§3.3, R2).

        REQUIRED. It used to default to `BdTracker(client)` — "the wiring that
        does not change" — and that default is how eight of nine construction
        sites came to mirror into bd whatever `tracker.backend` said. A
        default nobody notices is a default nobody notices being wrong, so the
        question is asked at every construction site instead; production
        answers it once, in `contractor.tracker_wiring`."""
        self._outbox = outbox
        """Where a mirror write waits when the tracker cannot answer (§3.3).

        Absent only for a wiring with no LEDGER, which has nowhere durable to
        wait — and such a wiring can reach no mirror at all, because every one
        of them follows a record transition its `NoContractorRecords` refuses.
        It does NOT fall back to a direct call: an unrecorded tracker write is
        the one thing the outbox exists to prevent (§3.1)."""
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

    def ref(self, stage_id: str) -> TrackerRef:
        """This stage's foreign identity, as the configured tracker knows it."""
        return TrackerRef(kind=self.tracker.kind, ref=stage_id)

    def mirror(self, stage_id: str, intent: TrackerIntent) -> None:
        """Ask the tracker for a desired state, durably (§3.1, §3.3).

        Through the outbox rather than at the tracker: the ledger has already
        decided, so an unreachable tracker leaves a pending row and the caller
        goes on. The drain is immediate because the caller is usually about to
        exit, and a row applied now is one the driver-exit drain finds nothing
        to do about.

        Never a direct call. A wiring with no outbox is refused BY NAME rather
        than allowed to write the tracker unrecorded: that branch is how eight
        construction sites mirrored into bd behind the configuration's back.
        """
        self._enqueue(stage_id, intent)
        self._drain(stage_id)

    def _enqueue(
        self,
        stage_id: str,
        intent: TrackerIntent,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        """Record the owed state, inside the fact's transaction when given one."""
        if self._outbox is None:
            raise ContractorAdapterError(MSG_NO_OUTBOX.format(stage_id=stage_id))
        self._outbox.enqueue(stage_id, intent, connection)

    def _drain(self, stage_id: str) -> None:
        """Try the tracker now; a row it does not answer waits for the exit.

        A CONFLICT is said out loud. It retires its row — the tracker answered,
        and re-sending the state would not change the answer — so a result
        nobody read was a tracker disagreeing about a task this process just
        decided, recorded nowhere a caller sees.
        """
        if self._outbox is None:
            return
        result = self._outbox.drain(self.tracker, stage_id)
        if result.conflicts:
            _LOG.warning(
                "wf.tracker.mirror_conflicted",
                stage_id=stage_id,
                refs=list(result.conflicts),
            )

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

    def item(self, stage_id: str) -> WorkItem | None:
        """What the CONFIGURED tracker says about this stage, or nothing (§3.3).

        The adapter's four bd reads — `show`, `direct_children`, `dependencies`,
        `blocking_dependencies` — are gone, and this is what replaced the only
        one production still needed. They asked the bd TRANSPORT while
        `self.tracker` held the configured port, so a repository on the file
        tracker read bd about its own stage and `landing.recover` decided the
        close had not completed.

        Nothing rather than a refusal when the tracker holds no item: an
        absent item is an ANSWER (R9) — the null tracker holds none at all, and
        a caller that cannot proceed without one says so in its own words.
        """
        return self.tracker.get(self.ref(stage_id))

    def release_stranded_claim(self, stage_id: str, actor: str) -> None:
        """Free a claim a crash inside §3.4's window left behind.

        Here rather than in admission, because two callers need exactly this
        detection: the next `wf contract` on the task, and `wf ledger
        reconcile <task>` — which §3.4 names as the other repair path and
        which used to drain the outbox and do nothing else, so a crash on a
        machine where the next `wf contract` is days away left `bd ready` and
        the file tracker wrong with the documented remedy doing nothing.

        The window leaves ONE shape — a PREPARED record plus an item this
        actor holds — and it is detected PER TASK rather than by a sweep the
        port would need a `list` for. The release is mirrored and drained now
        rather than at driver exit, because a fresh claim may be about to be
        taken and a release applied after it would take it away again.
        """
        stored = self.stored_record(stage_id)
        if stored is None or stored.state is not ContractorState.PREPARED:
            return
        if TrackerCapability.CLAIM not in self.tracker.capabilities:
            return
        held = self.tracker.get(self.ref(stage_id))
        if held is None or held.claimed_by != actor:
            return
        self.mirror(stage_id, Claim(ref=self.ref(stage_id), actor=actor, held=False))

    def record_claim(self, stage_id: str, actor: str) -> None:
        """Say in the outbox that this actor HOLDS the item now (§3.4).

        Not a second write — the claim was applied directly, because admission
        needs the answer before it can proceed. This is what stops an older
        row from undoing it: `release_stranded_claim` mirrors a release and
        drains it, and an `Unknown` there leaves the release pending. Nothing
        replaced it, so the next drain — the driver's exit — handed back the
        claim of a run in progress.

        A claim and a release are ONE desired-state key, so enqueueing the
        claim replaces that row with what is now true. A wiring with no outbox
        has no stale row to replace either.
        """
        if self._outbox is None:
            return
        self._enqueue(stage_id, Claim(ref=self.ref(stage_id), actor=actor))

    def unresolved_blockers(self, stage_id: str) -> tuple[Blocker, ...]:
        """What this stage still waits on, as the configured tracker sees it.

        Empty for a tracker with no `BLOCKERS` capability, which is R9's rule
        rather than an omission: a tracker that cannot answer the question has
        not answered it "no blockers", and the caller that cares whether it was
        asked at all reads `capabilities` (§3.3).
        """
        if TrackerCapability.BLOCKERS not in self.tracker.capabilities:
            return ()
        return tuple(
            blocker
            for blocker in self.tracker.blockers(self.ref(stage_id))
            if not blocker.resolved
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

    def _roots(self) -> WorkflowReads:
        """The root store this adapter was given, or a refusal naming the gap.

        A refusal rather than a fallback: the adapter has no transport of its
        own since S6 (R1), and answering "no such root" from a store nobody
        supplied would let an ownership check pass on absence.
        """
        if self._reads is None:
            raise ContractorAdapterError(MSG_NO_ROOT_READS)
        return self._reads

    def owns_root(self, instance_key: str, root_id: str) -> bool:
        """Require a uniquely persisted root, not an inferred key-shaped owner."""
        root = self._roots().root_by_instance_key(instance_key)
        return (
            root is not None
            and root.id == root_id
            and root.metadata.get("wf_root_id") == root_id
        )

    def has_root(self, instance_key: str) -> bool:
        """Report whether durable evidence exists for one contractor identity."""
        return self._roots().root_by_instance_key(instance_key) is not None

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
        held = self._required(stage_id)
        # A close changes nothing about the record — `land` stored this very
        # relation — and by now the record is EXPORTED and its bytes pinned.
        # Rewriting it would move `version` and `updated_at` inside a table the
        # export carries, so the task would stop re-exporting to the blob it
        # names and `wf ledger pin-export` would call the file stale (D3, §3.6).
        # The tracker mirror is the OUTBOX ROW, and it is written inside this
        # transition's transaction (§3.3): the ledger is the truth and the
        # item is the copy a human reads, so an unreachable tracker cannot
        # fail a close that has already happened — and a crash cannot lose the
        # `Close` either, because nothing re-derives one from `closed()`.
        closing = Close(
            ref=self.ref(stage_id),
            reason=MSG_CLOSE_REASON.format(digest=receipt_digest),
        )
        if held.record == record:
            # Nothing to transition: `land` stored this very relation and the
            # export is pinned, so rewriting it would move `version` and
            # `updated_at` inside a table the export carries (D3, §3.6). The
            # enqueue is then its own write, with no fact to join.
            result = held.record
            self._enqueue(stage_id, closing)
        else:
            result = self._write(record, held, mirror=closing).record
        self._drain(stage_id)
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
        if held.record.state in _RETIRED_STATES:
            # ABANDONED_EXTERNAL answers here too, and enqueues no Close: the
            # task is already retired and its item is already closed, which is
            # how we found out (§3.8). A second Close would be a mirror write
            # for a state the mirror reached first.
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
        # The mirror row is written WITH the transition (§3.3): a retired
        # task's item is closed so a human stops seeing it as work, and an
        # unreachable tracker leaves a pending row rather than failing the
        # retirement — but a crash may not leave a retirement with no row.
        result = self._write(
            abandoned,
            held,
            mirror=Close(ref=self.ref(stage_id), reason=MSG_ABANDON_REASON),
        ).record
        self._drain(stage_id)
        # After the transition and never before it, exactly as the close
        # releases through `finished`: a claim freed for an abandon that then
        # failed to record would hand the target to a second attempt while the
        # first one was still live (R11).
        if result.integration_digest is not None and self.integration_guard is not None:
            self.integration_guard.release(result)
        return result

    def abandon_external(self, stage_id: str, reason: str) -> ContractorRecord:
        """Retire a task its TRACKER ended, on what was observed (§3.8).

        Never guessed: the only caller is the one that saw a `Conflict` naming
        a closed item, and the state it writes is distinct from `ABANDONED` so
        that "we retired it" and "it was taken from us" stay two facts. No
        mirror follows — the item is already closed, which is how we found out.
        """
        held = self._required(stage_id)
        if held.record.state is ContractorState.ABANDONED_EXTERNAL:
            return held.record
        _LOG.info("wf.contract.abandoned_external", stage_id=stage_id, reason=reason)
        return self._write(
            held.record.model_copy(
                update={"state": ContractorState.ABANDONED_EXTERNAL}
            ),
            held,
        ).record

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
        mirror: TrackerIntent | None = None,
    ) -> StoredRecord:
        """Move the record forward from the version this call read (§3.2).

        The version travels with the read rather than being re-fetched here:
        re-reading it would make the guard a formality, since the write would
        then be guarded by whatever the state had just become.

        `mirror` is the desired tracker state this transition implies, and it
        is enqueued INSIDE the transition's own transaction: a crash between
        the fact and its outbox row would lose the intent forever, because a
        drain only applies rows that exist (§3.3).
        """
        return self.records.update(
            record,
            expected_version=held.version,
            brief=held.brief if brief is None else brief,
            inside=None
            if mirror is None
            else (
                lambda connection: self._enqueue(record.stage_id, mirror, connection)
            ),
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

        What ENDS succession used to be a stored CLOSED, and nothing writes
        one after S2 (§3.5). Three refusals replace it, in the order that
        names the finished task most precisely: the task derives `closed()`,
        the task is `retired()` — abandoned, which is never retried (§3.8) —
        or the stored record already landed, which is the crash-before-pin
        shape, where what is owed is recovery of the pin rather than a second
        attempt at work already on the target ref.
        """
        if incoming.attempt == stored.attempt:
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
