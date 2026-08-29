"""The durable ownership guard for a foreman's canonical wrapper root."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.foreman.config import ForemanConfig
from workflow_interpreter.supervisor.paths import read_record, write_record


class OwnerConflict(ValueError):
    """The wrapper root already belongs to another canonical repository."""


class OwnerRecord(BaseModel):
    """The canonical repository identity written beside all instance directories."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo_root: Path


def ensure_owner(config: ForemanConfig) -> OwnerRecord:
    """Create or verify the configured repository's ownership record.

    The guard sits under ``wrapper_root``, already
    ``sha256(realpath(repo_root))[:16]``, so it can only fire on a hash collision
    or when ``repo_root`` resolves differently between runs.
    """
    expected = OwnerRecord(repo_root=config.repo_root.resolve())
    found = read_record(config.owner_path, OwnerRecord)
    if found is None:
        write_record(config.owner_path, expected)
        return expected
    if found != expected:
        raise OwnerConflict("wrapper root belongs to a different repository")
    return found
