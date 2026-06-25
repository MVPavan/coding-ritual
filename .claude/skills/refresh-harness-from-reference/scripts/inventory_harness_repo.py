#!/usr/bin/env python3
import json
import sys
from pathlib import Path


SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "tests",
    "fixtures",
    "__pycache__",
    ".mypy_cache",
}


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def walk_files(root: Path):
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def collect_matches(root: Path, matcher, limit=200):
    results = []
    for path in walk_files(root):
        if matcher(path):
            results.append(rel(path, root))
            if len(results) >= limit:
                break
    return sorted(results)


def collect(root: Path):
    data = {
        "repo": root.name,
        "path": str(root),
        "has_claude": (root / "CLAUDE.md").exists(),
        "has_agents": (root / "AGENTS.md").exists(),
        "has_dot_claude": (root / ".claude").is_dir(),
        "agents": [],
        "commands": [],
        "rules": [],
        "skills": [],
        "hooks": [],
        "memory": [],
        "project_docs": [],
        "root_docs": [],
    }

    data["agents"] = collect_matches(
        root,
        lambda p: p.suffix == ".md" and "agents" in p.parts and "docs" not in p.parts,
    )
    data["commands"] = collect_matches(
        root,
        lambda p: p.suffix == ".md" and "commands" in p.parts and "docs" not in p.parts,
    )
    data["rules"] = collect_matches(
        root,
        lambda p: p.suffix == ".md" and "rules" in p.parts and "docs" not in p.parts,
    )
    data["skills"] = collect_matches(
        root,
        lambda p: p.name == "SKILL.md" and "skills" in p.parts and "docs" not in p.parts,
    )
    data["hooks"] = collect_matches(
        root,
        lambda p: "hooks" in p.parts and "docs" not in p.parts,
    )
    data["memory"] = collect_matches(
        root,
        lambda p: p.suffix == ".md" and "memory" in p.parts and "docs" not in p.parts,
    )
    data["project_docs"] = collect_matches(
        root,
        lambda p: p.suffix == ".md" and ".claude" in p.parts and "project" in p.parts,
    )
    data["root_docs"] = sorted(
        [
            rel(p, root)
            for p in [root / "README.md", root / "AGENTS.md", root / "CLAUDE.md"]
            if p.exists()
        ]
    )
    data["docs"] = collect_matches(
        root,
        lambda p: p.suffix == ".md" and (
            p.parts[0] == "docs" or p.parts[0] == "harness_learnings"
        ),
    )

    return data


def main():
    if len(sys.argv) != 2:
        print("usage: inventory_harness_repo.py <repo-path>", file=sys.stderr)
        sys.exit(1)

    root = Path(sys.argv[1]).resolve()
    if not root.exists() or not root.is_dir():
        print(f"repo not found: {root}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(collect(root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
