"""`playbooks/worktree-cleanup/audit.py` on a real temporary repository."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / ".claude/skills/mvp-mode/playbooks/worktree-cleanup/audit.py"
)
ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
}


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(cwd), *args],
        env=ENV,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def commit(cwd: Path, name: str) -> None:
    (cwd / name).write_text("x\n")
    git(cwd, "add", name)
    git(cwd, "commit", "-qm", name)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Main plus one worktree in each state the audit must tell apart."""
    main = tmp_path / "main"
    main.mkdir()
    git(main, "init", "-q", "-b", "main")
    (main / ".gitignore").write_text("build/\n")
    git(main, "add", ".gitignore")
    commit(main, "base")

    def worktree(name: str, *extra: str) -> Path:
        path = tmp_path / name
        git(main, "worktree", "add", "-q", *extra, str(path))
        return path

    merged = worktree("merged", "-b", "merged")
    (merged / "build").mkdir()
    (merged / "build" / "out").write_text("x\n")
    commit(worktree("unmerged", "-b", "unmerged"), "ahead")
    (worktree("dirty", "-b", "dirty") / "base").write_text("edited\n")
    (worktree("scratch", "-b", "scratch") / "note").write_text("x\n")
    commit(worktree("detached", "--detach"), "floating")
    worktree("detached-merged", "--detach")
    worktree("locked", "-b", "locked")
    git(main, "worktree", "lock", str(tmp_path / "locked"))
    shutil.rmtree(worktree("gone", "-b", "gone"))
    return main


def audit(repo: Path, *extra: str) -> dict[str, dict[str, Any]]:
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), "--json", *extra],
        env=ENV,
        capture_output=True,
        text=True,
        check=True,
    )
    rows = json.loads(done.stdout)["worktrees"]
    return {Path(row["path"]).name: row for row in rows}


def test_each_state_is_classified(repo: Path) -> None:
    rows = audit(repo, "--base", "main")
    assert {name: row["bucket"] for name, row in rows.items()} == {
        "main": "main",
        "merged": "propose",
        "unmerged": "unmerged",
        "dirty": "wip",
        "scratch": "scratch",
        "detached": "detached",
        "detached-merged": "propose",
        "locked": "locked",
        "gone": "prunable",
    }


def test_details_a_proposal_needs_are_reported(repo: Path) -> None:
    rows = audit(repo, "--base", "main")
    assert rows["merged"]["ignored"] == ["build/"]
    assert rows["merged"]["last_activity"]
    assert rows["dirty"]["wip"] == ["base"]
    assert rows["scratch"]["scratch"] == ["note"]
    assert rows["detached"]["on_a_ref"] is False
    assert rows["detached-merged"]["on_a_ref"] is True


def test_nothing_is_proposed_without_a_base(repo: Path) -> None:
    rows = audit(repo)
    assert rows["merged"]["bucket"] == "unknown"
    assert rows["merged"]["merge"] == "unknown"


def test_the_worktree_the_audit_runs_in_is_never_proposed(repo: Path) -> None:
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "--base", "main", "--json"],
        cwd=repo.parent / "merged",
        env=ENV,
        capture_output=True,
        text=True,
        check=True,
    )
    rows = {Path(r["path"]).name: r for r in json.loads(done.stdout)["worktrees"]}
    assert rows["merged"]["bucket"] == "current"


def test_nothing_is_changed(repo: Path) -> None:
    root = repo.parent

    def snapshot() -> tuple[str, str, list[str], float]:
        return (
            git(repo, "worktree", "list", "--porcelain"),
            git(repo, "for-each-ref"),
            sorted(
                str(p.relative_to(root))
                for p in root.rglob("*")
                if ".git" not in p.parts
            ),
            (root / "dirty" / "base").stat().st_mtime,
        )

    before = snapshot()
    audit(repo, "--base", "main")
    assert snapshot() == before
    assert "gone" in before[0]  # the prunable record survives the audit


def test_a_worktree_relative_base_means_the_selected_repos_commit(repo: Path) -> None:
    rows = audit(repo, "--base", "HEAD")
    assert rows["unmerged"]["bucket"] == "unmerged"
    assert rows["merged"]["bucket"] == "propose"
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), "--base", "HEAD"],
        env=ENV,
        capture_output=True,
        text=True,
        check=True,
    )
    assert done.stdout.startswith("base: HEAD\n")  # the ref the owner gave


def test_removing_one_missing_worktree_leaves_the_other_record(repo: Path) -> None:
    root = repo.parent
    git(repo, "worktree", "add", "-q", "-b", "gone2", str(root / "gone2"))
    shutil.rmtree(root / "gone2")

    git(repo, "worktree", "remove", str(root / "gone2"))

    listed = git(repo, "worktree", "list", "--porcelain")
    assert str(root / "gone2") not in listed
    assert str(root / "gone") in listed
    assert audit(repo, "--base", "main")["gone"]["bucket"] == "prunable"
