"""Versioned notification data carries no transition, approval or budget authority."""

from enum import StrEnum
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CANON_WAKE: Final = "wf-wake-event/1"
MAX_WAKE_BYTES: Final[int] = 8192
MSG_WAKE_BOUND: Final[str] = "wake event exceeds its 8 KiB bound"


class WakeCondition(StrEnum):
    """The complete set of model-free wake triggers in this engine version."""

    GATE_OPENED = "gate_opened"
    ROOT_TERMINAL = "root_terminal"
    REFUSAL = "refusal"
    DRIVER_EXIT = "driver_exit"
    HEARTBEAT_STALE = "heartbeat_stale"


class WakeCursor(BaseModel):
    """A stable condition identity, independent of repeated polls or file mtimes."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    identity: str = Field(min_length=1, max_length=2048)


class WakeEvent(BaseModel):
    """A durable observational event, explicitly distinct from transition payloads."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    canon: Literal["wf-wake-event/1"] = CANON_WAKE
    root_id: str = Field(min_length=1, max_length=256)
    instance_key: str = Field(min_length=1, max_length=1024)
    condition: WakeCondition
    cursor: WakeCursor
    fire_key: str = Field(pattern=r"^[a-f0-9]{64}$")
    observed_at: str
    fired_at: str | None = None
    detail: str = Field(default="", max_length=2048)

    @model_validator(mode="after")
    def _bounded_payload(self) -> "WakeEvent":
        """Bound the serialized data, including escaping and multibyte text."""
        if len(self.model_dump_json().encode()) > MAX_WAKE_BYTES:
            raise ValueError(MSG_WAKE_BOUND)
        return self
