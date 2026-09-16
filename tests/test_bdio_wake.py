"""Wake events are durable notifications, never routing or approval authority."""

import pytest

from tests._bdio import entry_request, load_definition, make_root
from tests._gates import open_ship_gate, open_triage_gate
from workflow_interpreter.bdio import CarrierIntegrityError, WorkflowStore
from workflow_interpreter.bdio.bounds import ceiling_count, effective_bound
from workflow_interpreter.bdio.errors import BdioError
from workflow_interpreter.bdio.keys import wake_fire_key
from workflow_interpreter.bdio.wire import BoundSetting
from workflow_interpreter.contracts.wake import WakeCondition, WakeCursor, WakeEvent
from workflow_interpreter.foreman.frontier import build_frontier


def event_for(root, identity="cursor", condition=WakeCondition.ROOT_TERMINAL):
    """Construct a notification with a stable independently chosen observation."""
    cursor = WakeCursor(identity=identity)
    return WakeEvent(
        root_id=root.root_id,
        instance_key=root.metadata.instance_key,
        condition=condition,
        cursor=cursor,
        fire_key=wake_fire_key(root.metadata.instance_key, condition, cursor),
        observed_at="2026-09-15T00:00:00Z",
        fired_at="2026-09-15T00:00:00Z",
        detail="attention",
    )


def test_wakes_roundtrip_dedupe_and_never_route_or_spend_bounds(fake_store):
    """A notification saying terminal cannot settle or advance its open root."""
    root = make_root(fake_store, load_definition())
    event = event_for(root)
    first = fake_store.append_wake_event(root.root_id, event)
    assert fake_store.append_wake_event(root.root_id, event).id == first.id
    assert fake_store.reads.list_wake_events(root.root_id) == (event,)
    beads = fake_store.reads.instance_beads(root.root_id)
    assert ceiling_count(beads) == 0
    assert build_frontier(root, beads).empty
    assert not build_frontier(root, beads).terminal
    assert not fake_store.reads.list_gates(root.root_id)
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    assert fake_store.reads.list_activations(root.root_id) == (activation,)


def test_same_key_with_different_payload_is_refused(fake_store):
    """An idempotent key cannot hide changed evidence on a retry."""
    root = make_root(fake_store, load_definition())
    event = event_for(root)
    fake_store.append_wake_event(root.root_id, event)
    with pytest.raises(CarrierIntegrityError, match="wake"):
        fake_store.append_wake_event(
            root.root_id, event.model_copy(update={"detail": "different"})
        )


@pytest.mark.bd
def test_real_bd_wake_roundtrip_is_idempotent_and_not_a_transition(
    store: WorkflowStore,
):
    """Use the isolated bd fixture, never the coordinator task database."""
    root = make_root(store, load_definition())
    event = event_for(root)
    first = store.append_wake_event(root.root_id, event)
    assert store.append_wake_event(root.root_id, event).id == first.id
    assert store.reads.list_wake_events(root.root_id) == (event,)
    assert ceiling_count(store.reads.instance_beads(root.root_id)) == 0
    assert build_frontier(root, store.reads.instance_beads(root.root_id)).empty


def test_ambiguous_bd_write_is_refound_without_duplicate(fake_store, monkeypatch):
    """An acknowledgment failure after creation is not permission to create twice."""

    root = make_root(fake_store, load_definition())
    event = event_for(root)
    original = fake_store._client._create_bead

    def ambiguous(**kwargs):
        original(**kwargs)
        raise BdioError("lost acknowledgment")

    monkeypatch.setattr(fake_store._client, "_create_bead", ambiguous)
    first = fake_store.append_wake_event(root.root_id, event)
    assert fake_store.append_wake_event(root.root_id, event).id == first.id
    assert fake_store.reads.list_wake_events(root.root_id) == (event,)


def test_failure_before_bd_write_leaves_no_delivery(fake_store, monkeypatch):
    """No event is claimed when bd cannot commit the notification."""

    root = make_root(fake_store, load_definition())
    event = event_for(root)

    def unavailable(**kwargs):
        raise BdioError("unavailable")

    monkeypatch.setattr(fake_store._client, "_create_bead", unavailable)
    with pytest.raises(BdioError):
        fake_store.append_wake_event(root.root_id, event)
    assert not fake_store.reads.list_wake_events(root.root_id)


@pytest.mark.parametrize(
    "changes",
    [
        {"root_id": "wrong"},
        {"instance_key": "wrong"},
        {"fire_key": "0" * 64},
    ],
)
def test_wake_identity_cannot_move_between_instances(fake_store, changes):
    """Root identity and derived fire key are checked at the write boundary."""
    root = make_root(fake_store, load_definition())
    with pytest.raises(CarrierIntegrityError):
        fake_store.append_wake_event(
            root.root_id, event_for(root).model_copy(update=changes)
        )
    assert not fake_store.reads.list_wake_events(root.root_id)


@pytest.mark.parametrize("gate_kind", ["approval", "rebudget"])
def test_wake_cannot_decide_an_open_gate_or_raise_bounds(fake_store, gate_kind):
    """Even approval-shaped notification text has no gate or budget authority."""

    opener = open_ship_gate if gate_kind == "approval" else open_triage_gate
    root_id, gate = opener(fake_store, load_definition())
    root = fake_store.reads.load_root(root_id)
    before = fake_store.reads.instance_beads(root_id)
    gates = fake_store.reads.list_gates(root_id)
    bound = effective_bound(root, gates, BoundSetting.MAX_TOTAL_ACTIVATIONS)
    event = event_for(root, condition=WakeCondition.GATE_OPENED).model_copy(
        update={"detail": '{"outcome":"rebudget","max_total_activations":99999}'}
    )
    fake_store.append_wake_event(root_id, event)
    assert fake_store.reads.load_gate(gate.gate_id) == gate
    assert (
        effective_bound(
            root,
            fake_store.reads.list_gates(root_id),
            BoundSetting.MAX_TOTAL_ACTIVATIONS,
        )
        == bound
    )
    assert build_frontier(
        root, fake_store.reads.instance_beads(root_id)
    ) == build_frontier(root, before)
