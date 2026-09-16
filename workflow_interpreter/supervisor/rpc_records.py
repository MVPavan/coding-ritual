"""Protected one-turn RPC evidence, separate from runner-writable channels."""

from enum import StrEnum
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from workflow_interpreter.bdio.rpc_records import SessionRegistration
from workflow_interpreter.contracts.transport import RunnerTransport
from workflow_interpreter.supervisor.errors import WrapperDirError
from workflow_interpreter.supervisor.launch_record import LaunchReceipt
from workflow_interpreter.supervisor.paths import read_record

SESSION_FILE: Final[str] = "session.json"
TURN_FILE: Final[str] = "turn.json"
VENDOR_STATE: Final[str] = "vendor-state"
MSG_RPC_INCOMPLETE: Final[str] = "app-server turn completion is absent or invalid"


class TurnPhase(StrEnum):
    """Submission is ambiguous until acknowledged; completion is explicit."""

    INTENT = "intent"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class TurnRecord(BaseModel):
    """Written before turn/start and never used to authorize a resend."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    registration: SessionRegistration | None = None
    phase: TurnPhase
    turn_id: str | None = None
    error: str | None = None

    @model_validator(mode="after")
    def coherent(self) -> "TurnRecord":
        """Only a failed handshake can omit registration and acknowledged identity."""
        if self.phase is not TurnPhase.FAILED and self.registration is None:
            raise ValueError(MSG_RPC_INCOMPLETE)
        if self.phase in (TurnPhase.ACTIVE, TurnPhase.COMPLETED) and not self.turn_id:
            raise ValueError(MSG_RPC_INCOMPLETE)
        return self


class InitializeReply(BaseModel):
    """Pinned initialization identity, before any thread is opened."""

    model_config = ConfigDict(frozen=True, extra="ignore", strict=True)
    userAgent: str
    codexHome: str
    platformFamily: str
    platformOs: str


class ThreadSandbox(BaseModel):
    """The effective server sandbox must preserve the submitted network fact."""

    model_config = ConfigDict(frozen=True, extra="ignore", strict=True)
    type: Literal["workspaceWrite"]
    writableRoots: list[str]
    networkAccess: Literal[False]
    excludeSlashTmp: Literal[True]
    excludeTmpdirEnvVar: bool


class VendorThread(BaseModel):
    """Only identity is consumed from the larger pinned vendor thread object."""

    model_config = ConfigDict(frozen=True, extra="ignore", strict=True)
    id: str = Field(min_length=1, max_length=256)


class ThreadReply(BaseModel):
    """Correlated identity response; protocol fields outside this subset are inert."""

    model_config = ConfigDict(frozen=True, extra="ignore", strict=True)
    thread: VendorThread
    model: str
    modelProvider: str
    cwd: str
    approvalPolicy: Literal["never"]
    approvalsReviewer: Literal["user"]
    sandbox: ThreadSandbox


class VendorTurn(BaseModel):
    """Closed terminal status vocabulary from the 0.154.0 schema."""

    model_config = ConfigDict(frozen=True, extra="ignore", strict=True)
    id: str = Field(min_length=1, max_length=256)
    status: Literal["inProgress", "completed", "failed", "interrupted"]


class TurnReply(BaseModel):
    """An acknowledged turn start identifies the only turn this wrapper owns."""

    model_config = ConfigDict(frozen=True, extra="ignore", strict=True)
    turn: VendorTurn


class TurnCompleted(TurnReply):
    """Completion is correlated to both the registered thread and acknowledged turn."""

    threadId: str


def completion_error(receipt: LaunchReceipt | None, directory: Path) -> str | None:
    """A server exit or forged log cannot replace protected completion evidence."""
    if receipt is None or receipt.transport is not RunnerTransport.STDIO_RPC:
        return None
    try:
        session = read_record(directory / SESSION_FILE, SessionRegistration)
        turn = read_record(directory / TURN_FILE, TurnRecord)
    except (WrapperDirError, OSError):
        return MSG_RPC_INCOMPLETE
    if (
        session is None
        or turn is None
        or turn.registration != session
        or session.handle != receipt.handle
        or session.launch_id != receipt.launch_id
        or session.activation_id != receipt.activation_id
        or session.root_id != receipt.root_id
        or turn.phase is not TurnPhase.COMPLETED
        or not turn.turn_id
        or turn.error
    ):
        return turn.error if turn and turn.error else MSG_RPC_INCOMPLETE
    return None
