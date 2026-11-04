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
from curation.scan import cli as scan_cli
from tests.curation.test_registry import _make_cfg, _ns, _rec_ns, _write_round

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


@pytest.mark.parametrize(
    ("edited", "logical_id"),
    [
        ("playbooks/a/ref.md", PLAYBOOK),
        ("notes.md", "skill:skills/router"),
    ],
)
def test_catalog_diff_reports_a_change_only_to_bundled_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], edited: str, logical_id: str
) -> None:
    def catalog_file(root: Path, name: str) -> Path:
        out = tmp_path / name
        cat = scan.scan_repo(root, "r", name, None)
        out.write_text(json.dumps(cat.to_dict()), encoding="utf-8")
        return out

    def diff(old: Path, new: Path) -> str:
        capsys.readouterr()
        assert scan_cli.main(["diff", str(old), str(new)]) == 0
        return str(capsys.readouterr().out)

    upstream = tmp_path / "upstream"
    router = _router(upstream)
    old = catalog_file(upstream, "old.json")
    (router / edited).write_text("edited\n", encoding="utf-8")
    new = catalog_file(upstream, "new.json")

    report = diff(old, new)
    assert f"~ {logical_id}  [" in report
    assert "CHANGED (material)" in report

    # A legacy catalog has no folder hash: that is unknown, never a change.
    legacy = json.loads(old.read_text(encoding="utf-8"))
    for cap in legacy["capabilities"]:
        del cap["tree_hash"]
    old.write_text(json.dumps(legacy), encoding="utf-8")
    assert logical_id not in diff(old, new)


def _git(repo: Path, *args: str) -> str:
    identity = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    done = subprocess.run(
        ["git", "-C", str(repo), *identity, *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    return done.stdout.strip()


def test_gap_diffs_a_playbook_with_its_reference_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A ruling with only a commit baseline falls back to `git diff`, whose paths
    are also what `gap` prints: both must cover the playbook's reference folder."""
    cfg = _make_cfg(tmp_path)
    upstream = cfg.repo_root / "reference_harnesses" / "refrepo"
    router = _router(upstream)
    subprocess.run(["git", "init", "-q", str(upstream)], check=True, timeout=15)
    _git(upstream, "add", ".")
    _git(upstream, "commit", "-qm", "ruled")
    ruled = _git(upstream, "rev-parse", "HEAD")
    book = scan.scan_repo(upstream, "refrepo", "x", ruled).by_logical_id()[PLAYBOOK]
    _write_round(
        cfg,
        "2026-11-01-r",
        {
            "type": "event",
            "id": "2026-11-01-r:1",
            "date": "2026-11-01",
            "kind": "defer",
            "subject": f"refrepo:{PLAYBOOK}",
            "why": "not now",
            "revisit_when": "later",
            "evidence": ["x:1"],
            "source": {
                "repo": "refrepo",
                "logical_id": PLAYBOOK,
                "path": book.canonical_path,
                "sha": ruled,
                "content_hash": book.content_hash,
            },
        },
    )

    (router / "playbooks" / "a" / "ref.md").write_text("edited\n", encoding="utf-8")
    _git(upstream, "commit", "-qam", "reference edit")

    capsys.readouterr()
    assert cli.cmd_gap(cfg, _ns(reference="refrepo", kind=None, beads=False)) == 0
    out = capsys.readouterr().out
    assert "changed since ruled (1)" in out
    assert "-- skills/router/playbooks/a.md skills/router/playbooks/a/\n" in out
