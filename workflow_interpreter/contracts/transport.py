"""Closed runner I/O transports; independent of vendor and workflow models."""

from enum import StrEnum


class RunnerTransport(StrEnum):
    """How the resident wrapper exchanges data with a single launched process."""

    EVENT_LOG = "event-log"
    STDIO_RPC = "stdio-rpc"
