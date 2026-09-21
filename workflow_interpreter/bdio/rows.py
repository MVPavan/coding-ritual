"""The neutral vocabulary of the store seam — rows, queries, writes, identity.

`LedgerStore` speaks these types and nothing else: an id, a status, a carrier,
and for an event row its payload. They outlived the protocol they were written
for (R1) because they are still the vocabulary the typed operations in this
package are expressed in — a row, a query, a write, a gate closure taken whole.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, Field

from workflow_interpreter.bdio.wire import ROW_MODEL, Metadata

STATUS_CLOSED: Final[str] = "closed"
STATUS_OPEN: Final[str] = "open"
"""A row's two durable statuses, in the neutral vocabulary (§3.1)."""


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


class GateSignature(BaseModel):
    """The historical trust an approval was accepted under (§3.6, D21).

    The bytes alone are not re-verifiable: verification depends on the
    allow-list of the moment, so the entry that matched and the policy in
    force travel WITH the signature. A backend with nowhere to put them keeps
    them out of its rows; it does not get to pretend it stored them.
    """

    model_config = ROW_MODEL

    payload_bytes: bytes
    signature_bytes: bytes
    signer_fingerprint: str
    allowed_signers_entry: str
    policy: Metadata


class GateClosure(BaseModel):
    """One gate close as the seam states it — the whole decision, at once.

    §3.3 makes a gate close ONE atomic operation: the nonce is consumed, the
    state and outcome are set, the signature is recorded and the attention
    projection is enqueued together, or none of it happens. Expressed as a
    single write so a backend that can transact does exactly that, rather than
    receiving the four parts as four calls it cannot join.
    """

    model_config = ROW_MODEL

    gate_id: str
    metadata: Metadata
    close_reason: str
    nonce: str | None = None
    signature: GateSignature | None = None


RowGuard = Callable[[StoreRow], None]
"""Re-checks a row inside the writing backend, raising to abandon the write.

A backend that can hold the read and the write in ONE transaction (the
ledger) evaluates this against the row it is about to change, which is what
makes §3.3's "read, check allowed, write version+1" atomic. A backend that
cannot transact (bd) does not evaluate it: its caller already re-read and
re-checked as close to the write as bd allows (`transitions.apply`), and a
second read there would only add a round-trip per transition."""
