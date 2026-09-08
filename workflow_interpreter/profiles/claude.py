"""The claude runner profile (`claude 2.1.227`), built from live probes.

Every flag below was run before it was written down (`scratchpad/probes/
phase4-cli-probes.md`). Four probe results shape this file:

- `--output-format stream-json` REQUIRES `--verbose` under `--print`; without
  it the CLI exits 1 before doing anything.
- `Write(path)` permission rules are inert. Claude matches file permissions on
  `Edit(path)` rules ONLY, and an `Edit` rule covers every file-editing tool
  including `Write`. Two probes denied the wrapper's own outcome channel before
  this was found.
- An absolute path in a rule is `//` + the path WITHOUT its leading slash
  (`Edit(//tmp/x)` is `/tmp/x`). One leading slash anchors to the settings
  source directory instead — silently, and somewhere else.
- `--tools` restricts the built-in set but explicitly does NOT affect MCP tools,
  and the ambient config had four MCP servers. `--strict-mcp-config` with no
  `--mcp-config` reduces `mcp_servers` to `[]` (probed).

The danger default is therefore expressed twice over: `--tools` decides which
tools EXIST, and `dontAsk` plus `Edit(...)` allow-rules decide which paths they
may touch. `writes = false` keeps the checkout as cwd and still refuses to write
it, while the three §6 channels stay writable — probed end to end.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Final

from workflow_interpreter.bdio import ActivationRecord, Usage
from workflow_interpreter.profiles._base import (
    BaseProfile,
    decimal_at,
    grant_dirs,
    int_at,
    mapping_at,
    optional_text_at,
    require_absolute,
    text_at,
)
from workflow_interpreter.profiles.config import MODEL_VENDOR_DEFAULT, RunnerName
from workflow_interpreter.profiles.errors import TaskRefused
from workflow_interpreter.supervisor.profile import (
    EventType,
    RunnerCommand,
    RunnerEvent,
    TaskSpec,
)

PRINT: Final[str] = "-p"
OUTPUT_FORMAT: Final[tuple[str, str]] = ("--output-format", "stream-json")
VERBOSE: Final[str] = "--verbose"
SESSION_ID: Final[str] = "--session-id"
RESUME: Final[str] = "--resume"
MODEL: Final[str] = "--model"
EFFORT: Final[str] = "--effort"
FALLBACK_MODEL: Final[str] = "--fallback-model"
PERMISSION_MODE: Final[tuple[str, str]] = ("--permission-mode", "dontAsk")
SETTING_SOURCES: Final[tuple[str, str]] = ("--setting-sources", "")
STRICT_MCP: Final[str] = "--strict-mcp-config"
TOOLS: Final[str] = "--tools"
ALLOWED_TOOLS: Final[str] = "--allowedTools"
DISALLOWED_TOOLS: Final[str] = "--disallowedTools"

READ_TOOLS: Final[tuple[str, ...]] = ("Read", "Glob", "Grep")
READ_ONLY_TOOLS: Final[tuple[str, ...]] = (*READ_TOOLS, "Write")
"""`Write` is in the `writes = false` set on purpose: §6 makes the three runner
channels writable regardless of `writes`, so a reviewer that cannot write has
no way to report and every review would grade `fail_code` (zero markers). The
allow-rules below are what keep that `Write` inside the wrapper directory."""
WRITE_TOOLS: Final[tuple[str, ...]] = (*READ_TOOLS, "Edit", "Write", "Bash")

GIT_DIR_SEGMENT: Final[str] = ".git"


def _git_dir_denials(cwd: str) -> list[str]:
    """Deny-rules keeping a `writes = true` runner out of the checkout's `.git`.

    `.git` sits inside the tree `writes = true` grants, and `.git/config` and
    `.git/hooks/` name PROGRAMS the wrapper's own git would then run as the
    wrapper — outside the bound the runner was given (`gitio.HARDENING` and
    `gitio.ENV_HARDENING` are the other half, for the vendors whose grant is a
    whole directory and cannot exclude anything). Deny beats allow, so these
    outrank the tree rule.

    TWO rules, because `.git` is not always a directory. In §5.4 worktree mode
    the checkout is a `git worktree`, whose `.git` is a FILE holding
    `gitdir: <path>` — and a glob needs a `.git/` path SEGMENT to match, so the
    `/**` form leaves the file itself editable. A runner that repoints it at a
    gitdir inside its own grant owns the config of every later
    `git -C <worktree>` the wrapper runs (Opus r2 #20). The file form is the
    rule that covers it; the tree form still covers the in-repo band, where
    `.git` really is a directory.
    """
    return [
        f"Edit(/{cwd}/{GIT_DIR_SEGMENT})",
        f"Edit(/{cwd}/{GIT_DIR_SEGMENT}/**)",
    ]


PUSH_DENIALS: Final[tuple[str, ...]] = (
    "Bash(git push)",
    "Bash(git push:*)",
    "Bash(git:* push:*)",
)
"""No profile ever pushes (§6). Deny beats allow in every permission mode, so
these outrank the bare `Bash` allow — probed against `git push --dry-run origin
main`, which was refused. It is defence in depth, not the policy: a determined
runner can phrase around a prefix rule, and the supervisor's `gitio` closed
subcommand set is the backstop."""

READ_ONLY_DENIALS: Final[tuple[str, ...]] = (
    "Bash",
    "NotebookEdit",
    "Task",
    "WebFetch",
    "WebSearch",
)
WRITE_DENIALS: Final[tuple[str, ...]] = (
    *PUSH_DENIALS,
    "NotebookEdit",
    "Task",
    "WebFetch",
    "WebSearch",
)
# GOTCHA: never put a bare `Edit` in either deny list. `Edit(path)` rules are
# the engine for ALL file-editing tools, so denying the tool by name denies
# every Write as well — including the outcome marker the wrapper requires.

TYPE_SYSTEM: Final[str] = "system"
TYPE_ASSISTANT: Final[str] = "assistant"
TYPE_USER: Final[str] = "user"
TYPE_RESULT: Final[str] = "result"
KEY_TYPE: Final[str] = "type"
KEY_SUBTYPE: Final[str] = "subtype"
KEY_SESSION: Final[str] = "session_id"
KEY_MESSAGE: Final[str] = "message"
KEY_CONTENT: Final[str] = "content"
KEY_USAGE: Final[str] = "usage"
KEY_COST: Final[str] = "total_cost_usd"
KEY_IS_ERROR: Final[str] = "is_error"
KEY_TEXT: Final[str] = "text"
KEY_INPUT_TOKENS: Final[str] = "input_tokens"
KEY_CACHE_READ_INPUT_TOKENS: Final[str] = "cache_read_input_tokens"
KEY_CACHE_CREATION_INPUT_TOKENS: Final[str] = "cache_creation_input_tokens"
KEY_OUTPUT_TOKENS: Final[str] = "output_tokens"
BLOCK_TEXT: Final[str] = "text"
BLOCK_TOOL_USE: Final[str] = "tool_use"
BLOCK_TOOL_RESULT: Final[str] = "tool_result"

_MSG_NOT_A_UUID: Final[str] = (
    "claude: --session-id requires a UUID and the activation carries {value!r}; "
    "claude is the one vendor whose session id §5.2 can pre-assign, so a "
    "non-UUID here means the mint did not use `prepare()`"
)


class ClaudeProfile(BaseProfile):
    """`claude -p` as a §6 runner: bounded by permission rules, not a sandbox."""

    runner = RunnerName.CLAUDE
    auth_env = (
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_BASE_URL",
        "CLAUDE_CODE_OAUTH_TOKEN",
    )
    # -- §5.2 session identity -------------------------------------------

    def prepare(self, activation: ActivationRecord) -> str:
        """Pre-assign the session id — minted here, never discovered (§5.2).

        Idempotent: an activation that already carries one keeps it, so a
        re-`prepare` after a crash cannot rename a session that may already have
        a running child.
        """
        return activation.metadata.session_id or str(uuid.uuid4())

    # -- §6 command construction -----------------------------------------

    def build_command(self, task: TaskSpec, session_id: str) -> RunnerCommand:
        """The headless one-shot, with the danger default inverted (§6)."""
        argv = [
            self.binary(),
            PRINT,
            self.require_brief(task),
            SESSION_ID,
            self._uuid(session_id),
            *self._invocation_flags(task),
        ]
        return self.command(argv, task, session_id)

    def build_resume_command(
        self, session_id: str, instructions: str, task: TaskSpec
    ) -> RunnerCommand:
        """The §8.1 continuation: the continuation's own bounds, `--resume`."""
        argv = [
            self.binary(),
            PRINT,
            instructions,
            RESUME,
            self._uuid(session_id),
            *self._invocation_flags(task),
        ]
        return self.command(argv, task, session_id)

    def build_resume_hint(self, session_id: str) -> str:
        """A human-pasteable resume line, recorded on gate beads (§6)."""
        return f"{self.binary()} {RESUME} {session_id}"

    def _invocation_flags(self, task: TaskSpec) -> list[str]:
        """Everything both invocations share: output shape, model, bounds."""
        flags = [
            *OUTPUT_FORMAT,
            VERBOSE,
            *SETTING_SOURCES,
            STRICT_MCP,
            *PERMISSION_MODE,
        ]
        if task.model and task.model != MODEL_VENDOR_DEFAULT:
            flags += [MODEL, task.model]
        if task.effort:
            flags += [EFFORT, task.effort]
        if task.fallback_models:
            flags += [FALLBACK_MODEL, ",".join(task.fallback_models)]
        return [*flags, *self._bounds(task)]

    def _bounds(self, task: TaskSpec) -> list[str]:
        """The §6 danger default, as three flags.

        `--tools` decides what EXISTS; the allow-rules decide what those tools
        may touch; the deny-rules outrank both. `writes = false` keeps the
        checkout as the working directory — claude bounds writes by path, so a
        readable-but-unwritable checkout needs no second directory.

        `writes = true` grants the node's `allowed_paths` and nothing wider
        (`_grant_rules`); the §2 mount bound underneath grants the same set.
        """
        channels = _channel_rules(task)
        if not task.writes:
            return [
                TOOLS,
                *READ_ONLY_TOOLS,
                ALLOWED_TOOLS,
                *READ_TOOLS,
                *channels,
                DISALLOWED_TOOLS,
                *READ_ONLY_DENIALS,
            ]
        cwd = require_absolute(self.runner, "task cwd", task.cwd)
        return [
            TOOLS,
            *WRITE_TOOLS,
            ALLOWED_TOOLS,
            *READ_TOOLS,
            "Bash",
            *_grant_rules(task),
            *channels,
            DISALLOWED_TOOLS,
            *_git_dir_denials(cwd),
            *WRITE_DENIALS,
        ]

    def _uuid(self, session_id: str) -> str:
        """Refuse a session id `--session-id` / `--resume` cannot carry."""
        try:
            uuid.UUID(session_id)
        except ValueError as error:
            raise TaskRefused(_MSG_NOT_A_UUID.format(value=session_id)) from error
        return session_id

    # -- §6 stream normalization -----------------------------------------

    def decode_event(self, payload: Mapping[str, object]) -> RunnerEvent | None:
        """Map one `stream-json` line onto the normalized §6 event."""
        session = optional_text_at(payload, KEY_SESSION)
        kind = text_at(payload, KEY_TYPE)
        if kind == TYPE_RESULT:
            return _result_event(payload, session)
        if kind in (TYPE_ASSISTANT, TYPE_USER):
            return _message_event(payload, session)
        if kind == TYPE_SYSTEM:
            return RunnerEvent(
                type=EventType.MESSAGE,
                text=text_at(payload, KEY_SUBTYPE),
                session=session,
            )
        # Parseable, and a real vendor line the wrapper has no opinion about
        # (`stream_event`, `rate_limit_event`, whatever a later release adds).
        # Recorded as a message rather than an error: it is not a defect.
        return RunnerEvent(type=EventType.MESSAGE, text=kind, session=session)


def _result_event(payload: Mapping[str, object], session: str | None) -> RunnerEvent:
    """The terminal line: the run's cumulative usage, cost and error flag."""
    usage = mapping_at(payload, KEY_USAGE)
    cost = decimal_at(payload, KEY_COST)
    return RunnerEvent(
        type=EventType.RESULT,
        text=text_at(payload, "result"),
        session=session,
        usage=Usage(
            known=True,
            input_tokens=int_at(usage, KEY_INPUT_TOKENS),
            cache_read_input_tokens=int_at(usage, KEY_CACHE_READ_INPUT_TOKENS),
            cache_creation_input_tokens=int_at(usage, KEY_CACHE_CREATION_INPUT_TOKENS),
            output_tokens=int_at(usage, KEY_OUTPUT_TOKENS),
        )
        if usage
        else None,
        cost_usd=None if cost is None else str(cost),
        is_error=payload.get(KEY_IS_ERROR) is True,
    )


def _message_event(payload: Mapping[str, object], session: str | None) -> RunnerEvent:
    """An `assistant` / `user` turn: a tool step when it carries tool blocks.

    No usage is attached even though `message.usage` is present: its counts
    repeat across content blocks and do not represent per-event telemetry.
    """
    content = mapping_at(payload, KEY_MESSAGE).get(KEY_CONTENT)
    blocks: Sequence[object] = content if isinstance(content, list) else ()
    texts: list[str] = []
    tools: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = text_at(block, KEY_TYPE)
        if block_type == BLOCK_TEXT:
            texts.append(text_at(block, KEY_TEXT))
        elif block_type == BLOCK_TOOL_USE:
            tools.append(text_at(block, "name"))
        elif block_type == BLOCK_TOOL_RESULT:
            tools.append(text_at(block, "tool_use_id"))
    if tools:
        return RunnerEvent(type=EventType.TOOL, text=" ".join(tools), session=session)
    return RunnerEvent(type=EventType.MESSAGE, text="\n".join(texts), session=session)


def _grant_rules(task: TaskSpec) -> list[str]:
    """One allow-rule per `allowed_paths` grant — never the checkout as a tree.

    Phase 2 of `docs/plans/allowed-paths-enforcement.md`: the §2 mount bound is
    the real containment, and this states the SAME grant set in claude's own
    permission engine, so a write outside it arrives as a tool refusal in the
    transcript (and in `permission_denials`) instead of as a mid-command
    `Read-only file system` from a bind the model cannot see.

    `Edit` is the only tool named because `Edit(path)` rules govern every
    file-editing tool including `Write`, and a `Write(path)` rule matches
    nothing (module docstring, probed). The directories come from `grant_dirs`,
    which is the mount bound's own mapping rather than a second one.

    A `writes = true` node that declares no grant therefore gets no repository
    path at all, which is exactly what its mount plan gives it.
    """
    return [_tree_rule(path) for path in grant_dirs(RunnerName.CLAUDE, task)]


def _tree_rule(directory: str) -> str:
    """An `Edit` allow-rule covering a whole directory tree."""
    return f"Edit(/{directory}/**)"


def _file_rule(path: str) -> str:
    """An `Edit` allow-rule covering exactly one file."""
    return f"Edit(/{path})"


def _channel_rules(task: TaskSpec) -> list[str]:
    """The §6 channels, writable regardless of `writes`.

    Claude bounds by exact path rather than by directory, so the rules name the
    channels themselves and never the activation directory that holds them —
    the wrapper's receipt, ledger, exit file and completion evidence are not
    reachable through any of these even by spelling.
    """
    channels = task.channels
    rules = [
        _tree_rule(
            require_absolute(RunnerName.CLAUDE, "artifact dir", channels.artifact_dir)
        ),
        _file_rule(
            require_absolute(RunnerName.CLAUDE, "outcome file", channels.outcome_file)
        ),
        _file_rule(
            require_absolute(RunnerName.CLAUDE, "effects file", channels.effects_file)
        ),
    ]
    if channels.scratch_dir:
        rules.append(
            _tree_rule(
                require_absolute(RunnerName.CLAUDE, "scratch dir", channels.scratch_dir)
            )
        )
    return rules
