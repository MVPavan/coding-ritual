"""Child exit: collect the §6 channels, compute §7, mirror the exit into bd.

§7's premise is that a claim is not a proof. The runner writes one marker; the
wrapper computes five clauses and the marker only ever gets to AGREE with them:

1. **Terminal observed** — the bd exit record this module writes last (§7.1).
2. **Claim parsed** — exactly one schema-valid marker naming an outcome the
   node declares. Zero, two, unparseable or undeclared is `fail_code`, and
   never fallback routing (§2 'Outcome vocabulary', drill 15).
3. **Evidence computed** — every `verify` entry of the PINNED graph, executed
   without a shell, with its declared timeout, in a clean detached checkout of
   the artifact commit, and only after its executable matches the digest pinned
   at instantiation. A mismatch does not run the check at all: an examiner the
   examinee may have edited is not evidence (§7.3, drill 13, `verify.py`).
4. **Artifact identity** — commit OID + tree OID, with the git ref pinned by
   the wrapper BEFORE any bd write (§7.4).
5. **Effects reconciled** — observed (commit range + dirty tree) minus declared
   (`$WF_EFFECTS_FILE`) minus `allowed_paths` (§7.5). This clause alone reads
   the LIVE tree: uncommitted and untracked files are exactly what it is about.

Ordering is the crash contract, and it has two halves:

- **The exit file is written FIRST**, from the raw observation, before a single
  check runs. §7 can take ten minutes; a wrapper killed inside it used to lose
  a completed run to §5.6 case 3 ("dead without exit"), because the only record
  that the child had exited was written after the computation. Now the crash
  window classifies as "exited, evidence incomplete" — and §7 is deterministic
  over git and the wrapper dir, so it is simply re-run.
- **git ref first, bd write second — the bd write is the commit point** (§7.4).
  `record_exit` is therefore the wrapper's FINAL act, and the on-disk exit file
  is demoted to a crash-window fallback the moment it succeeds (§5.3). The
  computed evidence lands in `completion.json` just before it, which is what
  makes "evidence incomplete" observable rather than assumed.

`record_evidence` and the close stay with the foreman — which is where §7 puts
them ("computed by the foreman wrapper at `exit-recorded`").
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import structlog
from pydantic import BaseModel

from workflow_interpreter.bdio import (
    ActivationRecord,
    ArtifactIdentity,
    Breaker,
    Evidence,
    ExitRecord,
    Outcome,
    Usage,
    VerifyOutcome,
    WorkflowStore,
)
from workflow_interpreter.schema.models import JUDGMENT_OUTCOME, Node
from workflow_interpreter.supervisor.channels import (
    REASON_EFFECTS,
    REASON_MARKER_ABSENT,
    path_allowed,
    pinned_verifier_digests,
    read_effects,
    read_marker,
    walk_outputs,
)
from workflow_interpreter.supervisor.clock import Clock, to_iso
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.errors import SupervisorError, WrapperDirError
from workflow_interpreter.supervisor.gitio import Git
from workflow_interpreter.supervisor.models import (
    RECORD_MODEL,
    AuditFlag,
    BranchAdvance,
    BranchAdvanceOutcome,
    CollectedExit,
    CompletionEvidence,
    ExitReason,
    LaunchReceipt,
    PinResult,
    VerifyResult,
)
from workflow_interpreter.supervisor.paths import (
    WrapperPaths,
    read_record,
    write_record,
)
from workflow_interpreter.supervisor.profile import Profile, TerminalEnvelope
from workflow_interpreter.supervisor.sandbox import SandboxMode
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
_REASON_EVIDENCE_UNCOMPUTED: Final[str] = (
    "the §7 evidence could not be computed ({error}); the exit IS recorded and "
    "no completion.json was written, so §5.6 re-runs §7 rather than treating a "
    "finished run as a transport failure"
)
_REASON_POST_EXIT_FAILED: Final[str] = (
    "the §6 channels could not be read or the §7.4 artifact could not be pinned "
    "({error})"
)


class ExitObservation(BaseModel):
    """Everything one child exit produced, in the order §7 produced it."""

    model_config = RECORD_MODEL

    collected: CollectedExit
    completion: CompletionEvidence
    exit_record: ExitRecord
    artifact: ArtifactIdentity | None
    activation: ActivationRecord
    usage: Usage = Usage(known=False)


class PostExit(BaseModel):
    """What the span between the exit file and `record_exit` produced (§7).

    A carrier rather than a tuple because the span is allowed to fail: every
    field has a defined value for "the wrapper could not compute this", and the
    caller must be able to build an `ExitObservation` either way.
    """

    model_config = RECORD_MODEL

    collected: CollectedExit
    completion: CompletionEvidence
    artifact: ArtifactIdentity | None = None
    usage: Usage = Usage(known=False)


def no_progress_breaker(
    previous_tree_oid: str | None, artifact: ArtifactIdentity | None
) -> Breaker | None:
    """§10.5: an attempt whose tree OID equals the rejected one made no progress."""
    if previous_tree_oid is None or artifact is None:
        return None
    return Breaker.NO_PROGRESS if artifact.tree_oid == previous_tree_oid else None


class ExitObserver:
    """Turns a dead child into §7 evidence and one bd exit record (§5.3)."""

    def __init__(
        self,
        config: SupervisorConfig,
        paths: WrapperPaths,
        git: Git,
        store: WorkflowStore,
        workspace: Workspace,
        clock: Clock,
    ) -> None:
        self._config = config
        self._paths = paths
        self._git = git
        self._store = store
        self._workspace = workspace
        self._clock = clock

    def observe(
        self,
        activation: ActivationRecord,
        node: Node,
        profile: Profile,
        *,
        exit_code: int,
        reason: ExitReason,
        pinned_digests: dict[str, str],
        previous_tree_oid: str | None = None,
    ) -> ExitObservation:
        """Observe an exit once, reusing the first durable exit record."""
        activation_id = activation.activation_id
        exit_record = activation.metadata.exit_record
        if exit_record is None:
            exit_record = self._exit_file_record(activation_id)
        if exit_record is None:
            exit_record = ExitRecord(
                exit_code=exit_code,
                ended_at=to_iso(self._clock.now()),
                reason=reason.value,
            )
            # FIRST, before anything that can take minutes. From here on a crash
            # is "exited, evidence incomplete" and §7 is re-run; before it, the
            # same crash lost a finished run to §5.6 case 3.
            write_record(self._paths.exit_file(activation_id), exit_record)
        elif exit_record.exit_code != exit_code or exit_record.reason != reason.value:
            _LOG.info(
                "wf.activation.exit_reused",
                activation_id=activation_id,
                recorded_exit_code=exit_record.exit_code,
                recorded_reason=exit_record.reason,
                passed_exit_code=exit_code,
                passed_reason=reason.value,
            )

        return self._observe_recorded(
            activation,
            node,
            profile,
            exit_record,
            pinned_digests=pinned_digests,
            previous_tree_oid=previous_tree_oid,
        )

    def replay(
        self,
        activation: ActivationRecord,
        node: Node,
        profile: Profile,
        exit_record: ExitRecord,
        *,
        pinned_digests: dict[str, str],
        previous_tree_oid: str | None = None,
    ) -> ExitObservation:
        """Resume observation from its durable exit record, with cache-miss effects.

        When ``completion.json`` is absent, replay re-runs attribution and
        artifact/output pinning and rewrites that completion cache before it
        mirrors the exit record.
        """
        return self._observe_recorded(
            activation,
            node,
            profile,
            exit_record,
            pinned_digests=pinned_digests,
            previous_tree_oid=previous_tree_oid,
        )

    def _exit_file_record(self, activation_id: str) -> ExitRecord | None:
        """Read a parseable crash-window exit record without trusting a bad file."""
        try:
            return read_record(self._paths.exit_file(activation_id), ExitRecord)
        except WrapperDirError:
            return None

    def _observe_recorded(
        self,
        activation: ActivationRecord,
        node: Node,
        profile: Profile,
        exit_record: ExitRecord,
        *,
        pinned_digests: dict[str, str],
        previous_tree_oid: str | None,
    ) -> ExitObservation:
        """Compute missing evidence, then mirror the already-chosen exit record."""
        completion = self._completion_record(activation.activation_id)
        if completion is None:
            post = self._post_exit(
                activation,
                node,
                profile,
                exit_record,
                pinned_digests,
                previous_tree_oid,
            )
        else:
            post = PostExit(
                collected=CollectedExit(marker=None),
                completion=completion,
                artifact=completion.evidence.artifact,
            )

        record = self._record_exit(activation, exit_record, post.completion)
        return ExitObservation(
            collected=post.collected,
            completion=post.completion,
            exit_record=exit_record,
            artifact=post.artifact,
            activation=record,
            usage=post.usage,
        )

    def _completion_record(self, activation_id: str) -> CompletionEvidence | None:
        """Read reusable §7 evidence, treating a bad file as incomplete work."""
        try:
            return read_record(
                self._paths.completion(activation_id), CompletionEvidence
            )
        except WrapperDirError:
            return None

    def _post_exit(
        self,
        activation: ActivationRecord,
        node: Node,
        profile: Profile,
        exit_record: ExitRecord,
        pinned_digests: dict[str, str],
        previous_tree_oid: str | None,
    ) -> PostExit:
        """Everything between the exit file and `record_exit` — and it cannot raise.

        The whole span is the guard, not just the §7 computation. `_evidence`
        alone left `record_attribution` and `pin_artifact` outside it, and both
        spawn git: `git hash-object` on the directory `git status` reports for a
        nested checkout exits 128, the `GitCommandError` escaped `observe()`,
        and the activation was left `dispatched` with a child that had provably
        exited — §5.6 then classified it case 3 and spent an infra retry on a
        finished run, deterministically, on every attempt (probed, Opus#12).

        `record_exit` is the wrapper's debt to §7.1 and it is owed whatever
        happened in here, so every `OSError` and every `SupervisorError` becomes
        a `fail_code` verdict carrying `VERIFY_UNRUNNABLE` instead. No
        `completion.json` is written for it, which is exactly the "exited,
        evidence incomplete" state §5.6 re-runs §7 from.
        """
        try:
            return self._collect_and_grade(
                activation,
                node,
                profile,
                exit_record,
                pinned_digests,
                previous_tree_oid,
            )
        except (OSError, SupervisorError) as exc:
            _LOG.error(
                "wf.exit.post_exit_failed",
                activation_id=activation.activation_id,
                error=str(exc),
            )
            return PostExit(
                collected=CollectedExit(
                    marker=None,
                    marker_error=_REASON_POST_EXIT_FAILED.format(error=exc),
                ),
                completion=self._uncomputable(None, exc),
            )

    def _collect_and_grade(
        self,
        activation: ActivationRecord,
        node: Node,
        profile: Profile,
        exit_record: ExitRecord,
        pinned_digests: dict[str, str],
        previous_tree_oid: str | None,
    ) -> PostExit:
        """Read the §6 channels, record §12 attribution, pin §7.4, grade §7."""
        handle = activation.metadata.handle
        envelope = None if handle is None else profile.collect_terminal_envelope(handle)
        collected = self._collect(activation.activation_id, node, envelope)
        declared = (
            None if collected.effects is None else frozenset(collected.effects.paths)
        )
        self._workspace.record_attribution(
            activation, node, declared=frozenset() if declared is None else declared
        )
        pin = self._workspace.pin_artifact(activation, node, declared=declared)
        outputs_pin = self._workspace.pin_outputs(activation, collected.artifact_paths)
        return PostExit(
            collected=collected,
            completion=self._evidence(
                activation,
                node,
                collected,
                pin.identity,
                pin.branch,
                outputs_pin,
                exit_record,
                pinned_digests,
                previous_tree_oid,
            ),
            artifact=pin.identity,
            usage=Usage(known=False) if envelope is None else envelope.usage,
        )

    def _record_exit(
        self,
        activation: ActivationRecord,
        exit_record: ExitRecord,
        completion: CompletionEvidence,
    ) -> ActivationRecord:
        """Mirror the exit unless a settled or recorded activation already owns it."""
        activation_id = activation.activation_id
        reloaded = self._store.reads.load_activation(activation_id)
        if reloaded.metadata.is_settled or reloaded.metadata.exit_record is not None:
            return reloaded
        record = self._store.record_exit(activation_id, exit_record)
        _LOG.info(
            "wf.activation.exit_recorded",
            activation_id=activation_id,
            exit_code=exit_record.exit_code,
            reason=exit_record.reason,
            outcome=completion.outcome.value,
        )
        return record

    def _evidence(
        self,
        activation: ActivationRecord,
        node: Node,
        collected: CollectedExit,
        artifact: ArtifactIdentity | None,
        branch: BranchAdvance | None,
        outputs_pin: PinResult,
        exit_record: ExitRecord,
        pinned_digests: dict[str, str],
        previous_tree_oid: str | None,
    ) -> CompletionEvidence:
        """Compute §7, or record WHY it could not be computed — never escape.

        A `VerifyTreeError` (no trustworthy tree to grade in) or a
        `GitCommandError` lands between the exit file and `record_exit`, and
        letting it out left the activation `dispatched` with a child that had
        provably exited: §5.6 then classified it case 3 and spent an infra retry
        on a run that had already finished. Caught, the exit still reaches bd
        and `completion.json` is deliberately NOT written — which is exactly the
        "exited, evidence incomplete" state §5.6 re-runs §7 from, because §7 is
        deterministic over git and the wrapper dir.
        """
        activation_id = activation.activation_id
        try:
            completion = self._compute(
                activation,
                node,
                collected,
                artifact,
                exit_record,
                pinned_digests,
                branch,
            )
        except (OSError, SupervisorError) as exc:
            _LOG.error(
                "wf.evidence.uncomputable",
                activation_id=activation_id,
                error=str(exc),
            )
            return self._with_sandbox_verdict(
                activation_id, self._uncomputable(artifact, exc)
            )
        completion = self._with_sandbox_verdict(activation_id, completion)
        completion = completion.model_copy(
            update={
                "evidence": completion.evidence.model_copy(
                    update={
                        "breaker": no_progress_breaker(previous_tree_oid, artifact),
                        "outputs_ref": outputs_pin.ref,
                        "outputs_tree_oid": None
                        if outputs_pin.identity is None
                        else outputs_pin.identity.tree_oid,
                        "claimed_outcome": completion.claimed_outcome,
                    }
                )
            }
        )
        write_record(self._paths.completion(activation_id), completion)
        return completion

    def _with_sandbox_verdict(
        self, activation_id: str, completion: CompletionEvidence
    ) -> CompletionEvidence:
        """Fold the bound this child actually ran under into the §7 verdict.

        Read from the launch RECEIPT rather than from the config, because the
        receipt records what the child actually ran under; the config can be
        changed between the dispatch and the close. Applied on every §7 verdict
        including the uncomputable one — an operator who turned the bound off
        must learn it from the close whatever else went wrong.

        Unbounded (O5): append `SANDBOX_OFF`, which blocks nothing.

        Bounded: `allowed_paths` are the node's writable mounts, so a path
        observed outside them was a write the kernel refused — the flag can
        only mean the bound did not hold. That is a wrapper invariant
        violation rather than anything the runner did, so it also overrules the
        outcome to `error_transport` and carries `BOUND_VIOLATED`
        (`foreman/finalize.decide` turns that into the retry-exempt deviation
        that halts). An ABSENT receipt asserts nothing about the bound and
        therefore changes nothing.
        """
        try:
            receipt = read_record(self._paths.receipt(activation_id), LaunchReceipt)
        except WrapperDirError:
            return completion
        if receipt is None:
            return completion
        if receipt.sandbox is SandboxMode.OFF:
            return completion.model_copy(
                update={"audit_flags": (*completion.audit_flags, AuditFlag.SANDBOX_OFF)}
            )
        if AuditFlag.EFFECT_OUTSIDE_ALLOWED_PATHS not in completion.audit_flags:
            return completion
        _LOG.error(
            "wf.sandbox.bound_violated",
            activation_id=activation_id,
            reasons=completion.reasons,
        )
        return completion.model_copy(
            update={
                "outcome": Outcome.ERROR_TRANSPORT,
                "audit_flags": (*completion.audit_flags, AuditFlag.BOUND_VIOLATED),
            }
        )

    @staticmethod
    def _uncomputable(
        artifact: ArtifactIdentity | None, error: Exception
    ) -> CompletionEvidence:
        """The §7 verdict when §7 could not be computed — never an exception.

        Shared by the narrow catch around the computation and the wide one
        around the whole post-exit span, so the two cannot drift into reporting
        the same failure two different ways.
        """
        return CompletionEvidence(
            outcome=Outcome.FAIL_CODE,
            claimed_outcome=None,
            evidence=Evidence(artifact=artifact),
            audit_flags=(AuditFlag.VERIFY_UNRUNNABLE,),
            reasons=(_REASON_EVIDENCE_UNCOMPUTED.format(error=error),),
        )

    # -- collection ------------------------------------------------------

    def _collect(
        self, activation_id: str, node: Node, envelope: TerminalEnvelope | None
    ) -> CollectedExit:
        """Read the three §6 channels once, recording WHY any of them failed.

        The marker comes from `$WF_OUTCOME_FILE` and from nowhere else. A
        profile's `collect_terminal_envelope` may also report one, but it is a
        vendor adapter's parse of a vendor's stream — accepting it as a
        fallback would give the runner a second, unvalidated way to name its
        own outcome (§6, "THE reserved channel").
        """
        declared = frozenset(node.outcomes or ())
        marker, marker_error = read_marker(
            self._paths.outcome(activation_id), declared, node.name
        )
        effects, effects_error = read_effects(self._paths.effects(activation_id))
        walk = walk_outputs(
            self._paths.artifacts(activation_id),
            self._paths.outputs_snapshot(activation_id),
            max_files=self._config.max_output_files,
            max_bytes=self._config.max_output_bytes,
            max_walk_entries=self._config.max_output_entries,
            max_depth=self._config.max_output_depth,
        )
        return CollectedExit(
            marker=marker,
            marker_error=marker_error,
            effects=effects,
            effects_error=effects_error,
            artifact_paths=walk.paths,
            outputs_unsafe=walk.unsafe,
            outputs_truncated=walk.truncated,
            session_id=None if envelope is None else envelope.session_id,
            duration_s=None if envelope is None else envelope.duration_s,
        )

    # -- the five §7 clauses ---------------------------------------------

    def _compute(
        self,
        activation: ActivationRecord,
        node: Node,
        collected: CollectedExit,
        artifact: ArtifactIdentity | None,
        exit_record: ExitRecord,
        pinned_digests: dict[str, str],
        branch: BranchAdvance | None,
    ) -> CompletionEvidence:
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
            )
        undeclared = self._undeclared_effects(
            activation, node, collected, artifact, cwd
        )
        out_of_scope = self._effects_outside_allowed_paths(
            activation, node, artifact, cwd
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
            return CompletionEvidence(
                outcome=Outcome.ERROR_RUNNER,
                claimed_outcome=None,
                evidence=evidence,
                verify_results=results,
                audit_flags=tuple(output_flags),
                reasons=(f"runner exited {exit_record.exit_code}", *output_reasons),
                branch=branch,
            )

        if collected.marker is None:
            reasons.append(collected.marker_error or REASON_MARKER_ABSENT)
            flags.append(AuditFlag.MARKER_INVALID)
            reasons.extend(output_reasons)
            flags.extend(output_flags)
            return CompletionEvidence(
                outcome=Outcome.FAIL_CODE,
                claimed_outcome=None,
                evidence=evidence,
                verify_results=results,
                audit_flags=tuple(flags),
                reasons=tuple(reasons),
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
        return CompletionEvidence(
            outcome=outcome,
            claimed_outcome=claimed,
            evidence=evidence,
            verify_results=results,
            audit_flags=tuple(flags),
            reasons=tuple(reasons),
            branch=branch,
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


__all__ = [
    "ExitObservation",
    "ExitObserver",
    "no_progress_breaker",
    "pinned_verifier_digests",
]
