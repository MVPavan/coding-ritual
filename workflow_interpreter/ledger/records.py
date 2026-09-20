"""The contractor's record, as a ledger row with a version guard (§3.2, R4).

The record used to live in bead metadata, which meant that admission — the one
operation that must work when the tracker is unreachable — could not run
without it. It is a ledger row now, keyed by task, exported with the task, and
guarded by a version rather than by a merge.

What this module holds is deliberately OPAQUE. `record_json` is the
contractor's own carrier and the ledger never parses it: the dependency runs
one way, `contractor` → `ledger`, and a ledger that understood a contractor
record would be the shortest path back to two stores that have to agree. The
named columns — `state`, `attempt`, `brief` — are projections the contractor
states alongside the carrier, for the queries that must not parse JSON:
`closed()` gates on `state`, and `_refuse_other_admission` asks the epic.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Final

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.ledger.constants import (
    MSG_RECORD_EXISTS,
    MSG_RECORD_MISSING,
    MSG_RECORD_STALE,
    LedgerOperation,
)
from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.ledger.errors import LedgerRecordConflict, sqlite_failure

FIRST_VERSION: Final[int] = 1
"""The version a record is written with, so a guard has something to state."""

_SQL_READ: Final[str] = (
    "SELECT task_id, state, attempt, version, root_id, brief, record_json "
    "FROM contractor_records WHERE task_id = ?"
)
_SQL_INSERT: Final[str] = (
    "INSERT INTO contractor_records "
    "(task_id, state, attempt, version, root_id, brief, record_json, updated_at) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
)
_SQL_UPDATE: Final[str] = (
    "UPDATE contractor_records SET state = ?, attempt = ?, version = ?, "
    "root_id = ?, brief = ?, record_json = ?, updated_at = ? "
    "WHERE task_id = ? AND version = ?"
)
_SQL_SET_STATE: Final[str] = (
    "UPDATE contractor_records SET state = ?, version = version + 1, "
    "updated_at = ? WHERE task_id = ?"
)
_SQL_BY_ROOT: Final[str] = (
    "SELECT task_id, state, attempt, version, root_id, brief, record_json "
    "FROM contractor_records WHERE root_id = ? ORDER BY task_id"
)
_SQL_BY_EPIC: Final[str] = (
    "SELECT contractor_records.task_id, contractor_records.state "
    "FROM contractor_records JOIN tasks ON tasks.task_id = "
    "contractor_records.task_id WHERE tasks.epic_id = ? "
    "ORDER BY contractor_records.task_id"
)


class ContractorRecordRow(BaseModel):
    """One `contractor_records` row, carrier and projections together."""

    model_config = ConfigDict(frozen=True)

    task_id: str
    state: str
    attempt: int
    version: int
    root_id: str | None
    brief: str | None
    record_json: str


def read(database: LedgerDatabase, task_id: str) -> ContractorRecordRow | None:
    """This task's contractor record, or nothing while it has none."""
    with database.locked() as connection:
        row = connection.execute(_SQL_READ, (task_id,)).fetchone()
    return None if row is None else _row(row)


def create(
    database: LedgerDatabase,
    task_id: str,
    *,
    state: str,
    attempt: int,
    root_id: str | None,
    brief: str | None,
    record_json: str,
) -> ContractorRecordRow:
    """Write the first record of a task, refusing a second first write.

    Separate from `update` rather than an upsert: "this task has no record
    yet" and "this task's record is at version n" are different claims, and a
    prepare that silently overwrote a record already in flight would be the
    metadata merge this table exists to replace.
    """
    with database.transaction() as connection:
        try:
            connection.execute(
                _SQL_INSERT,
                (
                    task_id,
                    state,
                    attempt,
                    FIRST_VERSION,
                    root_id,
                    brief,
                    record_json,
                    _now(),
                ),
            )
        except sqlite3.IntegrityError as conflict:
            raise LedgerRecordConflict(
                MSG_RECORD_EXISTS.format(task_id=task_id)
            ) from conflict
        except sqlite3.Error as failure:
            raise sqlite_failure(
                failure, operation=LedgerOperation.RECORDING.value, row_id=task_id
            ) from failure
    return _required(database, task_id, LedgerOperation.RECORDING.value)


def update(
    database: LedgerDatabase,
    task_id: str,
    *,
    state: str,
    attempt: int,
    root_id: str | None,
    brief: str | None,
    record_json: str,
    expected_version: int,
    inside: Callable[[sqlite3.Connection], None] | None = None,
) -> ContractorRecordRow:
    """Move a record forward, only from the version the caller read.

    The guard is the WHERE clause, so the check and the write are one
    statement inside `BEGIN IMMEDIATE`: a concurrent transition cannot land
    between them, and the loser is refused by name instead of overwriting a
    state it never saw.

    `inside` is another ledger write that belongs to THIS transition — the
    outbox row for the mirror it implies. It runs after the guard has held, so
    a refused transition enqueues nothing, and it commits or rolls back with
    the transition itself: a crash between the fact and its mirror row would
    otherwise lose the intent forever, since nothing re-derives a missing
    `Close` from a closed task (store-restructure §3.3).
    """
    with database.transaction() as connection:
        try:
            updated = connection.execute(
                _SQL_UPDATE,
                (
                    state,
                    attempt,
                    expected_version + 1,
                    root_id,
                    brief,
                    record_json,
                    _now(),
                    task_id,
                    expected_version,
                ),
            )
        except sqlite3.Error as failure:
            raise sqlite_failure(
                failure, operation=LedgerOperation.RECORDING.value, row_id=task_id
            ) from failure
        if updated.rowcount == 0:
            found = connection.execute(_SQL_READ, (task_id,)).fetchone()
            if found is None:
                raise LedgerRecordConflict(
                    MSG_RECORD_MISSING.format(
                        task_id=task_id, operation=LedgerOperation.RECORDING.value
                    )
                )
            raise LedgerRecordConflict(
                MSG_RECORD_STALE.format(
                    task_id=task_id,
                    found=_row(found).version,
                    expected=expected_version,
                )
            )
        if inside is not None:
            inside(connection)
    return _required(database, task_id, LedgerOperation.RECORDING.value)


def set_state(database: LedgerDatabase, task_id: str, state: str) -> None:
    """Record how far the contractor got, without restating the carrier.

    The one write that moves `state` alone. It still bumps `version`, because
    a transition written against the record as it was before this is exactly
    the stale write the guard exists for.
    """
    with database.transaction() as connection:
        updated = connection.execute(_SQL_SET_STATE, (state, _now(), task_id))
        if updated.rowcount == 0:
            raise LedgerRecordConflict(
                MSG_RECORD_MISSING.format(
                    task_id=task_id, operation=LedgerOperation.ABANDONING.value
                )
            )


def states_of_epic(
    database: LedgerDatabase, epic_id: str
) -> tuple[tuple[str, str], ...]:
    """Every task of this epic that has a contractor record, with its state.

    What `_refuse_other_admission` asks instead of listing the tracker's
    children and reading their beads: the epic is `tasks.epic_id`, which was
    written at mint, so the question is answerable with the tracker gone.
    """
    with database.locked() as connection:
        rows = connection.execute(_SQL_BY_EPIC, (epic_id,)).fetchall()
    return tuple((str(row[0]), str(row[1])) for row in rows)


def by_root(database: LedgerDatabase, root_id: str) -> tuple[ContractorRecordRow, ...]:
    """Every record naming this attempt root — at most one, by construction.

    A tuple rather than an optional because more than one is an ambiguity the
    CALLER decides about, exactly as it did when this was a scan over every
    bead's metadata; what changed is that the answer is a lookup.
    """
    with database.locked() as connection:
        rows = connection.execute(_SQL_BY_ROOT, (root_id,)).fetchall()
    return tuple(_row(row) for row in rows)


def _required(
    database: LedgerDatabase, task_id: str, operation: str
) -> ContractorRecordRow:
    """Read back the row this call just wrote, refusing if it is not there."""
    found = read(database, task_id)
    if found is None:
        raise LedgerRecordConflict(
            MSG_RECORD_MISSING.format(task_id=task_id, operation=operation)
        )
    return found


def _row(row: sqlite3.Row) -> ContractorRecordRow:
    """One selected row as its typed shape."""
    return ContractorRecordRow(
        task_id=str(row[0]),
        state=str(row[1]),
        attempt=int(row[2]),
        version=int(row[3]),
        root_id=None if row[4] is None else str(row[4]),
        brief=None if row[5] is None else str(row[5]),
        record_json=str(row[6]),
    )


def _now() -> str:
    """The timestamp a record write is stamped with."""
    return datetime.now(tz=UTC).isoformat()
