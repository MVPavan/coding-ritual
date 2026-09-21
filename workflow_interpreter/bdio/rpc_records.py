"""Typed vendor-session facts; process identity remains the original dispatch."""

from pydantic import BaseModel, ConfigDict, Field

from workflow_interpreter.bdio.carriers import ProcessHandle
from workflow_interpreter.contracts.codex import CODEX_VERSION
from workflow_interpreter.contracts.rpc_control import ControlState
from workflow_interpreter.contracts.rpc_usage import UsageSnapshot


class SessionRegistration(BaseModel):
    """A correlated vendor thread bound to one protected process launch."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    root_id: str
    activation_id: str
    launch_id: str = Field(min_length=1)
    handle: ProcessHandle
    thread_id: str = Field(min_length=1, max_length=256)
    crew_version: str = CODEX_VERSION
    model: str
    effort: str
    policy_digest: str
    state_path: str


class SessionCompletion(BaseModel):
    """Successful vendor turn, eligible for reuse only after activation settlement."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    registration: SessionRegistration
    turn_id: str = Field(min_length=1, max_length=256)
    usage: UsageSnapshot = UsageSnapshot()


class ControlRegistration(BaseModel):
    """Intent identity and accounting, without model instructions in bd."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    registration: SessionRegistration
    sequence: int = Field(ge=1)
    turn_id: str = Field(min_length=1, max_length=256)
    instructions_digest: str = Field(min_length=1, max_length=256)
    state: ControlState = ControlState.INTENT
