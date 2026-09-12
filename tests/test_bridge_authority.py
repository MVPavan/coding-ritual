"""Proof that phase landing only reads closed immutable gate evidence."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tests._helpers import VALID_FIXTURE
from workflow_interpreter.bdio.records import GateRecord
from workflow_interpreter.bdio.wire import BeadRecord, GateMetadata, GateState
from workflow_interpreter.bridge.authority import (
    MSG_SHIP_GATE_AMBIGUOUS,
    MSG_SHIP_GATE_MISSING,
    MSG_SHIP_GATE_MISSING_MARK,
    MSG_SHIP_GATE_NOT_CLOSED,
    MSG_SHIP_GATE_NOT_IMMUTABLE,
    MSG_SHIP_GATE_UNDECLARED_OUTCOME,
    BeadGateAuthority,
)
from workflow_interpreter.bridge.landing import SHIP_GATE
from workflow_interpreter.schema.graph_index import build_index
from workflow_interpreter.schema.loader import load_graph
from workflow_interpreter.schema.models import BindsMode, Outcome

ROOT_ID = "bridge-root"
OTHER_ROOT_ID = "other-root"
ARTIFACT_OID = "a" * 40
TREE = "b" * 40
GATE_ID = "gate-ship"


class _Reads:
    """Return the gate records held by this deterministic in-memory read seam."""

    def __init__(self, gates: tuple[GateRecord, ...]) -> None:
        self._gates = gates

    def load_root(self, root_id):
        return SimpleNamespace(
            root_id=root_id,
            index=build_index(
                load_graph(VALID_FIXTURE).document, allow_test_flags=False
            ),
        )

    def list_gates(self, root_id: str) -> tuple[GateRecord, ...]:
        """Return every configured gate so the authority must select safely."""
        return self._gates


def _ship_gate(
    *,
    gate_id: str = GATE_ID,
    root_id: str = ROOT_ID,
    gate_node: str = SHIP_GATE,
    state: GateState = GateState.CLOSED,
    binds: BindsMode = BindsMode.IMMUTABLE,
    outcomes: tuple[Outcome, ...] = (Outcome.APPROVE, Outcome.ABANDON),
    outcome: Outcome | None = Outcome.APPROVE,
    fingerprint: str | None = "fingerprint",
    digest: str | None = "digest",
    artifact_ref: str | None = ARTIFACT_OID,
    artifact_digest: str | None = TREE,
) -> GateRecord:
    """Build a closed ship gate whose evidence fields are individually mutable."""
    metadata = GateMetadata(
        wf_root_id=root_id,
        gate_key="gate-ship",
        gate_node=gate_node,
        binds=binds,
        outcomes=outcomes,
        seq=1,
        state=state,
        outcome=outcome,
        verified_fingerprint=fingerprint,
        payload_digest=digest,
        artifact_ref=artifact_ref,
        artifact_digest=artifact_digest,
    )
    return GateRecord(
        bead=BeadRecord(
            id=gate_id,
            title=gate_node,
            status="closed",
            issue_type="task",
            metadata=metadata.model_dump(mode="json", exclude_none=True),
        ),
        metadata=metadata,
    )


def test_refuses_when_no_ship_gate_belongs_to_the_requested_root() -> None:
    """Reject a ship-shaped gate that belongs to another root."""
    authority = BeadGateAuthority(_Reads((_ship_gate(root_id=OTHER_ROOT_ID),)))

    with pytest.raises(ValueError, match=MSG_SHIP_GATE_MISSING.format(root_id=ROOT_ID)):
        authority.verify(ROOT_ID)


def test_refuses_ambiguous_ship_gate_authority() -> None:
    """Reject duplicate closed ship gates instead of choosing one evidence source."""
    authority = BeadGateAuthority(
        _Reads((_ship_gate(), _ship_gate(gate_id="gate-ship-duplicate")))
    )

    with pytest.raises(
        ValueError,
        match=MSG_SHIP_GATE_AMBIGUOUS.format(
            root_id=ROOT_ID,
            gate_ids="gate-ship,gate-ship-duplicate",
        ),
    ):
        authority.verify(ROOT_ID)


def test_refuses_a_ship_gate_that_is_not_closed() -> None:
    """Reject an open gate even when its remaining recorded fields are present."""
    authority = BeadGateAuthority(_Reads((_ship_gate(state=GateState.OPEN),)))

    with pytest.raises(
        ValueError, match=MSG_SHIP_GATE_NOT_CLOSED.format(gate_id=GATE_ID)
    ):
        authority.verify(ROOT_ID)


def test_refuses_a_ship_gate_that_is_not_immutable() -> None:
    """Reject a mutable gate even when it names closed decision evidence."""
    authority = BeadGateAuthority(_Reads((_ship_gate(binds=BindsMode.MUTABLE),)))

    with pytest.raises(
        ValueError, match=MSG_SHIP_GATE_NOT_IMMUTABLE.format(gate_id=GATE_ID)
    ):
        authority.verify(ROOT_ID)


@pytest.mark.parametrize(
    ("field", "gate"),
    (
        ("outcome", _ship_gate(outcome=None)),
        ("verified_fingerprint", _ship_gate(fingerprint=None)),
        ("payload_digest", _ship_gate(digest=None)),
        ("artifact_ref", _ship_gate(artifact_ref=None)),
        ("artifact_digest", _ship_gate(artifact_digest=None)),
    ),
)
def test_refuses_a_closed_ship_gate_missing_a_verification_mark(
    field: str, gate: GateRecord
) -> None:
    """Reject each mark that only verified closure writes together."""
    authority = BeadGateAuthority(_Reads((gate,)))

    with pytest.raises(
        ValueError,
        match=MSG_SHIP_GATE_MISSING_MARK.format(gate_id=GATE_ID, field=field),
    ):
        authority.verify(ROOT_ID)


def test_refuses_a_closed_ship_gate_with_an_undeclared_outcome() -> None:
    """Reject a recorded decision that the ship gate was never allowed to make."""
    authority = BeadGateAuthority(
        _Reads((_ship_gate(outcomes=(Outcome.APPROVE,), outcome=Outcome.ABANDON),))
    )

    with pytest.raises(
        ValueError, match=MSG_SHIP_GATE_UNDECLARED_OUTCOME.format(gate_id=GATE_ID)
    ):
        authority.verify(ROOT_ID)


def test_declared_bridge_ship_approve_authorizes_landing() -> None:
    authority = BeadGateAuthority(_Reads((_ship_gate(),)))
    assert authority.verify(ROOT_ID).accepted is True


def test_declared_abandon_does_not_authorize_landing() -> None:
    authority = BeadGateAuthority(_Reads((_ship_gate(outcome=Outcome.ABANDON),)))
    assert authority.verify(ROOT_ID).accepted is False


@pytest.mark.parametrize("change", ("outcomes", "gate-type", "approve-route"))
def test_gate_must_correspond_to_pinned_ship_declaration(monkeypatch, change):
    reads = _Reads((_ship_gate(),))
    root = reads.load_root(ROOT_ID)
    index = root.index
    ship = index.nodes["ship"]
    if change == "outcomes":
        index.nodes["ship"] = ship.model_copy(update={"outcomes": (Outcome.APPROVE,)})
    elif change == "gate-type":
        index.nodes["ship"] = ship.model_copy(update={"gate_type": None})
    else:
        document = index.document.model_copy(
            update={
                "edge": tuple(
                    edge.model_copy(update={"to": "abandoned"})
                    if edge.from_node == "ship" and edge.on is Outcome.APPROVE
                    else edge
                    for edge in index.edges
                )
            }
        )
        root.index = index.model_copy(update={"document": document})
    monkeypatch.setattr(reads, "load_root", lambda _: root)
    with pytest.raises(ValueError, match="graph-declared"):
        BeadGateAuthority(reads).verify(ROOT_ID)
