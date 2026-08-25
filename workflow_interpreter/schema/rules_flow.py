"""Phase B rules about regions, cycles, routing and bounds (spec v0.3.1 §2, §7, §10, §13)."""

from __future__ import annotations

import shlex

from workflow_interpreter.schema.graph_index import (
    GraphIndex,
    at,
    component_regions,
    cyclic_components,
    cyclic_components_of,
    dominators,
    duration_seconds,
    effective_successors,
    finding_error,
    finding_warning,
    is_repo_relative,
    is_repo_relative_executable,
    path,
    predecessors,
    producer_node,
    region_names,
    restrict,
    verify_checks,
)
from workflow_interpreter.schema.messages import (
    MSG_BACK_EDGE,
    MSG_CROSS_REGION_INGRESS,
    MSG_CYCLE_MISSES_ENTRY_NODE,
    MSG_CYCLE_UNBOUNDED,
    MSG_MAX_TOTAL_ACTIVATIONS,
    MSG_NO_TERMINAL,
    MSG_NODE_UNREACHABLE,
    MSG_PRODUCER_NOT_DOMINATING,
    MSG_PRODUCER_SELF,
    MSG_REGION_ACYCLIC_FIELD,
    MSG_REGION_MAX_ENTRIES,
    MSG_REGION_ON_EXHAUSTED_KIND,
    MSG_REGION_ON_EXHAUSTED_REQUIRED,
    MSG_TEST_FLAG,
    MSG_VERIFY_CMD_ARGV,
    MSG_VERIFY_CMD_EXECUTABLE,
    MSG_VERIFY_PATH,
    MSG_VERIFY_SUBSET,
    MSG_VERIFY_TIMEOUT,
)
from workflow_interpreter.schema.models import (
    JUDGMENT_OUTCOME,
    PRODUCER_INSTANCE,
    Finding,
    NodeKind,
    RegionMode,
    RuleId,
)


def bounded_cycle_regions_bounded(index: GraphIndex) -> list[Finding]:
    """Round bounds exist exactly where rounds do (§10.1)."""
    findings: list[Finding] = []
    for position, region in enumerate(index.document.region):
        if region.mode is RegionMode.BOUNDED_CYCLE:
            if region.max_entries is None or region.max_entries < 1:
                findings.append(
                    finding_error(
                        RuleId.BOUNDED_CYCLE_REGIONS_BOUNDED,
                        at("region", position, "max_entries"),
                        MSG_REGION_MAX_ENTRIES.format(
                            region=region.name, value=region.max_entries
                        ),
                    )
                )
            if region.on_exhausted is None:
                findings.append(
                    finding_error(
                        RuleId.BOUNDED_CYCLE_REGIONS_BOUNDED,
                        at("region", position, "on_exhausted"),
                        MSG_REGION_ON_EXHAUSTED_REQUIRED.format(region=region.name),
                    )
                )
            else:
                target = index.nodes[region.on_exhausted]
                if target.kind is not NodeKind.GATE:
                    findings.append(
                        finding_error(
                            RuleId.BOUNDED_CYCLE_REGIONS_BOUNDED,
                            at("region", position, "on_exhausted"),
                            MSG_REGION_ON_EXHAUSTED_KIND.format(
                                region=region.name,
                                name=region.on_exhausted,
                                kind=target.kind.value,
                            ),
                        )
                    )
            continue
        for field in ("max_entries", "on_exhausted"):
            if getattr(region, field) is not None:
                findings.append(
                    finding_error(
                        RuleId.BOUNDED_CYCLE_REGIONS_BOUNDED,
                        at("region", position, field),
                        MSG_REGION_ACYCLIC_FIELD.format(
                            region=region.name, field=field
                        ),
                    )
                )
    return findings


def cycles_confined_to_bounded_cycle_regions(index: GraphIndex) -> list[Finding]:
    """A cycle inside one region must be inside a bounded-cycle region (§2 rule 2).

    Cycles are SCCs of the EFFECTIVE graph minus the exempt human-gate
    `rebudget` back-edges — a fallback edge closes just as real a runtime
    cycle as a declared one; a residual cycle spanning regions belongs to
    `cross_region_back_edge_illegal`, so the two rules never double-report.
    """
    findings: list[Finding] = []
    for component in cyclic_components(index):
        regions = component_regions(index, component)
        if len(regions) != 1:
            continue
        single = next(iter(regions))
        if (
            single is not None
            and index.regions[single].mode is RegionMode.BOUNDED_CYCLE
        ):
            continue
        findings.append(
            finding_error(
                RuleId.CYCLES_CONFINED_TO_BOUNDED_CYCLE_REGIONS,
                path("edge"),
                MSG_CYCLE_UNBOUNDED.format(
                    members=", ".join(component),
                    regions=region_names(regions),
                ),
            )
        )
    return findings


def cross_region_back_edge_illegal(index: GraphIndex) -> list[Finding]:
    """No cycle may span two regions, save the §2 rule 2 exemption.

    Purely graph-theoretic: a back-edge exists only relative to a cycle, so
    only residual SCCs are inspected and region declaration order carries no
    weight. Cross-region edges in acyclic flows — including from and through
    unregioned nodes — are legal.
    """
    findings: list[Finding] = []
    for component in cyclic_components(index):
        regions = component_regions(index, component)
        if len(regions) < 2:
            continue
        findings.append(
            finding_error(
                RuleId.CROSS_REGION_BACK_EDGE_ILLEGAL,
                path("edge"),
                MSG_BACK_EDGE.format(
                    members=", ".join(component),
                    regions=region_names(regions),
                ),
            )
        )
    return findings


def cross_region_edges_target_entry(index: GraphIndex) -> list[Finding]:
    """An edge entering a region from outside it targets its entry_node (§2 rule 6).

    Rounds are counted at the region's `entry_node` (§10.1). An edge arriving at
    any other member is an entry nobody counted: the wrapper has to give it a
    round of its own, which silently spends one of `max_entries` without an
    entry-node arrival ever happening (probed, phase-2 r3).

    Only DECLARED edges can carry it — fallback and `on_exhausted` routes target
    gates or terminals (§2 rule 4), and no activation is ever minted at one.
    """
    findings: list[Finding] = []
    for position, edge in enumerate(index.edges):
        target_region = index.nodes[edge.to].region
        if target_region is None or index.nodes[edge.from_node].region == target_region:
            continue
        entry_node = index.regions[target_region].entry_node
        if edge.to != entry_node:
            findings.append(
                finding_error(
                    RuleId.CROSS_REGION_EDGES_TARGET_ENTRY,
                    at("edge", position, "to"),
                    MSG_CROSS_REGION_INGRESS.format(
                        source=edge.from_node,
                        outcome=edge.on.value,
                        target=edge.to,
                        region=target_region,
                        entry_node=entry_node,
                    ),
                )
            )
    return findings


def bounded_cycle_cycles_include_entry_node(index: GraphIndex) -> list[Finding]:
    """A bounded-cycle region minus its entry_node must be acyclic (§2 rule 2).

    `max_entries` counts entries into `entry_node` (§10.1); a cycle among the
    region's other members never increments the round counter, so the region's
    exhaustion gate could never materialize. Asking instead whether the entry
    node sits in the cycle's SCC is defeatable by one edge that fuses such a
    sub-cycle onto the entry — the sub-cycle survives inside the larger
    component and still consumes no round (probed, phase-1 r2).
    """
    adjacency = effective_successors(index, skip_exempt=True)
    findings: list[Finding] = []
    for position, region in enumerate(index.document.region):
        if region.mode is not RegionMode.BOUNDED_CYCLE:
            continue
        body = frozenset(index.members[region.name]) - {region.entry_node}
        for component in cyclic_components_of(restrict(adjacency, body)):
            findings.append(
                finding_error(
                    RuleId.BOUNDED_CYCLE_CYCLES_INCLUDE_ENTRY_NODE,
                    at("region", position, "entry_node"),
                    MSG_CYCLE_MISSES_ENTRY_NODE.format(
                        members=", ".join(component),
                        region=region.name,
                        entry_node=region.entry_node,
                    ),
                )
            )
    return findings


def terminal_reachable_from_every_node(index: GraphIndex) -> list[Finding]:
    """A terminal is reachable from every node over the effective graph (§2 rule 1)."""
    routes = effective_successors(index)
    findings: list[Finding] = []
    for position, node in enumerate(index.document.node):
        seen: set[str] = {node.name}
        frontier = [node.name]
        reached = False
        while frontier and not reached:
            current = frontier.pop()
            if index.nodes[current].kind is NodeKind.TERMINAL:
                reached = True
                break
            for successor in routes[current]:
                if successor not in seen:
                    seen.add(successor)
                    frontier.append(successor)
        if not reached:
            findings.append(
                finding_error(
                    RuleId.TERMINAL_REACHABLE_FROM_EVERY_NODE,
                    at("node", position, "name"),
                    MSG_NO_TERMINAL.format(node=node.name),
                )
            )
    return findings


def nodes_reachable_from_entry(index: GraphIndex) -> list[Finding]:
    """Every node is reachable from `graph.entry` over the effective graph (§2 rule 6).

    The dual of `terminal_reachable_from_every_node`. Without it a whole dead
    subgraph loads clean: no path from entry reaches it, so `dominators` keeps
    its members' universal sets and every dominance-based rule passes
    vacuously (probed, phase-1 r3).
    """
    routes = effective_successors(index)
    entry = index.document.graph.entry
    reached: set[str] = {entry}
    frontier = [entry]
    while frontier:
        for successor in routes[frontier.pop()]:
            if successor not in reached:
                reached.add(successor)
                frontier.append(successor)
    return [
        finding_error(
            RuleId.NODES_REACHABLE_FROM_ENTRY,
            at("node", position, "name"),
            MSG_NODE_UNREACHABLE.format(node=node.name, entry=entry),
        )
        for position, node in enumerate(index.document.node)
        if node.name not in reached
    ]


def non_optional_inputs_producible(index: GraphIndex) -> list[Finding]:
    """A non-optional input whose producer may not have run yet is an error (§2 rule 5).

    "May not have run" is decided by dominance over the EFFECTIVE transition
    graph: the producer must lie on every path from `graph.entry` to the
    consumer, fallback and exhaustion routes included.
    """
    dominance = dominators(effective_successors(index), index.document.graph.entry)
    findings: list[Finding] = []
    for position, node in enumerate(index.document.node):
        for name in node.inputs or ():
            source = index.sources[name]
            producer = producer_node(source)
            if (
                source.optional
                or producer is None
                or source.producer == PRODUCER_INSTANCE
            ):
                continue
            if producer == node.name:
                findings.append(
                    finding_error(
                        RuleId.NON_OPTIONAL_INPUTS_PRODUCIBLE,
                        at("node", position, "inputs"),
                        MSG_PRODUCER_SELF.format(node=node.name, name=name),
                    )
                )
            elif producer not in dominance[node.name]:
                findings.append(
                    finding_error(
                        RuleId.NON_OPTIONAL_INPUTS_PRODUCIBLE,
                        at("node", position, "inputs"),
                        MSG_PRODUCER_NOT_DOMINATING.format(
                            node=node.name, name=name, producer=producer
                        ),
                    )
                )
    return findings


def _command_findings(
    node_name: str, position: int, check_index: int, cmd: str
) -> list[Finding]:
    """Validate `cmd` with the wrapper's own execution semantics (§2 rule 6, §7.3).

    The wrapper runs `shlex.split(cmd)` without a shell, so the validator splits
    it the same way: validating the raw string as one path accepted
    `"/bin/echo" x` and `bash scripts/verify.sh`, which execute an artifact the
    pin does not cover (probed, phase-1 r3). Tokens after argv[0] are plain
    arguments and carry no path constraint.
    """
    location = at("node", position, f"verify[{check_index}].cmd")
    try:
        argv = shlex.split(cmd)
    except ValueError:
        argv = []
    if not argv:
        return [
            finding_error(
                RuleId.VERIFY_ENTRIES_WELL_FORMED,
                location,
                MSG_VERIFY_CMD_ARGV.format(node=node_name, index=check_index),
            )
        ]
    if not is_repo_relative_executable(argv[0]):
        return [
            finding_error(
                RuleId.VERIFY_ENTRIES_WELL_FORMED,
                location,
                MSG_VERIFY_CMD_EXECUTABLE.format(
                    node=node_name, index=check_index, executable=argv[0]
                ),
            )
        ]
    return []


def verify_entries_well_formed(index: GraphIndex) -> list[Finding]:
    """Checks are repo-relative and fit inside the node's runaway ceiling (§2 rule 6, §7.3, §10)."""
    findings: list[Finding] = []
    for position, node in enumerate(index.document.node):
        ceiling = duration_seconds(node.max_wall) if node.max_wall is not None else None
        for check_index, check in enumerate(node.verify or ()):
            findings.extend(
                _command_findings(node.name, position, check_index, check.cmd)
            )
            # `cwd` is handed to the runtime as one directory, never split.
            if check.cwd is not None and not is_repo_relative(check.cwd):
                findings.append(
                    finding_error(
                        RuleId.VERIFY_ENTRIES_WELL_FORMED,
                        at("node", position, f"verify[{check_index}].cwd"),
                        MSG_VERIFY_PATH.format(
                            node=node.name,
                            index=check_index,
                            field="cwd",
                            value=check.cwd,
                        ),
                    )
                )
            if ceiling is not None and duration_seconds(check.timeout) > ceiling:
                findings.append(
                    finding_error(
                        RuleId.VERIFY_ENTRIES_WELL_FORMED,
                        at("node", position, f"verify[{check_index}].timeout"),
                        MSG_VERIFY_TIMEOUT.format(
                            node=node.name,
                            index=check_index,
                            timeout=check.timeout,
                            max_wall=node.max_wall,
                        ),
                    )
                )
    return findings


def instance_bounds_valid(index: GraphIndex) -> list[Finding]:
    """The instance ceiling must permit at least one mint (§10.3)."""
    ceiling = index.document.instance.max_total_activations
    if ceiling < 1:
        return [
            finding_error(
                RuleId.INSTANCE_BOUNDS_VALID,
                path("instance", "max_total_activations"),
                MSG_MAX_TOTAL_ACTIVATIONS.format(value=ceiling),
            )
        ]
    return []


def test_flags_require_opt_in(index: GraphIndex) -> list[Finding]:
    """Test switches need an explicit opt-in at load time (§2 fixture line 99, §13)."""
    if index.document.instance.test_force_first_reject and not index.allow_test_flags:
        return [
            finding_error(
                RuleId.TEST_FLAGS_REQUIRE_OPT_IN,
                path("instance", "test_force_first_reject"),
                MSG_TEST_FLAG,
            )
        ]
    return []


def judgment_verify_superset(index: GraphIndex) -> list[Finding]:
    """Warn when a judgment node's verify set is a subset of its predecessor's (§2 rule 7).

    Only TASK nodes run checks, and one node with a vacuous cross-check is one
    finding however many predecessors witness it.
    """
    findings: list[Finding] = []
    reverse = predecessors(index)
    for position, node in enumerate(index.document.node):
        if node.kind is not NodeKind.TASK:
            continue
        if node.outcomes is None or JUDGMENT_OUTCOME not in node.outcomes:
            continue
        own = verify_checks(node)
        witnesses = sorted(
            {
                predecessor
                for predecessor in reverse[node.name]
                if verify_checks(index.nodes[predecessor])
                and own <= verify_checks(index.nodes[predecessor])
            }
        )
        if witnesses:
            findings.append(
                finding_warning(
                    RuleId.JUDGMENT_VERIFY_SUPERSET,
                    at("node", position, "verify"),
                    MSG_VERIFY_SUBSET.format(
                        node=node.name, predecessor=", ".join(witnesses)
                    ),
                )
            )
    return findings
