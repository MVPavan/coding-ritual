"""Durable prepare-to-admit recovery for one selected phase stage."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.bdio.records import RootRecord
from workflow_interpreter.contractor.adapter import (
    ContractorAdapter,
    ContractorAdapterError,
)
from workflow_interpreter.contractor.models import ContractorRecord, ContractorState
from workflow_interpreter.contractor.verification import VerificationPolicy
from workflow_interpreter.inspector import INSTANCE_BRANCH_REF
from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.tracker import (
    Claim,
    Conflict,
    TrackerCapability,
    Unknown,
    WorkItemStatus,
)
from workflow_interpreter.tracker.constants import (
    MSG_CLOSED_ELSEWHERE,
    MSG_CONFLICT_CLAIM,
    MSG_UNKNOWN_CLAIM,
)

MSG_STAGE_NOT_DIRECT = "stage {stage_id!r} is not an open direct child of {epic_id!r}"
MSG_OTHER_ADMISSION = "stage {stage_id!r} has unfinished contractor admission"
MSG_BRIEF_REQUIRED = (
    "preparing stage {stage_id!r} needs its task brief: it is snapshotted with "
    "the record so that every later admission can run with the tracker "
    "unreachable (store-restructure §3.3, R4)"
)
MSG_IDENTITY_CONFLICT = "contractor identity conflicts with durable admission"
MSG_HEAD_MOVED = "coordinator HEAD differs from the recorded expected base"


class AdmissionRefused(ValueError):
    """Durable evidence is ambiguous and needs human attention."""

    def __init__(
        self, reason: str, *, blocked: bool = False, blocking_ids: tuple[str, ...] = ()
    ) -> None:
        """Name whether a refusal represents another stage's unfinished work."""
        super().__init__(reason)
        self.blocked = blocked
        self.blocking_ids = blocking_ids


class ContractorRoot(BaseModel):
    """The minimal persisted root identity admission is allowed to relate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    root_id: str
    instance_key: str
    instance_base_commit: str


class RootProvisioner(Protocol):
    """Use existing root convergence and persisted-base branch recovery."""

    def find(
        self, instance_key: str, backend: BackendKind, attempt: int
    ) -> ContractorRoot | None:
        """Return the uniquely converged root for an instance key."""

    def create(
        self, instance_key: str, backend: BackendKind, attempt: int
    ) -> ContractorRoot:
        """Create or recover one root through existing raw-record convergence."""

    def ensure_branch(self, root: ContractorRoot) -> None:
        """Restore the root's branch from its persisted base, never current HEAD."""


class WorkflowRootProvisioner:
    """Adapt existing root convergence and branch restoration to admission."""

    def __init__(
        self,
        adapter: ContractorAdapter,
        create_root: Callable[[str, BackendKind, int], RootRecord],
        git: Git,
        repo_root: Path,
    ) -> None:
        self._adapter = adapter
        self._create_root = create_root
        self._git = git
        self._repo_root = repo_root

    def find(
        self, instance_key: str, backend: BackendKind, attempt: int
    ) -> ContractorRoot | None:
        """Repair a discovered raw root through the existing convergence path."""
        if not self._adapter.has_root(instance_key):
            return None
        return self._contractor_root(self._create_root(instance_key, backend, attempt))

    def create(
        self, instance_key: str, backend: BackendKind, attempt: int
    ) -> ContractorRoot:
        """Create a root through the existing owner-first convergence path.

        `backend` is the attempt's own pin from the contractor record, not the
        `store` switch in force: a retry admitted after the switch flipped must
        land on the backend ITS record names (§3.2, D18). `attempt` is the
        record's own attempt number, which the root pins as its run identity
        (§3.7) rather than leaving it to be parsed back out of a root id.
        """
        return self._contractor_root(self._create_root(instance_key, backend, attempt))

    def ensure_branch(self, root: ContractorRoot) -> None:
        """Restore a missing branch from the root's persisted base commit."""
        branch = INSTANCE_BRANCH_REF.format(root_id=root.root_id)
        if self._git.ref_target(branch, cwd=self._repo_root) is None:
            self._git.update_ref(branch, root.instance_base_commit, cwd=self._repo_root)

    @staticmethod
    def _contractor_root(root: RootRecord) -> ContractorRoot:
        """Project a fully parsed root into the phase relation's identity fields."""
        base = root.metadata.instance_base_commit
        if base is None:
            raise AdmissionRefused(MSG_IDENTITY_CONFLICT)
        return ContractorRoot(
            root_id=root.root_id,
            instance_key=root.metadata.instance_key,
            instance_base_commit=base,
        )


class PhaseAdmission:
    """Prepare and admit one selected direct-child stage without scheduling it."""

    def __init__(
        self,
        adapter: ContractorAdapter,
        roots: RootProvisioner,
        head_commit: Callable[[], str],
        verification_policy: VerificationPolicy | None = None,
        root_backend: BackendKind = BackendKind.BD,
        task_brief: str | None = None,
        actor: str = "",
        blockers_checked: bool = True,
    ) -> None:
        """Pin the backend a first attempt is prepared on before it exists.

        `root_backend` is the `store` switch in force now (§3.2, D18). It is
        used only when THIS call prepares attempt one: a stored record already
        carries its own immutable pin, and admission never overwrites it.

        `task_brief` is the snapshot a FIRST prepare writes beside the record
        (§3.3, R4). A caller that has one has just read the tracker; a caller
        that has none is admitting a task that already prepared, and the
        snapshot it needs is already in the ledger.
        """
        self._adapter = adapter
        self._roots = roots
        self._head_commit = head_commit
        self._verification_policy = verification_policy
        self._root_backend = root_backend
        self._task_brief = task_brief
        self._actor = actor
        """Who a tracker claim is held BY (§3.4).

        The engine's configured actor, not a process identity: the claim has
        to mean the same thing to the second session that reads it, and a pid
        or a hostname would make every restart look like somebody else."""
        self._blockers_checked = blockers_checked

    def _claim(self, stage_id: str) -> None:
        """Claim the item in its tracker, immediately before the admit (§3.4).

        Last, and deliberately: every ledger-side refusal has already run, so
        an ordinary refusal never touches the tracker and `bd ready` is not
        churned — while the call still precedes the transaction, so no I/O sits
        inside one (R2, R3).

        `Unknown` REFUSES. A task whose tracker may or may not hold it for this
        actor is not one a second session can be told about; offline work is
        `NullTracker`, which declares no claim capability at all.
        """
        tracker = self._adapter.tracker
        if TrackerCapability.CLAIM not in tracker.capabilities:
            return
        ref = self._adapter.ref(stage_id)
        result = tracker.apply(Claim(ref=ref, actor=self._actor))
        if isinstance(result, Unknown):
            raise AdmissionRefused(
                MSG_UNKNOWN_CLAIM.format(ref=stage_id, reason=result.reason)
            )
        if isinstance(result, Conflict):
            self._refuse_conflicted_claim(stage_id, result)

    def _refuse_conflicted_claim(self, stage_id: str, result: Conflict) -> None:
        """Refuse a disputed claim, retiring the task its tracker ended (§3.8).

        The two conflicts are not one: an item somebody else HOLDS is a race
        this admission loses and the record stays where it is, while an item
        that has been CLOSED is a decision made outside the engine, and the
        record records it as abandoned-external rather than waiting for a
        claim that will never be granted.
        """
        if result.observed is not None and (
            result.observed.status is WorkItemStatus.CLOSED
        ):
            self._adapter.abandon_external(stage_id, result.reason)
            raise AdmissionRefused(MSG_CLOSED_ELSEWHERE.format(ref=stage_id))
        raise AdmissionRefused(
            MSG_CONFLICT_CLAIM.format(ref=stage_id, reason=result.reason)
        )

    def _release_stranded(self, stage_id: str, stored: ContractorRecord | None) -> None:
        """Free a claim a crash inside §3.4's window left behind.

        The detection lives on the adapter, because `wf ledger reconcile` is
        the other repair path §3.4 names and the two must not drift; `stored`
        is already in hand here, so the cheap answer is given first.
        """
        if stored is None or stored.state is not ContractorState.PREPARED:
            return
        self._adapter.release_stranded_claim(stage_id, self._actor)

    def admit(
        self, epic_id: str, stage_id: str, target_ref: str, expected_base_commit: str
    ) -> ContractorRecord:
        """Recover or complete durable admission for the named open stage."""
        return self._admit(
            epic_id,
            stage_id,
            target_ref,
            expected_base_commit,
            successor=None,
        )

    def admit_successor(
        self,
        epic_id: str,
        stage_id: str,
        target_ref: str,
        expected_base_commit: str,
        successor: ContractorRecord,
    ) -> ContractorRecord:
        """Admit the caller-declared next attempt after the retry policy approved it."""
        return self._admit(
            epic_id,
            stage_id,
            target_ref,
            expected_base_commit,
            successor=successor,
        )

    def _admit(
        self,
        epic_id: str,
        stage_id: str,
        target_ref: str,
        expected_base_commit: str,
        *,
        successor: ContractorRecord | None,
    ) -> ContractorRecord:
        """Run the shared validation and convergence path for one declared record."""
        if self._verification_policy is None:
            raise AdmissionRefused("contractor verification policy is missing")
        stored = self._adapter.stored_record(stage_id)
        # The tracker is READ only when this task has no record yet — which is
        # to say, only at prepare (§3.3). Every later admission, including a
        # retry and a recovery, is answered from the ledger, which is what
        # makes admission possible with the tracker gone (R4).
        if stored is None:
            self._selected_stage(epic_id, stage_id)
        self._refuse_other_admission(epic_id, stage_id)
        self._release_stranded(stage_id, stored)
        record = (
            self._record_or_prepare(
                stored,
                epic_id,
                stage_id,
                target_ref,
                expected_base_commit,
            )
            if successor is None
            else self._prepare_successor(
                stored,
                epic_id,
                stage_id,
                target_ref,
                expected_base_commit,
                successor,
            )
        )
        if (
            record.verification_policy is None
            or record.verification_policy != self._verification_policy
        ):
            raise AdmissionRefused("contractor verification policy missing or changed")
        root = self._roots.find(
            record.instance_key, record.root_backend, record.attempt
        )
        if root is None:
            if self._head_commit() != record.expected_base_commit:
                raise AdmissionRefused(MSG_HEAD_MOVED)
            root = self._roots.create(
                record.instance_key, record.root_backend, record.attempt
            )
        self._assert_root(root, record)
        self._roots.ensure_branch(root)
        if record.state is ContractorState.ADMITTED:
            return record
        self._claim(stage_id)
        try:
            return self._adapter.admit(stage_id, record, root_id=root.root_id)
        except (AdmissionRefused, ContractorAdapterError):
            # A ledger-side refusal AFTER the claim: the tracker is holding an
            # item for an admission that did not happen, and only this process
            # knows it (§3.4). A crash cannot run this, which is what
            # `_release_stranded` is for on the next invocation.
            self._adapter.mirror(
                stage_id,
                Claim(ref=self._adapter.ref(stage_id), actor=self._actor, held=False),
            )
            raise

    def _selected_stage(self, epic_id: str, stage_id: str) -> None:
        """Validate the caller-selected open direct child without selecting work.

        Through the port, and only when the tracker can answer: a tracker with
        no `CHILDREN` capability has no hierarchy to contradict the caller, and
        refusing every stage because nothing could list them would make
        `NullTracker` a tracker no run completes under (§3.3, R9).
        """
        tracker = self._adapter.tracker
        if TrackerCapability.CHILDREN not in tracker.capabilities:
            return
        for stage in tracker.children(self._adapter.ref(epic_id)):
            if stage.ref == stage_id and stage.status in (
                WorkItemStatus.OPEN,
                WorkItemStatus.IN_PROGRESS,
            ):
                return
        raise AdmissionRefused(
            MSG_STAGE_NOT_DIRECT.format(stage_id=stage_id, epic_id=epic_id)
        )

    def _refuse_other_admission(self, epic_id: str, stage_id: str) -> None:
        """Prevent one stage from bypassing another unfinished admission (§3.5).

        A ledger query over `retired()`, not the siblings' bead STATUS: the
        record moved into the ledger, so the epic's other tasks are answered
        from `tasks.epic_id` with the tracker unreachable — and "finished" is
        the derived answer rather than whatever label a bead last carried. A
        sibling that landed without a pinned export still blocks, because its
        record is not durable yet; an ABANDONED sibling does not, because it
        never will be (§3.8).
        """
        for other, _state in self._adapter.records.states_of_epic(epic_id):
            if other == stage_id:
                continue
            if not self._adapter.closure.retired(other):
                raise AdmissionRefused(
                    MSG_OTHER_ADMISSION.format(stage_id=other),
                    blocked=True,
                    blocking_ids=(other,),
                )

    def _prepare_successor(
        self,
        stored: ContractorRecord | None,
        epic_id: str,
        stage_id: str,
        target_ref: str,
        expected_base_commit: str,
        successor: ContractorRecord,
    ) -> ContractorRecord:
        """Validate and persist only an explicitly supplied successor intent."""
        if stored is None or (
            successor.epic_id != epic_id
            or successor.stage_id != stage_id
            or successor.target_ref != target_ref
            or successor.expected_base_commit != expected_base_commit
            or successor.state is not ContractorState.PREPARED
        ):
            raise AdmissionRefused(MSG_IDENTITY_CONFLICT)
        return self._adapter.prepare(stage_id, successor)

    def _record_or_prepare(
        self,
        stored: ContractorRecord | None,
        epic_id: str,
        stage_id: str,
        target_ref: str,
        expected_base_commit: str,
    ) -> ContractorRecord:
        """Read a matching intent or persist attempt one's complete record."""
        if stored is None:
            if self._task_brief is None:
                raise AdmissionRefused(MSG_BRIEF_REQUIRED.format(stage_id=stage_id))
            prepared = ContractorRecord.prepared(
                epic_id=epic_id,
                stage_id=stage_id,
                attempt=1,
                target_ref=target_ref,
                expected_base_commit=expected_base_commit,
                verification_policy=self._verification_policy,
                root_backend=self._root_backend,
                blockers_checked=self._blockers_checked,
            )
            return self._adapter.prepare(stage_id, prepared, brief=self._task_brief)
        record = stored
        if (
            record.verification_policy is None
            or record.verification_policy != self._verification_policy
            or record.epic_id != epic_id
            or record.stage_id != stage_id
            or record.target_ref != target_ref
            or record.expected_base_commit != expected_base_commit
            or record.state not in (ContractorState.PREPARED, ContractorState.ADMITTED)
        ):
            raise AdmissionRefused(MSG_IDENTITY_CONFLICT)
        return record

    @staticmethod
    def _assert_root(root: ContractorRoot, record: ContractorRecord) -> None:
        """Reject a root that does not prove the prepared identity."""
        if (
            root.instance_key != record.instance_key
            or root.instance_base_commit != record.expected_base_commit
            or (record.root_id is not None and record.root_id != root.root_id)
        ):
            raise AdmissionRefused(MSG_IDENTITY_CONFLICT)
