"""Composition for the caller-selected, one-stage contractor command."""

from __future__ import annotations

import sys
import tempfile
from enum import StrEnum
from pathlib import Path
from typing import Final

import structlog
from pydantic import BaseModel, ConfigDict, ValidationError

from workflow_interpreter.bdio import StoreOutputError
from workflow_interpreter.contractor.adapter import (
    ContractorAdapter,
    ContractorAdapterError,
)
from workflow_interpreter.contractor.admission import (
    AdmissionRefused,
    PhaseAdmission,
    WorkflowRootProvisioner,
)
from workflow_interpreter.contractor.authority import BeadGateAuthority
from workflow_interpreter.contractor.errors import ContractorRefusal
from workflow_interpreter.contractor.journal import ExportPin, LandingJournal
from workflow_interpreter.contractor.landing import (
    LANDING_RECEIPT_FILE,
    DetachedRepositoryGate,
    LandingDisposition,
    LandingIntent,
    LandingReceipt,
    PhaseLanding,
)
from workflow_interpreter.contractor.models import ContractorRecord, ContractorState
from workflow_interpreter.contractor.quiesce import NotQuiesced, assert_quiesced
from workflow_interpreter.contractor.records import RecordStoreUnavailable
from workflow_interpreter.contractor.retry import retry_refusal
from workflow_interpreter.contractor.tracker_wiring import adapter_of, drain_at_exit
from workflow_interpreter.contractor.verification import VerificationPolicy
from workflow_interpreter.foreman.compose import Composition
from workflow_interpreter.foreman.constants import (
    RUN_DEFAULT_MAX_WALL_S,
    RUN_DEFAULT_POLL_S,
)
from workflow_interpreter.foreman.errors import ResolutionError
from workflow_interpreter.foreman.frontier import build_frontier
from workflow_interpreter.foreman.identifiers import validate_bead_id
from workflow_interpreter.foreman.resolve import instantiate
from workflow_interpreter.foreman.tick import Foreman
from workflow_interpreter.foreman.wake import MonitorUnavailable
from workflow_interpreter.inspector.errors import (
    GitCommandError,
    LockUnavailable,
    WrapperDirError,
)
from workflow_interpreter.inspector.paths import read_record
from workflow_interpreter.ledger.checkpoint import TaskCheckpoint
from workflow_interpreter.ledger.constants import LANDING_INTENT_FILE
from workflow_interpreter.ledger.identity import mint_task
from workflow_interpreter.ledger.paths import coordinator_dirt
from workflow_interpreter.schema.decisions import CoordinationError
from workflow_interpreter.schema.loader import GraphValidationError, load_graph
from workflow_interpreter.schema.models import PRODUCER_INSTANCE
from workflow_interpreter.tracker import TrackerCapability, WorkItem, WorkItemStatus
from workflow_interpreter.tracker.constants import (
    MSG_BLOCKERS_UNAVAILABLE,
    MSG_BRIEF_REQUIRED,
)

TASK_BRIEF: Final[str] = "task_brief"
MSG_DETACHED: Final[str] = "coordinator checkout is detached"
MSG_DIRTY: Final[str] = "coordinator checkout is not clean"
MSG_CONTRACTOR_GRAPH_MISSING: Final[str] = "foreman contractor_graph setting is missing"
MSG_CONTRACTOR_GRAPH_INVALID: Final[str] = (
    "configured contractor graph is invalid: {reason}"
)
MSG_TASK_BRIEF_MISSING: Final[str] = "stage description is missing or empty"
MSG_TASK_BRIEF_UNDECLARED: Final[str] = (
    "configured contractor graph does not declare task_brief as an instance input"
)
MSG_OTHER_INPUT: Final[str] = (
    "configured contractor graph requires missing instance input {name!r}"
)
MSG_RETRY_NO_RECORD: Final[str] = "retry requires a stored contractor record"
MSG_RETRY_NO_ROOT: Final[str] = "retry requires the stored record to name a prior root"
MSG_EPIC_NO_STAGES: Final[str] = "contractor epic has no stages"
MSG_STAGE_NOT_IN_EPIC: Final[str] = (
    "selected stage {stage_id!r} does not belong to epic {epic_id!r}: the "
    "tracker holds no such direct child. Naming the id is the whole of the "
    "message a caller can act on — an id the tracker cannot read at all lands "
    "here too, now that the read goes through the port (S5)"
)
MSG_MINTED_ELSEWHERE: Final[str] = (
    "tracker ref {stage_id!r} minted task id {minted!r}: this build runs a "
    "task under the id its tracker knows it by, and a ref that needs a "
    "different one needs the tracker port that can translate between them "
    "(store-restructure §3.7, S5)"
)
MSG_ADMISSION_NO_ROOT: Final[str] = (
    "contractor admission requires the stored record to name a root"
)
_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)
EXIT_OK: Final[int] = 0
EXIT_REFUSED: Final[int] = 2


class ContractorCommandState(StrEnum):
    """The mutually exclusive stage-level facts the command reports."""

    PHASE_EXHAUSTED = "phase-exhausted"
    BLOCKED = "blocked"
    RESULT = "result"
    COMPLETED = "completed"
    RECOVERED = "recovered"
    REFUSED = "refused"


class ContractorCommandResult(BaseModel):
    """One JSON-ready command outcome with a distinct refusal exit code."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    exit_code: int
    report: dict[str, object]


class ContractorRefused(ValueError):
    """A caller-visible refusal that is not an interpreter crash."""


def execute_contractor(
    composition: Composition,
    *,
    epic_id: str,
    stage_id: str,
    retry: bool,
    trace: bool,
    retry_landing: bool = False,
    monitored: bool = False,
    brief: Path | None = None,
) -> ContractorCommandResult:
    """Validate, optionally admit, and run exactly the caller-named stage."""
    try:
        return _execute(
            composition,
            epic_id=epic_id,
            stage_id=stage_id,
            retry=retry,
            trace=trace,
            retry_landing=retry_landing,
            monitored=monitored,
            brief=brief,
        )
    except ContractorRefused as refusal:
        return ContractorCommandResult(
            exit_code=EXIT_REFUSED,
            report={
                "epic_id": epic_id,
                "reason": _refusal_reason(refusal),
                "stage_id": stage_id,
                "state": ContractorCommandState.REFUSED.value,
            },
        )
    except (
        AdmissionRefused,
        MonitorUnavailable,
        CoordinationError,
        LockUnavailable,
        StoreOutputError,
        ContractorAdapterError,
        ResolutionError,
        ContractorRefusal,
        NotQuiesced,
        RecordStoreUnavailable,
        ValidationError,
        WrapperDirError,
        GitCommandError,
    ) as refusal:
        if isinstance(refusal, AdmissionRefused) and refusal.blocked:
            return _result(
                ContractorCommandState.BLOCKED,
                epic_id=epic_id,
                stage_id=stage_id,
                blocking_ids=refusal.blocking_ids,
                reason=str(refusal),
            )
        return ContractorCommandResult(
            exit_code=EXIT_REFUSED,
            report={
                "epic_id": epic_id,
                "reason": _refusal_reason(refusal),
                "stage_id": stage_id,
                "state": ContractorCommandState.REFUSED.value,
            },
        )


def _execute(
    composition: Composition,
    *,
    epic_id: str,
    stage_id: str,
    retry: bool,
    trace: bool,
    retry_landing: bool = False,
    monitored: bool = False,
    brief: Path | None = None,
) -> ContractorCommandResult:
    """Apply the required ordering after keeping the trace branch read-only."""
    if retry_landing and (retry or trace):
        raise ContractorRefused(
            "--retry-landing cannot combine with --retry or --trace"
        )
    target_ref = composition.git.attached_branch_ref(cwd=composition.config.repo_root)
    if target_ref is None:
        raise ContractorRefused(MSG_DETACHED)
    # §3.5: both the succession refusal and the close refusal are decided by
    # whether this task's record is already durable in git, and the adapter
    # may not open a ledger of its own.
    adapter = adapter_of(composition)
    # R12: before anything reads or writes this task, refuse the one shape a
    # clean break would corrupt — a record still in flight in the home S4
    # retired. Ahead of the trace branch too: a trace of a task this build
    # cannot see the record of would report it as never prepared.
    assert_quiesced(adapter.tracker, stage_id)
    from workflow_interpreter.contractor.integration import (
        IntegrationGuard,
        prepared_for_stage,
        resume_integration,
        retry_integration,
    )

    adapter.integration_guard = IntegrationGuard(composition)
    if trace:
        return _trace(composition, adapter, epic_id=epic_id, stage_id=stage_id)
    from workflow_interpreter.foreman.replacement import repair_contractor_successor

    repair_contractor_successor(composition, stage_id)
    prior = adapter.stored_record(stage_id)
    # Whether this stage had a record when the command STARTED. The integration
    # branch below resumes into one, so `prior is None` stops being the answer
    # to "is this stage's prepare happening now?" — and the blocker check §3.3
    # puts at prepare would be skipped for every integration stage.
    prepared_here = prior is None
    # Every tracker read of this command is HERE, inside the one branch that
    # only a task with no record takes — which is prepare (§3.3, R4). A task
    # that has prepared is admitted, run, landed and closed from the ledger,
    # so the whole of that is possible with the tracker unreachable.
    if prior is None and TrackerCapability.CHILDREN in adapter.tracker.capabilities:
        stages = _direct_stages(adapter, epic_id)
        if _all_closed(stages) and not retry_landing:
            return _result(
                ContractorCommandState.PHASE_EXHAUSTED,
                epic_id=epic_id,
                stage_id=stage_id,
            )
        stage = adapter.tracker.get(adapter.ref(stage_id))
        if (
            stage is None
            or stage.parent != epic_id
            or not any(row.ref == stage_id for row in stages)
        ):
            raise ContractorRefused(
                MSG_STAGE_NOT_IN_EPIC.format(stage_id=stage_id, epic_id=epic_id)
            )
    pending = (
        prepared_for_stage(composition, epic_id, stage_id)
        if prior is None or prior.integration_digest is not None
        else None
    )
    if pending is not None and prior is None:
        prior = resume_integration(composition, pending)
    elif (
        pending is not None
        and prior is not None
        and pending.predecessor_digest == prior.integration_digest
        and pending.attempt == prior.attempt + 1
    ):
        prior = retry_integration(composition, prior)
        retry = False
    if (
        prior is not None
        and prior.integration_digest is not None
        and prior.state is ContractorState.PREPARED
    ):
        prior = resume_integration(
            composition, adapter.integration_guard.association(prior)
        )
        retry = False
    if retry_landing and (prior is None or prior.root_id is None):
        raise ContractorRefused("--retry-landing requires a stored pending intent")
    if prior is not None:
        if (
            prior.stage_id != stage_id
            or prior.epic_id != epic_id
            or prior.target_ref != target_ref
        ):
            raise ContractorRefused("stage/root ownership mismatch")
        if prior.verification_policy is None:
            raise ContractorRefused(
                "legacy contractor journal lacks verification policy; human attention required"
            )
        if prior.root_id is not None:
            wiring = composition.for_root(_require_root(prior))
            root = wiring.store.reads.load_root(prior.root_id)
            if (
                prior.integration_digest is None
                and prior.successor_key is None
                and root.metadata.instance_key != prior.instance_key
            ) or root.metadata.instance_base_commit != (
                prior.execution_base_commit or prior.expected_base_commit
            ):
                raise ContractorRefused("stage/root ownership mismatch")
            from workflow_interpreter.foreman.replacement import guard_contractor

            guard_contractor(composition, prior)
            if prior.integration_digest is not None:
                adapter.integration_guard.binding(prior, current=False)
            if retry_landing:
                return _land(
                    composition, adapter, prior, recover=False, retry_landing=True
                )
            if (
                wiring.paths.instance_dir / LANDING_INTENT_FILE
            ).exists() or prior.state in (
                ContractorState.LANDING,
                ContractorState.LANDED,
            ):
                if retry:
                    raise ContractorRefused("landing recovery cannot be retried")
                return _land(composition, adapter, prior, recover=True)
    if coordinator_dirt(
        composition.git.status_paths(cwd=composition.config.repo_root),
        task_id=stage_id,
    ):
        raise ContractorRefused(MSG_DIRTY)
    if (
        prior is not None
        and prior.root_id is not None
        and not retry
        and root.metadata.terminal == "shipped"
    ):
        return _land(composition, adapter, prior, recover=False)
    blockers_checked = True
    if prepared_here:
        # A tracker read, so it belongs to prepare and to nothing later
        # (§3.3): blockers are checked once, before the task has a record.
        blockers_checked, blocking = _blockers(composition, adapter, stage_id)
        if blocking:
            return _result(
                ContractorCommandState.BLOCKED,
                epic_id=epic_id,
                stage_id=stage_id,
                blocking_ids=blocking,
            )
    if prior is not None and prior.state is ContractorState.ADMITTED and not retry:
        if (
            composition.git.head_commit(cwd=composition.config.repo_root)
            != prior.expected_base_commit
        ):
            raise ContractorRefused("branch-moved")
        return _run_record(composition, adapter, prior, monitored=monitored)
    if prior is not None and prior.integration_digest is not None and retry:
        return _run_record(
            composition,
            adapter,
            retry_integration(composition, prior),
            monitored=monitored,
        )
    if retry and prior is not None and prior.root_id is not None:
        predecessor = composition.reads_for_root(prior.root_id).load_root(prior.root_id)
        if predecessor.metadata.coordination is not None:
            raise ContractorRefused(
                "coordinated contractor retry requires the original-owner successor operation"
            )
    graph = _contractor_graph(composition)
    task_brief = _brief_for(composition, adapter, epic_id, stage_id, prior, brief)
    expected_base = composition.git.head_commit(cwd=composition.config.repo_root)
    resume_prepared_retry = (
        retry
        and prior is not None
        and prior.state is ContractorState.PREPARED
        and prior.attempt > 1
    )
    successor = (
        _retry_successor(composition, adapter, stage_id)
        if retry and not resume_prepared_retry
        else None
    )
    policy = (
        prior.verification_policy
        if prior is not None
        else VerificationPolicy.pin(
            composition.config.contractor_checks or (), composition.config.repo_root
        )
    )
    with tempfile.TemporaryDirectory(prefix="contract-") as directory:
        brief_path = Path(directory) / "task-brief.md"
        brief_path.write_text(task_brief, encoding="utf-8")
        roots = WorkflowRootProvisioner(
            adapter,
            lambda instance_key, attempt: instantiate(
                composition,
                graph,
                instance_key=instance_key,
                instance_inputs={TASK_BRIEF: brief_path},
                allow_test_flags=False,
                overrides={},
                attempt=attempt,
            ),
            composition.git,
            composition.config.repo_root,
        )
        admission = PhaseAdmission(
            adapter,
            roots,
            lambda: composition.git.head_commit(cwd=composition.config.repo_root),
            verification_policy=policy,
            task_brief=task_brief,
            actor=composition.config.actor,
            blockers_checked=blockers_checked,
        )
        record = (
            admission.admit_successor(
                epic_id,
                stage_id,
                target_ref,
                expected_base,
                successor,
            )
            if successor is not None
            else admission.admit(epic_id, stage_id, target_ref, expected_base)
        )
    return _run_record(composition, adapter, record, monitored=monitored)


def _run_record(
    composition: Composition,
    adapter: ContractorAdapter,
    record: ContractorRecord,
    *,
    monitored: bool = False,
) -> ContractorCommandResult:
    """Resume the admitted root without reprovisioning from current configuration."""
    adapter.guard_integration(record)
    try:
        run = Foreman(composition).run(
            _require_root(record),
            poll_s=RUN_DEFAULT_POLL_S,
            max_wall_s=RUN_DEFAULT_MAX_WALL_S,
            monitored=monitored,
        )
    finally:
        # D6, as S5 rewrote it: the ticks enqueued their attention intents and
        # contacted no tracker. THIS is the driver's exit, so this is where the
        # mirror is written — in a `finally`, because a run that ended badly is
        # exactly the run whose attention flag a human needs to see.
        drain_at_exit(composition)
    latest = adapter.record(record.stage_id)
    if latest != record:
        if (
            record.instance_key not in latest.previous_attempts
            or latest.successor_key is None
        ):
            raise ContractorRefused("contractor changed outside successor lineage")
        adapter.guard_integration(latest)
        record = latest
    if run.report.terminal_node == "shipped":
        return _land(composition, adapter, record, recover=False)
    result = _result(
        ContractorCommandState.RESULT,
        epic_id=record.epic_id,
        stage_id=record.stage_id,
        record=record.model_dump(by_alias=True, mode="json"),
        result=run.model_dump(mode="json"),
    )
    return (
        result.model_copy(update={"exit_code": EXIT_REFUSED})
        if run.attention or run.report.stalled
        else result
    )


def _land(
    composition: Composition,
    adapter: ContractorAdapter,
    record: ContractorRecord,
    *,
    recover: bool,
    retry_landing: bool = False,
) -> ContractorCommandResult:
    """Compose authoritative landing using the admitted policy, including repair."""
    if record.verification_policy is None:
        raise ContractorRefused("contractor verification policy missing")
    wiring = composition.for_root(_require_root(record))
    # D17 and §3.6: the ledger surfaces are composed HERE, from the one
    # connection this process holds, and they are absent only for a wiring
    # with no ledger at all — where the adapter refuses the close instead.
    ledger = composition.ledger
    landing = PhaseLanding(
        adapter,
        composition.git,
        composition.config.repo_root,
        wiring.paths,
        BeadGateAuthority(wiring.store.reads),
        DetachedRepositoryGate(
            composition.git,
            wiring.paths,
            record.verification_policy,
            lambda message: print(message, file=sys.stderr),
        ),
        journal=None
        if ledger is None
        # The journal anchors what it writes (§3.9): the intent row is the
        # fact that says the work may be on the target ref, and it is written
        # after the last activation close — so nothing else carried it through
        # a rebuild (gate B, finding 2a).
        else LandingJournal(
            ledger,
            record.stage_id,
            record.epic_id,
            TaskCheckpoint(ledger, composition.git),
        ),
        export=None
        if ledger is None
        else ExportPin(
            ledger,
            composition.git,
            composition.config.repo_root,
            record.epic_id,
        ),
    )
    try:
        outcome = (
            landing.retry_landing(record.stage_id)
            if retry_landing
            else (
                landing.recover(record.stage_id)
                if recover
                else landing.land(record.stage_id)
            )
        )
    except ContractorRefusal as error:
        return ContractorCommandResult(
            exit_code=EXIT_REFUSED,
            report={
                "epic_id": record.epic_id,
                "stage_id": record.stage_id,
                "root_id": record.root_id,
                "attempt": record.attempt,
                "state": ContractorCommandState.REFUSED.value,
                "disposition": LandingDisposition.HUMAN_ATTENTION.value,
                "reason": str(error),
                "observed_target": composition.git.ref_target(
                    record.target_ref, cwd=composition.config.repo_root
                ),
            },
        )
    if outcome.disposition is not LandingDisposition.CLOSED:
        return ContractorCommandResult(
            exit_code=EXIT_REFUSED,
            report={
                "epic_id": record.epic_id,
                "stage_id": record.stage_id,
                "state": ContractorCommandState.REFUSED.value,
                **outcome.model_dump(mode="json"),
                "reason": outcome.reason or outcome.disposition.value,
            },
        )
    return _result(
        ContractorCommandState.RECOVERED
        if recover
        else ContractorCommandState.COMPLETED,
        epic_id=record.epic_id,
        stage_id=record.stage_id,
        record=adapter.record(record.stage_id).model_dump(by_alias=True, mode="json"),
        result=outcome.model_dump(mode="json"),
    )


def _contractor_graph(composition: Composition) -> Path:
    """Load the configured graph and reject unsupported required inputs first."""
    graph = composition.config.contractor_graph
    if graph is None:
        raise ContractorRefused(MSG_CONTRACTOR_GRAPH_MISSING)
    try:
        definition = load_graph(graph, allow_test_flags=False)
    except (GraphValidationError, OSError) as error:
        raise ContractorRefused(
            MSG_CONTRACTOR_GRAPH_INVALID.format(reason=error)
        ) from error
    instance_sources = tuple(
        source
        for source in definition.document.source
        if source.producer == PRODUCER_INSTANCE
    )
    if not any(source.name == TASK_BRIEF for source in instance_sources):
        raise ContractorRefused(MSG_TASK_BRIEF_UNDECLARED)
    for source in instance_sources:
        if not source.optional and source.name != TASK_BRIEF:
            raise ContractorRefused(MSG_OTHER_INPUT.format(name=source.name))
    return graph


def _task_brief(description: str | None) -> str:
    """Require the selected stage's actual description as the pinned brief."""
    if description is None or not description.strip():
        raise ContractorRefused(MSG_TASK_BRIEF_MISSING)
    return description


def _all_closed(stages: tuple[WorkItem, ...]) -> bool:
    """Whether this epic has nothing left open."""
    return all(stage.status is WorkItemStatus.CLOSED for stage in stages)


def _blockers(
    composition: Composition, adapter: ContractorAdapter, stage_id: str
) -> tuple[bool, tuple[str, ...]]:
    """Whether blockers were checked, and which are still unresolved (R9).

    An absent `BLOCKERS` capability is not liveness ambiguity, so the default
    is to record `blockers_checked=false` and proceed; a repository whose
    dependency graph really does gate work sets `tracker.blockers_required`
    and gets a refusal instead. Either way the record says which policy
    applied, so the trace can tell "nothing blocked it" from "nobody asked".
    """
    tracker = adapter.tracker
    if TrackerCapability.BLOCKERS not in tracker.capabilities:
        if composition.config.tracker.blockers_required:
            raise ContractorRefused(
                MSG_BLOCKERS_UNAVAILABLE.format(kind=tracker.kind.value)
            )
        return False, ()
    return True, tuple(
        blocker.ref
        for blocker in tracker.blockers(adapter.ref(stage_id))
        if not blocker.resolved
    )


def _brief_for(
    composition: Composition,
    adapter: ContractorAdapter,
    epic_id: str,
    stage_id: str,
    prior: ContractorRecord | None,
    supplied: Path | None = None,
) -> str:
    """The task brief, from the SNAPSHOT once one exists (§3.3, R4).

    A task that has prepared owns its brief: it is the one instance input the
    contractor graph requires, it was pinned into the root at admission, and
    re-reading the tracker's description here is what made an offline retry
    impossible — and what let an edited description change the brief of work
    already under way.

    A task that has NOT prepared reads it from the tracker, and the same call
    is where the ledger mints the task's identity from the tracker ref (§3.7):
    prepare is the one moment both facts are available.
    """
    if prior is not None:
        held = adapter.stored(stage_id)
        if held is not None and held.brief is not None:
            return held.brief
    item = adapter.tracker.get(adapter.ref(stage_id))
    if item is None:
        if supplied is None:
            raise ContractorRefused(
                MSG_BRIEF_REQUIRED.format(kind=adapter.tracker.kind.value, ref=stage_id)
            )
        brief = _task_brief(supplied.read_text(encoding="utf-8"))
    else:
        brief = _task_brief(item.brief)
    _mint(composition, adapter, epic_id, stage_id)
    return brief


def _mint(
    composition: Composition,
    adapter: ContractorAdapter,
    epic_id: str,
    stage_id: str,
) -> None:
    """Mint this tracker ref's task id at prepare, and pin the pair (§3.7).

    S3 built the mint and nothing called it. This is its one caller: prepare
    is where a tracker ref first becomes work the engine owns, so it is where
    `tasks.tracker_ref` and `tasks.tracker_kind` are written.

    A bd id already satisfies the grammar, so the minted id IS the ref and
    nothing moves. A ref that mints a DIFFERENT id is refused by name rather
    than run under an id the rest of this command does not use: making the two
    diverge safely is the tracker port's work (S5), not a silent rename here.
    """
    if composition.ledger is None:
        return
    minted = mint_task(
        composition.ledger,
        tracker_ref=stage_id,
        tracker_kind=adapter.tracker.kind,
        epic_id=epic_id,
    )
    if minted != stage_id:
        raise ContractorRefused(
            MSG_MINTED_ELSEWHERE.format(stage_id=stage_id, minted=minted)
        )


def _direct_stages(adapter: ContractorAdapter, epic_id: str) -> tuple[WorkItem, ...]:
    """Require the named epic to contain direct stages before reporting its state."""
    stages = adapter.tracker.children(adapter.ref(epic_id))
    if not stages:
        raise ContractorRefused(MSG_EPIC_NO_STAGES)
    return stages


def _retry_successor(
    composition: Composition,
    adapter: ContractorAdapter,
    stage_id: str,
) -> ContractorRecord:
    """Apply the prior root's retry predicate before persisting a successor."""
    try:
        prior = adapter.record(stage_id)
    except (KeyError, ValidationError) as error:
        raise ContractorRefused(MSG_RETRY_NO_RECORD) from error
    if prior.root_id is None:
        raise ContractorRefused(MSG_RETRY_NO_ROOT)
    wiring = composition.for_root(_require_root(prior))
    root = wiring.store.reads.load_root(prior.root_id)
    frontier = build_frontier(root, wiring.store.reads.instance_records(prior.root_id))
    terminals = root.definition.document.instance.contractor_retry_terminals or ()
    refusal = retry_refusal(prior.state, terminals, frontier)
    if refusal is not None:
        raise ContractorRefused(refusal.value)
    if (
        prior.state is ContractorState.GATE_RED
        and not BeadGateAuthority(wiring.store.reads).verify(prior.root_id).accepted
    ):
        raise ContractorRefused("retry lacks approved ship authority")
    return prior.next_attempt()


def _trace(
    composition: Composition,
    adapter: ContractorAdapter,
    *,
    epic_id: str,
    stage_id: str,
) -> ContractorCommandResult:
    """Render durable stage and root evidence without admitting or running work."""
    state, blocking_ids = _trace_state(composition, adapter, epic_id, stage_id)
    stage = adapter.tracker.get(adapter.ref(stage_id))
    record, relation_error = _record_for_trace(adapter, stage_id)
    report: dict[str, object] = {
        "blocking_ids": blocking_ids,
        "closure": {
            "reason": None if stage is None else stage.close_reason,
            "status": None if stage is None else stage.status.value,
        },
        "epic_id": epic_id,
        "gate_evidence": (),
        "landing_intent": None,
        "receipt_digest": None,
        "relation": None
        if record is None
        else record.model_dump(by_alias=True, mode="json"),
        "relation_error": relation_error,
        "root": None,
        "stage_id": stage_id,
        "state": state.value,
    }
    if record is None or record.root_id is None:
        return ContractorCommandResult(exit_code=EXIT_OK, report=report)
    wiring = composition.for_root(_require_root(record))
    root = wiring.store.reads.load_root(record.root_id)
    frontier = build_frontier(root, wiring.store.reads.instance_records(record.root_id))
    intent = read_record(wiring.paths.instance_dir / LANDING_INTENT_FILE, LandingIntent)
    receipt = read_record(
        wiring.paths.instance_dir / LANDING_RECEIPT_FILE, LandingReceipt
    )
    report.update(
        {
            "gate_evidence": tuple(
                {
                    "artifact_digest": gate.metadata.artifact_digest,
                    "artifact_ref": gate.metadata.artifact_ref,
                    "gate_id": gate.gate_id,
                    "node": gate.metadata.gate_node,
                    "outcome": gate.metadata.outcome,
                    "payload_digest": gate.metadata.payload_digest,
                    "state": gate.metadata.state,
                }
                for gate in frontier.decided_gates
            ),
            "landing_intent": None
            if intent is None
            else intent.model_dump(mode="json"),
            "receipt_digest": record.landing_receipt_digest,
            "root": {
                "base": root.metadata.instance_base_commit,
                "root_id": root.root_id,
                "terminal": frontier.terminal_node,
            },
            "landing_receipt": None
            if receipt is None
            else receipt.model_dump(mode="json"),
        }
    )
    return ContractorCommandResult(exit_code=EXIT_OK, report=report)


def _record_for_trace(
    adapter: ContractorAdapter, stage_id: str
) -> tuple[ContractorRecord | None, str | None]:
    """Read a relation for display while retaining malformed evidence as absence.

    The record moved into the ledger in S4, and with it the error an unreadable
    one raises: `adapter.stored` names it as an adapter refusal (§3.2). This
    degrades on THAT, because `--trace` is the one read-only diagnostic a human
    runs when a record will not parse, and exiting 2 would hide the root, the
    gate evidence and the parse error it exists to show.
    """
    try:
        return adapter.stored_record(stage_id), None
    except ContractorAdapterError as error:
        return None, str(error)


def _trace_state(
    composition: Composition,
    adapter: ContractorAdapter,
    epic_id: str,
    stage_id: str,
) -> tuple[ContractorCommandState, tuple[str, ...]]:
    """Compute the read-only phase fact without selecting or admitting a stage."""
    if TrackerCapability.CHILDREN in adapter.tracker.capabilities and _all_closed(
        _direct_stages(adapter, epic_id)
    ):
        return ContractorCommandState.PHASE_EXHAUSTED, ()
    _checked, blocking = _blockers(composition, adapter, stage_id)
    if blocking:
        return ContractorCommandState.BLOCKED, blocking
    for other, _state in adapter.records.states_of_epic(epic_id):
        if other == stage_id:
            continue
        if not adapter.closure.retired(other):
            return ContractorCommandState.BLOCKED, ()
    return ContractorCommandState.RESULT, ()


def _require_root(record: ContractorRecord) -> str:
    """Keep a malformed admitted relation from reaching the run loop."""
    if record.root_id is None:
        raise ContractorRefused(MSG_ADMISSION_NO_ROOT)
    return _safe_root_id(record.root_id)


def _result(
    state: ContractorCommandState,
    *,
    epic_id: str,
    stage_id: str,
    blocking_ids: tuple[str, ...] = (),
    record: dict[str, object] | None = None,
    reason: str | None = None,
    result: dict[str, object] | None = None,
) -> ContractorCommandResult:
    """Build one sorted-key-ready report for every non-refusal command state."""
    return ContractorCommandResult(
        exit_code=EXIT_OK,
        report={
            "blocking_ids": blocking_ids,
            "epic_id": epic_id,
            "record": record,
            "reason": reason,
            "result": result,
            "stage_id": stage_id,
            "state": state.value,
        },
    )


def _safe_root_id(root_id: str) -> str:
    """Translate only the known identifier validation boundary into a refusal."""
    try:
        return validate_bead_id(root_id)
    except ValueError as error:
        raise ContractorRefusal(str(error)) from error


def _refusal_reason(error: Exception) -> str:
    """Retain invalid field locations without echoing policy argv or environment."""
    validation = error if isinstance(error, ValidationError) else error.__cause__
    if isinstance(validation, ValidationError):
        return "invalid contractor record: " + "; ".join(
            ".".join(str(part) for part in item["loc"]) + ": " + item["type"]
            for item in validation.errors(include_input=False, include_context=False)
        )
    return str(error)
