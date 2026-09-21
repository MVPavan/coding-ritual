"""Explicit collected sources bind one original-owner integration member."""

import json
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Final

import pytest

from tests.test_children_process import writer_lab
from tests.test_foreman_main import _contractor_adapter, _contractor_stage
from workflow_interpreter.contractor import tracker_wiring as wiring_module
from workflow_interpreter.foreman.decisions import admission_of


def source_lab(tmp_path: Path):
    """One collected source child, on the caller's backend (run-ledger §3.2).

    `store` is a parameter because the §6 acceptance for this slice is that
    admission has no wall problem on the LEDGER and still works on bd: the
    30 s wall this file used to need is the bd round trip per tick, so the
    two runs are the measurement as much as the assertion.
    """
    from workflow_interpreter.inspector.sandbox import SandboxMode

    lab, owner, composition, spawner = writer_lab(
        tmp_path,
        sandbox=SandboxMode.BWRAP,
    )
    from workflow_interpreter.contractor.verification import CheckCommand

    composition = replace(
        composition,
        config=composition.config.model_copy(
            update={
                "contractor_checks": (
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
    # The stage bead goes into the SHARED file, because the forked children
    # read their own copy of it. On the ledger backend the run made no bd
    # write at all, so the file may not exist yet — its absence is "no rows",
    # not a failure.
    state = lab.fake_bd._state
    data = (
        json.loads(state.read_text()) if state.exists() else {"rows": {}, "next_id": 1}
    )
    data["rows"]["stage"] = _contractor_stage(
        "stage", description="Combine the collected work"
    )
    state.write_text(json.dumps(data))
    return lab, owner, composition, source


LEDGER_WALL_BUDGET_S: Final[float] = 7.5
"""What the same drill is allowed on the ledger. A quarter of the 30 s the bd
drill used to be given, asserted rather than claimed: the §6 acceptance for
this slice is that admission has no wall problem, and a budget nobody measures
is not a measurement."""


def test_replay_admits_only_one_original_owner_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replay converges on one member — and it converges on EITHER backend.

    Run on both because this is the §6 acceptance for the cutover: the test
    exists to prove the admission replay, and running it on the ledger proves
    the same replay without the per-tick bd round trip that made its wall
    budget flaky (`cr-xu34`).

    The ledger run is TIMED. In this file bd is the in-process double, so the
    number here bounds the engine's own work rather than the transport's; the
    round trips a real `bd` binary costs are measured by the real-bd rig
    (`tests/test_cutover_rig.py`).
    """
    from workflow_interpreter.contractor import integration

    started = time.monotonic()
    lab, owner, composition, source = source_lab(tmp_path)
    monkeypatch.setattr(
        wiring_module,
        "contractor_adapter",
        lambda *_, **__: _contractor_adapter(lab),
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
    # §3.2: the integration root is the owner's child, so the record that
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
    wall_s = time.monotonic() - started
    assert wall_s < LEDGER_WALL_BUDGET_S, (
        f"the ledger admission drill took {wall_s:.2f}s, over its "
        f"{LEDGER_WALL_BUDGET_S:.1f}s budget"
    )


@pytest.mark.parametrize("change", ["duplicate", "digest", "generation", "missing"])
def test_invalid_source_never_admits_integration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    from workflow_interpreter.contractor.errors import ContractorRefusal
    from workflow_interpreter.contractor.integration import (
        IntegrationRequest,
        prepare_integration,
    )
    from workflow_interpreter.schema.decisions import CoordinationError

    lab, owner, composition, source = source_lab(tmp_path)
    monkeypatch.setattr(
        wiring_module,
        "contractor_adapter",
        lambda *_, **__: _contractor_adapter(lab),
    )
    sources = (("source", 0, source.receipt_digest),)
    sources = {
        "duplicate": sources * 2,
        "digest": (("source", 0, "wrong"),),
        "generation": (("source", 1, source.receipt_digest),),
        "missing": (("missing", 0, source.receipt_digest),),
    }[change]
    before = lab.store.coordination_store().state(owner.root_id)
    with pytest.raises((ContractorRefusal, CoordinationError)):
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
    from workflow_interpreter.contractor.errors import ContractorRefusal
    from workflow_interpreter.contractor.integration import (
        IntegrationRequest,
        prepare_integration,
    )

    lab, owner, composition, source = source_lab(tmp_path)
    monkeypatch.setattr(
        wiring_module,
        "contractor_adapter",
        lambda *_, **__: _contractor_adapter(lab),
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
    with pytest.raises(ContractorRefusal, match="payload changed"):
        prepare_integration(
            composition,
            request.model_copy(update={"sources": (("source", 0, "changed"),)}),
        )
    assert lab.store.coordination_store().state(owner.root_id) == before


@pytest.mark.parametrize(
    "fault", ["association", "contractor", "reservation", "root", "child", "admission"]
)
def test_prepared_faults_repair_only_saved_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    from tests._fake_bd import InjectedCrash
    from workflow_interpreter.bdio import roots
    from workflow_interpreter.bdio.coordination import CoordinationStore
    from workflow_interpreter.contractor.adapter import ContractorAdapter
    from workflow_interpreter.contractor.integration import (
        IntegrationGuard,
        IntegrationRequest,
        prepare_integration,
    )

    lab, owner, composition, source = source_lab(tmp_path)
    monkeypatch.setattr(
        wiring_module,
        "contractor_adapter",
        lambda *_, **__: _contractor_adapter(lab),
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
        "contractor": (ContractorAdapter, "prepare"),
        "reservation": (CoordinationStore, "_reserve"),
        "root": (roots, "create_root"),
        "child": (CoordinationStore, "start_child"),
        "admission": (ContractorAdapter, "admit"),
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
    from workflow_interpreter.contractor.errors import ContractorRefusal
    from workflow_interpreter.contractor.integration import (
        IntegrationRequest,
        prepare_integration,
    )
    from workflow_interpreter.foreman.resolve import instantiate
    from workflow_interpreter.inspector.gitio import Git

    lab, owner, composition, source = source_lab(tmp_path)
    monkeypatch.setattr(
        wiring_module,
        "contractor_adapter",
        lambda *_, **__: _contractor_adapter(lab),
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
    with pytest.raises(ContractorRefusal, match="busy"):
        prepare_integration(
            composition, request.model_copy(update={"owner_id": other.root_id})
        )
    assert len(lab.store.coordination_store().state(other.root_id).reservations) == 1


@pytest.mark.parametrize(
    "failure", ["envelope", "capacity", "uncollected", "cancelled", "artifact-ref"]
)
def test_admission_limits_and_source_authority_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    from workflow_interpreter.contractor.errors import ContractorRefusal
    from workflow_interpreter.contractor.integration import (
        IntegrationRequest,
        prepare_integration,
    )
    from workflow_interpreter.foreman.envelope import EnvelopeRefusal
    from workflow_interpreter.schema.decisions import CoordinationError

    lab, owner, composition, source = source_lab(tmp_path)
    monkeypatch.setattr(
        wiring_module,
        "contractor_adapter",
        lambda *_, **__: _contractor_adapter(lab),
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
    with pytest.raises((ContractorRefusal, CoordinationError, EnvelopeRefusal)):
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
