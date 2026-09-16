"""Child attention reconciliation does not add normal-path Beads round trips."""

import pytest

from tests.test_codex_appserver_children import child_with_uncertain_control
from workflow_interpreter.bdio.reads import WorkflowReads
from workflow_interpreter.foreman.children import attention_blocks, observe
from workflow_interpreter.foreman.decisions import advance_decision
from workflow_interpreter.foreman.tick import TickReport


@pytest.mark.parametrize("attention", [None, "waiting at gate example"])
def test_normal_child_tick_does_not_read_observation(tmp_path, monkeypatch, attention):
    """Empty and gate-only attention cannot prevent local lifecycle progress."""
    lab, owner, coordinator, child, _ = child_with_uncertain_control(tmp_path)
    coordinator.update_child(owner, child.model_copy(update={"attention": attention}))

    def forbidden(*args, **kwargs):
        pytest.fail("normal child tick must not list observation evidence")

    monkeypatch.setattr(WorkflowReads, "list_activations", forbidden)
    monkeypatch.setattr(WorkflowReads, "list_gates", forbidden)
    report = advance_decision(lab.composition, child.root_id, lambda _: TickReport())
    assert not report.halted


def test_control_attention_lists_activations_once(tmp_path, monkeypatch):
    """Refreshing and classifying attention share the same durable snapshot."""
    lab, _, _, child, _ = child_with_uncertain_control(tmp_path)
    original = WorkflowReads.list_activations
    calls = []

    def counted(self, root_id):
        calls.append(root_id)
        return original(self, root_id)

    monkeypatch.setattr(WorkflowReads, "list_activations", counted)
    report = advance_decision(lab.composition, child.root_id, lambda _: TickReport())
    assert not report.halted
    assert calls == [child.root_id]


def test_observation_and_attention_share_snapshot(tmp_path, monkeypatch):
    """The coordinator reuses its observation snapshot when deciding to drive."""
    lab, _, _, child, _ = child_with_uncertain_control(tmp_path)
    activations = lab.store.reads.list_activations(child.root_id)

    def forbidden(*args, **kwargs):
        pytest.fail("the supplied activation snapshot must be reused")

    monkeypatch.setattr(WorkflowReads, "list_activations", forbidden)
    current = observe(lab.composition, child, activations=activations)
    assert current.attention == child.attention
    assert not attention_blocks(lab.composition, current, activations=activations)
