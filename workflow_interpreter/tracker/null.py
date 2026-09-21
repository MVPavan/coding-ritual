"""A tracker that holds nothing, so that a run under none still completes."""

from __future__ import annotations

from workflow_interpreter.ledger.constants import TrackerKind
from workflow_interpreter.tracker.constants import TrackerCapability
from workflow_interpreter.tracker.intents import Applied, TrackerIntent, TrackerResult
from workflow_interpreter.tracker.models import Blocker, TrackerRef, WorkItem


class NullTracker:
    """No capabilities, no items, and every intent `Applied` (§3.3).

    `Applied(observed=None)` rather than a refusal is the whole point: a run
    with no tracker is not a degraded run, it is a run with no mirror. A
    refusal here would make "offline" a failure mode instead of a wiring, and
    §3.4's `Unknown`-refuses rule would then refuse every offline admission.

    What such a run owes instead is the task brief, which the tracker would
    otherwise have held: `wf contract … --brief <file>` supplies it.
    """

    @property
    def kind(self) -> TrackerKind:
        """`none`: this run's tasks have no foreign identity."""
        return TrackerKind.NONE

    @property
    def capabilities(self) -> frozenset[TrackerCapability]:
        """None. Every caller branches on this rather than on a failure."""
        return frozenset()

    def get(self, ref: TrackerRef) -> WorkItem | None:
        """Nothing: there is no tracker holding this item."""
        return None

    def children(self, ref: TrackerRef) -> tuple[WorkItem, ...]:
        """Nothing: with no items there is no hierarchy."""
        return ()

    def blockers(self, ref: TrackerRef) -> tuple[Blocker, ...]:
        """Nothing: with no items there is nothing to wait on."""
        return ()

    def apply(self, intent: TrackerIntent) -> TrackerResult:
        """Applied, observing nothing: there is no mirror to write."""
        return Applied()
