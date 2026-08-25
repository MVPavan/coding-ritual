"""Shared §9 gate builders for the two gate test families (not a test module).

`test_bdio_gate_security` covers the refusal paths; `test_bdio_gate_lifecycle`
covers re-find, halt ordinals and concurrent rebudgets. Both need the same
"instance with an open gate" and "submit a signed approval" shapes, so there is
one definition of each here.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Final

from tests._bdio import SHIP, TRIAGE, entry_request, make_root
from tests.conftest import APPROVED_TEXT, PLAN_REF, Signer
from workflow_interpreter import GraphDefinition
from workflow_interpreter.bdio import (
    GateArtifact,
    GatePayload,
    canonical_payload_bytes,
)
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.records import GateRecord
from workflow_interpreter.bdio.wire import (
    BindsMode,
    GateOpenRequest,
    ResolvedSetting,
)
from workflow_interpreter.schema.models import Outcome

GRAPH_ID: Final[str] = "feature-delivery"


def approval_payload(
    root_id: str, gate: GateRecord, **overrides: object
) -> GatePayload:
    """An approval payload naming this gate of this instance."""
    base: dict[str, object] = {
        "graph_id": GRAPH_ID,
        "root_id": root_id,
        "gate_key": gate.metadata.gate_key,
        "outcome": Outcome.APPROVE,
        "artifact": GateArtifact(commit_oid="c" * 40, tree_oid="t" * 40),
        "nonce": uuid.uuid4().hex,
    }
    return GatePayload.model_validate(base | overrides)


def open_ship_gate(
    store: WorkflowStore, definition: GraphDefinition
) -> tuple[str, GateRecord]:
    """A fresh instance with its `ship` gate open on an immutable artifact."""
    root = make_root(store, definition)
    source = store.mint_activation(root.root_id, entry_request()).activation
    gate = store.open_gate(root.root_id, ship_gate_request(source.activation_id))
    return root.root_id, gate


def ship_gate_request(
    source_activation_id: str, **overrides: object
) -> GateOpenRequest:
    """The request `open_ship_gate` used — so a re-tick can present it again."""
    base: dict[str, object] = {
        "gate_node": SHIP,
        "outcomes": (Outcome.APPROVE, Outcome.ABANDON),
        "source_activation_id": source_activation_id,
        "opening_outcome": Outcome.ACCEPT,
    }
    return GateOpenRequest.model_validate(base | overrides)


def open_mutable_gate(
    store: WorkflowStore, definition: GraphDefinition
) -> tuple[str, GateRecord]:
    """A fresh instance with a `binds = "mutable"` gate over the plan document."""
    root = make_root(store, definition)
    source = store.mint_activation(root.root_id, entry_request()).activation
    gate = store.open_gate(
        root.root_id,
        ship_gate_request(
            source.activation_id,
            binds=BindsMode.MUTABLE,
            artifact_ref=PLAN_REF,
            artifact_digest=hashlib.sha256(APPROVED_TEXT).hexdigest(),
        ),
    )
    return root.root_id, gate


def open_triage_gate(
    store: WorkflowStore,
    definition: GraphDefinition,
    *overrides: ResolvedSetting,
    opening_outcome: Outcome = Outcome.FAIL_PLAN,
) -> tuple[str, GateRecord]:
    """A fresh instance with its `triage` (rebudget) gate open."""
    root = make_root(store, definition, *overrides)
    source = store.mint_activation(root.root_id, entry_request()).activation
    gate = store.open_gate(
        root.root_id,
        GateOpenRequest(
            gate_node=TRIAGE,
            outcomes=(Outcome.REBUDGET, Outcome.ABANDON),
            source_activation_id=source.activation_id,
            opening_outcome=opening_outcome,
        ),
    )
    return root.root_id, gate


def close(
    store: WorkflowStore,
    root_id: str,
    gate: GateRecord,
    approval: GatePayload,
    sign_payload: Signer,
) -> GateRecord:
    """Submit a signed approval for this gate."""
    encoded = canonical_payload_bytes(approval)
    return store.close_gate_verified(
        root_id,
        gate.gate_id,
        payload_bytes=encoded,
        signature=sign_payload(encoded, None),
    )
