"""The §6 runner-floor Protocol the phase-4 adapters implement.

This module declares the contract and NOTHING that satisfies it: claude, codex
and opencode adapters are phase 4. What lives here is the vendor-neutral shape
the supervisor drives — plus the two rules that keep a vendor adapter from
quietly becoming the trust boundary:

- **The exec is not delegable.** `launch` receives a `ChildLauncher` the
  SUPERVISOR owns and must exec through it. The §5.2 fork barrier and the exec
  ledger are the crash-atomicity contract; a profile that forked its own child
  would not have them. `launch.py` verifies the receipt and the ledger after
  every launch, so an adapter that ignores this is caught rather than trusted.
- **The runner channels are wrapper-provided** (§6): `$WF_OUTCOME_FILE`,
  `$WF_ARTIFACT_DIR` and `$WF_EFFECTS_FILE` — plus `$WF_SCRATCH_DIR`, the
  wrapper-owned `TMPDIR` a sandboxed child would otherwise not have — live
  together under `<activation>/channels/` and are writable regardless of the
  node's `writes`, so a `writes = false` reviewer can still report. The nesting
  is load-bearing: a sandbox grants directories, so the channels must not share
  one with the wrapper's own crash records (`paths.CHANNELS_DIR`).

`usage: unknown` is legal telemetry; `max_wall` is enforced by the supervisor
(§6).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from enum import StrEnum
from pathlib import Path
from typing import Final, Protocol

from pydantic import BaseModel, ConfigDict, Field

from workflow_interpreter.bdio import ActivationRecord, ProcessHandle, Usage
from workflow_interpreter.supervisor.channels import (
    COMMITTER_NAME,
    ENV_GIT_COMMITTER_EMAIL,
    ENV_GIT_COMMITTER_NAME,
    runner_committer_email,
)
from workflow_interpreter.supervisor.paths import (
    ARTIFACT_DIR,
    CHANNELS_DIR,
    EFFECTS_FILE,
    OUTCOME_FILE,
    SCRATCH_DIR,
)

PROFILE_MODEL: Final[ConfigDict] = ConfigDict(
    frozen=True, extra="forbid", arbitrary_types_allowed=False
)

ENV_OUTCOME_FILE: Final[str] = "WF_OUTCOME_FILE"
ENV_ARTIFACT_DIR: Final[str] = "WF_ARTIFACT_DIR"
ENV_EFFECTS_FILE: Final[str] = "WF_EFFECTS_FILE"
ENV_SCRATCH_DIR: Final[str] = "WF_SCRATCH_DIR"


class EventType(StrEnum):
    """The normalized event classes every runner's stream maps onto (§6)."""

    MESSAGE = "message"
    TOOL = "tool"
    USAGE = "usage"
    RESULT = "result"
    ERROR = "error"


class RunnerChannels(BaseModel):
    """The §6 wrapper-provided channels for one activation.

    All of them live under ONE directory (`paths.CHANNELS_DIR`), which is what
    lets a directory-granularity sandbox grant exactly the runner's channels and
    nothing of the wrapper's own crash-atomicity records.
    """

    model_config = PROFILE_MODEL

    outcome_file: str
    artifact_dir: str
    effects_file: str
    scratch_dir: str = ""
    """`$WF_SCRATCH_DIR`, the fourth channel — a `writes = true` node's only
    writable temp space once the sandbox stops granting `/tmp` (`paths.SCRATCH_DIR`).
    Empty only for a caller that built channels by hand; `channels_for` always
    supplies it, and an empty one is simply not exported."""
    log_path: str
    activation_id: str = ""
    """Empty only where a caller built channels without one; production always
    supplies it (`Dispatcher._launch`). With no id there is no §7.4 committer
    identity to stamp, so any in-repo commit the runner makes is unattributable
    and `pin_artifact` refuses it — the fail-closed direction."""

    def env(self) -> dict[str, str]:
        """The child's environment: the three §6 channels, plus §7.4 authorship.

        `GIT_COMMITTER_*` is not a channel and is here anyway, because it is set
        the same way and for the same reason — it is the wrapper telling the
        child something about the run rather than reading something back. §7.4
        attribution used to be path containment alone, so a dead runner's
        manifest naming a path the HUMAN later committed made the human's commit
        this activation's artifact, and an artifact pin is the §12 authority for
        the next reset to move HEAD off it (probed, Opus#21). The committer is
        the missing authorship half.

        `GIT_AUTHOR_*` is deliberately untouched: the author is whoever the
        runner says wrote the change, and overwriting that would destroy
        information rather than add any.
        """
        channels = {
            ENV_OUTCOME_FILE: self.outcome_file,
            ENV_ARTIFACT_DIR: self.artifact_dir,
            ENV_EFFECTS_FILE: self.effects_file,
        }
        if self.scratch_dir:
            channels[ENV_SCRATCH_DIR] = self.scratch_dir
        if not self.activation_id:
            return channels
        return {
            **channels,
            ENV_GIT_COMMITTER_NAME: COMMITTER_NAME,
            ENV_GIT_COMMITTER_EMAIL: runner_committer_email(self.activation_id),
        }


class TaskSpec(BaseModel):
    """Everything a profile needs to build one invocation (§6 `build_command`).

    Carries no bd handle and no store: a runner holds `bd --readonly` or no bd
    at all (§0.2), and the object that describes its task must not be a way
    around that.
    """

    model_config = PROFILE_MODEL

    root_id: str
    activation_id: str
    node: str
    model: str
    writes: bool
    allowed_paths: tuple[str, ...] = ()
    cwd: str
    channels: RunnerChannels
    brief: str = ""
    token_budget: int | None = None


class RunnerCommand(BaseModel):
    """A built invocation: argv, environment and working directory.

    `argv` is executed WITHOUT a shell, exactly like the §2 rule-6 `verify`
    contract — no expansion, no metacharacters, no interpreter prefix.
    """

    model_config = PROFILE_MODEL

    argv: tuple[str, ...] = Field(min_length=1)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: str
    log_path: str
    session_id: str


class TerminalEnvelope(BaseModel):
    """`collect_terminal_envelope(handle) -> {usage, session_id, duration}` (§6).

    §6 sketches a `marker` here too and this deliberately does not carry one.
    Nothing ever consumed it: §7.2 makes the CLAIM the foreman wrapper's to
    parse, and `exit.py::_collect` re-reads `$WF_OUTCOME_FILE` itself with the
    node's declared outcome set — precisely so a vendor adapter's parse of a
    vendor's stream cannot become a second, unvalidated way for a runner to name
    its own outcome. Reporting one anyway meant a profile deriving the reserved
    channel's path by convention from `handle.log_path`, which is the coupling
    `ProcessHandle` should have carried explicitly and did not.
    """

    model_config = PROFILE_MODEL

    usage: Usage = Usage(known=False)
    session_id: str | None = None
    duration_s: float | None = None


class RunnerEvent(BaseModel):
    """One normalized event of a runner's machine stream (§6 `parse_output`)."""

    model_config = PROFILE_MODEL

    type: EventType
    text: str = ""
    session: str | None = None
    usage: Usage | None = None
    cost_usd: str | None = None
    is_error: bool = False


class ChildLauncher(Protocol):
    """The supervisor's fork-barrier exec, handed to a profile at launch (§5.2)."""

    def __call__(
        self, command: RunnerCommand
    ) -> ProcessHandle: ...  # pragma: no cover - protocol


class Profile(Protocol):
    """The §6 runner floor. One invocation contract, three vendors (phase 4)."""

    def name(self) -> str:
        """The profile's stable identifier (`runner = "profile:<name>"`)."""
        ...  # pragma: no cover - protocol

    def prepare(self, activation: ActivationRecord) -> str:
        """Pre-assign the session id (§5.2) — never discovered from output."""
        ...  # pragma: no cover - protocol

    def build_command(self, task: TaskSpec, session_id: str) -> RunnerCommand:
        """Build the invocation; danger defaults inverted unless `writes` (§6)."""
        ...  # pragma: no cover - protocol

    def launch(self, command: RunnerCommand, launcher: ChildLauncher) -> ProcessHandle:
        """Exec THROUGH the supervisor's launcher; the barrier is not optional."""
        ...  # pragma: no cover - protocol

    def collect_terminal_envelope(self, handle: ProcessHandle) -> TerminalEnvelope:
        """The runner's terminal facts; the outcome CLAIM is §7's, not a profile's."""
        ...  # pragma: no cover - protocol

    def build_resume_command(
        self, session_id: str, instructions: str, task: TaskSpec
    ) -> RunnerCommand:
        """The steer continuation's invocation (§8.1), bounded by `task`.

        The `TaskSpec` is not optional and used to be absent. A `RunnerCommand`
        needs a working directory and the §6 channels; with neither in the
        signature the adapters remembered the launch they had built, which is
        per-object state on an object the registry mints fresh per lookup — so a
        real steer either refused outright or, on a reused profile, resumed
        inside the PREVIOUS activation's channels. Passing the continuation's
        own task removes the hidden state and the wrong answer with it.
        """
        ...  # pragma: no cover - protocol

    def build_resume_hint(self, session_id: str) -> str:
        """A human-pasteable resume line, recorded on gate beads (§6)."""
        ...  # pragma: no cover - protocol

    def parse_output(self, stream: Iterable[str]) -> Iterator[RunnerEvent]:
        """Normalize the runner's machine event stream (§6)."""
        ...  # pragma: no cover - protocol


def channels_for(
    activation_dir: Path, log_path: Path, activation_id: str = ""
) -> RunnerChannels:
    """The §6 channels for an activation, rooted in `<activation>/channels/`.

    The nesting is the whole point and is stated in exactly two places — here
    and `WrapperPaths.channels_dir` — because a producer and a reader that
    render a layout separately render two layouts eventually.

    `activation_id` is what stamps the §7.4 committer identity onto the child;
    omitting it produces channels with no identity, which makes any in-repo
    commit unattributable rather than misattributed.
    """
    channels_dir = activation_dir / CHANNELS_DIR
    return RunnerChannels(
        outcome_file=str(channels_dir / OUTCOME_FILE),
        artifact_dir=str(channels_dir / ARTIFACT_DIR),
        effects_file=str(channels_dir / EFFECTS_FILE),
        scratch_dir=str(channels_dir / SCRATCH_DIR),
        log_path=str(log_path),
        activation_id=activation_id,
    )
