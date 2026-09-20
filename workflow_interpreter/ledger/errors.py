"""Typed failures of the ledger backend, under the neutral `StoreError` tree.

Every one of these is a `StoreError`, so a caller above the seam routes on what
went wrong without learning that SQLite exists — the same rule `bdio/errors.py`
states for bd's own shapes.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from typing import Final

from workflow_interpreter.bdio.errors import (
    LifecycleConflictError,
    StoreBusyRefusal,
    StoreConfigError,
    StoreError,
    StoreTransportError,
)
from workflow_interpreter.ledger.constants import (
    BUSY_TIMEOUT_MS,
    MSG_BUSY_REFUSED,
    MSG_FENCE_BUSY,
    MSG_FENCE_HOLDERS_UNKNOWN,
)

_BUSY_CODES: Final[frozenset[int]] = frozenset(
    {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}
)
"""SQLite's two contention codes: another writer holds the database, or
another connection holds a table in it."""


class LedgerFenceBusy(StoreError):
    """The exclusive fence could not be taken inside its bounded wait (§3.4).

    Carries the holders' pids rather than only saying "busy": the wait is
    bounded so that an operator learns WHICH process to look at.
    """

    def __init__(self, path: str, waited_s: float, holders: Sequence[int]) -> None:
        self.holders = tuple(holders)
        named = (
            ", ".join(f"pid {pid}" for pid in self.holders)
            if self.holders
            else MSG_FENCE_HOLDERS_UNKNOWN
        )
        super().__init__(
            MSG_FENCE_BUSY.format(path=path, waited=waited_s, holders=named)
        )


class LedgerIdentityError(StoreConfigError):
    """The database is pinned to another repository or wrapper root (§3.5)."""


class LedgerEpicMissing(StoreConfigError):
    """A `tasks` row was owed and no epic was supplied to write on it (§3.7).

    Its own class because it is a WIRING refusal, not a transport one: the
    lazy `_ensure_task` path serves runs that never went through prepare, and
    the answer is to prepare the task rather than to retry the write.
    """


class LedgerMintConflict(StoreConfigError):
    """A mint could not write the row for the id it was about to answer with (§3.7).

    Its own class, and a refusal rather than a silent answer, because the id a
    mint returns is spent immediately on a ref, a worktree and a run
    directory: an id whose `tasks` row was never written names a task nothing
    can later find by its tracker ref.
    """


class LedgerRootCollision(StoreConfigError):
    """Two carriers pin the same attempt of one task under different keys (§3.7).

    A WIRING refusal beside `LedgerEpicMissing`, deliberately NOT a transport
    defect: `<task>-a<n>` is minted from the attempt the carrier pins, so a
    second instance key pinning an attempt that already has a root is a
    caller that has invented an attempt, and no retry can make it land.
    """


class LedgerAttemptInvalid(StoreConfigError):
    """A carrier pins a run identity whose attempt is not one a run can have.

    Attempts are counted from one (`RunIdentity`, `ge=FIRST_ATTEMPT`), and a
    carrier that HAS an identity is making a statement about which attempt it
    is. Reading a bad one as "no identity" would file the root as a child of
    whatever attempt happened to be in force, so it refuses instead.
    """


class LedgerExportError(StoreConfigError):
    """An export file is not one this schema may restore from (§3.6).

    Its own class because the bytes are UNTRUSTED input: a line naming a table
    or a column the schema does not have is refused before any SQL is built,
    and the whole import refuses with it.
    """


class LedgerAbsent(StoreConfigError):
    """There is no ledger to read, and a read-only command never makes one."""


class LedgerSchemaError(StoreConfigError):
    """The schema on disk is not one this build can migrate forward (§3.3)."""


class LedgerWriteUnsupported(StoreError):
    """A carrier the §3.3 schema has no table for was handed to the store."""


class LedgerTransportError(StoreTransportError):
    """SQLite itself failed — the ledger's transport defect."""


class LedgerGateConflict(LifecycleConflictError):
    """Another decision already owns this gate, its nonce or its signature (§3.3).

    A `LifecycleConflictError` because that is what it IS above the seam — a
    write that contradicts the state already recorded — so the bd path's
    refusal for the same situation (`gates._repair_closed_gate`) and this one
    route identically. What only the ledger can add is that the refusal is
    decided INSIDE the closing transaction, so the loser of a real race writes
    neither a nonce nor a signature.
    """


class LedgerBusyRefusal(StoreBusyRefusal):
    """A writer waited out `busy_timeout` and REFUSED, rather than retrying.

    §3.4.6 makes this its own failure: a silent retry loop under heavy child
    concurrency turns contention into an unexplained hang, so the wait is
    bounded by the pragma and what follows is a named refusal an operator and
    a caller can both route on.
    """

    def __init__(self, operation: str, row_id: str, timeout_ms: int) -> None:
        self.operation = operation
        self.row_id = row_id
        super().__init__(
            MSG_BUSY_REFUSED.format(
                operation=operation, row_id=row_id, timeout_ms=timeout_ms
            )
        )


class LedgerRecordConflict(LifecycleConflictError):
    """A contractor transition was written against a record that has moved.

    The version guard of §3.2: every transition states the version it read,
    the write is conditional on it, and a mismatch is refused rather than
    applied over whatever the other writer decided. A conflict, not a
    transport failure — the ledger is fine, the caller's evidence is stale.
    """


class LedgerClaimHeld(LifecycleConflictError):
    """Another holder already claims this integration target (R11).

    The loser of the CAS inside `BEGIN IMMEDIATE`, named rather than silently
    queued: the two attempts contend for one target, and the one that did not
    get it has to be told so it can refuse rather than land twice.
    """


def sqlite_failure(
    exc: sqlite3.Error, *, operation: str, row_id: str
) -> LedgerBusyRefusal | LedgerTransportError:
    """The typed failure one SQLite error is, busy told apart from broken.

    Told apart by SQLite's own error code rather than by matching message
    text, so a wording change upstream cannot turn a refusal into a defect.
    """
    if getattr(exc, "sqlite_errorcode", None) in _BUSY_CODES:
        return LedgerBusyRefusal(operation, row_id, BUSY_TIMEOUT_MS)
    return LedgerTransportError(str(exc))


class LedgerRowMissing(LedgerTransportError):
    """No row of that id exists, which is bd's `show` failure by another name."""
