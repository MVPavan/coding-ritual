"""Settlement of exit evidence into one durable activation close."""

from __future__ import annotations

import time
from typing import Final

import structlog
from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import (
    ActivationRecord,
    Deviation,
    Evidence,
    ExitRecord,
    GateRecord,
    GateState,
    Lifecycle,
    RootRecord,
    StoreError,
    StoreTransportError,
    Usage,
)
from workflow_interpreter.bdio.errors import StoreBusyRefusal
from workflow_interpreter.bdio.reads import gates_of
from workflow_interpreter.contracts.execution import CrewName
from workflow_interpreter.foreman.compose import InstanceWiring
from workflow_interpreter.foreman.constants import (
    DEVIATION_INSTANCE_BRANCH_DIVERGED,
    DEVIATION_UNDECLARED_EFFECTS_ACCEPTED,
    DEVIATION_UNDECLARED_EFFECTS_DISCARDED,
    EFFECTS_NODE,
    HALT_INDETERMINATE,
)
from workflow_interpreter.foreman.execution import resolved_static_node
from workflow_interpreter.foreman.finalize import bound_violated, decide
from workflow_interpreter.foreman.gates import effects_gate, halt_gate
from workflow_interpreter.inspector import (
    AuditFlag,
    BranchAdvanceOutcome,
    CompletionEvidence,
    InspectorError,
    SnapshotFailed,
)
from workflow_interpreter.inspector.channels import pinned_verifier_digests
from workflow_interpreter.inspector.paths import read_record
from workflow_interpreter.inspector.profile import (
    Profile,
    SessionObservationState,
    observe_session,
)
from workflow_interpreter.schema.models import IsolationMode, Node, Outcome

_BRANCH_ADVANCED = "instance branch advanced at settle to {commit}"
MSG_SESSION_TREE_UNPUBLISHED: Final = "session tree publication: {error}"
"""A retryable settle stall: the §3 tree OID is not in bd yet."""
MSG_SESSION_UNREGISTERED: Final = "session registration from the log: {error}"
"""A retryable settle stall: an observed vendor session is not in bd yet."""
DEVIATION_SESSION_UNREGISTERED: Final = "session_unregistered"
"""The turn closed without a vendor session a later resume could rejoin."""
MSG_SESSION_LOG_UNREADABLE: Final = "session log unreadable"
SESSION_LOG_READ_ATTEMPTS: Final[int] = 3
SESSION_LOG_READ_BACKOFF_S: Final[float] = 0.01
_TRANSIENT_STORE_ERRORS: Final[tuple[type[StoreError], ...]] = (
    StoreTransportError,
    StoreBusyRefusal,
)
"""The store's own transient causes (`bdio/errors.py`): a transport that failed
and a backend contended past its wait. Every other `StoreError` is a defect
that a retry reproduces, so a settle stalled on one would stall forever."""
_LOG: Final = structlog.get_logger(__name__)
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
    """Verify and durably close before removing disposable activation tools."""
    from workflow_interpreter.inspector.toolchain_cleanup import cleanup_toolchain

    result = _settle(wiring, root, node, activation, profile)
    if not result.activation.metadata.is_completed:
        return result
    if not activation.metadata.is_completed:
        # The durable close carries the deviation; later ticks cannot warn again.
        for deviation in result.activation.metadata.deviations:
            if deviation.kind == DEVIATION_SESSION_UNREGISTERED:
                _LOG.warning(
                    "wf.settle.session_unregistered",
                    activation_id=activation.activation_id,
                    reason=deviation.reason,
                )
    cleanup_toolchain(wiring.paths, result.activation)
    return result


def _settle(
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
    unregistered: tuple[Deviation, ...] = ()
    if activation.metadata.lifecycle in (
        Lifecycle.EXIT_RECORDED,
        Lifecycle.EVIDENCE_RECORDED,
    ):
        try:
            wiring.workspace.preserve_interrupted(activation, node)
        except (OSError, InspectorError) as exc:
            return Settlement(
                activation=activation,
                stalled=f"interrupted work preservation: {exc}",
            )
        try:
            activation = _publish_session_tree(wiring, activation, node)
        except (OSError, InspectorError, StoreError) as exc:
            return Settlement(
                activation=activation,
                stalled=MSG_SESSION_TREE_UNPUBLISHED.format(error=exc),
            )
        try:
            activation, unregistered = _register_logged_session(
                wiring, root, activation, profile
            )
        except _TRANSIENT_STORE_ERRORS as exc:
            return Settlement(
                activation=activation,
                stalled=MSG_SESSION_UNREGISTERED.format(error=exc),
            )
    if activation.metadata.lifecycle is Lifecycle.EVIDENCE_RECORDED:
        evidence = activation.metadata.evidence
        if evidence is None:
            return Settlement(activation=activation, stalled="evidence is missing")
        try:
            completion = read_record(
                wiring.paths.completion(activation.activation_id), CompletionEvidence
            )
        except (OSError, InspectorError):
            closed = wiring.store.close_activation(
                activation.activation_id,
                Outcome.ERROR_TRANSPORT,
                evidence=evidence,
                usage=activation.metadata.usage,
                deviations=unregistered,
            )
            return Settlement(activation=closed)
        if completion is None:
            try:
                exit_record = activation.metadata.exit_record or read_record(
                    wiring.paths.exit_file(activation.activation_id), ExitRecord
                )
                if exit_record is None:
                    raise InspectorError("ExitRecordMissing")
                completion = wiring.observer.replay(
                    activation,
                    node,
                    profile,
                    exit_record,
                    pinned_digests=pinned_verifier_digests(root),
                    previous_tree_oid=_previous_tree_oid(wiring, activation),
                    run_identity=root.metadata.run_identity,
                ).completion
            except SnapshotFailed as exc:
                return Settlement(activation=activation, stalled=str(exc))
            except (OSError, InspectorError, StoreError) as exc:
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
        deviations = (*_completion_deviations(completion), *unregistered)
        if AuditFlag.BOUND_VIOLATED in completion.audit_flags:
            # Ahead of the effects gate for the reason `finalize.decide` gives
            # on the fresh-observation path: a bound that did not hold is not a
            # crew outcome, so there is nothing for a human to accept about
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
                deviations=unregistered,
            )
            return Settlement(activation=closed)
        observation = wiring.observer.replay(
            activation,
            node,
            profile,
            exit_record,
            pinned_digests=pinned_verifier_digests(root),
            previous_tree_oid=_previous_tree_oid(wiring, activation),
            run_identity=root.metadata.run_identity,
        )
    except SnapshotFailed as exc:
        return Settlement(activation=activation, stalled=str(exc))
    except (OSError, InspectorError) as exc:
        closed = wiring.store.close_activation(
            activation.activation_id,
            Outcome.ERROR_TRANSPORT,
            evidence=Evidence(note=type(exc).__name__),
            deviations=unregistered,
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
    decided = (*decision.deviations, *unregistered)
    if decision.blocked:
        recorded = wiring.store.record_evidence(
            activation.activation_id, evidence, observation.usage
        )
        artifact = evidence.artifact
        if artifact is None:
            return _close_effects_discarded(
                wiring, recorded, evidence, observation.usage, decided
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
                decided,
                gate.gate_id,
            )
        if gate.metadata.outcome is Outcome.APPROVE:
            deviations = (
                *decided,
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
        wiring.store.record_evidence(
            activation.activation_id, evidence, observation.usage
        )
        # Only what this close adds: `close_activation` appends it after every
        # deviation the record already carries, so re-reading them here recorded
        # each of them twice more (cr-n2z.9).
        deviations = decided
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
            for gate in gates_of(wiring.store.reads.instance_records(root.root_id))
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
    completion: CompletionEvidence,
) -> tuple[Deviation, ...]:
    """The persisted wrapper facts a crash-window close ADDS, in order.

    Starts empty: the activation's own deviations are already on the record and
    `close_activation` merges them ahead of these (cr-n2z.9).
    """
    deviations: tuple[Deviation, ...] = ()
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


def _publish_session_tree(
    wiring: InstanceWiring, activation: ActivationRecord, node: Node
) -> ActivationRecord:
    """Publish the §3 tree a writing turn left, before its close makes it a source.

    The bytes were pinned at the exit, while the wrapper still held the band;
    this states their OID in bd at the last moment before `is_completed` lets
    a later activation resume the session that produced them. A store refusal
    propagates so the settle STALLS and retries: closing without the OID would
    make the next resume of this writer halt on MISSING_SNAPSHOT over what was
    only a transient bd failure.
    """
    if not node.writes:
        return activation
    tree_oid = wiring.workspace.session_tree_oid(activation.activation_id)
    if tree_oid is None or activation.metadata.session_tree_oid == tree_oid:
        return activation
    try:
        return wiring.store.record_session_tree(activation.activation_id, tree_oid)
    except StoreError:
        # R1: the frozen app-server crew never resumes onto this OID and its
        # pre-epic settle never waited on it, so a failure there stays silent.
        if _is_appserver(activation):
            return activation
        raise


def _register_logged_session(
    wiring: InstanceWiring,
    root: RootRecord,
    activation: ActivationRecord,
    profile: Profile,
) -> tuple[ActivationRecord, tuple[Deviation, ...]]:
    """Register a vendor session the watch saw in the log but never recorded.

    The monitor mirrors the identity each cycle, and a bd failure on its FINAL
    cycle is never retried there: closing the turn unregistered would make the
    next resume silently go fresh (`unregistered_source`) and reset the tree a
    writer's session was left on. Only an OBSERVED identity is registered —
    §5.6 recovery's rescan rule — and a TRANSIENT store failure propagates so
    the settle stalls and retries rather than sealing the record without it.

    A permanent refusal cannot be retried away: claude may ignore the
    `--session-id` it was handed, so the logged id contradicts the recorded one
    on every tick. That turn, like one whose log cannot be read, closes
    unregistered with the returned deviation saying why.
    """
    if activation.metadata.session_registration is not None:
        return activation, ()
    for attempt in range(SESSION_LOG_READ_ATTEMPTS):
        try:
            observation = observe_session(
                root, activation, profile, raise_read_error=True
            )
            break
        except OSError:
            if attempt + 1 == SESSION_LOG_READ_ATTEMPTS:
                return activation, _unregistered(activation, MSG_SESSION_LOG_UNREADABLE)
            time.sleep(SESSION_LOG_READ_BACKOFF_S)
    registration = observation.registration
    if observation.state is SessionObservationState.UNREADABLE:
        return activation, _unregistered(activation, MSG_SESSION_LOG_UNREADABLE)
    if registration is None:
        return activation, ()
    try:
        registered = wiring.store.register_session(
            activation.activation_id, registration
        )
    except _TRANSIENT_STORE_ERRORS:
        raise
    except StoreError as exc:
        return activation, _unregistered(activation, f"{type(exc).__name__}: {exc}")
    return registered, ()


def _unregistered(activation: ActivationRecord, reason: str) -> tuple[Deviation, ...]:
    """Name on the close why a turn stays unregistered."""
    return (
        Deviation(
            kind=DEVIATION_SESSION_UNREGISTERED,
            reason=reason,
            recorded_at="settle",
        ),
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


def reviewed_tree_oid(
    wiring: InstanceWiring, root: RootRecord, activation: ActivationRecord
) -> str | None:
    """The §3 tree a non-writer must find: what the writer it reviews pinned.

    Only where both run in the SAME checkout — an in-repo writer reviewed from
    the worktree left its bytes somewhere else — and only where that writer
    published a session tree. `None` leaves the observation record-only.
    """
    node = resolved_static_node(root, activation.metadata.node)
    # R1: a frozen app-server reviewer keeps its pre-epic launch unchanged.
    if node.writes or _is_appserver(activation):
        return None
    # The writer reviewed is the NEAREST writer back: a second reviewer, or a
    # gate whose source was a reviewer, changes no tree in between.
    predecessor = activation
    for _ in range(_MAX_PREDECESSOR_HOPS):
        predecessor_id = _predecessor_activation_id(wiring, predecessor)
        if predecessor_id is None:
            return None
        predecessor = wiring.store.reads.load_activation(predecessor_id)
        writer = resolved_static_node(root, predecessor.metadata.node)
        if not writer.writes:
            continue
        same_checkout = (writer.isolation is IsolationMode.IN_REPO) == (
            node.isolation is IsolationMode.IN_REPO
        )
        return predecessor.metadata.session_tree_oid if same_checkout else None
    return None


def _is_appserver(activation: ActivationRecord) -> bool:
    """Whether this activation runs the frozen app-server crew (R1)."""
    return (
        activation.metadata.crew_profile.removeprefix("profile:")
        == CrewName.CODEX_APPSERVER.value
    )


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
