"""§5.6 recovery: three cases, decided by evidence, never by a crash loop.

Drills 3 (exit file as the crash-window fallback), 17 (wrapper and child killed
mid-run → `error_transport` + `exit_unobserved` + orphan commit pinned) and 18
(malformed artifacts still classify deterministically).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._supervisor import (
    BOOT_ID,
    IMPLEMENT,
    FrozenClock,
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
    remove_proc_entry,
    runner_commit,
    write_proc_entry,
)
from workflow_interpreter.bdio import (
    ActivationRecord,
    ExitRecord,
    Lifecycle,
    MintReason,
    Outcome,
)
from workflow_interpreter.schema.models import IsolationMode
from workflow_interpreter.supervisor import (
    EVIDENCE_EXIT_UNOBSERVED,
    EXIT_CODE_UNOBSERVED,
    DirtyTreeRefused,
    GitCommandError,
    LaunchReceipt,
    LaunchReceiptState,
    Liveness,
    PinOutcome,
    Recovery,
    RecoveryCase,
    SteerIntent,
    SupervisorConfig,
    WrapperPaths,
    activation_ref,
    namespaced_ref,
)
from workflow_interpreter.supervisor.artifact import INSTANCE_BRANCH_REF
from workflow_interpreter.supervisor.paths import read_record, write_record
from workflow_interpreter.supervisor.steer import instructions_digest
from workflow_interpreter.supervisor.workspace import ORPHAN_NAMESPACE

RUNNER_FILE = "src/orphan.py"
HUMAN_FILE = "docs/human-chapter.md"
OTHER_BOOT_ID = "boot-after-the-reboot"
STEER_REASON = "the runner is looping on the same test"
STEER_INSTRUCTIONS = "stop looping"


class Lab:
    """A dispatched activation the wrapper has lost track of."""

    def __init__(
        self,
        tmp_path: Path,
        isolation: IsolationMode = IsolationMode.WORKTREE,
        *,
        advance_branch: bool = False,
    ) -> None:
        self.repo = make_repo(tmp_path)
        self.base = head_of(self.repo)
        self.config: SupervisorConfig = make_config(self.repo, tmp_path)
        _, self.store = make_store(tmp_path, self.base)
        self.root = make_root(self.store, self.repo, "recover-instance")
        self.paths: WrapperPaths = make_paths(self.config, self.root.root_id)
        self.clock = FrozenClock()
        self.git = make_git(self.config)
        self.workspace = make_workspace(
            self.paths, self.git, self.clock, advance_branch=advance_branch
        )
        self.node = node_of(self.root.definition.document, IMPLEMENT).model_copy(
            update={"isolation": isolation}
        )
        if isolation is IsolationMode.IN_REPO:
            self.workspace.band.acquire()
        self.pid = dead_pid()
        minted = self.store.mint_activation(self.root.root_id, entry_mint())
        self.activation: ActivationRecord = self.store.record_dispatch(
            minted.activation.activation_id,
            handle_for(
                self.pid, log_path=str(self.paths.log(minted.activation.activation_id))
            ),
        )
        self.paths.ensure_activation_dir(self.activation.activation_id)
        self.workspace.prepare(self.activation, self.node)
        self.recovery = Recovery(
            self.config, self.paths, self.store, self.workspace, self.clock
        )

    @property
    def tree(self) -> Path:
        """Where this activation's runner worked."""
        return self.workspace.path_for(self.node)

    def reload(self) -> ActivationRecord:
        """Re-read the activation from bd."""
        return self.store.reads.load_activation(self.activation.activation_id)

    def alive(self) -> None:
        """Make the handle's process look alive and provably ours."""
        write_proc_entry(self.config.proc_root, self.pid)

    def orphan_commit(self, path: str = RUNNER_FILE) -> str:
        """A commit the dead attempt left behind with nothing referencing it.

        Made under the §7.4 runner identity, which is what a real child's
        environment carries — the human's own identity is the OTHER case, and
        `test_recovery_quarantines_a_commit_the_human_made` is where it lives.
        """
        target = self.tree / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("half done\n", encoding="utf-8")
        return runner_commit(self.tree, "orphan", self.activation.activation_id)

    def effects(self, *paths: str) -> None:
        """The `$WF_EFFECTS_FILE` the dead runner left behind (§6, §7.5)."""
        self.paths.effects(self.activation.activation_id).write_text(
            json.dumps({"paths": list(paths)}), encoding="utf-8"
        )


@pytest.fixture
def lab(tmp_path: Path) -> Lab:
    """A dispatched activation whose child is already gone."""
    return Lab(tmp_path)


def test_a_bd_exit_record_is_case_one(lab: Lab) -> None:
    """§5.6.1: the exit was mirrored; §7 takes over from there."""
    lab.store.record_exit(
        lab.activation.activation_id,
        ExitRecord(exit_code=0, ended_at="2026-08-25T12:05:00Z", reason="exited"),
    )

    classification = lab.recovery.classify(lab.reload())

    assert classification.case is RecoveryCase.EXIT_RECORDED
    assert classification.exit_from_file is False


def test_a_minted_activation_is_not_launched_and_never_closed(lab: Lab) -> None:
    """R5: recovery does not turn an unlaunched activation into transport noise."""
    minted = lab.activation.model_copy(
        update={
            "metadata": lab.activation.metadata.model_copy(
                update={"lifecycle": Lifecycle.MINTED}
            )
        }
    )

    result = lab.recovery.resolve(minted, lab.node)

    assert result.classification.case is RecoveryCase.NOT_LAUNCHED
    assert result.closed is None
    assert (
        lab.store.reads.load_activation(minted.activation_id).metadata.outcome is None
    )


def test_abort_pending_receipt_is_terminated_until_it_becomes_aborted(lab: Lab) -> None:
    """Barrier cleanup owns its receipt even when bd never recorded a runner."""
    handle = lab.activation.metadata.handle
    assert handle is not None
    write_record(
        lab.paths.receipt(lab.activation.activation_id),
        LaunchReceipt(
            launch_id="barrier-abort",
            root_id=lab.root.root_id,
            activation_id=lab.activation.activation_id,
            argv=("/bin/false",),
            cwd=str(lab.repo),
            handle=handle,
            state=LaunchReceiptState.ABORT_PENDING,
        ),
    )

    classification = lab.recovery.classify(lab.reload())
    result = lab.recovery.resolve(lab.reload(), lab.node)
    receipt = read_record(
        lab.paths.receipt(lab.activation.activation_id), LaunchReceipt
    )

    assert classification.case is RecoveryCase.ABORT_PENDING
    assert result.termination is not None
    assert result.termination.confirmed_dead is True
    assert receipt is not None
    assert receipt.state is LaunchReceiptState.ABORTED
    assert receipt.abort_exit_code == result.termination.exit_code


def test_the_exit_file_is_the_crash_window_fallback(lab: Lab) -> None:
    """Drill 3: the child exited, bd never heard — the on-disk file still counts."""
    write_record(
        lab.paths.exit_file(lab.activation.activation_id),
        ExitRecord(exit_code=0, ended_at="2026-08-25T12:05:00Z", reason="exited"),
    )

    classification = lab.recovery.classify(lab.activation)

    assert classification.case is RecoveryCase.EXIT_RECORDED
    assert classification.exit_from_file is True
    assert classification.exit_record is not None


def test_a_provably_live_process_is_case_two(lab: Lab) -> None:
    """§5.6.2: pid, boot id and start time all agree — the wrapper's flags govern."""
    lab.alive()

    classification = lab.recovery.classify(lab.activation)

    assert classification.case is RecoveryCase.RUNNING
    assert classification.proof is not None
    assert classification.proof.status is Liveness.ALIVE


def test_a_reused_pid_is_not_alive(lab: Lab) -> None:
    """§5.3: same pid, different start time — case 3, and never signalled."""
    write_proc_entry(lab.config.proc_root, lab.pid, start_time="7777777")

    classification = lab.recovery.classify(lab.activation)

    assert classification.case is RecoveryCase.DEAD_WITHOUT_EXIT
    assert classification.proof is not None
    assert classification.proof.status is Liveness.IDENTITY_MISMATCH


def test_a_reboot_invalidates_the_handle(lab: Lab) -> None:
    """§5.3: boot id defeats a pid that is alive on a host that restarted."""
    lab.alive()
    lab.config.boot_id_path.write_text(f"{OTHER_BOOT_ID}\n", encoding="utf-8")

    classification = lab.recovery.classify(lab.activation)

    assert classification.case is RecoveryCase.DEAD_WITHOUT_EXIT
    assert classification.proof is not None
    assert classification.proof.boot_id_matches is False
    assert BOOT_ID != OTHER_BOOT_ID


def test_a_truncated_exit_file_classifies_toward_case_three(lab: Lab) -> None:
    """Drill 18: malformed is recorded and treated as absent, never raised."""
    lab.paths.exit_file(lab.activation.activation_id).write_text(
        '{"exit_code": 0, "ended', encoding="utf-8"
    )

    classification = lab.recovery.classify(lab.activation)

    assert classification.case is RecoveryCase.DEAD_WITHOUT_EXIT
    assert classification.malformed == ("exit-file",)


def test_a_corrupt_log_tail_is_decoded_not_refused(lab: Lab) -> None:
    """Drill 18: a truncated JSONL tail is evidence for a human, not a parser."""
    lab.paths.log(lab.activation.activation_id).write_bytes(
        b'{"type":"message","text":"\xff\xfe truncated'
    )

    classification = lab.recovery.classify(lab.activation)

    assert classification.case is RecoveryCase.DEAD_WITHOUT_EXIT
    assert "truncated" in classification.log_tail


def test_case_three_closes_error_transport_and_pins_the_orphan(lab: Lab) -> None:
    """Drill 17: `error_transport`, `evidence: exit_unobserved`, orphan pinned."""
    commit = lab.orphan_commit()

    resolution = lab.recovery.resolve(lab.activation, lab.node)

    assert resolution.classification.case is RecoveryCase.DEAD_WITHOUT_EXIT
    assert resolution.orphan is not None
    assert resolution.orphan.commit_oid == commit
    assert resolution.closed is not None
    assert resolution.closed.metadata.outcome is Outcome.ERROR_TRANSPORT
    evidence = resolution.closed.metadata.evidence
    assert evidence is not None
    assert evidence.note == EVIDENCE_EXIT_UNOBSERVED
    assert evidence.artifact is not None
    ref = activation_ref(lab.root.root_id, lab.activation.activation_id)
    assert lab.git.ref_target(ref, cwd=lab.repo) == commit


def test_case_three_without_a_commit_still_closes(lab: Lab) -> None:
    """§5.6: no partial artifact is required for the transport failure to close."""
    resolution = lab.recovery.resolve(lab.activation, lab.node)

    assert resolution.orphan is None
    assert resolution.closed is not None
    assert resolution.closed.metadata.outcome is Outcome.ERROR_TRANSPORT


def test_resolve_leaves_a_running_activation_alone(lab: Lab) -> None:
    """§5.6.2: a live child is not something recovery may close."""
    lab.alive()

    resolution = lab.recovery.resolve(lab.activation, lab.node)

    assert resolution.classification.case is RecoveryCase.RUNNING
    assert resolution.closed is None
    assert lab.reload().metadata.outcome is None


def test_resolve_is_idempotent(lab: Lab) -> None:
    """A re-tick after a case-3 close re-finds the recorded exit, not a second one."""
    first = lab.recovery.resolve(lab.activation, lab.node)

    second = lab.recovery.resolve(lab.reload(), lab.node)

    assert first.closed is not None
    assert second.classification.case is RecoveryCase.EXIT_RECORDED
    assert second.closed is None


def test_the_unobserved_exit_code_is_a_sentinel_never_zero(lab: Lab) -> None:
    """m16: the one thing this record must not be able to say is "it succeeded"."""
    lab.recovery.resolve(lab.activation, lab.node)

    recorded = lab.reload().metadata.exit_record
    assert recorded is not None
    assert recorded.exit_code == EXIT_CODE_UNOBSERVED
    assert recorded.reason == "exit_unobserved"


# --- the answers that are not answers (B6, M9) ---------------------------


def test_an_unanswerable_liveness_question_halts_instead_of_closing(
    lab: Lab,
) -> None:
    """B6: EACCES on `/proc` is not evidence of death.

    Classifying a transient read error as DEAD closed the activation
    `error_transport` and let the §10.2 retry exec a second child beside the
    survivor. A directory where `stat` should be reproduces the failure without
    depending on a permission the test runner may not be able to drop.
    """
    remove_proc_entry(lab.config.proc_root, lab.pid)
    (lab.config.proc_root / str(lab.pid) / "stat").mkdir(parents=True)

    resolution = lab.recovery.resolve(lab.activation, lab.node)

    assert resolution.classification.case is RecoveryCase.INDETERMINATE
    assert resolution.closed is None
    assert resolution.halted is not None
    assert lab.reload().metadata.outcome is None


def test_recovery_quarantines_a_commit_it_cannot_attribute(tmp_path: Path) -> None:
    """M15 through §5.6, and the chain it completed (probed).

    Recovery passed NO declaration, so in-repo `pin_artifact`'s attribution
    test was skipped on exactly the path M15 named: the wrapper died, the HUMAN
    committed their own work in their own checkout, and recovery pinned that
    commit as this activation's artifact. The ref then WAS wrapper lineage, so
    B3's HEAD protection saw `head_protected = False` and the next precondition
    `reset --hard`ed the human's commit away.

    Now the commit is quarantined instead: reachable forever under `orphan/`,
    named in the evidence NOTE rather than as an artifact, and invisible to
    `_is_runner_lineage` — so the next prepare still refuses.
    """
    lab = Lab(tmp_path, IsolationMode.IN_REPO)
    human = lab.orphan_commit(HUMAN_FILE)

    resolution = lab.recovery.resolve(lab.activation, lab.node)

    assert resolution.pin is not None
    assert resolution.pin.outcome is PinOutcome.QUARANTINED
    assert resolution.orphan is None
    assert resolution.closed is not None
    assert resolution.closed.metadata.outcome is Outcome.ERROR_TRANSPORT
    evidence = resolution.closed.metadata.evidence
    assert evidence is not None
    assert evidence.artifact is None
    assert evidence.note is not None
    assert human in evidence.note
    quarantine = namespaced_ref(
        lab.root.root_id, ORPHAN_NAMESPACE, lab.activation.activation_id
    )
    assert lab.git.ref_target(quarantine, cwd=lab.repo) == human
    assert (
        lab.git.ref_target(
            activation_ref(lab.root.root_id, lab.activation.activation_id), cwd=lab.repo
        )
        is None
    )

    with pytest.raises(DirtyTreeRefused) as refusal:
        lab.workspace.prepare(lab.reload(), lab.node)

    assert refusal.value.protected_head == human
    assert head_of(lab.repo) == human
    assert (lab.repo / HUMAN_FILE).exists()


def test_recovery_pins_a_commit_the_dead_runner_declared(tmp_path: Path) -> None:
    """M15's other side: the manifest the dead runner left IS the evidence.

    §5.6 has to keep working for the case it exists for — a wrapper that died
    after its runner committed — so the declaration is threaded from the effects
    file rather than simply skipped.
    """
    lab = Lab(tmp_path, IsolationMode.IN_REPO)
    lab.effects(RUNNER_FILE)
    commit = lab.orphan_commit()

    resolution = lab.recovery.resolve(lab.activation, lab.node)

    assert resolution.pin is not None
    assert resolution.pin.outcome is PinOutcome.PINNED
    assert resolution.orphan is not None
    assert resolution.orphan.commit_oid == commit
    ref = activation_ref(lab.root.root_id, lab.activation.activation_id)
    assert lab.git.ref_target(ref, cwd=lab.repo) == commit


def test_recovery_does_not_close_when_the_orphan_pin_fails(
    lab: Lab, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M9: §5.6 pins FIRST because the close authorizes the next reset.

    Swallowing the failure and closing anyway left a real commit with no ref —
    for the next precondition to reset past and a gc to collect. Nothing is
    closed until the commit is pinned or proven absent.
    """
    commit = lab.orphan_commit()

    def refuse(*_: object, **__: object) -> None:
        raise GitCommandError("the object store is unreadable")

    monkeypatch.setattr(lab.workspace, "pin_artifact", refuse)

    resolution = lab.recovery.resolve(lab.activation, lab.node)

    assert resolution.closed is None
    assert resolution.halted is not None
    assert lab.reload().metadata.outcome is None
    assert head_of(lab.paths.worktree) == commit


# --- a steer that crashed halfway (M10) ----------------------------------


def test_a_crashed_steer_is_finished_rather_than_called_a_transport_failure(
    lab: Lab,
) -> None:
    """M10: recovery never read `steer-intent.json`, so a deliberate kill
    classified as §5.6 case 3 — `error_transport`, an infra retry spent, and
    the continuation the human asked for never minted at all.
    """
    _persist_steer_intent(lab)

    resolution = lab.recovery.resolve(lab.activation, lab.node)

    assert resolution.classification.case is RecoveryCase.STEER_PENDING
    assert resolution.closed is not None
    assert resolution.closed.metadata.outcome is Outcome.STEERED
    assert resolution.steer is not None
    assert resolution.steer.continuation.created is True


def test_finishing_a_crashed_steer_mints_exactly_one_continuation(lab: Lab) -> None:
    """Drill 14: however many ticks find the intent, one continuation exists.

    The second recovery re-finds the continuation through the same idempotency
    key, so a closed `steered` activation stays safe to finish until its
    continuation exists.
    """
    _persist_steer_intent(lab)
    first = lab.recovery.resolve(lab.activation, lab.node)

    second = lab.recovery.resolve(lab.reload(), lab.node)

    assert first.steer is not None
    assert second.steer is not None
    assert not second.steer.continuation.created
    assert _continuations(lab) == [first.steer.continuation.activation.activation_id]


def test_recovery_rebuilds_a_persisted_steer_request_from_the_root_pin(
    lab: Lab,
) -> None:
    """A legacy intent cannot make crash recovery re-mint a divergent vendor."""
    intent = _persist_steer_intent(lab)
    divergent = intent.model_copy(
        update={
            "continuation": intent.continuation.model_copy(
                update={"runner_profile": "legacy-runner", "model": "legacy-model"}
            )
        }
    )
    write_record(lab.paths.steer_intent(lab.activation.activation_id), divergent)

    resolution = lab.recovery.resolve(lab.activation, lab.node)

    assert resolution.steer is not None
    continuation = resolution.steer.continuation.activation.metadata
    assert continuation.runner_profile == "fake"
    assert continuation.model == "fake-model"


def test_a_steer_intent_beside_a_closed_activation_stays_recoverable(lab: Lab) -> None:
    """A closed `steered` row preserves its intent for an idempotent re-mint."""
    _persist_steer_intent(lab)
    lab.recovery.resolve(lab.activation, lab.node)

    classification = lab.recovery.classify(lab.reload())

    assert classification.case is RecoveryCase.STEER_PENDING
    assert classification.steer_intent is not None


def test_recovery_records_instance_branch_divergence(tmp_path: Path) -> None:
    """R5: a moved instance ref closes with the routing-visible deviation."""
    lab = Lab(tmp_path, IsolationMode.IN_REPO, advance_branch=True)
    lab.effects(RUNNER_FILE)
    (lab.repo / "src" / "other.py").write_text("other\n", encoding="utf-8")
    moved = runner_commit(lab.repo, "other branch", "other-activation")
    lab.git.reset_hard(lab.base, cwd=lab.repo)
    lab.orphan_commit()
    branch = INSTANCE_BRANCH_REF.format(root_id=lab.root.root_id)
    lab.git.update_ref(branch, moved, cwd=lab.repo)

    resolution = lab.recovery.resolve(lab.activation, lab.node)

    assert resolution.closed is not None
    deviations = resolution.closed.metadata.deviations
    assert len(deviations) == 1
    assert deviations[0].kind == "instance_branch_diverged"


def test_recovery_records_missing_instance_branch_as_note(tmp_path: Path) -> None:
    """R5: a deleted instance ref is a note-only reconciliation condition."""
    lab = Lab(tmp_path, IsolationMode.IN_REPO, advance_branch=True)
    lab.effects(RUNNER_FILE)
    lab.orphan_commit()

    resolution = lab.recovery.resolve(lab.activation, lab.node)

    assert resolution.closed is not None
    evidence = resolution.closed.metadata.evidence
    assert evidence is not None
    assert "instance branch missing" in (evidence.note or "")
    assert resolution.closed.metadata.deviations == ()


def _persist_steer_intent(lab: Lab) -> SteerIntent:
    """A durable §8.1 intent for a steer whose process already died."""
    intent = SteerIntent(
        activation_id=lab.activation.activation_id,
        reason=STEER_REASON,
        instructions=STEER_INSTRUCTIONS,
        instructions_digest=instructions_digest(STEER_INSTRUCTIONS),
        requested_at="2026-08-25T12:01:00Z",
        continuation=entry_mint(
            mint_reason=MintReason.STEER_CONTINUATION,
            predecessor_activation_id=lab.activation.activation_id,
        ),
    )
    write_record(lab.paths.steer_intent(lab.activation.activation_id), intent)
    return intent


def _continuations(lab: Lab) -> list[str]:
    """Every activation of this instance that is not the steered one."""
    beads = lab.store.reads.instance_records(lab.root.root_id)
    from workflow_interpreter.bdio.reads import activations_of

    return [
        record.activation_id
        for record in activations_of(beads)
        if record.activation_id != lab.activation.activation_id
    ]


def test_interrupted_dirty_writer_is_recoverable_before_retry(lab: Lab) -> None:
    """Dirty bytes survive case-three close/reset without becoming an artifact."""
    (lab.tree / "src/feature.py").write_text("unfinished tracked\n")
    (lab.tree / RUNNER_FILE).write_text("unfinished untracked\n")
    result = lab.recovery.resolve(lab.activation, lab.node)
    assert result.closed is not None
    assert result.closed.metadata.outcome is Outcome.ERROR_TRANSPORT
    assert result.orphan is None
    record = lab.workspace.read_recovery(lab.activation)
    assert record is not None and record.pinned
    assert record.observed_head == lab.base
    assert record.intended_base == lab.base
    assert (
        lab.git.blob_text(f"{record.commit}:{RUNNER_FILE}", cwd=lab.repo)
        == "unfinished untracked\n"
    )
    retry = lab.store.mint_activation(
        lab.root.root_id,
        entry_mint(
            mint_reason=MintReason.INFRA_RETRY,
            predecessor_activation_id=lab.activation.activation_id,
        ),
    ).activation
    lab.workspace.prepare(retry, lab.node)
    (lab.tree / RUNNER_FILE).write_text("successor work\n")
    assert lab.workspace.preserve_interrupted(lab.activation, lab.node) == record
    assert (
        lab.git.blob_text(f"{record.commit}:src/feature.py", cwd=lab.repo)
        == "unfinished tracked\n"
    )
    assert (lab.tree / RUNNER_FILE).read_text() == "successor work\n"


def test_interrupted_pin_failure_remains_retryable(
    lab: Lab, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed pin leaves the writer open and the original files intact."""
    from workflow_interpreter.supervisor import SnapshotFailed

    (lab.tree / RUNNER_FILE).write_text("recover me\n")
    original = lab.git.update_ref

    def fail(ref: str, commit: str, *, cwd: Path) -> None:
        if "/recovery/" in ref:
            raise GitCommandError("injected recovery pin failure")
        original(ref, commit, cwd=cwd)

    monkeypatch.setattr(lab.git, "update_ref", fail)
    with pytest.raises(SnapshotFailed):
        lab.recovery.resolve(lab.activation, lab.node)
    assert not lab.reload().metadata.is_settled
    assert (lab.tree / RUNNER_FILE).read_text() == "recover me\n"
    monkeypatch.setattr(lab.git, "update_ref", original)
    result = lab.recovery.resolve(lab.reload(), lab.node)
    assert result.closed is not None
    assert result.closed.metadata.outcome is Outcome.ERROR_TRANSPORT
    assert lab.workspace.read_recovery(lab.activation).pinned


def test_recovery_chains_divergent_bytes_and_keeps_prior_pin_on_failure(
    lab: Lab, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tree identity, not commit timestamps, decides idempotency and chaining."""
    from workflow_interpreter.supervisor import SnapshotFailed

    path = lab.tree / RUNNER_FILE
    path.write_text("first\n")
    first = lab.workspace.preserve_interrupted(lab.activation, lab.node)
    assert first is not None and first.pinned
    original = lab.git.update_ref

    def refuse(ref: str, commit: str, *, cwd: Path) -> None:
        raise GitCommandError("injected ref failure")

    monkeypatch.setattr(lab.git, "update_ref", refuse)
    assert lab.workspace.preserve_interrupted(lab.activation, lab.node) == first
    path.write_text("second\n")
    with pytest.raises(SnapshotFailed):
        lab.workspace.preserve_interrupted(lab.activation, lab.node)
    assert lab.git.ref_target(first.ref, cwd=lab.repo) == first.commit
    assert path.read_text() == "second\n"
    monkeypatch.setattr(lab.git, "update_ref", original)
    second = lab.workspace.preserve_interrupted(lab.activation, lab.node)
    assert second is not None and second.pinned
    assert lab.git.is_ancestor(first.commit, second.commit, cwd=lab.repo)
    assert lab.git.blob_text(f"{first.commit}:{RUNNER_FILE}", cwd=lab.repo) == "first\n"
    assert (
        lab.git.blob_text(f"{second.commit}:{RUNNER_FILE}", cwd=lab.repo) == "second\n"
    )


def test_recovery_refuses_live_foreign_and_unowned_content(lab: Lab) -> None:
    """No live/successor bytes acquire an old producer's identity."""
    from workflow_interpreter.supervisor import SnapshotFailed

    (lab.tree / RUNNER_FILE).write_text("owned work\n")
    write_proc_entry(lab.config.proc_root, lab.pid)
    with pytest.raises(SnapshotFailed, match="confirmed process death"):
        lab.workspace.preserve_interrupted(lab.activation, lab.node)
    assert lab.workspace.read_recovery(lab.activation) is None
    remove_proc_entry(lab.config.proc_root, lab.pid)
    foreign = lab.activation.model_copy(
        update={
            "metadata": lab.activation.metadata.model_copy(
                update={"wf_root_id": "wf-foreign"}
            )
        }
    )
    with pytest.raises(SnapshotFailed, match="foreign"):
        lab.workspace.preserve_interrupted(foreign, lab.node)
    lab.paths.workspace_record.unlink()
    unavailable = lab.workspace.preserve_interrupted(lab.activation, lab.node)
    assert (
        unavailable is not None and unavailable.unavailable and not unavailable.pinned
    )
    assert lab.git.ref_target(unavailable.ref, cwd=lab.repo) is None
    assert (lab.tree / RUNNER_FILE).read_text() == "owned work\n"


def test_clean_and_readonly_work_need_no_recovery_pin(lab: Lab) -> None:
    """Do not create snapshots for clean or read-only exits."""
    assert lab.workspace.preserve_interrupted(lab.activation, lab.node) is None
    (lab.tree / RUNNER_FILE).write_text("not writer content\n")
    assert (
        lab.workspace.preserve_interrupted(
            lab.activation, lab.node.model_copy(update={"writes": False})
        )
        is None
    )
    assert not lab.paths.recovery_snapshot(lab.activation.activation_id).exists()


@pytest.mark.parametrize("already_preserved", [False, True])
def test_in_repo_recovery_does_not_capture_another_roots_writer(
    tmp_path: Path, already_preserved: bool
) -> None:
    """The shared band owner outranks a stale per-instance workspace record."""
    from workflow_interpreter.supervisor import LockUnavailable

    lab = Lab(tmp_path, IsolationMode.IN_REPO)
    path = lab.repo / RUNNER_FILE
    prior = None
    if already_preserved:
        path.write_text("old producer\n")
        prior = lab.workspace.preserve_interrupted(lab.activation, lab.node)
        path.unlink()
    lab.workspace.band.release()
    successor_root = make_root(lab.store, lab.repo, "successor-instance")
    successor_paths = make_paths(lab.config, successor_root.root_id)
    successor_workspace = make_workspace(successor_paths, lab.git, lab.clock)
    successor = lab.store.mint_activation(
        successor_root.root_id, entry_mint()
    ).activation
    successor_paths.ensure_activation_dir(successor.activation_id)
    with successor_workspace.band:
        successor_workspace.prepare(successor, lab.node)
        path.write_text("another roots live writer\n")
        with pytest.raises(LockUnavailable):
            lab.workspace.preserve_interrupted(lab.activation, lab.node)
    # Even after the successor wrapper releases its lock, its ownership persists.
    record = lab.workspace.preserve_interrupted(lab.activation, lab.node)
    assert path.read_text() == "another roots live writer\n"
    assert record is not None
    if already_preserved:
        assert record == prior
        assert (
            lab.git.blob_text(f"{record.commit}:{RUNNER_FILE}", cwd=lab.repo)
            == "old producer\n"
        )
    else:
        assert record.unavailable and not record.pinned
        assert lab.git.ref_target(record.ref, cwd=lab.repo) is None
    assert not successor_paths.recovery_snapshot(successor.activation_id).exists()


@pytest.mark.parametrize("pinned_write", [False, True])
def test_divergent_recovery_record_failure_preserves_history_and_retries(
    lab: Lab, monkeypatch: pytest.MonkeyPatch, pinned_write: bool
) -> None:
    """Both durable-record crash windows retain files and the prior snapshot."""
    from pydantic import BaseModel

    from workflow_interpreter.supervisor import SnapshotFailed
    from workflow_interpreter.supervisor import workspace as workspace_module
    from workflow_interpreter.supervisor.models import RecoverySnapshot

    path = lab.tree / RUNNER_FILE
    path.write_text("first producer bytes\n")
    first = lab.workspace.preserve_interrupted(lab.activation, lab.node)
    assert first is not None and first.pinned
    path.write_text("later producer bytes\n")
    original = workspace_module.write_record

    def refuse(path: Path, record: BaseModel) -> None:
        if isinstance(record, RecoverySnapshot) and record.pinned == pinned_write:
            raise OSError("injected record persistence failure")
        original(path, record)

    monkeypatch.setattr(workspace_module, "write_record", refuse)
    with pytest.raises(SnapshotFailed, match="persistence failure"):
        lab.recovery.resolve(lab.activation, lab.node)
    assert not lab.reload().metadata.is_settled
    assert path.read_text() == "later producer bytes\n"
    pinned = lab.git.ref_target(first.ref, cwd=lab.repo)
    assert pinned is not None
    assert lab.git.is_ancestor(first.commit, pinned, cwd=lab.repo)
    monkeypatch.setattr(workspace_module, "write_record", original)
    assert lab.recovery.resolve(lab.reload(), lab.node).closed is not None
    final = lab.workspace.read_recovery(lab.activation)
    assert final is not None and final.pinned
    assert lab.git.is_ancestor(first.commit, final.commit, cwd=lab.repo)
    assert (
        lab.git.blob_text(f"{first.commit}:{RUNNER_FILE}", cwd=lab.repo)
        == "first producer bytes\n"
    )
    assert (
        lab.git.blob_text(f"{final.commit}:{RUNNER_FILE}", cwd=lab.repo)
        == "later producer bytes\n"
    )


def test_recovery_rejects_mismatched_observed_head(lab: Lab) -> None:
    """Producer evidence must bind the recorded HEAD to its snapshot parent."""
    from workflow_interpreter.supervisor import SnapshotFailed

    (lab.tree / RUNNER_FILE).write_text("producer bytes\n")
    record = lab.workspace.preserve_interrupted(lab.activation, lab.node)
    assert record is not None and record.pinned
    write_record(
        lab.paths.recovery_snapshot(lab.activation.activation_id),
        record.model_copy(update={"observed_head": record.commit}),
    )
    with pytest.raises(SnapshotFailed, match="head identity"):
        lab.workspace.preserve_interrupted(lab.activation, lab.node)
    assert lab.git.ref_target(record.ref, cwd=lab.repo) == record.commit
    assert (lab.tree / RUNNER_FILE).read_text() == "producer bytes\n"


def test_failed_successor_reset_retains_previous_producer_ownership(
    lab: Lab, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A refused pre-reset pin does not relabel the preceding writer's bytes."""
    from workflow_interpreter.supervisor import SnapshotFailed, WorkspaceRecord

    path = lab.tree / RUNNER_FILE
    path.write_text("previous producer work\n")
    lab.store.close_activation(lab.activation.activation_id, Outcome.ERROR_TRANSPORT)
    successor = lab.store.mint_activation(
        lab.root.root_id,
        entry_mint(
            mint_reason=MintReason.INFRA_RETRY,
            predecessor_activation_id=lab.activation.activation_id,
        ),
    ).activation
    lab.paths.ensure_activation_dir(successor.activation_id)
    original = lab.git.update_ref

    def refuse(ref: str, commit: str, *, cwd: Path) -> None:
        if "/prereset/" in ref:
            raise GitCommandError("injected pre-reset failure")
        original(ref, commit, cwd=cwd)

    monkeypatch.setattr(lab.git, "update_ref", refuse)
    with pytest.raises(SnapshotFailed):
        lab.workspace.prepare(successor, lab.node)
    owner = read_record(lab.paths.workspace_record, WorkspaceRecord)
    assert (
        owner is not None and owner.owner_activation_id == lab.activation.activation_id
    )
    record = lab.workspace.preserve_interrupted(lab.activation, lab.node)
    assert record is not None and record.pinned
    assert lab.git.blob_text(f"{record.commit}:{RUNNER_FILE}", cwd=lab.repo) == (
        "previous producer work\n"
    )
    assert path.read_text() == "previous producer work\n"


def test_private_toolchain_survives_until_recovery_closes_dead_runner(lab: Lab) -> None:
    """Crash files are retained while alive and deleted only after classified close."""
    private = lab.paths.activation_dir(lab.activation.activation_id) / "toolchain"
    private.mkdir()
    (private / "payload").write_text("runner mutable")
    receipt = private.parent / "toolchain-seed.json"
    receipt.write_text("retained provenance")
    lab.alive()
    running = lab.recovery.resolve(lab.activation, lab.node)
    assert running.closed is None
    assert private.exists()
    remove_proc_entry(lab.config.proc_root, lab.pid)
    closed = lab.recovery.resolve(lab.activation, lab.node)
    assert closed.closed is not None
    assert not private.exists()
    assert receipt.read_text() == "retained provenance"


def test_cleanup_retries_after_close_without_touching_other_activation(
    lab: Lab,
) -> None:
    """Recovery can retry a crash after durable close but before cache deletion."""
    from workflow_interpreter.supervisor.toolchain_cleanup import cleanup_toolchain

    resolution = lab.recovery.resolve(lab.activation, lab.node)
    assert resolution.closed is not None
    private = lab.paths.activation_dir(lab.activation.activation_id) / "toolchain"
    private.mkdir()
    (private / "payload").write_text("left after close")
    other = private.parent.parent / "other" / "toolchain"
    other.mkdir(parents=True)
    (other / "payload").write_text("another activation")
    cleanup_toolchain(lab.paths, resolution.closed)
    cleanup_toolchain(lab.paths, resolution.closed)
    assert not private.exists()
    assert (other / "payload").read_text() == "another activation"


def test_cleanup_removes_unpublished_staging_only_after_close(lab: Lab) -> None:
    """A crash during copying leaves no complete cache but still needs cleanup."""
    from workflow_interpreter.supervisor.toolchain_cleanup import cleanup_toolchain

    staged = lab.paths.activation_dir(lab.activation.activation_id) / ".toolchain-crash"
    staged.mkdir()
    (staged / "partial").write_text("partial private copy")
    cleanup_toolchain(lab.paths, lab.activation)
    assert staged.exists()
    result = lab.recovery.resolve(lab.activation, lab.node)
    assert result.closed is not None
    assert not staged.exists()


def test_cleanup_failure_is_reported_and_retryable(
    lab: Lab,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deletion failure cannot erase provenance or prevent a later retry."""
    import shutil

    from structlog.testing import capture_logs

    from workflow_interpreter.supervisor.toolchain_cleanup import cleanup_toolchain

    result = lab.recovery.resolve(lab.activation, lab.node)
    assert result.closed is not None
    private = lab.paths.activation_dir(lab.activation.activation_id) / "toolchain"
    private.mkdir()
    (private / "payload").write_text("private")
    original = shutil.rmtree

    def fail(*args: object, **kwargs: object) -> None:
        """Model a transient host filesystem error."""
        raise OSError("disk busy")

    monkeypatch.setattr(shutil, "rmtree", fail)
    with capture_logs() as logs:
        cleanup_toolchain(lab.paths, result.closed)
    assert any("disk busy" in entry.get("error", "") for entry in logs)
    assert private.exists()
    monkeypatch.setattr(shutil, "rmtree", original)
    cleanup_toolchain(lab.paths, result.closed)
    assert not private.exists()


def test_closed_live_runner_defers_cleanup_until_death(lab: Lab) -> None:
    """A durable close can precede process death without blocking the driver."""
    from workflow_interpreter.supervisor.toolchain_cleanup import cleanup_toolchain

    lab.alive()
    closed = lab.store.close_activation(
        lab.activation.activation_id, Outcome.ERROR_TRANSPORT
    )
    private = lab.paths.activation_dir(closed.activation_id) / "toolchain"
    private.mkdir()
    pending = private.parent / "toolchain-cleanup.json"
    cleanup_toolchain(lab.paths, closed)
    assert private.exists()
    assert "pending" in pending.read_text()
    remove_proc_entry(lab.config.proc_root, lab.pid)
    cleanup_toolchain(lab.paths, closed)
    assert not private.exists()
    assert not pending.exists()
