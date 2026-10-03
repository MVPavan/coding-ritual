"""Bounded HTTP and destination policy shared by all direct acquisitions.

The httpcore network backend resolves and validates every DNS answer at the
actual connection, then connects to a numeric address. The HTTP origin stays
unchanged, so Host, TLS SNI and certificate verification use the original host.
Known NAT64 translation prefixes are denied, including aliases for public IPv4
addresses. Deployment-specific translation prefixes cannot be inferred here.
"""

from __future__ import annotations

import asyncio
import fcntl
import ipaddress
import os
import socket
import ssl
import time
import zlib
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpcore
import httpx

from dws.config import Settings
from dws.errors import DWSError

_NAT64_PREFIXES = (
    ipaddress.IPv6Network("64:ff9b::/96"),
    ipaddress.IPv6Network("64:ff9b:1::/48"),
)


def canonical_url(url: str) -> str:
    """Normalize an HTTP URL without permitting credentials or ambiguous hosts."""
    if any(ord(char) < 33 for char in url) or "\\" in url:
        raise DWSError("invalid_url", "URL contains whitespace or invalid characters")
    try:
        parts = urlsplit(url)
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            raise ValueError
        if parts.username is not None or parts.password is not None:
            raise ValueError
        host = parts.hostname.rstrip(".").encode("idna").decode("ascii").lower()
        if not host or "%" in host:
            raise ValueError
        port = parts.port
        if port is not None and not 1 <= port <= 65535:
            raise ValueError
        netloc = f"[{host}]" if ":" in host else host
        if port is not None and port != (443 if parts.scheme.lower() == "https" else 80):
            netloc += f":{port}"
        value = urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", parts.query, ""))
        return str(httpx.URL(value))
    except (ValueError, UnicodeError, httpx.InvalidURL):
        raise DWSError(
            "invalid_url", "An absolute HTTP(S) URL without credentials is required"
        ) from None


def _public_address(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.is_site_local:
            return False
        # RFC 6052 section 3.1 forbids non-global IPv4 in the well-known
        # prefix. Deny both known translation prefixes rather than trusting
        # the enclosing IPv6 address's is_global classification or translator.
        if any(ip in prefix for prefix in _NAT64_PREFIXES):
            return False
        if ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped
        elif ip.sixtofour or ip.teredo:
            return False
    return ip.is_global and not ip.is_multicast and not ip.is_unspecified and not ip.is_reserved


async def resolve_addresses(
    host: str, port: int, allowed_private_hosts: tuple[str, ...]
) -> list[str]:
    """Reject mixed public/private answers, not just the first DNS response."""
    normalized = host.lower().rstrip(".")
    try:
        literal = ipaddress.ip_address(normalized)
        addresses = [str(literal)]
    except ValueError:
        try:
            answers = await asyncio.get_running_loop().getaddrinfo(
                normalized, port, type=socket.SOCK_STREAM
            )
        except OSError:
            raise DWSError(
                "dns_failed", "The source hostname could not be resolved", 502
            ) from None
        addresses = list(dict.fromkeys(str(answer[4][0]) for answer in answers))
    if not addresses:
        raise DWSError("dns_failed", "The source hostname has no usable addresses", 502)
    if normalized not in allowed_private_hosts and any(
        not _public_address(ip) for ip in addresses
    ):
        raise DWSError("policy_denied", "Outbound policy denies a non-public destination", 403)
    return addresses


class PinnedBackend(httpcore.AsyncNetworkBackend):
    def __init__(self, allowed_private_hosts: tuple[str, ...]) -> None:
        self.allowed_private_hosts = allowed_private_hosts
        self.backend = httpcore.AnyIOBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        async with asyncio.timeout(timeout):
            addresses = await resolve_addresses(host, port, self.allowed_private_hosts)
            # Only a previously validated numeric address reaches the OS connect.
            for index, address in enumerate(addresses):
                try:
                    return await self.backend.connect_tcp(
                        address, port, timeout, local_address, socket_options
                    )
                except httpcore.ConnectError:
                    if index == len(addresses) - 1:
                        raise
        raise DWSError("source_unavailable", "Source connection failed", 502)

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        raise DWSError("policy_denied", "Unix sockets are not acquisition destinations", 403)

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


class CoreStream(httpx.AsyncByteStream):
    def __init__(self, response: httpcore.Response) -> None:
        self.response = response

    async def __aiter__(self) -> AsyncIterator[bytes]:
        async for chunk in self.response.aiter_stream():
            yield chunk

    async def aclose(self) -> None:
        await self.response.aclose()


class PinnedTransport(httpx.AsyncBaseTransport):
    def __init__(self, allowed_private_hosts: tuple[str, ...]) -> None:
        self.pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl.create_default_context(),
            network_backend=PinnedBackend(allowed_private_hosts),
            max_connections=1,
            max_keepalive_connections=0,
            retries=0,
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        response = await self.pool.handle_async_request(
            httpcore.Request(
                method=request.method,
                url=httpcore.URL(
                    scheme=request.url.raw_scheme,
                    host=request.url.raw_host,
                    port=request.url.port,
                    target=request.url.raw_path,
                ),
                headers=request.headers.raw,
                content=request.stream,
                extensions=request.extensions,
            )
        )
        return httpx.Response(
            response.status,
            headers=response.headers,
            stream=CoreStream(response),
            extensions=response.extensions,
        )

    async def aclose(self) -> None:
        await self.pool.aclose()


@asynccontextmanager
async def acquisition_slot(settings: Settings) -> AsyncIterator[None]:
    """Crash-released process locks bound concurrent API and worker acquisitions."""
    directory = settings.data_dir / "acquisition-slots"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    deadline = time.monotonic() + min(5.0, settings.request_timeout)
    while True:
        for index in range(settings.acquisition_slots):
            fd = os.open(
                directory / f"{index}.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600
            )
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                os.close(fd)
                continue
            try:
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
            return
        if time.monotonic() >= deadline:
            raise DWSError("acquisition_busy", "Acquisition capacity is busy; retry later", 429)
        await asyncio.sleep(0.05)


async def response_bytes(response: httpx.Response, max_bytes: int) -> bytes:
    """Bound both wire bytes and decoded bytes without a decompression bomb."""
    length = response.headers.get("content-length")
    if length:
        try:
            if int(length) < 0:
                raise ValueError
            if int(length) > max_bytes:
                raise DWSError(
                    "response_too_large", "Source exceeds the configured byte limit", 413
                )
        except ValueError:
            raise DWSError(
                "invalid_response", "Source has an invalid content length", 502
            ) from None
    encoding = response.headers.get("content-encoding", "identity").strip().lower()
    decoder: Any = None
    if encoding == "gzip":
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    elif encoding == "deflate":
        decoder = zlib.decompressobj()
    elif encoding not in {"", "identity"}:
        raise DWSError(
            "unsupported_encoding", "Source ignored the supported content encodings", 502
        )
    body = bytearray()
    wire_bytes = 0
    try:
        async for chunk in response.aiter_raw():
            wire_bytes += len(chunk)
            if wire_bytes > max_bytes:
                raise DWSError(
                    "response_too_large", "Source exceeds the configured byte limit", 413
                )
            if decoder is None:
                body.extend(chunk)
            else:
                pending = chunk
                while pending:
                    body.extend(decoder.decompress(pending, max_bytes - len(body) + 1))
                    pending = decoder.unconsumed_tail
                    if len(body) > max_bytes:
                        raise DWSError(
                            "response_too_large", "Decoded source exceeds the byte limit", 413
                        )
                if decoder.unused_data:
                    raise DWSError(
                        "invalid_response",
                        "Concatenated compressed content is unsupported",
                        502,
                    )
            if len(body) > max_bytes:
                raise DWSError(
                    "response_too_large", "Decoded source exceeds the byte limit", 413
                )
        if decoder is not None and not decoder.eof:
            raise DWSError("invalid_response", "Compressed source is incomplete", 502)
    except zlib.error:
        raise DWSError("invalid_response", "Compressed source is malformed", 502) from None
    return bytes(body)


def client(allowed_private_hosts: tuple[str, ...], timeout: float) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=PinnedTransport(allowed_private_hosts),
        timeout=timeout,
        follow_redirects=False,
        trust_env=False,
        headers={"User-Agent": "DWS/0.1 public-evidence", "Accept-Encoding": "identity"},
    )
