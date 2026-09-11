"""The signed, one-shot phase-bridge landing boundary and its recovery."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Final, Protocol

from pydantic import BaseModel, ConfigDict, Field

from workflow_interpreter.bridge.adapter import PhaseAdapter
from workflow_interpreter.bridge.models import PhaseBridgeRecord, PhaseBridgeState
from workflow_interpreter.supervisor.gitio import Git
from workflow_interpreter.supervisor.paths import (
    WrapperPaths,
    read_record,
    record_bytes,
    write_record,
)
from workflow_interpreter.supervisor.verify import VerifyTree

LANDING_SCHEMA: Final[str] = "phase-bridge-landing/1"
LANDING_INTENT_FILE: Final[str] = "phase-bridge-landing.json"
LANDING_RECEIPT_FILE: Final[str] = "phase-bridge-landing-receipt.json"
SHIP_GATE: Final[str] = "ship"
T1_MESSAGE: Final[str] = (
    "T1: landing-gate code is trusted candidate-controlled code; it may alter "
    "host-visible refs, receipts, or filesystem state and is not contained."
)
MSG_BRANCH_MOVED: Final[str] = "halted: branch-moved"
MSG_HUMAN_ATTENTION: Final[str] = "halted: human-attention"
MSG_GATE_MISMATCH: Final[str] = "immutable ship-gate evidence does not match landing"
MSG_REPOSITORY_GATE: Final[str] = "repository gate is incomplete, red, or mismatched"
MSG_IDENTITY: Final[str] = "landing intent and stage relation are ambiguous"


class LandingDisposition(StrEnum):
    """The closed outcomes of a one-shot landing or its recovery."""

    CLOSED = "closed"
    BRANCH_MOVED = "branch-moved"
    HUMAN_ATTENTION = "human-attention"
    NO_INTENT = "no-intent"


class ReceiptClosureState(StrEnum):
    """The receipt state written before a stage's final close."""

    PENDING = "pending"


class GateEvidence(BaseModel):
    """One re-verified accepted immutable ship-gate observation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    root_id: str
    gate_node: str
    closed: bool
    immutable: bool
    accepted: bool
    artifact_oid: str
    tree: str
    fingerprint: str
    digest: str
    artifact_ref: str


class RepositoryGateResult(BaseModel):
    """The complete, green repository-gate result for one artifact tree."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_oid: str
    tree: str
    complete: bool
    green: bool
    results: tuple[str, ...] = Field(min_length=1)


class LandingIntent(BaseModel):
    """The durable old-or-new record written before a target ref can move."""

    model_config = ConfigDict(
        frozen=True, extra="forbid", populate_by_name=True, serialize_by_alias=True
    )

    schema_version: str = Field(
        default=LANDING_SCHEMA, alias="schema", serialization_alias="schema"
    )
    ref: str
    expected_base: str
    artifact_oid: str
    tree: str
    gate_receipt_digest: str
    stage: str
    attempt: int = Field(ge=1)


class LandingReceipt(BaseModel):
    """The durable pre-close evidence for a completed landing boundary."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    intent_digest: str
    ref: str
    expected_base: str
    signed_oid: str
    landed_oid: str
    tree: str
    gate_receipt_digest: str
    repository_gate_results: tuple[str, ...]
    closure_state: ReceiptClosureState = ReceiptClosureState.PENDING


class LandingResult(BaseModel):
    """The operator-visible result of a landing boundary operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    disposition: LandingDisposition
    intent: LandingIntent | None = None
    observed_target: str | None = None


class GateAuthority(Protocol):
    """Re-verify the immutable human gate before landing or recovery."""

    def verify(self, root_id: str) -> GateEvidence:
        """Return evidence only after payload and signature verification."""


class RepositoryGate(Protocol):
    """Grade one candidate artifact in its detached, clean checkout."""

    def verify(self, artifact_oid: str, tree: str) -> RepositoryGateResult:
        """Return only a complete green result naming that artifact and tree."""


class DetachedRepositoryGate:
    """Run a repository gate only in the clean detached candidate checkout."""

    def __init__(
        self,
        git: Git,
        paths: WrapperPaths,
        checks: Callable[[Path, str], tuple[str, ...]],
        operator_output: Callable[[str], None],
    ) -> None:
        self._git = git
        self._paths = paths
        self._checks = checks
        self._operator_output = operator_output

    def verify(self, artifact_oid: str, tree: str) -> RepositoryGateResult:
        """Grade the signed commit only after making T1 visible to its operator."""
        if self._git.tree_oid(artifact_oid, cwd=self._paths.config.repo_root) != tree:
            raise ValueError(MSG_REPOSITORY_GATE)
        self._operator_output(T1_MESSAGE)
        with VerifyTree(self._git, self._paths, artifact_oid) as checkout:
            results = self._checks(checkout, artifact_oid)
        return RepositoryGateResult(
            artifact_oid=artifact_oid,
            tree=tree,
            complete=True,
            green=True,
            results=results,
        )


class LandingHooks:
    """Provide test-only composition seams around the durable landing boundary."""

    def after_cas(self) -> None:
        """Observe the post-CAS, pre-receipt crash window without changing production."""


class PhaseLanding:
    """Land one signed fast-forward and recover only its unfinished closure."""

    def __init__(
        self,
        adapter: PhaseAdapter,
        git: Git,
        repo_root: Path,
        paths: WrapperPaths,
        gate_authority: GateAuthority,
        repository_gate: RepositoryGate,
        *,
        hooks: LandingHooks | None = None,
    ) -> None:
        self._adapter = adapter
        self._git = git
        self._repo_root = repo_root
        self._paths = paths
        self._gate_authority = gate_authority
        self._repository_gate = repository_gate
        self._hooks = hooks or LandingHooks()

    def land(self, stage_id: str) -> LandingResult:
        """Execute the one allowed CAS after all landing evidence is green."""
        record = self._adapter.record(stage_id)
        if record.state in (PhaseBridgeState.LANDED, PhaseBridgeState.CLOSED):
            return self.recover(stage_id)
        if record.state not in (PhaseBridgeState.ADMITTED, PhaseBridgeState.LANDING):
            return LandingResult(disposition=LandingDisposition.HUMAN_ATTENTION)
        evidence = self._gate_evidence(record)
        observed_target = self._git.ref_target(record.target_ref, cwd=self._repo_root)
        if observed_target != record.expected_base_commit:
            return LandingResult(
                disposition=LandingDisposition.BRANCH_MOVED,
                observed_target=observed_target,
            )
        if not self._git.is_ancestor(
            record.expected_base_commit, evidence.artifact_oid, cwd=self._repo_root
        ):
            return LandingResult(disposition=LandingDisposition.HUMAN_ATTENTION)
        repository_gate = self._repository_gate.verify(
            evidence.artifact_oid, evidence.tree
        )
        if not self._repository_gate_matches(repository_gate, evidence):
            return LandingResult(disposition=LandingDisposition.HUMAN_ATTENTION)
        intent = LandingIntent(
            ref=record.target_ref,
            expected_base=record.expected_base_commit,
            artifact_oid=evidence.artifact_oid,
            tree=evidence.tree,
            gate_receipt_digest=evidence.digest,
            stage=record.stage_id,
            attempt=record.attempt,
        )
        self._write_intent(intent)
        if not self._git.update_ref_cas(
            intent.ref, intent.artifact_oid, intent.expected_base, cwd=self._repo_root
        ):
            return LandingResult(
                disposition=LandingDisposition.BRANCH_MOVED,
                intent=intent,
                observed_target=self._git.ref_target(intent.ref, cwd=self._repo_root),
            )
        self._hooks.after_cas()
        return self._finish(record, intent, repository_gate)

    def recover(self, stage_id: str) -> LandingResult:
        """Reconcile an unfinished intent without ever moving a target ref."""
        intent = read_record(self._intent_path(), LandingIntent)
        if intent is None:
            return LandingResult(disposition=LandingDisposition.NO_INTENT)
        record = self._adapter.record(stage_id)
        if not self._identity_matches(record, intent):
            return LandingResult(
                disposition=LandingDisposition.HUMAN_ATTENTION, intent=intent
            )
        evidence = self._gate_evidence(record)
        if not self._intent_matches_gate(intent, evidence):
            return LandingResult(
                disposition=LandingDisposition.HUMAN_ATTENTION, intent=intent
            )
        repository_gate = self._repository_gate.verify(intent.artifact_oid, intent.tree)
        if not self._repository_gate_matches(repository_gate, evidence):
            return LandingResult(
                disposition=LandingDisposition.HUMAN_ATTENTION, intent=intent
            )
        observed_target = self._git.ref_target(intent.ref, cwd=self._repo_root)
        if observed_target == intent.expected_base:
            return LandingResult(
                disposition=LandingDisposition.HUMAN_ATTENTION,
                intent=intent,
                observed_target=observed_target,
            )
        if observed_target is None or not self._git.is_ancestor(
            intent.artifact_oid, observed_target, cwd=self._repo_root
        ):
            return LandingResult(
                disposition=LandingDisposition.HUMAN_ATTENTION,
                intent=intent,
                observed_target=observed_target,
            )
        return self._finish(record, intent, repository_gate)

    def _finish(
        self,
        record: PhaseBridgeRecord,
        intent: LandingIntent,
        repository_gate: RepositoryGateResult,
    ) -> LandingResult:
        """Write receipt, relation, and close in their required durable order."""
        receipt = self._receipt(intent, repository_gate)
        receipt_digest = _digest_record(receipt)
        existing = read_record(self._receipt_path(), LandingReceipt)
        if existing is None:
            write_record(self._receipt_path(), receipt)
        elif not self._receipt_identity_matches(existing, receipt):
            return LandingResult(
                disposition=LandingDisposition.HUMAN_ATTENTION, intent=intent
            )
        else:
            receipt_digest = _digest_record(existing)
        landed = (
            record
            if record.state is PhaseBridgeState.CLOSED
            else record.landed(
                intent.artifact_oid,
                intent.tree,
                intent.gate_receipt_digest,
                receipt_digest,
            )
        )
        if landed.state is not PhaseBridgeState.CLOSED:
            self._adapter.land(record.stage_id, landed)
            landed = landed.closed()
        self._adapter.close(record.stage_id, landed, receipt_digest)
        return LandingResult(disposition=LandingDisposition.CLOSED, intent=intent)

    def _gate_evidence(self, record: PhaseBridgeRecord) -> GateEvidence:
        """Require the re-verified ship decision to agree with the stage root."""
        if record.root_id is None:
            raise ValueError(MSG_IDENTITY)
        evidence = self._gate_authority.verify(record.root_id)
        if (
            evidence.root_id != record.root_id
            or evidence.gate_node != SHIP_GATE
            or not evidence.closed
            or not evidence.immutable
            or not evidence.accepted
            or evidence.artifact_ref != evidence.artifact_oid
        ):
            raise ValueError(MSG_GATE_MISMATCH)
        return evidence

    @staticmethod
    def _repository_gate_matches(
        repository_gate: RepositoryGateResult, evidence: GateEvidence
    ) -> bool:
        """Require a complete repository result for the signed artifact itself."""
        return (
            bool(repository_gate.results)
            and repository_gate.complete
            and repository_gate.green
            and repository_gate.artifact_oid == evidence.artifact_oid
            and repository_gate.tree == evidence.tree
        )

    @staticmethod
    def _identity_matches(record: PhaseBridgeRecord, intent: LandingIntent) -> bool:
        """Reject a recovery whose stage journal cannot identify one attempt."""
        return (
            record.stage_id == intent.stage
            and record.attempt == intent.attempt
            and record.target_ref == intent.ref
            and record.expected_base_commit == intent.expected_base
            and record.root_id is not None
            and record.state
            in (
                PhaseBridgeState.ADMITTED,
                PhaseBridgeState.LANDED,
                PhaseBridgeState.CLOSED,
            )
        )

    @staticmethod
    def _intent_matches_gate(intent: LandingIntent, evidence: GateEvidence) -> bool:
        """Keep recovery bound to the same signed artifact and immutable gate digest."""
        return (
            intent.artifact_oid == evidence.artifact_oid
            and intent.tree == evidence.tree
            and intent.gate_receipt_digest == evidence.digest
        )

    @staticmethod
    def _receipt_identity_matches(
        existing: LandingReceipt, receipt: LandingReceipt
    ) -> bool:
        """Compare only receipt fields derived from the immutable landing intent."""
        return (
            existing.intent_digest == receipt.intent_digest
            and existing.ref == receipt.ref
            and existing.expected_base == receipt.expected_base
            and existing.signed_oid == receipt.signed_oid
            and existing.landed_oid == receipt.landed_oid
            and existing.tree == receipt.tree
            and existing.gate_receipt_digest == receipt.gate_receipt_digest
        )

    def _write_intent(self, intent: LandingIntent) -> None:
        """Persist and immediately read back the pre-CAS intent."""
        write_record(self._intent_path(), intent)
        if read_record(self._intent_path(), LandingIntent) != intent:
            raise ValueError(MSG_IDENTITY)

    def _intent_path(self) -> Path:
        """Locate this root's one landing intent record."""
        return self._paths.instance_dir / LANDING_INTENT_FILE

    def _receipt_path(self) -> Path:
        """Locate this root's one durable pre-close landing receipt."""
        return self._paths.instance_dir / LANDING_RECEIPT_FILE

    @staticmethod
    def _receipt(
        intent: LandingIntent, repository_gate: RepositoryGateResult
    ) -> LandingReceipt:
        """Build the receipt whose digest is named by the subsequent stage close."""
        return LandingReceipt(
            intent_digest=_digest_record(intent),
            ref=intent.ref,
            expected_base=intent.expected_base,
            signed_oid=intent.artifact_oid,
            landed_oid=intent.artifact_oid,
            tree=intent.tree,
            gate_receipt_digest=intent.gate_receipt_digest,
            repository_gate_results=repository_gate.results,
        )


def _digest_record(record: BaseModel) -> str:
    """Return the stable digest named by dependent durable evidence."""
    return hashlib.sha256(record_bytes(record)).hexdigest()
