"""Name → profile, over the closed vendor set (§P4).

A registry rather than a dict because a profile needs three injected things and
none of them may be discovered from the process: the profile configuration, the
clock, and the host environment the child's passthrough keys are copied from.
Building them at the composition root and handing the registry out keeps every
`os.environ` read in one place — the one `rules/python/safety.md` allows.

An unknown name is a typed refusal, never a fallback to some default vendor: a
bead whose `runner_profile` the wrapper cannot resolve is a bead nothing should
dispatch.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Final

from workflow_interpreter.profiles.claude import ClaudeProfile
from workflow_interpreter.profiles.codex import CodexProfile
from workflow_interpreter.profiles.config import (
    RUNNER_PREFIX,
    ProfileConfig,
    RunnerName,
)
from workflow_interpreter.profiles.errors import UnknownProfileError
from workflow_interpreter.profiles.opencode import OpencodeProfile
from workflow_interpreter.supervisor.clock import Clock
from workflow_interpreter.supervisor.profile import Profile

_MSG_UNKNOWN: Final[str] = "no runner profile named {name!r}; the closed set is {known}"

ProfileBuilder = Callable[[ProfileConfig, Clock, Mapping[str, str]], Profile]

BUILDERS: Final[dict[RunnerName, ProfileBuilder]] = {
    RunnerName.CLAUDE: ClaudeProfile,
    RunnerName.CODEX: CodexProfile,
    RunnerName.OPENCODE: OpencodeProfile,
}
"""The closed vendor set, as constructors. Each concrete class satisfies the
§6 `Profile` protocol structurally; `BaseProfile` alone does not, which is
the type checker confirming that the vendor half is not optional."""


def runner_name(name: str) -> RunnerName:
    """Resolve a runner name, accepting the §6 `profile:<name>` spelling.

    §6 records a runner as `runner = "profile:<name>"`, so a bead's
    `runner_profile` is looked up as it was written rather than re-derived by
    every caller.
    """
    bare = name.removeprefix(RUNNER_PREFIX)
    try:
        return RunnerName(bare)
    except ValueError as error:
        raise UnknownProfileError(
            _MSG_UNKNOWN.format(
                name=name, known=", ".join(sorted(item.value for item in RunnerName))
            )
        ) from error


class ProfileRegistry:
    """The one place a §6 profile is constructed."""

    def __init__(
        self,
        config: ProfileConfig,
        clock: Clock,
        host_env: Mapping[str, str],
    ) -> None:
        self._config = config
        self._clock = clock
        self._host_env = host_env

    def profile_for(self, name: str) -> Profile:
        """The profile for one vendor name; unknown names raise (see module doc)."""
        return BUILDERS[runner_name(name)](self._config, self._clock, self._host_env)
