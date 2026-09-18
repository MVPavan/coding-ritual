"""Names, pragmas and messages of the run ledger (run-ledger §3.3–§3.6).

A sibling package rather than a module inside `bdio/`: the ledger is a second
backend with its own schema, fence, identity pin and CLI, and `bdio/` is the
seam every backend is used THROUGH. The dependency runs one way —
`workflow_interpreter.ledger` imports the neutral row and error vocabulary from
`bdio`, and nothing in `bdio` imports the ledger.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

LEDGER_DIR: Final[str] = ".wf"
LEDGER_FILE: Final[str] = "ledger.db"
EXPORT_DIR: Final[str] = "export"
EXPORT_SUFFIX: Final[str] = ".jsonl"
FENCE_FILE: Final[str] = "ledger.lock"
EXPORT_REF_TEMPLATE: Final[str] = "refs/wf/exports/{task_id}"
"""Where a task's export BLOB is pinned before its bead may close (§3.6).

Here rather than in `contractor/journal.py`, which writes it, because
`ledger/reverify.py` reads it as the anchor that says which export bytes the
closing merge actually recorded — and the ledger may not import the contractor."""
IGNORE_FILE: Final[str] = ".gitignore"
IGNORE_BODY: Final[str] = (
    "# Engine state (run-ledger \u00a73.5, D4): the database is this machine's.\n"
    "# Nothing else here is ignored \u2014 the exports are committed (\u00a73.6), and a\n"
    "# stray file under this directory is a coordinator's own work.\n"
    "/.gitignore\n"
    f"/{LEDGER_FILE}\n"
    f"/{LEDGER_FILE}-wal\n"
    f"/{LEDGER_FILE}-shm\n"
)
"""What makes \u00a73.5's "the working tree's IGNORED `.wf/`" true rather than
assumed: without it the database is untracked dirt and the coordinator
cleanliness checks refuse the next contractor command on the engine's own file.
The rule names the database and itself, never the directory: a file somebody
else put under `.wf/` must stay visible as the dirt it is."""
TASK_LOCK_DIR: Final[str] = "tasks"
TASK_LOCK_SUFFIX: Final[str] = ".lock"
"""`<wrapper_root>/tasks/<task_id>.lock` — the task-keyed reconcile lock of
§3.2.2, distinct from the root-keyed member locks in `bdio/coordination.py`."""

FENCE_WAIT_S: Final[float] = 5.0
"""How long an exclusive taker waits before naming the holders and refusing.
Bounded on purpose (§3.4.6): a silent retry loop would turn a live reader into
an unexplained hang in import, migration and restore."""
FENCE_POLL_S: Final[float] = 0.05
BUSY_TIMEOUT_MS: Final[int] = 5000
"""§3.4.1 — SQLite's own wait for a writer, in milliseconds."""

READ_ONLY_PRAGMAS: Final[tuple[str, ...]] = (
    f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}",
    "PRAGMA foreign_keys=ON",
)
"""What a `mode=ro` connection may set: `journal_mode` and `synchronous` are
writes to the database header, and a reader must not make one."""

PRAGMAS: Final[tuple[str, ...]] = (
    "PRAGMA journal_mode=WAL",
    f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA foreign_keys=ON",
)

PROC_LOCKS: Final[str] = "/proc/locks"
"""Where the kernel lists every `flock` holder, so a refusal can name pids."""


class LedgerTable(StrEnum):
    """Every table of §3.3, named once."""

    META = "meta"
    TASKS = "tasks"
    ROOTS = "roots"
    ACTIVATIONS = "activations"
    GATES = "gates"
    NONCES = "nonces"
    SIGNATURES = "signatures"
    EVENTS = "events"
    SESSIONS = "sessions"
    FINDINGS = "findings"
    ARTIFACTS = "artifacts"
    USAGE = "usage"
    LANDINGS = "landings"
    PROJECTIONS = "projections"
    RESTORE_PENDING = "restore_pending"


ROW_TABLES: Final[tuple[LedgerTable, ...]] = (
    LedgerTable.ROOTS,
    LedgerTable.ACTIVATIONS,
    LedgerTable.GATES,
    LedgerTable.EVENTS,
)
"""The tables holding a neutral `StoreRow` — the ones the read seam selects
over. The rest hold facts ABOUT those rows and are reached through them."""

GATE_TABLES: Final[tuple[LedgerTable, ...]] = (
    LedgerTable.NONCES,
    LedgerTable.SIGNATURES,
)
"""Task-owned rows keyed by `gate_id` rather than by `task_id`. They belong to
the task their gate belongs to, which is how the export validates them."""

EXPORT_TABLES: Final[tuple[LedgerTable, ...]] = (
    LedgerTable.TASKS,
    *ROW_TABLES,
    *GATE_TABLES,
    LedgerTable.PROJECTIONS,
)
"""What one task's export carries: every task-owned row. The nonces and
signatures are here because §3.6 re-verifies a task's approvals from the export
ALONE, and the projections because a restored task whose attention rows were
dropped would silently keep whatever label bd last carried. Order matters
twice: rows are inserted in it (a signature needs its gate) and cleared in
reverse. `restore_pending` is the one task-owned table deliberately left out:
it records what an import OWES rather than what an export describes, and
carrying it would break the byte-identical round trip (§3.6). The
per-activation facts stay out until S4 writes them."""


DERIVED_ACTIVATION_TABLES: Final[tuple[LedgerTable, ...]] = (
    LedgerTable.SESSIONS,
    LedgerTable.FINDINGS,
    LedgerTable.ARTIFACTS,
    LedgerTable.USAGE,
)
"""Rows ABOUT an activation that no export carries, cleared with it.

They reference `activations`, so a rebuild that emptied the exportable tables
around them would fail its own foreign keys (§3.6). Each is derived from the
record a close settles — `findings` from the evidence carrier the export DOES
carry — so a restored task re-derives them rather than losing anything the
export describes."""


TARGET_LEDGER: Final[str] = "the ledger"
"""What a refusal names when the failure is the database itself rather than
one row of it."""


class LedgerOperation(StrEnum):
    """What a failing statement was doing, for the refusal that names it."""

    READING = "reading"
    BEGINNING = "beginning a transaction on"
    CREATING = "creating"
    MERGING = "merging metadata into"
    CLOSING = "closing"
    CLOSING_GATE = "closing the gate"
    CLAIMING = "claiming"
    RECONCILING = "reconciling the attention projection of"


class MetaKey(StrEnum):
    """The `meta` keys pinned at creation (§3.5)."""

    SCHEMA_VERSION = "schema_version"
    REPO_HASH = "repo_hash"
    WRAPPER_ROOT = "wrapper_root"
    CREATED_AT = "created_at"


class ExportKey(StrEnum):
    """The keys of an export line — a header, then one row per line (§3.6)."""

    KIND = "kind"
    TABLE = "table"
    ROW = "row"
    SCHEMA_VERSION = "schema_version"
    REPO_HASH = "repo_hash"
    WRAPPER_ROOT = "wrapper_root"
    TASK_ID = "task_id"


EXPORT_KIND_HEADER: Final[str] = "header"
EXPORT_KIND_ROW: Final[str] = "row"

STATUS_OPEN: Final[str] = "open"
STATUS_CLOSED: Final[str] = "closed"

# --- refusals ---------------------------------------------------------------

MSG_FENCE_BUSY: Final[str] = (
    "the ledger fence {path} is held after {waited:.1f}s by {holders}; "
    "import, migration and restore need it exclusively (§3.4)"
)
MSG_FENCE_HOLDERS_UNKNOWN: Final[str] = "a process this host would not name"
MSG_NOT_A_REPOSITORY: Final[str] = (
    "{repo_root} has no .git entry, so the ledger fence has no git common "
    "directory to live in (§3.4)"
)
MSG_WRAPPER_ROOT_MISMATCH: Final[str] = (
    "ledger {path} is pinned to wrapper root {pinned}; this process runs under "
    "{found} — refusing, always, not only while roots are live (§3.5)"
)
MSG_REPO_HASH_MISMATCH: Final[str] = (
    "ledger {path} is pinned to repository {pinned}; this process runs against "
    "{found} (§3.5)"
)
MSG_LEDGER_ABSENT: Final[str] = (
    "no ledger to read at {path}: a read-only command never creates one (§3.4)"
)
MSG_SCHEMA_BEHIND: Final[str] = (
    "ledger {path} carries schema version {found}, and this build needs "
    "{known}; a read-only command never migrates (§3.4)"
)
MSG_SCHEMA_AHEAD: Final[str] = (
    "ledger {path} carries schema version {found}, and this build knows "
    "{known}; migrations are forward-only (§3.3)"
)
MSG_UNKNOWN_CARRIER: Final[str] = (
    "a row carrying wf_kind={kind!r} has no table in the ledger schema (§3.3)"
)
MSG_BUSY_REFUSED: Final[str] = (
    "the ledger stayed busy for {timeout_ms} ms while {operation} {row_id}; "
    "refusing rather than retrying silently (§3.4.6)"
)
MSG_CLAIM_ON_LEDGER: Final[str] = (
    "integration-target claims stay bd-backed while the bd backend exists "
    "(D20); the ledger refuses {operation} {row_id} rather than holding a "
    "second claim table a bd-backed run could not see"
)
MSG_LOSSY_ROW: Final[str] = "the row did not read back as written: {detail}"
MSG_ROW_MISSING: Final[str] = (
    "no ledger row {row_id!r} in task {task_id!r}, so there is nothing to {operation}"
)
MSG_GATE_NOT_OPEN: Final[str] = (
    "gate {gate_id!r} is {state!r} carrying approval {recorded!r}, and this "
    "close carries {incoming!r}; the decision already recorded wins (§3.3)"
)
MSG_NONCE_SPENT: Final[str] = (
    "nonce {nonce!r} was already consumed by gate {owner!r}; it cannot also "
    "close {gate_id!r} (§9)"
)
MSG_GATE_SIGNED: Final[str] = (
    "gate {gate_id!r} already holds a recorded signature, so this close would "
    "replace the trust §3.6 re-verifies from (D21)"
)
MSG_EXPORT_GATE_TASK: Final[str] = (
    "{path} line {number} carries a {table} row for gate {gate_id!r}, which "
    "the file does not declare as a gate of task {declared!r} (§3.6)"
)
MSG_NOT_A_GATE: Final[str] = (
    "row {row_id!r} is a {table} row; only a gate is closed with a nonce and "
    "a signature (§3.3)"
)
MSG_UNKNOWN_TASK: Final[str] = "no ledger rows exist for task {task_id!r}"
MSG_EXPORT_HEADER: Final[str] = (
    "{path} is not a ledger export: its first line is not a {kind!r} object"
)
MSG_EXPORT_ROW_KIND: Final[str] = (
    "{path} line {number} is not a {kind!r} object, so the import refuses "
    "whole rather than restoring part of it (§3.6)"
)
MSG_EXPORT_TABLE: Final[str] = (
    "{path} line {number} names table {table!r}, which is not one a task "
    "export may write into (§3.6)"
)
MSG_EXPORT_TASK_ROWS: Final[str] = (
    "{path} declares task {task_id!r} and carries {count} {table} rows; an "
    "export restores exactly the one task it declares (§3.6)"
)
MSG_EXPORT_TASK_MISMATCH: Final[str] = (
    "{path} line {number} carries task_id {found!r}, and the header declares "
    "{declared!r}; the import refuses whole rather than restoring a task the "
    "file does not name (§3.6)"
)
MSG_EXPORT_COLUMN: Final[str] = (
    "{path} line {number} gives table {table} a column {column!r} the schema "
    "does not have (§3.3)"
)
MSG_EXPORT_BLOB: Final[str] = (
    "{path} carries a value for column {column!r} that is not the base64 a "
    "stored BLOB travels as: {reason} (§3.6)"
)
MSG_IMPORT_LANDED: Final[str] = (
    "ledger {path} records {count} landing row(s), and no export carries the "
    "landing journal, so an import cannot rebuild it (§3.6); this is a KNOWN "
    "limitation of import, deliberately deferred, and NOT a corrupt ledger — "
    "nothing has been changed, and the landed tasks are intact"
)
MSG_BAD_FILTER_KEY: Final[str] = (
    "carrier filter key {key!r} is not a plain identifier, so it cannot name a "
    "JSON path"
)
