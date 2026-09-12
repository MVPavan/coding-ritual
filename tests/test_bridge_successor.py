"""Successor associations preserve P1 landing and P4 target/source authority."""

from pathlib import Path

import pytest

from tests.test_integration_lifecycle import approve_integration, entry, prepared_lab
from workflow_interpreter.bridge.adapter import PhaseAdapter
from workflow_interpreter.bridge.integration import IntegrationGuard
from workflow_interpreter.foreman.replacement import guard_bridge, replace_checked
from workflow_interpreter.schema.decisions import (
    CoordinationError,
    TrustedReplacementRequest,
)


def integration_request(tmp_path, lab, record):
    root = lab.store.reads.load_root(record.root_id)
    inputs = {}
    for item in root.metadata.instance_inputs:
        path = tmp_path / (item.name + ".txt")
        path.write_text(item.body)
        inputs[item.name] = str(path)
    graph = tmp_path / "replacement.toml"
    graph.write_text(
        Path("workflows/integration.toml")
        .read_text()
        .replace('version = "1.0.0"', 'version = "1.0.1"')
    )
    return TrustedReplacementRequest(
        request_key="replace-integration",
        reason="correct instructions",
        graph=str(graph),
        inputs=inputs,
    )


def test_changed_integration_runs_fresh_review_and_lands(
    tmp_path, monkeypatch, signing_config, sign_payload
):
    lab, owner, previous = prepared_lab(
        tmp_path, monkeypatch, signing_config, sign_payload
    )
    request = integration_request(tmp_path, lab, previous)
    receipt = replace_checked(
        lab.composition, owner.root_id, previous.integration_slot, 0, request
    )
    adapter = PhaseAdapter.from_config(lab.config.bd)
    record = adapter.record("stage")
    guard = IntegrationGuard(lab.composition)
    association = guard.binding(record)
    assert record.root_id == receipt.root_id != previous.root_id
    assert record.expected_base_commit == previous.expected_base_commit
    assert association.request.sources == guard.association(previous).request.sources
    assert association.admission.slot == previous.integration_slot
    assert record.integration_generation == 1
    assert (
        guard.claim(association.target_key)[1].association_digest
        == association.identity_digest
    )
    assert (
        replace_checked(
            lab.composition, owner.root_id, previous.integration_slot, 0, request
        )
        == receipt
    )
    with pytest.raises(CoordinationError, match="superseded"):
        guard_bridge(lab.composition, previous)
    approve_integration(lab, record)
    result = entry(lab)
    assert result.exit_code == 0, result.report
    assert adapter.show("stage").status == "closed"
    acts = lab.store.reads.list_activations(receipt.root_id)
    assert [a.metadata.node for a in acts] == ["integrate", "review"]


@pytest.mark.parametrize(
    "boundary", ["association", "claim", "prepare", "root", "admit"]
)
def test_integration_successor_crash_repaired_by_normal_stage_entry(
    tmp_path, monkeypatch, signing_config, sign_payload, boundary
):
    from workflow_interpreter.bdio.coordination import CoordinationStore
    from workflow_interpreter.foreman.replacement import repair_bridge_successor

    lab, owner, previous = prepared_lab(
        tmp_path, monkeypatch, signing_config, sign_payload
    )
    request = integration_request(tmp_path, lab, previous)
    target, method = {
        "association": (IntegrationGuard, "save"),
        "claim": (IntegrationGuard, "write_claim"),
        "prepare": (PhaseAdapter, "prepare"),
        "root": (CoordinationStore, "admit_member"),
        "admit": (PhaseAdapter, "admit"),
    }[boundary]
    original = getattr(target, method)
    tripped = False

    def crash(*args, **kwargs):
        nonlocal tripped
        result = original(*args, **kwargs)
        if not tripped:
            tripped = True
            raise RuntimeError("durable crash")
        return result

    monkeypatch.setattr(target, method, crash)
    with pytest.raises(RuntimeError, match="durable crash"):
        replace_checked(
            lab.composition, owner.root_id, previous.integration_slot, 0, request
        )
    repair_bridge_successor(lab.composition, "stage")
    record = PhaseAdapter.from_config(lab.config.bd).record("stage")
    association = IntegrationGuard(lab.composition).binding(record)
    assert association.admission.generation == 1
    assert len(lab.store.coordination_store().state(owner.root_id).reservations) == 4
    assert (
        replace_checked(
            lab.composition, owner.root_id, previous.integration_slot, 0, request
        ).root_id
        == record.root_id
    )


@pytest.mark.parametrize("mode", ["trusted", "p2"])
def test_ordinary_bridge_continues_B_A_C_with_original_CAS(
    tmp_path, monkeypatch, signing_config, sign_payload, mode
):
    from tests._supervisor import ChildScript
    from tests.test_foreman_main import _bridge_adapter, _bridge_lab, _bridge_stage
    from workflow_interpreter.bridge.admission import (
        PhaseAdmission,
        WorkflowRootProvisioner,
    )
    from workflow_interpreter.bridge.verification import VerificationPolicy
    from workflow_interpreter.foreman.resolve import instantiate
    from workflow_interpreter.schema.models import Outcome
    from workflow_interpreter.supervisor.models import SandboxMode

    graph = tmp_path / "ordinary.toml"
    graph.write_text(
        Path("workflow_interpreter/fixtures/feature-delivery.toml")
        .read_text()
        .replace(
            "[instance]",
            "[instance]\ncoordination_limits = {max_members=3, max_activations=60, max_decision_attempts=2, max_replacements=1}",
        )
    )
    if mode == "p2":
        text = graph.read_text().replace(
            'name          = "review"',
            'name          = "review"\ncontext_budget_bytes = 32000\ndecision = {triggers=["fail_plan"], actions=["replace"], replacement_input="revision", decision_task={runner="profile:critic", model="test", instructions="Decide.", verify=[{cmd="scripts/verify-feature.sh",timeout="10s"}], context_budget_bytes=16000, max_wall="30s", stale_after="10s", max_infra_retries=0, max_steers=0, max_total_activations=2}}',
        )
        text = text.replace(
            '["task_brief", "diff_artifact", "review_findings"]',
            '["task_brief", "diff_artifact", "review_findings", "revision"]',
        )
        text += '\n[[source]]\nname="revision"\nproducer="instance"\noptional=true\ntrim_priority=99\n'
        graph.write_text(text)
    lab = _bridge_lab(
        tmp_path / "lab",
        toml=graph,
        signing=signing_config,
        signer=sign_payload,
        sandbox=SandboxMode.OFF,
    )
    lab.fake_bd.rows["stage"] = _bridge_stage("stage", description="Implement feature")
    monkeypatch.setattr(
        PhaseAdapter, "from_config", classmethod(lambda *_: _bridge_adapter(lab))
    )
    adapter = _bridge_adapter(lab)
    brief = tmp_path / "brief.txt"
    brief.write_text("Implement feature")
    roots = WorkflowRootProvisioner(
        adapter,
        lambda key: instantiate(
            lab.composition,
            graph,
            instance_key=key,
            instance_inputs={"task_brief": brief},
            allow_test_flags=False,
            overrides={},
        ),
        lab.git,
        lab.repo,
    )
    previous = PhaseAdmission(
        adapter,
        roots,
        lambda: lab.git.head_commit(cwd=lab.repo),
        VerificationPolicy.pin(lab.config.bridge_checks, lab.repo),
    ).admit("phase", "stage", "refs/heads/main", lab.head)
    lab.root = lab.store.reads.load_root(previous.root_id)
    lab.profiles.bind_node(
        "implement",
        ChildScript(
            marker='{"outcome":"done"}',
            effects='{"paths":["src/feature.py"]}',
            write_path="src/feature.py",
            write_body="value = 2\n",
            commit=True,
        ),
    )
    assert lab.tick().dispatched
    assert lab.tick().settled
    from workflow_interpreter.foreman.compose import instance_head

    a = instance_head(lab.git, lab.repo, previous.root_id)
    assert a != previous.expected_base_commit
    if mode == "trusted":
        graph.write_text(
            graph.read_text().replace('version     = "1.0.0"', 'version     = "1.0.1"')
        )
        receipt = replace_checked(
            lab.composition,
            previous.root_id,
            "work",
            0,
            TrustedReplacementRequest(
                request_key="ordinary",
                reason="continue",
                graph=str(graph),
                inputs={"task_brief": str(brief)},
            ),
        )
    else:
        lab.profiles.bind_node(
            "review",
            ChildScript(marker='{"outcome":"fail_plan"}', effects='{"paths":[]}'),
        )
        lab.profiles.decision_action = "replace"
        for _ in range(20):
            lab.tick()
            state = lab.store.coordination_store().state(previous.root_id)
            if (
                state.successors
                and next(iter(state.successors.values())).state == "admitted"
            ):
                break
        assert state.successors
        receipt = next(iter(state.successors.values())).receipt
        assert receipt is not None
        assert (
            lab.store.reads.load_root(receipt.root_id).definition.content_hash
            == lab.root.definition.content_hash
        )
    successor = adapter.record("stage")
    assert successor.expected_base_commit == previous.expected_base_commit
    assert successor.execution_base_commit == a
    lab.profiles.bind_node(
        "implement",
        ChildScript(
            marker='{"outcome":"done"}',
            effects='{"paths":["src/feature.py"]}',
            write_path="src/feature.py",
            write_body="value = 3\n",
            commit=True,
        ),
    )
    lab.profiles.bind_node(
        "review", ChildScript(marker='{"outcome":"accept"}', effects='{"paths":[]}')
    )
    result = entry(lab)
    assert result.exit_code == 0, result.report
    lab.root = lab.store.reads.load_root(receipt.root_id)
    gates = lab.store.reads.list_gates(receipt.root_id)
    assert len(gates) == 1
    lab.approve(gates[0].gate_id, Outcome.APPROVE)
    result = entry(lab)
    assert result.exit_code == 0, result.report
    c = lab.git.head_commit(cwd=lab.repo)
    assert lab.git.is_ancestor(a, c, cwd=lab.repo)
    assert c != a
    assert (lab.repo / "src/feature.py").read_text() == "value = 3\n"
    assert adapter.show("stage").status == "closed"


def test_bound_source_and_authorized_candidate_refuse_replacement(
    tmp_path, monkeypatch, signing_config, sign_payload
):
    from workflow_interpreter.schema.decisions import TrustedReplacementRequest

    lab, owner, record = prepared_lab(
        tmp_path, monkeypatch, signing_config, sign_payload
    )
    source_graph = tmp_path / "writer.toml"
    with pytest.raises(CoordinationError, match="source receipt"):
        replace_checked(
            lab.composition,
            owner.root_id,
            "source",
            0,
            TrustedReplacementRequest(
                request_key="source-change", reason="too late", graph=str(source_graph)
            ),
        )
    request = integration_request(tmp_path, lab, record)
    before = lab.store.coordination_store().state(owner.root_id)
    with pytest.raises(CoordinationError, match="key conflicts"):
        replace_checked(
            lab.composition,
            owner.root_id,
            record.integration_slot,
            0,
            request.model_copy(update={"request_key": "combine"}),
        )
    assert lab.store.coordination_store().state(owner.root_id) == before
    approve_integration(lab, record)
    with pytest.raises(CoordinationError, match="human gate"):
        replace_checked(
            lab.composition, owner.root_id, record.integration_slot, 0, request
        )
    assert PhaseAdapter.from_config(lab.config.bd).record("stage") == record
    assert entry(lab).exit_code == 0


def test_successful_writer_cannot_bypass_review_in_changed_graph(
    tmp_path, monkeypatch, signing_config, sign_payload
):
    lab, owner, record = prepared_lab(
        tmp_path, monkeypatch, signing_config, sign_payload
    )
    request = integration_request(tmp_path, lab, record)
    graph = Path(request.graph)
    text = graph.read_text().replace(
        'from = "integrate"\non = "done"\nto = "review"',
        'from = "integrate"\non = "done"\nto = "ship"',
    )
    assert text != graph.read_text()
    graph.write_text(text)
    from workflow_interpreter.schema.loader import GraphValidationError

    with pytest.raises((CoordinationError, GraphValidationError)):
        replace_checked(
            lab.composition, owner.root_id, record.integration_slot, 0, request
        )
    assert PhaseAdapter.from_config(lab.config.bd).record("stage") == record


def test_trusted_integration_replays_without_graph_or_inputs(
    tmp_path, monkeypatch, signing_config, sign_payload
):
    lab, owner, record = prepared_lab(
        tmp_path, monkeypatch, signing_config, sign_payload
    )
    request = integration_request(tmp_path, lab, record)
    receipt = replace_checked(
        lab.composition, owner.root_id, record.integration_slot, 0, request
    )
    Path(request.graph).unlink()
    for path in request.inputs.values():
        Path(path).unlink()
    assert (
        replace_checked(
            lab.composition, owner.root_id, record.integration_slot, 0, request
        )
        == receipt
    )
    current = PhaseAdapter.from_config(lab.config.bd).record("stage")
    assert IntegrationGuard(lab.composition).binding(current).receipt == receipt
