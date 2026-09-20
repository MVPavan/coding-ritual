"""bd behind the port (§3.3).

A wrapper over the existing `BdClient` rather than a rewrite: S6 deletes the
client's record-store half, and what survives is exactly the tracker traffic
this adapter issues. Wrapping it now is what lets S5 move the contractor onto
the port without moving bd at the same time.

What bd does NOT declare is `CLAIM`. This transport has no claim primitive —
`bd` says open, in_progress or closed, and nothing about who holds a row — and
declaring the capability anyway would mean emulating one with a label that
nothing else in bd respects. Admissions on bd serialise on the ledger's own
claim (R11) and on `_refuse_other_admission`; §3.4's tracker claim is issued by
the trackers that can actually answer it.
"""

from __future__ import annotations

from typing import Final

from workflow_interpreter.bdio.client import (
    STATUS_CLOSED,
    BdClient,
    DependencyType,
)
from workflow_interpreter.bdio.errors import StoreError, StoreOutputError
from workflow_interpreter.bdio.wire import BeadRecord
from workflow_interpreter.ledger.constants import TrackerKind
from workflow_interpreter.tracker.constants import TrackerCapability, WorkItemStatus
from workflow_interpreter.tracker.intents import (
    Annotate,
    Applied,
    Claim,
    Close,
    SetFlag,
    TrackerIntent,
    TrackerResult,
    Unknown,
)
from workflow_interpreter.tracker.models import Blocker, TrackerRef, WorkItem

BD_CAPABILITIES: Final[frozenset[TrackerCapability]] = frozenset(
    {
        TrackerCapability.CHILDREN,
        TrackerCapability.BLOCKERS,
        TrackerCapability.CLOSE,
        TrackerCapability.FLAG,
    }
)
"""No `CLAIM` (see the module docstring) and no `ANNOTATE`: annotation would be
a metadata merge, and §0.1 keeps bd metadata for the engine's own carriers."""

_STATUS: Final[dict[str, WorkItemStatus]] = {
    "open": WorkItemStatus.OPEN,
    "in_progress": WorkItemStatus.IN_PROGRESS,
    STATUS_CLOSED: WorkItemStatus.CLOSED,
}
_MSG_UNREACHABLE: Final[str] = "bd did not answer: {reason}"


class BdTracker:
    """The bd transport, as the four operations of the port."""

    def __init__(self, client: BdClient) -> None:
        self._client = client

    @property
    def kind(self) -> TrackerKind:
        """`bd`, as `tasks.tracker_kind` records it (§3.7)."""
        return TrackerKind.BD

    @property
    def capabilities(self) -> frozenset[TrackerCapability]:
        """Everything bd can answer without being emulated."""
        return BD_CAPABILITIES

    def get(self, ref: TrackerRef) -> WorkItem | None:
        """`bd show`, as one work item, or nothing when bd holds no such row.

        Only an UNREADABLE answer is absence. A command that exited non-zero
        or a binary that will not run says nothing about the caller's id, and
        reading it as "no such item" would hide a broken store behind an
        ordinary refusal — so those propagate.
        """
        try:
            return _item(self._client.show(ref.ref))
        except StoreOutputError:
            return None

    def children(self, ref: TrackerRef) -> tuple[WorkItem, ...]:
        """Only rows whose PERSISTED parent is this one.

        `bd list --parent` returns descendants, so the filter stays here: a
        grandchild admitted as a stage would run work the epic never declared.
        """
        return tuple(
            _item(bead)
            for bead in self._client.list_children(ref.ref)
            if bead.parent == ref.ref
        )

    def blockers(self, ref: TrackerRef) -> tuple[Blocker, ...]:
        """Only the BLOCKS relations, resolved when the blocking row closed."""
        return tuple(
            Blocker(ref=dependency.id, resolved=dependency.status == STATUS_CLOSED)
            for dependency in self._client.list_dependencies(ref.ref)
            if dependency.dependency_type is DependencyType.BLOCKS
        )

    def apply(self, intent: TrackerIntent) -> TrackerResult:
        """Write the desired state, or say the transport could not (§3.3).

        A refusal becomes `Unknown` rather than an exception, because the
        caller is usually holding a landed commit: the outbox retries the
        state, and nothing about the ledger depends on bd having answered.
        """
        try:
            return self._apply(intent)
        except StoreError as unreachable:
            return Unknown(reason=_MSG_UNREACHABLE.format(reason=unreachable))

    def _apply(self, intent: TrackerIntent) -> TrackerResult:
        """Route one intent to the bd write that expresses it."""
        if isinstance(intent, Close):
            held = self._client.show(intent.ref.ref)
            if held.status == STATUS_CLOSED and held.close_reason == intent.reason:
                return Applied(observed=_item(held))
            self._client._close_row(intent.ref.ref, intent.reason)
            return Applied(observed=self.get(intent.ref))
        if isinstance(intent, SetFlag):
            written = (
                self._client._add_label(intent.ref.ref, intent.flag)
                if intent.on
                else self._client._remove_label(intent.ref.ref, intent.flag)
            )
            return Applied(observed=_item(written))
        # `Claim` and `Annotate` are undeclared capabilities on bd, so they are
        # no-ops rather than refusals: a caller that checked `capabilities`
        # never sends one, and one that did not must not have its landing
        # failed by a mirror this transport cannot write.
        if isinstance(intent, Claim | Annotate):
            return Applied(observed=self.get(intent.ref))
        raise AssertionError(intent)  # pragma: no cover - the union is closed


def _item(bead: BeadRecord) -> WorkItem:
    """One bd row as a work item, with an unknown status read as OPEN.

    OPEN rather than a refusal: bd's status vocabulary is open-ended and a row
    labelled something this build has not seen is still a row somebody is
    expected to work, which is what every caller of `status` is asking.
    """
    return WorkItem(
        ref=bead.id,
        title=bead.title,
        brief=bead.description,
        status=_STATUS.get(bead.status, WorkItemStatus.OPEN),
        parent=bead.parent,
        flags=frozenset(bead.labels),
        close_reason=bead.close_reason,
    )
