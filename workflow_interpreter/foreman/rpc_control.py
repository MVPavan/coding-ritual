"""Reconcile durable control evidence and surface ambiguity through slice-3 wake."""

from pydantic import ValidationError

from workflow_interpreter.bdio import ActivationRecord, WorkflowStore
from workflow_interpreter.bdio.rpc_control import ControlBusy
from workflow_interpreter.bdio.rpc_records import ControlRegistration
from workflow_interpreter.contracts.rpc_control import (
    MSG_CONTROL_UNCERTAIN,
    ControlState,
)
from workflow_interpreter.contracts.rpc_usage import UsageSnapshot
from workflow_interpreter.foreman.observation import read_status, save_status
from workflow_interpreter.foreman.refusals import append_refusal
from workflow_interpreter.foreman.wake_constants import DEFAULT_EVENT_CAP
from workflow_interpreter.profiles.codex_rpc import RpcFailure
from workflow_interpreter.schema.models import Outcome
from workflow_interpreter.supervisor.errors import WrapperDirError
from workflow_interpreter.supervisor.launch_record import LaunchReceipt
from workflow_interpreter.supervisor.models import Liveness
from workflow_interpreter.supervisor.paths import WrapperPaths, read_record
from workflow_interpreter.supervisor.procfs import prove_liveness
from workflow_interpreter.supervisor.rpc_control import control_path, next_intent
from workflow_interpreter.supervisor.rpc_usage import USAGE_FILE


def _reconcile_control(
    paths: WrapperPaths,
    store: WorkflowStore,
    activation: ActivationRecord,
    control: ControlRegistration,
    *,
    lost: bool,
) -> ControlRegistration:
    """Recover each ack or lost intent, including earlier requests in the queue."""
    if control.state is ControlState.ACKNOWLEDGED:
        return control
    try:
        intent = next_intent(
            paths.activation_dir(activation.activation_id), control.sequence
        )
    except (OSError, ValidationError, RpcFailure):
        intent = None
    target = None
    if (
        intent is not None
        and intent.control.state is ControlState.ACKNOWLEDGED
        and intent.control.model_copy(update={"state": control.state}) == control
        and control.state is ControlState.SUBMITTING
    ):
        target = ControlState.ACKNOWLEDGED
    elif lost and control.state is not ControlState.UNCERTAIN:
        target = ControlState.UNCERTAIN
    if target is None:
        return control
    try:
        return store.record_control_state(activation.activation_id, control, target)
    except ControlBusy:
        # The file/death proof is evidence already. Retry its bd mirror next tick.
        return control.model_copy(update={"state": target})


def control_attention(
    paths: WrapperPaths,
    store: WorkflowStore,
    *,
    refusal_limit: int = DEFAULT_EVENT_CAP,
) -> tuple[str, ...]:
    """Never resend. Recover protected acks; uncertain intent requires an operator."""
    attention: list[str] = []
    for activation in store.reads.list_activations(paths.root_id):
        meta = activation.metadata
        if not meta.in_place_controls:
            continue
        try:
            receipt = read_record(
                paths.receipt(activation.activation_id), LaunchReceipt
            )
        except (OSError, WrapperDirError):
            receipt = None
        lost = meta.is_settled or (
            receipt is not None
            and receipt.owner is not None
            and prove_liveness(paths.config, receipt.owner).status
            in (Liveness.DEAD, Liveness.IDENTITY_MISMATCH)
        )
        controls = tuple(
            _reconcile_control(paths, store, activation, control, lost=lost)
            for control in meta.in_place_controls
        )
        if meta.outcome is Outcome.STEERED:
            continue
        for control in controls:
            if control.state is not ControlState.UNCERTAIN:
                continue
            key = f"{activation.activation_id}:control:{control.sequence}"
            try:
                append_refusal(
                    paths.instance_dir,
                    gate_id=activation.activation_id,
                    gate_key=key,
                    payload=control.model_dump_json().encode(),
                    signature=b"",
                    error="control_uncertain",
                    reason=MSG_CONTROL_UNCERTAIN,
                    path=control_path(
                        paths.activation_dir(activation.activation_id), control.sequence
                    ),
                    limit=refusal_limit,
                )
            except (OSError, ValueError) as error:
                save_status(
                    paths.instance_dir,
                    read_status(paths.instance_dir).degraded(error=str(error)),
                )
            if control.sequence == controls[-1].sequence:
                attention.append(key)
    return tuple(attention)


def session_status(
    paths: WrapperPaths, activations: tuple[ActivationRecord, ...]
) -> dict[str, object]:
    """Expose registered identity and separate accounting without reading transcripts."""
    result: dict[str, object] = {}
    for activation in activations:
        meta = activation.metadata
        if meta.session_registration is None:
            continue
        try:
            usage = read_record(
                paths.activation_dir(activation.activation_id) / USAGE_FILE,
                UsageSnapshot,
            )
        except (OSError, WrapperDirError):
            usage = None
        result[activation.activation_id] = {
            "thread_id": meta.session_registration.thread_id,
            "source_activation": meta.session_reuse_source.activation_id
            if meta.session_reuse_source
            else None,
            "usage": usage.model_dump(mode="json") if usage else None,
            "controls": [
                {"sequence": control.sequence, "state": control.state.value}
                for control in meta.in_place_controls
            ],
        }
    return result
