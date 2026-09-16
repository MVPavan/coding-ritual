"""Typed control accounting; no turn, activation, transition or approval is minted."""

import fcntl
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from workflow_interpreter.bdio import bounds, reads
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.errors import (
    BdioError,
    BoundExceededError,
    CarrierIntegrityError,
)
from workflow_interpreter.bdio.mint import views_of
from workflow_interpreter.bdio.rpc_records import (
    ControlRegistration,
    SessionRegistration,
)
from workflow_interpreter.bdio.wire import (
    BoundSetting,
    Deviation,
    Lifecycle,
    metadata_dict,
)
from workflow_interpreter.contracts.rpc_control import (
    DEVIATION_CONTROL_UNCERTAIN,
    MSG_CONTROL,
    MSG_CONTROL_RESOLUTION,
    MSG_CONTROL_SETTLED,
    ControlResolutionOrigin,
    ControlState,
)


class ControlBusy(BdioError):
    """Another host writer holds the control list; retry without blocking RPC."""


@contextmanager
def _guard(registration: SessionRegistration) -> Iterator[None]:
    """Serialize only control metadata in the launcher's protected log directory."""
    directory = Path(registration.handle.log_path).parent
    if not directory.is_absolute() or directory.resolve() != directory:
        raise CarrierIntegrityError(MSG_CONTROL)
    directory.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        directory / "rpc-control.lock", os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW, 0o600
    )
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ControlBusy("app-server control metadata is busy") from error
        yield
    finally:
        os.close(descriptor)


def _reserve(
    client: BdClient,
    reader: reads.WorkflowReads,
    activation_id: str,
    registration: SessionRegistration,
    turn_id: str,
    digest: str,
) -> ControlRegistration:
    """Under the caller's band, reserve budget before publishing an inbox request."""
    activation = reader.load_activation(activation_id)
    meta = activation.metadata
    if (
        meta.session_registration != registration
        or meta.is_settled
        or meta.lifecycle is not Lifecycle.DISPATCHED
    ):
        raise CarrierIntegrityError(MSG_CONTROL)
    root = reader.load_root(meta.wf_root_id)
    beads = reader.instance_beads(root.root_id)
    limit = bounds.effective_bound(
        root, reads.gates_of(beads), BoundSetting.MAX_STEERS, meta.node
    )
    used = bounds.steer_closes(
        views_of(reads.activations_of(beads)), meta.node, meta.round_no
    )
    refusal = (
        None
        if limit is None
        else bounds.steer_refusal(
            node=meta.node, round_no=meta.round_no, steer_closes=used, max_steers=limit
        )
    )
    if refusal is not None:
        raise BoundExceededError(refusal)
    control = ControlRegistration(
        registration=registration,
        sequence=len(meta.in_place_controls) + 1,
        turn_id=turn_id,
        instructions_digest=digest,
    )
    client._merge_metadata(
        activation_id,
        {
            "in_place_controls": [
                metadata_dict(item) for item in (*meta.in_place_controls, control)
            ]
        },
    )
    return control


def _record_state(
    client: BdClient,
    reader: reads.WorkflowReads,
    activation_id: str,
    control: ControlRegistration,
    state: ControlState,
    resolution_reason: str | None = None,
) -> ControlRegistration:
    """Update only this request; ambiguous controls can never be replayed or acked."""
    activation = reader.load_activation(activation_id)
    controls = activation.metadata.in_place_controls
    if not 1 <= control.sequence <= len(controls):
        raise CarrierIntegrityError(MSG_CONTROL)
    current = controls[control.sequence - 1]
    if current.model_copy(update={"state": control.state}) != control:
        raise CarrierIntegrityError(MSG_CONTROL)
    if current.state is state:
        return current
    allowed = {
        ControlState.INTENT: {ControlState.SUBMITTING, ControlState.UNCERTAIN},
        ControlState.SUBMITTING: {ControlState.ACKNOWLEDGED, ControlState.UNCERTAIN},
        ControlState.UNCERTAIN: {ControlState.RESOLVED},
    }
    if state not in allowed.get(current.state, set()):
        raise CarrierIntegrityError(MSG_CONTROL)
    deviations = activation.metadata.deviations
    if state is ControlState.RESOLVED:
        if not activation.metadata.is_settled and not resolution_reason:
            raise CarrierIntegrityError(MSG_CONTROL)
        if resolution_reason is not None and len(resolution_reason) > 512:
            raise CarrierIntegrityError(MSG_CONTROL)
        deviations = (
            *deviations,
            Deviation(
                kind=DEVIATION_CONTROL_UNCERTAIN,
                reason=MSG_CONTROL_RESOLUTION.format(
                    sequence=control.sequence,
                    reason=resolution_reason or MSG_CONTROL_SETTLED,
                ),
                recorded_at=(
                    ControlResolutionOrigin.OPERATOR
                    if resolution_reason
                    else ControlResolutionOrigin.SETTLEMENT
                ),
                instructions_digest=control.instructions_digest,
            ),
        )
    updated = current.model_copy(update={"state": state})
    client._merge_metadata(
        activation_id,
        {
            "in_place_controls": [
                metadata_dict(updated if item.sequence == control.sequence else item)
                for item in controls
            ],
            **(
                {"deviations": [metadata_dict(d) for d in deviations]}
                if state is ControlState.RESOLVED
                else {}
            ),
        },
    )
    return updated


def reserve(
    client: BdClient,
    reader: reads.WorkflowReads,
    activation_id: str,
    registration: SessionRegistration,
    turn_id: str,
    digest: str,
) -> ControlRegistration:
    """Reserve atomically against delivery updates; a busy lock spends no intent."""
    activation = reader.load_activation(activation_id)
    if activation.metadata.session_registration != registration:
        raise CarrierIntegrityError(MSG_CONTROL)
    with _guard(registration):
        return _reserve(client, reader, activation_id, registration, turn_id, digest)


def record_state(
    client: BdClient,
    reader: reads.WorkflowReads,
    activation_id: str,
    control: ControlRegistration,
    state: ControlState,
    resolution_reason: str | None = None,
) -> ControlRegistration:
    """Update atomically against new reservations; callers may defer a busy write."""
    activation = reader.load_activation(activation_id)
    if activation.metadata.session_registration != control.registration:
        raise CarrierIntegrityError(MSG_CONTROL)
    with _guard(control.registration):
        return _record_state(
            client, reader, activation_id, control, state, resolution_reason
        )
