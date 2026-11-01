"""Our skills' tree hashes leave out subfolders that hold other units (B1,
T1); an upstream skill's hash keeps them, so upstream edits still show."""

from __future__ import annotations

from pathlib import Path

from curation.scan import catalog as scan


def _router_hash(root: Path, ours: bool) -> str:
    skip = scan.UNIT_SUBFOLDERS if ours else frozenset()
    cat = scan.scan_repo(root, "r", "working-tree", None, unit_subfolders=skip)
    return next(c.tree_hash for c in cat.capabilities if c.name == "router")


def test_tree_hash_skips_playbooks_for_ours_only(tmp_path: Path) -> None:
    router = tmp_path / "skills" / "router"
    (router / "playbooks" / "bug-fix").mkdir(parents=True)
    (router / "references").mkdir()
    (router / "SKILL.md").write_text("---\nname: router\n---\n", encoding="utf-8")
    (router / "references" / "catalog.md").write_text("list\n", encoding="utf-8")
    book = router / "playbooks" / "bug-fix.md"
    book.write_text("---\ntrigger: a defect\n---\n", encoding="utf-8")
    ours, upstream = _router_hash(tmp_path, True), _router_hash(tmp_path, False)

    book.write_text("---\ntrigger: a defect, edited\n---\n", encoding="utf-8")
    (router / "playbooks" / "bug-fix" / "flakes.md").write_text("x\n", "utf-8")
    assert _router_hash(tmp_path, True) == ours
    assert _router_hash(tmp_path, False) != upstream

    (router / "references" / "catalog.md").write_text("edited\n", encoding="utf-8")
    assert _router_hash(tmp_path, True) != ours
