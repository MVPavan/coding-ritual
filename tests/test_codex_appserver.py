"""Fixture-only qualification of the pinned Codex stdio protocol boundary."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import jsonschema
import pytest

from workflow_interpreter.profiles.codex_rpc import RpcClient, RpcFailure, RpcMethod

FIXTURE = Path(__file__).parent / "fixtures" / "codex_appserver" / "server.py"


def test_fragmented_handshake_and_stderr_are_separate():
    """Only correlated stdout protocol frames establish a successful handshake."""
    with subprocess.Popen(
        [sys.executable, str(FIXTURE), "fragmented"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        with RpcClient(
            os.dup(process.stdin.fileno()),
            os.dup(process.stdout.fileno()),
            os.dup(process.stderr.fileno()),
        ) as client:
            request = client.request(
                RpcMethod.INITIALIZE,
                {
                    "clientInfo": {"name": "workflow-interpreter", "version": "1"},
                },
            )
            frames = []
            deadline = time.monotonic() + 3
            while not frames and time.monotonic() < deadline:
                frames.extend(client.poll(0.01))
            jsonschema.validate(
                frames[0].result,
                json.loads((FIXTURE.parent / "InitializeResponse.json").read_text()),
            )
            assert frames[0].id == request
            assert frames[0].result["userAgent"] == "codex-cli/0.154.0"
            assert "not a protocol frame" in client.stderr_tail
        process.stdin.close()
        process.wait(timeout=3)


@pytest.mark.parametrize(
    "mode", ["oversize", "invalid", "unknown", "wrong-id", "duplicate", "partial-eof"]
)
def test_invalid_protocol_fails_loud(mode):
    """Malformed, uncorrelated, or unknown data never silently becomes telemetry."""
    with subprocess.Popen(
        [sys.executable, str(FIXTURE), mode],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        try:
            with RpcClient(
                os.dup(process.stdin.fileno()),
                os.dup(process.stdout.fileno()),
                os.dup(process.stderr.fileno()),
            ) as client:
                client.request(RpcMethod.INITIALIZE, {})
                with pytest.raises(RpcFailure):
                    deadline = time.monotonic() + 3
                    while time.monotonic() < deadline:
                        client.poll(0.01)
                    pytest.fail("protocol corruption was ignored")
        finally:
            process.kill()
            process.wait(timeout=3)


def test_hung_request_deadline_does_not_block_polling():
    """The wrapper can enforce runtime bounds between short RPC polls."""
    with subprocess.Popen(
        [sys.executable, str(FIXTURE), "hang"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        try:
            with RpcClient(
                os.dup(process.stdin.fileno()),
                os.dup(process.stdout.fileno()),
                os.dup(process.stderr.fileno()),
                timeout_s=0.05,
            ) as client:
                client.request(RpcMethod.INITIALIZE, {})
                with pytest.raises(RpcFailure, match="deadline"):
                    while True:
                        client.poll(0.01)
        finally:
            process.kill()
            process.wait(timeout=3)


def test_fork_barrier_owns_rpc_pipes_and_preserves_receipt(tmp_path):
    """RPC uses the existing launch barrier; stderr never reaches the event log."""
    from tests._inspector import entry_mint
    from tests.test_inspector_launch import Lab
    from workflow_interpreter.contracts.transport import CrewTransport
    from workflow_interpreter.inspector.launch import ForkBarrierLauncher
    from workflow_interpreter.inspector.profile import CrewCommand
    from workflow_interpreter.inspector.sandbox import SandboxMode, SandboxPlan

    lab = Lab(tmp_path)
    activation = lab.store.mint_activation(lab.root.root_id, entry_mint()).activation
    aid = activation.activation_id
    lab.paths.ensure_activation_dir(aid)
    launcher = ForkBarrierLauncher(
        lab.config,
        lab.paths,
        lab.clock,
        activation_id=aid,
        launch_id="rpc-test",
        plan=SandboxPlan(toolchain_cache=(tmp_path / "cache",)),
        sandbox=SandboxMode.OFF,
    )
    handle = launcher(
        CrewCommand(
            argv=(sys.executable, str(FIXTURE)),
            env={},
            cwd=str(lab.repo),
            log_path=str(lab.paths.log(aid)),
            session_id="",
            transport=CrewTransport.STDIO_RPC,
        )
    )
    try:
        pipes = launcher.take_rpc_pipes()
        assert pipes is not None
        with RpcClient(*pipes.detach()) as client:
            client.request(RpcMethod.INITIALIZE, {})
            frames = []
            deadline = time.monotonic() + 3
            while not frames and time.monotonic() < deadline:
                frames.extend(client.poll(0.01))
            assert frames[0].result["userAgent"] == "codex-cli/0.154.0"
        assert lab.wc_l(aid) == 1
        assert lab.paths.log(aid).read_bytes() == b""
    finally:
        os.waitpid(handle.pid, 0)


@pytest.mark.parametrize("mode", ["tool", "approval"])
def test_server_tool_and_permission_requests_are_denied(mode):
    """Server requests receive bounded errors and never reach a host executor."""
    with subprocess.Popen(
        [sys.executable, str(FIXTURE), mode],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        try:
            with RpcClient(
                os.dup(process.stdin.fileno()),
                os.dup(process.stdout.fileno()),
                os.dup(process.stderr.fileno()),
            ) as client:
                client.request(RpcMethod.INITIALIZE, {})
                frames = []
                deadline = time.monotonic() + 3
                while not frames and time.monotonic() < deadline:
                    frames.extend(client.poll(0.01))
                assert frames[0].result["denial"] == {
                    "id": "server-1",
                    "error": {
                        "code": -32601,
                        "message": "unsupported tool or permission request",
                    },
                }
        finally:
            process.stdin.close()
            process.wait(timeout=3)


def test_late_server_request_after_close_cannot_reuse_a_host_file_fd(tmp_path, capsys):
    """A shutdown denial must never target a descriptor reused by a host record."""
    request_read, request_write = os.pipe()
    output_read, output_write = os.pipe()
    error_read, error_write = os.pipe()
    client = RpcClient(request_write, output_read, error_read)
    target = None
    try:
        client.close_input()
        target = os.open(tmp_path / "protected.json", os.O_CREAT | os.O_RDWR, 0o600)
        assert target == request_write
        os.write(output_write, b'{"id":7,"method":"item/tool/call","params":{}}\n')
        client.poll(0.01)
        assert not client.output_pending
        assert os.fstat(target).st_size == 0
        captured = capsys.readouterr()
        assert "input_closed" in captured.out + captured.err
        client.close()
        os.fstat(target)
    finally:
        client.close()
        for descriptor in (request_read, output_write, error_write, target):
            if descriptor is not None:
                os.close(descriptor)


@pytest.mark.parametrize(
    "args",
    [
        ["app-server", "--unsupported"],
        ["--version", "--unsupported"],
        ["app-server", "--listen", "stdio://", "-s", "read-only"],
    ],
)
def test_fixture_rejects_unknown_cli_arguments(args):
    """The executable fixture must not conceal unsupported production argv."""
    result = subprocess.run(
        [sys.executable, str(FIXTURE), *args],
        input="",
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )
    assert result.returncode == 2
    assert "unsupported argv" in result.stderr
