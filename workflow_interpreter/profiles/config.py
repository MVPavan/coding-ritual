"""Injected configuration for the §6 profiles: binaries, env passthrough, effort.

Frozen and handed in at construction, exactly like `bdio.config` and
`supervisor.config`, and for the same reason: `rules/python/safety.md` forbids
`os.environ` reads in business logic, and a profile whose sandbox posture came
from the ambient environment would be a profile the runner it launches could
reconfigure. The brief called for a `pydantic-settings` model; this repo has no
`pydantic-settings` dependency, the phase-4 brief allows only marker changes to
`pyproject.toml`, and both sibling config modules deliberately reject ambient
reads — so this follows the established convention instead. The host
environment still reaches the child, but only through `passthrough_env`: a
named allow-list, read once by the composition root and injected as data.

`effort` is a per-role free string on purpose. The three CLIs do not share an
effort vocabulary (`claude --effort low|medium|high|xhigh|max`,
`opencode --variant <provider-specific>`, `codex -c model_reasoning_effort=…`),
and inventing a translation table would silently mistranslate rather than fail.
Each value is passed through verbatim and validated by the CLI that owns it —
`claude` exits 1 on an unknown `--effort`, which is the loud failure §6 wants.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Annotated, Final

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_serializer

PROFILE_CONFIG_MODEL: Final[ConfigDict] = ConfigDict(
    frozen=True, extra="forbid", arbitrary_types_allowed=False
)

MODEL_VENDOR_DEFAULT: Final[str] = "default"
"""`TaskSpec.model` sentinel meaning "whatever the CLI would pick".

None of the three CLIs accepts the literal word `default` as a model name;
each takes an alias or a full name. The sentinel makes "unset" expressible
in a `TaskSpec` whose `model` is a required non-optional string, and the
model flag is then omitted rather than passed a word the CLI would reject."""

RUNNER_PREFIX: Final[str] = "profile:"
"""§6 records a runner as `runner = "profile:<name>"`; the registry accepts
either spelling so a bead's `runner_profile` can be looked up directly."""


class RunnerName(StrEnum):
    """The closed set of vendor runners phase 4 implements (§P4)."""

    CLAUDE = "claude"
    CODEX = "codex"
    OPENCODE = "opencode"


BASE_PASSTHROUGH_ENV: Final[tuple[str, ...]] = (
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "TZ",
)
"""The host keys every runner needs regardless of vendor.

`PATH` is not optional: `launch.py` execs with `os.execvpe(argv[0], argv, env)`,
which resolves the program against the PATH IN THAT ENV — a child env without
one cannot find its own CLI and exits 127. `HOME` is what carries subscription
credentials for all three CLIs (probed: `apiKeySource: "none"` and the run still
authenticated), so dropping it silently downgrades auth to none.
"""


VendorMap = Mapping[RunnerName, str]
"""A per-vendor mapping a FROZEN model can actually hold.

`frozen = True` freezes the model's ATTRIBUTES, not the objects behind them: a
`dict` field on it stays mutable in place, so "injected at construction and
never changed afterwards" was a claim the type did not make — on the object that
decides which binary gets exec'd. The annotation is a read-only `Mapping` so
callers keep passing the obvious `dict`, and `_freeze` makes what is STORED a
`MappingProxyType`, which has no mutating methods at all."""


def _freeze(value: VendorMap) -> VendorMap:
    """Store a read-only view, so a shared config cannot be edited in place."""
    return MappingProxyType(dict(value))


def _no_overrides() -> VendorMap:
    """The empty default, as a factory: a `mappingproxy` cannot be deep-copied,
    and pydantic deep-copies a literal default on every construction."""
    return MappingProxyType({})


class ProfileConfig(BaseModel):
    """Everything a profile needs that is not in the `TaskSpec` (§6)."""

    model_config = PROFILE_CONFIG_MODEL

    binary_overrides: Annotated[VendorMap, AfterValidator(_freeze)] = Field(
        default_factory=_no_overrides
    )
    """Where to find each CLI, when it is not simply on PATH under its own name.
    The `proc`-marked tests point these at stub executables, which is how a real
    `Supervisor.run` can be driven end to end without spending tokens."""
    passthrough_env: tuple[str, ...] = BASE_PASSTHROUGH_ENV
    """Host env keys copied into the child, in addition to the vendor's own
    named auth keys. A key that is absent from the host env is simply not set;
    it is never invented."""

    @field_serializer("binary_overrides")
    def _dump_vendor_map(self, value: VendorMap) -> dict[str, str]:
        """Dump the read-only view as a plain object.

        Without this pydantic warns that a `mappingproxy` is not the `dict` the
        schema expects. Nothing here is serialized in production — this config
        is injected, never carried — but a model that warns when dumped is a
        model somebody will eventually "fix" by making it mutable again.
        """
        return {key.value: item for key, item in value.items()}

    def binary_for(self, runner: RunnerName) -> str:
        """The executable for one vendor: the override, or the vendor's name."""
        return self.binary_overrides.get(runner, runner.value)
