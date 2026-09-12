"""The signed, one-shot phase-bridge landing boundary and its recovery."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from workflow_interpreter.bridge.adapter import PhaseAdapter
from workflow_interpreter.bridge.errors import BridgeRefusal
from workflow_interpreter.bridge.models import PhaseBridgeRecord, PhaseBridgeState
from workflow_interpreter.bridge.verification import (
    CheckResult,
    VerificationPolicy,
    observe_checks,
)
from workflow_interpreter.foreman.identifiers import validate_bead_id
from workflow_interpreter.supervisor.gitcmd import GitSubcommand
from workflow_interpreter.supervisor.gitio import Git
from workflow_interpreter.supervisor.paths import (
    WrapperPaths,
    read_record,
    record_bytes,
    write_record,
)
from workflow_interpreter.supervisor.verify import VerifyTree

LANDING_SCHEMA: Final = "phase-bridge-landing/2"
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
    PENDING = "pending"


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


class RepositoryGateResult(BaseModel):
    """The complete, green repository-gate result for one artifact tree."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_oid: str
    tree: str
    complete: bool
    green: bool
    policy_digest: str
    results: tuple[CheckResult, ...] = Field(min_length=1)


class LandingIntent(BaseModel):
    """The durable old-or-new record written before a target ref can move."""

    model_config = ConfigDict(
        frozen=True, extra="forbid", populate_by_name=True, serialize_by_alias=True
    )

    schema_version: Literal["phase-bridge-landing/2"] = Field(
        default=LANDING_SCHEMA, alias="schema", serialization_alias="schema"
    )
    ref: str
    expected_base: str
    artifact_oid: str
    tree: str
    gate_receipt_digest: str
    root_id: str
    policy_digest: str
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
    policy_digest: str
    repository_gate_results: tuple[CheckResult, ...]
    closure_state: ReceiptClosureState = ReceiptClosureState.PENDING


class LandingResult(BaseModel):
    """The operator-visible result of a landing boundary operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    disposition: LandingDisposition
    intent: LandingIntent | None = None
    observed_target: str | None = None
    reason: str | None = None
    next_action: str | None = None


class GateAuthority(Protocol):
    """Read authenticated immutable gate closure before landing or recovery."""

    def verify(self, root_id: str) -> GateEvidence:
        """Return evidence from existing authenticated closure marks and graph pins."""


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
        checks: VerificationPolicy,
        operator_output: Callable[[str], None],
    ) -> None:
        self._git = git
        self._paths = paths
        if not isinstance(checks, VerificationPolicy):
            raise TypeError("repository verification requires a pinned nonempty policy")
        self._checks = checks
        self._operator_output = operator_output

    def verify(self, artifact_oid: str, tree: str) -> RepositoryGateResult:
        """Grade the signed commit only after making T1 visible to its operator."""
        if self._git.tree_oid(artifact_oid, cwd=self._paths.config.repo_root) != tree:
            raise BridgeRefusal(MSG_REPOSITORY_GATE)
        self._operator_output(T1_MESSAGE)
        with VerifyTree(self._git, self._paths, artifact_oid) as checkout:
            results = observe_checks(
                self._checks, self._git, checkout, artifact_oid, tree
            )
        return RepositoryGateResult(
            artifact_oid=artifact_oid,
            tree=tree,
            complete=len(results) == len(self._checks.checks),
            green=self._checks.matches(results),
            policy_digest=self._checks.digest,
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
        if self._intent_path().exists() or record.state in (
            PhaseBridgeState.LANDED,
            PhaseBridgeState.CLOSED,
        ):
            return self.recover(stage_id)
        if record.state not in (PhaseBridgeState.ADMITTED, PhaseBridgeState.LANDING):
            return LandingResult(
                disposition=LandingDisposition.HUMAN_ATTENTION,
                reason="stage is not eligible for fresh landing",
            )
        reason = self._coordinator_refusal(record.target_ref)
        if reason:
            return LandingResult(
                disposition=LandingDisposition.HUMAN_ATTENTION, reason=reason
            )
        evidence = self._gate_evidence(record)
        observed_target = self._git.ref_target(record.target_ref, cwd=self._repo_root)
        if observed_target != record.expected_base_commit:
            return LandingResult(
                disposition=LandingDisposition.BRANCH_MOVED,
                observed_target=observed_target,
                reason="target no longer equals the admitted base",
            )
        if not self._git.is_ancestor(
            record.expected_base_commit, evidence.artifact_oid, cwd=self._repo_root
        ):
            return LandingResult(
                disposition=LandingDisposition.HUMAN_ATTENTION,
                reason="approved artifact does not descend from the admitted base",
            )
        repository_gate = self._repository_gate.verify(
            evidence.artifact_oid, evidence.tree
        )
        if not self._repository_gate_matches(repository_gate, evidence, record):
            self._adapter.gate_red(stage_id, record)
            return LandingResult(
                disposition=LandingDisposition.HUMAN_ATTENTION,
                reason=MSG_REPOSITORY_GATE,
            )
        intent = LandingIntent(
            root_id=self._paths.root_id,
            policy_digest=self._policy(record).digest,
            ref=record.target_ref,
            expected_base=record.expected_base_commit,
            artifact_oid=evidence.artifact_oid,
            tree=evidence.tree,
            gate_receipt_digest=evidence.digest,
            stage=record.stage_id,
            attempt=record.attempt,
        )
        return self._cas(record, intent, repository_gate)

    def _cas(
        self,
        record: PhaseBridgeRecord,
        intent: LandingIntent,
        repository_gate: RepositoryGateResult,
    ) -> LandingResult:
        """Move the ref only for fresh landing or an explicit operator retry."""
        from contextlib import nullcontext

        guard = self._adapter.integration_guard
        if record.integration_digest is not None and guard is None:
            raise BridgeRefusal("integration requires runtime guard")
        from workflow_interpreter.foreman.replacement import bridge_landing_locks

        context = (
            guard.ordered(guard.association(record))
            if record.integration_digest is not None and guard is not None
            else bridge_landing_locks(guard.composition, record)
            if guard is not None
            else nullcontext()
        )
        with context:
            self._adapter.guard_integration(record)
            if record.integration_digest is not None and guard is not None:
                guard.pre_cas(record)
            self._write_intent(intent)
            reason = self._coordinator_refusal(intent.ref)
            if reason:
                return LandingResult(
                    disposition=LandingDisposition.HUMAN_ATTENTION,
                    intent=intent,
                    reason=reason,
                )
            if not self._git.update_ref_cas(
                intent.ref,
                intent.artifact_oid,
                intent.expected_base,
                cwd=self._repo_root,
            ):
                return LandingResult(
                    disposition=LandingDisposition.BRANCH_MOVED,
                    intent=intent,
                    observed_target=self._git.ref_target(
                        intent.ref, cwd=self._repo_root
                    ),
                    reason="target moved before landing compare-and-swap",
                )
        self._hooks.after_cas()
        return self._finish(record, intent, repository_gate)

    def _authorized_intent(
        self, record: PhaseBridgeRecord
    ) -> tuple[LandingIntent, GateEvidence]:
        """Revalidate the durable journal and its authenticated artifact authority."""
        self._policy(record)
        intent = read_record(self._intent_path(), LandingIntent)
        if intent is None:
            raise BridgeRefusal("landing intent is missing")
        if not self._identity_matches(record, intent):
            raise BridgeRefusal(MSG_IDENTITY)
        evidence = self._gate_evidence(record)
        if not self._intent_matches_gate(intent, evidence):
            raise BridgeRefusal(MSG_GATE_MISMATCH)
        if not self._git.is_ancestor(
            intent.expected_base, intent.artifact_oid, cwd=self._repo_root
        ):
            raise BridgeRefusal(
                "intent artifact is not a fast-forward from the admitted base"
            )
        if self._git.tree_oid(intent.artifact_oid, cwd=self._repo_root) != intent.tree:
            raise BridgeRefusal(MSG_GATE_MISMATCH)
        return intent, evidence

    def retry_landing(self, stage_id: str) -> LandingResult:
        """Explicitly retry the same pending intent; never admit or run agents."""
        record = self._adapter.record(stage_id)
        if record.state is not PhaseBridgeState.ADMITTED:
            raise BridgeRefusal(
                "--retry-landing requires an admitted pending intent, not landed work"
            )
        intent, evidence = self._authorized_intent(record)
        if read_record(self._receipt_path(), LandingReceipt) is not None:
            raise BridgeRefusal("--retry-landing refuses an existing landing receipt")
        observed = self._git.ref_target(intent.ref, cwd=self._repo_root)
        if observed != intent.expected_base:
            return LandingResult(
                disposition=LandingDisposition.BRANCH_MOVED,
                intent=intent,
                observed_target=observed,
                reason="explicit landing retry requires the exact original target base",
            )
        reason = self._coordinator_refusal(intent.ref)
        if reason:
            return LandingResult(
                disposition=LandingDisposition.HUMAN_ATTENTION,
                intent=intent,
                reason=reason,
            )
        results = self._repository_gate.verify(intent.artifact_oid, intent.tree)
        if not self._repository_gate_matches(results, evidence, record):
            return LandingResult(
                disposition=LandingDisposition.HUMAN_ATTENTION,
                intent=intent,
                reason=MSG_REPOSITORY_GATE,
            )
        # Checks are trusted T1 code, but may have changed the journal or stage.
        current = self._adapter.record(stage_id)
        if current != record or self._authorized_intent(current)[0] != intent:
            raise BridgeRefusal(MSG_IDENTITY)
        return self._cas(record, intent, results)

    def recover(self, stage_id: str) -> LandingResult:
        """Reconcile an unfinished intent without ever moving a target ref."""
        record = self._adapter.record(stage_id)
        self._policy(record)
        if not self._intent_path().exists():
            return LandingResult(
                disposition=LandingDisposition.NO_INTENT,
                reason="landing intent is missing",
            )
        intent, evidence = self._authorized_intent(record)
        if (
            record.state is PhaseBridgeState.CLOSED
            and self._adapter.show(stage_id).status == "closed"
        ):
            return self._historical(record, intent, evidence)
        observed_target = self._git.ref_target(intent.ref, cwd=self._repo_root)
        if observed_target == intent.expected_base:
            if (
                record.state is not PhaseBridgeState.ADMITTED
                or self._receipt_path().exists()
            ):
                return LandingResult(
                    disposition=LandingDisposition.HUMAN_ATTENTION,
                    intent=intent,
                    observed_target=observed_target,
                    reason="target is at the old base but durable landing evidence exists; landing retry is not eligible",
                )
            return LandingResult(
                disposition=LandingDisposition.PENDING,
                intent=intent,
                observed_target=observed_target,
                reason="intent is pending at the original base; default recovery moves no ref",
                next_action="--retry-landing",
            )
        if observed_target is None or not self._git.is_ancestor(
            intent.artifact_oid, observed_target, cwd=self._repo_root
        ):
            return LandingResult(
                disposition=LandingDisposition.HUMAN_ATTENTION,
                intent=intent,
                observed_target=observed_target,
                reason="target does not contain the approved artifact",
            )
        repository_gate = self._repository_gate.verify(intent.artifact_oid, intent.tree)
        if not self._repository_gate_matches(repository_gate, evidence, record):
            return LandingResult(
                disposition=LandingDisposition.HUMAN_ATTENTION,
                intent=intent,
                reason=MSG_REPOSITORY_GATE,
            )
        return self._finish(record, intent, repository_gate)

    def _historical(
        self, record: PhaseBridgeRecord, intent: LandingIntent, evidence: GateEvidence
    ) -> LandingResult:
        """Validate historical completion without executing old host tools."""
        self._adapter.guard_integration(record, post_cas=True)
        if (
            record.integration_digest is not None
            and self._adapter.integration_guard is not None
        ):
            self._adapter.integration_guard.finished(record)
        receipt = read_record(self._receipt_path(), LandingReceipt)
        if receipt is None:
            raise BridgeRefusal("closed stage is missing its landing receipt")
        result = RepositoryGateResult(
            artifact_oid=intent.artifact_oid,
            tree=intent.tree,
            policy_digest=receipt.policy_digest,
            complete=True,
            green=True,
            results=receipt.repository_gate_results,
        )
        if (
            not self._repository_gate_matches(result, evidence, record)
            or not self._receipt_identity_matches(
                receipt, self._receipt(intent, result)
            )
            or not self._relation_matches(record, intent, _digest_record(receipt))
        ):
            raise BridgeRefusal(
                "closed relation, policy, intent and receipt do not correspond"
            )
        return LandingResult(
            disposition=LandingDisposition.CLOSED,
            intent=intent,
            reason="validated historical completion",
        )

    @staticmethod
    def _relation_matches(
        record: PhaseBridgeRecord, intent: LandingIntent, digest: str
    ) -> bool:
        """A persisted landed/closed relation must name exactly this receipt."""
        return (
            record.landing_receipt_digest == digest
            and record.landed_oid == intent.artifact_oid
            and record.tree == intent.tree
            and record.gate_receipt_digest == intent.gate_receipt_digest
        )

    def _coordinator_refusal(self, target_ref: str) -> str | None:
        """Preserve the attached coordinator identity before any authorized CAS."""
        if self._git.attached_branch_ref(cwd=self._repo_root) != target_ref:
            return "coordinator must be attached to the admitted target ref"
        if self._git.status_paths(cwd=self._repo_root):
            return "coordinator has staged, unstaged or untracked changes; preserve or repair them before retry"
        return None

    def _finish(
        self,
        record: PhaseBridgeRecord,
        intent: LandingIntent,
        repository_gate: RepositoryGateResult,
    ) -> LandingResult:
        """Write receipt, relation, and close in their required durable order."""
        self._adapter.guard_integration(record, post_cas=True)
        sync_reason = self._sync_checkout(intent)
        if sync_reason:
            return LandingResult(
                disposition=LandingDisposition.HUMAN_ATTENTION,
                intent=intent,
                reason=sync_reason,
                observed_target=self._git.ref_target(intent.ref, cwd=self._repo_root),
            )
        receipt = self._receipt(intent, repository_gate)
        receipt_digest = _digest_record(receipt)
        existing = read_record(self._receipt_path(), LandingReceipt)
        if existing is None:
            write_record(self._receipt_path(), receipt)
        elif not self._receipt_identity_matches(existing, receipt):
            return LandingResult(
                disposition=LandingDisposition.HUMAN_ATTENTION,
                intent=intent,
                reason="persisted receipt differs from the authorized intent or observed policy results",
            )
        else:
            receipt_digest = _digest_record(existing)
        if record.state in (
            PhaseBridgeState.LANDED,
            PhaseBridgeState.CLOSED,
        ) and not self._relation_matches(record, intent, receipt_digest):
            raise BridgeRefusal(
                "persisted landed relation does not match landing receipt digest or artifact"
            )
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
        self._policy(record)
        if record.root_id is None:
            raise BridgeRefusal(MSG_IDENTITY)
        evidence = self._gate_authority.verify(record.root_id)
        if (
            evidence.root_id != record.root_id
            or evidence.gate_node != SHIP_GATE
            or not evidence.closed
            or not evidence.immutable
            or not evidence.accepted
        ):
            raise BridgeRefusal(MSG_GATE_MISMATCH)
        return evidence

    @staticmethod
    def _repository_gate_matches(
        repository_gate: RepositoryGateResult,
        evidence: GateEvidence,
        record: PhaseBridgeRecord,
    ) -> bool:
        """Require a complete repository result for the signed artifact itself."""
        return (
            record.verification_policy is not None
            and repository_gate.policy_digest == record.verification_policy.digest
            and record.verification_policy.matches(repository_gate.results)
            and repository_gate.complete
            and repository_gate.green
            and repository_gate.artifact_oid == evidence.artifact_oid
            and repository_gate.tree == evidence.tree
        )

    @staticmethod
    def _identity_matches(record: PhaseBridgeRecord, intent: LandingIntent) -> bool:
        """Reject a recovery whose stage journal cannot identify one attempt."""
        return (
            record.root_id == intent.root_id
            and record.verification_policy is not None
            and record.verification_policy.digest == intent.policy_digest
            and record.stage_id == intent.stage
            and record.attempt == intent.attempt
            and record.target_ref == intent.ref
            and record.expected_base_commit == intent.expected_base
            and record.root_id is not None
            and record.state
            in (
                PhaseBridgeState.ADMITTED,
                PhaseBridgeState.LANDING,
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
            existing.policy_digest == receipt.policy_digest
            and existing.repository_gate_results == receipt.repository_gate_results
            and existing.intent_digest == receipt.intent_digest
            and existing.ref == receipt.ref
            and existing.expected_base == receipt.expected_base
            and existing.signed_oid == receipt.signed_oid
            and existing.landed_oid == receipt.landed_oid
            and existing.tree == receipt.tree
            and existing.gate_receipt_digest == receipt.gate_receipt_digest
        )

    def _sync_checkout(self, intent: LandingIntent) -> str | None:
        """Bring a clean old checkout forward without resetting refs or user edits."""
        if self._git.attached_branch_ref(cwd=self._repo_root) != intent.ref:
            return f"coordinator must return to admitted branch {intent.ref}; no checkout files changed"
        dirty = self._git.status_paths(cwd=self._repo_root)
        if not dirty:
            return None
        if self._git.ref_target(intent.ref, cwd=self._repo_root) != intent.artifact_oid:
            return "coordinator target differs from intent artifact; preserve current checkout"
        old_tree = self._git.tree_oid(intent.expected_base, cwd=self._repo_root)
        if (
            self._git.run(GitSubcommand.WRITE_TREE, cwd=self._repo_root).text
            != old_tree
        ):
            return "coordinator index differs from original base; preserve staged changes before recovery"
        if self._git.run(
            GitSubcommand.DIFF,
            "--quiet",
            "--no-ext-diff",
            "--no-textconv",
            intent.expected_base,
            "--",
            cwd=self._repo_root,
            check=False,
            config=self._git.filter_overrides(cwd=self._repo_root),
        ).returncode:
            return "coordinator tracked files differ from original base; preserve unstaged changes before recovery"
        if any(not tracked for _, tracked in dirty):
            return "coordinator has untracked files; preserve them before recovery"
        result = self._git.run(
            GitSubcommand.READ_TREE,
            "-m",
            "-u",
            intent.expected_base,
            intent.artifact_oid,
            cwd=self._repo_root,
            check=False,
            config=self._git.filter_overrides(cwd=self._repo_root),
        )
        if result.returncode or self._git.status_paths(cwd=self._repo_root):
            return "checkout changed during synchronization; preserve local changes and retry recovery"
        return None

    def _policy(self, record: PhaseBridgeRecord) -> VerificationPolicy:
        """Old journals and a different root directory cannot confer authority."""
        try:
            validate_bead_id(self._paths.root_id)
        except ValueError as error:
            raise BridgeRefusal(str(error)) from error
        if (
            self._paths.instance_dir.resolve()
            != self._paths.config.wrapper_root.resolve() / self._paths.root_id
        ):
            raise BridgeRefusal(MSG_IDENTITY)
        if (
            record.root_id != self._paths.root_id
            or self._repo_root != self._paths.config.repo_root
        ):
            raise BridgeRefusal(MSG_IDENTITY)
        if self._adapter.integration_guard is not None:
            from workflow_interpreter.foreman.replacement import guard_bridge

            guard_bridge(self._adapter.integration_guard.composition, record)
        elif record.successor_key is not None:
            raise BridgeRefusal("successor requires runtime guard")
        if record.verification_policy is None:
            raise BridgeRefusal(
                "legacy bridge journal lacks verification policy; human attention required"
            )
        return record.verification_policy

    def _write_intent(self, intent: LandingIntent) -> None:
        """Persist and immediately read back the pre-CAS intent."""
        existing = read_record(self._intent_path(), LandingIntent)
        if existing is not None and existing != intent:
            raise BridgeRefusal(MSG_IDENTITY)
        write_record(self._intent_path(), intent)
        if read_record(self._intent_path(), LandingIntent) != intent:
            raise BridgeRefusal(MSG_IDENTITY)

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
            policy_digest=intent.policy_digest,
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
