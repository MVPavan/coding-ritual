"""C2b audit contracts against real pinned records."""

from tests._bdio import (
    CLOSE,
    UPDATE,
    StoreWrites,
    entry_request,
    load_definition,
    make_root,
    seed_row,
)
from workflow_interpreter.bdio import Outcome
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.foreman.audit import audit
from workflow_interpreter.foreman.gates import halt_gate
from workflow_interpreter.ledger.store import LedgerStore


def test_audit_accepts_the_real_empty_instance(fake_store: WorkflowStore) -> None:
    root = make_root(fake_store, load_definition())
    assert (
        audit(root, fake_store.reads.instance_records(root.root_id)).violation is None
    )


def test_audit_reports_an_unverified_closed_gate_without_writing(
    fake_store: WorkflowStore, fake_client: LedgerStore
) -> None:
    root = make_root(fake_store, load_definition())
    gate = fake_store.open_gate(root.root_id, halt_gate("ceiling:20"))
    fake_client._merge_metadata(gate.gate_id, {"state": "closed"})
    writes = StoreWrites(fake_client)
    before_updates = writes.count(UPDATE)
    before_closes = writes.count(CLOSE)

    result = audit(root, fake_store.reads.instance_records(root.root_id))

    assert result.violation == "gate_close_unverified"
    assert writes.count(UPDATE) == before_updates
    assert writes.count(CLOSE) == before_closes


def test_audit_reports_two_unconsumed_completed_heads(
    fake_store: WorkflowStore, fake_client: LedgerStore
) -> None:
    root = make_root(fake_store, load_definition())
    first = fake_store.mint_activation(root.root_id, entry_request()).activation
    closed = fake_store.close_activation(first.activation_id, Outcome.DONE)
    # A second completed head under one root: a DIFFERENT idempotency key, so
    # the §3.3 mint would have written it rather than answering with the
    # first, which is exactly the residue the audit exists to name.
    seed_row(
        fake_client,
        "wf activation duplicate head",
        dict(closed.metadata.model_dump(mode="json"))
        | {"idempotency_key": "conflicting-head"},
    )

    result = audit(root, fake_store.reads.instance_records(root.root_id))

    assert result.violation == "more than one unconsumed routing head"
