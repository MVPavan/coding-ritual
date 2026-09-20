"""Where the contractor's record lives, and what a transition states about it.

The record moved out of bead metadata in S4 (§3.2, R4). What made that
necessary is admission: it must run with the tracker unreachable, and a record
only the tracker held could not be read, let alone advanced. What makes it
SAFE is the version guard — bead metadata was merged, so two writers silently
composed; a row is transitioned, so the second one is refused by name.

The contractor depends on this surface rather than on a database, the way it
depends on `ClosureProbe` rather than on a ledger: the adapter owns the record
and must not open a connection of its own.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, Protocol

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.contractor.models import ContractorRecord
from workflow_interpreter.ledger import records as rows
from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.ledger.tasks import pin_task_backend

if TYPE_CHECKING:
    from workflow_interpreter.foreman.compose import Composition

MSG_NO_RECORD_STORE: Final[str] = (
    "this wiring has no contractor record store: the record is a ledger row "
    "since S4, and a composition with no ledger cannot prepare, admit, land "
    "or abandon a task (store-restructure §3.2, R4)"
)


class RecordStoreUnavailable(RuntimeError):
    """A contractor write was attempted with nowhere durable to write it."""


class StoredRecord(BaseModel):
    """One stored record, with the version a transition must state."""

    model_config = ConfigDict(frozen=True)

    record: ContractorRecord
    version: int
    brief: str | None


class ContractorRecords(Protocol):
    """Read the stored record, write the first one, or move it forward."""

    def read(self, task_id: str) -> StoredRecord | None:
        """The stored record of this task, or nothing while it has none."""
        ...

    def create(self, record: ContractorRecord, *, brief: str | None) -> StoredRecord:
        """Write a task's first record, refusing a second first write."""
        ...

    def update(
        self, record: ContractorRecord, *, expected_version: int, brief: str | None
    ) -> StoredRecord:
        """Move the record forward from exactly the version the caller read."""
        ...

    def states_of_epic(self, epic_id: str) -> tuple[tuple[str, str], ...]:
        """Every task of this epic with a record, and that record's state."""
        ...


class LedgerContractorRecords:
    """The ledger's `contractor_records` table, as the contractor sees it.

    The `tasks` row is ensured before the first record is written, because
    `contractor_records.task_id` references it and a task whose roots are
    bd-backed may never have been written here. `pin_task_backend` is
    non-destructive, so a task that already names a backend keeps it (D18).
    """

    def __init__(self, database: LedgerDatabase, *, backend: BackendKind) -> None:
        self._database = database
        self._backend = backend

    def read(self, task_id: str) -> StoredRecord | None:
        """The stored record of this task, or nothing while it has none."""
        row = rows.read(self._database, task_id)
        return None if row is None else _stored(row)

    def create(self, record: ContractorRecord, *, brief: str | None) -> StoredRecord:
        """Write a task's first record, refusing a second first write."""
        pin_task_backend(self._database, record.stage_id, self._backend, record.epic_id)
        return _stored(
            rows.create(
                self._database,
                record.stage_id,
                state=record.state.value,
                attempt=record.attempt,
                root_id=record.root_id,
                brief=brief,
                record_json=record.model_dump_json(by_alias=True),
            )
        )

    def update(
        self, record: ContractorRecord, *, expected_version: int, brief: str | None
    ) -> StoredRecord:
        """Move the record forward from exactly the version the caller read."""
        return _stored(
            rows.update(
                self._database,
                record.stage_id,
                state=record.state.value,
                attempt=record.attempt,
                root_id=record.root_id,
                brief=brief,
                record_json=record.model_dump_json(by_alias=True),
                expected_version=expected_version,
            )
        )

    def states_of_epic(self, epic_id: str) -> tuple[tuple[str, str], ...]:
        """Every task of this epic with a record, and that record's state."""
        return rows.states_of_epic(self._database, epic_id)


class NoContractorRecords:
    """The answer for a composition with no ledger at all.

    A named refusal rather than an absent store, for `NoLedgerClosure`'s
    reason: a read-only view (`wf contract --trace`, the gate view) has to be
    able to say "no record here", while every WRITE has to say why it cannot
    happen instead of quietly not happening.
    """

    def read(self, task_id: str) -> StoredRecord | None:
        """Nothing: a wiring with no ledger holds no record."""
        return None

    def create(self, record: ContractorRecord, *, brief: str | None) -> StoredRecord:
        """Refuse: there is nowhere durable for a first record to go."""
        raise RecordStoreUnavailable(MSG_NO_RECORD_STORE)

    def update(
        self, record: ContractorRecord, *, expected_version: int, brief: str | None
    ) -> StoredRecord:
        """Refuse: there is nothing here to move forward."""
        raise RecordStoreUnavailable(MSG_NO_RECORD_STORE)

    def states_of_epic(self, epic_id: str) -> tuple[tuple[str, str], ...]:
        """Nothing: a wiring with no ledger holds no records to list."""
        return ()


def contractor_records(
    database: LedgerDatabase | None, *, backend: BackendKind
) -> ContractorRecords:
    """The record store for a composition whose ledger is optional.

    One definition, for `closure_probe`'s reason: every construction site of
    `ContractorAdapter` supplies one, and a second copy of "ledger or not"
    would be a second chance to get the ledger-less case wrong.
    """
    return (
        NoContractorRecords()
        if database is None
        else LedgerContractorRecords(database, backend=backend)
    )


def _stored(row: rows.ContractorRecordRow) -> StoredRecord:
    """One ledger row as the record and the version that guards it."""
    return StoredRecord(
        record=ContractorRecord.model_validate_json(row.record_json),
        version=row.version,
        brief=row.brief,
    )


def records_of(composition: Composition) -> ContractorRecords:
    """The record store of one composition, named once for every caller.

    Six construction sites build a `ContractorAdapter`, and each of them has a
    composition and nothing else in common. A second spelling of "which ledger
    and which backend" is a second chance for one of them to build a store
    that writes somewhere the rest do not read.
    """
    return contractor_records(composition.ledger, backend=composition.config.store)
