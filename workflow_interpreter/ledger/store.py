"""`LedgerStore` — the §3.3 tables behind the neutral `StoreBackend` seam.

`WorkflowReads` runs over this store exactly as it runs over bd, because every
§4 query is expressed as carrier filters and every carrier is here in
`metadata_json`. The write side is the four neutral methods plus the atomic
gate close, and each one IS one `BEGIN IMMEDIATE` transaction (§3.4.2): the
row, its projected columns, the `seq` it takes from `tasks.next_seq`, the
nonce a gate close consumes, the signature it records and the attention
projection it enqueues all land together or not at all.

Two things are deliberately NOT here. Claims stay bd-backed while the bd
backend exists (D20), so a claim write is refused rather than kept in a
second, invisible table. And a writer that waits out `busy_timeout` refuses by
name (§3.4.6) instead of retrying, so contention is visible.

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

from workflow_interpreter.bdio.carriers import GateState, Metadata
from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.bdio.errors import LossyWriteError
from workflow_interpreter.bdio.records import CanaryResult
from workflow_interpreter.bdio.rows import (
    BackendIdentity,
    GateClosure,
    NewRow,
    RowGuard,
    RowKind,
    RowQuery,
    StoreRow,
)
from workflow_interpreter.bdio.wire import (
    KEY_GATE_STATE,
    KEY_PAYLOAD_DIGEST,
    KEY_SUPERSEDED_BY,
    KEY_TERMINAL,
    KEY_WF_ROOT_ID,
)
from workflow_interpreter.ledger import rowmap
from workflow_interpreter.ledger.constants import (
    MSG_BAD_FILTER_KEY,
    MSG_CLAIM_ON_LEDGER,
    MSG_GATE_NOT_OPEN,
    MSG_GATE_SIGNED,
    MSG_LOSSY_ROW,
    MSG_NONCE_SPENT,
    MSG_NOT_A_GATE,
    MSG_ROW_MISSING,
    ROW_TABLES,
    STATUS_CLOSED,
    LedgerOperation,
    LedgerTable,
    MetaKey,
)
from workflow_interpreter.ledger.database import (
    LedgerDatabase,
    read_meta,
    schema_version,
)
from workflow_interpreter.ledger.errors import (
    LedgerClaimUnsupported,
    LedgerGateConflict,
    LedgerRowMissing,
    LedgerTransportError,
    sqlite_failure,
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
_SQL_SELECT_BY_COLUMN: Final[str] = (
    "SELECT * FROM {table} WHERE task_id = ? AND {column} = ?"
)
"""One row of this task by an indexed column — its id, or its natural key."""
_SQL_UPDATE_ROW: Final[str] = (
    "UPDATE {table} SET {assignments} WHERE task_id = ? AND {column} = ?"
)
_SQL_NONCE_INSERT: Final[str] = (
    "INSERT INTO nonces (nonce, gate_id, consumed_at) VALUES (?, ?, ?)"
)
_SQL_NONCE_OWNER: Final[str] = "SELECT gate_id FROM nonces WHERE nonce = ?"
_SQL_SIGNATURE_INSERT: Final[str] = (
    "INSERT INTO signatures (gate_id, payload_bytes, signature_bytes, "
    "signer_fingerprint, allowed_signers_entry, policy_json) "
    "VALUES (?, ?, ?, ?, ?, ?)"
)
_SQL_SIGNATURE_PRESENT: Final[str] = "SELECT 1 FROM signatures WHERE gate_id = ?"
_SQL_PROJECTION_INSERT: Final[str] = (
    "INSERT INTO projections (task_id, generation, created_at, acked_at) "
    "VALUES (?, ?, ?, NULL)"
)
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
        # One locked scope for the whole canary, the round trip and the
        # attributes alike: an identity read after the lock was released could
        # describe a state this probe never verified, and the canary would
        # then vouch for it. The lock is reentrant, so the transaction below
        # nests inside it.
        with self._database.locked() as connection:
            with self._database.transaction():
                connection.execute(_SQL_META_WRITE, (key, nonce))
                row = connection.execute(_SQL_META_READ, (key,)).fetchone()
                connection.execute(_SQL_META_DELETE, (key,))
            read = None if row is None else str(row[0])
            if read != nonce:
                raise LossyWriteError(
                    key, _ATTRIBUTE_SCHEMA, _MSG_PROBE.format(wrote=nonce, read=read)
                )
            attributes = {
                _ATTRIBUTE_SCHEMA: str(schema_version(connection)),
                _ATTRIBUTE_WRAPPER_ROOT: str(
                    read_meta(connection, MetaKey.WRAPPER_ROOT)
                ),
                _ATTRIBUTE_PATH: str(self._database.path),
            }
        return CanaryResult(
            kind=BackendKind.LEDGER,
            attributes=attributes,
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

        The §3.3 natural key is checked in the SAME transaction (§3.3 mint):
        a second create of one fact — a re-mint after a lost read-back, a
        re-appended event — ANSWERS with the row that already exists rather
        than failing on the UNIQUE constraint. That is what the keys are for,
        and deciding it under `BEGIN IMMEDIATE` is what makes it true between
        processes rather than only between ticks.
        """
        table = rowmap.table_for(new.metadata)
        connection = self._database.connection
        with self._database.transaction():
            existing = self._by_natural_key(table, new.metadata)
            if existing is not None:
                return existing
            self._ensure_task(connection)
            seq = self._allocate_seq(connection)
            attempt = self._next_attempt(connection) if _is_root(table) else 0
            row_id = rowmap.mint_id(
                table,
                new.metadata,
                task_id=self._task_id,
                attempt=attempt,
                seq=seq,
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
                at=_now(),
            )
            self._insert(table, columns)
            written = self._verified(table, row_id, metadata, LedgerOperation.CREATING)
            if _projects_attention(table, metadata):
                self._enqueue_projection()
        return written

    def _by_natural_key(
        self, table: LedgerTable, metadata: Metadata
    ) -> StoreRow | None:
        """The row this carrier's §3.3 unique key already names, if there is one."""
        key = rowmap.NATURAL_KEY[table]
        value = metadata.get(key)
        if not isinstance(value, str):
            return None
        statement = _SQL_SELECT_BY_COLUMN.format(table=table.value, column=key)
        found = self._execute_one(
            statement, (self._task_id, value), LedgerOperation.CREATING, value
        )
        return None if found is None else self._hydrated(table, found)

    def _merge_metadata(
        self, row_id: str, metadata: Metadata, *, guard: RowGuard | None = None
    ) -> StoreRow:
        """Merge a carrier delta into one row — read, check, write, in ONE go.

        The guard runs INSIDE the transaction, against the row this write is
        about to change: that is what makes §3.3's lifecycle transition atomic
        rather than merely narrow. `version` moves with the write, so a
        concurrent writer's merge is visible as a version it did not produce.
        """
        with self._database.transaction():
            table, row = self._locate(row_id, LedgerOperation.MERGING)
            current = self._hydrated(table, row)
            if guard is not None:
                guard(current)
            merged = dict(current.metadata) | dict(metadata)
            self._rewrite(table, row, merged)
            written = self._verified(table, row_id, merged, LedgerOperation.MERGING)
            if _projects_attention(table, merged):
                self._enqueue_projection()
        return written

    def _claim_and_merge_metadata(self, row_id: str, metadata: Metadata) -> StoreRow:
        """Refused: an integration-target claim is bd's row during coexistence.

        The only caller is the claim surface (`bdio/claims.py`), and D20 keeps
        claims in bd while `store` can still select it — a ledger-backed run
        must contend on the SAME row a bd-backed run reserves, or neither sees
        the other's reservation.
        """
        raise LedgerClaimUnsupported(
            MSG_CLAIM_ON_LEDGER.format(
                operation=LedgerOperation.CLAIMING.value, row_id=row_id
            )
        )

    def _close_row(self, row_id: str, reason: str) -> StoreRow:
        """Settle one row: `status`, its reason, and the projection it may owe.

        Idempotent, because every close in this package is driven forward
        rather than refused (`bdio/finalize.py`): closing a closed row with
        the same reason rewrites nothing and answers the row.
        """
        with self._database.transaction():
            table, row = self._locate(row_id, LedgerOperation.CLOSING)
            if row[rowmap.COLUMN_STATUS] == STATUS_CLOSED and (
                row[rowmap.COLUMN_CLOSE_REASON] == reason
            ):
                return self._hydrated(table, row)
            self._update(
                table,
                row_id,
                {
                    rowmap.COLUMN_STATUS: STATUS_CLOSED,
                    rowmap.COLUMN_CLOSE_REASON: reason,
                },
                LedgerOperation.CLOSING,
            )
            metadata = _parsed(row[rowmap.COLUMN_METADATA])
            written = self._verified(table, row_id, metadata, LedgerOperation.CLOSING)
            if written.status != STATUS_CLOSED or written.close_reason != reason:
                raise LossyWriteError(
                    row_id, table.value, MSG_LOSSY_ROW.format(detail=reason)
                )
            if _closes_attention(table):
                self._enqueue_projection()
        return written

    def _close_gate(self, closure: GateClosure) -> StoreRow:
        """The §3.3 gate close, whole: nonce, state, outcome, signature, projection.

        One `BEGIN IMMEDIATE` transaction, and the signature was verified
        OUTSIDE it — §3.4.2 forbids a subprocess inside a transaction, and
        `ssh-keygen` is one. What lands here is the DECISION: the nonce is
        consumed so it can never close a second gate, the carrier records the
        outcome, the historical trust (payload, signature, fingerprint, the
        allow-list entry that matched and the policy in force) is stored so
        §3.6 can re-verify from the export alone, and the attention projection
        is enqueued with it.

        The decision is also DECIDED here, inside the transaction. The caller
        read the gate as OPEN before it verified a signature (`gates.
        close_gate_verified`), so two approvals can arrive at one gate having
        both seen it open; whichever `BEGIN IMMEDIATE` commits first owns the
        gate, and the other is refused with its nonce and its signature
        unwritten. Letting the second write through while the nonce and
        signature inserts quietly kept the first one's rows would leave a gate
        whose recorded outcome and whose stored trust came from two different
        approvals (found in review).
        """
        with self._database.transaction():
            table, row = self._locate(closure.gate_id, LedgerOperation.CLOSING_GATE)
            if table is not LedgerTable.GATES:
                raise LedgerTransportError(
                    MSG_NOT_A_GATE.format(row_id=closure.gate_id, table=table.value)
                )
            recorded = self._decidable(table, row, closure)
            if recorded is not None:
                return recorded
            merged = dict(self._hydrated(table, row).metadata) | dict(closure.metadata)
            self._rewrite(table, row, merged)
            self._update(
                table,
                closure.gate_id,
                {
                    rowmap.COLUMN_STATUS: STATUS_CLOSED,
                    rowmap.COLUMN_CLOSE_REASON: closure.close_reason,
                },
                LedgerOperation.CLOSING_GATE,
            )
            self._consume_nonce(closure)
            self._record_signature(closure)
            written = self._verified(
                table, closure.gate_id, merged, LedgerOperation.CLOSING_GATE
            )
            self._enqueue_projection()
        return written

    # -- the writes, all inside their caller's transaction ---------------

    def _locate(
        self, row_id: str, operation: LedgerOperation
    ) -> tuple[LedgerTable, sqlite3.Row]:
        """The table and raw row this id names, or a refusal naming the task."""
        for table in ROW_TABLES:
            statement = _SQL_SELECT_BY_COLUMN.format(
                table=table.value, column=rowmap.ID_COLUMN[table]
            )
            row = self._execute_one(
                statement, (self._task_id, row_id), operation, row_id
            )
            if row is not None:
                return table, row
        raise LedgerRowMissing(
            MSG_ROW_MISSING.format(
                row_id=row_id, task_id=self._task_id, operation=operation.value
            )
        )

    def _hydrated(self, table: LedgerTable, row: sqlite3.Row) -> StoreRow:
        """One raw row as the neutral row the seam speaks."""
        return rowmap.hydrate(table, row, _parsed(row[rowmap.COLUMN_METADATA]))

    def _rewrite(self, table: LedgerTable, row: sqlite3.Row, merged: Metadata) -> None:
        """Store the merged carrier and re-project every column it feeds."""
        self._update(
            table,
            str(row[rowmap.ID_COLUMN[table]]),
            rowmap.merge_projection(
                table,
                row,
                metadata=merged,
                metadata_json=_json_text(merged),
                at=_now(),
            ),
            LedgerOperation.MERGING,
        )

    def _update(
        self,
        table: LedgerTable,
        row_id: str,
        columns: Mapping[str, JsonValue],
        operation: LedgerOperation,
    ) -> None:
        """Set named columns on one row of this task, every value bound."""
        assignments = ", ".join(f"{name} = ?" for name in columns)
        statement = _SQL_UPDATE_ROW.format(
            table=table.value, assignments=assignments, column=rowmap.ID_COLUMN[table]
        )
        self._execute(
            statement,
            (*columns.values(), self._task_id, row_id),
            operation,
            row_id,
        )

    def _verified(
        self,
        table: LedgerTable,
        row_id: str,
        expected: Metadata,
        operation: LedgerOperation,
    ) -> StoreRow:
        """Read the written row back INSIDE the transaction, or abandon it.

        Inside on purpose: a row that did not land exactly is rolled back with
        the rest of the operation, so it never becomes visible to a reader —
        which is what bd's read-back check cannot give (`client.py`).
        """
        statement = _SQL_SELECT_BY_COLUMN.format(
            table=table.value, column=rowmap.ID_COLUMN[table]
        )
        found = self._execute_one(statement, (self._task_id, row_id), operation, row_id)
        if found is None:
            raise LedgerRowMissing(
                MSG_ROW_MISSING.format(
                    row_id=row_id, task_id=self._task_id, operation=operation.value
                )
            )
        written = self._hydrated(table, found)
        if written.metadata != expected:
            raise LossyWriteError(
                row_id, table.value, MSG_LOSSY_ROW.format(detail=row_id)
            )
        return written

    def _decidable(
        self, table: LedgerTable, row: sqlite3.Row, closure: GateClosure
    ) -> StoreRow | None:
        """Refuse a close that contradicts a decision this gate already carries.

        Answers the recorded row when this closure IS that decision — the same
        approval re-submitted after a lost read-back — and `None` when the gate
        is open and nothing of this close has landed yet. Everything else is a
        conflict, raised before a single row of the closure is written.
        """
        current = self._hydrated(table, row)
        incoming = closure.metadata.get(KEY_PAYLOAD_DIGEST)
        state = current.metadata.get(KEY_GATE_STATE)
        if state != GateState.OPEN.value:
            digest = current.metadata.get(KEY_PAYLOAD_DIGEST)
            if digest is not None and digest == incoming:
                return current
            raise LedgerGateConflict(
                MSG_GATE_NOT_OPEN.format(
                    gate_id=closure.gate_id,
                    state=state,
                    recorded=digest,
                    incoming=incoming,
                )
            )
        signed = self._execute_one(
            _SQL_SIGNATURE_PRESENT,
            (closure.gate_id,),
            LedgerOperation.CLOSING_GATE,
            closure.gate_id,
        )
        if signed is not None:
            raise LedgerGateConflict(MSG_GATE_SIGNED.format(gate_id=closure.gate_id))
        self._assert_unspent(closure)
        return None

    def _assert_unspent(self, closure: GateClosure) -> None:
        """Refuse an approval whose nonce already closed some OTHER gate (§9)."""
        if closure.nonce is None:
            return
        owner = self._execute_one(
            _SQL_NONCE_OWNER,
            (closure.nonce,),
            LedgerOperation.CLOSING_GATE,
            closure.gate_id,
        )
        if owner is not None and str(owner[0]) != closure.gate_id:
            raise LedgerGateConflict(
                MSG_NONCE_SPENT.format(
                    nonce=closure.nonce, owner=str(owner[0]), gate_id=closure.gate_id
                )
            )

    def _consume_nonce(self, closure: GateClosure) -> None:
        """Spend the approval's nonce on THIS gate, once and for all (§9).

        A plain insert: `_decidable` has already proved the nonce is unspent,
        so a conflict here is a defect rather than a second owner to tolerate.
        """
        if closure.nonce is None:
            return
        self._execute(
            _SQL_NONCE_INSERT,
            (closure.nonce, closure.gate_id, _now()),
            LedgerOperation.CLOSING_GATE,
            closure.gate_id,
        )

    def _record_signature(self, closure: GateClosure) -> None:
        """Store the bytes AND the trust they were accepted under (§3.6, D21)."""
        signature = closure.signature
        if signature is None:
            return
        self._execute(
            _SQL_SIGNATURE_INSERT,
            (
                closure.gate_id,
                signature.payload_bytes,
                signature.signature_bytes,
                signature.signer_fingerprint,
                signature.allowed_signers_entry,
                _json_text(signature.policy),
            ),
            LedgerOperation.CLOSING_GATE,
            closure.gate_id,
        )

    def _enqueue_projection(self) -> None:
        """Journal one attention generation in the transaction that earned it.

        The generation comes from `tasks.next_seq`, in this transaction, so it
        is unique and ordered per task: the reconciler acks every row up to
        the generation it reconciled, and an ack can therefore never cover a
        change that happened after the state it read (§3.2).
        """
        self._execute(
            _SQL_PROJECTION_INSERT,
            (self._task_id, self._allocate_seq(self._database.connection), _now()),
            LedgerOperation.RECONCILING,
            self._task_id,
        )

    # -- the SQL --------------------------------------------------------

    def _execute(
        self,
        statement: str,
        values: Sequence[JsonValue] | Sequence[object],
        operation: LedgerOperation,
        row_id: str,
    ) -> tuple[sqlite3.Row, ...]:
        """Run one bound statement and return its rows, naming what failed.

        Under the database's lock even for a read: the connection is shared by
        every thread of this process (§3.4.1), and the lock is reentrant, so a
        statement already inside one of this store's transactions pays nothing.

        The rows are FETCHED here rather than handed back as a live cursor:
        `sqlite3` steps the rest of a result set as the caller fetches it, so
        a cursor that outlived the lock would step the shared connection while
        another thread holds it and answer half from each side of that
        thread's transaction.
        """
        try:
            with self._database.locked() as connection:
                return tuple(connection.execute(statement, tuple(values)).fetchall())
        except sqlite3.Error as exc:
            raise sqlite_failure(exc, operation=operation.value, row_id=row_id) from exc

    def _execute_one(
        self,
        statement: str,
        values: Sequence[JsonValue] | Sequence[object],
        operation: LedgerOperation,
        row_id: str,
    ) -> sqlite3.Row | None:
        """The first row of one bound statement, or nothing — fetched under the lock."""
        found = self._execute(statement, values, operation, row_id)
        return found[0] if found else None

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
        found = self._execute(
            statement, (self._task_id, *values), LedgerOperation.READING, table.value
        )
        return tuple(
            rowmap.hydrate(table, row, _parsed(row[rowmap.COLUMN_METADATA]))
            for row in found
        )

    def _insert(self, table: LedgerTable, columns: Mapping[str, JsonValue]) -> None:
        """Insert one fully projected row, every value bound."""
        names = ", ".join(columns)
        placeholders = ", ".join("?" for _ in columns)
        statement = f"INSERT INTO {table.value} ({names}) VALUES ({placeholders})"
        self._execute(
            statement, tuple(columns.values()), LedgerOperation.CREATING, table.value
        )

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


def _now() -> str:
    """The instant a durable fact is stamped with, in UTC ISO-8601."""
    return datetime.now(tz=UTC).isoformat()


def _projects_attention(table: LedgerTable, metadata: Metadata) -> bool:
    """Whether this write can change `wf:attention`'s value (§3.2).

    Derived from the WRITE rather than announced by the caller: the predicate
    is "any non-terminal root of this task has an OPEN gate", so every gate
    write moves it, and a root write moves it exactly when the root leaves the
    non-terminal set. A caller that forgot to declare a projection would
    otherwise leave the label stale with nothing to notice it.
    """
    if table is LedgerTable.GATES:
        return True
    return table is LedgerTable.ROOTS and (
        metadata.get(KEY_TERMINAL) is not None
        or metadata.get(KEY_SUPERSEDED_BY) is not None
    )


def _closes_attention(table: LedgerTable) -> bool:
    """A settled root or gate can retire the label; nothing else can."""
    return table in (LedgerTable.ROOTS, LedgerTable.GATES)


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
