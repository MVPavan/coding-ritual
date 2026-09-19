"""The `tasks` and `roots` backend pins the locator reads (§3.2, D18).

Separate from `store.py` because these are not row writes through the seam:
they are the two answers to "which backend owns this?", and one of them has to
be writable for a task whose roots live in **bd** — a `LedgerStore` only ever
writes `backend = 'ledger'`, since every row it holds is its own.

The pin is written once per task and never rewritten. A switch flipped later
applies to new ATTEMPT roots, whose per-attempt pin is the contractor record's
`root_backend`; this row is the locator for a run that has no contractor (D16).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final

from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.contracts.run_identity import epic_segment
from workflow_interpreter.ledger.constants import (
    MSG_EXPORT_NOT_RECORDED,
    MSG_STATE_NOT_RECORDED,
    TaskState,
)
from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.ledger.errors import LedgerExportError

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
_SQL_TASK_STATE: Final[str] = "SELECT state FROM tasks WHERE task_id = ?"
_SQL_RECORD_STATE: Final[str] = "UPDATE tasks SET state = ? WHERE task_id = ?"


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

    An UPDATE that matched nothing is a refusal, not a silent success: the
    caller's whole reason for being here is that the task now carries this
    blob, and a task with no row carries nothing — `export_oid` would go on
    answering "still owes an export" while the ref said otherwise (§3.6).
    """
    with database.transaction():
        updated = database.connection.execute(
            _SQL_RECORD_EXPORT, (oid, datetime.now(tz=UTC).isoformat(), task_id)
        )
        if updated.rowcount == 0:
            raise LedgerExportError(
                MSG_EXPORT_NOT_RECORDED.format(task_id=task_id, oid=oid)
            )


def export_oid(database: LedgerDatabase, task_id: str) -> str | None:
    """The pinned export blob of a task, or nothing while it owes one."""
    with database.locked() as connection:
        row = connection.execute(_SQL_TASK_EXPORT, (task_id,)).fetchone()
    return None if row is None or row[0] is None else str(row[0])


def record_task_state(database: LedgerDatabase, task_id: str, state: TaskState) -> None:
    """Record how far the contractor got with this task (§3.5).

    Written BEFORE the export bytes exist, unlike `export_oid`: the export has
    to carry it, because a ledger rebuilt in a clone has no other way to know
    that this task's work landed, and `closed()` refuses to derive closure for
    a task that never said so.

    An UPDATE that matched nothing is a refusal for the same reason the pin's
    is: the state would be silently lost and the task would stay open to every
    consumer that reads `closed()` or `retired()`.
    """
    with database.transaction():
        updated = database.connection.execute(_SQL_RECORD_STATE, (state.value, task_id))
        if updated.rowcount == 0:
            raise LedgerExportError(
                MSG_STATE_NOT_RECORDED.format(task_id=task_id, state=state.value)
            )


def task_state(database: LedgerDatabase, task_id: str) -> TaskState | None:
    """This task's recorded state, or nothing while it has reached none.

    An unrecognised value reads as nothing rather than raising: the column is
    exported, so a file written by a LATER build may name a state this one has
    no rule for, and "no state I can act on" is the safe reading of it — it
    leaves the task open.
    """
    with database.locked() as connection:
        row = connection.execute(_SQL_TASK_STATE, (task_id,)).fetchone()
    if row is None or row[0] is None:
        return None
    return next(
        (state for state in TaskState if state.value == str(row[0])),
        None,
    )


_SQL_TASK_ROOTS: Final[str] = (
    "SELECT root_id, terminal FROM roots WHERE task_id = ? ORDER BY seq"
)


def task_roots(database: LedgerDatabase, task_id: str) -> tuple[tuple[str, str], ...]:
    """Every ledger root of one task with the terminal it settled in.

    A root that has not settled answers with the empty string, so a caller can
    tell "no terminal yet" from "terminal `abandoned`" without a second read.
    """
    with database.locked() as connection:
        rows = connection.execute(_SQL_TASK_ROOTS, (task_id,)).fetchall()
    return tuple((str(row[0]), "" if row[1] is None else str(row[1])) for row in rows)
