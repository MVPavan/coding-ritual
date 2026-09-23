"""Test-only PID-1 observer: public QMD launcher with a flocked stdin carrier."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import select
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

BASE = Path("/state")
NODE = "/usr/local/bin/node"
LAUNCHER = "/opt/qmd/node_modules/.bin/qmd"
WORKER = "/opt/qmd/node_modules/@tobilu/qmd/dist/cli/qmd.js"
GET = ["get", "qmd://fixture/fixture.md"]


def emit(**values: Any) -> None:
    print(json.dumps(values), flush=True)


def read_chunk(fd: int, deadline: float) -> bytes:
    assert select.select([fd], [], [], max(0, deadline - time.monotonic()))[0], "read timeout"
    return os.read(fd, 65536)


def control(expected: str) -> None:
    data = b""
    deadline = time.monotonic() + 60
    while not data.endswith(b"\n"):
        assert len(data) < 100, "oversized control message"
        chunk = read_chunk(0, deadline)
        assert chunk, "observer control EOF"
        data += chunk
    assert data == (expected + "\n").encode(), data
    assert not (fcntl.fcntl(0, fcntl.F_GETFL) & os.O_NONBLOCK)


def identity(pid: int) -> dict[str, Any]:
    root = Path(f"/proc/{pid}")
    fields = (root / "stat").read_text().rsplit(")", 1)[1].split()
    assert fields[0] not in ("Z", "X"), (pid, fields[0])
    fds: dict[str, Any] = {}
    for path in (root / "fd").iterdir():
        try:
            stat = path.stat()
            fds[path.name] = dict(
                target=os.readlink(path),
                inode=stat.st_ino,
                device=stat.st_dev,
                info=(root / "fdinfo" / path.name).read_text(),
            )
        except FileNotFoundError:
            continue
    return dict(
        pid=pid,
        state=fields[0],
        ppid=int(fields[1]),
        starttime=fields[19],
        exe=os.readlink(root / "exe"),
        cmdline=(root / "cmdline").read_bytes().decode().rstrip("\0").split("\0"),
        fds=fds,
    )


def same_process(before: dict[str, Any], ppid: int) -> dict[str, Any]:
    after = identity(before["pid"])
    for key in ("pid", "starttime", "exe", "cmdline"):
        assert after[key] == before[key], (key, before, after)
    assert after["ppid"] == ppid, after
    return after


def reap(pid: int, expected: int) -> dict[str, int]:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        found, status = os.waitpid(pid, os.WNOHANG)
        if found:
            assert os.waitstatus_to_exitcode(status) == expected, (pid, status)
            assert not Path(f"/proc/{pid}").exists()
            return dict(pid=pid, exitcode=expected)
        time.sleep(0.01)
    raise AssertionError(f"reap timeout: {pid}")


def assert_stdin(process: dict[str, Any], lock: Path, safe: bool) -> None:
    fd = process["fds"]["0"]
    if safe:
        stat = lock.stat()
        assert (fd["target"], fd["inode"], fd["device"]) == (
            str(lock),
            stat.st_ino,
            stat.st_dev,
        )
        assert "FLOCK  ADVISORY  WRITE" in fd["info"], fd
    else:
        assert fd["target"] == "/dev/null", fd
        assert all(value["target"] != str(lock) for value in process["fds"].values())


def contender(mode: str) -> None:
    root = BASE / mode
    fd = os.open(root / "slot.lock", os.O_RDWR)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            outcome = "BUSY"
        else:
            outcome = "ACQUIRED"
        counter = root / "counter"
        count = int(counter.read_text()) if counter.exists() else 0
        if outcome == "ACQUIRED":
            count += 1
            counter.write_text(str(count))
        emit(
            outcome=outcome,
            counter=count,
            inode=os.fstat(fd).st_ino,
            device=os.fstat(fd).st_dev,
        )
    finally:
        os.close(fd)


def observe(mode: str) -> None:
    safe = mode == "stdin-carrier"
    assert safe or mode == "parent-only"
    assert os.getpid() == 1 and os.getuid() == os.getgid() == 1000
    status = Path("/proc/self/status").read_text()
    assert "CapEff:\t0000000000000000" in status and "NoNewPrivs:\t1" in status
    assert sorted(p.name for p in Path("/sys/class/net").iterdir()) == ["lo"]
    assert not (fcntl.fcntl(0, fcntl.F_GETFL) & os.O_NONBLOCK)
    root = BASE / mode
    root.mkdir()
    for name in ("home", "cache", "config", "corpus"):
        (root / name).mkdir()
    os.environ.update(
        HOME=str(root / "home"),
        XDG_CACHE_HOME=str(root / "cache"),
        QMD_CONFIG_DIR=str(root / "config"),
        INDEX_PATH=str(root / "index.sqlite"),
    )
    assert not list((root / "cache").rglob("*"))
    content = "# Lifetime fixture\n\nqmdchildneedle\n" + "synthetic corpus line\n" * 100000
    (root / "corpus" / "fixture.md").write_text(content)
    lock = root / "slot.lock"
    setup: list[dict[str, Any]] = []
    # Also smoke the existing noninteractive allowlist using the public launcher and carrier.
    with lock.open("w+") as carrier:
        fcntl.flock(carrier, fcntl.LOCK_EX)
        for args in (
            ["collection", "add", str(root / "corpus"), "--name", "fixture"],
            ["update"],
            ["status"],
            ["search", "qmdchildneedle", "--json"],
        ):
            result = subprocess.run(
                ["qmd", *args],
                stdin=carrier,
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )
            setup.append(dict(argv=["qmd", *args], stdout=result.stdout, stderr=result.stderr))
    search = json.loads(setup[-1]["stdout"])
    assert search and search[0]["file"] == GET[1]
    runtime = subprocess.run(
        [
            "node",
            "-e",
            """
const D=require('/opt/qmd/node_modules/better-sqlite3');const d=new D(':memory:');
console.log(JSON.stringify({node:process.version,
qmd:require('/opt/qmd/node_modules/@tobilu/qmd/package.json').version,
sqlite:d.prepare('select sqlite_version() v').get().v}));d.close();
""",
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    read_fd, write_fd = os.pipe()
    pid_read, pid_write = os.pipe()
    parent = os.fork()
    if parent == 0:
        os.close(0)  # Never share the observer's control open-file description with QMD.
        os.close(read_fd)
        os.close(pid_read)
        fd = os.open(lock, os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX)
        child = subprocess.Popen(
            ["qmd", *GET],
            stdin=fd if safe else subprocess.DEVNULL,
            stdout=write_fd,
            stderr=sys.stderr,
        )
        os.write(pid_write, str(child.pid).encode())
        os.close(pid_write)
        while True:
            signal.pause()
    os.close(write_fd)
    os.close(pid_write)
    launcher_pid = int(read_chunk(pid_read, time.monotonic() + 60))
    os.close(pid_read)
    prefix = b""
    deadline = time.monotonic() + 60
    while b"qmdchildneedle" not in prefix:
        assert len(prefix) < 131072
        chunk = read_chunk(read_fd, deadline)
        assert chunk, "QMD exited before fixture output"
        prefix += chunk
    children = Path(f"/proc/{launcher_pid}/task/{launcher_pid}/children").read_text().split()
    assert len(children) == 1, children  # No fallback to launcher identity.
    worker_pid = int(children[0])
    controller = identity(parent)
    assert controller["ppid"] == 1
    assert controller["exe"] == "/usr/local/bin/python3.13"
    assert controller["cmdline"] == ["python", "/probe.py", "observe", mode]
    launcher = identity(launcher_pid)
    worker = identity(worker_pid)
    assert launcher["exe"] == worker["exe"] == NODE
    assert launcher["cmdline"] == ["node", LAUNCHER, *GET]
    assert worker["cmdline"] == [NODE, WORKER, *GET]
    assert launcher["ppid"] == parent and worker["ppid"] == launcher_pid
    os.kill(worker_pid, signal.SIGSTOP)
    deadline = time.monotonic() + 5
    while True:
        worker = same_process(worker, launcher_pid)
        if worker["state"] == "T":
            break
        assert time.monotonic() < deadline, "stop timeout"
        time.sleep(0.01)

    def snapshot(worker_ppid: int, launcher_alive: bool) -> dict[str, Any]:
        current = same_process(worker, worker_ppid)
        assert current["state"] == "T"
        assert_stdin(current, lock, safe)
        values = dict(worker=current, observer=identity(1))
        if launcher_alive:
            current_launcher = same_process(
                launcher,
                parent
                if worker_ppid == launcher_pid and Path(f"/proc/{parent}").exists()
                else 1,
            )
            assert_stdin(current_launcher, lock, safe)
            values["launcher"] = current_launcher
        assert not (fcntl.fcntl(0, fcntl.F_GETFL) & os.O_NONBLOCK)
        return values

    emit(
        event="ready",
        mode=mode,
        controller=controller,
        **snapshot(launcher_pid, True),
        runtime=json.loads(runtime.stdout),
        setup=setup,
        prefix=prefix.decode(),
        fixture_bytes=len(content),
        pipe_size=fcntl.fcntl(read_fd, fcntl.F_GETPIPE_SZ),
        lock_inode=lock.stat().st_ino,
        lock_device=lock.stat().st_dev,
        cache_empty_before=True,
        mountinfo=Path("/proc/self/mountinfo").read_text(),
    )
    control("kill-parent")
    same_process(controller, 1)
    os.kill(parent, signal.SIGKILL)
    parent_reaped = reap(parent, -signal.SIGKILL)
    emit(event="parent-dead", reaped=parent_reaped, **snapshot(launcher_pid, True))
    control("kill-launcher")
    same_process(launcher, 1)
    os.kill(launcher_pid, signal.SIGKILL)
    launcher_reaped = reap(launcher_pid, -signal.SIGKILL)
    emit(event="launcher-dead", reaped=launcher_reaped, **snapshot(1, False))
    control("finish")
    same_process(worker, 1)
    os.kill(worker_pid, signal.SIGCONT)
    output = bytearray(prefix)
    deadline = time.monotonic() + 60
    while True:
        chunk = read_chunk(read_fd, deadline)
        if not chunk:
            break
        output.extend(chunk)
        assert len(output) < 8 * 1024 * 1024, "unexpected output size"
    os.close(read_fd)
    worker_reaped = reap(worker_pid, 0)
    lines = output.decode().splitlines()
    body_start = lines.index("1: # Lifetime fixture")
    assert lines[body_start:] == [
        f"{i}: {line}" for i, line in enumerate(content.split("\n"), 1)
    ]
    try:
        unexpected = os.waitpid(-1, os.WNOHANG)
    except ChildProcessError:
        pass
    else:
        raise AssertionError(f"unexpected remaining child: {unexpected}")
    assert not list((root / "cache").rglob("*"))
    assert not list((root / "home").rglob("*"))
    emit(
        event="finished",
        bytes=len(output),
        exact_numbered_body=True,
        output_sha256=hashlib.sha256(output).hexdigest(),
        body_lines=len(lines) - body_start,
        reaped=worker_reaped,
        all_children_reaped=True,
        cache_empty=True,
        models_absent=True,
        control_flags=fcntl.fcntl(0, fcntl.F_GETFL),
    )


if __name__ == "__main__":
    if sys.argv[1] == "contend":
        contender(sys.argv[2])
    else:
        observe(sys.argv[2])
