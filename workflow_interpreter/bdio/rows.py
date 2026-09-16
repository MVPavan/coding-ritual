"""The neutral vocabulary of the store seam — rows, queries, writes, identity.

A `StoreBackend` speaks these types and nothing else (§3.1). They carry what
every backend has: an id, a status, a carrier, and for an event row its
payload. Everything bd-shaped — titles, issue types, wisps, `bd context`
fields, a `BdConfig` — stays inside `client.py`, so the S1 ledger backend
implements a store rather than emulating bd.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.bdio.wire import ROW_MODEL, Metadata


class RowKind(StrEnum):
    """What a durable row IS to the store — a record, or an appended event.

    The only distinction the seam needs: an event row carries an immutable
    payload beside its carrier, a record row does not. How a backend spells
    that (bd's `--type`, a ledger table) is the backend's business.
    """

    RECORD = "record"
    EVENT = "event"


class StoreRow(BaseModel):
    """One durable row as a backend returns it, carrier included."""

    model_config = ROW_MODEL

    id: str
    status: str
    kind: RowKind = RowKind.RECORD
    metadata: Metadata = Field(default_factory=dict)
    payload: str | None = None
    close_reason: str | None = None


class RowQuery(BaseModel):
    """The selection a backend read is given — ANDed carrier filters.

    Never "all rows": every §4 read selects by `wf_root_id` or `wf_kind`, and
    a backend that cannot honour a filter must not answer more rows than it
    was asked for.
    """

    model_config = ROW_MODEL

    metadata_filters: Mapping[str, str] = Field(default_factory=dict)
    kind: RowKind | None = None


class NewRow(BaseModel):
    """A row to create: its carrier, its kind, and a human-readable summary.

    `summary` is disclosure, not identity — nothing routes on it. A backend
    with no human surface may store it and never show it.
    """

    model_config = ROW_MODEL

    summary: str
    metadata: Metadata
    kind: RowKind = RowKind.RECORD
    payload: Metadata | None = None


class BackendIdentity(BaseModel):
    """What a backend is, for the collaborators that must place its locks.

    `lock_root` is where execution locks over this backend's rows live, and
    `legacy_lock_root` is the pre-migration directory whose presence means an
    unmigrated layout — both are the backend's answer, so no caller has to
    know a workspace layout to ask (§3.4 lock order).
    """

    model_config = ROW_MODEL

    kind: BackendKind
    lock_root: Path
    legacy_lock_root: Path | None = None
