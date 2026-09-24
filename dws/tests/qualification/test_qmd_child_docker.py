"""Opt-in Docker E2E proof of public-QMD stdin-carried slot ownership."""

from __future__ import annotations

import hashlib
import json
import os
import select
import subprocess
import time
import traceback
import uuid
from pathlib import Path
from typing import Any

import pytest

IMAGE = "sha256:eb1475855045015fd0aa47e32605dcb5dcb68275d04f70be2386c9322694b616"
PROBE = Path(__file__).with_name("qmd_child_probe.py").resolve()
EVIDENCE = Path("scratchpad/dws/qmd-child-qualification/stdin-carrier")


def receive(
    process: subprocess.Popen[bytes],
    expected: str,
    events: list[dict[str, Any]],
    stderr_path: Path,
) -> dict[str, Any]:
    assert process.stdout is not None
    data = b""
    deadline = time.monotonic() + 90
    while not data.endswith(b"\n"):
        assert len(data) < 1024 * 1024, "oversized observer message"
        assert select.select([process.stdout], [], [], max(0, deadline - time.monotonic()))[
            0
        ], f"observer timeout: {expected}; {stderr_path.read_text()}"
        chunk = os.read(process.stdout.fileno(), 65536)
        assert chunk, f"observer EOF: {expected}; {stderr_path.read_text()}"
        data += chunk
    value: dict[str, Any] = json.loads(data)
    events.append(value)
    assert value["event"] == expected
    return value


def send(process: subprocess.Popen[bytes], value: str) -> None:
    assert process.stdin is not None
    assert select.select([], [process.stdin], [], 5)[1], "control write timeout"
    data = (value + "\n").encode()
    assert os.write(process.stdin.fileno(), data) == len(data)


def test_actual_qmd_child_lifetime() -> None:
    if os.environ.get("DWS_QMD_CHILD_DOCKER") != "1":
        pytest.skip("explicit DWS_QMD_CHILD_DOCKER=1 required")
    token = "dws-qmd-stdin-" + uuid.uuid4().hex[:12]
    run_dir = EVIDENCE / token
    run_dir.mkdir(parents=True)
    # Immutable source snapshots are the actual files mounted into this run.
    snapshot = run_dir / PROBE.name
    snapshot.write_bytes(PROBE.read_bytes())
    (run_dir / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    volume = token + "-state"
    evidence: dict[str, Any] = dict(
        image=IMAGE,
        volume=volume,
        cases={},
        commands=[],
        cleanup=[],
        cleanup_failures=[],
        result="not-qualified",
    )
    containers: list[str] = []
    processes: list[subprocess.Popen[bytes]] = []
    primary: BaseException | None = None
    volume_created = False

    def command(args: list[str]) -> subprocess.CompletedProcess[str]:
        entry: dict[str, Any] = dict(argv=args)
        evidence["commands"].append(entry)
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=90)
        except BaseException as exc:
            entry["error"] = repr(exc)
            raise
        entry.update(rc=result.returncode, stdout=result.stdout, stderr=result.stderr)
        assert result.returncode == 0, entry
        return result

    def flags(name: str) -> list[str]:
        return [
            "docker",
            "run",
            "--name",
            name,
            "--network",
            "none",
            "--read-only",
            "--user",
            "1000:1000",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--cpus",
            "1",
            "--memory",
            "1g",
            "--memory-swap",
            "1g",
            "--pids-limit",
            "128",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "-v",
            f"{volume}:/state",
            "-v",
            f"{snapshot.resolve()}:/probe.py:ro",
        ]

    def compete(
        mode: str, ready: dict[str, Any], case: dict[str, Any], expected: str, count: int
    ) -> None:
        name = token + "-competitor-" + uuid.uuid4().hex[:6]
        containers.append(name)
        result = command(flags(name) + [IMAGE, "python", "/probe.py", "contend", mode])
        value = json.loads(result.stdout)
        case["contenders"].append(value)
        assert value == dict(
            outcome=expected,
            counter=count,
            inode=ready["lock_inode"],
            device=ready["lock_device"],
        ), value

    try:
        inspected = json.loads(command(["docker", "image", "inspect", IMAGE]).stdout)
        assert inspected[0]["Id"] == IMAGE
        evidence["image_inspect"] = inspected
        command(["docker", "volume", "create", volume])
        volume_created = True
        evidence["volume_inspect"] = json.loads(
            command(["docker", "volume", "inspect", volume]).stdout
        )
        for mode in ("stdin-carrier", "parent-only"):
            name = token + "-" + mode
            containers.append(name)
            args = flags(name) + ["-i", IMAGE, "python", "/probe.py", "observe", mode]
            evidence["commands"].append(dict(argv=args, interactive=True))
            stderr_path = run_dir / (mode + ".stderr")
            with stderr_path.open("wb") as stderr:
                process = subprocess.Popen(
                    args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=stderr,
                    bufsize=0,
                )
            processes.append(process)
            case: dict[str, Any] = dict(events=[], contenders=[])
            evidence["cases"][mode] = case
            ready = receive(process, "ready", case["events"], stderr_path)
            assert ready["runtime"] == dict(node="v22.22.0", qmd="2.8.3", sqlite="3.53.4")
            compete(mode, ready, case, "BUSY", 0)
            send(process, "kill-parent")
            dead = receive(process, "parent-dead", case["events"], stderr_path)
            for key in ("pid", "starttime", "exe", "cmdline"):
                assert dead["worker"][key] == ready["worker"][key]
            assert dead["worker"]["state"] == "T"
            compete(
                mode,
                ready,
                case,
                "BUSY" if mode == "stdin-carrier" else "ACQUIRED",
                0 if mode == "stdin-carrier" else 1,
            )
            send(process, "kill-launcher")
            dead = receive(process, "launcher-dead", case["events"], stderr_path)
            for key in ("pid", "starttime", "exe", "cmdline"):
                assert dead["worker"][key] == ready["worker"][key]
            assert dead["worker"]["state"] == "T" and dead["worker"]["ppid"] == 1
            compete(
                mode,
                ready,
                case,
                "BUSY" if mode == "stdin-carrier" else "ACQUIRED",
                0 if mode == "stdin-carrier" else 2,
            )
            send(process, "finish")
            finished = receive(process, "finished", case["events"], stderr_path)
            assert finished["all_children_reaped"] and finished["cache_empty"]
            assert finished["models_absent"] and finished["exact_numbered_body"]
            assert finished["reaped"] == dict(pid=ready["worker"]["pid"], exitcode=0)
            assert process.wait(timeout=10) == 0, stderr_path.read_text()
            compete(mode, ready, case, "ACQUIRED", 1 if mode == "stdin-carrier" else 3)
        evidence["mechanism_assertions_passed"] = True
    except BaseException as exc:
        primary = exc
        evidence["primary_failure"] = traceback.format_exc()
    finally:
        # Every cleanup step is attempted, even after a diagnostic/cleanup failure.
        for name in containers:
            try:
                command(["docker", "rm", "-f", name])
                evidence["cleanup"].append(dict(container=name, removed=True))
            except BaseException as exc:
                evidence["cleanup_failures"].append(dict(container=name, error=repr(exc)))
        for process in processes:
            try:
                process.wait(timeout=10)
            except BaseException as exc:
                evidence["cleanup_failures"].append(
                    dict(client_pid=process.pid, error=repr(exc))
                )
            for pipe in (process.stdin, process.stdout):
                if pipe is not None:
                    try:
                        pipe.close()
                    except BaseException as exc:
                        evidence["cleanup_failures"].append(dict(pipe_close=repr(exc)))
        if volume_created:
            try:
                command(["docker", "volume", "rm", volume])
                evidence["cleanup"].append(dict(volume=volume, removed=True))
            except BaseException as exc:
                evidence["cleanup_failures"].append(dict(volume=volume, error=repr(exc)))
        for kind, args in (
            (
                "containers",
                ["docker", "ps", "-a", "--filter", f"name={token}", "--format", "{{.Names}}"],
            ),
            (
                "volumes",
                [
                    "docker",
                    "volume",
                    "ls",
                    "--filter",
                    f"name={volume}",
                    "--format",
                    "{{.Name}}",
                ],
            ),
        ):
            try:
                inventory = command(args).stdout
                evidence["remaining_" + kind] = inventory
                assert not inventory, inventory
            except BaseException as exc:
                evidence["cleanup_failures"].append(dict(inventory=kind, error=repr(exc)))
        if primary is None and not evidence["cleanup_failures"]:
            assert evidence["mechanism_assertions_passed"]
            evidence["result"] = "stdin-carrier-lifetime-qualified"
        evidence["completed_at_unix"] = time.time()
        evidence["sources"] = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in run_dir.glob("*.py")
        }
        (run_dir / "result.json").write_text(json.dumps(evidence, indent=2) + "\n")
        print(f"EVIDENCE={run_dir}/result.json")
    if primary is not None:
        raise primary
    assert not evidence["cleanup_failures"], evidence["cleanup_failures"]
    assert evidence["result"] == "stdin-carrier-lifetime-qualified"
