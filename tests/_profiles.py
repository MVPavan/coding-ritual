"""Builders, captured streams and CLI stubs shared by the profile families.

Not a test module. Three things live here:

- **The captured streams.** Every fixture under `tests/fixtures/profiles/` is a
  real CLI's real output, recorded during the phase-4 step-0 probes
  (`scratchpad/probes/phase4-cli-probes.md`), with the substitutions `REDACTIONS`
  declares applied and no others. That list is EXECUTABLE (`redact`) and checked
  (`test_profiles_parse.py`): "two substitutions and nothing else" was the
  earlier claim and it was not true — one capture had its IPC socket pid
  normalized and three did not.
- **Task builders**, because a `TaskSpec` with an empty brief is refused by
  design and the supervisor's own `task_builder` does not set one.
- **CLI stubs**: small `sh` programs that mimic each vendor's JSONL shape well
  enough to drive a REAL `ForkBarrierLauncher` and a REAL `Supervisor.run`. They
  are what makes the `proc` family an end-to-end proof that costs no tokens.
- **`Lab`**, the wiring that points those stubs at a real supervisor over a
  throwaway repo. It moved here from `test_profiles_process.py` when the §8.1
  continuity family grew its own module: two `test_profiles_*` modules drive the
  same lab, and a second copy of it would be a second answer to "what does an
  end-to-end profile run look like". The `lab` fixture is in `conftest.py`,
  which is the only place a fixture can be shared without an import that reads
  as unused.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import uuid
from pathlib import Path
from typing import Final

from tests._supervisor import (
    GIT_TIMEOUT_S,
    IMPLEMENT,
    FrozenClock,
    entry_mint,
    head_of,
    make_config,
    make_git,
    make_paths,
    make_repo,
    make_root,
    make_store,
    make_workspace,
    node_of,
)
from workflow_interpreter.bdio import ActivationRecord, MintRequest, ProcessHandle
from workflow_interpreter.profiles import ProfileConfig, ProfileRegistry, RunnerName
from workflow_interpreter.profiles.claude import ClaudeProfile
from workflow_interpreter.profiles.codex import CodexProfile
from workflow_interpreter.profiles.opencode import OpencodeProfile
from workflow_interpreter.schema.models import Node
from workflow_interpreter.supervisor import (
    Dispatcher,
    Steerer,
    SupervisionResult,
    Supervisor,
    SupervisorConfig,
    TaskSpec,
    channels_for,
    pinned_verifier_digests,
    procfs,
)
from workflow_interpreter.supervisor.artifact import BRANCH_TEMPLATE
from workflow_interpreter.supervisor.clock import Clock
from workflow_interpreter.supervisor.launch import DispatchResult, TaskBuilder
from workflow_interpreter.supervisor.paths import (
    ARTIFACT_DIR,
    CHANNELS_DIR,
    SCRATCH_DIR,
)
from workflow_interpreter.supervisor.profile import Profile, RunnerChannels
from workflow_interpreter.supervisor.sandbox import SandboxMode

FIXTURES: Final[Path] = Path(__file__).parent / "fixtures" / "profiles"

BRIEF: Final[str] = "implement the feature described in the task brief"
INSTRUCTIONS: Final[str] = "you have been idle; report what you have so far"
ACTIVATION: Final[str] = "wf-42"
ROOT_ID: Final[str] = "wf-root-1"
HOST: Final[str] = "lab"
MODEL: Final[str] = "claude-opus-5"

HOST_ENV: Final[dict[str, str]] = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/home/runner",
    "ANTHROPIC_API_KEY": "test-anthropic-key",
    "OPENAI_API_KEY": "test-openai-key",
    "OPENCODE_API_KEY": "test-opencode-key",
    "SSH_AUTH_SOCK": "/run/agent.sock",
    "AWS_SECRET_ACCESS_KEY": "must-not-reach-the-child",
}
"""A stand-in host environment. The last two exist so a test can prove the
passthrough is an ALLOW-LIST rather than a copy of everything ambient."""


REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
PROBE_DIR: Final[str] = str(REPO_ROOT / "scratchpad" / "probes" / "p4-cli-probes")
"""Where the step-0 captures were taken, on WHATEVER checkout is running.

It was the absolute path of one machine, written into a file that is about to be
committed — which CLAUDE.md's Git Safety rule forbids, and which fails silently
rather than loudly: on any other checkout both the redaction below and the
`FORBIDDEN` guard built from it become no-ops, so the provenance check would
stop guarding the thing it exists for while still passing."""
PROBE_DIR_REDACTED: Final[str] = "/wf/probe"
HOME_DIR_REDACTED: Final[str] = "/home/runner"

REDACTIONS: Final[tuple[tuple[str, str], ...]] = (
    (re.escape(PROBE_DIR), PROBE_DIR_REDACTED),
    (r"/home/[A-Za-z0-9._-]+", HOME_DIR_REDACTED),
    (r"(/tmp/cc-socks/)\d+(\.sock)", r"\g<1>0\g<2>"),
    (r"(cf-ray: )[0-9a-f]+-[A-Z]+", r"\g<1>0000000000000000-XXX"),
)
"""Every transformation applied to a captured stream before committing it.

In order, and each is here because the raw capture carried something about THIS
machine rather than about the CLI: the probe directory, the operator's home, the
per-process IPC socket claude opens under `/tmp/cc-socks/<pid>.sock`, and the
Cloudflare ray id on codex's 401 responses (whose suffix is a datacenter code).

Nothing else is touched. Session ids, thread ids, token counts, costs, tool
inputs and error text are the CAPTURE and are what the tests assert on; a
fixture whose interesting fields had been rewritten would prove nothing about a
real CLI. No credential-shaped string was present to remove — see `FORBIDDEN`,
which is checked rather than remembered."""

FORBIDDEN: Final[tuple[str, ...]] = (
    r"/home/(?!runner\b)[A-Za-z0-9._-]+",
    re.escape(PROBE_DIR),
    r"/tmp/cc-socks/[1-9]\d*\.sock",
    r"sk-[A-Za-z0-9]",
    r"ghp_[A-Za-z0-9]",
    r"Bearer\s+[A-Za-z0-9]",
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
)
"""What must not survive into a committed fixture, as patterns a test can run."""


def redact(text: str) -> str:
    """Apply `REDACTIONS` to a captured stream, in order."""
    for pattern, replacement in REDACTIONS:
        text = re.sub(pattern, replacement, text)
    return text


def fixture_files() -> list[Path]:
    """Every committed capture, sorted."""
    return sorted(path for path in FIXTURES.rglob("*") if path.is_file())


def read_stream(vendor: str, name: str) -> list[str]:
    """One captured vendor stream, as the lines a runner log would hold."""
    return (FIXTURES / vendor / name).read_text(encoding="utf-8").splitlines()


def make_supervisor_config(
    tmp_path: Path,
    *,
    sandbox: SandboxMode = SandboxMode.BWRAP,
    **overrides: object,
) -> SupervisorConfig:
    """A supervisor configuration the profiles can prove liveness against.

    Both roots are CREATED, not merely named: `sandbox.plan_for` read-only binds
    them and refuses a root that is not on disk, so a config whose `repo_root`
    never existed would make every sandboxed dispatch through this rig fail for
    a reason that is about the rig rather than about the bound.
    """
    values: dict[str, object] = {
        "repo_root": tmp_path / "repo",
        "wrapper_root": tmp_path / ".wf",
        "host": HOST,
        "sandbox": sandbox,
    }
    values.update(overrides)
    config = SupervisorConfig.model_validate(values)
    config.repo_root.mkdir(parents=True, exist_ok=True)
    config.wrapper_root.mkdir(parents=True, exist_ok=True)
    return config


def make_profile_config(**overrides: object) -> ProfileConfig:
    """The injected profile configuration, with test-friendly defaults."""
    return ProfileConfig.model_validate(overrides)


def make_channels(tmp_path: Path, activation_id: str = ACTIVATION) -> RunnerChannels:
    """The §6 channels for an activation, in a throwaway wrapper dir.

    Created through the same constants `WrapperPaths.ensure_activation_dir`
    uses, so a test can never disagree with production about where the runner's
    writable surface starts.
    """
    activation_dir = tmp_path / ".wf" / ROOT_ID / activation_id
    for channel in (ARTIFACT_DIR, SCRATCH_DIR):
        (activation_dir / CHANNELS_DIR / channel).mkdir(parents=True, exist_ok=True)
    return channels_for(activation_dir, activation_dir / "run.jsonl", activation_id)


def make_task(
    tmp_path: Path,
    *,
    writes: bool = True,
    brief: str = BRIEF,
    model: str = MODEL,
    node: str = "implement",
    cwd: Path | None = None,
    allowed_paths: tuple[str, ...] = (),
    effort: str | None = None,
    fallback_models: tuple[str, ...] = (),
) -> TaskSpec:
    """A `TaskSpec` for one node, with a checkout directory that exists."""
    worktree = cwd or (tmp_path / ".wf" / ROOT_ID / "worktree")
    worktree.mkdir(parents=True, exist_ok=True)
    return TaskSpec(
        root_id=ROOT_ID,
        activation_id=ACTIVATION,
        node=node,
        model=model,
        effort=effort,
        fallback_models=fallback_models,
        writes=writes,
        allowed_paths=allowed_paths,
        cwd=str(worktree),
        channels=make_channels(tmp_path),
        brief=brief,
    )


def new_session() -> str:
    """A wrapper-minted session id in the form claude requires."""
    return str(uuid.uuid4())


def make_claude(
    tmp_path: Path, clock: Clock, config: ProfileConfig | None = None
) -> ClaudeProfile:
    """A claude profile wired to its profile configuration."""
    return ClaudeProfile(
        config or make_profile_config(),
        clock,
        HOST_ENV,
    )


def make_codex(
    tmp_path: Path, clock: Clock, config: ProfileConfig | None = None
) -> CodexProfile:
    """A codex profile wired to its profile configuration."""
    return CodexProfile(
        config or make_profile_config(),
        clock,
        HOST_ENV,
    )


def make_opencode(
    tmp_path: Path, clock: Clock, config: ProfileConfig | None = None
) -> OpencodeProfile:
    """An opencode profile wired to its profile configuration."""
    return OpencodeProfile(
        config or make_profile_config(),
        clock,
        HOST_ENV,
    )


# --- CLI stubs -----------------------------------------------------------

_PREAMBLE: Final[str] = """#!/bin/sh
# A stand-in for a vendor CLI: emits that vendor's JSONL shape on stdout, then
# writes the two §6 channels the wrapper grades on. Reads no argv on purpose —
# the point is to prove the PROFILE composes with the supervisor, not to
# re-implement a CLI.
set -e
"""

_CHANNELS: Final[str] = """
printf '%s' "$WF_MARKER" > "$WF_OUTCOME_FILE"
printf '%s' "$WF_EFFECTS" > "$WF_EFFECTS_FILE"
printf 'from the stub\\n' > "$WF_ARTIFACT_DIR/note.txt"
"""

FORGED_RECORDS: Final[tuple[str, ...]] = (
    "exec.ledger",
    "launch-receipt.json",
    "exit.json",
    "completion.json",
)
"""The wrapper-owned records a runner must not be able to reach (B2).

Forging `exit.json` makes §5.6 classify a death the wrapper never observed;
deleting `launch-receipt.json` makes the next dispatch refuse and burns an infra
retry; appending to `exec.ledger` destroys the exactly-once evidence drills 1, 2,
10 and 22 rest on; pre-writing `completion.json` tells a later tick that §7
already finished."""

FORGED_LINE: Final[str] = "forged by the runner"

_FORGE: Final[str] = """
# Everything this stub can name lives under its own granted root: a real
# sandboxed child gets exactly the directory holding $WF_OUTCOME_FILE.
GRANT=$(dirname "$WF_OUTCOME_FILE")
for record in {records}; do
  printf '{line}\\n{line}\\n{line}\\n' > "$GRANT/$record"
done
""".format(records=" ".join(FORGED_RECORDS), line=FORGED_LINE)
"""Three lines per file on purpose: one line would leave `ExecLedger.count()`
reading 1 by coincidence, which is exactly the assertion this must be able to
break."""

STUB_BODIES: Final[dict[RunnerName, str]] = {
    RunnerName.CLAUDE: (
        """printf '%s\\n' '{"type":"system","subtype":"init","session_id":"SID","""
        """"tools":["Read","Write"]}'
printf '%s\\n' '{"type":"assistant","session_id":"SID","message":{"content":"""
        """[{"type":"text","text":"working"}],"usage":{"input_tokens":9,"output_tokens":3}}}'
printf '%s\\n' '{"type":"result","subtype":"success","session_id":"SID","""
        """"is_error":false,"result":"ok","total_cost_usd":0.25,"""
        """"usage":{"input_tokens":11,"output_tokens":22}}'
"""
    ),
    RunnerName.CODEX: (
        """printf '%s\\n' '{"type":"thread.started","thread_id":"SID"}'
printf '%s\\n' '{"type":"turn.started"}'
printf '%s\\n' '{"type":"item.completed","item":{"id":"item_0","""
        """"type":"agent_message","text":"ok"}}'
printf '%s\\n' '{"type":"turn.completed","usage":{"input_tokens":11,"""
        """"output_tokens":22}}'
"""
    ),
    RunnerName.OPENCODE: (
        """printf '%s\\n' '{"type":"step_start","sessionID":"SID","part":"""
        """{"type":"step-start"}}'
printf '%s\\n' '{"type":"step_finish","sessionID":"SID","part":"""
        """{"type":"step-finish","reason":"stop","cost":0.25,"""
        """"tokens":{"input":11,"output":22}}}'
"""
    ),
}

GRANDCHILD_PID_FILE: Final[str] = "grandchild.pid"
_GRANDCHILD: Final[str] = f"""
# A process the runner spawned, which the wrapper never knew about. It reports
# its pid through the artifact channel because that is the only writable place
# a sandboxed child has, and it outlives the stub unless the whole GROUP is
# signalled — which is the property a termination test needs.
sh -c 'while :; do sleep 0.2; done' &
printf '%s' "$!" > "$WF_ARTIFACT_DIR/{GRANDCHILD_PID_FILE}"
"""

FD0_FILE: Final[str] = "fd0.txt"
_FD0_PROBE: Final[str] = f"""
# What the launcher left on the child's fd 0 (M9). `readlink` on /proc/self/fd/0
# names the open file itself, so this is the child's own view of its stdin.
readlink /proc/self/fd/0 > "$WF_ARTIFACT_DIR/{FD0_FILE}"
"""

PUSH_PROBE_REMOTES: Final[tuple[tuple[str, str], ...]] = (
    ("origin", "https://github.example.invalid/wf/repo.git"),
    ("scp", "deploy@github.example.invalid:wf/repo.git"),
    ("ftp", "ftp://github.example.invalid/wf/repo.git"),
    ("localpath", "/srv/mirrors/wf/repo.git"),
)
"""Four remote spellings, three of which a prefix enumeration used to miss (R3).

`deploy@host:path` is scp-style with a user other than `git` — the ordinary CI
form — and neither it, nor `ftp://`, nor a bare local path started with any of
the five prefixes the backstop used to list."""
PUSH_PROBE_FILE: Final[str] = "push-url.txt"

_PUSH_PROBE: Final[str] = f"""
# What a `git push <remote>` in this child would ACTUALLY talk to, for EVERY
# remote the repo names. `git remote get-url --push` applies the same
# `pushInsteadOf` rewriting a push does, and answers offline — so the bound is
# observable without a network at all.
for name in $(git -C "$WF_PUSH_REPO" remote); do
  printf '%s %s\n' "$name" \
    "$(git -C "$WF_PUSH_REPO" remote get-url --push "$name")" \
    >> "$WF_ARTIFACT_DIR/{PUSH_PROBE_FILE}"
done
set +e
git -C "$WF_PUSH_REPO" push --dry-run origin main >> "$WF_ARTIFACT_DIR/{PUSH_PROBE_FILE}" 2>&1
printf 'push_rc=%s\n' "$?" >> "$WF_ARTIFACT_DIR/{PUSH_PROBE_FILE}"
set -e
"""
"""Run inside the forked child, in the environment the PROFILE built (M5b)."""

STUB_SESSION: Final[str] = "stub-session-id"
DEFAULT_MARKER: Final[str] = '{"outcome":"done"}'
DEFAULT_EFFECTS: Final[str] = '{"paths":[]}'


def write_stub(
    directory: Path,
    runner: RunnerName,
    *,
    session_id: str = STUB_SESSION,
    exit_code: int = 0,
    channels: bool = True,
    forge: bool = False,
    sleep_s: float = 0.0,
    push_probe: bool = False,
    fd0_probe: bool = False,
    grandchild: bool = False,
) -> Path:
    """Write an executable stub for one vendor and return its path.

    `forge` makes the child attempt every write B2 says a runner must not be
    able to make, addressed the only way a sandboxed child could address them —
    relative to the directory it was granted. `sleep_s` parks the child alive
    after it has written its channels, which is what a §8.1 steer needs to have
    something to kill.
    """
    body = STUB_BODIES[runner].replace("SID", session_id)
    source = (
        _PREAMBLE
        + body
        + (_CHANNELS if channels else "")
        + (_FORGE if forge else "")
        + (_PUSH_PROBE if push_probe else "")
        + (_FD0_PROBE if fd0_probe else "")
        + (_GRANDCHILD if grandchild else "")
        + (f"sleep {sleep_s}\n" if sleep_s else "")
        + f"exit {exit_code}\n"
    )
    path = directory / f"stub-{runner.value}"
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)
    return path


def stub_env(
    marker: str = DEFAULT_MARKER, effects: str = DEFAULT_EFFECTS
) -> dict[str, str]:
    """The extra passthrough keys the stubs read their channel payloads from."""
    return {"WF_MARKER": marker, "WF_EFFECTS": effects}


def profile_host_env() -> dict[str, str]:
    """The stand-in host environment, for a test asserting what is NOT in it."""
    return dict(HOST_ENV)


def host_env_with(**extra: str) -> dict[str, str]:
    """The stand-in host environment plus whatever a stub needs."""
    return {**HOST_ENV, "PATH": os.environ.get("PATH", "/usr/bin:/bin"), **extra}


# --- the process lab -----------------------------------------------------

PASSTHROUGH: Final[tuple[str, ...]] = ("PATH", "HOME", "WF_MARKER", "WF_EFFECTS")
"""The stubs read their channel payloads out of the environment, which also
exercises the passthrough allow-list on a real child."""

PARKED_S: Final[float] = 30.0
"""How long a `dispatch()` child stays alive when the test needs one to kill.
The fixture ends every one of them, so nothing outlives the test."""


def add_remote(repo: Path, name: str, url: str) -> None:
    """Give a throwaway repo a remote the backstop has to rewrite."""
    subprocess.run(
        ["git", "remote", "add", name, url],
        cwd=repo,
        check=True,
        capture_output=True,
        timeout=GIT_TIMEOUT_S,
    )


def task_builder(
    cwd: Path,
    node: Node,
    *,
    effort: str | None = None,
    fallback_models: tuple[str, ...] = (),
) -> TaskBuilder:
    """A `TaskBuilder` that supplies a brief, which a real profile requires."""

    def build(activation: ActivationRecord, channels: RunnerChannels) -> TaskSpec:
        return TaskSpec(
            root_id=activation.metadata.wf_root_id,
            activation_id=activation.activation_id,
            node=node.name,
            model=activation.metadata.model,
            effort=effort,
            fallback_models=fallback_models,
            writes=bool(node.writes),
            allowed_paths=node.allowed_paths or (),
            cwd=str(cwd),
            channels=channels,
            brief=BRIEF,
        )

    return build


class Lab:
    """One instance wired to run a real profile against a stub vendor CLI."""

    def __init__(
        self, tmp_path: Path, *, sandbox: SandboxMode = SandboxMode.BWRAP
    ) -> None:
        self.tmp_path = tmp_path
        self.repo = make_repo(tmp_path)
        self.base = head_of(self.repo)
        self.config = make_config(self.repo, tmp_path, fake_proc=False, sandbox=sandbox)
        self.fake_bd, self.store = make_store(tmp_path, self.base)
        self.root = make_root(self.store, self.repo, "profiles-instance")
        self.paths = make_paths(self.config, self.root.root_id)
        self.clock = FrozenClock()
        self.git = make_git(self.config)
        self.workspace = make_workspace(self.paths, self.git, self.clock)
        self.supervisor = Supervisor(
            self.config, self.paths, self.git, self.store, self.workspace, self.clock
        )
        self.steerer = Steerer(self.config, self.paths, self.store, self.clock)
        self.bin = tmp_path / "bin"
        self.bin.mkdir(exist_ok=True)
        self.children: list[ProcessHandle] = []
        """Every child `dispatch()` parked, so the fixture can end them all.

        A `dispatch()` child is `setsid`-detached and sleeping; without this a
        failing assertion would leave it running for its full sleep."""

    def ensure_worktree(self) -> None:
        """Create the instance worktree the way §5.4 does, if it is not there.

        A REAL `git worktree add`, not a bare `mkdir`: `dispatch()` runs with no
        precondition, and `_child` chdirs into the checkout before exec, so it
        has to exist. A bare directory used to do — until the §2 mount bound
        started pre-creating the node's grants inside the checkout, which left a
        NON-EMPTY directory that a later `Workspace._ensure_tree` could no
        longer `git worktree add` into. Making the rig's shortcut produce the
        same shape production does removes the divergence rather than papering
        over it, and it also gives `plan_for` the worktree shape to bind.
        """
        worktree = self.paths.worktree
        if (worktree / ".git").exists():
            return
        worktree.parent.mkdir(parents=True, exist_ok=True)
        self.git.worktree_add(
            worktree,
            BRANCH_TEMPLATE.format(root_id=self.paths.root_id),
            self.base,
            cwd=self.repo,
        )

    def cleanup(self) -> None:
        """End and reap every parked child, whatever the test did."""
        for handle in self.children:
            try:
                os.killpg(handle.pgid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                continue
            procfs.reap(handle.pid)

    def profile(self, runner: RunnerName, binary: Path | str) -> Profile:
        """A real profile whose vendor binary is the stub (or a missing path)."""
        config = ProfileConfig(
            binary_overrides={runner: str(binary)}, passthrough_env=PASSTHROUGH
        )
        registry = ProfileRegistry(config, self.clock, host_env_with(**stub_env()))
        return registry.profile_for(runner.value)

    def run(
        self,
        runner: RunnerName,
        *,
        request: MintRequest | None = None,
        writes: bool = True,
        marker: str = DEFAULT_MARKER,
        effects: str = DEFAULT_EFFECTS,
        binary: Path | str | None = None,
        exit_code: int = 0,
        channels: bool = True,
        forge: bool = False,
    ) -> SupervisionResult:
        """Dispatch one activation for real and watch it to `exit-recorded`.

        Always the graph's ENTRY node, because an entry mint may target no other
        one (§3.2); `writes` is flipped on a copy of it so both danger-default
        modes are reachable without staging a whole rejected round first.

        `request` is what a §8.1 continuation comes in as: the `MintRequest`
        `Steerer` produced, and nothing else. Whether the composition can then
        reach `build_resume_command` is the property the continuity family
        tests, so it is deliberately NOT given the instructions here.
        """
        stub = binary or write_stub(
            self.bin, runner, exit_code=exit_code, channels=channels, forge=forge
        )
        node = node_of(self.root.definition.document, IMPLEMENT).model_copy(
            update={"writes": writes}
        )
        config = ProfileConfig(
            binary_overrides={runner: str(stub)}, passthrough_env=PASSTHROUGH
        )
        registry = ProfileRegistry(
            config,
            self.clock,
            host_env_with(**stub_env(marker=marker, effects=effects)),
        )
        return self.supervisor.run(
            request or entry_mint(session_id=str(uuid.uuid4())),
            node,
            registry.profile_for(runner.value),
            task_builder(self.paths.worktree, node),
            pinned_digests=pinned_verifier_digests(self.root),
        )

    def dispatch(
        self,
        runner: RunnerName,
        *,
        request: MintRequest | None = None,
        session_id: str = STUB_SESSION,
        instructions: str | None = None,
        writes: bool = True,
        sleep_s: float = PARKED_S,
        push_probe: bool = False,
        fd0_probe: bool = False,
        grandchild: bool = False,
        extra_env: dict[str, str] | None = None,
        effort: str | None = None,
        fallback_models: tuple[str, ...] = (),
    ) -> DispatchResult:
        """Run §5.2 phase B alone, with no watch loop over the child.

        `Supervisor.run` also monitors and grades, and its `Monitor` advances the
        FrozenClock a poll interval per cycle — so a child that does anything
        slower than a `printf` is TERMed for a `max_wall` breach that took
        milliseconds of real time. A §8.1 steer needs a LIVE child and a `git`
        probe needs an undisturbed one; both get the real fork barrier, the real
        receipt and the real exec ledger, one layer down.
        """
        extra = extra_env or {}
        self.ensure_worktree()
        stub = write_stub(
            self.bin,
            runner,
            session_id=STUB_SESSION,
            sleep_s=sleep_s,
            push_probe=push_probe,
            fd0_probe=fd0_probe,
            grandchild=grandchild,
        )
        node = node_of(self.root.definition.document, IMPLEMENT).model_copy(
            update={"writes": writes}
        )
        config = ProfileConfig(
            binary_overrides={runner: str(stub)},
            passthrough_env=(*PASSTHROUGH, *sorted(extra)),
        )
        registry = ProfileRegistry(
            config, self.clock, host_env_with(**stub_env(), **extra)
        )
        dispatcher = Dispatcher(self.paths, self.store, self.clock)
        result = dispatcher.dispatch(
            request or entry_mint(session_id=session_id),
            registry.profile_for(runner.value),
            task_builder(
                self.paths.worktree,
                node,
                effort=effort,
                fallback_models=fallback_models,
            ),
            instructions=instructions,
        )
        if result.handle is not None:
            self.children.append(result.handle)
        return result

    def await_exit(self, handle: ProcessHandle) -> int:
        """Reap a child dispatched to run to completion, and report its status.

        Returned rather than discarded: a child that died in `_child`'s setup
        writes nothing at all, and a test asserting on files it never created
        reads as a missing file rather than as a child that never ran.
        """
        try:
            _, status = os.waitpid(handle.pid, 0)
        except ChildProcessError:  # pragma: no cover - already reaped
            return 0
        return os.waitstatus_to_exitcode(status)
