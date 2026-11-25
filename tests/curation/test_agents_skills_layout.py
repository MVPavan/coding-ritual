"""The skill tree lives in `.agents/skills`; `.claude/skills` is a Claude view of
it (one directory link, or one link per skill). Readers that go through git or
do not follow links must still find the playbooks and skills, at the current
revision and at a revision before the migration."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from curation.registry import config as config_mod
from curation.registry.catalogs import build_ours
from curation.registry.config import RegistryConfig
from curation.registry.steps import playbook_at

PLAYBOOK = """\
---
trigger: A defect to fix.
steps:
  - id: fix#1
    when: always
    calls: [{to: "skill:tdd"}]
---
# Fix
"""

SKILL = """\
---
name: tdd
description: Test first.
---
# TDD
"""


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.invalid",
        },
    )


def _migrated_repo(repo: Path, layout: str) -> None:
    """Commit 1: the skills under `.claude/skills`. Commit 2: moved to
    `.agents/skills` with the Claude view `layout` (`dir` or `per-skill`)."""
    _git(repo, "init", "-q")
    old = repo / ".claude" / "skills"
    (old / "mvp-mode" / "playbooks").mkdir(parents=True)
    (old / "mvp-mode" / "SKILL.md").write_text("---\nname: mvp-mode\n---\n", "utf-8")
    (old / "mvp-mode" / "playbooks" / "fix.md").write_text(PLAYBOOK, "utf-8")
    (old / "tdd").mkdir()
    (old / "tdd" / "SKILL.md").write_text(SKILL, "utf-8")
    _git(repo, "add", ".claude")
    _git(repo, "commit", "-q", "-m", "before")
    (repo / ".agents").mkdir()
    _git(repo, "mv", ".claude/skills", ".agents/skills")
    if layout == "dir":
        (repo / ".claude" / "skills").symlink_to("../.agents/skills")
    else:
        (repo / ".claude" / "skills").mkdir()
        for name in ("mvp-mode", "tdd"):
            (repo / ".claude" / "skills" / name).symlink_to(
                f"../../.agents/skills/{name}"
            )
    _git(repo, "add", ".claude/skills")
    _git(repo, "commit", "-q", "-m", "after")


@pytest.fixture(params=["dir", "per-skill"])
def cfg(
    request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> RegistryConfig:
    _migrated_repo(tmp_path, request.param)
    monkeypatch.setattr(config_mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(config_mod, "HL_DIR", tmp_path / "harness_lifecycle")
    return RegistryConfig.default()


def test_playbook_at_head_reads_the_real_tree(cfg: RegistryConfig) -> None:
    head = playbook_at(cfg, "fix", "HEAD")
    assert head is not None
    assert [s.id for s in head.steps] == ["fix#1"]


def test_playbook_at_pre_migration_revision(cfg: RegistryConfig) -> None:
    before = playbook_at(cfg, "fix", "HEAD~1")
    assert before is not None
    assert [s.id for s in before.steps] == ["fix#1"]


def test_build_ours_counts_the_skills(cfg: RegistryConfig) -> None:
    ours = build_ours(cfg)
    ids = {c.logical_id for c in ours.capabilities}
    assert {"skill:skills/tdd", "skill:skills/mvp-mode"} <= ids
    assert ours.counts["skill"]["logical"] == 2


def test_the_claude_view_resolves_to_the_real_skill_tree() -> None:
    """This repository's `.claude/skills` is a link whose target is `.agents/skills`."""
    root = Path(__file__).resolve().parents[2]
    view = root / ".claude" / "skills"
    assert view.is_symlink()
    assert view.resolve() == (root / ".agents" / "skills").resolve()
    assert (view / "mvp-mode" / "SKILL.md").is_file()
