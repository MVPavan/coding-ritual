#!/usr/bin/env python3
"""PreToolUse(apply_patch|Edit|Write) guard for Autopilot-full runs: the Codex half.

Applies the rule of `.claude/hooks/autopilot-branch-guard.sh` to every path the edit
names: refuse (exit 2, reason on stderr) only while a run marker exists in the
repository's common git dir and the checkout holding the path's folder (its nearest
existing ancestor for a new file) is on the default branch (origin/HEAD's target, else
`main` and `master`). A detached HEAD, a file outside any repository, a git error or an
unreadable payload passes.

Paths come from two fields of `tool_input`, the only shapes Codex sends:
- `command`: an `apply_patch` patch. Its `*** Add File: ` / `*** Update File: ` /
  `*** Delete File: ` / `*** Move to: ` headers are read as Codex's streaming parser
  reads them (`codex-rs/apply-patch/src/streaming_parser.rs`): a header line is trimmed,
  an update body line is trimmed only at its end, `*** Move to: ` counts only before
  the update body, and the filename is the rest of the line after the marker. Relative
  names resolve lexically against the payload's `cwd`, as Codex resolves them.
- `file_path`: a direct path, read as the Claude guard reads it: a relative path is
  joined to `cwd`, and its folder is taken by name and then walked by the filesystem,
  so `link/..` is the parent of the link's target.
Limit: writes made through the shell are not covered.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

BEGIN, END = "*** Begin Patch", "*** End Patch"
HEADERS = ("*** Add File: ", "*** Delete File: ", "*** Update File: ")
MOVE_TO = "*** Move to: "


def patch_paths(text: str) -> list[str]:
    """The filenames a patch's hunk headers name, as Codex's parser reads them."""
    found: list[str] = []
    mode = "before"  # before | patch | update | body | end
    for raw in text.strip().split("\n"):
        line = raw.removesuffix("\r")
        if mode == "before":
            mode = "patch" if line.strip() == BEGIN else "before"
            continue
        if mode == "end":
            break
        header = line.rstrip() if mode in ("update", "body") else line.strip()
        if header == END:
            mode = "end"
            continue
        marker = next((m for m in HEADERS if header.startswith(m)), None)
        if marker:
            found.append(header[len(marker) :])
            mode = "update" if marker == "*** Update File: " else "patch"
        elif mode == "update" and header.startswith(MOVE_TO):
            found.append(header[len(MOVE_TO) :])
            mode = "body"
        elif mode == "update":
            mode = "body"
    return found


def dirname(path: str) -> str:
    """POSIX `dirname`: the folder part by name, without touching the filesystem."""
    stem = path.rstrip("/")
    if not stem:
        return "/" if path else "."
    head, sep, _ = stem.rpartition("/")
    return (head.rstrip("/") or "/") if sep else "."


def folders(tool_input: object, cwd: str) -> list[str]:
    """The folder each named path lands in (dict order, duplicates dropped)."""
    if not isinstance(tool_input, dict):
        return []
    found: list[str] = []
    command = tool_input.get("command")
    if isinstance(command, str):
        for name in patch_paths(command):
            found.append(os.path.dirname(os.path.normpath(os.path.join(cwd, name))))
    file_path = tool_input.get("file_path")
    if isinstance(file_path, str) and file_path:
        joined = file_path if file_path.startswith("/") else f"{cwd}/{file_path}"
        found.append(dirname(joined))
    return list(dict.fromkeys(found))


def git(folder: str, *args: str) -> str | None:
    try:
        done = subprocess.run(
            ["git", "-C", folder, *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError):  # ValueError: a NUL byte in the path
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def refusal(folder: str) -> str | None:
    """The block message for an edit in `folder`, or None when the Claude guard passes."""
    while not os.path.isdir(folder):
        folder = dirname(folder)
    common = git(folder, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not common:
        return None
    marker = Path(common) / "autopilot-run"
    if not marker.exists():
        return None
    branch = git(folder, "symbolic-ref", "--quiet", "--short", "HEAD")
    if not branch:
        return None
    default = git(
        folder, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"
    )
    protected = [default.removeprefix("origin/")] if default else ["main", "master"]
    if branch not in protected:
        return None
    top = git(folder, "rev-parse", "--show-toplevel") or folder
    return (
        f"BLOCKED: an Autopilot-full run is active in this repository (run marker: "
        f"{marker}) and the checkout {top} is on its default branch '{branch}'. Make "
        "the edit on the feature's own branch, in its worktree. If no run is active "
        f"(a crashed run left the marker behind), delete {marker} and retry."
    )


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
    except ValueError:
        return 0
    if not isinstance(payload, dict):
        return 0
    cwd = payload.get("cwd")
    cwd = cwd if isinstance(cwd, str) and cwd else os.getcwd()
    for folder in folders(payload.get("tool_input"), cwd):
        reason = refusal(folder)
        if reason:
            print(reason, file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
