"""R8 pre-reset snapshot contracts against real Git repositories."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests._supervisor import (
    add_submodule,
    blob_at,
    commit_all,
    head_of,
    make_config,
    make_git,
    make_repo,
    tree_modes,
)
from workflow_interpreter.supervisor import gitsnapshot


def _snapshot(repo: Path, tmp_path: Path) -> str:
    """Create one pre-reset snapshot through the production Git transport."""
    config = make_config(repo, tmp_path)
    return make_git(config).snapshot_commit(
        message="snapshot",
        parents=(head_of(repo),),
        index_path=config.wrapper_root / "snapshot.index",
        cwd=repo,
    )


def test_snapshot_preserves_executable_and_symlink_modes(tmp_path: Path) -> None:
    """R8 restores executable files and links as Git's native tree modes."""
    repo = make_repo(tmp_path)
    script = repo / "run.sh"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    script.chmod(0o755)
    (repo / "link").symlink_to("src/feature.py")

    snapshot = _snapshot(repo, tmp_path)

    modes = tree_modes(repo, snapshot)
    assert modes["run.sh"] == "100755"
    assert modes["link"] == "120000"
    assert blob_at(repo, snapshot, "link") == "src/feature.py"


def test_snapshot_preserves_worktree_only_executable_mode(tmp_path: Path) -> None:
    """R8 opens its classification root on the worktree handed as `cwd`."""
    repo = make_repo(tmp_path)
    worktree = tmp_path / "worktree"
    subprocess.run(
        ["git", "worktree", "add", "--quiet", "--detach", str(worktree), "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    script = worktree / "run.sh"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    script.chmod(0o755)

    snapshot = _snapshot(worktree, tmp_path)

    assert tree_modes(repo, snapshot)["run.sh"] == "100755"


def test_snapshot_skips_an_untracked_nested_repository(tmp_path: Path) -> None:
    """An untracked nested repository cannot make a reset snapshot fail."""
    repo = make_repo(tmp_path)
    nested = repo / "nested"
    nested.mkdir()
    subprocess.run(
        ["git", "init", "--quiet", "--initial-branch=main"],
        cwd=nested,
        check=True,
        capture_output=True,
        text=True,
    )
    (repo / "src" / "feature.py").write_text("changed\n", encoding="utf-8")

    snapshot = _snapshot(repo, tmp_path)

    assert "nested" not in tree_modes(repo, snapshot)
    assert blob_at(repo, snapshot, "src/feature.py") == "changed\n"


def test_snapshot_records_a_fifo_at_a_tracked_path_as_deleted(tmp_path: Path) -> None:
    """A special replacement is an observed deletion, never a blocking hash."""
    repo = make_repo(tmp_path)
    target = repo / "src" / "feature.py"
    target.unlink()
    os.mkfifo(target)

    snapshot = _snapshot(repo, tmp_path)

    assert "src/feature.py" not in tree_modes(repo, snapshot)


def test_snapshot_omits_deleted_and_ignored_paths(tmp_path: Path) -> None:
    """R8 includes reset-risk content but never ignored files."""
    repo = make_repo(tmp_path)
    (repo / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    commit_all(repo, "ignore")
    (repo / "src" / "feature.py").unlink()
    (repo / "ignored.txt").write_text("ignored\n", encoding="utf-8")

    snapshot = _snapshot(repo, tmp_path)

    modes = tree_modes(repo, snapshot)
    assert "src/feature.py" not in modes
    assert "ignored.txt" not in modes


def test_snapshot_resolves_file_directory_replacements(tmp_path: Path) -> None:
    """Cacheinfo replacement removes stale file and directory index conflicts."""
    repo = make_repo(tmp_path)
    file_path = repo / "src" / "feature.py"
    file_path.unlink()
    file_path.mkdir()
    (file_path / "child").write_text("child\n", encoding="utf-8")

    snapshot = _snapshot(repo, tmp_path)

    assert tree_modes(repo, snapshot)["src/feature.py/child"] == "100644"


def test_snapshot_resolves_directory_file_replacements(tmp_path: Path) -> None:
    """Cacheinfo replacement also removes a tracked directory before a file."""
    repo = make_repo(tmp_path)
    directory = repo / "src"
    shutil.rmtree(directory)
    directory.write_text("replacement\n", encoding="utf-8")

    snapshot = _snapshot(repo, tmp_path)

    modes = tree_modes(repo, snapshot)
    assert modes["src"] == "100644"
    assert not any(path.startswith("src/") for path in modes)


def test_snapshot_removes_prereset_links_after_classification_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The temporary link directory is cleaned up before hashing can begin."""
    repo = make_repo(tmp_path)
    config = make_config(repo, tmp_path)

    def fail(*_: object, **__: object) -> object:
        raise OSError("injected classification failure")

    monkeypatch.setattr(gitsnapshot.fswalk, "classify_relative", fail)

    with pytest.raises(OSError, match="injected classification failure"):
        make_git(config).snapshot_commit(
            message="snapshot",
            parents=(head_of(repo),),
            index_path=config.wrapper_root / "snapshot.index",
            cwd=repo,
        )

    assert not (config.wrapper_root / "prereset.links").exists()


def test_snapshot_preserves_registered_submodule_gitlinks(tmp_path: Path) -> None:
    """A cached 160000 entry remains an outer-repository gitlink."""
    repo = make_repo(tmp_path)
    source = add_submodule(repo, "vendored")
    commit_all(repo, "submodule")
    cached_oid = subprocess.run(
        ["git", "rev-parse", "HEAD:vendored"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    (source / "module.txt").write_text("moved\n", encoding="utf-8")
    moved_oid = commit_all(source, "move submodule head")
    submodule = repo / "vendored"
    subprocess.run(
        ["git", "fetch", "--quiet"],
        cwd=submodule,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "checkout", "--quiet", "--detach", moved_oid],
        cwd=submodule,
        check=True,
        capture_output=True,
        text=True,
    )
    (repo / "src" / "feature.py").write_text("changed\n", encoding="utf-8")

    snapshot = _snapshot(repo, tmp_path)

    modes = tree_modes(repo, snapshot)
    snapshot_oid = subprocess.run(
        ["git", "rev-parse", f"{snapshot}:vendored"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert modes["vendored"] == "160000"
    assert snapshot_oid == cached_oid
    assert snapshot_oid != moved_oid
    assert not any(path.startswith("vendored/") for path in modes)
