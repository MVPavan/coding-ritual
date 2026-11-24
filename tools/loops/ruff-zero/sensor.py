#!/usr/bin/env python3
"""Sensor of the ruff-zero control loop: Ruff findings per file in the loop's scope.

usage: sensor.py [--root DIR] [--roots PATH ...]

Lints every tracked Python file under the scope roots (default: SCOPE_ROOTS
from loop.env beside this file) with the repository's resolved Ruff
configuration and prints one JSON object, stable for a given tree:

    {"loop", "tool", "ruleset": {"count", "target", "sha"}, "scope", "files_scanned",
     "total", "files": [{"path", "count", "rules": {code: n}}]}

`files` lists only files with findings, sorted by path. `ruleset` fingerprints
the enabled rules and target version as Ruff resolves them for this tree, so the run can stop when
the configuration changes under the loop. RUFF overrides the Ruff command
(default: `uv run --frozen ruff`).
"""

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RULE_LINE = re.compile(r"\(([A-Z]+[0-9]+)\)")


def settings_roots(env_file):
    for line in env_file.read_text().splitlines():
        if line.startswith("SCOPE_ROOTS="):
            return shlex.split(line.split("=", 1)[1])[0].split()
    raise SystemExit(f"sensor: SCOPE_ROOTS not set in {env_file}")


def ruleset(show_settings):
    """The enabled rule codes and target version Ruff resolved: their count, the version, a sha."""
    lines = show_settings.splitlines()
    start = lines.index("linter.rules.enabled = [")
    end = lines.index("]", start)
    codes = sorted(
        {m.group(1) for ln in lines[start + 1 : end] for m in RULE_LINE.finditer(ln)}
    )
    target = next(
        (
            ln.split("=", 1)[1].strip()
            for ln in lines
            if ln.startswith("linter.unresolved_target_version")
        ),
        "unknown",
    )
    digest = hashlib.sha256("\n".join([target, *codes]).encode()).hexdigest()[:12]
    return {"count": len(codes), "target": target, "sha": digest}


def summarize(findings, root):
    """Group Ruff's JSON findings by repository-relative path and rule code."""
    per_file = {}
    for item in findings:
        path = os.path.relpath(item["filename"], root)
        rules = per_file.setdefault(path, {})
        code = item.get("code") or "syntax-error"
        rules[code] = rules.get(code, 0) + 1
    files = [
        {
            "path": path,
            "count": sum(rules.values()),
            "rules": dict(sorted(rules.items())),
        }
        for path, rules in sorted(per_file.items())
    ]
    return files, sum(f["count"] for f in files)


def tracked_python(root, roots):
    out = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", *roots],
        capture_output=True,
        check=True,
    ).stdout
    return sorted(p for p in out.decode().split("\0") if p.endswith(".py"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".")
    parser.add_argument("--roots", nargs="+")
    args = parser.parse_args(argv)
    root = Path(
        subprocess.run(
            ["git", "-C", args.root, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    roots = args.roots or settings_roots(HERE / "loop.env")
    ruff = shlex.split(os.environ.get("RUFF", "uv run --frozen ruff"))
    files = tracked_python(root, roots)
    if not files:
        raise SystemExit(f"sensor: no tracked Python files under {roots}")
    version = subprocess.run(
        [*ruff, "--version"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()
    shown = subprocess.run(
        [*ruff, "check", "--no-cache", "--show-settings", files[0]],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    linted = subprocess.run(
        [
            *ruff,
            "check",
            "--no-cache",
            "--exit-zero",
            "--output-format",
            "json",
            "--",
            *files,
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    per_file, total = summarize(json.loads(linted), root)
    json.dump(
        {
            "loop": "ruff-zero",
            "tool": version,
            "ruleset": ruleset(shown),
            "scope": roots,
            "files_scanned": len(files),
            "total": total,
            "files": per_file,
        },
        sys.stdout,
        indent=1,
    )
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
