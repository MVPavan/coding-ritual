"""`workflows/build-loop.toml` — the second live graph, pinned by its shape.

Phase 7 slice B closes build-loop's three dead ends: a `fail_code` nobody
routed, reviewers with no early abandon, and verify scripts that name checks
the repo does not ship. Each is a whole-graph property, so it is asserted
here — on the one authoring copy (phase 7 D3) — rather than discovered in a
live run.
"""

from __future__ import annotations

from typing import Final

from tests._helpers import BUILD_LOOP_CONTENT_HASH, BUILD_LOOP_GRAPH
from workflow_interpreter import RuleId, load_graph
from workflow_interpreter.schema.models import Outcome, Severity

# D7: reviewers run the two cheap tree checks only, so `critic`'s set EQUALS
# `review_impl`'s and the superset lint fires exactly once. `review_impl` is
# silent because its set is incomparable with `implement`'s, not a superset.
CRITIC_VERIFY_PATH: Final[str] = "$.node[4].verify"

# B2: a red check is a rework routed to the region's entry node, never a dead
# end. B3: a BLOCKER that stands twice ends the region at its triage gate.
FAIL_CODE_EDGES: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("write_tests", "write_tests"),
        ("review_tests", "write_tests"),
        ("implement", "implement"),
        ("review_impl", "implement"),
        ("critic", "implement"),
    }
)
# Every `fail_plan` edge, not only the reviewers' two: each region's writer
# already had one, and this is what says the set did not grow a stray route.
FAIL_PLAN_EDGES: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("write_tests", "triage_tests"),
        ("review_tests", "triage_tests"),
        ("implement", "triage_build"),
        ("review_impl", "triage_build"),
    }
)
REVIEWER_FAIL_PLAN_EDGES: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("review_tests", "triage_tests"),
        ("review_impl", "triage_build"),
    }
)

# B1: the critic's instructions name all six; before slice B its `inputs` did
# not declare `seam_contract`, `acceptance_tests` or `test_findings`.
CRITIC_INPUTS: Final[frozenset[str]] = frozenset(
    {
        "task_brief",
        "seam_contract",
        "acceptance_tests",
        "diff_artifact",
        "test_findings",
        "impl_findings",
    }
)


def _edges(outcome: Outcome) -> frozenset[tuple[str, str]]:
    """The (from, to) pairs of every declared edge carrying `outcome`."""
    graph = load_graph(BUILD_LOOP_GRAPH)
    return frozenset(
        (edge.from_node, edge.to) for edge in graph.document.edge if edge.on is outcome
    )


def test_the_graph_validates_with_only_the_expected_superset_warning() -> None:
    """No ERROR finding, and exactly the one warning D7 accepts (§2 rule 7)."""
    graph = load_graph(BUILD_LOOP_GRAPH)

    assert [
        (warning.severity, warning.rule, warning.location) for warning in graph.warnings
    ] == [
        (Severity.WARNING, RuleId.JUDGMENT_VERIFY_SUPERSET, CRITIC_VERIFY_PATH),
    ]


def test_the_graph_content_hash_is_stable() -> None:
    """The pin every live instance's body is checked against (§2 rule 8, §3.1)."""
    graph = load_graph(BUILD_LOOP_GRAPH)

    assert graph.content_hash == BUILD_LOOP_CONTENT_HASH


def test_every_fail_code_is_routed_to_its_region_entry() -> None:
    """A red check reworks; an unrouted `fail_code` is the ADR 0004 dead end."""
    assert _edges(Outcome.FAIL_CODE) == FAIL_CODE_EDGES


def test_both_reviewers_can_abandon_early() -> None:
    """`fail_plan` ends each region at its triage gate, not by running out of rounds."""
    edges = _edges(Outcome.FAIL_PLAN)

    assert edges == FAIL_PLAN_EDGES
    assert REVIEWER_FAIL_PLAN_EDGES <= edges


def test_the_critic_declares_every_input_its_instructions_name() -> None:
    """An input the runner is told to read but the node never binds is unreadable."""
    graph = load_graph(BUILD_LOOP_GRAPH)
    critic = next(node for node in graph.document.node if node.name == "critic")

    assert critic.inputs is not None
    assert frozenset(critic.inputs) == CRITIC_INPUTS
