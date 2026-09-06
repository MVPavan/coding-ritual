"""The profiles driven through the REAL phase-3 machinery, with stub CLIs.

Nothing here is mocked below the profile: a real `Supervisor.run`, a real
`ForkBarrierLauncher`, a real fork/exec into a real process, a real exec ledger,
a real §5.4 worktree precondition and a real §7 grading pass. Only the vendor
binary is a stand-in — an `sh` script that emits that vendor's JSONL shape and
writes the §6 channels — which is what makes an end-to-end proof affordable
enough to run on every commit.

The `Lab` these tests drive lives in `tests/_profiles.py` and the `lab` fixture
in `conftest.py`, because §8.1 session continuity grew a module of its own
(`test_profiles_steer.py`) around the same wiring.

The `live` family (`test_profiles_live.py`) runs the same argv against the real
CLIs; this one proves the composition.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

import pytest

from tests._profiles import (
    FD0_FILE,
    FORGED_LINE,
    FORGED_RECORDS,
    PUSH_PROBE_FILE,
    PUSH_PROBE_REMOTES,
    STUB_SESSION,
    Lab,
    add_remote,
)
from tests._supervisor import (
    make_repo,
)
from workflow_interpreter.bdio import Lifecycle
from workflow_interpreter.profiles import RunnerName
from workflow_interpreter.profiles._base import PUSH_SINK
from workflow_interpreter.supervisor import ExecLedger
from workflow_interpreter.supervisor.models import LaunchReceipt
from workflow_interpreter.supervisor.paths import read_record

MISSING_BINARY: Final[str] = "/nonexistent/vendor-cli"
EXIT_EXEC_FAILED: Final[int] = 127
"""`launch.py::_child` exits 127 when `execvpe` cannot run the program — the
POSIX convention, and drill 22's injection point."""


@pytest.mark.proc
@pytest.mark.parametrize("runner", [RunnerName.CLAUDE, RunnerName.CODEX])
@pytest.mark.parametrize("writes", [True, False])
def test_a_real_profile_dispatches_and_reaches_exit_recorded(
    lab: Lab, runner: RunnerName, writes: bool
) -> None:
    """Phase 4 composes with phase 3: one exec, one exit, one bd mirror.

    Both `writes` modes of both launchable vendors, because the two modes build
    genuinely different invocations — codex even runs them from different
    working directories.
    """
    result = lab.run(runner, writes=writes)

    activation_id = result.dispatch.activation.activation_id
    assert ExecLedger(lab.paths.ledger(activation_id)).count() == 1
    assert result.observation is not None
    assert result.observation.exit_record.exit_code == 0
    assert result.observation.activation.metadata.lifecycle is Lifecycle.EXIT_RECORDED
    assert result.observation.collected.marker is not None


@pytest.mark.proc
def test_the_receipt_records_the_argv_the_profile_actually_built(lab: Lab) -> None:
    """§5.2's receipt is the durable record of what crossed the barrier.

    Asserting the danger default HERE rather than on a built command is the
    difference between "the profile intended read-only" and "a read-only child
    really ran".
    """
    result = lab.run(RunnerName.CODEX, writes=False)

    receipt = result.dispatch.receipt
    assert receipt is not None
    assert "workspace-write" in receipt.argv
    assert "read-only" not in receipt.argv
    assert "--dangerously-bypass-approvals-and-sandbox" not in receipt.argv
    assert receipt.cwd == str(
        lab.paths.channels_dir(result.dispatch.activation.activation_id)
    )


@pytest.mark.proc
def test_a_writing_node_runs_in_the_checkout(lab: Lab) -> None:
    """`writes = true` is repo-worktree write access, so that is the cwd."""
    result = lab.run(RunnerName.CODEX, writes=True)

    receipt = result.dispatch.receipt
    assert receipt is not None
    assert receipt.cwd == str(lab.paths.worktree)


@pytest.mark.proc
@pytest.mark.parametrize(
    "runner",
    [
        pytest.param(RunnerName.CODEX, id="codex-sandbox-backed"),
        pytest.param(RunnerName.CLAUDE, id="claude-layout-only"),
    ],
)
def test_a_child_cannot_forge_the_wrapper_records_from_inside_its_grant(
    lab: Lab, runner: RunnerName
) -> None:
    """B2: the runner's writable surface and the wrapper's records are disjoint.

    The stub writes every wrapper record it could reach the only way a sandboxed
    child could — relative to the directory holding `$WF_OUTCOME_FILE` —
    `exec.ledger`, `launch-receipt.json`, `exit.json`, `completion.json`. The run
    still has to end with the wrapper's own ledger line, the wrapper's own
    receipt, and a graded exit. Before the channels moved into `channels/`, that
    grant WAS the activation directory, so the same three-line junk landed on the
    exec ledger the exactly-once drills count and on the receipt the next
    dispatch parses.

    **The two parameters prove different amounts, and the ids say which.** The
    stub is not sandboxed — it is an `sh` script the test execs — so what runs is
    identical in both cases and what it demonstrates is LAYOUT: the records are
    not inside the grant, whatever the grant is enforced with.

    - `codex-sandbox-backed` — the layout is backed by an OS bound. Codex's
      writable root is exactly `channels/` on a `writes = false` node, plus the
      checkout on a writing one, and `SupervisorConfig` refuses a `wrapper_root`
      inside `repo_root` so the activation directory is outside both.
      Enforcement itself is the `live` family's to show; this shows the layout it
      enforces.
    - `claude-layout-only` — wrapper-side only. Claude has no OS sandbox:
      its `Edit` rules name the three §6
      channels by exact path and never the activation directory, but a
      `writes = true` node also grants `Bash`, and a shell can write any path the
      permission engine was not asked about. That residual is §0.3's cooperative
      one and no assertion here closes it.
    """
    result = lab.run(runner, forge=True)

    activation_id = result.dispatch.activation.activation_id
    ledger = ExecLedger(lab.paths.ledger(activation_id))
    receipt = read_record(lab.paths.receipt(activation_id), LaunchReceipt)
    assert receipt is not None
    assert ledger.count() == 1
    assert [entry.launch_id for entry in ledger.entries()] == [receipt.launch_id]
    assert result.observation is not None
    assert result.observation.exit_record.exit_code == 0
    assert result.observation.collected.marker is not None

    grant = lab.paths.channels_dir(activation_id)
    activation_dir = lab.paths.activation_dir(activation_id)
    for record in FORGED_RECORDS:
        assert (grant / record).read_text(encoding="utf-8").startswith(FORGED_LINE)
        assert FORGED_LINE not in (
            (activation_dir / record).read_text(encoding="utf-8")
            if (activation_dir / record).exists()
            else ""
        )


@pytest.mark.proc
def test_a_broken_cli_binary_leaves_one_countable_exec_and_no_graded_outcome(
    lab: Lab,
) -> None:
    """Drill 22, the half a stub CLI can prove: transport-shaped exit, no marker.

    The barrier still completes — the child appends its ledger line BEFORE it
    execs — so the attempt is countable, which is what the drill's
    `1 + max_infra_retries` arithmetic is made of. The exit code is 127 rather
    than a runner's, and `$WF_OUTCOME_FILE` holds nothing, so §7 has no claim to
    grade and no outcome is recorded.

    Renamed from `..._is_a_transport_failure_not_a_runner_verdict`, which
    claimed more than it showed: "no stored outcome" is true of a transport
    failure AND of a clean run that never wrote a marker, so it discriminated
    nothing about ROUTING. Drill 22's other half — that the foreman routes this
    to `error_transport` and spends an infra retry rather than a review round —
    is phase-5 work, because nothing in phase 4 routes anything.
    """
    result = lab.run(RunnerName.CLAUDE, binary=MISSING_BINARY)

    activation_id = result.dispatch.activation.activation_id
    assert ExecLedger(lab.paths.ledger(activation_id)).count() == 1
    assert result.observation is not None
    assert result.observation.exit_record.exit_code == EXIT_EXEC_FAILED
    assert result.observation.collected.marker is None
    assert result.observation.activation.metadata.outcome is None
    assert result.observation.usage.known is False


@pytest.mark.proc
def test_the_runners_stream_is_stored_only_inside_the_wrapper_directory(
    lab: Lab,
) -> None:
    """Drill 20, the half about STORAGE: the stream lands in `.wf/` and nowhere else.

    The profile never opens the log at all — `launch.py::_child` dup2s it onto
    the child's stdout and stderr — so what is provable here is that the
    runner's bytes exist in exactly one place and that place is inside `.wf/`.

    Renamed from `test_no_runner_log_bytes_leave_the_wrapper_directory`, which
    read as a claim about the foreman never LOADING the transcript. That half —
    §8.2's "the foreman's model reads bytes only at transitions", byte-budgeted
    — belongs to whatever does the reading, and nothing in phase 4 reads a log
    into a model at all. Phase 5.
    """
    result = lab.run(RunnerName.CLAUDE)

    activation_id = result.dispatch.activation.activation_id
    log = lab.paths.log(activation_id)
    assert log.read_text(encoding="utf-8").count('"type"') >= 3
    assert log.is_relative_to(lab.config.wrapper_root)
    stray = [
        path
        for path in lab.repo.rglob("*")
        if path.is_file() and b'"type"' in path.read_bytes()
    ]
    assert stray == []


@pytest.mark.proc
def test_the_envelope_reads_the_log_the_launcher_created(lab: Lab) -> None:
    """The §6 envelope is computed from the runner's own stream, end to end."""
    result = lab.run(RunnerName.CLAUDE)

    assert result.observation is not None
    usage = result.observation.usage
    assert usage.known is True
    assert (usage.input_tokens, usage.output_tokens) == (11, 22)
    assert usage.cost_usd == "0.25"


@pytest.mark.proc
def test_usage_unknown_is_legal_all_the_way_through(lab: Lab) -> None:
    """§6: a runner that reports no usage still completes; `max_wall` still holds."""
    silent = lab.bin / "stub-silent"
    silent.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"not json at all\"\n"
        'printf \'%s\' "$WF_MARKER" > "$WF_OUTCOME_FILE"\n'
        'printf \'%s\' "$WF_EFFECTS" > "$WF_EFFECTS_FILE"\n'
        "exit 0\n",
        encoding="utf-8",
    )
    silent.chmod(0o755)

    result = lab.run(RunnerName.CODEX, binary=silent)

    assert result.observation is not None
    assert result.observation.exit_record.exit_code == 0
    assert result.observation.usage.known is False
    assert result.observation.collected.marker is not None


@pytest.mark.proc
def test_a_codex_session_id_is_discovered_from_the_stream_and_reported(
    lab: Lab,
) -> None:
    """§5.2 deviation, made visible: codex names its own thread in event one."""
    result = lab.run(RunnerName.CODEX)

    assert result.observation is not None
    assert result.observation.collected.session_id == STUB_SESSION


@pytest.mark.proc
def test_the_profile_execs_through_the_supervisors_launcher(lab: Lab) -> None:
    """§5.2/§6: the fork barrier is not delegable, and `launch.py` checks.

    A profile that forked its own child would produce no receipt under this
    launch id, and the dispatcher refuses. The evidence that it did NOT is a
    receipt whose handle matches the ledger line.
    """
    result = lab.run(RunnerName.CLAUDE)

    receipt = result.dispatch.receipt
    assert receipt is not None
    assert result.dispatch.handle is not None
    assert receipt.handle.pid == result.dispatch.handle.pid
    entries = ExecLedger(
        lab.paths.ledger(result.dispatch.activation.activation_id)
    ).entries()
    assert [entry.pid for entry in entries] == [receipt.handle.pid]


@pytest.mark.proc
def test_the_childs_stdin_is_dev_null(lab: Lab, tmp_path: Path) -> None:
    """M9: `_child` redirects fd 1 and fd 2, and used to leave fd 0 alone.

    Every CLI probed reads or waits on stdin — claude stalls three seconds per
    launch and then warns, codex announces "Reading additional input from
    stdin..." — and a runner given no prompt argument blocks on it outright.

    The test PUTS a recognisable file on its own fd 0 first, because a harness
    whose stdin already happens to be `/dev/null` would make this pass either
    way. What the child inherits is then either that file (no redirect) or
    `/dev/null` (redirect), and it asks `/proc` rather than being told.
    """
    marker = tmp_path / "the-wrappers-own-stdin"
    marker.write_text("", encoding="utf-8")
    saved = os.dup(0)
    supplied = os.open(marker, os.O_RDONLY)
    try:
        os.dup2(supplied, 0)
        result = lab.dispatch(RunnerName.CODEX, sleep_s=0.0, fd0_probe=True)
        assert result.handle is not None
        assert lab.await_exit(result.handle) == 0
    finally:
        os.dup2(saved, 0)
        os.close(saved)
        os.close(supplied)

    observed = (
        lab.paths.artifacts(result.activation.activation_id) / FD0_FILE
    ).read_text(encoding="utf-8")
    assert observed.strip() == os.devnull
    assert str(marker) not in observed


# --- the vendor-neutral push backstop -------------------------------------


@pytest.mark.proc
@pytest.mark.parametrize("runner", [RunnerName.CLAUDE, RunnerName.CODEX])
def test_a_push_from_inside_the_child_env_is_rewritten_to_the_sink(
    lab: Lab, runner: RunnerName
) -> None:
    """M5b: "no profile ever pushes", for every vendor and every URL spelling.

    It used to be three claude deny-rules matching one spelling of one command,
    in one of the three vendors. This runs a REAL `git` inside a REAL forked
    child, in the environment `BaseProfile.child_env` built, and asks git itself
    what a push would talk to. The rewrite is what git reports, and the push
    attempt that follows never leaves the machine.

    Four remotes rather than one, because the backstop's prefix list was the
    same class of defect it was raised to fix: `deploy@host:repo`, `ftp://` and a
    local path all reported themselves UNCHANGED under the five-prefix version
    (R3), while the docstring said every form was covered. One `pushInsteadOf`
    entry on the empty prefix covers them, and only asserting on all four can
    tell the difference.
    """
    repo = make_repo(lab.tmp_path, name=f"push-probe-{runner.value}")
    for name, url in PUSH_PROBE_REMOTES:
        add_remote(repo, name, url)

    result = lab.dispatch(
        runner,
        session_id="",
        sleep_s=0.0,
        push_probe=True,
        extra_env={"WF_PUSH_REPO": str(repo)},
    )

    assert result.handle is not None
    assert lab.await_exit(result.handle) == 0
    activation_id = result.activation.activation_id
    observed = (lab.paths.artifacts(activation_id) / PUSH_PROBE_FILE).read_text(
        encoding="utf-8"
    )
    rewritten = dict(
        line.split(" ", 1)
        for line in observed.splitlines()
        if line.startswith(tuple(f"{name} " for name, _ in PUSH_PROBE_REMOTES))
    )
    assert sorted(rewritten) == sorted(name for name, _ in PUSH_PROBE_REMOTES), observed
    for name, url in PUSH_PROBE_REMOTES:
        assert rewritten[name].startswith(PUSH_SINK), (name, observed)
        assert rewritten[name] != url, (name, observed)
    assert "remote-wf-no-push" in observed, observed
    assert "push_rc=0" not in observed, observed
