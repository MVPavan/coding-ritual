"""`.codex/hooks/autopilot-branch-guard.py` decides exactly as the Claude guard does.

Both guards run over one table of (branch, path) cases in real temporary
repositories. The Codex guard gets the path in both payload shapes it reads: a
`tool_input.file_path` and an `apply_patch` patch (`tool_input.command`, the shape a
live Codex 0.172.0 probe captured). The patches are valid Codex patches for each
verb. A divergence from the Claude guard fails. The hook commands registered in
`.codex/hooks.json` are run as Codex runs them (`sh -c` in the turn's directory).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CLAUDE = ROOT / ".claude/hooks/autopilot-branch-guard.sh"
CODEX = ROOT / ".codex/hooks/autopilot-branch-guard.py"
BASH = shutil.which("bash") or "/bin/bash"
ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
    "PYTHONDONTWRITEBYTECODE": "1",
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


def hook(command: list[str], payload: object, cwd: Path) -> int:
    done = subprocess.run(
        command,
        input=payload if isinstance(payload, str) else json.dumps(payload),
        cwd=cwd,
        env=ENV,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if done.returncode == 2:
        assert done.stderr.startswith("BLOCKED: "), done.stderr
    return done.returncode


def claude(path: Path, cwd: Path) -> int:
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(path)}}
    return hook([BASH, str(CLAUDE)], {**payload, "cwd": str(cwd)}, cwd)


def codex(payload: object, cwd: Path) -> int:
    return hook([sys.executable, str(CODEX)], payload, cwd)


def add(path: object) -> str:
    return f"*** Add File: {path}\n+x\n"


def update(path: object) -> str:
    return f"*** Update File: {path}\n@@\n-a\n+x\n"


def delete(path: object) -> str:
    return f"*** Delete File: {path}\n"


def move(source: object, path: object) -> str:
    return f"*** Update File: {source}\n*** Move to: {path}\n@@\n-a\n+x\n"


def patch(*hunks: str) -> str:
    return "*** Begin Patch\n" + "".join(hunks) + "*** End Patch"


def apply_patch(text: str, cwd: Path) -> dict[str, object]:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "apply_patch",
        "tool_input": {"command": text},
        "cwd": str(cwd),
    }


def start_run(repo: Path) -> None:
    common = git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    (Path(common) / "autopilot-run").write_text("run\n")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    (root / "a.txt").write_text("a\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "init")
    return root


# Each case sets up the fixture and returns (path, cwd, expected exit code).
Case = Callable[[Path, Path], tuple[Path, Path, int]]


def no_marker_main(repo: Path, tmp: Path) -> tuple[Path, Path, int]:
    return repo / "a.txt", repo, 0


def marker_main(repo: Path, tmp: Path) -> tuple[Path, Path, int]:
    start_run(repo)
    return repo / "a.txt", repo, 2


def marker_main_new_folder(repo: Path, tmp: Path) -> tuple[Path, Path, int]:
    start_run(repo)
    return repo / "new" / "dir" / "b.txt", repo, 2


def marker_feature(repo: Path, tmp: Path) -> tuple[Path, Path, int]:
    start_run(repo)
    git(repo, "switch", "-qc", "feature")
    return repo / "a.txt", repo, 0


def worktree_feature_from_main_cwd(repo: Path, tmp: Path) -> tuple[Path, Path, int]:
    start_run(repo)
    git(repo, "worktree", "add", "-q", "-b", "feature", str(tmp / "wt"))
    return tmp / "wt" / "a.txt", repo, 0


def main_checkout_from_worktree_cwd(repo: Path, tmp: Path) -> tuple[Path, Path, int]:
    start_run(repo)
    git(repo, "worktree", "add", "-q", "-b", "feature", str(tmp / "wt"))
    return repo / "a.txt", tmp / "wt", 2


def origin_head_trunk_on_main(repo: Path, tmp: Path) -> tuple[Path, Path, int]:
    git(repo, "update-ref", "refs/remotes/origin/trunk", "HEAD")
    git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
    start_run(repo)
    return repo / "a.txt", repo, 0


def origin_head_trunk_on_trunk(repo: Path, tmp: Path) -> tuple[Path, Path, int]:
    origin_head_trunk_on_main(repo, tmp)
    git(repo, "switch", "-qc", "trunk")
    return repo / "a.txt", repo, 2


def master_without_origin_head(repo: Path, tmp: Path) -> tuple[Path, Path, int]:
    git(repo, "branch", "-m", "main", "master")
    start_run(repo)
    return repo / "a.txt", repo, 2


def detached_head(repo: Path, tmp: Path) -> tuple[Path, Path, int]:
    start_run(repo)
    git(repo, "switch", "-q", "--detach", "main")
    return repo / "a.txt", repo, 0


def outside_any_repository(repo: Path, tmp: Path) -> tuple[Path, Path, int]:
    start_run(repo)
    (tmp / "outside").mkdir()
    return tmp / "outside" / "plan.md", repo, 0


CASES: list[Case] = [
    no_marker_main,
    marker_main,
    marker_main_new_folder,
    marker_feature,
    worktree_feature_from_main_cwd,
    main_checkout_from_worktree_cwd,
    origin_head_trunk_on_main,
    origin_head_trunk_on_trunk,
    master_without_origin_head,
    detached_head,
    outside_any_repository,
]


@pytest.mark.parametrize("case", CASES, ids=[c.__name__ for c in CASES])
def test_both_payload_shapes_decide_as_the_claude_guard(
    case: Case, repo: Path, tmp_path: Path
) -> None:
    path, cwd, expected = case(repo, tmp_path)
    decisions = {
        "claude": claude(path, cwd),
        "file_path": codex(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": str(path)},
                "cwd": str(cwd),
            },
            cwd,
        ),
    }
    for verb, hunk in (("Add File", add), ("Update File", update), ("Delete", delete)):
        decisions[verb] = codex(apply_patch(patch(hunk(path)), cwd), cwd)
    decisions["Move to"] = codex(
        apply_patch(patch(move(tmp_path / "elsewhere.txt", path)), cwd), cwd
    )
    assert decisions == dict.fromkeys(decisions, expected)


def test_a_multi_file_patch_with_one_protected_path_is_refused(
    repo: Path, tmp_path: Path
) -> None:
    start_run(repo)
    wt = tmp_path / "wt"
    git(repo, "worktree", "add", "-q", "-b", "feature", str(wt))
    allowed, protected = wt / "a.txt", repo / "a.txt"
    assert (claude(allowed, wt), claude(protected, wt)) == (0, 2)
    assert codex(apply_patch(patch(update(allowed)), wt), wt) == 0
    text = patch(add(wt / "new.txt"), update(allowed), delete(protected))
    assert codex(apply_patch(text, wt), wt) == 2


def test_relative_patch_paths_resolve_against_the_payload_cwd(
    repo: Path, tmp_path: Path
) -> None:
    start_run(repo)
    wt = tmp_path / "wt"
    git(repo, "worktree", "add", "-q", "-b", "feature", str(wt))
    assert codex(apply_patch(patch(add("new/b.txt")), wt), tmp_path) == 0
    assert codex(apply_patch(patch(add("new/b.txt")), repo), tmp_path) == 2


@pytest.fixture
def feature(repo: Path, tmp_path: Path) -> Path:
    """A feature worktree of a marked repository whose own checkout is on `main`."""
    start_run(repo)
    wt = tmp_path / "wt"
    git(repo, "worktree", "add", "-q", "-b", "feature", str(wt))
    return wt


def test_an_indented_patch_header_is_read_as_codex_reads_it(
    repo: Path, feature: Path
) -> None:
    """Codex trims a header line before matching its marker (finding 1)."""
    text = f"*** Begin Patch\n  *** Add File: {repo / 'b.txt'}\n+x\n*** End Patch"
    assert claude(repo / "b.txt", feature) == 2
    assert codex(apply_patch(text, feature), feature) == 2


def test_a_patch_filename_keeps_its_leading_space(repo: Path, feature: Path) -> None:
    """`*** Add File:  sub/b.txt` names ` sub/b.txt`, not `sub/b.txt` (finding 1)."""
    (feature / " sub").symlink_to(repo)
    (feature / "sub").mkdir()
    target = feature / " sub" / "b.txt"
    assert claude(target, feature) == 2
    assert codex(apply_patch(patch(add(" sub/b.txt")), feature), feature) == 2


def test_update_body_lines_are_not_headers(repo: Path, feature: Path) -> None:
    """In an update body a header must start the line; Move to precedes the body."""
    protected = repo / "a.txt"
    body = (
        f"*** Update File: {feature / 'a.txt'}\n@@\n-a\n+x\n"
        f" *** Delete File: {protected}\n*** Move to: {protected}\n"
    )
    assert codex(apply_patch(patch(body), feature), feature) == 0
    assert codex(apply_patch(patch(delete(protected)), feature), feature) == 2


def test_edit_text_is_not_a_path(repo: Path, feature: Path) -> None:
    """Only `file_path` and patch headers in `command` name paths (findings 3+4)."""
    allowed = feature / "a.txt"
    for extra in (
        {"old_string": "foo", "new_string": "bar"},
        {"content": patch(delete(repo / "a.txt"))},
        {"edits": [{"path": str(repo / "a.txt")}]},
    ):
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(allowed), **extra},
            "cwd": str(repo),
        }
        assert claude(allowed, repo) == 0
        assert codex(payload, repo) == 0, extra


def test_a_file_path_parent_is_resolved_through_the_filesystem(
    repo: Path, feature: Path
) -> None:
    """`link/..` is the parent of the link's target, as the Claude guard sees it."""
    (repo / "sub").mkdir()
    (feature / "link").symlink_to(repo / "sub")
    target = feature / "link" / ".." / "b.txt"
    payload = {"tool_input": {"file_path": str(target)}, "cwd": str(feature)}
    assert claude(target, feature) == 2
    assert codex(payload, feature) == 2
    # A patch path resolves lexically, as Codex resolves it: feature/b.txt.
    assert codex(apply_patch(patch(add(target)), feature), feature) == 0


def registered(script: str) -> str:
    hooks = json.loads((ROOT / ".codex/hooks.json").read_text())["hooks"]
    commands = [
        hook["command"]
        for group in hooks["PreToolUse"]
        for hook in group["hooks"]
        if f".codex/hooks/{script}" in hook["command"]
    ]
    assert len(commands) == 1, commands
    return commands[0]


def shell(command: str, payload: object, cwd: Path) -> subprocess.CompletedProcess:
    env = {**ENV, "GIT_CEILING_DIRECTORIES": str(cwd.parent)}
    return subprocess.run(
        ["sh", "-c", command],
        input=json.dumps(payload),
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


@pytest.mark.parametrize(
    "script", ["autopilot-branch-guard.py", "block-generated-edits.py"]
)
def test_a_missing_hook_script_does_not_refuse(
    script: str, repo: Path, tmp_path: Path
) -> None:
    """Outside Git, or in a checkout without the script, the command exits 0."""
    command = registered(script)
    start_run(repo)
    outside = tmp_path / "outside"
    outside.mkdir()
    for cwd in (outside, repo):
        payload = apply_patch(patch(add(cwd / "docs/workstreams/status.md")), cwd)
        done = shell(command, payload, cwd)
        assert done.returncode == 0, (cwd, done.stderr)


def test_the_registered_guard_command_runs_the_guard(repo: Path) -> None:
    (repo / ".codex/hooks").mkdir(parents=True)
    shutil.copy(CODEX, repo / ".codex/hooks/autopilot-branch-guard.py")
    start_run(repo)
    command = registered("autopilot-branch-guard.py")
    done = shell(command, apply_patch(patch(update(repo / "a.txt")), repo), repo)
    assert done.returncode == 2, done.stderr
    assert done.stderr.startswith("BLOCKED: ")


@pytest.mark.parametrize("text", ["", "not json", "[]", '{"tool_input": 3}'])
def test_unreadable_payloads_pass_as_in_the_claude_guard(repo: Path, text: str) -> None:
    start_run(repo)
    assert codex(text, repo) == 0
