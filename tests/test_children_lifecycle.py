"""Independent children use the existing owner ledger and immutable pins."""

from pathlib import Path

import pytest

from tests._foreman import ForemanLab
from workflow_interpreter.foreman.decisions import admission_of
from workflow_interpreter.schema.decisions import CoordinationError
from workflow_interpreter.supervisor.models import SandboxMode

FIXTURE = Path("workflow_interpreter/fixtures/valid/bounded-decision.toml")


def owner_lab(tmp_path: Path) -> tuple[ForemanLab, str]:
    lab = ForemanLab(
        tmp_path, toml=FIXTURE, instance_inputs={}, sandbox=SandboxMode.OFF
    )
    return lab, lab.instantiate_resolved().root_id


def test_child_replacement_policy_requires_runtime_before_reserving(
    tmp_path: Path,
) -> None:
    lab, owner = owner_lab(tmp_path)
    coordinator = lab.store.coordination_store()
    admission = admission_of(lab.store.reads.load_root(owner), slot="one", generation=0)
    before = coordinator.state(owner)
    with pytest.raises(CoordinationError, match="runtime composition"):
        coordinator.start_child(owner, "one", admission)
    assert coordinator.state(owner) == before


def child_admission(lab: ForemanLab, owner: str, slot: str = "one"):
    from workflow_interpreter.schema.loader import canonical_bytes

    root = lab.store.reads.load_root(owner)
    admission = admission_of(root, slot=slot, generation=0)
    document = root.definition.document.model_copy(
        update={
            "node": tuple(
                n.model_copy(update={"decision": None})
                for n in root.definition.document.node
            )
        }
    )
    return admission.model_copy(
        update={"graph_body": canonical_bytes(document).decode()}
    )


def test_admission_replay_and_child_identity_are_durable(tmp_path: Path) -> None:
    lab, owner = owner_lab(tmp_path)
    coordinator = lab.store.coordination_store(composition=lab.composition)
    admission = child_admission(lab, owner)
    first = coordinator.start_child(owner, "one", admission)
    assert coordinator.start_child(owner, "one", admission) == first
    second = coordinator.start_child(owner, "two", child_admission(lab, owner, "two"))
    assert second.root_id != first.root_id
    status = coordinator.child_status(owner)
    assert status.reserved_activation_capacity == 24
    assert len(status.children) == 2
    assert all(
        row.wrapper_root == str(lab.supervisor_config.wrapper_root.resolve())
        for row in status.children
    )
    with pytest.raises(CoordinationError, match="conflicting"):
        coordinator.start_child(
            owner, "one", admission.model_copy(update={"base_commit": "a" * 40})
        )
    with pytest.raises(CoordinationError, match="capacity"):
        coordinator.start_child(owner, "three", child_admission(lab, owner, "three"))


def test_cancel_before_dispatch_is_durable_and_does_not_stop_sibling(
    tmp_path: Path,
) -> None:
    lab, owner = owner_lab(tmp_path)
    coordinator = lab.store.coordination_store(composition=lab.composition)
    first = coordinator.start_child(owner, "one", child_admission(lab, owner))
    coordinator.start_child(owner, "two", child_admission(lab, owner, "two"))
    cancelled = coordinator.cancel_child(owner, "one", 0, "stop-1", "no longer needed")
    assert cancelled.state == "cancelled"
    assert (
        coordinator.cancel_child(owner, "one", 0, "stop-1", "no longer needed")
        == cancelled
    )
    assert coordinator.state(owner).human_attention is None
    wiring = lab.composition.for_root(first.root_id)
    with pytest.raises(CoordinationError, match="cancel"), wiring.band:
        wiring.store.assert_member(first.root_id)
    with pytest.raises(CoordinationError, match="cancel"):
        coordinator.collect_child(owner, "one", 0)
    assert coordinator.recover_child(owner, "one", 0).children[0].state == "cancelled"
    with pytest.raises(CoordinationError, match="conflicting"):
        coordinator.cancel_child(owner, "one", 0, "stop-2", "different")


def test_drive_reaches_human_gate_without_collecting_success(tmp_path: Path) -> None:
    from tests._supervisor import ChildScript

    lab, owner = owner_lab(tmp_path)
    coordinator = lab.store.coordination_store(composition=lab.composition)
    coordinator.start_child(owner, "one", child_admission(lab, owner))
    lab.profiles.bind_node(
        "assess", ChildScript(marker='{"outcome":"no_diff"}', effects='{"paths":[]}')
    )
    lab.profiles.bind_node(
        "work", ChildScript(marker='{"outcome":"no_diff"}', effects='{"paths":[]}')
    )
    result = coordinator.drive_children(owner, 1, 5.0)
    assert result.children[0].attention.startswith("waiting")
    with pytest.raises(CoordinationError, match="settled"):
        coordinator.collect_child(owner, "one", 0)


def test_different_wrapper_homes_refuse_same_child_and_share_canonical_band(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    from workflow_interpreter.supervisor.band import BandLock
    from workflow_interpreter.supervisor.errors import LockUnavailable

    lab, owner = owner_lab(tmp_path)
    coordinator = lab.store.coordination_store(composition=lab.composition)
    child = coordinator.start_child(owner, "one", child_admission(lab, owner))
    config = lab.supervisor_config.model_copy(
        update={"wrapper_root": tmp_path / "other-home"}
    )
    other = replace(
        lab.composition,
        supervisor_config=config,
        config=lab.config.model_copy(update={"supervisor": config}),
    )
    with pytest.raises(CoordinationError, match="wrapper"):
        other.for_root(child.root_id)
    result = lab.store.coordination_store(composition=other).drive_children(
        owner, 1, 0.1
    )
    assert "wrapper" in result.children[0].attention
    coordinator.recover_child(owner, "one", 0)
    first = lab.composition.for_root(child.root_id)
    second = lab.composition.for_root(child.root_id)
    with first.band:
        with pytest.raises(LockUnavailable):
            second.band.acquire()
        with pytest.raises(LockUnavailable):
            BandLock(coordinator.member_lock_path(child.root_id)).acquire()
        report = coordinator.drive_children(owner, 1, 0.1)
        assert report.timed_out
        assert report.contended_slots == ("one",)


def test_child_continue_decision_stays_in_child_slot(tmp_path: Path) -> None:
    from tests._supervisor import ChildScript
    from workflow_interpreter.schema.loader import canonical_bytes

    lab, owner = owner_lab(tmp_path)
    root = lab.store.reads.load_root(owner)
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
        for n in root.definition.document.node
    )
    admission = admission_of(root, slot="one", generation=0).model_copy(
        update={
            "graph_body": canonical_bytes(
                root.definition.document.model_copy(update={"node": nodes})
            ).decode()
        }
    )
    coordinator = lab.store.coordination_store(composition=lab.composition)
    child = coordinator.start_child(owner, "one", admission)
    lab.profiles.bind_node(
        "assess", ChildScript(marker='{"outcome":"fail_plan"}', effects='{"paths":[]}')
    )
    lab.profiles.bind_node(
        "work", ChildScript(marker='{"outcome":"no_diff"}', effects='{"paths":[]}')
    )
    lab.profiles.decision_action = "continue_declared"
    result = coordinator.drive_children(owner, 1, 5.0)
    assert result.children[0].attention.startswith("waiting"), result
    requests = coordinator.state(owner).requests
    assert len(requests) == 1
    request = next(iter(requests.values()))
    assert request.boundary.root_id == child.root_id
    assert request.state == "applied"
    assert lab.store.reads.list_activations(owner) == ()


def test_cancel_during_launch_publication_stays_pending_until_recovery(
    tmp_path: Path,
) -> None:
    from workflow_interpreter.supervisor.band import BandLock

    lab, owner = owner_lab(tmp_path)
    coordinator = lab.store.coordination_store(composition=lab.composition)
    child = coordinator.start_child(owner, "one", child_admission(lab, owner))
    with BandLock(coordinator.member_lock_path(child.root_id, "launch")):
        intent = coordinator.cancel_child(owner, "one", 0, "stop", "launch racing")
        assert intent.state == "cancel_pending"
        assert coordinator.state(owner).human_attention is None
        assert coordinator.child_status(owner).children[0].cancellation == intent
    result = coordinator.recover_child(owner, "one", 0)
    assert result.children[0].state == "cancelled"


def test_cancel_before_actual_launch_never_executes_child(tmp_path: Path) -> None:
    from tests._supervisor import ChildScript, FakeProfile

    class CancelBeforeLaunch(FakeProfile):
        def build_command(self, task, session_id):
            command = super().build_command(task, session_id)
            coordinator.cancel_child(owner, "one", 0, "stop", "before launch")
            return command

    lab, owner = owner_lab(tmp_path)
    coordinator = lab.store.coordination_store(composition=lab.composition)
    child = coordinator.start_child(owner, "one", child_admission(lab, owner))
    lab.profiles.profile = CancelBeforeLaunch(
        ChildScript(marker='{"outcome":"no_diff"}', effects='{"paths":[]}')
    )
    result = coordinator.drive_children(owner, 1, 2)
    assert result.children[0].state == "cancelled"
    activations = lab.store.reads.list_activations(child.root_id)
    assert len(activations) == 1
    assert activations[0].metadata.handle is None
    with pytest.raises(CoordinationError, match="cancel"):
        lab.foreman.steer(
            child.root_id,
            activations[0].activation_id,
            reason="late steer",
            instructions="continue",
        )
    assert (
        not lab.composition.for_root(child.root_id)
        .paths.ledger(activations[0].activation_id)
        .exists()
    )
    assert coordinator.state(owner).human_attention is None


def test_same_lock_object_is_not_reentrant_across_threads(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    from workflow_interpreter.supervisor.band import BandLock
    from workflow_interpreter.supervisor.errors import LockUnavailable

    band = BandLock(tmp_path / "thread.lock")
    with band, ThreadPoolExecutor(max_workers=1) as pool:
        assert not pool.submit(lambda: band.held).result()
        with pytest.raises(LockUnavailable):
            pool.submit(band.acquire).result()


def test_writer_admission_refuses_shared_checkout_before_reservation(
    tmp_path: Path,
) -> None:
    from pydantic import TypeAdapter

    from tests.test_children_process import writer_lab
    from workflow_interpreter.bdio import ResolvedSetting

    lab, owner, composition, _spawner = writer_lab(tmp_path)
    coordinator = lab.store.coordination_store(composition=composition)
    admission = admission_of(owner, slot="one", generation=0)
    adapter = TypeAdapter(tuple[ResolvedSetting, ...])
    settings = tuple(
        item.model_copy(update={"value": "in-repo"})
        if item.key == "node.work.isolation"
        else item
        for item in adapter.validate_json(admission.config_json)
    )
    admission = admission.model_copy(
        update={"config_json": adapter.dump_json(settings).decode()}
    )
    before = coordinator.state(owner.root_id)
    with pytest.raises(CoordinationError, match="worktree"):
        coordinator.start_child(owner.root_id, "one", admission)
    assert coordinator.state(owner.root_id) == before


@pytest.mark.parametrize(
    "updates",
    [{"generation": 1}, {"request_id": "request"}, {"predecessor_id": "wf-old"}],
)
def test_child_refuses_supplied_lineage(tmp_path: Path, updates) -> None:
    lab, owner = owner_lab(tmp_path)
    coordinator = lab.store.coordination_store(composition=lab.composition)
    before = coordinator.state(owner)
    with pytest.raises(CoordinationError, match="standalone"):
        coordinator.start_child(
            owner, "one", child_admission(lab, owner).model_copy(update=updates)
        )
    assert coordinator.state(owner) == before
