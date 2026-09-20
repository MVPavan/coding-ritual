"""Which tracker this repository has, and what it is required to answer.

In `contractor/` rather than in `tracker/` on purpose: the tracker is the
contractor's collaborator and nothing else's, so the foreman's configuration
reaches it through the contractor's surface exactly as it reaches
`CheckCommand`. Nothing outside `contractor/` imports `tracker/`.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, model_validator

from workflow_interpreter.tracker.bd_transport import BdConfig

MSG_BD_REQUIRED: Final[str] = (
    "the bd tracker needs its transport: set tracker.bd.workspace and "
    "tracker.bd.actor in the foreman configuration (store-restructure §3.3)"
)


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
    bd: BdConfig | None = None
    """How to reach bd, required by the `bd` backend alone.

    HERE rather than on `ForemanConfig` (S6 review, finding 7): as a mandatory
    top-level field it made a `backend = "file"` repository configure a bd
    workspace it never reaches, and it put a bd import in `foreman/`. Which
    tracker this repository has and how to reach it are one fact."""
    blockers_required: bool = False
    """Whether a tracker that cannot answer blockers refuses (R9).

    False by default: an absent capability is not liveness ambiguity, and the
    record says `blockers_checked=false` so the trace shows which policy
    applied. A repository whose dependency graph actually gates work turns it
    on and gets a refusal instead of a recorded gap."""

    @model_validator(mode="after")
    def _backend_has_its_transport(self) -> TrackerSettings:
        """The chosen backend's own settings are present, or the config is invalid."""
        if self.backend is TrackerBackend.BD and self.bd is None:
            raise ValueError(MSG_BD_REQUIRED)
        return self
