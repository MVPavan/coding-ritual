"""Bounded host inbox: persist intent before delivery and never replay ambiguity."""

import hashlib
import time
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, model_validator

from workflow_interpreter.bdio import ActivationRecord, WorkflowStore
from workflow_interpreter.bdio.rpc_records import ControlRegistration
from workflow_interpreter.contracts.rpc_control import (
    MAX_CONTROL_BYTES,
    MSG_CONTROL,
)
from workflow_interpreter.profiles.codex_rpc import RpcClient, RpcFailure, RpcMethod
from workflow_interpreter.supervisor.errors import ContinuationRefused, WrapperDirError
from workflow_interpreter.supervisor.launch_record import LaunchReceipt
from workflow_interpreter.supervisor.models import Liveness
from workflow_interpreter.supervisor.paths import (
    WrapperPaths,
    read_record,
    write_record,
)
from workflow_interpreter.supervisor.procfs import prove_liveness
from workflow_interpreter.supervisor.rpc_records import TURN_FILE, TurnPhase, TurnRecord

CONTROL_PREFIX: Final[str] = "control-"
INTERRUPT_FILE: Final[str] = "interrupt.json"
COURTESY_SECONDS: Final[float] = 0.1
MAX_INBOX_BYTES: Final[int] = MAX_CONTROL_BYTES * 6 + 8192


class ControlIntent(BaseModel):
    """Model instructions remain outside bd and runner-writable channels."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    control: ControlRegistration
    instructions: str
    reason: str = Field(max_length=512)

    @model_validator(mode="after")
    def bounded_text(self) -> "ControlIntent":
        """Reject oversized or altered instructions before any protocol submission."""
        raw = self.instructions.encode()
        if not raw or len(raw) > MAX_CONTROL_BYTES:
            raise ValueError(MSG_CONTROL)
        if hashlib.sha256(raw).hexdigest() != self.control.instructions_digest:
            raise ValueError(MSG_CONTROL)
        return self


def control_path(directory: Path, sequence: int) -> Path:
    """One bounded request file per accounted control sequence."""
    return directory / f"{CONTROL_PREFIX}{sequence}.json"


def enqueue(
    paths: WrapperPaths,
    store: WorkflowStore,
    activation: ActivationRecord,
    *,
    reason: str,
    instructions: str,
) -> ControlRegistration:
    """Under the caller's execution band, account intent before inbox publication."""
    raw = instructions.encode()
    if not raw or len(raw) > MAX_CONTROL_BYTES or len(reason) > 512:
        raise ContinuationRefused(MSG_CONTROL)
    aid = activation.activation_id
    try:
        turn = read_record(paths.activation_dir(aid) / TURN_FILE, TurnRecord)
        receipt = read_record(paths.receipt(aid), LaunchReceipt)
    except (OSError, WrapperDirError) as error:
        raise ContinuationRefused(MSG_CONTROL) from error
    registration = activation.metadata.session_registration
    if (
        registration is None
        or turn is None
        or receipt is None
        or receipt.owner is None
        or turn.phase is not TurnPhase.ACTIVE
        or turn.registration != registration
        or not turn.turn_id
        or receipt.handle != registration.handle
        or receipt.launch_id != registration.launch_id
        or prove_liveness(paths.config, receipt.handle).status is not Liveness.ALIVE
        or prove_liveness(paths.config, receipt.owner).status is not Liveness.ALIVE
    ):
        raise ContinuationRefused(MSG_CONTROL)
    control = store.reserve_in_place_steer(
        aid, registration, turn.turn_id, hashlib.sha256(raw).hexdigest()
    )
    write_record(
        control_path(paths.activation_dir(aid), control.sequence),
        ControlIntent(control=control, instructions=instructions, reason=reason),
    )
    return control


def next_intent(directory: Path, sequence: int) -> ControlIntent | None:
    """Read exactly the next bounded file; no directory scan or unbounded queue."""
    path = control_path(directory, sequence)
    try:
        with path.open("rb") as stream:
            data = stream.read(MAX_INBOX_BYTES + 1)
    except FileNotFoundError:
        return None
    if len(data) > MAX_INBOX_BYTES:
        raise RpcFailure(MSG_CONTROL)
    return ControlIntent.model_validate_json(data)


def interrupt(client: RpcClient, turn: TurnRecord | None) -> None:
    """Courtesy only; a response never replaces group death proof or adds timeouts."""
    if client.pending or turn is None or turn.registration is None or not turn.turn_id:
        return
    try:
        client.request(
            RpcMethod.TURN_INTERRUPT,
            {"threadId": turn.registration.thread_id, "turnId": turn.turn_id},
        )
        deadline = time.monotonic() + COURTESY_SECONDS
        while client.pending and time.monotonic() < deadline:
            client.poll(min(0.01, max(0, deadline - time.monotonic())))
    except (RpcFailure, OSError):
        return


def request_interrupt(paths: WrapperPaths, activation: ActivationRecord) -> None:
    """Tell the resident wrapper to interrupt before the ordinary termination path."""
    if activation.metadata.session_registration is None:
        return
    try:
        write_record(
            paths.activation_dir(activation.activation_id) / INTERRUPT_FILE,
            activation.metadata.session_registration,
        )
    except OSError:
        return
    time.sleep(COURTESY_SECONDS)


def read_instructions(path: Path) -> str:
    """Bound host input before decoding; CLI files cannot allocate an unbounded body."""
    with path.open("rb") as stream:
        raw = stream.read(MAX_CONTROL_BYTES + 1)
    if not raw or len(raw) > MAX_CONTROL_BYTES:
        raise ContinuationRefused(MSG_CONTROL)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ContinuationRefused(MSG_CONTROL) from error
