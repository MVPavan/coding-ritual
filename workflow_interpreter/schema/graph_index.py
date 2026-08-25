"""Resolved lookups and graph algorithms shared by the semantic rules (spec v0.3.1 §2)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Container, Iterable, Mapping
from typing import Final

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.schema.models import (
    EXEMPT_BACK_EDGE_OUTCOME,
    PRODUCER_NODE_PREFIX,
    Edge,
    Finding,
    GateType,
    GraphDocument,
    Node,
    NodeKind,
    Region,
    RegionMode,
    RuleId,
    Severity,
    Source,
    VerifyCheck,
)

_DURATION_UNIT_SECONDS: Final[Mapping[str, int]] = {
    "s": 1,
    "m": 60,
    "h": 3600,
    "d": 86400,
}
_PARENT_SEGMENT: Final[str] = ".."
_PATH_SEPARATOR: Final[str] = "/"
_HOME_PREFIX: Final[str] = "~"
_ROOT_PATH: Final[str] = "$"

UNREGIONED: Final[str] = "(unregioned)"
"""Display name for nodes belonging to no region."""


class GraphIndex(BaseModel):
    """Resolved lookups shared by every rule."""

    model_config = ConfigDict(
        frozen=True, extra="forbid", arbitrary_types_allowed=False
    )

    document: GraphDocument
    allow_test_flags: bool
    nodes: dict[str, Node]
    regions: dict[str, Region]
    sources: dict[str, Source]
    members: dict[str, tuple[str, ...]]

    @property
    def edges(self) -> tuple[Edge, ...]:
        """Declared edges."""
        return self.document.edge


SemanticRule = Callable[[GraphIndex], list[Finding]]


def build_index(document: GraphDocument, *, allow_test_flags: bool) -> GraphIndex:
    """Build the lookup tables the rules run against."""
    members: dict[str, tuple[str, ...]] = {}
    for region in document.region:
        members[region.name] = tuple(
            node.name for node in document.node if node.region == region.name
        )
    return GraphIndex(
        document=document,
        allow_test_flags=allow_test_flags,
        nodes={node.name: node for node in document.node},
        regions={region.name: region for region in document.region},
        sources={source.name: source for source in document.source},
        members=members,
    )


def finding_error(rule: RuleId, location: str, message: str) -> Finding:
    """Build a blocking finding."""
    return Finding(
        rule=rule, severity=Severity.ERROR, location=location, message=message
    )


def finding_warning(rule: RuleId, location: str, message: str) -> Finding:
    """Build an advisory finding."""
    return Finding(
        rule=rule, severity=Severity.WARNING, location=location, message=message
    )


def at(collection: str, index: int, field: str | None = None) -> str:
    """Address a position inside one of the document's arrays, as JSONPath.

    One location dialect across both stages: `jsonschema` emits `$.node[0].name`
    and every semantic finding must read the same way.
    """
    suffix = f".{field}" if field else ""
    return f"{_ROOT_PATH}.{collection}[{index}]{suffix}"


def path(*parts: str) -> str:
    """Address a scalar member such as `$.graph.entry` or a whole array."""
    return ".".join((_ROOT_PATH, *parts))


def duplicates(names: Iterable[str]) -> list[tuple[str, int]]:
    """Names occurring more than once, with their counts, in stable order."""
    return sorted((name, count) for name, count in Counter(names).items() if count > 1)


def duration_seconds(value: str) -> int:
    """Convert a schema-validated duration such as `45m` into seconds."""
    return int(value[:-1]) * _DURATION_UNIT_SECONDS[value[-1]]


def is_repo_relative(value: str) -> bool:
    """True when a declared path stays inside the repo (no absolute or escaping form)."""
    if value.startswith(("/", _HOME_PREFIX)):
        return False
    return _PARENT_SEGMENT not in value.split(_PATH_SEPARATOR)


def is_repo_relative_executable(value: str) -> bool:
    """True when an argv[0] token names a file inside the repo (§2 rule 6, §7.3).

    Stricter than `is_repo_relative`: a token carrying no separator (`bash`,
    `env`) is resolved through PATH at exec time, so it denotes whatever the
    runtime host happens to install rather than the provenance-hashed artifact
    the pin covers.
    """
    return is_repo_relative(value) and _PATH_SEPARATOR in value


def producer_node(source: Source) -> str | None:
    """The node name behind a `node:<name>` producer, or None for `instance`."""
    if source.producer.startswith(PRODUCER_NODE_PREFIX):
        return source.producer[len(PRODUCER_NODE_PREFIX) :]
    return None


def is_exempt_back_edge(index: GraphIndex, edge: Edge) -> bool:
    """The §2 rule 2 exemption: human-gate `rebudget` into a bounded-cycle entry_node."""
    if edge.on is not EXEMPT_BACK_EDGE_OUTCOME:
        return False
    origin = index.nodes[edge.from_node]
    if origin.kind is not NodeKind.GATE or origin.gate_type is not GateType.HUMAN:
        return False
    return any(
        region.mode is RegionMode.BOUNDED_CYCLE and region.entry_node == edge.to
        for region in index.document.region
    )


def successors(index: GraphIndex, *, skip_exempt: bool = False) -> dict[str, list[str]]:
    """Adjacency over declared edges, optionally dropping the exempt back-edge."""
    adjacency: dict[str, list[str]] = {name: [] for name in index.nodes}
    for edge in index.edges:
        if skip_exempt and is_exempt_back_edge(index, edge):
            continue
        adjacency[edge.from_node].append(edge.to)
    return adjacency


def effective_successors(
    index: GraphIndex, *, skip_exempt: bool = False
) -> dict[str, list[str]]:
    """Every transition the runtime can actually take (§2 rules 2 and 5).

    Declared edges ∪ per-node fallback ∪ region `on_exhausted` ∪ global
    fallback. Reachability, dominance AND cycle analysis run over this graph:
    a declared-edges-only view misses the routes that bypass a producer and
    the runtime cycles a fallback edge closes.

    The exhaustion edge is modeled from a bounded-cycle region's `entry_node`
    ONLY — rounds are counted there (§10.1), so exhaustion cannot fire before
    the entry node ran. Emitting it from every member invents routes that skip
    the entry: fail-open for reachability, fail-wrong for dominance (probed).

    The §10.5 no-progress transition (a member exhausting its rounds without
    re-entering `entry_node`) needs no edge of its own: a member that can repeat
    at all sits on a cycle, and `bounded_cycle_cycles_include_entry_node` forces
    that cycle through `entry_node`, so the modeled exhaustion edge already
    covers it — transitively verified over 3,595 graphs (phase-1 r3).

    `skip_exempt` drops the §2 rule 2 exempt DECLARED back-edges; the routes
    invented here are never exempt — a fallback-routed edge never qualifies.
    """
    adjacency = successors(index, skip_exempt=skip_exempt)
    for node in index.document.node:
        if node.kind is NodeKind.TASK:
            adjacency[node.name].append((node.fallback or index.document.fallback).to)
    for region in index.document.region:
        if region.mode is RegionMode.BOUNDED_CYCLE and region.on_exhausted is not None:
            adjacency[region.entry_node].append(region.on_exhausted)
    return adjacency


def cyclic_components_of(adjacency: Mapping[str, list[str]]) -> list[list[str]]:
    """The cycles of an adjacency map.

    A single-node component is a cycle only when the node loops onto itself;
    everything returned here closes a cycle, which is the only sense in which
    "back-edge" is defined. Region declaration order carries no weight.
    """
    return [
        component
        for component in strongly_connected_components(adjacency)
        if len(component) > 1 or component[0] in adjacency[component[0]]
    ]


def cyclic_components(index: GraphIndex) -> list[list[str]]:
    """The effective-graph cycles left after removing the §2 rule 2 exempt back-edges."""
    return cyclic_components_of(effective_successors(index, skip_exempt=True))


def restrict(
    adjacency: Mapping[str, list[str]], members: Container[str]
) -> dict[str, list[str]]:
    """The subgraph induced by `members`; edges leaving the set are dropped."""
    return {
        name: [target for target in targets if target in members]
        for name, targets in adjacency.items()
        if name in members
    }


def component_regions(index: GraphIndex, component: Iterable[str]) -> set[str | None]:
    """The regions a cycle's members belong to; `None` marks unregioned members."""
    return {index.nodes[name].region for name in component}


def region_names(regions: Iterable[str | None]) -> str:
    """Render a region set for a message, naming the unregioned case explicitly."""
    return ", ".join(sorted(region or UNREGIONED for region in regions))


def strongly_connected_components(
    adjacency: Mapping[str, list[str]],
) -> list[list[str]]:
    """Tarjan's SCC, iterative (graphs are small but recursion depth is not a contract)."""
    index_of: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    components: list[list[str]] = []
    counter = 0

    for root in adjacency:
        if root in index_of:
            continue
        work: list[tuple[str, int]] = [(root, 0)]
        while work:
            node, child_index = work.pop()
            if child_index == 0:
                index_of[node] = low[node] = counter
                counter += 1
                stack.append(node)
                on_stack.add(node)
            recursed = False
            children = adjacency[node]
            while child_index < len(children):
                child = children[child_index]
                child_index += 1
                if child not in index_of:
                    work.append((node, child_index))
                    work.append((child, 0))
                    recursed = True
                    break
                if child in on_stack:
                    low[node] = min(low[node], index_of[child])
            if recursed:
                continue
            if low[node] == index_of[node]:
                component: list[str] = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    component.append(member)
                    if member == node:
                        break
                components.append(sorted(component))
            if work:
                parent, _ = work[-1]
                low[parent] = min(low[parent], low[node])
    return components


def predecessors(index: GraphIndex) -> dict[str, list[str]]:
    """Reverse adjacency over declared edges."""
    reverse: dict[str, list[str]] = {name: [] for name in index.nodes}
    for edge in index.edges:
        reverse[edge.to].append(edge.from_node)
    return reverse


def dominators(adjacency: Mapping[str, list[str]], entry: str) -> dict[str, set[str]]:
    """Iterative dominator sets over `adjacency`, starting at `entry`.

    Nodes unreachable from the entry keep the universal set, so a rule asking
    "does P always run before N" never reports on a node no path can reach.
    Callers pass the EFFECTIVE graph (`effective_successors`) — over declared
    edges alone a fallback-only predecessor looks unreachable and its universal
    set silently vanishes from the intersection.
    """
    names = set(adjacency)
    reverse: dict[str, list[str]] = {name: [] for name in names}
    for source, targets in adjacency.items():
        for target in targets:
            reverse[target].append(source)

    result: dict[str, set[str]] = {name: set(names) for name in names}
    result[entry] = {entry}
    changed = True
    while changed:
        changed = False
        for name in names:
            if name == entry:
                continue
            preds = reverse[name]
            if not preds:
                continue
            new: set[str] = set(names)
            for pred in preds:
                new &= result[pred]
            new.add(name)
            if new != result[name]:
                result[name] = new
                changed = True
    return result


def verify_checks(node: Node) -> frozenset[VerifyCheck]:
    """The node's check set, compared whole (§2 rule 7).

    Two checks sharing a `cmd` but differing in `cwd` or `timeout` are
    different checks; collapsing them to command strings invents subsets.
    """
    return frozenset(node.verify or ())
