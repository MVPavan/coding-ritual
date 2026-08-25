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

from workflow_interpreter.bdio.client import STATUS_CLOSED, BdClient
from workflow_interpreter.bdio.wire import BeadRecord


def is_finished(bead: BeadRecord, reason: str) -> bool:
    """Whether the bd side of this transition already landed exactly."""
    return bead.status == STATUS_CLOSED and bead.close_reason == reason


def close_forward(client: BdClient, bead: BeadRecord, reason: str) -> BeadRecord:
    """Drive this bead's close to completion, idempotently.

    A no-op when the close already landed with this reason; otherwise it
    re-drives `bd close`, which is how a half-finished transition — ours or a
    previous tick's — reaches the state its carrier already claims.
    """
    if is_finished(bead, reason):
        return bead
    return client._close_bead(bead.id, reason)
