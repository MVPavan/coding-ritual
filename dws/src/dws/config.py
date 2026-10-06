"""Owner-controlled local configuration; callers cannot raise these limits."""

from __future__ import annotations

import ipaddress
import os
import stat
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


def prepare_owner_state(path: Path) -> Path:
    """Create a private state root, or tighten a safe existing owner directory.

    Existing owner directories such as mode 0755 become 0700. Foreign-owned,
    writable-by-others, and symlink roots are rejected without changing them.
    Keep the final path component intact until these checks have completed.
    """
    absolute = path.absolute()
    try:
        before = absolute.lstat()
    except FileNotFoundError:
        absolute.mkdir(parents=True, exist_ok=True, mode=0o700)
        before = absolute.lstat()
    if not stat.S_ISDIR(before.st_mode) or before.st_uid != os.geteuid():
        raise ValueError(
            "DWS state must be a directory owned by the current user, not a symlink"
        )
    descriptor = os.open(absolute, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        current = os.fstat(descriptor)
        if (
            (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino)
            or current.st_uid != os.geteuid()
            or not stat.S_ISDIR(current.st_mode)
        ):
            raise ValueError("DWS state directory ownership changed during startup")
        if stat.S_IMODE(current.st_mode) & 0o022:
            raise ValueError("DWS state must not be writable by other users")
        if stat.S_IMODE(current.st_mode) != 0o700:
            os.fchmod(descriptor, 0o700)
            os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return absolute


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)
    data_dir: Path = Path(".state")
    api_url: str = "http://127.0.0.1:8765"
    token: str | None = Field(default=None, repr=False)
    searxng_url: str | None = None
    crawl4ai_url: str | None = None
    crawl4ai_token: str | None = Field(default=None, repr=False)
    tinyfish_api_key: str | None = Field(default=None, repr=False, exclude=True)
    tinyfish_enabled: bool = True
    tinyfish_fetch_escalation: bool = True
    tinyfish_fetch_ttl: int = Field(default=3600, ge=0, le=31_536_000)
    tinyfish_search_url: str = "https://api.search.tinyfish.ai/"
    tinyfish_fetch_url: str = "https://api.fetch.tinyfish.ai/"
    tinyfish_search_per_minute: int = Field(default=30, ge=1)
    tinyfish_search_per_hour: int = Field(default=500, ge=1)
    tinyfish_fetch_per_minute: int = Field(default=150, ge=1)
    tinyfish_fetch_per_day: int = Field(default=1000, ge=1)
    ddgs_enabled: bool = True
    allowed_private_hosts: tuple[str, ...] = ()
    max_bytes: int = Field(default=8_000_000, ge=1024, le=100_000_000)
    max_text_chars: int = Field(default=500_000, ge=1024, le=5_000_000)
    max_output_chars: int = Field(default=16_000, ge=256, le=100_000)
    max_response_bytes: int = Field(default=65_536, ge=16_384, le=1_000_000)
    request_timeout: float = Field(default=30, ge=1, le=120)
    max_pages: int = Field(default=200, ge=1, le=5000)
    max_depth: int = Field(default=5, ge=0, le=20)
    max_crawl_seconds: int = Field(default=600, ge=1, le=3600)
    max_jobs: int = Field(default=32, ge=1, le=1024)
    acquisition_slots: int = Field(default=4, ge=1, le=32)
    max_storage_bytes: int = Field(default=2_000_000_000, ge=1_000_000)
    min_free_bytes: int = Field(default=100_000_000, ge=0)
    retention_seconds: int = Field(default=2_592_000, ge=1)
    lease_seconds: int = Field(default=120, ge=10, le=600)

    @field_validator("tinyfish_search_url", "tinyfish_fetch_url")
    @classmethod
    def tinyfish_endpoint(cls, value: str, info: ValidationInfo) -> str:
        # Local import avoids the Settings/net dependency cycle.
        from dws.errors import DWSError
        from dws.net import canonical_url

        try:
            endpoint = canonical_url(value)
            parsed = urlsplit(endpoint)
            host = parsed.hostname or ""
            try:
                loopback = ipaddress.ip_address(host).is_loopback
            except ValueError:
                loopback = host == "localhost"
            product_host = (
                "api.search.tinyfish.ai"
                if info.field_name == "tinyfish_search_url"
                else "api.fetch.tinyfish.ai"
            )
            if not (
                (
                    parsed.scheme == "https"
                    and host == product_host
                    and parsed.port in {None, 443}
                )
                or (parsed.scheme == "http" and loopback)
            ):
                raise ValueError
            return endpoint
        except (DWSError, ValueError):
            raise ValueError(
                "TinyFish requires its HTTPS product host or an HTTP loopback endpoint"
            ) from None

    @field_validator("retention_seconds")
    @classmethod
    def supported_retention(cls, value: int) -> int:
        try:
            datetime.fromtimestamp(datetime.now(UTC).timestamp() + value, UTC)
        except (OverflowError, ValueError, OSError):
            raise ValueError("Retention exceeds the supported UTC timestamp range") from None
        return value

    @classmethod
    def from_env(cls) -> Settings:
        values: dict[str, object] = {}
        for key in cls.model_fields:
            name = "DWS_" + key.upper()
            if name in os.environ:
                value: object = os.environ[name]
                if key == "allowed_private_hosts":
                    value = tuple(x.strip().lower() for x in str(value).split(",") if x.strip())
                values[key] = value
        settings = cls.model_validate(values)
        return settings.model_copy(update={"data_dir": settings.data_dir.absolute()})
