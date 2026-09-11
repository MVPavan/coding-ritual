"""Closed, workspace-confined Git command transport shared by snapshotters."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Final

import structlog

from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.errors import GitCommandError

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

_MSG_FAILED: Final[str] = "git {subcommand} failed (exit {returncode}): {stderr}"
_MSG_TIMEOUT: Final[str] = "git {subcommand} exceeded its {timeout_s}s timeout"
_MSG_UNKNOWN: Final[str] = "git subcommand {subcommand!r} is not in the closed set"
_MSG_OUTSIDE: Final[str] = (
    "refusing to run git in {cwd}: outside both the repo and the wrapper dir"
)
HOOKS_DIR: Final[str] = "empty-hooks"
CORE_HOOKS_PATH: Final[str] = "core.hooksPath={path}"
GIT_INDEX_FILE: Final[str] = "GIT_INDEX_FILE"
"""Points snapshot plumbing at a THROWAWAY index, so the snapshot never stages
anything in the index a human is using."""
MAX_ARGV_BYTES: Final[int] = 128 * 1024


def chunk_argv(
    arguments: Sequence[str],
    *,
    fixed: Sequence[str] = (),
    repeated: Sequence[str] = (),
) -> tuple[tuple[str, ...], ...]:
    """Split arguments under the snapshot argv budget without dropping one."""
    fixed_bytes = sum(len(os.fsencode(argument)) + 1 for argument in fixed)
    repeated_bytes = sum(len(os.fsencode(argument)) + 1 for argument in repeated)
    chunks: list[tuple[str, ...]] = []
    current: list[str] = []
    current_bytes = fixed_bytes
    for argument in arguments:
        argument_bytes = len(os.fsencode(argument)) + 1 + repeated_bytes
        if current and current_bytes + argument_bytes > MAX_ARGV_BYTES:
            chunks.append(tuple(current))
            current = []
            current_bytes = fixed_bytes
        current.append(argument)
        current_bytes += argument_bytes
    if current:
        chunks.append(tuple(current))
    return tuple(chunks)


HARDENING: Final[tuple[str, ...]] = (
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.pager=cat",
)
"""Three program-naming config keys, pinned rather than inherited.

`core.hooksPath` is the third and is added per call, because its value is a path
the wrapper has to make exist first.

Three keys, not "the keys that name a program": `filter.<name>.clean` is the
counterexample that no FIXED `-c` neutralises — the driver NAME comes from the
repository's own `.gitattributes`. It is pinned per call instead, by the
overlay `gitio.Git._filter_overrides` computes (cr-o85.29). See the `gitio`
module docstring for what actually keeps `.git/config` out of a runner's hands,
and for the residual that is left."""
ENV_HARDENING: Final[Mapping[str, str]] = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
}
"""The ambient config files, dropped: `/etc/gitconfig` and `~/.gitconfig`.

Both are outside the wrapper's control and both can name programs. The global
one is also why two hosts disagreed about what a supervisor git call does —
whatever the operator happens to have in `~/.gitconfig` was in effect. Every
identity the wrapper needs is supplied explicitly (`SNAPSHOT_IDENTITY`), so
there is nothing left for it to contribute.

Applied LAST, so no caller overlay can drop either."""
SNAPSHOT_IDENTITY: Final[Mapping[str, str]] = {
    "GIT_AUTHOR_NAME": "wf-supervisor",
    "GIT_AUTHOR_EMAIL": "supervisor@workflow-interpreter.invalid",
    "GIT_COMMITTER_NAME": "wf-supervisor",
    "GIT_COMMITTER_EMAIL": "supervisor@workflow-interpreter.invalid",
}
"""The snapshot commit's identity, supplied rather than discovered: a repo with
no `user.email` configured would otherwise fail `commit-tree`, and the one
commit the wrapper authors must never be attributed to the human."""


class GitSubcommand(StrEnum):
    """The git subcommands the supervisor may run. Adding one is a design change.

    Note what is absent: `push`, `remote`, `fetch`, `commit`, `merge`, `rebase`.
    The supervisor observes and resets a working tree; the RUNNER commits, and
    nothing here ever publishes anything (§0.1's spirit, applied to git).

    `read-tree`, `hash-object`, `update-index`, `write-tree` and `commit-tree`
    are snapshot plumbing. `update-index` is deliberately included: staging
    runner-owned content through a throwaway index is the only way to keep
    `.gitattributes` filters out of the outputs pinning path. They are
    porcelain-free object-store operations: with
    `GIT_INDEX_FILE` pointed at a throwaway index none of them touches the
    repository's index or working tree, and `commit-tree` writes a commit OBJECT
    without moving any ref — which is why it is here while `commit` still is not.

    `config` is READ-ONLY here by construction: the only call site asks it to
    LIST names (`gitio.Git._filter_overrides`, cr-o85.29), and listing config
    is the one way to learn the filter-driver names a repository defines
    without letting `status` execute them. It never writes a key — no member of
    this set may be used to mutate configuration.

    `symbolic-ref` is READ-ONLY here by construction: the only call site asks
    `--quiet HEAD` whether the coordinator checkout is attached
    (`gitio.Git.attached_branch_ref`). Its wrapper accepts no ref name or value,
    so it cannot use `git symbolic-ref HEAD refs/heads/x` to rewrite HEAD.
    Adding a wrapper that accepts either argument would make this member unsafe.
    """

    REV_PARSE = "rev-parse"
    STATUS = "status"
    DIFF = "diff"
    WORKTREE = "worktree"
    UPDATE_REF = "update-ref"
    SHOW_REF = "show-ref"
    STASH = "stash"
    CLEAN = "clean"
    RESET = "reset"
    HASH_OBJECT = "hash-object"
    CAT_FILE = "cat-file"
    MERGE_BASE = "merge-base"
    READ_TREE = "read-tree"
    LS_FILES = "ls-files"
    LS_TREE = "ls-tree"
    UPDATE_INDEX = "update-index"
    WRITE_TREE = "write-tree"
    COMMIT_TREE = "commit-tree"
    CONFIG = "config"
    SYMBOLIC_REF = "symbolic-ref"


class GitResult:
    """One completed git invocation."""

    def __init__(self, returncode: int, stdout: str, stderr: str) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    @property
    def text(self) -> str:
        """Stdout with trailing whitespace stripped."""
        return self.stdout.strip()


class GitTransport:
    """Run closed-set Git commands under the wrapper's process controls."""

    def __init__(self, config: SupervisorConfig) -> None:
        self._config = config
        self._hooks_dir: Path | None = None

    def _hardening(self) -> list[str]:
        """Return the forced Git configuration for each invocation."""
        if self._hooks_dir is None:
            hooks = self._config.wrapper_root / HOOKS_DIR
            hooks.mkdir(parents=True, exist_ok=True)
            self._hooks_dir = hooks
        return [*HARDENING, "-c", CORE_HOOKS_PATH.format(path=self._hooks_dir)]

    def _assert_inside(self, cwd: Path) -> None:
        """Refuse a working directory outside the configured roots."""
        if not (
            cwd.is_relative_to(self._config.repo_root)
            or cwd.is_relative_to(self._config.wrapper_root)
        ):
            raise GitCommandError(_MSG_OUTSIDE.format(cwd=cwd))

    def run(
        self,
        subcommand: GitSubcommand,
        *args: str,
        cwd: Path,
        check: bool = True,
        env: Mapping[str, str] | None = None,
        config: Sequence[str] = (),
    ) -> GitResult:
        """Run one bounded Git command without a shell.

        `config` holds extra `-c key=value` pairs for pins a CALLER has to
        compute, where `HARDENING`'s fixed set cannot: the filter-driver
        blanking in `gitio` is the one such caller (cr-o85.29). They are placed
        BEFORE the hardening pins, and a later `-c` wins, so a caller overlay
        can never displace one of the three hardened keys.
        """
        if subcommand not in set(GitSubcommand):  # pragma: no cover
            raise GitCommandError(_MSG_UNKNOWN.format(subcommand=subcommand))
        self._assert_inside(cwd)
        argv = [
            self._config.git_binary,
            *config,
            *self._hardening(),
            subcommand.value,
            *args,
        ]
        try:
            completed = subprocess.run(
                argv,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self._config.git_timeout_s,
                check=False,
                env={**os.environ, **(env or {}), **ENV_HARDENING},
            )
        except subprocess.TimeoutExpired as exc:
            raise GitCommandError(
                _MSG_TIMEOUT.format(
                    subcommand=subcommand.value, timeout_s=self._config.git_timeout_s
                )
            ) from exc
        result = GitResult(completed.returncode, completed.stdout, completed.stderr)
        if check and result.returncode != 0:
            raise GitCommandError(
                _MSG_FAILED.format(
                    subcommand=subcommand.value,
                    returncode=result.returncode,
                    stderr=result.stderr.strip(),
                )
            )
        _LOG.debug("git", subcommand=subcommand.value, cwd=str(cwd))
        return result


__all__ = [
    "GIT_INDEX_FILE",
    "MAX_ARGV_BYTES",
    "SNAPSHOT_IDENTITY",
    "GitResult",
    "GitSubcommand",
    "GitTransport",
    "chunk_argv",
]
