"""Frozen configuration and provenance for disposable offline toolchains."""

from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Final, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

from workflow_interpreter.inspector import toolchain_constants as tc
from workflow_interpreter.inspector.errors import SandboxUnavailable

MODEL: Final[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
DEFAULT_UV: Final[str] = "uv"
DEFAULT_COPY: Final[str] = "cp"
DEFAULT_TIMEOUT: Final[float] = 120.0
DEFAULT_BYTES: Final[int] = 2 * 1024 * 1024 * 1024
DEFAULT_ENTRIES: Final[int] = 100_000
DEFAULT_RESERVE: Final[int] = 64 * 1024 * 1024


class ToolchainUnavailable(SandboxUnavailable):
    """Pinned offline tools cannot be prepared safely; retrying a node cannot help."""


class CopyMethod(StrEnum):
    """The copy request, not an assertion that the filesystem supports reflinks."""

    AUTO = "reflink-auto"
    PLAIN = "plain"


class ToolchainConfig(BaseModel):
    """Host-owned seed locations and preparation bounds, injected by configuration."""

    model_config = MODEL
    seed_root: Path | None = None
    host_cache: Path | None = None
    python_root: Path | None = None
    projects: tuple[str, ...] = (".",)
    uv_binary: str = DEFAULT_UV
    copy_binary: str = DEFAULT_COPY
    allow_host_fetch: bool = True
    timeout_s: float = Field(default=DEFAULT_TIMEOUT, gt=0)
    max_bytes: int = Field(default=DEFAULT_BYTES, gt=0)
    max_entries: int = Field(default=DEFAULT_ENTRIES, gt=0)
    reserve_bytes: int = Field(default=DEFAULT_RESERVE, ge=0)

    def with_host_env(self, env: Mapping[str, str]) -> Self:
        """Capture operator uv locations before a profile replaces child cache paths."""
        data = self.model_dump()
        if self.host_cache is None and env.get(tc.ENV_CACHE):
            data["host_cache"] = env[tc.ENV_CACHE]
        if self.python_root is None and env.get(tc.ENV_PYTHON):
            data["python_root"] = env[tc.ENV_PYTHON]
        if env.get(tc.ENV_OFFLINE, "").lower() in ("1", "true"):
            data["allow_host_fetch"] = False
        return self.model_validate(data)

    @field_validator("seed_root", "host_cache", "python_root")
    @classmethod
    def absolute_paths(cls, value: Path | None) -> Path | None:
        """Refuse relative host authority."""
        if value is not None and not value.is_absolute():
            raise ValueError(tc.MSG_HOST_ABSOLUTE)
        return value

    @field_validator("projects")
    @classmethod
    def relative_projects(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        """Permit explicit relative projects without parent traversal."""
        for value in values:
            if not value or Path(value).is_absolute() or ".." in Path(value).parts:
                raise ValueError(tc.MSG_PROJECT_RELATIVE)
        if len(values) != len(set(values)):
            raise ValueError(tc.MSG_DUPLICATE_PROJECTS)
        return values


class SeedReceipt(BaseModel):
    """Retained provenance; the corresponding private files are disposable."""

    model_config = MODEL
    project: str
    seed_key: str
    lock_digest: str
    project_digest: str
    python_digest: str | None = None
    interpreter_version: str
    uv_version: str
    copied_bytes: int = Field(ge=0)
    copy_method: CopyMethod
    offline_probe: str
    host_fetch: bool


class SeedPreparation(BaseModel):
    """Inspector-only preparation result used to build mounts and the receipt."""

    model_config = MODEL
    cache: Path
    protected_roots: tuple[Path, ...] = ()
    receipts: tuple[SeedReceipt, ...] = ()
