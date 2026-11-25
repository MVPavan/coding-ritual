#!/usr/bin/env python3
"""The one way out of a boundary with no network: a proxy and its forwarder.

usage: egress.py proxy --socket <path> --allow <host:port> --log <file>
                       [--head-timeout seconds]
       egress.py forward --socket <path> --port <port>
       egress.py filter

proxy runs outside the boundary and listens on a Unix socket. Each connection
sends one request head. Only `CONNECT <allowed host:port> HTTP/1.x` opens a
tunnel: this process resolves the name and connects, so the client never gives
it an address. Anything else gets a 403 with no outbound attempt, and a head that
is too long or too slow is closed the same way. Each decision goes to the log.

forward runs inside the boundary, listens on 127.0.0.1:<port>, passes each
connection's bytes to the Unix socket, and prints a line once it is listening.

filter writes a seccomp program in classic BPF to stdout, for `bwrap --seccomp`.
A network namespace does not isolate every socket family: AF_VSOCK reaches the
Windows host on WSL2. So socket() takes only the families below and any other
returns EAFNOSUPPORT. io_uring_setup returns ENOSYS, because IORING_OP_SOCKET makes
a socket with no socket() call, and so does another architecture or x32 syscall
number, which would use numbers this program does not check. It refuses a machine
it has no numbers for.

Standard library only: it runs under /usr/bin/python3 on both sides.
"""

from __future__ import annotations

import argparse
import os
import socket
import struct
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

MAX_HEAD = 8192
MAX_LOGGED = 200
CONNECT_TIMEOUT = 15.0
FORBIDDEN = b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\nContent-Length: 0\r\n\r\n"
BAD_GATEWAY = (
    b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\nContent-Length: 0\r\n\r\n"
)
ESTABLISHED = b"HTTP/1.1 200 Connection Established\r\n\r\n"

# Machine: its AUDIT_ARCH value and socket() number.
MACHINES = {"x86_64": (0xC000003E, 41), "aarch64": (0xC00000B7, 198)}
IO_URING_SETUP = 425  # the same on both
X32_BIT = 0x40000000
ALLOWED_FAMILIES = (
    socket.AF_UNIX,
    socket.AF_INET,
    socket.AF_INET6,
    socket.AF_NETLINK,
)
EAFNOSUPPORT = 97
ENOSYS = 38
# struct seccomp_data, little-endian: `nr`, `arch`, then the low half of args[0].
NR_OFFSET, ARCH_OFFSET, ARG0_OFFSET = 0, 4, 16
BPF_LOAD = 0x20  # BPF_LD | BPF_W | BPF_ABS
BPF_JEQ = 0x15  # BPF_JMP | BPF_JEQ | BPF_K
BPF_JSET = 0x45  # BPF_JMP | BPF_JSET | BPF_K
BPF_RET = 0x06  # BPF_RET | BPF_K
RET_ALLOW = 0x7FFF0000
RET_ERRNO = 0x00050000


def relay(left: socket.socket, right: socket.socket) -> None:
    """Pass bytes both ways until either side closes, then close both."""

    def pump(source: socket.socket, target: socket.socket) -> None:
        try:
            while data := source.recv(65536):
                target.sendall(data)
        except OSError:
            pass
        for side in (source, target):
            try:
                side.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    other = threading.Thread(target=pump, args=(right, left), daemon=True)
    other.start()
    pump(left, right)
    other.join()
    left.close()
    right.close()


def read_head(client: socket.socket, limit: float) -> tuple[bytes | None, str]:
    """Return the whole head and "", or None and why the client was given up on."""
    deadline = time.monotonic() + limit
    head = b""
    while b"\r\n\r\n" not in head:
        if len(head) > MAX_HEAD:
            return None, "oversized head"
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None, "silent client"
        client.settimeout(remaining)
        try:
            data = client.recv(4096)
        except TimeoutError:
            return None, "silent client"
        except OSError:
            return None, "client error"
        if not data:
            return None, "client closed before a whole head"
        head += data
    client.settimeout(None)
    if len(head) > MAX_HEAD:
        return None, "oversized head"
    return head, ""


def connect_target(head: bytes) -> str | None:
    """Return the target of a well-formed CONNECT head with nothing after it."""
    whole, _, after = head.partition(b"\r\n\r\n")
    if after:
        return None
    parts = whole.partition(b"\r\n")[0].split(b" ")
    if len(parts) != 3 or parts[0] != b"CONNECT":
        return None
    if parts[2] not in (b"HTTP/1.0", b"HTTP/1.1"):
        return None
    return parts[1].decode("latin-1")


def serve_client(
    client: socket.socket, allow: str, head_timeout: float, log: Callable[[str], None]
) -> None:
    head, why = read_head(client, head_timeout)
    if head is None:
        log(f"deny {why}")
        client.close()
        return
    target = connect_target(head)
    if target != allow:
        # Client-chosen bytes: one line, escaped and short, whatever they hold.
        shown = target or head.partition(b"\r\n")[0].decode("latin-1")
        log("deny " + shown[:MAX_LOGGED].encode("unicode_escape").decode("ascii"))
        try:
            client.sendall(FORBIDDEN)
        except OSError:
            pass
        client.close()
        return
    log(f"allow {allow}")
    host, _, port = allow.rpartition(":")
    try:
        upstream = socket.create_connection((host, int(port)), timeout=CONNECT_TIMEOUT)
    except OSError as error:
        log(f"failed {allow}: {error}")
        try:
            client.sendall(BAD_GATEWAY)
        except OSError:
            pass
        client.close()
        return
    upstream.settimeout(None)
    try:
        client.sendall(ESTABLISHED)
    except OSError:
        client.close()
        upstream.close()
        return
    relay(client, upstream)


def proxy(socket_path: str, allow: str, log_path: Path, head_timeout: float) -> None:
    lock = threading.Lock()
    with log_path.open(
        "a", buffering=1, encoding="ascii", errors="backslashreplace"
    ) as out:

        def log(line: str) -> None:
            with lock:
                out.write(line + "\n")

        server = socket.socket(socket.AF_UNIX)
        server.bind(socket_path)
        server.listen()
        while True:
            client, _ = server.accept()
            threading.Thread(
                target=serve_client,
                args=(client, allow, head_timeout, log),
                daemon=True,
            ).start()


def forward_client(client: socket.socket, socket_path: str) -> None:
    upstream = socket.socket(socket.AF_UNIX)
    try:
        upstream.connect(socket_path)
    except OSError:
        client.close()
        upstream.close()
        return
    relay(client, upstream)


def forward(socket_path: str, port: int) -> None:
    server = socket.create_server(("127.0.0.1", port))
    print("listening", flush=True)
    os.close(1)
    while True:
        client, _ = server.accept()
        threading.Thread(
            target=forward_client, args=(client, socket_path), daemon=True
        ).start()


def seccomp_filter(machine: str) -> bytes:
    """The program for this machine, as an array of struct sock_filter."""
    if machine not in MACHINES:
        raise SystemExit(f"egress.py: no seccomp numbers for machine: {machine}")
    arch, socket_nr = MACHINES[machine]
    deny = RET_ERRNO | ENOSYS
    # (code, jump if true, jump if false, k); a jump counts the instructions it skips.
    program = [
        (BPF_LOAD, 0, 0, ARCH_OFFSET),
        (BPF_JEQ, 1, 0, arch),
        (BPF_RET, 0, 0, deny),
    ]
    program.append((BPF_LOAD, 0, 0, NR_OFFSET))
    if machine == "x86_64":
        program += [(BPF_JSET, 0, 1, X32_BIT), (BPF_RET, 0, 0, deny)]
    program += [
        (BPF_JEQ, 0, 1, IO_URING_SETUP),
        (BPF_RET, 0, 0, deny),
        (BPF_JEQ, 1, 0, socket_nr),
        (BPF_RET, 0, 0, RET_ALLOW),
        (BPF_LOAD, 0, 0, ARG0_OFFSET),
    ]
    left = len(ALLOWED_FAMILIES)
    program += [
        (BPF_JEQ, left - i, 0, int(family)) for i, family in enumerate(ALLOWED_FAMILIES)
    ]
    program += [(BPF_RET, 0, 0, RET_ERRNO | EAFNOSUPPORT), (BPF_RET, 0, 0, RET_ALLOW)]
    return b"".join(struct.pack("<HBBI", *row) for row in program)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    proxy_mode = modes.add_parser("proxy")
    proxy_mode.add_argument("--socket", required=True)
    proxy_mode.add_argument("--allow", required=True)
    proxy_mode.add_argument("--log", required=True, type=Path)
    proxy_mode.add_argument("--head-timeout", type=float, default=10.0)
    forward_mode = modes.add_parser("forward")
    forward_mode.add_argument("--socket", required=True)
    forward_mode.add_argument("--port", required=True, type=int)
    modes.add_parser("filter")
    args = parser.parse_args()
    if args.mode == "proxy":
        proxy(args.socket, args.allow, args.log, args.head_timeout)
    elif args.mode == "filter":
        sys.stdout.buffer.write(seccomp_filter(os.uname().machine))
    else:
        forward(args.socket, args.port)


if __name__ == "__main__":
    main()
