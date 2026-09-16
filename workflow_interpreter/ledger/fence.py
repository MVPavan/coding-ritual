"""The repository-stable `flock` every ledger connection holds (§3.4.4).

Shared for the life of any connection that opens the database; exclusive for
import, migration and restore, with a bounded wait that then refuses naming the
holders' pids. One lock FILE, one inode: the exclusive taker must contend with
every reader, including readers in another worktree and under another wrapper
home, which is why the file lives in the git common directory.

Linux-only, like the rest of the wrapper: the holders are read from
`/proc/locks`, and a host without it refuses with an unnamed holder rather than
inventing one.
"""

from __future__ import annotations

import fcntl
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final

import structlog

from workflow_interpreter.ledger.constants import (
    FENCE_POLL_S,
    FENCE_WAIT_S,
    PROC_LOCKS,
)
from workflow_interpreter.ledger.errors import LedgerFenceBusy

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

_LOCKS_KIND_FIELD: Final[int] = 1
_LOCKS_PID_FIELD: Final[int] = 4
_LOCKS_INODE_FIELD: Final[int] = 5
_LOCKS_MIN_FIELDS: Final[int] = 6
_INODE_PARTS: Final[int] = 3
_DEVICE_BASE: Final[int] = 16
"""`/proc/locks` prints the device as `%02x:%02x`, so its two leading parts are
HEXADECIMAL while the inode that follows them is decimal."""
_FLOCK_KIND: Final[str] = "FLOCK"
"""A blocked WAITER is listed as `N: -> POSIX …`, which shifts every field by
one; requiring the kind in its own column drops those lines, and they are not
holders anyway."""


def _locked_file(field: str) -> tuple[int, int, int] | None:
    """One `/proc/locks` `major:minor:inode` field as its file identity.

    The WHOLE identity: an inode number is only unique within one device, so
    two filesystems on this host routinely carry the same number and comparing
    it alone would name an unrelated process as a holder of the fence.
    """
    parts = field.split(":")
    if len(parts) != _INODE_PARTS:
        return None
    try:
        major, minor, inode = parts
        return int(major, _DEVICE_BASE), int(minor, _DEVICE_BASE), int(inode)
    except ValueError:
        return None


def holders(path: Path) -> tuple[int, ...]:
    """Every pid the kernel records as holding an `flock` on this file.

    By device and INODE, not by name: a holder that opened the same inode
    through another worktree's path is exactly the contention this fence exists
    to surface.
    """
    try:
        stat = path.stat()
        lines = Path(PROC_LOCKS).read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    wanted = (os.major(stat.st_dev), os.minor(stat.st_dev), stat.st_ino)
    found: list[int] = []
    for line in lines:
        fields = line.split()
        if len(fields) < _LOCKS_MIN_FIELDS or fields[_LOCKS_KIND_FIELD] != _FLOCK_KIND:
            continue
        if _locked_file(fields[_LOCKS_INODE_FIELD]) != wanted:
            continue
        try:
            pid = int(fields[_LOCKS_PID_FIELD])
        except ValueError:
            continue
        if pid >= 0 and pid not in found:
            found.append(pid)
    return tuple(sorted(found))


class LedgerFence:
    """One lock file, taken shared by connections and exclusive by rebuilds."""

    def __init__(self, path: Path, *, wait_s: float = FENCE_WAIT_S) -> None:
        self._path = path
        self._wait_s = wait_s

    @property
    def path(self) -> Path:
        """The lock file every holder contends on."""
        return self._path

    def _open(self) -> int:
        """Open (creating) the lock file, returning a close-on-exec descriptor.

        `O_CLOEXEC` because a dispatched runner must never inherit the fence: a
        child that keeps the descriptor open keeps the lock held long after the
        writer that took it has exited.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        return os.open(self._path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o644)

    @contextmanager
    def shared(self) -> Iterator[int]:
        """Hold the fence shared — every reader and every writer takes this."""
        descriptor = self._open()
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH)
            yield descriptor
        finally:
            os.close(descriptor)

    @contextmanager
    def exclusive(self) -> Iterator[int]:
        """Hold the fence exclusively, or refuse naming who holds it (§3.4)."""
        descriptor = self._open()
        try:
            self._take_exclusive(descriptor)
            yield descriptor
        finally:
            os.close(descriptor)

    def _take_exclusive(self, descriptor: int) -> None:
        """Poll for the exclusive lock until the bounded wait is spent."""
        deadline = time.monotonic() + self._wait_s
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    held = holders(self._path)
                    _LOG.warning(
                        "wf.ledger.fence.busy", path=str(self._path), holders=held
                    )
                    raise LedgerFenceBusy(str(self._path), self._wait_s, held) from None
                time.sleep(FENCE_POLL_S)
