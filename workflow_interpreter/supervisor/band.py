"""The §12 execution band: one active runner per repo path, ever.

Its own module because it is its own thing — a concurrency primitive with no
knowledge of git, of the §5.4 precondition, or of whose file is whose. In-repo
isolation replaces physical isolation with two mechanisms, and this is the one
that makes "one active runner" true; recorded provenance (`workspace.py`) is
the other.
"""

from __future__ import annotations

import fcntl
import io
from pathlib import Path
from typing import Final, Self

from workflow_interpreter.supervisor.errors import LockUnavailable

_MSG_BAND_HELD: Final[str] = (
    "the §12 in-repo execution band at {path} is held by another runner"
)


class BandLock:
    """The §12 execution band: one active runner per repo path, ever.

    A `flock` rather than a lock FILE's existence: a wrapper killed with
    `SIGKILL` releases a `flock` when its descriptor closes, but would leave a
    marker file behind forever — and an execution band that a crash wedges
    permanently is worse than none.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._handle: io.TextIOWrapper | None = None

    @property
    def held(self) -> bool:
        """Whether this process currently holds the band."""
        return self._handle is not None

    def acquire(self) -> None:
        """Take the band, or refuse immediately — never queue behind a runner."""
        if self._handle is not None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        handle = self._path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            handle.close()
            raise LockUnavailable(_MSG_BAND_HELD.format(path=self._path)) from exc
        self._handle = handle

    def release(self) -> None:
        """Release the band; closing the descriptor is what actually frees it."""
        if self._handle is None:
            return
        fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        self._handle.close()
        self._handle = None

    def __enter__(self) -> Self:
        self.acquire()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.release()


__all__ = ["BandLock"]
