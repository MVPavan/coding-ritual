"""Real bounded host processes prove monitor independence and hook confinement."""

import json
import multiprocessing
import os
import signal
import sys
import time
from dataclasses import replace

import pytest

from tests._foreman import ForemanLab, LockedPersistentBd
from tests.test_bdio_wake import event_for
from workflow_interpreter.contracts.wake import WakeCondition
from workflow_interpreter.foreman.config import WakeConfig
from workflow_interpreter.foreman.heartbeat import DriverObserver
from workflow_interpreter.foreman.monitor import WakeMonitor
from workflow_interpreter.foreman.wake import HookError, run_hook
from workflow_interpreter.supervisor.clock import SystemClock


def _driver(composition, root_id, ready):
    """Leave startup heartbeat durable while a stub tick hangs."""
    os.setsid()
    with DriverObserver(composition, root_id):
        ready.set()
        time.sleep(30)


def _monitor(composition, root_id, ready, stop):
    """Run separately from the driver's group and survive its forced death."""
    os.setsid()
    with WakeMonitor(composition, root_id) as monitor:
        ready.set()
        while not stop.wait(0.01):
            monitor.poll()


@pytest.mark.proc
def test_monitor_survives_driver_death_and_records_stale_then_exit(tmp_path):
    """A hung driver's stale heartbeat and SIGKILL both wake a surviving process."""
    lab = ForemanLab(
        tmp_path,
        bd_factory=lambda workspace: LockedPersistentBd(
            workspace, tmp_path / "bd.json"
        ),
    )
    root = lab.instantiate()
    composition = replace(
        lab.composition,
        clock=SystemClock(),
        config=lab.config.model_copy(
            update={
                "wake": WakeConfig(poll_s=0.01, stale_s=0.1, min_fire_interval_s=0.01)
            }
        ),
    )
    context = multiprocessing.get_context("fork")
    driver_ready, monitor_ready = context.Event(), context.Event()
    monitor_stop = context.Event()
    driver = context.Process(
        target=_driver, args=(composition, root.root_id, driver_ready)
    )
    monitor = context.Process(
        target=_monitor, args=(composition, root.root_id, monitor_ready, monitor_stop)
    )
    driver.start()
    monitor.start()
    try:
        assert driver_ready.wait(5)
        assert monitor_ready.wait(5)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            events = lab.store.reads.list_wake_events(root.root_id)
            if any(
                event.condition is WakeCondition.HEARTBEAT_STALE for event in events
            ):
                break
            time.sleep(0.01)
        assert any(event.condition is WakeCondition.HEARTBEAT_STALE for event in events)
        os.killpg(driver.pid, signal.SIGKILL)
        driver.join(5)
        assert not driver.is_alive()
        assert monitor.is_alive()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            events = lab.store.reads.list_wake_events(root.root_id)
            if any(event.condition is WakeCondition.DRIVER_EXIT for event in events):
                break
            time.sleep(0.01)
        assert any(event.condition is WakeCondition.DRIVER_EXIT for event in events)
        assert monitor.is_alive()
    finally:
        monitor_stop.set()
        for process in (driver, monitor):
            process.join(5)
            if process.is_alive():
                process.kill()
                process.join(5)
    assert monitor.exitcode == 0


def test_hook_gets_bounded_json_without_shell_expansion(tmp_path):
    """Refusal text and shell metacharacters are data, never executable syntax."""
    lab = ForemanLab(tmp_path)
    event = event_for(lab.instantiate())
    output = tmp_path / "received.json"
    forbidden = tmp_path / "forbidden"
    literal = f"$(touch {forbidden})"
    config = WakeConfig(
        hook_argv=(
            sys.executable,
            "-c",
            "import json,sys; from pathlib import Path; data=sys.stdin.read(); Path(sys.argv[1]).write_text(json.dumps([data,sys.argv[2]]))",
            str(output),
            literal,
        )
    )
    run_hook(event, config, lab.composition.host_env)
    raw, received_literal = json.loads(output.read_text())
    assert len(raw.encode()) <= 8192
    assert json.loads(raw)["fire_key"] == event.fire_key
    assert received_literal == literal
    assert not forbidden.exists()


def test_hook_timeout_is_bounded_even_with_unlimited_output(tmp_path):
    """A flooding or hanging hook cannot block the monitor indefinitely."""
    lab = ForemanLab(tmp_path)
    event = event_for(lab.instantiate())
    config = WakeConfig(
        hook_timeout_s=0.1,
        hook_argv=(
            sys.executable,
            "-c",
            "import os;\nwhile True: os.write(1, b'x'*65536)",
        ),
    )
    start = time.monotonic()
    with pytest.raises(HookError, match="timed out"):
        run_hook(event, config, lab.composition.host_env)
    assert time.monotonic() - start < 3


def test_hook_nonzero_exit_is_reported(tmp_path):
    """A durable event is distinct from a failed external delivery attempt."""
    lab = ForemanLab(tmp_path)
    event = event_for(lab.instantiate())
    config = WakeConfig(hook_argv=(sys.executable, "-c", "raise SystemExit(9)"))
    with pytest.raises(HookError, match="exited 9"):
        run_hook(event, config, lab.composition.host_env)
