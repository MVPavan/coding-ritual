"""Graph-owned choice of intentional vendor history reuse."""

import hashlib
from enum import StrEnum
from typing import Final

from workflow_interpreter.contracts.execution import ExecutionPolicy


class SessionReuse(StrEnum):
    """Fresh is the default; same-node never crosses role or root boundaries."""

    FRESH = "fresh"
    SAME_NODE = "same-node"


class SessionMode(StrEnum):
    """Whether an activation starts a vendor session or resumes its own history."""

    FRESH = "fresh"
    RESUME = "resume"


MSG_SESSION_REUSE: Final[str] = "session_reuse requires the codex app-server crew"
MSG_SESSION_REUSE_AUTHORED: Final[str] = (
    "session_reuse is pinned-body compatibility only; "
    "author session_mode instead (fresh | resume)"
)
MSG_SESSION_MODE_CONFLICT: Final[str] = (
    "session_mode and legacy session_reuse cannot both be set"
)
MSG_SESSION_SOURCE: Final[str] = "session source is absent or incompatible"
SESSION_MODE_KEY: Final[str] = "node.{node}.session_mode"


def session_mode_key(node: str) -> str:
    """Name the immutable resolved-session setting for one task node."""
    return SESSION_MODE_KEY.format(node=node)


CONTEXT_CAP_KEY: Final[str] = "node.{node}.context_cap_tokens"
"""Role-binding-only pin: deliberately outside `NodeSetting`, which is the
project/override vocabulary, because the cap has no node or config override."""


def context_cap_key(node: str) -> str:
    """Name the pinned claude context-cap setting for one task node."""
    return CONTEXT_CAP_KEY.format(node=node)


def execution_policy_digest(pinned_policy: str) -> str:
    """Hash the canonical policy representation pinned by an activation."""
    return hashlib.sha256(pinned_policy.encode("utf-8")).hexdigest()


LEGACY_POLICY_REPRESENTATION: Final[str] = "legacy"


def activation_policy_digest(policy: ExecutionPolicy | None) -> str:
    """Use one digest rule for minted, selected, and observed activations."""
    representation = (
        LEGACY_POLICY_REPRESENTATION if policy is None else policy.model_dump_json()
    )
    return execution_policy_digest(representation)


class SessionFreshReason(StrEnum):
    """Durable reason for starting over instead of resuming a deliberate source.

    Every fresh launch of a RESUME-pinned node carries one: without it the
    record of a lost thread reads exactly like a legitimate first turn.
    """

    VERSION_MISMATCH = "version_mismatch"
    """The app-server's pinned protocol version no longer matches the source."""
    NO_SOURCE = "no_source"
    """No same-node candidate matched the pinned authority (often turn one)."""
    UNREGISTERED_SOURCE = "unregistered_source"
    """A candidate matched, but no vendor identity was ever observed for it."""
    VERSION_DRIFT = "version_drift"
    """A candidate matched, but ran under a different CLI than this process."""
    MODEL_CHANGED = "model_changed"
    """The newest candidate used another profile, model, or effort."""
    UNQUALIFIED_SOURCE = "unqualified_source"
    """A candidate matched, but registered no CLI version to compare (§6)."""
