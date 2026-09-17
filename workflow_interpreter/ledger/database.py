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
import threading
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Final, Self

import structlog

from workflow_interpreter.ledger.constants import (
    MSG_LEDGER_ABSENT,
    MSG_REPO_HASH_MISMATCH,
    MSG_SCHEMA_AHEAD,
    MSG_SCHEMA_BEHIND,
    MSG_WRAPPER_ROOT_MISMATCH,
    PRAGMAS,
    READ_ONLY_PRAGMAS,
    TARGET_LEDGER,
    LedgerOperation,
    LedgerTable,
    MetaKey,
)
from workflow_interpreter.ledger.errors import (
    LedgerAbsent,
    LedgerIdentityError,
    LedgerSchemaError,
    LedgerTransportError,
    sqlite_failure,
)
from workflow_interpreter.ledger.fence import LedgerFence
from workflow_interpreter.ledger.paths import (
    ensure_ledger_ignored,
    fence_path,
    ledger_path,
    repo_hash,
)
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


def connect(path: Path, *, read_only: bool = False) -> sqlite3.Connection:
    """Open one connection with the §3.4.1 pragmas applied.

    `read_only` opens the file `mode=ro` through SQLite's URI form: the file is
    never created, the schema is never migrated, and a stray write fails at
    SQLite rather than at a check that could be raced. It is what a read-only
    command (`costs`) gets, and the missing file is a NAMED refusal rather than
    the transport's own wording.
    """
    if not read_only:
        path.parent.mkdir(parents=True, exist_ok=True)
    try:
        # One connection per process (§3.4.1) means a process with threads
        # shares it, so the creating-thread check has to go and the mutual
        # exclusion has to come from `LedgerDatabase.transaction` instead.
        connection = sqlite3.connect(
            f"file:{path}?mode=ro" if read_only else str(path),
            uri=read_only,
            isolation_level=None,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        for pragma in READ_ONLY_PRAGMAS if read_only else PRAGMAS:
            connection.execute(pragma)
    except sqlite3.OperationalError as exc:
        if read_only and not path.is_file():
            raise LedgerAbsent(MSG_LEDGER_ABSENT.format(path=path)) from exc
        raise LedgerTransportError(str(exc)) from exc
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
def standalone_transaction(
    connection: sqlite3.Connection, *, write: bool = True
) -> Iterator[sqlite3.Connection]:
    """One transaction on a connection ONE caller owns alone (§3.4.2).

    Only for a connection nobody else can reach — the migration peek and the
    import's own connection. The process's shared connection is reached
    through `LedgerDatabase.transaction` and `LedgerDatabase.locked`, which
    take the mutual exclusion this function cannot: `check_same_thread=False`
    means two threads share one connection, and SQLite has no nested `BEGIN`,
    so an unlocked `BEGIN` here would commit another thread's work under its
    own name and an unlocked read would see that work half-done.

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
        read_only: bool = False,
    ) -> None:
        self._path = path
        self._repo_root = repo_root
        self._wrapper_root = wrapper_root
        self._fence = fence
        self._read_only = read_only
        self._writing = threading.RLock()
        if not read_only:
            self._migrate_if_behind()
        self._fence_hold = fence.shared()
        self._fence_hold.__enter__()
        try:
            self._connection = connect(path, read_only=read_only)
            self._assert_usable(self._connection)
        except BaseException:
            self._fence_hold.__exit__(None, None, None)
            raise

    @property
    def connection(self) -> sqlite3.Connection:
        """The single connection of this process, for a caller HOLDING the lock.

        Valid inside `transaction()` or `locked()`, which is where every
        production caller uses it; reaching for it outside either is the
        unsynchronised access those two exist to prevent.
        """
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

    @contextmanager
    def transaction(self, *, write: bool = True) -> Iterator[sqlite3.Connection]:
        """One transaction on this process's ONE connection (§3.4.1, §3.4.2).

        Reentrant-locked rather than merely begun: two threads of one process
        share the connection, and SQLite has no nested `BEGIN` — so a second
        thread entering here while the first is mid-transaction would commit
        the first one's work under its own name. The lock makes "a store
        method is one transaction" true between threads as well as between
        processes.
        """
        with (
            self._writing,
            standalone_transaction(self._connection, write=write) as connection,
        ):
            yield connection

    @contextmanager
    def locked(self) -> Iterator[sqlite3.Connection]:
        """The shared connection, held against other threads for one operation.

        Every operation on this connection that is NOT already inside
        `transaction()` goes through here — reads included. The connection is
        opened with `check_same_thread=False` (§3.4.1: one connection per
        process, whatever its threads), so an unsynchronised read runs while
        another thread is mid-`BEGIN` and sees uncommitted rows or a torn pair
        of them. The lock is reentrant, so a read inside this process's own
        transaction costs nothing.
        """
        with self._writing:
            yield self._connection

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
            with standalone_transaction(connection):
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
        """Refuse a schema from the future, or another repository's ledger.

        A read-only ledger must also be refused when it is BEHIND: the writer's
        path migrates such a database, and this one may not, so answering from
        a schema this build does not know would be answering from columns that
        mean something else.
        """
        version = schema_version(connection)
        if self._read_only and version < SCHEMA_VERSION:
            raise LedgerSchemaError(
                MSG_SCHEMA_BEHIND.format(
                    path=self._path, found=version, known=SCHEMA_VERSION
                )
            )
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


def open_readonly(
    repo_root: Path,
    wrapper_root: Path,
    *,
    path: Path | None = None,
    fence: LedgerFence | None = None,
) -> LedgerDatabase:
    """Open this repository's ledger `mode=ro`, creating and migrating nothing.

    For commands that only report (`costs`). An absent ledger is
    `LedgerAbsent` and a schema this build does not know is
    `LedgerSchemaError`; neither is a reason to write to a database a reader
    was only asked to read (§3.4).
    """
    return LedgerDatabase(
        ledger_path(repo_root) if path is None else path,
        repo_root=repo_root,
        wrapper_root=wrapper_root,
        fence=LedgerFence(fence_path(repo_root)) if fence is None else fence,
        read_only=True,
    )


def open_ledger(
    repo_root: Path,
    wrapper_root: Path,
    *,
    path: Path | None = None,
    fence: LedgerFence | None = None,
) -> LedgerDatabase:
    """Open this repository's ledger, creating and migrating it when needed."""
    ensure_ledger_ignored(repo_root)
    return LedgerDatabase(
        ledger_path(repo_root) if path is None else path,
        repo_root=repo_root,
        wrapper_root=wrapper_root,
        fence=LedgerFence(fence_path(repo_root)) if fence is None else fence,
    )
