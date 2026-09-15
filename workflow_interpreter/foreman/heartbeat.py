"""Protected driver responsiveness records; no transcript or model invocation."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Self

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import ProcessHandle
from workflow_interpreter.bdio.reads import activations_of, gates_of
from workflow_interpreter.foreman.refusals import (
    ObservationStatus,
    bounded,
    read_refusals,
)
from workflow_interpreter.foreman.wake_constants import (
    MSG_IDENTITY,
    OBSERVATION_STATUS,
    DriverCondition,
    DriverState,
)
from workflow_interpreter.supervisor.clock import Clock, elapsed_seconds, to_iso
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.paths import (
    HEARTBEAT_FILE,
    WrapperPaths,
    read_record,
    write_record,
)
from workflow_interpreter.supervisor.procfs import read_boot_id, read_start_time

if TYPE_CHECKING:
    from workflow_interpreter.foreman.compose import Composition
    from workflow_interpreter.foreman.tick import TickReport


class LogCursor(BaseModel):
    """Activation and inode generation distinguish truncation from forward output."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    activation_id: str
    device: int
    inode: int
    generation: int = 0
    offset: int


def log_cursor(
    path: Path, activation_id: str, previous: LogCursor | None
) -> LogCursor | None:
    """Inspect log metadata only; increment its generation after replacement/shrink."""
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    changed = previous is not None and (
        previous.activation_id != activation_id
        or previous.device != stat.st_dev
        or previous.inode != stat.st_ino
        or previous.offset > stat.st_size
    )
    return LogCursor(
        activation_id=activation_id,
        device=stat.st_dev,
        inode=stat.st_ino,
        generation=(previous.generation + int(changed)) if previous else 0,
        offset=stat.st_size,
    )


class DriverHeartbeat(BaseModel):
    """One atomic host-owned observation of a driver, including clean termination."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal[1] = 1
    root_id: str
    instance_key: str
    generation: str
    handle: ProcessHandle
    state: DriverState
    ticks: int = 0
    timestamp: str
    root_state: str
    activations: tuple[str, ...] = ()
    gates: tuple[str, ...] = ()
    refusal_count: int = 0
    last_condition: DriverCondition = DriverCondition.STARTING
    logs: tuple[LogCursor, ...] = ()
    durability_error: str | None = None


def process_handle(config: SupervisorConfig, clock: Clock) -> ProcessHandle:
    """Record the current host process with the same identity proof as a runner."""
    pid = os.getpid()
    start = read_start_time(config, pid)
    boot = read_boot_id(config)
    if start is None or boot is None:
        raise OSError(MSG_IDENTITY)
    return ProcessHandle(
        pid=pid,
        pgid=os.getpgrp(),
        host=config.host,
        host_boot_id=boot,
        proc_start_time=start,
        started_at=to_iso(clock.now()),
        log_path="",
        session_id="",
    )


class DriverObserver:
    """Own one driver generation across ticks and write stopped even on exceptions."""

    def __init__(self, composition: Composition, root_id: str) -> None:
        self._composition = composition
        self._root_id = root_id
        self._paths = WrapperPaths(composition.supervisor_config, root_id)
        self._generation = uuid.uuid4().hex
        self._handle = process_handle(composition.supervisor_config, composition.clock)
        self._ticks = 0
        self._condition = DriverCondition.STARTING
        previous = read_record(self._paths.driver_heartbeat, DriverHeartbeat)
        self._logs = (
            {log.activation_id: log for log in previous.logs} if previous else {}
        )

    def __enter__(self) -> Self:
        """Publish startup before entering potentially blocking driver work."""
        self._write(DriverState.STARTING)
        return self

    def observe(self, report: TickReport, *, advance: bool = True) -> None:
        """Record each completed tick and its operator-facing stop condition."""
        self._ticks += int(advance)
        self._condition = (
            DriverCondition.ATTENTION
            if report.refusals
            else DriverCondition.STALLED
            if report.stalled
            else DriverCondition.TERMINAL
            if report.terminal
            else DriverCondition.GATE
            if report.opened_gate or report.waiting_gate or report.halted
            else DriverCondition.ACTIVE
        )
        self._write(DriverState.RUNNING)

    def __exit__(self, *exc_info: object) -> None:
        """Persist expected stop or exceptional exit without asserting model success."""
        if exc_info and exc_info[0] is not None:
            self._condition = DriverCondition.ERROR
        self._write(DriverState.STOPPED)

    def _write(self, state: DriverState) -> None:
        """Snapshot durable carriers and log metadata after the tick's writes."""
        root = self._composition.store.reads.load_root(self._root_id)
        beads = self._composition.store.reads.instance_beads(self._root_id)
        active = tuple(a for a in activations_of(beads) if not a.metadata.is_completed)
        logs = tuple(
            cursor
            for activation in active
            if (
                cursor := log_cursor(
                    self._paths.log(activation.activation_id),
                    activation.activation_id,
                    self._logs.get(activation.activation_id),
                )
            )
            is not None
        )
        self._logs = {log.activation_id: log for log in logs}
        status = read_record(
            self._paths.instance_dir / OBSERVATION_STATUS, ObservationStatus
        )
        heartbeat = DriverHeartbeat(
            root_id=self._root_id,
            instance_key=root.metadata.instance_key,
            generation=self._generation,
            handle=self._handle,
            state=state,
            ticks=self._ticks,
            timestamp=to_iso(self._composition.clock.now()),
            root_state=root.bead.status,
            activations=tuple(a.activation_id for a in active),
            gates=tuple(
                g.gate_id for g in gates_of(beads) if g.bead.status != "closed"
            ),
            refusal_count=len(read_refusals(self._paths.instance_dir)),
            last_condition=self._condition,
            logs=logs,
            durability_error=status.error if status else None,
        )
        write_record(self._paths.driver_heartbeat, heartbeat)


def observation_status(directory: Path, clock: Clock) -> dict[str, object]:
    """Expose retained refusals and responsiveness without reading model output."""
    heartbeat = read_record(directory / HEARTBEAT_FILE, DriverHeartbeat)
    status = read_record(directory / OBSERVATION_STATUS, ObservationStatus)
    refusals = read_refusals(directory)
    return {
        "heartbeat": heartbeat.model_dump(
            mode="json",
            include={
                "state",
                "ticks",
                "generation",
                "last_condition",
                "durability_error",
            },
        )
        if heartbeat
        else None,
        "heartbeat_age_s": elapsed_seconds(heartbeat.timestamp, clock.now())
        if heartbeat
        else None,
        "refusals": [
            {**item.model_dump(mode="json"), "reason": bounded(item.reason, 512)}
            for item in refusals[-1:]
        ],
        "refusal_count": len(refusals),
        "durability": status.model_dump(mode="json") if status else None,
    }
