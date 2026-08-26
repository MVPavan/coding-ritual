"""Whether a `writes = true` runner can reach the `.git` the wrapper then runs.

`writes = true` grants the checkout and `.git` sits inside it, so a runner that
can write `.git/config` or `.git/hooks/` names PROGRAMS the supervisor's own git
executes as the wrapper — outside the sandbox that bounded the runner.
`git worktree add` runs `post-checkout` and `git add --all` runs
`filter.<x>.clean`, and §5.4 makes both calls on a tree the runner just had.

The earlier version of this docstring said codex's sandbox "grants a directory
and cannot exclude a subdirectory of it", so the wrapper's own git was the only
answer. That is WRONG and the probes say so. What each vendor actually gives:

- **codex** — the sandbox makes `<root>/.git` read-only inside every writable
  root, in both `writes` modes, whether `.git` is a directory (in-repo band) or
  the `gitdir:` FILE a worktree has (probes P2.2/P2.3). OS-enforced. The ruling
  is executed here rather than quoted: `codex sandbox` runs a command under the
  real sandbox with no model turn, so it costs nothing to assert.
- **claude** — no sandbox at all. `Edit(//<cwd>/.git)` and `Edit(//<cwd>/.git/**)`
  deny both shapes at the permission engine, and a granted `Bash` is the §0.3
  cooperative residual that no rule closes.

`gitio`'s own hardening is belt-and-braces on top of that, and it is three named
keys rather than a class: `core.hooksPath`, `core.pager`, `core.fsmonitor`, plus
the two ambient config files. `filter.*` is NOT pinned and cannot be — the
driver name comes from the repository's `.gitattributes` — which is why the
vendor bounds above are the load-bearing half.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Final

import pytest

from tests._profiles import make_claude, make_task
from tests._supervisor import GIT_TIMEOUT_S, FrozenClock, head_of, make_repo
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.gitio import Git, GitSubcommand

SENTINEL: Final[str] = "the-runners-hook-ran"
HOOK: Final[str] = "#!/bin/sh\nprintf ran > {sentinel}\n"

CODEX: Final[str] = "codex"
_SKIP_NO_CODEX: Final[str] = "the codex binary is not on PATH"
SANDBOX_TIMEOUT_S: Final[float] = 120.0
EROFS: Final[str] = "Read-only file system"
WROTE_TREE: Final[str] = "TREE_WROTE"
_SANDBOX_PROBE: Final[str] = (
    f'echo tree > f.txt && echo "{WROTE_TREE}"; (echo x > {{target}}) 2>&1; true'
)
"""What a `writes = true` codex child could try, phrased the only way it could:
relative to the root it was granted. Stderr is folded into stdout because the
refusal is the shell's report of the sandbox's `EROFS`, not codex's own."""


def _plant_hook(repo: Path, name: str, sentinel: Path) -> None:
    """Write an executable hook of the kind a `writes = true` runner could."""
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    hook = hooks / name
    hook.write_text(HOOK.format(sentinel=sentinel), encoding="utf-8")
    hook.chmod(0o755)


def _config(repo: Path, tmp_path: Path) -> SupervisorConfig:
    """A supervisor configuration over a throwaway repo."""
    return SupervisorConfig.model_validate(
        {"repo_root": repo, "wrapper_root": tmp_path / ".wf", "host": "lab"}
    )


def test_a_hook_the_runner_planted_never_runs_as_the_wrapper(tmp_path: Path) -> None:
    """`git worktree add` runs `post-checkout`; the wrapper's git must not.

    The control below proves the hook is real: run through plain `git` in the
    same repo, it fires.
    """
    repo = make_repo(tmp_path)
    sentinel = tmp_path / SENTINEL
    _plant_hook(repo, "post-checkout", sentinel)
    git = Git(_config(repo, tmp_path))

    git.run(
        GitSubcommand.WORKTREE,
        "add",
        "--detach",
        str(tmp_path / ".wf" / "wt"),
        head_of(repo),
        cwd=repo,
    )

    assert not sentinel.exists()


def test_the_control_shows_the_planted_hook_really_does_fire(tmp_path: Path) -> None:
    """Without the hardening, the same hook runs — so the test above proves it."""
    repo = make_repo(tmp_path)
    sentinel = tmp_path / SENTINEL
    _plant_hook(repo, "post-checkout", sentinel)

    subprocess.run(
        ["git", "worktree", "add", "--detach", str(tmp_path / "plain"), head_of(repo)],
        cwd=repo,
        check=True,
        capture_output=True,
        timeout=GIT_TIMEOUT_S,
    )

    assert sentinel.read_text(encoding="utf-8") == "ran"


def test_every_invocation_pins_the_config_keys_that_name_a_program(
    tmp_path: Path,
) -> None:
    """`core.pager`, `core.fsmonitor`, `core.hooksPath` and both ambient files.

    Asserted on the argv a stub `git` records, because two of the three keys have
    no observable effect on a `status` and the point is that they are ALWAYS sent
    — not that this particular subcommand would have been affected. The two
    environment entries are read back from the child's own environment for the
    same reason: `GIT_CONFIG_GLOBAL` makes what a wrapper git call does
    independent of whatever the operator has in `~/.gitconfig`, so a host with a
    populated one and a host without must send the identical thing.
    """
    repo = make_repo(tmp_path)
    recorder = tmp_path / "record-git"
    recorded = tmp_path / "argv.txt"
    recorder.write_text(
        f'#!/bin/sh\nprintf "%s\\n" "$@" > {recorded}\n'
        f'printf "%s\\n" "NOSYSTEM=$GIT_CONFIG_NOSYSTEM" >> {recorded}\n'
        f'printf "%s\\n" "GLOBAL=$GIT_CONFIG_GLOBAL" >> {recorded}\n',
        encoding="utf-8",
    )
    recorder.chmod(0o755)
    config = _config(repo, tmp_path).model_copy(update={"git_binary": str(recorder)})

    Git(config).run(GitSubcommand.STATUS, "--porcelain", cwd=repo)

    argv = recorded.read_text(encoding="utf-8").splitlines()
    assert "core.fsmonitor=false" in argv
    assert "core.pager=cat" in argv
    hooks = [item for item in argv if item.startswith("core.hooksPath=")]
    assert hooks == [f"core.hooksPath={tmp_path / '.wf' / 'empty-hooks'}"]
    assert not list((tmp_path / ".wf" / "empty-hooks").iterdir())
    assert "NOSYSTEM=1" in argv
    assert f"GLOBAL={os.devnull}" in argv
    assert argv.index("status") > argv.index("core.pager=cat")


@pytest.mark.parametrize("writes", [True, False])
def test_claude_denies_the_checkouts_git_directory_and_the_git_file(
    tmp_path: Path, writes: bool
) -> None:
    """Path-exact grants can exclude `.git`, so claude's do — in BOTH shapes.

    A `writes = false` node has no rule granting the checkout at all, so the
    denials are only meaningful — and only emitted — for a writing one.

    The `/**` form alone was a hole. A glob needs a `.git/` path SEGMENT to
    match, and §5.4's worktree has `.git` as a FILE holding `gitdir: <path>`;
    an `Edit` could repoint it at a gitdir inside the runner's own grant and own
    the config of every later `git -C <worktree>` the wrapper runs. Both spellings
    are asserted because only one of them covers the deployment mode this
    wrapper actually uses by default.
    """
    task = make_task(tmp_path, writes=writes)
    profile = make_claude(tmp_path, FrozenClock())

    command = profile.build_command(task, "3a4b16d0-3f0f-4e0a-9f4c-6f7f2c37a1f6")

    for denied in (f"Edit(/{task.cwd}/.git)", f"Edit(/{task.cwd}/.git/**)"):
        assert (denied in command.argv) is writes, denied
        if writes:
            assert command.argv.index(denied) > command.argv.index("--disallowedTools")


# --- the codex half, executed rather than quoted --------------------------


def _sandbox_write(cwd: Path, target: str) -> str:
    """Try one write under codex's REAL workspace-write sandbox; no model turn.

    `codex sandbox` runs an argv inside the sandbox the config describes and
    returns, so this spends no tokens and needs no auth. The flags are the ones
    `CodexProfile` emits for a `writes = true` node, minus the writable roots
    the §6 channels get — the question is what happens at the ROOT.
    """
    done = subprocess.run(
        [
            CODEX,
            "sandbox",
            "-c",
            'sandbox_mode="workspace-write"',
            "-c",
            "sandbox_workspace_write.network_access=false",
            "-c",
            "sandbox_workspace_write.exclude_slash_tmp=true",
            "--",
            "sh",
            "-c",
            _SANDBOX_PROBE.format(target=target),
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=SANDBOX_TIMEOUT_S,
    )
    return f"{done.stdout}{done.stderr}"


@pytest.mark.proc
@pytest.mark.parametrize(
    ("layout", "target"), [("repo", ".git/config"), ("worktree", ".git")]
)
def test_the_codex_sandbox_makes_dot_git_read_only_in_the_layout_it_is_given(
    tmp_path: Path, layout: str, target: str
) -> None:
    """The ruling behind `sandboxed = True`, run against the real sandbox.

    Two layouts, because `.git` has two shapes and the earlier claim covered
    neither honestly. In the §12 in-repo band the runner's root is the repo and
    `.git` is a DIRECTORY; in §5.4 worktree mode the root is a worktree and
    `.git` is a FILE naming the real gitdir. Each parameter names the thing a
    runner in that layout would actually have to write, and asserts the sandbox
    refuses it with `EROFS` — while the surrounding tree stays writable, which is
    the control that keeps this from passing because nothing ran.

    Skipped rather than assumed when codex is absent: an assertion about an OS
    sandbox that silently does not run is worse than no assertion (§0.3).
    """
    if shutil.which(CODEX) is None:
        pytest.skip(_SKIP_NO_CODEX)
    repo = make_repo(tmp_path)
    if layout == "worktree":
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(tmp_path / "wt"), head_of(repo)],
            cwd=repo,
            check=True,
            capture_output=True,
            timeout=GIT_TIMEOUT_S,
        )
        assert (tmp_path / "wt" / ".git").is_file()
    cwd = repo if layout == "repo" else tmp_path / "wt"

    observed = _sandbox_write(cwd, target)

    assert WROTE_TREE in observed, observed
    assert EROFS in observed, observed
