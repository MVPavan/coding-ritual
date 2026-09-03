"""Fixtures, graph fragments and helpers shared by the schema test modules.

Not a test module: the loader's test families live in `test_canonical_and_pinning`,
`test_semantic_rules`, `test_cycles_and_regions` and `test_diagnostics_and_registry`,
and every one of them addresses the same fixtures and the same minimal graph.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Final

import workflow_interpreter
from workflow_interpreter import GraphValidationError, RuleId, load_graph
from workflow_interpreter.schema import messages
from workflow_interpreter.schema.models import Finding

PACKAGE_ROOT = Path(workflow_interpreter.__file__).parent
FIXTURES = PACKAGE_ROOT / "fixtures"
VALID_FIXTURE = FIXTURES / "feature-delivery.toml"
# The `workflows/` authoring copy of the same graph (spec §2 `:100-102`,
# temporary until phase 5 collapses the split).
AUTHORING_FIXTURE = PACKAGE_ROOT.parent / "workflows" / "feature-delivery.toml"
INVALID_FIXTURES = sorted((FIXTURES / "invalid").glob("*.toml"))
WARNING_FIXTURES = sorted((FIXTURES / "warning").glob("*.toml"))
VALID_FIXTURES = [VALID_FIXTURE, *sorted((FIXTURES / "valid").glob("*.toml"))]
JUDGMENT_FIXTURE = (
    FIXTURES / "warning" / f"{RuleId.JUDGMENT_VERIFY_SUPERSET.value}.toml"
)

# A fixture file is named for the rule it must trip; `__<variant>` distinguishes
# several fixtures exercising different branches of the same rule.
VARIANT_SEPARATOR: Final[str] = "__"

# What one `{placeholder}` may stand for inside a rendered message: a token with
# no whitespace, or the comma-separated list several templates interpolate.
MESSAGE_TOKEN: Final[str] = r"\S+(?:, \S+)*"

# The §2 fixture is pinned by hash (§3.1); a change here means the graph's
# meaning changed and every live instance's pinned body is stale.
FEATURE_DELIVERY_CONTENT_HASH = (
    "2c9cf15e1107eb42df774d30b66ab993c724c89b4bbb874b88c4187bdee74635"
)

# A valid graph every semantic rule can be pushed off with one small edit.
MINIMAL_GRAPH: Final[str] = """
[graph]
id = "min"
version = "1.0.0"
entry = "work"
description = "minimal graph"

[instance]
max_total_activations = 5

[[region]]
name = "r"
mode = "acyclic"
entry_node = "work"

[[node]]
name = "work"
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

[[node]]
name = "approval"
kind = "gate"
gate_type = "human"
binds = "immutable"
outcomes = ["approve", "abandon"]

[[node]]
name = "finished"
kind = "terminal"

[[edge]]
from = "work"
on = "done"
to = "approval"

[[edge]]
from = "approval"
on = "approve"
to = "finished"

[[edge]]
from = "approval"
on = "abandon"
to = "finished"

[fallback]
to = "approval"
"""

REVIEW_VERIFY: Final[str] = 'verify = [{ cmd = "scripts/verify.sh", timeout = "5m" }]'
WORK_EDGE: Final[str] = '[[edge]]\nfrom = "work"\non = "done"\nto = "approval"\n'
FINISHED_NODE: Final[str] = '[[node]]\nname = "finished"\nkind = "terminal"\n'
FALLBACK: Final[str] = '[fallback]\nto = "approval"\n'
GATE_OUTCOMES: Final[str] = 'outcomes = ["approve", "abandon"]'

Replacements = tuple[tuple[str, str], ...]


def rule_of(path: Path) -> RuleId:
    """The rule a fixture file is named for, ignoring its `__variant` suffix."""
    return RuleId(path.stem.split(VARIANT_SEPARATOR, 1)[0])


def write(tmp_path: Path, text: str, name: str = "graph.toml") -> Path:
    """Materialize a TOML graph for the loader."""
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def mutate(text: str, replacements: Iterable[tuple[str, str]]) -> str:
    """Apply unique, asserted text replacements to a graph file."""
    for original, replacement in replacements:
        assert text.count(original) == 1, f"not a unique anchor: {original!r}"
        text = text.replace(original, replacement)
    return text


def findings_of(path: Path) -> tuple[Finding, ...]:
    """Every finding a fixture produces, whether it loads or not."""
    try:
        return load_graph(path).warnings
    except GraphValidationError as error:
        return (*error.findings, *error.warnings)


def message_templates() -> dict[str, str]:
    """Every diagnostic template the validator can render."""
    return {
        name: value for name, value in vars(messages).items() if name.startswith("MSG_")
    }


def message_pattern(template: str) -> re.Pattern[str]:
    """A regex matching the messages rendered from `template`, and no others.

    Anchored, and a placeholder becomes a whitespace-free token (or a comma-
    separated list of them — several templates interpolate one) rather than
    `.*`: an unanchored `.*` pattern swallows other templates' renderings, and
    the branch-coverage closure would then be satisfiable by the wrong message.
    """
    literals = re.split(r"\{[^}]*\}", template)
    body = MESSAGE_TOKEN.join(re.escape(part) for part in literals)
    return re.compile(f"^{body}$", re.DOTALL)


def matching_templates(text: str) -> set[str]:
    """The message templates whose pattern accepts `text`."""
    return {
        name
        for name, template in message_templates().items()
        if message_pattern(template).fullmatch(text)
    }
