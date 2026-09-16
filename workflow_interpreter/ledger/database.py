"""One process, one connection, one fence hold — the ledger's open path (§3.4).

Opening a ledger is four things in a fixed order, and the order is the point:

1. migrate first, under the EXCLUSIVE fence, so two first starts cannot both
   create and no reader sees a half-built schema;
2. then take the SHARED fence and hold it for the life of the connection;
3. apply the §3.4.1 pragmas;
4. verify the `repo_hash` and `wrapper_root` pins (§3.5) before answering
   anything.

Migration cannot happen while this process holds the shared fence: `flock` is
per open file description, so a second descriptor asking for `LOCK_EX` would
block on our own `LOCK_SH`. Hence the peek-then-migrate-then-hold order.

A store method is one transaction, and no subprocess, file I/O or bd call may
happen inside one (§3.4.2) — `transaction()` is deliberately the smallest thing
that can hold that rule.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import AbstractContextManager, closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Final, Self

import structlog

from workflow_interpreter.ledger.constants import (
    MSG_REPO_HASH_MISMATCH,
    MSG_SCHEMA_AHEAD,
    MSG_WRAPPER_ROOT_MISMATCH,
    PRAGMAS,
    TARGET_LEDGER,
    LedgerOperation,
    LedgerTable,
    MetaKey,
)
from workflow_interpreter.ledger.errors import (
    LedgerIdentityError,
    LedgerSchemaError,
    LedgerTransportError,
    sqlite_failure,
)
from workflow_interpreter.ledger.fence import LedgerFence
from workflow_interpreter.ledger.paths import fence_path, ledger_path, repo_hash
from workflow_interpreter.ledger.schema import SCHEMA_VERSION, apply_migrations

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

_SQL_META_READ: Final[str] = "SELECT value FROM meta WHERE key = ?"
_SQL_META_WRITE: Final[str] = "INSERT INTO meta (key, value) VALUES (?, ?)"
_SQL_META_UPSERT: Final[str] = (
    "INSERT INTO meta (key, value) VALUES (?, ?) "
    "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
)
_SQL_TABLE_PRESENT: Final[str] = (
    "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = ?"
)
_BEGIN: Final[str] = "BEGIN IMMEDIATE"
_BEGIN_READ: Final[str] = "BEGIN DEFERRED"
_COMMIT: Final[str] = "COMMIT"
_ROLLBACK: Final[str] = "ROLLBACK"
_NO_VERSION: Final[int] = 0


def connect(path: Path) -> sqlite3.Connection:
    """Open one connection with the §3.4.1 pragmas applied."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        connection = sqlite3.connect(path, isolation_level=None)
        connection.row_factory = sqlite3.Row
        for pragma in PRAGMAS:
            connection.execute(pragma)
    except sqlite3.Error as exc:
        raise LedgerTransportError(str(exc)) from exc
    return connection


def schema_version(connection: sqlite3.Connection) -> int:
    """The pinned schema version; 0 for a database with no `meta` table yet."""
    try:
        present = connection.execute(
            _SQL_TABLE_PRESENT, (LedgerTable.META.value,)
        ).fetchone()
        if not present or present[0] == 0:
            return _NO_VERSION
        row = connection.execute(
            _SQL_META_READ, (MetaKey.SCHEMA_VERSION.value,)
        ).fetchone()
    except sqlite3.Error as exc:
        raise LedgerTransportError(str(exc)) from exc
    return _NO_VERSION if row is None else int(row[0])


def read_meta(connection: sqlite3.Connection, key: MetaKey) -> str | None:
    """One pinned `meta` value, or nothing when it was never written."""
    try:
        row = connection.execute(_SQL_META_READ, (key.value,)).fetchone()
    except sqlite3.Error as exc:
        raise LedgerTransportError(str(exc)) from exc
    return None if row is None else str(row[0])


def assert_identity(
    connection: sqlite3.Connection,
    *,
    path: Path,
    repo_root: Path,
    wrapper_root: Path,
) -> None:
    """Refuse unless this ledger is pinned to this repository AND wrapper root.

    Both, because they answer different questions: `repo_hash` says whose facts
    these are, and `wrapper_root` says which engine home owns the run folders
    they point at. Import checks the same pair from the export header (§3.6).
    """
    pinned_repo = read_meta(connection, MetaKey.REPO_HASH)
    found_repo = repo_hash(repo_root)
    if pinned_repo is not None and pinned_repo != found_repo:
        raise LedgerIdentityError(
            MSG_REPO_HASH_MISMATCH.format(
                path=path, pinned=pinned_repo, found=found_repo
            )
        )
    pinned_wrapper = read_meta(connection, MetaKey.WRAPPER_ROOT)
    found_wrapper = str(wrapper_root.resolve())
    if pinned_wrapper is not None and pinned_wrapper != found_wrapper:
        raise LedgerIdentityError(
            MSG_WRAPPER_ROOT_MISMATCH.format(
                path=path, pinned=pinned_wrapper, found=found_wrapper
            )
        )


@contextmanager
def transaction(
    connection: sqlite3.Connection, *, write: bool = True
) -> Iterator[sqlite3.Connection]:
    """One store method, one transaction (§3.4.2) — commit, or roll back.

    `write=False` opens a DEFERRED transaction: an export reads a whole task
    under ONE snapshot (§3.6) and must not take a write lock to do it.
    """
    try:
        connection.execute(_BEGIN if write else _BEGIN_READ)
    except sqlite3.Error as exc:
        # A writer that cannot even BEGIN waited out `busy_timeout`; §3.4.6
        # makes that a named refusal rather than the start of a retry loop.
        raise sqlite_failure(
            exc, operation=LedgerOperation.BEGINNING.value, row_id=TARGET_LEDGER
        ) from exc
    try:
        yield connection
    except BaseException:
        connection.execute(_ROLLBACK)
        raise
    connection.execute(_COMMIT)


class LedgerDatabase:
    """A live ledger connection holding the shared fence for its whole life."""

    def __init__(
        self,
        path: Path,
        *,
        repo_root: Path,
        wrapper_root: Path,
        fence: LedgerFence,
    ) -> None:
        self._path = path
        self._repo_root = repo_root
        self._wrapper_root = wrapper_root
        self._fence = fence
        self._migrate_if_behind()
        self._fence_hold = fence.shared()
        self._fence_hold.__enter__()
        try:
            self._connection = connect(path)
            self._assert_usable(self._connection)
        except BaseException:
            self._fence_hold.__exit__(None, None, None)
            raise

    @property
    def connection(self) -> sqlite3.Connection:
        """The single connection of this process (§3.4.1)."""
        return self._connection

    @property
    def path(self) -> Path:
        """Where this ledger lives."""
        return self._path

    @property
    def repo_root(self) -> Path:
        """The repository whose facts this ledger holds."""
        return self._repo_root

    @property
    def wrapper_root(self) -> Path:
        """The engine home this ledger is pinned to (§3.5)."""
        return self._wrapper_root

    @property
    def fence(self) -> LedgerFence:
        """The fence this connection holds shared (§3.4.4)."""
        return self._fence

    def transaction(
        self, *, write: bool = True
    ) -> AbstractContextManager[sqlite3.Connection]:
        """One transaction on this process's connection."""
        return transaction(self._connection, write=write)

    def close(self) -> None:
        """Close the connection and release the shared fence, in that order."""
        try:
            self._connection.close()
        finally:
            self._fence_hold.__exit__(None, None, None)

    def __enter__(self) -> Self:
        """Use the ledger as a bounded resource."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Always release the connection and the fence."""
        self.close()

    def _migrate_if_behind(self) -> None:
        """Peek at the version, and migrate exclusively only when behind.

        The peek is an unfenced read, and it is only a decision to ASK for the
        fence: the version is read again inside the exclusive section, so a
        process that migrated while we waited leaves nothing to do.
        """
        with closing(connect(self._path)) as connection:
            if schema_version(connection) >= SCHEMA_VERSION:
                return
        with self._fence.exclusive(), closing(connect(self._path)) as connection:
            current = schema_version(connection)
            if current >= SCHEMA_VERSION:
                return
            with transaction(connection):
                if current == _NO_VERSION:
                    apply_migrations(connection, current)
                    self._pin_identity(connection)
                else:
                    assert_identity(
                        connection,
                        path=self._path,
                        repo_root=self._repo_root,
                        wrapper_root=self._wrapper_root,
                    )
                    apply_migrations(connection, current)
                connection.execute(
                    _SQL_META_UPSERT,
                    (MetaKey.SCHEMA_VERSION.value, str(SCHEMA_VERSION)),
                )
            _LOG.info(
                "wf.ledger.migrated",
                path=str(self._path),
                from_version=current,
                to_version=SCHEMA_VERSION,
            )

    def _pin_identity(self, connection: sqlite3.Connection) -> None:
        """Pin repository and wrapper identity at creation, once and for all."""
        connection.execute(
            _SQL_META_WRITE, (MetaKey.REPO_HASH.value, repo_hash(self._repo_root))
        )
        connection.execute(
            _SQL_META_WRITE,
            (MetaKey.WRAPPER_ROOT.value, str(self._wrapper_root.resolve())),
        )
        connection.execute(
            _SQL_META_WRITE,
            (MetaKey.CREATED_AT.value, datetime.now(tz=UTC).isoformat()),
        )

    def _assert_usable(self, connection: sqlite3.Connection) -> None:
        """Refuse a schema from the future, or another repository's ledger."""
        version = schema_version(connection)
        if version > SCHEMA_VERSION:
            raise LedgerSchemaError(
                MSG_SCHEMA_AHEAD.format(
                    path=self._path, found=version, known=SCHEMA_VERSION
                )
            )
        assert_identity(
            connection,
            path=self._path,
            repo_root=self._repo_root,
            wrapper_root=self._wrapper_root,
        )


def open_ledger(
    repo_root: Path,
    wrapper_root: Path,
    *,
    path: Path | None = None,
    fence: LedgerFence | None = None,
) -> LedgerDatabase:
    """Open this repository's ledger, creating and migrating it when needed."""
    return LedgerDatabase(
        ledger_path(repo_root) if path is None else path,
        repo_root=repo_root,
        wrapper_root=wrapper_root,
        fence=LedgerFence(fence_path(repo_root)) if fence is None else fence,
    )
