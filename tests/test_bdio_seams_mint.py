"""Phase-5 mint seam coverage."""

from __future__ import annotations

import pytest

from tests._bdio import entry_request, load_definition, make_root
from tests._gates import approval_payload, close
from tests.conftest import Signer
from workflow_interpreter.bdio import ActivationRecord
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.errors import CarrierIntegrityError
from workflow_interpreter.bdio.keys import idempotency_key
from workflow_interpreter.bdio.preflight import steer_ancestor
from workflow_interpreter.bdio.wire import (
    GateOpenRequest,
    GateReason,
    MintReason,
    MintRequest,
)
from workflow_interpreter.schema.models import Outcome


def _request(**updates: object) -> MintRequest:
    """Build a minimal mint request with one optional override."""
    values: dict[str, object] = {
        "node": "implement",
        "mint_reason": MintReason.ENTRY,
        "runner_profile": "shell",
        "model": "test",
        "session_id": "session",
    }
    values.update(updates)
    return MintRequest(**values)


def test_entry_request_refuses_each_predecessor_shape() -> None:
    """Catch ENTRY validation dropping either predecessor field."""
    with pytest.raises(CarrierIntegrityError, match="entry mint has no predecessor"):
        _request(predecessor_activation_id="wf-a")
    with pytest.raises(CarrierIntegrityError, match="entry mint has no predecessor"):
        _request(predecessor_gate_id="wf-g")


def test_non_entry_request_refuses_two_predecessors() -> None:
    """Catch ambiguous activation/gate successor identity."""
    with pytest.raises(CarrierIntegrityError, match="cannot name both"):
        _request(
            mint_reason=MintReason.EDGE,
            predecessor_activation_id="wf-a",
            predecessor_gate_id="wf-g",
        )


def test_a_cyclic_retry_ancestry_stops_after_bounded_lookups(
    fake_store: WorkflowStore,
) -> None:
    """P6: a malformed A→B→A retry chain must not repeatedly read bd."""
    root = make_root(fake_store, load_definition())
    seed = fake_store.mint_activation(root.root_id, entry_request()).activation

    def retry(activation_id: str, predecessor_id: str) -> ActivationRecord:
        return seed.model_copy(
            update={
                "bead": seed.bead.model_copy(update={"id": activation_id}),
                "metadata": seed.metadata.model_copy(
                    update={
                        "mint_reason": MintReason.INFRA_RETRY,
                        "predecessor_activation_id": predecessor_id,
                    }
                ),
            }
        )

    records = {"a": retry("a", "b"), "b": retry("b", "a")}
    lookups = 0

    class CyclicReads:
        def load_activation(self, activation_id: str) -> ActivationRecord:
            nonlocal lookups
            lookups += 1
            if lookups > 3:
                raise AssertionError("cyclic lookup did not stop")
            return records[activation_id]

    request = _request(
        mint_reason=MintReason.INFRA_RETRY, predecessor_activation_id="a"
    )

    assert steer_ancestor(CyclicReads(), request) is None
    assert lookups == 2


def test_gate_predecessor_halt_inherits_its_round(
    gate_store: WorkflowStore, sign_payload: Signer
) -> None:
    """Catch gate-only mints being resolved as missing activations or re-rounded."""
    store = gate_store
    root = make_root(store, load_definition())
    gate = store.open_gate(
        root.root_id,
        GateOpenRequest(
            gate_node="triage",
            outcomes=(Outcome.REBUDGET, Outcome.ABANDON),
            gate_reason=GateReason.HALT,
            region="build-review",
            round_no=4,
            halt_reason="dead end",
        ),
    )
    closed = close(
        store,
        root.root_id,
        gate,
        approval_payload(root.root_id, gate, outcome=Outcome.ABANDON),
        sign_payload,
    )

    minted = store.mint_activation(
        root.root_id,
        entry_request(
            mint_reason=MintReason.EDGE,
            predecessor_gate_id=closed.gate_id,
        ),
    ).activation

    assert minted.metadata.predecessor_gate_id == closed.gate_id
    assert minted.metadata.round_no == 4
    assert minted.metadata.outcome_taken is Outcome.ABANDON
    assert minted.metadata.idempotency_key == idempotency_key(
        root.root_id, closed.gate_id, Outcome.ABANDON, "implement"
    )


@pytest.mark.parametrize(
    ("region", "round_no"), (("another-region", 4), ("build-review", None))
)
def test_gate_predecessor_refuses_another_region_or_missing_round(
    gate_store: WorkflowStore, sign_payload: Signer, region: str, round_no: int | None
) -> None:
    """P1 refuses gate metadata that cannot derive this target's round."""
    root = make_root(gate_store, load_definition())
    gate = gate_store.open_gate(
        root.root_id,
        GateOpenRequest(
            gate_node="triage",
            outcomes=(Outcome.REBUDGET, Outcome.ABANDON),
            gate_reason=GateReason.HALT,
            region=region,
            round_no=round_no,
            halt_reason="dead end",
        ),
    )
    closed = close(
        gate_store,
        root.root_id,
        gate,
        approval_payload(root.root_id, gate, outcome=Outcome.ABANDON),
        sign_payload,
    )

    with pytest.raises(CarrierIntegrityError, match="region or round"):
        gate_store.mint_activation(
            root.root_id,
            entry_request(
                mint_reason=MintReason.EDGE, predecessor_gate_id=closed.gate_id
            ),
        )


def test_transition_gate_into_entry_opens_next_round(
    gate_store: WorkflowStore, sign_payload: Signer
) -> None:
    """Catch transition gate arrivals inheriting instead of opening a round."""
    store = gate_store
    root = make_root(store, load_definition())
    source = store.mint_activation(root.root_id, entry_request()).activation
    gate = store.open_gate(
        root.root_id,
        GateOpenRequest(
            gate_node="triage",
            outcomes=(Outcome.REBUDGET, Outcome.ABANDON),
            source_activation_id=source.activation_id,
            opening_outcome=Outcome.FAIL_PLAN,
            region="build-review",
            round_no=1,
        ),
    )
    closed = close(
        store,
        root.root_id,
        gate,
        approval_payload(root.root_id, gate, outcome=Outcome.ABANDON),
        sign_payload,
    )

    minted = store.mint_activation(
        root.root_id,
        entry_request(
            mint_reason=MintReason.EDGE,
            predecessor_gate_id=closed.gate_id,
        ),
    ).activation

    assert minted.metadata.round_no == 2
    with pytest.raises(CarrierIntegrityError, match="requires its predecessor"):
        store.mint_activation(
            root.root_id,
            entry_request(
                mint_reason=MintReason.INFRA_RETRY,
                predecessor_gate_id=closed.gate_id,
            ),
        )


def test_gate_predecessor_must_be_closed_verified_and_edge(
    fake_store: WorkflowStore,
) -> None:
    """Catch an unverified gate or non-edge reason crossing the mint seam."""
    store = fake_store
    root = make_root(store, load_definition())
    source = store.mint_activation(root.root_id, entry_request()).activation
    gate = store.open_gate(
        root.root_id,
        GateOpenRequest(
            gate_node="triage",
            outcomes=(Outcome.REBUDGET, Outcome.ABANDON),
            source_activation_id=source.activation_id,
            opening_outcome=Outcome.FAIL_PLAN,
            region="build-review",
            round_no=1,
        ),
    )
    with pytest.raises(CarrierIntegrityError, match="not verified closed"):
        store.mint_activation(
            root.root_id,
            entry_request(
                mint_reason=MintReason.EDGE, predecessor_gate_id=gate.gate_id
            ),
        )
