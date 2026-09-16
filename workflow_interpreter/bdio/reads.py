"""The §4 read vocabulary — every query the write API issues.

Free functions over a `StoreBackend`, so the write operations in `api.py` and
`gates.py` share exactly one definition of each query. Two rules hold
throughout:

- **Never "all rows".** Every read selects by `wf_root_id` (or `wf_kind`) —
  a bd workspace nested inside another repo's workspace leaks the outer
  project's beads into read paths (probed 2026-08-25).
- **Never timestamps.** Ordering is the foreman-assigned `seq`; bd stores
  second-granularity timestamps in read paths, so two beads of one tick are
  indistinguishable by time (§3.2).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Final

from pydantic import JsonValue

from workflow_interpreter.bdio import bounds
from workflow_interpreter.bdio.backend import StoreBackend
from workflow_interpreter.bdio.carriers import JSON_SAFE_INT_LIMIT
from workflow_interpreter.bdio.records import (
    ActivationRecord,
    GateRecord,
    InstanceRecord,
    RootRecord,
    RowRecord,
    parse_activation,
    parse_event,
    parse_gate,
    parse_instance_row,
    parse_root,
    parse_row,
)
from workflow_interpreter.bdio.rows import RowKind, RowQuery, StoreRow
from workflow_interpreter.bdio.wire import (
    KEY_EVENT_KEY,
    KEY_GATE_KEY,
    KEY_IDEMPOTENCY_KEY,
    KEY_INSTANCE_KEY,
    KEY_NONCE,
    KEY_SEQ,
    KEY_WF_KIND,
    KEY_WF_ROOT_ID,
    BoundSetting,
    WfKind,
)
from workflow_interpreter.contracts.wake import WakeEvent

FIRST_SEQ: Final[int] = 1


def load_root(client: StoreBackend, root_id: str) -> RootRecord:
    """Read a root and re-verify its pinned body's hash (§3.1, §4 tick step 0)."""
    return parse_root(client.get_row(root_id))


def load_activation(client: StoreBackend, activation_id: str) -> ActivationRecord:
    """Read one activation through the carrier contract."""
    return parse_activation(client.get_row(activation_id))


def load_gate(client: StoreBackend, gate_id: str) -> GateRecord:
    """Read one gate through the carrier contract."""
    return parse_gate(client.get_row(gate_id))


def find_roots(client: StoreBackend, instance_key: str) -> tuple[StoreRow, ...]:
    """Every root row carrying `instance_key` — more than one is race residue.

    Ordered by row id, so the §3.2 convergence rule (lowest id survives) reads
    the same from any tick that finds the duplicates.
    """
    found = client.find_rows(
        RowQuery(
            metadata_filters={
                KEY_WF_KIND: WfKind.ROOT.value,
                KEY_INSTANCE_KEY: instance_key,
            }
        )
    )
    return tuple(sorted(found, key=lambda row: row.id))


def roots_by_instance_key(
    client: StoreBackend, instance_key: str
) -> tuple[RowRecord, ...]:
    """Every root row carrying `instance_key`, as identity only.

    The pinned body is deliberately NOT re-validated: a caller asking whether
    a root exists for a bridge identity must get an answer even when that
    root's create/self-link pair was interrupted, and it must get it without
    naming a backend row (§3.1).
    """
    return tuple(parse_row(row) for row in find_roots(client, instance_key))


def list_roots(client: StoreBackend) -> tuple[RootRecord, ...]:
    """Every root row in the store, in row-id order (§4 'Load roots').

    A stateless tick has to DISCOVER its instances before it can load one, and
    without this the only way in was to import package internals (probed,
    phase-2 r3). Superseded roots are included: a tick that finds one needs to
    see the convergence, not a gap.
    """
    rows = client.find_rows(RowQuery(metadata_filters={KEY_WF_KIND: WfKind.ROOT.value}))
    return tuple(parse_root(row) for row in sorted(rows, key=lambda row: row.id))


def instance_rows(client: StoreBackend, root_id: str) -> tuple[StoreRow, ...]:
    """Every row of the instance, untyped — identity and carrier only."""
    return client.find_rows(RowQuery(metadata_filters={KEY_WF_ROOT_ID: root_id}))


def owns_instance_rows(client: StoreBackend, root_id: str) -> bool:
    """Whether any row of the instance other than the root itself links to it.

    Deliberately over untyped rows: ownership decides which duplicate root
    survives convergence (§3.2), and a malformed sibling row is exactly the
    residue that decision exists to clean up. Parsing every carrier here would
    make one unreadable row block the convergence.
    """
    return any(row.id != root_id for row in instance_rows(client, root_id))


def next_instance_seq(client: StoreBackend, root_id: str) -> int:
    """The next per-instance `seq`, read without parsing any carrier (§3.2).

    Same reason as `owns_instance_rows`: allocating the next sequence needs
    the numbers the rows carry, not their meaning, and an event backfill must
    not be blocked by a sibling row that no longer decodes.
    """
    return _next_seq_of_rows(instance_rows(client, root_id))


def _json_safe_seq(value: JsonValue | None) -> int | None:
    """A row's `seq` when it is an exact `JsonSafeInt`, else nothing.

    `bool` is an `int` in Python, and an integer past the JSON-safe bound was
    already rounded by the time it is read back (`carriers.JsonSafeInt`), so
    either one would allocate a successor no write could carry. Both are
    skipped exactly as an undecodable sibling row is.
    """
    if not isinstance(value, int) or isinstance(value, bool):
        return None
    if -JSON_SAFE_INT_LIMIT <= value <= JSON_SAFE_INT_LIMIT:
        return value
    return None


def _next_seq_of_rows(rows: Sequence[StoreRow]) -> int:
    """The successor of the highest valid `seq` any of these rows carries."""
    seen = [
        seq
        for row in rows
        if (seq := _json_safe_seq(row.metadata.get(KEY_SEQ))) is not None
    ]
    return max(seen, default=FIRST_SEQ - 1) + 1


def instance_records(client: StoreBackend, root_id: str) -> tuple[InstanceRecord, ...]:
    """Every row of the instance, typed — root, activations, gates and events (§4).

    The root itself is included: it carries its own `wf_root_id`, and both the
    §10.3 count and the `seq` allocation are defined over everything the
    selector returns.
    """
    return tuple(parse_instance_row(row) for row in instance_rows(client, root_id))


def list_activations(
    client: StoreBackend, root_id: str
) -> tuple[ActivationRecord, ...]:
    """Every activation of the instance, in `seq` order."""
    rows = client.find_rows(
        RowQuery(
            metadata_filters={
                KEY_WF_ROOT_ID: root_id,
                KEY_WF_KIND: WfKind.ACTIVATION.value,
            }
        )
    )
    return _ordered(parse_activation(row) for row in rows)


def list_gates(client: StoreBackend, root_id: str) -> tuple[GateRecord, ...]:
    """Every gate row of the instance, in `seq` order."""
    rows = client.find_rows(
        RowQuery(
            metadata_filters={
                KEY_WF_ROOT_ID: root_id,
                KEY_WF_KIND: WfKind.GATE.value,
            }
        )
    )
    return _ordered(parse_gate(row) for row in rows)


def find_by_idempotency_key(
    client: StoreBackend, root_id: str, idempotency_key: str
) -> tuple[ActivationRecord, ...]:
    """The §4 idempotency lookup — 0 or 1 row; more is race residue (§3.2).

    Closed activations are included (the read never filters by status): a key
    whose activation already ran must still be found, or a re-tick mints a
    duplicate.
    """
    rows = client.find_rows(
        RowQuery(
            metadata_filters={
                KEY_WF_ROOT_ID: root_id,
                KEY_WF_KIND: WfKind.ACTIVATION.value,
                KEY_IDEMPOTENCY_KEY: idempotency_key,
            }
        )
    )
    return tuple(parse_activation(row) for row in rows)


def find_gate(client: StoreBackend, root_id: str, gate_key: str) -> GateRecord | None:
    """The gate carrying `gate_key`, if this key was already opened (§3.4).

    Ordered by row id like `find_roots` and the §3.2 race rule: a key should
    have exactly one gate, and when residue makes it two, every tick must
    re-find the SAME one rather than whichever row the store listed first.
    """
    rows = sorted(
        client.find_rows(
            RowQuery(
                metadata_filters={
                    KEY_WF_ROOT_ID: root_id,
                    KEY_WF_KIND: WfKind.GATE.value,
                    KEY_GATE_KEY: gate_key,
                }
            )
        ),
        key=lambda row: row.id,
    )
    return parse_gate(rows[0]) if rows else None


def find_event(client: StoreBackend, root_id: str, event_key: str) -> RowRecord | None:
    """The event row carrying `event_key`, so backfill cannot duplicate (§3.3)."""
    rows = client.find_rows(
        RowQuery(
            metadata_filters={
                KEY_WF_ROOT_ID: root_id,
                KEY_WF_KIND: WfKind.EVENT.value,
                KEY_EVENT_KEY: event_key,
            },
            kind=RowKind.EVENT,
        )
    )
    return parse_row(rows[0]) if rows else None


def list_wake_events(client: StoreBackend, root_id: str) -> tuple[WakeEvent, ...]:
    """Read notifications independently of transition event backfill."""
    rows = client.find_rows(
        RowQuery(
            metadata_filters={
                KEY_WF_ROOT_ID: root_id,
                KEY_WF_KIND: WfKind.EVENT.value,
            },
            kind=RowKind.EVENT,
        )
    )
    return tuple(
        event
        for record in sorted(map(parse_row, rows), key=lambda item: item.id)
        if record.payload is not None
        and isinstance(event := parse_event(record), WakeEvent)
    )


def rows_with_nonce(
    client: StoreBackend, root_id: str, nonce: str
) -> tuple[StoreRow, ...]:
    """Instance rows that already recorded `nonce` — the §9 replay check."""
    return client.find_rows(
        RowQuery(metadata_filters={KEY_WF_ROOT_ID: root_id, KEY_NONCE: nonce})
    )


def _seq_of(record: InstanceRecord) -> int | None:
    """The §3.2 sequence a record carries, or `None` when it carries none."""
    if isinstance(record, ActivationRecord | GateRecord):
        return record.metadata.seq
    value = record.metadata.get(KEY_SEQ)
    return value if isinstance(value, int) else None


def next_seq(records: Sequence[InstanceRecord]) -> int:
    """The next per-instance `seq` (§3.2) — never derived from a timestamp."""
    seen = [seq for record in records if (seq := _seq_of(record)) is not None]
    return max(seen, default=FIRST_SEQ - 1) + 1


def activations_of(records: Sequence[InstanceRecord]) -> tuple[ActivationRecord, ...]:
    """The activations among already-fetched instance records, in `seq` order.

    A mint needs both the ceiling count (all records) and the activation views
    (§10.1/§10.2 counting); deriving the second from the first keeps one
    round-trip per mint instead of two.
    """
    return _ordered(
        record for record in records if isinstance(record, ActivationRecord)
    )


def gates_of(records: Sequence[InstanceRecord]) -> tuple[GateRecord, ...]:
    """The gates among already-fetched instance records, in `seq` order.

    Same motive as `activations_of`: a mint and a gate-open both need the
    ceiling count (all records) AND the closed rebudget gates the §10.4
    effective bound is computed from, and one fetch serves both.
    """
    return _ordered(record for record in records if isinstance(record, GateRecord))


def effective_bound(
    client: StoreBackend, root_id: str, setting: BoundSetting, scope: str = ""
) -> int | None:
    """The §10.4 bound in force for this instance: config ⊕ closed rebudgets."""
    return bounds.effective_bound(
        load_root(client, root_id), list_gates(client, root_id), setting, scope
    )


def _ordered[RecordT: (ActivationRecord, GateRecord)](
    records: Iterable[RecordT],
) -> tuple[RecordT, ...]:
    """Sort parsed records by `(seq, bead id)` — a total, deterministic order."""
    return tuple(sorted(records, key=lambda record: (record.metadata.seq, record.id)))


class WorkflowReads:
    """The §4 read vocabulary as an object — the ONLY handle a caller gets.

    `WorkflowStore` hands this out instead of the transport. It carries no
    write method at all, so "read bd directly" can no longer be one refactor
    away from "close a gate without verifying it" (§0.1).
    """

    def __init__(self, client: StoreBackend) -> None:
        self._client = client

    def load_root(self, root_id: str) -> RootRecord:
        """Read a root and re-verify its pinned body's hash (§3.1)."""
        return load_root(self._client, root_id)

    def roots_by_instance_key(self, instance_key: str) -> tuple[RowRecord, ...]:
        """Every root row carrying `instance_key` — more than one is residue."""
        return roots_by_instance_key(self._client, instance_key)

    def list_roots(self) -> tuple[RootRecord, ...]:
        """Every root bead in the workspace, in bead-id order (§4 'Load roots')."""
        return list_roots(self._client)

    def load_activation(self, activation_id: str) -> ActivationRecord:
        """Read one activation through the carrier contract."""
        return load_activation(self._client, activation_id)

    def load_gate(self, gate_id: str) -> GateRecord:
        """Read one gate through the carrier contract."""
        return load_gate(self._client, gate_id)

    def owns_instance_rows(self, root_id: str) -> bool:
        """Whether any row of the instance other than the root links to it."""
        return owns_instance_rows(self._client, root_id)

    def next_instance_seq(self, root_id: str) -> int:
        """The next per-instance `seq`, allocated without parsing carriers."""
        return next_instance_seq(self._client, root_id)

    def instance_records(self, root_id: str) -> tuple[InstanceRecord, ...]:
        """Every row of the instance, typed and selected by `wf_root_id` (§4)."""
        return instance_records(self._client, root_id)

    def list_activations(self, root_id: str) -> tuple[ActivationRecord, ...]:
        """Every activation of the instance, in `seq` order."""
        return list_activations(self._client, root_id)

    def list_gates(self, root_id: str) -> tuple[GateRecord, ...]:
        """Every gate bead of the instance, in `seq` order."""
        return list_gates(self._client, root_id)

    def effective_bound(
        self, root_id: str, setting: BoundSetting, scope: str = ""
    ) -> int | None:
        """The §10.4 bound in force: creation config ⊕ closed rebudget gates.

        The ONE reader a caller gets, so "what is the bound" cannot be answered
        from the root bead alone — which would miss every rebudget.
        """
        return effective_bound(self._client, root_id, setting, scope)

    def find_by_idempotency_key(
        self, root_id: str, idempotency_key: str
    ) -> tuple[ActivationRecord, ...]:
        """The §4 idempotency lookup — 0 or 1 bead; more is race residue (§3.2)."""
        return find_by_idempotency_key(self._client, root_id, idempotency_key)

    def find_gate(self, root_id: str, gate_key: str) -> GateRecord | None:
        """The gate carrying `gate_key`, if this key was already opened (§3.4)."""
        return find_gate(self._client, root_id, gate_key)

    def find_event(self, root_id: str, event_key: str) -> RowRecord | None:
        """The event row carrying `event_key` (§3.3)."""
        return find_event(self._client, root_id, event_key)

    def list_wake_events(self, root_id: str) -> tuple[WakeEvent, ...]:
        """Return typed notification evidence without interpreting it as routing."""
        return list_wake_events(self._client, root_id)
