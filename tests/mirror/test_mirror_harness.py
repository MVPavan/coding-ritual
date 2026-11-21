"""The harness's own isolation: what a hook or shell exports never steers the test store."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.mirror._harness import make_store, scrubbed_env

pytestmark = pytest.mark.bd


def test_harness_store_ignores_inherited_git_selectors_and_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=decoy, env=scrubbed_env(), check=True)
    config = (decoy / ".git" / "config").read_text()
    redirect = tmp_path / "redirect.gitconfig"
    redirect.write_text("[init]\n\tdefaultBranch = redirected\n")
    monkeypatch.setenv("GIT_DIR", str(decoy / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(decoy))
    monkeypatch.setenv("GIT_INDEX_FILE", str(decoy / ".git" / "index"))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(redirect))

    store = tmp_path / "store"
    make_store(store, "mh")
    assert (store / ".git").is_dir() and (store / ".beads").is_dir()
    assert "redirected" not in (store / ".git" / "HEAD").read_text()
    assert not (decoy / ".beads").exists()
    assert (decoy / ".git" / "config").read_text() == config
