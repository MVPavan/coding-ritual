"""`.claude/hooks/block-dangerous-commands.sh` run on JSON payloads, asserting its exit codes."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

BASH = shutil.which("bash") or "/bin/bash"
HOOK = Path(__file__).resolve().parents[2] / ".claude/hooks/block-dangerous-commands.sh"

BLOCKED_FORMS = [
    "push --force origin main",
    "push -f",
    "reset --hard HEAD",
    "clean -fd",
    "clean -f",
    "branch -D topic",
    "checkout .",
    "restore .",
]
GLOBAL_PREFIXES = [
    "-C /x",
    "-C '/a b'",
    "-c core.x=1",
    '-c "user.name=A B"',
    "--git-dir=/x/gd",
    "--git-dir /x/gd",
    "--work-tree=/x",
    "--work-tree /x",
    "--namespace=ns",
    "--namespace ns",
    "--no-pager",
    "--bare",
    "--literal-pathspecs",
    "-p",
    "-C /x -c a=b --no-pager --git-dir=/x/gd",
    "--no-optional-locks -C /x --work-tree /x -c a.b=c",
    "--shallow-file /dev/null",
    "--shallow-file /dev/null -C /tmp -c a.b=c",
    '-c user.name="A B"',
    "-C /a\\ b",
    '-C /a/"b c"',
    "-C '/a\nb'",
]
ALLOWED = [
    "git push origin main",
    "git -C /x push origin main",
    "git reset --soft HEAD~1",
    "git reset --mixed HEAD~1",
    "git -c core.x=1 reset --soft HEAD~1",
    "git -C /x status",
    "git -C /x log --oneline -5",
    "git --no-pager log",
    'git commit -m "use git -C to change directory"',
    'echo "git -c pins config for one command"',
    "git -C /x branch -d topic",
    "git -c alias.note='!echo reset --hard' status",
    'git commit -m "document git -C /x reset --hard HEAD"',
    "rg -n 'git --no-pager reset --hard HEAD' README.md",
    'echo "git -C /x push --force origin main"',
    "git --exec-path reset --hard HEAD",
    "git status -- 'git reset' '--hard'",
    "git -C /x status -- 'git reset' '--hard'",
    "git -C /x status -- 'git' 'reset --hard'",
    "git -C /x add -- 'git push' '--force'",
]


def hook_result(
    command: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_input": {"command": command}}, separators=(",", ":"))
    return subprocess.run(
        [BASH, str(HOOK)],
        input=payload,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def run_hook(command: str, env: dict[str, str] | None = None) -> int:
    return hook_result(command, env).returncode


@pytest.mark.parametrize("form", BLOCKED_FORMS)
def test_blocks_without_global_options(form: str) -> None:
    assert run_hook(f"git {form}") == 2


@pytest.mark.parametrize("prefix", GLOBAL_PREFIXES)
@pytest.mark.parametrize("form", BLOCKED_FORMS)
def test_blocks_after_global_options(prefix: str, form: str) -> None:
    assert run_hook(f"git {prefix} {form}") == 2


def test_blocks_after_global_options_in_a_compound_command() -> None:
    assert run_hook("cd /x && /usr/bin/git -C /y push --force") == 2


@pytest.mark.parametrize("form", BLOCKED_FORMS)
def test_blocks_before_a_separate_command_full_of_git_words(form: str) -> None:
    assert run_hook(f"git {form}; echo " + "git " * 500) == 2


def test_many_git_words_finish_fast_and_block() -> None:
    started = time.perf_counter()
    assert run_hook("git reset --hard HEAD; echo " + "git " * 4000) == 2
    assert time.perf_counter() - started < 2


def test_many_global_options_finish_fast_and_block_in_the_tokenizer() -> None:
    started = time.perf_counter()
    result = hook_result("git" + " -C git" * 4000 + " -C /x reset --hard HEAD")
    assert time.perf_counter() - started < 2
    assert result.returncode == 2
    assert "after git global options" in result.stderr


def test_one_huge_word_blocks_within_the_parse_budget() -> None:
    started = time.perf_counter()
    result = hook_result("echo " + "x" * 2_000_000 + "; git -C /x status")
    assert time.perf_counter() - started < 4
    assert result.returncode == 2
    assert "too large to check" in result.stderr


def test_a_slow_parse_does_not_delay_the_other_checks() -> None:
    started = time.perf_counter()
    result = hook_result(": " + "x" * 1_000_000 + "git\nbd init " + "--" + "force")
    assert time.perf_counter() - started < 1
    assert result.returncode == 2
    assert "beads store" in result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "bd init " + "--" + "force\n: " + "x" * 1_000_000,
        "printf x > " + "docs/" + "workstreams/" + "status.md\n: " + "x" * 1_000_000,
    ],
    ids=["bd-init", "mirror-write"],
)
def test_other_checks_block_before_a_large_later_line(command: str) -> None:
    assert run_hook(command) == 2


@pytest.mark.parametrize(
    "command",
    [
        "git -C /x reset --hard HEAD # don't",
        "# don't\ngit -C /x reset --hard HEAD",
        "echo x#y; git -C /x reset --hard HEAD",
        "echo '#'; git -C /x reset --hard HEAD",
    ],
)
def test_comments_are_read_as_the_shell_reads_them(command: str) -> None:
    assert run_hook(command) == 2


def test_a_comment_is_not_checked() -> None:
    assert run_hook("echo ok # don't git -C /x push " + "--" + "force") == 0


def test_blocks_after_a_large_harmless_prefix() -> None:
    assert run_hook("echo " + "x" * 132_000 + "; git -C /x reset --hard HEAD") == 2


@pytest.mark.parametrize("command", ALLOWED)
def test_allows(command: str) -> None:
    assert run_hook(command) == 0


def path_with(tmp_path: Path, tools: tuple[str, ...]) -> dict[str, str]:
    for tool in tools:
        found = shutil.which(tool)
        assert found is not None
        (tmp_path / tool).symlink_to(found)
    return {**os.environ, "PATH": str(tmp_path)}


def test_blocks_after_global_options_without_jq(tmp_path: Path) -> None:
    env = path_with(tmp_path, ("cat", "grep", "sed", "python3"))
    assert run_hook("git -C /x push --force", env) == 2
    assert run_hook("git -C /x status", env) == 0


def test_without_python_only_the_original_text_is_checked(tmp_path: Path) -> None:
    env = path_with(tmp_path, ("cat", "grep", "sed", "jq"))
    assert run_hook("git push --force", env) == 2
    assert run_hook("git -C /x push --force", env) == 0


def test_untokenizable_text_falls_back_to_the_original_check() -> None:
    assert run_hook("git push --force 'unbalanced") == 2
    assert run_hook("git -C /x push --force 'unbalanced") == 0


def test_a_failing_python_blocks(tmp_path: Path) -> None:
    env = path_with(tmp_path, ("cat", "grep", "sed", "jq"))
    stub = tmp_path / "python3"
    stub.write_text("#!/bin/sh\nexit 1\n")
    stub.chmod(0o755)
    result = hook_result("git -C /x status", env)
    assert result.returncode == 2
    assert "could not parse" in result.stderr
