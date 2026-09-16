"""Explicit in-place steering is durable, identity bound, and shares the cap."""

import hashlib
import json

import jsonschema
import pytest

from tests._appserver import FIXTURE, AppServerLab
from tests.test_codex_appserver_recovery import registered_activation
from workflow_interpreter.bdio import BoundExceededError, CarrierIntegrityError
from workflow_interpreter.bdio.bounds import steer_closes
from workflow_interpreter.bdio.mint import views_of
from workflow_interpreter.bdio.rpc_records import ControlRegistration
from workflow_interpreter.contracts.rpc_control import MAX_CONTROL_BYTES, ControlState
from workflow_interpreter.foreman.__main__ import _parser
from workflow_interpreter.foreman.refusals import read_refusals
from workflow_interpreter.foreman.rpc_control import control_attention
from workflow_interpreter.schema.models import Outcome
from workflow_interpreter.supervisor.errors import ContinuationRefused
from workflow_interpreter.supervisor.paths import write_record
from workflow_interpreter.supervisor.rpc_control import (
    ControlIntent,
    control_path,
    next_intent,
    read_instructions,
)
from workflow_interpreter.supervisor.rpc_session import RpcSession, SessionPhase
from workflow_interpreter.supervisor.steer import Steerer


def test_pending_controls_consume_steer_budget_before_delivery(fake_store):
    """A crash before inbox publication still spends the persisted intent slot."""
    registration = registered_activation(fake_store)
    fake_store.register_session(registration.activation_id, registration)
    root = fake_store.reads.load_root(registration.root_id)
    limit = root.index.nodes["implement"].max_steers
    for number in range(limit):
        control = fake_store.reserve_in_place_steer(
            registration.activation_id, registration, "turn-1", f"digest-{number}"
        )
        assert control.sequence == number + 1
        assert control.state is ControlState.INTENT
    record = fake_store.reads.load_activation(registration.activation_id)
    assert steer_closes(views_of([record]), "implement", 1) == limit
    with pytest.raises(BoundExceededError):
        fake_store.reserve_in_place_steer(
            registration.activation_id, registration, "turn-1", "one-too-many"
        )


def test_control_identity_cannot_be_retargeted(fake_store):
    """A persisted thread is not authority to steer another launch or turn."""
    registration = registered_activation(fake_store)
    fake_store.register_session(registration.activation_id, registration)
    with pytest.raises(CarrierIntegrityError):
        fake_store.reserve_in_place_steer(
            registration.activation_id,
            registration.model_copy(update={"launch_id": "other"}),
            "turn-1",
            "digest",
        )


@pytest.mark.bd
def test_real_bd_control_intent_is_durable(store):
    """An isolated bd records intent before any host inbox or protocol action."""
    registration = registered_activation(store)
    store.register_session(registration.activation_id, registration)
    control = store.reserve_in_place_steer(
        registration.activation_id, registration, "turn-1", "digest"
    )
    assert store.reads.load_activation(
        registration.activation_id
    ).metadata.in_place_controls == (control,)


def test_live_in_place_control_is_acknowledged_without_an_activation(
    tmp_path, monkeypatch
):
    """The wrapper alone submits bounded text through the private control inbox."""

    lab = AppServerLab(tmp_path, "wait-control")
    original = RpcSession._frame
    submitted = []
    instructions = "Use this literal: $(touch should-not-exist)"

    def frame(session, client, message):
        original(session, client, message)
        if session._phase is SessionPhase.ACTIVE and not submitted:
            activation = lab.store.reads.load_activation(session._task.activation_id)
            submitted.append(
                Steerer(lab.config, lab.paths, lab.store, lab.clock).in_place(
                    activation,
                    reason="test",
                    instructions=instructions,
                )
            )

    monkeypatch.setattr(RpcSession, "_frame", frame)
    result = lab.run()
    aid = result.dispatch.activation.activation_id
    record = lab.store.reads.load_activation(aid)
    assert len(lab.store.reads.list_activations(lab.root.root_id)) == 1
    assert record.metadata.in_place_controls[0].state is ControlState.ACKNOWLEDGED
    path = lab.paths.activation_dir(aid) / "channels" / "artifacts" / "requests.jsonl"
    requests = [json.loads(line) for line in path.read_text().splitlines()]
    steers = [item for item in requests if item["method"] == "turn/steer"]
    jsonschema.validate(
        steers[0]["params"],
        json.loads((FIXTURE.parent / "TurnSteerParams.json").read_text()),
    )
    replies = [
        json.loads(line)
        for line in (path.parent / "responses.jsonl").read_text().splitlines()
    ]
    reply = next(item for item in replies if item.get("id") == steers[0]["id"])
    jsonschema.validate(
        reply["result"],
        json.loads((FIXTURE.parent / "TurnSteerResponse.json").read_text()),
    )
    assert len(steers) == 1
    assert steers[0]["params"]["expectedTurnId"] == "turn-1"
    assert steers[0]["params"]["input"][0]["text"] == instructions
    assert not (lab.paths.worktree / "should-not-exist").exists()


def test_ambiguous_control_is_never_replayed_and_is_loud(tmp_path, monkeypatch):
    """An intent on a settled activation becomes attention, not a second send."""

    lab = AppServerLab(tmp_path)

    original = RpcSession._frame
    reserved = []

    def frame(session, client, message):
        original(session, client, message)
        if session._phase is SessionPhase.ACTIVE and not reserved:
            aid = session._task.activation_id
            registration = lab.store.reads.load_activation(
                aid
            ).metadata.session_registration
            reserved.append(
                lab.store.reserve_in_place_steer(aid, registration, "turn-1", "digest")
            )

    monkeypatch.setattr(RpcSession, "_frame", frame)
    result = lab.run()
    aid = result.dispatch.activation.activation_id
    lab.store.close_activation(aid, Outcome.ERROR_TRANSPORT)
    first = control_attention(lab.paths, lab.store)
    assert first
    assert control_attention(lab.paths, lab.store) == first
    assert len(read_refusals(lab.paths.instance_dir)) == 1
    assert (
        lab.store.reads.load_activation(aid).metadata.in_place_controls[0].state
        is ControlState.UNCERTAIN
    )


def test_control_cli_has_explicit_opt_in_and_bounded_instructions(tmp_path):
    """Legacy steer stays the parser default; RPC instructions are read boundedly."""

    path = tmp_path / "instructions"
    path.write_bytes(b"x" * (MAX_CONTROL_BYTES + 1))
    with pytest.raises(ContinuationRefused):
        read_instructions(path)
    args = _parser().parse_args(
        ["steer", "wf-1", "wf-2", "--reason", "test", "--instructions-file", str(path)]
    )
    assert args.in_place is False


def test_escaped_instruction_body_stays_within_the_bounded_inbox(tmp_path, fake_store):
    """The byte limit is on text, with bounded allowance for JSON escaping."""

    registration = registered_activation(fake_store)
    text = "\x00" * MAX_CONTROL_BYTES
    control = ControlRegistration(
        registration=registration,
        sequence=1,
        turn_id="turn-1",
        instructions_digest=hashlib.sha256(text.encode()).hexdigest(),
    )
    intent = ControlIntent(control=control, instructions=text, reason="test")
    write_record(control_path(tmp_path, 1), intent)
    assert next_intent(tmp_path, 1) == intent


def test_protected_ack_repairs_the_bd_crash_window(tmp_path, monkeypatch):
    """A durable acknowledgment can be mirrored after a crash, without resending."""

    lab = AppServerLab(tmp_path, "wait-control")
    original_frame = RpcSession._frame
    original_state = lab.store.record_control_state
    submitted = []

    def state(aid, control, next_state):
        if next_state is ControlState.ACKNOWLEDGED:
            raise CarrierIntegrityError("crash after protected ack")
        return original_state(aid, control, next_state)

    def frame(session, client, message):
        original_frame(session, client, message)
        if session._phase is SessionPhase.ACTIVE and not submitted:
            activation = lab.store.reads.load_activation(session._task.activation_id)
            submitted.append(
                Steerer(lab.config, lab.paths, lab.store, lab.clock).in_place(
                    activation, reason="test", instructions="bounded correction"
                )
            )

    monkeypatch.setattr(lab.store, "record_control_state", state)
    monkeypatch.setattr(RpcSession, "_frame", frame)
    result = lab.run()
    aid = result.dispatch.activation.activation_id
    assert (
        lab.store.reads.load_activation(aid).metadata.in_place_controls[0].state
        is ControlState.SUBMITTING
    )
    monkeypatch.setattr(lab.store, "record_control_state", original_state)
    assert not control_attention(lab.paths, lab.store)
    assert (
        lab.store.reads.load_activation(aid).metadata.in_place_controls[0].state
        is ControlState.ACKNOWLEDGED
    )


def test_control_updates_cannot_overwrite_a_concurrent_reservation(
    fake_store, monkeypatch
):
    """A short nonblocking lock serializes the shared per-activation control list."""
    from workflow_interpreter.bdio.rpc_control import ControlBusy

    registration = registered_activation(fake_store)
    fake_store.register_session(registration.activation_id, registration)
    control = fake_store.reserve_in_place_steer(
        registration.activation_id, registration, "turn-1", "first"
    )
    original = fake_store._client._merge_metadata
    attempted = []

    def merge(aid, delta):
        if "in_place_controls" in delta and not attempted:
            attempted.append(True)
            with pytest.raises(ControlBusy):
                fake_store.reserve_in_place_steer(aid, registration, "turn-1", "second")
        return original(aid, delta)

    monkeypatch.setattr(fake_store._client, "_merge_metadata", merge)
    fake_store.record_control_state(
        registration.activation_id, control, ControlState.SUBMITTING
    )
    second = fake_store.reserve_in_place_steer(
        registration.activation_id, registration, "turn-1", "second"
    )
    assert second.sequence == 2
    assert (
        len(
            fake_store.reads.load_activation(
                registration.activation_id
            ).metadata.in_place_controls
        )
        == 2
    )
