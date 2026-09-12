"""Public integration commands use the real source admission and association."""

import json
import sys
from dataclasses import replace
from pathlib import Path

from tests.test_foreman_main import _bridge_adapter
from tests.test_integration_admission import source_lab
from workflow_interpreter.bdio.coordination import CoordinationStore
from workflow_interpreter.bridge.adapter import PhaseAdapter
from workflow_interpreter.bridge.integration import (
    IntegrationRequest,
    prepare_integration,
)
from workflow_interpreter.bridge.verification import CheckCommand
from workflow_interpreter.foreman import __main__ as cli
from workflow_interpreter.foreman.constants import MAX_TRANSCRIPT_BYTES
from workflow_interpreter.foreman.decisions import admission_of


def test_prepare_and_status(tmp_path: Path, monkeypatch, capsys) -> None:
    lab, owner, composition, source = source_lab(tmp_path)
    monkeypatch.setattr(
        PhaseAdapter, "from_config", classmethod(lambda *_: _bridge_adapter(lab))
    )
    monkeypatch.setattr(cli, "_composition", lambda _: composition)
    request = tmp_path / "request.json"
    request.write_text(
        IntegrationRequest(
            owner_id=owner.root_id,
            epic_id="phase",
            stage_id="stage",
            request_key="cli",
            sources=(("source", 0, source.receipt_digest),),
        ).model_dump_json()
    )
    capsys.readouterr()
    assert cli.main(["integration", "prepare", "--request", str(request)]) == 0
    record = json.loads(capsys.readouterr().out)
    assert cli.main(["integration", "status", "phase", "stage"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["bridge"]["root_id"] == record["root_id"]
    assert status["association"]["receipt"]["root_id"] == record["root_id"]


def test_status_summarizes_large_prepared_integration_without_wholesale_truncation(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """The public status survives bulky pinned policy and collected siblings."""

    lab, owner, composition, first = source_lab(tmp_path)
    coordinator = lab.store.coordination_store(composition=composition)
    coordinator.start_child(
        owner.root_id, "second", admission_of(owner, slot="second", generation=0)
    )
    driven = coordinator.drive_children(owner.root_id, 1, 8)
    assert not driven.timed_out, driven
    second = coordinator.collect_child(owner.root_id, "second", 0)
    for process in composition.spawner.processes:
        process.join(timeout=5)
        assert not process.is_alive()

    # The full bridge record serializes this admission-pinned policy.  It is
    # deliberately larger than Foreman's public transcript cap, while the
    # actual two collected source receipts and prepared integration stay real.
    composition = replace(
        composition,
        config=composition.config.model_copy(
            update={
                "bridge_checks": (
                    CheckCommand(
                        name="oversized-status-policy",
                        argv=(sys.executable, "-c", "x" * MAX_TRANSCRIPT_BYTES),
                    ),
                )
            }
        ),
    )
    monkeypatch.setattr(
        PhaseAdapter, "from_config", classmethod(lambda *_: _bridge_adapter(lab))
    )
    monkeypatch.setattr(cli, "_composition", lambda _: composition)
    request = tmp_path / "two-source-request.json"
    request.write_text(
        IntegrationRequest(
            owner_id=owner.root_id,
            epic_id="phase",
            stage_id="stage",
            request_key="large-status",
            sources=(
                ("source", 0, first.receipt_digest),
                ("second", 0, second.receipt_digest),
            ),
        ).model_dump_json()
    )
    prepared = prepare_integration(
        composition, IntegrationRequest.model_validate_json(request.read_text())
    )

    capsys.readouterr()
    assert cli.main(["integration", "status", "phase", "stage"]) == 0
    rendered = capsys.readouterr().out
    assert len(rendered.encode()) <= MAX_TRANSCRIPT_BYTES
    status = json.loads(rendered)
    assert status["association"]["identity_digest"]
    assert status["association"]["receipt"]["root_id"] == prepared.root_id
    assert status["bridge"]["root_id"] == prepared.root_id
    assert status["target"]["base_commit"]


def test_status_omits_bulky_max_sibling_records(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """A maximum sibling view cannot displace prepared target identities."""

    lab, owner, composition, first = source_lab(tmp_path)
    coordinator = lab.store.coordination_store(composition=composition)
    coordinator.start_child(
        owner.root_id, "second", admission_of(owner, slot="second", generation=0)
    )
    driven = coordinator.drive_children(owner.root_id, 1, 8)
    assert not driven.timed_out, driven
    second = coordinator.collect_child(owner.root_id, "second", 0)
    for process in composition.spawner.processes:
        process.join(timeout=5)
        assert not process.is_alive()
    monkeypatch.setattr(
        PhaseAdapter, "from_config", classmethod(lambda *_: _bridge_adapter(lab))
    )
    prepared = prepare_integration(
        composition,
        IntegrationRequest(
            owner_id=owner.root_id,
            epic_id="phase",
            stage_id="stage",
            request_key="large-siblings",
            sources=(
                ("source", 0, first.receipt_digest),
                ("second", 0, second.receipt_digest),
            ),
        ),
    )
    original_child_status = CoordinationStore.child_status

    def bulky_child_status(self, owner_id):
        view = original_child_status(self, owner_id)
        if owner_id != owner.root_id:
            return view
        prototype = view.children[0].model_copy(update={"attention": "x" * 2048})
        return view.model_copy(
            update={
                "children": tuple(
                    prototype.model_copy(
                        update={
                            "root_id": f"sibling-{index}",
                            "slot": f"sibling-{index}",
                        }
                    )
                    for index in range(5)
                )
            }
        )

    monkeypatch.setattr(CoordinationStore, "child_status", bulky_child_status)
    monkeypatch.setattr(cli, "_composition", lambda _: composition)
    capsys.readouterr()
    assert cli.main(["integration", "status", "phase", "stage"]) == 0
    rendered = capsys.readouterr().out
    assert len(rendered.encode()) <= MAX_TRANSCRIPT_BYTES
    status = json.loads(rendered)
    assert status["association"]["root_id"] == prepared.root_id
    assert status["bridge"]["root_id"] == prepared.root_id
    assert status["children"]["count"] == 5
    assert status["children"]["omitted"] == [
        "records",
        "attention",
        "collection",
        "cancellation",
        "contended_slots",
    ]


def test_retry_cli_uses_saved_owner_and_requires_fresh_approval(
    tmp_path, monkeypatch, capsys, signing_config, sign_payload
):
    from tests._supervisor import commit_all
    from tests.test_integration_lifecycle import approve_integration, prepared_lab
    from workflow_interpreter.foreman.tick import Foreman

    lab, owner, record = prepared_lab(
        tmp_path, monkeypatch, signing_config, sign_payload
    )
    approve_integration(lab, record)
    assert (
        Foreman(lab.composition)
        .run(record.root_id, poll_s=0.01, max_wall_s=10)
        .report.terminal
    )
    (lab.repo / "moved.txt").write_text("preserve")
    base = commit_all(lab.repo, "move target")
    monkeypatch.setattr(cli, "_composition", lambda _: lab.composition)
    capsys.readouterr()
    assert cli.main(["integration", "retry", "phase", "stage"]) == 0
    successor = json.loads(capsys.readouterr().out)
    assert successor["root_id"] != record.root_id
    assert successor["expected_base_commit"] == base
    assert successor["integration_owner"] == owner.root_id
    assert not lab.store.reads.list_gates(successor["root_id"])
    assert len(lab.store.coordination_store().state(owner.root_id).reservations) == 4
