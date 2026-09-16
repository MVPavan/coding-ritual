"""Typed vendor-session facts; process identity remains the original dispatch."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from workflow_interpreter.bdio.carriers import ProcessHandle


class SessionRegistration(BaseModel):
    """A correlated vendor thread bound to one protected process launch."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    root_id: str
    activation_id: str
    launch_id: str = Field(min_length=1)
    handle: ProcessHandle
    thread_id: str = Field(min_length=1, max_length=256)
    runner_version: Literal["0.154.0"] = "0.154.0"
    model: str
    effort: str
    policy_digest: str
    state_path: str
