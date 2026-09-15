"""Closed, versioned execution authority shared across engine layers."""

from enum import StrEnum
from typing import Final, Literal

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
MSG_KNOWN_RUNNER: Final[str] = (
    "named execution policy requires a known runner: {runner!r}"
)
MSG_PINNED_POLICY: Final[str] = "named execution_profile requires a pinned policy"


class RunnerName(StrEnum):
    """Registered vendor identities, each with an explicit network capability."""

    CLAUDE = "claude"
    CODEX = "codex"
    OPENCODE = "opencode"

    @property
    def tool_network(self) -> ToolNetwork:
        """Return the declared fact; additions cannot inherit an implicit fallback."""
        return {
            RunnerName.CLAUDE: ToolNetwork.NOT_ENFORCED,
            RunnerName.CODEX: ToolNetwork.DENIED,
            RunnerName.OPENCODE: ToolNetwork.NOT_ENFORCED,
        }[self]

    @classmethod
    def from_profile(cls, value: str) -> "RunnerName":
        """Validate the bare or profile-prefixed spelling at a boundary."""
        try:
            return cls(value.removeprefix(RUNNER_PREFIX))
        except ValueError as error:
            raise ValueError(MSG_KNOWN_RUNNER.format(runner=value)) from error


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


def policy_for(name: ExecutionProfileName, runner: str) -> ExecutionPolicy:
    """Resolve current named authority and the runner's network enforcement fact."""
    return ExecutionPolicy(
        name=name,
        writes=name is ExecutionProfileName.WRITER,
        tool_network=RunnerName.from_profile(runner).tool_network,
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
