"""Real-collaborator test lab for the foreman slices.

The lab keeps only the vendor process boundary inert.  Ticks still use the
real store, workspace, git transport, recovery and exit observer.
"""

from __future__ import annotations

import fcntl
import hashlib
import io
import json
import multiprocessing
import os
import sys
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Final, TypedDict

from tests._fake_bd import FakeBd, InjectedCrash
from tests._helpers import VALID_FIXTURE, runner_roles
from tests._supervisor import (
    ChildScript,
    FakeProfile,
    FrozenClock,
    PersistentBd,
    commit_all,
    head_of,
    make_config,
    make_git,
    make_repo,
)
from workflow_interpreter import load_graph
from workflow_interpreter.bdio import (
    BdConfig,
    BoundMutation,
    ConfigSource,
    GateArtifact,
    GatePayload,
    GateRecord,
    GateVerifier,
    InstanceInput,
    Outcome,
    ProcessHandle,
    ResolvedSetting,
    SigningConfig,
    StaleFlagRecord,
    WorkflowStore,
    canonical_payload_bytes,
)
from workflow_interpreter.bdio.client import BdClient, CompletedCommand
from workflow_interpreter.bdio.records import RootRecord
from workflow_interpreter.foreman.compose import (
    Composition,
    InstanceWiring,
    ProfileResolver,
    WrapperLaunch,
)
from workflow_interpreter.foreman.config import ForemanConfig, RunnerBinding
from workflow_interpreter.foreman.gates import payload_template
from workflow_interpreter.foreman.resolve import _resolved_config, instantiate
from workflow_interpreter.foreman.supervise import run_wrapper
from workflow_interpreter.foreman.tick import Foreman, SteerReport, TickReport
from workflow_interpreter.profiles.config import RUNNER_PREFIX
from workflow_interpreter.supervisor import INSTANCE_BRANCH_REF
from workflow_interpreter.supervisor.band import BandLock
from workflow_interpreter.supervisor.models import StaleFlag
from workflow_interpreter.supervisor.paths import fsync_dir, write_record
from workflow_interpreter.supervisor.profile import (
    ChildLauncher,
    Profile,
    RunnerCommand,
    TaskSpec,
)

type OverrideValue = str | int | bool

# The lab's defaults are feature-delivery's: its two roles and the one instance
# input every drill written before phase 7 relies on. A graph with other roles
# or sources (build-loop) passes its own through `ForemanLab(roles=…,
# instance_inputs=…)`.
DEFAULT_LAB_ROLES: Final[Mapping[str, RunnerBinding]] = MappingProxyType(
    {
        "implementer": RunnerBinding(profile="fake"),
        "critic": RunnerBinding(profile="fake"),
    }
)
DEFAULT_LAB_INSTANCE_INPUTS: Final[Mapping[str, str]] = MappingProxyType(
    {"task_brief": "implement the lab fixture"}
)

# build-loop's five `runner = "profile:<role>"` names, all inert in the lab, and
# its two non-optional `producer = "instance"` sources. Shared by every test that
# puts the second graph on the lab.
BUILD_LOOP_ROLES: Final[Mapping[str, RunnerBinding]] = MappingProxyType(
    {
        role: RunnerBinding(profile="fake")
        for role in (
            "test-author",
            "test-critic",
            "implementer",
            "impl-critic",
            "critic",
        )
    }
)
BUILD_LOOP_INSTANCE_INPUTS: Final[Mapping[str, str]] = MappingProxyType(
    {"task_brief": "add the lab slice", "seam_contract": "def lab() -> int"}
)

# The resolver is asked for the runner name as the GRAPH spells it, so the
# accepted set is derived per graph; `fake` is the lab's own inert profile.
FAKE_PROFILE: Final[str] = "fake"


class _Profiles(ProfileResolver):
    """A scriptable resolver that keeps wrapper execution inside the real seam.

    `accepted` is the runner-name allow-list: a name outside it is a wiring bug
    in the lab, and failing loudly there beats silently handing every node the
    same profile.
    """

    def __init__(self, accepted: frozenset[str]) -> None:
        self.accepted = accepted
        self.profile = _QueuedProfile(
            self,
            ChildScript(
                marker='{"outcome":"done"}\n',
                effects='{"paths":["src/feature.py"]}',
                write_path="src/feature.py",
                write_body="value = 2\n",
                commit=True,
            ),
        )
        self._next: ChildScript | None = None
        self._by_node: dict[str, ChildScript] = {}

    def profile_for(self, name: str) -> Profile:
        if name not in self.accepted:
            raise AssertionError(f"unexpected wrapper profile: {name}")
        return self.profile

    def next_script_for_launch(self) -> ChildScript | None:
        """Expose the queued script without consuming it before the spawn succeeds."""
        return self._next

    def consume_next_script(self) -> None:
        """Clear the queued script after its child has actually launched."""
        self._next = None

    def fail_plan_next(self) -> None:
        """Make the next wrapper report the graph's fail-plan outcome."""
        self._next = ChildScript(marker='{"outcome":"fail_plan"}\n')

    def next_script(self, script: ChildScript) -> None:
        """Select the next wrapper child without bypassing its launcher."""
        self._next = script

    def bind_node(self, node: str, script: ChildScript) -> None:
        """Bind one script to a NODE, for a test that cannot queue per tick.

        `next_script` is single-shot and consumed at launch, which works only
        where the test ticks by hand; an unattended `Foreman.run` dispatches
        several nodes with no seam in between, so those tests declare what each
        node's runner does once, up front. An explicitly queued script still
        wins over the node binding.
        """
        self._by_node[node] = script

    def script_for_node(self, node: str) -> ChildScript | None:
        """The script bound to a node, if any."""
        return self._by_node.get(node)


class _QueuedProfile(FakeProfile):
    """A fake profile that consumes lab scripts only when building a child."""

    def __init__(self, profiles: _Profiles, script: ChildScript) -> None:
        super().__init__(script)
        self._profiles = profiles
        self.tasks: list[TaskSpec] = []

    def build_command(self, task: TaskSpec, session_id: str) -> RunnerCommand:
        """Build the next child without consuming a script during settlement."""
        self.tasks.append(task)
        next_script = self._profiles.next_script_for_launch() or (
            self._profiles.script_for_node(task.node)
        )
        if next_script is not None:
            self.script = next_script
        return super().build_command(task, session_id)

    def launch(self, command: RunnerCommand, launcher: ChildLauncher) -> ProcessHandle:
        """Consume the queued script only after its child actually starts."""
        handle = super().launch(command, launcher)
        self._profiles.consume_next_script()
        return handle


class InlineSpawner:
    """Run the wrapper synchronously through the same wiring as its tick."""

    def __init__(self, *, crash_after_start: bool = False) -> None:
        self.launches: list[WrapperLaunch] = []
        self._composition: Composition | None = None
        self._crash_after_start = crash_after_start
        self._fail_next = False

    def bind(self, composition: Composition) -> None:
        """Bind after the composition is complete, avoiding a second wiring path."""
        self._composition = composition

    def fail_next(self) -> None:
        """Fail the next spawn before a wrapper or child can begin."""
        self._fail_next = True

    def launch(
        self, launch: WrapperLaunch, *, wiring: InstanceWiring | None = None
    ) -> None:
        self.launches.append(launch)
        if self._composition is None:  # pragma: no cover - lab construction guard
            raise AssertionError("InlineSpawner was not bound to a composition")
        if wiring is None:  # pragma: no cover - dispatch always supplies its wiring
            raise AssertionError("InlineSpawner needs the tick wiring")
        if self._fail_next:
            self._fail_next = False
            raise InjectedCrash("inline spawn failed")
        run_wrapper(
            self._composition,
            launch.root_id,
            launch.activation_id,
            wiring=wiring,
        )
        if self._crash_after_start:
            raise InjectedCrash("inline wrapper crashed after start")


def _run_wrapper_in_child(
    composition: Composition, root_id: str, activation_id: str
) -> None:
    """Fork target kept at module scope so proc drills use the production seam."""
    run_wrapper(composition, root_id, activation_id)


class ProcSpawner:
    """Fork a wrapper and durably publish its PID before the killer proceeds."""

    def __init__(self) -> None:
        self.launches: list[WrapperLaunch] = []
        self.processes: list[object] = []
        self._composition: Composition | None = None

    def bind(self, composition: Composition) -> None:
        """Bind the exact composition that the child must inherit under fork."""
        self._composition = composition

    def launch(
        self, launch: WrapperLaunch, *, wiring: InstanceWiring | None = None
    ) -> None:
        """Start a detached child, append its PID, then release the test barrier."""
        if self._composition is None:  # pragma: no cover - lab construction guard
            raise AssertionError("ProcSpawner was not bound to a composition")
        self.launches.append(launch)
        child = multiprocessing.get_context("fork").Process(
            target=_run_wrapper_in_child,
            args=(self._composition, launch.root_id, launch.activation_id),
        )
        child.start()
        self.processes.append(child)
        directory = self._composition.for_root(
            launch.root_id
        ).paths.ensure_activation_dir(launch.activation_id)
        pids = directory / "spawned.pids"
        fd = os.open(pids, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, f"{child.pid}\n".encode("ascii"))
            os.fsync(fd)
        finally:
            os.close(fd)
        (directory / "spawned").touch()
        fsync_dir(directory)

    def await_barrier(
        self, wiring: InstanceWiring, activation_id: str, *, timeout_s: float = 5.0
    ) -> None:
        """Wait for exit persistence, wrapper unlock, and every child PID's death."""
        deadline = time.monotonic() + timeout_s
        paths = wiring.paths
        while time.monotonic() < deadline:
            activation = wiring.store.reads.load_activation(activation_id)
            if (
                paths.exit_file(activation_id).exists()
                or activation.metadata.exit_record
            ):
                break
            time.sleep(0.01)
        else:
            raise AssertionError("wrapper never persisted an exit record")
        while time.monotonic() < deadline:
            if not wrapper_alive_for_barrier(wiring, activation_id):
                break
            time.sleep(0.01)
        else:
            raise AssertionError("wrapper stayed alive after its exit record")
        pids = (paths.activation_dir(activation_id) / "spawned.pids").read_text(
            encoding="ascii"
        )
        for raw_pid in pids.splitlines():
            while time.monotonic() < deadline and _pid_running(int(raw_pid)):
                time.sleep(0.01)
            if _pid_running(int(raw_pid)):
                raise AssertionError(f"spawned wrapper {raw_pid} is still running")


def wrapper_alive_for_barrier(wiring: InstanceWiring, activation_id: str) -> bool:
    """Keep the three-stage proc barrier explicit at the same lock seam."""
    from workflow_interpreter.foreman.supervise import wrapper_alive

    return wrapper_alive(wiring, activation_id)


def _pid_running(pid: int) -> bool:
    """Treat a zombie as finished: the proc drill only needs execution to stop."""
    stat = Path(f"/proc/{pid}/stat")
    if not stat.exists():
        return False
    try:
        return stat.read_text(encoding="utf-8").split()[2] != "Z"
    except (IndexError, OSError):
        return False


class _PersistentCall(TypedDict):
    """One serialized fake-bd invocation attributed to its process."""

    pid: int
    argv: list[str]
    # Metadata travels as `@<path>` and its file is unlinked on return, so the
    # keys a call wrote are captured here or not at all (ADR 0003).
    metadata_keys: list[str]


class ForemanLab:
    """A throwaway repository wired through real foreman collaborators."""

    def __init__(
        self,
        tmp_path: Path,
        *,
        toml: Path = VALID_FIXTURE,
        overrides: Mapping[str, OverrideValue] | None = None,
        allow_test_flags: bool = False,
        signing: SigningConfig | None = None,
        signer: Callable[[bytes, Path | None], bytes] | None = None,
        bd_factory: Callable[[str], FakeBd] = FakeBd,
        band_wait_s: float = 30.0,
        roles: Mapping[str, RunnerBinding] = DEFAULT_LAB_ROLES,
        instance_inputs: Mapping[str, str] = DEFAULT_LAB_INSTANCE_INPUTS,
    ) -> None:
        """Wire a throwaway repo to a real foreman.

        `roles` binds each `runner = "profile:<role>"` name the graph declares —
        the real `resolve.instantiate` refuses a graph with an unbound role —
        and `instance_inputs` maps each `producer = "instance"` source name to
        its body. Both default to feature-delivery's, which `toml` also
        defaults to.
        """
        self.repo = make_repo(tmp_path)
        self.head = head_of(self.repo)
        self._workspace = tmp_path / "bd-workspace"
        self._bd_factory = bd_factory
        self._durable_factory = bd_factory is not FakeBd
        self._signing = signing
        self._band_wait_s = band_wait_s
        self.signer = signer
        self.overrides = {} if overrides is None else dict(overrides)
        self._roles = dict(roles)
        self._instance_inputs = dict(instance_inputs)
        self.allow_test_flags = allow_test_flags
        self._wrapper_home = tmp_path / "foreman"
        wrapper_root = (
            self._wrapper_home
            / hashlib.sha256(str(self.repo.resolve()).encode("utf-8")).hexdigest()[:16]
        )
        self.supervisor_config = make_config(
            self.repo, tmp_path, fake_proc=False, wrapper_root=wrapper_root
        )
        self._toml = toml
        self.definition = load_graph(toml, allow_test_flags=allow_test_flags)
        self._build_fresh()
        self.root: RootRecord | None = None

    def _accepted_profiles(self) -> frozenset[str]:
        """Every runner name the pinned graph can ask the resolver for."""
        return frozenset(
            {FAKE_PROFILE}
            | {f"{RUNNER_PREFIX}{role}" for role in runner_roles(self.definition)}
        )

    def _build_fresh(self) -> None:
        """Construct no composition collaborator from a prior process."""
        self.fake_bd = self._bd_factory(str(self._workspace))
        verifier = (
            None
            if self._signing is None
            else GateVerifier(self._signing, self._workspace)
        )
        self.store = WorkflowStore(
            BdClient(BdConfig(workspace=self._workspace, actor="test"), self.fake_bd),
            verifier,
        )
        self.git = make_git(self.supervisor_config)
        self.clock = FrozenClock()
        self.profiles = _Profiles(self._accepted_profiles())
        self.spawner = InlineSpawner()
        self.config = ForemanConfig(
            repo_root=self.repo,
            wrapper_home=self._wrapper_home,
            bd=BdConfig(workspace=self._workspace, actor="test"),
            signing=self._signing,
            host="test-host",
            supervisor=self.supervisor_config,
            actor="test",
            band_wait_s=self._band_wait_s,
            roles=self._roles,
        )
        self.composition = Composition(
            self.config,
            self.store,
            self.supervisor_config,
            self.git,
            self.clock,
            self.profiles,
            self.spawner,
        )
        self.spawner.bind(self.composition)
        self.foreman = Foreman(self.composition)

    def pin_checks(self, bodies: Mapping[str, str]) -> None:
        """Commit `bodies` as the repo's check scripts, before they are pinned.

        The §7.3 digests are read from the repo when the root is created and
        the checks execute from a checkout of the artifact commit, so a test
        that wants its own check bytes has to make them executable AND commit
        them before `instantiate`.
        """
        for name, body in bodies.items():
            path = self.repo / name
            # build-loop's checks live in `scripts/checks/`, which the fixture
            # repo does not have.
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
            path.chmod(0o755)
        self.head = commit_all(self.repo, "lab check scripts")

    def instantiate_resolved(
        self, overrides: Mapping[str, OverrideValue] | None = None
    ) -> RootRecord:
        """Pin the root through the REAL `resolve.instantiate`, overrides and all.

        `instantiate` is the only path that runs an override through
        `resolve()`'s vocabulary, type and usability checks before the
        immutable write, so a test about what an OVERRIDE does to a run has to
        come through here rather than through the hand-built resolution.
        """
        directory = self.repo.parent / "instance-inputs"
        directory.mkdir(parents=True, exist_ok=True)
        paths: dict[str, Path] = {}
        for name, body in self._instance_inputs.items():
            path = directory / f"{name}.md"
            path.write_text(body, encoding="utf-8")
            paths[name] = path
        self.root = instantiate(
            self.composition,
            self._toml,
            instance_key="foreman-lab",
            instance_inputs=paths,
            allow_test_flags=self.allow_test_flags,
            overrides=dict(overrides or {}),
        )
        return self.root

    def instantiate(self) -> RootRecord:
        """Pin the graph and create the instance branch, like resolve does."""
        root = self.store.create_root(
            instance_key="foreman-lab",
            definition=self.definition,
            resolved_config=self._overrides(),
            instance_inputs=tuple(
                InstanceInput(
                    name=name,
                    body=body,
                    sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
                )
                for name, body in self._instance_inputs.items()
            ),
            allow_test_flags=self.allow_test_flags,
            instance_base_commit=self.head,
        )
        branch = INSTANCE_BRANCH_REF.format(root_id=root.root_id)
        if self.git.ref_target(branch, cwd=self.repo) is None:
            self.git.update_ref(branch, self.head, cwd=self.repo)
        self.root = root
        return root

    def tick(self) -> TickReport:
        assert self.root is not None
        return self.foreman.tick(self.root.root_id)

    def rebuild(self) -> None:
        """Reconstruct a fresh foreman from durable bd, git, and wrapper state."""
        if not self._durable_factory:
            raise AssertionError("ForemanLab.rebuild requires a durable bd_factory")
        root_id = None if self.root is None else self.root.root_id
        self._build_fresh()
        self.root = None if root_id is None else self.store.reads.load_root(root_id)

    def crash_on_tick_create(self, occurrence: int) -> None:
        """Inject a crash on the requested routed tick create after its canary."""
        self.fake_bd.crash_on("create", occurrence + 1)

    def hold_wrapper_lock(self, activation_id: str) -> BandLock:
        """Hold an activation's real wrapper lock until the caller releases it."""
        lock = BandLock(
            self.wiring().paths.activation_dir(activation_id) / "wrapper.lock"
        )
        lock.acquire()
        return lock

    def approve(
        self,
        gate_id: str,
        outcome: Outcome,
        *,
        artifact: GateArtifact | None = None,
        mutation: BoundMutation | None = None,
    ) -> GateRecord:
        """Render and sign one gate so the next tick performs real intake."""
        assert self.root is not None
        if self.signer is None:
            raise AssertionError("ForemanLab.approve requires a signer")
        gate = self.store.reads.load_gate(gate_id)
        rendered = GatePayload.model_validate_json(payload_template(self.root, gate))
        payload = rendered.model_copy(
            update={
                "outcome": outcome,
                "artifact": rendered.artifact if artifact is None else artifact,
                "nonce": uuid.uuid4().hex,
                "bound_mutation": mutation,
            }
        )
        payload_bytes = canonical_payload_bytes(payload)
        directory = self.wiring().paths.instance_dir / "gates" / gate.metadata.gate_key
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "payload.json").write_bytes(payload_bytes)
        (directory / "payload.json.sig").write_bytes(self.signer(payload_bytes, None))
        fsync_dir(directory)
        return gate

    def refuse(self, gate_id: str) -> GateRecord:
        """Write an invalid signed payload for the next tick's intake probe."""
        gate = self.store.reads.load_gate(gate_id)
        directory = self.wiring().paths.instance_dir / "gates" / gate.metadata.gate_key
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "payload.json").write_bytes(b"{}")
        (directory / "payload.json.sig").write_bytes(b"invalid signature")
        fsync_dir(directory)
        return gate

    def refusal(self, gate_id: str) -> str:
        """Read the durable reason emitted by the last refused intake."""
        gate = self.store.reads.load_gate(gate_id)
        path = self.wiring().paths.instance_dir / "gates" / gate.metadata.gate_key
        return str(
            json.loads((path / "refusal.json").read_text(encoding="utf-8"))["reason"]
        )

    def beads(self, kind: str) -> list[dict[str, object]]:
        return [
            row
            for row in self.fake_bd.rows.values()
            if row["metadata"].get("wf_kind") == kind
        ]

    def count(self, subcommand: str) -> int:
        return self.fake_bd.command_count(subcommand)

    def wiring(self) -> InstanceWiring:
        assert self.root is not None
        return self.composition.for_root(self.root.root_id)

    def go_stale(
        self,
        activation_id: str,
        *,
        log_bytes: int = 65536,
        tail_bytes: bytes | None = None,
    ) -> None:
        """Write a monitor-shaped stale signal and a deliberately large raw log."""
        wiring = self.wiring()
        paths = wiring.paths
        paths.ensure_activation_dir(activation_id)
        with paths.log(activation_id).open("wb") as handle:
            handle.write(b"foreman-lab-sentinel\n" * (log_bytes // 21 + 1))
            if tail_bytes is not None:
                handle.write(tail_bytes)
        flag = StaleFlag(
            activation_id=activation_id,
            raised_at="2026-08-29T00:00:00Z",
            last_activity_at="2026-08-28T23:55:00Z",
            stale_after_s=60.0,
        )
        write_record(paths.stale_flag(activation_id), flag)
        wiring.store.record_stale_flag(
            activation_id,
            StaleFlagRecord(
                raised_at=flag.raised_at, last_activity_at=flag.last_activity_at
            ),
        )

    def steer(
        self, activation_id: str, *, reason: str, instructions: str
    ) -> SteerReport:
        assert self.root is not None
        return self.foreman.steer(
            self.root.root_id, activation_id, reason=reason, instructions=instructions
        )

    def transcript(self, fn: Callable[[], object]) -> tuple[int, str]:
        """Capture exactly one entrypoint's combined stdout and stderr bytes."""
        captured = io.BytesIO()
        stream = io.TextIOWrapper(captured, encoding="utf-8", write_through=True)
        previous_stdout, previous_stderr = sys.stdout, sys.stderr
        sys.stdout = stream
        sys.stderr = stream
        try:
            fn()
            stream.flush()
        finally:
            sys.stdout = previous_stdout
            sys.stderr = previous_stderr
        text = captured.getvalue().decode("utf-8")
        return len(text.encode("utf-8")), text

    def _overrides(self) -> tuple[ResolvedSetting, ...]:
        """Resolve the lab's root exactly as `resolve.instantiate` would.

        Through the real `_resolved_config`, not a canned tuple: it is what
        pins the role bindings and the graph's own defaults, and the execution
        path reads the ROOT's resolution for every field it acts on (§3.1), so
        a hand-built resolution that disagreed with the graph would drive the
        lab through a configuration no real instance could have.

        The lab's own `overrides` are layered ON TOP rather than passed in:
        several tests pin a §7.3 verifier digest through them, which is a key
        `resolve()` deliberately refuses as an instance override.
        """
        base = {
            setting.key: setting
            for setting in _resolved_config(self.composition, self.definition, {})
        }
        base.update(
            {
                key: ResolvedSetting(
                    key=key, value=value, source=ConfigSource.INSTANCE_OVERRIDE
                )
                for key, value in self.overrides.items()
            }
        )
        return tuple(base[key] for key in sorted(base))


class LockedPersistentBd(PersistentBd):
    """A persistent fake that serializes each load, command, and save cycle."""

    def __init__(self, workspace: str, state: Path) -> None:
        self._call_log: list[_PersistentCall] = []
        super().__init__(workspace, state)
        self._lock_path = state.with_suffix(state.suffix + ".lock")

    def __call__(self, argv: Sequence[str], timeout_s: float) -> CompletedCommand:
        """Keep competing fake-bd clients from loading the same stale state."""
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock_path.open("a", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                self._restore()
                result = FakeBd.__call__(self, argv, timeout_s)
                # `metadata_keys` rather than the argv alone: metadata travels
                # as `@<path>` (ADR 0003) and the transport unlinks the file
                # on return, so a later reader of this log could no longer
                # answer "which keys did this call write" from argv.
                self._call_log.append(
                    {
                        "pid": os.getpid(),
                        "argv": list(argv),
                        "metadata_keys": sorted(self.metadata_writes[-1]),
                    }
                )
                self._state.write_text(
                    json.dumps(
                        {
                            "rows": self.rows,
                            "next_id": self._next_id,
                            "calls": self._call_log,
                        }
                    ),
                    encoding="utf-8",
                )
                return result
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _restore(self) -> None:
        """Restore rows and the cross-process audit log together."""
        super()._restore()
        if not self._state.exists():
            return
        stored: dict[str, object] = json.loads(self._state.read_text(encoding="utf-8"))
        raw_calls = stored.get("calls", [])
        if not isinstance(raw_calls, list):
            raise TypeError("persistent fake-bd calls must be a list")
        calls: list[_PersistentCall] = []
        for entry in raw_calls:
            if not isinstance(entry, dict):
                raise TypeError("persistent fake-bd call must be an object")
            pid = entry.get("pid")
            argv = entry.get("argv")
            if (
                not isinstance(pid, int)
                or not isinstance(argv, list)
                or not all(isinstance(part, str) for part in argv)
            ):
                raise ValueError("persistent fake-bd call has an invalid shape")
            keys = entry.get("metadata_keys", [])
            if not isinstance(keys, list) or not all(
                isinstance(part, str) for part in keys
            ):
                raise ValueError("persistent fake-bd call has an invalid shape")
            calls.append({"pid": pid, "argv": argv, "metadata_keys": keys})
        self._call_log = calls
        self.calls = [
            (str(entry["argv"][3]), tuple(str(part) for part in entry["argv"]))
            for entry in self._call_log
        ]
        # Restored in lockstep with `calls`: the two are indexed together by
        # anything asking which keys a given call wrote.
        self.metadata_writes = [
            dict.fromkeys(entry["metadata_keys"]) for entry in self._call_log
        ]
