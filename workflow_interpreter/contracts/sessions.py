"""Graph-owned choice of intentional vendor history reuse."""

import hashlib
from enum import StrEnum
from typing import Final


class SessionReuse(StrEnum):
    """Fresh is the default; same-node never crosses role or root boundaries."""

    FRESH = "fresh"
    SAME_NODE = "same-node"


MSG_SESSION_REUSE: Final[str] = "session_reuse requires the codex app-server runner"
MSG_SESSION_SOURCE: Final[str] = "app-server session source is absent or incompatible"


def execution_policy_digest(pinned_policy: str) -> str:
    """Hash the root-pinned policy representation; the full policy stays on the root."""
    return hashlib.sha256(pinned_policy.encode("utf-8")).hexdigest()


class SessionFreshReason(StrEnum):
    """Durable reason for starting over instead of resuming a deliberate source."""

    VERSION_MISMATCH = "version_mismatch"
