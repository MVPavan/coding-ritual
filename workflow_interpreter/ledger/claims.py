"""The integration-target claim, as one ledger row two attempts contend for.

R11: claims stay ledger-local. There is one ledger per repository — linked
worktrees are refused (`foreman/config.py`) — so the row IS the serialisation
point, and a claim held in a git ref would outlive the ledger that is the only
thing able to say whose it was.

The CAS is the PRIMARY KEY inside `BEGIN IMMEDIATE`: the first claim of a
target is an INSERT that either lands or loses, so two attempts that both read
"free" cannot both proceed. A TRANSFER — a retry inheriting the target from the
attempt before it — names the row it is replacing and is an UPDATE, because
the caller has already proved, under the target lock, that the claim it is
moving is its own.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Final

from workflow_interpreter.bdio.claims import ClaimRecord
from workflow_interpreter.bdio.wire import Metadata
from workflow_interpreter.ledger.constants import MSG_CLAIM_HELD, LedgerOperation
from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.ledger.errors import LedgerClaimHeld, sqlite_failure

_SQL_READ: Final[str] = (
    "SELECT claim_key, holder, payload_json FROM claims WHERE claim_key = ?"
)
_SQL_INSERT: Final[str] = (
    "INSERT INTO claims (claim_key, holder, payload_json, claimed_at) "
    "VALUES (?, ?, ?, ?)"
)
_SQL_REPLACE: Final[str] = (
    "UPDATE claims SET holder = ?, payload_json = ?, claimed_at = ? "
    "WHERE claim_key = ? AND holder = ?"
)


class LedgerClaims:
    """The claims surface of one ledger — read, claim, or transfer."""

    def __init__(self, database: LedgerDatabase) -> None:
        self._database = database

    def find(self, key: str) -> tuple[ClaimRecord, ...]:
        """The claim on this target, as nought or one row.

        A tuple rather than an optional because the caller decides what more
        than one means; the primary key means there can never be more than
        one here, and that is the property this table was chosen for.
        """
        with self._database.locked() as connection:
            row = connection.execute(_SQL_READ, (key,)).fetchone()
        if row is None:
            return ()
        payload: Metadata = json.loads(str(row[2]))
        return (ClaimRecord(id=str(row[0]), holder=str(row[1]), payload=payload),)

    def write(
        self,
        key: str,
        holder: str,
        payload: Metadata,
        expected_holder: str | None = None,
    ) -> None:
        """Claim this target, or move the claim the caller read and still owns.

        `expected_holder` is what tells the two apart: nothing means "I read no
        claim", which is the one write that has to lose a race, and a named
        holder means "I read THIS claim and I am moving it" — guarded, inside
        the same `BEGIN IMMEDIATE`, against the holder having changed since.
        """
        encoded = json.dumps(payload, sort_keys=True)
        stamped = datetime.now(tz=UTC).isoformat()
        with self._database.transaction() as connection:
            if expected_holder is not None:
                self._replace(
                    connection, key, holder, encoded, stamped, expected_holder
                )
                return
            try:
                connection.execute(_SQL_INSERT, (key, holder, encoded, stamped))
            except sqlite3.IntegrityError as held:
                found = connection.execute(_SQL_READ, (key,)).fetchone()
                raise LedgerClaimHeld(
                    MSG_CLAIM_HELD.format(
                        claim_key=key,
                        holder="an unreadable claim"
                        if found is None
                        else str(found[1]),
                        incoming=holder,
                    )
                ) from held
            except sqlite3.Error as failure:
                raise sqlite_failure(
                    failure, operation=LedgerOperation.CLAIMING.value, row_id=key
                ) from failure

    @staticmethod
    def _replace(
        connection: sqlite3.Connection,
        key: str,
        holder: str,
        encoded: str,
        stamped: str,
        expected_holder: str,
    ) -> None:
        """Move the claim the caller read, refusing any other holder.

        The holder is the guard, in the WHERE clause, so the check and the
        write are one statement: a transfer written from a stale read is
        refused NAMING whoever holds the target now, instead of silently
        overwriting a claim it never saw.
        """
        updated = connection.execute(
            _SQL_REPLACE, (holder, encoded, stamped, key, expected_holder)
        )
        if updated.rowcount == 0:
            found = connection.execute(_SQL_READ, (key,)).fetchone()
            raise LedgerClaimHeld(
                MSG_CLAIM_HELD.format(
                    claim_key=key,
                    holder="nobody" if found is None else str(found[1]),
                    incoming=holder,
                )
            )
