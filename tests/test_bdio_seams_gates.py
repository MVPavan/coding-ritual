"""Phase-5 gate carrier seam coverage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._bdio import entry_request, load_definition, make_root
from tests._gates import approval_payload, close, ship_gate_request
from tests._supervisor import blob_at
from tests.conftest import Signer
from tests.test_supervisor_exit import DONE_MARKER, FEATURE_FILE, Lab
from workflow_interpreter.bdio import GateArtifact
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.errors import PayloadMismatchError
from workflow_interpreter.bdio.wire import EventPayload
from workflow_interpreter.schema.models import Outcome


def test_event_payload_preserves_gate_origin_and_sequence(
    fake_store: WorkflowStore,
) -> None:
    """Catch append_event ignoring its explicit sequence or gate provenance."""
    root = make_root(fake_store, load_definition())
    payload = EventPayload(
        **{
            "from": "gate",
            "to": "review",
            "outcome": Outcome.APPROVE,
            "activation_id": "wf-gate",
            "seq": 7,
            "actor": "test",
            "origin": "gate",
            "via_gate_id": "wf-gate",
        }
    )
    event = fake_store.append_event(root.root_id, payload, seq=19)
    assert event.metadata["seq"] == 19
    assert payload.origin == "gate"
    with pytest.raises(ValueError, match="origin"):
        EventPayload(
            **{
                "from": "gate",
                "to": "review",
                "outcome": Outcome.APPROVE,
                "activation_id": "wf-gate",
                "seq": 7,
                "actor": "test",
                "origin": "gates",
            }
        )


def test_evidence_preserves_outputs_and_claimed_outcome(tmp_path: Path) -> None:
    """P9/P13: real exit production records the outputs pin and marker claim."""
    lab = Lab(tmp_path)
    lab.commit_work(FEATURE_FILE)
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE)
    artifact = lab.paths.artifacts(lab.activation.activation_id) / "report.txt"
    artifact.write_text("captured output\n", encoding="utf-8")

    observation = lab.observe()

    evidence = observation.completion.evidence
    assert evidence.outputs_ref is not None
    assert evidence.outputs_tree_oid is not None
    outputs_commit = lab.git.ref_target(evidence.outputs_ref, cwd=lab.repo)
    assert outputs_commit is not None
    assert blob_at(lab.repo, outputs_commit, "report.txt") == "captured output\n"
    assert lab.git.tree_oid(outputs_commit, cwd=lab.repo) == evidence.outputs_tree_oid
    assert evidence.claimed_outcome is Outcome.DONE


def test_immutable_gate_rejects_payload_not_matching_recorded_artifact(
    gate_store: WorkflowStore,
    sign_payload: Signer,
) -> None:
    """Catch removal of immutable commit/tree equality checks from gate approval."""
    root = make_root(gate_store, load_definition())
    source = gate_store.mint_activation(root.root_id, entry_request()).activation
    gate = gate_store.open_gate(
        root.root_id,
        ship_gate_request(
            source.activation_id, artifact_ref="a" * 40, artifact_digest="b" * 40
        ),
    )
    approval = approval_payload(
        root.root_id,
        gate,
        artifact=GateArtifact(commit_oid="a" * 40, tree_oid="d" * 40),
    )

    with pytest.raises(PayloadMismatchError, match="tree_oid"):
        close(gate_store, root.root_id, gate, approval, sign_payload)
