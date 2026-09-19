"""The contractor's two ledger writes: the landing journal and the export pin.

Both exist because the wrapper directory is disposable and the working tree is
`git clean`-able, and both are therefore ordered rather than merely present.

**Landing journal (D17).** The intent file, then its row, before the CAS; the
receipt file, then its row, after. Recovery reads the FILE first — it is what
every existing recovery path revalidates — falls back to the row when the file
is gone, and refuses when both are missing. `UNIQUE(task_id, attempt, phase)`
is what makes the fallback unambiguous.

**Export pin (§3.6).** A task's whole record goes into git BEFORE its bead can
close: the export file is written, the same bytes are stored as a blob, the
blob is pinned under `refs/wf/exports/<task>`, and only then does the oid reach
`tasks.export_oid` and the contractor record. The export therefore survives a
deleted `.wf/` before the orchestrator has committed the file. The storing and
pinning half lives in `ledger.export.pin_export`, because `wf ledger
pin-export` recovers a crash between the two and must pin exactly what this
does.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ValidationError

from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.contractor.errors import ContractorRefusal
from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.ledger.closure import TaskClosure
from workflow_interpreter.ledger.constants import TaskState
from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.ledger.errors import LedgerExportError
from workflow_interpreter.ledger.export import pin_export, write_export
from workflow_interpreter.ledger.tasks import pin_task_backend, record_task_state

MSG_UNREADABLE_ROW: Final[str] = (
    "the journalled {phase} of attempt {attempt} of {task_id!r} is unreadable: {reason}"
)

_SQL_WRITE: Final[str] = (
    "INSERT INTO landings (task_id, attempt, phase, record_json, written_at) "
    "VALUES (?, ?, ?, ?, ?) "
    "ON CONFLICT(task_id, attempt, phase) DO UPDATE SET "
    "record_json = excluded.record_json, written_at = excluded.written_at"
)
_SQL_READ: Final[str] = (
    "SELECT record_json FROM landings WHERE task_id = ? AND attempt = ? AND phase = ?"
)


class LandingPhase(StrEnum):
    """The two journalled halves of one landing (§3.3 `landings.phase`)."""

    INTENT = "intent"
    RECEIPT = "receipt"


class LandingJournal:
    """One task's copy of its landing intent and receipt, in the ledger."""

    def __init__(
        self, database: LedgerDatabase, task_id: str, backend: BackendKind
    ) -> None:
        self._database = database
        self._task_id = task_id
        self._backend = backend

    def record(self, attempt: int, phase: LandingPhase, record: BaseModel) -> None:
        """Copy one landing half into the ledger, after its file was written.

        The task row is ensured first because `landings.task_id` references
        it: a bd-backed task may never have been written here, and D17 copies
        its landing all the same. `pin_task_backend` is non-destructive.

        Upsert rather than insert: a repeated landing attempt writes the same
        file over itself (`_write_intent`), and a journal that refused the
        second write would make the file and the row disagree about which
        attempt is current.
        """
        pin_task_backend(self._database, self._task_id, self._backend)
        with self._database.transaction():
            self._database.connection.execute(
                _SQL_WRITE,
                (
                    self._task_id,
                    attempt,
                    phase.value,
                    record.model_dump_json(),
                    datetime.now(tz=UTC).isoformat(),
                ),
            )

    def read[RecordT: BaseModel](
        self, attempt: int, phase: LandingPhase, model: type[RecordT]
    ) -> RecordT | None:
        """The journalled half, or nothing when this ledger never held it.

        A row that exists and does not parse is a REFUSAL, not a miss: falling
        through to "both are missing" would let an unreadable journal look
        like an unjournalled one, and those need different answers.
        """
        with self._database.locked() as connection:
            row = connection.execute(
                _SQL_READ, (self._task_id, attempt, phase.value)
            ).fetchone()
        if row is None:
            return None
        try:
            return model.model_validate_json(str(row[0]))
        except ValidationError as invalid:
            raise ContractorRefusal(
                MSG_UNREADABLE_ROW.format(
                    phase=phase.value,
                    attempt=attempt,
                    task_id=self._task_id,
                    reason=invalid,
                )
            ) from invalid


class ExportPin:
    """Puts a task's whole ledger record into git before its bead can close."""

    def __init__(self, database: LedgerDatabase, git: Git, repo_root: Path) -> None:
        self._database = database
        self._git = git
        self._repo_root = repo_root

    def pin(self, task_id: str, backend: BackendKind) -> str:
        """Record LANDED, export, store, pin — and answer the blob's object id.

        The task row is ensured first, because a task whose roots are all in
        bd may never have been written here and still owes an export: §3.6
        makes the export the precondition of closure for every contractor
        task, not only for ledger-backed ones. `pin_task_backend` is
        non-destructive, so a task that already named a backend keeps it.

        LANDED is recorded BEFORE the bytes are written, unlike the pin, and
        the order is the point (§3.5): the export has to carry the state, or a
        ledger rebuilt in a clone could never derive closure at all. The pin
        itself is elided from those bytes for the opposite reason.

        The export runs under the shared fence this connection already holds
        (§3.4.5), so it cannot publish a snapshot from before an exclusive
        restore. Storing and pinning the bytes is `ledger.pin_export`, shared
        with `wf ledger pin-export`: one definition of what a pin IS, so the
        recovery command cannot drift from the write it recovers.
        """
        pin_task_backend(self._database, task_id, backend)
        record_task_state(self._database, task_id, TaskState.LANDED)
        write_export(self._database, task_id)
        try:
            return pin_export(self._git, self._database, task_id, self._repo_root)
        except LedgerExportError as lost:
            # A pin the CONTRACTOR could not complete is a refusal of the
            # contractor's own operation, not a defect in the ledger: the
            # shared function states what went wrong, and this states whose
            # step it was, so the close still exits as a refusal (D5).
            raise ContractorRefusal(str(lost)) from lost

    @property
    def closure(self) -> TaskClosure:
        """The closure probe over the same ledger and checkout this pin writes.

        The landing composes it into the adapter, which is where the close is
        refused for a task whose record is not durable yet (§3.5, D5): the
        evidence and the write that depends on it must come from one place.
        """
        return TaskClosure(self._database, self._git)
