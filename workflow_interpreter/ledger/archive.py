"""Retire a finished task's bytes, but never before they are recoverable (§3.9).

`wf archive <task>` is MANUAL and deliberately so (D14): nothing in the engine
deletes a run folder on a schedule. It is also strictly ordered, and the order
is the whole design (D19):

1. refuse unless the task is RETIRED — `closed()` or abandoned (§3.5) — and,
   for a closed one, unless every root settled, because a live run has nothing
   to archive. An abandoned task stopped mid-run and has no terminal node to
   wait for (§3.8), so what stands in for the settlement there is the same
   proven death terminal cleanup takes before it deletes anything;
2. write a git bundle of every `refs/wf/<root>/*` the task pinned, to a path
   the operator chose OUTSIDE the repository;
3. verify that bundle with git itself;
4. and only then delete the run folders and the refs.

The task's local checkpoint anchor goes with them (§3.9), outside the bundle:
it holds rows the committed export already carries, and a retired task that
kept one would keep its blob reachable forever and be resurrected into every
later `import` by `checkpoint.rebuild_sources`.

The export is JSON and JSON does not preserve git objects, so the bundle is
the only thing standing between a retention pass and a rejected artifact
nobody can look at again.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio.reads import list_activations
from workflow_interpreter.inspector.config import InspectorConfig
from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.inspector.paths import WrapperPaths
from workflow_interpreter.inspector.toolchain_cleanup import death_refusal
from workflow_interpreter.ledger.checkpoint import (
    checkpoint_ref,
    staging_path,
    stale_ref,
)
from workflow_interpreter.ledger.closure import abandoned, retired
from workflow_interpreter.ledger.constants import MSG_NOT_RETIRED
from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.ledger.errors import LedgerExportError
from workflow_interpreter.ledger.store import LedgerStore
from workflow_interpreter.ledger.tasks import task_roots

ROOT_REF_PREFIX: Final[str] = "refs/wf/{root_id}/"

MSG_UNKNOWN_TASK: Final[str] = "the ledger holds no task {task_id!r}"
MSG_LIVE_ROOT: Final[str] = (
    "root {root_id!r} of task {task_id!r} has not settled; archive is for "
    "finished runs only"
)
MSG_BUNDLE_INSIDE: Final[str] = (
    "the bundle path {path} is inside the repository; archive writes outside it"
)
MSG_BUNDLE_EXISTS: Final[str] = "the bundle path {path} already exists"
MSG_NO_REFS: Final[str] = "task {task_id!r} pinned no refs/wf/<root>/ to archive"
MSG_LIVE_CREW: Final[str] = (
    "activation {activation_id!r} of root {root_id!r} still has a live crew "
    "({reason}); archive deletes bytes a running process may still be writing, "
    "so nothing was deleted"
)
MSG_UNVERIFIED: Final[str] = "git refused the bundle at {path}; nothing was deleted"


class ArchiveResult(BaseModel):
    """What one archive removed, and what it is recoverable from."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_id: str
    bundle: Path
    refs: tuple[str, ...]
    run_folders: tuple[Path, ...]
    checkpoint_cleared: bool = False
    """Whether this task also held a `refs/wf/checkpoints/` anchor. Reported
    rather than counted with `refs`: the bundle holds the root refs only, and
    the checkpoint is dropped because it is redundant, not preserved."""


def archive_task(
    git: Git,
    database: LedgerDatabase,
    task_id: str,
    *,
    bundle: Path,
    inspector: InspectorConfig,
) -> ArchiveResult:
    """Bundle, verify, then delete one retired task's run folders and refs.

    The two roots come from `inspector` rather than beside it: the wrapper
    directories this deletes and the repository it bundles from are the ones
    the death proof below reads its `/proc` evidence against, and a second
    pair of path arguments would be a second chance for them to disagree
    (`ForemanConfig` already asserts they match).
    """
    repo_root = inspector.repo_root
    wrapper_root = inspector.wrapper_root
    roots = task_roots(database, task_id)
    if not roots:
        raise LedgerExportError(MSG_UNKNOWN_TASK.format(task_id=task_id))
    if not retired(database, git, task_id):
        raise LedgerExportError(MSG_NOT_RETIRED.format(task_id=task_id))
    # A settled root is how a CLOSED task says its run is over. An abandoned
    # one never reaches a terminal node — that is what abandoning it did — so
    # asking for one kept `refs/wf/<root>/*` alive forever (cr-ov7l). The
    # retirement above is the gate a merely in-flight task still fails; the
    # state is read by name rather than by writing `roots.terminal`, which the
    # export carries as `wf_terminal` and would desync.
    if not abandoned(database, task_id):
        for root_id, terminal in roots:
            if not terminal:
                raise LedgerExportError(
                    MSG_LIVE_ROOT.format(root_id=root_id, task_id=task_id)
                )
    _assert_crews_dead(database, task_id, roots, inspector)
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
    cleared = _clear_checkpoint(git, repo_root, task_id)
    return ArchiveResult(
        task_id=task_id,
        bundle=bundle,
        refs=refs,
        run_folders=tuple(folders),
        checkpoint_cleared=cleared,
    )


def _assert_crews_dead(
    database: LedgerDatabase,
    task_id: str,
    roots: tuple[tuple[str, str], ...],
    inspector: InspectorConfig,
) -> None:
    """Refuse the archive while any activation of this task may still be running.

    Retirement is a RECORD event and a crew is an operating-system one, so
    neither `closed()` nor an abandon proves the processes are gone: `wf phase
    abandon` writes the state and leaves the killing to cleanup, which is the
    one thing that takes the death proof. Archive deletes strictly more than
    cleanup does — the wrapper directories AND the `refs/wf/<root>/*` that are
    the only pin on unbundled output — so it asks the SAME question, through
    the same `death_refusal`, rather than growing a second liveness rule that
    could drift from it (cr-ov7l, §3.9).
    """
    store = LedgerStore(database, task_id=task_id)
    for root_id, _ in roots:
        paths = WrapperPaths(inspector, root_id)
        for activation in list_activations(store, root_id):
            refusal = death_refusal(paths, activation)
            if refusal is not None:
                raise LedgerExportError(
                    MSG_LIVE_CREW.format(
                        activation_id=activation.activation_id,
                        root_id=root_id,
                        reason=refusal,
                    )
                )


def _clear_checkpoint(git: Git, repo_root: Path, task_id: str) -> bool:
    """Drop this task's local checkpoint anchor and its staged bytes (§3.9).

    Not in the bundle and not recoverable from it: a checkpoint is a LOCAL
    mid-run anchor over rows the committed export already carries, and this
    task is retired. Left behind it would keep its blob permanently reachable
    — contradicting the constant's own claim that dropped blobs become
    unreachable — and `_discovered` would resurrect the task into every later
    `import`, which is worst for an ABANDONED one (S7 review, finding 4).
    """
    ref = checkpoint_ref(task_id)
    if git.ref_target(ref, cwd=repo_root) is None:
        return False
    git.delete_ref(ref, cwd=repo_root)
    # The staleness marker goes with the anchor it is about (cr-kba4): left
    # behind it would refuse every later import over a checkpoint that no
    # longer exists.
    git.delete_ref(stale_ref(task_id), cwd=repo_root)
    staging_path(repo_root, task_id).unlink(missing_ok=True)
    return True
