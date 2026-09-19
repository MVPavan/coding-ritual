"""Minting one task's identity: the id, its epic, and the foreign id it came from.

The ledger mints `task_id`; `tasks.tracker_ref` + `tasks.tracker_kind` hold the
foreign id the tracker knows the work by (§3.7, R8). The two are separate
because the tracker's id is not ours to spend: `gh#123` is a perfectly good
GitHub issue and a name neither a path component nor a git ref can hold, while
`task_id` reaches `refs/wf/exports/<task>`, a worktree path, the
`docs/workstreams/<epic>/runs/<task>/a<n>` grant boundary and `WF_TASK_ID`.

For bd the two are the same string — a bead id already satisfies the grammar —
so no existing id, ref or `WF_*` value moves when this lands.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Final

from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.contracts.run_identity import (
    LOCK_SUFFIX,
    TRAVERSAL,
    ComponentKind,
    InvalidIdentifier,
    safe_component,
)
from workflow_interpreter.ledger.constants import (
    MSG_TRACKER_REF_UNUSABLE,
    TrackerKind,
)
from workflow_interpreter.ledger.database import LedgerDatabase

FIRST_SEQ: Final[int] = 1
SQL_INSERT_TASK: Final[str] = (
    "INSERT OR IGNORE INTO tasks "
    "(task_id, epic_id, graph_id, backend, next_seq, created_at, "
    "tracker_ref, tracker_kind) "
    "VALUES (?, ?, NULL, ?, ?, ?, ?, ?)"
)
"""The one statement that writes a `tasks` row — the mint below and the
locator's pin (`tasks.pin_task_backend`) are its only two callers."""

_SQL_BY_TRACKER_REF: Final[str] = (
    "SELECT task_id FROM tasks WHERE tracker_ref = ? AND tracker_kind = ?"
)
_SQL_BY_TASK_ID: Final[str] = "SELECT 1 FROM tasks WHERE task_id = ?"

_SAFE_CHARACTERS: Final[frozenset[str]] = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-"
)
_REPLACEMENT: Final[str] = "-"
_DOT: Final[str] = "."
_FIRST_SUFFIX: Final[int] = 2
"""A collision suffix starts at two: the unsuffixed stem IS the first one."""


def insert_task(
    connection: sqlite3.Connection,
    *,
    task_id: str,
    epic_id: str,
    backend: BackendKind,
    tracker_ref: str | None = None,
    tracker_kind: TrackerKind | None = None,
) -> None:
    """Write one `tasks` row if the task has none, on an open connection."""
    connection.execute(
        SQL_INSERT_TASK,
        (
            task_id,
            epic_id,
            backend.value,
            FIRST_SEQ,
            datetime.now(tz=UTC).isoformat(),
            tracker_ref,
            None if tracker_kind is None else tracker_kind.value,
        ),
    )


def sanitise_tracker_ref(tracker_ref: str) -> str:
    """The grammar-safe stem a foreign id mints its task id from.

    Every character the grammar does not admit becomes `-`, the traversal is
    collapsed, a `.lock` tail is dropped and any leading punctuation is cut,
    because each of those is a form the charset alone would pass and git or a
    path would then refuse. A ref that holds nothing usable is refused by
    name rather than mapped onto some default that two refs could share.
    """
    mapped = "".join(
        character if character in _SAFE_CHARACTERS else _REPLACEMENT
        for character in tracker_ref
    )
    while TRAVERSAL in mapped:
        mapped = mapped.replace(TRAVERSAL, _DOT)
    while mapped.endswith(LOCK_SUFFIX):
        mapped = mapped[: -len(LOCK_SUFFIX)]
    stem = mapped.lstrip("._-")
    if not stem:
        raise InvalidIdentifier(
            MSG_TRACKER_REF_UNUSABLE.format(tracker_ref=tracker_ref)
        )
    return safe_component(stem, kind=ComponentKind.TRACKER_REF)


def mint_task(
    database: LedgerDatabase,
    *,
    tracker_ref: str,
    tracker_kind: TrackerKind,
    epic_id: str,
    backend: BackendKind = BackendKind.LEDGER,
) -> str:
    """Mint this tracker ref's task id, or answer with the one it already has.

    Idempotent by the foreign id: preparing the same issue twice is one task,
    which is what makes a retried prepare safe. The collision suffix is chosen
    INSIDE the writing transaction, so two processes preparing two issues that
    sanitise alike cannot both read "free" and then both insert it.

    The epic and the stem are validated BEFORE the transaction opens: a
    component a path could not hold must not reach a row, a ref or a worktree,
    and there is nothing to roll back if it never got that far.
    """
    epic = safe_component(epic_id, kind=ComponentKind.EPIC)
    stem = sanitise_tracker_ref(tracker_ref)
    with database.transaction() as connection:
        existing = connection.execute(
            _SQL_BY_TRACKER_REF, (tracker_ref, tracker_kind.value)
        ).fetchone()
        if existing is not None:
            return str(existing[0])
        task_id = _free_task_id(connection, stem)
        insert_task(
            connection,
            task_id=task_id,
            epic_id=epic,
            backend=backend,
            tracker_ref=tracker_ref,
            tracker_kind=tracker_kind,
        )
    return task_id


def _free_task_id(connection: sqlite3.Connection, stem: str) -> str:
    """The stem, or the first `<stem>-<n>` no task holds, inside the transaction."""
    candidate = stem
    suffix = _FIRST_SUFFIX
    while connection.execute(_SQL_BY_TASK_ID, (candidate,)).fetchone() is not None:
        candidate = f"{stem}{_REPLACEMENT}{suffix}"
        suffix += 1
    return candidate
