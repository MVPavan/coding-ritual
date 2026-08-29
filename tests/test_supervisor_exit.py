"""§7 completion evidence: computed, never claimed.

Drills 13 (verifier provenance), 15 (lying completion, plus its zero-marker and
two-marker sub-cases) and 24 (undeclared effect) live here, against a real git
worktree and real verify scripts — a stubbed `git` or a stubbed `subprocess`
would be testing the test's idea of the evidence rather than the evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._supervisor import (
    FAILING_SCRIPT,
    IMPLEMENT,
    REVIEW,
    REVIEW_SCRIPT,
    VERIFY_SCRIPT,
    FakeProfile,
    FrozenClock,
    commit_all,
    dead_pid,
    entry_mint,
    handle_for,
    head_of,
    make_config,
    make_git,
    make_paths,
    make_repo,
    make_root,
    make_store,
    make_workspace,
    node_of,
    verifier_pins,
)
from workflow_interpreter.bdio import (
    ActivationRecord,
    BdCommandError,
    Breaker,
    ExitRecord,
    Lifecycle,
    LossyWriteError,
    Outcome,
)
from workflow_interpreter.schema.models import IsolationMode, Node
from workflow_interpreter.supervisor import (
    AuditFlag,
    CompletionEvidence,
    DirtyEntry,
    ExitObserver,
    ExitReason,
    GitCommandError,
    RecoveryCase,
    RunnerAttribution,
    SupervisorConfig,
    VerifyTreeError,
    Workspace,
    WrapperPaths,
)
from workflow_interpreter.supervisor.paths import read_record, write_record
from workflow_interpreter.supervisor.recover import classify

FEATURE_FILE = "src/feature.py"
OUTSIDE_FILE = "docs/notes.md"
DONE_MARKER = {"outcome": "done"}
BD_UPDATE = "update"
BD_SHOW = "show"


class Lab:
    """A dispatched activation whose child has just exited."""

    def __init__(
        self, tmp_path: Path, node_name: str = IMPLEMENT, *, in_repo: bool = False
    ) -> None:
        self.repo = make_repo(tmp_path)
        self.base = head_of(self.repo)
        self.config: SupervisorConfig = make_config(
            self.repo, tmp_path, fake_proc=False
        )
        self.bd, self.store = make_store(tmp_path, self.base)
        self.root = make_root(self.store, self.repo, "exit-instance")
        self.paths: WrapperPaths = make_paths(self.config, self.root.root_id)
        self.clock = FrozenClock()
        self.git = make_git(self.config)
        self.workspace = make_workspace(self.paths, self.git, self.clock)
        self.node: Node = node_of(self.root.definition.document, node_name)
        if in_repo:
            # §12: the human's own checkout, so the band is a precondition of
            # `prepare` — and the mode where `record_attribution` runs at all.
            self.node = self.node.model_copy(
                update={"isolation": IsolationMode.IN_REPO}
            )
            self.workspace.band.acquire()
        self.profile = FakeProfile()
        minted = self.store.mint_activation(self.root.root_id, entry_mint())
        self.activation = self.store.record_dispatch(
            minted.activation.activation_id, handle_for(dead_pid())
        )
        self.paths.ensure_activation_dir(self.activation.activation_id)
        self.workspace.prepare(self.activation, self.node)
        self.observer = ExitObserver(
            self.config,
            self.paths,
            self.git,
            self.store,
            self.workspace,
            self.clock,
        )

    @property
    def tree(self) -> Path:
        """The tree this activation's runner executes in (§5.4, §12)."""
        return self.workspace.path_for(self.node)

    def marker(self, raw: str) -> None:
        """Write `$WF_OUTCOME_FILE` verbatim (so zero/two markers are expressible)."""
        self.paths.outcome(self.activation.activation_id).write_text(
            raw, encoding="utf-8"
        )

    def effects(self, *paths: str) -> None:
        """Write the `$WF_EFFECTS_FILE` manifest."""
        self.paths.effects(self.activation.activation_id).write_text(
            json.dumps({"paths": list(paths)}), encoding="utf-8"
        )

    def pins(self, *scripts: str) -> dict[str, str]:
        """The §7.3 digests of the scripts AS THEY ARE IN THE WORKTREE now."""
        return verifier_pins(self.tree, self.node.name, *(scripts or (VERIFY_SCRIPT,)))

    def observe(
        self,
        *,
        pins: dict[str, str] | None = None,
        previous_tree_oid: str | None = None,
        exit_code: int = 0,
    ) -> object:
        """Run the §7 computation for this exited child."""
        return self.observer.observe(
            self.activation,
            self.node,
            self.profile,
            exit_code=exit_code,
            reason=ExitReason.EXITED,
            pinned_digests=pins if pins is not None else self.pins(),
            previous_tree_oid=previous_tree_oid,
        )

    def commit_work(self, path: str = FEATURE_FILE) -> str:
        """Have the "runner" write and commit a file in its worktree."""
        target = self.tree / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("value = 2\n", encoding="utf-8")
        return commit_all(self.tree, "the attempt")

    def reload(self) -> ActivationRecord:
        """Re-read the activation from bd."""
        return self.store.reads.load_activation(self.activation.activation_id)


@pytest.fixture
def lab(tmp_path: Path) -> Lab:
    """An `implement` activation whose child has exited."""
    return Lab(tmp_path)


def test_a_clean_done_run_produces_evidence_and_one_exit_record(lab: Lab) -> None:
    """§7's five clauses all hold; `record_exit` is the wrapper's final act."""
    commit = lab.commit_work()
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE)

    observation = lab.observe()

    assert observation.completion.outcome is Outcome.DONE
    assert observation.completion.claimed_outcome is Outcome.DONE
    assert observation.artifact is not None
    assert observation.artifact.commit_oid == commit
    assert [result.exit_code for result in observation.completion.verify_results] == [0]
    assert observation.completion.evidence.undeclared_effects == ()
    assert observation.activation.metadata.lifecycle is Lifecycle.EXIT_RECORDED
    assert observation.activation.metadata.evidence is None
    recorded = read_record(
        lab.paths.exit_file(lab.activation.activation_id), ExitRecord
    )
    assert recorded == observation.exit_record


def test_a_lying_completion_is_fail_code(lab: Lab) -> None:
    """Drill 15: marker says `done`, a verify check says otherwise."""
    (lab.tree / VERIFY_SCRIPT).write_text(FAILING_SCRIPT, encoding="utf-8")
    commit_all(lab.tree, "a failing examiner, honestly pinned")
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(VERIFY_SCRIPT)

    observation = lab.observe()

    assert observation.completion.outcome is Outcome.FAIL_CODE
    assert observation.completion.claimed_outcome is Outcome.DONE
    assert any("exited 1" in reason for reason in observation.completion.reasons)


def test_zero_markers_is_fail_code(lab: Lab) -> None:
    """Drill 15 sub-case: no marker at all, and no fallback routing."""
    lab.commit_work()
    lab.effects(FEATURE_FILE)

    observation = lab.observe()

    assert observation.completion.outcome is Outcome.FAIL_CODE
    assert observation.completion.claimed_outcome is None
    assert AuditFlag.MARKER_INVALID in observation.completion.audit_flags


def test_two_markers_is_fail_code(lab: Lab) -> None:
    """Drill 15 sub-case: a duplicate marker is never resolved by picking one."""
    lab.commit_work()
    lab.marker(f"{json.dumps(DONE_MARKER)}\n{json.dumps(DONE_MARKER)}\n")
    lab.effects(FEATURE_FILE)

    observation = lab.observe()

    assert observation.completion.outcome is Outcome.FAIL_CODE
    assert any("found 2" in reason for reason in observation.completion.reasons)


def test_an_undeclared_outcome_is_fail_code(lab: Lab) -> None:
    """§2: an outcome the node does not declare fails closed, never routes."""
    lab.commit_work()
    lab.marker(json.dumps({"outcome": Outcome.ACCEPT.value}))
    lab.effects(FEATURE_FILE)

    observation = lab.observe()

    assert observation.completion.outcome is Outcome.FAIL_CODE
    assert any(
        "does not declare" in reason for reason in observation.completion.reasons
    )


def test_an_unparseable_marker_is_fail_code(lab: Lab) -> None:
    """§6: THE reserved channel is schema-validated, not best-effort parsed."""
    lab.commit_work()
    lab.marker("{not json at all")
    lab.effects(FEATURE_FILE)

    observation = lab.observe()

    assert observation.completion.outcome is Outcome.FAIL_CODE


def test_an_edited_verifier_is_refused_not_run(lab: Lab) -> None:
    """Drill 13: the examinee may not edit its examiner (§7.3)."""
    pinned = lab.pins()
    (lab.tree / VERIFY_SCRIPT).write_text(
        "#!/bin/sh\nexit 0\n# quietly rewritten\n", encoding="utf-8"
    )
    commit_all(lab.tree, "runner edits the verifier")
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(VERIFY_SCRIPT)

    observation = lab.observe(pins=pinned)

    assert observation.completion.outcome is Outcome.FAIL_CODE
    assert AuditFlag.VERIFIER_PROVENANCE in observation.completion.audit_flags
    result = observation.completion.verify_results[0]
    assert result.provenance_ok is False
    assert result.exit_code == 126


def test_an_unpinned_verifier_is_also_refused(lab: Lab) -> None:
    """A check with no pinned digest cannot be provenance-checked — fail closed."""
    lab.commit_work()
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE)

    observation = lab.observe(pins={})

    assert observation.completion.outcome is Outcome.FAIL_CODE
    assert AuditFlag.VERIFIER_PROVENANCE in observation.completion.audit_flags


def test_an_undeclared_effect_is_recorded_and_flagged(lab: Lab) -> None:
    """Drill 24: observed ∖ (declared ∪ allowed) blocks the transition (§7.5)."""
    lab.commit_work(OUTSIDE_FILE)
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects()

    observation = lab.observe()

    assert observation.completion.evidence.undeclared_effects == (OUTSIDE_FILE,)
    assert AuditFlag.UNDECLARED_EFFECT in observation.completion.audit_flags


def test_a_declared_effect_outside_allowed_paths_is_still_reconciled(
    lab: Lab,
) -> None:
    """§7.5: `declared ∪ allowed` — a declared path is not an undeclared effect."""
    lab.commit_work(OUTSIDE_FILE)
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(OUTSIDE_FILE)

    observation = lab.observe()

    assert observation.completion.evidence.undeclared_effects == ()
    assert observation.completion.outcome is Outcome.DONE


def test_a_missing_effects_manifest_fails_a_success_claim(lab: Lab) -> None:
    """§6: the manifest is fail-closed; a `done` with no manifest is not done."""
    lab.commit_work()
    lab.marker(json.dumps(DONE_MARKER))

    observation = lab.observe()

    assert observation.completion.outcome is Outcome.FAIL_CODE
    assert AuditFlag.EFFECTS_MANIFEST_MISSING in observation.completion.audit_flags


def test_a_failure_claim_is_not_overwritten_by_failing_verify(lab: Lab) -> None:
    """§7.3: a failing check on a failure claim is consistent evidence."""
    (lab.tree / VERIFY_SCRIPT).write_text(FAILING_SCRIPT, encoding="utf-8")
    commit_all(lab.tree, "failing examiner")
    lab.marker(json.dumps({"outcome": Outcome.FAIL_PLAN.value}))
    lab.effects(VERIFY_SCRIPT)

    observation = lab.observe(exit_code=1)

    assert observation.completion.outcome is Outcome.FAIL_PLAN
    assert observation.completion.verify_results[0].exit_code == 1


def test_no_diff_claimed_with_a_commit_is_fail_code(lab: Lab) -> None:
    """§7.4: every writing attempt ends in a commit, else `no_diff` — not both."""
    lab.commit_work()
    lab.marker(json.dumps({"outcome": Outcome.NO_DIFF.value}))
    lab.effects(FEATURE_FILE)

    observation = lab.observe()

    assert observation.completion.outcome is Outcome.FAIL_CODE


def test_identical_tree_oid_records_the_no_progress_breaker(lab: Lab) -> None:
    """§10.5: a distinct commit with the rejected tree OID made no progress."""
    commit = lab.commit_work()
    tree_oid = lab.git.tree_oid(commit, cwd=lab.tree)
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE)

    observation = lab.observe(previous_tree_oid=tree_oid)

    assert observation.completion.evidence.breaker is Breaker.NO_PROGRESS


def test_accept_requires_the_reviewed_identity_to_be_the_verified_one(
    tmp_path: Path,
) -> None:
    """§7.3 anti-drift: a reviewer that verified a different commit is `fail_code`."""
    lab = Lab(tmp_path, node_name=REVIEW)
    lab.commit_work()
    lab.marker(json.dumps({"outcome": Outcome.ACCEPT.value}))
    lab.effects(FEATURE_FILE)

    observation = lab.observe(pins=lab.pins(VERIFY_SCRIPT, REVIEW_SCRIPT))

    assert observation.completion.outcome is Outcome.FAIL_CODE
    assert AuditFlag.ANTI_DRIFT in observation.completion.audit_flags


def test_accept_passes_when_the_reviewer_verified_the_reviewed_commit(
    tmp_path: Path,
) -> None:
    """§7.3: the reviewer ran both checks at the exact commit it reviewed."""
    lab = Lab(tmp_path, node_name=REVIEW)
    lab.marker(json.dumps({"outcome": Outcome.ACCEPT.value}))
    lab.effects()

    observation = lab.observe(pins=lab.pins(VERIFY_SCRIPT, REVIEW_SCRIPT))

    assert observation.completion.outcome is Outcome.ACCEPT
    assert observation.completion.audit_flags == ()
    assert len(observation.completion.verify_results) == 2


# --- the tree the checks actually run in (§7.3, §7.4) --------------------


def test_verify_runs_at_the_artifact_commit_not_the_dirty_worktree(lab: Lab) -> None:
    """B1: a runner cannot commit a broken tree and be graded on a good one.

    The probed counterexample: the runner COMMITS `BROKEN`, fixes the file in
    the working tree only, declares it, and collects a `done` with zero audit
    flags — while the evidence names the commit containing `BROKEN`.
    """
    checker = lab.tree / VERIFY_SCRIPT
    checker.write_text("#!/bin/sh\ngrep -q GOOD src/feature.py\n", encoding="utf-8")
    checker.chmod(0o755)
    (lab.tree / FEATURE_FILE).write_text("BROKEN\n", encoding="utf-8")
    pins = lab.pins()
    commit = commit_all(lab.tree, "the runner commits a broken tree")
    (lab.tree / FEATURE_FILE).write_text("GOOD\n", encoding="utf-8")
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE, VERIFY_SCRIPT)

    observation = lab.observe(pins=pins)

    assert observation.artifact is not None
    assert observation.artifact.commit_oid == commit
    assert observation.completion.verify_results[0].exit_code == 1
    assert observation.completion.outcome is Outcome.FAIL_CODE


def test_the_verify_tree_leaves_the_runners_worktree_untouched(lab: Lab) -> None:
    """B1: grading the artifact must not disturb what the runner left behind."""
    lab.commit_work()
    (lab.tree / "src" / "scratch.txt").write_text("runner scratch\n", encoding="utf-8")
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE, "src/scratch.txt")

    lab.observe()

    assert (lab.tree / "src" / "scratch.txt").exists()
    assert not lab.paths.verify_tree.exists()


# --- the crash window inside §7 (M13) ------------------------------------


def test_the_exit_file_lands_before_the_evidence_is_computed(
    lab: Lab, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M13: a wrapper killed inside a ten-minute §7 must not lose the run.

    Before the fix the exit file was written AFTER the computation, so a crash
    there left no record that the child had exited at all and §5.6 classified a
    finished run as case 3 — `error_transport`, an infra retry spent, the work
    abandoned. The failure is injected where the §7 computation is.
    """

    def explode(*_: object, **__: object) -> tuple[object, ...]:
        raise RuntimeError("the wrapper died inside §7")

    monkeypatch.setattr("workflow_interpreter.supervisor.exit.run_checks", explode)
    lab.commit_work()
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE)

    with pytest.raises(RuntimeError, match="died inside"):
        lab.observe(exit_code=7)

    recorded = read_record(
        lab.paths.exit_file(lab.activation.activation_id), ExitRecord
    )
    assert recorded is not None
    assert recorded.exit_code == 7
    classification = classify(lab.config, lab.paths, lab.activation)
    assert classification.case is RecoveryCase.EXIT_RECORDED
    assert classification.evidence_complete is False


def test_a_completed_computation_records_its_evidence_durably(lab: Lab) -> None:
    """M13: `completion.json` is what makes "evidence complete" observable."""
    lab.commit_work()
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE)

    observation = lab.observe()

    stored = read_record(
        lab.paths.completion(lab.activation.activation_id), CompletionEvidence
    )
    assert stored == observation.completion
    assert classify(lab.config, lab.paths, lab.activation).evidence_complete is True


def test_a_verifier_that_cannot_run_still_produces_an_exit_record(lab: Lab) -> None:
    """M14: the §7 grade is `fail_code` + a flag, and the exit is still mirrored."""
    checker = lab.tree / VERIFY_SCRIPT
    checker.chmod(0o644)
    commit_all(lab.tree, "the runner removed the examiner's execute bit")
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(VERIFY_SCRIPT)

    observation = lab.observe(pins=lab.pins())

    assert observation.completion.outcome is Outcome.FAIL_CODE
    assert AuditFlag.VERIFY_UNRUNNABLE in observation.completion.audit_flags
    assert observation.activation.metadata.lifecycle is Lifecycle.EXIT_RECORDED


def test_an_uncomputable_evidence_pass_still_records_the_exit(
    lab: Lab, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Opus#27: a git failure between the exit file and `record_exit` escaped.

    The child had provably exited, but bd never heard: the activation stayed
    `dispatched`, §5.6 classified it case 3, and an infra retry was spent on a
    run that had already finished. Caught, the exit still reaches bd and
    `completion.json` is deliberately NOT written — which is the "exited,
    evidence incomplete" state §5.6 re-runs §7 from, because §7 is
    deterministic over git and the wrapper dir.
    """

    def refuse(*_: object, **__: object) -> object:
        raise VerifyTreeError("the §7.3 checkout could not be created")

    monkeypatch.setattr("workflow_interpreter.supervisor.exit.VerifyTree", refuse)
    lab.commit_work()
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE)

    observation = lab.observe(exit_code=5)

    assert observation.exit_record.exit_code == 5
    assert observation.activation.metadata.lifecycle is Lifecycle.EXIT_RECORDED
    assert observation.completion.outcome is Outcome.FAIL_CODE
    assert AuditFlag.VERIFY_UNRUNNABLE in observation.completion.audit_flags
    assert not lab.paths.completion(lab.activation.activation_id).exists()
    classification = classify(lab.config, lab.paths, lab.reload())
    assert classification.case is RecoveryCase.EXIT_RECORDED
    assert classification.evidence_complete is False


@pytest.mark.parametrize("call", ["record_attribution", "pin_artifact"])
def test_a_git_failure_before_the_evidence_still_records_the_exit(
    lab: Lab, monkeypatch: pytest.MonkeyPatch, call: str
) -> None:
    """Opus#12 STILL OPEN: only the §7 COMPUTATION was inside the guard.

    `record_attribution` and `pin_artifact` run between the exit file and
    `record_exit` and both spawn git — `git hash-object` on the directory
    `git status` reports for a nested checkout exits 128 — so the
    `GitCommandError` escaped `observe()` exactly as it did before the guard
    existed: the exit file on disk, bd still `dispatched`, and every retry
    dying at the same line. The whole span is the guard now, and `record_exit`
    is owed to §7.1 whatever happened inside it.
    """

    def refuse(*_: object, **__: object) -> object:
        raise GitCommandError("git hash-object failed (exit 128)")

    monkeypatch.setattr(Workspace, call, refuse)
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE)

    observation = lab.observe(exit_code=3)

    assert observation.exit_record.exit_code == 3
    assert observation.activation.metadata.lifecycle is Lifecycle.EXIT_RECORDED
    assert observation.completion.outcome is Outcome.FAIL_CODE
    assert AuditFlag.VERIFY_UNRUNNABLE in observation.completion.audit_flags
    assert not lab.paths.completion(lab.activation.activation_id).exists()
    classification = classify(lab.config, lab.paths, lab.reload())
    assert classification.case is RecoveryCase.EXIT_RECORDED
    assert classification.evidence_complete is False


def test_an_unreadable_wrapper_dir_still_records_the_exit(
    lab: Lab, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same span, entered from the §6 channel reads rather than from git.

    `_collect` walks `$WF_ARTIFACT_DIR` and the profile's terminal envelope is
    a VENDOR adapter's code; an `OSError` out of either is not a reason to lose
    the one record §5.6 uses to tell a finished run from a dead one.
    """

    def refuse(*_: object, **__: object) -> object:
        raise OSError("the wrapper dir went away")

    monkeypatch.setattr(FakeProfile, "collect_terminal_envelope", refuse)

    observation = lab.observe()

    assert observation.activation.metadata.lifecycle is Lifecycle.EXIT_RECORDED
    assert observation.completion.outcome is Outcome.FAIL_CODE
    assert observation.collected.marker is None


def test_a_foreman_close_during_the_exit_is_skipped_without_a_write(
    lab: Lab, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A settled activation is returned without a conflicting bd write."""

    def unexpected_error(*_: object, **__: object) -> None:
        pytest.fail("an already-settled exit must not be logged as an error")

    monkeypatch.setattr(
        "workflow_interpreter.supervisor.exit._LOG.error", unexpected_error
    )
    lab.store.close_activation(lab.activation.activation_id, Outcome.STEERED)
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE)
    updates_before = lab.bd.command_count(BD_UPDATE)
    observation = lab.observe(exit_code=-15)

    assert observation.activation.metadata.outcome is Outcome.STEERED
    assert observation.activation.metadata.lifecycle is Lifecycle.CLOSED
    assert observation.activation.metadata.exit_record is None
    recorded = read_record(
        lab.paths.exit_file(lab.activation.activation_id), ExitRecord
    )
    assert recorded is not None
    assert recorded.exit_code == -15
    assert lab.bd.command_count(BD_UPDATE) == updates_before


def test_an_out_of_band_dirty_state_still_records_the_exit(tmp_path: Path) -> None:
    """Opus#16: the post-exit guard did not cover a `ValueError`.

    `record_attribution` decodes the §3.2 dirty state out of bd metadata, and a
    row whose trio was written out of band — one `bd update` away, and the case
    bead cr-too is open for — raises pydantic's `ValidationError`. That is a
    `ValueError`, so `(OSError, SupervisorError)` did not catch it and
    `observe()` died BEFORE `record_exit`: the child had provably exited and bd
    still said `dispatched`, which §5.6 spends an infra retry on every tick.
    Corrupt provenance decodes to `None` now — no snapshot, so nothing is
    attributable — and the exit still reaches bd.
    """
    lab = Lab(tmp_path, in_repo=True)
    activation_id = lab.activation.activation_id
    lab.bd.rows[activation_id]["metadata"]["pre_attempt_dirty_state"] = (
        '{"entries": "not a list"}'
    )
    lab.activation = lab.reload()
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE)

    observation = lab.observe(exit_code=0)

    assert observation.activation.metadata.lifecycle is Lifecycle.EXIT_RECORDED
    assert lab.reload().metadata.exit_record is not None
    assert read_record(lab.paths.exit_file(activation_id), ExitRecord) is not None
    # Unknown pre-attempt state attributes NOTHING — and REPLACES the record
    # on disk, so an earlier attempt's attribution cannot stay live either.
    attribution = read_record(lab.paths.attribution_record, RunnerAttribution)
    assert attribution is not None
    assert attribution.activation_id == activation_id
    assert attribution.entries == ()


def test_a_foreman_close_one_bd_command_later_propagates_to_the_wrapper_boundary(
    lab: Lab,
) -> None:
    """A race after the bd write is left for the wrapper boundary to classify."""

    def steer() -> None:
        lab.store.close_activation(lab.activation.activation_id, Outcome.STEERED)

    def arm() -> None:
        lab.bd.pause_before(BD_SHOW, steer)

    lab.bd.pause_before(BD_UPDATE, arm)
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE)
    with pytest.raises(LossyWriteError):
        lab.observe(exit_code=-15)

    activation = lab.reload()
    assert activation.metadata.outcome is Outcome.STEERED
    assert activation.metadata.lifecycle is Lifecycle.CLOSED
    # The later race, so the merge itself LANDED and only its verification
    # lost: bd carries this exit under the foreman's close.
    assert activation.metadata.exit_record is not None
    recorded = read_record(
        lab.paths.exit_file(lab.activation.activation_id), ExitRecord
    )
    assert recorded is not None
    assert recorded.exit_code == -15


def test_observe_is_idempotent_on_a_recorded_exit(lab: Lab) -> None:
    """A repeated observation reuses the first record and durable completion."""
    lab.commit_work()
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE)
    first = lab.observe(exit_code=0)
    updates_before = lab.bd.command_count(BD_UPDATE)
    lab.clock.sleep(1)
    second = lab.observer.observe(
        lab.reload(),
        lab.node,
        lab.profile,
        exit_code=9,
        reason=ExitReason.EXITED,
        pinned_digests=lab.pins(),
    )
    assert second.exit_record == first.exit_record
    assert second.completion == first.completion
    assert second.activation.metadata.exit_record == first.exit_record
    assert lab.bd.command_count(BD_UPDATE) == updates_before


def test_observe_reuses_the_exit_file_in_the_crash_window(lab: Lab) -> None:
    """An on-disk exit is the source of truth before its bd mirror lands."""
    exit_record = ExitRecord(
        exit_code=-15,
        ended_at="2026-08-25T12:00:00Z",
        reason=ExitReason.EXITED.value,
    )
    write_record(lab.paths.exit_file(lab.activation.activation_id), exit_record)
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE)
    observation = lab.observe(exit_code=0)
    assert observation.exit_record == exit_record
    assert observation.activation.metadata.exit_record == exit_record


def test_replay_recomputes_only_when_completion_is_absent(lab: Lab) -> None:
    """Replay uses durable completion, but re-runs §7 after an incomplete crash."""
    lab.commit_work()
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE)
    first = lab.observe(exit_code=0)
    replayed = lab.observer.replay(
        lab.reload(),
        lab.node,
        lab.profile,
        first.exit_record,
        pinned_digests=lab.pins(),
    )
    assert replayed.completion == first.completion
    lab.paths.completion(lab.activation.activation_id).unlink()
    recomputed = lab.observer.replay(
        lab.reload(),
        lab.node,
        lab.profile,
        first.exit_record,
        pinned_digests=lab.pins(),
    )
    assert recomputed.completion == first.completion
    assert lab.paths.completion(lab.activation.activation_id).exists()


def test_an_unknown_pre_attempt_state_retires_an_earlier_attribution(
    tmp_path: Path,
) -> None:
    """Micro-fix confirm (Sol): returning early left a PRIOR record authorizing.

    The attribution record is instance-scoped, so a bare `return None` on a
    corrupt dirty state kept the previous attempt's entries live — and a live
    probe then reset a path on that stale authority. Nothing attributable
    must mean an EMPTY record for this activation, carried forward from no one.
    """
    lab = Lab(tmp_path, in_repo=True)
    activation_id = lab.activation.activation_id
    stale = RunnerAttribution(
        activation_id="wf-earlier",
        observed_at="2026-01-01T00:00:00Z",
        head_commit=lab.base,
        entries=(DirtyEntry(path=FEATURE_FILE, digest="0" * 40, tracked=True),),
    )
    write_record(lab.paths.attribution_record, stale)
    lab.bd.rows[activation_id]["metadata"]["pre_attempt_dirty_state"] = (
        '{"entries": "not a list"}'
    )
    lab.activation = lab.reload()
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE)

    lab.observe(exit_code=0)

    attribution = read_record(lab.paths.attribution_record, RunnerAttribution)
    assert attribution is not None
    assert attribution.activation_id == activation_id
    assert attribution.entries == ()


def test_a_transient_bd_failure_on_the_exit_write_is_not_swallowed(
    lab: Lab,
) -> None:
    """Micro-fix confirm (Sol): `except BdioError` hid real transport failures.

    A bd that exits non-zero on the exit write is not the §8.1 race: nothing
    settled the activation and no exit record landed, so returning normally
    would report a mirrored exit that never happened and leave `dispatched`
    with only the exit FILE behind it. Only the two race members are absorbed,
    and only when the re-read proves the race; everything else propagates.
    """

    def fail() -> None:
        raise BdCommandError(("bd", "update"), 1, "dolt: connection reset", "update")

    lab.bd.pause_before(BD_UPDATE, fail)
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE)

    with pytest.raises(BdCommandError):
        lab.observe(exit_code=0)

    assert lab.reload().metadata.lifecycle is Lifecycle.DISPATCHED
    assert lab.reload().metadata.exit_record is None
