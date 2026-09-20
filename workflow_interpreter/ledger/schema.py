"""The §3.3 tables, and the forward-only migration crew that installs them.

Lossless by construction: every row keeps its whole carrier in `metadata_json`,
and the named columns are PROJECTIONS of that JSON for queries and constraints.
Two columns are not in §3.3's list and are here anyway — `status` and
`close_reason` — because the `StoreRow` the typed operations speak carries
them (`bdio/rows.py`).

The `-- dropped in v7` markers are deliberate: a migration is forward-only, so
the v1 statements keep the columns a v1 database really had, and v7 is where
they go. Reading them out of v1 would make every database that ever migrated
disagree with this file.

`meta` is key/value rather than one wide row: §3.5 pins repository identity
before any table is written, and a key/value table is the one shape a migration
can add a pin to without rewriting the row that guards migrations.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping
from contextlib import closing
from functools import cache
from typing import Final

from workflow_interpreter.ledger.constants import MSG_STATE_UNFOLDABLE
from workflow_interpreter.ledger.errors import LedgerSchemaError

_V1_META: Final[str] = """
CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
"""

_V1_TASKS: Final[str] = """
CREATE TABLE tasks (
    task_id     TEXT PRIMARY KEY,
    epic_id     TEXT NOT NULL,
    graph_id    TEXT,
    backend     TEXT NOT NULL,  -- dropped in v7
    next_seq    INTEGER NOT NULL,
    export_oid  TEXT,
    exported_at TEXT,
    created_at  TEXT NOT NULL
)
"""

_V1_ROOTS: Final[str] = """
CREATE TABLE roots (
    root_id              TEXT PRIMARY KEY,
    task_id              TEXT NOT NULL REFERENCES tasks(task_id),
    seq                  INTEGER NOT NULL,
    parent_root_id       TEXT,
    attempt              INTEGER NOT NULL,
    backend              TEXT NOT NULL,  -- dropped in v7
    instance_key         TEXT NOT NULL UNIQUE,
    graph_content_hash   TEXT,
    instance_inputs_json TEXT,
    allow_test_flags     INTEGER NOT NULL DEFAULT 0,
    instance_base_commit TEXT,
    config_signature     TEXT,
    coordination_json    TEXT,
    terminal             TEXT,
    terminal_at          TEXT,
    status               TEXT NOT NULL,
    close_reason         TEXT,
    metadata_json        TEXT NOT NULL
)
"""

_V1_ACTIVATIONS: Final[str] = """
CREATE TABLE activations (
    activation_id   TEXT PRIMARY KEY,
    task_id         TEXT NOT NULL REFERENCES tasks(task_id),
    seq             INTEGER NOT NULL,
    root_id         TEXT NOT NULL REFERENCES roots(root_id),
    node            TEXT NOT NULL,
    round_no        INTEGER NOT NULL,
    act_seq         INTEGER NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    lifecycle       TEXT,
    version         INTEGER NOT NULL DEFAULT 1,
    status          TEXT NOT NULL,
    close_reason    TEXT,
    metadata_json   TEXT NOT NULL
)
"""

_V1_GATES: Final[str] = """
CREATE TABLE gates (
    gate_id              TEXT PRIMARY KEY,
    task_id              TEXT NOT NULL REFERENCES tasks(task_id),
    seq                  INTEGER NOT NULL,
    root_id              TEXT NOT NULL REFERENCES roots(root_id),
    gate_key             TEXT NOT NULL,
    state                TEXT,
    outcome              TEXT,
    nonce                TEXT,
    verified_fingerprint TEXT,
    bound_key            TEXT,
    bound_value          TEXT,
    artifact_ref         TEXT,
    artifact_oid         TEXT,
    version              INTEGER NOT NULL DEFAULT 1,
    status               TEXT NOT NULL,
    close_reason         TEXT,
    metadata_json        TEXT NOT NULL,
    UNIQUE (root_id, gate_key)
)
"""

_V1_NONCES: Final[str] = """
CREATE TABLE nonces (
    nonce       TEXT PRIMARY KEY,
    gate_id     TEXT NOT NULL REFERENCES gates(gate_id),
    consumed_at TEXT NOT NULL
)
"""

_V1_SIGNATURES: Final[str] = """
CREATE TABLE signatures (
    gate_id               TEXT PRIMARY KEY REFERENCES gates(gate_id),
    payload_bytes         BLOB NOT NULL,
    signature_bytes       BLOB NOT NULL,
    signer_fingerprint    TEXT NOT NULL,
    allowed_signers_entry TEXT NOT NULL,
    policy_json           TEXT NOT NULL
)
"""

_V1_EVENTS: Final[str] = """
CREATE TABLE events (
    event_id      TEXT PRIMARY KEY,
    task_id       TEXT NOT NULL REFERENCES tasks(task_id),
    seq           INTEGER NOT NULL,
    root_id       TEXT NOT NULL REFERENCES roots(root_id),
    activation_id TEXT,
    kind          TEXT,
    event_key     TEXT NOT NULL,
    payload_json  TEXT,
    at            TEXT,
    status        TEXT NOT NULL,
    close_reason  TEXT,
    metadata_json TEXT NOT NULL,
    UNIQUE (root_id, event_key)
)
"""

_V1_SESSIONS: Final[str] = """
CREATE TABLE sessions (
    activation_id TEXT PRIMARY KEY REFERENCES activations(activation_id),
    backend       TEXT NOT NULL,  -- dropped in v7
    thread_id     TEXT,
    registered_at TEXT,
    completed_at  TEXT
)
"""

_V1_FINDINGS: Final[str] = """
CREATE TABLE findings (
    activation_id TEXT NOT NULL REFERENCES activations(activation_id),
    round_no      INTEGER NOT NULL,
    severity      TEXT NOT NULL,
    text          TEXT NOT NULL
)
"""

_V1_ARTIFACTS: Final[str] = """
CREATE TABLE artifacts (
    activation_id TEXT NOT NULL REFERENCES activations(activation_id),
    kind          TEXT NOT NULL,
    git_ref       TEXT NOT NULL,
    oid           TEXT NOT NULL,
    path_in_ref   TEXT,
    sha256        TEXT
)
"""

_V1_USAGE: Final[str] = """
CREATE TABLE usage (
    activation_id TEXT PRIMARY KEY REFERENCES activations(activation_id),
    tokens_in     INTEGER,
    tokens_out    INTEGER,
    cost_json     TEXT
)
"""

_V1_LANDINGS: Final[str] = """
CREATE TABLE landings (
    task_id     TEXT NOT NULL REFERENCES tasks(task_id),
    attempt     INTEGER NOT NULL,
    phase       TEXT NOT NULL,
    record_json TEXT NOT NULL,
    written_at  TEXT NOT NULL,
    UNIQUE (task_id, attempt, phase)
)
"""

_V1_PROJECTIONS: Final[str] = """
CREATE TABLE projections (
    task_id    TEXT NOT NULL REFERENCES tasks(task_id),
    generation INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    acked_at   TEXT,
    UNIQUE (task_id, generation)
)
"""

_V1_RESTORE_PENDING: Final[str] = """
CREATE TABLE restore_pending (
    task_id      TEXT PRIMARY KEY REFERENCES tasks(task_id),
    requested_at TEXT NOT NULL
)
"""
"""The drain an import owes every task it restores (§3.2), deliberately OUTSIDE
the exportable tables: a restore that journalled a `projections` row would spend
a sequence number and change the very bytes §3.6 requires an export→import→export
round trip to preserve. The reconciler treats a row here exactly as it treats an
unacked generation, and retires it in the same ack step."""

_V1_INDEXES: Final[tuple[str, ...]] = (
    "CREATE INDEX roots_by_task ON roots(task_id, seq)",
    "CREATE INDEX activations_by_root ON activations(root_id, act_seq)",
    "CREATE INDEX activations_by_task ON activations(task_id, seq)",
    "CREATE INDEX gates_by_root ON gates(root_id, seq)",
    "CREATE INDEX gates_by_task ON gates(task_id, seq)",
    "CREATE INDEX events_by_root ON events(root_id, seq)",
    "CREATE INDEX events_by_task ON events(task_id, seq)",
)

_V2_FINDINGS_KIND: Final[str] = (
    "ALTER TABLE findings ADD COLUMN kind TEXT NOT NULL DEFAULT 'diagnostic'"
)
"""§3.3's `findings` rows gained a second author. The reviewer's own numbered
findings are stored bounded and normalised (line endings, invalid UTF-8
replaced) as `kind = 'review'`; the rows derived from the
close carriers keep the default, which is also what any row written before
this migration was."""

_V3_TASKS_STATE: Final[str] = "ALTER TABLE tasks ADD COLUMN state TEXT"
"""How far the CONTRACTOR got with this task, as the ledger knows it
(store-restructure §3.5, R6): `landed`, `abandoned`, or nothing yet.

`closed()` is derived from LANDED plus a resolving anchor, so the state has to
be a ledger fact that the EXPORT carries — a task rebuilt in a clone has no
other way to say that its work landed. It is deliberately not the contractor's
whole lifecycle: S4 moves the record itself into `contractor_records`, and this
column is what that table's `state` becomes."""

_V4_TASKS_TRACKER: Final[tuple[str, ...]] = (
    "ALTER TABLE tasks ADD COLUMN tracker_ref TEXT",
    "ALTER TABLE tasks ADD COLUMN tracker_kind TEXT",
    "CREATE UNIQUE INDEX tasks_by_tracker ON tasks(tracker_ref, tracker_kind)",
)
"""The foreign id `task_id` was minted from, and which tracker minted it
(store-restructure §3.7, R8).

UNIQUE over the PAIR, which is the key the mint dedupes on: two trackers can
mint the same string, so a unique index on the ref alone would let bd's `X-1`
block GitHub's `X-1` from ever getting a row — while the lookup, keyed by both,
went on answering "no such task" (found in review). Nullable because a run
under no tracker at all has no foreign id, and SQLite's unique index admits any
number of rows with a NULL in the pair, which is exactly that rule."""

_V4_ROOTS_CHILD: Final[str] = (
    "ALTER TABLE roots ADD COLUMN child_no INTEGER NOT NULL DEFAULT 0"
)
"""Which non-attempt root of its attempt this is — `0` for the attempt root
itself (§3.7).

A column rather than a number parsed back out of `<task>-a<n>-c<m>`: the
ordinal is minted in the creating transaction and is the one thing keeping two
roots of one task distinct now that the attempt comes from the carrier instead
of from a count of the task's roots."""

_V5_CONTRACTOR_RECORDS: Final[str] = """
CREATE TABLE contractor_records (
    task_id     TEXT PRIMARY KEY REFERENCES tasks(task_id),
    state       TEXT NOT NULL,
    attempt     INTEGER NOT NULL,
    version     INTEGER NOT NULL,
    root_id     TEXT,
    brief       TEXT,
    record_json TEXT NOT NULL,
    updated_at  TEXT NOT NULL
)
"""
"""The contractor's own record, in the ledger rather than in bead metadata
(store-restructure §3.2, R4).

`record_json` is the whole carrier and the named columns are PROJECTIONS of it,
exactly as `roots` and `gates` are: `state` is what `closed()` gates on, and a
query that had to parse JSON to ask "did this land?" would be a second reading
of the same fact. `version` is the guard — every transition states the version
it read, so a stale writer is refused by name rather than overwriting a record
that moved on.

`root_id` is the attempt root the record names, projected so that the one
query that runs the other way — "which task owns this root?", which replacement
discovery asks — is a lookup rather than a scan of every carrier.

`brief` is the task brief snapshotted at prepare. It is here because admission
must run with the tracker unreachable (R4): the brief is the one instance input
the contractor graph requires, and re-reading it from the tracker at every
admission is what made an offline retry impossible."""

_V5_CLAIMS: Final[str] = """
CREATE TABLE claims (
    claim_key    TEXT PRIMARY KEY,
    holder       TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    claimed_at   TEXT NOT NULL
)
"""
"""Ledger-local CAS for the integration-target claim (§3.2, R11).

The PRIMARY KEY is the serialisation point: two attempts aiming at one target
contend on one row inside `BEGIN IMMEDIATE`, and the loser learns it lost. Not
a git ref, because there is one ledger per repository and a claim that outlived
the ledger is one nobody can see; not exported, because a claim is contention
state about a target rather than a fact about a task."""

_V5_TASKS_STATE_FOLDED: Final[str] = "ALTER TABLE tasks DROP COLUMN state"
"""S2's `tasks.state` folded into `contractor_records.state` (§3.5).

One home for LANDED and ABANDONED. The column was always described as "what
that table's `state` becomes", and two columns that had to agree about whether
a task landed would be the next place they disagree. Dropped rather than left
behind under R12's clean break: no live ledger and no committed export exist,
so there is nothing to read a stale copy — and a database that disagrees is
refused by `_refuse_unfoldable_state` rather than quietly losing the state."""

_V7_DROP_BACKEND: Final[tuple[str, ...]] = (
    "ALTER TABLE tasks DROP COLUMN backend",
    "ALTER TABLE roots DROP COLUMN backend",
    "ALTER TABLE sessions DROP COLUMN backend",
)
"""S6's cutover: the ledger is the only record store, so nothing is pinned.

Three columns, one per table that carried a pin. `tasks.backend` and
`roots.backend` were the locator's two answers to "which store owns this?"
(D18) and there is one store to own it now (R1); `sessions.backend` named the
same thing for a table this build has never written.

This CHANGES the export bytes — `tasks` and `roots` rows lose a column — so a
file written by a v6 build no longer round-trips against a v7 one. R12's clean
break is what makes that safe: no committed export and no live ledger exists,
and the release note says so.
"""

_V6_TRACKER_OUTBOX: Final[tuple[str, ...]] = (
    """
CREATE TABLE tracker_outbox (
    outbox_id   INTEGER PRIMARY KEY,
    task_id     TEXT NOT NULL,
    intent_key  TEXT NOT NULL,
    intent_json TEXT NOT NULL,
    enqueued_at TEXT NOT NULL,
    applied_at  TEXT,
    result      TEXT
)
""",
    (
        "CREATE UNIQUE INDEX tracker_outbox_pending "
        "ON tracker_outbox(intent_key) WHERE applied_at IS NULL"
    ),
)
"""Intents awaiting a tracker that can answer (store-restructure §3.3, R2).

The unique index is PARTIAL, and that is the whole design: an intent is a
desired STATE, so at most one unapplied row may exist per key and a second
enqueue replaces it rather than queueing a second write. Applied rows keep
their key freely, so the same task can be flagged, unflagged and flagged again.

The key is a plain rowid alias, not `AUTOINCREMENT`: rows here are retired in
place and never deleted, so there is no id to reuse — and `AUTOINCREMENT`
creates SQLite's own `sqlite_sequence` table, which §3.6's schema-derived
completeness check would then have to account for as an engine table.

`task_id` is not a foreign key into `tasks`: the release of a claim on a task
whose row a failed prepare never wrote is still a write the mirror owes.
Deliberately non-exported (§3.6) — it records what THIS checkout owes its
tracker, which is neither a fact about the task nor true in the clone that
rebuilds from the file."""

_SQL_V4_STATED_TASKS: Final[str] = (
    "SELECT task_id, state FROM tasks WHERE state IS NOT NULL ORDER BY task_id"
)


def _refuse_unfoldable_state(connection: sqlite3.Connection) -> None:
    """Refuse the v5 fold on a v4 row whose state nothing could carry (R6).

    `contractor_records` needs a whole contractor carrier, and v4's `tasks`
    holds none of its identity — so a LANDED row cannot be rebuilt as a record,
    and dropping its state would leave a task with a latched `export_oid`
    reading OPEN for ever (`closure.closed` asks the LANDED gate first). R12's
    clean break says no such database exists; this is what happens when one
    does, instead of the reopening R6 promises cannot happen.
    """
    for row in connection.execute(_SQL_V4_STATED_TASKS).fetchall():
        raise LedgerSchemaError(
            MSG_STATE_UNFOLDABLE.format(task_id=str(row[0]), state=str(row[1]))
        )


_MIGRATION_GUARDS: Final[Mapping[int, Callable[[sqlite3.Connection], None]]] = {
    4: _refuse_unfoldable_state
}
"""What must be TRUE of the database before migration `n` may run.

Beside `MIGRATIONS` rather than inside it, because a guard is a question and
the tuples are statements; keying by index keeps the two orders one order."""

MIGRATIONS: Final[tuple[tuple[str, ...], ...]] = (
    (
        _V1_META,
        _V1_TASKS,
        _V1_ROOTS,
        _V1_ACTIVATIONS,
        _V1_GATES,
        _V1_NONCES,
        _V1_SIGNATURES,
        _V1_EVENTS,
        _V1_SESSIONS,
        _V1_FINDINGS,
        _V1_ARTIFACTS,
        _V1_USAGE,
        _V1_LANDINGS,
        _V1_PROJECTIONS,
        _V1_RESTORE_PENDING,
        *_V1_INDEXES,
    ),
    (_V2_FINDINGS_KIND,),
    (_V3_TASKS_STATE,),
    (*_V4_TASKS_TRACKER, _V4_ROOTS_CHILD),
    (_V5_CONTRACTOR_RECORDS, _V5_CLAIMS, _V5_TASKS_STATE_FOLDED),
    _V6_TRACKER_OUTBOX,
    _V7_DROP_BACKEND,
)
"""One tuple of statements per schema version, in order. Index `n` migrates a
database at version `n` to version `n + 1`, so `len(MIGRATIONS)` IS the version
this build knows, and `SCHEMA_VERSION` is derived from it rather than declared
beside it, so a migration can never be added without moving the version."""

SCHEMA_VERSION: Final[int] = len(MIGRATIONS)
"""The version `meta.schema_version` pins; migrations are forward-only."""


def apply_migrations(connection: sqlite3.Connection, current: int) -> int:
    """Run every migration after `current`, returning the version reached.

    The caller holds the exclusive fence (§3.4) and owns the transaction: a
    migration and the `schema_version` write that records it must land or fail
    together.

    A migration's guard runs immediately before it, inside that transaction, so
    a refusal leaves the database exactly at the version it arrived with.
    """
    for version, statements in enumerate(MIGRATIONS[current:], start=current):
        guard = _MIGRATION_GUARDS.get(version)
        if guard is not None:
            guard(connection)
        for statement in statements:
            connection.execute(statement)
    return len(MIGRATIONS)


_SQL_TABLE_NAMES: Final[str] = "SELECT name FROM sqlite_master WHERE type = 'table'"
_SQL_COLUMN_NAMES: Final[str] = "SELECT name FROM pragma_table_info(?)"


@cache
def table_columns() -> Mapping[str, frozenset[str]]:
    """Every column name this build's migrations create, per table.

    Built by RUNNING the migrations into an in-memory database rather than by
    parsing their text or by restating them: the import path checks untrusted
    column names against this, and an allowlist that could drift from the
    schema it guards would not be one (§3.6).
    """
    with closing(sqlite3.connect(":memory:")) as connection:
        apply_migrations(connection, 0)
        tables = [str(row[0]) for row in connection.execute(_SQL_TABLE_NAMES)]
        return {
            name: frozenset(
                str(row[0]) for row in connection.execute(_SQL_COLUMN_NAMES, (name,))
            )
            for name in tables
        }
