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
the same rows come back out in the same order with the same canonical JSON.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from contextlib import closing
from pathlib import Path
from typing import Final

import structlog
from pydantic import BaseModel, ConfigDict, JsonValue

from workflow_interpreter.ledger.constants import (
    EXPORT_KIND_HEADER,
    EXPORT_KIND_ROW,
    EXPORT_TABLES,
    MSG_EXPORT_COLUMN,
    MSG_EXPORT_HEADER,
    MSG_EXPORT_ROW_KIND,
    MSG_EXPORT_TABLE,
    MSG_REPO_HASH_MISMATCH,
    MSG_UNKNOWN_TASK,
    MSG_WRAPPER_ROOT_MISMATCH,
    ROW_TABLES,
    ExportKey,
    LedgerTable,
    MetaKey,
)
from workflow_interpreter.ledger.database import (
    LedgerDatabase,
    assert_identity,
    connect,
    read_meta,
    schema_version,
    transaction,
)
from workflow_interpreter.ledger.errors import (
    LedgerExportError,
    LedgerIdentityError,
    LedgerSchemaError,
    LedgerTransportError,
)
from workflow_interpreter.ledger.fence import LedgerFence
from workflow_interpreter.ledger.paths import export_path, fence_path, repo_hash
from workflow_interpreter.ledger.schema import table_columns
from workflow_interpreter.schema.loader import canonical_json_bytes

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

_SQL_TASK: Final[str] = "SELECT * FROM tasks WHERE task_id = ?"
_SEQ_COLUMN: Final[str] = "seq"
_SECOND_LINE: Final[int] = 2
_NEWLINE: Final[bytes] = b"\n"

ExportLine = dict[str, JsonValue]
ExportRow = dict[str, JsonValue]


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
    connection = database.connection
    with transaction(connection, write=False):
        task = connection.execute(_SQL_TASK, (task_id,)).fetchone()
        if task is None:
            raise LedgerTransportError(MSG_UNKNOWN_TASK.format(task_id=task_id))
        header: ExportLine = {
            ExportKey.KIND.value: EXPORT_KIND_HEADER,
            ExportKey.SCHEMA_VERSION.value: schema_version(connection),
            ExportKey.REPO_HASH.value: read_meta(connection, MetaKey.REPO_HASH),
            ExportKey.WRAPPER_ROOT.value: read_meta(connection, MetaKey.WRAPPER_ROOT),
            ExportKey.TASK_ID.value: task_id,
        }
        lines = [header, _line(LedgerTable.TASKS, task)]
        lines += [
            _line(table, row) for table, row in _ordered_rows(connection, task_id)
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
    describes and a failure anywhere leaves it as it was.
    """
    parsed = tuple(
        _parse(path, repo_root=repo_root, wrapper_root=wrapper_root) for path in paths
    )
    taken = LedgerFence(fence_path(repo_root)) if fence is None else fence
    with taken.exclusive(), closing(connect(ledger)) as connection:
        for export in parsed:
            _assert_schema(connection, export.path, export.header)
        # The DESTINATION's pins, not only the files' headers: a ledger this
        # process may not write is refused here, inside the exclusive section
        # and before a single row is deleted (§3.5).
        assert_identity(
            connection, path=ledger, repo_root=repo_root, wrapper_root=wrapper_root
        )
        with transaction(connection):
            _clear(connection)
            for export in parsed:
                for table, row in export.rows:
                    _insert(connection, table, row)
    for export in parsed:
        _LOG.info("wf.ledger.imported", task_id=export.task_id, path=str(export.path))
    return tuple(export.task_id for export in parsed)


def _parse(path: Path, *, repo_root: Path, wrapper_root: Path) -> ParsedExport:
    """One export file as validated lines, or a refusal naming the bad one."""
    lines = _read_lines(path)
    header = lines[0]
    if header.get(ExportKey.KIND.value) != EXPORT_KIND_HEADER:
        raise LedgerIdentityError(
            MSG_EXPORT_HEADER.format(path=path, kind=EXPORT_KIND_HEADER)
        )
    _assert_header(header, path=path, repo_root=repo_root, wrapper_root=wrapper_root)
    rows = tuple(
        _row(line, path=path, number=number)
        for number, line in enumerate(lines[1:], start=_SECOND_LINE)
    )
    return ParsedExport(
        path=path,
        task_id=str(header[ExportKey.TASK_ID.value]),
        header=header,
        rows=rows,
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
    header: Mapping[str, JsonValue],
    *,
    path: Path,
    repo_root: Path,
    wrapper_root: Path,
) -> None:
    """Refuse an export written for another repository or wrapper root (§3.5)."""
    pinned_repo = header.get(ExportKey.REPO_HASH.value)
    found_repo = repo_hash(repo_root)
    if pinned_repo != found_repo:
        raise LedgerIdentityError(
            MSG_REPO_HASH_MISMATCH.format(
                path=path, pinned=pinned_repo, found=found_repo
            )
        )
    pinned_wrapper = header.get(ExportKey.WRAPPER_ROOT.value)
    found_wrapper = str(wrapper_root.resolve())
    if pinned_wrapper != found_wrapper:
        raise LedgerIdentityError(
            MSG_WRAPPER_ROOT_MISMATCH.format(
                path=path, pinned=pinned_wrapper, found=found_wrapper
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


def _line(table: LedgerTable, row: sqlite3.Row) -> ExportLine:
    """One database row as its export line."""
    return {
        ExportKey.KIND.value: EXPORT_KIND_ROW,
        ExportKey.TABLE.value: table.value,
        # `sqlite3.Row` iterates VALUES, so the column names come from `keys()`.
        ExportKey.ROW.value: dict(zip(row.keys(), tuple(row), strict=True)),
    }


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


def _clear(connection: sqlite3.Connection) -> None:
    """Empty every exportable table, children before parents, so the FKs hold.

    The whole state and not one task's rows: the export set IS the ledger after
    an import, so a task no file describes must not survive it (§3.6).
    """
    for table in reversed(EXPORT_TABLES):
        connection.execute(f"DELETE FROM {table.value}")


def _insert(
    connection: sqlite3.Connection, table: LedgerTable, row: Mapping[str, JsonValue]
) -> None:
    """Insert one VALIDATED exported row back into its table.

    Only `_row` may build the arguments: the names below are interpolated, and
    they are safe because they are schema names this build creates, never the
    file's own text. Every VALUE is bound.
    """
    names = ", ".join(row)
    placeholders = ", ".join("?" for _ in row)
    statement = f"INSERT INTO {table.value} ({names}) VALUES ({placeholders})"
    try:
        connection.execute(statement, tuple(row.values()))
    except sqlite3.Error as exc:
        raise LedgerTransportError(str(exc)) from exc
