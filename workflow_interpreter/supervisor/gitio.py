"""The git transport — the only place the supervisor spawns `git` (§5.4, §7.4).

Same three properties as `bdio.client`, for the same reasons:

1. **argv lists, never shell strings**, so no path or ref can become syntax.
2. **A closed subcommand set.** `push`, `remote` and `fetch` are not members,
   so "the supervisor never pushes" is structural rather than a convention
   somebody has to keep. Every subcommand here is local and confined to a
   working tree the wrapper owns.
3. **Explicit timeouts** on every invocation (`rules/python/safety.md`).

Working directories are checked, not trusted: every call must run inside the
repo the config names or inside the wrapper directory's worktree, so a caller
cannot aim a `clean -f` at an unrelated checkout.
"""

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
from workflow_interpreter.supervisor.models import EntryKind

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

NUL: Final[str] = "\0"
HEAD: Final[str] = "HEAD"
TREE_SUFFIX: Final[str] = "^{tree}"
COMMIT_SUFFIX: Final[str] = "^{commit}"
PATH_SEPARATOR: Final[str] = "--"
RENAME_CODES: Final[frozenset[str]] = frozenset({"R", "C"})
UNTRACKED_CODE: Final[str] = "?"
DELETED_CODE: Final[str] = "D"
STATUS_CODE_WIDTH: Final[int] = 2
_STATUS_PATH_OFFSET: Final[int] = 3
"""`XY <path>` — two status codes and the space that follows them."""

COMMITTER_PREFIX: Final[str] = "committer "
EMAIL_OPEN: Final[str] = "<"
EMAIL_CLOSE: Final[str] = ">"
"""`git cat-file commit` header shape: `committer NAME <EMAIL> TS TZ`. Git
forbids `<` and `>` in a name, so the LAST pair delimits the address."""

NO_BLOB: Final[str] = ""
"""The digest of a dirty path that HAS no blob: one that was deleted, and one
that is not a regular file. `git status -uall` reports a nested checkout as
`?? dir/` and a dirty submodule as ` M dir`, and `git hash-object -- <dir>` is a
fatal error, not an empty answer — which used to escape `prepare()` and wedge
every subsequent dispatch (probed). Callers tell those cases apart by the
entry's KIND, never by this value (`supervisor/models.py`)."""

_MSG_FAILED: Final[str] = "git {subcommand} failed (exit {returncode}): {stderr}"
_MSG_TIMEOUT: Final[str] = "git {subcommand} exceeded its {timeout_s}s timeout"
_MSG_UNKNOWN: Final[str] = "git subcommand {subcommand!r} is not in the closed set"
_MSG_OUTSIDE: Final[str] = (
    "refusing to run git in {cwd}: outside both the repo and the wrapper dir"
)

GIT_INDEX_FILE: Final[str] = "GIT_INDEX_FILE"
"""Points `read-tree` / `add` / `write-tree` at a THROWAWAY index, so the
snapshot never stages anything in the index a human is using."""

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

    `read-tree`, `add`, `write-tree` and `commit-tree` are the pre-destruction
    snapshot's plumbing (`snapshot_commit`) and exist for nothing else. They are
    porcelain-free object-store operations: with `GIT_INDEX_FILE` pointed at a
    throwaway index none of them touches the repository's index or working tree,
    and `commit-tree` writes a commit OBJECT without moving any ref — which is
    why it is here while `commit` still is not.
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
    ADD = "add"
    WRITE_TREE = "write-tree"
    COMMIT_TREE = "commit-tree"


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


class Git:
    """A workspace-confined git transport."""

    def __init__(self, config: SupervisorConfig) -> None:
        self._config = config

    def _assert_inside(self, cwd: Path) -> None:
        """Refuse a working directory the wrapper does not own."""
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
    ) -> GitResult:
        """Run one git subcommand, no shell, explicit timeout, confined cwd.

        `env` overlays the inherited environment rather than replacing it: git
        needs `PATH` to find its own subprograms, and the only overlays this
        transport ever passes are `snapshot_commit`'s throwaway index and
        author identity. No supervisor DECISION reads the environment
        (`rules/python/safety.md`); this is subprocess plumbing.
        """
        if subcommand not in set(GitSubcommand):  # pragma: no cover - enum guard
            raise GitCommandError(_MSG_UNKNOWN.format(subcommand=subcommand))
        self._assert_inside(cwd)
        argv = [self._config.git_binary, subcommand.value, *args]
        try:
            completed = subprocess.run(
                argv,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self._config.git_timeout_s,
                check=False,
                env=None if env is None else {**os.environ, **env},
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

    # -- reads -----------------------------------------------------------

    def rev_parse(self, revision: str, *, cwd: Path) -> str:
        """Resolve a revision to its object id."""
        return self.run(GitSubcommand.REV_PARSE, revision, cwd=cwd).text

    def head_commit(self, *, cwd: Path) -> str:
        """The working tree's current commit OID (§5.4's assertion subject)."""
        return self.rev_parse(HEAD, cwd=cwd)

    def tree_oid(self, commit: str, *, cwd: Path) -> str:
        """The tree OID of a commit — §10.5's no-progress identity."""
        return self.rev_parse(f"{commit}{TREE_SUFFIX}", cwd=cwd)

    def commit_exists(self, commit: str, *, cwd: Path) -> bool:
        """Whether a commit object is present (§7.4's reconciliation halt)."""
        return (
            self.run(
                GitSubcommand.CAT_FILE,
                "-e",
                f"{commit}{COMMIT_SUFFIX}",
                cwd=cwd,
                check=False,
            ).returncode
            == 0
        )

    def is_ancestor(self, ancestor: str, descendant: str, *, cwd: Path) -> bool:
        """Whether `ancestor` is reachable from `descendant`."""
        return (
            self.run(
                GitSubcommand.MERGE_BASE,
                "--is-ancestor",
                ancestor,
                descendant,
                cwd=cwd,
                check=False,
            ).returncode
            == 0
        )

    def status_paths(self, *, cwd: Path) -> tuple[tuple[str, bool], ...]:
        """Every dirty path as `(path, tracked)` — `-z`, so no path is quoted.

        Renames report two paths in one record; both are returned, because a
        rename dirties the source as much as the destination.
        """
        raw = self.run(
            GitSubcommand.STATUS,
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            cwd=cwd,
        ).stdout
        records = [record for record in raw.split(NUL) if record]
        found: list[tuple[str, bool]] = []
        index = 0
        while index < len(records):
            record = records[index]
            index += 1
            if len(record) < _STATUS_PATH_OFFSET:
                continue
            codes = record[:STATUS_CODE_WIDTH]
            tracked = UNTRACKED_CODE not in codes
            found.append((record[_STATUS_PATH_OFFSET:], tracked))
            if any(code in RENAME_CODES for code in codes) and index < len(records):
                found.append((records[index], tracked))
                index += 1
        return tuple(found)

    def committer_email(self, commit: str, *, cwd: Path) -> str | None:
        """The COMMITTER address of a commit object, or `None` if unreadable.

        `cat-file commit` prints the raw object, whose header is `committer NAME
        <EMAIL> TIMESTAMP TZ`. Read through the closed subcommand set rather
        than through `log --format`, which would put a porcelain formatter on
        the allow-list for one field. The scan stops at the blank line that ends
        the header, so a commit MESSAGE containing a `committer ` line cannot
        answer for the object.
        """
        result = self.run(
            GitSubcommand.CAT_FILE, "commit", commit, cwd=cwd, check=False
        )
        if result.returncode != 0:
            return None
        for line in result.stdout.splitlines():
            if not line:
                break
            if not line.startswith(COMMITTER_PREFIX):
                continue
            identity = line[len(COMMITTER_PREFIX) :]
            start = identity.rfind(EMAIL_OPEN)
            end = identity.rfind(EMAIL_CLOSE)
            return identity[start + 1 : end] if 0 <= start < end else None
        return None

    def diff_names(self, base: str, head: str, *, cwd: Path) -> tuple[str, ...]:
        """Paths changed between two commits (§7.5 observed effects)."""
        raw = self.run(
            GitSubcommand.DIFF, "--name-only", "-z", base, head, cwd=cwd
        ).stdout
        return tuple(path for path in raw.split(NUL) if path)

    def hash_working_file(self, path: str, *, cwd: Path) -> str:
        """The blob OID of a working-tree file, or `NO_BLOB` where there is none.

        ONLY a regular file is handed to `git hash-object`. A DIRECTORY was the
        shape that forced this: the human's own checkout legitimately contains
        nested repositories, vendored clones and dirty submodules, `git status
        -uall` reports each as one directory entry, and hashing one exits 128 —
        a fatal that killed the §5.4 precondition for the whole instance,
        deterministically, on every tick (probed — this repository's own
        `reference_harnesses/` shape triggers it).

        Every other non-regular target is refused the same way, and the worse
        one is not the fatal: `git hash-object` on a FIFO or a character device
        BLOCKS, so it does not fail until `git_timeout_s` and then wedges
        `prepare` on every subsequent tick (probed, r4).

        The test FOLLOWS symlinks, because `git hash-object` does: a symlink to
        a directory is the same `fatal: Unable to hash`, one to a FIFO is the
        same block, and one to a file hashes that file's content and is an
        ordinary entry. `is_file()` answers all of it, a broken symlink and a
        deleted path included.
        """
        if not (cwd / path).is_file():
            return NO_BLOB
        return self.run(GitSubcommand.HASH_OBJECT, PATH_SEPARATOR, path, cwd=cwd).text

    @staticmethod
    def entry_kind(path: str, *, cwd: Path) -> EntryKind:
        """What a dirty path RESOLVES to, for the caller that RECORDS it (§12).

        Beside `hash_working_file` because it is the same question, asked by the
        caller that has to record the answer rather than just avoid the fatal.
        Two renderings of "is this hashable" would drift.

        An ABSENT path is `FILE`: a deletion is the one no-blob entry whose
        content the object store still has, so it is not protected as opaque
        content is (`EntryKind`).
        """
        target = cwd / path
        if target.is_dir():
            return EntryKind.DIRECTORY
        if target.exists() and not target.is_file():
            return EntryKind.NON_REGULAR
        return EntryKind.FILE

    # -- writes (all confined to a working tree the wrapper owns) ---------

    def stash_create(self, *, cwd: Path) -> str | None:
        """`git stash create` — a snapshot commit, or `None` on a clean tree.

        Creates a dangling commit and touches neither the index nor the working
        tree, which is what makes it safe to run against a human's checkout
        (§12).
        """
        return self.run(GitSubcommand.STASH, "create", cwd=cwd).text or None

    def snapshot_commit(
        self, *, message: str, parents: Sequence[str], index_path: Path, cwd: Path
    ) -> str:
        """Commit the FULL working tree — untracked included — touching nothing.

        The pre-destruction snapshot of §12: every reset must be recoverable
        even where attribution erred, and `stash create` cannot provide that —
        it has no `--include-untracked`, and never-committed content is exactly
        what a reset destroys unrecoverably.

        Plumbing over a THROWAWAY index (`GIT_INDEX_FILE`), so the human's own
        index and working tree are never modified: `read-tree` seeds it from
        HEAD, `add --all` folds in every modification, deletion and untracked
        file, `write-tree` turns it into a tree object, and `commit-tree` names
        that tree under the given parents. Nothing here moves a ref — the
        caller pins the returned commit, and pins it before it resets anything.

        Ignored files are deliberately absent: `status --untracked-files=all`
        does not report them and `clean -f -d` (no `-x`) does not remove them,
        so the snapshot covers exactly the set a reset puts at risk.
        """
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.unlink(missing_ok=True)
        env = {GIT_INDEX_FILE: str(index_path), **SNAPSHOT_IDENTITY}
        self.run(GitSubcommand.READ_TREE, HEAD, cwd=cwd, env=env)
        self.run(GitSubcommand.ADD, "--all", cwd=cwd, env=env)
        tree = self.run(GitSubcommand.WRITE_TREE, cwd=cwd, env=env).text
        args: list[str] = [tree]
        for parent in parents:
            args += ["-p", parent]
        return self.run(
            GitSubcommand.COMMIT_TREE, *args, "-m", message, cwd=cwd, env=env
        ).text

    def worktree_add(self, path: Path, branch: str, commit: str, *, cwd: Path) -> None:
        """Create the §5.4 per-instance worktree at `commit` on `branch`."""
        self.run(
            GitSubcommand.WORKTREE,
            "add",
            "--force",
            "-B",
            branch,
            str(path),
            commit,
            cwd=cwd,
        )

    def worktree_add_detached(self, path: Path, commit: str, *, cwd: Path) -> None:
        """Check `commit` out at `path` on no branch — §7.3's isolated tree.

        Detached and branchless on purpose: this checkout exists to be graded
        and thrown away, and a branch would tie it to the instance's own
        history where a later reset could move it.
        """
        self.run(GitSubcommand.WORKTREE, "add", "--detach", str(path), commit, cwd=cwd)

    def worktree_remove(self, path: Path, *, cwd: Path, check: bool = True) -> None:
        """Remove the worktree at terminal (§5.4).

        `check = False` for the throwaway §7.3 checkout: "there was nothing to
        remove" and "the registration was already stale" are both fine answers
        when the goal is only that nothing is left behind.
        """
        self.run(
            GitSubcommand.WORKTREE, "remove", "--force", str(path), cwd=cwd, check=check
        )

    def worktree_prune(self, *, cwd: Path) -> None:
        """Drop registrations whose directories are gone (§7.3's throwaway tree)."""
        self.run(GitSubcommand.WORKTREE, "prune", cwd=cwd)

    def update_ref(self, ref: str, commit: str, *, cwd: Path) -> None:
        """Pin `refs/wf/<root_id>/<activation_id>` — idempotent for one value."""
        self.run(GitSubcommand.UPDATE_REF, ref, commit, cwd=cwd)

    def ref_target(self, ref: str, *, cwd: Path) -> str | None:
        """The commit a workflow ref points at, or `None` when unpinned."""
        result = self.run(GitSubcommand.SHOW_REF, "--verify", ref, cwd=cwd, check=False)
        if result.returncode != 0:
            return None
        return result.text.split()[0]

    def refs_under(self, prefix: str, *, cwd: Path) -> tuple[str, ...]:
        """Every commit a ref under `prefix` points at — the wrapper's pins.

        `check=False` because `show-ref` exits 1 on a repo with no refs at all,
        which is an empty answer rather than a failure. This is the §12 "did
        the WRAPPER put this commit here" question, so the answer is a set of
        commits and never a promise about the working tree.
        """
        result = self.run(GitSubcommand.SHOW_REF, cwd=cwd, check=False)
        found: list[str] = []
        for line in result.stdout.splitlines():
            oid, _, ref = line.partition(" ")
            if ref.startswith(prefix):
                found.append(oid)
        return tuple(found)

    def reset_hard(self, commit: str, *, cwd: Path) -> None:
        """Move HEAD and the tracked tree to `commit`."""
        self.run(GitSubcommand.RESET, "--hard", commit, cwd=cwd)

    def clean_paths(self, paths: Sequence[str], *, cwd: Path) -> None:
        """Remove exactly the named untracked paths — never a blanket `-fdx`.

        The whole §12 guarantee is that a reset touches the runner's files and
        nothing else, and a blanket clean is precisely the operation that
        cannot make that promise.
        """
        if paths:
            self.run(GitSubcommand.CLEAN, "-f", "-d", PATH_SEPARATOR, *paths, cwd=cwd)
