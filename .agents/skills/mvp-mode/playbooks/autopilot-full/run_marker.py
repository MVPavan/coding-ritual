#!/usr/bin/env python3
"""The Autopilot-full run marker: take it at intake, release it at exit.

usage: run_marker.py acquire [--repo <path>]
       run_marker.py release <run id> [--repo <path>]

The marker is the file `autopilot-run` in the repository's common git dir
(`git rev-parse --git-common-dir`), so every worktree of the repository sees
it; while it exists, the branch-guard hook refuses file edits in any checkout
on the default branch.

acquire  creates the marker only if no marker exists (an exclusive create, so
         two runs cannot both take it), writes a fresh run id into it and
         prints that id on stdout. Keep the id: release needs it.
release  removes the marker only if it still holds this run's id. A marker
         holding another id belongs to another run and is left in place.

Limit: release reads the id, then removes the file; a marker replaced between
the two steps would be removed. Only a person deleting a stale marker by hand
and a new run taking it in that instant could do that.

Exit codes:
    0  acquired (id printed) or released
    2  not in a git repository, or bad arguments
    4  refused: a marker already exists (acquire), or the marker is missing or
       holds another run's id (release); the message names the marker path
"""

from __future__ import annotations

import argparse
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

OK, ERROR, REFUSED = 0, 2, 4
NAME = "autopilot-run"


def marker_path(repo: str) -> Path:
    done = subprocess.run(
        ["git", "-C", repo, "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise SystemExit(
            f"run marker: {repo} is not in a git repository: {done.stderr.strip()}"
        )
    return Path(done.stdout.strip()) / NAME


def acquire(path: Path) -> int:
    run_id = f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{os.getpid()}-{secrets.token_hex(4)}"
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        held = path.read_text(errors="replace").strip() or "(empty)"
        print(
            f"run marker: refused: {path} already exists (run id {held}); another run "
            "is active, or a crashed run left it: ask the owner, start nothing",
            file=sys.stderr,
        )
        return REFUSED
    with os.fdopen(fd, "w") as fh:
        fh.write(run_id + "\n")
    print(run_id)
    return OK


def release(path: Path, run_id: str) -> int:
    try:
        held = path.read_text(errors="replace").strip()
    except FileNotFoundError:
        print(f"run marker: refused: no marker at {path}", file=sys.stderr)
        return REFUSED
    if held != run_id:
        print(
            f"run marker: refused: {path} holds run id {held or '(empty)'}, not "
            f"{run_id}; it belongs to another run and is left in place",
            file=sys.stderr,
        )
        return REFUSED
    path.unlink()
    print(f"released {path}")
    return OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", default=".", help="a path inside the repository")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("acquire")
    rel = sub.add_parser("release")
    rel.add_argument("run_id")
    args = parser.parse_args(argv)
    try:
        path = marker_path(args.repo)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return ERROR
    if args.action == "acquire":
        return acquire(path)
    return release(path, args.run_id)


if __name__ == "__main__":
    sys.exit(main())
