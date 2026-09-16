"""Closed states for experimental host-owned in-place control requests."""

from enum import StrEnum
from typing import Final


class ControlState(StrEnum):
    """Persisted intent spends budget even when delivery remains uncertain."""

    INTENT = "intent"
    SUBMITTING = "submitting"
    ACKNOWLEDGED = "acknowledged"
    UNCERTAIN = "uncertain"


MAX_CONTROL_BYTES: Final[int] = 16384
MSG_CONTROL: Final[str] = "app-server control identity or state mismatch"
MSG_CONTROL_BOUND: Final[str] = "app-server in-place steer limit exhausted"
MSG_CONTROL_UNCERTAIN: Final[str] = (
    "in-place steer delivery is uncertain; deliberate operator action required"
)
