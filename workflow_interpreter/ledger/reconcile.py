"""The attention projection: ledger state written onto the task bead (§3.2).

One label, `wf:attention`, whose desired value is a pure function of the
ledger — present iff any non-terminal root of the task has a gate in state
OPEN. Every transaction that can change that predicate journals a
`projections` row; this is the reconciler that drains them.

Three properties it exists to guarantee.

1. **No crash window.** The journal row is written in the SAME transaction as
   the state change, so a process that dies before writing the label leaves a
   row the next drain finds. Replay is idempotent because the write is "set
   the label to what the ledger says now", never "toggle".
2. **No lost update.** Recompute, write and ack all happen under one
   task-keyed lock, and the ack covers only generations at or below the one
   that was reconciled. A generation enqueued while this drain was running
   stays unacked, so the value it implies is never assumed to be written.
3. **No bd inside a transaction** (§3.4.2). The label write is a subprocess;
   the ledger reads that surround it are single statements.

The bd client is a DEPENDENCY, never a construction: a reconciler that built
its own transport would be a second bd write path, and §0.1 leaves exactly one.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Protocol

import structlog
from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio.carriers import GateState
from workflow_interpreter.bdio.wire import BeadRecord
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
_SQL_ACK: Final[str] = (
    "UPDATE projections SET acked_at = ? "
    "WHERE task_id = ? AND generation <= ? AND acked_at IS NULL"
)


class AttentionWriter(Protocol):
    """The bd surface a projection needs, and nothing else.

    Package-private names for the same reason `StoreBackend`'s writes are
    (§0.1): the label write is reachable from this one typed operation, not
    from anything holding a transport.
    """

    def _add_label(self, bead_id: str, label: str) -> BeadRecord:
        """Add one label and read the bead back."""

    def _remove_label(self, bead_id: str, label: str) -> BeadRecord:
        """Remove one label and read the bead back."""


class ReconcileResult(BaseModel):
    """What one drain did, for a caller and for the CLI's one line of output."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_id: str
    wanted: bool
    """The desired presence of the label, recomputed from the ledger."""
    generation: int | None = None
    """The newest generation this drain reconciled; `None` when none was due."""
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
        row = self._database.connection.execute(
            _SQL_WANTED, (task_id, GateState.OPEN.value, STATUS_OPEN)
        ).fetchone()
        return bool(row[0])

    def drain(self, task_id: str) -> ReconcileResult:
        """Reconcile every unacked generation of this task, under its lock.

        Order is the whole point: take the lock, read the newest unacked
        generation, recompute the desired state AFTER it, write bd and read
        the bead back, and only then ack up to that generation.

        The lock's wait is bounded and its refusal names the holder: another
        drain of this task is already doing exactly this work, and the rows
        this one would have acked stay unacked for whichever drain runs next.
        """
        lock = LedgerFence(
            task_lock_path(self._database.wrapper_root, task_id),
            wait_s=self._lock_wait_s,
        )
        with lock.exclusive():
            pending = self._database.connection.execute(
                _SQL_PENDING, (task_id,)
            ).fetchone()
            newest = pending["newest"]
            wanted = self.wanted(task_id)
            if newest is None:
                return ReconcileResult(task_id=task_id, wanted=wanted)
            generation = int(newest)
            self._write(task_id, wanted=wanted)
            acked = self._ack(task_id, generation)
        _LOG.info(
            "wf.ledger.attention_reconciled",
            task_id=task_id,
            wanted=wanted,
            generation=generation,
            acked=acked,
        )
        return ReconcileResult(
            task_id=task_id,
            wanted=wanted,
            generation=generation,
            acked=acked,
            written=True,
        )

    def _write(self, task_id: str, *, wanted: bool) -> BeadRecord:
        """Set the label to the desired state — the write that replay repeats."""
        if wanted:
            return self._writer._add_label(task_id, ATTENTION_LABEL)
        return self._writer._remove_label(task_id, ATTENTION_LABEL)

    def _ack(self, task_id: str, generation: int) -> int:
        """Ack every generation up to the one whose state was just written."""
        with self._database.transaction():
            cursor = self._database.connection.execute(
                _SQL_ACK,
                (datetime.now(tz=UTC).isoformat(), task_id, generation),
            )
            return int(cursor.rowcount)


__all__ = [
    "ATTENTION_LABEL",
    "AttentionReconciler",
    "AttentionWriter",
    "ReconcileResult",
    "task_lock_path",
]
