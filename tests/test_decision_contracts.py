"""Decision declarations are opt-in and nonrecursive."""

from pathlib import Path

import pytest

from workflow_interpreter.schema.loader import GraphValidationError, load_graph


def test_declared_decision_loads_as_data_not_an_executable_gate(tmp_path: Path) -> None:
    text = Path("workflow_interpreter/fixtures/feature-delivery.toml").read_text()
    text = text.replace(
        "[instance]",
        "[instance]\ncoordination_limits = {max_members=4, max_activations=500, max_decision_attempts=4, max_replacements=1}",
    )
    text = text.replace('name          = "implement"', 'name          = "implement"')
    # Put the inline field on the first ordinary node, independent of formatting.
    pos = text.index("[[node]]") + len("[[node]]")
    text = (
        text[:pos]
        + '\ncontext_budget_bytes = 32000\ndecision = {triggers=["fail_plan"], actions=["continue_declared","human"], decision_task={runner="profile:reviewer", model="test", instructions="Decide.", verify=[{cmd="scripts/verify.sh",timeout="10s"}], context_budget_bytes=16000, max_wall="30s", stale_after="10s", max_infra_retries=0, max_steers=0, max_total_activations=2}}\n'
        + text[pos:]
    )
    path = tmp_path / "decision.toml"
    path.write_text(text)
    definition = load_graph(path)
    assert definition.document.node[0].decision is not None
    path.write_text(
        text.replace('instructions="Decide."', 'instructions="Decide.", decision={}')
    )
    with pytest.raises(GraphValidationError):
        load_graph(path)
