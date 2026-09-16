"""Durable notification outbox and bounded, at-least-once trusted host hook."""

import os
import signal
import subprocess
from collections.abc import Mapping
from enum import StrEnum
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from workflow_interpreter.bdio import ProcessHandle
from workflow_interpreter.contracts.wake import MAX_WAKE_BYTES, WakeEvent
from workflow_interpreter.foreman.config import WakeConfig
from workflow_interpreter.foreman.wake_constants import MAX_EVENT_CAP

HOOK_ATTEMPTS: Final[int] = 3
MSG_HOOK_FAILED: Final[str] = "wake hook failed: {error}"
MSG_HOOK_TIMEOUT: Final[str] = "wake hook timed out"
MSG_HOOK_EXIT: Final[str] = "wake hook exited {code}"
MSG_MONITOR_REQUIRED: Final[str] = (
    "healthy monitor required; start foreman monitor {root_id}"
)
MSG_MONITOR_CAPACITY: Final[str] = (
    "monitor recovery exceeds capacity of {limit} records"
)
MSG_MONITOR_IDENTITY: Final[str] = "monitor state belongs to a different instance"
MSG_MONITOR_LOCK: Final[str] = "monitor must hold its instance lock before polling"
LOG_MONITOR_ERROR: Final[str] = "wf.monitor.error"
LOG_MONITOR_READY: Final[str] = "wf.monitor.ready"


class HookError(Exception):
    """A bounded host hook attempt failed; its durable event remains valid."""


class MonitorUnavailable(Exception):
    """Explicit monitored execution requires a live, acknowledged monitor."""


class MonitorState(StrEnum):
    """Only a lock-owning ready monitor may acknowledge monitored startup."""

    READY = "ready"
    STOPPED = "stopped"


class MonitorHealth(StrEnum):
    """Local identity and responsiveness proof, not a remote lease."""

    MISSING = "missing"
    HEALTHY = "healthy"
    STALE = "stale"
    STOPPED = "stopped"
    LOST = "lost"
    INDETERMINATE = "indeterminate"


class MonitorHandle(BaseModel):
    """Protected startup acknowledgment and monitor process identity."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    root_id: str
    instance_key: str
    handle: ProcessHandle | None = None
    timestamp: str
    state: MonitorState


class WakeDelivery(BaseModel):
    """Intent precedes the bd write; hook attempt intent precedes its side effect."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    event: WakeEvent
    event_id: str | None = None
    attempts: int = Field(default=0, ge=0, le=HOOK_ATTEMPTS)
    acknowledged: bool = False
    next_attempt_at: str | None = None
    error: str | None = None


class WakeState(BaseModel):
    """Bounded durable cursor and delivery state, preserved across monitor restarts."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal[1] = 1
    root_id: str
    instance_key: str
    journal_device: int | None = None
    journal_inode: int | None = None
    journal_offset: int = Field(default=0, ge=0)
    journal_generation: int = Field(default=0, ge=0)
    deliveries: tuple[WakeDelivery, ...] = Field(default=(), max_length=MAX_EVENT_CAP)
    last_fire_at: str | None = None
    last_error: str | None = None
    monitor_degraded: str | None = None
    saturated: bool = False
    cap_exhausted: bool = False


def run_hook(event: WakeEvent, config: WakeConfig, host_env: Mapping[str, str]) -> None:
    """Send compact JSON to configured argv; discard output and bound the process group."""
    if not config.hook_argv:
        return
    payload = event.model_dump_json().encode()
    if len(payload) > MAX_WAKE_BYTES:
        raise HookError(MSG_HOOK_FAILED.format(error="payload exceeds limit"))
    try:
        process = subprocess.Popen(
            config.hook_argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=dict(host_env),
            start_new_session=True,
            shell=False,
        )
        try:
            process.communicate(payload, timeout=config.hook_timeout_s)
        except subprocess.TimeoutExpired as error:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=1)
            raise HookError(MSG_HOOK_TIMEOUT) from error
        finally:
            if process.stdin is not None:
                process.stdin.close()
        if process.returncode:
            raise HookError(MSG_HOOK_EXIT.format(code=process.returncode))
    except (OSError, subprocess.SubprocessError) as error:
        raise HookError(MSG_HOOK_FAILED.format(error=error)) from error
