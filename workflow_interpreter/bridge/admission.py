"""Durable prepare-to-admit recovery for one selected phase stage."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio.records import RootRecord
from workflow_interpreter.bdio.wire import BeadRecord
from workflow_interpreter.bridge.adapter import PhaseAdapter
from workflow_interpreter.bridge.models import PhaseBridgeRecord, PhaseBridgeState
from workflow_interpreter.supervisor import INSTANCE_BRANCH_REF
from workflow_interpreter.supervisor.gitio import Git

STATUS_OPEN = "open"
STATUS_IN_PROGRESS = "in_progress"
STATUS_CLOSED = "closed"
MSG_STAGE_NOT_DIRECT = "stage {stage_id!r} is not an open direct child of {epic_id!r}"
MSG_OTHER_ADMISSION = "stage {stage_id!r} has unfinished bridge admission"
MSG_IDENTITY_CONFLICT = "phase bridge identity conflicts with durable admission"
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


class BridgeRoot(BaseModel):
    """The minimal persisted root identity admission is allowed to relate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    root_id: str
    instance_key: str
    instance_base_commit: str


class RootProvisioner(Protocol):
    """Use existing root convergence and persisted-base branch recovery."""

    def find(self, instance_key: str) -> BridgeRoot | None:
        """Return the uniquely converged root for an instance key."""

    def create(self, instance_key: str) -> BridgeRoot:
        """Create or recover one root through existing raw-record convergence."""

    def ensure_branch(self, root: BridgeRoot) -> None:
        """Restore the root's branch from its persisted base, never current HEAD."""


class WorkflowRootProvisioner:
    """Adapt existing root convergence and branch restoration to admission."""

    def __init__(
        self,
        adapter: PhaseAdapter,
        create_root: Callable[[str], RootRecord],
        git: Git,
        repo_root: Path,
    ) -> None:
        self._adapter = adapter
        self._create_root = create_root
        self._git = git
        self._repo_root = repo_root

    def find(self, instance_key: str) -> BridgeRoot | None:
        """Repair a discovered raw root through the existing convergence path."""
        if not self._adapter.has_root(instance_key):
            return None
        return self._bridge_root(self._create_root(instance_key))

    def create(self, instance_key: str) -> BridgeRoot:
        """Create a root through the existing owner-first convergence path."""
        return self._bridge_root(self._create_root(instance_key))

    def ensure_branch(self, root: BridgeRoot) -> None:
        """Restore a missing branch from the root's persisted base commit."""
        branch = INSTANCE_BRANCH_REF.format(root_id=root.root_id)
        if self._git.ref_target(branch, cwd=self._repo_root) is None:
            self._git.update_ref(branch, root.instance_base_commit, cwd=self._repo_root)

    @staticmethod
    def _bridge_root(root: RootRecord) -> BridgeRoot:
        """Project a fully parsed root into the phase relation's identity fields."""
        base = root.metadata.instance_base_commit
        if base is None:
            raise AdmissionRefused(MSG_IDENTITY_CONFLICT)
        return BridgeRoot(
            root_id=root.root_id,
            instance_key=root.metadata.instance_key,
            instance_base_commit=base,
        )


class PhaseAdmission:
    """Prepare and admit one selected direct-child stage without scheduling it."""

    def __init__(
        self,
        adapter: PhaseAdapter,
        roots: RootProvisioner,
        head_commit: Callable[[], str],
    ) -> None:
        self._adapter = adapter
        self._roots = roots
        self._head_commit = head_commit

    def admit(
        self, epic_id: str, stage_id: str, target_ref: str, expected_base_commit: str
    ) -> PhaseBridgeRecord:
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
        successor: PhaseBridgeRecord,
    ) -> PhaseBridgeRecord:
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
        successor: PhaseBridgeRecord | None,
    ) -> PhaseBridgeRecord:
        """Run the shared validation and convergence path for one declared record."""
        stage = self._selected_stage(epic_id, stage_id)
        self._refuse_other_admission(epic_id, stage_id)
        record = (
            self._record_or_prepare(
                stage.metadata.get("phase_bridge"),
                epic_id,
                stage_id,
                target_ref,
                expected_base_commit,
            )
            if successor is None
            else self._prepare_successor(
                stage.metadata.get("phase_bridge"),
                epic_id,
                stage_id,
                target_ref,
                expected_base_commit,
                successor,
            )
        )
        root = self._roots.find(record.instance_key)
        if root is None:
            if self._head_commit() != record.expected_base_commit:
                raise AdmissionRefused(MSG_HEAD_MOVED)
            root = self._roots.create(record.instance_key)
        self._assert_root(root, record)
        self._roots.ensure_branch(root)
        if record.state is PhaseBridgeState.ADMITTED:
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
            raw = stage.metadata.get("phase_bridge")
            if raw is None:
                continue
            try:
                PhaseBridgeRecord.model_validate(raw)
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
        successor: PhaseBridgeRecord,
    ) -> PhaseBridgeRecord:
        """Validate and persist only an explicitly supplied successor intent."""
        if raw is None or (
            successor.epic_id != epic_id
            or successor.stage_id != stage_id
            or successor.target_ref != target_ref
            or successor.expected_base_commit != expected_base_commit
            or successor.state is not PhaseBridgeState.PREPARED
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
    ) -> PhaseBridgeRecord:
        """Read a matching intent or persist attempt one's complete record."""
        if raw is None:
            prepared = PhaseBridgeRecord.prepared(
                epic_id=epic_id,
                stage_id=stage_id,
                attempt=1,
                target_ref=target_ref,
                expected_base_commit=expected_base_commit,
            )
            return self._adapter.prepare(stage_id, prepared)
        try:
            record = PhaseBridgeRecord.model_validate(raw)
        except ValueError as error:
            raise AdmissionRefused(MSG_IDENTITY_CONFLICT) from error
        if (
            record.epic_id != epic_id
            or record.stage_id != stage_id
            or record.target_ref != target_ref
            or record.expected_base_commit != expected_base_commit
            or record.state
            not in (PhaseBridgeState.PREPARED, PhaseBridgeState.ADMITTED)
        ):
            raise AdmissionRefused(MSG_IDENTITY_CONFLICT)
        return record

    @staticmethod
    def _assert_root(root: BridgeRoot, record: PhaseBridgeRecord) -> None:
        """Reject a root that does not prove the prepared identity."""
        if (
            root.instance_key != record.instance_key
            or root.instance_base_commit != record.expected_base_commit
            or (record.root_id is not None and record.root_id != root.root_id)
        ):
            raise AdmissionRefused(MSG_IDENTITY_CONFLICT)
