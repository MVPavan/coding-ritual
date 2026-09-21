"""Child attention reconciliation does not add normal-path Beads round trips."""

import pytest

from tests.test_codex_appserver_children import child_with_uncertain_control
from workflow_interpreter.bdio.reads import WorkflowReads
from workflow_interpreter.foreman.children import attention_blocks, observe
from workflow_interpreter.foreman.decisions import advance_decision
from workflow_interpreter.foreman.tick import TickReport
from workflow_interpreter.schema.decisions import CoordinationError


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


def test_blocking_halt_reason_drops_resolved_control_keys(tmp_path):
    """A blocked child halts on its real failure, never on a settled control."""
    from workflow_interpreter.foreman.rpc_control import acknowledge_uncertain

    lab, owner, coordinator, child, aid = child_with_uncertain_control(tmp_path)
    wiring = lab.composition.for_root(child.root_id)
    with wiring.band:
        acknowledge_uncertain(wiring.store, aid, "operator inspected delivery")
    coordinator.update_child(
        owner,
        child.model_copy(update={"attention": f"{aid}:control:1; crew log is gone"}),
    )
    report = advance_decision(lab.composition, child.root_id, lambda _: TickReport())
    assert report.halted
    assert report.stalled == "crew log is gone"


def test_child_lock_reused_root_must_match_identity(tmp_path):
    """A supplied root cannot silently select another child's exclusion path."""
    lab, owner, coordinator, child, _ = child_with_uncertain_control(tmp_path)
    owner_root = lab.store.reads.load_root(owner)
    with pytest.raises(CoordinationError, match="root identity mismatch"):
        coordinator.member_lock_path(child.root_id, root=owner_root)
