"""The contractor's record as a ledger row — S4's acceptance family (§3.2, R4).

What is proved here is the half of S4 that lives in the LEDGER: the record is a
row with a version guard, the state `closed()` gates on is folded into it, the
row is exported with its own emission branch and round-trips byte-identically,
`claims` is declared non-exported, and a v4 database with rows in it migrates
without losing them.

The half that lives in the CONTRACTOR — admission with the tracker gone, the
brief snapshot, `wf phase abandon`'s cleanup — is exercised through the
contractor lab in `test_cutover.py` and the adapter tests in `test_contractor.py`.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Final

import pytest

from tests._ledger import EPIC, TASK, repository, seed_contractor_record, seeded_task
from workflow_interpreter.ledger import records
from workflow_interpreter.ledger.constants import (
    EXPORT_TABLES,
    NON_EXPORTED,
    LedgerTable,
    TaskState,
)
from workflow_interpreter.ledger.database import LedgerDatabase, open_ledger
from workflow_interpreter.ledger.errors import LedgerRecordConflict
from workflow_interpreter.ledger.export import export_task
from workflow_interpreter.ledger.schema import MIGRATIONS, apply_migrations
from workflow_interpreter.ledger.tasks import task_state

_V4: Final[int] = 4
"""The version S3 left behind, which S4's fold migrates from."""
_CARRIER: Final[str] = json.dumps({"stage_id": TASK, "epic_id": EPIC})


@pytest.fixture
def ledger(tmp_path: Path) -> Iterator[LedgerDatabase]:
    """An open ledger over a fresh repository, closed with the test."""
    repo_root, wrapper_root = repository(tmp_path)
    with open_ledger(repo_root, wrapper_root) as database:
        yield database


# --- the version guard (§3.2) -----------------------------------------------


def test_a_transition_written_against_a_stale_version_is_refused_by_name(
    ledger: LedgerDatabase,
) -> None:
    """Bead metadata MERGED, so two writers composed silently; a row does not.

    The guard is what replaces the merge: a caller states the version it read,
    and a second transition written against that same version — after the
    first one moved the record — is refused rather than applied over a state
    it never saw.
    """
    seed_contractor_record(ledger, state="prepared")
    read = records.read(ledger, TASK)
    assert read is not None

    records.update(
        ledger,
        TASK,
        state="admitted",
        attempt=1,
        root_id="root-1",
        brief=None,
        record_json=_CARRIER,
        expected_version=read.version,
    )

    with pytest.raises(LedgerRecordConflict, match="version"):
        records.update(
            ledger,
            TASK,
            state="gate-red",
            attempt=1,
            root_id="root-1",
            brief=None,
            record_json=_CARRIER,
            expected_version=read.version,
        )
    moved = records.read(ledger, TASK)
    assert moved is not None
    assert (moved.state, moved.version) == ("admitted", read.version + 1)


def test_a_second_first_write_is_refused_rather_than_overwriting(
    ledger: LedgerDatabase,
) -> None:
    """ "This task has no record" and "its record is at n" are different claims."""
    seed_contractor_record(ledger, state="prepared")

    with pytest.raises(LedgerRecordConflict, match="already exists"):
        records.create(
            ledger,
            TASK,
            state="prepared",
            attempt=1,
            root_id=None,
            brief=None,
            record_json=_CARRIER,
        )


# --- the fold (§3.5) --------------------------------------------------------


def test_the_state_closure_gates_on_is_read_from_the_record(
    ledger: LedgerDatabase,
) -> None:
    """S2's `tasks.state` has ONE home now, and it is the record's."""
    seed_contractor_record(ledger, state="landed")

    assert task_state(ledger, TASK) is TaskState.LANDED


def test_an_in_flight_record_state_leaves_the_task_open(
    ledger: LedgerDatabase,
) -> None:
    """Only LANDED and ABANDONED are states closure derives from (§3.5)."""
    seed_contractor_record(ledger, state="admitted")

    assert task_state(ledger, TASK) is None


def test_the_tasks_table_no_longer_carries_a_state_column(
    ledger: LedgerDatabase,
) -> None:
    """The fold DROPPED the column; R12 leaves no second copy to read."""
    with ledger.locked() as connection:
        columns = {
            str(row[1]) for row in connection.execute("PRAGMA table_info(tasks)")
        }

    assert "state" not in columns


# --- the export (§3.6) ------------------------------------------------------


def test_the_record_is_exported_and_round_trips_byte_identically(
    ledger: LedgerDatabase,
) -> None:
    """D3: re-exporting the same rows is the same bytes, record included."""
    seeded_task(ledger)
    seed_contractor_record(ledger, state="landed", brief="the brief")

    first = export_task(ledger, TASK)
    second = export_task(ledger, TASK)

    assert first == second
    emitted = [json.loads(line) for line in first.decode().splitlines()]
    rows = [line for line in emitted if line.get("table") == "contractor_records"]
    assert len(rows) == 1
    assert rows[0]["row"]["brief"] == "the brief"
    # Directly after the `tasks` row it references: an import inserts in
    # emission order, and a record cannot precede its task.
    assert emitted[1]["table"] == LedgerTable.TASKS.value
    assert emitted[2]["table"] == LedgerTable.CONTRACTOR_RECORDS.value


def test_claims_are_declared_non_exported_with_a_stated_reason() -> None:
    """R5's completeness rule: every table is in one set or the other."""
    assert LedgerTable.CLAIMS not in EXPORT_TABLES
    assert LedgerTable.CLAIMS in NON_EXPORTED
    assert "R11" in NON_EXPORTED[LedgerTable.CLAIMS]


# --- the migration ----------------------------------------------------------


def test_a_v4_database_with_rows_migrates_without_losing_them(
    tmp_path: Path,
) -> None:
    """The fold runs on a ledger that already holds work, not only a fresh one.

    A `tasks` row written while the column still existed survives it, and the
    two new tables exist afterwards — which is the whole of what a
    forward-only migration owes the database it is handed. Nothing is carried
    ACROSS: R12's clean break means no live ledger holds a state a rebuilt
    record would have to inherit.
    """
    path = tmp_path / "v4.db"
    with closing(sqlite3.connect(path)) as connection:
        for statements in MIGRATIONS[:_V4]:
            for statement in statements:
                connection.execute(statement)
        connection.execute(
            "INSERT INTO tasks (task_id, epic_id, backend, next_seq, created_at, "
            "state) VALUES (?, ?, ?, ?, ?, ?)",
            (TASK, EPIC, "ledger", 1, "2026-01-01T00:00:00Z", "landed"),
        )
        connection.commit()

        reached = apply_migrations(connection, _V4)

        assert reached == len(MIGRATIONS)
        assert connection.execute("SELECT task_id FROM tasks").fetchall() == [(TASK,)]
        assert connection.execute("SELECT COUNT(*) FROM claims").fetchone() == (0,)
        assert connection.execute(
            "SELECT COUNT(*) FROM contractor_records"
        ).fetchone() == (0,)
