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


class LedgerExportError(StoreConfigError):
    """An export file is not one this schema may restore from (§3.6).

    Its own class because the bytes are UNTRUSTED input: a line naming a table
    or a column the schema does not have is refused before any SQL is built,
    and the whole import refuses with it.
    """


class LedgerImportUnsupported(StoreConfigError):
    """This ledger holds state an import cannot rebuild, so it refuses whole.

    Today that is the landing journal: `landings` is outside `EXPORT_TABLES`,
    so no export carries it and the rebuild could not put it back. A KNOWN,
    deferred limitation of import — not a damaged ledger — and its own class so
    an operator and a caller both route on it rather than on a foreign-key
    message from inside a rolled-back transaction.
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


class LedgerClaimUnsupported(StoreError):
    """Claims are bd-backed while the bd backend exists (D20).

    Not a missing feature: two backends discovering claims in two stores
    cannot see each other's reservations, so the ledger REFUSES the write
    instead of keeping a second, invisible claim table.
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
