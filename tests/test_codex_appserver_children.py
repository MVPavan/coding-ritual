"""Control uncertainty is advisory for coordinator-driven child lifecycle progress."""

import pytest

from tests._bdio import handle
from tests._foreman import DEFAULT_LAB_ROLES, ForemanLab, entry_request
from tests.test_children_lifecycle import FIXTURE, child_admission
from workflow_interpreter.bdio.rpc_records import SessionRegistration
from workflow_interpreter.contracts.rpc_control import ControlState
from workflow_interpreter.foreman.children import observe
from workflow_interpreter.foreman.rpc_control import acknowledge_uncertain
from workflow_interpreter.foreman.tick import Foreman
from workflow_interpreter.schema.models import Outcome
from workflow_interpreter.supervisor.models import SandboxMode


def child_with_uncertain_control(tmp_path):
    """Persist the exact runtime attention produced by an uncertain child tick."""
    graph = tmp_path / "children.toml"
    graph.write_text(FIXTURE.read_text().replace("max_steers = 0", "max_steers = 2"))
    roles = {
        name: binding.model_copy(update={"profile": "codex-appserver"})
        for name, binding in DEFAULT_LAB_ROLES.items()
    }
    lab = ForemanLab(
        tmp_path / "lab",
        toml=graph,
        roles=roles,
        instance_inputs={},
        sandbox=SandboxMode.OFF,
    )
    owner = lab.instantiate_resolved().root_id
    coordinator = lab.store.coordination_store(composition=lab.composition)
    child = coordinator.start_child(owner, "one", child_admission(lab, owner))
    wiring = lab.composition.for_root(child.root_id)
    with wiring.band:
        activation = wiring.store.mint_activation(
            child.root_id,
            entry_request(node="assess", runner_profile="codex-appserver"),
        ).activation
        aid = activation.activation_id
        process = handle(session_id="").model_copy(
            update={"log_path": str(wiring.paths.log(aid))}
        )
        wiring.store.record_dispatch(aid, process, launch_id="test-launch")
        registration = SessionRegistration(
            root_id=child.root_id,
            activation_id=aid,
            launch_id="test-launch",
            handle=process,
            thread_id="thread-1",
            model="fake",
            effort="medium",
            policy_digest="test",
            state_path=str(wiring.paths.activation_dir(aid) / "vendor-state"),
        )
        wiring.store.register_session(aid, registration)
        control = wiring.store.reserve_in_place_steer(
            aid, registration, "turn-1", "digest"
        )
        wiring.store.record_control_state(aid, control, ControlState.UNCERTAIN)
    child = coordinator.child_record(owner, "one", 0).model_copy(
        update={
            "attention": f"{aid}:control:1",
            "attention_source": "runtime",
        }
    )
    coordinator.update_child(owner, child)
    return lab, owner, coordinator, child, aid


@pytest.mark.parametrize("resolution", ["acknowledge", "settlement"])
def test_resolved_control_attention_does_not_stop_child_drive(tmp_path, resolution):
    """After acknowledgment or settlement, the coordinator advances the child."""
    lab, owner, coordinator, child, aid = child_with_uncertain_control(tmp_path)
    assert observe(lab.composition, child).attention == f"{aid}:control:1"
    wiring = lab.composition.for_root(child.root_id)
    if resolution == "acknowledge":
        with wiring.band:
            acknowledge_uncertain(wiring.store, aid, "operator inspected delivery")
        assert observe(lab.composition, child).attention is None
    with wiring.band:
        wiring.store.close_activation(aid, Outcome.NO_DIFF)
    assert observe(lab.composition, child).attention is None
    result = coordinator.drive_children(owner, 1, 2)
    assert any(
        activation.metadata.node == "work"
        for activation in lab.store.reads.list_activations(child.root_id)
    ), result.model_dump()


def test_live_control_attention_allows_settlement_during_child_drive(
    tmp_path, monkeypatch
):
    """The coordinator must enter the child tick that can observe vendor settlement."""
    lab, owner, coordinator, child, aid = child_with_uncertain_control(tmp_path)
    tick = Foreman._progress_local
    entered = []

    def complete_on_tick(foreman, root_id):
        if not entered:
            entered.append(root_id)
            wiring = lab.composition.for_root(root_id)
            with wiring.band:
                wiring.store.close_activation(aid, Outcome.NO_DIFF)
        return tick(foreman, root_id)

    monkeypatch.setattr(Foreman, "_progress_local", complete_on_tick)
    coordinator.drive_children(owner, 1, 2)
    assert entered == [child.root_id]
    assert any(
        activation.metadata.node == "work"
        for activation in lab.store.reads.list_activations(child.root_id)
    )
