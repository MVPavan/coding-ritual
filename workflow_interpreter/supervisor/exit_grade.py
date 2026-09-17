"""Host-only §7 evidence computation, independent of RPC completion records."""

from __future__ import annotations

from pathlib import Path
from typing import Final

import structlog
from pydantic import BaseModel

from workflow_interpreter.bdio import (
    ActivationRecord,
    ArtifactIdentity,
    Evidence,
    ExitRecord,
    Outcome,
    VerifyOutcome,
)
from workflow_interpreter.bdio.carriers import LedgerRenderBinding
from workflow_interpreter.contracts.run_identity import RunIdentity
from workflow_interpreter.schema.models import JUDGMENT_OUTCOME, Node
from workflow_interpreter.supervisor.channels import (
    REASON_EFFECTS,
    REASON_MARKER_ABSENT,
    path_allowed,
)
from workflow_interpreter.supervisor.errors import SupervisorError
from workflow_interpreter.supervisor.gitio import Git
from workflow_interpreter.supervisor.models import (
    RECORD_MODEL,
    AuditFlag,
    BranchAdvance,
    BranchAdvanceOutcome,
    CollectedExit,
    CompletionEvidence,
    EntryKind,
    VerifyResult,
)
from workflow_interpreter.supervisor.paths import (
    WrapperPaths,
)
from workflow_interpreter.supervisor.verify import VerifyTree, run_checks
from workflow_interpreter.supervisor.workspace import Workspace

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

SUCCESS_CLAIMS: Final[frozenset[Outcome]] = frozenset(
    {Outcome.DONE, Outcome.ACCEPT, Outcome.NO_DIFF}
)
"""Claims that assert the work succeeded, and therefore carry the full §7
burden. `fail_plan` and `reject` are failure claims: a failing check on them is
consistent evidence, recorded as-is and never overwritten (§7.3)."""

_REASON_VERIFY_FAILED: Final[str] = "verify check {cmd!r} exited {exit_code}"
_REASON_OUTPUTS_TRUNCATED: Final[str] = "output walk was truncated"
_REASON_PROVENANCE: Final[str] = (
    "verify check {cmd!r} hashes to {actual}, pinned {expected} — refused (§7.3)"
)
_REASON_UNDECLARED: Final[str] = "undeclared effects: {paths}"
_REASON_OUT_OF_SCOPE: Final[str] = (
    "modified outside allowed_paths (declared, so not blocking): {paths}"
)
_REASON_ANTI_DRIFT: Final[str] = (
    "reviewed identity {reviewed} is not the verified identity {verified}"
)
_REASON_NO_DIFF_COMMIT: Final[str] = (
    "marker claims no_diff but the attempt produced commit {commit}"
)
_STATE_NON_REGULAR: Final[str] = "non-regular"
"""The working-tree state of a path that is not a regular file. Distinct from
`NO_BLOB` (absent), which `hash_working_file` also returns for one."""


def render_binding(activation: ActivationRecord) -> LedgerRenderBinding | None:
    """The immutable ledger render this activation was MINTED against (§3.7).

    Read from the activation's own input bindings rather than from the render
    ref, because the ref is a mutable name and the binding is a pinned object
    id: a §7.3 check that resolves the render itself must be told which objects
    the engine promised it, not which ones a name points at now.
    """
    for binding in activation.metadata.inputs:
        if binding.ledger_render is not None:
            return binding.ledger_render
    return None


class ComputedEvidence(BaseModel):
    """The §7 verdict plus the one fact the sandbox verdict cannot recompute.

    `physically_written` is the out-of-grant subset whose on-disk state differs
    from the intended base commit's, measured at the single observation §7.5
    already made. It travels with the verdict because `_with_sandbox_verdict`
    runs where the worktree and the base commit are no longer in scope, and
    re-deriving it there would be a SECOND observation of a tree the first
    observation is the record of.
    """

    model_config = RECORD_MODEL

    completion: CompletionEvidence
    physically_written: tuple[str, ...] = ()


class EvidenceGrader:
    """Compute host verification and filesystem evidence for a single dead child."""

    def __init__(self, paths: WrapperPaths, git: Git, workspace: Workspace) -> None:
        self._paths, self._git, self._workspace = paths, git, workspace

    def _compute(
        self,
        activation: ActivationRecord,
        node: Node,
        collected: CollectedExit,
        artifact: ArtifactIdentity | None,
        exit_record: ExitRecord,
        pinned_digests: dict[str, str],
        branch: BranchAdvance | None,
        run_identity: RunIdentity | None = None,
    ) -> ComputedEvidence:
        """Decide the outcome the evidence supports — never the one claimed.

        `verified` is the commit the checks actually ran at, which is the
        artifact commit when there is one and `intended_base_commit` when there
        is not (a `no_diff` attempt, or a `writes = false` reviewer, both of
        which are graded at the commit they were given). It is a fact about the
        checkout `verify.py` created, not a read of a tree the runner can still
        write — which is what makes §7.3's anti-drift cross-check mean anything.
        """
        cwd = self._workspace.path_for(node)
        verified = (
            activation.metadata.intended_base_commit
            if artifact is None
            else artifact.commit_oid
        )
        with VerifyTree(self._git, self._paths, verified) as tree:
            results = run_checks(
                node,
                tree,
                pinned_digests,
                base_commit=activation.metadata.intended_base_commit,
                run_identity=run_identity,
                render=render_binding(activation),
            )
        undeclared = self._undeclared_effects(
            activation, node, collected, artifact, cwd
        )
        out_of_scope = self._effects_outside_allowed_paths(
            activation, node, artifact, cwd
        )
        physically_written = self._physically_written(
            out_of_scope,
            base_commit=activation.metadata.intended_base_commit,
            cwd=cwd,
            activation_id=activation.activation_id,
        )
        evidence = Evidence(
            verify=tuple(
                VerifyOutcome(
                    cmd=result.cmd,
                    exit_code=result.exit_code,
                    script_digest=result.script_digest,
                    attempts=result.attempts,
                )
                for result in results
            ),
            artifact=artifact,
            undeclared_effects=undeclared,
        )
        reasons: list[str] = []
        flags: list[AuditFlag] = []
        output_reasons = [
            f"unsafe output {entry.path} ({entry.kind.value})"
            for entry in collected.outputs_unsafe
        ]
        if collected.outputs_truncated:
            output_reasons.append(_REASON_OUTPUTS_TRUNCATED)
        output_flags = (
            [AuditFlag.OUTPUTS_UNSAFE]
            if collected.outputs_unsafe or collected.outputs_truncated
            else []
        )

        if exit_record.exit_code != 0 and collected.marker is None:
            return ComputedEvidence(
                completion=CompletionEvidence(
                    outcome=Outcome.ERROR_RUNNER,
                    claimed_outcome=None,
                    evidence=evidence,
                    verify_results=results,
                    audit_flags=tuple(output_flags),
                    reasons=(f"runner exited {exit_record.exit_code}", *output_reasons),
                    branch=branch,
                )
            )

        if collected.marker is None:
            reasons.append(collected.marker_error or REASON_MARKER_ABSENT)
            flags.append(AuditFlag.MARKER_INVALID)
            reasons.extend(output_reasons)
            flags.extend(output_flags)
            return ComputedEvidence(
                completion=CompletionEvidence(
                    outcome=Outcome.FAIL_CODE,
                    claimed_outcome=None,
                    evidence=evidence,
                    verify_results=results,
                    audit_flags=tuple(flags),
                    reasons=tuple(reasons),
                )
            )

        claimed = collected.marker.outcome
        outcome = claimed
        for result in results:
            if not result.provenance_ok:
                reasons.append(
                    _REASON_PROVENANCE.format(
                        cmd=result.cmd,
                        actual=result.script_digest,
                        expected=result.pinned_digest,
                    )
                )
                flags.append(AuditFlag.VERIFIER_PROVENANCE)
                outcome = Outcome.FAIL_CODE
            elif result.error is not None:
                # Flagged for the §10.6 sweep whatever the claim is, but only
                # a SUCCESS claim is overwritten by it: a check that could not
                # run is a failing check, and §7.3 does not overwrite a failure
                # claim with one (`_grade_success_claim` applies it).
                reasons.append(result.error)
                flags.append(AuditFlag.VERIFY_UNRUNNABLE)

        if claimed in SUCCESS_CLAIMS and outcome is not Outcome.FAIL_CODE:
            outcome, extra_reasons, extra_flags = self._grade_success_claim(
                activation, node, claimed, collected, artifact, results, verified
            )
            reasons.extend(extra_reasons)
            flags.extend(extra_flags)
        elif claimed is Outcome.REJECT and not collected.artifact_paths:
            reasons.append("reject claim carries no findings artifact")
            outcome = Outcome.FAIL_CODE

        if undeclared:
            reasons.append(_REASON_UNDECLARED.format(paths=", ".join(undeclared)))
            flags.append(AuditFlag.UNDECLARED_EFFECT)
        if out_of_scope:
            reasons.append(_REASON_OUT_OF_SCOPE.format(paths=", ".join(out_of_scope)))
            flags.append(AuditFlag.EFFECT_OUTSIDE_ALLOWED_PATHS)
        if collected.effects is None:
            flags.append(AuditFlag.EFFECTS_MANIFEST_MISSING)
        flags.extend(output_flags)
        reasons.extend(output_reasons)
        if branch is not None and branch.outcome is BranchAdvanceOutcome.DIVERGED:
            flags.append(AuditFlag.INSTANCE_BRANCH_DIVERGED)
            reasons.append("instance branch diverged")
        elif branch is not None and branch.outcome is BranchAdvanceOutcome.MISSING:
            reasons.append("instance branch missing")
        return ComputedEvidence(
            completion=CompletionEvidence(
                outcome=outcome,
                claimed_outcome=claimed,
                evidence=evidence,
                verify_results=results,
                audit_flags=tuple(flags),
                reasons=tuple(reasons),
                branch=branch,
            ),
            physically_written=physically_written,
        )

    def _grade_success_claim(
        self,
        activation: ActivationRecord,
        node: Node,
        claimed: Outcome,
        collected: CollectedExit,
        artifact: ArtifactIdentity | None,
        results: tuple[VerifyResult, ...],
        verified: str,
    ) -> tuple[Outcome, list[str], list[AuditFlag]]:
        """§7.3's outcome-specific burden for a claim that asserts success."""
        reasons: list[str] = []
        flags: list[AuditFlag] = []
        outcome = claimed
        for result in results:
            if result.exit_code != 0:
                reasons.append(
                    _REASON_VERIFY_FAILED.format(
                        cmd=result.cmd, exit_code=result.exit_code
                    )
                )
                outcome = Outcome.FAIL_CODE
        if collected.effects is None:
            reasons.append(
                collected.effects_error or REASON_EFFECTS.format(detail="is absent")
            )
            flags.append(AuditFlag.EFFECTS_MANIFEST_MISSING)
            outcome = Outcome.FAIL_CODE
        if claimed is JUDGMENT_OUTCOME:
            reviewed = activation.metadata.intended_base_commit
            if reviewed != verified:
                reasons.append(
                    _REASON_ANTI_DRIFT.format(reviewed=reviewed, verified=verified)
                )
                flags.append(AuditFlag.ANTI_DRIFT)
                outcome = Outcome.FAIL_CODE
        if claimed is Outcome.NO_DIFF and artifact is not None:
            reasons.append(_REASON_NO_DIFF_COMMIT.format(commit=artifact.commit_oid))
            outcome = Outcome.FAIL_CODE
        if claimed is Outcome.DONE and artifact is None and bool(node.writes):
            reasons.append("done claim produced no commit; that is no_diff (§7.4)")
            outcome = Outcome.FAIL_CODE
        return outcome, reasons, flags

    def _effects_outside_allowed_paths(
        self,
        activation: ActivationRecord,
        node: Node,
        artifact: ArtifactIdentity | None,
        cwd: Path,
    ) -> tuple[str, ...]:
        """observed ∖ allowed — scope, ignoring what the runner declared.

        The §7.5 set subtracts the runner's own manifest too, so a node that
        writes anywhere and says so is graded clean. This is the same observed
        set measured against the node's DECLARED scope alone, which is the
        only question an operator can act on (ADR 0001).
        """
        allowed = node.allowed_paths or ()
        return tuple(
            sorted(
                path
                for path in self._observed_paths(activation, artifact, cwd)
                if not path_allowed(path, allowed)
            )
        )

    def _undeclared_effects(
        self,
        activation: ActivationRecord,
        node: Node,
        collected: CollectedExit,
        artifact: ArtifactIdentity | None,
        cwd: Path,
    ) -> tuple[str, ...]:
        """§7.5: observed ∖ (declared ∪ allowed) — the set that blocks a transition."""
        declared = frozenset(collected.effects.paths if collected.effects else ())
        allowed = node.allowed_paths or ()
        return tuple(
            sorted(
                path
                for path in self._observed_paths(activation, artifact, cwd)
                if path not in declared and not path_allowed(path, allowed)
            )
        )

    def _physically_written(
        self,
        paths: tuple[str, ...],
        *,
        base_commit: str,
        cwd: Path,
        activation_id: str,
    ) -> tuple[str, ...]:
        """Of `paths`, those the working tree actually holds differently from base.

        The evidence `_with_sandbox_verdict` needs and the §7.5 observation
        cannot supply. `_observed_paths` reads the committed diff and `git
        status`, and BOTH of those are reachable through the index alone: under
        the §2 mount bound `.git` is writable by design (`sandbox.plan_for`),
        so `git rm --cached <path> && git commit` names an out-of-grant path in
        the diff while leaving the file untouched on disk, and `git
        update-index --cacheinfo` names one that is not on disk at all. Neither
        is a write the kernel had to refuse, so neither is evidence that the
        bound failed.

        The physical question is asked directly instead: the blob the working
        file hashes to now, against the blob the base commit records at that
        path, with ABSENT (`NO_BLOB`) counted as a state on either side. Equal
        means the forgery reached the index and never the filesystem.

        An UNCOMPUTABLE check answers nothing, so it answers "no evidence":
        escalation is the strong claim, and a `rev-parse` that failed for its
        own reasons must not be the thing that halts an instance.
        """
        written: list[str] = []
        try:
            for path in paths:
                disk = self._disk_state(path, cwd=cwd)
                if disk != self._git.blob_oid_at(base_commit, path, cwd=cwd):
                    written.append(path)
        except (OSError, SupervisorError) as exc:
            _LOG.error(
                "wf.sandbox.physical_check_uncomputable",
                activation_id=activation_id,
                paths=paths,
                error=str(exc),
            )
            return ()
        return tuple(written)

    def _disk_state(self, path: str, *, cwd: Path) -> str:
        """What the working tree holds at `path`, as one comparable token.

        A blob id for a regular file, `NO_BLOB` for an absent one, and
        `_STATE_NON_REGULAR` for a directory, symlink-to-directory or device —
        which `hash_working_file` also reports as `NO_BLOB`, and which must not
        therefore be read as "absent" and compared equal to a path the base
        commit does not have.
        """
        if Git.entry_kind(path, cwd=cwd) is not EntryKind.FILE:
            return _STATE_NON_REGULAR
        return self._git.hash_working_file(path, cwd=cwd)

    def _observed_paths(
        self,
        activation: ActivationRecord,
        artifact: ArtifactIdentity | None,
        cwd: Path,
    ) -> frozenset[str]:
        """Every path this activation changed: committed diff plus working tree.

        One definition, because §7.5's blocking set and the ADR 0001 scope flag
        must measure the same observation and differ only in what they subtract.
        """
        observed: set[str] = set()
        if artifact is not None:
            observed.update(
                self._git.diff_names(
                    activation.metadata.intended_base_commit,
                    artifact.commit_oid,
                    cwd=cwd,
                )
            )
        observed.update(path for path, _ in self._git.status_paths(cwd=cwd))
        return frozenset(observed)
