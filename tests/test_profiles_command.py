"""What each profile ACTUALLY execs: argv exactness and the §6 danger default.

The whole safety claim of phase 4 is a claim about argv. `writes = false` is
not a property of a profile's intention; it is a property of the exact flags it
emits, and every flag asserted here was run against the real CLI first
(`scratchpad/probes/phase4-cli-probes.md`) — including the two candidate
spellings that looked right, were emitted, and were silently ignored by the
vendor.

The matrix at the end is the load-bearing one: no profile, in any mode, may put
a bypass flag or an unguarded push on an argv.
"""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Final

import pytest

from tests._profiles import (
    BRIEF,
    INSTRUCTIONS,
    MODEL,
    make_claude,
    make_codex,
    make_opencode,
    make_profile_config,
    make_supervisor_config,
    make_task,
    new_session,
    profile_host_env,
)
from tests._supervisor import FrozenClock
from workflow_interpreter.profiles import (
    ProfileRegistry,
    RunnerName,
    TaskRefused,
    UnknownProfileError,
    UnsupportedOptionError,
    runner_name,
)
from workflow_interpreter.profiles._base import (
    ENV_MYPY_CACHE_DIR,
    ENV_PYTEST_ADDOPTS,
    ENV_RUFF_CACHE_DIR,
    ENV_UV_FROZEN,
    ENV_UV_PROJECT_ENVIRONMENT,
    BaseProfile,
    toolchain_env,
)
from workflow_interpreter.profiles.claude import ClaudeProfile
from workflow_interpreter.profiles.codex import KEY_WRITABLE_ROOTS as WRITABLE_ROOTS_KEY
from workflow_interpreter.profiles.codex import CodexProfile
from workflow_interpreter.supervisor.channels import (
    ENV_GIT_COMMITTER_EMAIL,
    ENV_GIT_COMMITTER_NAME,
)
from workflow_interpreter.supervisor.paths import CHANNELS_DIR
from workflow_interpreter.supervisor.profile import (
    ENV_ARTIFACT_DIR,
    ENV_EFFECTS_FILE,
    ENV_OUTCOME_FILE,
    RunnerCommand,
)

BYPASS_TOKENS: Final[tuple[str, ...]] = (
    "--dangerously-bypass-approvals-and-sandbox",
    "--dangerously-bypass-hook-trust",
    "--dangerously-skip-permissions",
    "--allow-dangerously-skip-permissions",
    "bypassPermissions",
    "danger-full-access",
    "--approve-for-me",
    "--ask-for-approval",
    "--auto",
    "--yolo",
)
"""Every bypass spelling the three CLIs offer, gathered from their own `--help`
output during the probes. A profile that emitted any of them would hand the
child more authority than the node declares, whatever else its flags said."""


def values_after(argv: tuple[str, ...], flag: str) -> tuple[str, ...]:
    """The variadic values a flag takes, up to the next flag."""
    start = argv.index(flag) + 1
    values: list[str] = []
    for item in argv[start:]:
        if item.startswith("-"):
            break
        values.append(item)
    return tuple(values)


# --- claude ---------------------------------------------------------------


def test_claude_read_only_grants_write_to_the_channels_and_nothing_else(
    tmp_path: Path,
) -> None:
    """§6: the three channels are writable REGARDLESS of `writes`.

    The probe that found this the hard way used `Write(<path>)` rules, which
    claude does not match on at all — the reviewer could not write its own
    outcome marker, so every review would have graded `fail_code` for a missing
    marker while looking perfectly configured.
    """
    task = make_task(tmp_path, writes=False)
    profile = make_claude(tmp_path, FrozenClock())

    command = profile.build_command(task, new_session())

    allowed = values_after(command.argv, "--allowedTools")
    activation_dir = Path(task.channels.outcome_file).parent.parent
    assert f"Edit(/{task.channels.artifact_dir}/**)" in allowed
    assert f"Edit(/{task.channels.outcome_file})" in allowed
    assert f"Edit(/{task.channels.effects_file})" in allowed
    assert f"Edit(/{task.channels.scratch_dir}/**)" in allowed
    assert not [rule for rule in allowed if f"Edit(/{task.cwd}" in rule]
    # B2: path-exact rules, so the activation directory holding the wrapper's
    # own records is not reachable through any of them.
    assert not [rule for rule in allowed if rule == f"Edit(/{activation_dir}/**)"]
    assert values_after(command.argv, "--tools") == ("Read", "Glob", "Grep", "Write")
    assert "Bash" in values_after(command.argv, "--disallowedTools")


def test_claude_writes_grants_the_checkout_and_denies_every_push_spelling(
    tmp_path: Path,
) -> None:
    """`writes = true` is repo-worktree write access only, and never a push (§6)."""
    task = make_task(tmp_path, writes=True)
    profile = make_claude(tmp_path, FrozenClock())

    command = profile.build_command(task, new_session())

    allowed = values_after(command.argv, "--allowedTools")
    denied = values_after(command.argv, "--disallowedTools")
    assert f"Edit(/{task.cwd}/**)" in allowed
    assert f"Edit(/{task.channels.artifact_dir}/**)" in allowed
    assert "Bash" in allowed
    assert {"Bash(git push)", "Bash(git push:*)", "Bash(git:* push:*)"} <= set(denied)
    assert values_after(command.argv, "--tools") == (
        "Read",
        "Glob",
        "Grep",
        "Edit",
        "Write",
        "Bash",
    )


@pytest.mark.parametrize("writes", [True, False])
def test_claude_never_denies_the_bare_edit_tool(tmp_path: Path, writes: bool) -> None:
    """The gotcha this file exists to keep: `Edit(path)` rules govern `Write`.

    A bare `Edit` in the deny list therefore denies every write in every mode,
    including the outcome marker — and deny beats allow, so the channel rules
    above would not save it.
    """
    profile = make_claude(tmp_path, FrozenClock())

    command = profile.build_command(make_task(tmp_path, writes=writes), new_session())

    assert "Edit" not in values_after(command.argv, "--disallowedTools")


def test_claude_always_pairs_stream_json_with_verbose(tmp_path: Path) -> None:
    """Probed: `--print` + `--output-format stream-json` exits 1 without it."""
    profile = make_claude(tmp_path, FrozenClock())

    command = profile.build_command(make_task(tmp_path), new_session())

    assert values_after(command.argv, "--output-format") == ("stream-json",)
    assert "--verbose" in command.argv


def test_claude_closes_the_mcp_hole_that_tools_cannot(tmp_path: Path) -> None:
    """`--tools` does not affect MCP tools; four ambient servers were live.

    `--strict-mcp-config` with no `--mcp-config` reduced `mcp_servers` to `[]`
    (probed), which is what makes the `--tools` bound total.
    """
    profile = make_claude(tmp_path, FrozenClock())

    command = profile.build_command(make_task(tmp_path), new_session())

    assert "--strict-mcp-config" in command.argv
    assert values_after(command.argv, "--setting-sources") == ("",)


def test_claude_refuses_a_session_id_the_cli_cannot_carry(tmp_path: Path) -> None:
    """`--session-id` takes a UUID; anything else fails at the CLI, loudly here."""
    profile = make_claude(tmp_path, FrozenClock())

    with pytest.raises(TaskRefused, match="UUID"):
        profile.build_command(make_task(tmp_path), "sess-super-1")


def test_claude_omits_the_model_flag_for_the_vendor_default(tmp_path: Path) -> None:
    """The §2 fixture's `model = "default"` is not a model name any CLI accepts."""
    profile = make_claude(tmp_path, FrozenClock())

    default = profile.build_command(make_task(tmp_path, model="default"), new_session())
    named = profile.build_command(make_task(tmp_path, model=MODEL), new_session())

    assert "--model" not in default.argv
    assert values_after(named.argv, "--model") == (MODEL,)


def test_claude_carries_the_configured_effort(tmp_path: Path) -> None:
    """Effort is per-vendor and passed through verbatim (`config.effort`)."""
    config = make_profile_config(effort={RunnerName.CLAUDE: "high"})
    profile = make_claude(tmp_path, FrozenClock(), config)

    command = profile.build_command(make_task(tmp_path), new_session())

    assert values_after(command.argv, "--effort") == ("high",)


def test_claude_resume_keeps_the_bounds_and_swaps_the_session_flag(
    tmp_path: Path,
) -> None:
    """§8.1's continuation is the same box with a new instruction."""
    profile = make_claude(tmp_path, FrozenClock())
    session = new_session()
    task = make_task(tmp_path, writes=False)
    launch = profile.build_command(task, session)

    resumed = profile.build_resume_command(session, INSTRUCTIONS, task)

    assert values_after(resumed.argv, "--resume") == (session,)
    assert "--session-id" not in resumed.argv
    assert INSTRUCTIONS in resumed.argv
    assert values_after(resumed.argv, "--allowedTools") == values_after(
        launch.argv, "--allowedTools"
    )
    assert resumed.cwd == launch.cwd


def test_a_resume_is_bounded_by_the_task_it_is_given_not_by_a_remembered_one(
    tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """M4: `build_resume_command` takes a `TaskSpec`, and holds no state at all.

    The adapters used to remember the last task `build_command` was handed.
    `ProfileRegistry.profile_for` mints a FRESH profile per lookup, so in
    production that state was always absent and a real steer refused; on a
    reused object it was worse — the continuation would have been bounded by the
    PREVIOUS activation's cwd and channels. This builds a resume for a second
    activation from a profile that launched a first, and every bound must be the
    second one's.
    """
    other = tmp_path_factory.mktemp("second-activation")
    profile = make_claude(tmp_path, FrozenClock())
    first = make_task(tmp_path, writes=False)
    second = make_task(other, writes=False)
    profile.build_command(first, new_session())

    resumed = profile.build_resume_command(new_session(), INSTRUCTIONS, second)

    assert resumed.cwd == second.cwd
    assert resumed.env[ENV_OUTCOME_FILE] == second.channels.outcome_file
    allowed = values_after(resumed.argv, "--allowedTools")
    assert f"Edit(/{second.channels.artifact_dir}/**)" in allowed
    assert f"Edit(/{first.channels.artifact_dir}/**)" not in allowed


@pytest.mark.parametrize("writes", [True, False])
def test_an_empty_brief_is_refused_rather_than_read_from_stdin(
    tmp_path: Path, writes: bool
) -> None:
    """Every CLI probed falls back to stdin, which the launcher never redirects."""
    profile = make_claude(tmp_path, FrozenClock())

    with pytest.raises(TaskRefused, match="empty brief"):
        profile.build_command(
            make_task(tmp_path, writes=writes, brief=""), new_session()
        )


# --- codex ----------------------------------------------------------------


def test_codex_read_only_roots_the_sandbox_at_the_wrapper_directory(
    tmp_path: Path,
) -> None:
    """`-s read-only` blocks the outcome channel too, so it cannot be used (§6).

    In `workspace-write` the working root is the ONLY writable place, so rooting
    a `writes = false` child at the activation directory leaves the checkout
    readable and unwritable while the channels stay writable. Probed both ways.
    """
    task = make_task(tmp_path, writes=False)
    activation_dir = str(Path(task.channels.outcome_file).parent)
    profile = make_codex(tmp_path, FrozenClock())

    command = profile.build_command(task, "")

    assert values_after(command.argv, "-s") == ("workspace-write",)
    assert values_after(command.argv, "-C") == (activation_dir,)
    assert command.cwd == activation_dir
    assert "read-only" not in command.argv
    assert "--add-dir" not in command.argv


def test_codex_writes_roots_the_sandbox_at_the_checkout_and_adds_the_channels(
    tmp_path: Path,
) -> None:
    """`--add-dir` DOES grant write in `workspace-write` (probed)."""
    task = make_task(tmp_path, writes=True)
    activation_dir = str(Path(task.channels.outcome_file).parent)
    profile = make_codex(tmp_path, FrozenClock())

    command = profile.build_command(task, "")

    assert values_after(command.argv, "-C") == (task.cwd,)
    assert command.cwd == task.cwd
    assert values_after(command.argv, "--add-dir") == (activation_dir,)
    assert (
        f'sandbox_workspace_write.writable_roots=["{activation_dir}"]' in command.argv
    )


@pytest.mark.parametrize("writes", [True, False])
def test_codex_removes_slash_tmp_but_keeps_the_wrapper_owned_tmpdir(
    tmp_path: Path, writes: bool
) -> None:
    """`workspace-write` leaves `/tmp` and `$TMPDIR` writable by DEFAULT.

    A `live` run against a checkout under `/tmp` wrote the file the read-only
    bound was supposed to refuse — and passed every other assertion while doing
    it (probe 12a). `/tmp` is therefore excluded in both modes.

    `$TMPDIR` is NOT excluded, and that is the deliberate half: the child's
    `TMPDIR` is set by the wrapper to `$WF_SCRATCH_DIR`, which already sits
    inside the grant. Excluding it would subtract the runner's only temp space
    from its own writable root, and the exclusion never protected anything —
    `TMPDIR` is not a passthrough key, so no host value can reach the child.
    """
    task = make_task(tmp_path, writes=writes)
    profile = make_codex(tmp_path, FrozenClock())

    command = profile.build_command(task, "")

    assert "sandbox_workspace_write.exclude_slash_tmp=true" in command.argv
    assert not [item for item in command.argv if "exclude_tmpdir_env_var" in item]
    assert command.env["TMPDIR"] == task.channels.scratch_dir
    assert Path(task.channels.scratch_dir).is_relative_to(
        Path(task.channels.outcome_file).parent
    )


@pytest.mark.parametrize("writes", [True, False])
def test_codex_grants_the_channels_directory_and_never_the_activation_dir(
    tmp_path: Path, writes: bool
) -> None:
    """B2: a directory grant must not include the wrapper's own crash records.

    Codex's sandbox grants DIRECTORIES, so before the channels moved into their
    own subdirectory, making `$WF_OUTCOME_FILE` writable — which §6 requires
    regardless of `writes` — also made `exec.ledger`, `launch-receipt.json`,
    `exit.json` and `completion.json` writable. Every path this argv grants must
    now be the channels directory, and the activation directory must appear
    nowhere.
    """
    task = make_task(tmp_path, writes=writes)
    channels_dir = Path(task.channels.outcome_file).parent
    activation_dir = channels_dir.parent
    profile = make_codex(tmp_path, FrozenClock())

    command = profile.build_command(task, "")

    granted = set(values_after(command.argv, "-C"))
    if "--add-dir" in command.argv:
        granted |= set(values_after(command.argv, "--add-dir"))
    for item in command.argv:
        if item.startswith(f"{WRITABLE_ROOTS_KEY}="):
            granted |= set(json.loads(item.split("=", 1)[1]))
    expected = {str(channels_dir)} | ({task.cwd} if writes else set())
    assert granted == expected
    assert str(activation_dir) not in granted
    assert channels_dir.name == CHANNELS_DIR


@pytest.mark.parametrize("writes", [True, False])
def test_codex_always_denies_the_network(tmp_path: Path, writes: bool) -> None:
    """The only enforced no-push bound of the three: a push cannot resolve a host.

    Probed: `curl` from inside the box returns `Could not resolve host`.
    """
    profile = make_codex(tmp_path, FrozenClock())

    command = profile.build_command(make_task(tmp_path, writes=writes), "")

    assert "sandbox_workspace_write.network_access=false" in command.argv


def test_codex_resume_carries_the_sandbox_as_config_because_it_has_no_flag(
    tmp_path: Path,
) -> None:
    """`codex exec resume` accepts neither `-s` nor `-C` (probed against --help).

    So the box travels as `-c` overrides and the working root as the process
    working directory — which is why the launch sets `cwd` to what it passed to
    `-C`, making the two invocations describe the same box.
    """
    profile = make_codex(tmp_path, FrozenClock())
    task = make_task(tmp_path, writes=False)
    launch = profile.build_command(task, "")

    resumed = profile.build_resume_command(
        "01a03d87-cda2-7062-aa5d-b5a73dc882c3", INSTRUCTIONS, task
    )

    assert resumed.argv[1:3] == ("exec", "resume")
    assert "-s" not in resumed.argv
    assert "-C" not in resumed.argv
    assert 'sandbox_mode="workspace-write"' in resumed.argv
    assert "sandbox_workspace_write.network_access=false" in resumed.argv
    assert "sandbox_workspace_write.exclude_slash_tmp=true" in resumed.argv
    assert resumed.cwd == launch.cwd


def test_a_writing_codex_resume_never_emits_the_flag_resume_cannot_parse(
    tmp_path: Path,
) -> None:
    """`--add-dir` exists on `codex exec` and NOT on `codex exec resume`.

    Emitting it there is not a soft failure — clap exits 2 before the model is
    reached, so every §8.1 continuation on a writing node would die as a
    transport error. The grant travels as `writable_roots` instead, which both
    subcommands accept.
    """
    task = make_task(tmp_path, writes=True)
    channels_dir = str(Path(task.channels.outcome_file).parent)
    profile = make_codex(tmp_path, FrozenClock())
    profile.build_command(task, "")

    resumed = profile.build_resume_command("01a03d87", INSTRUCTIONS, task)

    assert "--add-dir" not in resumed.argv
    assert f'sandbox_workspace_write.writable_roots=["{channels_dir}"]' in resumed.argv


def test_codex_refuses_to_resume_a_thread_it_was_never_told_about(
    tmp_path: Path,
) -> None:
    """Codex assigns the id in its first event; there is nothing else to name."""
    profile = make_codex(tmp_path, FrozenClock())
    task = make_task(tmp_path)
    profile.build_command(task, "")

    with pytest.raises(TaskRefused, match="thread id"):
        profile.build_resume_command("", INSTRUCTIONS, task)


def test_codex_puts_the_prompt_last_and_the_flags_first(tmp_path: Path) -> None:
    """`codex exec [OPTIONS] [PROMPT]`: a prompt among the flags is a parse error."""
    profile = make_codex(tmp_path, FrozenClock())

    command = profile.build_command(make_task(tmp_path), "")

    assert command.argv[-1] == BRIEF
    assert BRIEF not in command.argv[:-1]


# --- opencode -------------------------------------------------------------


@pytest.mark.parametrize("writes", [True, False])
def test_opencode_refuses_because_it_has_no_bound_to_offer(
    tmp_path: Path, writes: bool
) -> None:
    """§6: unsupported option = loud error, and here the option is the bound.

    Probed: no sandbox/permission/deny flag exists, the resolved permission
    stack is `*: allow` for every agent including `plan`, it comes from ambient
    config the wrapper does not own, and a plain headless run wrote a file with
    no approval.
    """
    profile = make_opencode(tmp_path, FrozenClock())

    with pytest.raises(UnsupportedOptionError) as refusal:
        profile.build_command(make_task(tmp_path, writes=writes), "")

    assert "--model provider/model" in str(refusal.value)
    assert ("bounded write mode" if writes else "read-only mode") in str(refusal.value)


def test_opencode_refuses_a_continuation_for_the_same_reason(tmp_path: Path) -> None:
    """A §8.1 continuation would be exactly as unbounded as the launch."""
    profile = make_opencode(tmp_path, FrozenClock())

    with pytest.raises(UnsupportedOptionError):
        profile.build_resume_command("ses_x", INSTRUCTIONS, make_task(tmp_path))


# --- the danger-default matrix -------------------------------------------


def every_command(tmp_path: Path) -> list[RunnerCommand]:
    """Every invocation any profile can build, in both `writes` modes."""
    clock = FrozenClock()
    commands: list[RunnerCommand] = []
    session = new_session()
    for writes in (True, False):
        task = make_task(tmp_path, writes=writes)
        claude: ClaudeProfile = make_claude(tmp_path, clock)
        commands.append(claude.build_command(task, session))
        commands.append(claude.build_resume_command(session, INSTRUCTIONS, task))
        codex: CodexProfile = make_codex(tmp_path, clock)
        commands.append(codex.build_command(task, ""))
        commands.append(codex.build_resume_command("01a03d87", INSTRUCTIONS, task))
    return commands


INTERPRETERS: Final[frozenset[str]] = frozenset(
    {"sh", "bash", "dash", "zsh", "ksh", "env", "python", "python3", "xargs"}
)
"""Programs that would turn the rest of an argv back into a command STRING."""


def test_every_command_is_argv_only_with_the_vendor_binary_first(
    tmp_path: Path,
) -> None:
    """§2 rule 6's contract, applied to runners: argv, never a shell string.

    `launch.py` execs with `execvpe(argv[0], argv, env)` — no shell, no
    expansion — so an interpreter prefix or a packed command string would be
    exec'd literally rather than interpreted, and a profile that needed one
    would be relying on something the launcher does not do.

    The interpreter check is on `argv[0]`, which is the only position that
    decides what gets executed. It used to read `assert "-c" not in argv[:1]`,
    which compares a flag against the PROGRAM name and is true of every argv
    ever built — including `("sh", "-c", ...)`, the one thing it was meant to
    catch.
    """
    for command in every_command(tmp_path):
        program = Path(command.argv[0])
        assert program.name in {"claude", "codex"}
        assert program.name not in INTERPRETERS


def every_codex_command(tmp_path: Path) -> list[RunnerCommand]:
    """Every invocation the codex profile can build, in both `writes` modes."""
    clock = FrozenClock()
    commands: list[RunnerCommand] = []
    for writes in (True, False):
        codex: CodexProfile = make_codex(tmp_path, clock)
        task = make_task(tmp_path, writes=writes)
        commands.append(codex.build_command(task, ""))
        commands.append(codex.build_resume_command("01a03d87", INSTRUCTIONS, task))
    return commands


def test_every_codex_command_refuses_the_hosts_own_codex_config(
    tmp_path: Path,
) -> None:
    """B1: ambient `~/.codex/config.toml` is authority the node never declared.

    This host's config carries a REMOTE MCP server. The MCP client is the codex
    PARENT process, which lives outside the sandbox, so a `writes = false`
    reviewer bounded by `workspace-write` still had an egress path for the diff
    it was handed — the exact defect that disqualified opencode. The same file
    also carries `sandbox_workspace_write` settings that are additive to the
    ones this profile emits.

    `--ignore-user-config` is the only mechanism that closes it, and it must be
    on EVERY argv: probed, `-c mcp_servers={}` is accepted with no diagnostic
    and leaves the server configured (round-1 addendum, A1.1), while a
    `CODEX_HOME` holding no `config.toml` lists none at all (A1.3).
    `--ignore-rules` is the same argument for execpolicy `.rules` files.
    """
    for command in every_codex_command(tmp_path):
        assert "--ignore-user-config" in command.argv, command.argv
        assert "--ignore-rules" in command.argv, command.argv


def test_no_profile_can_emit_a_bypass_flag(tmp_path: Path) -> None:
    """The one assertion that must hold for every mode of every vendor (§6)."""
    for command in every_command(tmp_path):
        for token in BYPASS_TOKENS:
            assert token not in command.argv, (command.argv[0], token)


def test_no_profile_can_emit_a_push_outside_a_denial(tmp_path: Path) -> None:
    """ "No profile ever pushes": every `push` on an argv is inside a deny rule."""
    for command in every_command(tmp_path):
        pushes = [item for item in command.argv if "push" in item]
        assert all(item.startswith("Bash(") for item in pushes), command.argv
        for item in pushes:
            denied = values_after(command.argv, "--disallowedTools")
            assert item in denied


def test_every_command_carries_the_committer_identity_and_the_channels(
    tmp_path: Path,
) -> None:
    """§7.4: the stamp is applied in ONE place, `RunnerChannels.env()`.

    A profile that built its own environment instead would leave every in-repo
    commit unattributable, `pin_artifact` would refuse it, and a `done` claim on
    a writing node would grade `fail_code` with nothing to point at.
    """
    for command in every_command(tmp_path):
        assert command.env[ENV_GIT_COMMITTER_NAME] == "wf-runner"
        assert "@workflow-interpreter.invalid" in command.env[ENV_GIT_COMMITTER_EMAIL]
        assert ENV_OUTCOME_FILE in command.env
        assert ENV_ARTIFACT_DIR in command.env
        assert ENV_EFFECTS_FILE in command.env


def test_the_child_environment_is_an_allow_list_not_a_copy(tmp_path: Path) -> None:
    """`rules/python/safety.md`: no ambient read reaches the child unnamed."""
    profile = make_claude(tmp_path, FrozenClock())

    command = profile.build_command(make_task(tmp_path), new_session())

    assert command.env["ANTHROPIC_API_KEY"] == "test-anthropic-key"
    assert command.env["PATH"] == "/usr/bin:/bin"
    assert "AWS_SECRET_ACCESS_KEY" not in command.env
    assert "SSH_AUTH_SOCK" not in command.env
    assert "OPENAI_API_KEY" not in command.env


def test_a_channel_cannot_be_shadowed_by_a_passthrough_key(tmp_path: Path) -> None:
    """The channels are written last, so no host key can redirect them."""
    config = make_profile_config(passthrough_env=("PATH", ENV_OUTCOME_FILE))
    profile = ClaudeProfile(
        config,
        make_supervisor_config(tmp_path),
        FrozenClock(),
        {"PATH": "/usr/bin", ENV_OUTCOME_FILE: "/tmp/attacker.json"},
    )
    task = make_task(tmp_path)

    command = profile.build_command(task, new_session())

    assert command.env[ENV_OUTCOME_FILE] == task.channels.outcome_file


def test_the_injected_profile_config_is_actually_frozen() -> None:
    """m15: `frozen = True` freezes attributes, not the objects behind them.

    `binary_overrides` and `effort` were `dict` fields, so a "frozen" config
    handed to three profiles could be edited in place by any of them — and this
    is the object that decides which binary gets exec'd. A mapping is still
    accepted at the boundary; what is STORED is immutable.
    """
    config = make_profile_config(
        binary_overrides={RunnerName.CODEX: "/opt/codex"},
        effort={RunnerName.CLAUDE: "high"},
    )

    assert config.binary_for(RunnerName.CODEX) == "/opt/codex"
    assert config.binary_for(RunnerName.CLAUDE) == "claude"
    assert config.effort_for(RunnerName.CLAUDE) == "high"
    assert config.effort_for(RunnerName.CODEX) is None
    with pytest.raises(TypeError):
        config.binary_overrides[RunnerName.CLAUDE] = "/opt/evil"  # type: ignore[index]
    with pytest.raises(TypeError):
        config.effort[RunnerName.CODEX] = "max"  # type: ignore[index]
    assert make_profile_config().binary_overrides == {}


# --- resume hints and the registry ---------------------------------------


def test_resume_hints_are_pasteable_vendor_commands(tmp_path: Path) -> None:
    """§6: recorded on gate beads for a human to use."""
    clock = FrozenClock()
    assert (
        make_claude(tmp_path, clock).build_resume_hint("abc") == "claude --resume abc"
    )
    assert make_codex(tmp_path, clock).build_resume_hint("abc") == "codex resume abc"
    assert (
        make_opencode(tmp_path, clock).build_resume_hint("abc")
        == "opencode --session abc"
    )


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("claude", RunnerName.CLAUDE),
        ("profile:claude", RunnerName.CLAUDE),
        ("codex", RunnerName.CODEX),
        ("opencode", RunnerName.OPENCODE),
    ],
)
def test_the_registry_resolves_the_closed_vendor_set(
    name: str, expected: RunnerName
) -> None:
    """§6 records `runner = "profile:<name>"`, so both spellings resolve."""
    assert runner_name(name) is expected


@pytest.mark.parametrize("name", ["", "gpt", "profile:implementer", "CLAUDE"])
def test_an_unknown_runner_name_is_a_typed_refusal(tmp_path: Path, name: str) -> None:
    """A bead the wrapper cannot resolve is a bead nothing should dispatch.

    `profile:implementer` is in the list on purpose: the §2 fixture names ROLES
    where the registry keys on VENDORS, and the mapping between them belongs to
    the foreman — flagged, and fail-closed until it exists.
    """
    registry = ProfileRegistry(
        make_profile_config(), make_supervisor_config(tmp_path), FrozenClock(), {}
    )

    with pytest.raises(UnknownProfileError, match="closed set"):
        registry.profile_for(name)


def test_the_registry_builds_a_profile_of_the_right_vendor(tmp_path: Path) -> None:
    """One construction point, four injected dependencies (see `registry.py`)."""
    registry = ProfileRegistry(
        make_profile_config(), make_supervisor_config(tmp_path), FrozenClock(), {}
    )

    for name in ("claude", "codex", "opencode"):
        profile = registry.profile_for(name)
        assert profile.name() == name
        assert isinstance(profile, BaseProfile)


def test_the_toolchain_cache_option_survives_a_path_with_a_space(
    tmp_path: Path,
) -> None:
    """`PYTEST_ADDOPTS` is shlex-split by pytest, so the path must be quoted.

    An unquoted `-o cache_dir=/a b/pytest` reaches pytest as two words and the
    run dies on an unrecognised argument — which is the whole gate of a
    `writes = true` node failing for a reason that has nothing to do with it.
    """
    scratch = tmp_path / "a dir" / "scratch"
    env = toolchain_env(str(scratch))

    assert shlex.split(env[ENV_PYTEST_ADDOPTS]) == [
        "-o",
        f"cache_dir={scratch / 'pytest'}",
    ]
    assert env[ENV_UV_PROJECT_ENVIRONMENT] == str(scratch / "venv")


def test_the_toolchain_env_reaches_every_child(tmp_path: Path) -> None:
    """Set plainly, not appended: the child inherits no `PYTEST_ADDOPTS` at all.

    `child_env` copies only `passthrough_env` keys, and `PYTEST_ADDOPTS` is not
    one of them — so there is never an inherited value to preserve, and an
    append branch would be code that cannot run.
    """
    clock = FrozenClock()
    profile = make_claude(tmp_path, clock)
    task = make_task(tmp_path)
    env = profile.child_env(task.channels)
    scratch = Path(task.channels.scratch_dir)

    assert env[ENV_RUFF_CACHE_DIR] == str(scratch / "ruff")
    assert env[ENV_MYPY_CACHE_DIR] == str(scratch / "mypy")
    assert env[ENV_UV_FROZEN] == "1"
    assert ENV_PYTEST_ADDOPTS not in profile_host_env()
