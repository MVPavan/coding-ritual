"""§8.2 monitoring: the stale flag, the `max_wall` ceiling, and zero tokens.

Drill 14's real claim is that the stale flag is raised **while the foreman is
not running**. Under manual ticks that is a structural property, not a timing
one, so it is asserted structurally: `Monitor` is constructed from a config, a
wrapper directory and a clock, and there is no way to hand it a bd store or a
model at all. The rest is arithmetic over an injected clock, which is why a
45-minute runaway costs microseconds here.

Drill 16 (`max_wall` → TERM, exit reason recorded) needs a real child to
signal, so that one test is marked `proc`.
"""

from __future__ import annotations

import inspect
import os
import signal
import subprocess
import time
from pathlib import Path

import pytest

from tests._fake_bd import FakeBd
from tests._supervisor import (
    IMPLEMENT,
    SESSION_ID,
    ChildScript,
    FakeProfile,
    FrozenClock,
    entry_mint,
    handle_for,
    head_of,
    make_config,
    make_paths,
    make_repo,
    make_root,
    make_store,
    node_of,
    remove_proc_entry,
    task_builder,
    write_proc_entry,
)
from workflow_interpreter.bdio import Lifecycle
from workflow_interpreter.supervisor import (
    ExitReason,
    ForkBarrierLauncher,
    Limits,
    Monitor,
    MonitorVerdict,
    ReapResult,
    StaleFlag,
    SupervisorConfig,
    WrapperPaths,
    channels_for,
)
from workflow_interpreter.supervisor import procfs as procfs_module
from workflow_interpreter.supervisor.models import EXIT_CODE_UNOBSERVED
from workflow_interpreter.supervisor.monitor import TERMINAL_VERDICTS
from workflow_interpreter.supervisor.paths import read_record
from workflow_interpreter.supervisor.run import _exit_code, _exit_reason, _StaleMirror

STALE_AFTER_S = 600.0
MAX_WALL_S = 2700.0
FAKE_PID = 424242
ROOT_ID = "wf-monitor"
LATE_EXIT_CODE = 3
"""An exit status that only the SECOND reap can see (the two-read window)."""
ADOPTED_EXIT_CODE = 7
"""The status a REATTACHED child really exits with, and which no `waitpid` in
the adopting process can ever collect."""


class Watched:
    """A fake `/proc` process plus the wrapper dir the monitor inspects."""

    def __init__(self, tmp_path: Path) -> None:
        self.repo = make_repo(tmp_path)
        self.config: SupervisorConfig = make_config(self.repo, tmp_path)
        self.paths: WrapperPaths = make_paths(self.config, ROOT_ID)
        self.clock = FrozenClock()
        self.activation_id = "wf-9"
        self.paths.ensure_activation_dir(self.activation_id)
        write_proc_entry(self.config.proc_root, FAKE_PID)
        self.handle = handle_for(
            FAKE_PID,
            started_at="2026-08-25T12:00:00Z",
            log_path=str(self.paths.log(self.activation_id)),
        )
        self.monitor = Monitor(
            self.config,
            self.paths,
            self.clock,
            activation_id=self.activation_id,
            handle=self.handle,
            limits=Limits(stale_after_s=STALE_AFTER_S, max_wall_s=MAX_WALL_S),
        )

    def emit(self, text: str) -> None:
        """Append bytes to the runner log — the only activity signal there is."""
        with self.paths.log(self.activation_id).open("a", encoding="utf-8") as log:
            log.write(text)


@pytest.fixture
def watched(tmp_path: Path) -> Watched:
    """A live fake child being monitored."""
    return Watched(tmp_path)


def test_monitor_cannot_reach_bd_or_a_model(watched: Watched) -> None:
    """Drill 14, by construction: nothing in the loop can consume a token."""
    parameters = set(inspect.signature(Monitor.__init__).parameters)

    assert parameters == {
        "self",
        "config",
        "paths",
        "clock",
        "activation_id",
        "handle",
        "limits",
    }


def test_a_whole_watch_raises_the_flag_without_one_bd_command(
    watched: Watched, tmp_path: Path
) -> None:
    """Drill 14, MEASURED: the constructor check alone proves nothing at runtime.

    A signature says a store was never handed in; it says nothing about a
    module-level import, a global, or a `subprocess` reaching for bd. So this
    runs a full `watch()` through a stale cycle to a terminal verdict with a
    live bd transport present in the same process, and counts the commands it
    issued: zero, while the flag is on disk.
    """
    fake, _ = make_store(tmp_path, "head")
    watched.clock.advance(STALE_AFTER_S + 1)
    watched.clock.on_sleep.append(
        lambda: remove_proc_entry(watched.config.proc_root, FAKE_PID)
    )

    result = watched.monitor.watch()

    assert result.verdict is MonitorVerdict.EXITED
    assert watched.paths.stale_flag(watched.activation_id).exists()
    assert fake.calls == []


def test_a_busy_child_is_simply_running(watched: Watched) -> None:
    """§8.2: byte growth is activity, and activity resets the staleness clock."""
    watched.clock.advance(STALE_AFTER_S + 1)
    watched.emit("event\n")

    result = watched.monitor.observe()

    assert result.verdict is MonitorVerdict.RUNNING
    assert result.log_size > 0
    assert not watched.paths.stale_flag(watched.activation_id).exists()


def test_silence_past_stale_after_raises_the_flag(watched: Watched) -> None:
    """Drill 14: the wrapper writes the stale flag with the last-event timestamp."""
    watched.clock.advance(STALE_AFTER_S + 1)

    result = watched.monitor.observe()

    assert result.verdict is MonitorVerdict.STALE
    flag = read_record(watched.paths.stale_flag(watched.activation_id), StaleFlag)
    assert flag is not None
    assert flag.last_activity_at == watched.handle.started_at
    assert flag.stale_after_s == STALE_AFTER_S
    assert result.stale == flag
    # The FIRST window only flags: §8.2's stale watch gives the runner one more
    # `stale_after` before it becomes terminable.
    assert result.termination is None


def test_the_stale_flag_keeps_its_first_timestamp(watched: Watched) -> None:
    """A re-raise must not rewrite when the runner actually went quiet."""
    watched.clock.advance(STALE_AFTER_S + 1)
    first = watched.monitor.observe()
    # Still inside the second window, which is what keeps this a re-raise
    # rather than the termination the window's end brings.
    watched.clock.advance(STALE_AFTER_S / 2)

    second = watched.monitor.observe()

    assert second.verdict is MonitorVerdict.STALE
    assert first.stale is not None
    assert second.stale is not None
    assert second.stale.raised_at == first.stale.raised_at


def test_activity_after_the_flag_defers_the_stale_termination(
    watched: Watched,
) -> None:
    """§8.2: the second window is silence, so any byte restarts the count.

    A runner that goes quiet, is flagged, and then speaks again is working —
    terminating it at a fixed `2 x stale_after` after the flag would kill it
    for a silence that ended.
    """
    watched.clock.advance(STALE_AFTER_S + 1)
    flagged = watched.monitor.observe()
    watched.emit("event\n")
    watched.clock.advance(STALE_AFTER_S)
    busy = watched.monitor.observe()
    watched.clock.advance(STALE_AFTER_S + 1)

    quiet_again = watched.monitor.observe()

    assert flagged.verdict is MonitorVerdict.STALE
    assert busy.verdict is MonitorVerdict.RUNNING
    assert quiet_again.verdict is MonitorVerdict.STALE
    assert quiet_again.termination is None


def test_a_second_stale_window_of_silence_is_terminable(watched: Watched) -> None:
    """§8.2: the watch ENDS a runner that stays silent through both windows.

    The fake `/proc` entry never goes away, so this is the unkillable shape:
    the kill is not confirmed, so it is not terminal — the same rule the
    `max_wall` ceiling obeys.
    """
    watched.clock.advance(2 * STALE_AFTER_S + 1)

    result = watched.monitor.observe()

    assert result.verdict is MonitorVerdict.INDETERMINATE
    assert result.verdict not in TERMINAL_VERDICTS
    assert result.termination is not None
    assert result.termination.confirmed_dead is False
    assert watched.paths.stale_flag(watched.activation_id).exists()


def test_max_wall_outranks_staleness_in_the_same_cycle(
    watched: Watched, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both ceilings breached is a runaway: the universal ceiling is recorded.

    A `max_wall` breach is silent by definition long before it is old enough,
    so the check order is the whole policy — and the flag file is the tell,
    since the staleness path raises it before it terminates.
    """
    watched.clock.advance(MAX_WALL_S + 1)

    first = watched.monitor.observe()

    assert first.verdict is MonitorVerdict.INDETERMINATE
    assert not watched.paths.stale_flag(watched.activation_id).exists()

    monkeypatch.setattr(
        procfs_module, "collect", lambda pid: ReapResult(exit_code=-signal.SIGKILL)
    )

    result = watched.monitor.observe()

    assert result.verdict is MonitorVerdict.MAX_WALL_BREACH
    assert result.exit_reason is ExitReason.MAX_WALL


def test_a_node_without_stale_after_is_never_terminated_for_silence(
    watched: Watched,
) -> None:
    """`stale_after` unset is §2's "no staleness policy", not a zero deadline."""
    monitor = Monitor(
        watched.config,
        watched.paths,
        watched.clock,
        activation_id=watched.activation_id,
        handle=watched.handle,
        limits=Limits(stale_after_s=0.0, max_wall_s=MAX_WALL_S),
    )
    watched.clock.advance(MAX_WALL_S - 1)

    result = monitor.observe()

    assert result.verdict is MonitorVerdict.RUNNING
    assert result.termination is None
    assert not watched.paths.stale_flag(watched.activation_id).exists()


def test_a_vanished_process_reads_as_exited(watched: Watched) -> None:
    """§8.2: liveness is `/proc` plus identity, and neither survives an exit."""
    remove_proc_entry(watched.config.proc_root, FAKE_PID)

    result = watched.monitor.observe()

    assert result.verdict is MonitorVerdict.EXITED


def test_a_child_that_dies_between_the_two_reads_keeps_its_exit_code(
    watched: Watched, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`waitpid` and `/proc` are two reads, and the child can die between them.

    Concluding "gone, code unknown" from that ordering threw away the status of
    every child short-lived enough to exit inside the window — recorded as
    `exit_unobserved`, which is §5.6's word for a transport failure and not for
    a run that finished. The interleaving is expressed as data rather than
    raced for: the first reap reports "still running", `/proc` then says dead.

    `ours` stays true through both answers: this is a child the wrapper really
    could have waited for, which is what separates it from the adopted case.
    """
    remove_proc_entry(watched.config.proc_root, FAKE_PID)
    answers = iter(
        [
            ReapResult(),
            ReapResult(exit_code=LATE_EXIT_CODE),
        ]
    )
    monkeypatch.setattr(procfs_module, "collect", lambda pid: next(answers))

    result = watched.monitor.observe()

    assert result.verdict is MonitorVerdict.EXITED
    assert result.exit_code == LATE_EXIT_CODE
    assert result.exit_reason is ExitReason.EXITED


def test_a_reused_pid_is_not_our_child(watched: Watched) -> None:
    """§5.3: the same pid with a different start time is somebody else."""
    write_proc_entry(watched.config.proc_root, FAKE_PID, start_time="999999")

    result = watched.monitor.observe()

    assert result.verdict is MonitorVerdict.EXITED


def test_an_unreadable_proc_is_never_recorded_as_an_exit(watched: Watched) -> None:
    """B6, the half that lived on the PRODUCTION path (probed).

    `Liveness.INDETERMINATE` has `alive == False`, and `_exited` asked only
    `.alive` — so a transient `/proc` failure on a perfectly healthy child read
    as "gone", ended the watch with verdict `exited` and no code, and `run.py`
    recorded `-256 / exit_unobserved`. That is §5.6's word for a transport
    failure: an infra retry was spent and a second child ran beside the
    survivor. A directory where `stat` should be reproduces the failure without
    needing a permission the test runner may not be able to drop.
    """
    stat = watched.config.proc_root / str(FAKE_PID) / "stat"
    stat.unlink()
    stat.mkdir()

    result = watched.monitor.observe()

    assert result.verdict is MonitorVerdict.INDETERMINATE
    assert result.exit_code is None
    assert result.verdict not in TERMINAL_VERDICTS


def test_the_watch_holds_position_until_proc_answers_again(watched: Watched) -> None:
    """B6: "hold position" means the loop KEEPS WATCHING, not that it guesses.

    The child here is alive throughout the unreadable window and then exits
    normally, and the watch has to end on that real exit rather than on the
    read error.
    """
    stat = watched.config.proc_root / str(FAKE_PID) / "stat"
    stat.unlink()
    stat.mkdir()

    def restore() -> None:
        stat.rmdir()
        write_proc_entry(watched.config.proc_root, FAKE_PID)

    watched.clock.on_sleep.append(restore)
    watched.clock.on_sleep.append(
        lambda: remove_proc_entry(watched.config.proc_root, FAKE_PID)
    )

    result = watched.monitor.watch()

    assert result.verdict is MonitorVerdict.EXITED
    assert len(watched.clock.sleeps) == 2


def test_a_max_wall_breach_that_cannot_prove_death_is_not_terminal(
    watched: Watched,
) -> None:
    """Opus#25: `_enforce_max_wall` recorded a terminal exit it never proved.

    `terminate` answers three ways, and `confirmed_dead = False` — the child
    survived TERM and KILL, or `/proc` could not be read — means it may still
    be writing the working tree. Recording `max-wall-breach` there ended the
    watch, wrote an exit record and released §5.6 to reset that tree underneath
    a live process. The fake `/proc` entry never goes away, which is exactly
    what an unkillable child looks like from here.
    """
    watched.clock.advance(MAX_WALL_S + 1)

    result = watched.monitor.observe()

    assert result.verdict is MonitorVerdict.INDETERMINATE
    assert result.verdict not in TERMINAL_VERDICTS
    assert result.exit_code is None
    assert result.exit_reason is None
    assert result.termination is not None
    assert result.termination.confirmed_dead is False


@pytest.mark.parametrize(
    ("silence_s", "verdict", "reason"),
    [
        (MAX_WALL_S + 1, MonitorVerdict.MAX_WALL_BREACH, ExitReason.MAX_WALL),
        (2 * STALE_AFTER_S + 1, MonitorVerdict.STALE_BREACH, ExitReason.STALE),
    ],
    ids=["max_wall", "stale"],
)
def test_an_unconfirmed_kill_is_reported_on_the_next_reap(
    watched: Watched,
    monkeypatch: pytest.MonkeyPatch,
    silence_s: float,
    verdict: MonitorVerdict,
    reason: ExitReason,
) -> None:
    """A delayed reap after an unconfirmed kill is still this wrapper's breach.

    One dance for both ceilings: the proof stays pending, so the status — when
    it finally arrives, cycles later — is recorded as the breach that caused
    the kill and not as an ordinary signal death.
    """
    stat = watched.config.proc_root / str(FAKE_PID) / "stat"
    reaped: list[int] = []

    def make_proc_indeterminate() -> None:
        stat.unlink()
        stat.mkdir()

    def record_reap(pid: int) -> None:
        reaped.append(pid)

    watched.clock.on_sleep.append(lambda: None)
    watched.clock.on_sleep.append(make_proc_indeterminate)
    monkeypatch.setattr(procfs_module, "reap", record_reap)
    watched.clock.advance(silence_s)

    first = watched.monitor.observe()

    assert first.verdict is MonitorVerdict.INDETERMINATE
    assert first.termination is not None
    assert first.termination.confirmed_dead is False
    assert reaped == []

    stat.rmdir()
    write_proc_entry(watched.config.proc_root, FAKE_PID)
    monkeypatch.setattr(
        procfs_module, "collect", lambda pid: ReapResult(exit_code=-signal.SIGKILL)
    )

    result = watched.monitor.observe()

    assert result.verdict is verdict
    assert result.verdict in TERMINAL_VERDICTS
    assert result.exit_reason is reason
    assert result.exit_code == -signal.SIGKILL
    assert result.termination == first.termination
    assert _exit_reason(result) is reason


def test_watch_returns_on_the_first_terminal_verdict(watched: Watched) -> None:
    """The loop polls at the configured interval and stops when the child is gone."""
    watched.clock.on_sleep.append(
        lambda: remove_proc_entry(watched.config.proc_root, FAKE_PID)
    )

    result = watched.monitor.watch()

    assert result.verdict is MonitorVerdict.EXITED
    assert watched.clock.sleeps == [watched.config.poll_interval_s]


@pytest.mark.proc
@pytest.mark.parametrize(
    ("silence_s", "verdict", "reason"),
    [
        (MAX_WALL_S + 1, MonitorVerdict.MAX_WALL_BREACH, ExitReason.MAX_WALL),
        (2 * STALE_AFTER_S + 1, MonitorVerdict.STALE_BREACH, ExitReason.STALE),
    ],
    ids=["max_wall", "stale"],
)
def test_a_breached_ceiling_terms_the_group_and_records_the_reason(
    tmp_path: Path,
    silence_s: float,
    verdict: MonitorVerdict,
    reason: ExitReason,
) -> None:
    """Drill 16 for both ceilings: TERM the group, record why (§8.2).

    The second case is the staleness one: a runner that stayed silent through
    a second `stale_after` window is ended exactly as a runaway is, so the
    same real child is signalled and the same proof is demanded — only the
    recorded reason differs.
    """
    repo = make_repo(tmp_path)
    config = make_config(repo, tmp_path, fake_proc=False)
    _, store = make_store(tmp_path, head_of(repo))
    root = make_root(store, repo, "runaway")
    paths = make_paths(config, root.root_id)
    clock = FrozenClock(real_sleep_s=0.05)
    activation = store.mint_activation(root.root_id, entry_mint()).activation
    activation_id = activation.activation_id
    paths.ensure_activation_dir(activation_id)
    node = node_of(root.definition.document, IMPLEMENT)
    profile = FakeProfile(ChildScript(sleep_s=30))
    command = profile.build_command(
        task_builder(repo, node)(
            activation,
            channels_for(paths.activation_dir(activation_id), paths.log(activation_id)),
        ),
        SESSION_ID,
    )
    handle = ForkBarrierLauncher(
        config, paths, clock, activation_id=activation_id, launch_id="runaway-1"
    )(command)

    clock.advance(silence_s)
    monitor = Monitor(
        config,
        paths,
        clock,
        activation_id=activation_id,
        handle=handle,
        limits=Limits(stale_after_s=STALE_AFTER_S, max_wall_s=MAX_WALL_S),
    )
    result = monitor.observe()

    assert result.verdict is verdict
    assert result.exit_reason is reason
    assert result.termination is not None
    assert result.termination.confirmed_dead is True
    assert "SIGTERM" in result.termination.signals_sent
    # Opus#23 / Sol#18: `terminate` reaps as its LAST act and a status can be
    # collected exactly once, so reaping again for the code always answered
    # `None` — recorded as EXIT_CODE_UNOBSERVED, which claims the wrapper never
    # saw a death it had just carried out. The proof carries the real status.
    assert result.exit_code == -signal.SIGTERM
    assert result.termination.exit_code == result.exit_code
    assert _exit_code(result) == -signal.SIGTERM
    assert _exit_reason(result) is reason
    _reap(handle.pid)


# --- the stale mirror can never end the watch (blocker 4b) ---------------


def _stale_mirror(watched: Watched, tmp_path: Path) -> tuple[FakeBd, _StaleMirror, str]:
    """A real `_StaleMirror` over a real store, watching a dispatched activation."""
    fake, store = make_store(tmp_path, head_of(watched.repo))
    root = make_root(store, watched.repo, "mirror-instance")
    minted = store.mint_activation(root.root_id, entry_mint()).activation
    activation_id = minted.activation_id
    store.record_dispatch(activation_id, handle_for(FAKE_PID))
    return fake, _StaleMirror(store, activation_id), activation_id


def test_a_bd_failure_in_the_mirror_defers_instead_of_killing_the_watch(
    watched: Watched, tmp_path: Path
) -> None:
    """Sol#25: an exception out of `on_cycle` aborted `Monitor.watch`.

    The stale flag is a HINT for a tier-2 decision; the watch is what enforces
    `max_wall` and what eventually records the exit. Trading the second for the
    first is the wrong way round — a bd hiccup left a live detached child with
    no ceiling and no exit record at all. So the mirror defers and the NEXT
    cycle retries, which is all the outbox this needs: the child is still
    stale and the flag is still on disk.
    """
    fake, mirror, activation_id = _stale_mirror(watched, tmp_path)
    row = fake.rows.pop(activation_id)
    watched.clock.advance(STALE_AFTER_S + 1)
    watched.clock.on_sleep.append(lambda: fake.rows.setdefault(activation_id, row))
    watched.clock.on_sleep.append(
        lambda: remove_proc_entry(watched.config.proc_root, FAKE_PID)
    )

    result = watched.monitor.watch(mirror)

    assert result.verdict is MonitorVerdict.EXITED
    assert mirror.recorded is True
    assert mirror.abandoned is None
    assert fake.rows[activation_id]["metadata"]["stale_flag"]["raised_at"] != ""


def test_a_foreman_closing_first_does_not_kill_the_watch(
    watched: Watched, tmp_path: Path
) -> None:
    """Blocker 4b: the close a stale flag PROVOKES must not abort the watch.

    A §8.1 steer is exactly what a stale child is supposed to trigger, so the
    activation being closed out from under the mirror is the expected case, not
    an exotic one. `record_stale_flag` refuses it (§8.2 is a statement about a
    RUNNING child) and the mirror absorbs the refusal: the lifecycle only moves
    forward, so it stops trying rather than spending a bd read every poll.
    """
    fake, mirror, activation_id = _stale_mirror(watched, tmp_path)
    fake.rows[activation_id]["metadata"]["lifecycle"] = Lifecycle.CLOSED.value
    watched.clock.advance(STALE_AFTER_S + 1)
    watched.clock.on_sleep.append(
        lambda: remove_proc_entry(watched.config.proc_root, FAKE_PID)
    )

    result = watched.monitor.watch(mirror)

    assert result.verdict is MonitorVerdict.EXITED
    assert mirror.recorded is False
    assert mirror.abandoned is not None
    assert watched.paths.stale_flag(watched.activation_id).exists()


def _reap(pid: int) -> None:
    """Reap a child the wrapper already killed, if it is still ours to reap."""
    try:
        os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        return


# --- the three /proc facts the watch cannot guess at ---------------------


def test_an_unreadable_boot_id_holds_position_instead_of_crashing(
    watched: Watched,
) -> None:
    """Opus#19: the one `/proc` read that sat OUTSIDE the INDETERMINATE contract.

    `read_boot_id` used a bare `read_text()`, so a container that lost its
    `/proc` mount — the module docstring's own example of an INDETERMINATE case
    — raised `FileNotFoundError` out of `prove_liveness`, through `observe`,
    `watch` and `Supervisor._supervise`, killing the resident supervisor with a
    live detached child, no exit record and nobody left to write one. The same
    read is what §5.6 recovery classifies on.
    """
    watched.config.boot_id_path.unlink()

    result = watched.monitor.observe()

    assert result.verdict is MonitorVerdict.INDETERMINATE
    assert result.verdict not in TERMINAL_VERDICTS
    assert result.exit_code is None


@pytest.mark.proc
def test_an_adopted_childs_exit_is_unobservable_rather_than_unobserved(
    tmp_path: Path,
) -> None:
    """Opus#20: `waitpid` can never collect the status of a REATTACHED child.

    REATTACHED means, by §5.2's own definition, that ANOTHER wrapper process
    exec'd the child and died before `record_dispatch`; the child is reparented
    to init, so it is not a child of the process now adopting it. `waitpid`
    answers ECHILD forever, the code is UNKNOWABLE — and recording it as
    `exit_unobserved` claimed §5.6's transport failure for a run that finished
    normally, which is the very thing adoption exists to stop.

    A REAL double-forked child, because that is the only shape that reproduces
    it: an in-process crash leaves the child still ours, so it reaps fine and
    the production case is never exercised.
    """
    repo = make_repo(tmp_path)
    config = make_config(repo, tmp_path, fake_proc=False)
    _, store = make_store(tmp_path, head_of(repo))
    root = make_root(store, repo, "adopted")
    paths = make_paths(config, root.root_id)
    activation_id = store.mint_activation(
        root.root_id, entry_mint()
    ).activation.activation_id
    paths.ensure_activation_dir(activation_id)
    pid = _orphan_child(tmp_path, ADOPTED_EXIT_CODE)
    boot_id = procfs_module.read_boot_id(config)
    assert boot_id is not None
    handle = handle_for(
        pid,
        boot_id=boot_id,
        start_time=procfs_module.read_start_time(config, pid) or "",
        log_path=str(paths.log(activation_id)),
    )
    monitor = Monitor(
        config,
        paths,
        FrozenClock(real_sleep_s=0.2),
        activation_id=activation_id,
        handle=handle,
        limits=Limits(stale_after_s=0.0, max_wall_s=0.0),
    )

    result = monitor.watch()

    assert result.verdict is MonitorVerdict.EXITED
    assert result.exit_code is None
    assert result.exit_reason is ExitReason.EXIT_STATUS_UNOBSERVABLE_REATTACHED
    assert _exit_reason(result) is ExitReason.EXIT_STATUS_UNOBSERVABLE_REATTACHED
    assert _exit_code(result) == EXIT_CODE_UNOBSERVED


def _orphan_child(tmp_path: Path, exit_code: int) -> int:
    """Start a `setsid` grandchild and let its parent die, as a crash would.

    The pid is read out of a file the grandchild writes, because the only
    process that ever knew it directly is the intermediate `sh` — which is
    exactly the wrapper whose death made this an adoption.
    """
    pidfile = tmp_path / "orphan.pid"
    script = tmp_path / "orphan.sh"
    script.write_text(
        f"#!/bin/sh\necho $$ > {pidfile}\nsleep 1\nexit {exit_code}\n", encoding="utf-8"
    )
    script.chmod(0o755)
    subprocess.run(["sh", "-c", f"setsid {script} &"], check=True, timeout=30)
    deadline = time.monotonic() + 10.0
    while not pidfile.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    time.sleep(0.1)
    return int(pidfile.read_text(encoding="utf-8").strip())
