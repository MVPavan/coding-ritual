"""`curation/scan/drift.py`: a changed mechanism never hides behind a move or a
small edit (astra harness review 2026-11-20)."""

from __future__ import annotations

from pathlib import Path

from curation.scan.catalog import scan_repo
from curation.scan.drift import diff_catalogs, render_diff
from curation.scan.models import CatalogDiff

FRONT = "---\nname: {name}\ndescription: Use when x.\n---\n\n"
BODY = "".join(f"Step {n}: do the thing number {n}.\n" for n in range(1, 50))


def _skill(root: Path, folder: str, body: str, helper: str) -> None:
    skill = root / "skills" / folder
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(FRONT.format(name="tool") + body)
    (skill / "helper.md").write_text(helper)


def _diff(
    tmp_path: Path, old: tuple[str, str, str], new: tuple[str, str, str]
) -> CatalogDiff:
    old_root, new_root = tmp_path / "old", tmp_path / "new"
    _skill(old_root, *old)
    _skill(new_root, *new)
    old_cat = scan_repo(old_root, "r", source="old", source_commit=None)
    new_cat = scan_repo(new_root, "r", source="new", source_commit=None)
    diff = diff_catalogs(old_cat, new_cat, old_root=old_root, new_root=new_root)
    assert render_diff(old_cat, new_cat, diff)  # renders without error
    return diff


def test_a_move_with_a_changed_helper_is_not_content_identical(tmp_path: Path) -> None:
    diff = _diff(
        tmp_path,
        ("tool", BODY, "Ask before deleting.\n"),
        ("tool-renamed", BODY, "Delete without asking.\n"),
    )

    assert diff.moved == ()
    [(cap, reason)] = diff.modified_material
    assert cap.logical_id.endswith("tool-renamed")
    assert "moved from" in reason and "needs a look" in reason


def test_an_identical_move_stays_a_move(tmp_path: Path) -> None:
    diff = _diff(tmp_path, ("tool", BODY, "h\n"), ("tool-renamed", BODY, "h\n"))

    assert len(diff.moved) == 1
    assert diff.modified_material == diff.modified_minor == ()


def test_a_one_line_instruction_edit_needs_a_look(tmp_path: Path) -> None:
    edited = BODY.replace("Step 7: do the thing", "Step 7: never do the thing")
    diff = _diff(tmp_path, ("tool", BODY, "h\n"), ("tool", edited, "h\n"))

    [(_, reason)] = diff.modified_material
    assert "needs a look" in reason and "small" in reason
    assert diff.modified_minor == ()


def test_magnitude_counts_every_changed_file_in_the_folder(tmp_path: Path) -> None:
    edited = BODY.replace("Step 7: do the thing", "Step 7: never do the thing")
    diff = _diff(tmp_path, ("tool", BODY, BODY), ("tool", edited, "Rewritten.\n"))

    [(_, reason)] = diff.modified_material
    assert "large" in reason and "in 2 of 2 files" in reason, reason


def test_a_move_cannot_hide_a_change_outside_the_scanned_set(tmp_path: Path) -> None:
    # `fixtures/` is skipped by the scan but covered by the folder hash.
    old_root, new_root = tmp_path / "old", tmp_path / "new"
    _skill(old_root, "tool", BODY, "h\n")
    _skill(new_root, "tool-renamed", BODY, "h\n")
    for root, text in ((old_root, "Ask first.\n"), (new_root, "Never ask.\n")):
        folder = next((root / "skills").iterdir()) / "fixtures"
        folder.mkdir()
        (folder / "instructions.md").write_text(text)
    old_cat = scan_repo(old_root, "r", source="old", source_commit=None)
    new_cat = scan_repo(new_root, "r", source="new", source_commit=None)

    diff = diff_catalogs(old_cat, new_cat, old_root=old_root, new_root=new_root)

    assert diff.moved == ()
    [(_, reason)] = diff.modified_material
    assert "needs a look" in reason
    assert "files outside the scanned set changed" in reason


def test_a_script_byte_change_is_never_formatting(tmp_path: Path) -> None:
    # A trailing space after a continuation backslash breaks the command.
    script = "#!/bin/sh\necho one \\\n  two\n"
    broken = script.replace("\\\n", "\\ \n")
    old_root, new_root = tmp_path / "old", tmp_path / "new"
    _skill(old_root, "tool", BODY, "h\n")
    _skill(new_root, "tool", BODY, "h\n")
    (old_root / "skills/tool/run.sh").write_text(script)
    (new_root / "skills/tool/run.sh").write_text(broken)
    old_cat = scan_repo(old_root, "r", source="old", source_commit=None)
    new_cat = scan_repo(new_root, "r", source="new", source_commit=None)

    diff = diff_catalogs(old_cat, new_cat, old_root=old_root, new_root=new_root)

    [(_, reason)] = diff.modified_material
    assert "needs a look" in reason and "in 1 of 3 files" in reason
    assert diff.modified_minor == ()


def test_trailing_space_in_markdown_prose_is_formatting(tmp_path: Path) -> None:
    diff = _diff(tmp_path, ("tool", BODY, "h\n"), ("tool", BODY, "h  \n"))

    assert diff.modified_material == ()
    [(_, reason)] = diff.modified_minor
    assert "Markdown formatting only" in reason
