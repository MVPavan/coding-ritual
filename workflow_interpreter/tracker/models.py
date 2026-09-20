"""What a tracker is read as: a reference, an item, a blocker (§3.3).

Deliberately the five fields §3.3's table names and nothing more — title,
brief, status, parent, and who holds it. Everything else a tracker happens to
carry is the tracker's business; the engine's facts live in the ledger.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.ledger.constants import TrackerKind
from workflow_interpreter.tracker.constants import WorkItemStatus


class TrackerRef(BaseModel):
    """One work item's foreign identity: which tracker, and its id there.

    The pair rather than the string, for `tasks.tracker_ref`'s reason (§3.7):
    two trackers can mint the same id, so a ref that did not name its tracker
    could not say which system to close.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: TrackerKind
    ref: str


class WorkItem(BaseModel):
    """What the tracker says about one item, as the engine reads it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ref: str
    title: str
    brief: str | None
    status: WorkItemStatus
    parent: str | None = None
    claimed_by: str | None = None
    """Who the tracker believes is working this item, when it can say.

    The one field a `Claim` reads back: `Applied(observed)` is written AND read
    back (§3.3), so a claim is only claimed when the tracker agrees it is."""
    flags: frozenset[str] = frozenset()
    close_reason: str | None = None


class Blocker(BaseModel):
    """One item this task waits on, and whether it is still waiting.

    Its own model rather than a `WorkItem`: a blocker is a RELATION, and the
    trackers in scope answer it without answering what the blocking item is —
    bd's dependency rows carry an id and a status and nothing else.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    ref: str
    resolved: bool
