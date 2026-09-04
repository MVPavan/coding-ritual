"""Semantic-rule tests driven by the mutation table (spec v0.3.1 §2).

One small edit to a valid graph per rule, plus the staging contract between
phase A (referential integrity) and phase B (graph shape and bounds).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._helpers import (
    JUDGMENT_FIXTURE,
    MINIMAL_GRAPH,
    REVIEW_VERIFY,
    WORK_EDGE,
    Replacements,
    mutate,
    write,
)
from tests._mutations import MUTATION_CASES
from workflow_interpreter import GraphValidationError, RuleId, load_graph


def test_minimal_graph_is_valid(tmp_path: Path) -> None:
    """The mutation base must be clean, or every mutation case proves nothing."""
    graph = load_graph(write(tmp_path, MINIMAL_GRAPH))

    assert graph.warnings == ()


@pytest.mark.parametrize(
    ("replacements", "rule"),
    [
        pytest.param(replacements, rule, id=case_id)
        for case_id, replacements, rule in MUTATION_CASES
    ],
)
def test_mutation_trips_exactly_its_rule(
    tmp_path: Path, replacements: Replacements, rule: RuleId
) -> None:
    """A small edit to a valid graph trips one named rule and no other."""
    path = write(tmp_path, mutate(MINIMAL_GRAPH, replacements))

    with pytest.raises(GraphValidationError) as excinfo:
        load_graph(path)

    assert excinfo.value.rule_ids == frozenset({rule})


def test_verify_cmd_may_carry_arguments(tmp_path: Path) -> None:
    """argv[0] carries the path constraint; later tokens are plain args (§2 rule 6)."""
    text = mutate(
        MINIMAL_GRAPH,
        (('cmd = "scripts/verify.sh"', 'cmd = "scripts/verify.sh --strict"'),),
    )

    graph = load_graph(write(tmp_path, text))

    assert graph.warnings == ()


def test_verify_subset_compares_whole_checks(tmp_path: Path) -> None:
    """Two checks sharing a `cmd` but differing in timeout are not the same check."""
    text = mutate(
        JUDGMENT_FIXTURE.read_text(encoding="utf-8"),
        ((REVIEW_VERIFY, 'verify = [{ cmd = "scripts/verify.sh", timeout = "3m" }]'),),
    )

    graph = load_graph(write(tmp_path, text))

    assert graph.warnings == ()


def test_verify_subset_warns_once_per_node(tmp_path: Path) -> None:
    """One vacuous cross-check is one warning, however many predecessors witness it.

    `work` gains a `no_diff` route into its own duplicate so that the second
    witness is reachable from the entry (nodes_reachable_from_entry).
    """
    text = mutate(
        JUDGMENT_FIXTURE.read_text(encoding="utf-8"),
        (('outcomes = ["done"]', 'outcomes = ["done", "no_diff"]'),),
    )
    predecessor = text[
        text.index('[[node]]\nname = "work"') : text.index('[[node]]\nname = "review"')
    ]
    text = mutate(
        text,
        (
            (
                predecessor,
                predecessor + predecessor.replace('name = "work"', 'name = "work2"'),
            ),
            (
                '[[edge]]\nfrom = "work"\non = "done"\nto = "review"\n',
                (
                    '[[edge]]\nfrom = "work"\non = "done"\nto = "review"\n\n'
                    '[[edge]]\nfrom = "work"\non = "no_diff"\nto = "work2"\n\n'
                    '[[edge]]\nfrom = "work2"\non = "done"\nto = "review"\n'
                ),
            ),
        ),
    )

    graph = load_graph(write(tmp_path, text))

    assert len(graph.warnings) == 1
    assert "work, work2" in graph.warnings[0].message


def test_gate_declaring_accept_is_not_a_judgment_node(tmp_path: Path) -> None:
    """Only task nodes run checks; a gate's empty check set is not a vacuous one."""
    text = mutate(
        MINIMAL_GRAPH,
        (
            ('outcomes = ["approve", "abandon"]', 'outcomes = ["accept", "abandon"]'),
            ('on = "approve"', 'on = "accept"'),
        ),
    )

    graph = load_graph(write(tmp_path, text))

    assert graph.warnings == ()


def test_phase_a_error_suppresses_phase_b(tmp_path: Path) -> None:
    """A dangling reference stops the run; phase-B rules never dereference it."""
    text = mutate(
        MINIMAL_GRAPH,
        (
            (WORK_EDGE, '[[edge]]\nfrom = "work"\non = "done"\nto = "nope"\n'),
            ("max_total_activations = 5", "max_total_activations = 0"),
        ),
    )

    path = write(tmp_path, text)

    with pytest.raises(GraphValidationError) as excinfo:
        load_graph(path)

    assert excinfo.value.rule_ids == frozenset({RuleId.EDGE_ENDPOINTS_EXIST})


def test_two_phase_b_violations_are_both_reported(tmp_path: Path) -> None:
    """Phase B reports every defect it finds, not the first."""
    text = mutate(
        MINIMAL_GRAPH,
        (
            ("max_total_activations = 5", "max_total_activations = 0"),
            ("token_budget = 1000", "token_budget = 0"),
        ),
    )

    path = write(tmp_path, text)

    with pytest.raises(GraphValidationError) as excinfo:
        load_graph(path)

    assert excinfo.value.rule_ids == frozenset(
        {RuleId.INSTANCE_BOUNDS_VALID, RuleId.NODE_FIELDS_MATCH_KIND}
    )


@pytest.mark.parametrize(
    "runner",
    [
        pytest.param('runner = "script:checks/route.sh"', id="unknown-prefix"),
        pytest.param('runner = "implementer"', id="bare-word"),
        pytest.param('runner = "profile:"', id="empty-role"),
    ],
)
def test_runner_must_be_a_profile_role_alias(tmp_path: Path, runner: str) -> None:
    """A runner the foreman's roles map could never resolve is refused at load.

    `profile:<role>` is the only spelling §3.1 binds; anything else used to
    pass validation and instantiation and die later at dispatch (cr-0jd).
    """
    path = write(tmp_path, mutate(MINIMAL_GRAPH, (('runner = "profile:x"', runner),)))

    with pytest.raises(GraphValidationError) as excinfo:
        load_graph(path)

    assert excinfo.value.rule_ids == frozenset({RuleId.SCHEMA})
