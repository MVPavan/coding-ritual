"""Real deterministic processes through ordinary Foreman and Supervisor."""

from dataclasses import replace
from pathlib import Path

import pytest

from tests._foreman import ForemanLab, LockedPersistentBd, ProcSpawner
from tests._supervisor import ChildScript
from workflow_interpreter.foreman.decisions import admission_of
from workflow_interpreter.supervisor.clock import SystemClock
from workflow_interpreter.supervisor.models import SandboxMode


def writer_lab(
    tmp_path: Path, *, sandbox: SandboxMode = SandboxMode.OFF, writing: bool = True
):
    graph = tmp_path / "writer.toml"
    graph.write_text("""[graph]
id = "children-proof"
version = "1.0.0"
entry = "work"
description = "Deterministic independent writer proof"
[instance]
max_total_activations = 3
coordination_limits = {max_members=5, max_activations=15, max_decision_attempts=2, max_replacements=1}
[fallback]
to = "failed"
[[node]]
name = "work"
kind = "task"
instructions = "Write the deterministic feature and report done."
runner = "profile:implementer"
writes = true
isolation = "worktree"
allowed_paths = ["src/**"]
verify = [{cmd="scripts/verify-feature.sh", timeout="20s"}]
max_wall = "1m"
context_budget_bytes = 16000
stale_after = "1m"
max_infra_retries = 0
max_steers = 0
outcomes = ["done", "fail_code"]
[[node]]
name = "done"
kind = "terminal"
[[node]]
name = "failed"
kind = "terminal"
[[edge]]
from = "work"
on = "done"
to = "done"
[[edge]]
from = "work"
on = "fail_code"
to = "failed"
""")
    if not writing:
        graph.write_text(
            graph.read_text()
            .replace("writes = true", "writes = false")
            .replace('allowed_paths = ["src/**"]', "allowed_paths = []")
            .replace(
                'outcomes = ["done", "fail_code"]',
                'outcomes = ["no_diff", "fail_code"]',
            )
            .replace('on = "done"', 'on = "no_diff"')
        )
    lab = ForemanLab(
        tmp_path,
        toml=graph,
        bd_factory=lambda workspace: LockedPersistentBd(
            workspace, tmp_path / "bd.json"
        ),
        instance_inputs={},
        sandbox=sandbox,
    )
    owner = lab.instantiate_resolved()
    spawner = ProcSpawner()
    composition = replace(lab.composition, spawner=spawner, clock=SystemClock())
    spawner.bind(composition)
    return lab, owner, composition, spawner


def test_real_writer_collection_keeps_immutable_evidence(tmp_path: Path) -> None:
    lab, owner, composition, spawner = writer_lab(tmp_path)
    coordinator = lab.store.coordination_store(composition=composition)
    child = coordinator.start_child(
        owner.root_id, "one", admission_of(owner, slot="one", generation=0)
    )
    try:
        result = coordinator.drive_children(owner.root_id, 1, 8.0)
        assert not result.timed_out, result
        receipt = coordinator.collect_child(owner.root_id, "one", 0)
        assert receipt.root_id == child.root_id
        assert receipt.terminal == "done"
        assert receipt.artifact_commit != lab.head
        assert (
            lab.git.tree_oid(receipt.outputs_commit, cwd=lab.repo)
            == receipt.outputs_tree
        )
        assert coordinator.collect_child(owner.root_id, "one", 0) == receipt
        assert lab.store.reads.load_root(owner.root_id).metadata.terminal is None
    finally:
        for process in spawner.processes:
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=5)


@pytest.mark.proc
@pytest.mark.parametrize("cap", [1, 2])
def test_process_cap_isolation_cancel_and_fresh_driver_recovery(
    tmp_path: Path, cap: int
) -> None:
    from workflow_interpreter.supervisor import procfs
    from workflow_interpreter.supervisor.models import Liveness

    lab, owner, composition, spawner = writer_lab(tmp_path)
    lab.profiles.bind_node(
        "work",
        ChildScript(
            marker='{"outcome":"done"}',
            effects='{"paths":["src/feature.py"]}',
            write_path="src/feature.py",
            write_body="value = 2\n",
            commit=True,
            sleep_s=30,
        ),
    )
    coordinator = lab.store.coordination_store(composition=composition)
    children = [
        coordinator.start_child(
            owner.root_id, slot, admission_of(owner, slot=slot, generation=0)
        )
        for slot in ("one", "two")
    ]
    before = coordinator.state(owner.root_id).reservations
    try:
        result = coordinator.drive_children(owner.root_id, cap, 1.0)
        assert result.timed_out, result.model_dump_json()
        acts = [
            a for c in children for a in lab.store.reads.list_activations(c.root_id)
        ]
        assert len(acts) == cap
        assert all(a.metadata.handle is not None for a in acts)
        assert all(
            procfs.prove_liveness(
                composition.supervisor_config, a.metadata.handle
            ).status
            is Liveness.ALIVE
            for a in acts
        )
        paths = [composition.for_root(c.root_id).paths for c in children[:cap]]
        assert len({p.worktree.resolve() for p in paths}) == cap
        if cap == 2:
            assert (
                paths[0].worktree.joinpath(".git").read_text()
                != paths[1].worktree.joinpath(".git").read_text()
            )
        fresh = lab.store.coordination_store(composition=replace(composition))
        recovered = fresh.recover_child(owner.root_id, "one", 0)
        assert recovered.children[0].root_id == children[0].root_id
        assert fresh.state(owner.root_id).reservations == before
        receipt = fresh.cancel_child(owner.root_id, "one", 0, "cancel-1", "stop first")
        assert receipt.state == "cancelled"
        assert fresh.state(owner.root_id).human_attention is None
        with pytest.raises(ValueError, match="cancel"):
            fresh.collect_child(owner.root_id, "one", 0)
        assert (
            procfs.prove_liveness(
                composition.supervisor_config, acts[0].metadata.handle
            ).status
            is not Liveness.ALIVE
        )
        if cap == 2:
            assert (
                procfs.prove_liveness(
                    composition.supervisor_config, acts[1].metadata.handle
                ).status
                is Liveness.ALIVE
            )
    finally:
        for child in children:
            row = coordinator.child_record(owner.root_id, child.link.slot, 0)
            if row.cancellation is None:
                coordinator.cancel_child(
                    owner.root_id, child.link.slot, 0, "cleanup", "test cleanup"
                )
        for process in spawner.processes:
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=5)
    # The normal observer can still persist output after the cancellation fence.
    late = lab.store.reads.load_activation(acts[0].activation_id)
    assert late.metadata.exit_record is not None
    assert late.metadata.evidence is not None


@pytest.mark.proc
def test_indeterminate_process_death_stays_pending(tmp_path: Path) -> None:
    lab, owner, composition, spawner = writer_lab(tmp_path)
    lab.profiles.bind_node(
        "work",
        ChildScript(marker='{"outcome":"done"}', effects='{"paths":[]}', sleep_s=30),
    )
    coordinator = lab.store.coordination_store(composition=composition)
    child = coordinator.start_child(
        owner.root_id, "one", admission_of(owner, slot="one", generation=0)
    )
    try:
        coordinator.drive_children(owner.root_id, 1, 0.8)
        activation = lab.store.reads.list_activations(child.root_id)[0]
        handle = activation.metadata.handle
        assert handle is not None
        proc = tmp_path / "unreadable-proc"
        (proc / str(handle.pid)).mkdir(parents=True)
        (proc / str(handle.pid) / "stat").write_text("malformed process identity")
        config = composition.supervisor_config.model_copy(update={"proc_root": proc})
        uncertain = replace(
            composition,
            supervisor_config=config,
            config=composition.config.model_copy(update={"supervisor": config}),
        )
        pending = lab.store.coordination_store(composition=uncertain).cancel_child(
            owner.root_id, "one", 0, "stop", "uncertain identity"
        )
        assert pending.state == "cancel_pending"
        with pytest.raises(ValueError, match="cancel"):
            coordinator.collect_child(owner.root_id, "one", 0)
        assert (
            coordinator.recover_child(owner.root_id, "one", 0).children[0].state
            == "cancelled"
        )
    finally:
        row = coordinator.child_record(owner.root_id, "one", 0)
        if row.cancellation is None:
            coordinator.cancel_child(owner.root_id, "one", 0, "cleanup", "cleanup")
        else:
            coordinator.recover_child(owner.root_id, "one", 0)
        for process in spawner.processes:
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=5)


def _drive_in_process(composition, owner_id):
    composition.store.coordination_store(composition=composition).drive_children(
        owner_id, 2, 30.0
    )


def _contending_driver(composition, owner_id, results):
    from workflow_interpreter.supervisor.errors import LockUnavailable

    try:
        composition.store.coordination_store(composition=composition).drive_children(
            owner_id, 2, 0.1
        )
    except LockUnavailable:
        results.put("contended")
    else:
        results.put("incorrectly acquired")


@pytest.mark.proc
def test_killed_driver_recovers_same_running_process_and_reservation(
    tmp_path: Path,
) -> None:
    import multiprocessing
    import time

    from workflow_interpreter.supervisor import procfs
    from workflow_interpreter.supervisor.models import Liveness

    lab, owner, composition, _spawner = writer_lab(tmp_path)
    lab.profiles.bind_node(
        "work",
        ChildScript(marker='{"outcome":"done"}', effects='{"paths":[]}', sleep_s=30),
    )
    coordinator = lab.store.coordination_store(composition=composition)
    child = coordinator.start_child(
        owner.root_id, "one", admission_of(owner, slot="one", generation=0)
    )
    coordinator.start_child(
        owner.root_id, "two", admission_of(owner, slot="two", generation=0)
    )
    reservations = coordinator.state(owner.root_id).reservations
    driver = multiprocessing.get_context("fork").Process(
        target=_drive_in_process, args=(composition, owner.root_id)
    )
    driver.start()
    try:
        deadline = time.monotonic() + 5
        handle = None
        while time.monotonic() < deadline:
            acts = lab.store.reads.list_activations(child.root_id)
            if acts and acts[0].metadata.handle:
                handle = acts[0].metadata.handle
                break
            time.sleep(0.01)
        assert handle is not None
        results = multiprocessing.get_context("fork").Queue()
        contender = multiprocessing.get_context("fork").Process(
            target=_contending_driver, args=(composition, owner.root_id, results)
        )
        contender.start()
        contender.join(timeout=5)
        assert contender.exitcode == 0
        assert results.get(timeout=1) == "contended"
        results.close()
        driver.kill()
        driver.join(timeout=5)
        assert driver.exitcode == -9
        fresh = lab.store.coordination_store(composition=replace(composition))
        recovered = fresh.recover_child(owner.root_id, "one", 0)
        assert recovered.children[0].root_id == child.root_id
        assert fresh.state(owner.root_id).reservations == reservations
        assert (
            lab.store.reads.list_activations(child.root_id)[0].metadata.handle == handle
        )
        assert (
            procfs.prove_liveness(composition.supervisor_config, handle).status
            is Liveness.ALIVE
        )
        # The dead driver's canonical lock is released; no new admission is needed.
        fresh.drive_children(owner.root_id, 2, 0.1)
        assert fresh.state(owner.root_id).reservations == reservations
    finally:
        if driver.is_alive():
            driver.kill()
            driver.join(timeout=5)
        for slot in ("one", "two"):
            coordinator.cancel_child(owner.root_id, slot, 0, "cleanup", "cleanup")


@pytest.mark.proc
def test_failed_child_reports_terminal_and_cannot_collect(tmp_path: Path) -> None:
    lab, owner, composition, spawner = writer_lab(tmp_path)
    lab.profiles.bind_node(
        "work", ChildScript(marker='{"outcome":"fail_code"}', effects='{"paths":[]}')
    )
    coordinator = lab.store.coordination_store(composition=composition)
    coordinator.start_child(
        owner.root_id, "one", admission_of(owner, slot="one", generation=0)
    )
    result = coordinator.drive_children(owner.root_id, 1, 5)
    assert result.children[0].terminal == "failed"
    assert result.children[0].outcome == "fail_code"
    with pytest.raises(ValueError, match="unsuccessfully"):
        coordinator.collect_child(owner.root_id, "one", 0)
    for process in spawner.processes:
        process.join(timeout=5)


@pytest.mark.proc
def test_output_reference_tamper_refuses_collection(tmp_path: Path) -> None:
    lab, owner, composition, spawner = writer_lab(tmp_path)
    coordinator = lab.store.coordination_store(composition=composition)
    child = coordinator.start_child(
        owner.root_id, "one", admission_of(owner, slot="one", generation=0)
    )
    coordinator.drive_children(owner.root_id, 1, 5)
    activation = lab.store.reads.list_activations(child.root_id)[0]
    lab.git.update_ref(activation.metadata.evidence.outputs_ref, lab.head, cwd=lab.repo)
    with pytest.raises(ValueError, match="tree"):
        coordinator.collect_child(owner.root_id, "one", 0)
    assert coordinator.child_status(owner.root_id).children[0].collection is None
    for process in spawner.processes:
        process.join(timeout=5)


@pytest.mark.proc
@pytest.mark.parametrize("crash_publication", [False, True])
def test_cancel_between_real_launch_and_dispatch_publication(
    tmp_path: Path, crash_publication: bool
) -> None:
    import multiprocessing

    from tests._fake_bd import InjectedCrash
    from tests._supervisor import FakeProfile

    publication = multiprocessing.get_context("fork").Event()

    class CancellingProfile(FakeProfile):
        def launch(self, command, launcher):
            handle = super().launch(command, launcher)
            receipt = coordinator.cancel_child(
                owner.root_id, "one", 0, "racing-stop", "after fork"
            )
            assert receipt.state == "cancel_pending"
            publication.set()
            if crash_publication:
                raise InjectedCrash("publisher died after receipt, before dispatch")
            return handle

    lab, owner, composition, spawner = writer_lab(tmp_path)
    coordinator = lab.store.coordination_store(composition=composition)
    child = coordinator.start_child(
        owner.root_id, "one", admission_of(owner, slot="one", generation=0)
    )
    lab.profiles.profile = CancellingProfile(
        ChildScript(marker='{"outcome":"done"}', effects='{"paths":[]}', sleep_s=30)
    )
    try:
        coordinator.drive_children(owner.root_id, 1, 1.5)
        assert publication.wait(5), "launch did not reach publication barrier"
        row = coordinator.recover_child(owner.root_id, "one", 0).children[0]
        assert row.state == "cancelled", row
        activation = lab.store.reads.list_activations(child.root_id)[0]
        assert activation.metadata.handle is not None
        assert (
            composition.for_root(child.root_id)
            .paths.receipt(activation.activation_id)
            .exists()
        )
        from workflow_interpreter.foreman.compose import WrapperLaunch
        from workflow_interpreter.foreman.constants import DISPATCH_REQUEST
        from workflow_interpreter.schema.decisions import CoordinationError
        from workflow_interpreter.supervisor.paths import ExecLedger, read_record

        wiring = composition.for_root(child.root_id)
        if not crash_publication:
            spawner.await_barrier(wiring, activation.activation_id)
        assert len(spawner.processes) == 1
        process = spawner.processes[0]
        process.join(timeout=5)
        assert not process.is_alive()
        assert process.exitcode is not None
        assert ExecLedger(wiring.paths.ledger(activation.activation_id)).count() == 1
        launch = read_record(
            wiring.paths.activation_dir(activation.activation_id) / DISPATCH_REQUEST,
            WrapperLaunch,
        )
        assert launch is not None
        with wiring.band, pytest.raises(CoordinationError, match="cancel"):
            wiring.store.mint_activation(child.root_id, launch.request)
        assert len(wiring.store.reads.list_activations(child.root_id)) == 1
        with pytest.raises(ValueError, match="cancel"):
            coordinator.collect_child(owner.root_id, "one", 0)
    finally:
        coordinator.recover_child(owner.root_id, "one", 0)
        for process in spawner.processes:
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=5)


@pytest.mark.proc
def test_confined_writer_collection(tmp_path: Path) -> None:
    lab, owner, composition, spawner = writer_lab(tmp_path, sandbox=SandboxMode.BWRAP)
    coordinator = lab.store.coordination_store(composition=composition)
    coordinator.start_child(
        owner.root_id, "one", admission_of(owner, slot="one", generation=0)
    )
    try:
        result = coordinator.drive_children(owner.root_id, 1, 5)
        receipt = coordinator.collect_child(owner.root_id, "one", 0)
        assert receipt.terminal == "done", result
    finally:
        for process in spawner.processes:
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=5)


@pytest.mark.proc
def test_nonwriting_child_collects_its_pinned_artifact_and_output(
    tmp_path: Path,
) -> None:
    lab, owner, composition, spawner = writer_lab(tmp_path, writing=False)
    lab.profiles.bind_node(
        "work",
        ChildScript(
            marker='{"outcome":"no_diff"}',
            effects='{"paths":[]}',
            artifact_path="answer.txt",
            artifact_body="answer",
        ),
    )
    coordinator = lab.store.coordination_store(composition=composition)
    coordinator.start_child(
        owner.root_id, "one", admission_of(owner, slot="one", generation=0)
    )
    try:
        coordinator.drive_children(owner.root_id, 1, 5)
        receipt = coordinator.collect_child(owner.root_id, "one", 0)
        assert receipt.artifact_commit == lab.head
        assert receipt.artifact_source == "activation-input"
        assert (
            lab.git.blob_text(f"{receipt.outputs_tree}:answer.txt", cwd=lab.repo)
            == "answer"
        )
    finally:
        for process in spawner.processes:
            process.join(timeout=5)
