"""Explicit collected sources bind one original-owner integration member."""

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from tests.test_children_process import writer_lab
from tests.test_foreman_main import _bridge_adapter, _bridge_stage
from workflow_interpreter.foreman.decisions import admission_of


def source_lab(tmp_path: Path):
    lab, owner, composition, spawner = writer_lab(tmp_path)
    from workflow_interpreter.bridge.verification import CheckCommand

    composition = replace(
        composition,
        config=composition.config.model_copy(
            update={
                "bridge_checks": (
                    CheckCommand(
                        name="checks",
                        argv=(
                            sys.executable,
                            "-c",
                            "from pathlib import Path; assert Path('src/feature.py').is_file()",
                        ),
                    ),
                )
            }
        ),
    )
    coordinator = lab.store.coordination_store(composition=composition)
    coordinator.start_child(
        owner.root_id, "source", admission_of(owner, slot="source", generation=0)
    )
    result = coordinator.drive_children(owner.root_id, 1, 8)
    assert not result.timed_out
    source = coordinator.collect_child(owner.root_id, "source", 0)
    for process in spawner.processes:
        process.join(timeout=5)
        assert not process.is_alive()
    data = json.loads(lab.fake_bd._state.read_text())
    data["rows"]["stage"] = _bridge_stage(
        "stage", description="Combine the collected work"
    )
    lab.fake_bd._state.write_text(json.dumps(data))
    return lab, owner, composition, source


def test_replay_admits_only_one_original_owner_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from workflow_interpreter.bridge import integration
    from workflow_interpreter.bridge.adapter import PhaseAdapter

    lab, owner, composition, source = source_lab(tmp_path)
    monkeypatch.setattr(
        PhaseAdapter, "from_config", classmethod(lambda *_: _bridge_adapter(lab))
    )
    request = integration.IntegrationRequest(
        owner_id=owner.root_id,
        epic_id="phase",
        stage_id="stage",
        request_key="combine",
        sources=(("source", 0, source.receipt_digest),),
    )
    first = integration.prepare_integration(composition, request)
    assert integration.prepare_integration(composition, request) == first
    state = lab.store.coordination_store().state(owner.root_id)
    assert len(state.children) == 2
    assert len(state.reservations) == 3
    assert state.active[first.integration_slot] == first.root_id
    root = lab.store.reads.load_root(first.root_id)
    assert root.metadata.coordination.owner_id == owner.root_id
    assert set(root.metadata.essential_inputs) == {
        "integration_sources",
        "stage_brief",
        "target_base",
    }


@pytest.mark.parametrize("change", ["duplicate", "digest", "generation", "missing"])
def test_invalid_source_never_admits_integration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    from workflow_interpreter.bridge.adapter import PhaseAdapter
    from workflow_interpreter.bridge.errors import BridgeRefusal
    from workflow_interpreter.bridge.integration import (
        IntegrationRequest,
        prepare_integration,
    )
    from workflow_interpreter.schema.decisions import CoordinationError

    lab, owner, composition, source = source_lab(tmp_path)
    monkeypatch.setattr(
        PhaseAdapter, "from_config", classmethod(lambda *_: _bridge_adapter(lab))
    )
    sources = (("source", 0, source.receipt_digest),)
    sources = {
        "duplicate": sources * 2,
        "digest": (("source", 0, "wrong"),),
        "generation": (("source", 1, source.receipt_digest),),
        "missing": (("missing", 0, source.receipt_digest),),
    }[change]
    before = lab.store.coordination_store().state(owner.root_id)
    with pytest.raises((BridgeRefusal, CoordinationError)):
        prepare_integration(
            composition,
            IntegrationRequest(
                owner_id=owner.root_id,
                epic_id="phase",
                stage_id="stage",
                request_key="combine",
                sources=sources,
            ),
        )
    assert lab.store.coordination_store().state(owner.root_id) == before


def test_changed_request_key_refuses_without_second_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from workflow_interpreter.bridge.adapter import PhaseAdapter
    from workflow_interpreter.bridge.errors import BridgeRefusal
    from workflow_interpreter.bridge.integration import (
        IntegrationRequest,
        prepare_integration,
    )

    lab, owner, composition, source = source_lab(tmp_path)
    monkeypatch.setattr(
        PhaseAdapter, "from_config", classmethod(lambda *_: _bridge_adapter(lab))
    )
    request = IntegrationRequest(
        owner_id=owner.root_id,
        epic_id="phase",
        stage_id="stage",
        request_key="combine",
        sources=(("source", 0, source.receipt_digest),),
    )
    prepare_integration(composition, request)
    before = lab.store.coordination_store().state(owner.root_id)
    with pytest.raises(BridgeRefusal, match="payload changed"):
        prepare_integration(
            composition,
            request.model_copy(update={"sources": (("source", 0, "changed"),)}),
        )
    assert lab.store.coordination_store().state(owner.root_id) == before


@pytest.mark.parametrize(
    "fault", ["association", "bridge", "reservation", "root", "child", "admission"]
)
def test_prepared_faults_repair_only_saved_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    from tests._fake_bd import InjectedCrash
    from workflow_interpreter.bdio import roots
    from workflow_interpreter.bdio.coordination import CoordinationStore
    from workflow_interpreter.bridge.adapter import PhaseAdapter
    from workflow_interpreter.bridge.integration import (
        IntegrationGuard,
        IntegrationRequest,
        prepare_integration,
    )

    lab, owner, composition, source = source_lab(tmp_path)
    monkeypatch.setattr(
        PhaseAdapter, "from_config", classmethod(lambda *_: _bridge_adapter(lab))
    )
    request = IntegrationRequest(
        owner_id=owner.root_id,
        epic_id="phase",
        stage_id="stage",
        request_key="combine",
        sources=(("source", 0, source.receipt_digest),),
    )
    cls, method = {
        "association": (IntegrationGuard, "save"),
        "bridge": (PhaseAdapter, "prepare"),
        "reservation": (CoordinationStore, "_reserve"),
        "root": (roots, "create_root"),
        "child": (CoordinationStore, "start_child"),
        "admission": (PhaseAdapter, "admit"),
    }[fault]
    original = getattr(cls, method)
    armed = True

    def crash(self, *args, **kwargs):
        nonlocal armed
        result = original(self, *args, **kwargs)
        if armed:
            armed = False
            raise InjectedCrash("saved boundary")
        return result

    monkeypatch.setattr(cls, method, crash)
    with pytest.raises(InjectedCrash):
        prepare_integration(composition, request)
    state = lab.store.coordination_store().state(owner.root_id)
    saved = state.integrations["combine"]
    assert saved.admission.slot == "integration.stage.1"
    result = prepare_integration(composition, request)
    assert (
        result.root_id
        == lab.store.coordination_store()
        .state(owner.root_id)
        .active["integration.stage.1"]
    )
    assert len(lab.store.coordination_store().state(owner.root_id).reservations) == 3
    if saved.receipt:
        assert saved.receipt.root_id == result.root_id


def test_other_owner_busy_before_target_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from workflow_interpreter.bridge.adapter import PhaseAdapter
    from workflow_interpreter.bridge.errors import BridgeRefusal
    from workflow_interpreter.bridge.integration import (
        IntegrationRequest,
        prepare_integration,
    )
    from workflow_interpreter.foreman.resolve import instantiate
    from workflow_interpreter.supervisor.gitio import Git

    lab, owner, composition, source = source_lab(tmp_path)
    monkeypatch.setattr(
        PhaseAdapter, "from_config", classmethod(lambda *_: _bridge_adapter(lab))
    )
    request = IntegrationRequest(
        owner_id=owner.root_id,
        epic_id="phase",
        stage_id="stage",
        request_key="combine",
        sources=(("source", 0, source.receipt_digest),),
    )
    prepare_integration(composition, request)
    other = instantiate(
        composition,
        lab._toml,
        instance_key="other",
        instance_inputs={},
        allow_test_flags=False,
        overrides={},
    )
    real_ref = Git.ref_target

    def no_snapshot(self, ref, *, cwd):
        if ref.startswith("refs/heads/"):
            pytest.fail("busy contender must not snapshot target")
        return real_ref(self, ref, cwd=cwd)

    monkeypatch.setattr(Git, "ref_target", no_snapshot)
    with pytest.raises(BridgeRefusal, match="busy"):
        prepare_integration(
            composition, request.model_copy(update={"owner_id": other.root_id})
        )
    assert len(lab.store.coordination_store().state(other.root_id).reservations) == 1


@pytest.mark.bd
def test_real_beads_roundtrips_integration_claim_and_one_root(
    tmp_path: Path, bd_config
) -> None:
    import subprocess
    from dataclasses import replace

    from workflow_interpreter.bdio import WorkflowStore
    from workflow_interpreter.bdio.client import BdClient
    from workflow_interpreter.bridge.integration import (
        IntegrationGuard,
        IntegrationRequest,
        prepare_integration,
    )
    from workflow_interpreter.bridge.verification import CheckCommand
    from workflow_interpreter.foreman.resolve import instantiate
    from workflow_interpreter.foreman.tick import Foreman

    lab, _, composition, spawner = writer_lab(tmp_path)
    store = WorkflowStore(BdClient(bd_config))
    composition = replace(
        composition,
        store=store,
        config=composition.config.model_copy(
            update={
                "bd": bd_config,
                "bridge_checks": (
                    CheckCommand(
                        name="source",
                        argv=(
                            sys.executable,
                            "-c",
                            "from pathlib import Path; assert Path('src/feature.py').is_file()",
                        ),
                    ),
                ),
            }
        ),
    )
    spawner.bind(composition)
    owner = instantiate(
        composition,
        lab._toml,
        instance_key="p4-real-owner-" + tmp_path.name,
        instance_inputs={},
        allow_test_flags=False,
        overrides={},
    )
    coordinator = store.coordination_store(composition=composition)
    child = coordinator.start_child(
        owner.root_id, "source", admission_of(owner, slot="source", generation=0)
    )
    try:
        result = Foreman(composition).run(child.root_id, poll_s=0.05, max_wall_s=30)
        assert result.report.terminal, result
        source = coordinator.collect_child(owner.root_id, "source", 0)

        def create(*args):
            return (
                subprocess.check_output(
                    ["bd", "create", *args, "--silent"],
                    cwd=bd_config.workspace,
                    timeout=30,
                )
                .decode()
                .strip()
            )

        epic = create("--title", "P4 isolated test", "--type", "epic")
        stage = create(
            "--title",
            "P4 isolated integration",
            "--parent",
            epic,
            "--description",
            "Combine the explicit source",
        )
        request = IntegrationRequest(
            owner_id=owner.root_id,
            epic_id=epic,
            stage_id=stage,
            request_key="real-integration",
            sources=(("source", 0, source.receipt_digest),),
        )
        record = prepare_integration(composition, request)
        assert prepare_integration(composition, request) == record
        state = coordinator.state(owner.root_id)
        assert len(state.children) == 2 and len(state.reservations) == 3
        claim = IntegrationGuard(composition).claim(
            state.integrations[request.request_key].target_key
        )
        assert (
            claim is not None
            and claim[1].association_digest == record.integration_digest
        )
    finally:
        for process in spawner.processes:
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=5)


@pytest.mark.parametrize(
    "failure", ["envelope", "capacity", "uncollected", "cancelled", "artifact-ref"]
)
def test_admission_limits_and_source_authority_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    from workflow_interpreter.bridge.adapter import PhaseAdapter
    from workflow_interpreter.bridge.errors import BridgeRefusal
    from workflow_interpreter.bridge.integration import (
        IntegrationRequest,
        prepare_integration,
    )
    from workflow_interpreter.foreman.envelope import EnvelopeRefusal
    from workflow_interpreter.schema.decisions import CoordinationError

    lab, owner, composition, source = source_lab(tmp_path)
    monkeypatch.setattr(
        PhaseAdapter, "from_config", classmethod(lambda *_: _bridge_adapter(lab))
    )
    coordinator = lab.store.coordination_store(composition=composition)
    sources = (("source", 0, source.receipt_digest),)
    if failure == "envelope":
        data = json.loads(lab.fake_bd._state.read_text())
        data["rows"]["stage"]["description"] = "x" * 62000
        lab.fake_bd._state.write_text(json.dumps(data))
    elif failure == "capacity":
        for slot in ("reserved-1", "reserved-2"):
            coordinator.start_child(
                owner.root_id, slot, admission_of(owner, slot=slot, generation=0)
            )
    elif failure in ("uncollected", "cancelled"):
        coordinator.start_child(
            owner.root_id, "pending", admission_of(owner, slot="pending", generation=0)
        )
        if failure == "cancelled":
            coordinator.cancel_child(
                owner.root_id, "pending", 0, "stop", "not a contribution"
            )
        sources = (("pending", 0, "no-collection"),)
    else:
        lab.git.update_ref(
            source.outputs_ref, owner.metadata.instance_base_commit, cwd=lab.repo
        )
    before = set(coordinator.state(owner.root_id).children)
    with pytest.raises((BridgeRefusal, CoordinationError, EnvelopeRefusal)):
        prepare_integration(
            composition,
            IntegrationRequest(
                owner_id=owner.root_id,
                epic_id="phase",
                stage_id="stage",
                request_key="combine",
                sources=sources,
            ),
        )
    assert set(coordinator.state(owner.root_id).children) == before
