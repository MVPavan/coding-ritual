"""bd behind the port (§3.3).

A wrapper over the bd transport rather than a rewrite. S6 deleted the
client's record-store half and moved what survived under `tracker/`
(`bd_transport.py`): what is left is exactly the tracker traffic this adapter
issues.

bd DOES answer the claim, and this adapter used to say it did not. The
docstring here claimed bd "says open, in_progress or closed, and nothing about
who holds a row"; that was simply false — `bd show --json` carries `assignee`
and `bd update` writes it (probed on bd 1.1.0). What was actually missing was
local: `BeadRecord` did not carry the field. With `CLAIM` undeclared, §3.4's
claim-first, `_release_stranded`, `_refuse_conflicted_claim` and the
external-close detection were all dead on the one tracker every checkout runs.

The write is `--assignee <actor>` rather than bd's own `--claim`, because
`--claim` binds the row to bd's user identity and refuses a row assigned to
anyone else — including this engine's actor. Exclusion is still ledger-side
(R11 plus `_refuse_other_admission`): read-then-write across a subprocess is
not atomic, and the claim here is the DESIRED STATE the port promises, not a
mutex.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from pydantic import JsonValue

from workflow_interpreter.bdio.errors import StoreError, StoreOutputError
from workflow_interpreter.ledger.constants import TrackerKind
from workflow_interpreter.tracker.bd_transport import (
    STATUS_CLOSED,
    BdClient,
    BeadRecord,
    DependencyType,
)
from workflow_interpreter.tracker.constants import TrackerCapability, WorkItemStatus
from workflow_interpreter.tracker.errors import BdCommandError
from workflow_interpreter.tracker.intents import (
    Annotate,
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

BD_CAPABILITIES: Final[frozenset[TrackerCapability]] = frozenset(
    {
        TrackerCapability.CHILDREN,
        TrackerCapability.BLOCKERS,
        TrackerCapability.CLAIM,
        TrackerCapability.CLOSE,
        TrackerCapability.FLAG,
    }
)
"""No `ANNOTATE`: annotation would be a metadata merge, and §0.1 keeps bd
metadata for the engine's own carriers."""

_NOBODY: Final[str] = ""
"""What `--assignee` is given to clear the field (probed)."""
_MSG_CLOSED: Final[str] = "bead {ref!r} is closed"
_MSG_HELD: Final[str] = "bead {ref!r} is assigned to {holder!r}"

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

    def legacy_metadata(self, ref: str) -> Mapping[str, JsonValue]:
        """What this bead carries, uninterpreted — R12's quiesce probe ONLY.

        Not part of the port and not a read the engine routes on: bd is the
        one tracker whose items ever held a contractor record (in metadata,
        until S4), so it is the one adapter that can answer whether a task is
        still in flight in that retired home. The caller
        (`contractor/quiesce.py`) owns what the keys mean; this answers only
        what is there.

        An unanswerable probe is NOT an empty answer. Swallowing every failure
        made R12's refusal skippable by a single `bd show` timeout — the one
        guard whose whole value is that it cannot be missed — so a transport
        that never got an answer propagates, and the caller refuses by name
        (S6 review, finding 5).

        bd RAN and said no is a different thing, and it is an answer: an
        unreadable row (`StoreOutputError`) and a non-zero exit
        (`BdCommandError` — an id bd does not hold, a workspace bd was never
        initialised in) are both "this build's tracker carries no record here",
        deterministic, and the same on every retry. What propagates is the
        retryable half: a timeout, or a bd that could not be run at all.
        """
        try:
            return self._client.show(ref).metadata
        except (StoreOutputError, BdCommandError):
            return {}

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
            self._client.close(intent.ref.ref, intent.reason)
            return Applied(observed=self.get(intent.ref))
        if isinstance(intent, SetFlag):
            written = (
                self._client.add_label(intent.ref.ref, intent.flag)
                if intent.on
                else self._client.remove_label(intent.ref.ref, intent.flag)
            )
            return Applied(observed=_item(written))
        if isinstance(intent, Claim):
            return self._claim(intent)
        # `Annotate` is an undeclared capability on bd, so it is a no-op rather
        # than a refusal: a caller that checked `capabilities` never sends one,
        # and one that did not must not have its landing failed by a mirror
        # this transport cannot write.
        if isinstance(intent, Annotate):
            return Applied(observed=self.get(intent.ref))
        raise AssertionError(intent)  # pragma: no cover - the union is closed

    def _claim(self, intent: Claim) -> TrackerResult:
        """Hold or hand back one bead for one actor, refusing somebody else's.

        A desired state, so re-applying it is one claim and not two writes:
        a bead this actor already holds is `Applied` without touching bd. A
        CLOSED bead conflicts whichever way the claim points, and the observed
        item travels with the refusal — §3.8's abandoned-external detection is
        exactly "the conflict said closed".
        """
        held = _item(self._client.show(intent.ref.ref))
        if held.status is WorkItemStatus.CLOSED:
            return Conflict(reason=_MSG_CLOSED.format(ref=held.ref), observed=held)
        if not intent.held:
            if held.claimed_by is None:
                return Applied(observed=held)
            return Applied(
                observed=_item(self._client.write_assignee(intent.ref.ref, _NOBODY))
            )
        if held.claimed_by not in (None, intent.actor):
            return Conflict(
                reason=_MSG_HELD.format(ref=held.ref, holder=held.claimed_by),
                observed=held,
            )
        if (
            held.claimed_by == intent.actor
            and held.status is WorkItemStatus.IN_PROGRESS
        ):
            return Applied(observed=held)
        return Applied(
            observed=_item(self._client.write_assignee(intent.ref.ref, intent.actor))
        )


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
        claimed_by=bead.assignee or None,
    )
