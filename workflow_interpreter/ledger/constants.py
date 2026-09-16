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

FENCE_WAIT_S: Final[float] = 5.0
"""How long an exclusive taker waits before naming the holders and refusing.
Bounded on purpose (§3.4.6): a silent retry loop would turn a live reader into
an unexplained hang in import, migration and restore."""
FENCE_POLL_S: Final[float] = 0.05
BUSY_TIMEOUT_MS: Final[int] = 5000
"""§3.4.1 — SQLite's own wait for a writer, in milliseconds."""

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


ROW_TABLES: Final[tuple[LedgerTable, ...]] = (
    LedgerTable.ROOTS,
    LedgerTable.ACTIVATIONS,
    LedgerTable.GATES,
    LedgerTable.EVENTS,
)
"""The tables holding a neutral `StoreRow` — the ones the read seam selects
over. The rest hold facts ABOUT those rows and are reached through them."""

EXPORT_TABLES: Final[tuple[LedgerTable, ...]] = (
    LedgerTable.TASKS,
    *ROW_TABLES,
)
"""What one task's export carries in S1. The remaining §3.3 tables are written
by S2 and join this tuple with the writes that fill them."""


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
MSG_SCHEMA_AHEAD: Final[str] = (
    "ledger {path} carries schema version {found}, and this build knows "
    "{known}; migrations are forward-only (§3.3)"
)
MSG_UNKNOWN_CARRIER: Final[str] = (
    "a row carrying wf_kind={kind!r} has no table in the ledger schema (§3.3)"
)
MSG_NO_WRITE_SURFACE: Final[str] = (
    "the ledger backend implements reads and row creation only; {operation} "
    "lands with the S2 write surface"
)
MSG_LOSSY_ROW: Final[str] = "the row did not read back as written: {detail}"
MSG_UNKNOWN_TASK: Final[str] = "no ledger rows exist for task {task_id!r}"
MSG_EXPORT_HEADER: Final[str] = (
    "{path} is not a ledger export: its first line is not a {kind!r} object"
)
MSG_BAD_FILTER_KEY: Final[str] = (
    "carrier filter key {key!r} is not a plain identifier, so it cannot name a "
    "JSON path"
)
