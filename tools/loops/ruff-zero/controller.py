#!/usr/bin/env python3
"""Controller of the ruff-zero control loop: choose the next file (one per run).

usage: controller.py --sensor FILE --notes FILE [--root DIR] [--loop NAME]

Reads the sensor's JSON and the loop bead's notes and prints one JSON object:
the chosen target, its findings, the tests that exercise it, and every file it
passed over and why. Exit 0: a target is chosen. Exit 3: the set point holds
(no finding in scope). Exit 4: findings remain but every file holding them is
excluded.

Order: fewest findings first, then path, so early runs stay small to review
while the loop is tuned. A file is passed over when its latest
note is `done` or `skipped`, when it failed twice since its last `reopened`
note, or when its path holds a character the agent's allowlist cannot carry.
Notes are lines `<loop> done|skipped|failed|reopened <path> [<rest>]`; other
lines are ignored.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

MAX_FAILURES = 2
SAFE_PATH = re.compile(r"[A-Za-z0-9._/-]+")


def read_notes(text, loop):
    """Per path: (state, failures). The latest done/skipped wins; reopened clears both."""
    line_re = re.compile(rf"^\s*{re.escape(loop)} (done|skipped|failed|reopened) (\S+)")
    state = {}
    for line in text.splitlines():
        m = line_re.match(line)
        if not m:
            continue
        kind, path = m.groups()
        last, failures = state.get(path, (None, 0))
        if kind == "reopened":
            state[path] = (None, 0)
        elif kind == "failed":
            state[path] = (last, failures + 1)
        else:
            state[path] = (kind, failures)
    return state


def exclusion(path, notes):
    last, failures = notes.get(path, (None, 0))
    if not SAFE_PATH.fullmatch(path):
        return "path holds a character the allowlist cannot carry"
    if last:
        return f"noted {last}"
    if failures >= MAX_FAILURES:
        return f"failed {failures} times"
    return None


def tests_for(target, test_files, read):
    """Test files that exercise the target: itself when it is one, else those naming its stem."""
    name = Path(target).name
    if target.startswith("tests/") and name.startswith("test_"):
        return [target]
    word = re.compile(rf"\b{re.escape(Path(target).stem)}\b")
    return sorted(t for t in test_files if t != target and word.search(read(t)))


def choose(sensor, notes, test_files, read):
    excluded = []
    candidates = []
    for f in sensor["files"]:
        why = exclusion(f["path"], notes)
        if why:
            excluded.append({"path": f["path"], "count": f["count"], "reason": why})
        else:
            candidates.append(f)
    candidates.sort(key=lambda f: (f["count"], f["path"]))
    out = {
        "loop": sensor["loop"],
        "total": sensor["total"],
        "selectable": len(candidates),
        "excluded": excluded,
    }
    if sensor["total"] == 0:
        return 3, {"status": "set point reached", **out}
    if not candidates:
        return 4, {"status": "no selectable target", **out}
    pick = candidates[0]
    return 0, {
        "status": "target",
        "target": pick["path"],
        "count": pick["count"],
        "rules": pick["rules"],
        "tests": tests_for(pick["path"], test_files, read),
        **out,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sensor", required=True)
    parser.add_argument("--notes", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--loop", default="ruff-zero")
    args = parser.parse_args(argv)
    sensor = json.loads(Path(args.sensor).read_text())
    notes = read_notes(Path(args.notes).read_text(), args.loop)
    root = Path(args.root)
    listed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", "tests"],
        capture_output=True,
        check=True,
    ).stdout.decode()
    test_files = [
        p
        for p in listed.split("\0")
        if Path(p).name.startswith("test_") and p.endswith(".py")
    ]
    code, out = choose(
        sensor, notes, test_files, lambda p: (root / p).read_text(errors="replace")
    )
    json.dump(out, sys.stdout, indent=1)
    sys.stdout.write("\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
