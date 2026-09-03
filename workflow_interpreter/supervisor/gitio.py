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

4. **Three named config keys are pinned, and the ambient files are dropped**
   (`HARDENING`, `ENV_HARDENING`). Every key git reads can come from
   `.git/config`, and several of them name a PROGRAM the supervisor's own git
   would then run as the wrapper — outside the sandbox that bounded the runner.
   `core.hooksPath` is redirected at an empty directory the wrapper owns (the
   live one: `git worktree add` runs `post-checkout`, and that is a call §5.4
   makes on a tree the runner just had), `core.pager` and `core.fsmonitor` are
   pinned beside it, `GIT_CONFIG_NOSYSTEM` drops `/etc/gitconfig` and
   `GIT_CONFIG_GLOBAL` drops `~/.gitconfig`.

   **What that is NOT is "the repository's configuration is not trusted".** It
   said so, and the claim was false: `filter.<name>.clean` alone survives it,
   ran on the former `git add --all` snapshot implementation — and cannot be
   pinned generically, because the
   driver name is chosen by the repository's own `.gitattributes` (Opus r2 #20,
   probed against this class). `diff.external`, `core.sshCommand`,
   `credential.helper`, `init.templateDir`, `core.alternateRefsCommand` and
   `uploadpack.packObjectsHook` are the same shape. The honest statement is that
   `.git/config` is kept OUT OF THE RUNNER'S REACH rather than distrusted here,
   and the pins above are belt-and-braces for the keys that can be named:

   - **codex** — the sandbox makes `<root>/.git` read-only inside every writable
     root, whether it is a directory or a worktree's `gitdir:` file, in both
     `writes` modes (probes P2.2/P2.3, and the executable ruling in
     `tests/test_profiles_git_isolation.py`). OS-enforced, not requested.
   - **claude** — `Edit(//<cwd>/.git)` and `Edit(//<cwd>/.git/**)` deny both
     shapes, and `Bash` on a `writes = true` node is the §0.3 cooperative
     residual: claude has no sandbox, so a shell it grants can write `.git/config`
     whatever the permission engine says (`ClaudeProfile.sandboxed = False`).

   The residual that remains for BOTH vendors is a nested repository inside a
   granted tree — a submodule checkout's own `.git` is not the root's, so
   codex's sandbox does not protect it (P2.3). Nothing follows from it wrapper-side:
   `GitSubcommand` is a closed set and none of its members recurses into a
   submodule, so no wrapper git ever reads that config.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Final

from workflow_interpreter.supervisor.errors import GitCommandError
from workflow_interpreter.supervisor.gitcmd import (
    MAX_ARGV_BYTES,
    SNAPSHOT_IDENTITY,
    GitResult,
    GitSubcommand,
    GitTransport,
)
from workflow_interpreter.supervisor.gitsnapshot import (
    commit_directory,
    snapshot_commit,
)
from workflow_interpreter.supervisor.models import EntryKind

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


class Git(GitTransport):
    """Supervisor Git reads and mutations above the shared command transport."""

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
        if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
            raise GitCommandError(f"commit must be a full lowercase SHA-1: {commit!r}")
        exists = self.run(GitSubcommand.CAT_FILE, "-e", commit, cwd=cwd, check=False)
        if exists.returncode == 1:
            return False
        if exists.returncode != 0:
            raise GitCommandError(f"git cat-file failed (exit {exists.returncode})")
        kind = self.run(GitSubcommand.CAT_FILE, "-t", commit, cwd=cwd, check=False)
        if kind.returncode != 0:
            raise GitCommandError(f"git cat-file failed (exit {kind.returncode})")
        return kind.text == "commit"

    def is_ancestor(self, ancestor: str, descendant: str, *, cwd: Path) -> bool:
        """Whether `ancestor` is reachable from `descendant`."""
        result = self.run(
            GitSubcommand.MERGE_BASE,
            "--is-ancestor",
            ancestor,
            descendant,
            cwd=cwd,
            check=False,
        )
        if result.returncode == 0:
            return True
        if result.returncode == 1:
            return False
        raise GitCommandError(f"git merge-base failed (exit {result.returncode})")

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
            raise GitCommandError(f"git cat-file failed (exit {result.returncode})")
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

    def tree_entries(self, tree: str, *, cwd: Path) -> tuple[str, ...]:
        """Return the NUL-delimited paths in one pinned tree."""
        raw = self.run(
            GitSubcommand.LS_TREE, "-r", "-z", "--name-only", tree, cwd=cwd
        ).stdout
        return tuple(path for path in raw.split(NUL) if path)

    def blob_text(self, oid: str, *, cwd: Path) -> str:
        """Read one pinned blob as text."""
        return self.run(GitSubcommand.CAT_FILE, "blob", oid, cwd=cwd).stdout

    def diff_text(self, base: str, head: str, *, cwd: Path) -> str:
        """Read the text diff between two pinned commits."""
        return self.run(GitSubcommand.DIFF, base, head, cwd=cwd).stdout

    def diff_stat(self, base: str, head: str, *, cwd: Path) -> str:
        """The `--stat` summary between two commits — §9's cumulative gate view.

        `DIFF` is already a member of the closed subcommand set, so this adds a
        rendering and not a capability.
        """
        return self.run(GitSubcommand.DIFF, "--stat", base, head, cwd=cwd).stdout

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
        HEAD; `hash-object --no-filters` and `update-index` fold in every
        modification, deletion and untracked file; `write-tree` turns it into
        a tree object; and `commit-tree` names that tree under the given
        parents. Nothing here moves a ref — the caller pins the returned
        commit, and pins it before it resets anything.

        Ignored files are deliberately absent: `status --untracked-files=all`
        does not report them and `clean -f -d` (no `-x`) does not remove them,
        so the snapshot covers exactly the set a reset puts at risk.
        """
        return snapshot_commit(
            self,
            message=message,
            parents=parents,
            index_path=index_path,
            cwd=cwd,
        )

    def commit_directory(
        self,
        paths: tuple[str, ...],
        *,
        root: Path,
        message: str,
        index_path: Path,
        cwd: Path,
    ) -> str:
        """Commit wrapper-owned output bytes without consulting attributes."""
        return commit_directory(
            self,
            paths,
            root=root,
            message=message,
            index_path=index_path,
            cwd=cwd,
        )

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
        self.run(GitSubcommand.WORKTREE, "remove", str(path), cwd=cwd, check=check)

    def worktree_prune(self, *, cwd: Path) -> None:
        """Drop registrations whose directories are gone (§7.3's throwaway tree)."""
        self.run(GitSubcommand.WORKTREE, "prune", cwd=cwd)

    def update_ref(self, ref: str, commit: str, *, cwd: Path) -> None:
        """Pin `refs/wf/<root_id>/<activation_id>` — idempotent for one value."""
        self.run(GitSubcommand.UPDATE_REF, ref, commit, cwd=cwd)

    def ref_target(self, ref: str, *, cwd: Path) -> str | None:
        """The commit a workflow ref points at, or `None` when unpinned."""
        if not ref.startswith("refs/"):
            raise GitCommandError(f"ref must start with refs/: {ref!r}")
        result = self.run(
            GitSubcommand.REV_PARSE, "--verify", "-q", ref, cwd=cwd, check=False
        )
        if result.returncode == 1:
            return None
        if result.returncode != 0:
            raise GitCommandError(f"git rev-parse failed (exit {result.returncode})")
        return result.text

    def refs_under(self, prefix: str, *, cwd: Path) -> tuple[str, ...]:
        """Every commit a ref under `prefix` points at — the wrapper's pins.

        `check=False` because `show-ref` exits 1 on a repo with no refs at all,
        which is an empty answer rather than a failure. This is the §12 "did
        the WRAPPER put this commit here" question, so the answer is a set of
        commits and never a promise about the working tree.
        """
        result = self.run(GitSubcommand.SHOW_REF, cwd=cwd, check=False)
        if result.returncode == 1:
            return ()
        if result.returncode != 0:
            raise GitCommandError(f"git show-ref failed (exit {result.returncode})")
        found: list[str] = []
        for line in result.stdout.splitlines():
            oid, _, ref = line.partition(" ")
            if ref.startswith(prefix):
                found.append(oid)
        return tuple(found)

    def update_ref_cas(self, ref: str, new: str, old: str, *, cwd: Path) -> bool:
        """Advance `ref` only when it still names `old`."""
        return (
            self.run(
                GitSubcommand.UPDATE_REF, ref, new, old, cwd=cwd, check=False
            ).returncode
            == 0
        )

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


__all__ = [
    "MAX_ARGV_BYTES",
    "SNAPSHOT_IDENTITY",
    "Git",
    "GitResult",
    "GitSubcommand",
]
