"""Finding message templates for the semantic rules (spec v0.3.1 §2, §7, §10)."""

from __future__ import annotations

from typing import Final

MSG_DUPLICATE_NAME: Final[str] = "duplicate {kind} name {name!r} ({count} declarations)"
MSG_ENTRY_UNKNOWN: Final[str] = "entry {name!r} is not a declared node"
MSG_ENTRY_TERMINAL: Final[str] = (
    "entry {name!r} is a terminal; the graph would end before it starts"
)
# "edge" prefix, not a bare "{side} ...": without it this template's rendering is
# indistinguishable from MSG_ENTRY_UNKNOWN's, for a reader and for a test alike.
MSG_EDGE_ENDPOINT_UNKNOWN: Final[str] = "edge {side} {name!r} is not a declared node"
MSG_NODE_REGION_UNKNOWN: Final[str] = "node {node!r} names undeclared region {region!r}"
MSG_REGION_ENTRY_UNKNOWN: Final[str] = (
    "region {region!r} entry_node {name!r} is not a declared node"
)
MSG_REGION_ENTRY_FOREIGN: Final[str] = (
    "region {region!r} entry_node {name!r} belongs to region {actual!r}"
)
MSG_REGION_ENTRY_TERMINAL: Final[str] = (
    "region {region!r} entry_node {name!r} is a terminal; the region could "
    "never be entered (§2 rule 6)"
)
MSG_REGION_EMPTY: Final[str] = "region {region!r} has no member nodes"
MSG_REGION_ON_EXHAUSTED_UNKNOWN: Final[str] = (
    "region {region!r} on_exhausted {name!r} is not a declared node"
)
MSG_FALLBACK_UNKNOWN: Final[str] = "fallback target {name!r} is not a declared node"
MSG_FALLBACK_KIND: Final[str] = (
    "fallback target {name!r} is a {kind} node; §2 rule 4 requires a gate or terminal"
)
MSG_INPUT_UNKNOWN: Final[str] = (
    "node {node!r} consumes input {name!r} with no [[source]] entry"
)
MSG_PRODUCER_UNKNOWN: Final[str] = (
    "source {source!r} names producer node {name!r} which is not declared"
)
MSG_TRIM_PRIORITY: Final[str] = (
    "source {source!r} trim_priority must be >= 1, got {value}"
)
MSG_FIELD_REQUIRED: Final[str] = "{kind} node {node!r} must declare {field}"
MSG_FIELD_EMPTY: Final[str] = "{kind} node {node!r} declares an empty {field}"
MSG_FIELD_FORBIDDEN: Final[str] = "{kind} node {node!r} must not declare {field}"
MSG_FIELD_RANGE: Final[str] = "node {node!r} {field} must be >= {minimum}, got {value}"
MSG_OUTCOME_DUPLICATE: Final[str] = (
    "node {node!r} declares outcome {outcome!r} more than once"
)
MSG_OUTCOME_SYSTEM: Final[str] = (
    "node {node!r} declares system outcome {outcome!r}; "
    "system outcomes are wrapper-handled (§2)"
)
MSG_TERMINAL_EXIT: Final[str] = "terminal node {node!r} declares an outgoing edge"
MSG_EDGE_UNDECLARED: Final[str] = "node {node!r} does not declare outcome {outcome!r}"
MSG_EDGE_DUPLICATE: Final[str] = (
    "{count} edges declared for ({node!r}, {outcome!r}); exactly one is allowed"
)
MSG_EDGE_SYSTEM: Final[str] = (
    "edge on system outcome {outcome!r}; system outcomes are never edge-routed (§2)"
)
MSG_GATE_UNCOVERED: Final[str] = (
    "gate {node!r} declares outcome {outcome!r} with no edge"
)
MSG_REGION_MAX_ENTRIES: Final[str] = (
    "bounded-cycle region {region!r} must declare max_entries >= 1, got {value}"
)
MSG_REGION_ON_EXHAUSTED_REQUIRED: Final[str] = (
    "bounded-cycle region {region!r} must declare on_exhausted"
)
MSG_REGION_ON_EXHAUSTED_KIND: Final[str] = (
    "region {region!r} on_exhausted {name!r} is a {kind} node; "
    "exhaustion materializes a gate (§10.1)"
)
MSG_REGION_ACYCLIC_FIELD: Final[str] = (
    "acyclic region {region!r} must not declare {field}"
)
MSG_CYCLE_UNBOUNDED: Final[str] = (
    "cycle {members} is not confined to one bounded-cycle region (regions: {regions})"
)
MSG_BACK_EDGE: Final[str] = (
    "cycle {members} spans regions {regions}; the only legal cross-region cycle "
    "is one closed by a human-gate rebudget edge into a bounded-cycle "
    "entry_node (§2 rule 2)"
)
MSG_CROSS_REGION_INGRESS: Final[str] = (
    "edge {source} -{outcome}-> {target} enters region {region!r} at a node "
    "that is not its entry_node {entry_node!r}; the arrival would consume a "
    "round max_entries never counted (§2 rule 6, §10.1)"
)
MSG_CYCLE_MISSES_ENTRY_NODE: Final[str] = (
    "cycle {members} lies inside bounded-cycle region {region!r} but does not "
    "pass through its entry_node {entry_node!r}; max_entries would bound "
    "nothing (§10.1)"
)
MSG_NO_TERMINAL: Final[str] = "no terminal is reachable from node {node!r}"
MSG_NODE_UNREACHABLE: Final[str] = (
    "node {node!r} is not reachable from entry {entry!r} over the effective "
    "graph; it could never activate (§2 rule 6)"
)
MSG_PRODUCER_SELF: Final[str] = (
    "node {node!r} consumes non-optional input {name!r} it produces itself"
)
MSG_PRODUCER_NOT_DOMINATING: Final[str] = (
    "node {node!r} consumes non-optional input {name!r} whose producer {producer!r} "
    "does not run on every path from entry"
)
MSG_VERIFY_PATH: Final[str] = (
    "node {node!r} verify[{index}].{field} {value!r} is not repo-relative; "
    "a check outside the pinned repo cannot be provenance-hashed (§7.3)"
)
MSG_VERIFY_CMD_ARGV: Final[str] = (
    "node {node!r} verify[{index}].cmd does not split into a non-empty argv; "
    "the wrapper executes it without a shell (§2 rule 6)"
)
MSG_VERIFY_CMD_EXECUTABLE: Final[str] = (
    "node {node!r} verify[{index}] executable {executable!r} must be a "
    "repo-relative path; a PATH lookup or interpreter wrapper is not the "
    "provenance-hashed artifact (§2 rule 6, §7.3)"
)
MSG_VERIFY_TIMEOUT: Final[str] = (
    "node {node!r} verify[{index}] timeout {timeout} exceeds max_wall {max_wall}"
)
MSG_ALLOWED_PATHS_NON_WRITER: Final[str] = (
    "node {node!r} declares writes = false but non-empty allowed_paths"
)
MSG_ALLOWED_PATHS_WRITER: Final[str] = (
    "node {node!r} declares writes = true but no allowed_paths; "
    "every effect would need the runner to declare it (§7.5)"
)
MSG_MAX_TOTAL_ACTIVATIONS: Final[str] = (
    "max_total_activations must be >= 1, got {value}"
)
MSG_TEST_FLAG: Final[str] = (
    "test_force_first_reject = true requires loading with allow_test_flags (§13)"
)
MSG_VERIFY_SUBSET: Final[str] = (
    "judgment node {node!r} verify set is a subset of predecessor(s) {predecessor}; "
    "the anti-drift cross-check would be vacuous (§2 rule 7)"
)

MSG_TASK_UNINSTRUCTED: Final[str] = (
    "task node {node!r} carries no instructions; it will be refused at "
    "root creation and its runner would be told nothing about its job "
    "(ADR 0002)"
)
