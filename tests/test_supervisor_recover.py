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
    node_of,
    remove_proc_entry,
    runner_commit,
    write_proc_entry,
)
from workflow_interpreter.bdio import (
    ActivationRecord,
    ExitRecord,
    MintReason,
    Outcome,
)
from workflow_interpreter.schema.models import IsolationMode
from workflow_interpreter.supervisor import (
    EVIDENCE_EXIT_UNOBSERVED,
    EXIT_CODE_UNOBSERVED,
    DirtyTreeRefused,
    GitCommandError,
    Liveness,
    PinOutcome,
    Recovery,
    RecoveryCase,
    SteerIntent,
    SupervisorConfig,
    Workspace,
    WrapperPaths,
    activation_ref,
    namespaced_ref,
)
from workflow_interpreter.supervisor.paths import write_record
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
        self, tmp_path: Path, isolation: IsolationMode = IsolationMode.WORKTREE
    ) -> None:
        self.repo = make_repo(tmp_path)
        self.base = head_of(self.repo)
        self.config: SupervisorConfig = make_config(self.repo, tmp_path)
        _, self.store = make_store(tmp_path, self.base)
        self.root = make_root(self.store, self.repo, "recover-instance")
        self.paths: WrapperPaths = make_paths(self.config, self.root.root_id)
        self.clock = FrozenClock()
        self.git = make_git(self.config)
        self.workspace = Workspace(self.paths, self.git, self.clock)
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

    The second tick finds a CLOSED activation, so the intent beside it is
    residue and recovery does nothing at all — §5.6 is about
    dispatched-not-closed work. The remaining window (closed `steered`, the
    continuation not yet minted) is a half-finished transition the §4 frontier
    owns, exactly like every other close/mint pair.
    """
    _persist_steer_intent(lab)
    first = lab.recovery.resolve(lab.activation, lab.node)

    second = lab.recovery.resolve(lab.reload(), lab.node)

    assert first.steer is not None
    assert second.steer is None
    assert _continuations(lab) == [first.steer.continuation.activation.activation_id]


def test_a_steer_intent_beside_a_closed_activation_is_residue(lab: Lab) -> None:
    """A finished steer's intent file must not re-open a settled activation."""
    _persist_steer_intent(lab)
    lab.recovery.resolve(lab.activation, lab.node)

    classification = lab.recovery.classify(lab.reload())

    assert classification.case is not RecoveryCase.STEER_PENDING
    assert classification.steer_intent is None


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
    beads = lab.store.reads.instance_beads(lab.root.root_id)
    from workflow_interpreter.bdio.reads import activations_of

    return [
        record.activation_id
        for record in activations_of(beads)
        if record.activation_id != lab.activation.activation_id
    ]
