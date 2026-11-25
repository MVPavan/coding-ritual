"""`.claude/scripts/sync-codex.py`: the rerunnable check/repair of the Codex view.

Each case builds a tiny repository (hooks on both sides, `.codex/hooks.json`,
`.agents/skills`, the layout file), breaks one thing and runs the script on it
with `--repo`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / ".claude" / "scripts" / "sync-codex.py"
LAYOUT = Path("mvp-harness/plugins/mvp-plugin/scripts/skill-layout.txt")
IDENTICAL = ("block-dangerous-commands.sh", "bd-prime.sh", "bead-mirror-session.sh")
SESSION = "startup|resume|clear|compact"


def entry(matcher: str, command: str) -> dict[str, object]:
    """One `.codex/hooks.json` registration."""
    return {"matcher": matcher, "hooks": [{"type": "command", "command": command}]}


HOOKS_JSON = {
    "hooks": {
        "SessionStart": [
            entry(
                SESSION,
                'bash "$(git rev-parse --show-toplevel)/.codex/hooks/bd-prime.sh"',
            ),
            entry(SESSION, 'bash "$top/.codex/hooks/bead-mirror-session.sh"; exit 0'),
        ],
        "PreToolUse": [
            entry("Bash", 'bash "$top/.codex/hooks/block-dangerous-commands.sh"'),
            entry(
                "apply_patch|Edit|Write",
                'python3 "$top/.codex/hooks/block-generated-edits.py"',
            ),
            entry(
                "apply_patch|Edit|Write",
                'python3 "$top/.codex/hooks/autopilot-branch-guard.py"',
            ),
        ],
    }
}


def run(repo: Path, mode: str) -> subprocess.CompletedProcess[str]:
    """Run the script on `repo` in `--check` or `--write` mode."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), mode, "--repo", str(repo)],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def build(root: Path, layout: str = "dir") -> Path:
    """A minimal repository whose Codex view is in sync."""
    claude_hooks = root / ".claude" / "hooks"
    codex_hooks = root / ".codex" / "hooks"
    claude_hooks.mkdir(parents=True)
    codex_hooks.mkdir(parents=True)
    for name in IDENTICAL:
        body = f"#!/usr/bin/env bash\n# {name}\nexit 0\n"
        (claude_hooks / name).write_text(body)
        (codex_hooks / name).write_text(body)
    (claude_hooks / "block-generated-edits.sh").write_text("#!/usr/bin/env bash\n")
    (claude_hooks / "autopilot-branch-guard.sh").write_text("#!/usr/bin/env bash\n")
    (codex_hooks / "block-generated-edits.py").write_text("print()\n")
    (codex_hooks / "autopilot-branch-guard.py").write_text("print()\n")
    (root / ".codex" / "hooks.json").write_text(json.dumps(HOOKS_JSON, indent=2))
    for name in ("alpha", "beta"):
        skill = root / ".agents" / "skills" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\nname: {name}\n---\n")
    (root / LAYOUT).parent.mkdir(parents=True)
    (root / LAYOUT).write_text(f"{layout}\n")
    if layout == "dir":
        (root / ".claude" / "skills").symlink_to("../.agents/skills")
    else:
        (root / ".claude" / "skills").mkdir()
        for name in ("alpha", "beta"):
            (root / ".claude" / "skills" / name).symlink_to(
                f"../../.agents/skills/{name}"
            )
    return root


def test_fixture_is_in_sync(tmp_path: Path) -> None:
    """The fixture as built passes, in both layouts."""
    for layout in ("dir", "per-skill"):
        repo = build(tmp_path / layout, layout)
        completed = run(repo, "--check")
        assert completed.returncode == 0, completed.stdout + completed.stderr


def test_hook_drift_is_named_then_repaired(tmp_path: Path) -> None:
    """A stale Codex copy fails `--check`; `--write` copies the Claude source."""
    repo = build(tmp_path)
    stale = repo / ".codex" / "hooks" / "block-dangerous-commands.sh"
    stale.write_text("#!/usr/bin/env bash\n# old\n")
    before = run(repo, "--check")
    assert before.returncode == 1
    drift = [line for line in before.stdout.splitlines() if line]
    assert len(drift) == 1
    assert "block-dangerous-commands.sh" in drift[0]
    assert (
        stale.read_text()
        != (repo / ".claude/hooks/block-dangerous-commands.sh").read_text()
    )
    assert run(repo, "--write").returncode == 0
    assert (
        stale.read_bytes()
        == (repo / ".claude/hooks/block-dangerous-commands.sh").read_bytes()
    )
    assert run(repo, "--check").returncode == 0


def test_dangling_hooks_json_script_fails(tmp_path: Path) -> None:
    """A script `.codex/hooks.json` names but that does not exist fails."""
    repo = build(tmp_path)
    hooks_json = repo / ".codex" / "hooks.json"
    data = json.loads(hooks_json.read_text())
    data["hooks"]["PreToolUse"].append(
        {"hooks": [{"type": "command", "command": "bash .codex/hooks/ghost.sh"}]}
    )
    hooks_json.write_text(json.dumps(data))
    completed = run(repo, "--check")
    assert completed.returncode == 1
    assert "ghost.sh" in completed.stdout


def test_unparseable_hooks_json_fails(tmp_path: Path) -> None:
    """`.codex/hooks.json` that is not JSON fails."""
    repo = build(tmp_path)
    (repo / ".codex" / "hooks.json").write_text("{not json")
    completed = run(repo, "--check")
    assert completed.returncode == 1
    assert "hooks.json" in completed.stdout


def test_codex_skills_present_fails(tmp_path: Path) -> None:
    """`.codex/skills` must not exist."""
    repo = build(tmp_path)
    (repo / ".codex" / "skills").mkdir()
    completed = run(repo, "--check")
    assert completed.returncode == 1
    assert ".codex/skills" in completed.stdout


def test_root_only_files_in_codex_are_reported_never_removed(tmp_path: Path) -> None:
    """Root-only names under `.codex/hooks` fail; `--write` leaves them for a hand."""
    repo = build(tmp_path)
    leaked = repo / ".codex" / "hooks" / "harness-staleness-nudge.sh"
    leaked.write_text("#!/usr/bin/env bash\n")
    notes = repo / ".codex" / "hooks" / "harness-notes.txt"
    notes.write_text("local notes\n")
    assert run(repo, "--check").returncode == 1
    repaired = run(repo, "--write")
    assert repaired.returncode == 1
    assert "harness-notes.txt" in repaired.stdout
    assert leaked.exists()
    assert notes.read_text() == "local notes\n"


def test_per_skill_links_follow_added_and_removed_skills(tmp_path: Path) -> None:
    """`per-skill`: a new skill needs its link, a retired one loses it."""
    repo = build(tmp_path, "per-skill")
    gamma = repo / ".agents" / "skills" / "gamma"
    gamma.mkdir()
    (gamma / "SKILL.md").write_text("---\nname: gamma\n---\n")
    link = repo / ".claude" / "skills" / "gamma"
    added = run(repo, "--check")
    assert added.returncode == 1
    assert "gamma" in added.stdout
    assert run(repo, "--write").returncode == 0
    assert link.is_symlink()
    assert link.resolve() == gamma.resolve()
    assert run(repo, "--check").returncode == 0

    (gamma / "SKILL.md").unlink()
    gamma.rmdir()
    removed = run(repo, "--check")
    assert removed.returncode == 1
    assert "gamma" in removed.stdout
    assert run(repo, "--write").returncode == 0
    assert not link.is_symlink()
    assert run(repo, "--check").returncode == 0


@pytest.mark.parametrize("layout", ["dir", "per-skill"])
def test_a_wrong_skill_link_is_reported_never_replaced(
    tmp_path: Path, layout: str
) -> None:
    """A link at a wanted path pointing elsewhere may be the user's own: report it."""
    repo = build(tmp_path, layout)
    mine = repo / "my-skills" / "alpha"
    mine.mkdir(parents=True)
    (mine / "SKILL.md").write_text("mine\n")
    view = repo / ".claude" / "skills"
    link = view if layout == "dir" else view / "alpha"
    link.unlink()
    link.symlink_to("../my-skills" if layout == "dir" else "../../my-skills/alpha")
    text = os.readlink(link)
    assert run(repo, "--check").returncode == 1
    assert run(repo, "--write").returncode == 1
    assert os.readlink(link) == text


def test_a_symlinked_agents_dir_fails(tmp_path: Path) -> None:
    repo = build(tmp_path)
    outside = tmp_path / "outside-agents"
    (repo / ".agents").rename(outside)
    (repo / ".agents").symlink_to(outside)
    assert run(repo, "--check").returncode == 1


def test_a_malformed_hook_list_is_reported(tmp_path: Path) -> None:
    repo = build(tmp_path)
    path = repo / ".codex" / "hooks.json"
    data = json.loads(path.read_text())
    data["hooks"]["SessionStart"][0]["hooks"] = 42
    path.write_text(json.dumps(data))
    result = run(repo, "--check")
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "bd-prime.sh" in result.stdout

    data["hooks"]["SessionStart"][0]["hooks"] = [
        {"type": "prompt", "command": "bash .codex/hooks/bd-prime.sh"}
    ]
    path.write_text(json.dumps(data))
    assert run(repo, "--check").returncode == 1


def test_declared_pairs_need_their_halves(tmp_path: Path) -> None:
    """An active pair needs its Claude half, its Codex half and its wiring."""
    repo = build(tmp_path / "claude")
    (repo / ".claude" / "hooks" / "autopilot-branch-guard.sh").unlink()
    completed = run(repo, "--check")
    assert completed.returncode == 1
    assert (
        ".claude/hooks/autopilot-branch-guard.sh: Claude half of a declared pair missing"
        in completed.stdout
    )

    repo = build(tmp_path / "codex")
    hooks_json = repo / ".codex" / "hooks.json"
    data = json.loads(hooks_json.read_text())
    data["hooks"]["PreToolUse"].pop()  # the guard's Codex half is unreferenced
    hooks_json.write_text(json.dumps(data))
    (repo / ".codex" / "hooks" / "autopilot-branch-guard.py").unlink()
    completed = run(repo, "--check")
    assert completed.returncode == 1
    assert (
        ".codex/hooks/autopilot-branch-guard.py: Codex half of "
        ".claude/hooks/autopilot-branch-guard.sh missing" in completed.stdout
    )


def test_the_branch_guard_must_be_wired(tmp_path: Path) -> None:
    """The Codex guard present but unregistered, or under another matcher, fails."""
    want = (
        ".codex/hooks.json: no PreToolUse [apply_patch|Edit|Write] entry runs "
        ".codex/hooks/autopilot-branch-guard.py"
    )
    repo = build(tmp_path / "unwired")
    hooks_json = repo / ".codex" / "hooks.json"
    data = json.loads(hooks_json.read_text())
    data["hooks"]["PreToolUse"].pop()
    hooks_json.write_text(json.dumps(data))
    completed = run(repo, "--check")
    assert completed.returncode == 1
    assert want in completed.stdout

    repo = build(tmp_path / "matcher")
    hooks_json = repo / ".codex" / "hooks.json"
    data = json.loads(hooks_json.read_text())
    data["hooks"]["PreToolUse"][-1]["matcher"] = "apply_patch"
    hooks_json.write_text(json.dumps(data))
    completed = run(repo, "--check")
    assert completed.returncode == 1
    assert want in completed.stdout


# Writes stay inside the repository (finding 1) ---------------------------------


def outside_sentinel(tmp_path: Path) -> Path:
    sentinel = tmp_path / "outside" / "sentinel.sh"
    sentinel.parent.mkdir()
    sentinel.write_text("sentinel\n")
    sentinel.chmod(0o640)
    return sentinel


def test_symlinked_hook_destination_is_reported_not_written(tmp_path: Path) -> None:
    repo = build(tmp_path / "repo")
    sentinel = outside_sentinel(tmp_path)
    target = repo / ".codex" / "hooks" / "bd-prime.sh"
    target.unlink()
    target.symlink_to(sentinel)
    for mode in ("--write", "--check"):
        completed = run(repo, mode)
        assert completed.returncode == 1, mode
        assert ".codex/hooks/bd-prime.sh" in completed.stdout
    assert sentinel.read_text() == "sentinel\n"
    assert sentinel.stat().st_mode & 0o777 == 0o640
    assert target.is_symlink()


def test_symlinked_codex_hooks_dir_is_reported_not_written(tmp_path: Path) -> None:
    repo = build(tmp_path / "repo")
    outside = tmp_path / "outside-hooks"
    (repo / ".codex" / "hooks").rename(outside)
    (repo / ".codex" / "hooks").symlink_to(outside)
    (outside / "bd-prime.sh").write_text("stale\n")
    (outside / "harness-x.sh").write_text("keep\n")
    for mode in ("--check", "--write"):
        completed = run(repo, mode)
        assert completed.returncode == 1, mode
        assert "Traceback" not in completed.stderr
    assert (outside / "bd-prime.sh").read_text() == "stale\n"
    assert (outside / "harness-x.sh").read_text() == "keep\n"


def test_directory_at_hook_destination_is_reported(tmp_path: Path) -> None:
    repo = build(tmp_path)
    target = repo / ".codex" / "hooks" / "bd-prime.sh"
    target.unlink()
    target.mkdir()
    completed = run(repo, "--write")
    assert completed.returncode == 1
    assert "Traceback" not in completed.stderr
    assert ".codex/hooks/bd-prime.sh" in completed.stdout
    assert target.is_dir()


def test_hook_copy_replaces_the_file_atomically(tmp_path: Path) -> None:
    """The repair writes a new inode, so a hard-linked alias keeps its bytes."""
    repo = build(tmp_path / "repo")
    target = repo / ".codex" / "hooks" / "bd-prime.sh"
    target.write_text("stale\n")
    alias = tmp_path / "alias"
    os.link(target, alias)
    source = repo / ".claude" / "hooks" / "bd-prime.sh"
    source.chmod(0o755)
    assert run(repo, "--write").returncode == 0
    assert target.read_bytes() == source.read_bytes()
    assert target.stat().st_mode & 0o777 == 0o755
    assert alias.read_text() == "stale\n"
    assert not [p for p in target.parent.iterdir() if p.name.startswith(".")]


# Deletes only what the script made (finding 2) ---------------------------------


def test_per_skill_keeps_links_it_did_not_make(tmp_path: Path) -> None:
    repo = build(tmp_path / "repo", "per-skill")
    custom = repo / ".claude" / "skills" / "custom"
    custom.symlink_to("../../my-skills/custom")
    completed = run(repo, "--write")
    assert completed.returncode == 1
    assert ".claude/skills/custom" in completed.stdout
    assert custom.is_symlink()
    assert os.readlink(custom) == "../../my-skills/custom"


# Canonical skill source (finding 3) ---------------------------------------------


def test_missing_skill_source_fails_in_both_layouts(tmp_path: Path) -> None:
    for layout in ("dir", "per-skill"):
        repo = build(tmp_path / layout, layout)
        (repo / ".agents" / "skills").rename(repo / "moved-skills")
        for mode in ("--check", "--write"):
            completed = run(repo, mode)
            assert completed.returncode == 1, (layout, mode)
            assert ".agents/skills" in completed.stdout
        view = repo / ".claude" / "skills"
        if layout == "dir":
            assert os.readlink(view) == "../.agents/skills"
        else:
            assert sorted(p.name for p in view.iterdir()) == ["alpha", "beta"]


def test_symlinked_or_empty_skill_source_fails(tmp_path: Path) -> None:
    repo = build(tmp_path / "linked")
    skills = repo / ".agents" / "skills"
    skills.rename(repo / "real-skills")
    skills.symlink_to("../real-skills")
    assert run(repo, "--check").returncode == 1

    repo = build(tmp_path / "empty")
    for name in ("alpha", "beta"):
        (repo / ".agents" / "skills" / name / "SKILL.md").unlink()
    assert run(repo, "--check").returncode == 1


# Required hook wiring (finding 4) ------------------------------------------------


def test_missing_hook_registration_fails(tmp_path: Path) -> None:
    repo = build(tmp_path / "unwired")
    hooks_json = repo / ".codex" / "hooks.json"
    data = json.loads(hooks_json.read_text())
    del data["hooks"]["PreToolUse"][0]  # the shell guard
    hooks_json.write_text(json.dumps(data))
    completed = run(repo, "--write")
    assert completed.returncode == 1
    assert "block-dangerous-commands.sh" in completed.stdout
    assert json.loads(hooks_json.read_text()) == data  # never auto-written

    repo = build(tmp_path / "empty")
    (repo / ".codex" / "hooks.json").write_text("{}")
    completed = run(repo, "--check")
    assert completed.returncode == 1
    for script in ("bd-prime.sh", "bead-mirror-session.sh", "block-generated-edits.py"):
        assert script in completed.stdout

    repo = build(tmp_path / "matcher")
    hooks_json = repo / ".codex" / "hooks.json"
    data = json.loads(hooks_json.read_text())
    data["hooks"]["PreToolUse"][0]["matcher"] = "Shell"
    hooks_json.write_text(json.dumps(data))
    assert run(repo, "--check").returncode == 1
