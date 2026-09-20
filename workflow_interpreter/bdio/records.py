"""Parsed views of a workflow row — backend-neutral identity plus its §3 carrier.

Parsing is where the carrier contract is enforced: a row that does not decode
into its declared `wf_kind` raises `CarrierIntegrityError` rather than being
skipped, because a silently ignored row is a bound that silently under-counts.

The records carry `id`, `status` and their typed metadata, never the backend
row they were parsed from: a consumer above the seam that could reach a
backend row through a record is a consumer pinned to one backend (§3.1).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Final

from pydantic import BaseModel, ValidationError

from workflow_interpreter.bdio.errors import (
    CarrierIntegrityError,
    PinnedGraphMismatchError,
)
from workflow_interpreter.bdio.keys import wake_fire_key
from workflow_interpreter.bdio.rows import StoreRow
from workflow_interpreter.bdio.wire import (
    KEY_WF_KIND,
    WIRE_MODEL,
    ActivationMetadata,
    EventMetadata,
    EventPayload,
    GateMetadata,
    Metadata,
    RootMetadata,
    WfKind,
    config_signature,
)
from workflow_interpreter.contracts.wake import CANON_WAKE, WakeEvent
from workflow_interpreter.schema.graph_index import GraphIndex, build_index
from workflow_interpreter.schema.loader import GraphValidationError, load_pinned_body
from workflow_interpreter.schema.models import GraphDefinition

_MSG_WAKE_IDENTITY: Final[str] = "wake event identity mismatch"
_MSG_EVENT_INVALID: Final[str] = "invalid event {row_id}: {reason}"

_MSG_WRONG_KIND: Final[str] = (
    "row {row_id} carries wf_kind={found!r}, expected {expected!r}"
)
_MSG_UNDECODABLE: Final[str] = (
    "row {row_id} does not decode as a {expected} carrier: {reason}"
)
_MSG_BODY_INVALID: Final[str] = (
    "root {row_id} carries a pinned body that no longer validates: {reason}"
)
_MSG_HASH_MISMATCH: Final[str] = (
    "root {row_id} pinned body hashes to {actual}, recorded {expected} — "
    "the instance halts (§3.1)"
)
_MSG_SELF_ID: Final[str] = (
    "root {row_id} carries wf_root_id={found!r}; a root carries its own id (§3)"
)


class RootRecord(BaseModel):
    """A root row with its pinned graph re-validated and hash-checked.

    Deliberately carries NO effective-bound accessor: a bound is the root's
    creation-time config ⊕ the mutations of the instance's closed rebudget
    gates (§10.4), which this object alone cannot see. A reader that had one
    here would silently answer from the config half only, which is exactly the
    reading that made a concurrent rebudget look lost. `bounds.effective_bound`
    is the single home.
    """

    model_config = WIRE_MODEL

    id: str
    status: str
    close_reason: str | None = None
    metadata: RootMetadata
    definition: GraphDefinition

    @property
    def kind(self) -> str | None:
        """The §3 discriminator this record was parsed under."""
        return WfKind.ROOT.value

    @property
    def root_id(self) -> str:
        """The instance id every other record links to."""
        return self.id

    @property
    def index(self) -> GraphIndex:
        """Node and region lookups over the pinned graph."""
        return build_index(
            self.definition.document, allow_test_flags=self.metadata.allow_test_flags
        )


class ActivationRecord(BaseModel):
    """An activation row and its §3.2 metadata."""

    model_config = WIRE_MODEL

    id: str
    status: str
    close_reason: str | None = None
    metadata: ActivationMetadata

    @property
    def kind(self) -> str | None:
        """The §3 discriminator this record was parsed under."""
        return WfKind.ACTIVATION.value

    @property
    def activation_id(self) -> str:
        """The record id."""
        return self.id


class GateRecord(BaseModel):
    """A gate row and its §3.4 metadata."""

    model_config = WIRE_MODEL

    id: str
    status: str
    close_reason: str | None = None
    metadata: GateMetadata

    @property
    def kind(self) -> str | None:
        """The §3 discriminator this record was parsed under."""
        return WfKind.GATE.value

    @property
    def gate_id(self) -> str:
        """The record id."""
        return self.id


class RowRecord(BaseModel):
    """An instance row nothing routes on: the root, an event, or an unclassified row.

    Unclassified is deliberately not a parse error. §10.3 counts a row whose
    kind cannot be read, because failing closed at the ceiling means
    over-counting and never under-counting; refusing to parse it here would
    instead make the whole instance unreadable.
    """

    model_config = WIRE_MODEL

    id: str
    status: str
    close_reason: str | None = None
    kind: str | None = None
    metadata: Metadata
    payload: str | None = None


type InstanceRecord = ActivationRecord | GateRecord | RowRecord
"""Every row of one instance, typed — what `WorkflowReads.instance_records`
hands out, so no consumer above the seam reads a backend row (§3.1)."""


class MintResult(BaseModel):
    """The outcome of `mint_activation`.

    `created = False` is the crash-safe path: the natural key already existed,
    so this tick re-found the activation instead of minting a second one
    (drill 1).
    """

    model_config = WIRE_MODEL

    activation: ActivationRecord
    idempotency_key: str
    created: bool


class CanaryResult(BaseModel):
    """The §11 startup probe's evidence for one tick, whichever backend ran it.

    `attributes` are the ledger's own identity facts — its schema version, the
    wrapper root it is pinned to, its path — already asserted when the
    connection opened; they are carried for the record, never routed on.
    """

    model_config = WIRE_MODEL

    attributes: Mapping[str, str]
    probe_row_id: str
    nonce: str


def _assert_kind(row: StoreRow, expected: WfKind) -> None:
    """Refuse a row whose discriminator is not the expected one."""
    found = row.metadata.get(KEY_WF_KIND)
    if found != expected.value:
        raise CarrierIntegrityError(
            _MSG_WRONG_KIND.format(row_id=row.id, found=found, expected=expected.value)
        )


def parse_activation(row: StoreRow) -> ActivationRecord:
    """Decode an activation row, or fail closed."""
    _assert_kind(row, WfKind.ACTIVATION)
    try:
        metadata = ActivationMetadata.model_validate(row.metadata)
    except ValidationError as exc:
        raise CarrierIntegrityError(
            _MSG_UNDECODABLE.format(
                row_id=row.id, expected=WfKind.ACTIVATION.value, reason=exc
            )
        ) from exc
    return ActivationRecord(
        id=row.id,
        status=row.status,
        close_reason=row.close_reason,
        metadata=metadata,
    )


def parse_gate(row: StoreRow) -> GateRecord:
    """Decode a gate row, or fail closed."""
    _assert_kind(row, WfKind.GATE)
    try:
        metadata = GateMetadata.model_validate(row.metadata)
    except ValidationError as exc:
        raise CarrierIntegrityError(
            _MSG_UNDECODABLE.format(
                row_id=row.id, expected=WfKind.GATE.value, reason=exc
            )
        ) from exc
    return GateRecord(
        id=row.id,
        status=row.status,
        close_reason=row.close_reason,
        metadata=metadata,
    )


def parse_root(row: StoreRow) -> RootRecord:
    """Decode a root row, re-validate its pinned body and check its hash.

    The hash is re-verified on every read (§0.4, §4 tick step 0): a corrupted
    or edited pinned body halts the instance instead of routing from a body
    nobody approved.
    """
    _assert_kind(row, WfKind.ROOT)
    try:
        metadata = RootMetadata.model_validate(row.metadata)
    except ValidationError as exc:
        raise CarrierIntegrityError(
            _MSG_UNDECODABLE.format(
                row_id=row.id, expected=WfKind.ROOT.value, reason=exc
            )
        ) from exc
    if metadata.wf_root_id != row.id:
        raise CarrierIntegrityError(
            _MSG_SELF_ID.format(row_id=row.id, found=metadata.wf_root_id)
        )
    try:
        definition = load_pinned_body(
            metadata.graph_body.encode("utf-8"),
            allow_test_flags=metadata.allow_test_flags,
        )
    except GraphValidationError as exc:
        raise PinnedGraphMismatchError(
            _MSG_BODY_INVALID.format(row_id=row.id, reason=exc)
        ) from exc
    if definition.content_hash != metadata.graph_content_hash:
        raise PinnedGraphMismatchError(
            _MSG_HASH_MISMATCH.format(
                row_id=row.id,
                actual=definition.content_hash,
                expected=metadata.graph_content_hash,
            )
        )
    if (
        metadata.config_signature is not None
        and metadata.config_signature != config_signature(metadata.resolved_config)
    ):
        raise PinnedGraphMismatchError(
            _MSG_BODY_INVALID.format(row_id=row.id, reason="config signature mismatch")
        )
    return RootRecord(
        id=row.id,
        status=row.status,
        close_reason=row.close_reason,
        metadata=metadata,
        definition=definition,
    )


def parse_row(row: StoreRow) -> RowRecord:
    """Carry a row nothing routes on across the seam, kind unparsed."""
    kind = row.metadata.get(KEY_WF_KIND)
    return RowRecord(
        id=row.id,
        status=row.status,
        close_reason=row.close_reason,
        kind=kind if isinstance(kind, str) else None,
        metadata=row.metadata,
        payload=row.payload,
    )


def parse_instance_row(row: StoreRow) -> InstanceRecord:
    """Decode one row of an instance under the kind it declares.

    The dispatch is here rather than in each consumer so that "which rows are
    activations" has exactly one answer, and so an instance read hands out
    typed records rather than backend rows (§3.1).
    """
    kind = row.metadata.get(KEY_WF_KIND)
    if kind == WfKind.ACTIVATION.value:
        return parse_activation(row)
    if kind == WfKind.GATE.value:
        return parse_gate(row)
    return parse_row(row)


def parse_event(record: RowRecord) -> EventPayload | WakeEvent:
    """Validate either event discriminator without treating notifications as routes."""
    try:
        raw = json.loads(record.payload or "null")
        if isinstance(raw, dict) and raw.get("canon") == CANON_WAKE:
            metadata = EventMetadata.model_validate(record.metadata)
            event = WakeEvent.model_validate(raw)
            if (
                event.root_id != metadata.wf_root_id
                or event.fire_key != metadata.event_key
                or event.fire_key
                != wake_fire_key(
                    event.root_id, event.instance_key, event.condition, event.cursor
                )
                or event.fired_at is None
            ):
                raise ValueError(_MSG_WAKE_IDENTITY)
            return event
        return EventPayload.model_validate(raw)
    except (ValueError, TypeError) as error:
        raise CarrierIntegrityError(
            _MSG_EVENT_INVALID.format(row_id=record.id, reason=error)
        ) from error
