"""Phase-5 bounds seam coverage."""

from __future__ import annotations

import pytest

from tests._bdio import entry_request, handle, load_definition, make_root, run_to_close
from workflow_interpreter.bdio import Deviation, ExitRecord, MintReason, Outcome
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.bounds import consecutive_infra_closes
from workflow_interpreter.bdio.constants import (
    DEVIATION_BOUND_VIOLATED,
    DEVIATION_INPUTS_UNAVAILABLE,
    DEVIATION_PRECONDITION_REFUSED,
    DEVIATION_SANDBOX_UNAVAILABLE,
)
from workflow_interpreter.bdio.mint import views_of


@pytest.mark.parametrize(
    "kind",
    (
        DEVIATION_PRECONDITION_REFUSED,
        DEVIATION_INPUTS_UNAVAILABLE,
        DEVIATION_SANDBOX_UNAVAILABLE,
        DEVIATION_BOUND_VIOLATED,
    ),
)
def test_an_exempt_refusal_neither_counts_nor_breaks_an_infra_run(
    fake_store: WorkflowStore, kind: str
) -> None:
    """Catch removal of P14's skip from the trailing infra-close predicate.

    Both exempt kinds close `error_transport` and both route to a halt gate,
    so neither may spend a `(node, round)` retry slot on its way there.
    """
    root = make_root(fake_store, load_definition())
    first = fake_store.mint_activation(root.root_id, entry_request()).activation
    run_to_close(fake_store, first.activation_id, Outcome.ERROR_TRANSPORT)
    refused = fake_store.mint_activation(
        root.root_id,
        entry_request(
            mint_reason=MintReason.INFRA_RETRY,
            predecessor_activation_id=first.activation_id,
        ),
    ).activation
    fake_store.record_dispatch(refused.activation_id, handle())
    fake_store.record_exit(
        refused.activation_id,
        ExitRecord(exit_code=1, ended_at="2026-08-25T00:01:00Z", reason="x"),
    )
    fake_store.close_activation(
        refused.activation_id,
        Outcome.ERROR_TRANSPORT,
        deviations=(
            Deviation(
                kind=kind,
                reason="human work",
                recorded_at="2026-08-25T00:01:00Z",
            ),
        ),
    )
    last = fake_store.mint_activation(
        root.root_id,
        entry_request(
            mint_reason=MintReason.INFRA_RETRY,
            predecessor_activation_id=refused.activation_id,
        ),
    ).activation
    run_to_close(fake_store, last.activation_id, Outcome.ERROR_TRANSPORT)

    activations = fake_store.reads.list_activations(root.root_id)
    assert consecutive_infra_closes(views_of(activations), "implement", 1) == 2
