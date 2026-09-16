"""Repair-forward finalization — the one helper every close goes through.

Every terminal transition in this package is two writes: the carrier records
the outcome, then the bead is closed. That order is deliberate (§5.1, §3.3) —
the reverse would leave a closed bead with no routing truth, which nothing can
recover. But it means a crash between the two leaves a bead whose metadata says
`closed` and whose bd status says `open`.

The only correct response to that state is to FINISH it. Returning early
(because the carrier already says closed) leaves an open bead the frontier
re-picks forever; raising a lifecycle conflict is worse — it wedges the bead
permanently, because §0.1 leaves no raw bd write to repair it with (probed,
phase-2 review: a human gate approval was unrecoverable this way).

`bd close` is idempotent and overwrites the reason (probed), so re-driving it
is always safe and always converges.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from workflow_interpreter.bdio.backend import StoreBackend
from workflow_interpreter.bdio.client import STATUS_CLOSED
from workflow_interpreter.bdio.records import (
    ActivationRecord,
    GateRecord,
    RootRecord,
)
from workflow_interpreter.bdio.wire import BeadRecord


class ClosableRow(Protocol):
    """The identity a repair-forward close needs.

    A `Protocol` rather than `BeadRecord`, so the parsed records can be closed
    without carrying the backend row they were parsed from (§3.1).
    """

    id: str
    status: str
    close_reason: str | None


def is_finished(row: ClosableRow, reason: str) -> bool:
    """Whether the durable side of this transition already landed exactly."""
    return row.status == STATUS_CLOSED and row.close_reason == reason


def close_forward(client: StoreBackend, bead: BeadRecord, reason: str) -> BeadRecord:
    """Drive this bead's close to completion, idempotently.

    A no-op when the close already landed with this reason; otherwise it
    re-drives `bd close`, which is how a half-finished transition — ours or a
    previous tick's — reaches the state its carrier already claims.
    """
    if is_finished(bead, reason):
        return bead
    return client._close_bead(bead.id, reason)


def close_record_forward[RecordT: (ActivationRecord, GateRecord, RootRecord)](
    client: StoreBackend,
    record: RecordT,
    reason: str,
    parse: Callable[[BeadRecord], RecordT],
) -> RecordT:
    """Drive a parsed record's close to completion, idempotently.

    The record already carries the status the decision needs, so the finished
    case costs no call and no re-parse — exactly what passing the backend row
    used to buy, without the row (§3.1).
    """
    if is_finished(record, reason):
        return record
    return parse(client._close_bead(record.id, reason))
