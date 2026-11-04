"""Materiality-filtered catalog diffs and the git helpers drift uses (stdlib only)."""

from __future__ import annotations

import io
import subprocess
import tarfile
from difflib import SequenceMatcher
from pathlib import Path

from curation.scan.catalog import normalize, read_text
from curation.scan.models import Capability, Catalog, CatalogDiff, Kind, Material


def _change_ratio(old_text: str, new_text: str) -> tuple[int, float]:
    old_lines = normalize(old_text).splitlines()
    new_lines = normalize(new_text).splitlines()
    matcher = SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    changed = (len(old_lines) - matched) + (len(new_lines) - matched)
    denom = max(1, len(old_lines) + len(new_lines))
    return changed, changed / denom


def _tree_changed(old: Capability, new: Capability) -> bool:
    """Whether the folder hash moved. A legacy catalog has none: unknown, no change."""
    return bool(old.tree_hash and new.tree_hash and old.tree_hash != new.tree_hash)


def classify_change(
    old: Capability,
    new: Capability,
    old_root: Path | None = None,
    new_root: Path | None = None,
) -> tuple[Material, str]:
    """Decide whether a modified capability is a material or cosmetic change.

    Signature changes (name/description/tools/MCP surface) are always material,
    and so is a change only to a skill's or playbook's bundled files: nothing sizes
    it, and hiding a real edit is the worse error. Body-only changes are measured precisely when both trees are on disk (drift);
    from catalogs alone we cannot size the change, so we surface it as material
    rather than risk hiding a real edit.
    """
    if old.signature_hash != new.signature_hash:
        return Material.MATERIAL, "frontmatter/surface changed"
    if old.content_hash == new.content_hash:
        if _tree_changed(old, new):
            return Material.MATERIAL, "folder bytes changed (normalized main file unchanged)"
        if set(old.variant_hashes) != set(new.variant_hashes):
            return Material.MINOR, "mirror-only change (canonical unchanged)"
        return Material.MINOR, "paths changed only"
    if old_root is not None and new_root is not None and "#" not in old.canonical_path:
        old_file, new_file = (
            old_root / old.canonical_path,
            new_root / new.canonical_path,
        )
        if old_file.exists() and new_file.exists():
            changed, ratio = _change_ratio(read_text(old_file), read_text(new_file))
            if changed > 15 or ratio > 0.10:
                return (
                    Material.MATERIAL,
                    f"body changed (~{changed} lines, {ratio:.0%})",
                )
            return Material.MINOR, f"minor body edit (~{changed} lines, {ratio:.0%})"
    return Material.MATERIAL, "body changed (magnitude not computed)"


def diff_catalogs(
    old: Catalog,
    new: Catalog,
    old_root: Path | None = None,
    new_root: Path | None = None,
) -> CatalogDiff:
    old_map = old.by_logical_id()
    new_map = new.by_logical_id()
    added_list = [new_map[k] for k in new_map if k not in old_map]
    removed_list = [old_map[k] for k in old_map if k not in new_map]
    # Move detection: a removed + added pair with identical (kind, content) is a
    # rename, not a real remove/add — keeps drift quiet and ledger continuity.
    added_by_key: dict[tuple[Kind, str], list[Capability]] = {}
    for cap in added_list:
        added_by_key.setdefault((cap.kind, cap.content_hash), []).append(cap)
    moved: list[tuple[Capability, Capability]] = []
    still_removed: list[Capability] = []
    for cap in removed_list:
        cands = added_by_key.get((cap.kind, cap.content_hash))
        if cands:
            moved.append((cap, cands.pop(0)))
        else:
            still_removed.append(cap)
    still_added = [c for caps in added_by_key.values() for c in caps]
    material: list[tuple[Capability, str]] = []
    minor: list[tuple[Capability, str]] = []
    for key in new_map:
        if key not in old_map:
            continue
        old_cap, new_cap = old_map[key], new_map[key]
        if (
            old_cap.content_hash == new_cap.content_hash
            and old_cap.signature_hash == new_cap.signature_hash
            and set(old_cap.variant_hashes) == set(new_cap.variant_hashes)
            and not _tree_changed(old_cap, new_cap)
        ):
            continue
        level, reason = classify_change(old_cap, new_cap, old_root, new_root)
        (material if level is Material.MATERIAL else minor).append((new_cap, reason))
    return CatalogDiff(
        added=tuple(sorted(still_added, key=lambda c: c.logical_id)),
        removed=tuple(sorted(still_removed, key=lambda c: c.logical_id)),
        moved=tuple(sorted(moved, key=lambda p: p[1].logical_id)),
        modified_material=tuple(sorted(material, key=lambda t: t[0].logical_id)),
        modified_minor=tuple(sorted(minor, key=lambda t: t[0].logical_id)),
    )


def render_diff(old: Catalog, new: Catalog, diff: CatalogDiff) -> str:
    lines = [
        f"## drift: {new.repo}",
        f"{old.source}  ->  {new.source}",
        "",
        (
            f"material: {len(diff.added)} added, {len(diff.removed)} removed, "
            f"{len(diff.modified_material)} changed   |   "
            f"minor: {len(diff.modified_minor)} + {len(diff.moved)} moved"
        ),
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
    if diff.moved:
        lines.append("\n### moved (renamed; content identical)")
        for old_cap, new_cap in diff.moved:
            lines.append(f"  → {old_cap.logical_id}  ⇒  {new_cap.logical_id}")
    if not (diff.added or diff.removed or diff.modified_material):
        lines.append("\nNo material changes.")
    return "\n".join(lines)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
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
        capture_output=True,
        check=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        try:
            tar.extractall(dest, filter="data")
        except TypeError:
            tar.extractall(dest)
