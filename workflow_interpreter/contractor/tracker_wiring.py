"""Where a tracker port — and the adapter that holds one — is built.

Every entry point that reaches a tracker comes through here: `wf contract`,
`wf phase abandon`, `wf run`/`wf status`'s gate view, the integration surface,
replacement coordination, the foreman's `_composition` (for the attention
drain) and `wf ledger reconcile`. A second spelling of "which tracker does this
repository have" is a second chance for one of them to write the mirror
somebody else is not reading — which is exactly what eight of the nine
`ContractorAdapter` construction sites used to do, each defaulting to bd and to
no outbox whatever `tracker.backend` said.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import structlog

from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.config import BdConfig
from workflow_interpreter.bdio.errors import StoreError
from workflow_interpreter.bdio.reads import WorkflowReads
from workflow_interpreter.contractor.adapter import ContractorAdapter
from workflow_interpreter.contractor.records import contractor_records
from workflow_interpreter.contractor.tracker_config import (
    TrackerBackend,
    TrackerSettings,
)
from workflow_interpreter.foreman.config import ForemanConfig
from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.ledger.closure import closure_probe
from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.ledger.reconcile import AttentionWriter
from workflow_interpreter.tracker import BdTracker, FileTracker, NullTracker
from workflow_interpreter.tracker.attention import OutboxAttentionWriter
from workflow_interpreter.tracker.errors import TrackerRefused, TrackerUnavailable
from workflow_interpreter.tracker.outbox import DrainResult, TrackerOutbox
from workflow_interpreter.tracker.port import TrackerPort

if TYPE_CHECKING:
    from workflow_interpreter.foreman.compose import Composition

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)
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
        return FileTracker(settings.path)
    return BdTracker(BdClient(config) if client is None else client)


def contractor_adapter(
    config: ForemanConfig,
    database: LedgerDatabase | None,
    git: Git,
    reads: WorkflowReads | None = None,
    *,
    client: BdClient | None = None,
) -> ContractorAdapter:
    """The contractor's adapter, wired to the tracker this repository CONFIGURED.

    The one construction site, for `records_of`'s reason and a sharper one:
    the adapter's tracker and its outbox are not defaults it can pick, they are
    the answer to "what does `tracker.backend` say and where does an
    unanswered mirror wait". Nine call sites picked their own; eight of them
    picked bd and no outbox, so `wf phase abandon` closed a bd bead in a
    repository whose tasks live in a file — and left no outbox row to say so.

    `reads` is the store the engine's ROOTS live in, which is not the tracker
    and not always bd (§3.2); without one the adapter falls back to its own
    transport.
    """
    return ContractorAdapter.from_config(
        config.bd,
        reads,
        closure=closure_probe(database, git),
        records=contractor_records(database, backend=config.store),
        tracker=tracker_for(config.tracker, config.bd, client),
        outbox=None if database is None else TrackerOutbox(database),
    )


def adapter_of(
    composition: Composition, reads: WorkflowReads | None = None
) -> ContractorAdapter:
    """The contractor adapter of one composition, named once for every caller.

    Every production caller has a composition and nothing else in common, so
    this is the spelling they share; `wf ledger reconcile` has no composition
    and reaches `contractor_adapter` directly.
    """
    return contractor_adapter(
        composition.config,
        composition.ledger,
        composition.git,
        composition.store.reads if reads is None else reads,
    )


def attention_writer(database: LedgerDatabase, tracker: TrackerPort) -> AttentionWriter:
    """The reconciler's writer: one `SetFlag` on the outbox, never a call.

    Named here rather than constructed at each entry point because the whole
    of D6's supersession is which writer the reconciler is given (§3.2).
    """
    return OutboxAttentionWriter(database, tracker)


def repair_mirror(
    config: ForemanConfig,
    database: LedgerDatabase,
    git: Git,
    task_id: str,
) -> DrainResult:
    """Everything `wf ledger reconcile <task>` owes the mirror (§3.4, §3.2.4).

    Two repairs, not one. Draining what is owed was already here; the PREPARED
    -plus-claimed release was not, although §3.4 names this command beside the
    next `wf contract` as the way that shape is repaired — so on a machine
    where the next contract invocation is days away, the documented remedy did
    nothing and the tracker stayed wrong about who holds the task.

    The release runs FIRST and shares `release_stranded_claim`, the same
    detection admission performs: two spellings of "is this claim stranded"
    would be two chances to release a live one.

    What the drain DID comes back, because the human at this command is the
    one who has to hear about a conflict: the row retires either way, so a
    result nobody returned was a disagreement nobody was told about.
    """
    adapter = contractor_adapter(config, database, git)
    adapter.release_stranded_claim(task_id, config.actor)
    return drain_outbox(database, adapter.tracker, task_id)


def drain_at_exit(composition: Composition) -> None:
    """Apply what this invocation accumulated, before the DRIVER exits (D6).

    Every driver, not only `wf contract`: `wf run` and `wf tick` build the same
    composition and let the reconciler enqueue a `SetFlag`, so a drain only the
    contractor performed left an operator driving a root with `wf run` unable
    to see `wf:attention` until somebody happened to run another command.

    Still zero tracker calls INSIDE a tick — this is the exit, after the loop.
    Bounded and non-fatal on purpose, exactly as the attention drain it
    replaces was: an unreachable tracker leaves the rows pending for the next
    drain, and it must not fail a run whose facts are already in the ledger.

    NOTHING escapes, and that is stricter than it looks: this runs from a
    `finally`, so an exception raised here REPLACES the driver's own failure
    with a mirror's. `TrackerRefused` — an unreadable file tracker — used to do
    exactly that. A drain failure is logged, leaves its rows pending, and
    leaves the exit status to whatever the run itself decided.
    """
    if composition.ledger is None:
        return
    try:
        result = drain_outbox(
            composition.ledger,
            tracker_for(composition.config.tracker, composition.config.bd),
        )
    except (StoreError, TrackerUnavailable, TrackerRefused, OSError) as refusal:
        _LOG.warning("wf.tracker.outbox_drain_refused", reason=str(refusal))
        return
    if result.conflicts:
        # A conflict is an ANSWER, so its row retired; the only record of it
        # was one `_LOG.info` nobody reads at exit. It is a decision for a
        # human — the tracker disagrees about a task this run just landed.
        _LOG.warning("wf.tracker.mirror_conflicted", refs=list(result.conflicts))


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
