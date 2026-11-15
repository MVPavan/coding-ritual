"""`playbooks/eval/egress.py`, run as its own processes against local listeners."""

from __future__ import annotations

import importlib.util
import socket
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / ".claude/skills/mvp-mode/playbooks/eval/egress.py"
)
PYTHON = "/usr/bin/python3"  # the one the runner uses on both sides
OK = b"HTTP/1.1 200"
FORBIDDEN = b"HTTP/1.1 403"


class Echo:
    """A local TCP server that counts connections and echoes bytes back."""

    def __init__(self) -> None:
        self.server = socket.create_server(("127.0.0.1", 0))
        self.port: int = self.server.getsockname()[1]
        self.accepted = 0
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self) -> None:
        while True:
            try:
                client, _ = self.server.accept()
            except OSError:
                return
            self.accepted += 1
            threading.Thread(target=self._echo, args=(client,), daemon=True).start()

    @staticmethod
    def _echo(client: socket.socket) -> None:
        with client:
            while data := client.recv(4096):
                client.sendall(data)


class Proxy:
    def __init__(self, root: Path, allow: str) -> None:
        self.path = str(root / "p.sock")
        self.log = root / "decisions.log"
        self.process = subprocess.Popen(
            [
                PYTHON,
                "-I",
                str(SCRIPT),
                "proxy",
                "--socket",
                self.path,
                "--allow",
                allow,
                "--log",
                str(self.log),
                "--head-timeout",
                "0.5",
            ]
        )
        _wait_for(lambda: Path(self.path).exists())

    def connect(self) -> socket.socket:
        client = socket.socket(socket.AF_UNIX)
        client.settimeout(5)
        client.connect(self.path)
        return client

    def decisions(self) -> str:
        return self.log.read_text()


def _wait_for(ready: object) -> None:
    assert callable(ready)
    deadline = time.monotonic() + 5
    while not ready():
        assert time.monotonic() < deadline, "timed out"
        time.sleep(0.01)


def _ask(client: socket.socket, head: bytes) -> bytes:
    """Send a head and return all the proxy says until it closes."""
    client.sendall(head)
    answer = b""
    while data := client.recv(4096):
        answer += data
    return answer


@pytest.fixture
def echo() -> Iterator[Echo]:
    server = Echo()
    yield server
    server.server.close()


@pytest.fixture
def proxy(echo: Echo) -> Iterator[Proxy]:
    if not Path(PYTHON).exists():
        pytest.skip(f"{PYTHON} is missing")
    with tempfile.TemporaryDirectory(prefix="work") as root:
        running = Proxy(Path(root), f"127.0.0.1:{echo.port}")
        yield running
        running.process.kill()
        running.process.wait()


def test_the_allowed_target_is_tunnelled_both_ways(proxy: Proxy, echo: Echo) -> None:
    with proxy.connect() as client:
        client.sendall(
            f"CONNECT 127.0.0.1:{echo.port} HTTP/1.1\r\nHost: x\r\n\r\n".encode()
        )
        assert client.recv(4096).startswith(OK)
        client.sendall(b"out and back")
        assert client.recv(4096) == b"out and back"

    assert echo.accepted == 1
    assert f"allow 127.0.0.1:{echo.port}" in proxy.decisions()


@pytest.mark.parametrize(
    ("make_head", "logged"),
    [
        (
            lambda port: f"CONNECT 127.0.0.1:{port + 1} HTTP/1.1\r\n\r\n",
            "deny 127.0.0.1:",
        ),
        (
            lambda port: "CONNECT example.invalid:443 HTTP/1.1\r\n\r\n",
            "deny example.invalid:443",
        ),
        (
            lambda port: f"GET http://127.0.0.1:{port}/ HTTP/1.1\r\n\r\n",
            "deny GET http",
        ),
        (lambda port: f"CONNECT 127.0.0.1:{port} HTTP/2\r\n\r\n", "deny CONNECT"),
        (lambda port: f"CONNECT  127.0.0.1:{port} HTTP/1.1\r\n\r\n", "deny CONNECT"),
        (lambda port: f"\x00\xff\n127.0.0.1:{port}\r\n\r\n", "deny \\x00"),
    ],
)
def test_anything_else_gets_403_and_no_outbound(
    proxy: Proxy, echo: Echo, make_head: object, logged: str
) -> None:
    assert callable(make_head)
    with proxy.connect() as client:
        answer = _ask(client, make_head(echo.port).encode("latin-1"))

    assert answer.startswith(FORBIDDEN)
    assert echo.accepted == 0
    assert logged in proxy.decisions()


@pytest.mark.parametrize(
    "after", ["early", "early\r\n\r\n", "CONNECT 127.0.0.1:1 HTTP/1.1\r\n\r\n"]
)
def test_bytes_after_the_head_are_refused(proxy: Proxy, echo: Echo, after: str) -> None:
    head = f"CONNECT 127.0.0.1:{echo.port} HTTP/1.1\r\n\r\n{after}".encode()
    with proxy.connect() as client:
        assert _ask(client, head).startswith(FORBIDDEN)
    assert echo.accepted == 0


def test_a_denied_target_cannot_forge_a_log_line(proxy: Proxy) -> None:
    with proxy.connect() as client:
        _ask(client, b"CONNECT a\nallow\x1b:443 HTTP/1.1\r\n\r\n")
    assert [line[:5] for line in proxy.decisions().splitlines()] == ["deny "]


def test_an_oversized_head_is_closed_with_no_outbound(proxy: Proxy, echo: Echo) -> None:
    with proxy.connect() as client:
        # Closed with bytes unread: the client sees an end or a reset, never an answer.
        try:
            client.sendall(f"CONNECT 127.0.0.1:{echo.port} HTTP/1.1\r\n".encode())
            client.sendall(b"X-Pad: " + b"a" * 20000)
            assert not client.recv(4096)
        except (BrokenPipeError, ConnectionResetError):
            pass

    assert echo.accepted == 0
    assert "deny oversized head" in proxy.decisions()


def test_a_silent_client_is_closed_with_no_outbound(proxy: Proxy, echo: Echo) -> None:
    with proxy.connect() as client:
        client.sendall(f"CONNECT 127.0.0.1:{echo.port} HTTP/1.1\r\n".encode())
        assert not client.recv(4096)

    assert echo.accepted == 0
    assert "deny silent client" in proxy.decisions()


def test_a_target_that_will_not_connect_is_a_502(echo: Echo) -> None:
    with tempfile.TemporaryDirectory(prefix="work") as root:
        unused = socket.create_server(("127.0.0.1", 0))
        port = unused.getsockname()[1]
        unused.close()
        running = Proxy(Path(root), f"127.0.0.1:{port}")
        try:
            with running.connect() as client:
                answer = _ask(
                    client, f"CONNECT 127.0.0.1:{port} HTTP/1.1\r\n\r\n".encode()
                )
            assert answer.startswith(b"HTTP/1.1 502")
            assert f"failed 127.0.0.1:{port}" in running.decisions()
        finally:
            running.process.kill()
            running.process.wait()


def test_the_forwarder_relays_through_the_proxy(proxy: Proxy, echo: Echo) -> None:
    probe = socket.create_server(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    forwarder = subprocess.Popen(
        [
            PYTHON,
            "-I",
            str(SCRIPT),
            "forward",
            "--socket",
            proxy.path,
            "--port",
            str(port),
        ],
        stdout=subprocess.PIPE,
    )
    try:
        assert forwarder.stdout is not None
        assert forwarder.stdout.readline() == b"listening\n"
        with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
            client.sendall(f"CONNECT 127.0.0.1:{echo.port} HTTP/1.1\r\n\r\n".encode())
            assert client.recv(4096).startswith(OK)
            client.sendall(b"through both")
            assert client.recv(4096) == b"through both"
    finally:
        forwarder.kill()
        forwarder.wait()


def test_a_machine_without_its_numbers_is_refused() -> None:
    spec = importlib.util.spec_from_file_location("eval_egress", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # No bytecode beside the script: that folder ships.
    writes_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    sys.dont_write_bytecode = writes_bytecode

    with pytest.raises(SystemExit, match="riscv64"):
        module.seccomp_filter("riscv64")
