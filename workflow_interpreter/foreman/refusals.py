"""Bounded durable refusal journal, independent of mutable gate inbox receipts."""

import hashlib
from pathlib import Path

import structlog
from pydantic import BaseModel, ConfigDict

from workflow_interpreter.foreman.wake_constants import (
    DEFAULT_EVENT_CAP,
    DETAIL_BYTES,
    JOURNAL_LOCK,
    LOG_CAP,
    LOG_REFUSAL,
    MAX_CONDITION_BYTES,
    MAX_EVENT_CAP,
    MSG_JOURNAL_BOUND,
    OBSERVATION_STATUS,
    REFUSAL_JOURNAL,
)
from workflow_interpreter.supervisor.band import BandLock
from workflow_interpreter.supervisor.paths import write_durable, write_record


class RefusalRecord(BaseModel):
    """A stable identity for one failed signed gate intake, without its secrets."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    identity: str
    gate_id: str
    gate_key: str
    path: str
    error: str
    reason: str


class ObservationStatus(BaseModel):
    """Fixed-size evidence of saturation or degraded observation durability."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    saturated: bool = False
    error: str | None = None


def bounded(text: str, limit: int = DETAIL_BYTES) -> str:
    """Bound UTF-8 diagnostics without retaining approval payloads or signatures."""
    return text.encode("utf-8")[:limit].decode("utf-8", errors="ignore")


def read_refusals(directory: Path) -> tuple[RefusalRecord, ...]:
    """Read the bounded journal; corruption is a reported error, not an empty log."""
    try:
        with (directory / REFUSAL_JOURNAL).open("rb") as stream:
            raw = stream.read(MAX_EVENT_CAP * MAX_CONDITION_BYTES + 1)
    except FileNotFoundError:
        return ()
    if len(raw) > MAX_EVENT_CAP * MAX_CONDITION_BYTES:
        raise ValueError(MSG_JOURNAL_BOUND)
    records = []
    for line in raw.splitlines():
        if len(line) > MAX_CONDITION_BYTES:
            raise ValueError(MSG_JOURNAL_BOUND)
        records.append(RefusalRecord.model_validate_json(line))
    return tuple(records)


def append_refusal(
    directory: Path,
    *,
    gate_id: str,
    gate_key: str,
    payload: bytes,
    signature: bytes,
    error: str,
    reason: str,
    path: Path,
    limit: int = DEFAULT_EVENT_CAP,
) -> RefusalRecord:
    """Persist once per signed refusal identity before reporting intake failure."""
    digest = hashlib.sha256()
    for part in (
        gate_key.encode(),
        payload,
        signature,
        error.encode(),
        bounded(reason).encode(),
    ):
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    record = RefusalRecord(
        identity=digest.hexdigest(),
        gate_id=gate_id,
        gate_key=gate_key,
        path=bounded(str(path), 1024),
        error=bounded(error, 128),
        reason=bounded(reason),
    )
    with BandLock(directory / JOURNAL_LOCK):
        records = read_refusals(directory)
        if any(old.identity == record.identity for old in records):
            return record
        if len(records) >= limit:
            write_record(
                directory / OBSERVATION_STATUS, ObservationStatus(saturated=True)
            )
            structlog.get_logger(__name__).error(LOG_CAP)
            return record
        encoded = record.model_dump_json().encode() + b"\n"
        if len(encoded) > MAX_CONDITION_BYTES:
            raise ValueError(MSG_JOURNAL_BOUND)
        write_durable(
            directory / REFUSAL_JOURNAL,
            b"".join(old.model_dump_json().encode() + b"\n" for old in records)
            + encoded,
        )
        structlog.get_logger(__name__).error(
            LOG_REFUSAL,
            gate_id=gate_id,
            identity=record.identity,
            path=record.path,
            error=record.error,
            reason=record.reason,
        )
    return record
