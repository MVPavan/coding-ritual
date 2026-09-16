"""P5 ordinary workflow templates exercise real graph and root seams."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._foreman import ForemanLab
from tests._supervisor import ChildScript, commit_all
from workflow_interpreter import load_graph
from workflow_interpreter.bdio import Outcome
from workflow_interpreter.bridge.command import _bridge_graph
from workflow_interpreter.foreman.routing import route
from workflow_interpreter.schema.graph_index import build_index
from workflow_interpreter.schema.models import BindsMode, GateType, NodeKind
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

    lab = ForemanLab(tmp_path, toml=BASIC, sandbox=SandboxMode.BWRAP)
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
        sandbox=SandboxMode.BWRAP,
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


@pytest.mark.parametrize(
    "template", sorted(WORKFLOWS.glob("*.toml")), ids=lambda p: p.stem
)
def test_loaded_tasks_separate_local_evidence_from_mandatory_host_verify(
    template: Path,
) -> None:
    """Catch lost verification guidance at the loader seam, not model compliance.

    Removing a task's host gate, evidence slot, or environment/failure distinction
    must fail. These prose assertions do not prove that a model obeys them.
    """
    graph = load_graph(template)
    for node in graph.document.node:
        if node.kind is not NodeKind.TASK:
            continue
        assert node.verify, node.name
        text = " ".join((node.instructions or "").split())
        for clause in (
            "Your verdict is a claim",
            "full declared HOST verification remains mandatory and gates advancement",
            "available supported local checks",
            "command and result, or a not-run reason",
            "must not alone cause `fail_code` or `reject`",
            "Do not retry dependency installs",
            "Real code/test failures must be reported",
            "never relabeled as environment problems",
            "$WF_SCRATCH_DIR",
            "temporary repositories and caches",
        ):
            assert clause in text, (template.name, node.name, clause)
        for obsolete in (
            "after the pinned check passes",
            "after pinned checks pass",
            "when the verify command passes",
            "when the verify commands pass",
        ):
            assert obsolete not in text, (template.name, node.name, obsolete)
        if Outcome.ACCEPT in node.outcomes:
            assert "source/spec judgments" in text


@pytest.mark.parametrize(
    ("template", "expected"),
    [
        ("basic", {"write": ("scripts/verify-feature.sh",)}),
        (
            "design-spec",
            {
                "draft": ("scripts/verify-feature.sh",),
                "review": ("scripts/verify-feature.sh", "scripts/review-checks.sh"),
            },
        ),
        (
            "integration",
            {
                "integrate": ("scripts/verify-feature.sh",),
                "review": ("scripts/verify-feature.sh", "scripts/review-checks.sh"),
            },
        ),
        (
            "feature-delivery",
            {
                "implement": ("scripts/verify-feature.sh",),
                "review": ("scripts/verify-feature.sh", "scripts/review-checks.sh"),
            },
        ),
        (
            "engine-bootstrap",
            {
                "implement": ("scripts/verify-engine-bootstrap.sh",),
                "review": ("scripts/verify-engine-bootstrap.sh",),
            },
        ),
        (
            "pointer-handoff",
            {
                "implement": ("scripts/verify-pointer-handoff.sh",),
                "review": ("scripts/verify-pointer-handoff.sh",),
            },
        ),
        (
            "build-loop",
            {
                "write_tests": ("scripts/checks/tests-parse.sh",),
                "review_tests": (
                    "scripts/checks/tests-parse.sh",
                    "scripts/checks/assertion-strength.sh",
                ),
                "implement": (
                    "scripts/verify-feature.sh",
                    "scripts/checks/tests-untouched.sh",
                    "scripts/checks/mutate.sh",
                ),
                "review_impl": (
                    "scripts/checks/tests-parse.sh",
                    "scripts/checks/assertion-strength.sh",
                ),
                "critic": (
                    "scripts/checks/tests-parse.sh",
                    "scripts/checks/assertion-strength.sh",
                ),
            },
        ),
    ],
)
def test_local_guidance_preserves_declared_host_checks(
    template: str, expected: dict[str, tuple[str, ...]]
) -> None:
    """Moving obligations to the host must not drop any of its declared checks."""
    graph = load_graph(WORKFLOWS / f"{template}.toml")
    assert {
        node.name: tuple(check.cmd for check in node.verify or ())
        for node in graph.document.node
        if node.kind is NodeKind.TASK
    } == expected


@pytest.mark.parametrize(
    "template",
    [
        "feature-delivery",
        "engine-bootstrap",
        "pointer-handoff",
        "integration",
        "build-loop",
        "design-spec",
    ],
)
def test_review_evidence_guidance_matches_role_outcomes(template: str) -> None:
    """Instruction delivery/compatibility only; this cannot prove model judgment."""
    graph = load_graph(WORKFLOWS / f"{template}.toml")
    for node in graph.document.node:
        if node.kind is not NodeKind.TASK:
            continue
        text = " ".join((node.instructions or "").split())
        if Outcome.ACCEPT not in node.outcomes:
            assert "Evidence discipline:" not in text
            continue
        assert "Evidence discipline:" in text
        guidance = text.split("Evidence discipline:", 1)[1].split(
            "Your verdict is a claim", 1
        )[0]
        raw_guidance = (node.instructions or "").split("Evidence discipline:", 1)[1]
        raw_guidance = (
            "Evidence discipline:" + raw_guidance.split("Your verdict is a claim", 1)[0]
        )
        assert len(raw_guidance.encode("utf-8")) <= 900
        for clause in (
            "observed/source-proven",
            "producer-reported",
            "inference",
            "Source-proven defects reject without execution",
            "questions, not MAJOR",
            "tool absence",
            "remembered defaults",
            "file counts",
            "exact evidence",
            "candidate/tool version/environment",
            "failure scenario",
            "smallest non-mutating host command",
            "never auto-run requests",
            "required-evidence gaps",
            "never invent success or waive evidence",
            "review/evidence blockage",
            "existing attention/approval boundaries",
            "no automatic probe",
        ):
            assert clause in guidance, (template, node.name, clause)
        verdict = "fail_plan" if Outcome.FAIL_PLAN in node.outcomes else "reject"
        assert f"material gaps: `{verdict}`" in guidance
        if Outcome.FAIL_PLAN not in node.outcomes:
            assert "`fail_plan`" not in guidance
        expected_target = {
            "feature-delivery": {"review": "triage"},
            "engine-bootstrap": {"review": "triage"},
            "pointer-handoff": {"review": "triage"},
            "integration": {"review": "halt"},
            "design-spec": {"review": "halt"},
            "build-loop": {
                "review_tests": "triage_tests",
                "review_impl": "triage_build",
                "critic": "implement",
            },
        }[template][node.name]
        assert (
            route(
                build_index(graph.document, allow_test_flags=False),
                node,
                Outcome(verdict),
            ).target
            == expected_target
        )


def test_critic_distinguishes_tool_absence_from_material_evidence_blockage() -> None:
    """Pin the inline distinction; text checks do not prove model behavior."""
    graph = load_graph(WORKFLOWS / "build-loop.toml")
    critic = next(node for node in graph.document.node if node.name == "critic")
    text = " ".join((critic.instructions or "").split())
    assert "not alone cause `fail_code` or `reject`" in text
    assert (
        "An unresolved mandatory review-evidence gap still requires `reject`." in text
    )
    assert "otherwise `accept` only when no material evidence gap remains" in text


@pytest.mark.parametrize(
    ("template", "version"),
    [
        ("feature-delivery", "1.0.2"),
        ("engine-bootstrap", "1.0.2"),
        ("pointer-handoff", "1.0.2"),
        ("integration", "1.0.2"),
        ("build-loop", "1.0.3"),
        ("design-spec", "1.0.2"),
    ],
)
def test_reviewer_template_versions(template: str, version: str) -> None:
    """Instruction changes ship under a new version, leaving old pins intact."""
    assert load_graph(WORKFLOWS / f"{template}.toml").document.graph.version == version
