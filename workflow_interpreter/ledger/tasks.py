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
from workflow_interpreter.contracts.run_identity import epic_segment
from workflow_interpreter.ledger.database import LedgerDatabase

_FIRST_SEQ: Final[int] = 1
_SQL_PIN_TASK: Final[str] = (
    "INSERT OR IGNORE INTO tasks "
    "(task_id, epic_id, graph_id, backend, next_seq, created_at) "
    "VALUES (?, ?, NULL, ?, ?, ?)"
)
_SQL_TASK_BACKEND: Final[str] = "SELECT backend FROM tasks WHERE task_id = ?"
_SQL_TASK_EXPORT: Final[str] = "SELECT export_oid FROM tasks WHERE task_id = ?"
_SQL_RECORD_EXPORT: Final[str] = (
    "UPDATE tasks SET export_oid = ?, exported_at = ? WHERE task_id = ?"
)
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
    with database.locked() as connection:
        row = connection.execute(_SQL_TASK_BACKEND, (task_id,)).fetchone()
    return None if row is None else BackendKind(str(row[0]))


def root_backend(database: LedgerDatabase, root_id: str) -> BackendKind | None:
    """The backend pinned on one root, or nothing when the ledger has no such root.

    A root the ledger holds a row for IS ledger-backed; the column is read
    rather than assumed so that the pin the row was written with is the one
    that answers, exactly as it does for the task.
    """
    with database.locked() as connection:
        row = connection.execute(_SQL_ROOT_BACKEND, (root_id,)).fetchone()
    return None if row is None else BackendKind(str(row[0]))


def record_export_oid(database: LedgerDatabase, task_id: str, oid: str) -> None:
    """Record the blob this task's export is pinned as (§3.6).

    Overwrites rather than appends: a crash after the blob was written but
    before the oid was recorded re-runs the export at the next close, and the
    later pin is the one the later close names.
    """
    with database.transaction():
        database.connection.execute(
            _SQL_RECORD_EXPORT, (oid, datetime.now(tz=UTC).isoformat(), task_id)
        )


def export_oid(database: LedgerDatabase, task_id: str) -> str | None:
    """The pinned export blob of a task, or nothing while it owes one."""
    with database.locked() as connection:
        row = connection.execute(_SQL_TASK_EXPORT, (task_id,)).fetchone()
    return None if row is None or row[0] is None else str(row[0])
