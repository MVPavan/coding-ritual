"""§5.4 precondition and §12 isolation, against real git working trees.

Drills 4 (reset before the rework dispatch), 5 (mid-reset idempotence) and 26
(in-repo dirty-tree refusal and attributed reset) live here. Real `git` rather
than a stubbed transport: the whole point of the precondition is what `git`
actually reports, and a fake status parser proves nothing about it.

The in-repo family is written against POSITIVE ATTRIBUTION, and the shape of
every test in it is the same: nothing is resettable until the WRAPPER has
recorded that it watched a runner produce exactly that content, and any later
divergence — a human edit, a human commit, a missing record — puts it back
behind tier-2 confirmation.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

from tests._supervisor import (
    blob_at,
    commit_all,
    head_of,
    make_git,
    runner_commit,
)
from tests._workspace import (
    CLEAN,
    CONFIRMED_AT,
    HUMAN_COMMITTED,
    HUMAN_FILE,
    HUMAN_TEXT,
    NESTED_DIR,
    NESTED_TEXT,
    RUNNER_FILE,
    SCRATCH_FILE,
    SCRATCH_TEXT,
    STRANGER_ACTIVATION,
    TRACKED_FILE,
    TRACKED_ORIGINAL,
    Fixture,
    attribute,
    confirmation_for,
    entry_for,
    in_repo,
    nested_checkout,
    worktree,
)
from workflow_interpreter.schema.models import IsolationMode
from workflow_interpreter.supervisor import (
    BandLock,
    ConfirmedPath,
    DirtySnapshot,
    DirtyTreeRefused,
    EntryKind,
    Git,
    GitCommandError,
    HumanConfirmation,
    LockUnavailable,
    PreconditionRefused,
    SnapshotFailed,
    WorkspaceRecord,
    encode_dirty_state,
    namespaced_ref,
)
from workflow_interpreter.supervisor.paths import read_record
from workflow_interpreter.supervisor.workspace import PRERESET_NAMESPACE

__all__ = ["in_repo", "worktree"]

FIFO_LINK = "pipe-link"
"""A symlink inside the repo naming a FIFO outside it — an ordinary `git
status` entry that `git hash-object` follows into a blocking open."""
FIFO_TIMEOUT_S = 2.0
"""Short enough that "it blocked until the timeout" and "it answered" are not
the same observation to a test."""


def _fifo_link(fixture: Fixture) -> None:
    """Leave a link to a FIFO in the human's tree, as their tooling does."""
    fifo = fixture.repo.parent / "outside.fifo"
    os.mkfifo(fifo)
    (fixture.repo / FIFO_LINK).symlink_to(fifo)


# --- worktree mode -------------------------------------------------------


def test_first_dispatch_creates_the_worktree_at_the_expected_head(
    worktree: Fixture,
) -> None:
    """§5.4: the per-instance worktree is created by the wrapper at first dispatch."""
    result = worktree.workspace.prepare(worktree.activation, worktree.node)

    assert result.reset_verified_commit == worktree.base
    assert result.pre_attempt_commit == worktree.base
    assert head_of(worktree.paths.worktree) == worktree.base
    record = read_record(worktree.paths.workspace_record, WorkspaceRecord)
    assert record is not None
    assert record.branch == f"wf/{worktree.root.root_id}"
    assert record.owner_activation_id == worktree.activation.activation_id
    assert record.read_only is False


def test_rework_dispatch_resets_head_and_tree(worktree: Fixture) -> None:
    """Drill 4: after a rejected attempt, the next dispatch observes a clean base."""
    worktree.workspace.prepare(worktree.activation, worktree.node)
    tree = worktree.paths.worktree
    (tree / RUNNER_FILE).write_text("rejected work\n", encoding="utf-8")
    ahead = commit_all(tree, "rejected attempt")
    (tree / "src" / "leftover.txt").write_text("junk\n", encoding="utf-8")
    assert ahead != worktree.base

    result = worktree.workspace.prepare(worktree.activation, worktree.node)

    assert result.reset_applied is True
    assert head_of(tree) == worktree.base
    assert not (tree / "src" / "leftover.txt").exists()
    assert not (tree / RUNNER_FILE).exists()


def test_precondition_is_idempotent(worktree: Fixture) -> None:
    """Drill 5: re-running the precondition converges instead of re-resetting."""
    worktree.workspace.prepare(worktree.activation, worktree.node)
    (worktree.paths.worktree / RUNNER_FILE).write_text("x\n", encoding="utf-8")

    first = worktree.workspace.prepare(worktree.activation, worktree.node)
    second = worktree.workspace.prepare(worktree.activation, worktree.node)

    assert first.reset_applied is True
    assert second.reset_applied is False
    assert first.reset_verified_commit == second.reset_verified_commit
    assert head_of(worktree.paths.worktree) == worktree.base


def test_missing_intended_base_commit_refuses(worktree: Fixture) -> None:
    """§7.4: a bd record naming a commit git does not have halts the instance."""
    ghost = worktree.activation.model_copy(
        update={
            "metadata": worktree.activation.metadata.model_copy(
                update={"intended_base_commit": "0" * 40}
            )
        }
    )
    with pytest.raises(PreconditionRefused, match="does not exist"):
        worktree.workspace.prepare(ghost, worktree.node)


def test_read_only_node_is_recorded_as_such(worktree: Fixture) -> None:
    """§5.4: a `writes = false` node gets a checkout marked read-only."""
    reviewer = worktree.node.model_copy(update={"writes": False})

    worktree.workspace.prepare(worktree.activation, reviewer)

    record = read_record(worktree.paths.workspace_record, WorkspaceRecord)
    assert record is not None
    assert record.read_only is True


# --- in-repo mode (§12) --------------------------------------------------


def test_in_repo_requires_the_execution_band(tmp_path: Path) -> None:
    """§12: no in-repo dispatch happens outside the single-flight band."""
    fixture = Fixture(tmp_path, IsolationMode.IN_REPO)

    with pytest.raises(PreconditionRefused, match="execution band"):
        fixture.workspace.prepare(fixture.activation, fixture.node)


def test_band_is_single_flight(tmp_path: Path) -> None:
    """§12: one active runner per repo path, ever."""
    fixture = Fixture(tmp_path, IsolationMode.IN_REPO)
    fixture.workspace.band.acquire()
    contender = BandLock(fixture.paths.band_lock)
    try:
        with pytest.raises(LockUnavailable):
            contender.acquire()
    finally:
        fixture.workspace.band.release()


def test_in_repo_refuses_to_reset_human_work(in_repo: Fixture) -> None:
    """Drill 26: uncommitted human edits block the reset; the work survives."""
    human = in_repo.repo / HUMAN_FILE
    human.write_text(HUMAN_TEXT, encoding="utf-8")

    with pytest.raises(DirtyTreeRefused) as refusal:
        in_repo.workspace.prepare(
            in_repo.activation,
            in_repo.node,
            prior_dirty_state=encode_dirty_state(
                DirtySnapshot(entries=(entry_for(in_repo, HUMAN_FILE),))
            ),
        )

    assert HUMAN_FILE in refusal.value.protected_paths
    assert human.read_text(encoding="utf-8") == HUMAN_TEXT


def test_in_repo_first_dispatch_treats_every_dirty_path_as_human(
    in_repo: Fixture,
) -> None:
    """§12: with no prior snapshot nothing can be shown to be the runner's."""
    (in_repo.repo / HUMAN_FILE).write_text(HUMAN_TEXT, encoding="utf-8")

    with pytest.raises(DirtyTreeRefused) as refusal:
        in_repo.workspace.prepare(in_repo.activation, in_repo.node)

    assert refusal.value.protected_paths == (HUMAN_FILE,)


def test_in_repo_resets_what_the_wrapper_attributed_to_the_runner(
    in_repo: Fixture,
) -> None:
    """Drill 26: TRACKED content the wrapper watched the runner leave is resettable.

    Tracked because that is now the whole resettable set in-repo: the content
    a reset destroys here is in the object store and `reset --hard` puts it
    back, which is exactly what untracked content cannot offer.
    """
    (in_repo.repo / TRACKED_FILE).write_text("runner output\n", encoding="utf-8")
    attribute(in_repo, TRACKED_FILE)

    result = in_repo.workspace.prepare(
        in_repo.activation, in_repo.node, prior_dirty_state=CLEAN
    )

    assert result.reset_applied is True
    assert (in_repo.repo / TRACKED_FILE).read_text(encoding="utf-8") == TRACKED_ORIGINAL
    assert result.pre_attempt_dirty_state is not None
    assert TRACKED_FILE in result.pre_attempt_dirty_state


def test_in_repo_refuses_human_work_created_while_the_runner_ran(
    in_repo: Fixture,
) -> None:
    """B2: a file that merely APPEARED during the run is not the runner's.

    The probed counterexample: the human writes untracked notes and edits a
    tracked file mid-run, and the next dispatch `git clean`s the notes away —
    they were in neither the prior snapshot nor the stash, so nothing was left
    of them at all. Nothing here is resettable: the human's two paths because
    the wrapper cannot attribute them, and the runner's own untracked file
    because untracked content is never auto-deleted whatever the evidence says.
    """
    first = in_repo.workspace.prepare(in_repo.activation, in_repo.node)
    (in_repo.repo / RUNNER_FILE).write_text("runner output\n", encoding="utf-8")
    attribute(in_repo, RUNNER_FILE)
    (in_repo.repo / HUMAN_FILE).write_text(HUMAN_TEXT, encoding="utf-8")
    (in_repo.repo / TRACKED_FILE).write_text(
        "value = 1\n# human edit\n", encoding="utf-8"
    )

    with pytest.raises(DirtyTreeRefused) as refusal:
        in_repo.workspace.prepare(
            in_repo.activation,
            in_repo.node,
            prior_dirty_state=first.pre_attempt_dirty_state,
        )

    assert set(refusal.value.protected_paths) == {HUMAN_FILE, TRACKED_FILE, RUNNER_FILE}
    assert (in_repo.repo / HUMAN_FILE).read_text(encoding="utf-8") == HUMAN_TEXT
    assert "# human edit" in (in_repo.repo / TRACKED_FILE).read_text(encoding="utf-8")


def test_the_runner_declaring_a_humans_untracked_file_does_not_release_it(
    in_repo: Fixture,
) -> None:
    """B2, round 2: the declaration is RUNNER-CONTROLLED, so it cannot be enough.

    The probed counterexample: the human writes `notes.md` mid-run and the
    runner — with no malice at all, building its manifest out of `git status` —
    declares it. All three "independent" attribution tests then pass on the
    human's file, and the next prepare `git clean`s it away. It was never
    committed, so there is nothing anywhere to get it back from.

    An untracked path is therefore never auto-deleted, whatever the evidence
    says. The runner's OWN untracked output is protected by the same rule, and
    that is the intended cost: the alternative is a rule the runner can steer.
    """
    first = in_repo.workspace.prepare(in_repo.activation, in_repo.node)
    (in_repo.repo / HUMAN_FILE).write_text(HUMAN_TEXT, encoding="utf-8")
    (in_repo.repo / RUNNER_FILE).write_text("runner output\n", encoding="utf-8")
    attribution = attribute(in_repo, HUMAN_FILE, RUNNER_FILE)

    with pytest.raises(DirtyTreeRefused) as refusal:
        in_repo.workspace.prepare(
            in_repo.activation,
            in_repo.node,
            prior_dirty_state=first.pre_attempt_dirty_state,
        )

    # The wrapper still RECORDS what it observed — the record is an
    # observation, and the policy is what refuses to act on it.
    assert attribution.digest_of(HUMAN_FILE) is not None
    assert set(refusal.value.protected_paths) == {HUMAN_FILE, RUNNER_FILE}
    assert (in_repo.repo / HUMAN_FILE).read_text(encoding="utf-8") == HUMAN_TEXT


def test_an_attributed_path_edited_since_is_protected_again(
    in_repo: Fixture,
) -> None:
    """B2: attribution is bound to CONTENT, so a later edit revokes it."""
    (in_repo.repo / TRACKED_FILE).write_text("runner output\n", encoding="utf-8")
    attribute(in_repo, TRACKED_FILE)
    (in_repo.repo / TRACKED_FILE).write_text(
        "a human kept working on it\n", encoding="utf-8"
    )

    with pytest.raises(DirtyTreeRefused) as refusal:
        in_repo.workspace.prepare(
            in_repo.activation, in_repo.node, prior_dirty_state=CLEAN
        )

    assert refusal.value.protected_paths == (TRACKED_FILE,)


def test_in_repo_refuses_to_move_head_off_an_unpinned_commit(
    in_repo: Fixture,
) -> None:
    """B3: a commit no wrapper ref pins is somebody else's, and survives.

    The probed counterexample: the human commits their own work between two
    attempts and the next precondition `reset --hard`s it away — no ownership
    test at all, and the commit pinned nowhere for them to find again.
    """
    in_repo.workspace.prepare(in_repo.activation, in_repo.node)
    (in_repo.repo / HUMAN_COMMITTED).parent.mkdir(parents=True, exist_ok=True)
    (in_repo.repo / HUMAN_COMMITTED).write_text(HUMAN_TEXT, encoding="utf-8")
    human = commit_all(in_repo.repo, "a chapter the human wrote")

    with pytest.raises(DirtyTreeRefused) as refusal:
        in_repo.workspace.prepare(
            in_repo.activation, in_repo.node, prior_dirty_state=CLEAN
        )

    assert refusal.value.protected_head == human
    assert head_of(in_repo.repo) == human
    assert (in_repo.repo / HUMAN_COMMITTED).read_text(encoding="utf-8") == HUMAN_TEXT


def test_in_repo_moves_head_off_a_commit_the_wrapper_pinned(
    in_repo: Fixture,
) -> None:
    """B3, the other side: wrapper-pinned lineage IS the licence to reset.

    The commit is made under the §7.4 runner identity, because that is now half
    of what makes it attributable at all — see
    `test_a_commit_the_human_made_is_not_this_attempts_artifact`.
    """
    in_repo.workspace.prepare(in_repo.activation, in_repo.node)
    (in_repo.repo / RUNNER_FILE).write_text("runner output\n", encoding="utf-8")
    runner_commit(in_repo.repo, "the attempt", in_repo.activation.activation_id)
    pinned = in_repo.workspace.pin_artifact(
        in_repo.activation, in_repo.node, declared=frozenset({RUNNER_FILE})
    )
    assert pinned is not None

    result = in_repo.workspace.prepare(
        in_repo.activation, in_repo.node, prior_dirty_state=CLEAN
    )

    assert result.reset_applied is True
    assert head_of(in_repo.repo) == in_repo.base


def test_in_repo_confirmation_releases_exactly_the_named_content(
    in_repo: Fixture,
) -> None:
    """§12: tier-2 confirmation names paths AND the content it saw.

    Tracked on purpose: `git stash create` does not capture untracked files
    (`Workspace._snapshot`), so this is the case where the snapshot commit is
    the thing that actually preserves the released work.
    """
    (in_repo.repo / TRACKED_FILE).write_text("human edit\n", encoding="utf-8")

    result = in_repo.workspace.prepare(
        in_repo.activation,
        in_repo.node,
        prior_dirty_state=encode_dirty_state(
            DirtySnapshot(entries=(entry_for(in_repo, TRACKED_FILE),))
        ),
        confirmation=confirmation_for(in_repo, TRACKED_FILE),
    )

    assert result.plan.protected == ()
    assert (in_repo.repo / TRACKED_FILE).read_text(encoding="utf-8") == "value = 1\n"
    snapshot = DirtySnapshot.model_validate_json(result.pre_attempt_dirty_state or "{}")
    assert snapshot.stash_commit is not None


def test_a_confirmation_does_not_release_content_written_after_it(
    in_repo: Fixture,
) -> None:
    """m21: a confirmation is bound to the bytes the human actually looked at."""
    (in_repo.repo / TRACKED_FILE).write_text(
        "what the human approved\n", encoding="utf-8"
    )
    stale = confirmation_for(in_repo, TRACKED_FILE)
    (in_repo.repo / TRACKED_FILE).write_text("what came later\n", encoding="utf-8")

    with pytest.raises(DirtyTreeRefused) as refusal:
        in_repo.workspace.prepare(
            in_repo.activation,
            in_repo.node,
            prior_dirty_state=CLEAN,
            confirmation=stale,
        )

    assert refusal.value.protected_paths == (TRACKED_FILE,)
    assert (in_repo.repo / TRACKED_FILE).read_text(
        encoding="utf-8"
    ) == "what came later\n"


def test_a_confirmation_bound_to_another_activation_releases_nothing(
    in_repo: Fixture,
) -> None:
    """m21/Sol#21: `activation_id` was carried and never read.

    A confirmation is scoped in three dimensions — path, content, attempt — and
    only two of them were checked, so one kept from an earlier attempt released
    identical content in a later one the human never looked at.
    """
    (in_repo.repo / TRACKED_FILE).write_text("human edit\n", encoding="utf-8")
    stranger = confirmation_for(in_repo, TRACKED_FILE).model_copy(
        update={"activation_id": STRANGER_ACTIVATION}
    )

    with pytest.raises(DirtyTreeRefused) as refusal:
        in_repo.workspace.prepare(
            in_repo.activation,
            in_repo.node,
            prior_dirty_state=CLEAN,
            confirmation=stranger,
        )

    assert refusal.value.protected_paths == (TRACKED_FILE,)
    assert in_repo.activation.activation_id != STRANGER_ACTIVATION


# --- the pre-destruction snapshot (§12) ----------------------------------


def test_a_reset_pins_a_snapshot_that_still_holds_what_it_deleted(
    worktree: Fixture,
) -> None:
    """B1: every reset is recoverable, INCLUDING the untracked content.

    Attribution is a judgement, and the judgement is made partly out of what
    the runner says about itself. So the reset is not allowed to be the last
    word: before the first destructive command, the whole dirty state —
    untracked files and all, which `stash create` cannot capture — is committed
    and pinned. `reset --hard` and `clean` then destroy nothing that is not
    reachable from a ref.
    """
    worktree.workspace.prepare(worktree.activation, worktree.node)
    tree = worktree.paths.worktree
    (tree / SCRATCH_FILE).write_text(SCRATCH_TEXT, encoding="utf-8")
    (tree / TRACKED_FILE).write_text("half-finished\n", encoding="utf-8")

    result = worktree.workspace.prepare(worktree.activation, worktree.node)

    assert result.reset_applied is True
    assert not (tree / SCRATCH_FILE).exists()
    assert (tree / TRACKED_FILE).read_text(encoding="utf-8") == TRACKED_ORIGINAL
    assert result.pre_reset_commit is not None
    ref = namespaced_ref(
        worktree.root.root_id,
        PRERESET_NAMESPACE,
        worktree.activation.activation_id,
    )
    git = make_git(worktree.config)
    assert git.ref_target(ref, cwd=worktree.repo) == result.pre_reset_commit
    assert blob_at(worktree.repo, result.pre_reset_commit, SCRATCH_FILE) == SCRATCH_TEXT
    assert (
        blob_at(worktree.repo, result.pre_reset_commit, TRACKED_FILE)
        == "half-finished\n"
    )


def test_a_second_reset_keeps_the_first_snapshot_reachable(
    worktree: Fixture,
) -> None:
    """One ref per activation, and it must not strand what it replaces.

    The previous snapshot is carried as a second parent, so the ref reaches
    every snapshot it has ever held rather than only the newest.
    """
    worktree.workspace.prepare(worktree.activation, worktree.node)
    tree = worktree.paths.worktree
    (tree / SCRATCH_FILE).write_text(SCRATCH_TEXT, encoding="utf-8")
    first = worktree.workspace.prepare(worktree.activation, worktree.node)
    (tree / SCRATCH_FILE).write_text("a second round of it\n", encoding="utf-8")

    second = worktree.workspace.prepare(worktree.activation, worktree.node)

    assert first.pre_reset_commit is not None
    assert second.pre_reset_commit != first.pre_reset_commit
    assert make_git(worktree.config).is_ancestor(
        first.pre_reset_commit, second.pre_reset_commit or "", cwd=worktree.repo
    )
    assert blob_at(worktree.repo, first.pre_reset_commit, SCRATCH_FILE) == SCRATCH_TEXT


def test_a_reset_refuses_when_its_snapshot_cannot_be_pinned(
    worktree: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B1: an unpinnable snapshot ABORTS the reset — it is never logged past.

    The undo is the thing that makes destroying attributed work acceptable at
    all, so proceeding without one is exactly the case this must refuse.
    """
    worktree.workspace.prepare(worktree.activation, worktree.node)
    tree = worktree.paths.worktree
    (tree / SCRATCH_FILE).write_text(SCRATCH_TEXT, encoding="utf-8")

    def refuse(*_: object, **__: object) -> str:
        raise GitCommandError("the object store is read-only")

    monkeypatch.setattr(Git, "snapshot_commit", refuse)

    with pytest.raises(SnapshotFailed, match="pre-destruction snapshot"):
        worktree.workspace.prepare(worktree.activation, worktree.node)

    assert (tree / SCRATCH_FILE).read_text(encoding="utf-8") == SCRATCH_TEXT


def test_a_snapshot_does_not_run_a_clean_filter(worktree: Fixture) -> None:
    """R8: snapshot bytes come from the worktree, never an attributes filter."""
    worktree.workspace.prepare(worktree.activation, worktree.node)
    tree = worktree.paths.worktree
    sentinel = tree.parent / "filter-ran"
    script = tree.parent / "filter.sh"
    script.write_text(
        "#!/bin/sh\nprintf filter-ran > \"$1\"\nsed 's/HELLO/MANGLED/'\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    (tree / ".gitattributes").write_text("* filter=evil\n", encoding="utf-8")
    commit_all(tree, "attributes")
    subprocess.run(
        ["git", "config", "filter.evil.clean", f"{script} {sentinel}"],
        cwd=tree,
        check=True,
        capture_output=True,
        text=True,
    )
    (tree / TRACKED_FILE).write_text("HELLO\n", encoding="utf-8")
    snapshot = make_git(worktree.config).snapshot_commit(
        message="filter-free snapshot",
        parents=(head_of(tree),),
        index_path=worktree.paths.snapshot_index,
        cwd=tree,
    )

    assert not sentinel.exists()
    assert blob_at(worktree.repo, snapshot, TRACKED_FILE) == "HELLO\n"


# --- directory entries: the shape `git hash-object` cannot answer --------


def test_a_nested_checkout_protects_instead_of_wedging_the_precondition(
    in_repo: Fixture,
) -> None:
    """Opus#18: `git status -uall` reports it as ONE entry naming a directory.

    `git hash-object -- vendorwork/` is `fatal: Unable to hash` (exit 128), so
    hashing every dirty path with no filter raised `GitCommandError` out of
    `prepare()` — through `Dispatcher.dispatch` and `Supervisor.run` — and the
    instance could never dispatch again until a human deleted the directory.
    Deterministic, and this repository's own `reference_harnesses/` shape
    triggers it. A directory is now its own kind: never hashed, and protected,
    so the answer is the §12 tier-2 refusal that names it.
    """
    nested = nested_checkout(in_repo)

    with pytest.raises(DirtyTreeRefused) as refusal:
        in_repo.workspace.prepare(in_repo.activation, in_repo.node)

    assert refusal.value.protected_paths == (f"{NESTED_DIR}/",)
    assert (nested / "a.txt").read_text(encoding="utf-8") == NESTED_TEXT


def test_a_declared_directory_is_recorded_without_being_hashed(
    in_repo: Fixture,
) -> None:
    """Opus#12: `record_attribution` spawned the same fatal, inside `observe()`.

    Between the exit file and `record_exit`, which left the activation
    `dispatched` on a child that had provably exited. The observation is still
    RECORDED — the wrapper does not edit what it saw — with the digest a
    directory actually has (none) and the kind that says why.
    """
    nested_checkout(in_repo)

    record = attribute(in_repo, f"{NESTED_DIR}/")

    entry = next(item for item in record.entries if item.path == f"{NESTED_DIR}/")
    assert entry.kind is EntryKind.DIRECTORY
    assert entry.digest == ""


def test_a_directory_is_never_resettable_even_when_a_human_released_it(
    in_repo: Fixture,
) -> None:
    """§12: a directory's `""` digest binds nothing, so it cannot be confirmed.

    Every directory hashes to the same empty digest, so a tier-2 confirmation
    naming one would authorize `clean -f -d` over whatever it holds LATER — the
    exact content binding that makes a confirmation narrower than a blanket
    "yes". The refusal therefore runs before the confirmation, not after it.
    """
    nested = nested_checkout(in_repo)
    attribute(in_repo, f"{NESTED_DIR}/")
    released = HumanConfirmation(
        activation_id=in_repo.activation.activation_id,
        confirmed=(ConfirmedPath(path=f"{NESTED_DIR}/", digest=""),),
        reason="the human said so",
        actor="human",
        confirmed_at=CONFIRMED_AT,
    )

    with pytest.raises(DirtyTreeRefused) as refusal:
        in_repo.workspace.prepare(
            in_repo.activation,
            in_repo.node,
            prior_dirty_state=CLEAN,
            confirmation=released,
        )

    assert refusal.value.protected_paths == (f"{NESTED_DIR}/",)
    assert (nested / "a.txt").read_text(encoding="utf-8") == NESTED_TEXT


def test_the_transport_never_hands_a_directory_to_hash_object(
    in_repo: Fixture,
) -> None:
    """The structural half of the same fix: no caller can wedge on it either.

    `git hash-object -- <dir>` exits 128, and the two §12 record builders are
    not the only places a path from `git status` reaches the transport. A
    directory has no blob, so the transport answers `NO_BLOB` — the same answer
    a deleted path gets, which is why the ENTRY carries the kind and the digest
    alone is never asked to distinguish them.

    The test follows symlinks because `git hash-object` does: probed, a symlink
    to a directory is the same `fatal: Unable to hash`, while a symlink to a
    file hashes that file and stays an ordinary entry.
    """
    nested = nested_checkout(in_repo)
    (in_repo.repo / "dirlink").symlink_to(nested)
    (in_repo.repo / "filelink").symlink_to(nested / "a.txt")
    git = make_git(in_repo.config)

    assert git.hash_working_file(f"{NESTED_DIR}/", cwd=in_repo.repo) == ""
    assert git.hash_working_file("dirlink", cwd=in_repo.repo) == ""
    assert git.hash_working_file("filelink", cwd=in_repo.repo) != ""


def test_the_transport_never_blocks_on_a_symlink_to_a_fifo(
    in_repo: Fixture,
) -> None:
    """Opus#15: the directory fix answered ONE shape of "this has no blob".

    `git status -uall` reports a symlink as an ordinary entry and `git
    hash-object` FOLLOWS it, so a link to a FIFO — or a socket, or
    `/dev/zero` — is handed to a `git` that then BLOCKS on the open. Worse than
    the directory's exit 128: it does not fail until `git_timeout_s`, and then
    every tick wedges `prepare` again for as long as the link is there. Only a
    regular file is hashed now, so the answer is immediate and is `NO_BLOB`.

    The short timeout is the assertion's teeth: without the guard this call
    spends the whole of it inside `git` and then raises.
    """
    _fifo_link(in_repo)
    git = make_git(in_repo.config.model_copy(update={"git_timeout_s": FIFO_TIMEOUT_S}))

    started = time.monotonic()
    assert git.hash_working_file(FIFO_LINK, cwd=in_repo.repo) == ""
    assert time.monotonic() - started < FIFO_TIMEOUT_S


def test_a_fifo_link_is_recorded_as_opaque_and_never_released(
    in_repo: Fixture,
) -> None:
    """§12: the same treatment a directory gets, for the same reason.

    Its digest is `""` and so is every other opaque entry's, so a tier-2
    confirmation naming this content binds nothing — it would release whatever
    the link points at LATER. The kind is what the refusal keys on, and the
    record states the shape honestly rather than calling a pipe a directory.
    """
    _fifo_link(in_repo)

    record = attribute(in_repo, FIFO_LINK)

    entry = next(item for item in record.entries if item.path == FIFO_LINK)
    assert entry.kind is EntryKind.NON_REGULAR
    assert entry.digest == ""
    released = HumanConfirmation(
        activation_id=in_repo.activation.activation_id,
        confirmed=(ConfirmedPath(path=FIFO_LINK, digest=""),),
        reason="the human said so",
        actor="human",
        confirmed_at=CONFIRMED_AT,
    )

    with pytest.raises(DirtyTreeRefused) as refusal:
        in_repo.workspace.prepare(
            in_repo.activation,
            in_repo.node,
            prior_dirty_state=CLEAN,
            confirmation=released,
        )

    assert FIFO_LINK in refusal.value.protected_paths


def test_an_in_repo_reset_snapshot_holds_the_humans_untracked_content(
    in_repo: Fixture,
) -> None:
    """Sol#1: the snapshot's CONTENT was only ever asserted in worktree mode.

    `_apply` is shared, so in-repo executes the same pin — but in-repo is the
    mode where the destroyed bytes are the HUMAN's, where a mistaken judgement
    has no undo of its own, and where the untracked content `stash create`
    cannot capture is exactly what a tier-2 release destroys. The claim "every
    reset is recoverable" is worth asserting where it matters most, so this
    test reads the bytes back out of the pinned commit rather than trusting
    that the shared path ran.
    """
    first = in_repo.workspace.prepare(in_repo.activation, in_repo.node)
    (in_repo.repo / SCRATCH_FILE).write_text(SCRATCH_TEXT, encoding="utf-8")
    (in_repo.repo / TRACKED_FILE).write_text("half-finished\n", encoding="utf-8")
    attribute(in_repo, TRACKED_FILE)

    result = in_repo.workspace.prepare(
        in_repo.activation,
        in_repo.node,
        prior_dirty_state=first.pre_attempt_dirty_state,
        confirmation=confirmation_for(in_repo, SCRATCH_FILE),
    )

    assert result.reset_applied is True
    assert not (in_repo.repo / SCRATCH_FILE).exists()
    assert (in_repo.repo / TRACKED_FILE).read_text(encoding="utf-8") == TRACKED_ORIGINAL
    assert result.pre_reset_commit is not None
    ref = namespaced_ref(
        in_repo.root.root_id,
        PRERESET_NAMESPACE,
        in_repo.activation.activation_id,
    )
    assert (
        make_git(in_repo.config).ref_target(ref, cwd=in_repo.repo)
        == result.pre_reset_commit
    )
    assert blob_at(in_repo.repo, result.pre_reset_commit, SCRATCH_FILE) == SCRATCH_TEXT
    assert (
        blob_at(in_repo.repo, result.pre_reset_commit, TRACKED_FILE)
        == "half-finished\n"
    )
