"""Whether a task is closed, derived once and then LATCHED (§3.5, R6).

Closure is not a stored state. A stored CLOSED can only be written after the
export bytes exist, so it could never be IN the export — either it violates D5
("never closable before the record is durable") or it is lost the moment the
ledger is rebuilt from the file that is supposed to carry the whole record.

So it is derived, from two facts and one latch:

```text
closed(task):
    if tasks.export_oid is set:                      return True    # the latch
    if tasks.state != LANDED:                        return False
    oid = anchor_oid(task)            # committed blob first, export ref second
    if oid is None:                                  return False
    if blob_hash(.wf/export/<task>.jsonl) != oid:    return False
    tasks.export_oid = oid                           # derive once, then latch
    return True
```

The latch is what makes it MONOTONIC, and monotonicity is the whole point. A
live re-export is a function of mutable state — the header carries the schema
version and `projections` is exported — so recomputing closure would reopen
every closed task after one migration or one attention drain. Today's
`export_oid is None` is monotonic; this keeps that property and adds only the
rebuild path.

The file ON DISK is hashed, never a fresh export, exactly as `reverify._pin_check`
does, and the anchor comes from `reverify.anchor_oid` itself: `wf ledger verify`
and `closed()` must never disagree about which bytes are this task's record. A
stale committed blob that no longer matches the file is "not closed" to both,
and the orchestrator recommits.

`retired(task) = closed(task) ∨ state == ABANDONED`: an abandoned task never
exports, so terminal cleanup and archive would otherwise defer forever (§3.8).
Nothing else reads `retired`.
"""

from __future__ import annotations

from typing import Final, Protocol

import structlog

from workflow_interpreter.inspector.gitio import NO_BLOB, Git
from workflow_interpreter.ledger.constants import TaskState
from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.ledger.reverify import anchor_oid
from workflow_interpreter.ledger.tasks import export_oid, record_export_oid, task_state

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)


def closed(database: LedgerDatabase, git: Git, task_id: str) -> bool:
    """Whether this task's whole record is durable in git (§3.5).

    The first ask that can answer yes WRITES the answer, so every later ask is
    a column read and no git state can take it back.
    """
    if export_oid(database, task_id) is not None:
        return True
    if task_state(database, task_id) is not TaskState.LANDED:
        return False
    anchor, pinned, relative = anchor_oid(database.repo_root, task_id)
    if anchor is None or pinned is None:
        return False
    found = git.hash_working_file(relative, cwd=database.repo_root)
    if found == NO_BLOB or found != pinned:
        return False
    record_export_oid(database, task_id, pinned)
    _LOG.info(
        "wf.ledger.closure_derived",
        task_id=task_id,
        anchor=anchor.value,
        oid=pinned,
    )
    return True


def retired(database: LedgerDatabase, git: Git, task_id: str) -> bool:
    """Whether this task is over — closed, or abandoned (§3.5, §3.8).

    What terminal cleanup and archive read. An abandoned task has no export
    and never will, so asking them to wait for closure would keep its worktree
    and its refs forever.
    """
    return closed(database, git, task_id) or (
        task_state(database, task_id) is TaskState.ABANDONED
    )


class ClosureProbe(Protocol):
    """What a caller needs to ask about a task's closure, and nothing else.

    A protocol rather than the class below because the contractor depends on
    the QUESTION, not on the ledger that answers it: the adapter holds one of
    these to refuse a close and a succession, and it must not know what a
    database is.
    """

    def closed(self, task_id: str) -> bool:
        """Whether this task's whole record is durable in git."""
        ...

    def retired(self, task_id: str) -> bool:
        """Whether this task is closed or abandoned."""
        ...


class TaskClosure:
    """The ledger's own answer to both questions, for one checkout.

    The contractor holds one of these rather than a database and a git seam:
    the adapter owns bead writes and may not grow a ledger of its own, but the
    close it performs and the succession it refuses are both decided by
    whether the task's record is already durable (§3.5).
    """

    def __init__(self, database: LedgerDatabase, git: Git) -> None:
        self._database = database
        self._git = git

    def closed(self, task_id: str) -> bool:
        """Whether this task's whole record is durable in git."""
        return closed(self._database, self._git, task_id)

    def retired(self, task_id: str) -> bool:
        """Whether this task is closed or abandoned."""
        return retired(self._database, self._git, task_id)
