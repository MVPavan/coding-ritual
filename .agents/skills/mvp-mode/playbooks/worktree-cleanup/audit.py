#!/usr/bin/env python3
"""Read-only audit of a repository's Git worktrees. It changes nothing.

usage: audit.py [--repo <path>] [--base <ref>] [--json]

Paths come from `git worktree list`, never from what anyone typed. Each worktree
gets a bucket, which is advice; only `propose` and `prunable` are ever offered
for removal, and the owner's pinned set overrides any bucket:

    main       the main worktree; never removed
    current    the worktree this audit runs in
    bare       a bare repository entry
    locked     locked on purpose
    prunable   its directory is gone; only the record remains
    unreadable git could not read its status
    wip        tracked files have uncommitted changes
    scratch    untracked files only
    unknown    no base ref to judge the merge state against
    detached   detached HEAD whose commit the base does not contain
    unmerged   its branch has commits the base does not contain
    propose    clean, and the base contains its HEAD

"Merged" means the base contains HEAD, so a squash or rebase merge reads as
unmerged, the safe direction, and a branch with no commits of its own reads as
merged. `ignored` counts what removal would also delete and no bucket holds for.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class Worktree:
    path: str
    head: str = ""
    branch: str | None = None
    detached: bool = False
    bare: bool = False
    locked: bool = False
    prunable: bool = False
    merge: str = "unknown"  # merged | unmerged | unknown
    on_a_ref: bool = True  # False: removal leaves its commits unreachable
    wip: list[str] = field(default_factory=list)
    scratch: list[str] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)
    last_activity: str | None = None
    bucket: str = ""


def git(cwd: str, *args: str) -> subprocess.CompletedProcess[str]:
    # No optional locks: `status` must not rewrite the index of a worktree it audits.
    return subprocess.run(
        ["git", "--no-optional-locks", "-C", cwd, *args],
        capture_output=True,
        text=True,
        check=False,
    )


def parse_worktrees(porcelain: str) -> list[Worktree]:
    """Parse `git worktree list --porcelain -z`: NUL-ended fields, an empty one per record."""
    worktrees: list[Worktree] = []
    for field_ in porcelain.split("\0"):
        key, _, value = field_.partition(" ")
        if key == "worktree":
            worktrees.append(Worktree(path=value))
        elif not worktrees or not field_:
            continue
        elif key == "HEAD":
            worktrees[-1].head = value
        elif key == "branch":
            worktrees[-1].branch = value.removeprefix("refs/heads/")
        elif key in ("detached", "bare", "locked", "prunable"):
            setattr(worktrees[-1], key, True)
    return worktrees


def parse_status(porcelain: str) -> tuple[list[str], list[str], list[str]]:
    """(tracked changes, untracked, ignored) from `status --porcelain -z --ignored`."""
    wip: list[str] = []
    scratch: list[str] = []
    ignored: list[str] = []
    entries = iter(porcelain.split("\0"))
    for entry in entries:
        if not entry:
            continue
        code, name = entry[:2], entry[3:]
        if code == "??":
            scratch.append(name)
        elif code == "!!":
            ignored.append(name)
        else:
            wip.append(name)
            if "R" in code or "C" in code:
                next(entries, None)  # the rename's source path
    return wip, scratch, ignored


def resolve_base(repo: str, base: str | None) -> tuple[str | None, str | None]:
    """The ref as given and its commit, resolved once in the selected repo: a name
    such as HEAD means something else in each worktree."""
    if base is None:
        head = git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
        base = head.stdout.strip() if head.returncode == 0 else None
    if base is None:
        return None, None
    found = git(repo, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")
    return (base, found.stdout.strip()) if found.returncode == 0 else (None, None)


def last_activity(wt: Worktree) -> str | None:
    """The newer of the last commit and the newest uncommitted file."""
    commit = git(wt.path, "log", "-1", "--format=%ct")
    stamps = [int(commit.stdout.strip())] if commit.stdout.strip() else []
    for name in [*wt.wip, *wt.scratch]:
        try:
            stamps.append(int((Path(wt.path) / name).stat().st_mtime))
        except OSError:
            continue  # a deleted file has no time of its own
    if not stamps:
        return None
    return datetime.fromtimestamp(max(stamps), UTC).isoformat(timespec="seconds")


def bucket_of(wt: Worktree, index: int, cwd: Path, readable: bool) -> str:
    if wt.bare:
        return "bare"
    if index == 0:
        return "main"
    if wt.prunable:
        return "prunable"
    root = Path(wt.path).resolve()
    if cwd == root or root in cwd.parents:
        return "current"
    if wt.locked:
        return "locked"
    if not readable:
        return "unreadable"
    if wt.wip:
        return "wip"
    if wt.scratch:
        return "scratch"
    if wt.merge == "unknown":
        return "unknown"
    if wt.merge == "unmerged":
        return "detached" if wt.detached else "unmerged"
    return "propose"


def inspect(wt: Worktree, index: int, base_sha: str | None, cwd: Path) -> None:
    readable = False
    if not wt.bare and not wt.prunable:
        status = git(wt.path, "status", "--porcelain", "-z", "--ignored")
        readable = status.returncode == 0
        if readable:
            wt.wip, wt.scratch, wt.ignored = parse_status(status.stdout)
            wt.last_activity = last_activity(wt)
            if base_sha is not None:
                merged = git(wt.path, "merge-base", "--is-ancestor", "HEAD", base_sha)
                wt.merge = {0: "merged", 1: "unmerged"}.get(
                    merged.returncode, "unknown"
                )
            refs = git(wt.path, "for-each-ref", "--contains", "HEAD", "--count=1")
            wt.on_a_ref = bool(refs.stdout.strip())
    wt.bucket = bucket_of(wt, index, cwd, readable)


def audit(repo: str, base: str | None, cwd: Path) -> tuple[list[Worktree], str | None]:
    listed = git(repo, "worktree", "list", "--porcelain", "-z")
    if listed.returncode != 0:
        raise SystemExit(f"audit.py: {listed.stderr.strip()}")
    worktrees = parse_worktrees(listed.stdout)
    name, sha = resolve_base(repo, base)
    for index, wt in enumerate(worktrees):
        inspect(wt, index, sha, cwd)
    return worktrees, name


def render(worktrees: list[Worktree], base: str | None) -> str:
    lines = [f"base: {base or 'none found; pass --base <ref>'}"]
    for wt in worktrees:
        lines.append(f"{wt.bucket:10} {wt.path}")
        lines.append(
            f"           ref={wt.branch or wt.head[:10] or '-'} merge={wt.merge} "
            f"wip={len(wt.wip)} scratch={len(wt.scratch)} "
            f"ignored={len(wt.ignored)} last={wt.last_activity or '-'}"
        )
        if not wt.on_a_ref:
            lines.append("           no ref holds this HEAD: removal orphans it")
        for label, names in (("scratch", wt.scratch), ("ignored", wt.ignored)):
            if names and wt.bucket in ("scratch", "propose"):
                lines.append(f"           {label}: {', '.join(names[:10])}")
    lines.append(
        "Buckets are advice; the owner's pinned set wins. Nothing was changed."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Git worktrees; read-only.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--base", help="default: origin/HEAD")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    worktrees, base = audit(args.repo, args.base, Path(os.getcwd()).resolve())
    if args.json:
        print(
            json.dumps(
                {"base": base, "worktrees": [asdict(w) for w in worktrees]}, indent=1
            )
        )
    else:
        print(render(worktrees, base))
    return 0


if __name__ == "__main__":
    sys.exit(main())
