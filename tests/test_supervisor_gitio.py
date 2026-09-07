"""Strict git-helper contracts used by the supervisor's recovery paths."""

import subprocess
from collections.abc import Mapping
from hashlib import sha1
from pathlib import Path

import pytest

from tests._supervisor import (
    blob_at,
    commit_all,
    head_of,
    make_config,
    make_git,
    make_repo,
    tree_modes,
)
from workflow_interpreter.schema.models import Outcome
from workflow_interpreter.supervisor import GitCommandError, gitcmd, gitsnapshot
from workflow_interpreter.supervisor.gitcmd import GitResult, GitSubcommand


def _commit_outputs(
    repo: Path, root: Path, paths: tuple[str, ...], *, index_name: str = "outputs.index"
) -> tuple[object, str]:
    """Commit selected output bytes using the production P9 transport."""
    config = make_config(repo, root.parent)
    git = make_git(config)
    commit = git.commit_directory(
        paths,
        root=root,
        message="pin outputs",
        index_path=root.parent / index_name,
        cwd=repo,
    )
    return git, commit


def test_strict_git_helpers_distinguish_absence_from_git_failure(
    tmp_path: Path,
) -> None:
    """Missing objects answer conservatively while a broken git context raises."""
    repo = make_repo(tmp_path)
    config = make_config(repo, tmp_path)
    git = make_git(config)
    head = head_of(repo)
    (repo / "later.txt").write_text("later\n", encoding="utf-8")
    later = commit_all(repo, "later")
    missing = "0" * 40

    assert git.ref_target("refs/heads/missing", cwd=repo) is None
    assert git.is_ancestor(head, later, cwd=repo) is True
    assert git.is_ancestor(later, head, cwd=repo) is False
    assert git.commit_exists(missing, cwd=repo) is False
    assert git.commit_exists(head, cwd=repo) is True
    assert git.refs_under("refs/wf/missing/", cwd=repo) == ()

    with pytest.raises(GitCommandError):
        git.ref_target(head, cwd=repo)
    with pytest.raises(GitCommandError):
        git.commit_exists("short", cwd=repo)
    with pytest.raises(GitCommandError):
        git.refs_under("refs/", cwd=config.wrapper_root)


def test_commit_helpers_reject_non_commits_and_git_failures(tmp_path: Path) -> None:
    """A tree or unreadable object is never mistaken for a usable commit."""
    repo = make_repo(tmp_path)
    config = make_config(repo, tmp_path)
    git = make_git(config)
    head = head_of(repo)
    tree = git.tree_oid(head, cwd=repo)

    assert git.commit_exists(tree, cwd=repo) is False
    assert git.committer_email(head, cwd=repo) == "wf@test"

    with pytest.raises(GitCommandError):
        git.is_ancestor(head, head, cwd=config.wrapper_root)
    with pytest.raises(GitCommandError):
        git.commit_exists(head, cwd=config.wrapper_root)
    with pytest.raises(GitCommandError):
        git.committer_email("0" * 40, cwd=repo)


def test_terminal_worktree_removal_refuses_a_late_human_edit(tmp_path: Path) -> None:
    """A terminal cleanup must not force-remove a worktree made dirty after its check."""
    repo = make_repo(tmp_path)
    config = make_config(repo, tmp_path)
    git = make_git(config)
    worktree = tmp_path / "terminal-worktree"
    git.worktree_add_detached(worktree, head_of(repo), cwd=repo)
    human_file = worktree / "human.txt"
    human_file.write_text("keep me\n", encoding="utf-8")

    with pytest.raises(GitCommandError):
        git.worktree_remove(worktree, cwd=repo)

    assert human_file.read_text(encoding="utf-8") == "keep me\n"


def test_snapshot_chunks_hashing_without_losing_positional_blob_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R8: every low-budget chunk adds its own files to the same index."""
    repo = make_repo(tmp_path)
    config = make_config(repo, tmp_path)
    expected: dict[str, str] = {}
    for index in range(8):
        path = f"unique-{index}-{'x' * 65}.txt"
        value = f"content-{index}\n"
        (repo / path).write_text(value, encoding="utf-8")
        expected[path] = value
    monkeypatch.chdir(repo)
    repo_cwd = Path(".")
    git = make_git(config.model_copy(update={"repo_root": repo_cwd}))
    monkeypatch.setattr(gitcmd, "MAX_ARGV_BYTES", 200)
    staged = gitsnapshot.parse_stage_entries(
        git.run(GitSubcommand.LS_FILES, "-z", "--stage", cwd=repo_cwd).stdout
    )
    indexed = tuple(entry.path for entry in staged)
    untracked = tuple(
        path
        for path in git.run(
            GitSubcommand.LS_FILES,
            "-z",
            "--others",
            "--exclude-standard",
            cwd=repo_cwd,
        ).stdout.split("\0")
        if path and path not in indexed
    )
    expected_hash_chunks = gitcmd.chunk_argv(
        tuple(str(repo_cwd / path) for path in (*indexed, *untracked)),
        fixed=(GitSubcommand.HASH_OBJECT.value, "-w", "--no-filters", "--"),
    )
    original_run = git.run
    hashes = 0

    def counted_run(
        subcommand: GitSubcommand,
        *args: str,
        cwd: Path,
        check: bool = True,
        env: Mapping[str, str] | None = None,
    ) -> GitResult:
        nonlocal hashes
        if subcommand is GitSubcommand.HASH_OBJECT:
            hashes += 1
        return original_run(subcommand, *args, cwd=cwd, check=check, env=env)

    monkeypatch.setattr(git, "run", counted_run)
    snapshot = git.snapshot_commit(
        message="chunked snapshot",
        parents=(head_of(repo),),
        index_path=config.wrapper_root / "snapshot.index",
        cwd=repo_cwd,
    )

    assert hashes >= 2
    assert hashes == len(expected_hash_chunks)
    modes = tree_modes(repo, snapshot)
    assert set(expected).issubset(modes)
    assert {path: blob_at(repo, snapshot, path) for path in expected} == expected


def test_commit_directory_chunks_by_argv_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P9: every low-budget hash chunk contributes to one outputs tree."""
    repo = make_repo(tmp_path)
    root = tmp_path / "outputs"
    root.mkdir()
    expected = {f"unique-{index}.txt": f"content-{index}\n" for index in range(8)}
    for path, contents in expected.items():
        (root / path).write_text(contents, encoding="utf-8")
    monkeypatch.setattr(gitcmd, "MAX_ARGV_BYTES", 200)
    git, commit = _commit_outputs(repo, root, tuple(expected))

    assert tree_modes(repo, commit) == {path: "100644" for path in expected}
    assert {path: blob_at(repo, commit, path) for path in expected} == expected
    assert git.tree_oid(commit, cwd=repo)


def test_a_runner_gitattributes_cannot_run_a_clean_filter(tmp_path: Path) -> None:
    """P9 hashes output bytes without attribute-selected clean filters."""
    repo = make_repo(tmp_path)
    root = tmp_path / "outputs"
    root.mkdir()
    sentinel = tmp_path / "filter-ran"
    filter_program = tmp_path / "clean-filter.sh"
    filter_program.write_text(
        f"#!/bin/sh\nprintf ran > {sentinel}\nprintf mangled\n",
        encoding="utf-8",
    )
    filter_program.chmod(0o755)
    subprocess.run(
        ["git", "config", "filter.runner.clean", str(filter_program)],
        cwd=repo,
        check=True,
    )
    (root / ".gitattributes").write_text("result.txt filter=runner\n", encoding="utf-8")
    (root / "result.txt").write_text("runner bytes\n", encoding="utf-8")

    _, commit = _commit_outputs(repo, root, (".gitattributes", "result.txt"))

    assert not sentinel.exists()
    assert blob_at(repo, commit, "result.txt") == "runner bytes\n"


@pytest.mark.proc
def test_hash_working_file_uses_raw_runner_bytes_without_a_clean_filter(
    tmp_path: Path,
) -> None:
    """`runner bytes\\n` must not hash as the filter's `mangled\\n` output."""
    repo = make_repo(tmp_path)
    sentinel = tmp_path / "hash-filter-ran"
    filter_program = tmp_path / "hash-clean-filter.sh"
    filter_program.write_text(
        f"#!/bin/sh\nprintf ran > {sentinel}\nprintf mangled\n",
        encoding="utf-8",
    )
    filter_program.chmod(0o755)
    subprocess.run(
        ["git", "config", "filter.runner.clean", str(filter_program)],
        cwd=repo,
        check=True,
    )
    (repo / ".gitattributes").write_text("target.txt filter=runner\n", encoding="utf-8")
    (repo / "target.txt").write_text("runner bytes\n", encoding="utf-8")

    digest = make_git(make_config(repo, tmp_path)).hash_working_file(
        "target.txt", cwd=repo
    )

    raw = b"runner bytes\n"
    assert digest == sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    assert not sentinel.exists()


def test_a_glob_named_output_is_pinned_literally(tmp_path: Path) -> None:
    """P9 passes each collected output as data, never as a pathspec pattern."""
    repo = make_repo(tmp_path)
    root = tmp_path / "outputs"
    root.mkdir()
    (root / "*.txt").write_text("literal\n", encoding="utf-8")
    (root / "other.txt").write_text("not selected\n", encoding="utf-8")

    _, commit = _commit_outputs(repo, root, ("*.txt",))

    assert tree_modes(repo, commit) == {"*.txt": "100644"}
    assert blob_at(repo, commit, "*.txt") == "literal\n"


def test_the_outputs_snapshot_is_removed_after_a_successful_pin_and_kept_after_a_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P9 removes only a successfully committed capture for replay diagnosis."""
    from tests.test_supervisor_exit import Lab

    lab = Lab(tmp_path)
    snapshot = lab.paths.outputs_snapshot(lab.activation.activation_id)
    snapshot.mkdir()
    (snapshot / "success.txt").write_text("success\n", encoding="utf-8")

    pinned = lab.workspace.pin_outputs(lab.activation, ("success.txt",))

    assert pinned.identity is not None
    assert not snapshot.exists()
    snapshot.mkdir()
    (snapshot / "failure.txt").write_text("failure\n", encoding="utf-8")

    def fail(*_: object, **__: object) -> str:
        raise GitCommandError("object store unavailable")

    monkeypatch.setattr(lab.git, "commit_directory", fail)
    with pytest.raises(GitCommandError, match="object store unavailable"):
        lab.workspace.pin_outputs(lab.activation, ("failure.txt",))

    assert (snapshot / "failure.txt").read_text(encoding="utf-8") == "failure\n"


def test_outputs_snapshot_cleanup_does_not_hide_a_successful_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P9 cleanup is diagnostic-only: an unlink failure cannot undo the pin."""
    from tests.test_supervisor_exit import Lab
    from workflow_interpreter.supervisor import workspace as workspace_module

    lab = Lab(tmp_path)
    snapshot = lab.paths.outputs_snapshot(lab.activation.activation_id)
    snapshot.mkdir()
    (snapshot / "result.txt").write_text("output\n", encoding="utf-8")

    def refuse_cleanup(*_: object, **kwargs: object) -> None:
        if kwargs["ignore_errors"] is not True:
            raise PermissionError("injected cleanup failure")

    monkeypatch.setattr(workspace_module.shutil, "rmtree", refuse_cleanup)
    pinned = lab.workspace.pin_outputs(lab.activation, ("result.txt",))

    assert pinned.identity is not None
    assert (snapshot / "result.txt").read_text(encoding="utf-8") == "output\n"


def test_workspace_default_does_not_advance_the_instance_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P12 keeps branch movement explicitly opt-in for ordinary activations."""
    from tests.test_supervisor_exit import FEATURE_FILE, Lab

    lab = Lab(tmp_path)
    lab.commit_work(FEATURE_FILE)

    def unexpected_advance(*_: object, **__: object) -> object:
        raise AssertionError("default workspace advanced the instance branch")

    monkeypatch.setattr(lab.workspace, "advance_instance_branch", unexpected_advance)
    pinned = lab.workspace.pin_artifact(lab.activation, lab.node)

    assert pinned.identity is not None
    assert pinned.branch is None


def test_a_git_failure_checking_a_base_commit_is_not_a_missing_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R2 keeps a broken object store distinct from an absent base commit."""
    from tests._workspace import Fixture
    from workflow_interpreter.schema.models import IsolationMode
    from workflow_interpreter.supervisor import PreconditionRefused

    fixture = Fixture(tmp_path, IsolationMode.WORKTREE)

    def fail(*_: object, **__: object) -> bool:
        raise GitCommandError("cat-file failed")

    monkeypatch.setattr(fixture.workspace._git, "commit_exists", fail)

    with pytest.raises(GitCommandError) as raised:
        fixture.workspace.prepare(fixture.activation, fixture.node)

    assert not isinstance(raised.value, PreconditionRefused)


def test_a_previous_snapshot_read_failure_is_infra_not_a_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R2 maps a pre-reset ref failure to the retryable snapshot error."""
    from tests._workspace import SCRATCH_FILE, SCRATCH_TEXT, Fixture
    from workflow_interpreter.schema.models import IsolationMode
    from workflow_interpreter.supervisor import PreconditionRefused, SnapshotFailed

    fixture = Fixture(tmp_path, IsolationMode.WORKTREE)
    fixture.workspace.prepare(fixture.activation, fixture.node)
    tree = fixture.paths.worktree
    (tree / SCRATCH_FILE).write_text(SCRATCH_TEXT, encoding="utf-8")

    def fail(*_: object, **__: object) -> str | None:
        raise GitCommandError("show-ref failed")

    monkeypatch.setattr(fixture.workspace._git, "ref_target", fail)

    with pytest.raises(SnapshotFailed) as raised:
        fixture.workspace.prepare(fixture.activation, fixture.node)

    assert not isinstance(raised.value, PreconditionRefused)
    assert (tree / SCRATCH_FILE).read_text(encoding="utf-8") == SCRATCH_TEXT


def test_a_pin_listing_failure_is_not_misread_as_human_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R2 lets an in-repo lineage lookup failure escape the refusal path."""
    from tests._workspace import Fixture
    from workflow_interpreter.schema.models import IsolationMode
    from workflow_interpreter.supervisor import DirtyTreeRefused

    fixture = Fixture(tmp_path, IsolationMode.IN_REPO)
    fixture.workspace.band.acquire()
    (fixture.repo / "src" / "feature.py").write_text("human commit\n", encoding="utf-8")
    commit_all(fixture.repo, "human")

    def fail(*_: object, **__: object) -> tuple[str, ...]:
        raise GitCommandError("show-ref failed")

    monkeypatch.setattr(fixture.workspace._git, "refs_under", fail)

    with pytest.raises(GitCommandError) as raised:
        fixture.workspace.prepare(fixture.activation, fixture.node)

    assert not isinstance(raised.value, DirtyTreeRefused)


def test_an_artifact_lineage_failure_is_not_an_unattributed_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R2 does not convert an ancestry read failure into a permanent verdict."""
    from tests._workspace import Fixture
    from workflow_interpreter.schema.models import IsolationMode

    fixture = Fixture(tmp_path, IsolationMode.WORKTREE)
    fixture.workspace.prepare(fixture.activation, fixture.node)
    (fixture.paths.worktree / "src" / "feature.py").write_text(
        "runner commit\n", encoding="utf-8"
    )
    commit_all(fixture.paths.worktree, "runner")

    def fail(*_: object, **__: object) -> bool:
        raise GitCommandError("merge-base failed")

    monkeypatch.setattr(fixture.workspace._git, "is_ancestor", fail)

    with pytest.raises(GitCommandError):
        fixture.workspace.pin_artifact(fixture.activation, fixture.node)


def test_a_git_failure_inside_exit_pinning_is_replayable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R2 leaves a transient artifact-pin error as uncomputable evidence."""
    from tests.test_supervisor_exit import FEATURE_FILE, Lab
    from workflow_interpreter.supervisor import AuditFlag

    lab = Lab(tmp_path)
    lab.commit_work(FEATURE_FILE)
    lab.marker('{"outcome": "done"}')
    lab.effects(FEATURE_FILE)

    def fail(*_: object, **__: object) -> object:
        raise GitCommandError("update-ref failed")

    monkeypatch.setattr(lab.workspace, "pin_artifact", fail)

    observation = lab.observe()

    assert AuditFlag.VERIFY_UNRUNNABLE in observation.completion.audit_flags
    assert not lab.paths.completion(lab.activation.activation_id).exists()

    monkeypatch.undo()
    replayed = lab.observe()

    assert replayed.completion.outcome is Outcome.DONE
    assert replayed.artifact is not None
    assert lab.paths.completion(lab.activation.activation_id).exists()


def test_a_git_failure_during_orphan_pinning_leaves_recovery_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R2 never closes an unobserved activation when its preservation failed."""
    from tests.test_supervisor_recover import RUNNER_FILE, Lab

    lab = Lab(tmp_path)
    lab.effects(RUNNER_FILE)
    lab.orphan_commit(RUNNER_FILE)

    def fail(*_: object, **__: object) -> object:
        raise GitCommandError("object store unavailable")

    monkeypatch.setattr(lab.workspace, "pin_artifact", fail)

    resolution = lab.recovery.resolve(lab.activation, lab.node)

    assert resolution.closed is None
    assert resolution.halted is not None


@pytest.mark.proc
def test_status_paths_never_runs_an_attribute_selected_clean_filter(
    tmp_path: Path,
) -> None:
    """cr-o85.29: `status` content-compares, and that RAN the runner's program.

    A `.gitattributes` inside the tree is runner-writable, and the driver it
    names only has to exist in `.git/config` for `git status` to spawn it AS
    THE WRAPPER. Git content-compares every entry whose size still matches the
    index, so an UNTOUCHED tree is enough to fire it — no modification needed,
    which is why the first assertion here is on a clean checkout.
    """
    repo = make_repo(tmp_path)
    sentinel = tmp_path / "status-filter-ran"
    filter_program = tmp_path / "status-clean-filter.sh"
    filter_program.write_text(
        f"#!/bin/sh\nprintf ran > {sentinel}\ncat\n", encoding="utf-8"
    )
    filter_program.chmod(0o755)
    subprocess.run(
        ["git", "config", "filter.runner.clean", str(filter_program)],
        cwd=repo,
        check=True,
    )
    (repo / ".gitattributes").write_text("* filter=runner\n", encoding="utf-8")
    commit_all(repo, "runner attributes")
    git = make_git(make_config(repo, tmp_path))
    assert sentinel.exists(), "the rig is inert: the human's own commit never filtered"
    sentinel.unlink()

    assert git.status_paths(cwd=repo) == ()
    assert not sentinel.exists()

    (repo / "src" / "feature.py").write_text("value = 2\n", encoding="utf-8")
    (repo / "src" / "new.txt").write_text("new\n", encoding="utf-8")

    assert set(git.status_paths(cwd=repo)) == {
        ("src/feature.py", True),
        ("src/new.txt", False),
    }
    assert not sentinel.exists()


@pytest.mark.proc
def test_the_writing_git_calls_never_run_an_attribute_selected_smudge_filter(
    tmp_path: Path,
) -> None:
    """cr-o85.29's other direction: a checkout WRITES, and writing smudges.

    `worktree add` and `reset --hard` restore files through the same attribute
    machinery, so the driver a committed `.gitattributes` names runs as the
    wrapper — on the call that hands a runner its tree, and on the destructive
    one that takes it back.
    """
    repo = make_repo(tmp_path)
    sentinel = tmp_path / "smudge-filter-ran"
    filter_program = tmp_path / "smudge-filter.sh"
    filter_program.write_text(
        f"#!/bin/sh\nprintf ran > {sentinel}\ncat\n", encoding="utf-8"
    )
    filter_program.chmod(0o755)
    subprocess.run(
        ["git", "config", "filter.evil.smudge", str(filter_program)],
        cwd=repo,
        check=True,
    )
    (repo / ".gitattributes").write_text("* filter=evil\n", encoding="utf-8")
    head = commit_all(repo, "runner attributes")
    (repo / "src" / "feature.py").unlink()
    subprocess.run(["git", "checkout", "--", "src/feature.py"], cwd=repo, check=True)
    assert sentinel.exists(), "the rig is inert: a plain checkout never smudged"
    sentinel.unlink()
    git = make_git(make_config(repo, tmp_path))

    git.worktree_add(tmp_path / ".wf" / "live", "wf/live", head, cwd=repo)
    assert not sentinel.exists()

    git.worktree_add_detached(tmp_path / ".wf" / "graded", head, cwd=repo)
    assert not sentinel.exists()

    (repo / "src" / "feature.py").write_text("value = 2\n", encoding="utf-8")
    git.reset_hard(head, cwd=repo)

    assert not sentinel.exists()
    assert (repo / "src" / "feature.py").read_text(encoding="utf-8") == "value = 1\n"
