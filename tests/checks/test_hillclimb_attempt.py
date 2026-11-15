"""`playbooks/hillclimb/attempt.py`: undo exactly one attempt and nothing else."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

HELPER = (
    Path(__file__).parents[2] / ".claude/skills/mvp-mode/playbooks/hillclimb/attempt.py"
)
ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}
BASE = "one\ntwo\nthree\nfour\nfive\nsix\nseven\neight\n"
BINARY = bytes(range(256))
REFUSED = 2
MISMATCH = 1


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args], cwd=repo, env=ENV, capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


def tool(repo: Path, *args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HELPER), *map(str, args)],
        cwd=repo,
        env=ENV,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    (path / "a.txt").write_text(BASE)
    (path / "b.txt").write_text("b\n")
    git(path, "add", "a.txt", "b.txt")
    git(path, "commit", "-qm", "base")
    return path


def snapshot(repo: Path) -> tuple[str, str]:
    tree, index = tool(repo, "snapshot").stdout.split()
    return tree, index


def attempt(repo: Path, edit) -> tuple[Path, str, str]:
    """Snapshot, edit, snapshot, patch: what undo takes."""
    start, index = snapshot(repo)
    edit()
    end, _ = snapshot(repo)
    patch = repo.parent / f"{start[:8]}-{end[:8]}.patch"
    assert tool(repo, "patch", start, end, patch).returncode == 0
    return patch, start, index


def test_kept_then_rejected_in_one_file_undoes_only_the_reject(repo: Path) -> None:
    a = repo / "a.txt"
    attempt(repo, lambda: a.write_text(BASE.replace("one", "KEPT")))
    kept = a.read_text()
    rejected = attempt(repo, lambda: a.write_text(kept.replace("eight", "REJECTED")))
    assert tool(repo, "undo", *rejected).returncode == 0
    assert a.read_text() == kept


def test_another_writers_dirty_path_is_untouched(repo: Path) -> None:
    (repo / "b.txt").write_text("theirs\n")
    (repo / "theirs.txt").write_text("untracked\n")
    done = attempt(repo, lambda: (repo / "a.txt").write_text("mine\n"))
    assert tool(repo, "undo", *done).returncode == 0
    assert (repo / "a.txt").read_text() == BASE
    assert (repo / "b.txt").read_text() == "theirs\n"
    assert (repo / "theirs.txt").read_text() == "untracked\n"


def test_created_and_deleted_files_come_back(repo: Path) -> None:
    def edit() -> None:
        (repo / "new.txt").write_text("new\n")
        (repo / "b.txt").unlink()

    done = attempt(repo, edit)
    assert tool(repo, "undo", *done).returncode == 0
    assert not (repo / "new.txt").exists()
    assert (repo / "b.txt").read_text() == "b\n"


def test_binary_file_round_trips(repo: Path) -> None:
    (repo / "blob.bin").write_bytes(BINARY)
    done = attempt(repo, lambda: (repo / "blob.bin").write_bytes(BINARY[::-1]))
    assert tool(repo, "undo", *done).returncode == 0
    assert (repo / "blob.bin").read_bytes() == BINARY


def test_refused_reverse_changes_nothing_and_exits_non_zero(repo: Path) -> None:
    def edit() -> None:
        (repo / "a.txt").write_text(BASE.replace("one", "A"))
        (repo / "b.txt").write_text("mine\n")

    done = attempt(repo, edit)
    (repo / "b.txt").write_text("moved on\n")
    result = tool(repo, "undo", *done)
    assert result.returncode == REFUSED
    assert (repo / "a.txt").read_text() == BASE.replace("one", "A")
    assert (repo / "b.txt").read_text() == "moved on\n"


def test_verify_fails_on_a_wrong_tree(repo: Path) -> None:
    tree, index = snapshot(repo)
    assert tool(repo, "verify", tree, index).returncode == 0
    (repo / "a.txt").write_text("drift\n")
    assert tool(repo, "verify", tree, index).returncode == MISMATCH


def test_a_byte_converting_file_is_refused(repo: Path) -> None:
    (repo / ".gitattributes").write_text("*.txt text eol=lf\n")
    (repo / "crlf.txt").write_bytes(b"one\r\ntwo\r\n")
    assert tool(repo, "snapshot").returncode == REFUSED


def test_a_file_git_would_rewrite_on_the_way_out_is_refused(repo: Path) -> None:
    (repo / ".gitattributes").write_text("lf.txt text eol=crlf\n")
    (repo / "lf.txt").write_bytes(b"one\ntwo\n")
    assert tool(repo, "snapshot").returncode == REFUSED
    assert (repo / "lf.txt").read_bytes() == b"one\ntwo\n"


def test_an_identity_filter_in_with_a_changing_filter_out_is_refused(
    repo: Path,
) -> None:
    git(repo, "config", "filter.upper.clean", "cat")
    git(repo, "config", "filter.upper.smudge", "tr a-z A-Z")
    (repo / ".gitattributes").write_text("up.txt filter=upper\n")
    (repo / "up.txt").write_bytes(b"lower\n")
    assert tool(repo, "snapshot").returncode == REFUSED
    assert (repo / "up.txt").read_bytes() == b"lower\n"


def test_attributes_changed_after_the_end_snapshot_refuse_before_applying(
    repo: Path,
) -> None:
    done = attempt(repo, lambda: (repo / "a.txt").write_text("mine\n"))
    (repo / ".gitattributes").write_text("a.txt text eol=crlf\n")
    assert tool(repo, "undo", *done).returncode == REFUSED
    assert (repo / "a.txt").read_bytes() == b"mine\n"


@pytest.mark.parametrize("smudge", ["cat; printf '\\n'", "cat; printf '\\nTAIL'"])
def test_a_filter_adding_a_tail_to_the_last_file_is_refused(
    repo: Path, smudge: str
) -> None:
    git(repo, "config", "filter.tail.clean", "cat")
    git(repo, "config", "filter.tail.smudge", smudge)
    (repo / ".gitattributes").write_text("z.txt filter=tail\n")
    (repo / "z.txt").write_bytes(b"last\n")
    assert tool(repo, "snapshot").returncode == REFUSED
    assert (repo / "z.txt").read_bytes() == b"last\n"


def test_attributes_added_after_a_deletion_refuse_with_the_file_still_absent(
    repo: Path,
) -> None:
    done = attempt(repo, (repo / "a.txt").unlink)
    (repo / ".gitattributes").write_text("a.txt text eol=crlf\n")
    assert tool(repo, "undo", *done).returncode == REFUSED
    assert not (repo / "a.txt").exists()


@pytest.mark.parametrize("path", [".gitattributes", "deep/er/.gitattributes"])
def test_a_patch_changing_gitattributes_is_refused(repo: Path, path: str) -> None:
    start, _ = snapshot(repo)
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text("# rule\n")
    end, _ = snapshot(repo)
    out = repo.parent / "attrs.patch"
    assert tool(repo, "patch", start, end, out).returncode == REFUSED
    assert not out.exists()


def test_a_foreign_edit_after_the_end_snapshot_refuses_and_touches_nothing(
    repo: Path,
) -> None:
    done = attempt(repo, lambda: (repo / "a.txt").write_text("mine\n"))
    (repo / "b.txt").write_text("theirs\n")
    assert tool(repo, "undo", *done).returncode == REFUSED
    assert (repo / "a.txt").read_text() == "mine\n"
    assert (repo / "b.txt").read_text() == "theirs\n"


def test_a_refusal_after_a_real_apply_exits_one(repo: Path) -> None:
    done = attempt(repo, (repo / "a.txt").unlink)
    (repo / ".git/info/attributes").write_text("a.txt text eol=crlf\n")
    assert tool(repo, "undo", *done).returncode == MISMATCH


def test_a_failure_during_the_real_apply_exits_one(repo: Path) -> None:
    (repo / ".gitignore").write_text("ignored\n")
    git(repo, "add", ".gitignore")
    git(repo, "commit", "-qm", "ignore")

    def edit() -> None:
        (repo / "a.txt").unlink()
        (repo / "a.txt").mkdir()
        (repo / "a.txt/child").write_text("child\n")
        (repo / "a.txt/ignored").write_text("ignored\n")

    assert tool(repo, "undo", *attempt(repo, edit)).returncode == MISMATCH


def test_odd_paths_snapshot_and_come_back(repo: Path) -> None:
    odd = repo / " lead\nnew line.txt"
    odd.write_text("odd\n")
    (repo / "empty.txt").write_bytes(b"")
    done = attempt(repo, lambda: odd.write_text("changed\n"))
    assert tool(repo, "undo", *done).returncode == 0
    assert odd.read_text() == "odd\n"


def test_a_patch_inside_the_tree_is_refused_unless_ignored(repo: Path) -> None:
    (repo / ".gitignore").write_text("ignored/\n")
    (repo / "ignored").mkdir()
    start, _ = snapshot(repo)
    (repo / "a.txt").write_text("mine\n")
    end, _ = snapshot(repo)
    inside = repo / "a.patch"
    assert tool(repo, "patch", start, end, inside).returncode == REFUSED
    assert not inside.exists()
    assert tool(repo, "patch", start, end, repo / "ignored/a.patch").returncode == 0
    assert tool(repo, "patch", start, end, repo.parent / "a.patch").returncode == 0


def test_an_edit_between_snapshots_is_named_by_the_patch(repo: Path) -> None:
    def edit() -> None:
        (repo / "a.txt").write_text("mine\n")
        (repo / "b.txt").write_text("theirs\n")

    patch, _, _ = attempt(repo, edit)
    assert "b.txt" in git(repo, "apply", "--numstat", str(patch))
