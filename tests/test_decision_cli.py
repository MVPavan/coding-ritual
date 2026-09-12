"""The actual Foreman command consumes decisions and reports coordination."""

import json
from pathlib import Path

import pytest

from tests._foreman import ForemanLab
from tests._supervisor import ChildScript
from tests.test_decision_lifecycle import FIXTURE
from workflow_interpreter.foreman import __main__ as cli
from workflow_interpreter.supervisor.models import SandboxMode


def test_create_run_status_includes_consumed_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lab = ForemanLab(
        tmp_path, toml=FIXTURE, instance_inputs={}, sandbox=SandboxMode.OFF
    )
    monkeypatch.setattr(cli, "_composition", lambda _: lab.composition)
    _, created = lab.transcript(
        lambda: cli.main(
            [
                "create",
                str(FIXTURE),
                "--instance-key",
                "cli-decision",
                "--allow-unsigned-gates",
            ]
        )
    )
    root_id = created.splitlines()[0]
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
    _, run = lab.transcript(lambda: cli.main(["run", root_id, "--max-wall", "3600"]))
    assert "ship" in run
    _, status = lab.transcript(lambda: cli.main(["status", root_id]))
    view = json.loads(status.splitlines()[0])
    assert view["coordination"]["requests"][0]["state"] == "applied"
    assert view["coordination"]["reserved_activation_capacity"] == 10
    assert view["open_gates"][0]["node"] == "ship"
