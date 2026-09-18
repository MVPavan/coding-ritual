"""Durable prepare-to-admit recovery for one selected phase stage."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.bdio.records import RootRecord
from workflow_interpreter.bdio.wire import BeadRecord
from workflow_interpreter.contractor.adapter import ContractorAdapter
from workflow_interpreter.contractor.models import ContractorRecord, ContractorState
from workflow_interpreter.contractor.verification import VerificationPolicy
from workflow_interpreter.inspector import INSTANCE_BRANCH_REF
from workflow_interpreter.inspector.gitio import Git

STATUS_OPEN = "open"
STATUS_IN_PROGRESS = "in_progress"
STATUS_CLOSED = "closed"
MSG_STAGE_NOT_DIRECT = "stage {stage_id!r} is not an open direct child of {epic_id!r}"
MSG_OTHER_ADMISSION = "stage {stage_id!r} has unfinished contractor admission"
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
    ) -> None:
        """Pin the backend a first attempt is prepared on before it exists.

        `root_backend` is the `store` switch in force now (§3.2, D18). It is
        used only when THIS call prepares attempt one: a stored record already
        carries its own immutable pin, and admission never overwrites it.
        """
        self._adapter = adapter
        self._roots = roots
        self._head_commit = head_commit
        self._verification_policy = verification_policy
        self._root_backend = root_backend

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
        stage = self._selected_stage(epic_id, stage_id)
        self._refuse_other_admission(epic_id, stage_id)
        record = (
            self._record_or_prepare(
                stage.metadata.get("contractor"),
                epic_id,
                stage_id,
                target_ref,
                expected_base_commit,
            )
            if successor is None
            else self._prepare_successor(
                stage.metadata.get("contractor"),
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
        return self._adapter.admit(stage_id, record, root_id=root.root_id)

    def _selected_stage(self, epic_id: str, stage_id: str) -> BeadRecord:
        """Validate the caller-selected open direct child without selecting work."""
        stages = self._adapter.direct_children(epic_id)
        for stage in stages:
            if stage.id == stage_id and stage.status in (
                STATUS_OPEN,
                STATUS_IN_PROGRESS,
            ):
                return stage
        raise AdmissionRefused(
            MSG_STAGE_NOT_DIRECT.format(stage_id=stage_id, epic_id=epic_id)
        )

    def _refuse_other_admission(self, epic_id: str, stage_id: str) -> None:
        """Prevent one stage from bypassing another persisted admission intent."""
        for stage in self._adapter.direct_children(epic_id):
            if stage.id == stage_id:
                continue
            raw = stage.metadata.get("contractor")
            if raw is None:
                continue
            try:
                ContractorRecord.model_validate(raw)
            except ValueError as error:
                raise AdmissionRefused(MSG_IDENTITY_CONFLICT) from error
            if stage.status != STATUS_CLOSED:
                raise AdmissionRefused(
                    MSG_OTHER_ADMISSION.format(stage_id=stage.id),
                    blocked=True,
                    blocking_ids=(stage.id,),
                )

    def _prepare_successor(
        self,
        raw: object | None,
        epic_id: str,
        stage_id: str,
        target_ref: str,
        expected_base_commit: str,
        successor: ContractorRecord,
    ) -> ContractorRecord:
        """Validate and persist only an explicitly supplied successor intent."""
        if raw is None or (
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
        raw: object | None,
        epic_id: str,
        stage_id: str,
        target_ref: str,
        expected_base_commit: str,
    ) -> ContractorRecord:
        """Read a matching intent or persist attempt one's complete record."""
        if raw is None:
            prepared = ContractorRecord.prepared(
                epic_id=epic_id,
                stage_id=stage_id,
                attempt=1,
                target_ref=target_ref,
                expected_base_commit=expected_base_commit,
                verification_policy=self._verification_policy,
                root_backend=self._root_backend,
            )
            return self._adapter.prepare(stage_id, prepared)
        try:
            record = ContractorRecord.model_validate(raw)
        except ValueError as error:
            raise AdmissionRefused(MSG_IDENTITY_CONFLICT) from error
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
