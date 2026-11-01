"""Scan a harness working tree into a logical capability catalog (stdlib only)."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

from curation.scan.models import Capability, Catalog, Kind, _Entry

# Directory segments that never contain first-class capabilities: VCS/build/vendor
# noise, test fixtures, and — crucially — docs/ (harnesses mirror rendered and
# translated skill copies under docs/, which would otherwise inflate the count).
# Excluded anywhere in a path: VCS/build/vendor noise and test fixtures.
EXCLUDE_ANYWHERE = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "dist",
        "build",
        "__pycache__",
        ".mypy_cache",
        "test",
        "tests",
        "fixtures",
    }
)


# Excluded only as a TOP-LEVEL dir: harnesses mirror rendered/translated skill
# copies under a top-level docs/ (or examples/), but a capability legitimately
# nested under e.g. agents/docs/ must not be dropped.
EXCLUDE_TOPLEVEL = frozenset({"docs", "examples"})


# A capability's "root kind dir": the directory whose name marks the kind.
HOOK_SUFFIXES = frozenset({".sh", ".py", ".mjs", ".js", ".ts"})


MCP_FILENAMES = frozenset({"mcp.json", ".mcp.json"})


# Hook scripts are often shipped without an extension and invoked through a
# dispatcher (superpowers wires `run-hook.cmd session-start`, where the real hook
# body is the extensionless `hooks/session-start`). Treat an extensionless file
# under a hooks/ dir as a hook so those are not silently dropped.
HOOK_EXTENSIONLESS = ""


HOOK_MATCH_SUFFIXES = HOOK_SUFFIXES | {HOOK_EXTENSIONLESS}


# Self-test programs that ship alongside real hooks. They exercise the hook, they
# are not a capability the harness offers, so they must not be counted as one.
TEST_STEM_PREFIX = "test-"


TEST_STEM_SUFFIX = "-test"


SKILL_FILENAME = "SKILL.md"

# Subfolders of OUR skill folders that hold other units: each playbook in a
# router's `playbooks/` is its own unit (unit-kinds B1, T1), so its edits never
# change the router's tree hash. Only the ours build passes it to `scan_repo`;
# an upstream skill keeps such a folder in its hash, so upstream edits show.
UNIT_SUBFOLDERS = frozenset({"playbooks"})


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


def _is_test_script(name: str) -> bool:
    """True for a self-test program shipped beside a real capability."""
    stem = name.rsplit(".", 1)[0] if "." in name else name
    return stem.startswith(TEST_STEM_PREFIX) or stem.endswith(TEST_STEM_SUFFIX)


def classify(parts: tuple[str, ...]) -> Kind | None:
    """Map a repo-relative path to a capability kind, or None."""
    name = parts[-1]
    suffix = "." + name.rsplit(".", 1)[1] if "." in name else ""
    if name == "plugin.json" and ".claude-plugin" in parts:
        return Kind.PLUGIN
    # Single-skill repos ship a bare `skill/SKILL.md` (singular) — e.g.
    # html-artifacts, matching the .skill zip packaging convention.
    if name == SKILL_FILENAME and ("skills" in parts or "skill" in parts):
        return Kind.SKILL
    if suffix == ".md" and "commands" in parts:
        return Kind.COMMAND
    if suffix == ".md" and "agents" in parts:
        return Kind.AGENT
    if suffix == ".md" and "rules" in parts:
        return Kind.RULE
    if "hooks" in parts and suffix in HOOK_MATCH_SUFFIXES:
        return None if _is_test_script(name) else Kind.HOOK
    return None


def canonical_name(kind: Kind, parts: tuple[str, ...]) -> str:
    """The stable identity of a capability, shared across mirror copies."""
    if kind is Kind.SKILL:
        return parts[-2] if len(parts) >= 2 else parts[-1]
    if kind in (Kind.COMMAND, Kind.AGENT, Kind.RULE):
        anchor = kind.value + "s"
        idx = _last_index(parts, anchor)
        tail = parts[idx + 1 :] if idx >= 0 else parts[-1:]
        return "/".join(tail).rsplit(".", 1)[0]
    if kind is Kind.HOOK:
        return parts[-1]
    if kind is Kind.PLUGIN:
        return parts[-2] if len(parts) >= 2 else parts[-1]
    return parts[-1]


def category(kind: Kind, parts: tuple[str, ...]) -> str:
    """The grouping directory a capability falls under — its own folder's
    immediate parent. A grouped skill (skills/productivity/foo/SKILL.md) yields
    its group ('productivity'); a flat one (skills/foo/SKILL.md) yields the
    generic anchor ('skills'). Single-file kinds report their parent dir;
    plugins report their containing namespace.
    """
    if kind is Kind.PLUGIN:
        if ".claude-plugin" in parts:
            idx = parts.index(".claude-plugin")
            return parts[idx - 1] if idx >= 1 else ""
        return parts[-2] if len(parts) >= 2 else ""
    if kind is Kind.SKILL:
        if len(parts) >= 3:
            return parts[-3]
        return parts[-2] if len(parts) >= 2 else ""
    return parts[-2] if len(parts) >= 2 else ""


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
        return "/".join(stripped[:-1])  # the skill directory
    joined = "/".join(stripped)
    return joined.rsplit(".", 1)[0] if "." in stripped[-1] else joined


def _plugin_dedup_key(parts: tuple[str, ...], name: str) -> str:
    """Plugin identity: containing namespace (if any) + the plugin.json name.
    Computed from RAW parts — `.claude-plugin` is a manifest dir, NOT a mirror
    root, so it must not be stripped; a root-level plugin keys by its name rather
    than an empty path.
    """
    if ".claude-plugin" in parts:
        container = "/".join(parts[: parts.index(".claude-plugin")])
    else:
        container = "/".join(parts[:-1])
    return f"{container}/{name}" if container else name


def _raw_frontmatter(text: str) -> str:
    """The YAML frontmatter block, canonicalised for the signature: top-level keys
    are sorted (so a pure key-reorder is not read as a surface change) and blank /
    trailing whitespace is normalised. Block-style list changes (adding a tool or
    permission) still register; re-indentation within a value is a rare residual.
    """
    if not text.startswith("---"):
        return ""
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return ""
    block: list[str] = []
    closed = False
    for line in lines[1:]:
        if line.strip() == "---":
            closed = True
            break
        block.append(line)
    if not closed:
        return ""
    groups: list[list[str]] = []
    for line in block:
        is_top = (
            bool(line)
            and not line[0].isspace()
            and not line.lstrip().startswith("-")
            and ":" in line
        )
        if is_top or not groups:
            groups.append([line])
        else:
            groups[-1].append(line)
    groups.sort(key=lambda g: g[0])
    return normalize("\n".join("\n".join(g) for g in groups))


def _plugin_name(text: str) -> str:
    """The `name` from a plugin.json, or '' if unreadable."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return ""
    name = data.get("name") if isinstance(data, dict) else None
    return str(name) if isinstance(name, str) else ""


def _plugin_description(text: str) -> str:
    """The `description` from a plugin.json, or '' if unreadable.

    Plugin manifests are JSON, so they carry no Markdown frontmatter — without
    this the description column is blank for every plugin.
    """
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return ""
    description = data.get("description") if isinstance(data, dict) else None
    return str(description) if isinstance(description, str) else ""


def _iter_files(root: Path) -> tuple[list[Path], int]:
    """The files to scan and the count excluded by rule. Inside a git work tree,
    files git ignores are skipped before either count, like `_skill_tree_hash`,
    so local caches never change `physical_scanned` or `excluded`."""
    kept: list[Path] = []
    excluded = 0
    listed = _git_visible_files(root)
    visible = set(listed) if listed is not None else None
    for path in root.rglob("*"):
        if not path.is_file() or (visible is not None and path not in visible):
            continue
        rel_parts = path.relative_to(root).parts
        if any(seg in EXCLUDE_ANYWHERE for seg in rel_parts) or (
            rel_parts and rel_parts[0] in EXCLUDE_TOPLEVEL
        ):
            excluded += 1
            continue
        kept.append(path)
    return kept, excluded


GIT_TIMEOUT = 15


def _git_visible_files(skill_dir: Path) -> list[Path] | None:
    """The files under `skill_dir` that git does not ignore (tracked plus
    untracked-not-ignored), or None when git is unavailable or the folder is
    not in a git work tree. A folder git ignores wholly lists no file: `[]`,
    never a fallback to every file on disk.
    """
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(skill_dir),
                "ls-files",
                "-co",
                "--exclude-standard",
                "-z",
            ],
            capture_output=True,
            timeout=GIT_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    # Paths are relative to the folder. A set: an unmerged path is listed once
    # per stage. A tracked file deleted on disk is skipped.
    names = {os.fsdecode(raw) for raw in result.stdout.split(b"\0") if raw}
    return [skill_dir / name for name in names if (skill_dir / name).is_file()]


def folder_files(folder: Path) -> list[Path]:
    """Every file under `folder` that git does not ignore; every file on disk
    when git is unavailable."""
    listed = _git_visible_files(folder)
    if listed is not None:
        return listed
    return [p for p in folder.rglob("*") if p.is_file()]


def hash_files(base: Path, files: list[Path]) -> str:
    """sha256 over `files`, sorted by their path relative to `base` and framed
    as ``<relpath>\\0<byte length>\\0<raw bytes>`` with no text normalization."""
    digest = hashlib.sha256()
    for path in sorted(files, key=lambda p: str(p.relative_to(base))):
        rel = str(path.relative_to(base)).encode("utf-8")
        raw = path.read_bytes()
        digest.update(rel)
        digest.update(b"\0")
        digest.update(str(len(raw)).encode("ascii"))
        digest.update(b"\0")
        digest.update(raw)
    return digest.hexdigest()


def _skill_tree_hash(skill_dir: Path, skip: frozenset[str] = frozenset()) -> str:
    """sha256 over every file in a skill's folder (§4), skipping files git
    ignores when the folder is in a git work tree (caches such as
    ``__pycache__`` would otherwise make the hash machine-specific), so an
    edit to any bundled reference, script or asset changes the hash. Files in
    a `skip` subfolder belong to other units and are left out.
    """
    return hash_files(
        skill_dir,
        [
            p
            for p in folder_files(skill_dir)
            if p.relative_to(skill_dir).parts[0] not in skip
        ],
    )


def _signature_hash(kind: Kind, name: str, surface: str) -> str:
    """Hash a capability's invocation surface: kind, name, and the full (normalized)
    frontmatter/config block. Any tool/permission/description change flips it, so a
    permission expansion can never be bucketed as a cosmetic body edit.
    """
    return sha1(
        json.dumps(
            {"kind": kind.value, "name": name, "surface": surface}, sort_keys=True
        )
    )


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
        entries.append(
            _Entry(
                kind=Kind.MCP,
                name=str(server_name),
                relpath=f"{rel}#{server_name}",
                dedup_key=f"{stripped}#{server_name}",
                content_hash=sha1(normalize(body)),
                signature_hash=_signature_hash(
                    Kind.MCP, str(server_name), json.dumps(config, sort_keys=True)
                ),
                description=str(cfg.get("command", cfg.get("url", ""))),
                line_count=body.count("\n") + 1,
                rank=root_rank(Kind.MCP, rel_parts),
                tree_hash=sha1(normalize(body)),
            )
        )
    return entries


def _entry_for(
    path: Path,
    root: Path,
    kind: Kind,
    assets: tuple[str, ...] = (),
    unit_subfolders: frozenset[str] = frozenset(),
) -> _Entry:
    parts = path.relative_to(root).parts
    text = read_text(path)
    fm = parse_frontmatter(text) if path.suffix == ".md" else {}
    if kind is Kind.PLUGIN:
        name = _plugin_name(text) or canonical_name(kind, parts)
        surface = normalize(text)
        dkey = _plugin_dedup_key(parts, name)
        description = _plugin_description(text)
    else:
        name = fm.get("name") or canonical_name(kind, parts)
        surface = _raw_frontmatter(text)
        dkey = dedup_key(kind, parts)
        description = fm.get("description", "")
    normalized = normalize(text)
    content_hash = sha1(normalized)
    # A skill's tree hash spans its whole folder; other kinds reuse content_hash.
    tree_hash = (
        _skill_tree_hash(path.parent, unit_subfolders)
        if kind is Kind.SKILL
        else content_hash
    )
    return _Entry(
        kind=kind,
        name=name,
        relpath=str(path.relative_to(root)),
        dedup_key=dkey,
        content_hash=content_hash,
        signature_hash=_signature_hash(kind, name, surface),
        description=description,
        line_count=normalized.count("\n"),
        rank=root_rank(kind, parts),
        category=category(kind, parts),
        assets=assets,
        tree_hash=tree_hash,
    )


def _skill_assets(files: list[Path], root: Path) -> dict[Path, tuple[str, ...]]:
    """Map each skill directory to the non-capability files bundled inside it.

    A skill often ships prompt templates and helper scripts in its own folder.
    Those are part of the skill rather than standalone capabilities, so they are
    attributed to the nearest enclosing skill — never promoted to their own row.
    """
    skill_dirs = {
        path.parent
        for path in files
        if classify(path.relative_to(root).parts) is Kind.SKILL
    }
    owned: dict[Path, list[str]] = {directory: [] for directory in skill_dirs}
    for path in files:
        if path.name == SKILL_FILENAME:
            continue
        owners = [directory for directory in skill_dirs if directory in path.parents]
        if not owners:
            continue
        nearest = max(owners, key=lambda directory: len(directory.parts))
        owned[nearest].append(str(path.relative_to(root)))
    return {directory: tuple(sorted(paths)) for directory, paths in owned.items()}


def scan_repo(
    root: Path,
    repo: str,
    source: str,
    source_commit: str | None,
    unit_subfolders: frozenset[str] = frozenset(),
) -> Catalog:
    """Build a logical capability catalog from a harness working tree; skill
    tree hashes leave out `unit_subfolders` (ours only: UNIT_SUBFOLDERS)."""
    files, excluded = _iter_files(root)
    assets_by_skill_dir = _skill_assets(files, root)
    entries: list[_Entry] = []
    for path in files:
        parts = path.relative_to(root).parts
        if (
            path.name in MCP_FILENAMES
            or path.name.endswith(".mcp.json")
            or path.name == "plugin.json"
        ):
            entries.extend(_scan_mcp(path, root))
        kind = classify(parts)
        if kind is not None:
            assets = (
                assets_by_skill_dir.get(path.parent, ()) if kind is Kind.SKILL else ()
            )
            entries.append(_entry_for(path, root, kind, assets, unit_subfolders))

    groups: dict[str, list[_Entry]] = {}
    for entry in entries:
        logical_id = f"{entry.kind.value}:{entry.dedup_key}"
        groups.setdefault(logical_id, []).append(entry)

    capabilities: list[Capability] = []
    for logical_id, group in groups.items():
        canonical = min(group, key=lambda e: (e.rank, e.relpath))
        variant_hashes = tuple(sorted({e.content_hash for e in group}))
        capabilities.append(
            Capability(
                kind=canonical.kind,
                name=canonical.name,
                category=canonical.category,
                logical_id=logical_id,
                canonical_path=canonical.relpath,
                paths=tuple(sorted(e.relpath for e in group)),
                description=canonical.description,
                content_hash=canonical.content_hash,
                signature_hash=canonical.signature_hash,
                variant_hashes=variant_hashes,
                line_count=canonical.line_count,
                assets=canonical.assets,
                tree_hash=canonical.tree_hash,
            )
        )
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


def render_catalog_summary(catalog: Catalog) -> str:
    lines = [
        f"## catalog: {catalog.repo}  ({catalog.source})",
        (
            f"scanned {catalog.physical_scanned} files, excluded {catalog.excluded} "
            f"(docs/tests/vendor)"
        ),
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
