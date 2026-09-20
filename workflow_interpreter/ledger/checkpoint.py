"""The export a task takes at every activation close (§3.9, R10, S7).

The ledger is per-checkout working state, and until this slice an in-flight
task did not survive losing it: its rows existed only in `.wf/ledger.db`, the
evidence in `refs/wf/*` outlived them, recovery refused that ownerless evidence
and the orchestrator retried the whole attempt. A checkpoint is the anchor that
makes the rows outlive the file — the same export bytes the close writes,
pinned to a LOCAL ref, never written into the working tree and never committed.

Three rules hold it apart from the close export, and each is a NAME rather than
a flag:

- **`write_checkpoint` versus `pin_export`.** The pin is the claim "this blob
  is what the ledger says about a task that LANDED", so it gates on the state
  and records `tasks.export_oid` — the closure latch. A checkpoint claims only
  "these were the rows at an activation close", which is legal in every state
  and latches nothing. One emitter feeds both (`export.export_task`), so D3's
  byte rules apply unchanged and neither can drift from the other.
- **`refs/wf/checkpoints/` versus `refs/wf/exports/`.** `reverify.anchor_oid`
  — the one definition of a CLOSE anchor, shared by `closed()` and `wf ledger
  verify` — reads the committed blob and the export ref. It cannot see this
  namespace, so a task anchored only by checkpoints is never closed, and no
  caller has to remember that.
- **The staging file is outside the working tree.** Bytes reach `git
  hash-object` through a file; that file lives beside the fence in the git
  common directory, so it is neither coordinator dirt nor something the
  orchestrator could commit as a close.

A rebuild reads each task from the newest anchor it has, and that is the close
anchor whenever one exists: the committed export path may only be written for
a LANDED task, so every file on it is written AFTER the last activation close
and preferring it by name is the same answer a timestamp would give — without
trusting a timestamp.

What a checkpoint does NOT carry is what an export does not carry: `claims`,
`tracker_outbox`, `sessions`, `artifacts` and `usage` are outside
`EXPORT_TABLES`. So a rebuild loses pending outbox rows and held claims, and
they are re-derived rather than restored — `wf ledger reconcile <task>` drains
a `Close` the rebuilt `closed()` says is owed and releases a stranded claim,
and the next admission re-takes the claim through the normal path.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import Final
from uuid import uuid4

import structlog

from workflow_interpreter.bdio.errors import StoreError
from workflow_interpreter.contracts.run_identity import ComponentKind, safe_component
from workflow_interpreter.inspector.errors import GitCommandError
from workflow_interpreter.inspector.gitcmd import GitSubcommand
from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.inspector.sandbox import fence_dir
from workflow_interpreter.ledger.constants import (
    CHECKPOINT_BYTES_LIMIT,
    CHECKPOINT_DIR,
    CHECKPOINT_REF_TEMPLATE,
    EXPORT_SUFFIX,
    MSG_CHECKPOINTS_UNREADABLE,
)
from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.ledger.errors import LedgerExportError
from workflow_interpreter.ledger.export import export_task
from workflow_interpreter.ledger.paths import export_dir, export_path, fence_path

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

_BLOB: Final[str] = "blob"
_HEAD_FILE: Final[str] = "HEAD"
_TEMP_INFIX: Final[str] = "."
"""What separates the staging file's name from the unique suffix that makes a
concurrent writer's temporary file a different file."""

_STAGING_LOCKS: Final[dict[str, threading.Lock]] = {}
_LOCKS_GUARD: Final[threading.Lock] = threading.Lock()
"""One lock per task, minted under a guard: the dict is read and extended from
every thread that closes an activation, and `setdefault` alone would let two
threads of one task take two different locks."""


def checkpoint_ref(task_id: str) -> str:
    """`refs/wf/checkpoints/<task>` — this task's local, uncommitted anchor."""
    return CHECKPOINT_REF_TEMPLATE.format(task_id=task_id)


def staging_path(repo_root: Path, task_id: str) -> Path:
    """Where this task's checkpoint bytes are staged, outside the working tree.

    The id goes through the ONE identifier grammar before it becomes a path
    component (`safe_component`, §3.6's rule for every ref and every path the
    engine derives from a task id), rather than being trusted because of where
    it was read from: this path is under the git COMMON directory, which every
    worktree of the repository shares, so a traversal here would escape into
    the one directory the fence itself lives in.
    """
    safe = safe_component(task_id, kind=ComponentKind.TASK)
    return fence_path(repo_root).parent / CHECKPOINT_DIR / f"{safe}{EXPORT_SUFFIX}"


def write_checkpoint(git: Git, database: LedgerDatabase, task_id: str) -> str:
    """Anchor this task's current rows at `refs/wf/checkpoints/<task>` (§3.9).

    The same bytes a close would export, from the same emitter, so a rebuild
    reads one shape whichever anchor answered. Nothing about the FILE and
    nothing about closure is written: no `.wf/export/` file is touched and
    `tasks.export_oid` is not recorded, because a checkpoint is not the claim
    the latch stands for.

    Overwrites the ref rather than adding to it — one per task is what makes
    this bounded, and the blob it drops becomes unreachable for git gc.

    Raises rather than degrading: the DEGRADING caller is `TaskCheckpoint`,
    which is the one that runs on the activation-close path. A future operator
    command aimed at this must hear about a failure.

    Two writers of ONE task are the case this is ordered for (S7 review,
    finding 3): the staging path is keyed by task id alone, and a task can
    have several roots closing activations on two threads of one process
    (`database.py`). So the bytes land through `os.replace` of a uniquely
    named file — either complete export is valid, a half-written one is not —
    and the stage, the blob and the ref are taken under one per-task lock, so
    the ref a checkpoint pins names the bytes that checkpoint staged.

    The snapshot is read BEFORE the lock, because `export_task` holds the
    connection for the whole read and the lock is only about the file.
    """
    payload = export_task(database, task_id)
    path = staging_path(database.repo_root, task_id)
    ref = checkpoint_ref(task_id)
    with _staging_lock(task_id):
        _stage(path, payload)
        oid = git.write_blob(path, cwd=database.repo_root)
        git.update_ref(ref, oid, cwd=database.repo_root)
    _LOG.info(
        "wf.ledger.checkpointed",
        task_id=task_id,
        ref=ref,
        oid=oid,
        bytes=len(payload),
    )
    return oid


def _stage(path: Path, payload: bytes) -> None:
    """Put `payload` on `path` atomically, leaving no partial file behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}{_TEMP_INFIX}{uuid4().hex}")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _staging_lock(task_id: str) -> threading.Lock:
    """The lock that orders this task's stage, blob and ref against its twin.

    Per task rather than one global lock: two different tasks share neither
    the staging file nor the ref, and the ledger's own `_writing` lock is
    released before any of this runs (it guards the connection, not the file).
    """
    with _LOCKS_GUARD:
        return _STAGING_LOCKS.setdefault(task_id, threading.Lock())


def checkpoint_source(git: Git, repo_root: Path, task_id: str) -> Path | None:
    """Stage this task's checkpoint blob as a file a rebuild can parse.

    A file because `import_exports` parses files and must keep doing so: the
    import's whole shape — every source validated BEFORE the exclusive fence —
    is the property that keeps a bad set from reaching SQL, and a second entry
    point taking bytes would be a second chance to lose it. The staging file is
    outside the working tree, so materialising a checkpoint can never be
    mistaken for the committed export (§3.6).
    """
    oid = git.ref_target(checkpoint_ref(task_id), cwd=repo_root)
    if oid is None:
        return None
    payload = git.bounded_bytes(
        GitSubcommand.CAT_FILE,
        _BLOB,
        oid,
        cwd=repo_root,
        limit=CHECKPOINT_BYTES_LIMIT,
    )
    path = staging_path(repo_root, task_id)
    with _staging_lock(task_id):
        _stage(path, payload)
    return path


def checkpoint_tasks(git: Git, repo_root: Path) -> tuple[str, ...]:
    """Every task this checkout holds a checkpoint for, in ref order.

    Three different answers, and only one of them is empty by right:

    - a tree git does not recognise as a repository AT ALL has no refs to
      find, and a rebuild from the COMMITTED exports — which needs no git —
      must not be lost to the question of whether it also has checkpoints.
      Decided by the SHAPE of the checkout (`_git_readable`) rather than by a
      git failure, because `git show-ref` spends one exit code (128) on both
      that and every fatal defect;
    - git answering "no refs under this prefix" is the empty set, because that
      answer is TRUE (`ref_names_under` returns `()` on `show-ref`'s exit 1);
    - git FAILING to answer is refused. Swallowing it made `_discovered` fall
      back to the committed exports alone, and the import that followed
      cleared every in-flight task's rows out of a live ledger while reporting
      success (S7 review, finding 2).
    """
    if not _git_readable(repo_root):
        _LOG.info("wf.ledger.checkpoints_unreadable", repo_root=str(repo_root))
        return ()
    prefix = CHECKPOINT_REF_TEMPLATE.format(task_id="")
    try:
        names = git.ref_names_under(prefix, cwd=repo_root)
    except GitCommandError as unanswerable:
        raise LedgerExportError(
            MSG_CHECKPOINTS_UNREADABLE.format(
                prefix=prefix, repo_root=repo_root, reason=unanswerable
            )
        ) from unanswerable
    return tuple(name.removeprefix(prefix) for name in names)


def _git_readable(repo_root: Path) -> bool:
    """Whether git will read this tree as a repository at all (§3.9's degrade).

    Structural, and no subprocess: `fence_dir` already routes on what `.git`
    IS, and `<common>/HEAD` is the file whose absence makes every git command
    answer "not a git repository". That is the ONE unreadable checkout a
    rebuild degrades past, so it is decided here rather than read out of an
    exit code that also carries real failures.
    """
    fence = fence_dir(repo_root)
    return fence is not None and (fence.parent / _HEAD_FILE).is_file()


def rebuild_sources(
    git: Git, repo_root: Path, task_ids: Sequence[str]
) -> tuple[Path, ...]:
    """The files a rebuild reads: each task's CLOSE anchor, else its checkpoint.

    The close export wins wherever one is on disk, and that is the newest
    answer rather than merely the preferred one: NOTHING may write that path
    for a task that has not landed (`export.write_landed_export`), so every
    file on it was written at landing — after the last activation close — and
    a checkpoint can only ever be the older of the two. Before that gate, an
    operator's `wf ledger export` of a running task left a file the import
    preferred over every later checkpoint, and the import clears before it
    refills (S7 review, finding 1). Its FILE rather than its anchor — a crash
    between `write_export` and the pin leaves the whole record sitting in the
    checkout unanchored (§3.6), and a rebuild that preferred the checkpoint
    there would drop the task back below LANDED and leave `pin-export`, the
    documented recovery, refusing it.

    A task NAMED on the command line with neither anchor keeps its committed
    path, so the import refuses by naming the file the operator expected —
    rather than quietly rebuilding a smaller set than they asked for. A
    discovered task always has one of the two, because that is what discovered
    it.

    Which tasks HAVE a checkpoint is asked once, of the ref listing, rather
    than per task: one `show-ref` instead of a `rev-parse` each, and it is the
    one question that degrades when git cannot answer for the tree.
    """
    checkpointed = frozenset(checkpoint_tasks(git, repo_root))
    wanted = tuple(task_ids) if task_ids else _discovered(repo_root, checkpointed)
    sources: list[Path] = []
    for task_id in wanted:
        committed = export_path(repo_root, task_id)
        staged = (
            checkpoint_source(git, repo_root, task_id)
            if task_id in checkpointed and not committed.is_file()
            else None
        )
        sources.append(committed if staged is None else staged)
    return tuple(sources)


def _discovered(repo_root: Path, anchored: frozenset[str]) -> tuple[str, ...]:
    """Every task some anchor in this checkout can rebuild, deduplicated."""
    committed = {
        path.name.removesuffix(EXPORT_SUFFIX)
        for path in export_dir(repo_root).glob(f"*{EXPORT_SUFFIX}")
    }
    return tuple(sorted(committed | anchored))


class TaskCheckpoint:
    """The `CheckpointSink` an activation close reaches, and it never raises.

    The degradation is the whole contract (§3.9): by the time this is called
    the close has committed, so raising would turn "this run cannot be rebuilt
    from a deleted ledger" — the behaviour of every build before S7 — into
    "this run failed". A full disk, a read-only object store, a checkout that
    is not a repository: all of them log and continue.
    """

    def __init__(self, database: LedgerDatabase, git: Git) -> None:
        self._database = database
        self._git = git

    def checkpoint(self, task_id: str) -> None:
        """Anchor the task's rows, or record why this close could not."""
        try:
            write_checkpoint(self._git, self._database, task_id)
        except (OSError, GitCommandError, StoreError) as refusal:
            _LOG.warning(
                "wf.ledger.checkpoint_refused", task_id=task_id, reason=str(refusal)
            )
