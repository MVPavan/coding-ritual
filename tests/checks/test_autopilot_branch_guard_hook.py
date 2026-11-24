"""`.claude/hooks/autopilot-branch-guard.sh` run on JSON payloads in real temporary repositories."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BASH = shutil.which("bash") or "/bin/bash"
HOOK = Path(__file__).resolve().parents[2] / ".claude/hooks/autopilot-branch-guard.sh"
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
    return done.stdout.strip()


def guard(tool: str, path: Path, cwd: Path) -> subprocess.CompletedProcess[str]:
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    payload = {"tool_name": tool, "tool_input": {key: str(path)}, "cwd": str(cwd)}
    return subprocess.run(
        [BASH, str(HOOK)],
        input=json.dumps(payload),
        cwd=cwd,
        env=ENV,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def marker(repo: Path) -> Path:
    common = git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(common) / "autopilot-run"


def start_run(repo: Path) -> Path:
    path = marker(repo)
    path.write_text("run\n")
    return path


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    (root / "a.txt").write_text("a\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "init")
    return root


def test_no_marker_allows_an_edit_on_the_default_branch(repo: Path) -> None:
    assert guard("Edit", repo / "a.txt", repo).returncode == 0


def test_marker_refuses_an_edit_on_the_default_branch_and_names_the_marker(
    repo: Path,
) -> None:
    path = start_run(repo)
    done = guard("Edit", repo / "a.txt", repo)
    assert done.returncode == 2
    assert "BLOCKED" in done.stderr
    assert str(path) in done.stderr


def test_marker_refuses_a_new_file_in_a_new_folder_on_the_default_branch(
    repo: Path,
) -> None:
    start_run(repo)
    assert guard("Write", repo / "new" / "dir" / "b.txt", repo).returncode == 2


@pytest.mark.parametrize("tool", ["MultiEdit", "NotebookEdit"])
def test_marker_refuses_the_other_edit_tools_on_the_default_branch(
    repo: Path, tool: str
) -> None:
    start_run(repo)
    assert guard(tool, repo / "a.txt", repo).returncode == 2


def test_marker_allows_an_edit_on_a_feature_branch(repo: Path) -> None:
    start_run(repo)
    git(repo, "switch", "-qc", "feature")
    assert guard("Edit", repo / "a.txt", repo).returncode == 0


def test_second_worktree_on_a_feature_branch_is_allowed_while_main_checkout_is_refused(
    repo: Path, tmp_path: Path
) -> None:
    start_run(repo)
    wt = tmp_path / "wt"
    git(repo, "worktree", "add", "-q", "-b", "feature", str(wt))
    assert guard("Edit", wt / "a.txt", repo).returncode == 0
    assert guard("Edit", repo / "a.txt", wt).returncode == 2


def test_second_worktree_on_the_default_branch_sees_the_marker(
    repo: Path, tmp_path: Path
) -> None:
    git(repo, "switch", "-qc", "feature")
    wt = tmp_path / "wt"
    git(repo, "worktree", "add", "-q", str(wt), "main")
    path = start_run(wt)
    assert path == marker(repo)
    done = guard("Write", wt / "a.txt", wt)
    assert done.returncode == 2
    assert str(path) in done.stderr
    assert guard("Edit", repo / "a.txt", repo).returncode == 0


def test_default_branch_comes_from_origin_head(repo: Path) -> None:
    git(repo, "update-ref", "refs/remotes/origin/trunk", "HEAD")
    git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
    start_run(repo)
    assert guard("Edit", repo / "a.txt", repo).returncode == 0
    git(repo, "switch", "-qc", "trunk")
    assert guard("Edit", repo / "a.txt", repo).returncode == 2


def test_master_is_refused_without_origin_head(repo: Path) -> None:
    git(repo, "branch", "-m", "main", "master")
    start_run(repo)
    assert guard("Edit", repo / "a.txt", repo).returncode == 2


def test_detached_head_is_no_branch_and_is_allowed(repo: Path) -> None:
    start_run(repo)
    git(repo, "switch", "-q", "--detach", "main")
    assert guard("Edit", repo / "a.txt", repo).returncode == 0


def test_a_file_outside_any_repository_is_allowed(repo: Path, tmp_path: Path) -> None:
    start_run(repo)
    outside = tmp_path / "outside"
    outside.mkdir()
    assert guard("Write", outside / "plan.md", repo).returncode == 0


MARKER_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / ".claude/skills/mvp-mode/playbooks/autopilot-full/run_marker.py"
)


def bin_without_jq(tmp_path: Path, *tools: str) -> Path:
    """A PATH folder holding only the named tools, linked from this machine's."""
    folder = tmp_path / "bin"
    folder.mkdir(exist_ok=True)
    for tool in tools:
        found = shutil.which(tool)
        assert found, tool
        (folder / tool).symlink_to(found)
    return folder


def guard_raw(
    text: str, cwd: Path, path_dir: Path, project_dir: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in ENV.items() if k != "CLAUDE_PROJECT_DIR"}
    if project_dir is not None:
        env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    return subprocess.run(
        [BASH, str(HOOK)],
        input=text,
        cwd=cwd,
        env={**env, "PATH": str(path_dir)},
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


@pytest.mark.parametrize(
    ("tool", "key"), [("Write", "file_path"), ("NotebookEdit", "notebook_path")]
)
def test_without_jq_a_spaced_relative_payload_is_still_refused(
    repo: Path, tmp_path: Path, tool: str, key: str
) -> None:
    path_dir = bin_without_jq(
        tmp_path, "cat", "dirname", "git", "python3", "grep", "head", "sed"
    )
    text = (
        f'{{ "tool_name" : "{tool}", "tool_input" : {{ "{key}" : "new/b.txt" }}, '
        f'"cwd" : "{repo}" }}'
    )
    assert guard_raw(text, repo, path_dir).returncode == 0
    start_run(repo)
    done = guard_raw(text, repo, path_dir)
    assert done.returncode == 2, done.stderr
    assert str(marker(repo)) in done.stderr


def test_without_jq_or_python_a_marker_refuses_every_edit(
    repo: Path, tmp_path: Path
) -> None:
    path_dir = bin_without_jq(tmp_path, "cat", "dirname", "git")
    text = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "a.txt"}})
    assert guard_raw(text, repo, path_dir).returncode == 0
    start_run(repo)
    done = guard_raw(text, repo, path_dir)
    assert done.returncode == 2
    assert "neither jq nor python3" in done.stderr


def test_without_a_decoder_the_project_dirs_marker_refuses_from_another_cwd(
    repo: Path, tmp_path: Path
) -> None:
    other = tmp_path / "other"
    other.mkdir()
    git(other, "init", "-q", "-b", "main")
    path_dir = bin_without_jq(tmp_path, "cat", "dirname", "git")
    text = json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": str(repo / "a.txt")}}
    )
    start_run(repo)
    done = guard_raw(text, other, path_dir, project_dir=repo)
    assert done.returncode == 2, done.stderr
    assert str(marker(repo)) in done.stderr


def run_marker(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(MARKER_SCRIPT), "--repo", str(repo), *args],
        env=ENV,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def test_a_second_run_cannot_take_or_release_the_first_runs_marker(
    repo: Path,
) -> None:
    first = run_marker(repo, "acquire")
    assert first.returncode == 0, first.stderr
    first_id = first.stdout.strip()
    assert marker(repo).read_text().strip() == first_id
    second = run_marker(repo, "acquire")
    assert second.returncode == 4
    assert str(marker(repo)) in second.stderr
    stray = run_marker(repo, "release", "another-run")
    assert stray.returncode == 4
    assert marker(repo).read_text().strip() == first_id
    assert guard("Edit", repo / "a.txt", repo).returncode == 2
    assert run_marker(repo, "release", first_id).returncode == 0
    assert not marker(repo).exists()
    assert guard("Edit", repo / "a.txt", repo).returncode == 0
