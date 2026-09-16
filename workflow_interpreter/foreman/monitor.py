"""Separate host monitor: durable observations, idempotent bd events, no model calls."""

from __future__ import annotations

import hashlib
import os
from datetime import timedelta
from typing import Self

import structlog

from workflow_interpreter.bdio.errors import StoreError
from workflow_interpreter.bdio.keys import wake_fire_key
from workflow_interpreter.bdio.reads import gates_of
from workflow_interpreter.contracts.wake import WakeCondition, WakeCursor, WakeEvent
from workflow_interpreter.foreman.compose import Composition
from workflow_interpreter.foreman.heartbeat import process_handle, read_heartbeat
from workflow_interpreter.foreman.observation import bounded, read_status, save_status
from workflow_interpreter.foreman.refusals import RefusalRecord, read_journal
from workflow_interpreter.foreman.wake import (
    HOOK_ATTEMPTS,
    LOG_MONITOR_ERROR,
    LOG_MONITOR_READY,
    MSG_MONITOR_CAPACITY,
    MSG_MONITOR_IDENTITY,
    MSG_MONITOR_LOCK,
    MSG_MONITOR_REQUIRED,
    HookError,
    MonitorHandle,
    MonitorHealth,
    MonitorState,
    MonitorUnavailable,
    WakeDelivery,
    WakeState,
    run_hook,
)
from workflow_interpreter.foreman.wake_constants import (
    LOG_CAP,
    MAX_CONDITION_BYTES,
    MAX_EVENT_CAP,
    MONITOR_HANDLE,
    MONITOR_LOCK,
    MSG_JOURNAL_RECORD,
    REFUSAL_JOURNAL,
    WAKE_STATE,
    DriverCondition,
    DriverState,
)
from workflow_interpreter.supervisor.band import BandLock
from workflow_interpreter.supervisor.clock import elapsed_seconds, from_iso, to_iso
from workflow_interpreter.supervisor.errors import WrapperDirError
from workflow_interpreter.supervisor.models import Liveness
from workflow_interpreter.supervisor.paths import (
    WrapperPaths,
    read_record,
    write_record,
)
from workflow_interpreter.supervisor.procfs import prove_liveness


def monitor_health(composition: Composition, root_id: str) -> MonitorHealth:
    """Require an acknowledged, fresh monitor with matching local process identity."""
    paths = WrapperPaths(composition.supervisor_config, root_id)
    handle = read_record(paths.instance_dir / MONITOR_HANDLE, MonitorHandle)
    if handle is None:
        return MonitorHealth.MISSING
    root = composition.store.reads.load_root(root_id)
    if (
        handle.root_id != root_id
        or handle.instance_key != root.metadata.instance_key
        or handle.handle is None
        or handle.handle.host != composition.supervisor_config.host
    ):
        return MonitorHealth.INDETERMINATE
    if handle.state is MonitorState.STOPPED:
        return MonitorHealth.STOPPED
    proof = prove_liveness(composition.supervisor_config, handle.handle)
    if proof.status is Liveness.INDETERMINATE:
        return MonitorHealth.INDETERMINATE
    if not proof.alive:
        return MonitorHealth.LOST
    if (
        elapsed_seconds(handle.timestamp, composition.clock.now())
        > composition.config.wake.stale_s
    ):
        return MonitorHealth.STALE
    return MonitorHealth.HEALTHY


def require_monitor(composition: Composition, root_id: str) -> None:
    """Gate only explicitly monitored startup, never ordinary run or bridge use."""
    try:
        health = monitor_health(composition, root_id)
    except (WrapperDirError, OSError, ValueError) as error:
        raise MonitorUnavailable(
            MSG_MONITOR_REQUIRED.format(root_id=root_id)
        ) from error
    if health is not MonitorHealth.HEALTHY:
        raise MonitorUnavailable(MSG_MONITOR_REQUIRED.format(root_id=root_id))


def monitor_status(composition: Composition, root_id: str) -> dict[str, object]:
    """Report delivery health without pretending a bd event is a received hook."""
    paths = WrapperPaths(composition.supervisor_config, root_id)
    state = None
    degraded = None
    try:
        state = read_record(paths.instance_dir / WAKE_STATE, WakeState)
        health = monitor_health(composition, root_id)
    except (WrapperDirError, OSError, ValueError) as error:
        degraded = bounded(str(error))
        health = MonitorHealth.INDETERMINATE
    return {
        "health": health.value,
        "monitor_degraded": degraded or (state.monitor_degraded if state else None),
        "pending_fires": sum(d.event_id is None for d in state.deliveries)
        if state
        else 0,
        "pending_hooks": sum(
            d.event_id is not None and not d.acknowledged and d.attempts < HOOK_ATTEMPTS
            for d in state.deliveries
        )
        if state
        else 0,
        "exhausted_hooks": sum(
            not d.acknowledged and d.attempts == HOOK_ATTEMPTS for d in state.deliveries
        )
        if state
        else 0,
        "last_delivery_error": state.last_error if state else None,
        "wake_cap_exhausted": state.cap_exhausted if state else False,
        "saturated": state.saturated if state else False,
    }


class WakeMonitor:
    """One locally locked monitor owns the per-instance durable delivery outbox."""

    def __init__(self, composition: Composition, root_id: str) -> None:
        """Bind a host process and its protected outbox to one admitted root."""
        self._composition = composition
        self._root_id = root_id
        self._config = composition.config.wake
        self._paths = WrapperPaths(composition.supervisor_config, root_id)
        self._lock = BandLock(self._paths.instance_dir / MONITOR_LOCK)
        self._clock = composition.clock
        self._handle = process_handle(composition.supervisor_config, self._clock)
        self._instance_key = composition.store.reads.load_root(
            root_id
        ).metadata.instance_key
        self._state = WakeState(root_id=root_id, instance_key=self._instance_key)

    def __enter__(self) -> Self:
        """Acquire exclusive local ownership, reconcile bd, then acknowledge startup."""
        self._lock.acquire()
        try:
            prior = read_record(self._paths.instance_dir / WAKE_STATE, WakeState)
            if prior is not None:
                if (
                    prior.root_id != self._root_id
                    or prior.instance_key != self._instance_key
                ):
                    raise MonitorUnavailable(MSG_MONITOR_IDENTITY)
                self._state = prior
            self._reconcile()
            self._save()
            self._ack(MonitorState.READY)
            structlog.get_logger(__name__).info(
                LOG_MONITOR_READY, root_id=self._root_id
            )
            return self
        except BaseException:
            self._lock.release()
            raise

    def __exit__(self, *exc_info: object) -> None:
        """Leave explicit stopped evidence and always release the kernel lock."""
        try:
            self._ack(MonitorState.STOPPED)
        finally:
            self._lock.release()

    def run(self, *, max_wall_s: float | None = None) -> WakeState:
        """Poll independently until interrupted or an optional test/operator bound."""
        started = self._clock.now()
        with self:
            while True:
                self.poll()
                if (
                    max_wall_s is not None
                    and (self._clock.now() - started).total_seconds() >= max_wall_s
                ):
                    return self._state
                self._clock.sleep(self._config.poll_s)

    def poll(self) -> WakeState:
        """Persist observed cursors before delivering, retaining errors and retries."""
        if not self._lock.held:
            raise MonitorUnavailable(MSG_MONITOR_LOCK)
        self._ack(MonitorState.READY)
        try:
            if not self._reconcile():
                self._save()
                return self._state
            self._observe()
            self._save()
            self._fire()
            self._hooks()
        except (StoreError, OSError) as error:
            self._state = self._state.model_copy(
                update={"last_error": bounded(str(error))}
            )
            self._save()
            structlog.get_logger(__name__).error(
                LOG_MONITOR_ERROR, root_id=self._root_id, reason=bounded(str(error))
            )
        return self._state

    def _ack(self, state: MonitorState) -> None:
        """Publish liveness separately from the driver's heartbeat and kill group."""
        write_record(
            self._paths.instance_dir / MONITOR_HANDLE,
            MonitorHandle(
                root_id=self._root_id,
                instance_key=self._instance_key,
                handle=self._handle,
                timestamp=to_iso(self._clock.now()),
                state=state,
            ),
        )

    def _save(self) -> None:
        """Atomically commit cursor/attempt changes before their following effects."""
        write_record(self._paths.instance_dir / WAKE_STATE, self._state)

    def _replace(self, delivery: WakeDelivery) -> None:
        """Update exactly one existing fire without growing the bounded outbox."""
        self._state = self._state.model_copy(
            update={
                "deliveries": tuple(
                    delivery if old.event.fire_key == delivery.event.fire_key else old
                    for old in self._state.deliveries
                )
            }
        )
        self._save()

    def _reconcile(self) -> bool:
        """Expose read failures durably and retry without pretending delivery works."""
        try:
            self._reconcile_events()
        except (StoreError, WrapperDirError, OSError, ValueError) as error:
            detail = bounded(str(error))
            self._state = self._state.model_copy(
                update={"monitor_degraded": detail, "last_error": detail}
            )
            structlog.get_logger(__name__).error(
                LOG_MONITOR_ERROR, root_id=self._root_id, reason=detail
            )
            return False
        self._state = self._state.model_copy(update={"monitor_degraded": None})
        return True

    def _reconcile_events(self) -> None:
        """Recover ambiguous bd writes and derive lifetime usage from durable events."""
        events = self._composition.store.reads.list_wake_events(self._root_id)
        deliveries = {d.event.fire_key: d for d in self._state.deliveries}
        for event in events:
            if event.instance_key != self._instance_key:
                raise MonitorUnavailable(MSG_MONITOR_IDENTITY)
            old = deliveries.get(event.fire_key)
            if old is not None and old.event != event:
                raise MonitorUnavailable(MSG_MONITOR_IDENTITY)
            bead = self._composition.store.reads.find_event(
                self._root_id, event.fire_key
            )
            if bead is not None:
                deliveries[event.fire_key] = (
                    old or WakeDelivery(event=event)
                ).model_copy(update={"event_id": bead.id})
        if len(deliveries) > MAX_EVENT_CAP:
            raise MonitorUnavailable(MSG_MONITOR_CAPACITY.format(limit=MAX_EVENT_CAP))
        times = [event.fired_at for event in events if event.fired_at]
        if self._state.last_fire_at:
            times.append(self._state.last_fire_at)
        exhausted = len(events) >= self._config.lifetime_cap
        if exhausted and not self._state.cap_exhausted:
            structlog.get_logger(__name__).error(LOG_CAP, root_id=self._root_id)
        self._state = self._state.model_copy(
            update={
                "deliveries": tuple(deliveries.values()),
                "cap_exhausted": exhausted,
                "last_fire_at": max(times, key=from_iso) if times else None,
            }
        )

    def _queue(self, condition: WakeCondition, identity: str, detail: str) -> None:
        """Reserve finite capacity for a newly observed condition before advancing cursors."""
        cursor = WakeCursor(identity=identity)
        key = wake_fire_key(self._root_id, self._instance_key, condition, cursor)
        if any(d.event.fire_key == key for d in self._state.deliveries):
            return
        if len(self._state.deliveries) >= self._config.lifetime_cap:
            self._state = self._state.model_copy(update={"saturated": True})
            return
        event = WakeEvent(
            root_id=self._root_id,
            instance_key=self._instance_key,
            condition=condition,
            cursor=cursor,
            fire_key=key,
            observed_at=to_iso(self._clock.now()),
            detail=bounded(detail),
        )
        self._state = self._state.model_copy(
            update={
                "deliveries": (
                    *self._state.deliveries,
                    WakeDelivery(event=event),
                )
            }
        )

    def _journal(self) -> None:
        """Consume bounded condition records by offset; reset safely after truncation."""
        try:
            stream = (self._paths.instance_dir / REFUSAL_JOURNAL).open("rb")
        except FileNotFoundError:
            return
        with stream:
            stat = os.fstat(stream.fileno())
            size = stat.st_size
            offset = self._state.journal_offset
            generation = self._state.journal_generation
            changed = (
                self._state.journal_device != stat.st_dev
                or self._state.journal_inode != stat.st_ino
            )
            if size < offset or (
                changed and (offset or self._state.journal_inode is not None)
            ):
                offset = 0
                generation += 1
            stream.seek(offset)
            corrupt = False
            for _ in range(MAX_EVENT_CAP):
                line = stream.readline(MAX_CONDITION_BYTES + 1)
                if not line:
                    break
                offset = stream.tell()
                try:
                    if len(line) > MAX_CONDITION_BYTES or not line.endswith(b"\n"):
                        raise ValueError(MSG_JOURNAL_RECORD)
                    record = RefusalRecord.model_validate_json(line)
                except ValueError:
                    corrupt = True
                    continue
                self._queue(
                    WakeCondition.REFUSAL, record.identity, record.model_dump_json()
                )
            if corrupt:
                journal = read_journal(self._paths.instance_dir)
                save_status(
                    self._paths.instance_dir,
                    read_status(self._paths.instance_dir).degraded(
                        journal=journal.invalid_records, error=journal.error
                    ),
                )
                self._state = self._state.model_copy(
                    update={"monitor_degraded": MSG_JOURNAL_RECORD}
                )
        self._state = self._state.model_copy(
            update={
                "journal_offset": offset,
                "journal_generation": generation,
                "journal_device": stat.st_dev,
                "journal_inode": stat.st_ino,
            }
        )

    def _observe(self) -> None:
        """Read carrier/log metadata only; historical gate records close polling gaps."""
        root = self._composition.store.reads.load_root(self._root_id)
        for gate in gates_of(
            self._composition.store.reads.instance_beads(self._root_id)
        ):
            self._queue(WakeCondition.GATE_OPENED, gate.metadata.gate_key, gate.gate_id)
        self._journal()
        if root.metadata.terminal is not None:
            self._queue(
                WakeCondition.ROOT_TERMINAL,
                root.metadata.terminal,
                root.metadata.terminal,
            )
        heartbeat, error = read_heartbeat(self._paths.driver_heartbeat)
        if error:
            self._state = self._state.model_copy(update={"monitor_degraded": error})
        if heartbeat is None:
            return
        if (
            heartbeat.root_id != self._root_id
            or heartbeat.instance_key != self._instance_key
        ):
            raise MonitorUnavailable(MSG_MONITOR_IDENTITY)
        identity = hashlib.sha256(
            (
                heartbeat.generation
                + (heartbeat.identity.model_dump_json() if heartbeat.identity else "")
            ).encode()
        ).hexdigest()
        stopped = heartbeat.state is DriverState.STOPPED
        if stopped and heartbeat.last_condition is not DriverCondition.ERROR:
            return
        proof = (
            prove_liveness(self._composition.supervisor_config, heartbeat.identity)
            if heartbeat.identity is not None
            else None
        )
        lost = (
            heartbeat.identity is not None
            and heartbeat.identity.host == self._composition.supervisor_config.host
            and proof is not None
            and proof.status in (Liveness.DEAD, Liveness.IDENTITY_MISMATCH)
        )
        if heartbeat.identity is not None and (stopped or lost):
            self._queue(
                WakeCondition.DRIVER_EXIT,
                identity,
                heartbeat.last_condition.value
                if stopped
                else proof.status.value
                if proof
                else "",
            )
        elif (
            elapsed_seconds(heartbeat.timestamp, self._clock.now())
            > self._config.stale_s
        ):
            self._queue(
                WakeCondition.HEARTBEAT_STALE,
                f"{identity}:{heartbeat.ticks}",
                heartbeat.last_condition.value,
            )

    def _fire(self) -> None:
        """Confirm at most one new durable event per interval; bd failure never acks it."""
        if self._state.cap_exhausted:
            return
        if (
            self._state.last_fire_at
            and elapsed_seconds(self._state.last_fire_at, self._clock.now())
            < self._config.min_fire_interval_s
        ):
            return
        pending = next((d for d in self._state.deliveries if d.event_id is None), None)
        if pending is None:
            return
        now = to_iso(self._clock.now())
        event = pending.event.model_copy(
            update={"fired_at": pending.event.fired_at or now}
        )
        self._state = self._state.model_copy(update={"last_fire_at": now})
        pending = pending.model_copy(update={"event": event})
        self._replace(pending)
        bead = self._composition.store.append_wake_event(self._root_id, event)
        self._replace(pending.model_copy(update={"event_id": bead.id}))
        self._reconcile()
        self._save()

    def _hooks(self) -> None:
        """Journal attempts before bounded execution and acknowledge only after success."""
        for delivery in self._state.deliveries:
            if (
                delivery.event_id is None
                or delivery.acknowledged
                or delivery.attempts >= HOOK_ATTEMPTS
            ):
                continue
            if delivery.next_attempt_at and self._clock.now() < from_iso(
                delivery.next_attempt_at
            ):
                continue
            if not self._config.hook_argv:
                self._replace(delivery.model_copy(update={"acknowledged": True}))
                continue
            attempt = delivery.attempts + 1
            pending = delivery.model_copy(
                update={
                    "attempts": attempt,
                    "next_attempt_at": to_iso(
                        self._clock.now()
                        + timedelta(seconds=self._config.hook_backoff_s * attempt)
                    ),
                }
            )
            self._replace(pending)
            try:
                run_hook(pending.event, self._config, self._composition.host_env)
            except HookError as error:
                detail = bounded(str(error))
                self._state = self._state.model_copy(update={"last_error": detail})
                self._replace(pending.model_copy(update={"error": detail}))
                structlog.get_logger(__name__).error(
                    LOG_MONITOR_ERROR, fire_key=pending.event.fire_key, reason=detail
                )
            else:
                self._replace(
                    pending.model_copy(update={"acknowledged": True, "error": None})
                )
            # One bounded subprocess per poll keeps monitor health responsive.
            return
