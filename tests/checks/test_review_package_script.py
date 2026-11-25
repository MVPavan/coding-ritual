"""`playbooks/implement/review-package.sh`: a path given through the Claude
view `.claude/skills/...` packages the canonical `.agents/skills/...` file."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / ".agents/skills/mvp-mode/playbooks/implement/review-package.sh"
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


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args], env=ENV, check=True, capture_output=True
    )


def package(repo: Path, out: Path, *paths: str) -> str:
    subprocess.run(
        ["bash", str(SCRIPT), "full", "HEAD~1", str(out), "mixed", *paths],
        cwd=repo,
        env=ENV,
        check=True,
        capture_output=True,
    )
    return (out / "review-mixed.diff").read_text()


def _commit_edit(repo: Path) -> None:
    (repo / "README.md").write_text("readme v2\n")
    (repo / ".agents/skills/tdd/SKILL.md").write_text("tdd v2\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "edit")


@pytest.mark.parametrize("form", ["bare", "dot", "absolute"])
def test_a_claude_view_path_packages_the_committed_skill_change(
    tmp_path: Path, form: str
) -> None:
    repo = tmp_path / "repo"
    (repo / ".agents/skills/tdd").mkdir(parents=True)
    (repo / ".agents/skills/tdd/SKILL.md").write_text("tdd v1\n")
    (repo / ".claude").mkdir()
    (repo / ".claude/skills").symlink_to("../.agents/skills")
    (repo / "README.md").write_text("readme v1\n")
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    _commit_edit(repo)
    out = tmp_path / "review"
    skill = {
        "bare": ".claude/skills/tdd/SKILL.md",
        "dot": "./.claude/skills/tdd/SKILL.md",
        "absolute": str(repo / ".claude/skills/tdd/SKILL.md"),
    }[form]
    diff = package(repo, out, "README.md", skill)
    assert "+readme v2" in diff
    assert "+tdd v2" in diff
    assert (out / "snap-mixed/.agents/skills/tdd/SKILL.md").read_text() == "tdd v2\n"


def test_a_claude_view_path_spans_the_migration(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".claude/skills/tdd").mkdir(parents=True)
    (repo / ".claude/skills/tdd/SKILL.md").write_text("tdd v1\n")
    (repo / "README.md").write_text("readme v1\n")
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    (repo / ".agents").mkdir()
    git(repo, "mv", ".claude/skills", ".agents/skills")
    (repo / ".claude/skills").symlink_to("../.agents/skills")
    _commit_edit(repo)
    diff = package(repo, tmp_path / "review", ".claude/skills/tdd/SKILL.md")
    assert "-tdd v1" in diff
    assert "+tdd v2" in diff


def test_a_claude_view_path_is_literal(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".agents/skills/tdd").mkdir(parents=True)
    (repo / ".agents/skills/tdd/SKILL.md").write_text("tdd\n")
    (repo / ".claude").mkdir()
    (repo / ".claude/skills").symlink_to("../.agents/skills")
    git(repo, "init", "-q")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    git(repo, "commit", "-q", "--allow-empty", "-m", "empty")
    for name in ("options[2].md", "options2.md"):
        (repo / ".agents/skills/tdd" / name).write_text(f"{name}\n")
    out = tmp_path / "review"
    package(repo, out, "./.claude/skills/tdd/options[2].md")
    snap = out / "snap-mixed/.agents/skills/tdd"
    assert (snap / "options[2].md").is_file()
    assert not (snap / "options2.md").exists()
