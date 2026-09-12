"""One decision uses ordinary process execution and resumes useful work."""

from pathlib import Path

from tests._foreman import ForemanLab
from tests._supervisor import ChildScript
from workflow_interpreter.supervisor.models import SandboxMode

FIXTURE = Path("workflow_interpreter/fixtures/valid/bounded-decision.toml")


def test_decision_executes_then_continues_to_work_without_signing_gate(
    tmp_path: Path,
) -> None:
    lab = ForemanLab(
        tmp_path, toml=FIXTURE, instance_inputs={}, sandbox=SandboxMode.OFF
    )
    root = lab.instantiate_resolved()
    lab.profiles.bind_node(
        "assess", ChildScript(marker='{"outcome":"fail_plan"}', effects='{"paths":[]}')
    )
    lab.profiles.bind_node(
        "work",
        ChildScript(
            marker='{"outcome":"no_diff"}',
            effects='{"paths":[]}',
            artifact_path="result.json",
            artifact_body='{"sum":55}',
        ),
    )
    lab.profiles.decision_action = "continue_declared"
    result = lab.foreman.run(root.root_id, poll_s=0.01, max_wall_s=3600)
    assert (
        result.report.opened_gate is not None or result.report.waiting_gate is not None
    ), result
    view = lab.store.coordination_store().coordination_view(root.root_id)
    assert len(view.requests) == 1
    assert view.requests[0].state == "applied"
    assert view.requests[0].response.action == "continue_declared"
    assert [t.node for t in lab.profiles.profile.tasks] == ["assess", "decide", "work"]
    gate = lab.store.reads.list_gates(root.root_id)[0]
    assert gate.metadata.gate_node == "ship"
    assert gate.metadata.verified_fingerprint is None
    work = next(
        a
        for a in lab.store.reads.list_activations(root.root_id)
        if a.metadata.node == "work"
    )
    assert work.metadata.evidence.outputs_tree_oid
    assert (
        lab.git.blob_text(
            f"{work.metadata.evidence.outputs_tree_oid}:result.json", cwd=lab.repo
        )
        == '{"sum":55}'
    )


def test_replacement_inherits_owner_and_advice_is_essential(tmp_path: Path) -> None:
    lab = ForemanLab(
        tmp_path, toml=FIXTURE, instance_inputs={}, sandbox=SandboxMode.OFF
    )
    root = lab.instantiate_resolved()
    lab.profiles.bind_node(
        "assess", ChildScript(marker='{"outcome":"fail_plan"}', effects='{"paths":[]}')
    )
    lab.profiles.decision_action = "replace"
    # Repeated replacement eventually exhausts the original owner's reservations.
    result = lab.foreman.run(root.root_id, poll_s=0.01, max_wall_s=3600)
    state = lab.store.coordination_store().state(root.root_id)
    assert result.report.halted, result
    assert len(state.reservations) <= 5
    assert sum(r.capacity.ceiling for r in state.reservations.values()) <= 28
    replacements = [
        r for r in state.reservations.values() if r.capacity.kind == "replacement"
    ]
    assert replacements
    for reservation in replacements:
        member = lab.store.reads.load_root(reservation.root_id)
        assert member.metadata.essential_inputs == ("revision",)
        assert member.metadata.coordination.owner_id == root.root_id
    assert any(
        "corrected approach" in task.brief
        for task in lab.profiles.profile.tasks
        if task.node == "assess"
    )
    # Recreating the initial handle must not reactivate the original generation.
    before = state.active
    lab.instantiate_resolved()
    assert lab.store.coordination_store().state(root.root_id).active == before


def test_local_halt_cap_and_defensive_rebudget_clamp(tmp_path: Path) -> None:
    import pytest

    from workflow_interpreter.bdio import BoundSetting
    from workflow_interpreter.bdio.bounds import effective_bound
    from workflow_interpreter.bdio.errors import BoundExceededError
    from workflow_interpreter.foreman.gates import halt_gate
    from workflow_interpreter.schema.decisions import CoordinationError

    lab = ForemanLab(
        tmp_path, toml=FIXTURE, instance_inputs={}, sandbox=SandboxMode.OFF
    )
    root = lab.instantiate_resolved({"instance.max_total_activations": 1})
    wiring = lab.composition.for_root(root.root_id)
    with pytest.raises(CoordinationError, match="member band"):
        lab.store.open_gate(root.root_id, halt_gate("one"))
    with wiring.band:
        gate = wiring.store.open_gate(root.root_id, halt_gate("one"))
        # Same logical open gate re-finds even at capacity.
        assert (
            wiring.store.open_gate(root.root_id, halt_gate("one")).gate_id
            == gate.gate_id
        )
        # A different gate cannot cross H, even though legacy HALT is exempt.
        from workflow_interpreter.bdio.wire import GateOpenRequest
        from workflow_interpreter.schema.models import BindsMode, Outcome

        request = GateOpenRequest(
            gate_node="ship",
            outcomes=(Outcome.APPROVE, Outcome.ABANDON),
            binds=BindsMode.IMMUTABLE,
            source_activation_id="wf-source",
            opening_outcome=Outcome.NO_DIFF,
            artifact_ref=lab.head,
            artifact_digest=lab.git.tree_oid(lab.head, cwd=lab.repo),
        )
        with pytest.raises(BoundExceededError):
            wiring.store.open_gate(root.root_id, request)
    # Historical signed raises cannot move the immutable allocation.
    from workflow_interpreter.bdio.carriers import GateState

    raised = gate.model_copy(
        update={
            "metadata": gate.metadata.model_copy(
                update={
                    "state": GateState.CLOSED,
                    "outcome": Outcome.REBUDGET,
                    "bound_key": "instance.max_total_activations",
                    "bound_value": 100,
                    "verified_fingerprint": "signed",
                    "payload_digest": "d" * 64,
                }
            )
        }
    )
    assert effective_bound(root, (raised,), BoundSetting.MAX_TOTAL_ACTIVATIONS) == 1


import pytest


@pytest.mark.parametrize(
    "patch",
    [
        {"request_id": "stale"},
        {"parent_generation": 99},
        {"artifact_digest": "f" * 40},
        {"producing_activation_id": "stale"},
        {"action": "approve"},
        {"signer": "model"},
    ],
)
def test_untrusted_decision_cannot_resume_work(tmp_path: Path, patch: dict) -> None:
    lab = ForemanLab(
        tmp_path, toml=FIXTURE, instance_inputs={}, sandbox=SandboxMode.OFF
    )
    root = lab.instantiate_resolved()
    lab.profiles.bind_node(
        "assess", ChildScript(marker='{"outcome":"fail_plan"}', effects='{"paths":[]}')
    )
    lab.profiles.decision_action = "continue_declared"
    lab.profiles.decision_patch = patch
    result = lab.foreman.run(root.root_id, poll_s=0.01, max_wall_s=3600)
    assert result.report.halted
    assert "work" not in [t.node for t in lab.profiles.profile.tasks]
    assert lab.store.coordination_store().state(root.root_id).human_attention


def test_consumed_intent_replays_after_restart_without_second_decider(
    tmp_path: Path,
) -> None:
    from tests._supervisor import PersistentBd

    lab = ForemanLab(
        tmp_path,
        toml=FIXTURE,
        instance_inputs={},
        sandbox=SandboxMode.OFF,
        bd_factory=lambda workspace: PersistentBd(
            workspace, tmp_path / "bd-state.json"
        ),
    )
    root = lab.instantiate_resolved()
    lab.profiles.bind_node(
        "assess", ChildScript(marker='{"outcome":"fail_plan"}', effects='{"paths":[]}')
    )
    lab.profiles.decision_action = "continue_declared"
    for _ in range(30):
        report = lab.tick()
        state = lab.store.coordination_store().state(root.root_id)
        if state.requests and next(iter(state.requests.values())).state == "consumed":
            break
        assert not report.stalled, report
    else:
        pytest.fail("consumption not reached")
    reserved = state.reservations
    lab.rebuild()
    lab.profiles.bind_node(
        "work", ChildScript(marker='{"outcome":"no_diff"}', effects='{"paths":[]}')
    )
    result = lab.foreman.run(root.root_id, poll_s=0.01, max_wall_s=3600)
    assert result.report.opened_gate
    assert [t.node for t in lab.profiles.profile.tasks] == ["work"]
    coordinator = lab.store.coordination_store()
    assert coordinator.state(root.root_id).reservations == reserved
    request = next(iter(coordinator.state(root.root_id).requests.values()))
    from workflow_interpreter.schema.decisions import CoordinationError

    with pytest.raises(CoordinationError, match="already consumed"):
        coordinator.consume_decision(root.root_id, request.request_id, request.response)


def test_repeated_closed_halts_cannot_exceed_member_allocation(tmp_path: Path) -> None:
    from workflow_interpreter.bdio.errors import BoundExceededError
    from workflow_interpreter.foreman.gates import halt_gate

    lab = ForemanLab(
        tmp_path, toml=FIXTURE, instance_inputs={}, sandbox=SandboxMode.OFF
    )
    root = lab.instantiate_resolved({"instance.max_total_activations": 1})
    wiring = lab.composition.for_root(root.root_id)
    with wiring.band:
        gate = wiring.store.open_gate(root.root_id, halt_gate("capacity"))
        # Simulate a historical authenticated close at the external Beads boundary.
        row = lab.fake_bd.rows[gate.gate_id]
        row["status"] = "closed"
        row["metadata"].update(state="closed", outcome="abandon")
        with pytest.raises(BoundExceededError):
            wiring.store.open_gate(root.root_id, halt_gate("another halt"))
    assert len(lab.store.reads.list_gates(root.root_id)) == 1


def test_oversize_replacement_advice_refuses_before_replacement_dispatch(
    tmp_path: Path,
) -> None:
    lab = ForemanLab(
        tmp_path, toml=FIXTURE, instance_inputs={}, sandbox=SandboxMode.OFF
    )
    root = lab.instantiate_resolved({"node.assess.context_budget_bytes": 4000})
    lab.profiles.bind_node(
        "assess", ChildScript(marker='{"outcome":"fail_plan"}', effects='{"paths":[]}')
    )
    lab.profiles.decision_action = "replace"
    lab.profiles.decision_patch = {"revision": "essential revision " * 350}
    result = lab.foreman.run(root.root_id, poll_s=0.01, max_wall_s=3600)
    assert result.report.halted
    assert "envelope requires" in result.report.stalled
    assert [t.node for t in lab.profiles.profile.tasks] == ["assess", "decide"]
    state = lab.store.coordination_store().state(root.root_id)
    assert not any(
        r.capacity.kind == "replacement" for r in state.reservations.values()
    )


def test_first_pass_acceptance_has_no_decision_member(tmp_path: Path) -> None:
    lab = ForemanLab(
        tmp_path, toml=FIXTURE, instance_inputs={}, sandbox=SandboxMode.OFF
    )
    root = lab.instantiate_resolved()
    for node in ("assess", "work"):
        lab.profiles.bind_node(
            node, ChildScript(marker='{"outcome":"no_diff"}', effects='{"paths":[]}')
        )
    result = lab.foreman.run(root.root_id, poll_s=0.01, max_wall_s=3600)
    assert result.report.opened_gate
    view = lab.store.coordination_store().coordination_view(root.root_id)
    assert view.requests == ()
    assert view.members == 1
    assert [t.node for t in lab.profiles.profile.tasks] == ["assess", "work"]


def test_lost_decision_admission_reply_repairs_same_root(tmp_path: Path) -> None:
    from tests._fake_bd import InjectedCrash

    lab = ForemanLab(
        tmp_path, toml=FIXTURE, instance_inputs={}, sandbox=SandboxMode.OFF
    )
    root = lab.instantiate_resolved()
    lab.profiles.bind_node(
        "assess", ChildScript(marker='{"outcome":"fail_plan"}', effects='{"paths":[]}')
    )
    lab.profiles.bind_node(
        "work", ChildScript(marker='{"outcome":"no_diff"}', effects='{"paths":[]}')
    )
    lab.profiles.decision_action = "continue_declared"
    for _ in range(15):
        lab.tick()
        state = lab.store.coordination_store().state(root.root_id)
        if state.requests:
            break
    assert next(iter(state.requests.values())).state == "requested"
    lab.fake_bd.lose_response_on("create")
    with pytest.raises(InjectedCrash):
        lab.tick()
    result = lab.foreman.run(root.root_id, poll_s=0.01, max_wall_s=3600)
    assert result.report.opened_gate, result
    state = lab.store.coordination_store().state(root.root_id)
    assert len(state.reservations) == 2
    assert (
        len(
            [
                r
                for r in lab.fake_bd.rows.values()
                if r["metadata"].get("wf_kind") == "root"
            ]
        )
        == 2
    )


def test_local_region_exhaustion_requests_decision_without_more_work(
    tmp_path: Path,
) -> None:
    text = FIXTURE.read_text().replace(
        'name = "assess"\nkind = "task"',
        'name = "assess"\nkind = "task"\nregion = "cycle"',
    )
    text += '\n[[region]]\nname="cycle"\nmode="bounded-cycle"\nentry_node="assess"\nmax_entries=1\non_exhausted="ship"\n'
    text = text.replace(
        'from = "assess"\non = "no_diff"\nto = "work"',
        'from = "assess"\non = "no_diff"\nto = "assess"',
    )
    path = tmp_path / "exhaustion.toml"
    path.write_text(text)
    lab = ForemanLab(tmp_path, toml=path, instance_inputs={}, sandbox=SandboxMode.OFF)
    root = lab.instantiate_resolved()
    lab.profiles.bind_node(
        "assess", ChildScript(marker='{"outcome":"no_diff"}', effects='{"paths":[]}')
    )
    lab.profiles.decision_action = "human"
    result = lab.foreman.run(root.root_id, poll_s=0.01, max_wall_s=3600)
    assert result.report.halted, result
    state = lab.store.coordination_store().state(root.root_id)
    request = next(iter(state.requests.values()))
    assert request.boundary.kind == "allowance_exhausted"
    assert "continue_declared" not in request.actions
    assert [t.node for t in lab.profiles.profile.tasks] == ["assess", "decide"]


def test_signed_rebudget_above_allocation_is_refused(
    tmp_path: Path, signing_config, sign_payload
) -> None:
    from workflow_interpreter.bdio.signing import BoundMutation
    from workflow_interpreter.foreman.gates import halt_gate
    from workflow_interpreter.schema.models import Outcome

    lab = ForemanLab(
        tmp_path,
        toml=FIXTURE,
        instance_inputs={},
        sandbox=SandboxMode.OFF,
        signing=signing_config,
        signer=sign_payload,
    )
    root = lab.instantiate_resolved({"instance.max_total_activations": 2})
    wiring = lab.composition.for_root(root.root_id)
    with wiring.band:
        gate = wiring.store.open_gate(root.root_id, halt_gate("allocation proof"))
    lab.approve(
        gate.gate_id,
        Outcome.REBUDGET,
        mutation=BoundMutation(key="instance.max_total_activations", value=3),
    )
    report = lab.tick()
    assert report.refusals and not report.closed_gates, report
    current = lab.store.reads.load_gate(gate.gate_id)
    assert current.metadata.state.value == "open"
    assert current.metadata.verified_fingerprint is None
    assert "immutable member allocation" in lab.refusal(gate.gate_id)


def test_two_process_reservations_converge_on_one_debit(tmp_path: Path) -> None:
    import multiprocessing

    from tests._foreman import LockedPersistentBd
    from workflow_interpreter.foreman.decisions import admission_of
    from workflow_interpreter.schema.decisions import MemberCapacity
    from workflow_interpreter.supervisor.errors import LockUnavailable

    lab = ForemanLab(
        tmp_path,
        toml=FIXTURE,
        instance_inputs={},
        sandbox=SandboxMode.OFF,
        bd_factory=lambda workspace: LockedPersistentBd(
            workspace, tmp_path / "state.json"
        ),
    )
    root = lab.instantiate_resolved()
    admission = admission_of(root, slot="child-proof", generation=0)
    capacity = MemberCapacity(ceiling=8, kind="child")
    context = multiprocessing.get_context("fork")
    barrier = context.Barrier(2)
    queue = context.Queue()

    def child() -> None:
        barrier.wait(timeout=10)
        try:
            reservation = lab.store.coordination_store().reserve(
                root.root_id, "same-child", capacity, admission
            )
            queue.put(reservation.reservation_id)
        except LockUnavailable:
            queue.put("contended")

    children = [context.Process(target=child) for _ in range(2)]
    for process in children:
        process.start()
    for process in children:
        process.join(timeout=20)
        assert process.exitcode == 0
    replies = [queue.get(timeout=2) for _ in children]
    assert "same-child" in replies
    coordinator = lab.store.coordination_store()
    coordinator.reserve(root.root_id, "same-child", capacity, admission)
    assert len(coordinator.state(root.root_id).reservations) == 2
    assert (
        coordinator.coordination_view(root.root_id).reserved_activation_capacity == 16
    )


def test_coordinated_detached_wrapper_acquires_its_member_band(tmp_path: Path) -> None:
    import pytest

    from tests._fake_bd import InjectedCrash
    from workflow_interpreter.foreman.supervise import run_wrapper

    lab = ForemanLab(
        tmp_path, toml=FIXTURE, instance_inputs={}, sandbox=SandboxMode.OFF
    )
    root = lab.instantiate_resolved()
    lab.profiles.bind_node(
        "assess", ChildScript(marker='{"outcome":"fail_plan"}', effects='{"paths":[]}')
    )
    lab.spawner.fail_next()
    with pytest.raises(InjectedCrash):
        lab.foreman.tick(root.root_id)
    activation = lab.store.reads.list_activations(root.root_id)[0]
    # Fresh wiring, outside the tick band, as in the actual detached CLI wrapper.
    run_wrapper(lab.composition, root.root_id, activation.activation_id)
    assert (
        lab.store.reads.load_activation(activation.activation_id).metadata.exit_record
        is not None
    )
