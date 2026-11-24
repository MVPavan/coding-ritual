"""Spec criterion Lock, manual half: two manual runs wait or report busy.

The background half (the worker, the supervisor's death) is M3.1's.
"""

from __future__ import annotations

import fcntl
import json
import os
import time

import pytest

from tests.mirror._harness import Mirror

pytestmark = pytest.mark.bd


def wait_until_locked(m: Mirror, timeout: float = 20.0) -> None:
    """Return once some process holds the clone-wide lock."""
    lock = m.mirror_dir / "lock"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if lock.exists():
            fd = os.open(lock, os.O_RDWR)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(fd, fcntl.LOCK_UN)
            except BlockingIOError:
                return
            finally:
                os.close(fd)
        time.sleep(0.02)
    raise AssertionError("the first run never took the lock")


def test_lock_second_manual_run_reports_busy_or_waits(mirror: Mirror) -> None:
    mirror.write_switch()
    # Each gh call takes a second, so the first run holds the lock for a while.
    mirror.fake.set_fault("delay", 1.0)
    first = mirror.run("outbound", background=True)
    wait_until_locked(mirror)

    busy = mirror.run("--lock-wait", "0.2", "outbound")
    assert busy.returncode == 7 and "busy" in busy.stderr
    assert "state.json" not in mirror.mirror_files()

    waiter = mirror.run("--lock-wait", "30", "outbound", background=True)
    assert first.poll() is None, (
        "the first run still holds the lock as the second starts"
    )
    assert first.wait(timeout=30) == 0
    assert waiter.wait(timeout=30) == 0

    by_pid = [c["caller_pid"] for c in mirror.fake.calls()]
    assert set(by_pid) == {first.pid, waiter.pid}, "the busy run must make no gh call"
    assert by_pid == sorted(by_pid, key=lambda pid: pid != first.pid), (
        "the waiting run called GitHub only after the first run released the lock"
    )
    state = json.loads((mirror.mirror_dir / "state.json").read_text())
    assert state["binding"]["store_project_id"] == mirror.project_id


def test_lock_held_elsewhere_blocks_state_changes_not_the_dry_run(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    assert mirror.run("outbound").returncode == 0
    fd = os.open(mirror.mirror_dir / "lock", os.O_RDWR)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        reset = mirror.run("--lock-wait", "0.2", "reset-state")
        assert reset.returncode == 7 and "busy" in reset.stderr
        assert (mirror.mirror_dir / "state.json").exists()
        assert mirror.run("--lock-wait", "0.2", "outbound").returncode == 7
        assert mirror.run("--lock-wait", "0.2", "outbound", "--dry-run").returncode == 0
    finally:
        os.close(fd)
    assert mirror.run("--lock-wait", "0.2", "reset-state").returncode == 0
