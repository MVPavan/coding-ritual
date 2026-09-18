"""Bounded nonblocking stdio RPC; all process and workflow authority stays outside."""

from __future__ import annotations

import os
import selectors
import time
from enum import StrEnum
from typing import Final, Self

import structlog
from pydantic import BaseModel, ConfigDict, JsonValue, ValidationError, model_validator

from workflow_interpreter.contracts.codex import (
    CODEX_VERSION as CODEX_VERSION,  # noqa: PLC0414
)

MAX_FRAME_BYTES: Final[int] = 262144
MAX_STDERR_BYTES: Final[int] = 16384
MAX_POLL_S: Final[float] = 0.1
MAX_FRAMES_PER_POLL: Final[int] = 64
MSG_FRAME: Final[str] = "invalid or oversized app-server frame"
MSG_CORRELATION: Final[str] = "uncorrelated or duplicate app-server response"
MSG_DEADLINE: Final[str] = "app-server request deadline exceeded"
MSG_EOF: Final[str] = "app-server protocol closed"
MSG_UNKNOWN: Final[str] = "unknown app-server notification or request"
MSG_UNSUPPORTED: Final[str] = "unsupported tool or permission request"
MSG_BUSY: Final[str] = "app-server request already pending"


_LOG = structlog.get_logger(__name__)
MSG_INPUT_CLOSED: Final[str] = "wf.rpc.outbound_dropped.input_closed"


class RpcMethod(StrEnum):
    """Exercised client methods from the pinned generated schema."""

    INITIALIZE = "initialize"
    INITIALIZED = "initialized"
    THREAD_START = "thread/start"
    THREAD_RESUME = "thread/resume"
    TURN_START = "turn/start"
    TURN_STEER = "turn/steer"
    TURN_INTERRUPT = "turn/interrupt"


class Notification(StrEnum):
    """Closed recognized notification subset; everything else fails loudly."""

    THREAD_STARTED = "thread/started"
    THREAD_STATUS = "thread/status/changed"
    TURN_STARTED = "turn/started"
    TURN_COMPLETED = "turn/completed"
    USAGE = "thread/tokenUsage/updated"
    ITEM_STARTED = "item/started"
    ITEM_COMPLETED = "item/completed"
    MESSAGE_DELTA = "item/agentMessage/delta"
    COMMAND_DELTA = "item/commandExecution/outputDelta"
    REASONING_DELTA = "item/reasoning/textDelta"
    SUMMARY_DELTA = "item/reasoning/summaryTextDelta"
    SUMMARY_PART = "item/reasoning/summaryPartAdded"
    FILE_DELTA = "item/fileChange/outputDelta"
    DIFF = "turn/diff/updated"
    PLAN = "turn/plan/updated"
    ERROR = "error"
    WARNING = "warning"
    CONFIG_WARNING = "configWarning"
    DEPRECATION = "deprecationNotice"


class ServerRequest(StrEnum):
    """Recognized requests are denied, never dispatched to host tools."""

    TOOL = "item/tool/call"
    COMMAND_APPROVAL = "item/commandExecution/requestApproval"
    FILE_APPROVAL = "item/fileChange/requestApproval"
    PERMISSIONS = "item/permissions/requestApproval"
    INPUT = "item/tool/requestUserInput"
    ELICITATION = "mcpServer/elicitation/request"


class RpcFailure(Exception):
    """Transport/protocol failure; the owner must terminate and record evidence."""


class RpcError(BaseModel):
    """A bounded protocol error, never an executable tool result."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    code: int
    message: str
    data: JsonValue = None


class RpcFrame(BaseModel):
    """Envelope validation precedes any method-specific interpretation."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    id: int | str | None = None
    method: str | None = None
    params: dict[str, JsonValue] | None = None
    result: dict[str, JsonValue] | None = None
    error: RpcError | None = None
    jsonrpc: str | None = None

    @model_validator(mode="after")
    def valid_shape(self) -> Self:
        """Reject mixed request/response shapes and unsupported JSON-RPC versions."""
        if self.jsonrpc not in (None, "2.0"):
            raise ValueError(MSG_FRAME)
        if self.method is not None:
            if self.result is not None or self.error is not None:
                raise ValueError(MSG_FRAME)
        elif self.id is None or (self.result is None) == (self.error is None):
            raise ValueError(MSG_FRAME)
        return self


class RpcClient:
    """Own three pipe descriptors and one bounded in-flight request.

    Polling never waits beyond 100 ms. The resident inspector remains responsible
    for process death proof and max-wall/stale enforcement between polls. Stderr
    is drained independently into a bounded tail and is never parsed as protocol.
    """

    def __init__(
        self, stdin: int, stdout: int, stderr: int, *, timeout_s: float = 10
    ) -> None:
        self._input = stdin
        self._output = stdout
        self._error = stderr
        self._selector = selectors.DefaultSelector()
        self._fds = {stdin, stdout, stderr}
        for descriptor in self._fds:
            os.set_blocking(descriptor, False)
        self._selector.register(stdout, selectors.EVENT_READ)
        self._selector.register(stderr, selectors.EVENT_READ)
        self._incoming = bytearray()
        self._outgoing = bytearray()
        self._stderr = bytearray()
        self._sequence = 0
        self._pending: int | None = None
        self._deadline = 0.0
        self._timeout = timeout_s
        self.eof = False

    @property
    def stderr_tail(self) -> str:
        """Diagnostic-only bounded text; callers must not log credentials from it."""
        return self._stderr.decode("utf-8", errors="replace")

    @property
    def output_pending(self) -> bool:
        """Whether required replies still need flushing before stdin closes."""
        return bool(self._outgoing)

    @property
    def pending(self) -> bool:
        """Whether a submitted request remains ambiguous/unacknowledged."""
        return self._pending is not None

    def __enter__(self) -> Self:
        """Enter the descriptor ownership scope."""
        return self

    def __exit__(self, *exc_info: object) -> None:
        """Release every owned descriptor even after a protocol failure."""
        self.close()

    def close_input(self) -> None:
        """Signal end of client input after flushing all required messages."""
        if self._input in self._fds:
            if self._input in self._selector.get_map():
                self._selector.unregister(self._input)
            os.close(self._input)
            self._fds.remove(self._input)

    def close(self) -> None:
        """Close only these pipe endpoints; process lifetime belongs to the wrapper."""
        self._selector.close()
        for descriptor in self._fds:
            os.close(descriptor)
        self._fds.clear()

    def _queue(self, frame: RpcFrame) -> None:
        """Bound queued output even if the vendor never reads stdin."""
        if self._input not in self._fds:
            _LOG.warning(MSG_INPUT_CLOSED, method=frame.method, request_id=frame.id)
            return
        data = frame.model_dump_json(exclude_none=True).encode() + b"\n"
        if len(data) + len(self._outgoing) > MAX_FRAME_BYTES:
            raise RpcFailure(MSG_FRAME)
        self._outgoing.extend(data)
        if self._input not in self._selector.get_map():
            self._selector.register(self._input, selectors.EVENT_WRITE)

    def request(self, method: RpcMethod, params: dict[str, JsonValue]) -> int:
        """Queue once; the owner must persist intent before invoking this method."""
        if self._pending is not None:
            raise RpcFailure(MSG_BUSY)
        self._sequence += 1
        self._queue(RpcFrame(id=self._sequence, method=method.value, params=params))
        self._pending = self._sequence
        self._deadline = time.monotonic() + self._timeout
        return self._sequence

    def notify(self, method: RpcMethod) -> None:
        """Queue the initialized notification without manufacturing a request ID."""
        self._queue(RpcFrame(method=method.value))

    def _frame(self, line: bytes) -> RpcFrame | None:
        """Check correlation and reject server-request capabilities at the boundary."""
        try:
            frame = RpcFrame.model_validate_json(line)
        except ValidationError as error:
            raise RpcFailure(MSG_FRAME) from error
        if frame.method is None:
            if frame.id != self._pending or self._pending is None:
                raise RpcFailure(MSG_CORRELATION)
            self._pending = None
            return frame
        if frame.id is not None:
            try:
                ServerRequest(frame.method)
            except ValueError as error:
                raise RpcFailure(MSG_UNKNOWN) from error
            self._queue(
                RpcFrame(
                    id=frame.id,
                    error=RpcError(
                        code=-32601,
                        message=MSG_UNSUPPORTED,
                    ),
                )
            )
            return None
        try:
            Notification(frame.method)
        except ValueError as error:
            raise RpcFailure(MSG_UNKNOWN) from error
        return frame

    def poll(self, timeout_s: float = MAX_POLL_S) -> tuple[RpcFrame, ...]:
        """Advance bounded I/O once, returning validated frames without blocking work."""
        if self._pending is not None and time.monotonic() >= self._deadline:
            raise RpcFailure(MSG_DEADLINE)
        try:
            for key, _ in self._selector.select(min(MAX_POLL_S, max(0, timeout_s))):
                if key.fd == self._input:
                    count = os.write(key.fd, self._outgoing)
                    del self._outgoing[:count]
                    if not self._outgoing:
                        self._selector.unregister(key.fd)
                    continue
                data = os.read(key.fd, 65536)
                if not data:
                    self._selector.unregister(key.fd)
                    if key.fd == self._output:
                        self.eof = True
                    continue
                if key.fd == self._error:
                    self._stderr.extend(data)
                    del self._stderr[:-MAX_STDERR_BYTES]
                else:
                    self._incoming.extend(data)
        except OSError as error:
            raise RpcFailure(MSG_EOF) from error
        frames = []
        for _ in range(MAX_FRAMES_PER_POLL):
            end = self._incoming.find(b"\n")
            if end < 0:
                break
            if end > MAX_FRAME_BYTES:
                raise RpcFailure(MSG_FRAME)
            line = bytes(self._incoming[:end])
            del self._incoming[: end + 1]
            frame = self._frame(line)
            if frame is not None:
                frames.append(frame)
        if len(self._incoming) > MAX_FRAME_BYTES:
            raise RpcFailure(MSG_FRAME)
        if self.eof and (self._incoming or self._pending is not None):
            raise RpcFailure(MSG_EOF)
        return tuple(frames)
