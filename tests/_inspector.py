"""Builders and doubles shared by the inspector test families (not a test module).

Three things live here, because every inspector family needs all three:

- **`FakeProfile`** — the §6 test double, scripted rather than mocked: it
  builds a real `/bin/sh` command out of a declarative script (emit log bytes,
  write a marker, hang, ignore TERM, exit with a code) and execs it through the
  inspector's OWN launcher. Nothing here fakes the fork barrier; a double that
  did would prove nothing about the thing being tested.
- **A throwaway git repo** with a verify script, so the §5.4/§7 families work
  against real `git` behaviour rather than a stubbed `Git`.
- **A fake `/proc`** — a directory of `<pid>/stat` files and a `boot_id`, so
  liveness, PID reuse and reboots can be expressed as data instead of as real
  processes that must actually be running at assertion time.

Nothing here touches this repo's `.beads`: bd is `FakeBd` over the real
transport, exactly as the phase-2 families use it.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from collections.abc import Callable, Iterable, Iterator, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Final

from pydantic import BaseModel, ConfigDict

from tests._bdio import RESOLVED_CONFIG, load_definition
from tests._fake_bd import FakeBd
from workflow_interpreter.bdio import (
    ActivationRecord,
    ConfigSource,
    MintReason,
    MintRequest,
    ProcessHandle,
    ResolvedSetting,
    RootRecord,
    Usage,
    WorkflowStore,
)
from workflow_interpreter.bdio.rpc_records import SessionRegistration
from workflow_interpreter.bdio.wire import NodeSetting, resolved_settings
from workflow_interpreter.contracts.execution import (
    EXECUTION_POLICY_KEY,
    ToolNetwork,
)
from workflow_interpreter.contracts.sessions import execution_policy_digest
from workflow_interpreter.inspector import (
    BandLock,
    ChildLauncher,
    CrewChannels,
    CrewCommand,
    CrewEvent,
    EventType,
    InspectorConfig,
    TaskSpec,
    TerminalEnvelope,
    Workspace,
    WrapperPaths,
)
from workflow_interpreter.inspector.channels import (
    COMMITTER_NAME,
    ENV_GIT_COMMITTER_EMAIL,
    ENV_GIT_COMMITTER_NAME,
    VERIFIER_DIGEST_KEY,
    crew_committer_email,
    sha256_file,
)
from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.inspector.paths import write_durable
from workflow_interpreter.ledger.claims import LedgerClaims
from workflow_interpreter.ledger.database import open_ledger
from workflow_interpreter.ledger.store import LedgerStore
from workflow_interpreter.schema.models import GraphDocument, Node
from workflow_interpreter.tracker.bd_transport import CompletedCommand

TEST_ACTOR: Final[str] = "wf-test-inspector"
TEST_HOST: Final[str] = "lab"
BOOT_ID: Final[str] = "boot-0000-1111"
START_TIME: Final[str] = "424242"
SESSION_ID: Final[str] = "sess-super-1"
IMPLEMENT: Final[str] = "implement"
REVIEW: Final[str] = "review"
VERIFY_SCRIPT: Final[str] = "scripts/verify-feature.sh"
REVIEW_SCRIPT: Final[str] = "scripts/review-checks.sh"
DEBRIEF_SCRIPT: Final[str] = "scripts/verify-debrief.sh"
DEBRIEF: Final[str] = "debrief"
DEBRIEF_MARKER: Final[str] = '{"outcome":"no_diff"}\n'
NO_EFFECTS: Final[str] = '{"paths":[]}'
SHELL: Final[str] = "/bin/sh"
GIT_TIMEOUT_S: Final[float] = 60.0

HUMAN_NAME: Final[str] = "wf test"
HUMAN_EMAIL: Final[str] = "wf@test"
ENV_GIT_AUTHOR_NAME: Final[str] = "GIT_AUTHOR_NAME"
ENV_GIT_AUTHOR_EMAIL: Final[str] = "GIT_AUTHOR_EMAIL"
HUMAN_IDENTITY: Final[dict[str, str]] = {
    ENV_GIT_AUTHOR_NAME: HUMAN_NAME,
    ENV_GIT_AUTHOR_EMAIL: HUMAN_EMAIL,
    ENV_GIT_COMMITTER_NAME: HUMAN_NAME,
    ENV_GIT_COMMITTER_EMAIL: HUMAN_EMAIL,
}
"""The human identity every throwaway repo commits under, as ENVIRONMENT.

Repo config alone was not enough: `GIT_COMMITTER_EMAIL` OVERRIDES `user.email`,
and the wrapper exports the §7.4 crew identity into every child environment
— so a suite run from inside an activation committed as `crew+<id>@...` and
`test_commit_helpers_reject_non_commits_and_git_failures` failed on it
(cr-o85.34.22, phase-7 live D2)."""

PASSING_SCRIPT: Final[str] = "#!/bin/sh\nexit 0\n"
FAILING_SCRIPT: Final[str] = "#!/bin/sh\nexit 1\n"


# --- clock ---------------------------------------------------------------


class FrozenClock:
    """A clock the test moves by hand; `sleep` advances it instead of blocking.

    Every wrapper deadline (`stale_after`, `max_wall`, the TERM grace) is a
    function of this, so a drill about a 45-minute runaway costs microseconds
    and cannot flake.
    """

    def __init__(
        self, start: datetime | None = None, *, real_sleep_s: float = 0.0
    ) -> None:
        self.current = start or datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
        self.sleeps: list[float] = []
        self.on_sleep: list[Callable[[], None]] = []
        self.real_sleep_s = real_sleep_s
        """Nonzero only where a REAL process has to be given real time to die
        (`procfs.terminate`'s TERM/KILL grace); every other deadline in the
        wrapper is pure arithmetic over `now()`."""

    def now(self) -> datetime:
        """The current (frozen) time."""
        return self.current

    def sleep(self, seconds: float) -> None:
        """Advance time and fire any one-shot callback the test registered."""
        self.sleeps.append(seconds)
        self.current += timedelta(seconds=seconds)
        if self.real_sleep_s:
            time.sleep(self.real_sleep_s)
        if self.on_sleep:
            self.on_sleep.pop(0)()

    def advance(self, seconds: float) -> None:
        """Move the clock forward without sleeping."""
        self.current += timedelta(seconds=seconds)


# --- fake /proc ----------------------------------------------------------


def make_fake_proc(root: Path, boot_id: str = BOOT_ID) -> tuple[Path, Path]:
    """Create a fake `/proc` root and `boot_id` file; return both paths."""
    proc_root = root / "proc"
    proc_root.mkdir(parents=True, exist_ok=True)
    boot_path = root / "boot_id"
    boot_path.write_text(f"{boot_id}\n", encoding="utf-8")
    return proc_root, boot_path


def write_proc_entry(
    proc_root: Path, pid: int, start_time: str = START_TIME, state: str = "S"
) -> None:
    """Write a `/proc/<pid>/stat` whose comm deliberately contains `) ` noise."""
    entry = proc_root / str(pid)
    entry.mkdir(parents=True, exist_ok=True)
    # Fields 3..24, i.e. everything after the `pid (comm)` prefix. Index 0 is
    # the state and index 19 is field 22, the start time (`procfs.py`).
    fields = [str(value) for value in range(3, 25)]
    fields[0] = state
    fields[19] = start_time
    (entry / "stat").write_text(
        f"{pid} (weird ) name) {' '.join(fields)}\n", encoding="utf-8"
    )


def remove_proc_entry(proc_root: Path, pid: int) -> None:
    """Make a process disappear, the way an exit does."""
    stat = proc_root / str(pid) / "stat"
    if stat.exists():
        stat.unlink()
        stat.parent.rmdir()


def dead_pid() -> int:
    """A pid that is provably not in use: forked, exited and reaped."""
    pid = os.fork()
    if pid == 0:  # pragma: no cover - child
        os._exit(0)
    os.waitpid(pid, 0)
    return pid


# --- git repo ------------------------------------------------------------


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    """Run git in a throwaway repo with an explicit timeout and identity.

    `HUMAN_IDENTITY` is merged BEFORE the caller's `env`, so `crew_git` still
    commits as the crew while everything else is pinned to the human.
    """
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_S,
        env={**os.environ, **HUMAN_IDENTITY, **(env or {})},
    )
    return completed.stdout.strip()


def make_repo(tmp_path: Path, name: str = "repo") -> Path:
    """A throwaway git repo with one commit and the fixture's verify scripts.

    It carries no `.wf/repo-id`: that file is minted by the first ledger open
    (store-restructure §3.6), so a repository nothing has run against yet does
    not have one, and every lab built on this repo therefore exercises the real
    FIRST-run path rather than a checkout whose id was already committed.
    """
    repo = tmp_path / name
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "--quiet", "--initial-branch=main")
    _git(repo, "config", "user.email", HUMAN_EMAIL)
    _git(repo, "config", "user.name", HUMAN_NAME)
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "scripts").mkdir(exist_ok=True)
    (repo / "src").mkdir(exist_ok=True)
    for script in (VERIFY_SCRIPT, REVIEW_SCRIPT, DEBRIEF_SCRIPT):
        path = repo / script
        path.write_text(PASSING_SCRIPT, encoding="utf-8")
        path.chmod(0o755)
    (repo / "src" / "feature.py").write_text("value = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "initial")
    return repo


def head_of(repo: Path) -> str:
    """The repo's current HEAD commit."""
    return _git(repo, "rev-parse", "HEAD")


def commit_all(repo: Path, message: str) -> str:
    """Commit everything in a throwaway repo, as the HUMAN's own identity."""
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", message)
    return head_of(repo)


def crew_git(repo: Path, *args: str, activation_id: str) -> str:
    """Run one raw git command under the §7.4 crew identity.

    `crew_commit` is the whole-worktree version and stages with `add -A`. A
    test that forges the INDEX alone — `rm --cached`, `update-index
    --cacheinfo` — needs the identity without the staging, because `add -A`
    would put the very file back that the forgery removed.
    """
    return _git(
        repo,
        *args,
        env={
            ENV_GIT_COMMITTER_NAME: COMMITTER_NAME,
            ENV_GIT_COMMITTER_EMAIL: crew_committer_email(activation_id),
        },
    )


def crew_commit(repo: Path, message: str, activation_id: str) -> str:
    """Commit everything under the §7.4 identity a real crew would carry.

    The wrapper stamps `GIT_COMMITTER_*` onto the child's environment
    (`CrewChannels.env()`), so a test that wants a commit `pin_artifact` can
    ATTRIBUTE has to make it the way the child would. Using the repo's own
    `user.email` instead produces exactly the human's commit — which is the case
    the authorship half of §7.4 exists to refuse.
    """
    _git(repo, "add", "-A")
    _git(
        repo,
        "commit",
        "--quiet",
        "-m",
        message,
        env={
            ENV_GIT_COMMITTER_NAME: COMMITTER_NAME,
            ENV_GIT_COMMITTER_EMAIL: crew_committer_email(activation_id),
        },
    )
    return head_of(repo)


def blob_at(repo: Path, commit: str, path: str) -> str:
    """One file's contents inside a commit — how a human recovers from a snapshot.

    Deliberately raw `git`, and deliberately unstripped: the inspector's own
    transport has no `show`, and the question here is whether the EXACT bytes
    are retrievable by somebody who only has the ref.
    """
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_S,
    )
    return completed.stdout


def tree_modes(repo: Path, commit: str) -> dict[str, str]:
    """Return each recursive tree path's Git mode for snapshot assertions."""
    entries: dict[str, str] = {}
    for record in _git(repo, "ls-tree", "-r", "-z", commit).split("\0"):
        if not record:
            continue
        header, _, path = record.partition("\t")
        mode, _, _ = header.split(maxsplit=2)
        entries[path] = mode
    return entries


def add_submodule(repo: Path, name: str) -> Path:
    """Add a committed local submodule without modifying the fixture factory."""
    source = repo.parent / f"{name}-source"
    source.mkdir()
    _git(source, "init", "--quiet", "--initial-branch=main")
    _git(source, "config", "user.email", "wf@test")
    _git(source, "config", "user.name", "wf test")
    (source / "module.txt").write_text("module\n", encoding="utf-8")
    _git(source, "add", "-A")
    _git(source, "commit", "--quiet", "-m", "initial")
    _git(
        repo, "-c", "protocol.file.allow=always", "submodule", "add", str(source), name
    )
    return source


# --- inspector wiring ---------------------------------------------------


def make_config(
    repo: Path, tmp_path: Path, *, fake_proc: bool = True, **overrides: object
) -> InspectorConfig:
    """A `InspectorConfig` for a throwaway repo, with `.wf/` beside it."""
    values: dict[str, object] = {
        "repo_root": repo,
        "wrapper_root": tmp_path / ".wf",
        "host": TEST_HOST,
        "term_grace_s": 2.0,
        "kill_grace_s": 2.0,
        "poll_interval_s": 1.0,
        "barrier_timeout_s": 10.0,
    }
    if fake_proc:
        proc_root, boot_path = make_fake_proc(tmp_path / "sys")
        values["proc_root"] = proc_root
        values["boot_id_path"] = boot_path
    values.update(overrides)
    return InspectorConfig.model_validate(values)


LAB_TASK: Final[str] = "cr-3411.2"
LAB_EPIC: Final[str] = "cr-3411"


def make_store(
    tmp_path: Path, head: str, state: Path | None = None
) -> tuple[LedgerStore, WorkflowStore]:
    """A ledger plus the typed store over it, wired to a git head.

    `state` names the database file, which is how TWO PROCESSES share a store
    (`make_persistent_store`). Before S6 that took a `PersistentBd` saving
    in-memory rows to JSON around every command; the record store is SQLite
    now, so sharing it is naming the same path.
    """
    repo_root = tmp_path / "store-repo"
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    wrapper_root = tmp_path / "store-wrapper"
    wrapper_root.mkdir(parents=True, exist_ok=True)
    database = open_ledger(
        repo_root,
        wrapper_root,
        path=tmp_path / "store-ledger.db" if state is None else state,
    )
    backend = LedgerStore(database, task_id=LAB_TASK, epic_id=LAB_EPIC)
    return backend, WorkflowStore(
        backend,
        branch_head_reader=lambda: head,
        claims=LedgerClaims(database),
    )


class PersistentBd(FakeBd):
    """A `FakeBd` whose rows live in a JSON file instead of in one process.

    Exists for exactly one property: the inspector is supposed to keep
    recording after the process that started it is gone, and proving that needs
    a SEPARATE process whose bd writes the test can still read. An in-memory
    double cannot express that at all — the rows die with the wrapper.

    Load-before / save-after each command, which is enough because the wrapper
    and the test never run a command at the same time (the test waits on a
    sentinel file).
    """

    def __init__(self, workspace: str, state: Path) -> None:
        super().__init__(workspace)
        self._state = state
        self._restore()

    def __call__(self, argv: Sequence[str], timeout_s: float) -> CompletedCommand:
        """Run one bd argv against the shared on-disk rows."""
        self._restore()
        result = super().__call__(argv, timeout_s)
        write_durable(
            self._state,
            json.dumps({"rows": self.rows}).encode("utf-8"),
        )
        return result

    def _restore(self) -> None:
        """Adopt whatever another process last wrote."""
        if not self._state.exists():
            return
        stored = json.loads(self._state.read_text(encoding="utf-8"))
        self.rows = stored["rows"]


def make_persistent_store(
    tmp_path: Path, head: str, state: Path
) -> tuple[LedgerStore, WorkflowStore]:
    """A store two processes can share, by naming one database file."""
    return make_store(tmp_path, head, state)


def verifier_pins(repo: Path, node_name: str, *scripts: str) -> dict[str, str]:
    """The §7.3 pinned digests for a node's verify scripts, as instantiated."""
    return {
        VERIFIER_DIGEST_KEY.format(node=node_name, program=script): sha256_file(
            repo / script
        )
        or ""
        for script in scripts
    }


def pinned_config(repo: Path) -> tuple[ResolvedSetting, ...]:
    """The §3.1 resolved config plus the §7.3 verify digests for the fixture."""
    digests = {
        **verifier_pins(repo, IMPLEMENT, VERIFY_SCRIPT),
        **verifier_pins(repo, REVIEW, VERIFY_SCRIPT, REVIEW_SCRIPT),
    }
    return (
        *RESOLVED_CONFIG,
        *(
            ResolvedSetting(key=key, value=value, source=ConfigSource.PROJECT_CONFIG)
            for key, value in sorted(digests.items())
        ),
    )


def make_root(store: WorkflowStore, repo: Path, instance_key: str) -> RootRecord:
    """Pin the §2 fixture graph into the in-memory bd workspace."""
    return store.create_root(
        instance_key=instance_key,
        definition=load_definition(),
        resolved_config=pinned_config(repo),
    )


def node_of(document: GraphDocument, name: str) -> Node:
    """One node of the pinned graph, by name."""
    return next(node for node in document.node if node.name == name)


def entry_mint(node: str = IMPLEMENT, **overrides: object) -> MintRequest:
    """An entry mint request for the fixture's entry node."""
    base: dict[str, object] = {
        "node": node,
        "mint_reason": MintReason.ENTRY,
        "crew_profile": "fake",
        "model": "fake-model",
        "session_id": SESSION_ID,
    }
    return MintRequest.model_validate(base | overrides)


def make_paths(config: InspectorConfig, root_id: str) -> WrapperPaths:
    """The wrapper directory for one instance."""
    return WrapperPaths(config, root_id)


def make_git(config: InspectorConfig) -> Git:
    """The inspector's git transport for a throwaway repo."""
    return Git(config)


def make_workspace(
    paths: WrapperPaths,
    git: Git,
    clock: FrozenClock,
    *,
    advance_branch: bool = False,
) -> Workspace:
    """Create a workspace with its one required execution band."""
    return Workspace(
        paths, git, clock, BandLock(paths.band_lock), advance_branch=advance_branch
    )


def observe_session(
    store: WorkflowStore,
    activation: ActivationRecord,
    *,
    thread_id: str | None = None,
) -> ActivationRecord:
    """Register the vendor identity event a live child would have emitted.

    Resume history is built only from an OBSERVED session (§5.2): a preassigned
    id proves nothing, so a lab that dispatches a scripted child rather than a
    real vendor has to mirror the identity event itself before anything may
    resume it — which is what the resident inspector does off the child's log.

    The default `thread_id` is the id the launch already carries, because that
    is what a vendor honouring a caller-supplied session answers with.
    """
    metadata = activation.metadata
    thread_id = thread_id or metadata.session_id or SESSION_ID
    settings = resolved_settings(store.reads.load_root(metadata.wf_root_id).metadata)
    effort = settings.get(NodeSetting.EFFORT.at(metadata.node))
    policy = settings.get(EXECUTION_POLICY_KEY.format(node=metadata.node), "legacy")
    assert metadata.handle is not None
    assert metadata.launch_id is not None
    return store.register_session(
        activation.activation_id,
        SessionRegistration(
            root_id=metadata.wf_root_id,
            activation_id=activation.activation_id,
            launch_id=metadata.launch_id,
            handle=metadata.handle,
            thread_id=thread_id,
            crew_profile=metadata.crew_profile,
            model=metadata.model,
            effort=str(effort),
            policy_digest=execution_policy_digest(str(policy)),
            state_path="",
        ),
    )


def handle_for(
    pid: int,
    *,
    started_at: str = "2026-08-25T12:00:00Z",
    boot_id: str = BOOT_ID,
    start_time: str = START_TIME,
    log_path: str = "/dev/null",
) -> ProcessHandle:
    """A §5.3 handle pointing at a (possibly fake) process."""
    return ProcessHandle(
        pid=pid,
        pgid=pid,
        host=TEST_HOST,
        host_boot_id=boot_id,
        proc_start_time=start_time,
        started_at=started_at,
        log_path=log_path,
        session_id=SESSION_ID,
    )


# --- the §6 test double --------------------------------------------------


class ChildScript(BaseModel):
    """A declarative description of what the fake crew's child does."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    emit: str = ""
    """Text appended to the crew log, one line at a time."""
    marker: str | None = None
    """Raw bytes written to `$WF_OUTCOME_FILE` (raw, so drill 15's zero/two
    marker sub-cases are expressible)."""
    effects: str | None = None
    """Raw bytes written to `$WF_EFFECTS_FILE`."""
    write_path: str | None = None
    """One worktree-relative file written by the child for artifact drills."""
    write_body: str = ""
    write_files: tuple[tuple[str, str], ...] = ()
    """Further worktree-relative `(path, body)` files, parents created.

    A debrief writes three files into one directory, which a single
    `write_path` cannot express."""
    commit: bool = False
    """Commit the written artifact with the wrapper's crew identity."""
    artifact_path: str | None = None
    """One wrapper-artifact-relative finding written by a non-writing child."""
    artifact_body: str = ""
    sleep_s: float = 0.0
    assert_clean_tree: bool = False
    """Spec:857-859, injection point 4: have the CHILD observe its OWN
    worktree before it does anything else. Only the crew's own process can
    see whether its worktree is genuinely clean at start — a `git reset
    --hard` the orchestrator ran before dispatch only touches tracked paths,
    so an untracked or otherwise unstaged leftover can survive it invisibly
    to any outside observer that only ever diffs committed trees. This
    fails the CHILD, from inside, before it writes or commits anything."""
    ignore_term: bool = False
    """Drill 19: the child traps TERM and loops, so only KILL can end it.

    The trap alone is not enough — a trapped `sh` still dies when the `sleep`
    it is waiting on is killed by the same group signal — so the child loops
    over short sleeps instead of waiting on one long one.
    """
    exit_code: int = 0

    def shell(self) -> str:
        """Render the script as `sh` source."""
        lines = [] if self.ignore_term else ["set -e"]
        if self.ignore_term:
            lines.append("trap '' TERM")
        if self.assert_clean_tree:
            lines.append('dirty="$(git status --porcelain)"')
            lines.append('if [ -n "$dirty" ]; then printf %s "$dirty" >&2; exit 1; fi')
        if self.emit:
            lines.append(f"printf '%s' {_quote(self.emit)}")
        if self.marker is not None:
            lines.append(f'printf %s {_quote(self.marker)} > "$WF_OUTCOME_FILE"')
        if self.effects is not None:
            lines.append(f'printf %s {_quote(self.effects)} > "$WF_EFFECTS_FILE"')
        if self.write_path is not None:
            lines.append(
                f"printf %s {_quote(self.write_body)} > {_quote(self.write_path)}"
            )
        for path, body in self.write_files:
            lines.append(f"mkdir -p -- {_quote(str(PurePosixPath(path).parent))}")
            lines.append(f"printf %s {_quote(body)} > {_quote(path)}")
        if self.commit:
            written = [
                *([] if self.write_path is None else [self.write_path]),
                *(path for path, _ in self.write_files),
            ]
            if not written:
                raise ValueError("a committing ChildScript needs something written")
            for path in written:
                lines.append(f"git add -- {_quote(path)}")
            lines.append("git commit --quiet -m 'crew artifact'")
        if self.artifact_path is not None:
            destination = f'"$WF_ARTIFACT_DIR"/{_quote(self.artifact_path)}'
            lines.append(f'mkdir -p "$(dirname {destination})"')
            lines.append(f"printf %s {_quote(self.artifact_body)} > {destination}")
        if self.ignore_term:
            lines.append("while :; do sleep 0.2; done")
        elif self.sleep_s:
            lines.append(f"sleep {self.sleep_s}")
        lines.append(f"exit {self.exit_code}")
        return "\n".join(lines)


def _quote(text: str) -> str:
    """Single-quote a string for `sh`."""
    escaped = text.replace("'", "'\\''")
    return f"'{escaped}'"


class FakeProfile:
    """A scriptable §6 profile: real `/bin/sh` children, real inspector launcher."""

    tool_network = ToolNetwork.NOT_ENFORCED

    def __init__(
        self,
        script: ChildScript | None = None,
        *,
        session_id: str = SESSION_ID,
    ) -> None:
        self.script = script or ChildScript()
        self.session_id = session_id
        self.launched: list[CrewCommand] = []
        self.bypass_launcher = False
        """Set by the test that asserts the wrapper CATCHES a profile which
        refuses to exec through the injected launcher (§5.2, §6)."""

    def name(self) -> str:
        """The profile identifier."""
        return "fake"

    def prepare(self, activation: ActivationRecord) -> str:
        """The pre-assigned session id (§5.2)."""
        return self.session_id

    def build_command(self, task: TaskSpec, session_id: str) -> CrewCommand:
        """A `/bin/sh -c <script>` invocation carrying the three §6 channels."""
        return CrewCommand(
            argv=(SHELL, "-c", self.script.shell()),
            env={"PATH": "/usr/bin:/bin", **task.channels.env()},
            cwd=task.cwd,
            log_path=task.channels.log_path,
            session_id=session_id,
        )

    def launch(self, command: CrewCommand, launcher: ChildLauncher) -> ProcessHandle:
        """Exec through the inspector's launcher, unless the test says otherwise."""
        self.launched.append(command)
        if self.bypass_launcher:
            return handle_for(dead_pid(), log_path=command.log_path)
        return launcher(command)

    def collect_terminal_envelope(self, handle: ProcessHandle) -> TerminalEnvelope:
        """Usage is unknown, which §6 says is legal."""
        return TerminalEnvelope(
            usage=Usage(known=False), session_id=handle.session_id, duration_s=1.0
        )

    def build_resume_command(
        self, session_id: str, instructions: str, task: TaskSpec
    ) -> CrewCommand:
        """The steer continuation's invocation, bounded by the continuation's task.

        Signature follows the §6 Protocol's M4 change: the task is passed in
        rather than remembered, so this double runs its child in the SAME place
        and with the same channels a launch would.
        """
        return CrewCommand(
            argv=(SHELL, "-c", self.script.shell()),
            env={"PATH": "/usr/bin:/bin", **task.channels.env()},
            cwd=task.cwd,
            log_path=task.channels.log_path,
            session_id=session_id,
        )

    def build_resume_hint(self, session_id: str) -> str:
        """A human-pasteable resume line."""
        return f"fake --resume {session_id}"

    def parse_output(self, stream: Iterable[str]) -> Iterator[CrewEvent]:
        """Normalize the stream; the fake crew emits plain text."""
        return iter(CrewEvent(type=EventType.MESSAGE, text=line) for line in stream)

    def qualify_cli(self, version: str | None, error: str | None = None) -> None:
        """Accept the registry's qualification; the fake crew has no binary."""

    def cli_version(self) -> str | None:
        """No vendor CLI, so no probed version."""
        return None

    def cli_version_error(self) -> str | None:
        """No vendor CLI, so nothing failed to probe."""
        return None


def task_builder(
    cwd: Path,
    node: Node,
    *,
    effort: str | None = "medium",
) -> Callable[[ActivationRecord, CrewChannels], TaskSpec]:
    """A `TaskBuilder` for one node and working directory."""

    def build(activation: ActivationRecord, channels: CrewChannels) -> TaskSpec:
        return TaskSpec(
            root_id=activation.metadata.wf_root_id,
            activation_id=activation.activation_id,
            node=node.name,
            model=activation.metadata.model,
            effort=effort,
            writes=bool(node.writes),
            allowed_paths=node.allowed_paths or (),
            cwd=str(cwd),
            channels=channels,
        )

    return build
