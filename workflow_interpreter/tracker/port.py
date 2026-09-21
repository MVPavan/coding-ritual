"""The tracker port: four operations, a capability set, an intent union (R2).

Four, and deliberately not the seven `StoreBackend` grew. What is NOT here is
as much of the design as what is: there is no `list`, because the one sweep
that would have needed it — finding the tasks stranded inside §3.4's claim
window — is answered per task from the ledger's own PREPARED row instead, and a
`list` would have made every tracker owe a query language.

Only the contractor holds one. The foreman, the inspector and the crew never
import this package: a tracker call on the run loop is a run that stops when
somebody else's service does (§3.1).
"""

from __future__ import annotations

from typing import Protocol

from workflow_interpreter.ledger.constants import TrackerKind
from workflow_interpreter.tracker.constants import TrackerCapability
from workflow_interpreter.tracker.intents import TrackerIntent, TrackerResult
from workflow_interpreter.tracker.models import Blocker, TrackerRef, WorkItem


class TrackerPort(Protocol):
    """Read three things about a work item, and ask it for one desired state."""

    @property
    def kind(self) -> TrackerKind:
        """Which tracker this is, as `tasks.tracker_kind` records it (§3.7)."""
        ...

    @property
    def capabilities(self) -> frozenset[TrackerCapability]:
        """What this tracker can do. An absent capability is not an error."""
        ...

    def get(self, ref: TrackerRef) -> WorkItem | None:
        """The item, or nothing when this tracker does not hold one."""
        ...

    def children(self, ref: TrackerRef) -> tuple[WorkItem, ...]:
        """The items whose parent is this one."""
        ...

    def blockers(self, ref: TrackerRef) -> tuple[Blocker, ...]:
        """What this item waits on, resolved or not."""
        ...

    def apply(self, intent: TrackerIntent) -> TrackerResult:
        """Make the item match the desired state, and say what happened."""
        ...
