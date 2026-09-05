"""Phase-6 slice A: a computed `fail_code` routes when the graph declares it.

Every routing test here runs through `tick()` on the fake-bd lab rather than
through `route()` alone: the dead end was enforced twice (frontier and
routing), so a pure-routing test could pass while the frontier still refused
the same activation a head.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._bdio import load_definition
from tests._foreman import ForemanLab
from tests._helpers import (
    AUTHORING_FIXTURE,
    FEATURE_DELIVERY_CONTENT_HASH,
    VALID_FIXTURE,
    undeclared_fail_code_graph,
)
from tests._supervisor import (
    REVIEW_SCRIPT,
    VERIFY_SCRIPT,
    ChildScript,
    commit_all,
)
from tests.conftest import Signer
from workflow_interpreter import load_graph
from workflow_interpreter.bdio import Outcome, SigningConfig
from workflow_interpreter.foreman.routing import RouteKind, route
from workflow_interpreter.schema.graph_index import build_index
from workflow_interpreter.supervisor.sandbox import SandboxMode

# A check whose bytes are constant — so its pinned digest keeps matching — and
# whose verdict depends on a file the runner may commit. That is the only way
# to make a check go red at a tick seam without also tripping §7.3 provenance.
RED_MARKER = "src/red.py"
REVIEW_RED_MARKER = "src/review_red.py"
RED_IF_MARKER = f"#!/bin/sh\ntest ! -f {RED_MARKER}\n"
REVIEW_RED_IF_MARKER = f"#!/bin/sh\ntest ! -f {REVIEW_RED_MARKER}\n"
REWRITTEN_CHECK = "#!/bin/sh\nexit 0\n# quietly rewritten\n"

FINDINGS_FILE = "review.md"


def _lab(
    tmp_path: Path,
    signing: SigningConfig,
    signer: Signer,
    *,
    toml: Path = VALID_FIXTURE,
    verify: str | None = None,
    review: str | None = None,
) -> ForemanLab:
    """A lab whose pinned check scripts are the ones this test needs.

    `sandbox = off`: this family stages its §7.3 cases by having the runner
    commit a rewritten `scripts/` check, which is outside every node's grants
    and which the §2 mount bound refuses before the provenance check is ever
    reached. The bound is proven elsewhere; what these assert is the layer
    above it.
    """
    lab = ForemanLab(
        tmp_path,
        toml=toml,
        signing=signing,
        signer=signer,
        sandbox=SandboxMode.OFF,
    )
    bodies = {VERIFY_SCRIPT: verify, REVIEW_SCRIPT: review}
    written = False
    for name, body in bodies.items():
        if body is None:
            continue
        path = lab.repo / name
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
        written = True
    if written:
        # The pins are taken from the repo at `instantiate`, and the checks are
        # executed from the checkout, so the scripts must be committed first.
        lab.head = commit_all(lab.repo, "lab check scripts")
    return lab


def _implement(lab: ForemanLab, script: ChildScript) -> str:
    """Run one `implement` activation to a settled close."""
    lab.profiles.next_script(script)
    activation_id = lab.tick().dispatched
    assert activation_id is not None
    assert lab.tick().settled == activation_id
    return activation_id


def _writes(path: str, *, body: str = "value = 2\n") -> ChildScript:
    """A writing runner that claims `done` after committing one declared file."""
    return ChildScript(
        marker='{"outcome":"done"}\n',
        effects=f'{{"paths":["{path}"]}}',
        write_path=path,
        write_body=body,
        commit=True,
    )


def _reviews(outcome: str, *, findings: bool = True) -> ChildScript:
    """A non-writing reviewer claiming `outcome`, with or without findings."""
    return ChildScript(
        marker=f'{{"outcome":"{outcome}"}}\n',
        effects='{"paths":[]}',
        artifact_path=FINDINGS_FILE if findings else None,
        artifact_body="the findings" if findings else "",
    )


def test_a_writers_computed_fail_code_takes_the_declared_self_edge(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """A red check on a `done` claim reworks the node instead of halting."""
    lab = _lab(tmp_path, signing_config, sign_payload, verify=RED_IF_MARKER)
    lab.instantiate()
    failed_id = _implement(lab, _writes(RED_MARKER))
    failed = lab.store.reads.load_activation(failed_id)
    assert failed.metadata.outcome is Outcome.FAIL_CODE
    assert failed.metadata.evidence is not None
    assert failed.metadata.evidence.claimed_outcome is Outcome.DONE

    report = lab.tick()

    assert report.opened_gate is None
    assert report.dispatched is not None
    reworked = lab.store.reads.load_activation(report.dispatched)
    assert reworked.metadata.node == "implement"
    assert reworked.metadata.predecessor_activation_id == failed_id


def test_a_reviewers_computed_fail_code_routes_back_to_implement(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """A red reviewer check is a rework, not a human halt."""
    lab = _lab(tmp_path, signing_config, sign_payload, review=REVIEW_RED_IF_MARKER)
    lab.instantiate()
    _implement(lab, _writes(REVIEW_RED_MARKER))
    lab.profiles.next_script(_reviews("accept"))
    review_id = lab.tick().dispatched
    assert review_id is not None
    assert lab.tick().settled == review_id
    reviewed = lab.store.reads.load_activation(review_id)
    assert reviewed.metadata.outcome is Outcome.FAIL_CODE
    assert reviewed.metadata.evidence is not None
    assert reviewed.metadata.evidence.claimed_outcome is Outcome.ACCEPT

    report = lab.tick()

    assert report.opened_gate is None
    assert report.dispatched is not None
    assert (
        lab.store.reads.load_activation(report.dispatched).metadata.node == "implement"
    )


def test_an_undeclared_fail_code_still_opens_a_halt_gate(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """§13 drill 25: a node that does not declare `fail_code` cannot route it."""
    graph = undeclared_fail_code_graph(tmp_path)
    lab = _lab(
        tmp_path,
        signing_config,
        sign_payload,
        toml=graph,
        verify=RED_IF_MARKER,
    )
    lab.instantiate()
    failed_id = _implement(lab, _writes(RED_MARKER))
    assert lab.store.reads.load_activation(failed_id).metadata.outcome is (
        Outcome.FAIL_CODE
    )

    gate_id = lab.tick().opened_gate

    assert gate_id is not None
    gate = lab.store.reads.load_gate(gate_id)
    assert gate.metadata.gate_node == "halt"
    assert gate.metadata.halt_reason == f"fail_code:implement:{failed_id}"


def test_a_declared_fail_code_without_an_edge_falls_back() -> None:
    """Declared but unrouted is the graph's fallback, never a dead end."""
    document = load_definition().document
    index = build_index(
        document.model_copy(
            update={
                "edge": tuple(
                    edge for edge in document.edge if edge.on is not Outcome.FAIL_CODE
                )
            }
        ),
        allow_test_flags=False,
    )

    decision = route(index, index.nodes["implement"], Outcome.FAIL_CODE)

    assert decision.kind is RouteKind.FALLBACK
    assert decision.target == "triage"


def test_review_fail_plan_survives_a_red_check_but_not_a_rewritten_one(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """§7.3 overwrites only success claims — except on verifier provenance."""
    lab = _lab(tmp_path, signing_config, sign_payload, review=REVIEW_RED_IF_MARKER)
    lab.instantiate()
    _implement(lab, _writes(REVIEW_RED_MARKER))
    lab.profiles.next_script(_reviews("fail_plan", findings=False))
    review_id = lab.tick().dispatched
    assert review_id is not None
    assert lab.tick().settled == review_id
    reviewed = lab.store.reads.load_activation(review_id)
    assert reviewed.metadata.outcome is Outcome.FAIL_PLAN
    assert reviewed.metadata.evidence is not None
    assert reviewed.metadata.evidence.artifact is None
    assert any(result.exit_code != 0 for result in reviewed.metadata.evidence.verify)
    gate_id = lab.tick().opened_gate
    assert gate_id is not None
    assert lab.store.reads.load_gate(gate_id).metadata.gate_node == "triage"


def test_a_rewritten_reviewer_check_overwrites_even_a_failure_claim(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """The examinee may not edit its examiner, whatever it claims (§7.3)."""
    lab = _lab(tmp_path, signing_config, sign_payload)
    lab.instantiate()
    _implement(
        lab,
        ChildScript(
            marker='{"outcome":"done"}\n',
            effects=f'{{"paths":["{REVIEW_SCRIPT}"]}}',
            write_path=REVIEW_SCRIPT,
            write_body=REWRITTEN_CHECK,
            commit=True,
        ),
    )
    lab.profiles.next_script(_reviews("fail_plan", findings=False))
    review_id = lab.tick().dispatched
    assert review_id is not None
    assert lab.tick().settled == review_id

    reviewed = lab.store.reads.load_activation(review_id)

    assert reviewed.metadata.outcome is Outcome.FAIL_CODE
    assert reviewed.metadata.evidence is not None
    assert reviewed.metadata.evidence.claimed_outcome is Outcome.FAIL_PLAN
    # 126: refused, not run — the §7.3 provenance verdict, not a red check.
    assert [
        result.exit_code
        for result in reviewed.metadata.evidence.verify
        if result.cmd == REVIEW_SCRIPT
    ] == [126]


def test_round_two_review_binds_round_one_findings(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """`review_findings` is the reviewer's own prior round (`inputs.py:87-93`)."""
    lab = _lab(tmp_path, signing_config, sign_payload)
    lab.instantiate()
    _implement(lab, _writes("src/feature.py"))
    lab.profiles.next_script(_reviews("reject"))
    first_review = lab.tick().dispatched
    assert first_review is not None
    assert lab.tick().settled == first_review
    _implement(lab, _writes("src/feature.py", body="value = 3\n"))
    second_review = lab.tick().dispatched
    assert second_review is not None

    bound = lab.store.reads.load_activation(second_review).metadata.inputs

    assert {binding.name for binding in bound} == {
        "task_brief",
        "diff_artifact",
        "review_findings",
    }
    findings = next(binding for binding in bound if binding.name == "review_findings")
    assert findings.producer_activation_id == first_review


@pytest.mark.parametrize("path", [VALID_FIXTURE, AUTHORING_FIXTURE])
def test_both_copies_of_the_graph_still_validate(path: Path) -> None:
    """Slice A's edits keep both copies free of ERROR findings (§2 rule 8)."""
    graph = load_graph(path)

    assert graph.warnings == ()
    assert graph.content_hash == FEATURE_DELIVERY_CONTENT_HASH
