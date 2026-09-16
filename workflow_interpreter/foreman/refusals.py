"""Bounded durable refusal journal, independent of mutable gate inbox receipts."""

import hashlib
from pathlib import Path

import structlog
from pydantic import BaseModel, ConfigDict, ValidationError

from workflow_interpreter.foreman.observation import (
    ObservationStatus,
    bounded,
    read_status,
    save_status,
)
from workflow_interpreter.foreman.wake_constants import (
    DEFAULT_EVENT_CAP,
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

# Retain the existing observation exports while sharing the advisory I/O boundary.
__all__ = [
    "ObservationStatus",
    "RefusalJournal",
    "RefusalRecord",
    "append_refusal",
    "bounded",
    "read_journal",
    "read_refusals",
]


class RefusalRecord(BaseModel):
    """A stable identity for one failed signed gate intake, without its secrets."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    identity: str
    gate_id: str
    gate_key: str
    path: str
    error: str
    reason: str


class RefusalJournal(BaseModel):
    """Valid journal evidence plus a count of skipped corrupt records."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    records: tuple[RefusalRecord, ...] = ()
    invalid_records: int = 0
    error: str | None = None


def read_journal(directory: Path) -> RefusalJournal:
    """Retain readable refusals even when another bounded journal line is corrupt."""
    try:
        with (directory / REFUSAL_JOURNAL).open("rb") as stream:
            raw = stream.read(MAX_EVENT_CAP * MAX_CONDITION_BYTES + 1)
    except FileNotFoundError:
        return RefusalJournal()
    except OSError as error:
        return RefusalJournal(error=bounded(str(error)))
    over_bound = len(raw) > MAX_EVENT_CAP * MAX_CONDITION_BYTES
    records = []
    invalid = 0
    for line in raw.splitlines()[:MAX_EVENT_CAP]:
        try:
            if len(line) > MAX_CONDITION_BYTES:
                raise ValueError(MSG_JOURNAL_BOUND)
            records.append(RefusalRecord.model_validate_json(line))
        except (ValidationError, ValueError):
            invalid += 1
    return RefusalJournal(
        records=tuple(records),
        invalid_records=invalid,
        error=MSG_JOURNAL_BOUND if over_bound else None,
    )


def read_refusals(directory: Path) -> tuple[RefusalRecord, ...]:
    """Return readable evidence; observation callers also report journal diagnostics."""
    return read_journal(directory).records


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
        journal = read_journal(directory)
        if journal.error:
            raise OSError(journal.error)
        if journal.invalid_records:
            save_status(
                directory,
                read_status(directory).degraded(journal=journal.invalid_records),
            )
        records = journal.records
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
