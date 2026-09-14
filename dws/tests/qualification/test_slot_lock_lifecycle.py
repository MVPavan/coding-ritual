"""Linux filesystem slot-lock qualification with real independent processes."""

from __future__ import annotations

import os
import selectors
import shutil
import signal
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

BUSY_EXIT = 75
LOCK_TARGET_ENVIRONMENT = "DWS_LOCK_QUALIFICATION_DIR"
PROBE_PATH = Path(__file__).with_name("lock_probe.py")
PROCESS_TIMEOUT_SECONDS = 5.0
POLL_INTERVAL_SECONDS = 0.02


@pytest.fixture
def lock_directory(tmp_path: Path) -> Iterator[Path]:
    """Create one isolated lock directory on pytest's target filesystem or requested volume."""
    configured_target = os.environ.get(LOCK_TARGET_ENVIRONMENT)
    if configured_target is None:
        yield tmp_path
        return

    target = Path(configured_target) / f"pytest-slot-lock-{uuid.uuid4().hex}"
    target.mkdir(parents=True)
    try:
        yield target
    finally:
        shutil.rmtree(target)


@pytest.fixture(autouse=True)
def require_linux_flock() -> None:
    """Fail loudly rather than skipping when this Linux-only qualification cannot run."""
    if sys.platform != "linux":
        pytest.fail("filesystem slot-lock qualification requires Linux fcntl.flock semantics")


def probe(*arguments: str) -> list[str]:
    """Build a private probe command executed with the test interpreter."""
    return [sys.executable, str(PROBE_PATH), *arguments]


def start_holder(*lock_paths: Path) -> subprocess.Popen[str]:
    """Start an independent process that holds all supplied slots."""
    process = subprocess.Popen(
        probe("hold", *(value for path in lock_paths for value in ("--lock-path", str(path)))),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert read_line(process) == "READY"
    return process


def contend(lock_directory: Path, slot_count: int) -> subprocess.CompletedProcess[str]:
    """Ask an independent process whether any slot can be acquired immediately."""
    return subprocess.run(
        probe("contend", "--lock-dir", str(lock_directory), "--slot-count", str(slot_count)),
        capture_output=True,
        text=True,
        timeout=PROCESS_TIMEOUT_SECONDS,
        check=False,
    )


def inspect_filesystem(lock_directory: Path) -> subprocess.CompletedProcess[str]:
    """Ask the probe to report the mount that contains the lock directory."""
    return subprocess.run(
        probe("filesystem", "--target-dir", str(lock_directory)),
        capture_output=True,
        text=True,
        timeout=PROCESS_TIMEOUT_SECONDS,
        check=False,
    )


def read_line(process: subprocess.Popen[str]) -> str:
    """Read one readiness line with a bounded selector wait."""
    assert process.stdout is not None
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        events = selector.select(PROCESS_TIMEOUT_SECONDS)
    assert events, f"no readiness output from probe PID {process.pid}"
    line = process.stdout.readline().strip()
    assert line, f"empty readiness output from probe PID {process.pid}"
    return line


def stop_owned_process(process: subprocess.Popen[str]) -> None:
    """Terminate one process created by this test, without touching process groups."""
    if process.poll() is None:
        process.terminate()
    process.wait(timeout=PROCESS_TIMEOUT_SECONDS)


def stop_owned_child(child_pid: int) -> None:
    """Terminate the exact child PID announced by the probe, if it still exists."""
    try:
        os.kill(child_pid, signal.SIGTERM)
    except ProcessLookupError:
        return


def wait_for_owned_child_exit(child_pid: int) -> None:
    """Confirm a signalled probe child exited before test cleanup completes."""
    deadline = time.monotonic() + PROCESS_TIMEOUT_SECONDS
    while True:
        try:
            os.kill(child_pid, 0)
        except ProcessLookupError:
            return
        if time.monotonic() >= deadline:
            pytest.fail(f"probe child PID {child_pid} did not exit before the deadline")
        time.sleep(POLL_INTERVAL_SECONDS)


def wait_for_available_slot(lock_directory: Path) -> subprocess.CompletedProcess[str]:
    """Wait only briefly for a terminated child to release its inherited descriptor."""
    deadline = time.monotonic() + PROCESS_TIMEOUT_SECONDS
    while True:
        contender = contend(lock_directory, 1)
        if contender.returncode == 0:
            return contender
        if time.monotonic() >= deadline:
            pytest.fail("child exit did not release the filesystem slot before the deadline")
        time.sleep(POLL_INTERVAL_SECONDS)


def test_parent_crash_does_not_release_a_lock_held_by_surviving_child(
    lock_directory: Path,
) -> None:
    """A safe supervisor must transfer lock ownership into its child before a crash."""
    supervisor = subprocess.Popen(
        probe("supervise", "--lock-path", str(lock_directory / "slot-0.lock")),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    child_pid: int | None = None
    try:
        ready = read_line(supervisor).split()
        assert ready[0] == "READY"
        child_pid = int(ready[1])
        assert contend(lock_directory, 1).returncode == BUSY_EXIT

        supervisor.kill()
        supervisor.wait(timeout=PROCESS_TIMEOUT_SECONDS)
        os.kill(child_pid, 0)

        competing = contend(lock_directory, 1)
        assert competing.returncode == BUSY_EXIT

        stop_owned_child(child_pid)
        wait_for_owned_child_exit(child_pid)
        child_pid = None
        released = wait_for_available_slot(lock_directory)
        assert released.stdout == "ACQUIRED\n"
    finally:
        if supervisor.poll() is None:
            stop_owned_process(supervisor)
        if child_pid is not None:
            stop_owned_child(child_pid)
            wait_for_owned_child_exit(child_pid)
            wait_for_owned_child_exit(child_pid)


def test_target_filesystem_is_observed_and_emitted(lock_directory: Path) -> None:
    """The qualification output identifies the filesystem that supplied its lock semantics."""
    result = inspect_filesystem(lock_directory)

    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("TARGET=")
    assert " FILESYSTEM=" in result.stdout
    assert " MOUNT=" in result.stdout
    print(result.stdout, end="")


def test_parent_only_lock_ownership_releases_early_while_the_child_survives(
    lock_directory: Path,
) -> None:
    """Negative control: a parent-only descriptor is unsafe for child work ownership."""
    supervisor = subprocess.Popen(
        probe(
            "supervise",
            "--lock-path",
            str(lock_directory / "slot-0.lock"),
            "--ownership",
            "parent-only",
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    child_pid: int | None = None
    try:
        ready = read_line(supervisor).split()
        assert ready[0] == "READY"
        child_pid = int(ready[1])
        assert contend(lock_directory, 1).returncode == BUSY_EXIT

        supervisor.kill()
        supervisor.wait(timeout=PROCESS_TIMEOUT_SECONDS)
        os.kill(child_pid, 0)

        competing = contend(lock_directory, 1)
        assert competing.returncode == 0
        assert competing.stdout == "ACQUIRED\n"
    finally:
        if supervisor.poll() is None:
            stop_owned_process(supervisor)
        if child_pid is not None:
            stop_owned_child(child_pid)


def test_one_slot_excludes_an_independent_contender(lock_directory: Path) -> None:
    """The same slot cannot be acquired twice by independent probe processes."""
    holder = start_holder(lock_directory / "slot-0.lock")
    try:
        contender = contend(lock_directory, 1)
        assert contender.returncode == BUSY_EXIT
        assert contender.stdout == "BUSY\n"
    finally:
        stop_owned_process(holder)


def test_full_slot_set_denies_a_third_independent_contender(lock_directory: Path) -> None:
    """Two occupied capacity slots deny a third process instead of multiplying capacity."""
    first = start_holder(lock_directory / "slot-0.lock")
    second = start_holder(lock_directory / "slot-1.lock")
    try:
        contender = contend(lock_directory, 2)
        assert contender.returncode == BUSY_EXIT
        assert contender.stdout == "BUSY\n"
    finally:
        stop_owned_process(first)
        stop_owned_process(second)


def test_releasing_a_slot_permits_reuse_by_an_independent_process(lock_directory: Path) -> None:
    """A slot becomes available only after its holder exits and closes the descriptor."""
    holder = start_holder(lock_directory / "slot-0.lock")
    try:
        assert contend(lock_directory, 1).returncode == BUSY_EXIT
    finally:
        stop_owned_process(holder)

    contender = contend(lock_directory, 1)
    assert contender.returncode == 0
    assert contender.stdout == "ACQUIRED\n"
