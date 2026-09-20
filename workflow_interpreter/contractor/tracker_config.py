"""Which tracker this repository has, and what it is required to answer.

In `contractor/` rather than in `tracker/` on purpose: the tracker is the
contractor's collaborator and nothing else's, so the foreman's configuration
reaches it through the contractor's surface exactly as it reaches
`CheckCommand`. Nothing outside `contractor/` imports `tracker/`.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class TrackerBackend(StrEnum):
    """The trackers this build can be wired to."""

    BD = "bd"
    FILE = "file"
    NULL = "null"


class TrackerSettings(BaseModel):
    """One repository's tracker wiring."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    backend: TrackerBackend = TrackerBackend.BD
    """bd by default, because that is what every existing checkout runs."""
    path: Path | None = None
    """The document a `file` tracker is, required by that backend alone."""
    blockers_required: bool = False
    """Whether a tracker that cannot answer blockers refuses (R9).

    False by default: an absent capability is not liveness ambiguity, and the
    record says `blockers_checked=false` so the trace shows which policy
    applied. A repository whose dependency graph actually gates work turns it
    on and gets a refusal instead of a recorded gap."""
