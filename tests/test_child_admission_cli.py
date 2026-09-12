"""Normal child admission resolves graph and configuration before reservation."""

import json
from pathlib import Path

from tests.test_children_process import writer_lab
from workflow_interpreter.foreman import __main__ as cli


def test_checked_admission_pins_distinct_children(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    lab, owner, composition, _ = writer_lab(tmp_path)
    monkeypatch.setattr(cli, "_composition", lambda path: composition)
    capsys.readouterr()
    roots = []
    for slot in ("one", "two"):
        assert (
            cli.main(
                [
                    "children",
                    "admit",
                    owner.root_id,
                    slot,
                    "--graph",
                    str(tmp_path / "writer.toml"),
                ]
            )
            == 0
        )
        result = json.loads(capsys.readouterr().out)
        assert result["admission_digest"]
        assert result["graph_hash"] == owner.definition.content_hash
        roots.append(result["receipt"]["root_id"])
    assert roots[0] != roots[1]
    assert len(lab.store.coordination_store().state(owner.root_id).children) == 2


def test_checked_admission_refuses_undeclared_input_without_reservation(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    lab, owner, composition, _ = writer_lab(tmp_path)
    monkeypatch.setattr(cli, "_composition", lambda path: composition)
    extra = tmp_path / "extra.txt"
    extra.write_text("not declared")
    before = lab.store.coordination_store().state(owner.root_id)
    capsys.readouterr()
    assert (
        cli.main(
            [
                "children",
                "admit",
                owner.root_id,
                "one",
                "--graph",
                str(tmp_path / "writer.toml"),
                "--input",
                f"extra={extra}",
            ]
        )
        == 2
    )
    assert "not declared" in capsys.readouterr().out
    assert lab.store.coordination_store().state(owner.root_id) == before


def test_raw_admission_cannot_smuggle_unresolved_model_pins(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from workflow_interpreter.foreman.decisions import admission_of

    lab, owner, composition, _ = writer_lab(tmp_path)
    monkeypatch.setattr(cli, "_composition", lambda _: composition)
    admission = admission_of(owner, slot="one", generation=0)
    settings = json.loads(admission.config_json)
    for setting in settings:
        if setting["key"].endswith(".model"):
            setting["value"] = "unresolved-authority"
    path = tmp_path / "forged.json"
    path.write_text(
        admission.model_copy(
            update={"config_json": json.dumps(settings)}
        ).model_dump_json()
    )
    capsys.readouterr()
    assert (
        cli.main(["children", "start", owner.root_id, "one", "--admission", str(path)])
        == 2
    )
    assert "pins" in capsys.readouterr().out
    assert not lab.store.coordination_store().state(owner.root_id).children
