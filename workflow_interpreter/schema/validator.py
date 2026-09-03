"""Semantic rule registry (spec v0.3.1 §2, §10).

Every rule is one function `(GraphIndex) -> list[Finding]`. Phase A establishes
referential integrity (names resolve); phase B assumes it and is skipped when
phase A reports an error, so a broken reference never cascades into a dozen
derived findings.
"""

from __future__ import annotations

from typing import Final

from workflow_interpreter.schema.graph_index import SemanticRule, build_index
from workflow_interpreter.schema.models import Finding, GraphDocument, Severity
from workflow_interpreter.schema.rules_flow import (
    bounded_cycle_cycles_include_entry_node,
    bounded_cycle_regions_bounded,
    cross_region_back_edge_illegal,
    cross_region_edges_target_entry,
    cycles_confined_to_bounded_cycle_regions,
    instance_bounds_valid,
    judgment_verify_superset,
    nodes_reachable_from_entry,
    non_optional_inputs_producible,
    terminal_reachable_from_every_node,
    test_flags_require_opt_in,
    verify_entries_well_formed,
)
from workflow_interpreter.schema.rules_nodes import (
    allowed_paths_well_formed,
    edge_outcome_declared_by_source,
    gate_outcomes_edge_covered,
    no_duplicate_edges,
    no_edges_on_system_outcomes,
    node_fields_match_kind,
    node_outcome_declarations_valid,
    task_nodes_instructed,
    terminals_have_no_exits,
)
from workflow_interpreter.schema.rules_references import (
    edge_endpoints_exist,
    entry_node_valid,
    fallback_targets_gate_or_terminal,
    input_names_resolve_to_sources,
    region_membership_valid,
    source_registry_well_formed,
    unique_names,
)

PHASE_A_RULES: Final[tuple[SemanticRule, ...]] = (
    unique_names,
    entry_node_valid,
    edge_endpoints_exist,
    region_membership_valid,
    fallback_targets_gate_or_terminal,
    input_names_resolve_to_sources,
    source_registry_well_formed,
)

PHASE_B_RULES: Final[tuple[SemanticRule, ...]] = (
    node_fields_match_kind,
    node_outcome_declarations_valid,
    terminals_have_no_exits,
    edge_outcome_declared_by_source,
    no_duplicate_edges,
    no_edges_on_system_outcomes,
    gate_outcomes_edge_covered,
    allowed_paths_well_formed,
    bounded_cycle_regions_bounded,
    cycles_confined_to_bounded_cycle_regions,
    cross_region_back_edge_illegal,
    cross_region_edges_target_entry,
    bounded_cycle_cycles_include_entry_node,
    terminal_reachable_from_every_node,
    nodes_reachable_from_entry,
    non_optional_inputs_producible,
    verify_entries_well_formed,
    instance_bounds_valid,
    test_flags_require_opt_in,
    judgment_verify_superset,
    task_nodes_instructed,
)


def validate_semantics(
    document: GraphDocument, *, allow_test_flags: bool
) -> list[Finding]:
    """Run every semantic rule; phase B is skipped when a reference does not resolve."""
    index = build_index(document, allow_test_flags=allow_test_flags)
    findings: list[Finding] = []
    for rule in PHASE_A_RULES:
        findings.extend(rule(index))
    if any(finding.severity is Severity.ERROR for finding in findings):
        return findings
    for rule in PHASE_B_RULES:
        findings.extend(rule(index))
    return findings
