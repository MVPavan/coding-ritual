"""The detached wrapper entrypoint for one already-minted activation."""

from __future__ import annotations

from enum import StrEnum
from time import monotonic, sleep

from workflow_interpreter.bdio import (
    ActivationRecord,
    Deviation,
    Evidence,
    Lifecycle,
    LifecycleConflictError,
    LossyWriteError,
    MintRequest,
    Outcome,
    RootRecord,
)
from workflow_interpreter.bdio.constants import (
    DEVIATION_FORK_BARRIER_ABORT,
    DEVIATION_INPUTS_UNAVAILABLE,
    DEVIATION_PRECONDITION_REFUSED,
    DEVIATION_SANDBOX_UNAVAILABLE,
)
from workflow_interpreter.foreman.close import _previous_tree_oid
from workflow_interpreter.foreman.compose import (
    Composition,
    InstanceWiring,
    WrapperLaunch,
)
from workflow_interpreter.foreman.constants import DISPATCH_REQUEST, WRAPPER_LOCK
from workflow_interpreter.foreman.execution import resolved_node
from workflow_interpreter.foreman.identifiers import activation_dir, validate_bead_id
from workflow_interpreter.foreman.inputs import (
    DefaultComposer,
    InputsUnavailable,
    materialize,
)
from workflow_interpreter.profiles.errors import TaskRefused, UnsupportedOptionError
from workflow_interpreter.supervisor.band import BandLock
from workflow_interpreter.supervisor.channels import pinned_verifier_digests
from workflow_interpreter.supervisor.errors import (
    BandNotHeld,
    ContinuationRefused,
    DirtyTreeRefused,
    ExecLedgerError,
    ForkBarrierAbortError,
    ForkBarrierError,
    LockUnavailable,
    PreconditionRefused,
    SandboxUnavailable,
    SupervisorError,
)
from workflow_interpreter.supervisor.gitio import Git
from workflow_interpreter.supervisor.launch import TaskBuilder
from workflow_interpreter.supervisor.models import LaunchOutcome
from workflow_interpreter.supervisor.paths import read_record
from workflow_interpreter.supervisor.profile import RunnerChannels, TaskSpec

_DEVIATION_CONTINUATION_REFUSED = "continuation_refused"


def wrapper_alive(wiring: InstanceWiring, activation_id: str) -> bool:
    """Return whether another wrapper currently holds this activation's lock."""
    lock = BandLock(wiring.paths.activation_dir(activation_id) / WRAPPER_LOCK)
    try:
        lock.acquire()
    except LockUnavailable:
        return True
    lock.release()
    return False


def _precondition_reason(error: PreconditionRefused) -> str:
    """Name the human state a precondition refusal protected, when available."""
    if not isinstance(error, DirtyTreeRefused):
        return str(error)
    if error.protected_paths:
        return ", ".join(error.protected_paths)
    return error.protected_head or str(error)


def _close_error(
    wiring: InstanceWiring,
    activation_id: str,
    outcome: Outcome,
    error: Exception,
    *,
    deviations: tuple[Deviation, ...] = (),
) -> WrapperExit:
    """Persist a mapped wrapper failure while the activation is still minted."""
    try:
        wiring.store.close_activation(
            activation_id,
            outcome,
            evidence=Evidence(note=str(error)),
            deviations=deviations,
        )
    except LifecycleConflictError:
        if wiring.store.reads.load_activation(activation_id).metadata.is_settled:
            return WrapperExit.CLOSED_BY_TICK
        raise
    return WrapperExit.DONE


class WrapperExit(StrEnum):
    """The limited results a detached wrapper may report to its parent."""

    DONE = "done"
    LOCKED = "locked"
    STALE = "stale"
    CLOSED_BY_TICK = "closed_by_tick"
    FAILED = "failed"


def _request(activation_id: str, wiring: InstanceWiring) -> MintRequest:
    """Load the durable dispatch request, rebuilding only crash-safe metadata."""
    launch = read_record(
        wiring.paths.activation_dir(activation_id) / DISPATCH_REQUEST,
        WrapperLaunch,
    )
    if launch is not None:
        return launch.request
    activation = wiring.store.reads.load_activation(activation_id)
    meta = activation.metadata
    return MintRequest(
        node=meta.node,
        mint_reason=meta.mint_reason,
        runner_profile=meta.runner_profile,
        model=meta.model,
        session_id=meta.session_id,
        predecessor_activation_id=meta.predecessor_activation_id,
        predecessor_gate_id=meta.predecessor_gate_id,
        inputs=meta.inputs,
    )


def _task_builder(root: RootRecord, wiring: InstanceWiring, git: Git) -> TaskBuilder:
    """Build a real profile task from the activation's immutable bindings."""
    composer = DefaultComposer()

    def build(activation: ActivationRecord, channels: RunnerChannels) -> TaskSpec:
        current = wiring.store.reads.load_activation(activation.activation_id)
        resolved = resolved_node(root, current.metadata.node)
        node = resolved.node
        by_id = {
            item.activation_id: item
            for item in wiring.store.reads.list_activations(root.root_id)
        }
        inputs = tuple(
            materialize(
                git,
                wiring.repo_root,
                root,
                binding,
                None
                if binding.producer_activation_id == "instance"
                else by_id.get(binding.producer_activation_id),
            )
            for binding in current.metadata.inputs
        )
        return TaskSpec(
            root_id=root.root_id,
            activation_id=current.activation_id,
            node=node.name,
            model=current.metadata.model,
            effort=resolved.effort,
            fallback_models=resolved.fallback_models,
            writes=bool(node.writes),
            allowed_paths=node.allowed_paths or (),
            cwd=str(wiring.workspace.path_for(node)),
            channels=channels,
            brief=composer.compose(root, current, inputs),
            token_budget=node.token_budget,
        )

    return build


def run_wrapper(
    composition: Composition,
    root_id: str,
    activation_id: str,
    *,
    wiring: InstanceWiring | None = None,
) -> WrapperExit:
    """Run one wrapper from its durable request and close only mapped failures."""
    validate_bead_id(root_id)
    resolved = composition.for_root(root_id) if wiring is None else wiring
    directory = activation_dir(resolved.paths, activation_id)
    lock = BandLock(directory / WRAPPER_LOCK)
    try:
        lock.acquire()
    except LockUnavailable:
        return WrapperExit.LOCKED
    try:
        activation = resolved.store.reads.load_activation(activation_id)
        if activation.metadata.wf_root_id != root_id:
            raise ValueError("activation does not belong to root")
        if activation.metadata.lifecycle is not Lifecycle.MINTED:
            return WrapperExit.STALE
        root = resolved.store.reads.load_root(root_id)
        request = _request(activation_id, resolved)
        # The EFFECTIVE node: everything downstream of here — the §5.4
        # precondition, workspace isolation, the §8.2 monitor limits — must
        # read the resolution the root pinned, not the graph body alone (§3.1).
        node = resolved_node(root, activation.metadata.node).node
        profile = composition.profiles.profile_for(request.runner_profile)
        deadline = monotonic() + composition.config.band_wait_s
        while True:
            try:
                dispatch = resolved.supervisor.run(
                    request,
                    node,
                    profile,
                    _task_builder(root, resolved, composition.git),
                    pinned_digests=pinned_verifier_digests(root),
                    previous_tree_oid=_previous_tree_oid(resolved, activation),
                )
                break
            except LockUnavailable:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise
                sleep(min(0.05, remaining))
        return (
            WrapperExit.STALE
            if dispatch.dispatch.outcome is LaunchOutcome.ALREADY_DISPATCHED
            else WrapperExit.DONE
        )
    except ForkBarrierAbortError as exc:
        # This is deliberately not in bdio.bounds' retry-exempt set: it closes
        # `error_transport` and consumes the normal §10.2 infra retry.
        return _close_error(
            resolved,
            activation_id,
            Outcome.ERROR_TRANSPORT,
            exc,
            deviations=(
                Deviation(
                    kind=DEVIATION_FORK_BARRIER_ABORT,
                    reason=str(exc),
                    recorded_at="wrapper",
                ),
            ),
        )
    except (
        ForkBarrierError,
        ExecLedgerError,
        TaskRefused,
        UnsupportedOptionError,
    ) as exc:
        return _close_error(resolved, activation_id, Outcome.ERROR_RUNNER, exc)
    except ContinuationRefused as exc:
        return _close_error(
            resolved,
            activation_id,
            Outcome.ERROR_TRANSPORT,
            exc,
            deviations=(
                Deviation(
                    kind=_DEVIATION_CONTINUATION_REFUSED,
                    reason=str(exc),
                    recorded_at="wrapper",
                ),
            ),
        )
    except InputsUnavailable as exc:
        # The wrapper runs in its own process (`DetachedSpawner`), so an input
        # that no longer materializes must become a durable CLOSE here: left to
        # propagate, the child dies with the activation still MINTED and every
        # later tick re-dispatches it. The deviation is what turns the close
        # into a halt gate instead of an infra retry (`frontier._dead_end`).
        return _close_error(
            resolved,
            activation_id,
            Outcome.ERROR_TRANSPORT,
            exc,
            deviations=(
                Deviation(
                    kind=DEVIATION_INPUTS_UNAVAILABLE,
                    reason=str(exc),
                    recorded_at="wrapper",
                ),
            ),
        )
    except SandboxUnavailable as exc:
        # BEFORE the generic `(SupervisorError, OSError)` catch below, which
        # would spend a §10.2 infra retry on it. O1 makes an unbounded dispatch
        # impossible, and a host with no `bwrap` will not grow one on the next
        # tick — so this closes as a dead end that opens a halt gate, exactly
        # the `InputsUnavailable` shape.
        return _close_error(
            resolved,
            activation_id,
            Outcome.ERROR_TRANSPORT,
            exc,
            deviations=(
                Deviation(
                    kind=DEVIATION_SANDBOX_UNAVAILABLE,
                    reason=str(exc),
                    recorded_at="wrapper",
                ),
            ),
        )
    except BandNotHeld as exc:
        return _close_error(resolved, activation_id, Outcome.ERROR_TRANSPORT, exc)
    except PreconditionRefused as exc:
        return _close_error(
            resolved,
            activation_id,
            Outcome.ERROR_TRANSPORT,
            exc,
            deviations=(
                Deviation(
                    kind=DEVIATION_PRECONDITION_REFUSED,
                    reason=_precondition_reason(exc),
                    recorded_at="wrapper",
                ),
            ),
        )
    except (LifecycleConflictError, LossyWriteError):
        refreshed = resolved.store.reads.load_activation(activation_id)
        return (
            WrapperExit.CLOSED_BY_TICK
            if refreshed.metadata.is_settled
            else WrapperExit.FAILED
        )
    except (SupervisorError, OSError) as exc:
        return _close_error(resolved, activation_id, Outcome.ERROR_TRANSPORT, exc)
    finally:
        lock.release()
