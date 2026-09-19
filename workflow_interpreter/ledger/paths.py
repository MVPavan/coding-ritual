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
from uuid import uuid4

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
    MSG_REPO_ID_ABSENT,
    REPO_ID_FILE,
)
from workflow_interpreter.ledger.errors import LedgerIdentityError

REPO_HASH_LENGTH: Final[int] = 16
"""The same prefix `ForemanConfig.wrapper_root` names a repository by."""

_EXCLUSIVE_CREATE: Final[str] = "x"
"""Open a file only when creating it, so two first starts cannot both mint."""


def repo_hash(repo_root: Path) -> str:
    """The repository's stable identity, as the wrapper root already spells it.

    The WRAPPER HOME's name only: it answers "which engine home is this
    checkout's", which is a question about this machine's paths. What an
    export is pinned to is `repo_id`, which a move or a clone does not change.
    """
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


def repo_id_path(repo_root: Path) -> Path:
    """`<repo>/.wf/repo-id` — TRACKED, and committed beside the exports."""
    return repo_root / LEDGER_DIR / REPO_ID_FILE


def read_repo_id(repo_root: Path) -> str | None:
    """This checkout's repository id, or nothing when none was ever minted."""
    path = repo_id_path(repo_root)
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip() or None


def ensure_repo_id(repo_root: Path) -> str:
    """Mint `<repo>/.wf/repo-id` once, and answer the id in force (§3.6).

    Exclusive create rather than "check, then write": two first starts race
    here, and a repository that minted two identities would refuse its own
    exports. The loser of the race reads the winner's file, which is why the
    answer comes from a re-read rather than from the value this call generated.

    Nothing here commits the file. It is tracked, not ignored
    (`ensure_ledger_ignored`), and the orchestrator commits it exactly as it
    commits an export.
    """
    existing = read_repo_id(repo_root)
    if existing is not None:
        return existing
    path = repo_id_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open(_EXCLUSIVE_CREATE, encoding="utf-8") as handle:
            handle.write(f"{uuid4()}\n")
    except FileExistsError:
        pass
    minted = read_repo_id(repo_root)
    if minted is None:  # pragma: no cover - the file is written just above
        raise LedgerIdentityError(
            MSG_REPO_ID_ABSENT.format(repo_root=repo_root, relpath=repo_id_relpath())
        )
    return minted


def repo_id_relpath() -> str:
    """`.wf/repo-id` as git spells it, from the repository root."""
    return str(PurePosixPath(LEDGER_DIR) / REPO_ID_FILE)


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
    """The dirty paths a COORDINATOR owns, minus the two the ENGINE writes.

    Two named paths, never the directory: this task's export, and the
    repository id. Both are tracked files in `<repo>/.wf/` that the engine
    writes and the orchestrator commits (§3.6, "the export file appears in the
    main checkout, exactly as `.beads/issues.jsonl` does after a bd write"), so
    a cleanliness check that counted either would block the next stage's
    admission on the engine's own durable write — the repo id on the very
    first open in a fresh checkout, before anything else has happened.

    Looking past the whole directory instead would hide every other staged,
    modified or untracked file under it — including another task's export and
    the ledger database when it is not ignored — from checks whose whole
    purpose is to preserve a coordinator's work before a checkout is
    synchronised.
    """
    allowed = {export_relpath(task_id), repo_id_relpath()}
    return tuple(entry for entry in entries if entry[0] not in allowed)
