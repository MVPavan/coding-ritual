"""Name → profile, over the registered crew set (§P4).

A registry rather than a dict because a profile needs three injected things and
none of them may be discovered from the process: the profile configuration, the
clock, and the host environment the child's passthrough keys are copied from.
Building them at the composition root and handing the registry out keeps every
`os.environ` read in one place — the one `rules/python/safety.md` allows.

An unknown name is a typed refusal, never a fallback to some default vendor: a
bead whose `crew_profile` the wrapper cannot resolve is a bead nothing should
dispatch.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Final

from workflow_interpreter.inspector.clock import Clock
from workflow_interpreter.inspector.profile import Profile
from workflow_interpreter.profiles.claude import ClaudeProfile
from workflow_interpreter.profiles.codex import CodexProfile
from workflow_interpreter.profiles.codex_appserver import CodexAppServerProfile
from workflow_interpreter.profiles.config import (
    CREW_PREFIX,
    CrewName,
    ProfileConfig,
)
from workflow_interpreter.profiles.errors import UnknownProfileError
from workflow_interpreter.profiles.opencode import OpencodeProfile

_MSG_UNKNOWN: Final[str] = (
    "no crew profile named {name!r}; registered profiles are {known}"
)
ProfileBuilder = Callable[[ProfileConfig, Clock, Mapping[str, str]], Profile]

BUILDERS: Final[dict[CrewName, ProfileBuilder]] = {
    CrewName.CLAUDE: ClaudeProfile,
    CrewName.CODEX: CodexProfile,
    CrewName.CODEX_APPSERVER: CodexAppServerProfile,
    CrewName.OPENCODE: OpencodeProfile,
}
"""The closed vendor set, as constructors. Each concrete class satisfies the
§6 `Profile` protocol structurally; `BaseProfile` alone does not, which is
the type checker confirming that the vendor half is not optional."""


class ProfileRegistry:
    """The one place a §6 profile is constructed."""

    def __init__(
        self,
        config: ProfileConfig,
        clock: Clock,
        host_env: Mapping[str, str],
        *,
        builders: Mapping[str, ProfileBuilder] | None = None,
    ) -> None:
        self._config = config
        self._clock = clock
        self._host_env = host_env
        self._builders: dict[str, ProfileBuilder] = {
            name.value: builder for name, builder in BUILDERS.items()
        }
        self._builders.update(builders or {})

    def profile_for(self, name: str) -> Profile:
        """The registered crew profile; unknown names raise (see module doc)."""
        builder = self._builders.get(name.removeprefix(CREW_PREFIX))
        if builder is None:
            raise UnknownProfileError(
                _MSG_UNKNOWN.format(name=name, known=", ".join(sorted(self._builders)))
            )
        return builder(self._config, self._clock, self._host_env)
