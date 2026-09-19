"""One task's rows out to a tracked JSONL file, and back in again (§3.6).

The export is the durable record a task is closable against, so it is written
under ONE read transaction while the shared fence is held: it can never publish
a snapshot from the middle of an exclusive restore. The import is the mirror —
every selected file parsed and validated first, then ONE exclusive fence and
ONE transaction that clears every exportable table and refills it from the
files. A rebuild is therefore a rebuild and not an append: a task the export
set does not describe does not survive it, no reader can enter between two
files, and any failure rolls the whole restore back.

Order is `(task_id, seq)`, the per-task sequence every row is given inside the
transaction that wrote it, which is what makes the round trip byte-identical:
the same rows come back out in the same order with the same canonical JSON,
with no exception — the attention drain a restore owes every task it brings
back is recorded outside the exportable state (`_record_restore`).
"""

from __future__ import annotations

import base64
import binascii
import json
import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import structlog
from pydantic import BaseModel, ConfigDict, JsonValue

from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.ledger.constants import (
    DERIVED_ACTIVATION_TABLES,
    ELIDED_TASK_COLUMNS,
    EXPORT_KIND_HEADER,
    EXPORT_KIND_ROW,
    EXPORT_REF_TEMPLATE,
    EXPORT_TABLES,
    GATE_TABLES,
    MSG_EXPORT_BLOB,
    MSG_EXPORT_COLUMN,
    MSG_EXPORT_GATE_TASK,
    MSG_EXPORT_HEADER,
    MSG_EXPORT_REPO_ID_MISMATCH,
    MSG_EXPORT_ROW_KIND,
    MSG_EXPORT_TABLE,
    MSG_EXPORT_TASK_MISMATCH,
    MSG_EXPORT_TASK_ROWS,
    MSG_PIN_LOST,
    MSG_PIN_NO_FILE,
    MSG_PIN_NOT_LANDED,
    MSG_PIN_STALE,
    MSG_PIN_TASK_MISMATCH,
    MSG_REPO_ID_ABSENT,
    MSG_UNKNOWN_TASK,
    ROW_TABLES,
    ExportKey,
    LedgerTable,
    MetaKey,
    TaskState,
)
from workflow_interpreter.ledger.database import (
    LedgerDatabase,
    assert_identity,
    connect,
    read_meta,
    schema_version,
    standalone_transaction,
)
from workflow_interpreter.ledger.errors import (
    LedgerExportError,
    LedgerIdentityError,
    LedgerSchemaError,
    LedgerTransportError,
)
from workflow_interpreter.ledger.fence import LedgerFence
from workflow_interpreter.ledger.paths import (
    export_path,
    fence_path,
    read_repo_id,
    repo_id_relpath,
)
from workflow_interpreter.ledger.schema import table_columns
from workflow_interpreter.ledger.store import rebuild_findings
from workflow_interpreter.ledger.tasks import record_export_oid, task_state
from workflow_interpreter.schema.loader import canonical_json_bytes

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

_SQL_TASK: Final[str] = "SELECT * FROM tasks WHERE task_id = ?"
_SQL_GATE_ROWS: Final[str] = (
    "SELECT {table}.* FROM {table} JOIN gates ON {table}.gate_id = gates.gate_id "
    "WHERE gates.task_id = ? ORDER BY gates.seq, {table}.gate_id"
)
"""A nonce and a signature belong to the task their GATE belongs to; they carry
no `task_id` of their own, so the join is what scopes them (§3.3)."""
_SQL_PROJECTIONS: Final[str] = (
    "SELECT * FROM projections WHERE task_id = ? ORDER BY generation"
)
_SQL_RESTORE_PENDING: Final[str] = (
    "INSERT INTO restore_pending (task_id, requested_at) VALUES (?, ?)"
)
_SQL_CLEAR_RESTORES: Final[str] = "DELETE FROM restore_pending"
_SQL_LANDINGS: Final[str] = (
    f"SELECT * FROM {LedgerTable.LANDINGS.value} WHERE task_id = ? "
    "ORDER BY attempt, phase"
)
_GATE_COLUMN: Final[str] = "gate_id"
_BLOB_KEY: Final[str] = "base64"
"""A signature's payload and bytes are BLOBs, and JSON has no bytes. They
travel as a single-key object rather than as bare text, so a decoder can tell a
restored BLOB from a column that really is a string (§3.6)."""
_SEQ_COLUMN: Final[str] = "seq"
_TASK_COLUMN: Final[str] = "task_id"
_ONE_TASK_ROW: Final[int] = 1
_SECOND_LINE: Final[int] = 2
_NEWLINE: Final[bytes] = b"\n"

ExportLine = dict[str, JsonValue]
ExportRow = dict[str, JsonValue]
NumberedRow = tuple[int, LedgerTable, ExportRow]


class ParsedExport(BaseModel):
    """One export file, validated whole before any fence is taken (§3.6)."""

    model_config = ConfigDict(frozen=True)

    path: Path
    task_id: str
    header: ExportLine
    rows: tuple[tuple[LedgerTable, ExportRow], ...]


def export_task(database: LedgerDatabase, task_id: str) -> bytes:
    """Every row of one task as export bytes, read under one snapshot (§3.6).

    Returns the bytes rather than writing them: file I/O inside a transaction
    is forbidden (§3.4.2), and the caller decides whether they go to `.wf/
    export/`, to a git blob, or to both.
    """
    with database.transaction(write=False) as connection:
        task = connection.execute(_SQL_TASK, (task_id,)).fetchone()
        if task is None:
            raise LedgerTransportError(MSG_UNKNOWN_TASK.format(task_id=task_id))
        header: ExportLine = {
            ExportKey.KIND.value: EXPORT_KIND_HEADER,
            ExportKey.SCHEMA_VERSION.value: schema_version(connection),
            ExportKey.REPO_ID.value: read_meta(connection, MetaKey.REPO_ID),
            ExportKey.TASK_ID.value: task_id,
        }
        lines = [header, _line(LedgerTable.TASKS, task, elide=ELIDED_TASK_COLUMNS)]
        # Directly after the `tasks` row it hangs off, and before everything
        # keyed by a root: `landings` has no per-task `seq` of its own, so it
        # cannot ride the `(seq, table)` emission below (§3.6).
        lines += [
            _line(table, row) for table, row in _landing_rows(connection, task_id)
        ]
        lines += [
            _line(table, row) for table, row in _ordered_rows(connection, task_id)
        ]
        # After the rows they hang off, because that is the order an import
        # inserts them in and a signature cannot precede its gate (§3.3 FKs).
        lines += [
            _line(table, row) for table, row in _auxiliary_rows(connection, task_id)
        ]
    return b"".join(canonical_json_bytes(line) + _NEWLINE for line in lines)


def write_export(database: LedgerDatabase, task_id: str) -> Path:
    """Write `<repo>/.wf/export/<task>.jsonl`, overwriting, never appending."""
    payload = export_task(database, task_id)
    path = export_path(database.repo_root, task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    _LOG.info("wf.ledger.exported", task_id=task_id, path=str(path), bytes=len(payload))
    return path


def pin_export(
    git: Git, database: LedgerDatabase, task_id: str, repo_root: Path
) -> str:
    """Pin the export ON DISK under `refs/wf/exports/<task>` and record its oid.

    The bytes already written, never a fresh export: this is the recovery for
    a crash between `write_export` and the pin (§3.6, `wf ledger pin-export`),
    and re-exporting would pin a ledger that has moved on since the file was
    written — a different blob from the one the operator is holding.

    Which is exactly why the file is CHECKED against a fresh export before it
    is pinned. A pin is the claim "this blob is what the ledger says about this
    task", and a file written before the ledger moved on is no longer that
    claim: it would be recorded on a `tasks` row that can never re-export it,
    and the next close would refuse a task whose pin its own bytes contradict.
    Equality is the only state in which re-pinning the operator's file and
    re-exporting would agree, so equality is the only state that pins.

    Four refusals come before the blob is written, each naming its own defect:
    the task must have a `tasks` row (`export_task`), the file must be an
    export of THIS task, the task must have LANDED, and its bytes must be the
    current ones.

    LANDED is the other end of the closure latch (§3.5). This command exists
    for the operator, so it can be aimed at any task at all; a pin recorded on
    a task still in flight would be read as closure the moment anything asked
    `closed()`, and that task's landing would then skip both `adapter.land`
    and the pin it is supposed to recover.

    The ref is read back because `update-ref` succeeding is not the same fact
    as the ref naming this blob, and the oid must not be recorded unless it
    does.
    """
    path = export_path(repo_root, task_id)
    if not path.is_file():
        raise LedgerExportError(MSG_PIN_NO_FILE.format(path=path, task_id=task_id))
    # Before the header check, so a task with no rows at all is refused as the
    # unknown task it is rather than as a file that disagrees with the ledger.
    current = export_task(database, task_id)
    _assert_pins_this_task(path, task_id)
    state = task_state(database, task_id)
    if state is not TaskState.LANDED:
        raise LedgerExportError(
            MSG_PIN_NOT_LANDED.format(
                task_id=task_id, state="nothing" if state is None else state.value
            )
        )
    if path.read_bytes() != current:
        raise LedgerExportError(MSG_PIN_STALE.format(path=path, task_id=task_id))
    oid = git.write_blob(path, cwd=repo_root)
    ref = EXPORT_REF_TEMPLATE.format(task_id=task_id)
    git.update_ref(ref, oid, cwd=repo_root)
    found = git.ref_target(ref, cwd=repo_root)
    if found != oid:
        raise LedgerExportError(
            MSG_PIN_LOST.format(task_id=task_id, ref=ref, found=found, oid=oid)
        )
    record_export_oid(database, task_id, oid)
    _LOG.info("wf.ledger.pinned", task_id=task_id, ref=ref, oid=oid)
    return oid


def import_export(
    path: Path,
    *,
    repo_root: Path,
    wrapper_root: Path,
    ledger: Path,
    fence: LedgerFence | None = None,
) -> str:
    """Rebuild the ledger's exportable rows from ONE export file."""
    return import_exports(
        (path,),
        repo_root=repo_root,
        wrapper_root=wrapper_root,
        ledger=ledger,
        fence=fence,
    )[0]


def import_exports(
    paths: Sequence[Path],
    *,
    repo_root: Path,
    wrapper_root: Path,
    ledger: Path,
    fence: LedgerFence | None = None,
) -> tuple[str, ...]:
    """Rebuild every exportable row from these exports, atomically (§3.6).

    Three properties, and each one is a step of this order: every file is
    parsed and validated BEFORE the fence, so a malformed set never reaches
    SQL; the fence is taken ONCE, so no reader can enter between two files; and
    every exportable table is CLEARED inside the single transaction that
    refills it, so the ledger ends up carrying exactly what the export set
    describes and a failure anywhere leaves it as it was. The derived
    per-activation tables are rebuilt in that transaction too, from the
    restored carriers (`rebuild_findings`).

    The landing journal rides along: `landings` is exported now (§3.6), so a
    landed ledger is rebuilt rather than refused whole, and D17's fallback
    still has a row to read afterwards.
    """
    repo_id = read_repo_id(repo_root)
    if repo_id is None:
        raise LedgerIdentityError(
            MSG_REPO_ID_ABSENT.format(repo_root=repo_root, relpath=repo_id_relpath())
        )
    parsed = tuple(_parse(path, repo_id=repo_id) for path in paths)
    taken = LedgerFence(fence_path(repo_root)) if fence is None else fence
    with taken.exclusive(), closing(connect(ledger)) as connection:
        for export in parsed:
            _assert_schema(connection, export.path, export.header)
        # The DESTINATION's pins, not only the files' headers: a ledger this
        # process may not write is refused here, inside the exclusive section
        # and before a single row is deleted (§3.5).
        assert_identity(
            connection,
            path=ledger,
            repo_id=repo_id,
            repo_root=repo_root,
            wrapper_root=wrapper_root,
        )
        with standalone_transaction(connection):
            _clear(connection)
            for export in parsed:
                for table, row in export.rows:
                    _insert(connection, table, row, path=export.path)
            for export in parsed:
                # The derived per-activation projections `_clear` emptied, back
                # from the carriers this rebuild just inserted and inside the
                # same transaction: `findings` is derivable state, and a
                # restored ledger that answered §3.3 with nothing until the
                # next close would be a silent loss (found in review).
                rebuild_findings(connection, export.task_id)
                _record_restore(connection, export.task_id)
    for export in parsed:
        _LOG.info("wf.ledger.imported", task_id=export.task_id, path=str(export.path))
    return tuple(export.task_id for export in parsed)


def _assert_pins_this_task(path: Path, task_id: str) -> None:
    """Refuse to pin a file that is not an export of THIS task (§3.6).

    Read from the file's own header rather than inferred from its name: the
    oid is recorded on the `tasks` row of `task_id`, so a file describing some
    other task would make that row point at a blob it does not describe — and
    the operator would learn it only when a rebuild restored the wrong task.
    """
    header = _read_lines(path)[0]
    if header.get(ExportKey.KIND.value) != EXPORT_KIND_HEADER:
        raise LedgerExportError(
            MSG_EXPORT_HEADER.format(path=path, kind=EXPORT_KIND_HEADER)
        )
    declared = header.get(ExportKey.TASK_ID.value)
    if declared != task_id:
        raise LedgerExportError(
            MSG_PIN_TASK_MISMATCH.format(path=path, declared=declared, task_id=task_id)
        )


def _record_restore(connection: sqlite3.Connection, task_id: str) -> None:
    """Owe one attention drain for a restored task, in the restoring transaction.

    An import REPLACES the destination ledger rather than merging into it, so
    the label on the task bead was written from state this rebuild discarded —
    including state no export file describes — and EVERY restored task owes the
    one drain that re-derives it (§3.2), whatever its projection history says.

    The row goes in `restore_pending`, which no export carries and no import
    reads: a journalled `projections` row would spend a sequence number and
    break §3.6's byte-identical round trip. The reconciler drains it exactly as
    it drains an unacked generation, and a task that owes both is drained once.
    """
    connection.execute(
        _SQL_RESTORE_PENDING, (task_id, datetime.now(tz=UTC).isoformat())
    )


def _parse(path: Path, *, repo_id: str) -> ParsedExport:
    """One export file as validated lines, or a refusal naming the bad one."""
    lines = _read_lines(path)
    header = lines[0]
    if header.get(ExportKey.KIND.value) != EXPORT_KIND_HEADER:
        raise LedgerIdentityError(
            MSG_EXPORT_HEADER.format(path=path, kind=EXPORT_KIND_HEADER)
        )
    _assert_header(header, path=path, repo_id=repo_id)
    numbered = tuple(
        (number, *_row(line, path=path, number=number))
        for number, line in enumerate(lines[1:], start=_SECOND_LINE)
    )
    task_id = str(header[ExportKey.TASK_ID.value])
    _assert_task(numbered, path=path, task_id=task_id)
    return ParsedExport(
        path=path,
        task_id=task_id,
        header=header,
        rows=tuple((table, row) for _, table, row in numbered),
    )


def _assert_task(rows: Sequence[NumberedRow], *, path: Path, task_id: str) -> None:
    """Prove a file's rows are the one task its header declares (§3.6).

    The header is what an import REPORTS as restored, and it is read
    independently of the rows: without this, a file headed task A could refill
    the cleared ledger with task B's rows — or with none at all — and the
    whole-state rebuild would still report a successful restore of A.
    """
    declared = [entry for entry in rows if entry[1] is LedgerTable.TASKS]
    if len(declared) != _ONE_TASK_ROW:
        raise LedgerExportError(
            MSG_EXPORT_TASK_ROWS.format(
                path=path,
                task_id=task_id,
                count=len(declared),
                table=LedgerTable.TASKS.value,
            )
        )
    gates = {
        row.get(_GATE_COLUMN)
        for _number, table, row in rows
        if table is LedgerTable.GATES
    }
    for number, table, row in rows:
        if table in GATE_TABLES:
            # A nonce and a signature carry no `task_id`: they are the task's
            # exactly when their gate is, and the gate must be in THIS file.
            gate = row.get(_GATE_COLUMN)
            if gate not in gates:
                raise LedgerExportError(
                    MSG_EXPORT_GATE_TASK.format(
                        path=path,
                        number=number,
                        table=table.value,
                        gate_id=gate,
                        declared=task_id,
                    )
                )
            continue
        # Every other exportable table carries `task_id`, the `tasks` row as
        # its key.
        found = row.get(_TASK_COLUMN)
        if found != task_id:
            raise LedgerExportError(
                MSG_EXPORT_TASK_MISMATCH.format(
                    path=path, number=number, found=found, declared=task_id
                )
            )


def _row(
    line: Mapping[str, JsonValue], *, path: Path, number: int
) -> tuple[LedgerTable, ExportRow]:
    """One export line as the table and columns it may be inserted into.

    Untrusted text: the table name and every column name are interpolated into
    the INSERT (SQLite binds neither), so both are checked against the schema
    this build creates before any statement exists to run.
    """
    row = line.get(ExportKey.ROW.value)
    if line.get(ExportKey.KIND.value) != EXPORT_KIND_ROW or not isinstance(row, dict):
        raise LedgerExportError(
            MSG_EXPORT_ROW_KIND.format(path=path, number=number, kind=EXPORT_KIND_ROW)
        )
    named = line.get(ExportKey.TABLE.value)
    table = next(
        (candidate for candidate in EXPORT_TABLES if candidate.value == named), None
    )
    if table is None:
        raise LedgerExportError(
            MSG_EXPORT_TABLE.format(path=path, number=number, table=named)
        )
    allowed = table_columns()[table.value]
    for column in row:
        if column not in allowed:
            raise LedgerExportError(
                MSG_EXPORT_COLUMN.format(
                    path=path, number=number, table=table.value, column=column
                )
            )
    return table, dict(row)


def _assert_header(
    header: Mapping[str, JsonValue], *, path: Path, repo_id: str
) -> None:
    """Refuse an export written for another repository (§3.6).

    The repository, and nothing about the machine: `repo_id` is committed with
    the export, so a clone at any path reads it as its own, and the wrapper
    root the exporting checkout happened to use is not the importing
    checkout's business (it is still pinned on the DATABASE).
    """
    pinned_repo = header.get(ExportKey.REPO_ID.value)
    if pinned_repo != repo_id:
        raise LedgerIdentityError(
            MSG_EXPORT_REPO_ID_MISMATCH.format(
                path=path, pinned=pinned_repo, found=repo_id
            )
        )


def _assert_schema(
    connection: sqlite3.Connection, path: Path, header: Mapping[str, JsonValue]
) -> None:
    """Refuse an export from a schema this database is not at."""
    found = schema_version(connection)
    declared = header.get(ExportKey.SCHEMA_VERSION.value)
    if declared != found:
        raise LedgerSchemaError(
            f"{path} was exported from schema version {declared}, and this "
            f"ledger is at {found}; migrate before importing (§3.3)"
        )


def _read_lines(path: Path) -> list[ExportLine]:
    """Every line of an export as its JSON object, header first."""
    text = path.read_text(encoding="utf-8").splitlines()
    if not text:
        raise LedgerIdentityError(
            MSG_EXPORT_HEADER.format(path=path, kind=EXPORT_KIND_HEADER)
        )
    lines: list[ExportLine] = []
    for line in text:
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise LedgerIdentityError(
                MSG_EXPORT_HEADER.format(path=path, kind=EXPORT_KIND_HEADER)
            )
        lines.append(parsed)
    return lines


def _line(
    table: LedgerTable, row: sqlite3.Row, *, elide: frozenset[str] = frozenset()
) -> ExportLine:
    """One database row as its export line, without the elided columns.

    `elide` is how §3.6's "facts about the task, never about the file" is
    enforced: the `tasks` row drops the pin it was exported as, which is
    written after these bytes exist and could therefore never be in them.
    """
    return {
        ExportKey.KIND.value: EXPORT_KIND_ROW,
        ExportKey.TABLE.value: table.value,
        # `sqlite3.Row` iterates VALUES, so the column names come from `keys()`.
        ExportKey.ROW.value: {
            name: _encoded(value)
            for name, value in zip(row.keys(), tuple(row), strict=True)
            if name not in elide
        },
    }


def _encoded(value: object) -> JsonValue:
    """One stored value as JSON — a BLOB as its base64 carrier."""
    if isinstance(value, bytes):
        return {_BLOB_KEY: base64.b64encode(value).decode("ascii")}
    parsed: JsonValue = value  # type: ignore[assignment]
    return parsed


def _decoded(value: JsonValue, *, path: Path, column: str) -> object:
    """One exported value back as what the column holds, BLOBs included.

    Untrusted text: a carrier that does not decode is refused with the file and
    the column that carried it, never handed to SQLite as a string that would
    silently land in a BLOB column.
    """
    if not isinstance(value, dict) or set(value) != {_BLOB_KEY}:
        return value
    encoded = value[_BLOB_KEY]
    try:
        return base64.b64decode(str(encoded), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise LedgerExportError(
            MSG_EXPORT_BLOB.format(path=path, column=column, reason=exc)
        ) from exc


def _ordered_rows(
    connection: sqlite3.Connection, task_id: str
) -> Iterator[tuple[LedgerTable, sqlite3.Row]]:
    """Every row-table row of the task, in `(task_id, seq)` order."""
    collected: list[tuple[int, str, LedgerTable, sqlite3.Row]] = []
    for table in ROW_TABLES:
        statement = f"SELECT * FROM {table.value} WHERE task_id = ?"
        for row in connection.execute(statement, (task_id,)).fetchall():
            collected.append((int(row[_SEQ_COLUMN]), table.value, table, row))
    for _, _, table, row in sorted(collected, key=lambda item: (item[0], item[1])):
        yield table, row


def _landing_rows(
    connection: sqlite3.Connection, task_id: str
) -> Iterator[tuple[LedgerTable, sqlite3.Row]]:
    """The task's landing journal, in `(attempt, phase)` order (§3.6).

    Its own emission branch because `landings` has no `seq` — it is written by
    `contractor/journal.py`, outside the row seam that mints one — so the
    `(seq, table)` order the row tables are emitted in has nothing to sort it
    by. `(attempt, phase)` is the table's own UNIQUE key, which is
    deterministic, which is what keeps the round trip byte-identical.
    """
    for row in connection.execute(_SQL_LANDINGS, (task_id,)).fetchall():
        yield LedgerTable.LANDINGS, row


def _auxiliary_rows(
    connection: sqlite3.Connection, task_id: str
) -> Iterator[tuple[LedgerTable, sqlite3.Row]]:
    """The task's nonces, signatures and projections, in a durable order.

    They have no per-task `seq` of their own — they are facts ABOUT a gate or
    about the task — so each is ordered by the key that identifies it: a gate's
    own `seq` for the two gate-keyed tables, and the generation for a
    projection. Deterministic, which is what keeps the round trip byte-identical.
    """
    for table in GATE_TABLES:
        statement = _SQL_GATE_ROWS.format(table=table.value)
        for row in connection.execute(statement, (task_id,)).fetchall():
            yield table, row
    for row in connection.execute(_SQL_PROJECTIONS, (task_id,)).fetchall():
        yield LedgerTable.PROJECTIONS, row


def _clear(connection: sqlite3.Connection) -> None:
    """Empty every exportable table, children before parents, so the FKs hold.

    The whole state and not one task's rows: the export set IS the ledger after
    an import, so a task no file describes must not survive it (§3.6).

    `restore_pending` is not exportable and is cleared all the same, first:
    it references `tasks`, and a drain owed for a task this rebuild does not
    bring back is owed for nothing. The per-activation tables go with it, for
    the same reason and in the same spirit: they reference rows this rebuild
    replaces. `findings` is put back by `rebuild_findings` before the
    transaction commits; `sessions`, `artifacts` and `usage` have no writer in
    this build, so clearing them is the whole of their restore.
    """
    connection.execute(_SQL_CLEAR_RESTORES)
    for derived in DERIVED_ACTIVATION_TABLES:
        connection.execute(f"DELETE FROM {derived.value}")
    for table in reversed(EXPORT_TABLES):
        connection.execute(f"DELETE FROM {table.value}")


def _insert(
    connection: sqlite3.Connection,
    table: LedgerTable,
    row: Mapping[str, JsonValue],
    *,
    path: Path,
) -> None:
    """Insert one VALIDATED exported row back into its table.

    Only `_row` may build the arguments: the names below are interpolated, and
    they are safe because they are schema names this build creates, never the
    file's own text. Every VALUE is bound.
    """
    names = ", ".join(row)
    placeholders = ", ".join("?" for _ in row)
    statement = f"INSERT INTO {table.value} ({names}) VALUES ({placeholders})"
    values = tuple(
        _decoded(value, path=path, column=column) for column, value in row.items()
    )
    try:
        connection.execute(statement, values)
    except sqlite3.Error as exc:
        raise LedgerTransportError(str(exc)) from exc
