"""The composition root: dispatch → watch → exit-recorded, in one process.

Three properties that only exist once something OWNS the sequence:

- the §3.2 carry-forward trio reaches bd BEFORE the child can exec (B7);
- the §8.2 stale flag reaches bd as well as the wrapper dir (§8.2, M11);
- the exit still gets recorded after the process that started the supervisor is
  killed (§5.3's "alive for the child's lifetime", B5).

The last one is a real three-process drill — pytest spawns a foreman, the
foreman spawns a wrapper, the wrapper spawns a runner, and the foreman is
SIGKILLed while the runner is still going. bd is file-backed for it
(`PersistentBd`), because the whole question is whether writes made by a
process the test does not own still land.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests._fake_bd import InjectedCrash
from tests._supervisor import (
    IMPLEMENT,
    ChildScript,
    FakeProfile,
    FrozenClock,
    entry_mint,
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
from workflow_interpreter.bdio import Lifecycle
from workflow_interpreter.schema.models import IsolationMode
from workflow_interpreter.supervisor import (
    ExecLedger,
    LaunchOutcome,
    MonitorVerdict,
    SupervisionResult,
    Supervisor,
    pinned_verifier_digests,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKER_JSON = '{"outcome":"done"}'
EFFECTS_JSON = '{"paths":[]}'
STALE_AFTER = "1s"
CHILD_SECONDS = 3.0
SENTINEL_TIMEOUT_S = 90.0

WRAPPER_MAIN = '''
"""A supervisor wrapper in its own process, for the parent-death drill."""
import sys
from pathlib import Path

sys.path.insert(0, {repo!r})
sys.path.insert(0, {tests!r})

import structlog

structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(50))

from tests._supervisor import (
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
from workflow_interpreter.supervisor import (
    Supervisor,
    SystemClock,
    Workspace,
    pinned_verifier_digests,
)

tmp = Path(sys.argv[1])
root_id = sys.argv[2]
repo = tmp / "repo"
config = make_config(repo, tmp, fake_proc=False, poll_interval_s=0.2)
_, store = make_persistent_store(tmp, head_of(repo), tmp / "bd-state.json")
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
result = Supervisor(config, paths, git, store, workspace, clock).run(
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
        self.root = make_root(self.store, self.repo, "run-instance")
        self.paths = make_paths(self.config, self.root.root_id)
        self.clock = FrozenClock()
        self.git = make_git(self.config)
        self.workspace = make_workspace(self.paths, self.git, self.clock)
        self.node = node_of(self.root.definition.document, IMPLEMENT)
        self.supervisor = Supervisor(
            self.config, self.paths, self.git, self.store, self.workspace, self.clock
        )

    def supervise(self, script: ChildScript) -> SupervisionResult:
        """Run one activation end to end against a scripted child."""
        return self.supervisor.run(
            entry_mint(),
            self.node,
            FakeProfile(script),
            task_builder(self.paths.worktree, self.node),
            pinned_digests=pinned_verifier_digests(self.root),
        )


@pytest.fixture
def lab(tmp_path: Path) -> Lab:
    """A supervisor over a throwaway repo and an in-memory bd."""
    return Lab(tmp_path)


@pytest.mark.proc
def test_one_call_dispatches_watches_and_records_the_exit(lab: Lab) -> None:
    """B5: nothing in the package tied dispatch → watch → exit before this.

    `Monitor.watch` and `ExitObserver` had zero non-test callers, so in
    production shape no process enforced `max_wall` or wrote the exit record.
    """
    result = lab.supervise(
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
    lab.fake_bd.pause_before(
        "update",
        lambda: ledger_at_write.append(
            ExecLedger(lab.paths.ledger(activation_id)).count()
        ),
    )

    result = lab.supervise(ChildScript(marker=MARKER_JSON, effects=EFFECTS_JSON))

    metadata = lab.store.reads.load_activation(activation_id).metadata
    assert metadata.pre_attempt_commit == lab.base
    assert metadata.reset_verified_commit == lab.base
    assert ledger_at_write == [0]
    assert result.dispatch.precondition is not None


@pytest.mark.proc
def test_a_re_dispatch_does_not_rewrite_a_recorded_precondition(lab: Lab) -> None:
    """§5.1: the trio describes a tree the child already ran against."""
    lab.supervise(ChildScript(marker=MARKER_JSON, effects=EFFECTS_JSON))
    before = lab.fake_bd.command_count("update")

    second = lab.supervise(ChildScript(marker=MARKER_JSON, effects=EFFECTS_JSON))

    assert second.observation is None
    assert second.dispatch.precondition is None
    assert lab.fake_bd.command_count("update") == before


@pytest.mark.proc
def test_a_stale_child_raises_the_flag_on_disk_and_in_bd(tmp_path: Path) -> None:
    """M11: §8.2 says "file AND bd metadata"; only the file existed.

    Losing `.wf/` therefore lost a decision-relevant datum, which §P1 says the
    observation cache is never allowed to hold alone. The mirror lives in the
    supervisor, not in the loop: `Monitor` still cannot reach bd at all.
    """
    lab = Lab(tmp_path)
    lab.node = lab.node.model_copy(update={"stale_after": STALE_AFTER})
    lab.clock.real_sleep_s = 0.05

    result = lab.supervise(ChildScript(sleep_s=CHILD_SECONDS, marker=MARKER_JSON))

    activation_id = result.dispatch.activation.activation_id
    assert result.stale_recorded is True
    assert lab.paths.stale_flag(activation_id).exists()
    recorded = lab.store.reads.load_activation(activation_id).metadata.stale_flag
    assert recorded is not None
    assert recorded.raised_at != ""


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
    lab.fake_bd.crash_on("update", 2)
    script = ChildScript(
        sleep_s=CHILD_SECONDS, marker=MARKER_JSON, effects=EFFECTS_JSON
    )
    with pytest.raises(InjectedCrash):
        lab.supervise(script)

    result = lab.supervise(script)

    activation_id = result.dispatch.activation.activation_id
    assert result.dispatch.outcome is LaunchOutcome.REATTACHED
    assert result.monitor is not None
    assert result.monitor.verdict is MonitorVerdict.EXITED
    assert result.observation is not None
    assert result.observation.exit_record.exit_code == 0
    assert result.observation.activation.metadata.lifecycle is Lifecycle.EXIT_RECORDED
    assert ExecLedger(lab.paths.ledger(activation_id)).count() == 1


@pytest.mark.proc
def test_an_in_repo_node_runs_inside_the_execution_band(lab: Lab) -> None:
    """Opus#30: `Supervisor.run` never acquired the §12 band.

    So the composition root that §5.3 says owns the lifecycle could not run an
    in-repo node at all — `prepare` refused it — and any caller that took the
    band itself had to keep holding it through the watch and the exit
    observation, since `ExitObserver` records what the runner left dirty while
    the band is still that runner's. Taken around the whole run, both hold.
    """
    node = lab.node.model_copy(update={"isolation": IsolationMode.IN_REPO})
    build = task_builder(lab.repo, node)
    held: list[bool] = []

    def watched_builder(activation: object, channels: object) -> object:
        held.append(lab.workspace.band.held)
        return build(activation, channels)  # type: ignore[arg-type]

    result = lab.supervisor.run(
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
    """B5's real claim: the supervisor outlives whatever started it.

    §5.3 gives the wrapper the child's whole lifetime, and drill 14 asserts the
    flags are raised "while the foreman process is not running". Both are only
    true if the wrapper is a process in its own right — so this one kills the
    parent of the wrapper mid-run and reads bd afterwards.
    """
    repo = make_repo(tmp_path)
    state = tmp_path / "bd-state.json"
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
    rows = json.loads(state.read_text(encoding="utf-8"))["rows"]
    activations = [
        row for row in rows.values() if row["metadata"].get("wf_kind") == "activation"
    ]
    assert len(activations) == 1
    assert activations[0]["metadata"]["lifecycle"] == Lifecycle.EXIT_RECORDED.value
    assert activations[0]["metadata"]["exit_record"]["exit_code"] == 0


def _await(sentinel: Path, timeout_s: float = SENTINEL_TIMEOUT_S) -> None:
    """Wait for a file another process writes, or fail the test."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if sentinel.exists():
            return
        time.sleep(0.05)
    raise AssertionError(f"{sentinel.name} never appeared")
