"""Phase B rules about node shape, outcomes and edge declarations (spec v0.3.1 §2 rules 3, 4, 6)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Final

from workflow_interpreter.schema.graph_index import (
    GraphIndex,
    at,
    duplicates,
    finding_error,
    finding_warning,
    is_repo_relative,
    path,
)
from workflow_interpreter.schema.messages import (
    MSG_ALLOWED_PATH,
    MSG_ALLOWED_PATHS_NON_WRITER,
    MSG_ALLOWED_PATHS_WRITER,
    MSG_EDGE_DUPLICATE,
    MSG_EDGE_SYSTEM,
    MSG_EDGE_UNDECLARED,
    MSG_FIELD_EMPTY,
    MSG_FIELD_FORBIDDEN,
    MSG_FIELD_RANGE,
    MSG_FIELD_REQUIRED,
    MSG_GATE_UNCOVERED,
    MSG_OUTCOME_DUPLICATE,
    MSG_OUTCOME_SYSTEM,
    MSG_TASK_UNINSTRUCTED,
    MSG_TERMINAL_EXIT,
)
from workflow_interpreter.schema.models import (
    SYSTEM_OUTCOMES,
    Finding,
    NodeKind,
    RuleId,
)

_EXECUTION_FIELDS: Final[tuple[str, ...]] = (
    "runner",
    "model",
    "isolation",
    "writes",
    "allowed_paths",
    "inputs",
    "verify",
    "token_budget",
    "max_wall",
    "stale_after",
    "max_infra_retries",
    "max_steers",
)
_GATE_FIELDS: Final[tuple[str, ...]] = ("gate_type", "binds")
_TASK_REQUIRED: Final[tuple[str, ...]] = (
    "runner",
    "writes",
    "allowed_paths",
    "verify",
    "token_budget",
    "max_wall",
    "stale_after",
    "max_infra_retries",
    "max_steers",
    "outcomes",
)
_GATE_REQUIRED: Final[tuple[str, ...]] = ("gate_type", "binds", "outcomes")
_NON_EMPTY_FIELDS: Final[frozenset[str]] = frozenset({"verify", "outcomes"})
_MINIMUMS: Final[Mapping[str, int]] = {
    "token_budget": 1,
    "max_infra_retries": 0,
    "max_steers": 0,
}
_KIND_FORBIDDEN: Final[Mapping[NodeKind, tuple[str, ...]]] = {
    NodeKind.TASK: _GATE_FIELDS,
    # A gate's outcomes are all edge-covered, so its `fallback` could never
    # fire: dead config that cycle analysis would nonetheless have to model.
    NodeKind.GATE: (*_EXECUTION_FIELDS, "fallback"),
    NodeKind.TERMINAL: (*_EXECUTION_FIELDS, *_GATE_FIELDS, "outcomes", "fallback"),
}
_KIND_REQUIRED: Final[Mapping[NodeKind, tuple[str, ...]]] = {
    NodeKind.TASK: _TASK_REQUIRED,
    NodeKind.GATE: _GATE_REQUIRED,
    NodeKind.TERMINAL: (),
}


def node_fields_match_kind(index: GraphIndex) -> list[Finding]:
    """Per-kind required and forbidden fields (§2 rules 3 and 6).

    The schema accepts the union of all node fields so unknown keys stay a
    schema error; which subset a kind may carry is decided here.
    """
    findings: list[Finding] = []
    for position, node in enumerate(index.document.node):
        kind = node.kind.value
        for field in _KIND_REQUIRED[node.kind]:
            value = getattr(node, field)
            if value is None:
                findings.append(
                    finding_error(
                        RuleId.NODE_FIELDS_MATCH_KIND,
                        at("node", position, field),
                        MSG_FIELD_REQUIRED.format(
                            kind=kind, node=node.name, field=field
                        ),
                    )
                )
            elif field in _NON_EMPTY_FIELDS and len(value) == 0:
                findings.append(
                    finding_error(
                        RuleId.NODE_FIELDS_MATCH_KIND,
                        at("node", position, field),
                        MSG_FIELD_EMPTY.format(kind=kind, node=node.name, field=field),
                    )
                )
        for field in _KIND_FORBIDDEN[node.kind]:
            if getattr(node, field) is not None:
                findings.append(
                    finding_error(
                        RuleId.NODE_FIELDS_MATCH_KIND,
                        at("node", position, field),
                        MSG_FIELD_FORBIDDEN.format(
                            kind=kind, node=node.name, field=field
                        ),
                    )
                )
        for field, minimum in _MINIMUMS.items():
            value = getattr(node, field)
            if value is not None and value < minimum:
                findings.append(
                    finding_error(
                        RuleId.NODE_FIELDS_MATCH_KIND,
                        at("node", position, field),
                        MSG_FIELD_RANGE.format(
                            node=node.name, field=field, minimum=minimum, value=value
                        ),
                    )
                )
    return findings


def node_outcome_declarations_valid(index: GraphIndex) -> list[Finding]:
    """A node's declared outcomes are a duplicate-free set of graph outcomes (§2)."""
    findings: list[Finding] = []
    for position, node in enumerate(index.document.node):
        location = at("node", position, "outcomes")
        declared = node.outcomes or ()
        for name, _count in duplicates(item.value for item in declared):
            findings.append(
                finding_error(
                    RuleId.NODE_OUTCOME_DECLARATIONS_VALID,
                    location,
                    MSG_OUTCOME_DUPLICATE.format(node=node.name, outcome=name),
                )
            )
        for outcome in declared:
            if outcome in SYSTEM_OUTCOMES:
                findings.append(
                    finding_error(
                        RuleId.NODE_OUTCOME_DECLARATIONS_VALID,
                        location,
                        MSG_OUTCOME_SYSTEM.format(
                            node=node.name, outcome=outcome.value
                        ),
                    )
                )
    return findings


def terminals_have_no_exits(index: GraphIndex) -> list[Finding]:
    """Terminals have no exits (§2 rule 3)."""
    return [
        finding_error(
            RuleId.TERMINALS_HAVE_NO_EXITS,
            at("edge", position, "from"),
            MSG_TERMINAL_EXIT.format(node=edge.from_node),
        )
        for position, edge in enumerate(index.edges)
        if index.nodes[edge.from_node].kind is NodeKind.TERMINAL
    ]


def edge_outcome_declared_by_source(index: GraphIndex) -> list[Finding]:
    """An edge may only route an outcome its source node declares (§2 rule 4).

    System outcomes and terminal sources are left to the rules that own them,
    so a single defect never produces two findings.
    """
    findings: list[Finding] = []
    for position, edge in enumerate(index.edges):
        origin = index.nodes[edge.from_node]
        if edge.on in SYSTEM_OUTCOMES or origin.kind is NodeKind.TERMINAL:
            continue
        if origin.outcomes is None:
            continue
        if edge.on not in origin.outcomes:
            findings.append(
                finding_error(
                    RuleId.EDGE_OUTCOME_DECLARED_BY_SOURCE,
                    at("edge", position, "on"),
                    MSG_EDGE_UNDECLARED.format(
                        node=edge.from_node, outcome=edge.on.value
                    ),
                )
            )
    return findings


def no_duplicate_edges(index: GraphIndex) -> list[Finding]:
    """Exactly one edge per `(from, on)` — routing must be deterministic (§2 rule 4)."""
    pairs = Counter((edge.from_node, edge.on) for edge in index.edges)
    return [
        finding_error(
            RuleId.NO_DUPLICATE_EDGES,
            path("edge"),
            MSG_EDGE_DUPLICATE.format(count=count, node=node, outcome=outcome.value),
        )
        for (node, outcome), count in sorted(
            pairs.items(), key=lambda item: str(item[0])
        )
        if count > 1
    ]


def no_edges_on_system_outcomes(index: GraphIndex) -> list[Finding]:
    """System outcomes are never edge-routed (§2 'Outcome vocabulary', §10.2)."""
    return [
        finding_error(
            RuleId.NO_EDGES_ON_SYSTEM_OUTCOMES,
            at("edge", position, "on"),
            MSG_EDGE_SYSTEM.format(outcome=edge.on.value),
        )
        for position, edge in enumerate(index.edges)
        if edge.on in SYSTEM_OUTCOMES
    ]


def gate_outcomes_edge_covered(index: GraphIndex) -> list[Finding]:
    """Every gate outcome is edge-covered — a gate never falls back (§2 rule 3)."""
    routed = {(edge.from_node, edge.on) for edge in index.edges}
    findings: list[Finding] = []
    for position, node in enumerate(index.document.node):
        if node.kind is not NodeKind.GATE or node.outcomes is None:
            continue
        for outcome in node.outcomes:
            if outcome in SYSTEM_OUTCOMES:
                continue
            if (node.name, outcome) not in routed:
                findings.append(
                    finding_error(
                        RuleId.GATE_OUTCOMES_EDGE_COVERED,
                        at("node", position, "outcomes"),
                        MSG_GATE_UNCOVERED.format(
                            node=node.name, outcome=outcome.value
                        ),
                    )
                )
    return findings


def allowed_paths_well_formed(index: GraphIndex) -> list[Finding]:
    """`allowed_paths` is repo-relative and agrees with the node's write access.

    The set exempts paths from undeclared-effect reporting (§7.5); it does
    not bound what a node may write (ADR 0001).
    """
    findings: list[Finding] = []
    for position, node in enumerate(index.document.node):
        if node.allowed_paths is None:
            continue
        location = at("node", position, "allowed_paths")
        for path_index, value in enumerate(node.allowed_paths):
            if not is_repo_relative(value):
                findings.append(
                    finding_error(
                        RuleId.ALLOWED_PATHS_WELL_FORMED,
                        location,
                        MSG_ALLOWED_PATH.format(
                            node=node.name, index=path_index, value=value
                        ),
                    )
                )
        if node.writes is False and node.allowed_paths:
            findings.append(
                finding_error(
                    RuleId.ALLOWED_PATHS_WELL_FORMED,
                    location,
                    MSG_ALLOWED_PATHS_NON_WRITER.format(node=node.name),
                )
            )
        if node.writes is True and not node.allowed_paths:
            findings.append(
                finding_error(
                    RuleId.ALLOWED_PATHS_WELL_FORMED,
                    location,
                    MSG_ALLOWED_PATHS_WRITER.format(node=node.name),
                )
            )
    return findings


def forbidden_fields(kind: NodeKind) -> frozenset[str]:
    """The `Node` fields this kind may not carry (spec §2 rule 3).

    Public so configuration resolution can close its key vocabulary against
    the SAME table the validator enforces, rather than keeping a parallel list
    that drifts (spec §14, "closed resolved-config key vocabulary").
    """
    return frozenset(_KIND_FORBIDDEN[kind])


def task_nodes_instructed(index: GraphIndex) -> list[Finding]:
    """Warn when a task node does not state what it must do (ADR 0002).

    A warning, not an error: `create_root` is the enforcement chokepoint, and
    making this an error would reject every previously pinned body on read.
    This exists so the omission surfaces while authoring rather than at the
    moment an instance is created.
    """
    return [
        finding_warning(
            RuleId.TASK_NODES_INSTRUCTED,
            at("node", position, "instructions"),
            MSG_TASK_UNINSTRUCTED.format(node=node.name),
        )
        for position, node in enumerate(index.document.node)
        if node.kind is NodeKind.TASK and not (node.instructions or "").strip()
    ]
