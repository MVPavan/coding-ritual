"""Closed, versioned execution authority shared across engine layers."""

from enum import StrEnum
from typing import Final, Literal, Protocol

from pydantic import BaseModel, ConfigDict, model_validator

EXECUTION_POLICY_KEY: Final[str] = "node.{node}.execution_policy"
MSG_PROFILE_WRITES: Final[str] = "execution_profile forbids authored or override writes"
MSG_REVIEWER_GRANTS: Final[str] = "reviewer execution_profile forbids allowed_paths"
MSG_PROFILE_KIND: Final[str] = "execution_profile is only valid on task nodes"
MSG_POLICY_MISMATCH: Final[str] = "execution policy disagrees with the named profile"
MSG_NAMED_SANDBOX: Final[str] = "named execution_profile requires the outer sandbox"
MSG_GRANTS_MISSING: Final[str] = "named execution_profile requires resolved grants"
MSG_PRIVATE_GRANTS: Final[str] = (
    "execution channels, scratch, or cache escape their private roots"
)


class ExecutionProfileName(StrEnum):
    """Model activation authority; host verification is not a model profile."""

    WRITER = "writer"
    REVIEWER = "reviewer"


class ToolNetwork(StrEnum):
    """Observed enforcement fact, never a network admission requirement."""

    DENIED = "denied"
    NOT_ENFORCED = "not_enforced"


RUNNER_PREFIX: Final[str] = "profile:"
MSG_UNREGISTERED_RUNNER: Final[str] = (
    "named execution policy requires a registered runner; unregistered runner: {runner!r}"
)
MSG_PINNED_POLICY: Final[str] = "named execution_profile requires a pinned policy"


class RunnerName(StrEnum):
    """Built-in vendor identities; registration and capabilities live on profiles."""

    CLAUDE = "claude"
    CODEX = "codex"
    OPENCODE = "opencode"


class UnregisteredRunnerError(Exception):
    """The selected runner is absent from the injected profile registry."""


class NetworkProfile(Protocol):
    """The runner capability needed by durable execution policy admission."""

    @property
    def tool_network(self) -> ToolNetwork:
        """The enforcement fact declared by this registered runner."""
        ...


class ExecutionRegistry(Protocol):
    """Resolve registered runners without depending on concrete adapters."""

    def profile_for(self, name: str) -> NetworkProfile:
        """Resolve a profile or raise UnregisteredRunnerError."""
        ...


def tool_network_for(runner: str, profiles: ExecutionRegistry | None) -> ToolNetwork:
    """Read the registry capability; never infer a fact from a vendor spelling."""
    if not runner or profiles is None:
        raise UnregisteredRunnerError(MSG_UNREGISTERED_RUNNER.format(runner=runner))
    try:
        return profiles.profile_for(runner).tool_network
    except UnregisteredRunnerError as error:
        raise UnregisteredRunnerError(
            MSG_UNREGISTERED_RUNNER.format(runner=runner)
        ) from error


class ExecutionPolicy(BaseModel):
    """The immutable meaning pinned when a named node enters an instance."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal[1] = 1
    name: ExecutionProfileName
    writes: bool
    tool_network: ToolNetwork

    @model_validator(mode="after")
    def _consistent_authority(self) -> "ExecutionPolicy":
        """Refuse policy data that contradicts the closed profile vocabulary."""
        if self.writes != (self.name is ExecutionProfileName.WRITER):
            raise ValueError(MSG_POLICY_MISMATCH)
        return self


def policy_for(
    name: ExecutionProfileName, tool_network: ToolNetwork
) -> ExecutionPolicy:
    """Resolve current named authority and the runner's network enforcement fact."""
    return ExecutionPolicy(
        name=name,
        writes=name is ExecutionProfileName.WRITER,
        tool_network=tool_network,
    )


class ExecutionGrants(BaseModel):
    """Resolved paths shared by outer mounts and vendor permission translations."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    policy: ExecutionPolicy
    checkout_read_root: str
    process_cwd: str
    read_only_roots: tuple[str, ...]
    checkout_write_dirs: tuple[str, ...]
    git_dirs: tuple[str, ...]
    channels: str
    scratch: str
    private_cache: str
    read_only_pins: tuple[str, ...]

    @property
    def writable_directories(self) -> tuple[str, ...]:
        """The entire explicit directory grant, excluding readonly pins."""
        return tuple(
            dict.fromkeys(
                (
                    *self.checkout_write_dirs,
                    *self.git_dirs,
                    self.channels,
                    self.scratch,
                    self.private_cache,
                )
            )
        )


MSG_CODEX_IN_REPO: Final[str] = (
    "codex: node {node!r} writes and its checkout {checkout} is an in-repo "
    "band checkout, which this runner cannot be bounded for. `git add` creates "
    "`index.lock` directly inside `<C>/.git`, and that same directory holds "
    "`config`, `hooks/` and `info/` — the surface that names PROGRAMS the "
    "wrapper's own git later executes. `sandbox_workspace_write` grants whole "
    "directories and has no key that takes a subdirectory back, so granting the "
    "one would grant the others. Run this node in §5.4 worktree isolation, or "
    "bind the role to a runner whose permission layer is path-exact."
)
