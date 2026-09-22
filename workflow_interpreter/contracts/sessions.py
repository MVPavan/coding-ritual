"""Graph-owned choice of intentional vendor history reuse."""

import hashlib
from enum import StrEnum
from typing import Final


class SessionReuse(StrEnum):
    """Fresh is the default; same-node never crosses role or root boundaries."""

    FRESH = "fresh"
    SAME_NODE = "same-node"


class SessionMode(StrEnum):
    """Whether an activation starts a vendor session or resumes its own history."""

    FRESH = "fresh"
    RESUME = "resume"


MSG_SESSION_REUSE: Final[str] = "session_reuse requires the codex app-server crew"
MSG_SESSION_MODE_CONFLICT: Final[str] = (
    "session_mode and legacy session_reuse cannot both be set"
)
MSG_SESSION_SOURCE: Final[str] = "session source is absent or incompatible"
SESSION_MODE_KEY: Final[str] = "node.{node}.session_mode"


def session_mode_key(node: str) -> str:
    """Name the immutable resolved-session setting for one task node."""
    return SESSION_MODE_KEY.format(node=node)


def execution_policy_digest(pinned_policy: str) -> str:
    """Hash the root-pinned policy representation; the full policy stays on the root."""
    return hashlib.sha256(pinned_policy.encode("utf-8")).hexdigest()


class SessionFreshReason(StrEnum):
    """Durable reason for starting over instead of resuming a deliberate source."""

    VERSION_MISMATCH = "version_mismatch"
