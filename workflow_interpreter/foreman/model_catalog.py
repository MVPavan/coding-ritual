"""Bounded CLI catalog discovery with a sourced Claude seed."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final, Protocol

import structlog
from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_serializer,
    field_validator,
)

from workflow_interpreter.contracts.execution import CrewName
from workflow_interpreter.foreman.config import ForemanConfig
from workflow_interpreter.profiles.claude import (
    EFFORT,
    MODEL,
    OUTPUT_FORMAT,
    PRINT,
    SETTING_SOURCES,
    STRICT_MCP,
    TOOLS,
)

SCHEMA_VERSION: Final[int] = 1
CATALOG_FILE: Final[str] = "model-catalog.json"
SEED_FILE: Final[Path] = (
    Path(__file__).resolve().parents[2] / "config" / "claude-model-seed.json"
)
CODEX_SOURCE: Final[str] = "bundled-cli"
CLAUDE_SOURCE: Final[str] = "checked-seed-and-probe"
CLAUDE_REQUIRED_FLAGS: Final[tuple[str, ...]] = (
    "--model",
    "--effort",
    "--autocompact",
    "--tools",
    "--output-format",
    "--max-budget-usd",
)
CLAUDE_EFFORT_ORDER: Final[tuple[str, ...]] = ("low", "medium", "high", "xhigh", "max")
DISCOVERY_TIMEOUT_S: Final[float] = 5.0
PROBE_TIMEOUT_S: Final[float] = 15.0
PROBE_ATTEMPTS: Final[int] = 3
PROBE_BUDGET_USD: Final[float] = 0.10
"""Conservative bound for one Opus turn; size against a live probe in S8."""
STARTUP_BUDGET_USD: Final[float] = 0.50
PROBE_BACKOFF_S: Final[float] = 0.25
LOG = structlog.get_logger(__name__)


class Visibility(StrEnum):
    """Codex bundled model visibility."""

    LIST = "list"
    HIDE = "hide"


class VerificationStatus(StrEnum):
    """What owner-start qualification actually established."""

    SEED_UNPROBED = "seed-unprobed"
    PROBE_OK = "probe-ok"
    PROBE_FAILED = "probe-failed"


class CliModelSupport(StrEnum):
    """Whether the checked seed established CLI support for an ID."""

    UNVERIFIED = "unverified"
    VERIFIED = "verified"


class CatalogProvenance(StrEnum):
    """How this process obtained its catalog snapshot."""

    REFRESHED = "refreshed"
    LOADED = "loaded"
    FALLBACK = "fallback"


class Runner(Protocol):
    """The injectable CLI boundary used by discovery and admission."""

    def __call__(
        self, argv: list[str], timeout: float
    ) -> subprocess.CompletedProcess[str]:
        """Run one bounded CLI command."""


class CatalogModel(BaseModel):
    """One normalized, selectable model."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    efforts: tuple[str, ...]
    context_window: int
    visibility: Visibility | None = None
    verification: VerificationStatus | None = None
    probe_attempts: int | None = None
    probe_duration_ms: int | None = None
    probe_cost_usd: float | None = None
    probe_error: str | None = None


class FamilySnapshot(BaseModel):
    """One family's qualified choices and bounded diagnostics."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    cli_version: str | None = None
    source: str
    models: tuple[CatalogModel, ...] = ()
    hidden_count: int = 0
    available: bool = False
    warnings: tuple[str, ...] = ()
    refusals: tuple[str, ...] = ()


class CatalogSnapshot(BaseModel):
    """An immutable owner-start result, including its audit digest."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int = SCHEMA_VERSION
    generated_at: str
    families: Mapping[CrewName, FamilySnapshot]
    digest: str

    @field_validator("families", mode="after")
    @classmethod
    def _freeze_families(
        cls, value: Mapping[CrewName, FamilySnapshot]
    ) -> Mapping[CrewName, FamilySnapshot]:
        """Prevent mutation of a qualified snapshot after construction."""
        return MappingProxyType(dict(value))

    @field_serializer("families")
    def _serialize_families(
        self, value: Mapping[CrewName, FamilySnapshot]
    ) -> dict[str, dict[str, Any]]:
        """Serialize the read-only mapping as canonical family objects."""
        return {
            key.value: family.model_dump(exclude_none=True)
            for key, family in value.items()
        }


@dataclass(frozen=True)
class CatalogResult:
    """A snapshot with its process-local provenance, or both absent."""

    snapshot: CatalogSnapshot | None
    provenance: CatalogProvenance | None


class ModelCatalog:
    """Discover CLI choices and qualify bound Claude models once per owner start."""

    def __init__(
        self,
        codex_binary: str,
        claude_binary: str,
        runner: Runner | None = None,
        *,
        host_env: Mapping[str, str] | None = None,
        seed_path: Path = SEED_FILE,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        """Inject executable paths, process environment, and the CLI boundary."""
        self._binaries = {CrewName.CODEX: codex_binary, CrewName.CLAUDE: claude_binary}
        self._runner = runner
        self._host_env = None if host_env is None else dict(host_env)
        self._seed_path = seed_path
        self._sleeper = sleeper

    def _run(self, argv: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
        """Run a bounded command through the injected boundary."""
        if self._runner is not None:
            return self._runner(argv, timeout)
        return subprocess.run(
            argv,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            env=self._host_env,
        )

    def refresh(
        self, bindings: Mapping[str, tuple[str, str]] | None = None
    ) -> CatalogSnapshot:
        """Discover both families and probe each distinct bound Claude model."""
        chosen = bindings or {}
        codex = self._codex()
        claude = self._claude(chosen)
        families = {CrewName.CLAUDE: claude, CrewName.CODEX: codex}
        digest = _catalog_digest(families)
        generated_at = (
            datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        )
        return CatalogSnapshot(
            generated_at=generated_at, families=families, digest=digest
        )

    def _codex(self) -> FamilySnapshot:
        """Normalize visible bundled Codex entries without claiming entitlement."""
        binary = self._binaries[CrewName.CODEX]
        try:
            version = self._run([binary, "--version"], DISCOVERY_TIMEOUT_S)
            listing = self._run(
                [binary, "debug", "models", "--bundled"], DISCOVERY_TIMEOUT_S
            )
            if version.returncode or not version.stdout.strip() or listing.returncode:
                raise ValueError("Codex version or bundled models command failed")
            raw = json.loads(listing.stdout)
            entries = raw["models"]
            if not isinstance(entries, list) or not entries:
                raise ValueError("Codex models list is empty or invalid")
            seen: set[str] = set()
            models: list[CatalogModel] = []
            hidden = 0
            for entry in entries:
                name = entry["slug"]
                window = entry["context_window"]
                levels = entry["supported_reasoning_levels"]
                visibility = entry["visibility"]
                if (
                    not isinstance(name, str)
                    or not name.strip()
                    or name in seen
                    or type(window) is not int
                    or window <= 0
                    or not isinstance(levels, list)
                    or not levels
                    or visibility not in (Visibility.LIST, Visibility.HIDE)
                ):
                    raise ValueError("Codex model entry is malformed or duplicated")
                efforts = tuple(sorted({level["effort"] for level in levels}))
                if not efforts or any(
                    not isinstance(level, str) or not level for level in efforts
                ):
                    raise ValueError("Codex effort list is malformed")
                seen.add(name)
                if visibility == Visibility.HIDE:
                    hidden += 1
                else:
                    models.append(
                        CatalogModel(
                            id=name,
                            efforts=efforts,
                            context_window=window,
                            visibility=visibility,
                        )
                    )
            return FamilySnapshot(
                cli_version=version.stdout.strip(),
                source=CODEX_SOURCE,
                models=tuple(sorted(models, key=lambda model: model.id)),
                hidden_count=hidden,
                available=True,
            )
        except (
            OSError,
            subprocess.TimeoutExpired,
            ValueError,
            KeyError,
            TypeError,
            json.JSONDecodeError,
        ) as error:
            LOG.warning(
                "wf.model_catalog.discovery_failed",
                family=CrewName.CODEX.value,
                reason=str(error),
            )
            return FamilySnapshot(
                cli_version=None,
                source=CODEX_SOURCE,
                refusals=(f"codex catalog unavailable: {error}",),
            )

    def _claude(self, bindings: Mapping[str, tuple[str, str]]) -> FamilySnapshot:
        """Check Claude flags and seed, then qualify bound IDs with paid probes."""
        binary = self._binaries[CrewName.CLAUDE]
        try:
            seed = json.loads(self._seed_path.read_text(encoding="utf-8"))
            if seed["schema_version"] != SCHEMA_VERSION:
                raise ValueError("unsupported Claude seed schema")
            version = self._run([binary, "--version"], DISCOVERY_TIMEOUT_S)
            help_result = self._run([binary, "--help"], DISCOVERY_TIMEOUT_S)
            if (
                version.returncode
                or not version.stdout.strip()
                or help_result.returncode
            ):
                raise ValueError("Claude version or help command failed")
            if any(flag not in help_result.stdout for flag in CLAUDE_REQUIRED_FLAGS):
                raise ValueError("Claude help is missing required flags")
            entries = seed["models"]
            if not isinstance(entries, list) or not entries:
                raise ValueError("Claude seed is empty or invalid")
            models: dict[str, CatalogModel] = {}
            cli_version = version.stdout.strip()
            version_number = _version_number(cli_version.split()[0])
            drifted = False
            for entry in entries:
                model = CatalogModel(
                    id=entry["id"],
                    context_window=entry["context_window"],
                    efforts=tuple(sorted(entry["efforts"])),
                    verification=VerificationStatus.SEED_UNPROBED,
                )
                if (
                    not model.id
                    or model.id in models
                    or model.context_window <= 0
                    or any(
                        effort not in CLAUDE_EFFORT_ORDER for effort in model.efforts
                    )
                    or not entry["source_url"]
                    or not entry["effort_source_url"]
                    or not entry["source_date"]
                    or entry["cli_model_support"]
                    not in (CliModelSupport.UNVERIFIED, CliModelSupport.VERIFIED)
                    or _version_number(entry["verified_cli_min"])
                    > _version_number(entry["verified_cli_max"])
                ):
                    raise ValueError("Claude seed entry is malformed or duplicated")
                if not (
                    _version_number(entry["verified_cli_min"])
                    <= version_number
                    <= _version_number(entry["verified_cli_max"])
                ):
                    drifted = True
                models[model.id] = model
            warnings: list[str] = []
            if drifted:
                warnings.append("Claude CLI version differs from checked seed version")
            refusals: list[str] = []
            probed: set[str] = set()
            reserved = 0.0
            for role, (name, effort) in sorted(bindings.items()):
                selected = models.get(name)
                if selected is None:
                    reason = f"role {role!r}: unknown Claude model {name!r}"
                    refusals.append(reason)
                    LOG.warning("wf.model_catalog.binding_refused", reason=reason)
                elif effort not in selected.efforts:
                    reason = (
                        f"role {role!r}: unsupported effort {effort!r} for {name!r}"
                    )
                    refusals.append(reason)
                    LOG.warning("wf.model_catalog.binding_refused", reason=reason)
                elif name not in probed:
                    probed.add(name)
                    probe_effort = next(
                        level
                        for level in CLAUDE_EFFORT_ORDER
                        if level in selected.efforts
                    )
                    passed, charged, cost, duration_ms, attempts, probe_error = (
                        self._probe_claude(binary, name, probe_effort, reserved)
                    )
                    reserved += charged
                    models[name] = selected.model_copy(
                        update={
                            "verification": (
                                VerificationStatus.PROBE_OK
                                if passed
                                else VerificationStatus.PROBE_FAILED
                            ),
                            "probe_attempts": attempts,
                            "probe_duration_ms": duration_ms,
                            "probe_cost_usd": cost,
                            "probe_error": probe_error,
                        }
                    )
                    if not passed:
                        LOG.warning(
                            "wf.model_catalog.probe_failed",
                            model=name,
                            reason=probe_error,
                        )
                        refusals.extend(
                            f"role {bound_role!r}: Claude probe failed for {name!r}: {probe_error}"
                            for bound_role, (bound_name, _) in sorted(bindings.items())
                            if bound_name == name
                        )
            return FamilySnapshot(
                cli_version=cli_version,
                source=CLAUDE_SOURCE,
                models=tuple(models[name] for name in sorted(models)),
                available=True,
                warnings=tuple(warnings),
                refusals=tuple(dict.fromkeys(refusals)),
            )
        except (
            OSError,
            subprocess.TimeoutExpired,
            ValueError,
            KeyError,
            TypeError,
            json.JSONDecodeError,
        ) as error:
            LOG.warning(
                "wf.model_catalog.discovery_failed",
                family=CrewName.CLAUDE.value,
                reason=str(error),
            )
            return FamilySnapshot(
                cli_version=None,
                source=CLAUDE_SOURCE,
                refusals=(f"claude catalog unavailable: {error}",),
            )

    def _probe_claude(
        self, binary: str, model: str, effort: str, reserved: float
    ) -> tuple[bool, float, float | None, int, int, str | None]:
        """Admit one bound model with a retry and aggregate cost ceiling."""
        charged = 0.0
        reported_cost: float | None = None
        began = time.monotonic()
        last_error: str | None = None
        for attempt in range(PROBE_ATTEMPTS):
            if reserved + charged + PROBE_BUDGET_USD > STARTUP_BUDGET_USD:
                return (
                    False,
                    charged,
                    reported_cost,
                    int((time.monotonic() - began) * 1000),
                    attempt,
                    "aggregate probe cost cap reached",
                )
            argv = [
                binary,
                PRINT,
                "Reply OK",
                *SETTING_SOURCES,
                STRICT_MCP,
                MODEL,
                model,
                EFFORT,
                effort,
                TOOLS,
                "",
                OUTPUT_FORMAT[0],
                "json",
                "--max-budget-usd",
                str(PROBE_BUDGET_USD),
            ]
            charged += PROBE_BUDGET_USD
            try:
                result = self._run(argv, PROBE_TIMEOUT_S)
                if result.returncode == 0:
                    payload = json.loads(result.stdout)
                    if not isinstance(payload, dict):
                        raise ValueError("Claude probe returned a non-object result")
                    cost = payload.get("total_cost_usd")
                    if (
                        isinstance(cost, (int, float))
                        and not isinstance(cost, bool)
                        and cost >= 0
                    ):
                        reported_cost = (reported_cost or 0.0) + float(cost)
                    if payload.get("is_error") is False:
                        return (
                            True,
                            charged,
                            reported_cost,
                            int((time.monotonic() - began) * 1000),
                            attempt + 1,
                            None,
                        )
                    last_error = "Claude probe reported an error result"
                else:
                    last_error = f"Claude probe exited {result.returncode}"
            except (
                OSError,
                subprocess.TimeoutExpired,
                ValueError,
                TypeError,
                json.JSONDecodeError,
            ) as error:
                last_error = str(error)
            if attempt + 1 < PROBE_ATTEMPTS:
                self._sleeper(PROBE_BACKOFF_S * (2**attempt))
        return (
            False,
            charged,
            reported_cost,
            int((time.monotonic() - began) * 1000),
            PROBE_ATTEMPTS,
            last_error,
        )

    def write(self, snapshot: CatalogSnapshot, wrapper_root: Path) -> Path:
        """Atomically publish a diagnostic snapshot under the wrapper root."""
        wrapper_root.mkdir(parents=True, exist_ok=True)
        target = wrapper_root / CATALOG_FILE
        content = snapshot.model_dump(mode="json", exclude_none=True)
        temporary: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=wrapper_root, prefix=f".{CATALOG_FILE}.", delete=False
            ) as handle:
                temporary = handle.name
                handle.write(_json_bytes(content))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
            temporary = None
            directory_fd = os.open(wrapper_root, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temporary is not None:
                os.unlink(temporary)
        return target


def load_snapshot(wrapper_root: Path) -> CatalogSnapshot | None:
    """Read an owner's snapshot for worker diagnostics, never admission."""
    path = wrapper_root / CATALOG_FILE
    if not path.exists():
        return None
    snapshot = CatalogSnapshot.model_validate_json(path.read_text(encoding="utf-8"))
    if snapshot.schema_version != SCHEMA_VERSION:
        raise ValueError("unsupported model catalog schema")
    if _catalog_digest(snapshot.families) != snapshot.digest:
        raise ValueError("model catalog digest mismatch")
    return snapshot


def catalog_at_start(
    config: ForemanConfig,
    command: str,
    host_env: Mapping[str, str],
    runner: Runner | None = None,
    *,
    child_command: str | None = None,
) -> CatalogResult:
    """Refresh only long-lived owners; other commands read diagnostics."""

    def prior_snapshot(provenance: CatalogProvenance) -> CatalogResult:
        """Read the previous file for diagnostics without admitting from it."""
        try:
            snapshot = load_snapshot(config.wrapper_root)
            return CatalogResult(snapshot, provenance if snapshot is not None else None)
        except (
            OSError,
            ValueError,
            ValidationError,
            subprocess.TimeoutExpired,
        ) as error:
            LOG.warning("wf.model_catalog.load_failed", reason=str(error))
            return CatalogResult(None, None)

    if command not in ("run", "contract") and not (
        command == "children" and child_command == "drive"
    ):
        return prior_snapshot(CatalogProvenance.LOADED)
    try:
        catalog = ModelCatalog(
            config.profiles.binary_for(CrewName.CODEX),
            config.profiles.binary_for(CrewName.CLAUDE),
            runner,
            host_env=host_env,
        )
        snapshot = catalog.refresh(
            {
                role: (binding.model, binding.effort)
                for role, binding in config.roles.items()
                if binding.profile.removeprefix("profile:") == CrewName.CLAUDE.value
            }
        )
        catalog.write(snapshot, config.wrapper_root)
        return CatalogResult(snapshot, CatalogProvenance.REFRESHED)
    except (OSError, ValueError, ValidationError, subprocess.TimeoutExpired) as error:
        LOG.warning("wf.model_catalog.refresh_failed", reason=str(error))
        return prior_snapshot(CatalogProvenance.FALLBACK)


def _catalog_digest(families: Mapping[CrewName, FamilySnapshot]) -> str:
    """Hash only selectable catalog facts, excluding probe diagnostics."""
    fields = {"id", "efforts", "context_window", "visibility", "verification"}
    content = {
        family.value: {
            "cli_version": snapshot.cli_version,
            "models": [
                model.model_dump(mode="json", include=fields, exclude_none=True)
                for model in snapshot.models
            ],
        }
        for family, snapshot in sorted(families.items())
    }
    return hashlib.sha256(_json_bytes(content)).hexdigest()


def _json_bytes(value: object) -> bytes:
    """Canonicalize content for persistence and its audit digest."""
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def _version_number(value: str) -> tuple[int, int, int]:
    """Parse the three-part CLI version used by the checked seed."""
    pieces = value.split(".")
    if len(pieces) != 3 or any(not piece.isdecimal() for piece in pieces):
        raise ValueError("invalid Claude CLI version")
    return int(pieces[0]), int(pieces[1]), int(pieces[2])
