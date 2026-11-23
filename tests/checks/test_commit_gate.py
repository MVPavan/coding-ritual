"""`playbooks/autopilot-full/commit_gate.py` on a real temporary repository.

Each check the gate file names is a small Python command that appends its
label and arguments to a log outside the repository, so a test can read which
checks ran, in what order, and on which paths.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / ".claude/skills/mvp-mode/playbooks/autopilot-full/commit_gate.py"
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
GATE = ".repo-context/commit-gate.toml"
REPO_GATE = Path(__file__).resolve().parents[2] / GATE


def repo_row(kind: str, name_part: str) -> dict[str, object]:
    """One row of this repository's own gate file, by kind and part of its name."""
    rows = tomllib.loads(REPO_GATE.read_text())[kind]
    (row,) = [r for r in rows if name_part in r["name"]]
    return dict(row)


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(cwd), *args],
        env=ENV,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def gate(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=repo,
        env=ENV,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def logger(log: Path, label: str, code: int = 0) -> list[str]:
    """A command that appends `<label> <args…>` to `log`, then exits `code`."""
    body = (
        "import sys; "
        "open(sys.argv[1], 'a').write(' '.join(sys.argv[2:]) + '\\n'); "
        f"sys.exit({code})"
    )
    return [sys.executable, "-c", body, str(log), label]


def value_text(value: object) -> str:
    if isinstance(value, dict):
        inner = ", ".join(f"{k} = {json.dumps(v)}" for k, v in value.items())
        return "{ " + inner + " }"
    return json.dumps(value)


def toml(tables: list[tuple[str, dict[str, object]]]) -> str:
    lines: list[str] = []
    for name, fields in tables:
        lines.append(f"[[{name}]]")
        lines += [f"{key} = {value_text(value)}" for key, value in fields.items()]
        lines.append("")
    return "\n".join(lines)


def write_gate(repo: Path, tables: list[tuple[str, dict[str, object]]]) -> None:
    """Write and commit the gate file, so it is part of the clean tree."""
    path = repo / GATE
    path.parent.mkdir(exist_ok=True)
    path.write_text(toml(tables))
    git(repo, "add", GATE)
    git(repo, "commit", "-qm", "gate")


def ran(log: Path) -> list[str]:
    return log.read_text().splitlines() if log.exists() else []


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    (root / "kept.py").write_text("x = 1\n")
    (root / "notes.txt").write_text("notes\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "init")
    return root


@pytest.fixture
def log(tmp_path: Path) -> Path:
    return tmp_path / "ran.log"


def stage(repo: Path, name: str, body: str = "y = 2\n") -> None:
    (repo / name).parent.mkdir(parents=True, exist_ok=True)
    (repo / name).write_text(body)
    git(repo, "add", name)


def test_missing_gate_file_is_its_own_exit(repo: Path) -> None:
    stage(repo, "new.py")
    done = gate(repo)
    assert done.returncode == 3
    assert "commit-gate.toml" in done.stderr
    assert "write it" in done.stderr


def test_pass_runs_staged_check_on_matching_staged_paths_only(
    repo: Path, log: Path
) -> None:
    write_gate(
        repo,
        [
            (
                "staged",
                {"name": "py", "glob": ["*.py"], "command": logger(log, "staged")},
            )
        ],
    )
    stage(repo, "pkg/new.py")
    stage(repo, "other.txt")
    done = gate(repo)
    assert done.returncode == 0, done.stdout + done.stderr
    assert ran(log) == ["staged pkg/new.py"]
    assert "PASS py" in done.stdout


def test_staged_checks_run_before_project_checks(repo: Path, log: Path) -> None:
    write_gate(
        repo,
        [
            ("project", {"name": "whole", "command": logger(log, "project")}),
            (
                "staged",
                {"name": "py", "glob": ["*.py"], "command": logger(log, "staged")},
            ),
        ],
    )
    stage(repo, "new.py")
    done = gate(repo)
    assert done.returncode == 0, done.stdout + done.stderr
    assert ran(log) == ["staged new.py", "project"]


def test_failing_staged_check_fails_before_any_project_check(
    repo: Path, log: Path
) -> None:
    write_gate(
        repo,
        [
            (
                "staged",
                {"name": "lint", "glob": ["*.py"], "command": logger(log, "staged", 1)},
            ),
            ("project", {"name": "whole", "command": logger(log, "project")}),
        ],
    )
    stage(repo, "new.py")
    done = gate(repo)
    assert done.returncode == 1
    assert ran(log) == ["staged new.py"]
    assert "FAIL lint" in done.stdout


def test_failing_project_check_fails(repo: Path, log: Path) -> None:
    write_gate(
        repo, [("project", {"name": "suite", "command": logger(log, "project", 3)})]
    )
    stage(repo, "new.py")
    done = gate(repo)
    assert done.returncode == 1
    assert ran(log) == ["project"]
    assert "FAIL suite" in done.stdout


def test_project_check_runs_only_when_its_paths_are_staged(
    repo: Path, log: Path
) -> None:
    write_gate(
        repo,
        [
            (
                "project",
                {"name": "docs", "when": ["docs/*"], "command": logger(log, "project")},
            )
        ],
    )
    stage(repo, "new.py")
    assert gate(repo).returncode == 0
    assert ran(log) == []
    stage(repo, "docs/a.md")
    done = gate(repo)
    assert done.returncode == 0, done.stdout + done.stderr
    assert ran(log) == ["project"]


def test_per_file_check_runs_once_per_path(repo: Path, log: Path) -> None:
    write_gate(
        repo,
        [
            (
                "staged",
                {
                    "name": "each",
                    "glob": ["*.py"],
                    "per_file": True,
                    "command": logger(log, "one"),
                },
            )
        ],
    )
    stage(repo, "a.py")
    stage(repo, "b.py")
    assert gate(repo).returncode == 0
    assert sorted(ran(log)) == ["one a.py", "one b.py"]


def test_refuses_a_staged_path_with_unstaged_changes(repo: Path, log: Path) -> None:
    write_gate(
        repo,
        [
            (
                "staged",
                {"name": "py", "glob": ["*.py"], "command": logger(log, "staged")},
            )
        ],
    )
    stage(repo, "new.py")
    (repo / "new.py").write_text("changed after staging\n")
    done = gate(repo)
    assert done.returncode == 4
    assert "new.py" in done.stderr
    assert ran(log) == []


def test_unstaged_change_elsewhere_refuses_only_when_a_project_check_is_due(
    repo: Path, log: Path
) -> None:
    write_gate(
        repo,
        [
            (
                "staged",
                {"name": "py", "glob": ["*.py"], "command": logger(log, "staged")},
            )
        ],
    )
    stage(repo, "new.py")
    (repo / "notes.txt").write_text("edited, not staged\n")
    assert gate(repo).returncode == 0
    write_gate(
        repo,
        [
            (
                "staged",
                {"name": "py", "glob": ["*.py"], "command": logger(log, "staged")},
            ),
            ("project", {"name": "whole", "command": logger(log, "project")}),
        ],
    )
    stage(repo, "new2.py")
    log.unlink()
    done = gate(repo)
    assert done.returncode == 4
    assert "notes.txt" in done.stderr
    assert ran(log) == []


def test_untracked_file_refuses_when_a_project_check_is_due(
    repo: Path, log: Path
) -> None:
    write_gate(
        repo, [("project", {"name": "whole", "command": logger(log, "project")})]
    )
    stage(repo, "new.py")
    (repo / "stray.py").write_text("not added\n")
    done = gate(repo)
    assert done.returncode == 4
    assert "stray.py" in done.stderr
    assert ran(log) == []


def test_nothing_staged_is_refused(repo: Path, log: Path) -> None:
    write_gate(
        repo, [("project", {"name": "whole", "command": logger(log, "project")})]
    )
    done = gate(repo)
    assert done.returncode == 4
    assert "nothing staged" in done.stderr
    assert ran(log) == []


def test_manual_checks_are_listed_when_their_paths_are_staged(repo: Path) -> None:
    write_gate(
        repo,
        [
            (
                "manual",
                {
                    "name": "links",
                    "when": ["*.md"],
                    "do": "Validate the changed links.",
                },
            ),
            (
                "manual",
                {
                    "name": "plugin",
                    "when": ["plugin/*"],
                    "do": "Run the plugin harness.",
                },
            ),
        ],
    )
    stage(repo, "README.md")
    done = gate(repo)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "Validate the changed links." in done.stdout
    assert "Run the plugin harness." not in done.stdout


def test_unknown_field_in_the_gate_file_is_a_config_error(repo: Path) -> None:
    write_gate(
        repo,
        [
            (
                "staged",
                {"name": "py", "glob": ["*.py"], "command": ["true"], "shell": True},
            )
        ],
    )
    stage(repo, "new.py")
    done = gate(repo)
    assert done.returncode == 2
    assert "shell" in done.stderr


def test_the_gate_changes_neither_the_tree_nor_the_index(repo: Path, log: Path) -> None:
    write_gate(
        repo,
        [
            (
                "staged",
                {"name": "py", "glob": ["*.py"], "command": logger(log, "staged")},
            )
        ],
    )
    stage(repo, "new.py")
    before = (git(repo, "status", "--porcelain"), git(repo, "write-tree"))
    assert gate(repo).returncode == 0
    assert (git(repo, "status", "--porcelain"), git(repo, "write-tree")) == before


def test_since_judges_the_branch_tip_on_the_paths_it_changed(
    repo: Path, log: Path
) -> None:
    write_gate(
        repo,
        [
            (
                "staged",
                {"name": "py", "glob": ["*.py"], "command": logger(log, "staged")},
            ),
            ("project", {"name": "whole", "command": logger(log, "project")}),
        ],
    )
    git(repo, "switch", "-qc", "feature")
    stage(repo, "new.py")
    git(repo, "commit", "-qm", "feature")
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "--since", "main"],
        cwd=repo,
        env=ENV,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert ran(log) == ["staged new.py", "project"]


def test_since_refuses_a_tree_that_differs_from_the_branch_tip(
    repo: Path, log: Path
) -> None:
    write_gate(
        repo,
        [
            (
                "staged",
                {"name": "py", "glob": ["*.py"], "command": logger(log, "staged")},
            )
        ],
    )
    git(repo, "switch", "-qc", "feature")
    stage(repo, "new.py")
    git(repo, "commit", "-qm", "feature")
    (repo / "notes.txt").write_text("edited, not committed\n")
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "--since", "main"],
        cwd=repo,
        env=ENV,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert done.returncode == 4
    assert "notes.txt" in done.stderr
    assert ran(log) == []


def test_an_unstaged_edit_to_the_gate_file_is_refused(repo: Path, log: Path) -> None:
    write_gate(
        repo, [("project", {"name": "suite", "command": logger(log, "project", 1)})]
    )
    stage(repo, "new.py")
    (repo / GATE).write_text("# every check removed, not staged\n")
    done = gate(repo)
    assert done.returncode == 4, done.stdout + done.stderr
    assert "gate file" in done.stderr
    assert ran(log) == []


def test_since_catches_whitespace_the_branch_committed(repo: Path) -> None:
    write_gate(repo, [("project", repo_row("project", "whitespace"))])
    git(repo, "switch", "-qc", "feature")
    stage(repo, "new.py", "y = 2   \n")
    git(repo, "commit", "-qm", "trailing whitespace")
    done = gate(repo, "--since", "main")
    assert done.returncode == 1, done.stdout + done.stderr
    assert "FAIL whitespace" in done.stdout
    assert "new.py" in done.stdout


def test_an_absent_optional_tool_is_skipped_not_passed(
    repo: Path, tmp_path: Path
) -> None:
    bare = tmp_path / "bin"
    bare.mkdir()
    (bare / "sh").symlink_to(shutil.which("sh") or "/bin/sh")
    row = repo_row("staged", "shellcheck")
    row["env"] = {"PATH": str(bare)}
    write_gate(repo, [("staged", row)])
    stage(repo, "run.sh", "echo hi\n")
    done = gate(repo)
    assert done.returncode == 0, done.stdout + done.stderr
    assert f"SKIP {row['name']}" in done.stdout
    assert "PASS" not in done.stdout
    assert "0 check(s) passed, 1 skipped" in done.stdout


def test_an_unstaged_symlinked_gate_file_is_refused(
    repo: Path, log: Path, tmp_path: Path
) -> None:
    write_gate(
        repo, [("project", {"name": "suite", "command": logger(log, "project", 1)})]
    )
    stage(repo, "new.py")
    outside = tmp_path / "outside.toml"
    outside.write_text("# every check removed\n")
    (repo / GATE).unlink()
    (repo / GATE).symlink_to(outside)
    done = gate(repo)
    assert done.returncode == 4, done.stdout + done.stderr
    assert "gate file" in done.stderr
    assert ran(log) == []


def test_a_trunk_merge_that_brings_no_change_is_gated_not_refused(
    repo: Path, log: Path
) -> None:
    write_gate(
        repo,
        [
            (
                "staged",
                {"name": "py", "glob": ["*.py"], "command": logger(log, "staged")},
            )
        ],
    )
    git(repo, "switch", "-qc", "feature")
    stage(repo, "new.py")
    git(repo, "commit", "-qm", "feature work")
    git(repo, "switch", "-q", "main")
    stage(repo, "tmp.txt", "added\n")
    git(repo, "commit", "-qm", "add")
    git(repo, "rm", "-q", "tmp.txt")
    git(repo, "commit", "-qm", "revert the add")
    git(repo, "switch", "-q", "feature")
    git(repo, "merge", "-q", "--no-ff", "--no-commit", "main")
    assert git(repo, "diff", "--cached", "--name-only") == ""
    done = gate(repo)
    assert done.returncode == 0, done.stdout + done.stderr
    assert ran(log) == ["staged new.py"]


def test_an_ordinary_empty_commit_is_still_refused(repo: Path, log: Path) -> None:
    write_gate(
        repo, [("project", {"name": "whole", "command": logger(log, "project")})]
    )
    git(repo, "switch", "-qc", "feature")
    stage(repo, "new.py")
    git(repo, "commit", "-qm", "feature work")
    done = gate(repo)
    assert done.returncode == 4
    assert "nothing staged" in done.stderr
    assert ran(log) == []


def parents(repo: Path) -> list[str]:
    return git(repo, "rev-list", "--parents", "-n", "1", "HEAD").split()[1:]


def test_a_pending_merge_equal_to_both_parents_is_gated_not_refused(
    repo: Path, log: Path
) -> None:
    whitespace = repo_row("project", "whitespace")
    write_gate(
        repo,
        [
            (
                "staged",
                {"name": "py", "glob": ["*.py"], "command": logger(log, "staged")},
            ),
            ("project", whitespace),
            ("project", {"name": "whole", "command": logger(log, "project")}),
        ],
    )
    base = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "switch", "-qc", "feature")
    stage(repo, "shared.py", "y = 2   \n")
    git(repo, "commit", "-qm", "on the feature")
    git(repo, "switch", "-q", "main")
    stage(repo, "shared.py", "y = 2   \n")
    git(repo, "commit", "-qm", "the same change on trunk")
    incoming = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "switch", "-q", "feature")
    git(repo, "merge", "-q", "--no-ff", "--no-commit", "main")
    assert git(repo, "diff", "--cached", "--name-only") == ""
    assert git(repo, "diff", "--cached", "--name-only", "MERGE_HEAD") == ""
    done = gate(repo)
    assert done.returncode == 1, done.stdout + done.stderr
    assert "equal to both parents" in done.stdout
    assert f"git diff {base} {incoming}" in done.stdout
    assert f"FAIL {whitespace['name']}" in done.stdout
    assert "shared.py:1" in done.stdout
    assert ran(log) == ["staged shared.py"]


def test_a_gated_trunk_merge_commits_with_both_parents(repo: Path, log: Path) -> None:
    write_gate(
        repo,
        [
            ("project", {"name": "whole", "command": logger(log, "project")}),
            ("manual", {"name": "diff and status", "do": "Inspect {range}."}),
        ],
    )
    git(repo, "switch", "-qc", "feature")
    stage(repo, "new.py")
    git(repo, "commit", "-qm", "feature work")
    feature_tip = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "switch", "-q", "main")
    stage(repo, "docs/trunk.md", "trunk\n")
    git(repo, "commit", "-qm", "trunk moves on")
    trunk_tip = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "switch", "-q", "feature")
    git(repo, "merge", "-q", "--no-ff", "--no-commit", "main")
    done = gate(repo)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "judging the staged merge" in done.stdout
    assert "Inspect git diff --cached." in done.stdout
    git(repo, "commit", "-q", "--no-edit")
    assert parents(repo) == [feature_tip, trunk_tip]


def test_the_manual_checks_name_the_range_the_gate_judged(
    repo: Path, log: Path
) -> None:
    write_gate(
        repo,
        [
            ("project", {"name": "whole", "command": logger(log, "project")}),
            ("manual", {"name": "diff and status", "do": "Inspect {range}."}),
        ],
    )
    base = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "switch", "-qc", "feature")
    stage(repo, "new.py")
    git(repo, "commit", "-qm", "feature work")
    tip = git(repo, "rev-parse", "HEAD").strip()
    done = gate(repo, "--since", "main")
    assert done.returncode == 0, done.stdout + done.stderr
    assert f"Inspect git diff {base} HEAD." in done.stdout
    assert tip in done.stdout
