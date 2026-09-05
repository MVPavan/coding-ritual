"""The mutation table: one small edit to a valid graph per semantic rule.

Each case names the single rule the edit must trip; `test_semantic_rules`
asserts exactly that, and `test_diagnostics_and_registry` reuses the same
inputs as the corpus every diagnostic template must be rendered by.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Final

from tests._helpers import (
    FALLBACK,
    FINISHED_NODE,
    GATE_OUTCOMES,
    INVALID_FIXTURES,
    MINIMAL_GRAPH,
    VALID_FIXTURES,
    WARNING_FIXTURES,
    WORK_EDGE,
    Replacements,
    findings_of,
    mutate,
    write,
)
from workflow_interpreter import RuleId
from workflow_interpreter.schema.models import Finding

REGION_MEMBER_NODE: Final[str] = """
[[node]]
name = "extra"
kind = "task"
region = "r"
runner = "profile:x"
writes = false
allowed_paths = []
verify = [{ cmd = "scripts/verify.sh", timeout = "5m" }]
token_budget = 1000
max_wall = "10m"
stale_after = "5m"
max_infra_retries = 1
max_steers = 1
outcomes = ["done"]
fallback = { to = "finished" }
"""
"""A second member of region `r`, reachable only from OUTSIDE the region — the
non-entry ingress §2 rule 6 refuses. Its own fallback goes to the terminal so
the global fallback gate does not close a cross-region cycle as well."""


def source_block(
    producer: str, *, optional: bool = False, trim_priority: int = 1
) -> str:
    """A `[[source]]` block appended to MINIMAL_GRAPH by the mutation cases."""
    return (
        f'\n[[source]]\nname = "own"\nproducer = "{producer}"\n'
        f"optional = {str(optional).lower()}\ntrim_priority = {trim_priority}\n"
    )


def _cmd(value: str) -> tuple[str, str]:
    """Replace the minimal graph's check command with `value` (a literal string)."""
    return ('cmd = "scripts/verify.sh"', f"cmd = '{value}'")


# (case id, replacements applied to MINIMAL_GRAPH, the one rule they must trip)
MUTATION_CASES: Final[tuple[tuple[str, Replacements, RuleId], ...]] = (
    (
        "entry-unknown",
        (('entry = "work"', 'entry = "nope"'),),
        RuleId.ENTRY_NODE_VALID,
    ),
    (
        "entry-terminal",
        (('entry = "work"', 'entry = "finished"'),),
        RuleId.ENTRY_NODE_VALID,
    ),
    (
        "duplicate-node-name",
        ((FINISHED_NODE, FINISHED_NODE + "\n" + FINISHED_NODE),),
        RuleId.UNIQUE_NAMES,
    ),
    (
        "node-region-unknown",
        (('region = "r"', 'region = "nope"'),),
        RuleId.REGION_MEMBERSHIP_VALID,
    ),
    (
        "region-entry-node-unknown",
        (('entry_node = "work"', 'entry_node = "nope"'),),
        RuleId.REGION_MEMBERSHIP_VALID,
    ),
    (
        "region-entry-node-terminal",
        (
            ('entry_node = "work"', 'entry_node = "finished"'),
            (FINISHED_NODE, FINISHED_NODE + 'region = "r"\n'),
        ),
        RuleId.REGION_MEMBERSHIP_VALID,
    ),
    (
        "region-on-exhausted-unknown",
        (
            (
                'mode = "acyclic"\nentry_node = "work"',
                (
                    'mode = "bounded-cycle"\nentry_node = "work"\n'
                    'max_entries = 2\non_exhausted = "nope"'
                ),
            ),
        ),
        RuleId.REGION_MEMBERSHIP_VALID,
    ),
    (
        "edge-endpoint-unknown",
        ((WORK_EDGE, '[[edge]]\nfrom = "work"\non = "done"\nto = "nope"\n'),),
        RuleId.EDGE_ENDPOINTS_EXIST,
    ),
    (
        "fallback-unknown",
        ((FALLBACK, '[fallback]\nto = "nope"\n'),),
        RuleId.FALLBACK_TARGETS_GATE_OR_TERMINAL,
    ),
    (
        "fallback-targets-task",
        ((FALLBACK, '[fallback]\nto = "work"\n'),),
        RuleId.FALLBACK_TARGETS_GATE_OR_TERMINAL,
    ),
    (
        "input-unknown",
        (("allowed_paths = []\n", 'allowed_paths = []\ninputs = ["nope"]\n'),),
        RuleId.INPUT_NAMES_RESOLVE_TO_SOURCES,
    ),
    (
        "producer-unknown",
        ((FALLBACK, FALLBACK + source_block("node:nope", optional=True)),),
        RuleId.SOURCE_REGISTRY_WELL_FORMED,
    ),
    (
        "trim-priority-zero",
        (
            (
                FALLBACK,
                FALLBACK + source_block("instance", optional=True, trim_priority=0),
            ),
        ),
        RuleId.SOURCE_REGISTRY_WELL_FORMED,
    ),
    (
        "task-missing-runner",
        (('runner = "profile:x"\n', ""),),
        RuleId.NODE_FIELDS_MATCH_KIND,
    ),
    (
        "task-missing-writes",
        (("writes = false\n", ""),),
        RuleId.NODE_FIELDS_MATCH_KIND,
    ),
    (
        "gate-carrying-runner",
        (
            (
                'kind = "gate"\ngate_type = "human"',
                'kind = "gate"\nrunner = "profile:x"\ngate_type = "human"',
            ),
        ),
        RuleId.NODE_FIELDS_MATCH_KIND,
    ),
    (
        "gate-carrying-fallback",
        ((GATE_OUTCOMES, GATE_OUTCOMES + '\nfallback = { to = "finished" }'),),
        RuleId.NODE_FIELDS_MATCH_KIND,
    ),
    (
        "empty-verify",
        (('verify = [{ cmd = "scripts/verify.sh", timeout = "5m" }]', "verify = []"),),
        RuleId.NODE_FIELDS_MATCH_KIND,
    ),
    (
        "token-budget-zero",
        (("token_budget = 1000", "token_budget = 0"),),
        RuleId.NODE_FIELDS_MATCH_KIND,
    ),
    (
        "duplicate-outcome",
        (('outcomes = ["done"]', 'outcomes = ["done", "done"]'),),
        RuleId.NODE_OUTCOME_DECLARATIONS_VALID,
    ),
    (
        "system-outcome-declared",
        (('outcomes = ["done"]', 'outcomes = ["done", "error_runner"]'),),
        RuleId.NODE_OUTCOME_DECLARATIONS_VALID,
    ),
    (
        "terminal-with-exit",
        (
            (
                FINISHED_NODE,
                FINISHED_NODE + '\n[[node]]\nname = "aborted"\nkind = "terminal"\n',
            ),
            (
                FALLBACK,
                '[[edge]]\nfrom = "finished"\non = "done"\nto = "aborted"\n\n'
                + FALLBACK,
            ),
        ),
        RuleId.TERMINALS_HAVE_NO_EXITS,
    ),
    (
        "edge-outcome-undeclared",
        ((WORK_EDGE, '[[edge]]\nfrom = "work"\non = "fail_plan"\nto = "approval"\n'),),
        RuleId.EDGE_OUTCOME_DECLARED_BY_SOURCE,
    ),
    (
        "duplicate-edge",
        (
            (
                WORK_EDGE,
                WORK_EDGE + '\n[[edge]]\nfrom = "work"\non = "done"\nto = "finished"\n',
            ),
        ),
        RuleId.NO_DUPLICATE_EDGES,
    ),
    (
        "edge-on-system-outcome",
        (
            (
                WORK_EDGE,
                WORK_EDGE
                + '\n[[edge]]\nfrom = "work"\non = "error_runner"\nto = "finished"\n',
            ),
        ),
        RuleId.NO_EDGES_ON_SYSTEM_OUTCOMES,
    ),
    (
        "gate-outcome-uncovered",
        ((GATE_OUTCOMES, 'outcomes = ["approve", "abandon", "rebudget"]'),),
        RuleId.GATE_OUTCOMES_EDGE_COVERED,
    ),
    (
        "writer-without-allowed-paths",
        (("writes = false", "writes = true"),),
        RuleId.ALLOWED_PATHS_WELL_FORMED,
    ),
    (
        "unreachable-node",
        (
            (
                FINISHED_NODE,
                FINISHED_NODE + '\n[[node]]\nname = "stranded"\nkind = "terminal"\n',
            ),
        ),
        RuleId.NODES_REACHABLE_FROM_ENTRY,
    ),
    # -- §2 rule 6 command execution semantics: the validator splits `cmd` the
    # way the wrapper will, so argv[0] is what must be repo-relative.
    (
        "verify-cmd-absolute",
        (_cmd("/opt/verify.sh"),),
        RuleId.VERIFY_ENTRIES_WELL_FORMED,
    ),
    (
        "verify-cmd-quoted-absolute",
        (_cmd('"/bin/echo" outside'),),
        RuleId.VERIFY_ENTRIES_WELL_FORMED,
    ),
    (
        "verify-cmd-quoted-parent-escape",
        (_cmd('"../outside.sh"'),),
        RuleId.VERIFY_ENTRIES_WELL_FORMED,
    ),
    (
        "verify-cmd-interpreter",
        (_cmd("bash scripts/verify.sh"),),
        RuleId.VERIFY_ENTRIES_WELL_FORMED,
    ),
    (
        "verify-cmd-env-wrapper",
        (_cmd("env A=1 scripts/verify.sh"),),
        RuleId.VERIFY_ENTRIES_WELL_FORMED,
    ),
    (
        "verify-cmd-blank",
        (_cmd(" "),),
        RuleId.VERIFY_ENTRIES_WELL_FORMED,
    ),
    (
        "verify-cmd-unbalanced-quote",
        (_cmd('scripts/verify.sh "unclosed'),),
        RuleId.VERIFY_ENTRIES_WELL_FORMED,
    ),
    (
        "verify-cwd-absolute",
        (
            (
                'cmd = "scripts/verify.sh", timeout = "5m"',
                'cmd = "scripts/verify.sh", cwd = "/tmp", timeout = "5m"',
            ),
        ),
        RuleId.VERIFY_ENTRIES_WELL_FORMED,
    ),
    (
        "verify-timeout-over-max-wall",
        (('timeout = "5m"', 'timeout = "20m"'),),
        RuleId.VERIFY_ENTRIES_WELL_FORMED,
    ),
    (
        "acyclic-region-declares-bounds",
        (('mode = "acyclic"', 'mode = "acyclic"\nmax_entries = 2'),),
        RuleId.BOUNDED_CYCLE_REGIONS_BOUNDED,
    ),
    (
        "instance-ceiling-zero",
        (("max_total_activations = 5", "max_total_activations = 0"),),
        RuleId.INSTANCE_BOUNDS_VALID,
    ),
    (
        "test-flag-without-opt-in",
        (
            (
                "max_total_activations = 5",
                "max_total_activations = 5\ntest_force_first_reject = true",
            ),
        ),
        RuleId.TEST_FLAGS_REQUIRE_OPT_IN,
    ),
    (
        "cross-region-ingress-at-non-entry-node",
        (
            (
                FINISHED_NODE,
                FINISHED_NODE + REGION_MEMBER_NODE,
            ),
            (
                '[[edge]]\nfrom = "approval"\non = "approve"\nto = "finished"\n',
                (
                    '[[edge]]\nfrom = "approval"\non = "approve"\nto = "extra"\n\n'
                    '[[edge]]\nfrom = "extra"\non = "done"\nto = "finished"\n'
                ),
            ),
        ),
        RuleId.CROSS_REGION_EDGES_TARGET_ENTRY,
    ),
    (
        "input-produced-by-itself",
        (
            ("allowed_paths = []\n", 'allowed_paths = []\ninputs = ["own"]\n'),
            (FALLBACK, FALLBACK + source_block("node:work")),
        ),
        RuleId.NON_OPTIONAL_INPUTS_PRODUCIBLE,
    ),
)


def all_findings(tmp_path: Path) -> Iterator[Finding]:
    """Findings from every fixture and every inline mutation case."""
    for path in (*INVALID_FIXTURES, *WARNING_FIXTURES, *VALID_FIXTURES):
        yield from findings_of(path)
    for case_id, replacements, _rule in MUTATION_CASES:
        path = write(tmp_path, mutate(MINIMAL_GRAPH, replacements), f"{case_id}.toml")
        yield from findings_of(path)
