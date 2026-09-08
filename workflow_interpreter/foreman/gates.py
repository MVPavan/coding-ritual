"""Foreman-side construction and signed intake of human gates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

import structlog
from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import (
    ActivationRecord,
    ArtifactIdentity,
    BindsMode,
    GateArtifact,
    GateOpenRequest,
    GatePayload,
    GateReason,
    GateRecord,
    GateVerificationError,
    RootRecord,
    WorkflowStore,
    canonical_payload_bytes,
)
from workflow_interpreter.foreman.constants import (
    EFFECTS_NODE,
    GATE_NONCE_PLACEHOLDER,
    GATES_DIR,
    HALT_BOUND_VIOLATED,
    HALT_BRANCH_DIVERGED,
    HALT_FAIL_CODE,
    HALT_INPUTS_UNAVAILABLE,
    HALT_NODE,
    HALT_PRECONDITION_REFUSED,
    HALT_SANDBOX_UNAVAILABLE,
    HALT_UNUSABLE_RESOLUTION,
    NO_ARTIFACT_OID,
)
from workflow_interpreter.schema.graph_index import GraphIndex
from workflow_interpreter.schema.models import Outcome
from workflow_interpreter.supervisor.gitio import Git
from workflow_interpreter.supervisor.paths import WrapperPaths, fsync_dir, write_durable
from workflow_interpreter.supervisor.profile import Profile

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

_PAYLOAD = "payload.json"
_SIGNATURE = "payload.json.sig"
_REFUSAL = "refusal.json"
_DEAD_END_REASONS = frozenset(
    reason.split(":", 1)[0]
    for reason in (
        HALT_FAIL_CODE,
        HALT_BRANCH_DIVERGED,
        HALT_PRECONDITION_REFUSED,
        HALT_INPUTS_UNAVAILABLE,
        HALT_SANDBOX_UNAVAILABLE,
        HALT_UNUSABLE_RESOLUTION,
        HALT_BOUND_VIOLATED,
    )
)


class IntakeResult(BaseModel):
    """One gate inbox observation: absent, refused, or durably closed."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    gate: GateRecord | None = None
    refusal: str | None = None


def transition_gate(
    git: Git,
    repo_root: Path,
    index: GraphIndex,
    gate_node: str,
    source: ActivationRecord,
    opening_outcome: Outcome,
) -> GateOpenRequest:
    """Build a transition gate bound to the source's verified artifact."""
    node = index.nodes[gate_node]
    evidence = source.metadata.evidence
    artifact = None if evidence is None else evidence.artifact
    artifact_ref = source.metadata.intended_base_commit
    artifact_digest: str
    if artifact is not None:
        artifact_ref = artifact.commit_oid
        artifact_digest = artifact.tree_oid
    else:
        artifact_digest = git.tree_oid(artifact_ref, cwd=repo_root)
    return GateOpenRequest(
        gate_node=gate_node,
        outcomes=node.outcomes or (),
        binds=node.binds or BindsMode.IMMUTABLE,
        source_activation_id=source.activation_id,
        opening_outcome=opening_outcome,
        region=source.metadata.region,
        round_no=source.metadata.round_no,
        artifact_ref=artifact_ref,
        artifact_digest=artifact_digest,
    )


def exhaustion_gate(
    index: GraphIndex, source: ActivationRecord, target: str
) -> GateOpenRequest:
    """Build the bounded-region approval gate for one exhausted round.

    Outcomes come from the TARGET NODE, exactly as `transition_gate` takes
    them, and not from a vocabulary fixed per gate kind. A verb the node does
    not declare has no edge, so it routes to the graph fallback — and when the
    fallback is itself a gate node, the instance stalls on "gate route is not
    a task" forever, having already consumed the human's signed approval
    (cr-mub, found by the live DRILL-27 run, not by the lab).
    """
    return GateOpenRequest(
        gate_node=target,
        outcomes=index.nodes[target].outcomes or (),
        gate_reason=GateReason.EXHAUSTION,
        source_activation_id=source.activation_id,
        opening_outcome=source.metadata.outcome,
        region=source.metadata.region,
        round_no=source.metadata.round_no,
    )


def no_progress_gate(
    index: GraphIndex, source: ActivationRecord, target: str
) -> GateOpenRequest:
    """Build the human gate that resolves a no-progress breaker.

    Offers the target node's own declared outcomes — see `exhaustion_gate`
    for why a fixed per-kind vocabulary is a dead end.
    """
    return GateOpenRequest(
        gate_node=target,
        outcomes=index.nodes[target].outcomes or (),
        source_activation_id=source.activation_id,
        opening_outcome=source.metadata.outcome,
        region=source.metadata.region,
        round_no=source.metadata.round_no,
    )


def effects_gate(
    source: ActivationRecord, outcome: Outcome, artifact: ArtifactIdentity
) -> GateOpenRequest:
    """Build the effects-decision gate for an activation's declared residue."""
    return GateOpenRequest(
        gate_node=EFFECTS_NODE,
        outcomes=(Outcome.APPROVE, Outcome.ABANDON),
        source_activation_id=source.activation_id,
        opening_outcome=outcome,
        region=source.metadata.region,
        round_no=source.metadata.round_no,
        artifact_ref=artifact.commit_oid,
        artifact_digest=artifact.tree_oid,
    )


def halt_gate(
    reason: str,
    *,
    source: ActivationRecord | None = None,
    resume_hint: str | None = None,
) -> GateOpenRequest:
    """Build the one serial human halt gate, with dead-end source provenance."""
    kind = reason.split(":", 1)[0]
    if kind in _DEAD_END_REASONS and source is None:
        raise ValueError("dead-end halt requires its source")
    dead_end = kind in _DEAD_END_REASONS and source is not None
    return GateOpenRequest(
        gate_node=HALT_NODE,
        outcomes=(Outcome.APPROVE, Outcome.REBUDGET, Outcome.ABANDON),
        gate_reason=GateReason.HALT,
        source_activation_id=(source.activation_id if dead_end and source else None),
        region=source.metadata.region if dead_end and source else None,
        round_no=source.metadata.round_no if dead_end and source else None,
        halt_reason=reason,
        resume_hint=resume_hint,
    )


def resume_hint(profile: Profile, activation: ActivationRecord) -> str | None:
    """Render a profile-owned continuation hint when a session was recorded."""
    handle = activation.metadata.handle
    session_id = (
        handle.session_id if handle is not None else ""
    ) or activation.metadata.session_id
    return None if not session_id else profile.build_resume_hint(session_id)


def inbox_dir(paths: WrapperPaths, gate: GateRecord) -> Path:
    """Name the one directory a §9 approval for this gate is dropped into.

    The single expression `status`/`run` render and `ensure_inbox` create, so
    the reported path and the created directory cannot drift apart.
    """
    return paths.instance_dir / GATES_DIR / gate.metadata.gate_key


def ensure_inbox(paths: WrapperPaths, gate: GateRecord) -> Path:
    """Create the gate's inbox directory as the gate opens, and name it."""
    directory = inbox_dir(paths, gate)
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as failed:
        # The gate bead is already durable, so losing it here would be worse
        # than an absent directory: report the path anyway and let the next
        # `status` show the operator what is missing.
        _LOG.error("wf.gate.inbox_unwritable", path=str(directory), error=str(failed))
    return directory


def intake(
    store: WorkflowStore, root: RootRecord, gate: GateRecord, inbox: Path
) -> IntakeResult:
    """Verify and close one open gate when its complete signed payload exists."""
    directory = inbox / gate.metadata.gate_key
    payload = directory / _PAYLOAD
    signature = directory / _SIGNATURE
    if not payload.exists() or not signature.exists():
        return IntakeResult()
    try:
        closed = store.close_gate_verified(
            root.root_id,
            gate.gate_id,
            payload_bytes=payload.read_bytes(),
            signature=signature.read_bytes(),
        )
    except GateVerificationError as exc:
        reason = str(exc)
        try:
            write_durable(
                directory / _REFUSAL,
                (
                    json.dumps(
                        {"error": type(exc).__name__, "reason": reason}, sort_keys=True
                    )
                    + "\n"
                ).encode("utf-8"),
            )
        except OSError:
            pass
        return IntakeResult(refusal=reason)
    try:
        (directory / _REFUSAL).unlink(missing_ok=True)
        fsync_dir(directory)
    except OSError:
        pass
    return IntakeResult(gate=closed)


def _template_outcome(outcomes: tuple[Outcome, ...]) -> Outcome:
    """Pick a template outcome that is signable with the nonce alone.

    The template's contract is that replacing the nonce yields the exact bytes
    a human signs, so it must not render an outcome whose payload needs a field
    the template cannot supply: §9 makes `bound_mutation` legal IFF the outcome
    is `rebudget`, and required by it. Taking `outcomes[0]` happened to be safe
    only while every gate offered `approve` first; once a gate offers its own
    node's verbs (cr-mub), `triage` leads with `rebudget`.
    """
    return next(
        (item for item in outcomes if item is not Outcome.REBUDGET), outcomes[0]
    )


def payload_template(root: RootRecord, gate: GateRecord) -> str:
    """Render the unsigned canonical approval shape for one gate inbox."""
    artifact = GateArtifact(
        commit_oid=gate.metadata.artifact_ref or NO_ARTIFACT_OID,
        tree_oid=gate.metadata.artifact_digest or NO_ARTIFACT_OID,
    )
    return canonical_payload_bytes(
        GatePayload(
            graph_id=root.definition.document.graph.id,
            root_id=root.root_id,
            gate_key=gate.metadata.gate_key,
            outcome=_template_outcome(gate.metadata.outcomes),
            artifact=artifact,
            nonce=GATE_NONCE_PLACEHOLDER,
        )
    ).decode("utf-8")
