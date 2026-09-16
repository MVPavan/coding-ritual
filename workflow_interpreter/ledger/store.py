"""`LedgerStore` — the §3.3 tables behind the neutral `StoreBackend` seam.

S1 delivers the READ side whole: `WorkflowReads` runs over this store exactly
as it runs over bd, because every §4 query is expressed as carrier filters and
every carrier is here in `metadata_json`. The write side is one method —
`_create_row` — which is what a read needs in order to have anything to read;
the transitions, gate closes, nonces, signatures and projections of §3.3 land
with S2, and calling one of them here refuses loudly rather than half-writing.

Every statement is parameterised, including the JSON paths a carrier filter
selects on: `json_extract(metadata_json, ?)` takes its path as a bound value,
so no filter key is ever concatenated into SQL.
"""

from __future__ import annotations

import json
import re
import secrets
import sqlite3
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Final

from pydantic import JsonValue

from workflow_interpreter.bdio.carriers import Metadata
from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.bdio.errors import LossyWriteError
from workflow_interpreter.bdio.records import CanaryResult
from workflow_interpreter.bdio.rows import (
    BackendIdentity,
    NewRow,
    RowKind,
    RowQuery,
    StoreRow,
)
from workflow_interpreter.bdio.wire import KEY_WF_ROOT_ID
from workflow_interpreter.ledger import rowmap
from workflow_interpreter.ledger.constants import (
    MSG_BAD_FILTER_KEY,
    MSG_LOSSY_ROW,
    MSG_NO_WRITE_SURFACE,
    ROW_TABLES,
    LedgerTable,
    MetaKey,
)
from workflow_interpreter.ledger.database import (
    LedgerDatabase,
    read_meta,
    schema_version,
)
from workflow_interpreter.ledger.errors import (
    LedgerRowMissing,
    LedgerTransportError,
    LedgerWriteUnsupported,
)
from workflow_interpreter.ledger.paths import fence_path
from workflow_interpreter.schema.loader import canonical_json_bytes

COORDINATION_DIR: Final[str] = "coordination"
"""Execution locks live beside the fence, in the git common directory: they
must be found identically from every worktree and every wrapper home (§3.4)."""

CANARY_NONCE_BYTES: Final[int] = 8
_PROBE_KEY_FORMAT: Final[str] = "probe:{nonce}"
_ATTRIBUTE_SCHEMA: Final[str] = "schema_version"
_ATTRIBUTE_WRAPPER_ROOT: Final[str] = "wrapper_root"
_ATTRIBUTE_PATH: Final[str] = "path"

_FIRST_SEQ: Final[int] = 1
_FIRST_ATTEMPT: Final[int] = 1
_EPIC_SEPARATOR: Final[str] = "."
_IDENTIFIER: Final[re.Pattern[str]] = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_JSON_PATH_FORMAT: Final[str] = "$.{key}"

_SQL_TASK_INSERT: Final[str] = (
    "INSERT OR IGNORE INTO tasks "
    "(task_id, epic_id, graph_id, backend, next_seq, created_at) "
    "VALUES (?, ?, NULL, ?, ?, ?)"
)
_SQL_TASK_SEQ: Final[str] = "SELECT next_seq FROM tasks WHERE task_id = ?"
_SQL_TASK_SEQ_BUMP: Final[str] = (
    "UPDATE tasks SET next_seq = next_seq + 1 WHERE task_id = ?"
)
_SQL_ROOT_COUNT: Final[str] = "SELECT COUNT(*) FROM roots WHERE task_id = ?"
_SQL_META_WRITE: Final[str] = "INSERT INTO meta (key, value) VALUES (?, ?)"
_SQL_META_DELETE: Final[str] = "DELETE FROM meta WHERE key = ?"
_SQL_META_READ: Final[str] = "SELECT value FROM meta WHERE key = ?"
_FILTER_CLAUSE: Final[str] = "CAST(json_extract(metadata_json, ?) AS TEXT) = ?"
_MSG_PROBE: Final[str] = "the ledger probe wrote {wrote!r} and read back {read!r}"


class LedgerStore:
    """One repository's ledger, scoped to the task whose rows it writes.

    The task is pinned at construction because §3.3 gives every row a
    `task_id` and a per-task `seq`, and D16 requires every root to be
    reachable from the tracker: a store with no task could only write rows
    nobody could export.
    """

    def __init__(self, database: LedgerDatabase, *, task_id: str) -> None:
        self._database = database
        self._task_id = task_id

    @property
    def kind(self) -> BackendKind:
        """The ledger, the backend this store speaks for (§3.2)."""
        return BackendKind.LEDGER

    @property
    def task_id(self) -> str:
        """The task bead every row of this store belongs to (D16)."""
        return self._task_id

    @property
    def database(self) -> LedgerDatabase:
        """The connection and fence hold this store reads and writes through."""
        return self._database

    # -- the neutral backend surface (§3.1) -------------------------------

    def identity(self) -> BackendIdentity:
        """Where the ledger's rows and their execution locks live (§3.4)."""
        return BackendIdentity(
            kind=BackendKind.LEDGER,
            lock_root=fence_path(self._database.repo_root).parent / COORDINATION_DIR,
            legacy_lock_root=None,
        )

    def probe(self) -> CanaryResult:
        """Assert the pinned identity and round-trip a value (§11).

        The ledger's assertions are its own: a schema this build knows and a
        wrapper root this process matches — both already enforced when the
        connection opened — plus a real write-read-delete through SQLite, so a
        database that opened but cannot durably answer fails here.
        """
        nonce = secrets.token_hex(CANARY_NONCE_BYTES)
        key = _PROBE_KEY_FORMAT.format(nonce=nonce)
        connection = self._database.connection
        with self._database.transaction():
            connection.execute(_SQL_META_WRITE, (key, nonce))
            row = connection.execute(_SQL_META_READ, (key,)).fetchone()
            connection.execute(_SQL_META_DELETE, (key,))
        read = None if row is None else str(row[0])
        if read != nonce:
            raise LossyWriteError(
                key, _ATTRIBUTE_SCHEMA, _MSG_PROBE.format(wrote=nonce, read=read)
            )
        return CanaryResult(
            kind=BackendKind.LEDGER,
            attributes={
                _ATTRIBUTE_SCHEMA: str(schema_version(connection)),
                _ATTRIBUTE_WRAPPER_ROOT: str(
                    read_meta(connection, MetaKey.WRAPPER_ROOT)
                ),
                _ATTRIBUTE_PATH: str(self._database.path),
            },
            probe_row_id=key,
            nonce=nonce,
        )

    def get_row(self, row_id: str) -> StoreRow:
        """One row by id, looked up in each row table until it is found."""
        for table in ROW_TABLES:
            found = self._select(table, f"{rowmap.ID_COLUMN[table]} = ?", (row_id,))
            if found:
                return found[0]
        raise LedgerRowMissing(f"no ledger row {row_id!r} in task {self._task_id!r}")

    def find_rows(self, query: RowQuery) -> tuple[StoreRow, ...]:
        """Rows this task holds that the carrier filters select, closed included."""
        clauses: list[str] = []
        values: list[JsonValue] = []
        for key, wanted in query.metadata_filters.items():
            clauses.append(_FILTER_CLAUSE)
            values += [_json_path(key), wanted]
        where = " AND ".join(clauses) if clauses else "1 = 1"
        rows: list[StoreRow] = []
        for table in _tables_for(query.kind):
            rows += self._select(table, where, tuple(values))
        return tuple(rows)

    def _create_row(self, new: NewRow) -> StoreRow:
        """Create one row, its task row, and its per-task `seq`, in one write.

        `summary` is disclosure the ledger has no human surface for and is
        deliberately dropped: §3.3 stores the carrier, and nothing routes on a
        title (`bdio/rows.py`). The read-back happens inside the same
        transaction, so a row that did not land exactly never becomes visible.
        """
        table = rowmap.table_for(new.metadata)
        connection = self._database.connection
        with self._database.transaction():
            self._ensure_task(connection)
            seq = self._allocate_seq(connection)
            attempt = self._next_attempt(connection) if _is_root(table) else 0
            row_id = rowmap.mint_id(
                table, new.metadata, task_id=self._task_id, attempt=attempt
            )
            metadata = _self_identified(new.metadata, table, row_id)
            columns = rowmap.projection(
                table,
                row_id=row_id,
                task_id=self._task_id,
                attempt=attempt,
                seq=seq,
                metadata=metadata,
                metadata_json=_json_text(metadata),
                payload_json=None if new.payload is None else _json_text(new.payload),
            )
            self._insert(connection, table, columns)
            written = self._select(table, f"{rowmap.ID_COLUMN[table]} = ?", (row_id,))
            if len(written) != 1 or written[0].metadata != metadata:
                raise LossyWriteError(
                    row_id, table.value, MSG_LOSSY_ROW.format(detail=row_id)
                )
        return written[0]

    def _merge_metadata(self, row_id: str, metadata: Metadata) -> StoreRow:
        """S2's write surface — refused here rather than half-implemented."""
        raise LedgerWriteUnsupported(
            MSG_NO_WRITE_SURFACE.format(operation="merging metadata")
        )

    def _claim_and_merge_metadata(self, row_id: str, metadata: Metadata) -> StoreRow:
        """S2's write surface; claims stay bd-backed until the cutover (D20)."""
        raise LedgerWriteUnsupported(
            MSG_NO_WRITE_SURFACE.format(operation="claiming a row")
        )

    def _close_row(self, row_id: str, reason: str) -> StoreRow:
        """S2's write surface — a close is a §5.1 transition, not an update."""
        raise LedgerWriteUnsupported(
            MSG_NO_WRITE_SURFACE.format(operation="closing a row")
        )

    # -- the SQL --------------------------------------------------------

    def _select(
        self, table: LedgerTable, where: str, values: Sequence[JsonValue]
    ) -> tuple[StoreRow, ...]:
        """Every row of this task in `table` the clause selects, hydrated.

        The only text interpolated into a statement anywhere in this module is
        a `LedgerTable` member's own value and the fixed clause constants above
        — SQLite cannot bind a table name, and an enum member is not user
        input. Every caller-supplied value, including the JSON path a carrier
        filter names, is BOUND.
        """
        statement = f"SELECT * FROM {table.value} WHERE task_id = ? AND ({where})"
        try:
            cursor = self._database.connection.execute(
                statement, (self._task_id, *values)
            )
            found = cursor.fetchall()
        except sqlite3.Error as exc:
            raise LedgerTransportError(str(exc)) from exc
        return tuple(
            rowmap.hydrate(table, row, _parsed(row[rowmap.COLUMN_METADATA]))
            for row in found
        )

    def _insert(
        self,
        connection: sqlite3.Connection,
        table: LedgerTable,
        columns: Mapping[str, JsonValue],
    ) -> None:
        """Insert one fully projected row, every value bound."""
        names = ", ".join(columns)
        placeholders = ", ".join("?" for _ in columns)
        statement = f"INSERT INTO {table.value} ({names}) VALUES ({placeholders})"
        try:
            connection.execute(statement, tuple(columns.values()))
        except sqlite3.Error as exc:
            raise LedgerTransportError(str(exc)) from exc

    def _ensure_task(self, connection: sqlite3.Connection) -> None:
        """Create this store's `tasks` row once; every later write reuses it."""
        connection.execute(
            _SQL_TASK_INSERT,
            (
                self._task_id,
                epic_segment(self._task_id),
                BackendKind.LEDGER.value,
                _FIRST_SEQ,
                datetime.now(tz=UTC).isoformat(),
            ),
        )

    def _allocate_seq(self, connection: sqlite3.Connection) -> int:
        """Take the next per-task `seq` inside the writing transaction (§3.3)."""
        row = connection.execute(_SQL_TASK_SEQ, (self._task_id,)).fetchone()
        if row is None:  # pragma: no cover - the task row is written just above
            raise LedgerTransportError(f"task row {self._task_id!r} vanished")
        connection.execute(_SQL_TASK_SEQ_BUMP, (self._task_id,))
        return int(row[0])

    def _next_attempt(self, connection: sqlite3.Connection) -> int:
        """The attempt number a new root of this task gets (D8)."""
        row = connection.execute(_SQL_ROOT_COUNT, (self._task_id,)).fetchone()
        return _FIRST_ATTEMPT + (0 if row is None else int(row[0]))


def epic_segment(task_id: str) -> str:
    """The parent prefix of a dotted bead id — deterministic, no bd lookup (§2)."""
    head, separator, _ = task_id.partition(_EPIC_SEPARATOR)
    return head if separator else task_id


def _is_root(table: LedgerTable) -> bool:
    """Whether this table holds roots, which alone carry an attempt number."""
    return table is LedgerTable.ROOTS


def _tables_for(kind: RowKind | None) -> tuple[LedgerTable, ...]:
    """Which row tables a query's `kind` filter selects."""
    if kind is None:
        return ROW_TABLES
    return tuple(
        table for table in ROW_TABLES if rowmap.ROW_KIND_OF_TABLE[table] is kind
    )


def _json_path(key: str) -> str:
    """The JSON path a carrier key names, refusing anything but an identifier.

    The path is a BOUND value, so this is defence in depth rather than the
    escaping: a key that is not a plain identifier is a caller bug, and
    answering it as `$.weird key` would silently select nothing.
    """
    if _IDENTIFIER.fullmatch(key) is None:
        raise LedgerTransportError(MSG_BAD_FILTER_KEY.format(key=key))
    return _JSON_PATH_FORMAT.format(key=key)


def _json_text(value: Metadata) -> str:
    """Canonical JSON for a stored carrier — sorted keys, no stray whitespace."""
    return canonical_json_bytes(value).decode("utf-8")


def _parsed(text: str) -> Metadata:
    """One stored carrier back as the mapping the seam speaks."""
    parsed: Metadata = json.loads(text)
    return parsed


def _self_identified(metadata: Metadata, table: LedgerTable, row_id: str) -> Metadata:
    """A root carries its own id, which the ledger knows BEFORE the insert.

    On bd the id only exists after the create, so `roots._ensure_self_id`
    completes the pair with a second write; here the id is deterministic, so
    the row is never durably self-less and that crash window does not exist.
    """
    if not _is_root(table) or metadata.get(KEY_WF_ROOT_ID) == row_id:
        return dict(metadata)
    return dict(metadata) | {KEY_WF_ROOT_ID: row_id}
