"""Small subprocess roles used only by the filesystem-lock qualification tests.

The probe is intentionally separate from ``dws`` runtime code: it characterizes
the Linux filesystem primitive that a future runtime may choose to use.
"""

from __future__ import annotations

import argparse
import fcntl
import os
import select
import signal
import subprocess
import sys
import threading
from pathlib import Path

BUSY_EXIT = 75
CHILD_READY = "CHILD_READY"
DEFAULT_LIFETIME_SECONDS = 15.0
READY_PREFIX = "READY"


def lock_file(path: Path) -> int:
    """Open and exclusively lock a slot file, returning its file descriptor."""
    file_descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    fcntl.flock(file_descriptor, fcntl.LOCK_EX)
    return file_descriptor


def try_lock_file(path: Path) -> int | None:
    """Try to lock a slot file without waiting, or return ``None`` when busy."""
    file_descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(file_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(file_descriptor)
        return None
    return file_descriptor


def write_line(line: str) -> None:
    """Publish one readiness or result line to the supervising test process."""
    sys.stdout.write(f"{line}\n")
    sys.stdout.flush()


def wait_for_release(maximum_seconds: float) -> None:
    """Keep a probe role alive until termination or its bounded lifetime expires."""
    stop = threading.Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    stop.wait(maximum_seconds)


def hold(arguments: argparse.Namespace) -> int:
    """Hold the requested slot files until input closes or a bounded timeout expires."""
    file_descriptors = [lock_file(Path(path)) for path in arguments.lock_path]
    try:
        write_line(READY_PREFIX)
        wait_for_release(arguments.maximum_seconds)
    finally:
        for file_descriptor in file_descriptors:
            os.close(file_descriptor)
    return 0


def contend(arguments: argparse.Namespace) -> int:
    """Acquire one available slot without waiting, or report a full slot set."""
    for slot_number in range(arguments.slot_count):
        file_descriptor = try_lock_file(Path(arguments.lock_dir) / f"slot-{slot_number}.lock")
        if file_descriptor is not None:
            try:
                write_line("ACQUIRED")
            finally:
                os.close(file_descriptor)
            return 0
    write_line("BUSY")
    return BUSY_EXIT


def child(arguments: argparse.Namespace) -> int:
    """Represent the long-running child process whose lock ownership is qualified."""
    if arguments.inherited_fd is not None:
        os.fstat(arguments.inherited_fd)
    write_line(CHILD_READY)
    wait_for_release(arguments.maximum_seconds)
    return 0


def supervise(arguments: argparse.Namespace) -> int:
    """Lock one slot, start a child, and expose their ready state to the test."""
    lock_path = Path(arguments.lock_path)
    file_descriptor = lock_file(lock_path)
    command = [
        sys.executable,
        __file__,
        "child",
        "--maximum-seconds",
        str(arguments.maximum_seconds),
    ]
    pass_file_descriptors: tuple[int, ...] = ()
    if arguments.ownership == "inherited":
        command.extend(("--inherited-fd", str(file_descriptor)))
        pass_file_descriptors = (file_descriptor,)
    child_process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        text=True,
        pass_fds=pass_file_descriptors,
    )
    try:
        assert child_process.stdout is not None
        readable, _, _ = select.select([child_process.stdout], [], [], arguments.ready_timeout)
        if not readable or child_process.stdout.readline().strip() != CHILD_READY:
            child_process.terminate()
            child_process.wait(timeout=arguments.ready_timeout)
            return 1
        write_line(f"{READY_PREFIX} {child_process.pid}")
        wait_for_release(arguments.maximum_seconds)
    finally:
        os.close(file_descriptor)
        if child_process.poll() is None:
            child_process.terminate()
            child_process.wait(timeout=arguments.ready_timeout)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the private command interface used by qualification tests."""
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="role", required=True)

    hold_parser = subcommands.add_parser("hold")
    hold_parser.add_argument("--lock-path", action="append", required=True)
    hold_parser.add_argument("--maximum-seconds", type=float, default=DEFAULT_LIFETIME_SECONDS)
    hold_parser.set_defaults(handler=hold)

    contend_parser = subcommands.add_parser("contend")
    contend_parser.add_argument("--lock-dir", required=True)
    contend_parser.add_argument("--slot-count", type=int, required=True)
    contend_parser.set_defaults(handler=contend)

    child_parser = subcommands.add_parser("child")
    child_parser.add_argument("--inherited-fd", type=int)
    child_parser.add_argument("--maximum-seconds", type=float, default=DEFAULT_LIFETIME_SECONDS)
    child_parser.set_defaults(handler=child)

    supervisor_parser = subcommands.add_parser("supervise")
    supervisor_parser.add_argument("--lock-path", required=True)
    supervisor_parser.add_argument(
        "--maximum-seconds",
        type=float,
        default=DEFAULT_LIFETIME_SECONDS,
    )
    supervisor_parser.add_argument("--ready-timeout", type=float, default=3.0)
    supervisor_parser.add_argument(
        "--ownership",
        choices=("inherited", "parent-only"),
        default="inherited",
    )
    supervisor_parser.set_defaults(handler=supervise)
    return parser


def main() -> int:
    """Run a private probe role and return its process status."""
    arguments = build_parser().parse_args()
    return int(arguments.handler(arguments))


if __name__ == "__main__":
    raise SystemExit(main())
