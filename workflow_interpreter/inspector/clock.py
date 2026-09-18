"""Time and sleeping as injected capabilities (§8.2).

`stale_after` and `max_wall` are the wrapper's only two runtime enforcement
powers, and both are pure functions of elapsed time. A test that has to sleep
for them is a test that is slow and flaky, so the clock is injected everywhere
and the real one lives here alone.

Timestamps are recorded as UTC ISO-8601 strings, matching the `bdio` carriers
(`ProcessHandle.started_at`, `ExitRecord.ended_at`), never as floats.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Final, Protocol

ISO_SUFFIX_UTC: Final[str] = "+00:00"
ISO_SUFFIX_Z: Final[str] = "Z"


class Clock(Protocol):
    """Wall-clock reads and sleeps, injected so the drills need no real time."""

    def now(self) -> datetime: ...  # pragma: no cover - protocol

    def sleep(self, seconds: float) -> None: ...  # pragma: no cover - protocol


class SystemClock:
    """The real clock: UTC wall time and `time.sleep`."""

    def now(self) -> datetime:
        """The current UTC time."""
        return datetime.now(tz=UTC)

    def sleep(self, seconds: float) -> None:
        """Block for `seconds`."""
        time.sleep(seconds)


def to_iso(moment: datetime) -> str:
    """Render an aware datetime as the `…Z` UTC string the carriers store."""
    text = moment.astimezone(UTC).isoformat()
    return text.replace(ISO_SUFFIX_UTC, ISO_SUFFIX_Z)


def from_iso(text: str) -> datetime:
    """Parse a recorded timestamp back into an aware datetime."""
    normalized = (
        f"{text[: -len(ISO_SUFFIX_Z)]}{ISO_SUFFIX_UTC}"
        if text.endswith(ISO_SUFFIX_Z)
        else text
    )
    return datetime.fromisoformat(normalized).astimezone(UTC)


def elapsed_seconds(since: str, now: datetime) -> float:
    """Seconds between a recorded timestamp and `now` (never negative)."""
    return max(0.0, (now - from_iso(since)).total_seconds())
