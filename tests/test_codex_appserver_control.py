"""Explicit in-place steering is durable, identity bound, and shares the cap."""

import hashlib
import json

import jsonschema
import pytest

from tests._appserver import FIXTURE, AppServerLab
from tests._bdio import entry_request, handle
from tests._foreman import DEFAULT_LAB_ROLES, ForemanLab
from tests._foreman import entry_request as foreman_entry_request
from tests.test_codex_appserver_recovery import registered_activation
from workflow_interpreter.bdio import (
    BoundExceededError,
    CarrierIntegrityError,
    MintReason,
    bounds,
)
from workflow_interpreter.bdio.bounds import steer_closes
from workflow_interpreter.bdio.mint import views_of
from workflow_interpreter.bdio.rpc_control import ControlBusy
from workflow_interpreter.bdio.rpc_records import (
    ControlRegistration,
    SessionRegistration,
)
from workflow_interpreter.contracts.rpc_control import MAX_CONTROL_BYTES, ControlState
from workflow_interpreter.foreman import __main__ as cli
from workflow_interpreter.foreman.__main__ import _parser
from workflow_interpreter.foreman.refusals import read_refusals
from workflow_interpreter.foreman.rpc_control import control_attention
from workflow_interpreter.inspector.errors import ContinuationRefused
from workflow_interpreter.inspector.paths import write_record
from workflow_interpreter.inspector.rpc_control import (
    ControlIntent,
    control_path,
    next_intent,
    read_instructions,
)
from workflow_interpreter.inspector.rpc_session import RpcSession, SessionPhase
from workflow_interpreter.inspector.steer import Steerer
from workflow_interpreter.schema.models import Outcome


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
    store.record_control_state(
        registration.activation_id, control, ControlState.UNCERTAIN
    )
    store.record_control_state(
        registration.activation_id,
        control.model_copy(update={"state": ControlState.UNCERTAIN}),
        ControlState.RESOLVED,
        resolution_reason="operator inspected uncertainty",
    )
    persisted = store.reads.load_activation(registration.activation_id).metadata
    assert persisted.in_place_controls[0].state is ControlState.RESOLVED
    assert persisted.deviations[-1].kind == "control_uncertain"


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
    """An intent on a settled activation becomes a deviation without blocking progress."""

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
    assert first == ()
    assert control_attention(lab.paths, lab.store) == ()
    assert len(read_refusals(lab.paths.instance_dir)) == 1
    assert (
        lab.store.reads.load_activation(aid).metadata.in_place_controls[0].state
        is ControlState.RESOLVED
    )
    assert lab.store.reads.load_activation(aid).metadata.deviations[-1].kind == (
        "control_uncertain"
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


def test_unpinned_steer_limit_is_uncapped_in_both_paths(fake_store, monkeypatch):
    """Omitting the bound has the same meaning for relaunch and in-place control."""

    registration = registered_activation(fake_store).model_copy(
        update={
            "policy_digest": "c49fea7425fa7f8699897a97c159c6690267d9003bb78c53fafa8fc15c325d84"
        }
    )
    fake_store.register_session(registration.activation_id, registration)
    original = bounds.effective_bound
    monkeypatch.setattr(
        bounds,
        "effective_bound",
        lambda *args: (
            None if args[2] is bounds.BoundSetting.MAX_STEERS else original(*args)
        ),
    )
    activation = fake_store.reads.load_activation(registration.activation_id)
    request = entry_request(crew_profile="codex-appserver").model_copy(
        update={
            "mint_reason": MintReason.STEER_CONTINUATION,
            "predecessor_activation_id": registration.activation_id,
        }
    )
    fake_store._preflight_steer_continuation(registration.root_id, activation, request)
    for number in range(4):
        fake_store.reserve_in_place_steer(
            registration.activation_id, registration, "turn-1", f"digest-{number}"
        )


def uncertain_foreman(tmp_path):
    """A real foreman with a durable ambiguous control and inert vendor boundary."""

    roles = {
        name: binding.model_copy(update={"profile": "codex-appserver"})
        for name, binding in DEFAULT_LAB_ROLES.items()
    }
    lab = ForemanLab(tmp_path, roles=roles)
    root = lab.instantiate()
    activation = (
        lab.wiring()
        .store.mint_activation(
            root.root_id, foreman_entry_request(crew_profile="codex-appserver")
        )
        .activation
    )
    aid = activation.activation_id
    process = handle(session_id="").model_copy(
        update={"log_path": str(lab.wiring().paths.log(aid))}
    )
    lab.store.record_dispatch(aid, process, launch_id="test-launch")
    registration = SessionRegistration(
        root_id=root.root_id,
        activation_id=aid,
        launch_id="test-launch",
        handle=process,
        thread_id="thread-1",
        model="fake",
        effort="medium",
        policy_digest="test",
        state_path=str(lab.wiring().paths.activation_dir(aid) / "vendor-state"),
    )
    lab.store.register_session(aid, registration)
    control = lab.store.reserve_in_place_steer(aid, registration, "turn-1", "digest")
    lab.store.record_control_state(aid, control, ControlState.UNCERTAIN)
    return lab, aid


def test_closed_uncertain_control_does_not_block_root_progress(tmp_path):
    """The former permanent wedge now records deviation and mints the next attempt."""
    lab, aid = uncertain_foreman(tmp_path)
    lab.store.close_activation(aid, Outcome.ERROR_TRANSPORT)
    report = lab.tick()
    assert report.refusals == ()
    assert report.dispatched is not None
    assert report.dispatched != aid
    meta = lab.store.reads.load_activation(aid).metadata
    assert meta.in_place_controls[0].state is ControlState.RESOLVED
    assert len(meta.deviations) == 1
    assert meta.deviations[0].kind == "control_uncertain"


def test_operator_command_resolves_live_uncertain_control(tmp_path, monkeypatch):
    """Explicit acknowledgment clears attention without replay or a budget refund."""

    lab, aid = uncertain_foreman(tmp_path)
    paths = lab.wiring().paths
    assert control_attention(paths, lab.store)
    monkeypatch.setattr(cli, "_composition", lambda _: lab.composition)
    assert (
        cli.main(
            [
                "steer",
                lab.root.root_id,
                aid,
                "--acknowledge-uncertain",
                "--reason",
                "operator inspected the interrupted control",
            ]
        )
        == 0
    )
    assert control_attention(paths, lab.store) == ()
    meta = lab.store.reads.load_activation(aid).metadata
    assert not meta.is_settled
    assert meta.in_place_controls[0].state is ControlState.RESOLVED
    assert meta.deviations[0].recorded_at == "operator"
    assert (
        steer_closes(
            views_of(lab.store.reads.list_activations(lab.root.root_id)), "implement", 1
        )
        == 1
    )


def test_busy_reconciliation_defers_resolution_until_uncertainty_is_durable(
    tmp_path, monkeypatch
):
    """A lock released between writes must not resolve a merely inferred state."""
    lab, aid = uncertain_foreman(tmp_path)
    control = lab.store.reads.load_activation(aid).metadata.in_place_controls[0]
    lab.store._client._merge_metadata(
        aid,
        {
            "in_place_controls": [
                control.model_copy(
                    update={"state": ControlState.SUBMITTING}
                ).model_dump(mode="json")
            ]
        },
    )
    lab.store.close_activation(aid, Outcome.ERROR_TRANSPORT)
    original = lab.store.record_control_state
    attempts = []

    def busy_once(activation_id, item, state, **kwargs):
        attempts.append(state)
        if len(attempts) == 1:
            raise ControlBusy("injected contention")
        return original(activation_id, item, state, **kwargs)

    monkeypatch.setattr(lab.store, "record_control_state", busy_once)
    assert control_attention(lab.wiring().paths, lab.store) == ()
    assert attempts == [ControlState.UNCERTAIN]
    assert control_attention(lab.wiring().paths, lab.store) == ()
    assert lab.store.reads.load_activation(aid).metadata.in_place_controls[0].state is (
        ControlState.RESOLVED
    )
