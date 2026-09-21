"""The codex crew profile (`codex-cli 0.148.0`), built from live probes.

Codex is the only one of the three with an OS-level sandbox, and the only one
whose flags differ between launching and resuming. Both facts came out of the
probes and both shape this file:

- **`codex exec resume` accepts neither `-s/--sandbox` nor `-C/--cd`.** They
  exist on `codex exec` and are simply not in the resume subcommand. So the
  sandbox travels as `-c` config overrides, which BOTH subcommands accept, and
  the working root travels as the process working directory, which both
  inherit. The launch therefore passes `-C` and the identical `-c` overrides,
  so the two invocations describe the same box by two routes that cannot drift.
- **`-s read-only` blocks EVERY write, including into `--add-dir`** (probed:
  the refusal is `patch rejected: writing is blocked by read-only sandbox`, on
  stderr, with exit code 0 and a cheerful `"done"` on stdout). §6 requires the
  three crew channels to be writable REGARDLESS of `writes`, so a
  `writes = false` codex node cannot use `read-only` at all: it could never
  write `$WF_OUTCOME_FILE`, and every review would grade `fail_code` for a
  missing marker.

  The inversion is expressed with the WORKSPACE ROOT instead. In
  `workspace-write` the root (the working directory) is writable and everything
  else is not, so `writes = false` roots the child at the activation's
  `channels/` directory: the checkout stays readable and unwritable, the
  channels stay writable, and the wrapper's own crash records — one level up —
  are outside the grant entirely. `writes = true` roots it at the checkout and
  adds `channels/` as a writable root. Both probed, both ways round.
- **`sandbox_workspace_write.network_access = false` is a real no-push bound.**
  A `curl` from inside the box returned `Could not resolve host` (probed), so a
  `git push` cannot reach a remote — the only one of the three vendors where
  "no profile ever pushes" is enforced rather than requested.
- **`workspace-write` leaves `/tmp` writable by default**, which is not a
  detail: a `live`-marked run against a checkout under `/tmp` wrote the file the
  read-only bound was supposed to refuse, and passed every other assertion while
  doing it. A bound that evaporates depending on where the wrapper root happens
  to sit is not a bound, so `exclude_slash_tmp` is set in BOTH modes. The cost
  it used to carry — a `writes = true` node with nowhere to put a temp file — is
  paid by `$WF_SCRATCH_DIR`, the wrapper-owned `TMPDIR` inside `channels/`.
- **The host's own `~/.codex/config.toml` is ambient authority.** It is ignored
  on every argv (`IGNORE_AMBIENT_CONFIG`); the `-c` spelling that looked like it
  would pin the MCP set empty was probed and does not.
- **`.git` is read-only inside every writable root.** The sandbox refuses a write
  to `<root>/.git` in both modes, whether it is a directory or the `gitdir:` FILE
  a §5.4 worktree has (probes P2.2/P2.3, executed by
  `tests/test_profiles_git_isolation.py`). One residual is recorded rather than
  claimed away: `.git` of a repository NESTED inside a granted tree — a submodule
  checkout — is not `<root>/.git` and is writable. Nothing follows from it
  wrapper-side, because `gitio.GitSubcommand` is a closed set and none of its
  members recurses into a submodule, so no wrapper git ever reads that config.
- A linked-worktree writer needs its per-worktree Git directory and shared
  object store outside the checkout. Its branch and reflog grants are limited
  to `wf/<root_id>/candidate` directories, checked against the trusted task ID.
  The outer sandbox pins config, info and pointer files read-only. In-repo
  writers and legacy shared branch layouts are unsupported and must not widen
  these grants.
- Codex 0.154 needs `.agents` and `.codex` mount targets already present in the
  checkout under the outer read-only bound. A checkout missing them fails at
  launch; this profile does not create vendor directories in user source.
- **Codex cannot pre-assign a session id.** `thread_id` is emitted in the first
  `--json` line and is settable nowhere. §5.2 wants it pre-assigned; this is
  recorded as a deviation, not worked around.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from workflow_interpreter.bdio import ActivationRecord, Usage
from workflow_interpreter.contracts.execution import MSG_CODEX_IN_REPO, ToolNetwork
from workflow_interpreter.inspector.profile import (
    CrewCommand,
    CrewEvent,
    EventType,
    TaskSpec,
)
from workflow_interpreter.inspector.sandbox import GIT_ENTRY, worktree_git_write_roots
from workflow_interpreter.profiles._base import (
    BaseProfile,
    int_at,
    mapping_at,
    optional_text_at,
    require_absolute,
    text_at,
)
from workflow_interpreter.profiles.config import MODEL_VENDOR_DEFAULT, CrewName
from workflow_interpreter.profiles.errors import TaskRefused, UnsupportedOptionError

EXEC: Final[str] = "exec"
RESUME: Final[str] = "resume"
JSON_FLAG: Final[str] = "--json"
SKIP_GIT_CHECK: Final[str] = "--skip-git-repo-check"
IGNORE_AMBIENT_CONFIG: Final[tuple[str, str]] = (
    "--ignore-user-config",
    "--ignore-rules",
)
"""Emitted on EVERY codex argv, launch and resume alike (B1).

`~/.codex/config.toml` is authority no node declared, and on the machine this
was built for it carried a remote MCP server. The MCP client is the codex PARENT
process — outside the sandbox — so a `writes = false` reviewer bounded by
`workspace-write` still had a way to send the diff it was given somewhere, which
is the same defect that disqualified opencode. The same file's
`sandbox_workspace_write` settings are additive to the ones below, so ambient
`writable_roots` widened even the read-only path.

`-c mcp_servers={}` is NOT a second mechanism, and looked like one: probed, it is
accepted with no diagnostic and the server is still configured afterwards, while
a `CODEX_HOME` with no `config.toml` lists none (round-1 addendum, A1.1/A1.3).
Auth is unaffected — the flag's own help says it still uses `CODEX_HOME`.

**These two flags close the whole ambient-config surface, not part of it**
(probe P2.1, round-2 addendum). Two loose ends were raised against that and both
are answered:

- *A project-level `.codex/config.toml` in a crew-writable checkout.* Codex
  0.148 has no project config file; the project surface is execpolicy `.rules`,
  which is exactly what `--ignore-rules` drops ("Do not load user or project
  execpolicy `.rules` files"). Project TRUST — which would gate any project-level
  authority — lives in the USER `config.toml`'s `projects` table, and
  `--ignore-user-config` drops that file. Probed: a scratch checkout carrying
  `[mcp_servers.evil]` with an empty `CODEX_HOME` lists no MCP servers at all.
- *System config (`/etc/codex`).* Host-admin authority, not crew-writable, so
  it is outside the §0.3 threat model these flags exist for. A wrapper cannot
  and should not override the machine's operator."""
SANDBOX: Final[str] = "-s"
WORKSPACE_WRITE: Final[str] = "workspace-write"
CD: Final[str] = "-C"
ADD_DIR: Final[str] = "--add-dir"
MODEL: Final[str] = "-m"
CONFIG: Final[str] = "-c"

KEY_SANDBOX_MODE: Final[str] = "sandbox_mode"
KEY_WRITABLE_ROOTS: Final[str] = "sandbox_workspace_write.writable_roots"
KEY_NETWORK_ACCESS: Final[str] = "sandbox_workspace_write.network_access"
KEY_EXCLUDE_SLASH_TMP: Final[str] = "sandbox_workspace_write.exclude_slash_tmp"
KEY_REASONING_EFFORT: Final[str] = "model_reasoning_effort"

_MSG_UNUSABLE_MODEL: Final[str] = (
    "codex: node {node!r} has no usable model; a task must pin an explicit "
    "non-default model before argv construction"
)
_MSG_UNUSABLE_EFFORT: Final[str] = (
    "codex: node {node!r} has no usable effort; a task must pin effort before "
    "argv construction"
)

TYPE_THREAD_STARTED: Final[str] = "thread.started"
TYPE_TURN_COMPLETED: Final[str] = "turn.completed"
TYPE_TURN_FAILED: Final[str] = "turn.failed"
TYPE_ERROR: Final[str] = "error"
TYPE_ITEM_STARTED: Final[str] = "item.started"
TYPE_ITEM_UPDATED: Final[str] = "item.updated"
TYPE_ITEM_COMPLETED: Final[str] = "item.completed"
ITEM_TYPES: Final[frozenset[str]] = frozenset(
    {TYPE_ITEM_STARTED, TYPE_ITEM_UPDATED, TYPE_ITEM_COMPLETED}
)

ITEM_AGENT_MESSAGE: Final[str] = "agent_message"
ITEM_COMMAND: Final[str] = "command_execution"
ITEM_ERROR: Final[str] = "error"

KEY_TYPE: Final[str] = "type"
KEY_THREAD_ID: Final[str] = "thread_id"
KEY_ITEM: Final[str] = "item"
KEY_USAGE: Final[str] = "usage"
KEY_MESSAGE: Final[str] = "message"
KEY_TEXT: Final[str] = "text"
KEY_COMMAND: Final[str] = "command"
KEY_INPUT_TOKENS: Final[str] = "input_tokens"
KEY_CACHED_INPUT_TOKENS: Final[str] = "cached_input_tokens"
KEY_CACHE_WRITE_INPUT_TOKENS: Final[str] = "cache_write_input_tokens"
KEY_OUTPUT_TOKENS: Final[str] = "output_tokens"


_MSG_NO_SESSION: Final[str] = (
    "codex: cannot resume without a thread id; codex assigns one in its first "
    "`thread.started` event and it must be recorded from there before a §8.1 "
    "continuation can name it"
)


class CodexProfile(BaseProfile):
    """`codex exec` as a §6 crew: an OS sandbox, and no network."""

    tool_network = ToolNetwork.DENIED
    crew = CrewName.CODEX
    auth_env = (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "CODEX_HOME",
    )
    # -- §5.2 session identity -------------------------------------------

    def prepare(self, activation: ActivationRecord) -> str:
        """The recorded thread id, or `""` — codex cannot pre-assign one.

        `codex exec` has no session-id flag in any form, and `thread_id` is
        emitted in the first line of the `--json` stream. §5.2 says the session
        id is pre-assigned and "never discovered from output"; for this vendor
        that is not achievable, so the empty string means "not yet known" and
        `collect_terminal_envelope` reports the id the stream named. Flagged as
        a §5.2 deviation rather than papered over with a wrapper-minted id the
        vendor would ignore — a handle carrying an id no session has is worse
        than a handle carrying none.
        """
        return activation.metadata.session_id

    # -- §6 command construction -----------------------------------------

    def build_command(self, task: TaskSpec, session_id: str) -> CrewCommand:
        """The headless one-shot, with the danger default inverted (§6)."""
        root = self._workspace_root(task)
        argv = [
            self.binary(),
            EXEC,
            JSON_FLAG,
            SKIP_GIT_CHECK,
            *IGNORE_AMBIENT_CONFIG,
            SANDBOX,
            WORKSPACE_WRITE,
            CD,
            root,
            *self._launch_only_flags(task, root),
            *self._sandbox_flags(task, root),
            *self._shared_flags(task),
            self.require_brief(task),
        ]
        return self.command(argv, task, session_id, cwd=root)

    def build_resume_command(
        self, session_id: str, instructions: str, task: TaskSpec
    ) -> CrewCommand:
        """The §8.1 continuation: the same box, expressed only as `-c` overrides.

        `codex exec resume` has no `-s` and no `-C`, so the sandbox mode, the
        writable roots and the network denial all travel as config overrides,
        and the working root is the process working directory — which is why
        `build_command` sets `cwd` to the same directory it passes to `-C`.
        """
        if not session_id:
            raise TaskRefused(_MSG_NO_SESSION)
        root = self._workspace_root(task)
        argv = [
            self.binary(),
            EXEC,
            RESUME,
            session_id,
            JSON_FLAG,
            SKIP_GIT_CHECK,
            *IGNORE_AMBIENT_CONFIG,
            CONFIG,
            _toml(KEY_SANDBOX_MODE, WORKSPACE_WRITE),
            *self._sandbox_flags(task, root),
            *self._shared_flags(task),
            instructions,
        ]
        return self.command(argv, task, session_id, cwd=root)

    def build_resume_hint(self, session_id: str) -> str:
        """A human-pasteable resume line, recorded on gate beads (§6)."""
        return f"{self.binary()} {RESUME} {session_id}"

    def _workspace_root(self, task: TaskSpec) -> str:
        """The directory codex treats as writable — the whole danger default.

        `writes = false` roots the child in the activation's `channels/`
        directory, so the checkout is readable and unwritable while the §6
        channels stay writable. `writes = true` roots it in the checkout. In
        neither mode is the activation directory itself granted: the wrapper's
        receipt, exec ledger, exit file and completion evidence live one level
        above the grant, where no crew can forge or delete them
        (`paths.CHANNELS_DIR`).

        Phase 2 of `docs/plans/allowed-paths-enforcement.md` deliberately does
        NOT narrow this to the node's `allowed_paths`: `workspace-write` always
        makes the working root writable and 0.153.3's `sandbox_workspace_write`
        has no key that takes that back, so the only vendor-side expression of a
        read-only checkout is to move the root off it — which would leave a
        writer's cwd outside the repo its brief names paths relative to, and its
        `git add`/`git commit` nowhere. A writer's checkout therefore stays
        vendor-writable and the §2 bubblewrap mount bound
        (`inspector/sandbox.py`) is the containment. Revisit when 0.153's
        `permission_profiles` can express a read-only cwd — it is already the
        surface `codex sandbox` takes as a required `--permission-profile`,
        which the profile has not probed.
        """
        if task.execution_grants is not None:
            return task.execution_grants.process_cwd
        if task.writes:
            return require_absolute(self.crew, "task cwd", task.cwd)
        return str(_channels_dir(task))

    def _sandbox_flags(self, task: TaskSpec, root: str) -> list[str]:
        """The box itself, in the `-c` spelling BOTH subcommands accept.

        `/tmp` is removed from the writable set in both modes: `workspace-write`
        leaves it writable by default, which quietly unbounds any node whose
        checkout or wrapper root happens to live there (caught by a `live` run,
        not by reasoning — probe 12a).

        `$TMPDIR` is deliberately NOT excluded any more. That exclusion was
        aimed at an INHERITED `TMPDIR` naming somewhere outside the box, and it
        never fired: `TMPDIR` is not a passthrough key, so the value the child
        sees is the one `BaseProfile.child_env` sets — `$WF_SCRATCH_DIR`, inside
        the grant. Excluding it now would carve the crew's only temp space out
        of its own writable root.
        """
        flags = [
            CONFIG,
            _toml_bool(KEY_NETWORK_ACCESS, value=False),
            CONFIG,
            _toml_bool(KEY_EXCLUDE_SLASH_TMP, value=True),
        ]
        roots = _writable_roots(task, root)
        if not roots:
            return flags
        return [
            CONFIG,
            _toml_list(KEY_WRITABLE_ROOTS, roots),
            *flags,
        ]

    def _launch_only_flags(self, task: TaskSpec, root: str) -> list[str]:
        """`--add-dir`, which `codex exec` accepts and `codex exec resume` does not.

        Redundant with `writable_roots` by design rather than by accident: the
        launch states the grant both ways so the flag path and the config path
        cannot disagree, and the resume states it the only way it can. Both
        spellings come off the SAME `_writable_roots` call for the same reason —
        the §8.1 continuation has to describe the box the launch described, and
        two lists built two ways is how that stops being true.
        """
        words: list[str] = []
        for granted in _writable_roots(task, root):
            words += [ADD_DIR, granted]
        return words

    def _shared_flags(self, task: TaskSpec) -> list[str]:
        """Model and effort, in codex's own vocabulary."""
        return [
            MODEL,
            _required_model(task),
            CONFIG,
            _toml(KEY_REASONING_EFFORT, _required_effort(task)),
        ]

    # -- §6 stream normalization -----------------------------------------

    def decode_event(self, payload: Mapping[str, object]) -> CrewEvent | None:
        """Map one `--json` line onto the normalized §6 event."""
        kind = text_at(payload, KEY_TYPE)
        if kind == TYPE_THREAD_STARTED:
            # The ONE place a codex session id exists (see `prepare`).
            return CrewEvent(
                type=EventType.MESSAGE,
                text=kind,
                session=optional_text_at(payload, KEY_THREAD_ID),
            )
        if kind == TYPE_TURN_COMPLETED:
            usage = mapping_at(payload, KEY_USAGE)
            return CrewEvent(
                type=EventType.RESULT,
                text=kind,
                usage=Usage(
                    known=True,
                    input_tokens=_uncached_input_tokens(usage),
                    cache_read_input_tokens=int_at(usage, KEY_CACHED_INPUT_TOKENS),
                    cache_creation_input_tokens=int_at(
                        usage, KEY_CACHE_WRITE_INPUT_TOKENS
                    ),
                    output_tokens=int_at(usage, KEY_OUTPUT_TOKENS),
                )
                if usage
                else None,
            )
        if kind in (TYPE_ERROR, TYPE_TURN_FAILED):
            return CrewEvent(
                type=EventType.ERROR,
                text=text_at(payload, KEY_MESSAGE) or kind,
                is_error=True,
            )
        if kind in ITEM_TYPES:
            return _item_event(mapping_at(payload, KEY_ITEM), kind)
        return CrewEvent(type=EventType.MESSAGE, text=kind)


def _uncached_input_tokens(usage: Mapping[str, object]) -> int | None:
    """Remove Codex's cached and cache-write subsets from its total input count."""
    input_tokens = int_at(usage, KEY_INPUT_TOKENS)
    if input_tokens is None:
        return None
    return (
        input_tokens
        - (int_at(usage, KEY_CACHED_INPUT_TOKENS) or 0)
        - (int_at(usage, KEY_CACHE_WRITE_INPUT_TOKENS) or 0)
    )


def _item_event(item: Mapping[str, object], kind: str) -> CrewEvent:
    """One `item.*` line, classified by the item's own type."""
    item_type = text_at(item, KEY_TYPE)
    if item_type == ITEM_COMMAND:
        return CrewEvent(type=EventType.TOOL, text=text_at(item, KEY_COMMAND))
    if item_type == ITEM_ERROR:
        return CrewEvent(
            type=EventType.ERROR,
            text=text_at(item, KEY_MESSAGE) or text_at(item, KEY_TEXT),
            is_error=True,
        )
    if item_type == ITEM_AGENT_MESSAGE:
        return CrewEvent(type=EventType.MESSAGE, text=text_at(item, KEY_TEXT))
    return CrewEvent(type=EventType.MESSAGE, text=item_type or kind)


def _writable_roots(task: TaskSpec, root: str) -> tuple[str, ...]:
    """Grant the private cache and channels, plus writer-only Git state."""
    if task.execution_grants is not None:
        return task.execution_grants.writable_directories
    roots: list[str] = []
    channels_dir = str(_channels_dir(task))
    if channels_dir != root:
        roots.append(channels_dir)
    if not task.writes:
        if task.toolchain_cache is not None:
            roots.append(
                require_absolute(
                    CrewName.CODEX, "toolchain cache", task.toolchain_cache
                )
            )
        return tuple(roots)
    checkout = Path(require_absolute(CrewName.CODEX, "task cwd", task.cwd))
    if (checkout / GIT_ENTRY).is_dir():
        raise UnsupportedOptionError(
            MSG_CODEX_IN_REPO.format(node=task.node, checkout=checkout)
        )
    roots += [str(path) for path in worktree_git_write_roots(checkout, task.root_id)]
    # The inspector supplies an activation-private path, never inferred here.
    if task.toolchain_cache is not None:
        roots.append(
            require_absolute(CrewName.CODEX, "toolchain cache", task.toolchain_cache)
        )
    return tuple(roots)


def _channels_dir(task: TaskSpec) -> Path:
    """The directory holding this activation's §6 channels, and only those.

    Derived from `$WF_OUTCOME_FILE`, which `channels_for` always writes as
    `<activation_dir>/channels/outcome.json`. Codex's sandbox grants
    directories, not files, so this is the smallest grant that makes the
    reserved outcome channel writable — and since the wrapper's own records sit
    outside `channels/`, the grant is now exactly the crew's own surface.
    """
    return Path(
        require_absolute(CrewName.CODEX, "outcome file", task.channels.outcome_file)
    ).parent


def _required_model(task: TaskSpec) -> str:
    """Refuse a task whose model would otherwise be omitted from argv."""
    model = task.model
    if not isinstance(model, str) or not model.strip() or model == MODEL_VENDOR_DEFAULT:
        raise TaskRefused(_MSG_UNUSABLE_MODEL.format(node=task.node))
    return model


def _required_effort(task: TaskSpec) -> str:
    """Refuse a task whose effort would otherwise be omitted from argv."""
    effort = task.effort
    if not isinstance(effort, str) or not effort.strip():
        raise TaskRefused(_MSG_UNUSABLE_EFFORT.format(node=task.node))
    return effort


def _toml(key: str, value: str) -> str:
    """A `-c key="value"` override. JSON quoting is TOML basic-string quoting."""
    return f"{key}={json.dumps(value)}"


def _toml_bool(key: str, *, value: bool) -> str:
    """A `-c key=true|false` override."""
    return f"{key}={'true' if value else 'false'}"


def _toml_list(key: str, values: tuple[str, ...]) -> str:
    """A `-c key=["a","b"]` override."""
    return f"{key}=[{','.join(json.dumps(value) for value in values)}]"
