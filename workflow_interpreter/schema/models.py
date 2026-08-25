"""Frozen data model for a workflow graph definition (spec v0.3.1 §2).

Mirrors `graph_schema.json` one-to-one. Field names use the TOML spelling
(`from` is exposed under the alias so the canonical serialization used for
`content_hash` is byte-comparable with the spec's vocabulary).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Final

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

MODEL_CONFIG: Final[ConfigDict] = ConfigDict(
    frozen=True,
    extra="forbid",
    populate_by_name=True,
    arbitrary_types_allowed=False,
)

DURATION_PATTERN: Final[str] = r"^[1-9][0-9]*[smhd]$"
IDENTIFIER_PATTERN: Final[str] = r"^[a-z0-9][a-z0-9_-]*$"
SEMVER_PATTERN: Final[str] = r"^[0-9]+\.[0-9]+\.[0-9]+$"
PRODUCER_INSTANCE: Final[str] = "instance"
PRODUCER_NODE_PREFIX: Final[str] = "node:"

Identifier = Annotated[
    str, StringConstraints(pattern=IDENTIFIER_PATTERN, max_length=64)
]
Duration = Annotated[str, StringConstraints(pattern=DURATION_PATTERN)]
RelativePath = Annotated[str, StringConstraints(min_length=1)]


class NodeKind(StrEnum):
    """Node kinds of §2."""

    TASK = "task"
    GATE = "gate"
    TERMINAL = "terminal"


class GateType(StrEnum):
    """Gate types. v1 ships human gates only (§13); native types are deferred (§14)."""

    HUMAN = "human"


class BindsMode(StrEnum):
    """Artifact class a gate approval binds to (§9)."""

    IMMUTABLE = "immutable"
    MUTABLE = "mutable"


class IsolationMode(StrEnum):
    """Execution isolation (§12)."""

    WORKTREE = "worktree"
    IN_REPO = "in-repo"


class RegionMode(StrEnum):
    """Region modes of §2."""

    ACYCLIC = "acyclic"
    BOUNDED_CYCLE = "bounded-cycle"


class Outcome(StrEnum):
    """The closed global outcome vocabulary (§2 'Outcome vocabulary')."""

    DONE = "done"
    NO_DIFF = "no_diff"
    ACCEPT = "accept"
    REJECT = "reject"
    FAIL_CODE = "fail_code"
    FAIL_PLAN = "fail_plan"
    APPROVE = "approve"
    REBUDGET = "rebudget"
    ABANDON = "abandon"
    ERROR_RUNNER = "error_runner"
    ERROR_TRANSPORT = "error_transport"
    STEERED = "steered"
    SUPERSEDED = "superseded"


SYSTEM_OUTCOMES: Final[frozenset[Outcome]] = frozenset(
    {
        Outcome.ERROR_RUNNER,
        Outcome.ERROR_TRANSPORT,
        Outcome.STEERED,
        Outcome.SUPERSEDED,
    }
)
"""Never edge-routed; wrapper-handled per §10.2."""

GRAPH_OUTCOMES: Final[frozenset[Outcome]] = frozenset(Outcome) - SYSTEM_OUTCOMES
"""Edge-routed, node-declared."""

JUDGMENT_OUTCOME: Final[Outcome] = Outcome.ACCEPT
"""A node declaring `accept` performs the §7.3 anti-drift cross-check."""

EXEMPT_BACK_EDGE_OUTCOME: Final[Outcome] = Outcome.REBUDGET
"""The one outcome that may carry a legal cross-region back-edge (§2 rule 2)."""


class Severity(StrEnum):
    """Finding severity. Only ERROR blocks a load."""

    ERROR = "error"
    WARNING = "warning"


class RuleId(StrEnum):
    """Identifier of the check that produced a finding.

    Semantic rule ids double as the file names under `fixtures/invalid/`.
    """

    TOML_PARSE = "toml_parse"
    PINNED_PARSE = "pinned_parse"
    PINNED_NONCANONICAL = "pinned_noncanonical"
    SCHEMA = "schema"

    # -- phase A: referential integrity --------------------------------
    UNIQUE_NAMES = "unique_names"
    ENTRY_NODE_VALID = "entry_node_valid"
    EDGE_ENDPOINTS_EXIST = "edge_endpoints_exist"
    REGION_MEMBERSHIP_VALID = "region_membership_valid"
    FALLBACK_TARGETS_GATE_OR_TERMINAL = "fallback_targets_gate_or_terminal"
    INPUT_NAMES_RESOLVE_TO_SOURCES = "input_names_resolve_to_sources"
    SOURCE_REGISTRY_WELL_FORMED = "source_registry_well_formed"

    # -- phase B: graph shape and bounds --------------------------------
    NODE_FIELDS_MATCH_KIND = "node_fields_match_kind"
    NODE_OUTCOME_DECLARATIONS_VALID = "node_outcome_declarations_valid"
    TERMINALS_HAVE_NO_EXITS = "terminals_have_no_exits"
    EDGE_OUTCOME_DECLARED_BY_SOURCE = "edge_outcome_declared_by_source"
    NO_DUPLICATE_EDGES = "no_duplicate_edges"
    NO_EDGES_ON_SYSTEM_OUTCOMES = "no_edges_on_system_outcomes"
    GATE_OUTCOMES_EDGE_COVERED = "gate_outcomes_edge_covered"
    BOUNDED_CYCLE_REGIONS_BOUNDED = "bounded_cycle_regions_bounded"
    CYCLES_CONFINED_TO_BOUNDED_CYCLE_REGIONS = (
        "cycles_confined_to_bounded_cycle_regions"
    )
    CROSS_REGION_BACK_EDGE_ILLEGAL = "cross_region_back_edge_illegal"
    CROSS_REGION_EDGES_TARGET_ENTRY = "cross_region_edges_target_entry"
    BOUNDED_CYCLE_CYCLES_INCLUDE_ENTRY_NODE = "bounded_cycle_cycles_include_entry_node"
    TERMINAL_REACHABLE_FROM_EVERY_NODE = "terminal_reachable_from_every_node"
    NODES_REACHABLE_FROM_ENTRY = "nodes_reachable_from_entry"
    NON_OPTIONAL_INPUTS_PRODUCIBLE = "non_optional_inputs_producible"
    VERIFY_ENTRIES_WELL_FORMED = "verify_entries_well_formed"
    ALLOWED_PATHS_WELL_FORMED = "allowed_paths_well_formed"
    INSTANCE_BOUNDS_VALID = "instance_bounds_valid"
    TEST_FLAGS_REQUIRE_OPT_IN = "test_flags_require_opt_in"
    JUDGMENT_VERIFY_SUPERSET = "judgment_verify_superset"


class Finding(BaseModel):
    """One validation result, addressed to a location inside the graph file."""

    model_config = MODEL_CONFIG

    rule: RuleId
    severity: Severity
    location: str
    message: str


class GraphMeta(BaseModel):
    """`[graph]` — identity and entry point."""

    model_config = MODEL_CONFIG

    id: Identifier
    version: Annotated[str, StringConstraints(pattern=SEMVER_PATTERN)]
    entry: Identifier
    description: Annotated[str, StringConstraints(min_length=1)]


class InstanceBounds(BaseModel):
    """`[instance]` — the §10.3 instance ceiling and v1 test switches."""

    model_config = MODEL_CONFIG

    max_total_activations: int
    test_force_first_reject: bool = False


class Region(BaseModel):
    """`[[region]]` — a round-bounded or acyclic sub-graph (§10.1)."""

    model_config = MODEL_CONFIG

    name: Identifier
    mode: RegionMode
    entry_node: Identifier
    max_entries: int | None = None
    on_exhausted: Identifier | None = None


class VerifyCheck(BaseModel):
    """One structured check executed by the wrapper from a trusted pinned source (§7.3)."""

    model_config = MODEL_CONFIG

    cmd: RelativePath
    timeout: Duration
    cwd: RelativePath | None = None


class FallbackRoute(BaseModel):
    """`[fallback]` / `[node.fallback]` — where an unrouted declared outcome goes (§2)."""

    model_config = MODEL_CONFIG

    to: Identifier


class Node(BaseModel):
    """`[[node]]` — the union of all kinds; per-kind field rules live in the validator."""

    model_config = MODEL_CONFIG

    name: Identifier
    kind: NodeKind
    region: Identifier | None = None
    runner: Annotated[str, StringConstraints(min_length=1)] | None = None
    model: Annotated[str, StringConstraints(min_length=1)] | None = None
    isolation: IsolationMode | None = None
    writes: bool | None = None
    allowed_paths: tuple[RelativePath, ...] | None = None
    inputs: tuple[Identifier, ...] | None = None
    verify: tuple[VerifyCheck, ...] | None = None
    token_budget: int | None = None
    max_wall: Duration | None = None
    stale_after: Duration | None = None
    max_infra_retries: int | None = None
    max_steers: int | None = None
    outcomes: tuple[Outcome, ...] | None = None
    gate_type: GateType | None = None
    binds: BindsMode | None = None
    fallback: FallbackRoute | None = None


class Edge(BaseModel):
    """`[[edge]]` — a declared transition."""

    model_config = MODEL_CONFIG

    from_node: Identifier = Field(alias="from")
    on: Outcome
    to: Identifier


class Source(BaseModel):
    """`[[source]]` — the input registry entry bound at mint (§2 'Input binding')."""

    model_config = MODEL_CONFIG

    name: Identifier
    producer: Annotated[str, StringConstraints(min_length=1)]
    optional: bool
    trim_priority: int


class GraphDocument(BaseModel):
    """The whole parsed TOML document."""

    model_config = MODEL_CONFIG

    graph: GraphMeta
    instance: InstanceBounds
    node: tuple[Node, ...]
    edge: tuple[Edge, ...]
    fallback: FallbackRoute
    region: tuple[Region, ...] = ()
    source: tuple[Source, ...] = ()


class GraphDefinition(BaseModel):
    """A validated graph plus the hash it is pinned by (§2 rule 8, §3.1)."""

    model_config = MODEL_CONFIG

    document: GraphDocument
    content_hash: str
    warnings: tuple[Finding, ...] = ()
