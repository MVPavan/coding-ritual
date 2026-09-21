"""The composition root: dispatch → watch → exit-recorded, in one process.

Three properties that only exist once something OWNS the sequence:

- the §3.2 carry-forward trio reaches bd BEFORE the child can exec (B7);
- the §8.2 stale flag reaches bd as well as the wrapper dir (§8.2, M11);
- the exit still gets recorded after the process that started the inspector is
  killed (§5.3's "alive for the child's lifetime", B5).

The last one is a real three-process drill — pytest spawns a foreman, the
foreman spawns a wrapper, the wrapper spawns a crew, and the foreman is
SIGKILLed while the crew is still going. bd is file-backed for it
(`PersistentBd`), because the whole question is whether writes made by a
process the test does not own still land.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests._bdio import UPDATE, StoreWrites
from tests._fake_bd import InjectedCrash
from tests._inspector import (
    IMPLEMENT,
    ChildScript,
    FakeProfile,
    FrozenClock,
    entry_mint,
    handle_for,
    head_of,
    make_config,
    make_git,
    make_paths,
    make_persistent_store,
    make_repo,
    make_root,
    make_store,
    make_workspace,
    node_of,
    task_builder,
)
from workflow_interpreter.bdio import Lifecycle, MintReason
from workflow_interpreter.contracts.transport import CrewTransport
from workflow_interpreter.inspector import (
    ExecLedger,
    ExecLedgerEntry,
    ExitReason,
    InspectionResult,
    Inspector,
    LaunchOutcome,
    LaunchReceipt,
    MonitorVerdict,
    SteerIntent,
    pinned_verifier_digests,
    procfs,
)
from workflow_interpreter.inspector.models import HOST_ENDED_EXIT_REASONS
from workflow_interpreter.inspector.paths import write_record
from workflow_interpreter.inspector.steer import instructions_digest
from workflow_interpreter.schema.models import IsolationMode, Outcome

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKER_JSON = '{"outcome":"done"}'
EFFECTS_JSON = '{"paths":[]}'
STALE_AFTER = "1s"
CHILD_SECONDS = 3.0
SENTINEL_TIMEOUT_S = 90.0
BD_UPDATE = "update"
STEER_REASON = "the crew is repeating itself"
STEER_INSTRUCTIONS = "start from the failing test instead"
REQUESTED_AT = "2026-09-02T09:00:00Z"
ORPHAN_LAUNCH_ID = "crashed-rpc-launcher"
ORPHAN_SECONDS = 30
"""Long enough that only the wrapper's own kill can end the adopted child."""

WRAPPER_MAIN = '''
"""An inspector wrapper in its own process, for the parent-death drill."""
import sys
from pathlib import Path

sys.path.insert(0, {repo!r})
sys.path.insert(0, {tests!r})

import structlog

structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(50))

from tests._inspector import (
    IMPLEMENT,
    ChildScript,
    FakeProfile,
    entry_mint,
    head_of,
    make_config,
    make_git,
    make_paths,
    make_persistent_store,
    make_workspace,
    node_of,
    task_builder,
)
from workflow_interpreter.inspector import (
    Inspector,
    SystemClock,
    Workspace,
    pinned_verifier_digests,
)

tmp = Path(sys.argv[1])
root_id = sys.argv[2]
repo = tmp / "repo"
config = make_config(repo, tmp, fake_proc=False, poll_interval_s=0.2)
_, store = make_persistent_store(tmp, head_of(repo), tmp / "shared-ledger.db")
root = store.reads.load_root(root_id)
paths = make_paths(config, root_id)
git = make_git(config)
clock = SystemClock()
workspace = make_workspace(paths, git, clock)
node = node_of(root.definition.document, IMPLEMENT)
profile = FakeProfile(
    ChildScript(
        emit="working\\n",
        marker={marker!r},
        effects={effects!r},
        sleep_s={seconds},
    )
)
(tmp / "WRAPPER-STARTED").write_text("1", encoding="utf-8")
result = Inspector(config, paths, git, store, workspace, clock).run(
    entry_mint(),
    node,
    profile,
    task_builder(paths.worktree, node),
    pinned_digests=pinned_verifier_digests(root),
)
(tmp / "WRAPPER-DONE").write_text(
    result.observation.activation.metadata.lifecycle.value, encoding="utf-8"
)
'''

FOREMAN_MAIN = '''
"""A foreman that starts one wrapper and then does nothing until it is killed."""
import subprocess
import sys
import time

log = open(sys.argv[3], "wb")
subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2], sys.argv[4]], stdout=log, stderr=log)
while True:
    time.sleep(0.1)
'''


class Lab:
    """One instance wired for the in-process composition tests."""

    def __init__(self, tmp_path: Path) -> None:
        self.repo = make_repo(tmp_path)
        self.base = head_of(self.repo)
        self.config = make_config(self.repo, tmp_path, fake_proc=False)
        self.fake_bd, self.store = make_store(tmp_path, self.base)
        self.writes = StoreWrites(self.fake_bd)
        """Every record-store write this lab served, counted and injectable —
        the hooks the bd double used to give a case (S6: bd is not a record
        store, R1)."""
        self.root = make_root(self.store, self.repo, "run-instance")
        self.paths = make_paths(self.config, self.root.root_id)
        self.clock = FrozenClock()
        self.git = make_git(self.config)
        self.workspace = make_workspace(self.paths, self.git, self.clock)
        self.node = node_of(self.root.definition.document, IMPLEMENT)
        self.inspector = Inspector(
            self.config, self.paths, self.git, self.store, self.workspace, self.clock
        )

    def inspect(self, script: ChildScript) -> InspectionResult:
        """Run one activation end to end against a scripted child."""
        return self.inspector.run(
            entry_mint(),
            self.node,
            FakeProfile(script),
            task_builder(self.paths.worktree, self.node),
            pinned_digests=pinned_verifier_digests(self.root),
        )


@pytest.fixture
def lab(tmp_path: Path) -> Lab:
    """An inspector over a throwaway repo and an in-memory bd."""
    return Lab(tmp_path)


@pytest.mark.proc
def test_one_call_dispatches_watches_and_records_the_exit(lab: Lab) -> None:
    """B5: nothing in the package tied dispatch → watch → exit before this.

    `Monitor.watch` and `ExitObserver` had zero non-test callers, so in
    production shape no process enforced `max_wall` or wrote the exit record.
    """
    result = lab.inspect(
        ChildScript(emit="hello\n", marker=MARKER_JSON, effects=EFFECTS_JSON)
    )

    assert result.monitor is not None
    assert result.monitor.verdict is MonitorVerdict.EXITED
    assert result.observation is not None
    assert result.observation.exit_record.exit_code == 0
    assert result.observation.activation.metadata.lifecycle is Lifecycle.EXIT_RECORDED
    assert (
        ExecLedger(lab.paths.ledger(result.dispatch.activation.activation_id)).count()
        == 1
    )


@pytest.mark.proc
def test_the_carry_forward_trio_is_recorded_before_the_child_execs(lab: Lab) -> None:
    """B7: §3.2 derives a rework's base from `pre_attempt_commit`.

    Never written, it fell through to the branch head — which after a reject IS
    the rejected artifact, so the rework based on exactly the work that was
    rejected. The ORDER is the fix: the exec ledger must still be empty when
    the trio lands, or a crash in between recreates the hole.
    """
    ledger_at_write: list[int] = []
    activation_id = lab.store.mint_activation(
        lab.root.root_id, entry_mint()
    ).activation.activation_id
    lab.writes.pause_before(
        UPDATE,
        lambda: ledger_at_write.append(
            ExecLedger(lab.paths.ledger(activation_id)).count()
        ),
    )

    result = lab.inspect(ChildScript(marker=MARKER_JSON, effects=EFFECTS_JSON))

    metadata = lab.store.reads.load_activation(activation_id).metadata
    assert metadata.pre_attempt_commit == lab.base
    assert metadata.reset_verified_commit == lab.base
    assert ledger_at_write == [0]
    assert result.dispatch.precondition is not None


@pytest.mark.proc
def test_a_re_dispatch_does_not_rewrite_a_recorded_precondition(lab: Lab) -> None:
    """§5.1: the trio describes a tree the child already ran against."""
    lab.inspect(ChildScript(marker=MARKER_JSON, effects=EFFECTS_JSON))
    before = lab.writes.count(UPDATE)

    second = lab.inspect(ChildScript(marker=MARKER_JSON, effects=EFFECTS_JSON))

    assert second.observation is None
    assert second.dispatch.precondition is None
    assert lab.writes.count(UPDATE) == before


def _persist_steer_intent(lab: Lab) -> str:
    """Mint the activation the run will re-find, with a §8.1 intent already on disk.

    Pre-minting is how the other tests here learn an activation id before the
    run (§3.2's idempotency key makes the inspector re-find this one), and it
    is what makes the race deterministic: the intent is durable before the
    watch ends, exactly as `Steerer.steer` writes it before the kill.
    """
    activation_id = lab.store.mint_activation(
        lab.root.root_id, entry_mint()
    ).activation.activation_id
    write_record(
        lab.paths.steer_intent(activation_id),
        SteerIntent(
            activation_id=activation_id,
            reason=STEER_REASON,
            instructions=STEER_INSTRUCTIONS,
            instructions_digest=instructions_digest(STEER_INSTRUCTIONS),
            requested_at=REQUESTED_AT,
            continuation=entry_mint(
                mint_reason=MintReason.STEER_CONTINUATION,
                predecessor_activation_id=activation_id,
            ),
        ),
    )
    return activation_id


@pytest.mark.proc
def test_a_pending_steer_intent_leaves_the_exit_to_the_steerer(lab: Lab) -> None:
    """cr-us7: the wrapper raced the steerer and won, wedging the steer.

    A child killed by §8.1 dies with no reaped status, so the watch ends
    `exited` with no code and the observer graded it `exit_unobserved` →
    `error_transport`: an infra retry spent on a deliberate kill, and a close
    that made the steerer's own `steered` close raise
    `LifecycleConflictError`. The durable intent is the same evidence §5.6
    lets outrank an exit record, so the wrapper now defers too.
    """
    activation_id = _persist_steer_intent(lab)
    updates_before = lab.writes.count(BD_UPDATE)

    result = lab.inspect(ChildScript(marker=MARKER_JSON, effects=EFFECTS_JSON))

    assert result.dispatch.activation.activation_id == activation_id
    assert result.monitor is not None
    assert result.observation is None
    assert not lab.paths.exit_file(activation_id).exists()
    metadata = lab.store.reads.load_activation(activation_id).metadata
    assert metadata.lifecycle is Lifecycle.DISPATCHED
    assert metadata.exit_record is None
    # The §3.2 trio and the dispatch, and nothing after them: no `record_exit`
    # and no close reached bd, so the steerer's own close cannot conflict.
    assert lab.writes.count(BD_UPDATE) == updates_before + 2


@pytest.mark.proc
def test_a_malformed_steer_intent_does_not_suppress_the_exit(lab: Lab) -> None:
    """An unreadable intent is §5.6's to report, not the wrapper's to act on."""
    activation_id = lab.store.mint_activation(
        lab.root.root_id, entry_mint()
    ).activation.activation_id
    path = lab.paths.steer_intent(activation_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")

    result = lab.inspect(ChildScript(marker=MARKER_JSON, effects=EFFECTS_JSON))

    assert result.observation is not None
    assert result.observation.exit_record.exit_code == 0
    assert lab.paths.exit_file(activation_id).exists()
    metadata = lab.store.reads.load_activation(activation_id).metadata
    assert metadata.lifecycle is Lifecycle.EXIT_RECORDED


def test_a_malformed_steer_intent_reads_as_no_intent_at_all(lab: Lab) -> None:
    """The same rule as the drill above, at the seam and without a child.

    The end-to-end version is `proc`-marked, so the unit suite — the one §7.3's
    mutation check runs — never exercised the `WrapperDirError` branch at all:
    making it answer "a steer is pending" killed no test, and that mutant
    suppresses the exit record of every activation with a corrupt byte in its
    wrapper dir. A valid intent is asserted beside it so the test cannot pass
    by answering `False` to everything.
    """
    activation_id = lab.store.mint_activation(
        lab.root.root_id, entry_mint()
    ).activation.activation_id
    path = lab.paths.steer_intent(activation_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")

    unreadable = lab.inspector._steer_pending(activation_id)
    # The §3.2 idempotency key re-finds the same activation, so this replaces
    # the corrupt bytes with a well-formed intent on the same path.
    assert _persist_steer_intent(lab) == activation_id

    assert unreadable is False
    assert lab.inspector._steer_pending(activation_id) is True


@pytest.mark.proc
def test_a_stale_child_is_flagged_on_disk_and_in_bd_then_terminated(
    tmp_path: Path,
) -> None:
    """M11: §8.2 says "file AND bd metadata"; only the file existed.

    Losing `.wf/` therefore lost a decision-relevant datum, which §P1 says the
    observation cache is never allowed to hold alone. The mirror lives in the
    inspector, not in the loop: `Monitor` still cannot reach bd at all.

    The child here stays silent for the whole watch, so it runs the §8.2 order
    end to end: the flag is raised and mirrored in the first window, and the
    second one ends the child. The mirror has to happen BEFORE the kill, which
    is the ordering this asserts by reading both afterwards.
    """
    lab = Lab(tmp_path)
    lab.node = lab.node.model_copy(update={"stale_after": STALE_AFTER})
    lab.clock.real_sleep_s = 0.05

    result = lab.inspect(ChildScript(sleep_s=CHILD_SECONDS))

    activation_id = result.dispatch.activation.activation_id
    assert result.monitor is not None
    assert result.monitor.verdict is MonitorVerdict.STALE_BREACH
    assert result.stale_recorded is True
    assert lab.paths.stale_flag(activation_id).exists()
    recorded = lab.store.reads.load_activation(activation_id).metadata.stale_flag
    assert recorded is not None
    assert recorded.raised_at != ""


@pytest.mark.proc
def test_a_stale_termination_is_graded_as_a_crew_error(tmp_path: Path) -> None:
    """§8.2: a second silent window ends the child, and §7 grades what is left.

    The route to `error_crew` — and so to one infra retry (§10.2) — is the
    `max_wall` one exactly: nothing reads the exit REASON, and a TERMed child
    with no marker is a crew error whichever ceiling ended it. The reason is
    still recorded, because it is the only place the difference survives.
    """
    lab = Lab(tmp_path)
    lab.node = lab.node.model_copy(update={"stale_after": STALE_AFTER})
    lab.clock.real_sleep_s = 0.05

    result = lab.inspect(ChildScript(sleep_s=CHILD_SECONDS))

    assert result.monitor is not None
    assert result.monitor.verdict is MonitorVerdict.STALE_BREACH
    assert result.observation is not None
    assert result.observation.exit_record.reason == ExitReason.STALE.value
    assert result.observation.exit_record.exit_code == -signal.SIGTERM
    assert result.observation.completion.outcome is Outcome.ERROR_CREW
    assert result.observation.activation.metadata.lifecycle is Lifecycle.EXIT_RECORDED


@pytest.mark.proc
def test_a_reattached_child_is_adopted_into_the_watch(lab: Lab) -> None:
    """Opus#24/Sol#5: the REATTACH path returned with nobody watching the child.

    REATTACH is the §5.2 crash window — our own receipt and ledger line exist
    while bd still says `minted`, which can only mean the wrapper that exec'd
    the child died before recording the dispatch. So nobody else is watching,
    and returning left a LIVE child with no `max_wall` enforcement and no exit
    record: its eventual normal exit later became §5.6's `error_transport`, and
    the infra retry then ran a second child against the same tree.

    The crash is injected exactly where the window is — the `record_dispatch`
    write, after the child has already exec'd.
    """
    lab.clock.real_sleep_s = 0.05
    lab.writes.crash_on(UPDATE, 2)
    script = ChildScript(
        sleep_s=CHILD_SECONDS, marker=MARKER_JSON, effects=EFFECTS_JSON
    )
    with pytest.raises(InjectedCrash):
        lab.inspect(script)

    result = lab.inspect(script)

    activation_id = result.dispatch.activation.activation_id
    assert result.dispatch.outcome is LaunchOutcome.REATTACHED
    assert result.monitor is not None
    assert result.monitor.verdict is MonitorVerdict.EXITED
    assert result.observation is not None
    assert result.observation.exit_record.exit_code == 0
    assert result.observation.activation.metadata.lifecycle is Lifecycle.EXIT_RECORDED
    assert ExecLedger(lab.paths.ledger(activation_id)).count() == 1


def _orphaned_rpc_receipt(lab: Lab, tmp_path: Path) -> str:
    """Mint one activation whose §5.2 receipt names a live ORPHANED RPC child.

    The exact §5.2 crash window for an STDIO-RPC launch: the receipt and the
    ledger line are durable, bd still says `minted`, and the wrapper that
    exec'd the child is gone — so the child is reparented to init and its pipes
    died with its launcher. A `setsid` grandchild whose parent exits is the
    only shape that reproduces "alive, ours to signal, never ours to reap".
    """
    activation = lab.store.mint_activation(lab.root.root_id, entry_mint()).activation
    activation_id = activation.activation_id
    lab.paths.ensure_activation_dir(activation_id)
    lab.workspace.prepare(activation, lab.node)
    pidfile = tmp_path / "orphan.pid"
    script = tmp_path / "orphan.sh"
    script.write_text(
        f"#!/bin/sh\necho $$ > {pidfile}\nsleep {ORPHAN_SECONDS}\n", encoding="utf-8"
    )
    script.chmod(0o755)
    subprocess.run(["sh", "-c", f"setsid {script} &"], check=True, timeout=30)
    deadline = time.monotonic() + SENTINEL_TIMEOUT_S
    while not pidfile.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    pid = int(pidfile.read_text(encoding="utf-8").strip())
    boot_id = procfs.read_boot_id(lab.config)
    assert boot_id is not None
    handle = handle_for(
        pid,
        boot_id=boot_id,
        start_time=procfs.read_start_time(lab.config, pid) or "",
        log_path=str(lab.paths.log(activation_id)),
    )
    write_record(
        lab.paths.receipt(activation_id),
        LaunchReceipt(
            transport=CrewTransport.STDIO_RPC,
            launch_id=ORPHAN_LAUNCH_ID,
            root_id=lab.root.root_id,
            activation_id=activation_id,
            argv=(str(script),),
            cwd=str(lab.repo),
            handle=handle,
        ),
    )
    lab.paths.ledger(activation_id).write_bytes(
        ExecLedger.line(
            ExecLedgerEntry(
                launch_id=ORPHAN_LAUNCH_ID,
                activation_id=activation_id,
                pid=pid,
                at=REQUESTED_AT,
            )
        )
    )
    return activation_id


@pytest.mark.proc
def test_a_reattached_rpc_child_the_wrapper_kills_is_recorded_as_host_ended(
    tmp_path: Path,
) -> None:
    """Sol: the host-kill of an adopted RPC child passed as a normal finish.

    A reattached STDIO-RPC child cannot be watched — the pipes belonged to the
    dead launcher — so the wrapper kills it and watches the corpse. The kill
    was never ours to reap (ECHILD), so the watch reads that death as
    `EXIT_STATUS_UNOBSERVABLE_REATTACHED`: "it ended on its own", which is
    outside `HOST_ENDED_EXIT_REASONS` and so accepted by `foreman/decisions` as
    a finished run. A decider this wrapper KILLED would have been read for its
    answer. The status is genuinely unknowable; the CAUSE is not.
    """
    lab = Lab(tmp_path)
    lab.clock.real_sleep_s = 0.05
    activation_id = _orphaned_rpc_receipt(lab, tmp_path)

    result = lab.inspector.run(
        entry_mint(),
        lab.node,
        FakeProfile(ChildScript()),
        task_builder(lab.paths.worktree, lab.node),
        pinned_digests=pinned_verifier_digests(lab.root),
    )

    assert result.dispatch.activation.activation_id == activation_id
    assert result.dispatch.outcome is LaunchOutcome.REATTACHED
    assert result.observation is not None
    reason = ExitReason(result.observation.exit_record.reason)
    assert reason is ExitReason.TERMINATED
    assert reason in HOST_ENDED_EXIT_REASONS


@pytest.mark.proc
def test_an_in_repo_node_runs_inside_the_execution_band(lab: Lab) -> None:
    """Opus#30: `Inspector.run` never acquired the §12 band.

    So the composition root that §5.3 says owns the lifecycle could not run an
    in-repo node at all — `prepare` refused it — and any caller that took the
    band itself had to keep holding it through the watch and the exit
    observation, since `ExitObserver` records what the crew left dirty while
    the band is still that crew's. Taken around the whole run, both hold.
    """
    node = lab.node.model_copy(update={"isolation": IsolationMode.IN_REPO})
    build = task_builder(lab.repo, node)
    held: list[bool] = []

    def watched_builder(activation: object, channels: object) -> object:
        held.append(lab.workspace.band.held)
        return build(activation, channels)  # type: ignore[arg-type]

    result = lab.inspector.run(
        entry_mint(),
        node,
        FakeProfile(ChildScript(marker=MARKER_JSON, effects=EFFECTS_JSON)),
        watched_builder,  # type: ignore[arg-type]
        pinned_digests=pinned_verifier_digests(lab.root),
    )

    assert held == [True]
    assert lab.workspace.band.held is False
    assert result.observation is not None
    assert result.observation.activation.metadata.lifecycle is Lifecycle.EXIT_RECORDED


@pytest.mark.proc
def test_the_exit_is_recorded_after_the_wrappers_parent_is_killed(
    tmp_path: Path,
) -> None:
    """B5's real claim: the inspector outlives whatever started it.

    §5.3 gives the wrapper the child's whole lifetime, and drill 14 asserts the
    flags are raised "while the foreman process is not running". Both are only
    true if the wrapper is a process in its own right — so this one kills the
    parent of the wrapper mid-run and reads the shared ledger afterwards.
    """
    repo = make_repo(tmp_path)
    state = tmp_path / "shared-ledger.db"
    _, store = make_persistent_store(tmp_path, head_of(repo), state)
    root = make_root(store, repo, "detached-instance")
    wrapper = tmp_path / "wrapper_main.py"
    wrapper.write_text(
        WRAPPER_MAIN.format(
            repo=str(REPO_ROOT),
            tests=str(REPO_ROOT / "tests"),
            marker=MARKER_JSON,
            effects=EFFECTS_JSON,
            seconds=CHILD_SECONDS,
        ),
        encoding="utf-8",
    )
    foreman = tmp_path / "foreman_main.py"
    foreman.write_text(FOREMAN_MAIN, encoding="utf-8")

    process = subprocess.Popen(
        [
            sys.executable,
            str(foreman),
            str(wrapper),
            str(tmp_path),
            str(tmp_path / "wrapper.log"),
            root.root_id,
        ]
    )
    try:
        _await(tmp_path / "WRAPPER-STARTED")
        os.kill(process.pid, signal.SIGKILL)
        process.wait(timeout=SENTINEL_TIMEOUT_S)
        _await(tmp_path / "WRAPPER-DONE")
    finally:
        if process.poll() is None:  # pragma: no cover - only on an early failure
            process.kill()

    assert (tmp_path / "WRAPPER-DONE").read_text(encoding="utf-8") == "exit-recorded"
    # Read back through a SECOND connection to the one database file: that is
    # what "two processes share a store" is since S6 (R1).
    _, reader = make_persistent_store(tmp_path, head_of(repo), state)
    (activation,) = reader.reads.list_activations(root.root_id)
    assert activation.metadata.lifecycle is Lifecycle.EXIT_RECORDED
    assert activation.metadata.exit_record is not None
    assert activation.metadata.exit_record.exit_code == 0


def _await(sentinel: Path, timeout_s: float = SENTINEL_TIMEOUT_S) -> None:
    """Wait for a file another process writes, or fail the test."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if sentinel.exists():
            return
        time.sleep(0.05)
    raise AssertionError(f"{sentinel.name} never appeared")
