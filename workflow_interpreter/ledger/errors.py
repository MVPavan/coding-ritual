"""Typed failures of the ledger backend, under the neutral `StoreError` tree.

Every one of these is a `StoreError`, so a caller above the seam routes on what
went wrong without learning that SQLite exists — the same rule `bdio/errors.py`
states for bd's own shapes.
"""

from __future__ import annotations

from collections.abc import Sequence

from workflow_interpreter.bdio.errors import (
    StoreConfigError,
    StoreError,
    StoreTransportError,
)
from workflow_interpreter.ledger.constants import (
    MSG_FENCE_BUSY,
    MSG_FENCE_HOLDERS_UNKNOWN,
)


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


class LedgerSchemaError(StoreConfigError):
    """The schema on disk is not one this build can migrate forward (§3.3)."""


class LedgerWriteUnsupported(StoreError):
    """A write surface S1 does not implement was called (S2 delivers it)."""


class LedgerTransportError(StoreTransportError):
    """SQLite itself failed — the ledger's transport defect."""


class LedgerRowMissing(LedgerTransportError):
    """No row of that id exists, which is bd's `show` failure by another name."""
