"""The attention projection: ledger state written onto the task bead (§3.2).

One label, `wf:attention`, whose desired value is a pure function of the
ledger — present iff any non-terminal root of the task has a gate in state
OPEN. Every transaction that can change that predicate journals a
`projections` row; this is the reconciler that drains them.

A restore owes a drain too, and owes it in `restore_pending` rather than in
`projections`, so that §3.6's export→import→export stays byte-identical. A row
there is due exactly as an unacked generation is, and is retired in the same
ack step.

Three properties it exists to guarantee.

1. **No crash window.** The journal row is written in the SAME transaction as
   the state change, so a process that dies before writing the label leaves a
   row the next drain finds. Replay is idempotent because the write is "set
   the label to what the ledger says now", never "toggle".
2. **No lost update.** Recompute, write and ack all happen under one
   task-keyed lock, and the ack covers only generations at or below the one
   that was reconciled. A generation enqueued while this drain was running
   stays unacked, so the value it implies is never assumed to be written.
3. **No tracker inside a transaction** (§3.4.2), and since S5 no tracker
   inside a TICK either: the writer enqueues one `SetFlag` intent on the
   outbox and the drain at driver exit applies it (§3.3, superseding D6's
   direct label write).

The writer is a DEPENDENCY, never a construction: a reconciler that built its
own transport would be a second tracker write path, and §0.1 leaves one.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Protocol

import structlog
from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio.carriers import GateState
from workflow_interpreter.ledger.constants import (
    FENCE_WAIT_S,
    STATUS_OPEN,
    TASK_LOCK_DIR,
    TASK_LOCK_SUFFIX,
)
from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.ledger.fence import LedgerFence

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

ATTENTION_LABEL: Final[str] = "wf:attention"
"""The one derived label (§3.2). Never `bd human`, whose dismiss CLOSES the
issue — a projection may not decide a task is over."""

_SQL_PENDING: Final[str] = (
    "SELECT COUNT(*) AS pending, MAX(generation) AS newest FROM projections "
    "WHERE task_id = ? AND acked_at IS NULL"
)
_SQL_WANTED: Final[str] = (
    "SELECT EXISTS ("
    "  SELECT 1 FROM gates JOIN roots ON gates.root_id = roots.root_id "
    "  WHERE gates.task_id = ? AND gates.state = ? "
    "    AND roots.terminal IS NULL AND roots.status = ?"
    ") AS wanted"
)
_SQL_RESTORE: Final[str] = "SELECT requested_at FROM restore_pending WHERE task_id = ?"
_SQL_TASK_OF_ROOT: Final[str] = "SELECT task_id FROM roots WHERE root_id = ?"
_SQL_ACK: Final[str] = (
    "UPDATE projections SET acked_at = ? "
    "WHERE task_id = ? AND generation <= ? AND acked_at IS NULL"
)
_SQL_ACK_RESTORE: Final[str] = (
    "DELETE FROM restore_pending WHERE task_id = ? AND requested_at = ?"
)


class AttentionWriter(Protocol):
    """The one write a projection needs, as a DESIRED state (§3.3, R2).

    One method taking `on`, rather than the add/remove pair bd's transport
    speaks: the projection's whole correctness argument is that replay is
    idempotent because the write is "the flag should be present", never
    "toggle it". S5's writer enqueues exactly that intent on the outbox, so
    the label is applied when the driver exits instead of inside a tick.
    """

    def set_flag(self, task_id: str, flag: str, *, on: bool) -> None:
        """Make this flag's presence on the task match `on`."""


class ReconcileResult(BaseModel):
    """What one drain did, for a caller and for the CLI's one line of output."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_id: str
    wanted: bool
    """The desired presence of the label, recomputed from the ledger."""
    generation: int | None = None
    """The newest generation this drain reconciled; `None` when none was due —
    including a drain due only because the task was restored."""
    restored: bool = False
    """Whether this drain also retired the row an import left for a restore."""
    acked: int = 0
    written: bool = False
    """Whether bd was written at all — a drain with nothing due writes nothing."""


def task_lock_path(wrapper_root: Path, task_id: str) -> Path:
    """`<wrapper_root>/tasks/<task_id>.lock` — the task-keyed reconcile lock.

    Deliberately not the root-keyed member lock (`bdio/coordination.py`): two
    roots of ONE task must not interleave their recompute and their write, and
    a per-root lock lets exactly that happen (D6).
    """
    return wrapper_root / TASK_LOCK_DIR / f"{task_id}{TASK_LOCK_SUFFIX}"


class AttentionReconciler:
    """Drains one task's attention projections onto its task bead (§3.2)."""

    def __init__(
        self,
        database: LedgerDatabase,
        writer: AttentionWriter,
        *,
        lock_wait_s: float = FENCE_WAIT_S,
    ) -> None:
        self._database = database
        self._writer = writer
        self._lock_wait_s = lock_wait_s

    def wanted(self, task_id: str) -> bool:
        """Whether the ledger says this task needs attention, right now.

        A superseded or settled root cannot hold attention open: the predicate
        is over the task's LIVE roots, so a gate left open under a root that
        lost its race is not a reason to flag a human.
        """
        with self._database.locked() as connection:
            row = connection.execute(
                _SQL_WANTED, (task_id, GateState.OPEN.value, STATUS_OPEN)
            ).fetchone()
        return bool(row[0])

    def drain(self, task_id: str) -> ReconcileResult:
        """Reconcile every unacked generation of this task, under its lock.

        Order is the whole point: take the lock, read the newest unacked
        generation and the restore this task owes, recompute the desired state
        AFTER them, write bd and read the bead back, and only then ack up to
        that generation and retire that restore. A task owing both is one
        drain: the label is a function of the ledger, and it is written once.

        The lock's wait is bounded and its refusal names the holder: another
        drain of this task is already doing exactly this work, and the rows
        this one would have acked stay unacked for whichever drain runs next.
        """
        lock = LedgerFence(
            task_lock_path(self._database.wrapper_root, task_id),
            wait_s=self._lock_wait_s,
        )
        with lock.exclusive():
            with self._database.locked() as connection:
                pending = connection.execute(_SQL_PENDING, (task_id,)).fetchone()
                restore = connection.execute(_SQL_RESTORE, (task_id,)).fetchone()
            newest = pending["newest"]
            wanted = self.wanted(task_id)
            if newest is None and restore is None:
                return ReconcileResult(task_id=task_id, wanted=wanted)
            generation = None if newest is None else int(newest)
            self._write(task_id, wanted=wanted)
            acked = self._ack(task_id, generation, restore)
        _LOG.info(
            "wf.ledger.attention_reconciled",
            task_id=task_id,
            wanted=wanted,
            generation=generation,
            restored=restore is not None,
            acked=acked,
        )
        return ReconcileResult(
            task_id=task_id,
            wanted=wanted,
            generation=generation,
            restored=restore is not None,
            acked=acked,
            written=True,
        )

    def _write(self, task_id: str, *, wanted: bool) -> None:
        """Set the label to the desired state — the write that replay repeats."""
        self._writer.set_flag(task_id, ATTENTION_LABEL, on=wanted)

    def _ack(
        self, task_id: str, generation: int | None, restore: sqlite3.Row | None
    ) -> int:
        """Retire what this drain reconciled: generations, and the restore.

        The restore is deleted by the timestamp this drain READ, for the reason
        the ack is bounded by the generation it read: an import that landed
        while bd was being written owes a drain of its own, and this one must
        not swallow it.
        """
        acked = 0
        with self._database.transaction():
            if generation is not None:
                cursor = self._database.connection.execute(
                    _SQL_ACK,
                    (datetime.now(tz=UTC).isoformat(), task_id, generation),
                )
                acked = int(cursor.rowcount)
            if restore is not None:
                self._database.connection.execute(
                    _SQL_ACK_RESTORE, (task_id, restore["requested_at"])
                )
        return acked


class RootAttentionDrain:
    """Drains the task that owns one root, for a driver that is about to exit.

    The driver settles a root and leaves (`foreman/tick.py`); §3.2.4 makes that
    exit the last chance to write the label the settlement implies, because
    nothing else will run until the next tick of some other root. It takes the
    ROOT id because that is what a driver has: the task is the ledger's own
    mapping, and a root this ledger does not hold — every root on the bd
    backend — is simply nothing to drain.

    Refusals are not swallowed here. The caller decides what an unreachable bd
    costs it, and for the driver that is a logged refusal and unacked rows, not
    a blocked exit.
    """

    def __init__(
        self,
        database: LedgerDatabase,
        writer: AttentionWriter,
        *,
        lock_wait_s: float = FENCE_WAIT_S,
    ) -> None:
        self._database = database
        self._writer = writer
        self._lock_wait_s = lock_wait_s

    def __call__(self, root_id: str) -> None:
        """Reconcile this root's task, if the ledger holds the root at all."""
        with self._database.locked() as connection:
            row = connection.execute(_SQL_TASK_OF_ROOT, (root_id,)).fetchone()
        if row is None:
            return
        AttentionReconciler(
            self._database, self._writer, lock_wait_s=self._lock_wait_s
        ).drain(str(row[0]))


__all__ = [
    "ATTENTION_LABEL",
    "AttentionReconciler",
    "AttentionWriter",
    "ReconcileResult",
    "RootAttentionDrain",
    "task_lock_path",
]
