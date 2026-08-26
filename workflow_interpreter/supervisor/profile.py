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
- **The three runner channels are wrapper-provided** (§6): `$WF_OUTCOME_FILE`,
  `$WF_ARTIFACT_DIR` and `$WF_EFFECTS_FILE` live in the wrapper directory and
  are writable regardless of the node's `writes`, so a `writes = false`
  reviewer can still report.

`usage: unknown` is legal and disables only the best-effort token ceiling —
`max_wall` always holds (§6).
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
from workflow_interpreter.supervisor.models import OutcomeMarker, TerminationProof
from workflow_interpreter.supervisor.paths import (
    ARTIFACT_DIR,
    EFFECTS_FILE,
    OUTCOME_FILE,
)

PROFILE_MODEL: Final[ConfigDict] = ConfigDict(
    frozen=True, extra="forbid", arbitrary_types_allowed=False
)

ENV_OUTCOME_FILE: Final[str] = "WF_OUTCOME_FILE"
ENV_ARTIFACT_DIR: Final[str] = "WF_ARTIFACT_DIR"
ENV_EFFECTS_FILE: Final[str] = "WF_EFFECTS_FILE"


class ProcessStatus(StrEnum):
    """What `Profile.inspect` reports about a handle (§6)."""

    ALIVE = "alive"
    DEAD = "dead"


class EventType(StrEnum):
    """The normalized event classes every runner's stream maps onto (§6)."""

    MESSAGE = "message"
    TOOL = "tool"
    USAGE = "usage"
    RESULT = "result"
    ERROR = "error"


class RunnerChannels(BaseModel):
    """The §6 wrapper-provided channels for one activation."""

    model_config = PROFILE_MODEL

    outcome_file: str
    artifact_dir: str
    effects_file: str
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


class InspectResult(BaseModel):
    """`Profile.inspect(handle) -> alive | dead | exit_code` (§6)."""

    model_config = PROFILE_MODEL

    status: ProcessStatus
    exit_code: int | None = None


class TerminalEnvelope(BaseModel):
    """`collect_terminal_envelope(handle) -> {marker, usage, session_id, duration}`."""

    model_config = PROFILE_MODEL

    marker: OutcomeMarker | None = None
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


class Capabilities(BaseModel):
    """What a runner supports; unsupported options are a loud error (§6)."""

    model_config = PROFILE_MODEL

    live_usage: bool = False
    resume: bool = False


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

    def inspect(self, handle: ProcessHandle) -> InspectResult:
        """Alive, dead, or dead with an exit code."""
        ...  # pragma: no cover - protocol

    def collect_terminal_envelope(self, handle: ProcessHandle) -> TerminalEnvelope:
        """Read the runner's terminal facts from its own channels."""
        ...  # pragma: no cover - protocol

    def terminate(self, handle: ProcessHandle) -> TerminationProof:
        """TERM → bounded wait → KILL, with proof of death (§8.1)."""
        ...  # pragma: no cover - protocol

    def build_resume_command(self, session_id: str, instructions: str) -> RunnerCommand:
        """The steer continuation's invocation (§8.1)."""
        ...  # pragma: no cover - protocol

    def build_resume_hint(self, session_id: str) -> str:
        """A human-pasteable resume line, recorded on gate beads (§6)."""
        ...  # pragma: no cover - protocol

    def parse_output(self, stream: Iterable[str]) -> Iterator[RunnerEvent]:
        """Normalize the runner's machine event stream (§6)."""
        ...  # pragma: no cover - protocol

    def capabilities(self) -> Capabilities:
        """Declared capabilities; `live_usage = False` disables only the token
        ceiling (§6)."""
        ...  # pragma: no cover - protocol


def channels_for(
    activation_dir: Path, log_path: Path, activation_id: str = ""
) -> RunnerChannels:
    """The three §6 channels for an activation, rooted in its wrapper dir.

    `activation_id` is what stamps the §7.4 committer identity onto the child;
    omitting it produces channels with no identity, which makes any in-repo
    commit unattributable rather than misattributed.
    """
    return RunnerChannels(
        outcome_file=str(activation_dir / OUTCOME_FILE),
        artifact_dir=str(activation_dir / ARTIFACT_DIR),
        effects_file=str(activation_dir / EFFECTS_FILE),
        log_path=str(log_path),
        activation_id=activation_id,
    )
