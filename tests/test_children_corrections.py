"""Regressions from the grouped P2/P3 integration review."""

import subprocess
from dataclasses import replace

import pytest

from tests.test_children_process import writer_lab
from workflow_interpreter.foreman.decisions import admission_of


def test_signed_halt_resolution_unblocks_child(tmp_path, signing_config, sign_payload):
    from tests._foreman import ForemanLab
    from tests.test_children_lifecycle import FIXTURE, child_admission
    from workflow_interpreter.bdio import Outcome
    from workflow_interpreter.foreman.gates import halt_gate
    from workflow_interpreter.inspector.models import SandboxMode

    lab = ForemanLab(
        tmp_path,
        toml=FIXTURE,
        instance_inputs={},
        sandbox=SandboxMode.OFF,
        signing=signing_config,
        signer=sign_payload,
    )
    owner = lab.instantiate_resolved().root_id
    coordinator = lab.store.coordination_store(composition=lab.composition)
    child = coordinator.start_child(owner, "one", child_admission(lab, owner))
    wiring = lab.composition.for_root(child.root_id)
    with wiring.band:
        gate = wiring.store.open_gate(child.root_id, halt_gate("ceiling:20"))
    assert coordinator.drive_children(owner, 1, 0.1).children[0].attention
    lab.root = lab.store.reads.load_root(child.root_id)
    lab.approve(gate.gate_id, Outcome.ABANDON)
    result = coordinator.drive_children(owner, 1, 0.5)
    assert lab.store.reads.load_gate(gate.gate_id).status == "closed"
    assert result.children[0].state == "settled"
    assert result.children[0].attention is None


def test_recover_retries_repaired_child_runtime_failure(tmp_path):
    lab, owner, composition, spawner = writer_lab(tmp_path)
    coordinator = lab.store.coordination_store(composition=composition)
    child = coordinator.start_child(
        owner.root_id, "one", admission_of(owner, slot="one", generation=0)
    )
    # Persist a concrete runtime refusal, then repair its cause.
    from workflow_interpreter.inspector import INSTANCE_BRANCH_REF as INSTANCE_BRANCH

    branch = INSTANCE_BRANCH.format(root_id=child.root_id)
    subprocess.run(["git", "update-ref", "-d", branch], cwd=lab.repo, check=True)
    try:
        result = coordinator.drive_children(owner.root_id, 1, 0.2)
        assert result.children[0].attention
        subprocess.run(
            ["git", "update-ref", branch, lab.head], cwd=lab.repo, check=True
        )
        coordinator.recover_child(owner.root_id, "one", 0)
        result = coordinator.drive_children(owner.root_id, 1, 8)
        assert result.children[0].state == "settled", result
        assert result.children[0].attention is None
    finally:
        for process in spawner.processes:
            process.join(timeout=5)


def test_wrapper_mismatch_is_reported_without_blocking_healthy_sibling(tmp_path):
    from tests.test_children_lifecycle import child_admission, owner_lab

    lab, owner = owner_lab(tmp_path)
    coordinator = lab.store.coordination_store(composition=lab.composition)
    coordinator.start_child(owner, "bad", child_admission(lab, owner, "bad"))
    config = lab.inspector_config.model_copy(
        update={"wrapper_root": tmp_path / "other"}
    )
    other = replace(
        lab.composition,
        inspector_config=config,
        config=lab.config.model_copy(update={"inspector": config}),
    )
    other_coordinator = lab.store.coordination_store(composition=other)
    healthy = other_coordinator.start_child(
        owner, "healthy", child_admission(lab, owner, "healthy")
    )
    result = other_coordinator.drive_children(owner, 2, 0.2)
    assert "wrapper" in result.children[0].attention
    assert lab.store.reads.list_activations(healthy.root_id)
    assert coordinator.state(owner).human_attention is None


@pytest.mark.proc
def test_cancel_terminates_child_decision_process(tmp_path):
    import time

    from tests._foreman import ForemanLab, LockedPersistentBd, ProcSpawner
    from tests._inspector import ChildScript
    from tests.test_children_lifecycle import FIXTURE
    from workflow_interpreter.inspector import procfs
    from workflow_interpreter.inspector.clock import SystemClock
    from workflow_interpreter.inspector.models import Liveness, SandboxMode
    from workflow_interpreter.schema.loader import canonical_bytes

    lab = ForemanLab(
        tmp_path,
        toml=FIXTURE,
        instance_inputs={},
        sandbox=SandboxMode.OFF,
        bd_factory=lambda workspace: LockedPersistentBd(
            workspace, tmp_path / "bd.json"
        ),
    )
    owner = lab.instantiate_resolved()
    nodes = tuple(
        n.model_copy(
            update={
                "decision": n.decision.model_copy(
                    update={"actions": ("continue_declared", "human")}
                )
            }
        )
        if n.decision
        else n
        for n in owner.definition.document.node
    )
    admission = admission_of(owner, slot="one", generation=0).model_copy(
        update={
            "graph_body": canonical_bytes(
                owner.definition.document.model_copy(update={"node": nodes})
            ).decode()
        }
    )
    spawner = ProcSpawner()
    composition = replace(lab.composition, spawner=spawner, clock=SystemClock())
    spawner.bind(composition)
    lab.profiles.bind_node(
        "assess", ChildScript(marker='{"outcome":"fail_plan"}', effects='{"paths":[]}')
    )
    lab.profiles.bind_node(
        "decide",
        ChildScript(marker='{"outcome":"no_diff"}', effects='{"paths":[]}', sleep_s=30),
    )
    coordinator = lab.store.coordination_store(composition=composition)
    child = coordinator.start_child(owner.root_id, "one", admission)
    try:
        handle = None
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            coordinator.drive_children(owner.root_id, 1, 0.1)
            requests = coordinator.state(owner.root_id).requests
            decision = next((r for r in requests.values() if r.decision_root_id), None)
            if decision:
                activations = lab.store.reads.list_activations(
                    decision.decision_root_id
                )
                if activations and activations[0].metadata.handle:
                    handle = activations[0].metadata.handle
                    break
        assert handle is not None
        assert (
            procfs.prove_liveness(composition.inspector_config, handle).status
            is Liveness.ALIVE
        )
        receipt = coordinator.cancel_child(
            owner.root_id, "one", 0, "stop", "stop decision"
        )
        assert receipt.state == "cancelled"
        assert any(activations[0].activation_id in ref for ref in receipt.evidence)
        assert (
            procfs.prove_liveness(composition.inspector_config, handle).status
            is Liveness.DEAD
        )
        before = coordinator.state(owner.root_id)
        coordinator.drive_children(owner.root_id, 1, 0.1)
        assert coordinator.state(owner.root_id).requests == before.requests
        assert before.human_attention is None
        assert child.root_id != decision.decision_root_id
    finally:
        coordinator.cancel_child(owner.root_id, "one", 0, "stop", "stop decision")
        for process in spawner.processes:
            process.join(timeout=5)
