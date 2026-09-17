"""The `tasks` and `roots` backend pins the locator reads (§3.2, D18).

Separate from `store.py` because these are not row writes through the seam:
they are the two answers to "which backend owns this?", and one of them has to
be writable for a task whose roots live in **bd** — a `LedgerStore` only ever
writes `backend = 'ledger'`, since every row it holds is its own.

The pin is written once per task and never rewritten. A switch flipped later
applies to new ATTEMPT roots, whose per-attempt pin is the bridge record's
`root_backend`; this row is the locator for a run that has no bridge (D16).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final

from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.ledger.store import epic_segment

_FIRST_SEQ: Final[int] = 1
_SQL_PIN_TASK: Final[str] = (
    "INSERT OR IGNORE INTO tasks "
    "(task_id, epic_id, graph_id, backend, next_seq, created_at) "
    "VALUES (?, ?, NULL, ?, ?, ?)"
)
_SQL_TASK_BACKEND: Final[str] = "SELECT backend FROM tasks WHERE task_id = ?"
_SQL_ROOT_BACKEND: Final[str] = "SELECT backend FROM roots WHERE root_id = ?"


def pin_task_backend(
    database: LedgerDatabase, task_id: str, backend: BackendKind
) -> BackendKind:
    """Record this task's backend if it has none, and answer what is pinned.

    Idempotent and non-destructive: a task that already names a backend keeps
    it, so a second start under a flipped `store` switch cannot retro-pin the
    roots that already exist (D18, no reverse migration). The answer is read
    back inside the same transaction, so the caller learns the pin in force
    rather than the one it asked for.
    """
    with database.transaction():
        database.connection.execute(
            _SQL_PIN_TASK,
            (
                task_id,
                epic_segment(task_id),
                backend.value,
                _FIRST_SEQ,
                datetime.now(tz=UTC).isoformat(),
            ),
        )
        pinned = task_backend(database, task_id)
    if pinned is None:  # pragma: no cover - the row is written just above
        raise LookupError(f"task row {task_id!r} vanished after its pin")
    return pinned


def task_backend(database: LedgerDatabase, task_id: str) -> BackendKind | None:
    """The backend pinned for a task, or nothing when the task is unknown."""
    row = database.connection.execute(_SQL_TASK_BACKEND, (task_id,)).fetchone()
    return None if row is None else BackendKind(str(row[0]))


def root_backend(database: LedgerDatabase, root_id: str) -> BackendKind | None:
    """The backend pinned on one root, or nothing when the ledger has no such root.

    A root the ledger holds a row for IS ledger-backed; the column is read
    rather than assumed so that the pin the row was written with is the one
    that answers, exactly as it does for the task.
    """
    row = database.connection.execute(_SQL_ROOT_BACKEND, (root_id,)).fetchone()
    return None if row is None else BackendKind(str(row[0]))
