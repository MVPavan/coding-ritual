"""Closed states for experimental host-owned in-place control requests."""

from enum import StrEnum
from typing import Final


class ControlState(StrEnum):
    """Persisted intent spends budget even when delivery remains uncertain."""

    INTENT = "intent"
    SUBMITTING = "submitting"
    ACKNOWLEDGED = "acknowledged"
    UNCERTAIN = "uncertain"
    RESOLVED = "resolved"


MAX_CONTROL_BYTES: Final[int] = 16384
MSG_CONTROL: Final[str] = "app-server control identity or state mismatch"
MSG_CONTROL_BOUND: Final[str] = "app-server in-place steer limit exhausted"
MSG_CONTROL_UNCERTAIN: Final[str] = (
    "in-place steer delivery is uncertain; deliberate operator action required"
)


class ControlResolutionOrigin(StrEnum):
    """Who closed delivery uncertainty without changing the vendor acknowledgment."""

    OPERATOR = "operator"
    SETTLEMENT = "settlement"


DEVIATION_CONTROL_UNCERTAIN: Final[str] = "control_uncertain"
MSG_CONTROL_SETTLED: Final[str] = "activation settled"
MSG_CONTROL_RESOLUTION: Final[str] = "control {sequence}: {reason}"
MSG_CONTROL_ARGUMENTS: Final[str] = "steer requires --instructions-file"
