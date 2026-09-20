"""The two failures a tracker READ can have (§3.3).

Writes never raise — they answer `Applied`, `Conflict` or `Unknown`, because a
write that raised would put the decision about a landed commit in an exception
handler. Reads raise, because a read has no desired state to fall back on.
"""

from __future__ import annotations


class TrackerUnavailable(RuntimeError):
    """The tracker could not be reached. Retryable."""


class TrackerRefused(RuntimeError):
    """The tracker answered, and the answer was no. Permanent."""
