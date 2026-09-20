"""Where a tracker port is built, named once for every composition root.

Three entry points need one — `wf contract`, the foreman's `_composition` (for
the attention drain) and `wf ledger reconcile` — and a second spelling of
"which tracker does this repository have" would be a second chance for one of
them to write the mirror somebody else is not reading.
"""

from __future__ import annotations

from typing import Final

from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.config import BdConfig
from workflow_interpreter.contractor.tracker_config import (
    TrackerBackend,
    TrackerSettings,
)
from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.ledger.reconcile import AttentionWriter
from workflow_interpreter.tracker import BdTracker, FileTracker, NullTracker
from workflow_interpreter.tracker.attention import OutboxAttentionWriter
from workflow_interpreter.tracker.outbox import DrainResult, TrackerOutbox
from workflow_interpreter.tracker.port import TrackerPort

MSG_FILE_PATH_REQUIRED: Final[str] = (
    "the file tracker needs its document: set tracker.path in the foreman "
    "configuration (store-restructure §3.3)"
)


def tracker_for(
    settings: TrackerSettings, config: BdConfig, client: BdClient | None = None
) -> TrackerPort:
    """The port this repository's configuration names.

    `client` is a parameter so the bd adapter can reuse a transport that
    already exists — the contractor adapter holds one — rather than opening a
    second one beside it.
    """
    if settings.backend is TrackerBackend.NULL:
        return NullTracker()
    if settings.backend is TrackerBackend.FILE:
        if settings.path is None:
            raise ValueError(MSG_FILE_PATH_REQUIRED)
        return FileTracker(settings.path, actor=config.actor)
    return BdTracker(BdClient(config) if client is None else client)


def attention_writer(database: LedgerDatabase, tracker: TrackerPort) -> AttentionWriter:
    """The reconciler's writer: one `SetFlag` on the outbox, never a call.

    Named here rather than constructed at each entry point because the whole
    of D6's supersession is which writer the reconciler is given (§3.2).
    """
    return OutboxAttentionWriter(database, tracker)


def drain_outbox(
    database: LedgerDatabase, tracker: TrackerPort, task_id: str | None = None
) -> DrainResult:
    """Apply what this checkout still owes its tracker.

    Here rather than reached for directly, so that the outbox stays inside the
    contractor's surface: `wf ledger reconcile` is a human asking for the
    mirror to be caught up, and it must not be a second import of `tracker/`
    from a package that never touches one.
    """
    return TrackerOutbox(database).drain(tracker, task_id)
