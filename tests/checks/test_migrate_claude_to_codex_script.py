"""`migrate-claude-to-codex/scripts/migrate_claude_to_codex.py` on a target whose
skills live in `.agents/skills` (Codex reads them there): verify checks that
tree, and migrate creates no `.codex/skills` links."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / ".agents/skills/migrate-claude-to-codex/scripts/migrate_claude_to_codex.py"
)


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migrate_claude_to_codex", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


helper = _load()


def _skill(root: Path, folder: str, name: str) -> None:
    (root / folder).mkdir(parents=True)
    (root / folder / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: A skill.\n---\n# Body\n"
    )


def _migrated(repo: Path, name: str = "brief-me") -> Path:
    _skill(repo / ".agents" / "skills", "brief-me", name)
    (repo / ".claude").mkdir()
    (repo / ".claude" / "skills").symlink_to("../.agents/skills")
    (repo / ".codex").mkdir()
    return repo


def test_verify_checks_the_agents_skill_tree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _migrated(tmp_path, name="wrong-name")
    code = helper.main(["verify", "--repo", str(repo), "--skip-codex"])
    out = capsys.readouterr().out
    assert code == 1, out
    assert "does not match folder 'brief-me'" in out


def test_verify_passes_a_correct_agents_skill_tree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _migrated(tmp_path)
    assert helper.main(["verify", "--repo", str(repo), "--skip-codex"]) == 0


def test_migrate_creates_no_codex_skill_links(tmp_path: Path) -> None:
    repo = _migrated(tmp_path)
    assert helper.main(["migrate", "--repo", str(repo), "--apply"]) == 0
    assert not (repo / ".codex" / "skills").exists()


def test_a_legacy_target_still_gets_codex_skill_links(tmp_path: Path) -> None:
    _skill(tmp_path / ".claude" / "skills", "brief-me", "brief-me")
    assert helper.main(["migrate", "--repo", str(tmp_path), "--apply"]) == 0
    link = tmp_path / ".codex" / "skills" / "brief-me"
    assert link.is_symlink()
    assert (link / "SKILL.md").is_file()


def test_a_mixed_target_links_its_claude_only_skills(tmp_path: Path) -> None:
    _skill(tmp_path / ".agents" / "skills", "native", "native")
    _skill(tmp_path / ".claude" / "skills", "legacy", "legacy")
    assert helper.main(["migrate", "--repo", str(tmp_path), "--apply"]) == 0
    link = tmp_path / ".codex" / "skills" / "legacy"
    assert link.is_symlink()
    assert (link / "SKILL.md").is_file()
    assert not (tmp_path / ".codex" / "skills" / "native").exists()
    assert helper.main(["verify", "--repo", str(tmp_path), "--skip-codex"]) == 0


def test_an_empty_agents_tree_keeps_legacy_links(tmp_path: Path) -> None:
    (tmp_path / ".agents" / "skills").mkdir(parents=True)
    _skill(tmp_path / ".claude" / "skills", "legacy", "legacy")
    assert helper.main(["migrate", "--repo", str(tmp_path), "--apply"]) == 0
    assert (tmp_path / ".codex" / "skills" / "legacy").is_symlink()


def test_a_same_name_skill_in_both_trees_is_a_conflict(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _skill(tmp_path / ".agents" / "skills", "tdd", "tdd")
    _skill(tmp_path / ".claude" / "skills", "tdd", "tdd")
    assert helper.main(["migrate", "--repo", str(tmp_path), "--apply"]) == 0
    assert "conflict" in capsys.readouterr().out
    assert not (tmp_path / ".codex" / "skills" / "tdd").exists()


def test_a_same_name_folder_without_a_skill_is_no_conflict(tmp_path: Path) -> None:
    (tmp_path / ".agents" / "skills" / "legacy").mkdir(parents=True)
    (tmp_path / ".agents" / "skills" / "legacy" / "README.md").write_text("notes\n")
    _skill(tmp_path / ".claude" / "skills", "legacy", "legacy")
    assert helper.main(["migrate", "--repo", str(tmp_path), "--apply"]) == 0
    assert (tmp_path / ".codex" / "skills" / "legacy" / "SKILL.md").is_file()


@pytest.mark.parametrize(
    ("line", "found"),
    [
        ("<other>/.agents/skills/native/SKILL.md", False),
        ("<other>{repo}/.codex/skills/tdd/SKILL.md", False),
        ("{repo}/.agents/skills/native/SKILL.md", True),
        ("skills dir: {repo}/.codex/skills", True),
        ("- .agents/skills/native/SKILL.md", True),
    ],
)
def test_discovery_accepts_only_this_repositorys_skills(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, line: str, found: bool
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    output = line.format(repo=repo).replace("<other>", str(tmp_path / "other"))
    monkeypatch.setattr(helper.shutil, "which", lambda _: "/bin/codex")
    monkeypatch.setattr(
        helper.subprocess,
        "run",
        lambda *a, **k: helper.subprocess.CompletedProcess(a, 0, stdout=output),
    )
    assert helper.run_codex_discovery(repo)[0] is found
