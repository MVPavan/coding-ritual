"""The attention projection, as an outbox intent (D6, superseded).

run-ledger's D6 wrote the label directly, per settling tick. That put a
subprocess on the run loop: a tick settled a root and then waited on somebody
else's service to say so. The projection itself is unchanged — the reconciler
still recomputes the desired presence from the ledger under the task lock and
still acks only what it read — but what it WRITES is now one `SetFlag` row.

So the drain is where it was promised: before the driver exits, once, for
every intent the run accumulated, and never inside a tick.
"""

from __future__ import annotations

from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.tracker.intents import SetFlag
from workflow_interpreter.tracker.models import TrackerRef
from workflow_interpreter.tracker.outbox import TrackerOutbox
from workflow_interpreter.tracker.port import TrackerPort


class OutboxAttentionWriter:
    """An `AttentionWriter` that enqueues the flag instead of writing it."""

    def __init__(self, database: LedgerDatabase, tracker: TrackerPort) -> None:
        """Hold the tracker only for its KIND — the ref needs one (§3.7).

        Not to call it: this writer never contacts a tracker, which is the
        whole point. The kind is what says which system the enqueued ref
        belongs to, and taking the port rather than the bare kind keeps a
        wiring from naming one tracker here and draining another.
        """
        self._outbox = TrackerOutbox(database)
        self._tracker = tracker

    def set_flag(self, task_id: str, flag: str, *, on: bool) -> None:
        """Record the flag's desired presence; the drain applies it."""
        self._outbox.enqueue(
            task_id,
            SetFlag(
                ref=TrackerRef(kind=self._tracker.kind, ref=task_id),
                flag=flag,
                on=on,
            ),
        )
