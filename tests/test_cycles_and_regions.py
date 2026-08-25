"""Fixture-driven verdicts for the flow rules (spec v0.3.1 §2 rules 1, 2, 5, §10.1).

The corpus under `fixtures/` is dominated by cycle, region and reachability
cases — each file is named for the single rule it must trip (or, under
`valid/`, for the legal shape it must not trip), so the sweep below is the
contract for effective-transition analysis.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._helpers import (
    FIXTURES,
    INVALID_FIXTURES,
    VALID_FIXTURES,
    WARNING_FIXTURES,
    rule_of,
)
from workflow_interpreter import GraphValidationError, RuleId, Severity, load_graph


@pytest.mark.parametrize("path", VALID_FIXTURES, ids=lambda path: path.stem)
def test_valid_fixtures_load_without_findings(path: Path) -> None:
    """Legal graphs load clean — including acyclic flows that cross regions (§2 rule 2)."""
    graph = load_graph(path, allow_test_flags=True)

    assert graph.warnings == ()
    assert graph.content_hash


@pytest.mark.parametrize("path", INVALID_FIXTURES, ids=lambda path: path.stem)
def test_invalid_fixture_reports_exactly_its_rule(path: Path) -> None:
    """Each invalid fixture fails on its own rule and no other."""
    with pytest.raises(GraphValidationError) as excinfo:
        load_graph(path)

    error = excinfo.value
    assert error.rule_ids == frozenset({rule_of(path)})
    assert all(finding.severity is Severity.ERROR for finding in error.findings)


@pytest.mark.parametrize("path", WARNING_FIXTURES, ids=lambda path: path.stem)
def test_warning_fixture_loads_with_its_warning(path: Path) -> None:
    """A warning rule annotates the graph; it does not refuse it (§2 rule 7)."""
    graph = load_graph(path)

    assert [finding.rule for finding in graph.warnings] == [rule_of(path)]
    assert all(finding.severity is Severity.WARNING for finding in graph.warnings)


def test_test_flags_are_accepted_with_opt_in() -> None:
    """The same graph the loader refuses by default loads under allow_test_flags (§13)."""
    path = FIXTURES / "invalid" / f"{RuleId.TEST_FLAGS_REQUIRE_OPT_IN.value}.toml"

    graph = load_graph(path, allow_test_flags=True)

    assert graph.document.instance.test_force_first_reject is True
