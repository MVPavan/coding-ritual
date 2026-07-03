#!/usr/bin/env python3
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
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
from pathlib import Path
from shutil import rmtree

SCHEMA = "harness-capability-catalog/v1"

# Directory segments that never contain first-class capabilities: VCS/build/vendor
# noise, test fixtures, and — crucially — docs/ (harnesses mirror rendered and
# translated skill copies under docs/, which would otherwise inflate the count).
# Excluded anywhere in a path: VCS/build/vendor noise and test fixtures.
EXCLUDE_ANYWHERE = frozenset({
    ".git", "node_modules", ".venv", "venv", "dist", "build",
    "__pycache__", ".mypy_cache", "test", "tests", "fixtures",
})
# Excluded only as a TOP-LEVEL dir: harnesses mirror rendered/translated skill
# copies under a top-level docs/ (or examples/), but a capability legitimately
# nested under e.g. agents/docs/ must not be dropped.
EXCLUDE_TOPLEVEL = frozenset({"docs", "examples"})

# A capability's "root kind dir": the directory whose name marks the kind.
HOOK_SUFFIXES = frozenset({".sh", ".py", ".mjs", ".js", ".ts"})
MCP_FILENAMES = frozenset({"mcp.json", ".mcp.json"})


class Kind(str, Enum):
    """The kinds of capability a harness can ship."""

    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    RULE = "rule"
    HOOK = "hook"
    MCP = "mcp"
    PLUGIN = "plugin"


@dataclass(frozen=True)
class Capability:
    """One logical capability, collapsed across mirror copies."""

    kind: Kind
    name: str
    logical_id: str
    canonical_path: str
    paths: tuple[str, ...]
    description: str
    content_hash: str
    signature_hash: str
    variant_hashes: tuple[str, ...]
    line_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "name": self.name,
            "logical_id": self.logical_id,
            "canonical_path": self.canonical_path,
            "paths": list(self.paths),
            "description": self.description,
            "content_hash": self.content_hash,
            "signature_hash": self.signature_hash,
            "variant_hashes": list(self.variant_hashes),
            "line_count": self.line_count,
        }

    @staticmethod
    def from_dict(data: dict[str, object]) -> "Capability":
        return Capability(
            kind=Kind(data["kind"]),
            name=str(data["name"]),
            logical_id=str(data["logical_id"]),
            canonical_path=str(data["canonical_path"]),
            paths=tuple(str(p) for p in data.get("paths", [])),  # type: ignore[arg-type]
            description=str(data.get("description", "")),
            content_hash=str(data["content_hash"]),
            signature_hash=str(data["signature_hash"]),
            variant_hashes=tuple(str(h) for h in data.get("variant_hashes", [])),  # type: ignore[arg-type]
            line_count=int(data.get("line_count", 0)),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class Catalog:
    """A full capability inventory of one harness at one point in time."""

    repo: str
    source: str
    source_commit: str | None
    counts: dict[str, dict[str, int]]
    physical_scanned: int
    excluded: int
    capabilities: tuple[Capability, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "repo": self.repo,
            "source": self.source,
            "source_commit": self.source_commit,
            "physical_scanned": self.physical_scanned,
            "excluded": self.excluded,
            "counts": self.counts,
            "capabilities": [c.to_dict() for c in self.capabilities],
        }

    @staticmethod
    def from_dict(data: dict[str, object]) -> "Catalog":
        return Catalog(
            repo=str(data["repo"]),
            source=str(data.get("source", "")),
            source_commit=(str(data["source_commit"]) if data.get("source_commit") else None),
            counts=dict(data.get("counts", {})),  # type: ignore[arg-type]
            physical_scanned=int(data.get("physical_scanned", 0)),  # type: ignore[arg-type]
            excluded=int(data.get("excluded", 0)),  # type: ignore[arg-type]
            capabilities=tuple(
                Capability.from_dict(c) for c in data.get("capabilities", [])  # type: ignore[arg-type]
            ),
        )

    def by_logical_id(self) -> dict[str, Capability]:
        return {c.logical_id: c for c in self.capabilities}


# --- Raw scan entry (one physical file, before logical grouping) --------------


@dataclass(frozen=True)
class _Entry:
    kind: Kind
    name: str
    relpath: str
    dedup_key: str
    content_hash: str
    signature_hash: str
    description: str
    line_count: int
    rank: int


# --- Text helpers -------------------------------------------------------------


def normalize(text: str) -> str:
    """Canonicalise text so cosmetic edits don't read as content changes.

    Unifies line endings, strips trailing whitespace, collapses runs of blank
    lines, and trims leading/trailing blank lines.
    """
    unified = text.replace("\r\n", "\n").replace("\r", "\n")
    out: list[str] = []
    blank = 0
    for line in unified.split("\n"):
        stripped = line.rstrip()
        if stripped == "":
            blank += 1
            if blank <= 1:
                out.append("")
        else:
            blank = 0
            out.append(stripped)
    return "\n".join(out).strip() + "\n"


def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_frontmatter(text: str) -> dict[str, str]:
    """Extract simple top-level YAML frontmatter keys (single-line scalars).

    Deliberately minimal: enough for name/description/tools, no YAML dependency.
    Multi-line values are truncated to their first line.
    """
    if not text.startswith("---"):
        return {}
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return {}
    fm: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip().strip("\"'")
    return fm


# --- Classification -----------------------------------------------------------


def classify(parts: tuple[str, ...]) -> Kind | None:
    """Map a repo-relative path to a capability kind, or None."""
    name = parts[-1]
    suffix = "." + name.rsplit(".", 1)[1] if "." in name else ""
    if name == "plugin.json" and ".claude-plugin" in parts:
        return Kind.PLUGIN
    if name == "SKILL.md" and "skills" in parts:
        return Kind.SKILL
    if suffix == ".md" and "commands" in parts:
        return Kind.COMMAND
    if suffix == ".md" and "agents" in parts:
        return Kind.AGENT
    if suffix == ".md" and "rules" in parts:
        return Kind.RULE
    if "hooks" in parts and suffix in HOOK_SUFFIXES:
        return Kind.HOOK
    return None


def canonical_name(kind: Kind, parts: tuple[str, ...]) -> str:
    """The stable identity of a capability, shared across mirror copies."""
    if kind is Kind.SKILL:
        return parts[-2] if len(parts) >= 2 else parts[-1]
    if kind in (Kind.COMMAND, Kind.AGENT, Kind.RULE):
        anchor = kind.value + "s"
        idx = _last_index(parts, anchor)
        tail = parts[idx + 1:] if idx >= 0 else parts[-1:]
        return "/".join(tail).rsplit(".", 1)[0]
    if kind is Kind.HOOK:
        return parts[-1]
    if kind is Kind.PLUGIN:
        return parts[-2] if len(parts) >= 2 else parts[-1]
    return parts[-1]


def _last_index(parts: tuple[str, ...], value: str) -> int:
    for i in range(len(parts) - 1, -1, -1):
        if parts[i] == value:
            return i
    return -1


def root_rank(kind: Kind, parts: tuple[str, ...]) -> int:
    """Rank a physical path's "canonical-ness"; lower wins.

    Prefers a capability whose kind dir sits at the top of the tree
    (skills/foo/SKILL.md) over a nested per-tool mirror (.kiro/skills/foo/...),
    and penalises hidden top-level roots so canonical copies are chosen.
    """
    anchor = "skills" if kind is Kind.SKILL else kind.value + "s"
    idx = _last_index(parts, anchor)
    depth = idx if idx >= 0 else len(parts)
    hidden_penalty = 1000 if parts and parts[0].startswith(".") else 0
    return depth + hidden_penalty


def _strip_leading_dots(parts: tuple[str, ...]) -> tuple[str, ...]:
    """Drop leading per-tool mirror roots (`.kiro/`, `.cursor/`, `.claude/`, …) so a
    skill mirrored into several tool trees collapses to one identity — while a
    distinct plugin namespace (`plugins/discord/…` vs `plugins/telegram/…`) does not.
    """
    i = 0
    while i < len(parts) - 1 and parts[i].startswith("."):
        i += 1
    return parts[i:]


def dedup_key(kind: Kind, parts: tuple[str, ...]) -> str:
    """Namespace-aware grouping identity: merges mirror copies of ONE capability
    but keeps genuinely distinct capabilities apart (fixes over-merge). Uses the
    mirror-stripped path, which retains any containing plugin namespace.
    """
    stripped = _strip_leading_dots(parts)
    if kind is Kind.SKILL:
        return "/".join(stripped[:-1])                       # the skill directory
    joined = "/".join(stripped)
    return joined.rsplit(".", 1)[0] if "." in stripped[-1] else joined


def _plugin_dedup_key(parts: tuple[str, ...], name: str) -> str:
    """Plugin identity: containing namespace (if any) + the plugin.json name.
    Computed from RAW parts — `.claude-plugin` is a manifest dir, NOT a mirror
    root, so it must not be stripped; a root-level plugin keys by its name rather
    than an empty path.
    """
    if ".claude-plugin" in parts:
        container = "/".join(parts[:parts.index(".claude-plugin")])
    else:
        container = "/".join(parts[:-1])
    return f"{container}/{name}" if container else name


def _raw_frontmatter(text: str) -> str:
    """The normalized YAML frontmatter block (between the first two `---`), or ''.

    Hashed into the signature so block-style list changes (e.g. adding a tool /
    permission) are seen even though the minimal scalar parser cannot read them.
    """
    if not text.startswith("---"):
        return ""
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return ""
    block: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            return normalize("\n".join(block))
        block.append(line)
    return ""


def _plugin_name(text: str) -> str:
    """The `name` from a plugin.json, or '' if unreadable."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return ""
    name = data.get("name") if isinstance(data, dict) else None
    return str(name) if isinstance(name, str) else ""


# --- Scanning -----------------------------------------------------------------


def _iter_files(root: Path) -> "tuple[list[Path], int]":
    kept: list[Path] = []
    excluded = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if any(seg in EXCLUDE_ANYWHERE for seg in rel_parts) or (
            rel_parts and rel_parts[0] in EXCLUDE_TOPLEVEL
        ):
            excluded += 1
            continue
        kept.append(path)
    return kept, excluded


def _signature_hash(kind: Kind, name: str, surface: str) -> str:
    """Hash a capability's invocation surface: kind, name, and the full (normalized)
    frontmatter/config block. Any tool/permission/description change flips it, so a
    permission expansion can never be bucketed as a cosmetic body edit.
    """
    return sha1(json.dumps({"kind": kind.value, "name": name, "surface": surface}, sort_keys=True))


def _scan_mcp(path: Path, root: Path) -> list[_Entry]:
    """Enumerate MCP servers declared in an mcp.json / plugin.json file."""
    try:
        data = json.loads(read_text(path))
    except (json.JSONDecodeError, ValueError):
        return []
    servers = data.get("mcpServers") or data.get("servers") or {}
    if not isinstance(servers, dict):
        return []
    rel_parts = path.relative_to(root).parts
    rel = str(path.relative_to(root))
    stripped = "/".join(_strip_leading_dots(rel_parts))
    entries: list[_Entry] = []
    for server_name, config in servers.items():
        body = json.dumps(config, sort_keys=True, indent=2)
        cfg = config if isinstance(config, dict) else {}
        entries.append(_Entry(
            kind=Kind.MCP,
            name=str(server_name),
            relpath=f"{rel}#{server_name}",
            dedup_key=f"{stripped}#{server_name}",
            content_hash=sha1(normalize(body)),
            signature_hash=_signature_hash(Kind.MCP, str(server_name), json.dumps(config, sort_keys=True)),
            description=str(cfg.get("command", cfg.get("url", ""))),
            line_count=body.count("\n") + 1,
            rank=root_rank(Kind.MCP, rel_parts),
        ))
    return entries


def _entry_for(path: Path, root: Path, kind: Kind) -> _Entry:
    parts = path.relative_to(root).parts
    text = read_text(path)
    fm = parse_frontmatter(text) if path.suffix == ".md" else {}
    if kind is Kind.PLUGIN:
        name = _plugin_name(text) or canonical_name(kind, parts)
        surface = normalize(text)
        dkey = _plugin_dedup_key(parts, name)
    else:
        name = fm.get("name") or canonical_name(kind, parts)
        surface = _raw_frontmatter(text)
        dkey = dedup_key(kind, parts)
    normalized = normalize(text)
    return _Entry(
        kind=kind,
        name=name,
        relpath=str(path.relative_to(root)),
        dedup_key=dkey,
        content_hash=sha1(normalized),
        signature_hash=_signature_hash(kind, name, surface),
        description=fm.get("description", ""),
        line_count=normalized.count("\n"),
        rank=root_rank(kind, parts),
    )


def scan_repo(root: Path, repo: str, source: str, source_commit: str | None) -> Catalog:
    """Build a logical capability catalog from a harness working tree."""
    files, excluded = _iter_files(root)
    entries: list[_Entry] = []
    for path in files:
        parts = path.relative_to(root).parts
        if path.name in MCP_FILENAMES or path.name.endswith(".mcp.json") or path.name == "plugin.json":
            entries.extend(_scan_mcp(path, root))
        kind = classify(parts)
        if kind is not None:
            entries.append(_entry_for(path, root, kind))

    groups: dict[str, list[_Entry]] = {}
    for entry in entries:
        logical_id = f"{entry.kind.value}:{entry.dedup_key}"
        groups.setdefault(logical_id, []).append(entry)

    capabilities: list[Capability] = []
    for logical_id, group in groups.items():
        canonical = min(group, key=lambda e: (e.rank, e.relpath))
        variant_hashes = tuple(sorted({e.content_hash for e in group}))
        capabilities.append(Capability(
            kind=canonical.kind,
            name=canonical.name,
            logical_id=logical_id,
            canonical_path=canonical.relpath,
            paths=tuple(sorted(e.relpath for e in group)),
            description=canonical.description,
            content_hash=canonical.content_hash,
            signature_hash=canonical.signature_hash,
            variant_hashes=variant_hashes,
            line_count=canonical.line_count,
        ))
    capabilities.sort(key=lambda c: c.logical_id)

    counts: dict[str, dict[str, int]] = {}
    physical_by_kind: dict[Kind, int] = {}
    for entry in entries:
        physical_by_kind[entry.kind] = physical_by_kind.get(entry.kind, 0) + 1
    for cap in capabilities:
        bucket = counts.setdefault(cap.kind.value, {"physical": 0, "logical": 0})
        bucket["logical"] += 1
    for kind, n in physical_by_kind.items():
        counts.setdefault(kind.value, {"physical": 0, "logical": 0})["physical"] = n

    return Catalog(
        repo=repo,
        source=source,
        source_commit=source_commit,
        counts=counts,
        physical_scanned=len(files),
        excluded=excluded,
        capabilities=tuple(capabilities),
    )


# --- Materiality + diff -------------------------------------------------------


class Material(str, Enum):
    MATERIAL = "material"
    MINOR = "minor"


def _change_ratio(old_text: str, new_text: str) -> tuple[int, float]:
    old_lines = normalize(old_text).splitlines()
    new_lines = normalize(new_text).splitlines()
    matcher = SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    changed = (len(old_lines) - matched) + (len(new_lines) - matched)
    denom = max(1, len(old_lines) + len(new_lines))
    return changed, changed / denom


def classify_change(
    old: Capability,
    new: Capability,
    old_root: Path | None = None,
    new_root: Path | None = None,
) -> tuple[Material, str]:
    """Decide whether a modified capability is a material or cosmetic change.

    Signature changes (name/description/tools/MCP surface) are always material.
    Body-only changes are measured precisely when both trees are on disk (drift);
    from catalogs alone we cannot size the change, so we surface it as material
    rather than risk hiding a real edit.
    """
    if old.signature_hash != new.signature_hash:
        return Material.MATERIAL, "frontmatter/surface changed"
    if old.content_hash == new.content_hash:
        if set(old.variant_hashes) != set(new.variant_hashes):
            return Material.MINOR, "mirror-only change (canonical unchanged)"
        return Material.MINOR, "paths changed only"
    if old_root is not None and new_root is not None and "#" not in old.canonical_path:
        old_file, new_file = old_root / old.canonical_path, new_root / new.canonical_path
        if old_file.exists() and new_file.exists():
            changed, ratio = _change_ratio(read_text(old_file), read_text(new_file))
            if changed > 15 or ratio > 0.10:
                return Material.MATERIAL, f"body changed (~{changed} lines, {ratio:.0%})"
            return Material.MINOR, f"minor body edit (~{changed} lines, {ratio:.0%})"
    return Material.MATERIAL, "body changed (magnitude not computed)"


@dataclass(frozen=True)
class CatalogDiff:
    added: tuple[Capability, ...]
    removed: tuple[Capability, ...]
    modified_material: tuple[tuple[Capability, str], ...]
    modified_minor: tuple[tuple[Capability, str], ...]


def diff_catalogs(
    old: Catalog,
    new: Catalog,
    old_root: Path | None = None,
    new_root: Path | None = None,
) -> CatalogDiff:
    old_map = old.by_logical_id()
    new_map = new.by_logical_id()
    added = tuple(new_map[k] for k in new_map if k not in old_map)
    removed = tuple(old_map[k] for k in old_map if k not in new_map)
    material: list[tuple[Capability, str]] = []
    minor: list[tuple[Capability, str]] = []
    for key in new_map:
        if key not in old_map:
            continue
        old_cap, new_cap = old_map[key], new_map[key]
        if (old_cap.content_hash == new_cap.content_hash
                and old_cap.signature_hash == new_cap.signature_hash
                and set(old_cap.variant_hashes) == set(new_cap.variant_hashes)):
            continue
        level, reason = classify_change(old_cap, new_cap, old_root, new_root)
        (material if level is Material.MATERIAL else minor).append((new_cap, reason))
    return CatalogDiff(
        added=tuple(sorted(added, key=lambda c: c.logical_id)),
        removed=tuple(sorted(removed, key=lambda c: c.logical_id)),
        modified_material=tuple(sorted(material, key=lambda t: t[0].logical_id)),
        modified_minor=tuple(sorted(minor, key=lambda t: t[0].logical_id)),
    )


# --- Rendering ----------------------------------------------------------------


def render_catalog_summary(catalog: Catalog) -> str:
    lines = [
        f"## catalog: {catalog.repo}  ({catalog.source})",
        f"scanned {catalog.physical_scanned} files, excluded {catalog.excluded} "
        f"(docs/tests/vendor)",
        "",
        f"{'kind':<10}{'physical':>10}{'logical':>10}",
    ]
    total_phys = total_log = 0
    for kind in Kind:
        bucket = catalog.counts.get(kind.value)
        if not bucket:
            continue
        lines.append(f"{kind.value:<10}{bucket['physical']:>10}{bucket['logical']:>10}")
        total_phys += bucket["physical"]
        total_log += bucket["logical"]
    lines.append(f"{'TOTAL':<10}{total_phys:>10}{total_log:>10}")
    return "\n".join(lines)


def render_diff(old: Catalog, new: Catalog, diff: CatalogDiff) -> str:
    lines = [
        f"## drift: {new.repo}",
        f"{old.source}  ->  {new.source}",
        "",
        f"material: {len(diff.added)} added, {len(diff.removed)} removed, "
        f"{len(diff.modified_material)} changed   |   "
        f"minor: {len(diff.modified_minor)}",
    ]
    if diff.added:
        lines.append("\n### ADDED (material)")
        for cap in diff.added:
            desc = f" — {cap.description}" if cap.description else ""
            lines.append(f"  + {cap.logical_id}{desc}")
    if diff.removed:
        lines.append("\n### REMOVED (material)")
        for cap in diff.removed:
            lines.append(f"  - {cap.logical_id}")
    if diff.modified_material:
        lines.append("\n### CHANGED (material)")
        for cap, reason in diff.modified_material:
            lines.append(f"  ~ {cap.logical_id}  [{reason}]")
    if diff.modified_minor:
        lines.append("\n### changed (minor — cosmetic/mirror)")
        for cap, reason in diff.modified_minor:
            lines.append(f"  · {cap.logical_id}  [{reason}]")
    if not (diff.added or diff.removed or diff.modified_material):
        lines.append("\nNo material changes.")
    return "\n".join(lines)


# --- Git helpers (drift) ------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def pinned_commit(submodule: Path) -> str:
    return _git(submodule, "rev-parse", "HEAD")


def upstream_ref(submodule: Path) -> str:
    try:
        head = _git(submodule, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
        if head:
            return "origin/" + head.rsplit("/", 1)[-1]
    except subprocess.CalledProcessError:
        pass
    for branch in ("origin/main", "origin/master"):
        try:
            _git(submodule, "rev-parse", "--verify", "--quiet", branch)
            return branch
        except subprocess.CalledProcessError:
            continue
    raise SystemExit(f"cannot resolve upstream default branch for {submodule}")


def archive_ref(submodule: Path, ref: str, dest: Path) -> None:
    raw = subprocess.run(
        ["git", "-C", str(submodule), "archive", ref],
        capture_output=True, check=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        try:
            tar.extractall(dest, filter="data")  # type: ignore[call-arg]
        except TypeError:
            tar.extractall(dest)


# --- Commands -----------------------------------------------------------------


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
        Path(args.out).write_text(json.dumps(catalog.to_dict(), indent=2) + "\n", encoding="utf-8")
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
        subprocess.run(["git", "-C", str(submodule), "fetch", "--quiet", "origin"], check=True)
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
        old_cat = scan_repo(old_root, repo, source=f"pinned {pinned[:10]}", source_commit=pinned)
        new_cat = scan_repo(new_root, repo, source=f"{head_ref} {head[:10]}", source_commit=head)
        diff = diff_catalogs(old_cat, new_cat, old_root=old_root, new_root=new_root)
        print(render_diff(old_cat, new_cat, diff))
    finally:
        rmtree(tmp, ignore_errors=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reference-harness capability scanner + differ.")
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
    p_drift.add_argument("--no-fetch", dest="fetch", action="store_false", help="skip git fetch")
    p_drift.set_defaults(func=cmd_drift, fetch=True)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
