"""Parsed views of a workflow bead — a bd row plus its typed §3 carrier.

Parsing is where the carrier contract is enforced: a bead that does not decode
into its declared `wf_kind` raises `CarrierIntegrityError` rather than being
skipped, because a silently ignored row is a bound that silently under-counts.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ValidationError

from workflow_interpreter.bdio.errors import (
    CarrierIntegrityError,
    PinnedGraphMismatchError,
)
from workflow_interpreter.bdio.wire import (
    KEY_WF_KIND,
    WIRE_MODEL,
    ActivationMetadata,
    BeadRecord,
    GateMetadata,
    RootMetadata,
    WfKind,
    config_signature,
)
from workflow_interpreter.schema.graph_index import GraphIndex, build_index
from workflow_interpreter.schema.loader import GraphValidationError, load_pinned_body
from workflow_interpreter.schema.models import GraphDefinition

_MSG_WRONG_KIND: Final[str] = (
    "bead {bead_id} carries wf_kind={found!r}, expected {expected!r}"
)
_MSG_UNDECODABLE: Final[str] = (
    "bead {bead_id} does not decode as a {expected} carrier: {reason}"
)
_MSG_BODY_INVALID: Final[str] = (
    "root {bead_id} carries a pinned body that no longer validates: {reason}"
)
_MSG_HASH_MISMATCH: Final[str] = (
    "root {bead_id} pinned body hashes to {actual}, recorded {expected} — "
    "the instance halts (§3.1)"
)
_MSG_SELF_ID: Final[str] = (
    "root {bead_id} carries wf_root_id={found!r}; a root carries its own id (§3)"
)


class RootRecord(BaseModel):
    """A root bead with its pinned graph re-validated and hash-checked.

    Deliberately carries NO effective-bound accessor: a bound is the root's
    creation-time config ⊕ the mutations of the instance's closed rebudget
    gates (§10.4), which this object alone cannot see. A reader that had one
    here would silently answer from the config half only, which is exactly the
    reading that made a concurrent rebudget look lost. `bounds.effective_bound`
    is the single home.
    """

    model_config = WIRE_MODEL

    bead: BeadRecord
    metadata: RootMetadata
    definition: GraphDefinition

    @property
    def root_id(self) -> str:
        """The instance id every other bead links to."""
        return self.bead.id

    @property
    def index(self) -> GraphIndex:
        """Node and region lookups over the pinned graph."""
        return build_index(
            self.definition.document, allow_test_flags=self.metadata.allow_test_flags
        )


class ActivationRecord(BaseModel):
    """An activation bead and its §3.2 metadata."""

    model_config = WIRE_MODEL

    bead: BeadRecord
    metadata: ActivationMetadata

    @property
    def activation_id(self) -> str:
        """The bead id."""
        return self.bead.id


class GateRecord(BaseModel):
    """A gate bead and its §3.4 metadata."""

    model_config = WIRE_MODEL

    bead: BeadRecord
    metadata: GateMetadata

    @property
    def gate_id(self) -> str:
        """The bead id."""
        return self.bead.id


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
    """The §11 startup canary's evidence for one tick."""

    model_config = WIRE_MODEL

    backend: str
    dolt_mode: str
    bd_version: str
    wisp_id: str
    nonce: str


def _assert_kind(bead: BeadRecord, expected: WfKind) -> None:
    """Refuse a bead whose discriminator is not the expected one."""
    found = bead.metadata.get(KEY_WF_KIND)
    if found != expected.value:
        raise CarrierIntegrityError(
            _MSG_WRONG_KIND.format(
                bead_id=bead.id, found=found, expected=expected.value
            )
        )


def parse_activation(bead: BeadRecord) -> ActivationRecord:
    """Decode an activation bead, or fail closed."""
    _assert_kind(bead, WfKind.ACTIVATION)
    try:
        metadata = ActivationMetadata.model_validate(bead.metadata)
    except ValidationError as exc:
        raise CarrierIntegrityError(
            _MSG_UNDECODABLE.format(
                bead_id=bead.id, expected=WfKind.ACTIVATION.value, reason=exc
            )
        ) from exc
    return ActivationRecord(bead=bead, metadata=metadata)


def parse_gate(bead: BeadRecord) -> GateRecord:
    """Decode a gate bead, or fail closed."""
    _assert_kind(bead, WfKind.GATE)
    try:
        metadata = GateMetadata.model_validate(bead.metadata)
    except ValidationError as exc:
        raise CarrierIntegrityError(
            _MSG_UNDECODABLE.format(
                bead_id=bead.id, expected=WfKind.GATE.value, reason=exc
            )
        ) from exc
    return GateRecord(bead=bead, metadata=metadata)


def parse_root(bead: BeadRecord) -> RootRecord:
    """Decode a root bead, re-validate its pinned body and check its hash.

    The hash is re-verified on every read (§0.4, §4 tick step 0): a corrupted
    or edited pinned body halts the instance instead of routing from a body
    nobody approved.
    """
    _assert_kind(bead, WfKind.ROOT)
    try:
        metadata = RootMetadata.model_validate(bead.metadata)
    except ValidationError as exc:
        raise CarrierIntegrityError(
            _MSG_UNDECODABLE.format(
                bead_id=bead.id, expected=WfKind.ROOT.value, reason=exc
            )
        ) from exc
    if metadata.wf_root_id != bead.id:
        raise CarrierIntegrityError(
            _MSG_SELF_ID.format(bead_id=bead.id, found=metadata.wf_root_id)
        )
    try:
        definition = load_pinned_body(
            metadata.graph_body.encode("utf-8"),
            allow_test_flags=metadata.allow_test_flags,
        )
    except GraphValidationError as exc:
        raise PinnedGraphMismatchError(
            _MSG_BODY_INVALID.format(bead_id=bead.id, reason=exc)
        ) from exc
    if definition.content_hash != metadata.graph_content_hash:
        raise PinnedGraphMismatchError(
            _MSG_HASH_MISMATCH.format(
                bead_id=bead.id,
                actual=definition.content_hash,
                expected=metadata.graph_content_hash,
            )
        )
    if (
        metadata.config_signature is not None
        and metadata.config_signature != config_signature(metadata.resolved_config)
    ):
        raise PinnedGraphMismatchError(
            _MSG_BODY_INVALID.format(
                bead_id=bead.id, reason="config signature mismatch"
            )
        )
    return RootRecord(bead=bead, metadata=metadata, definition=definition)
