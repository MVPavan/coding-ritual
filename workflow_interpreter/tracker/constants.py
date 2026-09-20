"""The tracker port's fixed vocabulary, named once (store-restructure §3.3).

Every set a caller branches on is an enum here rather than a string at the
branch: the port exists so that bd, GitHub, Jira, a file and nothing at all are
one surface, and a surface whose values are spelled at each call site is one
that drifts per adapter.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class TrackerCapability(StrEnum):
    """What one tracker can actually do (§3.3).

    Declared by the adapter rather than discovered by failing: `NullTracker`
    declares none and every run still completes, and a missing `BLOCKERS` is
    recorded as an unchecked question rather than guessed at (R9).
    """

    CHILDREN = "children"
    BLOCKERS = "blockers"
    CLAIM = "claim"
    CLOSE = "close"
    ANNOTATE = "annotate"
    FLAG = "flag"


class IntentKind(StrEnum):
    """The closed union of desired states a caller may ask a tracker for."""

    CLAIM = "claim"
    CLOSE = "close"
    SET_FLAG = "set_flag"
    ANNOTATE = "annotate"


class ResultKind(StrEnum):
    """How a tracker answered one intent (§3.3).

    `UNKNOWN` is the only one that goes to the outbox: `APPLIED` is done and
    `CONFLICT` is the tracker disagreeing, which is a decision for the caller
    and never a retry.
    """

    APPLIED = "applied"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"


class WorkItemStatus(StrEnum):
    """The three states every tracker in scope can express."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class TrackerFlag(StrEnum):
    """The flags the engine sets on a work item, and their spellings.

    One member today. It is `wf:attention` and never bd's own `human` flag,
    whose dismissal CLOSES the issue — a projection may not decide a task is
    over (run-ledger §3.2)."""

    ATTENTION = "wf:attention"


DEFAULT_CAPABILITIES: Final[frozenset[TrackerCapability]] = frozenset(TrackerCapability)
"""What a tracker that can do everything declares. `FileTracker`'s default, and
the set the bd adapter subtracts from."""

MSG_UNKNOWN_CLAIM: Final[str] = (
    "tracker did not answer the claim on {ref!r}: {reason}. Ambiguity refuses "
    "admission — a task whose tracker may or may not hold it for this actor is "
    "not one a second session can be told about (store-restructure §3.4, R3)"
)
MSG_CONFLICT_CLAIM: Final[str] = (
    "tracker refused the claim on {ref!r}: {reason}. The tracker disagrees "
    "about who holds this task, and admission never overrules it (§3.4)"
)
MSG_CLOSED_ELSEWHERE: Final[str] = (
    "task {ref!r} was closed in its tracker while this run held it, so the "
    "record is retired as abandoned-external rather than admitted: a task "
    "somebody else ended is observed, never guessed at (§3.8)"
)
MSG_BLOCKERS_UNAVAILABLE: Final[str] = (
    "tracker {kind!r} declares no BLOCKERS capability and this tracker is "
    "configured to require one: without it the record would say "
    "blockers_checked=false and proceed (store-restructure R9)"
)
MSG_BRIEF_REQUIRED: Final[str] = (
    "tracker {kind!r} holds no work item for {ref!r}, so the task brief has to "
    "be supplied: pass --brief <file> (store-restructure §3.3)"
)
MSG_FILE_UNREADABLE: Final[str] = (
    "tracker file {path} is not a tracker document: {reason}"
)
