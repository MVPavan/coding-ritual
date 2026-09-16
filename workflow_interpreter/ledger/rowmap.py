"""Neutral rows in, §3.3 tables out — the one place the mapping lives.

Three jobs, all deterministic and all pure: which table a carrier belongs to,
which id the row gets (D8's deterministic ids), and which indexed columns
project out of the carrier. The carrier itself is stored WHOLE in
`metadata_json`; nothing here may drop a field, because the projections exist
for queries and constraints and never replace the record.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Final

from pydantic import JsonValue

from workflow_interpreter.bdio.carriers import Metadata
from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.bdio.rows import RowKind, StoreRow
from workflow_interpreter.bdio.wire import (
    KEY_EVENT_KEY,
    KEY_GATE_KEY,
    KEY_IDEMPOTENCY_KEY,
    KEY_INSTANCE_KEY,
    KEY_NONCE,
    KEY_SEQ,
    KEY_TERMINAL,
    KEY_WF_KIND,
    KEY_WF_ROOT_ID,
    WfKind,
)
from workflow_interpreter.ledger.constants import (
    MSG_UNKNOWN_CARRIER,
    STATUS_OPEN,
    LedgerTable,
)
from workflow_interpreter.ledger.errors import LedgerWriteUnsupported
from workflow_interpreter.schema.loader import canonical_json_bytes

TABLE_OF_KIND: Final[Mapping[WfKind, LedgerTable]] = {
    WfKind.ROOT: LedgerTable.ROOTS,
    WfKind.ACTIVATION: LedgerTable.ACTIVATIONS,
    WfKind.GATE: LedgerTable.GATES,
    WfKind.EVENT: LedgerTable.EVENTS,
}
"""`canary` is deliberately absent: the ledger's §11 probe round-trips through
`meta` rather than minting a throwaway row nobody would ever collect."""

ID_COLUMN: Final[Mapping[LedgerTable, str]] = {
    LedgerTable.ROOTS: "root_id",
    LedgerTable.ACTIVATIONS: "activation_id",
    LedgerTable.GATES: "gate_id",
    LedgerTable.EVENTS: "event_id",
}

ROW_KIND_OF_TABLE: Final[Mapping[LedgerTable, RowKind]] = {
    LedgerTable.ROOTS: RowKind.RECORD,
    LedgerTable.ACTIVATIONS: RowKind.RECORD,
    LedgerTable.GATES: RowKind.RECORD,
    LedgerTable.EVENTS: RowKind.EVENT,
}

COLUMN_METADATA: Final[str] = "metadata_json"
COLUMN_PAYLOAD: Final[str] = "payload_json"
COLUMN_TASK: Final[str] = "task_id"
COLUMN_SEQ: Final[str] = "seq"
COLUMN_STATUS: Final[str] = "status"
COLUMN_CLOSE_REASON: Final[str] = "close_reason"
COLUMN_ROOT: Final[str] = "root_id"

_KEY_NODE: Final[str] = "node"
_KEY_ROUND_NO: Final[str] = "round_no"
_KEY_LIFECYCLE: Final[str] = "lifecycle"
_KEY_STATE: Final[str] = "state"
_KEY_OUTCOME: Final[str] = "outcome"
_KEY_FINGERPRINT: Final[str] = "verified_fingerprint"
_KEY_BOUND_KEY: Final[str] = "bound_key"
_KEY_BOUND_VALUE: Final[str] = "bound_value"
_KEY_ARTIFACT_REF: Final[str] = "artifact_ref"
_KEY_ARTIFACT_OID: Final[str] = "artifact_oid"
_KEY_GRAPH_HASH: Final[str] = "graph_content_hash"
_KEY_INSTANCE_INPUTS: Final[str] = "instance_inputs"
_KEY_ALLOW_TEST_FLAGS: Final[str] = "allow_test_flags"
_KEY_BASE_COMMIT: Final[str] = "instance_base_commit"
_KEY_CONFIG_SIGNATURE: Final[str] = "config_signature"
_KEY_COORDINATION: Final[str] = "coordination"
_KEY_ACTIVATION_ID: Final[str] = "activation_id"

_FIRST_VERSION: Final[int] = 1
LEDGER_BACKEND: Final[str] = BackendKind.LEDGER.value

_ROOT_ID_FORMAT: Final[str] = "{task_id}-a{attempt}"
_ACTIVATION_ID_FORMAT: Final[str] = "{root_id}.{node}.r{round_no}.{seq}"
_GATE_ID_FORMAT: Final[str] = "{root_id}.g{seq}"
_EVENT_ID_FORMAT: Final[str] = "{root_id}.e{seq}"


def table_for(metadata: Metadata) -> LedgerTable:
    """The table a carrier belongs in, refusing a `wf_kind` with no table."""
    kind = metadata.get(KEY_WF_KIND)
    for candidate, table in TABLE_OF_KIND.items():
        if kind == candidate.value:
            return table
    raise LedgerWriteUnsupported(MSG_UNKNOWN_CARRIER.format(kind=kind))


def _text(metadata: Metadata, key: str) -> str | None:
    """A carrier field as text, or nothing when it is absent or not a scalar."""
    value = metadata.get(key)
    if value is None or isinstance(value, bool):
        return None
    return value if isinstance(value, str) else None


def _integer(metadata: Metadata, key: str, default: int = 0) -> int:
    """A carrier field as an integer projection, defaulting when absent."""
    value = metadata.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return value


def mint_id(
    table: LedgerTable, metadata: Metadata, *, task_id: str, attempt: int
) -> str:
    """The deterministic id this row gets on the ledger backend (D8).

    A root is `<task>-a<n>`, and everything below it is named from the root and
    the carrier's own `(node, round, seq)` — so the id of a row is a FUNCTION of
    the facts it records, and a re-created row cannot get a second name.
    """
    if table is LedgerTable.ROOTS:
        return _ROOT_ID_FORMAT.format(task_id=task_id, attempt=attempt)
    root_id = _text(metadata, KEY_WF_ROOT_ID) or task_id
    seq = _integer(metadata, KEY_SEQ)
    if table is LedgerTable.ACTIVATIONS:
        return _ACTIVATION_ID_FORMAT.format(
            root_id=root_id,
            node=_text(metadata, _KEY_NODE) or "",
            round_no=_integer(metadata, _KEY_ROUND_NO),
            seq=seq,
        )
    if table is LedgerTable.GATES:
        return _GATE_ID_FORMAT.format(root_id=root_id, seq=seq)
    return _EVENT_ID_FORMAT.format(root_id=root_id, seq=seq)


def _json_column(metadata: Metadata, key: str) -> str | None:
    """A structured carrier field as its own canonical JSON column, or nothing.

    A projection, never a replacement: the same object is inside
    `metadata_json` — this column exists so a query can reach it.
    """
    value = metadata.get(key)
    if value is None:
        return None
    return canonical_json_bytes(value).decode("utf-8")


def projection(
    table: LedgerTable,
    *,
    row_id: str,
    task_id: str,
    attempt: int,
    seq: int,
    metadata: Metadata,
    metadata_json: str,
    payload_json: str | None,
) -> dict[str, JsonValue]:
    """Every column of one row: the carrier, plus what is indexed out of it."""
    shared: dict[str, JsonValue] = {
        ID_COLUMN[table]: row_id,
        COLUMN_TASK: task_id,
        COLUMN_SEQ: seq,
        COLUMN_STATUS: STATUS_OPEN,
        COLUMN_CLOSE_REASON: None,
        COLUMN_METADATA: metadata_json,
    }
    root_id = _text(metadata, KEY_WF_ROOT_ID) or row_id
    if table is LedgerTable.ROOTS:
        return shared | {
            "parent_root_id": None,
            "attempt": attempt,
            "backend": LEDGER_BACKEND,
            KEY_INSTANCE_KEY: _text(metadata, KEY_INSTANCE_KEY) or row_id,
            _KEY_GRAPH_HASH: _text(metadata, _KEY_GRAPH_HASH),
            "instance_inputs_json": _json_column(metadata, _KEY_INSTANCE_INPUTS),
            _KEY_ALLOW_TEST_FLAGS: int(bool(metadata.get(_KEY_ALLOW_TEST_FLAGS))),
            _KEY_BASE_COMMIT: _text(metadata, _KEY_BASE_COMMIT),
            _KEY_CONFIG_SIGNATURE: _text(metadata, _KEY_CONFIG_SIGNATURE),
            "coordination_json": _json_column(metadata, _KEY_COORDINATION),
            KEY_TERMINAL: _text(metadata, KEY_TERMINAL),
            "terminal_at": None,
        }
    if table is LedgerTable.ACTIVATIONS:
        return shared | {
            COLUMN_ROOT: root_id,
            _KEY_NODE: _text(metadata, _KEY_NODE) or "",
            _KEY_ROUND_NO: _integer(metadata, _KEY_ROUND_NO),
            "act_seq": _integer(metadata, KEY_SEQ),
            KEY_IDEMPOTENCY_KEY: _text(metadata, KEY_IDEMPOTENCY_KEY) or row_id,
            _KEY_LIFECYCLE: _text(metadata, _KEY_LIFECYCLE),
            "version": _FIRST_VERSION,
        }
    if table is LedgerTable.GATES:
        return shared | {
            COLUMN_ROOT: root_id,
            KEY_GATE_KEY: _text(metadata, KEY_GATE_KEY) or row_id,
            _KEY_STATE: _text(metadata, _KEY_STATE),
            _KEY_OUTCOME: _text(metadata, _KEY_OUTCOME),
            KEY_NONCE: _text(metadata, KEY_NONCE),
            _KEY_FINGERPRINT: _text(metadata, _KEY_FINGERPRINT),
            _KEY_BOUND_KEY: _text(metadata, _KEY_BOUND_KEY),
            _KEY_BOUND_VALUE: _text(metadata, _KEY_BOUND_VALUE),
            _KEY_ARTIFACT_REF: _text(metadata, _KEY_ARTIFACT_REF),
            _KEY_ARTIFACT_OID: _text(metadata, _KEY_ARTIFACT_OID),
            "version": _FIRST_VERSION,
        }
    return shared | {
        COLUMN_ROOT: root_id,
        _KEY_ACTIVATION_ID: _text(metadata, _KEY_ACTIVATION_ID),
        "kind": _text(metadata, KEY_WF_KIND),
        KEY_EVENT_KEY: _text(metadata, KEY_EVENT_KEY) or row_id,
        COLUMN_PAYLOAD: payload_json,
        "at": None,
    }


def hydrate(table: LedgerTable, row: sqlite3.Row, metadata: Metadata) -> StoreRow:
    """One database row as the neutral `StoreRow` the seam speaks."""
    payload = row[COLUMN_PAYLOAD] if ROW_KIND_OF_TABLE[table] is RowKind.EVENT else None
    return StoreRow(
        id=row[ID_COLUMN[table]],
        status=row[COLUMN_STATUS],
        kind=ROW_KIND_OF_TABLE[table],
        metadata=metadata,
        payload=payload,
        close_reason=row[COLUMN_CLOSE_REASON],
    )
