"""Where the ledger, its exports and its fence live for one repository.

Three separate places on purpose (§3.4, D4): the database is in the working
tree's ignored `.wf/`, the export is a tracked file beside it, and the fence is
in the git common directory — shared by every worktree and every wrapper home
over one repository, and outside `git clean`'s reach.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Final

from workflow_interpreter.inspector.sandbox import fence_dir
from workflow_interpreter.ledger.constants import (
    EXPORT_DIR,
    EXPORT_SUFFIX,
    FENCE_FILE,
    IGNORE_BODY,
    IGNORE_FILE,
    LEDGER_DIR,
    LEDGER_FILE,
    MSG_NOT_A_REPOSITORY,
)
from workflow_interpreter.ledger.errors import LedgerIdentityError

REPO_HASH_LENGTH: Final[int] = 16
"""The same prefix `ForemanConfig.wrapper_root` names a repository by."""


def repo_hash(repo_root: Path) -> str:
    """The repository's stable identity, as the wrapper root already spells it."""
    return hashlib.sha256(str(repo_root.resolve()).encode("utf-8")).hexdigest()[
        :REPO_HASH_LENGTH
    ]


def ledger_path(repo_root: Path) -> Path:
    """`<repo>/.wf/ledger.db` — gitignored, and deletable by `git clean` (§3.5)."""
    return repo_root / LEDGER_DIR / LEDGER_FILE


def export_dir(repo_root: Path) -> Path:
    """`<repo>/.wf/export/` — tracked, one JSONL file per task (§3.6)."""
    return repo_root / LEDGER_DIR / EXPORT_DIR


def export_path(repo_root: Path, task_id: str) -> Path:
    """The export file of one task bead."""
    return export_dir(repo_root) / f"{task_id}{EXPORT_SUFFIX}"


def ensure_ledger_ignored(repo_root: Path) -> Path:
    """Write `<repo>/.wf/.gitignore` once, so the database is really ignored.

    §3.5 calls `.wf/` "the working tree's ignored" directory and D4 puts the
    database there; nothing made that true, so the first contractor command after
    the cutover refused its own ledger as coordinator dirt. The rule ignores
    everything under `.wf/` EXCEPT `export/`, which §3.6 says the orchestrator
    commits. Never rewritten: a repository that ignores this directory its own
    way keeps its rule.
    """
    path = repo_root / LEDGER_DIR / IGNORE_FILE
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(IGNORE_BODY, encoding="utf-8")
    return path


def fence_path(repo_root: Path) -> Path:
    """`<git common dir>/wf/ledger.lock`, refusing a tree that is not a repo.

    Refuses rather than falling back to a path inside the working tree: a fence
    two wrapper homes cannot both find is not a fence.
    """
    directory = fence_dir(repo_root)
    if directory is None:
        raise LedgerIdentityError(MSG_NOT_A_REPOSITORY.format(repo_root=repo_root))
    return directory / FENCE_FILE


def ensure_fence_dir(repo_root: Path) -> Path | None:
    """Create `<git common dir>/wf/` before any dispatch, or answer nothing.

    Nothing when the tree is not a git checkout: the crew sandbox pins this
    directory in the two shapes that HAVE a git entry (`sandbox._git_binds`),
    and a shape with no `.git` gets no git binds at all.
    """
    directory = fence_dir(repo_root)
    if directory is None:
        return None
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def export_relpath(task_id: str) -> str:
    """`.wf/export/<task>.jsonl` as git spells it, from the repository root."""
    return str(PurePosixPath(LEDGER_DIR) / EXPORT_DIR / f"{task_id}{EXPORT_SUFFIX}")


def coordinator_dirt(
    entries: Iterable[tuple[str, bool]], *, task_id: str
) -> tuple[tuple[str, bool], ...]:
    """The dirty paths a COORDINATOR owns, with THIS task's export removed.

    Exactly one path, never the directory: the export the contractor writes moments
    before it closes is tracked in `<repo>/.wf/` (§3.6, "the export file appears
    in the main checkout, exactly as `.beads/issues.jsonl` does after a bd
    write"), so a cleanliness check that counted it would block the next
    stage's admission on the very write that made this close durable.

    Looking past the whole directory instead would hide every other staged,
    modified or untracked file under it — including another task's export and
    the ledger database when it is not ignored — from checks whose whole
    purpose is to preserve a coordinator's work before a checkout is
    synchronised.
    """
    allowed = export_relpath(task_id)
    return tuple(entry for entry in entries if entry[0] != allowed)
