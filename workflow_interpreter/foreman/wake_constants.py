"""Durable observation vocabulary and bounded host delivery defaults."""

from enum import StrEnum
from typing import Final

REFUSAL_JOURNAL: Final[str] = "refusals.jsonl"
OBSERVATION_STATUS: Final[str] = "observation-status.json"
JOURNAL_LOCK: Final[str] = "refusals.lock"
MONITOR_HANDLE: Final[str] = "monitor.json"
MONITOR_LOCK: Final[str] = "monitor.lock"
WAKE_STATE: Final[str] = "wake-state.json"
MAX_CONDITION_BYTES: Final[int] = 8192
DEFAULT_EVENT_CAP: Final[int] = 100
MAX_EVENT_CAP: Final[int] = 10000
DETAIL_BYTES: Final[int] = 2048
MSG_JOURNAL_BOUND: Final[str] = "refusal journal exceeds its configured bound"
MSG_DURABILITY: Final[str] = "observation durability degraded: {error}"
MSG_IDENTITY: Final[str] = "cannot establish driver/monitor process identity"
LOG_REFUSAL: Final[str] = "wf.gate.refused"
LOG_DURABILITY: Final[str] = "wf.observation.degraded"
LOG_CAP: Final[str] = "wf.wake_cap_exhausted"


class DriverState(StrEnum):
    """Responsive driver lifecycle, independent of model progress."""

    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"


class DriverCondition(StrEnum):
    """Why the last driver observation matters to an operator."""

    STARTING = "starting"
    ACTIVE = "active"
    ATTENTION = "attention"
    GATE = "gate"
    TERMINAL = "terminal"
    STALLED = "stalled"
    STOPPED = "stopped"
    ERROR = "error"
