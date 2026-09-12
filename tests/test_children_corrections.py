"""Regressions from the grouped P2/P3 integration review."""

import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from tests.test_children_process import writer_lab
from workflow_interpreter.bdio import BdConfig, WorkflowStore
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.foreman.decisions import admission_of
from workflow_interpreter.foreman.resolve import instantiate
from workflow_interpreter.supervisor.band import BandLock


@pytest.mark.bd
def test_standard_beads_checkout_stays_clean_with_coordination_locks(
    tmp_path: Path,
) -> None:
    lab, _owner, composition, _spawner = writer_lab(tmp_path)
    subprocess.run(
        ["bd", "init", "--prefix", "wf", "--non-interactive"],
        cwd=lab.repo,
        check=True,
        capture_output=True,
        timeout=30,
    )
    # Commit only the initialization files in this throwaway consumer repository.
    files = (
        subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=lab.repo
        )
        .decode()
        .split("\0")[:-1]
    )
    if files:
        subprocess.run(
            ["git", "add", "--", *files], cwd=lab.repo, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-qm", "initialize Beads"],
            cwd=lab.repo,
            check=True,
            capture_output=True,
        )
    config = BdConfig(workspace=lab.repo, actor="test")
    store = WorkflowStore(BdClient(config))
    composition = replace(
        composition,
        store=store,
        config=composition.config.model_copy(update={"bd": config}),
    )
    owner = instantiate(
        composition,
        tmp_path / "writer.toml",
        instance_key="standard-owner",
        instance_inputs={},
        allow_test_flags=False,
        overrides={},
    )
    coordinator = store.coordination_store(composition=composition)
    child = coordinator.start_child(
        owner.root_id, "one", admission_of(owner, slot="one", generation=0)
    )
    with BandLock(coordinator.member_lock_path(child.root_id)):
        pass
    coordinator.cancel_child(owner.root_id, "one", 0, "stop", "finished")
    coordinator.drive_children(owner.root_id, 1, 0.1)
    assert lab.git.status_paths(cwd=lab.repo) == ()
    alias = tmp_path / "alias"
    alias.symlink_to(lab.repo, target_is_directory=True)
    alias_store = WorkflowStore(
        BdClient(config.model_copy(update={"workspace": alias}))
    )
    for purpose in ("band", "launch", "drive"):
        assert alias_store.coordination_store().member_lock_path(
            child.root_id, purpose
        ) == coordinator.member_lock_path(child.root_id, purpose)
    lock_area = lab.repo / ".beads" / "coordination"
    assert (lock_area / f"{owner.root_id}.lock").exists()
    assert coordinator.member_lock_path(owner.root_id, "drive").is_relative_to(
        lock_area
    )


def test_legacy_lock_namespace_requires_explicit_offline_migration(
    tmp_path: Path,
) -> None:
    from tests.test_children_lifecycle import owner_lab
    from workflow_interpreter.schema.decisions import CoordinationError

    lab, owner = owner_lab(tmp_path)
    legacy = lab.config.bd.workspace / ".wf-coordination" / f"{owner}.drive.lock"
    with BandLock(legacy), pytest.raises(CoordinationError, match="legacy"):
        lab.store.coordination_store().member_lock_path(owner, "drive")
    assert legacy.exists()


def test_signed_halt_resolution_unblocks_child(tmp_path, signing_config, sign_payload):
    from tests._foreman import ForemanLab
    from tests.test_children_lifecycle import FIXTURE, child_admission
    from workflow_interpreter.bdio import Outcome
    from workflow_interpreter.foreman.gates import halt_gate
    from workflow_interpreter.supervisor.models import SandboxMode

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
    assert lab.store.reads.load_gate(gate.gate_id).bead.status == "closed"
    assert result.children[0].state == "settled"
    assert result.children[0].attention is None


def test_recover_retries_repaired_child_runtime_failure(tmp_path):
    lab, owner, composition, spawner = writer_lab(tmp_path)
    coordinator = lab.store.coordination_store(composition=composition)
    child = coordinator.start_child(
        owner.root_id, "one", admission_of(owner, slot="one", generation=0)
    )
    # Persist a concrete runtime refusal, then repair its cause.
    from workflow_interpreter.supervisor import INSTANCE_BRANCH_REF as INSTANCE_BRANCH

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
    config = lab.supervisor_config.model_copy(
        update={"wrapper_root": tmp_path / "other"}
    )
    other = replace(
        lab.composition,
        supervisor_config=config,
        config=lab.config.model_copy(update={"supervisor": config}),
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
    from tests._supervisor import ChildScript
    from tests.test_children_lifecycle import FIXTURE
    from workflow_interpreter.schema.loader import canonical_bytes
    from workflow_interpreter.supervisor import procfs
    from workflow_interpreter.supervisor.clock import SystemClock
    from workflow_interpreter.supervisor.models import Liveness, SandboxMode

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
            procfs.prove_liveness(composition.supervisor_config, handle).status
            is Liveness.ALIVE
        )
        receipt = coordinator.cancel_child(
            owner.root_id, "one", 0, "stop", "stop decision"
        )
        assert receipt.state == "cancelled"
        assert any(activations[0].activation_id in ref for ref in receipt.evidence)
        assert (
            procfs.prove_liveness(composition.supervisor_config, handle).status
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
