#!/usr/bin/env python3
"""Commit gate: run a project's own checks on what is staged, before a commit.

usage: commit_gate.py [--repo <path>] [--config <path>] [--since <ref>]

Reads the project's gate file (default `<repo>/.repo-context/commit-gate.toml`)
and runs, in this order, stopping at the first failure:

    [[staged]]   checks given the staged paths that match their globs
    [[project]]  whole-project checks, each due when a staged path matches its
                 `when` globs (no `when`: always due)

Each list runs in file order, so the file puts its cheapest checks first.
`[[manual]]` entries name what no script can judge; the gate prints the ones
whose `when` globs match a staged path, for the agent to do by hand. The gate
first prints the range it judges as a `git diff` command, and a manual entry's
`{range}` becomes that command, so a by-hand check reads the same range.

Fields:
    staged:  name, glob, command, per_file (default false), timeout, env
    project: name, command, when, timeout, env
    manual:  name, do, when

`command` is an argument list, run from the repository root with no shell.
A staged check gets its matching paths appended, or with `per_file` one run
per path. An argument that is exactly `{diff}` becomes the range being judged,
as `git diff` takes it, the same range the gate prints: `--cached` for a
staged commit, `<merge base> HEAD` with `--since`, and during a merge the
range named below. Globs use fnmatch on repository-relative paths, so `*`
also matches `/`. `timeout` is in seconds (default 1800); `env` adds variables.

A command that exits 77 is skipped, not passed (an optional tool that is not
installed, say): it prints SKIP with its output and is not counted as passed.

The gate file is read from the tree being judged: the index for a staged
commit, HEAD with `--since`, by its repository-relative name. A gate file in
the working copy that differs from that one (unstaged edits, or a draft not
yet staged), that is not a regular file in either view (a symlink, say), or
that resolves outside the repository refuses, so the checks that run are the
ones the commit carries.

During a merge (MERGE_HEAD exists) the checks due follow every path the merge
touches: the staged diff against either parent and the paths trunk brought in
since the merge base. The range is the staged diff against the first parent;
when that is empty, against the incoming parent; when both are empty (the
result equals both parents), the checks with no `when` and those matching the
paths trunk brought in still run, and the range is what trunk brought in
(`<merge base> <incoming>`). The checks given `{diff}` and the printed range
always read the same range. A merge is never refused as empty; an ordinary
empty commit is.

The checks read the working tree, so the gate first proves the working tree
holds what the commit will hold, as far as the checks read it: a staged path
with unstaged changes refuses, and when any project check is due, any unstaged
change or untracked file anywhere refuses. Limit: files git ignores (caches,
build output, environments) and anything outside the repository are not
compared; a check that reads them may see state the commit does not carry.

With `--since <ref>` the gate judges the committed branch tip instead of the
index: the paths are those changed from the merge base of <ref> and HEAD to
HEAD, and any staged, unstaged or untracked change refuses. Use it once trunk
is merged into the branch, when nothing is staged and the tip is what will be
integrated.

The gate only reads: it never stages, stashes, formats or rewrites a file.

Exit codes:
    0  every due check passed or was skipped (manual checks, if any, are printed)
    1  a check failed (its output is printed)
    2  the gate file or the arguments are invalid
    3  no gate file: write it before the first commit
    4  refused: nothing is staged (or nothing changed since <ref>), the gate
       file in the working copy differs from the judged one, or the working
       tree holds changes the commit (or the tip) does not
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import stat
import subprocess
import sys
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

PASS, FAIL, CONFIG, MISSING, REFUSED = 0, 1, 2, 3, 4
SKIPPED = 77
DIFF = "{diff}"
DEFAULT_CONFIG = ".repo-context/commit-gate.toml"
DEFAULT_TIMEOUT = 1800.0
SHOWN = 20

FIELDS = {
    "staged": ({"name", "glob", "command"}, {"per_file", "timeout", "env"}),
    "project": ({"name", "command"}, {"when", "timeout", "env"}),
    "manual": ({"name", "do"}, {"when"}),
}


class GateError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Check:
    kind: str
    name: str
    command: list[str] = field(default_factory=list)
    globs: list[str] = field(default_factory=list)
    per_file: bool = False
    timeout: float = DEFAULT_TIMEOUT
    env: dict[str, str] = field(default_factory=dict)
    do: str = ""


def git(root: Path, *args: str) -> list[str]:
    done = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False
    )
    if done.returncode != 0:
        raise GateError(
            CONFIG, f"git {' '.join(args)} failed: {done.stderr.decode().strip()}"
        )
    return [os.fsdecode(p) for p in done.stdout.split(b"\0") if p]


def _strings(value: object, where: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(v, str) and v for v in value)
    ):
        raise GateError(
            CONFIG, f"{where}: must be a non-empty list of non-empty strings"
        )
    return list(value)


def missing(path: Path) -> GateError:
    return GateError(
        MISSING,
        f"commit gate: no gate file at {path}; write it before the first commit "
        "(the project's checks, from its verification document)",
    )


def refuse_gate_file(rel: str, why: str) -> GateError:
    return GateError(
        REFUSED,
        f"commit gate: refused: the gate file {rel} {why}; the gate runs the checks the "
        "judged tree carries, so stage the gate file's change or undo it first",
    )


def judged_gate_file(root: Path, rel: str, since: str | None) -> bytes:
    """The gate file as the judged tree holds it: the index, or HEAD with --since.

    `rel` is the gate file's repository-relative name; git reads that name, never
    a resolved path. Both the working-copy entry and the judged entry must be a
    regular file inside the repository, and the two must be identical."""
    path = root / rel
    where = "the index" if since is None else "HEAD"
    if not path.resolve().is_relative_to(root.resolve()):
        raise refuse_gate_file(rel, "resolves outside the repository")
    if os.path.lexists(path) and not stat.S_ISREG(os.lstat(path).st_mode):
        raise refuse_gate_file(rel, "in the working copy is not a regular file")
    entry = (
        git(root, "ls-files", "--stage", "-z", "--", rel)
        if since is None
        else git(root, "ls-tree", "-z", "HEAD", "--", rel)
    )
    if entry and entry[0].split(" ", 1)[0] not in {"100644", "100755"}:
        raise refuse_gate_file(rel, f"in {where} is not a regular file")
    shown = subprocess.run(
        ["git", "-C", str(root), "show", f"{'' if since is None else 'HEAD'}:{rel}"],
        capture_output=True,
        check=False,
    )
    judged = shown.stdout if entry and shown.returncode == 0 else None
    on_disk = path.read_bytes() if path.is_file() else None
    if judged is None and on_disk is None:
        raise missing(path)
    if judged != on_disk:
        raise refuse_gate_file(
            rel,
            f"is not in {where}"
            if judged is None
            else "is missing from the working copy"
            if on_disk is None
            else f"in the working copy differs from {where}",
        )
    return judged


def load(path: Path, text: bytes) -> list[Check]:
    try:
        data = tomllib.loads(text.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise GateError(CONFIG, f"{path}: not valid TOML: {exc}") from exc
    unknown = set(data) - set(FIELDS)
    if unknown:
        raise GateError(
            CONFIG, f"{path}: unknown table(s) {sorted(unknown)}; use {sorted(FIELDS)}"
        )
    checks: list[Check] = []
    for kind, (required, optional) in FIELDS.items():
        entries = data.get(kind, [])
        if not isinstance(entries, list):
            raise GateError(
                CONFIG, f"{path}: [{kind}] must be an array of tables ([[{kind}]])"
            )
        for n, entry in enumerate(entries, start=1):
            where = f"{path}: [[{kind}]] #{n}"
            missing = required - set(entry)
            extra = set(entry) - required - optional
            if missing or extra:
                raise GateError(
                    CONFIG,
                    f"{where}: missing {sorted(missing)}, unknown {sorted(extra)}"
                    if missing and extra
                    else f"{where}: missing field(s) {sorted(missing)}"
                    if missing
                    else f"{where}: unknown field(s) {sorted(extra)}",
                )
            name = entry["name"]
            if not isinstance(name, str) or not name:
                raise GateError(CONFIG, f"{where}: name must be a non-empty string")
            globs = (
                _strings(entry.get("glob", entry.get("when")), f"{where} globs")
                if ("glob" in entry or "when" in entry)
                else []
            )
            per_file = entry.get("per_file", False)
            timeout = entry.get("timeout", DEFAULT_TIMEOUT)
            env = entry.get("env", {})
            do = entry.get("do", "")
            if not isinstance(per_file, bool):
                raise GateError(CONFIG, f"{where}: per_file must be true or false")
            if (
                isinstance(timeout, bool)
                or not isinstance(timeout, (int, float))
                or timeout <= 0
            ):
                raise GateError(
                    CONFIG, f"{where}: timeout must be a positive number of seconds"
                )
            if not isinstance(env, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in env.items()
            ):
                raise GateError(CONFIG, f"{where}: env must be a table of strings")
            if kind == "manual" and (not isinstance(do, str) or not do):
                raise GateError(CONFIG, f"{where}: do must be a non-empty string")
            command = (
                _strings(entry["command"], f"{where} command")
                if kind != "manual"
                else []
            )
            checks.append(
                Check(
                    kind, name, command, globs, per_file, float(timeout), dict(env), do
                )
            )
    return checks


def matching(paths: list[str], globs: list[str]) -> list[str]:
    return [p for p in paths if any(fnmatch.fnmatchcase(p, g) for g in globs)]


def safe(path: str) -> str:
    """A path a command cannot read as an option."""
    return "./" + path if path.startswith("-") else path


def run(check: Check, root: Path, args: list[str], diff: list[str]) -> tuple[str, str]:
    """Run one check: ("pass" | "fail" | "skip", output)."""
    argv = [a2 for a in check.command for a2 in (diff if a == DIFF else [a])]
    argv += args
    try:
        done = subprocess.run(
            argv,
            cwd=root,
            env={**os.environ, **check.env},
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=check.timeout,
            check=False,
        )
    except FileNotFoundError:
        return "fail", f"command not found: {argv[0]}"
    except subprocess.TimeoutExpired:
        return "fail", f"timed out after {check.timeout:g}s"
    output = (done.stdout + done.stderr).strip()
    if done.returncode == SKIPPED:
        return "skip", output
    if done.returncode != 0:
        return "fail", f"exit {done.returncode}" + (f"\n{output}" if output else "")
    return "pass", output


def listed(paths: list[str]) -> str:
    shown = "\n".join(f"  {p}" for p in paths[:SHOWN])
    more = f"\n  … and {len(paths) - SHOWN} more" if len(paths) > SHOWN else ""
    return shown + more


def pending_merge(root: Path) -> str | None:
    """The incoming commit of a merge in progress (MERGE_HEAD), if any."""
    done = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "-q", "--verify", "MERGE_HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return (done.stdout.strip() or None) if done.returncode == 0 else None


def gate(root: Path, rel: str = DEFAULT_CONFIG, since: str | None = None) -> int:
    checks = load(root / rel, judged_gate_file(root, rel, since))
    unstaged = git(root, "diff", "--name-only", "--no-renames", "-z")
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "-z")
    names = ["--name-only", "--no-renames", "-z"]
    incoming = pending_merge(root) if since is None else None
    if since is None and incoming is None:
        changed = ["--cached"]
        judged = "the staged diff"
        staged_all = git(root, "diff", *changed, *names)
        if not staged_all:
            raise GateError(REFUSED, "commit gate: refused: nothing staged")
    elif since is None:
        first = git(root, "diff", "--cached", *names)
        second = git(root, "diff", "--cached", incoming, *names)
        base = git(root, "merge-base", "HEAD", incoming)
        brought = git(root, "diff", base[0].strip(), incoming, *names) if base else []
        staged_all = sorted(set(first) | set(second) | set(brought))
        if first:
            changed = ["--cached"]
            judged = (
                f"the staged merge of {incoming[:12]} against the first parent HEAD"
            )
        elif second:
            changed = ["--cached", incoming]
            judged = (
                "the staged merge, equal to the first parent, against the incoming "
                f"parent {incoming[:12]}"
            )
        else:
            changed = [base[0].strip(), incoming] if base else ["--cached"]
            judged = (
                f"the staged merge of {incoming[:12]}, equal to both parents; checks due "
                "by the paths trunk brought in"
            )
    else:
        base = git(root, "merge-base", since, "HEAD")
        changed = [base[0].strip(), "HEAD"] if base else []
        if not changed:
            raise GateError(
                CONFIG, f"commit gate: no merge base between {since} and HEAD"
            )
        dirty = sorted(
            set(git(root, "diff", "--cached", *names)) | set(unstaged) | set(untracked)
        )
        if dirty:
            raise GateError(
                REFUSED,
                "commit gate: refused: --since judges the branch tip, and the working tree "
                "differs from HEAD (staged, unstaged or untracked):\n" + listed(dirty),
            )
        tip = git(root, "rev-parse", "HEAD")[0].strip()
        judged = f"the tip {tip} against its merge base with {since}"
        staged_all = git(root, "diff", *changed, *names)
        if not staged_all:
            raise GateError(
                REFUSED, f"commit gate: refused: nothing changed since {since}"
            )
    in_index = set(git(root, "ls-files", "-z"))
    present = [p for p in staged_all if p in in_index]
    range_text = "git diff " + " ".join(changed)
    print(f"judging {judged}: {range_text}")

    plan: list[tuple[Check, list[str]]] = []
    for check in checks:
        if check.kind == "staged":
            paths = matching(present, check.globs)
            if paths:
                plan.append((check, paths))
    project_due = [
        c
        for c in checks
        if c.kind == "project" and (not c.globs or matching(staged_all, c.globs))
    ]
    plan += [(c, []) for c in project_due]

    read_by_staged = sorted({p for _, paths in plan for p in paths} & set(unstaged))
    if read_by_staged:
        raise GateError(
            REFUSED,
            "commit gate: refused: staged paths also have unstaged changes, so the checks "
            "would not see what the commit holds; stage or undo them:\n"
            + listed(read_by_staged),
        )
    if project_due and (unstaged or untracked):
        raise GateError(
            REFUSED,
            "commit gate: refused: whole-project checks are due and the working tree holds "
            "changes the commit would not (unstaged or untracked); commit them with this "
            "change or remove them first:\n"
            + listed(sorted(set(unstaged) | set(untracked))),
        )

    skipped: list[str] = []
    for n, (check, paths) in enumerate(plan):
        started = time.monotonic()
        if check.per_file:
            results = [run(check, root, [safe(p)], changed) for p in paths]
            failed = [
                f"{p}: {out}" for p, (st, out) in zip(paths, results) if st == "fail"
            ]
            skips = [
                f"{p}: {out}" for p, (st, out) in zip(paths, results) if st == "skip"
            ]
            status = "fail" if failed else "skip" if skips else "pass"
            detail = "\n".join(failed or skips)
        else:
            status, detail = run(check, root, [safe(p) for p in paths], changed)
        took = time.monotonic() - started
        if status == "fail":
            print(f"FAIL {check.name} ({check.kind}, {took:.1f}s)\n{detail}")
            rest = [c.name for c, _ in plan[n + 1 :]]
            if rest:
                print("not run: " + ", ".join(rest))
            return FAIL
        if status == "skip":
            skipped.append(check.name)
            print(
                f"SKIP {check.name} ({check.kind})" + (f"\n{detail}" if detail else "")
            )
            continue
        print(f"PASS {check.name} ({check.kind}, {took:.1f}s)")

    passed = len(plan) - len(skipped)
    print(
        f"commit gate: {passed} check(s) passed"
        + (f", {len(skipped)} skipped: {', '.join(skipped)}" if skipped else "")
    )
    manual = [
        c
        for c in checks
        if c.kind == "manual" and (not c.globs or matching(staged_all, c.globs))
    ]
    if manual:
        print(
            f"manual checks to do before committing, on {range_text} "
            "(record each result with that range):"
        )
        for c in manual:
            print(f"  - {c.name}: {c.do.replace('{range}', range_text)}")
    return PASS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--repo", default=".", help="a path inside the repository (default: .)"
    )
    parser.add_argument(
        "--config",
        help=f"the gate file, inside the repository (default: <repo root>/{DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--since",
        metavar="REF",
        help="judge the branch tip on the paths changed since REF",
    )
    args = parser.parse_args(argv)
    try:
        top = git(Path(args.repo), "rev-parse", "--show-toplevel")
        root = Path(top[0].strip()) if top else Path(args.repo)
        rel = DEFAULT_CONFIG
        if args.config:
            rel = os.path.relpath(os.path.abspath(args.config), root)
            if rel == ".." or rel.startswith("../") or os.path.isabs(rel):
                raise GateError(
                    REFUSED,
                    f"commit gate: refused: the gate file {args.config} is outside the "
                    "repository; it must be a file the judged tree carries",
                )
        return gate(root, Path(rel).as_posix(), args.since)
    except GateError as exc:
        print(str(exc), file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
