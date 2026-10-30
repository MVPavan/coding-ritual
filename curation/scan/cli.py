"""Capability scanner + differ for reference harnesses.

The coding-ritual repo curates external agent harnesses under `reference_harnesses/`
(git submodules). This tool answers "what capabilities does a harness ship?" and
"what changed?" deterministically, so the model only has to read the short list of
things that actually moved — never hundreds of files.

Subcommands:
  catalog <repo-path> [--name NAME] [--out FILE]
      Scan a harness working tree into a JSON capability catalog.
  diff <old.json> <new.json>
      Materiality-filtered change report between two catalogs.
  drift <submodule-path> [--no-fetch]
      Catalog the pinned commit vs upstream HEAD and report the drift.

A "capability" is a skill / command / agent / rule / hook / MCP server / plugin.
Capabilities are deduplicated to LOGICAL units: harnesses often mirror the same
skill into several per-tool trees (.claude/, .cursor/, .kiro/, .agents/) and into
translated docs/ copies. We collapse those by (kind, name), keep the canonical
copy, and record the mirror paths + their content hashes as variants.

Pure Python standard library — no third-party dependencies, so it runs in any
checkout without an install step.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from shutil import rmtree

from curation.scan.catalog import render_catalog_summary, scan_repo
from curation.scan.drift import (
    _git,
    archive_ref,
    diff_catalogs,
    pinned_commit,
    render_diff,
    upstream_ref,
)
from curation.scan.models import Catalog


def cmd_catalog(args: argparse.Namespace) -> int:
    root = Path(args.repo).resolve()
    if not root.is_dir():
        raise SystemExit(f"not a directory: {root}")
    repo = args.name or root.name
    commit = None
    if (root / ".git").exists():
        try:
            commit = pinned_commit(root)
        except subprocess.CalledProcessError:
            commit = None
    catalog = scan_repo(root, repo, source="working-tree", source_commit=commit)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(catalog.to_dict(), indent=2) + "\n", encoding="utf-8"
        )
        print(f"wrote {args.out}", file=sys.stderr)
    print(render_catalog_summary(catalog))
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    old = Catalog.from_dict(json.loads(Path(args.old).read_text(encoding="utf-8")))
    new = Catalog.from_dict(json.loads(Path(args.new).read_text(encoding="utf-8")))
    diff = diff_catalogs(old, new)
    print(render_diff(old, new, diff))
    return 0


def cmd_drift(args: argparse.Namespace) -> int:
    submodule = Path(args.submodule).resolve()
    if not (submodule / ".git").exists():
        raise SystemExit(f"not a git submodule/repo: {submodule}")
    if args.fetch:
        subprocess.run(
            ["git", "-C", str(submodule), "fetch", "--quiet", "origin"], check=True
        )
    pinned = pinned_commit(submodule)
    head_ref = upstream_ref(submodule)
    head = _git(submodule, "rev-parse", head_ref)
    tmp = Path(tempfile.mkdtemp(prefix="harness-drift-"))
    try:
        old_root, new_root = tmp / "pinned", tmp / "head"
        old_root.mkdir()
        new_root.mkdir()
        archive_ref(submodule, pinned, old_root)
        archive_ref(submodule, head, new_root)
        repo = submodule.name
        old_cat = scan_repo(
            old_root, repo, source=f"pinned {pinned[:10]}", source_commit=pinned
        )
        new_cat = scan_repo(
            new_root, repo, source=f"{head_ref} {head[:10]}", source_commit=head
        )
        diff = diff_catalogs(old_cat, new_cat, old_root=old_root, new_root=new_root)
        print(render_diff(old_cat, new_cat, diff))
    finally:
        rmtree(tmp, ignore_errors=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reference-harness capability scanner + differ."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_cat = sub.add_parser("catalog", help="scan a harness working tree into a catalog")
    p_cat.add_argument("repo", help="path to the harness working tree")
    p_cat.add_argument("--name", help="catalog repo name (default: dir name)")
    p_cat.add_argument("--out", help="write catalog JSON to this path")
    p_cat.set_defaults(func=cmd_catalog)

    p_diff = sub.add_parser("diff", help="report drift between two catalog JSON files")
    p_diff.add_argument("old", help="old catalog JSON")
    p_diff.add_argument("new", help="new catalog JSON")
    p_diff.set_defaults(func=cmd_diff)

    p_drift = sub.add_parser("drift", help="catalog pinned vs upstream HEAD and report")
    p_drift.add_argument("submodule", help="path to a reference-harness submodule")
    p_drift.add_argument(
        "--no-fetch", dest="fetch", action="store_false", help="skip git fetch"
    )
    p_drift.set_defaults(func=cmd_drift, fetch=True)

    args = parser.parse_args(argv)
    return int(args.func(args))
