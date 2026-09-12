"""P5 ordinary workflow templates exercise real graph and root seams."""

from __future__ import annotations

from pathlib import Path

from tests._foreman import ForemanLab
from tests._supervisor import ChildScript, commit_all
from workflow_interpreter import load_graph
from workflow_interpreter.bdio import Outcome
from workflow_interpreter.bridge.command import _bridge_graph
from workflow_interpreter.schema.models import BindsMode, GateType
from workflow_interpreter.supervisor.models import SandboxMode

WORKFLOWS = Path(__file__).parents[1] / "workflows"
BASIC = WORKFLOWS / "basic.toml"
DESIGN_SPEC = WORKFLOWS / "design-spec.toml"


def test_basic_writer_returns_immutable_artifact_without_a_bridge(
    tmp_path: Path,
) -> None:
    """Removing the writer's commit or adding a gate must make this fail."""
    graph = load_graph(BASIC)
    writer = next(node for node in graph.document.node if node.name == "write")
    assert writer.writes is True
    assert writer.allowed_paths == ("src/**",)

    lab = ForemanLab(tmp_path, toml=BASIC, sandbox=SandboxMode.OFF)
    root = lab.instantiate_resolved()
    lab.profiles.next_script(
        ChildScript(
            marker='{"outcome":"done"}',
            effects='{"paths":["src/basic.py"]}',
            write_path="src/basic.py",
            write_body="value = 1\n",
            commit=True,
        )
    )

    lab.tick()
    lab.tick()

    activation = lab.store.reads.list_activations(root.root_id)[0]
    assert activation.metadata.outcome is Outcome.DONE
    assert activation.metadata.evidence is not None
    assert activation.metadata.evidence.artifact is not None
    assert lab.store.reads.list_gates(root.root_id) == ()


def test_design_spec_admits_and_exposes_only_the_existing_bridge_gate(
    tmp_path: Path,
    signing_config,
    sign_payload,
) -> None:
    """Removing review, widening its grant, or weakening ship must make this fail."""
    graph = load_graph(DESIGN_SPEC)
    nodes = {node.name: node for node in graph.document.node}

    assert nodes["draft"].writes is True
    assert nodes["draft"].allowed_paths == ("docs/**",)
    assert nodes["review"].writes is False
    assert nodes["review"].allowed_paths == ()
    assert nodes["ship"].gate_type is GateType.HUMAN
    assert nodes["ship"].binds is BindsMode.IMMUTABLE
    assert nodes["ship"].outcomes == (Outcome.APPROVE, Outcome.ABANDON)

    lab = ForemanLab(
        tmp_path,
        toml=DESIGN_SPEC,
        signing=signing_config,
        signer=sign_payload,
        sandbox=SandboxMode.OFF,
    )
    (lab.repo / "docs").mkdir()
    (lab.repo / "docs" / ".gitkeep").write_text("", encoding="utf-8")
    commit_all(lab.repo, "add design directory")
    root = lab.instantiate_resolved()

    assert _bridge_graph(lab.composition) == DESIGN_SPEC
    assert tuple(item.name for item in root.metadata.instance_inputs) == ("task_brief",)

    lab.profiles.next_script(
        ChildScript(
            marker='{"outcome":"done"}',
            effects='{"paths":["docs/design.md"]}',
            write_path="docs/design.md",
            write_body="# Design\n",
            commit=True,
        )
    )
    draft = lab.tick().dispatched
    assert draft is not None
    assert lab.tick().settled == draft

    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"accept"}', effects='{"paths":[]}')
    )
    review = lab.tick().dispatched
    assert review is not None
    assert lab.tick().settled == review
    reviewed = lab.store.reads.load_activation(review)
    assert reviewed.metadata.evidence is not None
    assert reviewed.metadata.evidence.artifact is None

    ship = lab.tick().opened_gate
    assert ship is not None
    assert lab.store.reads.load_gate(ship).metadata.gate_node == "ship"
    lab.approve(ship, Outcome.APPROVE)
    assert lab.tick().closed_gates == (ship,)
    assert lab.tick().terminal is True
