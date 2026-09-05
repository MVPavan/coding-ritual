"""Settlement of exit evidence into one durable activation close."""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import (
    ActivationRecord,
    BdioError,
    Deviation,
    Evidence,
    ExitRecord,
    GateRecord,
    GateState,
    Lifecycle,
    RootRecord,
    Usage,
)
from workflow_interpreter.bdio.reads import gates_of
from workflow_interpreter.foreman.compose import InstanceWiring
from workflow_interpreter.foreman.constants import (
    DEVIATION_INSTANCE_BRANCH_DIVERGED,
    DEVIATION_UNDECLARED_EFFECTS_ACCEPTED,
    DEVIATION_UNDECLARED_EFFECTS_DISCARDED,
    EFFECTS_NODE,
    HALT_INDETERMINATE,
)
from workflow_interpreter.foreman.finalize import bound_violated, decide
from workflow_interpreter.foreman.gates import effects_gate, halt_gate
from workflow_interpreter.schema.models import Node, Outcome
from workflow_interpreter.supervisor import (
    AuditFlag,
    BranchAdvanceOutcome,
    CompletionEvidence,
    SupervisorError,
)
from workflow_interpreter.supervisor.channels import pinned_verifier_digests
from workflow_interpreter.supervisor.paths import read_record
from workflow_interpreter.supervisor.profile import Profile

_BRANCH_ADVANCED = "instance branch advanced at settle to {commit}"
_MAX_PREDECESSOR_HOPS: Final = 1024


class Settlement(BaseModel):
    """One tick's settlement result; events are deliberately handled elsewhere."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    activation: ActivationRecord
    awaiting: bool = False
    opened: str | None = None
    stalled: str | None = None


def settle(
    wiring: InstanceWiring,
    root: RootRecord,
    node: Node,
    activation: ActivationRecord,
    profile: Profile,
) -> Settlement:
    """Persist evidence exactly once, then close from its recorded verdict.

    A missing completion record invokes replay, which may re-run attribution and
    artifact/output pinning before it writes a replacement completion record.
    """
    if activation.metadata.lifecycle is Lifecycle.EVIDENCE_RECORDED:
        evidence = activation.metadata.evidence
        if evidence is None:
            return Settlement(activation=activation, stalled="evidence is missing")
        try:
            completion = read_record(
                wiring.paths.completion(activation.activation_id), CompletionEvidence
            )
        except (OSError, SupervisorError):
            closed = wiring.store.close_activation(
                activation.activation_id,
                Outcome.ERROR_TRANSPORT,
                evidence=evidence,
                usage=activation.metadata.usage,
                deviations=activation.metadata.deviations,
            )
            return Settlement(activation=closed)
        if completion is None:
            try:
                exit_record = activation.metadata.exit_record or read_record(
                    wiring.paths.exit_file(activation.activation_id), ExitRecord
                )
                if exit_record is None:
                    raise SupervisorError("ExitRecordMissing")
                completion = wiring.observer.replay(
                    activation,
                    node,
                    profile,
                    exit_record,
                    pinned_digests=pinned_verifier_digests(root),
                    previous_tree_oid=_previous_tree_oid(wiring, activation),
                ).completion
            except (OSError, SupervisorError, BdioError) as exc:
                halt = wiring.store.open_gate(
                    root.root_id,
                    halt_gate(
                        HALT_INDETERMINATE.format(
                            detail=f"completion replay: {type(exc).__name__}"
                        )
                    ),
                )
                return Settlement(
                    activation=activation,
                    awaiting=halt.metadata.state is GateState.OPEN,
                    opened=halt.gate_id,
                )
        if not _replay_agrees_with_recorded_evidence(completion, evidence):
            halt = wiring.store.open_gate(
                root.root_id,
                halt_gate(
                    HALT_INDETERMINATE.format(
                        detail="completion replay: durable evidence mismatch"
                    )
                ),
            )
            return Settlement(
                activation=activation,
                awaiting=halt.metadata.state is GateState.OPEN,
                opened=halt.gate_id,
            )
        deviations = _completion_deviations(activation, completion)
        if AuditFlag.BOUND_VIOLATED in completion.audit_flags:
            # Ahead of the effects gate for the reason `finalize.decide` gives
            # on the fresh-observation path: a bound that did not hold is not a
            # runner outcome, so there is nothing for a human to accept about
            # the effects it let through. Closing here dead-ends it at a halt.
            closed = wiring.store.close_activation(
                activation.activation_id,
                completion.outcome,
                evidence=evidence,
                usage=activation.metadata.usage,
                deviations=deviations,
            )
            return Settlement(activation=closed)
        gate = (
            _effects_gate(wiring, root, activation)
            if evidence.undeclared_effects
            else None
        )
        if gate is None and evidence.undeclared_effects:
            artifact = evidence.artifact
            if artifact is None:
                return _close_effects_discarded(
                    wiring,
                    activation,
                    evidence,
                    activation.metadata.usage,
                    deviations,
                )
            gate = wiring.store.open_gate(
                root.root_id, effects_gate(activation, completion.outcome, artifact)
            )
        if gate is not None:
            if gate.metadata.state is GateState.OPEN:
                return Settlement(activation=activation, awaiting=True)
            if gate.metadata.outcome is Outcome.ABANDON:
                return _close_effects_discarded(
                    wiring,
                    activation,
                    evidence,
                    activation.metadata.usage,
                    deviations,
                    gate.gate_id,
                )
            if gate.metadata.outcome is Outcome.APPROVE:
                return _close_recorded_effects_approved(
                    wiring, activation, evidence, gate.gate_id, deviations
                )
            return Settlement(
                activation=activation, stalled="effects gate has invalid outcome"
            )
        closed = wiring.store.close_activation(
            activation.activation_id,
            completion.outcome,
            evidence=evidence,
            usage=activation.metadata.usage,
            deviations=deviations,
        )
        return Settlement(activation=closed)
    if activation.metadata.lifecycle is not Lifecycle.EXIT_RECORDED:
        return Settlement(activation=activation, awaiting=True)
    try:
        exit_record = activation.metadata.exit_record or read_record(
            wiring.paths.exit_file(activation.activation_id), ExitRecord
        )
        if exit_record is None:
            closed = wiring.store.close_activation(
                activation.activation_id,
                Outcome.ERROR_TRANSPORT,
                evidence=Evidence(note="ExitRecordMissing"),
            )
            return Settlement(activation=closed)
        observation = wiring.observer.replay(
            activation,
            node,
            profile,
            exit_record,
            pinned_digests=pinned_verifier_digests(root),
            previous_tree_oid=_previous_tree_oid(wiring, activation),
        )
    except (OSError, SupervisorError) as exc:
        closed = wiring.store.close_activation(
            activation.activation_id,
            Outcome.ERROR_TRANSPORT,
            evidence=Evidence(note=type(exc).__name__),
        )
        return Settlement(activation=closed)
    completion = observation.completion
    evidence = completion.evidence.model_copy(
        update={"claimed_outcome": completion.claimed_outcome}
    )
    diverged = AuditFlag.INSTANCE_BRANCH_DIVERGED in completion.audit_flags
    if (
        completion.branch is not None
        and completion.branch.outcome is BranchAdvanceOutcome.MISSING
        and evidence.artifact is not None
    ):
        again = wiring.workspace.advance_instance_branch(
            evidence.artifact.commit_oid, cwd=wiring.repo_root
        )
        if again.outcome is BranchAdvanceOutcome.MISSING:
            return Settlement(activation=activation, stalled="instance branch missing")
        diverged = diverged or again.outcome is BranchAdvanceOutcome.DIVERGED
        if again.outcome in {
            BranchAdvanceOutcome.ADVANCED,
            BranchAdvanceOutcome.UNCHANGED,
        }:
            note = _BRANCH_ADVANCED.format(commit=evidence.artifact.commit_oid)
            evidence = evidence.model_copy(
                update={
                    "note": note
                    if evidence.note is None
                    else f"{evidence.note}; {note}"
                }
            )
    decision = decide(node, activation, completion)
    if decision.blocked:
        recorded = wiring.store.record_evidence(
            activation.activation_id, evidence, observation.usage
        )
        artifact = evidence.artifact
        if artifact is None:
            return _close_effects_discarded(
                wiring,
                recorded,
                evidence,
                observation.usage,
                recorded.metadata.deviations,
            )
        gate = wiring.store.open_gate(
            root.root_id,
            effects_gate(
                recorded,
                decision.outcome,
                artifact,
            ),
        )
        if gate.metadata.state is GateState.OPEN:
            return Settlement(activation=recorded, awaiting=True, opened=gate.gate_id)
        if gate.metadata.outcome is Outcome.ABANDON:
            return _close_effects_discarded(
                wiring,
                recorded,
                evidence,
                observation.usage,
                recorded.metadata.deviations,
                gate.gate_id,
            )
        if gate.metadata.outcome is Outcome.APPROVE:
            deviations = (
                *recorded.metadata.deviations,
                Deviation(
                    kind=DEVIATION_UNDECLARED_EFFECTS_ACCEPTED,
                    reason="undeclared effects approved",
                    recorded_at="settle",
                    gate_id=gate.gate_id,
                ),
            )
        else:
            return Settlement(
                activation=recorded, stalled="effects gate has invalid outcome"
            )
    else:
        deviations = decision.deviations
        recorded = wiring.store.record_evidence(
            activation.activation_id, evidence, observation.usage
        )
        deviations = (*recorded.metadata.deviations, *deviations)
    if diverged:
        deviations = (
            *deviations,
            Deviation(
                kind=DEVIATION_INSTANCE_BRANCH_DIVERGED,
                reason="instance branch diverged",
                recorded_at="settle",
            ),
        )
    closed = wiring.store.close_activation(
        activation.activation_id,
        decision.outcome,
        evidence=evidence,
        usage=observation.usage,
        deviations=deviations,
    )
    return Settlement(activation=closed)


def _effects_gate(
    wiring: InstanceWiring, root: RootRecord, activation: ActivationRecord
) -> GateRecord | None:
    """Find this activation's effects decision without replaying its exit."""
    return next(
        (
            gate
            for gate in gates_of(wiring.store.reads.instance_beads(root.root_id))
            if gate.metadata.gate_node == EFFECTS_NODE
            and gate.metadata.source_activation_id == activation.activation_id
        ),
        None,
    )


def _close_recorded_effects_approved(
    wiring: InstanceWiring,
    activation: ActivationRecord,
    evidence: Evidence,
    gate_id: str,
    deviations: tuple[Deviation, ...],
) -> Settlement:
    """Close a verified effects approval using only its durable gate outcome."""
    closed = wiring.store.close_activation(
        activation.activation_id,
        _effects_gate_outcome(wiring, activation, gate_id),
        evidence=evidence,
        usage=activation.metadata.usage,
        deviations=(
            *deviations,
            Deviation(
                kind=DEVIATION_UNDECLARED_EFFECTS_ACCEPTED,
                reason="undeclared effects approved",
                recorded_at="settle",
                gate_id=gate_id,
            ),
        ),
    )
    return Settlement(activation=closed)


def _completion_deviations(
    activation: ActivationRecord, completion: CompletionEvidence
) -> tuple[Deviation, ...]:
    """Preserve persisted wrapper facts across a crash-window close."""
    deviations = activation.metadata.deviations
    violation = bound_violated(completion)
    if violation is not None:
        deviations = (*deviations, violation)
    if AuditFlag.INSTANCE_BRANCH_DIVERGED not in completion.audit_flags:
        return deviations
    return (
        *deviations,
        Deviation(
            kind=DEVIATION_INSTANCE_BRANCH_DIVERGED,
            reason="instance branch diverged",
            recorded_at="settle",
        ),
    )


def _replay_agrees_with_recorded_evidence(
    completion: CompletionEvidence, evidence: Evidence
) -> bool:
    """Require a replay's artifact, checks, and claim to match durable evidence."""
    return (
        completion.evidence.artifact == evidence.artifact
        and completion.evidence.verify == evidence.verify
        and completion.claimed_outcome == evidence.claimed_outcome
    )


def _previous_tree_oid(
    wiring: InstanceWiring, activation: ActivationRecord
) -> str | None:
    """Recover the rework artifact identity that §10.5 compares on replay."""
    node = activation.metadata.node
    predecessor = activation
    for _ in range(_MAX_PREDECESSOR_HOPS):
        predecessor_id = _predecessor_activation_id(wiring, predecessor)
        if predecessor_id is None:
            return None
        predecessor = wiring.store.reads.load_activation(predecessor_id)
        evidence = predecessor.metadata.evidence
        if (
            predecessor.metadata.node == node
            and predecessor.metadata.is_completed
            and evidence is not None
            and evidence.artifact is not None
        ):
            return evidence.artifact.tree_oid
    return None


def _predecessor_activation_id(
    wiring: InstanceWiring, activation: ActivationRecord
) -> str | None:
    """Find the activation before one activation, including a gate predecessor."""
    predecessor_id = activation.metadata.predecessor_activation_id
    if predecessor_id is not None or activation.metadata.predecessor_gate_id is None:
        return predecessor_id
    gate = wiring.store.reads.load_gate(activation.metadata.predecessor_gate_id)
    return gate.metadata.source_activation_id


def _effects_gate_outcome(
    wiring: InstanceWiring, activation: ActivationRecord, gate_id: str
) -> Outcome:
    """Read the computed outcome frozen in the verified effects gate request."""
    gate = wiring.store.reads.load_gate(gate_id)
    return gate.metadata.opening_outcome or Outcome.FAIL_CODE


def _close_effects_discarded(
    wiring: InstanceWiring,
    activation: ActivationRecord,
    evidence: Evidence,
    usage: Usage | None,
    deviations: tuple[Deviation, ...],
    gate_id: str | None = None,
) -> Settlement:
    """Fail closed when undeclared effects are rejected or cannot be bound."""
    closed = wiring.store.close_activation(
        activation.activation_id,
        Outcome.FAIL_CODE,
        evidence=evidence,
        usage=usage,
        deviations=(
            *deviations,
            Deviation(
                kind=DEVIATION_UNDECLARED_EFFECTS_DISCARDED,
                reason="undeclared effects discarded",
                recorded_at="settle",
                gate_id=gate_id,
            ),
        ),
    )
    return Settlement(activation=closed)
