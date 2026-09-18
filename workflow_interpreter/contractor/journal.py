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
deleted `.wf/` before the orchestrator has committed the file.
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
from workflow_interpreter.ledger.constants import EXPORT_REF_TEMPLATE
from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.ledger.export import write_export
from workflow_interpreter.ledger.tasks import pin_task_backend, record_export_oid

MSG_PIN_LOST: Final[str] = (
    "the export of {task_id!r} could not be pinned: {ref} names {found!r}, "
    "not the blob {oid!r} just written (run-ledger §3.6)"
)
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
        """Export, store, pin, record — and answer the blob's object id.

        The task row is ensured first, because a task whose roots are all in
        bd may never have been written here and still owes an export: §3.6
        makes the export the precondition of CLOSED for every contractor task, not
        only for ledger-backed ones. `pin_task_backend` is non-destructive, so
        a task that already named a backend keeps it.

        The export runs under the shared fence this connection already holds
        (§3.4.5), so it cannot publish a snapshot from before an exclusive
        restore. The ref is read back because `update-ref` succeeding is not
        the same fact as the ref naming this blob, and the oid must not reach
        the bead unless it does.
        """
        pin_task_backend(self._database, task_id, backend)
        path = write_export(self._database, task_id)
        oid = self._git.write_blob(path, cwd=self._repo_root)
        ref = EXPORT_REF_TEMPLATE.format(task_id=task_id)
        self._git.update_ref(ref, oid, cwd=self._repo_root)
        found = self._git.ref_target(ref, cwd=self._repo_root)
        if found != oid:
            raise ContractorRefusal(
                MSG_PIN_LOST.format(task_id=task_id, ref=ref, found=found, oid=oid)
            )
        record_export_oid(self._database, task_id, oid)
        return oid
