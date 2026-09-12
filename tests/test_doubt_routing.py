"""Declared doubt uses the ordinary identity-bound decision execution."""

from pathlib import Path

from tests._foreman import ForemanLab
from tests._supervisor import ChildScript
from workflow_interpreter.supervisor.models import SandboxMode


def test_doubt_continues_only_its_declared_edge(tmp_path: Path) -> None:
    graph = tmp_path / "doubt.toml"
    graph.write_text(
        Path("workflow_interpreter/fixtures/valid/bounded-decision.toml")
        .read_text()
        .replace('"fail_plan"', '"doubt"')
    )
    lab = ForemanLab(
        tmp_path / "lab", toml=graph, instance_inputs={}, sandbox=SandboxMode.OFF
    )
    root = lab.instantiate_resolved()
    lab.profiles.bind_node(
        "assess", ChildScript(marker='{"outcome":"doubt"}', effects='{"paths":[]}')
    )
    lab.profiles.bind_node(
        "work", ChildScript(marker='{"outcome":"no_diff"}', effects='{"paths":[]}')
    )
    lab.profiles.decision_action = "continue_declared"
    result = lab.foreman.run(root.root_id, poll_s=0.01, max_wall_s=3600)
    assert result.report.opened_gate or result.report.waiting_gate, result
    requests = lab.store.coordination_store().coordination_view(root.root_id).requests
    assert len(requests) == 1
    assert requests[0].boundary.kind == "doubt"
    assert requests[0].state == "applied"
    assert [t.node for t in lab.profiles.profile.tasks] == ["assess", "decide", "work"]


import pytest


def test_writing_doubt_child_exposes_ship_and_settles_after_approval(
    tmp_path: Path, monkeypatch, capsys, signing_config, sign_payload
) -> None:
    import json

    from workflow_interpreter.foreman import __main__ as cli
    from workflow_interpreter.foreman.decisions import admission_of
    from workflow_interpreter.schema.models import Outcome

    graph = tmp_path / "writing-doubt.toml"
    text = Path("workflow_interpreter/fixtures/valid/bounded-decision.toml").read_text()
    text = text.replace('"fail_plan"', '"doubt"')
    start = text.index('name = "work"')
    end = text.index("[[node]]", start)
    work = text[start:end].replace("writes = false", "writes = true")
    work = work.replace("allowed_paths = []", 'allowed_paths = ["src/**"]')
    work = work.replace('outcomes = ["no_diff"]', 'outcomes = ["done"]')
    text = (text[:start] + work + text[end:]).replace(
        'from = "work"\non = "no_diff"', 'from = "work"\non = "done"'
    )
    graph.write_text(text)
    lab = ForemanLab(
        tmp_path / "lab",
        toml=graph,
        instance_inputs={},
        sandbox=SandboxMode.OFF,
        signing=signing_config,
        signer=sign_payload,
    )
    owner = lab.instantiate_resolved()
    coordinator = lab.store.coordination_store(composition=lab.composition)
    child = coordinator.start_child(
        owner.root_id, "doubt", admission_of(owner, slot="doubt", generation=0)
    )
    lab.root = lab.store.reads.load_root(child.root_id)
    lab.profiles.bind_node(
        "assess", ChildScript(marker='{"outcome":"doubt"}', effects='{"paths":[]}')
    )
    lab.profiles.bind_node(
        "work",
        ChildScript(
            marker='{"outcome":"done"}',
            effects='{"paths":["src/child_doubt.py"]}',
            write_path="src/child_doubt.py",
            write_body="DOUBT = 'resolved'\n",
            commit=True,
        ),
    )
    lab.profiles.decision_action = "continue_declared"
    result = lab.foreman.run(child.root_id, poll_s=0.01, max_wall_s=3600)
    assert result.report.opened_gate or result.report.waiting_gate, result
    (request,) = coordinator.state(owner.root_id).requests.values()
    assert request.state == "applied" and request.boundary.kind == "doubt"
    monkeypatch.setattr(cli, "_composition", lambda _: lab.composition)
    capsys.readouterr()
    assert cli.main(["status", child.root_id]) == 0
    status = json.loads(capsys.readouterr().out)
    (gate,) = status["open_gates"]
    assert gate["node"] == "ship"
    assert status["terminal"] is None and status["root_state"] == "open"
    work_activation = max(
        lab.store.reads.list_activations(child.root_id), key=lambda a: a.metadata.seq
    )
    assert work_activation.bead.status == "closed"
    assert (
        work_activation.metadata.evidence.artifact.commit_oid
        == status["instance_branch_head"]
    )
    assert lab.foreman.tick(child.root_id).waiting_gate == gate["gate_id"]
    lab.approve(gate["gate_id"], Outcome.APPROVE)
    assert lab.foreman.run(child.root_id, poll_s=0.01, max_wall_s=3600).report.terminal
    collected = coordinator.collect_child(owner.root_id, "doubt", 0)
    assert collected.terminal == "done"
    assert collected.artifact_commit == status["instance_branch_head"]
    assert [t.node for t in lab.profiles.profile.tasks] == ["assess", "decide", "work"]


@pytest.mark.parametrize(
    "outcome,terminal,requests",
    [("fail_plan", "abandoned", 0), ("no_diff", None, 0), ("doubt", None, 1)],
)
def test_doubt_is_distinct_from_fail_plan_and_ordinary_acceptance(
    tmp_path: Path, outcome: str, terminal: str | None, requests: int
) -> None:
    graph = tmp_path / "distinct.toml"
    text = (
        Path("workflow_interpreter/fixtures/valid/bounded-decision.toml")
        .read_text()
        .replace('"fail_plan"', '"doubt"')
    )
    text = text.replace(
        'outcomes = ["doubt", "no_diff"]',
        'outcomes = ["doubt", "fail_plan", "no_diff"]',
    )
    text += '\n[[edge]]\nfrom="assess"\non="fail_plan"\nto="abandoned"\n'
    graph.write_text(text)
    lab = ForemanLab(
        tmp_path / "lab", toml=graph, instance_inputs={}, sandbox=SandboxMode.OFF
    )
    root = lab.instantiate_resolved()
    lab.profiles.bind_node(
        "assess",
        ChildScript(marker='{"outcome":"' + outcome + '"}', effects='{"paths":[]}'),
    )
    lab.profiles.bind_node(
        "work", ChildScript(marker='{"outcome":"no_diff"}', effects='{"paths":[]}')
    )
    lab.profiles.decision_action = "continue_declared"
    report = lab.foreman.run(root.root_id, poll_s=0.01, max_wall_s=3600).report
    assert report.terminal_node == terminal
    assert len(lab.store.coordination_store().state(root.root_id).requests) == requests
