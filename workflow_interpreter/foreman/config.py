"""Injected foreman configuration and deterministic wrapper-root derivation."""

import hashlib
import tomllib
from pathlib import Path
from typing import Annotated, Final

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from workflow_interpreter.bdio.config import BdConfig, SigningConfig
from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.contractor.tracker_config import TrackerSettings
from workflow_interpreter.contractor.verification import CheckCommand
from workflow_interpreter.foreman.wake_constants import (
    DEFAULT_EVENT_CAP,
    MAX_EVENT_CAP,
    MSG_STALE_SPACING,
)
from workflow_interpreter.inspector.config import InspectorConfig
from workflow_interpreter.inspector.sandbox import GIT_ENTRY
from workflow_interpreter.profiles.config import MODEL_VENDOR_DEFAULT, ProfileConfig

MSG_WORKTREE_REPO_ROOT: Final[str] = (
    "foreman repo_root {repo_root} is a linked worktree; configure the "
    "repository whose git common directory it borrows (run-ledger §3.5)"
)


class CrewBinding(BaseModel):
    """The profile and pinned invocation choices selected for a graph role."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    profile: str
    model: Annotated[str, StringConstraints(min_length=1)]
    effort: Annotated[str, StringConstraints(min_length=1)]


class WakeConfig(BaseModel):
    """Trusted host notification limits, never graph- or crew-selected commands."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    poll_s: float = Field(default=5, gt=0, allow_inf_nan=False)
    stale_s: float = Field(default=120, gt=0, allow_inf_nan=False)
    min_fire_interval_s: float = Field(default=30, gt=0, allow_inf_nan=False)
    lifetime_cap: int = Field(default=DEFAULT_EVENT_CAP, gt=0, le=MAX_EVENT_CAP)
    hook_argv: tuple[
        Annotated[
            str, StringConstraints(min_length=1, max_length=4096, pattern=r"^[^\x00]+$")
        ],
        ...,
    ] = Field(default=(), max_length=64)
    hook_timeout_s: float = Field(default=10, gt=0, le=10, allow_inf_nan=False)
    hook_backoff_s: float = Field(default=5, gt=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def _stale_above_poll(self) -> "WakeConfig":
        """A normally scheduled poll is not itself a stale heartbeat."""
        if self.stale_s <= self.poll_s:
            raise ValueError(MSG_STALE_SPACING)
        return self


class ForemanConfig(BaseModel):
    """All foreman authority arrives as injected configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo_root: Path
    wrapper_home: Path
    bd: BdConfig
    store: BackendKind = BackendKind.BD
    """Which backend a NEW attempt root is pinned to (§3.2, D18).

    New roots only: an existing root always resolves through the backend its
    contractor record or `tasks` row pinned, so flipping this back to `bd` leaves
    every ledger-backed root loadable. There is no reverse migration."""
    signing: SigningConfig | None = None
    profiles: ProfileConfig = Field(default_factory=ProfileConfig)
    wake: WakeConfig = Field(default_factory=WakeConfig)
    project_config: dict[str, str | int | bool] = Field(default_factory=dict)
    roles: dict[str, CrewBinding] = Field(default_factory=dict)
    tracker: TrackerSettings = Field(default_factory=TrackerSettings)
    """Which tracker this repository has (store-restructure §3.3).

    Reached through `contractor/` because the tracker is the contractor's
    collaborator and nothing else's: the foreman, the inspector and the crew
    never touch one."""
    contractor_graph: Path | None = None
    contractor_checks: tuple[CheckCommand, ...] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    host: str
    inspector: InspectorConfig
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
        if self.inspector.repo_root != self.repo_root:
            raise ValueError("inspector repo_root must match foreman repo_root")
        if self.inspector.wrapper_root != self.wrapper_root:
            raise ValueError("inspector wrapper_root must match foreman wrapper_root")
        for role, binding in self.roles.items():
            if binding.model == MODEL_VENDOR_DEFAULT:
                raise ValueError(
                    f"role {role!r} cannot bind model {MODEL_VENDOR_DEFAULT!r}"
                )
        return self


def load_config(path: Path) -> ForemanConfig:
    """Load a checked-in TOML config without consulting ambient environment.

    The repository identity is resolved HERE rather than in the model, because
    it is a fact about the filesystem: a linked worktree borrows another
    checkout's git common directory, so its ledger fence, its `refs/wf/` pins
    and its wrapper root would all be the OTHER repository's while `repo_root`
    claimed to name this one (run-ledger §3.5). Routed on what `.git` IS, the
    way every other resolver in this repository does it, rather than on `git
    rev-parse --git-common-dir`: the answer is the same and no subprocess runs
    inside configuration loading.
    """
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    config = ForemanConfig.model_validate(raw).model_copy(update={"config_path": path})
    if (config.repo_root / GIT_ENTRY).is_file():
        raise ValueError(MSG_WORKTREE_REPO_ROOT.format(repo_root=config.repo_root))
    return config
