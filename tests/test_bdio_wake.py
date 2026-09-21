"""Wake events are durable notifications, never routing or approval authority."""

import pytest

from tests._bdio import entry_request, load_definition, make_root
from tests._gates import open_ship_gate, open_triage_gate
from workflow_interpreter.bdio import CarrierIntegrityError
from workflow_interpreter.bdio.bounds import ceiling_count, effective_bound
from workflow_interpreter.bdio.errors import StoreError
from workflow_interpreter.bdio.keys import wake_fire_key
from workflow_interpreter.bdio.reads import next_seq
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
        fire_key=wake_fire_key(
            root.root_id, root.metadata.instance_key, condition, cursor
        ),
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
    beads = fake_store.reads.instance_records(root.root_id)
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


def test_ambiguous_bd_write_is_refound_without_duplicate(fake_store, monkeypatch):
    """An acknowledgment failure after creation is not permission to create twice."""

    root = make_root(fake_store, load_definition())
    event = event_for(root)
    original = fake_store._client._create_row

    def ambiguous(new):
        original(new)
        raise StoreError("lost acknowledgment")

    monkeypatch.setattr(fake_store._client, "_create_row", ambiguous)
    first = fake_store.append_wake_event(root.root_id, event)
    assert fake_store.append_wake_event(root.root_id, event).id == first.id
    assert fake_store.reads.list_wake_events(root.root_id) == (event,)


def test_failure_before_bd_write_leaves_no_delivery(fake_store, monkeypatch):
    """No event is claimed when bd cannot commit the notification."""

    root = make_root(fake_store, load_definition())
    event = event_for(root)

    def unavailable(new):
        raise StoreError("unavailable")

    monkeypatch.setattr(fake_store._client, "_create_row", unavailable)
    with pytest.raises(StoreError):
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
    before = fake_store.reads.instance_records(root_id)
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
        root, fake_store.reads.instance_records(root_id)
    ) == build_frontier(root, before)


def test_wake_append_cannot_steal_a_reserved_activation_sequence(
    fake_store, monkeypatch
):
    """A monitor append in the driver's read/create window uses another namespace."""

    root = make_root(fake_store, load_definition())
    original = fake_store._client._create_row
    wakes = []

    def interleave(new):
        """Commit a notification after mint selected its sequence, before its write."""
        if new.metadata.get("wf_kind") == "activation":
            wakes.append(fake_store.append_wake_event(root.root_id, event_for(root)))
        return original(new)

    monkeypatch.setattr(fake_store._client, "_create_row", interleave)
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    assert activation.metadata.seq == 1
    assert wakes[0].metadata["seq"] == -1
    second = fake_store.append_wake_event(root.root_id, event_for(root, "second"))
    assert second.metadata["seq"] == -2
    assert next_seq(fake_store.reads.instance_records(root.root_id)) == 2


def test_lost_wake_payload_does_not_reuse_sequence(fake_store, ledger):
    """Unreadable notifications still occupy their monotonic sequence slot."""
    root = make_root(fake_store, load_definition())
    first = fake_store.append_wake_event(root.root_id, event_for(root))
    # Straight at the column, because the point is a row nothing can PARSE:
    # every typed write refuses to leave one, which is why this has to be
    # stated rather than provoked.
    with ledger.transaction() as connection:
        connection.execute(
            "UPDATE events SET payload_json = NULL WHERE event_id = ?", (first.id,)
        )
    second = fake_store.append_wake_event(root.root_id, event_for(root, "second"))
    assert second.metadata["seq"] == -2
