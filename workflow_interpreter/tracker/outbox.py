"""Intents awaiting a tracker that can answer (§3.2, D6).

The outbox is what makes the tracker a MIRROR rather than a dependency. A
close, an attention flag and a claim release are all decided by the ledger
first; the row here is the statement that the mirror still owes a write, and
the drain is the only place a tracker is contacted outside prepare and admit.

Two properties it exists to give.

1. **Nothing durable waits on a tracker.** A landed, exported, pinned task is
   closed whatever bd says; `Unknown` leaves a row and the process exits.
2. **One pending row per desired state.** The rows are states, not events, so
   a second enqueue of the same key REPLACES the pending one instead of
   queueing a second write — which is why a drain can be repeated and why
   "exactly one pending row" is a property worth asserting.

`tracker_outbox` is not exported (§3.6): it records what this checkout still
owes its tracker, which is neither a fact about the task nor portable to the
clone that rebuilds from the file.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final

import structlog
from pydantic import BaseModel, ConfigDict

from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.tracker.constants import ResultKind
from workflow_interpreter.tracker.intents import (
    INTENT_ADAPTER,
    Annotate,
    SetFlag,
    TrackerIntent,
)
from workflow_interpreter.tracker.port import TrackerPort

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

_SQL_ENQUEUE: Final[str] = (
    "INSERT INTO tracker_outbox (task_id, intent_key, intent_json, enqueued_at) "
    "VALUES (?, ?, ?, ?) "
    "ON CONFLICT (intent_key) WHERE applied_at IS NULL DO UPDATE SET "
    "intent_json = excluded.intent_json, enqueued_at = excluded.enqueued_at"
)
_SQL_PENDING: Final[str] = (
    "SELECT outbox_id, intent_json FROM tracker_outbox "
    "WHERE applied_at IS NULL ORDER BY outbox_id"
)
_SQL_PENDING_TASK: Final[str] = (
    "SELECT outbox_id, intent_json FROM tracker_outbox "
    "WHERE applied_at IS NULL AND task_id = ? ORDER BY outbox_id"
)
_SQL_RETIRE: Final[str] = (
    "UPDATE tracker_outbox SET applied_at = ?, result = ? WHERE outbox_id = ?"
)


class DrainResult(BaseModel):
    """What one drain did, for the caller and for the log line."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    applied: int = 0
    conflicts: tuple[str, ...] = ()
    """The refs whose tracker disagreed. Retired, not retried: a conflict is a
    decision for whoever reads it, and re-sending the same state would not
    change the answer."""
    pending: int = 0


def intent_key(intent: TrackerIntent) -> str:
    """The key one pending row per desired state is kept under.

    The kind and the ref, plus whatever else makes two intents of that kind
    DIFFERENT states rather than the same one restated: two flags are two
    rows, two closings of one item are one row.
    """
    parts = [intent.kind.value, intent.ref.kind.value, intent.ref.ref]
    if isinstance(intent, SetFlag):
        parts.append(intent.flag)
    elif isinstance(intent, Annotate):
        parts.append(intent.key)
    return ":".join(parts)


class TrackerOutbox:
    """The `tracker_outbox` table, enqueued into and drained from."""

    def __init__(self, database: LedgerDatabase) -> None:
        self._database = database

    def enqueue(self, task_id: str, intent: TrackerIntent) -> None:
        """Record that the mirror owes this desired state.

        Never inside a caller's transaction and never conditional on a
        tracker: this is a single ledger write, and it is what makes the
        tracker call itself optional for everything after it (§3.1).
        """
        with self._database.transaction() as connection:
            connection.execute(
                _SQL_ENQUEUE,
                (
                    task_id,
                    intent_key(intent),
                    intent.model_dump_json(),
                    datetime.now(tz=UTC).isoformat(),
                ),
            )

    def pending(self, task_id: str | None = None) -> tuple[TrackerIntent, ...]:
        """Every intent still owed, oldest first."""
        return tuple(intent for _, intent in self._rows(task_id))

    def drain(self, tracker: TrackerPort, task_id: str | None = None) -> DrainResult:
        """Apply what is owed, retiring every row the tracker answered.

        `Unknown` is the only answer that leaves a row: it means the tracker
        did not say, and the desired state is still owed. A `Conflict` is an
        answer — the tracker disagrees — so the row retires and the conflict
        is reported rather than retried forever.
        """
        applied = 0
        conflicts: list[str] = []
        pending = 0
        for outbox_id, intent in self._rows(task_id):
            result = tracker.apply(intent)
            if result.result is ResultKind.UNKNOWN:
                pending += 1
                continue
            if result.result is ResultKind.CONFLICT:
                conflicts.append(intent.ref.ref)
            else:
                applied += 1
            self._retire(outbox_id, result.result)
        if applied or conflicts or pending:
            _LOG.info(
                "wf.tracker.outbox_drained",
                tracker=tracker.kind.value,
                applied=applied,
                conflicts=conflicts,
                pending=pending,
            )
        return DrainResult(applied=applied, conflicts=tuple(conflicts), pending=pending)

    def _rows(self, task_id: str | None) -> tuple[tuple[int, TrackerIntent], ...]:
        """Every unapplied row, parsed back into the intent it was enqueued as."""
        with self._database.locked() as connection:
            rows = connection.execute(
                _SQL_PENDING if task_id is None else _SQL_PENDING_TASK,
                () if task_id is None else (task_id,),
            ).fetchall()
        return tuple(
            (int(row["outbox_id"]), INTENT_ADAPTER.validate_json(row["intent_json"]))
            for row in rows
        )

    def _retire(self, outbox_id: int, result: ResultKind) -> None:
        """Mark one row answered, keeping WHICH answer it got."""
        with self._database.transaction() as connection:
            connection.execute(
                _SQL_RETIRE,
                (datetime.now(tz=UTC).isoformat(), result.value, outbox_id),
            )
