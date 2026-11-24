"""Materiality-filtered catalog diffs and the git helpers drift uses (stdlib only)."""

from __future__ import annotations

import io
import subprocess
import sys
import tarfile
import tempfile
from difflib import SequenceMatcher
from pathlib import Path

from curation.scan.catalog import (
    normalize,
    playbook_tree_files,
    scan_repo,
    skill_tree_files,
)
from curation.scan.models import Capability, Catalog, CatalogDiff, Kind, Material


def _change_ratio(old_text: str, new_text: str, prose: bool) -> tuple[int, int]:
    """Changed lines and total lines across both sides; Markdown prose is
    normalized first, any other file is compared as written."""
    if prose:
        old_text, new_text = normalize(old_text), normalize(new_text)
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    matcher = SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    changed = (len(old_lines) - matched) + (len(new_lines) - matched)
    return changed, len(old_lines) + len(new_lines)


def _tree_changed(old: Capability, new: Capability) -> bool:
    """Whether the folder hash moved. A legacy catalog has none: unknown, no change."""
    return bool(old.tree_hash and new.tree_hash and old.tree_hash != new.tree_hash)


MAIN = "<main>"  # the unit's own file, whatever it is called


class _Unit:
    """A unit's files as its tree hash covers them, keyed by path inside the
    unit so a moved unit pairs file by file, and which of them the scan lists."""

    def __init__(self, cap: Capability, root: Path) -> None:
        main = root / cap.canonical_path
        base = main.parent if cap.kind is Kind.SKILL else main.with_suffix("")
        if cap.kind is Kind.SKILL:
            paths = skill_tree_files(main.parent)
        elif cap.kind is Kind.PLAYBOOK:
            paths = playbook_tree_files(main)
        else:
            paths = [main]
        self.files: dict[str, bytes] = {}
        self.prose: set[str] = set()
        for path in paths:
            key = MAIN if path == main else str(path.relative_to(base))
            self.files[key] = path.read_bytes()
            if path.suffix == ".md":
                self.prose.add(key)
        self.scanned = {MAIN} | {
            str((root / rel).relative_to(base))
            for rel in cap.assets
            if base in (root / rel).parents
        }

    @staticmethod
    def of(cap: Capability, root: Path | None) -> _Unit | None:
        if root is None or "#" in cap.canonical_path:
            return None
        if not (root / cap.canonical_path).is_file():
            return None
        return _Unit(cap, root)


def _grade_files(old: _Unit, new: _Unit) -> tuple[Material, str] | None:
    """Grade a change over every file the tree hash covers; None when no byte
    changed. Only Markdown prose has cosmetic edits (line endings, trailing
    space, blank runs): any other byte change, like any text change, is
    material ("needs a look"). Its magnitude is reported beside that flag,
    never instead of it: one reversed instruction is a small edit and still a
    changed mechanism."""
    keys = sorted(set(old.files) | set(new.files))
    changed = total = 0
    edited: list[str] = []
    cosmetic = 0
    for key in keys:
        before, after = old.files.get(key, b""), new.files.get(key, b"")
        prose = key in old.prose | new.prose
        old_text = before.decode("utf-8", errors="replace")
        new_text = after.decode("utf-8", errors="replace")
        lines, count = _change_ratio(old_text, new_text, prose)
        total += count
        if before == after:
            continue
        if prose and normalize(old_text) == normalize(new_text):
            cosmetic += 1
            continue
        changed += max(lines, 1)  # a byte change on no line still counts
        edited.append(key)
    if not (edited or cosmetic):
        return None
    if not edited:
        return (
            Material.MINOR,
            f"Markdown formatting only, in {cosmetic} of {len(keys)} files",
        )
    ratio = changed / max(1, total)
    size = "large" if changed > 15 or ratio > 0.10 else "small"
    reason = (
        f"needs a look; {size} edit, ~{changed} lines ({ratio:.0%}) "
        f"in {len(edited)} of {len(keys)} files"
    )
    if any(key not in old.scanned | new.scanned for key in edited):
        reason += "; files outside the scanned set changed"
    return Material.MATERIAL, reason


def classify_change(
    old: Capability,
    new: Capability,
    old_root: Path | None = None,
    new_root: Path | None = None,
) -> tuple[Material, str]:
    """Decide whether a modified capability is a material or cosmetic change.

    Signature changes (name/description/tools/MCP surface) are always material.
    When both trees are on disk (drift), every file the tree hash covers is
    compared (`_grade_files`). A tree hash that differs while no compared file
    did is still material. From catalogs alone nothing can be sized, so a body
    or folder change is material rather than risk hiding a real edit; only a
    path or mirror change is minor.
    """
    if old.signature_hash != new.signature_hash:
        return Material.MATERIAL, "frontmatter/surface changed"
    old_unit, new_unit = _Unit.of(old, old_root), _Unit.of(new, new_root)
    if old_unit is not None and new_unit is not None:
        graded = _grade_files(old_unit, new_unit)
        if graded is not None:
            return graded
        if _tree_changed(old, new):
            return (
                Material.MATERIAL,
                "needs a look; folder hash changed, but no compared file did",
            )
    if old.content_hash == new.content_hash:
        if _tree_changed(old, new):
            return (
                Material.MATERIAL,
                "folder bytes changed (normalized main file unchanged)",
            )
        if set(old.variant_hashes) != set(new.variant_hashes):
            return Material.MINOR, "mirror-only change (canonical unchanged)"
        return Material.MINOR, "paths changed only"
    return Material.MATERIAL, "body changed (magnitude not computed)"


def _identical_move(old: Capability, new: Capability) -> bool:
    """A move is a plain rename only when nothing but its location changed:
    same surface, mirrors and folder hash. A differing folder hash always rules
    it out."""
    return (
        old.signature_hash == new.signature_hash
        and set(old.variant_hashes) == set(new.variant_hashes)
        and not _tree_changed(old, new)
    )


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
    # Move detection: a removed + added pair with identical (kind, main-file
    # content) is a move, not a real remove/add — ledger continuity. Only a move
    # whose whole unit is unchanged is a plain rename; any other is graded as a
    # change, labelled with where it moved from.
    added_by_key: dict[tuple[Kind, str], list[Capability]] = {}
    for cap in added_list:
        added_by_key.setdefault((cap.kind, cap.content_hash), []).append(cap)
    moved: list[tuple[Capability, Capability]] = []
    still_removed: list[Capability] = []
    material: list[tuple[Capability, str]] = []
    minor: list[tuple[Capability, str]] = []
    for cap in removed_list:
        cands = added_by_key.get((cap.kind, cap.content_hash))
        if not cands:
            still_removed.append(cap)
            continue
        target = cands.pop(0)
        if _identical_move(cap, target):
            moved.append((cap, target))
            continue
        level, reason = classify_change(cap, target, old_root, new_root)
        bucket = material if level is Material.MATERIAL else minor
        bucket.append((target, f"moved from {cap.logical_id}; {reason}"))
    still_added = [c for caps in added_by_key.values() for c in caps]
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


def _is_sparse_checkout(root: Path) -> bool:
    try:
        return _git(root, "config", "--type=bool", "core.sparseCheckout") == "true"
    except subprocess.CalledProcessError:  # unset
        return False


def scan_checkout(root: Path, repo: str, commit: str | None) -> Catalog:
    """Scan `root`, or a full export of its HEAD when it is a sparse checkout: a
    scan of the partial tree would look complete and still carry the right commit.
    """
    if commit is None or not _is_sparse_checkout(root):
        return scan_repo(root, repo, source="working-tree", source_commit=commit)
    print(
        f"sparse checkout: scanning a full export of HEAD {commit[:10]}",
        file=sys.stderr,
    )
    with tempfile.TemporaryDirectory(prefix="harness-catalog-") as tmp:
        archive_ref(root, commit, Path(tmp))
        return scan_repo(Path(tmp), repo, source="working-tree", source_commit=commit)
