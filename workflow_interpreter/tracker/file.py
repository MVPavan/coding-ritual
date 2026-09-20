"""A whole tracker in one JSON file (§3.3).

Here for two reasons and not as a toy. It is the tracker a repository with no
issue service actually wants — `bd`, GitHub and Jira are all optional — and it
is the one implementation of the port that a test can drive to every answer
the port can give without a network or a subprocess, which is what makes the
conformance suite a suite rather than three copies of the bd path.

The file IS the tracker: `upsert` is how an item comes to exist, exactly as
`bd create` is on the other adapter.
"""

from __future__ import annotations

import fcntl
import json
import os
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Final

from pydantic import ValidationError

from workflow_interpreter.ledger.constants import TrackerKind
from workflow_interpreter.tracker.constants import (
    DEFAULT_CAPABILITIES,
    MSG_FILE_LOCKED,
    MSG_FILE_UNREADABLE,
    TrackerCapability,
    WorkItemStatus,
)
from workflow_interpreter.tracker.errors import TrackerRefused
from workflow_interpreter.tracker.intents import (
    Applied,
    Claim,
    Close,
    Conflict,
    SetFlag,
    TrackerIntent,
    TrackerResult,
    Unknown,
)
from workflow_interpreter.tracker.models import Blocker, TrackerRef, WorkItem

_ITEMS: Final[str] = "items"
_BLOCKERS: Final[str] = "blockers"
_NOTES: Final[str] = "notes"
_MSG_NO_ITEM: Final[str] = "this tracker holds no item {ref!r}"
_MSG_CLOSED: Final[str] = "item {ref!r} is closed"
_MSG_HELD: Final[str] = "item {ref!r} is held by {holder!r}"
_LOCK_SUFFIX: Final[str] = ".lock"
_LOCK_TIMEOUT_S: Final[float] = 10.0
"""How long a writer waits for the document. Bounded rather than blocking: a
tracker that never answers must become `Unknown` — the outbox owns the retry —
and a contractor that blocked here forever would be a run a mirror can hang."""
_LOCK_POLL_S: Final[float] = 0.01


class _LockTimeout(RuntimeError):
    """The document stayed locked. Private: every caller turns it into a result."""


class FileTracker:
    """One JSON document, read whole and written whole."""

    def __init__(
        self,
        path: Path,
        *,
        capabilities: frozenset[TrackerCapability] | None = None,
    ) -> None:
        """Pin the document and what this tracker is allowed to claim it can do.

        No actor: the holder of a claim is `intent.actor`, which is the only
        identity `_claim` ever compares, and a second copy of it on the tracker
        would be a second answer to "who is this" that nothing reads.

        `capabilities` is a parameter because a file tracker's abilities are a
        deployment fact, not a code fact: a repository that keeps its blocking
        relations somewhere else declares no `BLOCKERS` and R9 records that the
        question went unasked, rather than the file pretending to answer it.
        """
        self._path = path
        self._capabilities = (
            DEFAULT_CAPABILITIES if capabilities is None else capabilities
        )

    @property
    def kind(self) -> TrackerKind:
        """`file`: the foreign id is the key in this document."""
        return TrackerKind.FILE

    @property
    def capabilities(self) -> frozenset[TrackerCapability]:
        """What this deployment declared its file can answer."""
        return self._capabilities

    def get(self, ref: TrackerRef) -> WorkItem | None:
        """The item under this ref, or nothing."""
        return self._items(self._read()).get(ref.ref)

    def children(self, ref: TrackerRef) -> tuple[WorkItem, ...]:
        """Every item whose recorded parent is this ref."""
        return tuple(
            item
            for item in self._items(self._read()).values()
            if item.parent == ref.ref
        )

    def blockers(self, ref: TrackerRef) -> tuple[Blocker, ...]:
        """What this item waits on, resolved when the blocking item closed.

        An unknown blocking ref is UNRESOLVED: the document names something it
        does not hold, and reading that as "nothing to wait for" would turn a
        broken relation into permission to proceed.
        """
        document = self._read()
        items = self._items(document)
        blocking = document.get(_BLOCKERS, {}).get(ref.ref, [])
        return tuple(
            Blocker(
                ref=str(other),
                resolved=str(other) in items
                and items[str(other)].status is WorkItemStatus.CLOSED,
            )
            for other in blocking
        )

    def upsert(self, item: WorkItem) -> WorkItem:
        """Write one item whole, creating it when this file has none."""
        try:
            with self._locked():
                document = self._read()
                document.setdefault(_ITEMS, {})[item.ref] = item.model_dump(mode="json")
                self._write(document)
        except _LockTimeout as timeout:
            raise TrackerRefused(str(timeout)) from timeout
        return item

    def apply(self, intent: TrackerIntent) -> TrackerResult:
        """Make the item match the desired state and read it back (§3.3).

        Every branch is idempotent because every intent is a state: applying
        the same `Close` twice is one closed item, and that is what makes an
        outbox retry safe rather than merely tolerated.

        The whole read-modify-write happens under an exclusive OS lock, and
        the read happens INSIDE it. Without both, two `wf contract` processes
        on sibling stages each read `claimed_by is None`, each write the whole
        document and each are told `Applied` — two holders of one claim, and
        the later write erases the earlier stage's claim as well (§3.4).
        """
        try:
            with self._locked():
                return self._apply_locked(intent)
        except _LockTimeout as timeout:
            return Unknown(reason=str(timeout))

    def _apply_locked(self, intent: TrackerIntent) -> TrackerResult:
        """One intent against a document nobody else can be writing."""
        document = self._read()
        held = self._items(document).get(intent.ref.ref)
        if held is None:
            return Conflict(reason=_MSG_NO_ITEM.format(ref=intent.ref.ref))
        if isinstance(intent, Claim):
            return self._claim(document, held, intent)
        if isinstance(intent, Close):
            updated = held.model_copy(
                update={
                    "status": WorkItemStatus.CLOSED,
                    "close_reason": intent.reason,
                    "claimed_by": None,
                }
            )
        elif isinstance(intent, SetFlag):
            flags = set(held.flags)
            if intent.on:
                flags.add(intent.flag)
            else:
                flags.discard(intent.flag)
            updated = held.model_copy(update={"flags": frozenset(flags)})
        else:
            document.setdefault(_NOTES, {}).setdefault(intent.ref.ref, {})[
                intent.key
            ] = intent.text
            updated = held
        return Applied(observed=self._store(document, updated))

    def _claim(
        self, document: dict[str, Any], held: WorkItem, intent: Claim
    ) -> TrackerResult:
        """Hold or release the item for one actor, refusing somebody else's.

        A CLOSED item conflicts whichever way the claim points, and the
        observed item travels with the refusal: §3.8's abandoned-external
        detection is exactly "the conflict said closed", and a caller that had
        to re-read to learn that could read something else again.
        """
        if held.status is WorkItemStatus.CLOSED:
            return Conflict(reason=_MSG_CLOSED.format(ref=held.ref), observed=held)
        if not intent.held:
            return Applied(
                observed=self._store(
                    document,
                    held.model_copy(
                        update={"claimed_by": None, "status": WorkItemStatus.OPEN}
                    ),
                )
            )
        if held.claimed_by not in (None, intent.actor):
            return Conflict(
                reason=_MSG_HELD.format(ref=held.ref, holder=held.claimed_by),
                observed=held,
            )
        return Applied(
            observed=self._store(
                document,
                held.model_copy(
                    update={
                        "claimed_by": intent.actor,
                        "status": WorkItemStatus.IN_PROGRESS,
                    }
                ),
            )
        )

    def _store(self, document: dict[str, Any], item: WorkItem) -> WorkItem:
        """Write the whole document and answer with what it now holds."""
        document.setdefault(_ITEMS, {})[item.ref] = item.model_dump(mode="json")
        self._write(document)
        return item

    def _read(self) -> dict[str, Any]:
        """The document, or an empty one when the file does not exist yet."""
        if not self._path.exists():
            return {}
        try:
            loaded = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as unreadable:
            raise TrackerRefused(
                MSG_FILE_UNREADABLE.format(path=self._path, reason=unreadable)
            ) from unreadable
        if not isinstance(loaded, dict):
            raise TrackerRefused(
                MSG_FILE_UNREADABLE.format(path=self._path, reason="not an object")
            )
        return loaded

    def _write(self, document: dict[str, Any]) -> None:
        """Replace the file atomically: a half-written tracker is no tracker.

        The staging name is UNIQUE per write. A fixed `<path>.tmp` is shared
        state of exactly the kind the lock removes, and the one writer that
        does not take the lock — a second tool, an older build — used to
        interleave into it and have `os.replace` publish the mixture.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        staged = self._path.with_name(f"{self._path.name}.{uuid.uuid4().hex}.tmp")
        staged.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
        os.replace(staged, self._path)

    @contextmanager
    def _locked(self) -> Iterator[None]:
        """Hold this document exclusively, or give up within the timeout.

        On a SIDECAR file rather than the document: the document is replaced
        by `os.replace`, so a lock held on its inode would be a lock on a file
        that no longer exists the moment anybody writes.
        """
        lock_path = self._path.with_name(self._path.name + _LOCK_SUFFIX)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + _LOCK_TIMEOUT_S
        handle = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            while True:
                try:
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise _LockTimeout(
                            MSG_FILE_LOCKED.format(
                                path=self._path, timeout=_LOCK_TIMEOUT_S
                            )
                        ) from None
                    time.sleep(_LOCK_POLL_S)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)
        finally:
            os.close(handle)

    def _items(self, document: dict[str, Any]) -> dict[str, WorkItem]:
        """Every item the document holds, parsed once per call."""
        try:
            return {
                str(ref): WorkItem.model_validate(body)
                for ref, body in document.get(_ITEMS, {}).items()
            }
        except ValidationError as invalid:
            raise TrackerRefused(
                MSG_FILE_UNREADABLE.format(path=self._path, reason=invalid)
            ) from invalid
