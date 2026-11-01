"""`scan.py catalog` on a sparse checkout scans a full export of its HEAD, since a
scan of the partial tree would look complete and carry the right commit."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from curation.scan.cli import main


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    return result.stdout.strip()


def _repo(root: Path) -> str:
    for name in ("kept", "other"):
        skill = root / name / "skills" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\nname: {name}\n---\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "init")
    return _git(root, "rev-parse", "HEAD")


def _catalog(repo: Path, out: Path) -> dict[str, object]:
    assert main(["catalog", str(repo), "--name", "h", "--out", str(out)]) == 0
    data: dict[str, object] = json.loads(out.read_text(encoding="utf-8"))
    return data


def _ids(catalog: dict[str, object]) -> set[str]:
    caps = catalog["capabilities"]
    assert isinstance(caps, list)
    return {str(c["logical_id"]) for c in caps}


def test_sparse_checkout_is_cataloged_whole(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    commit = _repo(repo)
    _git(repo, "sparse-checkout", "set", "kept")
    assert not (repo / "other").exists()

    catalog = _catalog(repo, tmp_path / "out.json")

    assert _ids(catalog) == {"skill:kept/skills/kept", "skill:other/skills/other"}
    assert (catalog["source"], catalog["source_commit"]) == ("working-tree", commit)
    assert f"full export of HEAD {commit[:10]}" in capsys.readouterr().out


def test_other_checkout_scans_its_working_tree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    commit = _repo(repo)
    # Not committed, so only a working-tree scan finds it.
    new = repo / "new" / "skills" / "new"
    new.mkdir(parents=True)
    (new / "SKILL.md").write_text("---\nname: new\n---\n", encoding="utf-8")

    catalog = _catalog(repo, tmp_path / "out.json")

    assert "skill:new/skills/new" in _ids(catalog)
    assert (catalog["source"], catalog["source_commit"]) == ("working-tree", commit)
    assert "sparse" not in capsys.readouterr().out
