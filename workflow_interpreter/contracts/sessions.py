"""Graph-owned choice of intentional vendor history reuse."""

from enum import StrEnum
from typing import Final


class SessionReuse(StrEnum):
    """Fresh is the default; same-node never crosses role or root boundaries."""

    FRESH = "fresh"
    SAME_NODE = "same-node"


MSG_SESSION_REUSE: Final[str] = "session_reuse requires the codex app-server runner"
MSG_SESSION_SOURCE: Final[str] = "app-server session source is absent or incompatible"
