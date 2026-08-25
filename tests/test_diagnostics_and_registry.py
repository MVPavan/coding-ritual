"""Diagnostic-contract and registry-closure tests (spec v0.3.1 §2).

Every rule ships with a fixture, every message template is rendered by some
input, and no template's pattern accepts another's rendering.
"""

from __future__ import annotations

from pathlib import Path

from tests._helpers import (
    INVALID_FIXTURES,
    WARNING_FIXTURES,
    matching_templates,
    message_pattern,
    message_templates,
    rule_of,
)
from tests._mutations import all_findings
from workflow_interpreter import RuleId
from workflow_interpreter.schema import messages
from workflow_interpreter.schema.models import Node
from workflow_interpreter.schema.rules_nodes import (
    _EXECUTION_FIELDS,
    _GATE_FIELDS,
    _GATE_REQUIRED,
    _KIND_FORBIDDEN,
    _KIND_REQUIRED,
    _MINIMUMS,
    _TASK_REQUIRED,
)
from workflow_interpreter.schema.validator import PHASE_A_RULES, PHASE_B_RULES


def test_every_semantic_rule_has_a_fixture() -> None:
    """No rule ships without a fixture proving it fires."""
    registered = {rule.__name__ for rule in (*PHASE_A_RULES, *PHASE_B_RULES)}
    covered = {rule_of(path).value for path in (*INVALID_FIXTURES, *WARNING_FIXTURES)}

    assert registered == {member.value for member in RuleId} - {
        RuleId.TOML_PARSE.value,
        RuleId.PINNED_PARSE.value,
        RuleId.PINNED_NONCANONICAL.value,
        RuleId.SCHEMA.value,
    }
    assert registered == covered


def test_every_message_branch_is_exercised(tmp_path: Path) -> None:
    """Every diagnostic the validator can emit is produced by some test input."""
    produced = [finding.message for finding in all_findings(tmp_path)]

    unexercised = {
        name
        for name, template in message_templates().items()
        if not any(message_pattern(template).fullmatch(text) for text in produced)
    }

    assert unexercised == set()


def test_each_message_identifies_its_own_template(tmp_path: Path) -> None:
    """No template's pattern accepts another template's rendering (branch-coverage closure).

    Without it `test_every_message_branch_is_exercised` proves less than it
    reads: a template with no producer of its own can be "exercised" by some
    other rule's message.
    """
    ambiguous = {
        message: sorted(matching_templates(message))
        for message in {finding.message for finding in all_findings(tmp_path)}
        if len(matching_templates(message)) != 1
    }

    assert ambiguous == {}


def test_entry_and_edge_endpoint_messages_do_not_collide() -> None:
    """The two 'is not a declared node' diagnostics stay distinguishable (regression)."""
    entry_message = messages.MSG_ENTRY_UNKNOWN.format(name="nope")

    assert message_pattern(messages.MSG_ENTRY_UNKNOWN).fullmatch(entry_message)
    assert not message_pattern(messages.MSG_EDGE_ENDPOINT_UNKNOWN).fullmatch(
        entry_message
    )


def test_findings_use_one_location_dialect(tmp_path: Path) -> None:
    """Schema and semantic findings address the document the same way (JSONPath)."""
    locations = {finding.location for finding in all_findings(tmp_path)}

    assert locations
    assert all(location.startswith("$") for location in locations)


def test_rule_field_names_resolve_on_the_node_model() -> None:
    """A field rename must break a test, not silently disable a rule."""
    referenced = {
        *_EXECUTION_FIELDS,
        *_GATE_FIELDS,
        *_TASK_REQUIRED,
        *_GATE_REQUIRED,
        *_MINIMUMS,
        *(field for fields in _KIND_FORBIDDEN.values() for field in fields),
        *(field for fields in _KIND_REQUIRED.values() for field in fields),
    }

    assert referenced <= set(Node.model_fields)
