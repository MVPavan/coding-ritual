"""One task's rows out to a tracked JSONL file, and back in again (§3.6).

The export is the durable record a task is closable against, so it is written
under ONE read transaction while the shared fence is held: it can never publish
a snapshot from the middle of an exclusive restore. The import is the mirror —
exclusive fence, one transaction, the task's rows replaced rather than merged,
so a rebuild is a rebuild and not an append.

Order is `(task_id, seq)`, the per-task sequence every row is given inside the
transaction that wrote it, which is what makes the round trip byte-identical:
the same rows come back out in the same order with the same canonical JSON.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import closing
from pathlib import Path
from typing import Final

import structlog
from pydantic import JsonValue

from workflow_interpreter.ledger.constants import (
    EXPORT_KIND_HEADER,
    EXPORT_KIND_ROW,
    EXPORT_TABLES,
    MSG_EXPORT_HEADER,
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
    connect,
    read_meta,
    schema_version,
    transaction,
)
from workflow_interpreter.ledger.errors import (
    LedgerIdentityError,
    LedgerSchemaError,
    LedgerTransportError,
)
from workflow_interpreter.ledger.fence import LedgerFence
from workflow_interpreter.ledger.paths import export_path, fence_path, repo_hash
from workflow_interpreter.schema.loader import canonical_json_bytes

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

_SQL_TASK: Final[str] = "SELECT * FROM tasks WHERE task_id = ?"
_SEQ_COLUMN: Final[str] = "seq"
_NEWLINE: Final[bytes] = b"\n"

ExportLine = dict[str, JsonValue]


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
    """Rebuild one task's rows from its export, under the exclusive fence.

    The task's rows are DELETED first: an import is a restore of the exported
    state, and merging would leave rows the export does not describe alive
    beside the ones it does.
    """
    lines = _read_lines(path)
    header = lines[0]
    if header.get(ExportKey.KIND.value) != EXPORT_KIND_HEADER:
        raise LedgerIdentityError(
            MSG_EXPORT_HEADER.format(path=path, kind=EXPORT_KIND_HEADER)
        )
    _assert_header(header, path=path, repo_root=repo_root, wrapper_root=wrapper_root)
    task_id = str(header[ExportKey.TASK_ID.value])
    taken = LedgerFence(fence_path(repo_root)) if fence is None else fence
    with taken.exclusive(), closing(connect(ledger)) as connection:
        _assert_schema(connection, path, header)
        with transaction(connection):
            _delete_task(connection, task_id)
            for line in lines[1:]:
                _insert(connection, line)
    _LOG.info("wf.ledger.imported", task_id=task_id, path=str(path))
    return task_id


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


def _delete_task(connection: sqlite3.Connection, task_id: str) -> None:
    """Remove the task's rows, children before parents, so the FKs hold."""
    for table in reversed(EXPORT_TABLES):
        connection.execute(f"DELETE FROM {table.value} WHERE task_id = ?", (task_id,))


def _insert(connection: sqlite3.Connection, line: Mapping[str, JsonValue]) -> None:
    """Insert one exported row back into the table it names."""
    table = LedgerTable(str(line[ExportKey.TABLE.value]))
    row = line[ExportKey.ROW.value]
    if not isinstance(row, dict):
        raise LedgerTransportError(f"export line for {table.value} carries no row")
    names = ", ".join(row)
    placeholders = ", ".join("?" for _ in row)
    statement = f"INSERT INTO {table.value} ({names}) VALUES ({placeholders})"
    try:
        connection.execute(statement, tuple(row.values()))
    except sqlite3.Error as exc:
        raise LedgerTransportError(str(exc)) from exc
