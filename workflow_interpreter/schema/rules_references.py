"""Phase A rules: every name in the document resolves (spec v0.3.1 §2 rules 1, 4, 5).

These run first and short-circuit phase B, so a dangling reference produces one
finding rather than cascading through every rule that would dereference it.
"""

from __future__ import annotations

from workflow_interpreter.schema.graph_index import (
    GraphIndex,
    at,
    duplicates,
    finding_error,
    path,
    producer_node,
)
from workflow_interpreter.schema.messages import (
    MSG_DUPLICATE_NAME,
    MSG_EDGE_ENDPOINT_UNKNOWN,
    MSG_ENTRY_TERMINAL,
    MSG_ENTRY_UNKNOWN,
    MSG_FALLBACK_KIND,
    MSG_FALLBACK_UNKNOWN,
    MSG_INPUT_UNKNOWN,
    MSG_NODE_REGION_UNKNOWN,
    MSG_PRODUCER_UNKNOWN,
    MSG_REGION_EMPTY,
    MSG_REGION_ENTRY_FOREIGN,
    MSG_REGION_ENTRY_TERMINAL,
    MSG_REGION_ENTRY_UNKNOWN,
    MSG_REGION_ON_EXHAUSTED_UNKNOWN,
    MSG_TRIM_PRIORITY,
)
from workflow_interpreter.schema.models import Finding, NodeKind, RuleId


def unique_names(index: GraphIndex) -> list[Finding]:
    """Node, region and source names are keys; duplicates make every lookup ambiguous (§2)."""
    findings: list[Finding] = []
    for collection, names in (
        ("node", [node.name for node in index.document.node]),
        ("region", [region.name for region in index.document.region]),
        ("source", [source.name for source in index.document.source]),
    ):
        for name, count in duplicates(names):
            findings.append(
                finding_error(
                    RuleId.UNIQUE_NAMES,
                    path(collection),
                    MSG_DUPLICATE_NAME.format(kind=collection, name=name, count=count),
                )
            )
    return findings


def entry_node_valid(index: GraphIndex) -> list[Finding]:
    """Exactly one entry, and it must be able to execute (§2 rule 1)."""
    entry = index.document.graph.entry
    node = index.nodes.get(entry)
    if node is None:
        return [
            finding_error(
                RuleId.ENTRY_NODE_VALID,
                path("graph", "entry"),
                MSG_ENTRY_UNKNOWN.format(name=entry),
            )
        ]
    if node.kind is NodeKind.TERMINAL:
        return [
            finding_error(
                RuleId.ENTRY_NODE_VALID,
                path("graph", "entry"),
                MSG_ENTRY_TERMINAL.format(name=entry),
            )
        ]
    return []


def edge_endpoints_exist(index: GraphIndex) -> list[Finding]:
    """Both endpoints of every declared edge name a declared node (§2 rule 4)."""
    findings: list[Finding] = []
    for position, edge in enumerate(index.edges):
        for side, name in (("from", edge.from_node), ("to", edge.to)):
            if name not in index.nodes:
                findings.append(
                    finding_error(
                        RuleId.EDGE_ENDPOINTS_EXIST,
                        at("edge", position, side),
                        MSG_EDGE_ENDPOINT_UNKNOWN.format(side=side, name=name),
                    )
                )
    return findings


def region_membership_valid(index: GraphIndex) -> list[Finding]:
    """Region references resolve and each region owns its entry_node (§2, §10.1)."""
    findings: list[Finding] = []
    for position, node in enumerate(index.document.node):
        if node.region is not None and node.region not in index.regions:
            findings.append(
                finding_error(
                    RuleId.REGION_MEMBERSHIP_VALID,
                    at("node", position, "region"),
                    MSG_NODE_REGION_UNKNOWN.format(node=node.name, region=node.region),
                )
            )
    for position, region in enumerate(index.document.region):
        entry = index.nodes.get(region.entry_node)
        if entry is None:
            findings.append(
                finding_error(
                    RuleId.REGION_MEMBERSHIP_VALID,
                    at("region", position, "entry_node"),
                    MSG_REGION_ENTRY_UNKNOWN.format(
                        region=region.name, name=region.entry_node
                    ),
                )
            )
        elif entry.region != region.name:
            findings.append(
                finding_error(
                    RuleId.REGION_MEMBERSHIP_VALID,
                    at("region", position, "entry_node"),
                    MSG_REGION_ENTRY_FOREIGN.format(
                        region=region.name, name=region.entry_node, actual=entry.region
                    ),
                )
            )
        elif entry.kind is NodeKind.TERMINAL:
            findings.append(
                finding_error(
                    RuleId.REGION_MEMBERSHIP_VALID,
                    at("region", position, "entry_node"),
                    MSG_REGION_ENTRY_TERMINAL.format(
                        region=region.name, name=region.entry_node
                    ),
                )
            )
        if region.on_exhausted is not None and region.on_exhausted not in index.nodes:
            findings.append(
                finding_error(
                    RuleId.REGION_MEMBERSHIP_VALID,
                    at("region", position, "on_exhausted"),
                    MSG_REGION_ON_EXHAUSTED_UNKNOWN.format(
                        region=region.name, name=region.on_exhausted
                    ),
                )
            )
        if not index.members.get(region.name):
            findings.append(
                finding_error(
                    RuleId.REGION_MEMBERSHIP_VALID,
                    at("region", position, "name"),
                    MSG_REGION_EMPTY.format(region=region.name),
                )
            )
    return findings


def fallback_targets_gate_or_terminal(index: GraphIndex) -> list[Finding]:
    """Global and per-node fallbacks land on a gate or terminal (§2 rule 4)."""
    findings: list[Finding] = []
    targets: list[tuple[str, str]] = [
        (path("fallback", "to"), index.document.fallback.to)
    ]
    for position, node in enumerate(index.document.node):
        if node.fallback is not None:
            targets.append((at("node", position, "fallback.to"), node.fallback.to))
    for location, target in targets:
        target_node = index.nodes.get(target)
        if target_node is None:
            findings.append(
                finding_error(
                    RuleId.FALLBACK_TARGETS_GATE_OR_TERMINAL,
                    location,
                    MSG_FALLBACK_UNKNOWN.format(name=target),
                )
            )
        elif target_node.kind not in (NodeKind.GATE, NodeKind.TERMINAL):
            findings.append(
                finding_error(
                    RuleId.FALLBACK_TARGETS_GATE_OR_TERMINAL,
                    location,
                    MSG_FALLBACK_KIND.format(name=target, kind=target_node.kind.value),
                )
            )
    return findings


def input_names_resolve_to_sources(index: GraphIndex) -> list[Finding]:
    """Every `inputs` name resolves in `[[source]]`; an unknown name is a hard error (§2 rule 5)."""
    findings: list[Finding] = []
    for position, node in enumerate(index.document.node):
        for name in node.inputs or ():
            if name not in index.sources:
                findings.append(
                    finding_error(
                        RuleId.INPUT_NAMES_RESOLVE_TO_SOURCES,
                        at("node", position, "inputs"),
                        MSG_INPUT_UNKNOWN.format(node=node.name, name=name),
                    )
                )
    return findings


def source_registry_well_formed(index: GraphIndex) -> list[Finding]:
    """Producers resolve and the trim bound is usable (§2 rule 5)."""
    findings: list[Finding] = []
    for position, source in enumerate(index.document.source):
        producer = producer_node(source)
        if producer is not None and producer not in index.nodes:
            findings.append(
                finding_error(
                    RuleId.SOURCE_REGISTRY_WELL_FORMED,
                    at("source", position, "producer"),
                    MSG_PRODUCER_UNKNOWN.format(source=source.name, name=producer),
                )
            )
        if source.trim_priority < 1:
            findings.append(
                finding_error(
                    RuleId.SOURCE_REGISTRY_WELL_FORMED,
                    at("source", position, "trim_priority"),
                    MSG_TRIM_PRIORITY.format(
                        source=source.name, value=source.trim_priority
                    ),
                )
            )
    return findings
