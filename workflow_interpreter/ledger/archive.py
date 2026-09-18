"""Retire a closed task's bytes, but never before they are recoverable (§3.9).

`wf archive <task>` is MANUAL and deliberately so (D14): nothing in the engine
deletes a run folder on a schedule. It is also strictly ordered, and the order
is the whole design (D19):

1. refuse unless the task's record is durable — exported, with every root
   settled — because an unfinished run has nothing to archive;
2. write a git bundle of every `refs/wf/<root>/*` the task pinned, to a path
   the operator chose OUTSIDE the repository;
3. verify that bundle with git itself;
4. and only then delete the run folders and the refs.

The export is JSON and JSON does not preserve git objects, so the bundle is
the only thing standing between a retention pass and a rejected artifact
nobody can look at again.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.ledger.errors import LedgerExportError
from workflow_interpreter.ledger.tasks import export_oid, task_roots

ROOT_REF_PREFIX: Final[str] = "refs/wf/{root_id}/"

MSG_UNKNOWN_TASK: Final[str] = "the ledger holds no task {task_id!r}"
MSG_NOT_EXPORTED: Final[str] = (
    "task {task_id!r} has no export_oid: it is not closed, and an unexported "
    "task may not be archived (§3.6)"
)
MSG_LIVE_ROOT: Final[str] = (
    "root {root_id!r} of task {task_id!r} has not settled; archive is for "
    "finished runs only"
)
MSG_BUNDLE_INSIDE: Final[str] = (
    "the bundle path {path} is inside the repository; archive writes outside it"
)
MSG_BUNDLE_EXISTS: Final[str] = "the bundle path {path} already exists"
MSG_NO_REFS: Final[str] = "task {task_id!r} pinned no refs/wf/<root>/ to archive"
MSG_UNVERIFIED: Final[str] = "git refused the bundle at {path}; nothing was deleted"


class ArchiveResult(BaseModel):
    """What one archive removed, and what it is recoverable from."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_id: str
    bundle: Path
    refs: tuple[str, ...]
    run_folders: tuple[Path, ...]


def archive_task(
    git: Git,
    database: LedgerDatabase,
    task_id: str,
    *,
    bundle: Path,
    repo_root: Path,
    wrapper_root: Path,
) -> ArchiveResult:
    """Bundle, verify, then delete one closed task's run folders and refs."""
    roots = task_roots(database, task_id)
    if not roots:
        raise LedgerExportError(MSG_UNKNOWN_TASK.format(task_id=task_id))
    if export_oid(database, task_id) is None:
        raise LedgerExportError(MSG_NOT_EXPORTED.format(task_id=task_id))
    for root_id, terminal in roots:
        if not terminal:
            raise LedgerExportError(
                MSG_LIVE_ROOT.format(root_id=root_id, task_id=task_id)
            )
    if bundle.resolve().is_relative_to(repo_root.resolve()):
        raise LedgerExportError(MSG_BUNDLE_INSIDE.format(path=bundle))
    if bundle.exists():
        raise LedgerExportError(MSG_BUNDLE_EXISTS.format(path=bundle))
    refs = tuple(
        ref
        for root_id, _ in roots
        for ref in git.ref_names_under(
            ROOT_REF_PREFIX.format(root_id=root_id), cwd=repo_root
        )
    )
    if not refs:
        raise LedgerExportError(MSG_NO_REFS.format(task_id=task_id))
    bundle.parent.mkdir(parents=True, exist_ok=True)
    git.bundle_create(bundle, refs, cwd=repo_root)
    if not git.bundle_verify(bundle, cwd=repo_root):
        # The bundle is the only copy of these objects that survives the
        # deletion below, so a bundle git will not accept means the deletion
        # does not happen — not that it happens and the bundle is suspect.
        raise LedgerExportError(MSG_UNVERIFIED.format(path=bundle))
    folders: list[Path] = []
    for root_id, _ in roots:
        folder = wrapper_root / root_id
        if folder.is_dir() and not folder.is_symlink():
            shutil.rmtree(folder)
            folders.append(folder)
    for ref in refs:
        git.delete_ref(ref, cwd=repo_root)
    return ArchiveResult(
        task_id=task_id, bundle=bundle, refs=refs, run_folders=tuple(folders)
    )
