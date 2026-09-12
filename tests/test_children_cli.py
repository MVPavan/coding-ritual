"""Actual command parser and coordination reports."""

import json
from pathlib import Path

import pytest

from tests.test_children_lifecycle import child_admission, owner_lab
from workflow_interpreter.foreman import __main__ as cli


def test_cli_start_status_cancel_recover_and_refused_collection(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    lab, owner = owner_lab(tmp_path)
    monkeypatch.setattr(cli, "_composition", lambda path: lab.composition)
    admission = tmp_path / "admission.json"
    admission.write_text(child_admission(lab, owner).model_dump_json())
    assert (
        cli.main(["children", "start", owner, "one", "--admission", str(admission)])
        == 0
    )
    capsys.readouterr()
    assert cli.main(["children", "status", owner]) == 0
    status = json.loads(capsys.readouterr().out)
    assert len(status["children"]) == 1
    assert (
        cli.main(
            [
                "children",
                "cancel",
                owner,
                "one",
                "0",
                "--request-key",
                "stop",
                "--reason",
                "finished",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert cli.main(["children", "recover", owner, "one", "0"]) == 0
    assert json.loads(capsys.readouterr().out)["children"][0]["state"] == "cancelled"
    assert cli.main(["children", "collect", owner, "one", "0"]) == 2
    assert "cancel" in capsys.readouterr().out


@pytest.mark.parametrize(
    "arguments",
    [
        ["status", "../bad"],
        ["recover", "wf-1", "one", "-1"],
        ["drive", "wf-1", "--max-concurrent", "0", "--max-wall", "1"],
        ["drive", "wf-1", "--max-concurrent", "1", "--max-wall", "nan"],
    ],
)
def test_cli_refuses_malformed_bounds(
    tmp_path: Path, monkeypatch, capsys, arguments
) -> None:
    lab, _owner = owner_lab(tmp_path)
    monkeypatch.setattr(cli, "_composition", lambda path: lab.composition)
    assert cli.main(["children", *arguments]) == 2
    assert "refused" in capsys.readouterr().out


@pytest.mark.proc
def test_cli_drives_and_collects_real_writer(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from tests.test_children_process import writer_lab
    from workflow_interpreter.foreman.decisions import admission_of

    lab, owner, composition, spawner = writer_lab(tmp_path)
    monkeypatch.setattr(cli, "_composition", lambda path: composition)
    admission = tmp_path / "admission.json"
    admission.write_text(
        admission_of(owner, slot="one", generation=0).model_dump_json()
    )
    assert (
        cli.main(
            ["children", "start", owner.root_id, "one", "--admission", str(admission)]
        )
        == 0
    )
    capsys.readouterr()
    assert (
        cli.main(
            [
                "children",
                "drive",
                owner.root_id,
                "--max-concurrent",
                "1",
                "--max-wall",
                "5",
            ]
        )
        == 0
    )
    row = json.loads(capsys.readouterr().out)["children"][0]
    assert row["state"] == "settled"
    activation = lab.store.reads.load_activation(row["activation_id"])
    assert row["session_id"] == activation.metadata.session_id
    assert row["pid"] == activation.metadata.handle.pid
    assert row["proc_start_time"] == activation.metadata.handle.proc_start_time
    assert cli.main(["children", "collect", owner.root_id, "one", "0"]) == 0
    collected = json.loads(capsys.readouterr().out)
    assert collected["artifact_commit"] != lab.head
    assert len(collected["receipt_digest"]) == 64
    for process in spawner.processes:
        process.join(timeout=5)


def test_cli_does_not_disguise_programming_value_error(monkeypatch, capsys):
    def broken_composition(path):
        raise ValueError("programming defect")

    monkeypatch.setattr(cli, "_composition", broken_composition)
    assert cli.main(["children", "status", "wf-1"]) == 1
    output = capsys.readouterr()
    assert "programming defect" in output.err
    assert "refused" not in output.out
