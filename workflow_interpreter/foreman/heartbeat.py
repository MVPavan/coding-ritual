"""Protected driver responsiveness records; no transcript or model invocation."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Self

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from workflow_interpreter.bdio import ProcessHandle
from workflow_interpreter.bdio.errors import StoreError
from workflow_interpreter.bdio.reads import activations_of, gates_of
from workflow_interpreter.foreman.observation import (
    bounded,
    read_status,
    save_status,
)
from workflow_interpreter.foreman.refusals import read_journal
from workflow_interpreter.foreman.wake_constants import (
    MSG_IDENTITY,
    DriverCondition,
    DriverState,
)
from workflow_interpreter.supervisor.clock import Clock, elapsed_seconds, to_iso
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.errors import WrapperDirError
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
    identity: ProcessHandle | None = Field(
        default=None, validation_alias=AliasChoices("identity", "handle")
    )
    identity_degraded: bool = False
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


def process_handle(config: SupervisorConfig, clock: Clock) -> ProcessHandle | None:
    """Record the current host process with the same identity proof as a runner."""
    pid = os.getpid()
    start = read_start_time(config, pid)
    boot = read_boot_id(config)
    if start is None or boot is None:
        return None
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
        self.status = read_status(self._paths.instance_dir)
        if self._handle is None:
            self.status = self.status.degraded(identity=MSG_IDENTITY)
        previous, error = read_heartbeat(self._paths.driver_heartbeat)
        if error:
            self.status = self.status.degraded(heartbeat=error)
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
            self._condition = (
                DriverCondition.STOPPED
                if exc_info[0] in (KeyboardInterrupt, SystemExit)
                else DriverCondition.ERROR
            )
        self._write(DriverState.STOPPED)

    def _write(self, state: DriverState) -> None:
        """Keep observational I/O failures out of the driver's control flow."""
        try:
            self._snapshot(state)
        except (StoreError, WrapperDirError, OSError, ValueError) as error:
            self.status = self.status.degraded(error=str(error), heartbeat=str(error))
        self.status = save_status(self._paths.instance_dir, self.status)

    def _snapshot(self, state: DriverState) -> None:
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
        persisted = read_status(self._paths.instance_dir)
        journal = read_journal(self._paths.instance_dir)
        self.status = self.status.model_copy(
            update={"saturated": self.status.saturated or persisted.saturated}
        ).degraded(
            error=journal.error or persisted.error,
            heartbeat=persisted.heartbeat_degraded,
            journal=max(journal.invalid_records, persisted.journal_degraded),
            identity=persisted.identity_degraded,
        )
        heartbeat = DriverHeartbeat(
            root_id=self._root_id,
            instance_key=root.metadata.instance_key,
            generation=self._generation,
            identity=self._handle,
            identity_degraded=self._handle is None,
            state=state,
            ticks=self._ticks,
            timestamp=to_iso(self._composition.clock.now()),
            root_state=root.bead.status,
            activations=tuple(a.activation_id for a in active),
            gates=tuple(
                g.gate_id for g in gates_of(beads) if g.bead.status != "closed"
            ),
            refusal_count=len(journal.records),
            last_condition=self._condition,
            logs=logs,
            durability_error=self.status.error,
        )
        write_record(self._paths.driver_heartbeat, heartbeat)


def observation_status(directory: Path, clock: Clock) -> dict[str, object]:
    """Expose retained refusals and responsiveness without reading model output."""
    heartbeat, heartbeat_error = read_heartbeat(directory / HEARTBEAT_FILE)
    journal = read_journal(directory)
    status = read_status(directory).degraded(
        heartbeat=heartbeat_error, journal=journal.invalid_records, error=journal.error
    )
    age = None
    if heartbeat:
        try:
            age = elapsed_seconds(heartbeat.timestamp, clock.now())
        except ValueError as error:
            status = status.degraded(heartbeat=str(error))
    refusals = journal.records
    return {
        "heartbeat": heartbeat.model_dump(
            mode="json",
            include={
                "state",
                "ticks",
                "generation",
                "last_condition",
                "durability_error",
                "identity_degraded",
            },
        )
        if heartbeat
        else None,
        "heartbeat_age_s": age,
        "refusals": [
            {**item.model_dump(mode="json"), "reason": bounded(item.reason, 512)}
            for item in refusals[-1:]
        ],
        "refusal_count": len(refusals),
        "durability": status.model_dump(mode="json"),
    }


def read_heartbeat(path: Path) -> tuple[DriverHeartbeat | None, str | None]:
    """Malformed or unreadable heartbeat evidence is advisory, never authority."""
    try:
        return read_record(path, DriverHeartbeat), None
    except (WrapperDirError, OSError, ValueError) as error:
        return None, bounded(str(error))
