"""`interrogate/scripts/`: what the copy and the checkout check promise an adversary's run."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[2] / ".claude/skills/interrogate/scripts"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def run(script: str, *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPTS / script), *map(str, args)],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    git(path, "init", "-q")
    git(path, "config", "user.email", "t@example.invalid")
    git(path, "config", "user.name", "t")
    (path / "a.txt").write_text("one\n")
    (path / "b.txt").write_text("one\n")
    (path / ".gitignore").write_text("ignored/\n")
    git(path, "add", ".")
    git(path, "commit", "-qm", "start")
    return path


def object_files(repo: Path) -> set[tuple[int, int]]:
    found = (repo / ".git/objects").rglob("*")
    return {(s.st_dev, s.st_ino) for s in (f.stat() for f in found if f.is_file())}


def install_hook(repo: Path) -> None:
    hook = repo / ".git/hooks/post-index-change"
    hook.parent.mkdir(exist_ok=True)
    hook.write_text("#!/bin/sh\nprintf hook-ran >> a.txt\n")
    hook.chmod(0o755)


def test_copy_carries_every_state_and_shares_nothing(
    repo: Path, tmp_path: Path
) -> None:
    (repo / "a.txt").write_text("staged\n")
    git(repo, "add", "a.txt")
    (repo / "b.txt").write_text("unstaged\n")
    (repo / "new.txt").write_text("new\n")
    (repo / "ignored").mkdir()
    (repo / "ignored/x").write_text("x\n")
    copy = tmp_path / "copy"

    assert run("make-copy.sh", repo, copy).returncode == 0

    assert git(copy, "rev-parse", "HEAD") == git(repo, "rev-parse", "HEAD")
    assert git(copy, "status", "--short") == git(repo, "status", "--short")
    assert (copy / "new.txt").read_text() == "new\n"
    assert not (copy / "ignored").exists()
    assert git(copy, "remote") == ""
    assert not (copy / ".git/objects/info/alternates").exists()
    assert not object_files(repo) & object_files(copy)


@pytest.mark.parametrize(
    "spoil",
    [
        lambda repo: git(repo, "add", "-N", "c.txt"),
        lambda repo: git(repo, "config", "core.sparseCheckout", "true"),
    ],
    ids=["intent-to-add", "sparse-checkout"],
)
def test_refusal_stops_with_a_reason_and_no_state(
    repo: Path, tmp_path: Path, spoil
) -> None:
    (repo / "c.txt").write_text("c\n")
    spoil(repo)
    done = run("make-copy.sh", repo, tmp_path / "copy")
    assert done.returncode == 2
    assert done.stderr.startswith("make-copy:")
    assert not (tmp_path / "copy.state").exists()


def test_destination_inside_the_checkout_is_refused(repo: Path) -> None:
    assert run("make-copy.sh", repo, repo / "copy").returncode == 2
    assert not (repo / "copy").exists()


def test_copy_from_pristine_refuses_a_changed_snapshot(
    repo: Path, tmp_path: Path
) -> None:
    pristine = tmp_path / "pristine"
    assert run("make-copy.sh", repo, pristine).returncode == 0
    state = f"{pristine}.state"
    assert (
        run("make-copy.sh", "--expect", state, pristine, tmp_path / "ok").returncode
        == 0
    )
    (pristine / "a.txt").write_text("attacked\n")
    assert (
        run("make-copy.sh", "--expect", state, pristine, tmp_path / "no").returncode
        == 2
    )


def test_check_names_a_change_git_status_misses(repo: Path, tmp_path: Path) -> None:
    git(repo, "config", "core.fileMode", "false")
    pristine = tmp_path / "pristine"
    assert run("make-copy.sh", repo, pristine).returncode == 0
    state = f"{pristine}.state"
    assert run("checkout-changes.sh", state, repo).returncode == 0

    (repo / "a.txt").chmod(0o755)
    assert git(repo, "status", "--short") == ""
    done = run("checkout-changes.sh", state, repo)

    assert done.returncode == 1
    assert "a.txt" in done.stdout


def test_a_source_hook_cannot_change_the_checkout(repo: Path, tmp_path: Path) -> None:
    pristine = tmp_path / "pristine"
    assert run("make-copy.sh", repo, pristine).returncode == 0
    install_hook(repo)

    assert run("checkout-changes.sh", f"{pristine}.state", repo).returncode == 0
    assert run("make-copy.sh", repo, tmp_path / "second").returncode == 0

    assert (repo / "a.txt").read_text() == "one\n"


def test_check_says_when_it_could_not_check(tmp_path: Path) -> None:
    assert run("checkout-changes.sh", tmp_path / "missing.state").returncode == 2
