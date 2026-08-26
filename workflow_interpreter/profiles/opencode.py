"""The opencode runner profile (`opencode 1.18.21`) — parses, but refuses to launch.

§6 says the danger default is inverted and an unsupported option is a loud
error. For opencode the unsupported option is *the bound itself*, and the
probes are unambiguous about it:

- `opencode run` has no sandbox flag, no permission flag and no deny flag. The
  only permission-shaped switch is `--auto`, which is strictly MORE permissive.
- Its resolved permission stack begins
  `{"permission":"*","action":"allow","pattern":"*"}` — from a clean scratch
  working directory, under `env -i`, with no project config in sight. It is
  IDENTICAL for the `plan` agent, so `--agent plan` is not a read-only mode.
- The stack is assembled from ambient user and project configuration that the
  wrapper does not own (it still listed allow-entries harvested from this
  machine's `$HOME` and from an unrelated repository), and setting
  `OPENCODE_CONFIG_CONTENT` to a deny block did not change it.
- A plain headless `opencode run` created a file in the working directory with
  no approval step at all.

So there is no configuration of this CLI in which the wrapper can promise that
a `writes = false` node does not write, or that a `writes = true` node does not
push — and §6's floor is exactly those two promises. `build_command` refuses,
loudly and with the reason, rather than launching a child the wrapper would
then have to describe as bounded.

Everything that does NOT depend on a bound is implemented and tested against
real captured streams: the §6 event normalization, per-step usage and cost, the
session id, the terminal envelope, and a human-pasteable resume hint. The day
opencode grows a real write bound, this file gets a `build_command` and nothing
else has to move.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from workflow_interpreter.bdio import ActivationRecord, Usage
from workflow_interpreter.profiles._base import (
    BaseProfile,
    decimal_at,
    int_at,
    mapping_at,
    optional_text_at,
    text_at,
)
from workflow_interpreter.profiles.config import RunnerName
from workflow_interpreter.profiles.errors import UnsupportedOptionError
from workflow_interpreter.supervisor.profile import (
    EventType,
    RunnerCommand,
    RunnerEvent,
    TaskSpec,
)

SESSION: Final[str] = "--session"

BOUNDABLE: Final[tuple[str, ...]] = (
    "--model provider/model",
    "--variant <effort>",
    "--agent <name>",
    "-s <session>",
    "--format json",
    "--dir <cwd>",
    "--pure",
)
"""What `opencode run` CAN be told. None of it constrains writes, shell,
network or push — which is the whole of what §6's danger default is about."""

UNBOUNDABLE_READS: Final[str] = (
    "a read-only mode: `opencode run` has no sandbox or permission flag, the "
    "resolved permission stack is `*: allow` for every agent including `plan`, "
    "and it is sourced from ambient config the wrapper does not own"
)
UNBOUNDABLE_WRITES: Final[str] = (
    "a bounded write mode: nothing confines the child to the checkout and "
    "nothing can deny `git push`, so `writes = true` would grant strictly more "
    "authority than the node declares"
)

_MSG_REFUSED: Final[str] = (
    "opencode cannot express {missing}. It CAN bound: {boundable}. "
    "Node {node} declares writes={writes}; refusing to build an invocation "
    "whose danger default cannot be inverted (§6)."
)

TYPE_TEXT: Final[str] = "text"
TYPE_TOOL_USE: Final[str] = "tool_use"
TYPE_STEP_FINISH: Final[str] = "step_finish"
TYPE_ERROR: Final[str] = "error"

KEY_TYPE: Final[str] = "type"
KEY_SESSION: Final[str] = "sessionID"
KEY_PART: Final[str] = "part"
KEY_TEXT: Final[str] = "text"
KEY_TOOL: Final[str] = "tool"
KEY_TOKENS: Final[str] = "tokens"
KEY_COST: Final[str] = "cost"
KEY_REASON: Final[str] = "reason"
KEY_INPUT: Final[str] = "input"
KEY_OUTPUT: Final[str] = "output"
KEY_ERROR: Final[str] = "error"
REASON_STOP: Final[str] = "stop"


class OpencodeProfile(BaseProfile):
    """`opencode run` as a §6 runner: everything but a launch (see module doc)."""

    runner = RunnerName.OPENCODE
    auth_env = (
        "OPENCODE_API_KEY",
        "OPENCODE_CONFIG",
        "OPENCODE_CONFIG_DIR",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
    )
    sandboxed = False
    denies_network = False
    reports_cost = True
    live_usage = True
    """`step_finish` carries per-step tokens and cost, several times per run,
    and the counts are genuinely per step rather than repeated — so a running
    total is available while the child is still going (probed)."""
    supports_resume = False
    """The vendor supports `-s <session>`; the WRAPPER cannot use it, because a
    §8.1 continuation would be exactly as unbounded as the launch it continues.
    `capabilities().resume` describes what the wrapper can do, so it is False —
    the human-facing `build_resume_hint` is still offered, because a human
    pasting it is choosing that risk knowingly."""

    def prepare(self, activation: ActivationRecord) -> str:
        """The recorded session id, or `""` — opencode assigns `ses_…` itself."""
        return activation.metadata.session_id

    def build_command(self, task: TaskSpec, session_id: str) -> RunnerCommand:
        """Refuse: §6's danger default cannot be expressed by this CLI."""
        raise UnsupportedOptionError(
            _MSG_REFUSED.format(
                missing=UNBOUNDABLE_WRITES if task.writes else UNBOUNDABLE_READS,
                boundable=", ".join(BOUNDABLE),
                node=task.node,
                writes=task.writes,
            )
        )

    def build_resume_command(
        self, session_id: str, instructions: str, task: TaskSpec
    ) -> RunnerCommand:
        """Refuse: a continuation inherits the launch's missing bound."""
        raise UnsupportedOptionError(
            _MSG_REFUSED.format(
                missing=UNBOUNDABLE_WRITES if task.writes else UNBOUNDABLE_READS,
                boundable=", ".join(BOUNDABLE),
                node=task.node,
                writes=task.writes,
            )
        )

    def build_resume_hint(self, session_id: str) -> str:
        """A human-pasteable resume line, recorded on gate beads (§6)."""
        return f"{self.binary()} {SESSION} {session_id}"

    def decode_event(self, payload: Mapping[str, object]) -> RunnerEvent | None:
        """Map one `--format json` line onto the normalized §6 event."""
        session = optional_text_at(payload, KEY_SESSION)
        kind = text_at(payload, KEY_TYPE)
        part = mapping_at(payload, KEY_PART)
        if kind == TYPE_STEP_FINISH:
            return _step_event(part, session)
        if kind == TYPE_TEXT:
            return RunnerEvent(
                type=EventType.MESSAGE, text=text_at(part, KEY_TEXT), session=session
            )
        if kind == TYPE_TOOL_USE:
            return RunnerEvent(
                type=EventType.TOOL, text=text_at(part, KEY_TOOL), session=session
            )
        if kind == TYPE_ERROR:
            return RunnerEvent(
                type=EventType.ERROR,
                text=text_at(part, KEY_ERROR) or text_at(payload, KEY_ERROR) or kind,
                session=session,
                is_error=True,
            )
        return RunnerEvent(type=EventType.MESSAGE, text=kind, session=session)


def _step_event(part: Mapping[str, object], session: str | None) -> RunnerEvent:
    """A `step_finish`: per-step usage, and `RESULT` only on the final stop.

    Several steps make up one run and each reports its own tokens, so only the
    step whose reason is `stop` is terminal; the rest are `USAGE`, which is what
    lets a token ceiling watch a run that is still going.
    """
    tokens = mapping_at(part, KEY_TOKENS)
    cost = decimal_at(part, KEY_COST)
    terminal = text_at(part, KEY_REASON) == REASON_STOP
    return RunnerEvent(
        type=EventType.RESULT if terminal else EventType.USAGE,
        text=text_at(part, KEY_REASON),
        session=session,
        usage=Usage(
            known=True,
            input_tokens=int_at(tokens, KEY_INPUT),
            output_tokens=int_at(tokens, KEY_OUTPUT),
        )
        if tokens
        else None,
        cost_usd=None if cost is None else str(cost),
    )
