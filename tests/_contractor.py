"""How a test builds a `ContractorAdapter` (S5, §3.3).

The adapter has no default tracker any more. It used to fall back to
`BdTracker(client)`, and that default is exactly what let eight of nine
production construction sites mirror into bd whatever `tracker.backend` said —
a default that "does not change the wiring" is a default nobody notices being
wrong. Production names its tracker in `contractor.tracker_wiring`; the suites
that build an adapter straight over a fake transport name it here, once.
"""

from __future__ import annotations

from typing import Any

from workflow_interpreter.contractor.adapter import ContractorAdapter
from workflow_interpreter.tracker.bd import BdTracker
from workflow_interpreter.tracker.bd_transport import BdClient
from workflow_interpreter.tracker.port import TrackerPort


def bd_adapter(
    client: BdClient, *args: Any, tracker: TrackerPort | None = None, **kwargs: Any
) -> ContractorAdapter:
    """An adapter over `client`, tracked by bd through that same transport."""
    return ContractorAdapter(
        *args,
        tracker=BdTracker(client) if tracker is None else tracker,
        **kwargs,
    )
