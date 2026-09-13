"""Read-only task, root, activation, and bounded raw-log collection."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Protocol, cast

from pydantic import BaseModel, Field, ValidationError

from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.errors import CarrierIntegrityError
from workflow_interpreter.bdio.reads import find_roots, list_activations
from workflow_interpreter.bdio.records import ActivationRecord
from workflow_interpreter.bdio.wire import BeadRecord, Lifecycle
from workflow_interpreter.bridge.adapter import MSG_CLOSE_REASON
from workflow_interpreter.bridge.landing import (
    LANDING_INTENT_FILE,
    LANDING_RECEIPT_FILE,
    LandingIntent,
    LandingReceipt,
)
from workflow_interpreter.bridge.models import PhaseBridgeRecord, PhaseBridgeState
from workflow_interpreter.costs.models import (
    COST_MODEL,
    Diagnostic,
    Measurement,
    TokenUsage,
    UsageObservation,
)
from workflow_interpreter.costs.profiles import LogContext, LogParseResult, parse_log
from workflow_interpreter.supervisor.errors import WrapperDirError
from workflow_interpreter.supervisor.models import ExecLedgerEntry, LaunchReceipt
from workflow_interpreter.supervisor.paths import read_record, record_bytes

EXTERNAL_ATTRIBUTION_SCOPE_GAP = (
    "coordinator, planning, and child usage needs explicit supplement attribution"
)


class ReadClient(Protocol):
    """The BdClient read subset used by task-cost collection."""

    def show(self, bead_id: str) -> BeadRecord:
        """Return one bead row."""
        ...

    def list_beads(
        self,
        *,
        metadata_filters: Mapping[str, str] | None = None,
        issue_type: Any = None,
    ) -> tuple[BeadRecord, ...]:
        """Return bead rows matching metadata filters."""
        ...


class CompletionEvidence(BaseModel):
    """Checks supporting or refusing a whole-task completion claim."""

    model_config = COST_MODEL

    verified: bool
    basis: tuple[str, ...]


class RootSummary(BaseModel):
    """One current or previous phase-bridge attempt root."""

    model_config = COST_MODEL

    root_id: str
    instance_key: str
    attempt: int = Field(ge=1)
    current: bool


class ActivationSummary(BaseModel):
    """Observable lifecycle facts for one activation."""

    model_config = COST_MODEL

    activation_id: str
    root_id: str
    node: str
    round_no: int
    profile: str
    model: str
    lifecycle: str
    outcome: str | None
    started_at: str | None
    ended_at: str | None


class TaskCollection(BaseModel):
    """All read-only usage inputs and diagnostics for one explicit stage."""

    model_config = COST_MODEL

    task_id: str
    epic_id: str | None
    completion: CompletionEvidence
    roots: tuple[RootSummary, ...]
    activations: tuple[ActivationSummary, ...]
    observations: tuple[UsageObservation, ...]
    diagnostics: tuple[Diagnostic, ...]
    uncovered_scope: tuple[str, ...]
    usage_complete: bool
    coverage_complete: bool


def collect_task(
    client: ReadClient,
    stage_id: str,
    *,
    runtime_roots: Mapping[str, Path] | None = None,
    max_log_bytes: int = 32 * 1024 * 1024,
    max_log_events: int = 100_000,
) -> TaskCollection:
    """Collect one explicit stage without invoking a write, launch, or network call."""
    stage = client.show(stage_id)
    diagnostics: list[Diagnostic] = []
    try:
        bridge = PhaseBridgeRecord.model_validate(stage.metadata.get("phase_bridge"))
    except ValidationError:
        return _unreadable_task(stage_id, "phase bridge metadata is invalid")
    if bridge.stage_id != stage_id:
        return _unreadable_task(stage_id, "phase bridge names a different stage")

    root_rows: list[tuple[int, bool, BeadRecord]] = []
    expected_keys = (*bridge.previous_attempts, bridge.instance_key)
    expected_template = (
        f"phase-bridge:{bridge.epic_id}:{bridge.stage_id}:attempt:" + "{attempt}"
    )
    roots_valid = True
    for attempt, instance_key in enumerate(expected_keys, start=1):
        if instance_key != expected_template.format(attempt=attempt):
            diagnostics.append(
                Diagnostic(
                    code="attempt-identity-invalid",
                    source=f"stage:{stage_id}",
                    detail=f"attempt {attempt} does not use the derived instance identity",
                )
            )
            roots_valid = False
        found = find_roots(cast(BdClient, client), instance_key)
        if len(found) != 1:
            diagnostics.append(
                Diagnostic(
                    code="root-resolution-ambiguous",
                    source=f"stage:{stage_id}",
                    detail=f"attempt {attempt} resolves to {len(found)} roots",
                )
            )
            roots_valid = False
            continue
        row = found[0]
        if row.metadata.get("wf_root_id") != row.id:
            diagnostics.append(
                Diagnostic(
                    code="root-identity-mismatch",
                    source=f"root:{row.id}",
                    detail="root self identity does not match its bead identity",
                )
            )
            roots_valid = False
        root_rows.append((attempt, attempt == len(expected_keys), row))

    current_matches = [row for _, current, row in root_rows if current]
    if len(current_matches) != 1 or current_matches[0].id != bridge.root_id:
        diagnostics.append(
            Diagnostic(
                code="current-root-mismatch",
                source=f"stage:{stage_id}",
                detail="bridge current root does not match the resolved current attempt",
            )
        )
        roots_valid = False

    current_root_closed = False
    current_root_terminal_valid: bool | None = False
    if len(current_matches) == 1:
        current_root = current_matches[0]
        terminal = current_root.metadata.get("terminal")
        current_root_closed = current_root.status == "closed"
        current_root_terminal_valid = (
            None if terminal is None else terminal == "shipped"
        )
        if not current_root_closed or current_root_terminal_valid is False:
            diagnostics.append(
                Diagnostic(
                    code="current-root-terminal-contradiction",
                    source=f"root:{current_root.id}",
                    detail="current root is not closed or records a non-shipped terminal",
                )
            )

    expected_close_reason = MSG_CLOSE_REASON.format(
        digest=bridge.landing_receipt_digest
    )
    close_reason_valid = (
        None
        if stage.close_reason is None
        else stage.close_reason == expected_close_reason
    )
    if close_reason_valid is False:
        diagnostics.append(
            Diagnostic(
                code="stage-close-reason-contradiction",
                source=f"stage:{stage_id}",
                detail="stage close reason names a different landing receipt",
            )
        )

    landing_evidence_valid, landing_diagnostic = _landing_evidence_consistency(
        bridge,
        runtime_roots or {},
        max_bytes=max_log_bytes,
    )
    if landing_diagnostic is not None:
        diagnostics.append(landing_diagnostic)

    completion_checks: dict[str, bool | None] = {
        "stage-closed": stage.status == "closed",
        "bridge-closed": bridge.state is PhaseBridgeState.CLOSED,
        "current-root": bool(bridge.root_id),
        "landed-oid": bool(bridge.landed_oid),
        "tree": bool(bridge.tree),
        "gate-receipt-digest": bool(bridge.gate_receipt_digest),
        "landing-receipt-digest": bool(bridge.landing_receipt_digest),
        "attempt-roots": roots_valid and len(root_rows) == len(expected_keys),
        "current-root-closed": current_root_closed,
        "current-root-terminal": current_root_terminal_valid,
        "stage-close-reason": close_reason_valid,
        "landing-records": landing_evidence_valid,
    }
    completion = CompletionEvidence(
        verified=all(valid is not False for valid in completion_checks.values()),
        basis=tuple(
            f"{name}:{'unavailable' if valid is None else 'valid' if valid else 'invalid'}"
            for name, valid in completion_checks.items()
        ),
    )

    summaries: list[ActivationSummary] = []
    observations: list[UsageObservation] = []
    usage_complete = True
    for _, _, root_row in sorted(root_rows, key=lambda item: item[0]):
        try:
            activations = list_activations(cast(BdClient, client), root_row.id)
        except CarrierIntegrityError:
            diagnostics.append(
                Diagnostic(
                    code="activation-carrier-invalid",
                    source=f"root:{root_row.id}",
                    detail="one or more activation carriers are invalid",
                )
            )
            usage_complete = False
            continue
        for activation in activations:
            summaries.append(_activation_summary(activation))
            enriched = _enriched_observations(
                activation,
                runtime_roots or {},
                max_log_bytes=max_log_bytes,
                max_log_events=max_log_events,
            )
            if enriched is not None:
                diagnostics.extend(enriched.diagnostics)
                usage_complete = usage_complete and enriched.complete
                if enriched.observations:
                    observations.extend(enriched.observations)
                    continue
            baseline = _baseline_observation(activation)
            if baseline is None:
                continue
            if isinstance(baseline, Diagnostic):
                diagnostics.append(baseline)
                usage_complete = False
            else:
                observations.append(baseline)

    try:
        observations = list(_deduplicate(observations))
    except ValueError:
        diagnostics.append(
            Diagnostic(
                code="usage-identity-conflict",
                source=f"stage:{stage_id}",
                detail="the same usage identity carries conflicting observations",
            )
        )
        usage_complete = False
        observations = []
    uncovered = (EXTERNAL_ATTRIBUTION_SCOPE_GAP,)
    coverage_complete = completion.verified and usage_complete and not uncovered
    return TaskCollection(
        task_id=stage_id,
        epic_id=bridge.epic_id,
        completion=completion,
        roots=tuple(
            RootSummary(
                root_id=row.id,
                instance_key=str(row.metadata.get("instance_key")),
                attempt=attempt,
                current=current,
            )
            for attempt, current, row in sorted(root_rows, key=lambda item: item[0])
        ),
        activations=tuple(summaries),
        observations=tuple(observations),
        diagnostics=tuple(diagnostics),
        uncovered_scope=uncovered,
        usage_complete=usage_complete,
        coverage_complete=coverage_complete,
    )


def _baseline_observation(
    activation: ActivationRecord,
) -> UsageObservation | Diagnostic | None:
    """Validate normalized durable usage as one activation total."""
    raw = activation.metadata.usage
    source = f"bd:activation:{activation.activation_id}:usage"
    if raw is None or not raw.known:
        metadata = activation.metadata
        if (
            metadata.lifecycle is Lifecycle.MINTED
            and metadata.handle is None
            and metadata.exit_record is None
            and metadata.outcome is None
        ):
            return None
        return Diagnostic(
            code="usage-unreported",
            source=source,
            detail="activation has no known durable token usage",
        )
    try:
        tokens = TokenUsage(
            input=raw.input_tokens,
            cache_read=raw.cache_read_input_tokens,
            cache_write=raw.cache_creation_input_tokens,
            output=raw.output_tokens,
        )
        if all(value is None for value in tokens.additive().values()):
            raise ValueError("all counters absent")
        return UsageObservation(
            identity=f"{activation.metadata.wf_root_id}/{activation.activation_id}/durable",
            provider=_provider(activation.metadata.runner_profile),
            profile=activation.metadata.runner_profile,
            root_id=activation.metadata.wf_root_id,
            activation_id=activation.activation_id,
            exec_id=activation.activation_id,
            session_id=activation.metadata.session_id,
            role=activation.metadata.node,
            model=activation.metadata.model,
            requested_model=activation.metadata.model,
            model_mapping_provenance=(
                "durable requested model only; observed identity unavailable"
            ),
            measurement=Measurement.TERMINAL_CUMULATIVE,
            tokens=tokens,
            source=source,
            vendor_cost_usd=(None if raw.cost_usd is None else Decimal(raw.cost_usd)),
            started_at=(
                None
                if activation.metadata.handle is None
                else activation.metadata.handle.started_at
            ),
            ended_at=(
                None
                if activation.metadata.exit_record is None
                else activation.metadata.exit_record.ended_at
            ),
        )
    except (InvalidOperation, ValidationError, ValueError):
        return Diagnostic(
            code="usage-invalid",
            source=source,
            detail="durable usage has invalid or empty token counters",
        )


def _enriched_observations(
    activation: ActivationRecord,
    runtime_roots: Mapping[str, Path],
    *,
    max_log_bytes: int,
    max_log_events: int,
) -> LogParseResult | None:
    """Parse the known wrapper layout only when its root is explicitly mapped."""
    configured = runtime_roots.get(activation.metadata.wf_root_id)
    if configured is None:
        return None
    try:
        root = configured.resolve(strict=True)
        if not root.is_dir():
            raise ValueError("runtime root is not a directory")
    except (OSError, ValueError):
        return _runtime_failure(
            "runtime-path-invalid", "configured runtime root is invalid"
        )
    activation_dir = root / activation.activation_id
    log = activation_dir / "run.jsonl"
    receipt_path = activation_dir / "launch-receipt.json"
    ledger_path = activation_dir / "exec.ledger"
    try:
        if not log.resolve(strict=True).is_relative_to(root):
            raise ValueError("log escapes configured runtime root")
        if not receipt_path.resolve(strict=True).is_relative_to(root):
            raise ValueError("receipt escapes configured runtime root")
    except (OSError, ValueError):
        return _runtime_failure(
            "runtime-path-invalid",
            "runtime log or receipt is absent or escapes the configured root",
        )
    try:
        receipt = read_record(receipt_path, LaunchReceipt)
    except WrapperDirError:
        return _runtime_failure(
            "launch-receipt-invalid", "launch receipt is malformed or unreadable"
        )
    if receipt is None or receipt.activation_id != activation.activation_id:
        return _runtime_failure(
            "launch-receipt-invalid",
            "launch receipt is absent or names a different activation",
        )
    try:
        if not ledger_path.resolve(strict=True).is_relative_to(root):
            raise ValueError("ledger escapes configured runtime root")
        ledger = _read_exec_ledger(ledger_path, max_bytes=max_log_bytes)
    except (OSError, ValueError):
        return _runtime_failure(
            "exec-ledger-invalid",
            "exec ledger is absent, unsafe, oversized, malformed, or unreadable",
        )
    if len([entry for entry in ledger if entry.launch_id == receipt.launch_id]) != 1:
        return _runtime_failure(
            "exec-ledger-invalid",
            "exec ledger does not prove exactly one matching launch",
        )
    return parse_log(
        log,
        LogContext(
            profile=activation.metadata.runner_profile,
            root_id=activation.metadata.wf_root_id,
            activation_id=activation.activation_id,
            launch_id=receipt.launch_id,
            requested_model=activation.metadata.model,
            model=activation.metadata.model,
            role=activation.metadata.node,
            started_at=receipt.handle.started_at,
            ended_at=(
                None
                if activation.metadata.exit_record is None
                else activation.metadata.exit_record.ended_at
            ),
        ),
        max_bytes=max_log_bytes,
        max_events=max_log_events,
    )


def _read_exec_ledger(path: Path, *, max_bytes: int) -> tuple[ExecLedgerEntry, ...]:
    """Read at most one byte beyond the ledger ceiling and skip torn lines."""
    with path.open("rb") as handle:
        raw = handle.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("ledger exceeds byte limit")
    entries: list[ExecLedgerEntry] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            entries.append(ExecLedgerEntry.model_validate_json(line))
        except ValidationError:
            continue
    return tuple(entries)


def _runtime_failure(code: str, detail: str) -> LogParseResult:
    """Return an incomplete runtime result without reading an unsafe path."""
    return LogParseResult(
        observations=(),
        diagnostics=(Diagnostic(code=code, source="runtime-layout", detail=detail),),
        complete=False,
    )


def _landing_evidence_consistency(
    bridge: PhaseBridgeRecord,
    runtime_roots: Mapping[str, Path],
    *,
    max_bytes: int,
) -> tuple[bool | None, Diagnostic | None]:
    """Cross-check mapped landing records without treating absence as proof."""
    if bridge.root_id is None or bridge.root_id not in runtime_roots:
        return None, None
    source = f"root:{bridge.root_id}:landing"
    try:
        root = runtime_roots[bridge.root_id].resolve(strict=True)
        if not root.is_dir():
            raise ValueError("runtime root is not a directory")
        intent_path = root / LANDING_INTENT_FILE
        receipt_path = root / LANDING_RECEIPT_FILE
        for path in (intent_path, receipt_path):
            if not path.resolve(strict=True).is_relative_to(root):
                raise ValueError("landing record escapes configured runtime root")
            if path.stat().st_size > max_bytes:
                raise ValueError("landing record exceeds byte limit")
        intent = read_record(intent_path, LandingIntent)
        receipt = read_record(receipt_path, LandingReceipt)
    except (OSError, ValueError, WrapperDirError):
        return False, Diagnostic(
            code="landing-evidence-contradiction",
            source=source,
            detail="mapped landing records are absent, unsafe, oversized, or invalid",
        )
    valid = bool(
        intent is not None
        and receipt is not None
        and intent.root_id == bridge.root_id
        and intent.stage == bridge.stage_id
        and intent.attempt == bridge.attempt
        and intent.ref == bridge.target_ref
        and intent.expected_base == bridge.expected_base_commit
        and intent.artifact_oid == bridge.landed_oid
        and intent.tree == bridge.tree
        and intent.gate_receipt_digest == bridge.gate_receipt_digest
        and receipt.intent_digest == hashlib.sha256(record_bytes(intent)).hexdigest()
        and receipt.ref == intent.ref
        and receipt.expected_base == intent.expected_base
        and receipt.signed_oid == intent.artifact_oid
        and receipt.landed_oid == intent.artifact_oid
        and receipt.tree == intent.tree
        and receipt.gate_receipt_digest == intent.gate_receipt_digest
        and receipt.policy_digest == intent.policy_digest
        and (
            bridge.verification_policy is None
            or (
                intent.policy_digest == bridge.verification_policy.digest
                and bridge.verification_policy.matches(receipt.repository_gate_results)
            )
        )
        and bridge.landing_receipt_digest
        == hashlib.sha256(record_bytes(receipt)).hexdigest()
    )
    if valid:
        return True, None
    return False, Diagnostic(
        code="landing-evidence-contradiction",
        source=source,
        detail="mapped landing intent, receipt, and stage relation do not agree",
    )


def _activation_summary(activation: ActivationRecord) -> ActivationSummary:
    """Project one activation onto report-safe lifecycle metadata."""
    metadata = activation.metadata
    return ActivationSummary(
        activation_id=activation.activation_id,
        root_id=metadata.wf_root_id,
        node=metadata.node,
        round_no=metadata.round_no,
        profile=metadata.runner_profile,
        model=metadata.model,
        lifecycle=metadata.lifecycle.value,
        outcome=None if metadata.outcome is None else metadata.outcome.value,
        started_at=None if metadata.handle is None else metadata.handle.started_at,
        ended_at=None
        if metadata.exit_record is None
        else metadata.exit_record.ended_at,
    )


def _deduplicate(
    observations: list[UsageObservation],
) -> tuple[UsageObservation, ...]:
    """Deduplicate identical usage identities and reject conflicts."""
    unique: dict[str, UsageObservation] = {}
    for observation in observations:
        previous = unique.get(observation.identity)
        if previous is not None and previous != observation:
            raise ValueError("conflicting observation")
        unique[observation.identity] = observation
    return tuple(unique[key] for key in sorted(unique))


def _provider(profile: str) -> str:
    """Map a known runner profile to its pricing provider identity."""
    return {"claude": "anthropic", "codex": "openai"}.get(profile, profile)


def _unreadable_task(stage_id: str, detail: str) -> TaskCollection:
    """Build a stable incomplete result for invalid bridge metadata."""
    return TaskCollection(
        task_id=stage_id,
        epic_id=None,
        completion=CompletionEvidence(verified=False, basis=("phase-bridge:invalid",)),
        roots=(),
        activations=(),
        observations=(),
        diagnostics=(
            Diagnostic(
                code="phase-bridge-invalid", source=f"stage:{stage_id}", detail=detail
            ),
        ),
        uncovered_scope=("task execution identity is unavailable",),
        usage_complete=False,
        coverage_complete=False,
    )
