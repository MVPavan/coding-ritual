"""R12's clean break: what a record in the OLD home gets, and why not a shim.

The contractor's record lived in bead metadata until S4 moved it into the
ledger. S6 deletes the seam that could still read one, and R12 says the break
is clean: no dual home, no read shim, nothing that keeps the retired shape
alive for one more slice.

That leaves exactly one migration surface — a task still IN FLIGHT in the old
home — and it is the one shape a silent break would corrupt. A task at
PREPARED or ADMITTED there has no ledger record, so every later step would
read it as a task that never prepared: mint a second id, claim, admit, and run
work that is already running. So it refuses here, by name, with the remedy.

A task whose old record is LANDED, CLOSED or abandoned is not refused. Its work
is over; nothing this build does to it can run it twice, and refusing every
bead the previous build ever touched would make the cutover unusable.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, Protocol, runtime_checkable

from pydantic import JsonValue

LEGACY_RECORD_KEYS: Final[frozenset[str]] = frozenset({"contractor", "phase_bridge"})
"""The bead-metadata keys the record was ever stored under.

Both, because S0 renamed the key without a shim (`phase_bridge` → `contractor`)
and R12's quiesce is what made THAT safe too: a bead written before S0 is as
unreadable to this build as one written before S4, and the refusal must name it
rather than miss it."""

IN_FLIGHT_STATES: Final[frozenset[str]] = frozenset({"prepared", "admitted"})
"""The record states that mean work is underway and nobody may start it again."""

MSG_REMEDY: Final[str] = (
    "finish or abandon the task on the build that wrote it, then remove the "
    "record from the item's metadata"
)
MSG_NOT_QUIESCED: Final[str] = (
    "task {task_id!r} still carries a contractor record in the item's metadata "
    "under {key!r}, at state {state!r}: that home was retired in S4 and this "
    "build reads no shim for it (store-restructure R12). Remedy: " + MSG_REMEDY
)

_STATE_FIELD: Final[str] = "state"


class NotQuiesced(RuntimeError):
    """The cutover was asked to run over a task the old home still owns."""


@runtime_checkable
class LegacyMetadata(Protocol):
    """A tracker that can still show what its items carry (bd, and only bd).

    Runtime-checkable because the probe is a property of the TRANSPORT, not of
    the port: a file tracker and `NullTracker` never held a record, so there is
    nothing for them to answer and nothing for them to implement.
    """

    def legacy_metadata(self, ref: str) -> Mapping[str, JsonValue]:
        """Whatever the item carries, uninterpreted."""


def assert_quiesced(tracker: object, task_id: str) -> None:
    """Refuse a task whose record is still in flight in the retired home.

    Per task rather than a sweep, for R3's reason: the command already knows
    which task it is about, and a scan of every item a tracker holds would be
    a startup cost paid forever for a condition that is true of nothing.
    """
    if not isinstance(tracker, LegacyMetadata):
        return
    metadata = tracker.legacy_metadata(task_id)
    for key in sorted(LEGACY_RECORD_KEYS):
        held = metadata.get(key)
        if not isinstance(held, Mapping):
            continue
        state = held.get(_STATE_FIELD)
        if isinstance(state, str) and state.lower() in IN_FLIGHT_STATES:
            raise NotQuiesced(
                MSG_NOT_QUIESCED.format(task_id=task_id, key=key, state=state)
            )
