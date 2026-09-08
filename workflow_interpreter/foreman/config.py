"""Injected foreman configuration and deterministic wrapper-root derivation."""

import hashlib
import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from workflow_interpreter.bdio.config import BdConfig, SigningConfig
from workflow_interpreter.profiles.config import MODEL_VENDOR_DEFAULT, ProfileConfig
from workflow_interpreter.supervisor.config import SupervisorConfig


class RunnerBinding(BaseModel):
    """The profile and pinned invocation choices selected for a graph role."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    profile: str
    model: str
    effort: str
    fallback: tuple[str, ...] = ()


class ForemanConfig(BaseModel):
    """All foreman authority arrives as injected configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo_root: Path
    wrapper_home: Path
    bd: BdConfig
    signing: SigningConfig | None = None
    profiles: ProfileConfig = Field(default_factory=ProfileConfig)
    project_config: dict[str, str | int | bool] = Field(default_factory=dict)
    roles: dict[str, RunnerBinding] = Field(default_factory=dict)
    host: str
    supervisor: SupervisorConfig
    band_wait_s: float = Field(default=30.0, gt=0)
    actor: str = Field(min_length=1)
    config_path: Path | None = None

    @property
    def wrapper_root(self) -> Path:
        """Return the stable root for the explicitly configured repository path."""
        digest = hashlib.sha256(
            str(self.repo_root.resolve()).encode("utf-8")
        ).hexdigest()
        return self.wrapper_home / digest[:16]

    @property
    def owner_path(self) -> Path:
        """Return the wrapper-root ownership record used by the tick guard.

        This is near-tautological: ``wrapper_root`` already includes the
        resolved repository hash, so another repository can collide here only
        on a hash collision.
        """
        return self.wrapper_root / "owner.json"

    @model_validator(mode="after")
    def _shares_one_repository_identity(self) -> "ForemanConfig":
        """Refuse relative or split paths without consulting the working directory."""
        if not self.repo_root.is_absolute() or not self.wrapper_home.is_absolute():
            raise ValueError("foreman repo_root and wrapper_home must be absolute")
        if self.supervisor.repo_root != self.repo_root:
            raise ValueError("supervisor repo_root must match foreman repo_root")
        if self.supervisor.wrapper_root != self.wrapper_root:
            raise ValueError("supervisor wrapper_root must match foreman wrapper_root")
        for role, binding in self.roles.items():
            if binding.model == MODEL_VENDOR_DEFAULT:
                raise ValueError(
                    f"role {role!r} cannot bind model {MODEL_VENDOR_DEFAULT!r}"
                )
        return self


def load_config(path: Path) -> ForemanConfig:
    """Load a checked-in TOML config without consulting ambient environment."""
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    return ForemanConfig.model_validate(raw).model_copy(update={"config_path": path})
