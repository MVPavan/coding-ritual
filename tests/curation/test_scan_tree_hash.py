"""A playbook in a skill's `playbooks/` is its own unit (B1, T1): the skill's tree
hash leaves it out, an upstream one is cataloged on its own (F3) so its edits show
in `gap`, and ours are ledger subjects instead."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from curation.registry import cli
from curation.scan import catalog as scan
from tests.curation.test_registry import _make_cfg, _ns, _rec_ns

PLAYBOOK = "playbook:skills/router/playbooks/a"


def _router(root: Path) -> Path:
    router = root / "skills" / "router"
    (router / "playbooks" / "a").mkdir(parents=True)
    (router / "SKILL.md").write_text("---\nname: router\n---\n", encoding="utf-8")
    (router / "notes.md").write_text("notes\n", encoding="utf-8")
    (router / "playbooks" / "a.md").write_text("# a\n", encoding="utf-8")
    (router / "playbooks" / "a" / "ref.md").write_text("ref\n", encoding="utf-8")
    return router


def _hashes(root: Path) -> tuple[str, str]:
    caps = scan.scan_repo(root, "r", "working-tree", None).by_logical_id()
    return caps["skill:skills/router"].tree_hash, caps[PLAYBOOK].tree_hash


def test_playbook_is_cataloged_as_its_own_unit(tmp_path: Path) -> None:
    _router(tmp_path)
    caps = scan.scan_repo(tmp_path, "r", "working-tree", None).by_logical_id()
    book = caps[PLAYBOOK]
    assert (book.kind.value, book.name) == ("playbook", "a")
    assert book.canonical_path == "skills/router/playbooks/a.md"
    assert book.assets == ("skills/router/playbooks/a/ref.md",)
    assert caps["skill:skills/router"].assets == ("skills/router/notes.md",)
    # A reference is not a playbook, and our own scan catalogs none: ours are
    # ledger subjects.
    assert [c for c in caps if c.startswith("playbook:")] == [PLAYBOOK]
    ours = scan.scan_repo(tmp_path, "r", "x", None, catalog_playbooks=False)
    assert not [c for c in ours.by_logical_id() if c.startswith("playbook:")]


def test_edits_change_only_the_owning_unit(tmp_path: Path) -> None:
    router = _router(tmp_path)
    skill, book = _hashes(tmp_path)

    (router / "playbooks" / "a.md").write_text("# a, edited\n", encoding="utf-8")
    assert _hashes(tmp_path)[0] == skill
    edited = _hashes(tmp_path)[1]
    assert edited != book

    (router / "playbooks" / "a" / "ref.md").write_text("edited\n", encoding="utf-8")
    assert _hashes(tmp_path)[0] == skill
    assert _hashes(tmp_path)[1] != edited

    edited = _hashes(tmp_path)[1]
    (router / "notes.md").write_text("edited\n", encoding="utf-8")
    assert _hashes(tmp_path)[0] != skill
    assert _hashes(tmp_path)[1] == edited


@pytest.mark.parametrize("stray", ["playbooks/stray.txt", "playbooks/shared/ref.md"])
def test_a_file_no_playbook_owns_stays_with_the_skill(
    tmp_path: Path, stray: str
) -> None:
    router = _router(tmp_path)
    file = router / stray
    file.parent.mkdir(exist_ok=True)
    file.write_text("x\n", encoding="utf-8")
    skill, book = _hashes(tmp_path)
    caps = scan.scan_repo(tmp_path, "r", "working-tree", None).by_logical_id()
    assert f"skills/router/{stray}" in caps["skill:skills/router"].assets

    file.write_text("edited\n", encoding="utf-8")
    assert _hashes(tmp_path) != (skill, book)
    assert _hashes(tmp_path)[1] == book


def test_a_playbook_the_scan_skips_owns_nothing(tmp_path: Path) -> None:
    _router(tmp_path)
    (tmp_path / ".gitignore").write_text("/skills/router/playbooks/a.md\n", "utf-8")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, timeout=15)
    caps = scan.scan_repo(tmp_path, "r", "working-tree", None).by_logical_id()
    assert PLAYBOOK not in caps
    assert "skills/router/playbooks/a/ref.md" in caps["skill:skills/router"].assets


def test_skill_without_playbooks_hashes_as_before(tmp_path: Path) -> None:
    folder = tmp_path / "skills" / "plain"
    (folder / "references").mkdir(parents=True)
    (folder / "SKILL.md").write_bytes(b"skill\n")
    (folder / "references" / "r.md").write_bytes(b"ref\n")
    want = hashlib.sha256(b"SKILL.md\x006\x00skill\nreferences/r.md\x004\x00ref\n")
    cat = scan.scan_repo(tmp_path, "r", "working-tree", None)
    assert cat.by_logical_id()["skill:skills/plain"].tree_hash == want.hexdigest()


def _gap(
    cfg: Any, upstream: Path, kind: str, capsys: pytest.CaptureFixture[str]
) -> str:
    cat = scan.scan_repo(upstream, "refrepo", "working-tree", "pin")
    (cfg.catalogs_dir / "refrepo.json").write_text(
        json.dumps(cat.to_dict()), encoding="utf-8"
    )
    capsys.readouterr()
    assert cli.cmd_gap(cfg, _ns(reference="refrepo", kind=kind, beads=False)) == 0
    return str(capsys.readouterr().out)


def _rule(cfg: Any, logical_id: str) -> None:
    cli.cmd_round(
        cfg,
        _ns(
            round_command="open",
            slug="2026-11-01-r",
            date="2026-11-01",
            scope="s",
            json=None,
            json_file=None,
            stdin=False,
        ),
    )
    ruling = {
        "kind": "defer",
        "subject": f"refrepo:{logical_id}",
        "why": "not now",
        "revisit_when": "later",
        "evidence": ["x:1"],
    }
    assert cli.cmd_record(cfg, _rec_ns(json=json.dumps(ruling))) == 0


def test_gap_follows_a_playbook_through_its_ruling(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = _make_cfg(tmp_path)
    upstream = tmp_path / "upstream"
    router = _router(upstream)

    def gap() -> str:
        return _gap(cfg, upstream, "playbook", capsys)

    assert f"+ {PLAYBOOK}" in gap()  # unruled

    _rule(cfg, PLAYBOOK)
    assert PLAYBOOK not in gap()  # ruled

    (router / "playbooks" / "a" / "ref.md").write_text("edited\n", encoding="utf-8")
    assert PLAYBOOK in gap()  # changed upstream, by its reference alone

    (router / "playbooks" / "a.md").unlink()
    (router / "playbooks" / "a" / "ref.md").unlink()
    assert "removed upstream" in gap()


@pytest.mark.parametrize("stray", ["playbooks/stray.txt", "playbooks/shared/ref.md"])
def test_gap_shows_a_stray_edit_on_the_ruled_skill(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], stray: str
) -> None:
    cfg = _make_cfg(tmp_path)
    upstream = tmp_path / "upstream"
    router = _router(upstream)
    file = router / stray
    file.parent.mkdir(exist_ok=True)
    file.write_text("x\n", encoding="utf-8")

    def gap() -> str:
        return _gap(cfg, upstream, "skill", capsys)

    gap()
    _rule(cfg, "skill:skills/router")
    assert "skill:skills/router" not in gap()

    (router / "playbooks" / "a.md").write_text("# a, edited\n", encoding="utf-8")
    assert "skill:skills/router" not in gap()  # the playbook's, not the skill's

    file.write_text("edited\n", encoding="utf-8")
    assert "skill:skills/router" in gap()
