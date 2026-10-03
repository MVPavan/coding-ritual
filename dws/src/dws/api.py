"""Local authenticated command API with an optional thin MCP mount."""

from __future__ import annotations

import asyncio
import os
import re
import secrets
import stat
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from dws.config import Settings, prepare_owner_state
from dws.engine import Engine
from dws.errors import DWSError


def _valid_token(token: str) -> str:
    # RFC 6750 bearer syntax; never include the credential in a startup error.
    if not 1 <= len(token) <= 4096 or re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", token) is None:
        raise ValueError("The DWS API token must be a nonempty valid bearer credential")
    return token


def _read_local_token(directory: int) -> str:
    descriptor = os.open(
        "api-token",
        os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
        dir_fd=directory,
    )
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or not 1 <= info.st_size <= 4097
        ):
            raise ValueError(
                "The local API token must be a regular file owned by the current user "
                "with mode 0600"
            )
        try:
            token = stream.read(4098).decode("ascii").removesuffix("\n")
        except UnicodeDecodeError:
            raise ValueError(
                "The local API token file contains an invalid credential"
            ) from None
    return _valid_token(token)


def local_token(settings: Settings) -> str:
    path = prepare_owner_state(settings.data_dir)
    if settings.token is not None:
        return _valid_token(settings.token)
    directory = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(directory)
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o022:
            raise ValueError(
                "The API token directory must be owned by the current user "
                "and not writable by others"
            )
        try:
            return _read_local_token(directory)
        except FileNotFoundError:
            pass
        staging = ".api-token-" + secrets.token_hex(16) + ".tmp"
        descriptor = os.open(
            staging,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=directory,
        )
        try:
            with os.fdopen(descriptor, "wb") as stream:
                os.fchmod(stream.fileno(), 0o600)
                stream.write((secrets.token_urlsafe(32) + "\n").encode("ascii"))
                stream.flush()
                os.fsync(stream.fileno())
            with suppress(FileExistsError):
                # A concurrent starter can win, but can never observe partial contents.
                os.link(
                    staging,
                    "api-token",
                    src_dir_fd=directory,
                    dst_dir_fd=directory,
                    follow_symlinks=False,
                )
            os.fsync(directory)
            return _read_local_token(directory)
        finally:
            os.unlink(staging, dir_fd=directory)
            os.fsync(directory)
    finally:
        os.close(directory)


class LocalAccess:
    """ASGI admission and byte limits also cover the mounted MCP application."""

    def __init__(self, app: ASGIApp, token: str, active_limit: int = 32) -> None:
        self.app = app
        self.token = _valid_token(token)
        self.active_limit = active_limit
        self.active = 0

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1")
            for k, v in scope.get("headers", [])
        }
        origin = headers.get("origin")
        try:
            host = urlsplit("//" + headers.get("host", "")).hostname
            parsed_origin = urlsplit(origin) if origin else None
        except ValueError:
            host, parsed_origin = None, None
        if host not in {"127.0.0.1", "localhost", "dws-api", "::1"} or (
            origin
            and (
                parsed_origin is None
                or parsed_origin.hostname not in {"127.0.0.1", "localhost", "::1"}
                or parsed_origin.scheme not in {"http", "https"}
            )
        ):
            await JSONResponse({"error": {"code": "local_access_only"}}, 403)(
                scope, receive, send
            )
            return
        if scope["path"] not in {"/health", "/ready"}:
            provided = headers.get("authorization", "")
            if not secrets.compare_digest(
                provided.encode("latin-1"), ("Bearer " + self.token).encode("utf-8")
            ):
                await JSONResponse({"error": {"code": "authentication_required"}}, 401)(
                    scope, receive, send
                )
                return
        if self.active >= self.active_limit:
            await JSONResponse(
                {"error": {"code": "busy", "message": "Admission limit reached"}}, 429
            )(scope, receive, send)
            return
        length = headers.get("content-length", "0")
        if (
            len(length) > 6
            or not length.isascii()
            or not length.isdecimal()
            or int(length) > 65536
        ):
            await JSONResponse({"error": {"code": "request_too_large"}}, 413)(
                scope, receive, send
            )
            return
        self.active += 1
        try:
            await self.serve_bounded(scope, receive, send)
        finally:
            self.active -= 1

    async def serve_bounded(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Buffer only a bounded request, including chunked bodies, before effects.
        body = bytearray()
        try:
            async with asyncio.timeout(10):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body", b""))
                    if len(body) > 65536:
                        await JSONResponse({"error": {"code": "request_too_large"}}, 413)(
                            scope, receive, send
                        )
                        return
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            await JSONResponse({"error": {"code": "request_timeout"}}, 408)(
                scope, receive, send
            )
            return
        delivered = False

        async def bounded_receive() -> Message:
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, bounded_receive, send)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    token = local_token(settings)
    engine = Engine(settings)
    mcp_app: Any = None
    if os.environ.get("DWS_MCP_ENABLED", "false").lower() == "true":
        from dws.mcp_adapter import create_mcp

        mcp_app = create_mcp(engine).http_app(path="/", stateless_http=True, json_response=True)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if mcp_app is not None:
            async with mcp_app.lifespan(app):
                yield
        else:
            yield

    app = FastAPI(title="DWS", version="1.0", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.engine = engine
    app.add_middleware(LocalAccess, token=token, active_limit=settings.max_jobs)

    @app.exception_handler(DWSError)
    async def dws_error(request: Request, error: DWSError) -> JSONResponse:
        return JSONResponse(error.payload(), status_code=error.status)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception) -> JSONResponse:
        failure = DWSError(
            "internal_error", "An unexpected internal failure prevented the operation.", 500
        )
        return JSONResponse(failure.payload(), status_code=failure.status)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "dws"}

    @app.get("/ready")
    async def ready() -> dict[str, object]:
        return {"status": "ready", "retrieval": "sqlite_fts5", "mcp": mcp_app is not None}

    @app.post("/v1/{operation}")
    async def command(operation: str, request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except (ValueError, UnicodeDecodeError, RecursionError):
            raise DWSError("invalid_json", "Invalid JSON request") from None
        try:
            if not isinstance(payload, dict):
                raise DWSError("invalid_request", "The request must be a JSON object")
            return JSONResponse(await engine.execute(operation, payload))
        except ValidationError as error:
            fields = [".".join(str(x) for x in item["loc"]) for item in error.errors()]
            raise DWSError(
                "invalid_request", "Invalid fields: " + ", ".join(fields)[:512], 422
            ) from None

    if mcp_app is not None:
        app.mount("/mcp", mcp_app)
    return app
