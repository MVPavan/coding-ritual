"""Advisory observation diagnostics never acquire workflow authority."""

from pathlib import Path

import structlog
from pydantic import BaseModel, ConfigDict, Field

from workflow_interpreter.foreman.wake_constants import (
    DETAIL_BYTES,
    LOG_DURABILITY,
    OBSERVATION_STATUS,
)
from workflow_interpreter.supervisor.errors import WrapperDirError
from workflow_interpreter.supervisor.paths import read_record, write_record


def bounded(text: str, limit: int = DETAIL_BYTES) -> str:
    """Bound UTF-8 diagnostics without retaining approval payloads or signatures."""
    return text.encode("utf-8")[:limit].decode("utf-8", errors="ignore")


class ObservationStatus(BaseModel):
    """Bounded advisory failures; repeated reads do not recount a corrupt line."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    saturated: bool = False
    error: str | None = None
    heartbeat_degraded: str | None = None
    journal_degraded: int = Field(default=0, ge=0)
    identity_degraded: str | None = None

    def degraded(
        self,
        *,
        error: str | None = None,
        heartbeat: str | None = None,
        journal: int = 0,
        identity: str | None = None,
    ) -> "ObservationStatus":
        """Retain bounded diagnostic evidence without turning it into a refusal."""
        updated = self.model_copy(
            update={
                "error": bounded(error) if error else self.error,
                "heartbeat_degraded": bounded(heartbeat)
                if heartbeat
                else self.heartbeat_degraded,
                "journal_degraded": max(self.journal_degraded, journal),
                "identity_degraded": bounded(identity)
                if identity
                else self.identity_degraded,
            }
        )
        if updated != self:
            structlog.get_logger(__name__).error(LOG_DURABILITY, **updated.model_dump())
        return updated


def read_status(directory: Path) -> ObservationStatus:
    """Read optional diagnostics without letting malformed diagnostics abort status."""
    try:
        return (
            read_record(directory / OBSERVATION_STATUS, ObservationStatus)
            or ObservationStatus()
        )
    except (WrapperDirError, OSError, ValueError) as error:
        return ObservationStatus().degraded(error=str(error))


def save_status(directory: Path, status: ObservationStatus) -> ObservationStatus:
    """Attempt persistence, returning even unwritable evidence to the active caller."""
    try:
        write_record(directory / OBSERVATION_STATUS, status)
    except (WrapperDirError, OSError, ValueError) as error:
        return status.degraded(error=str(error))
    return status
