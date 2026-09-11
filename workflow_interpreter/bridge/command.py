"""Composition for the caller-selected, one-stage phase bridge command."""

from __future__ import annotations

import tempfile
from enum import StrEnum
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, ValidationError

from workflow_interpreter.bdio import BdOutputError
from workflow_interpreter.bdio.wire import BeadRecord
from workflow_interpreter.bridge.adapter import (
    PHASE_BRIDGE_METADATA_KEY,
    STATUS_CLOSED,
    PhaseAdapter,
    PhaseAdapterError,
)
from workflow_interpreter.bridge.admission import (
    AdmissionRefused,
    PhaseAdmission,
    WorkflowRootProvisioner,
)
from workflow_interpreter.bridge.landing import (
    LANDING_INTENT_FILE,
    LANDING_RECEIPT_FILE,
    LandingIntent,
    LandingReceipt,
)
from workflow_interpreter.bridge.models import PhaseBridgeRecord
from workflow_interpreter.bridge.retry import retry_refusal
from workflow_interpreter.foreman.compose import Composition
from workflow_interpreter.foreman.constants import (
    RUN_DEFAULT_MAX_WALL_S,
    RUN_DEFAULT_POLL_S,
)
from workflow_interpreter.foreman.errors import ResolutionError
from workflow_interpreter.foreman.frontier import build_frontier
from workflow_interpreter.foreman.resolve import instantiate
from workflow_interpreter.foreman.tick import Foreman
from workflow_interpreter.schema.loader import GraphValidationError, load_graph
from workflow_interpreter.schema.models import PRODUCER_INSTANCE
from workflow_interpreter.supervisor.paths import read_record

TASK_BRIEF: Final[str] = "task_brief"
MSG_DETACHED: Final[str] = "coordinator checkout is detached"
MSG_DIRTY: Final[str] = "coordinator checkout is not clean"
MSG_BRIDGE_GRAPH_MISSING: Final[str] = "foreman bridge_graph setting is missing"
MSG_BRIDGE_GRAPH_INVALID: Final[str] = "configured bridge graph is invalid: {reason}"
MSG_TASK_BRIEF_MISSING: Final[str] = "stage description is missing or empty"
MSG_TASK_BRIEF_UNDECLARED: Final[str] = (
    "configured bridge graph does not declare task_brief as an instance input"
)
MSG_OTHER_INPUT: Final[str] = (
    "configured bridge graph requires missing instance input {name!r}"
)
MSG_RETRY_NO_RECORD: Final[str] = "retry requires a stored phase bridge record"
MSG_RETRY_NO_ROOT: Final[str] = "retry requires the stored record to name a prior root"
MSG_EPIC_NO_STAGES: Final[str] = "phase bridge epic has no stages"
MSG_ADMISSION_NO_ROOT: Final[str] = (
    "phase bridge admission requires the stored record to name a root"
)
EXIT_OK: Final[int] = 0
EXIT_REFUSED: Final[int] = 2


class PhaseBridgeCommandState(StrEnum):
    """The mutually exclusive stage-level facts the command reports."""

    PHASE_EXHAUSTED = "phase-exhausted"
    BLOCKED = "blocked"
    RESULT = "result"
    REFUSED = "refused"


class PhaseBridgeCommandResult(BaseModel):
    """One JSON-ready command outcome with a distinct refusal exit code."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    exit_code: int
    report: dict[str, object]


class PhaseBridgeRefused(ValueError):
    """A caller-visible refusal that is not an interpreter crash."""


def execute_phase_bridge(
    composition: Composition,
    *,
    epic_id: str,
    stage_id: str,
    retry: bool,
    trace: bool,
) -> PhaseBridgeCommandResult:
    """Validate, optionally admit, and run exactly the caller-named stage."""
    try:
        return _execute(
            composition, epic_id=epic_id, stage_id=stage_id, retry=retry, trace=trace
        )
    except PhaseBridgeRefused as refusal:
        return PhaseBridgeCommandResult(
            exit_code=EXIT_REFUSED,
            report={
                "epic_id": epic_id,
                "reason": str(refusal),
                "stage_id": stage_id,
                "state": PhaseBridgeCommandState.REFUSED.value,
            },
        )
    except (
        AdmissionRefused,
        BdOutputError,
        PhaseAdapterError,
        ResolutionError,
    ) as refusal:
        if isinstance(refusal, AdmissionRefused) and refusal.blocked:
            return _result(
                PhaseBridgeCommandState.BLOCKED,
                epic_id=epic_id,
                stage_id=stage_id,
                blocking_ids=refusal.blocking_ids,
                reason=str(refusal),
            )
        return PhaseBridgeCommandResult(
            exit_code=EXIT_REFUSED,
            report={
                "epic_id": epic_id,
                "reason": str(refusal),
                "stage_id": stage_id,
                "state": PhaseBridgeCommandState.REFUSED.value,
            },
        )


def _execute(
    composition: Composition,
    *,
    epic_id: str,
    stage_id: str,
    retry: bool,
    trace: bool,
) -> PhaseBridgeCommandResult:
    """Apply the required ordering after keeping the trace branch read-only."""
    target_ref = composition.git.attached_branch_ref(cwd=composition.config.repo_root)
    if target_ref is None:
        raise PhaseBridgeRefused(MSG_DETACHED)
    if composition.git.status_paths(cwd=composition.config.repo_root):
        raise PhaseBridgeRefused(MSG_DIRTY)
    adapter = PhaseAdapter.from_config(composition.config.bd)
    if trace:
        return _trace(composition, adapter, epic_id=epic_id, stage_id=stage_id)
    stages = _direct_stages(adapter, epic_id)
    if all(stage.status == STATUS_CLOSED for stage in stages):
        return _result(
            PhaseBridgeCommandState.PHASE_EXHAUSTED,
            epic_id=epic_id,
            stage_id=stage_id,
        )
    dependencies = adapter.blocking_dependencies(stage_id)
    if dependencies:
        return _result(
            PhaseBridgeCommandState.BLOCKED,
            epic_id=epic_id,
            stage_id=stage_id,
            blocking_ids=tuple(dependency.id for dependency in dependencies),
        )
    graph = _bridge_graph(composition)
    stage = adapter.show(stage_id)
    task_brief = _task_brief(stage.description)
    expected_base = composition.git.head_commit(cwd=composition.config.repo_root)
    successor = _retry_successor(composition, adapter, stage_id) if retry else None
    with tempfile.TemporaryDirectory(prefix="phase-bridge-") as directory:
        brief_path = Path(directory) / "task-brief.md"
        brief_path.write_text(task_brief, encoding="utf-8")
        roots = WorkflowRootProvisioner(
            adapter,
            lambda instance_key: instantiate(
                composition,
                graph,
                instance_key=instance_key,
                instance_inputs={TASK_BRIEF: brief_path},
                allow_test_flags=False,
                overrides={},
            ),
            composition.git,
            composition.config.repo_root,
        )
        admission = PhaseAdmission(
            adapter,
            roots,
            lambda: composition.git.head_commit(cwd=composition.config.repo_root),
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
    run = Foreman(composition).run(
        _require_root(record),
        poll_s=RUN_DEFAULT_POLL_S,
        max_wall_s=RUN_DEFAULT_MAX_WALL_S,
    )
    return _result(
        PhaseBridgeCommandState.RESULT,
        epic_id=epic_id,
        stage_id=stage_id,
        record=record.model_dump(by_alias=True, mode="json"),
        result=run.model_dump(mode="json"),
    )


def _bridge_graph(composition: Composition) -> Path:
    """Load the configured graph and reject unsupported required inputs first."""
    graph = composition.config.bridge_graph
    if graph is None:
        raise PhaseBridgeRefused(MSG_BRIDGE_GRAPH_MISSING)
    try:
        definition = load_graph(graph, allow_test_flags=False)
    except (GraphValidationError, OSError) as error:
        raise PhaseBridgeRefused(
            MSG_BRIDGE_GRAPH_INVALID.format(reason=error)
        ) from error
    instance_sources = tuple(
        source
        for source in definition.document.source
        if source.producer == PRODUCER_INSTANCE
    )
    if not any(source.name == TASK_BRIEF for source in instance_sources):
        raise PhaseBridgeRefused(MSG_TASK_BRIEF_UNDECLARED)
    for source in instance_sources:
        if not source.optional and source.name != TASK_BRIEF:
            raise PhaseBridgeRefused(MSG_OTHER_INPUT.format(name=source.name))
    return graph


def _task_brief(description: str | None) -> str:
    """Require the selected stage's actual description as the pinned brief."""
    if description is None or not description.strip():
        raise PhaseBridgeRefused(MSG_TASK_BRIEF_MISSING)
    return description


def _direct_stages(adapter: PhaseAdapter, epic_id: str) -> tuple[BeadRecord, ...]:
    """Require the named epic to contain direct stages before reporting its state."""
    stages = adapter.direct_children(epic_id)
    if not stages:
        raise PhaseBridgeRefused(MSG_EPIC_NO_STAGES)
    return stages


def _retry_successor(
    composition: Composition,
    adapter: PhaseAdapter,
    stage_id: str,
) -> PhaseBridgeRecord:
    """Apply the prior root's retry predicate before persisting a successor."""
    try:
        prior = adapter.record(stage_id)
    except (KeyError, ValidationError) as error:
        raise PhaseBridgeRefused(MSG_RETRY_NO_RECORD) from error
    if prior.root_id is None:
        raise PhaseBridgeRefused(MSG_RETRY_NO_ROOT)
    wiring = composition.for_root(prior.root_id)
    root = wiring.store.reads.load_root(prior.root_id)
    frontier = build_frontier(root, wiring.store.reads.instance_beads(prior.root_id))
    terminals = root.definition.document.instance.phase_bridge_retry_terminals or ()
    refusal = retry_refusal(prior.state, terminals, frontier)
    if refusal is not None:
        raise PhaseBridgeRefused(refusal.value)
    return prior.next_attempt()


def _trace(
    composition: Composition,
    adapter: PhaseAdapter,
    *,
    epic_id: str,
    stage_id: str,
) -> PhaseBridgeCommandResult:
    """Render durable stage and root evidence without admitting or running work."""
    state, blocking_ids = _trace_state(adapter, epic_id, stage_id)
    stage = adapter.show(stage_id)
    record, relation_error = _record_for_trace(
        stage.metadata.get(PHASE_BRIDGE_METADATA_KEY)
    )
    report: dict[str, object] = {
        "blocking_ids": blocking_ids,
        "closure": {"reason": stage.close_reason, "status": stage.status},
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
        return PhaseBridgeCommandResult(exit_code=EXIT_OK, report=report)
    wiring = composition.for_root(record.root_id)
    root = wiring.store.reads.load_root(record.root_id)
    frontier = build_frontier(root, wiring.store.reads.instance_beads(record.root_id))
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
    return PhaseBridgeCommandResult(exit_code=EXIT_OK, report=report)


def _record_for_trace(
    raw: object | None,
) -> tuple[PhaseBridgeRecord | None, str | None]:
    """Parse a relation for display while retaining malformed evidence as absence."""
    if raw is None:
        return None, None
    try:
        return PhaseBridgeRecord.model_validate(raw), None
    except ValidationError as error:
        return None, str(error)


def _trace_state(
    adapter: PhaseAdapter, epic_id: str, stage_id: str
) -> tuple[PhaseBridgeCommandState, tuple[str, ...]]:
    """Compute the read-only phase fact without selecting or admitting a stage."""
    stages = _direct_stages(adapter, epic_id)
    if all(stage.status == STATUS_CLOSED for stage in stages):
        return PhaseBridgeCommandState.PHASE_EXHAUSTED, ()
    dependencies = adapter.blocking_dependencies(stage_id)
    if dependencies:
        return (
            PhaseBridgeCommandState.BLOCKED,
            tuple(dependency.id for dependency in dependencies),
        )
    for stage in stages:
        if stage.id == stage_id or stage.status == STATUS_CLOSED:
            continue
        if stage.metadata.get(PHASE_BRIDGE_METADATA_KEY) is not None:
            return PhaseBridgeCommandState.BLOCKED, ()
    return PhaseBridgeCommandState.RESULT, ()


def _require_root(record: PhaseBridgeRecord) -> str:
    """Keep a malformed admitted relation from reaching the run loop."""
    if record.root_id is None:
        raise PhaseBridgeRefused(MSG_ADMISSION_NO_ROOT)
    return record.root_id


def _result(
    state: PhaseBridgeCommandState,
    *,
    epic_id: str,
    stage_id: str,
    blocking_ids: tuple[str, ...] = (),
    record: dict[str, object] | None = None,
    reason: str | None = None,
    result: dict[str, object] | None = None,
) -> PhaseBridgeCommandResult:
    """Build one sorted-key-ready report for every non-refusal command state."""
    return PhaseBridgeCommandResult(
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
