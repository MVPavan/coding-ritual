"""Protected registration and ambiguous RPC recovery, with no live vendor calls."""

import json
import os

import pytest

from tests._appserver import AppServerLab
from tests._bdio import (
    RESOLVED_CONFIG,
    entry_request,
    handle,
    load_definition,
    make_root,
)
from tests._inspector import entry_mint
from tests._profiles import task_builder
from workflow_interpreter.bdio import CarrierIntegrityError
from workflow_interpreter.bdio.rpc_records import SessionCompletion, SessionRegistration
from workflow_interpreter.inspector import procfs
from workflow_interpreter.inspector.launch import Dispatcher
from workflow_interpreter.inspector.models import LaunchReceipt, RecoveryCase
from workflow_interpreter.inspector.paths import read_record, write_record
from workflow_interpreter.inspector.recover import Recovery
from workflow_interpreter.inspector.rpc_session import RpcSession
from workflow_interpreter.profiles.codex_rpc import RpcClient
from workflow_interpreter.schema.models import Outcome


def registered_activation(store):
    """Mint a root with explicit app-server crew pins and a dispatched identity."""
    settings = tuple(
        item.model_copy(update={"value": "codex-appserver"})
        if item.key.endswith(".crew")
        else item
        for item in RESOLVED_CONFIG
    )
    root = make_root(store, load_definition(), *settings)
    activation = store.mint_activation(
        root.root_id, entry_request(crew_profile="codex-appserver", session_id="")
    ).activation
    process = handle(session_id="").model_copy(
        update={
            "log_path": str(
                store._client.workspace
                / "wrapper"
                / activation.activation_id
                / "run.jsonl"
            )
        }
    )
    store.record_dispatch(activation.activation_id, process, launch_id="launch-1")
    return SessionRegistration(
        root_id=root.root_id,
        activation_id=activation.activation_id,
        launch_id="launch-1",
        handle=process,
        thread_id="thread-1",
        crew_version="0.154.0",
        model=activation.metadata.model,
        effort="medium",
        policy_digest="policy-1",
        state_path="/state/root/node",
    )


def test_registration_is_idempotent_and_preserves_process_handle(fake_store):
    """Thread identity never rewrites the process identity used for death proof."""
    registration = registered_activation(fake_store)
    first = fake_store.register_session(registration.activation_id, registration)
    second = fake_store.register_session(registration.activation_id, registration)
    assert first == second
    assert second.metadata.session_id == "thread-1"
    assert second.metadata.handle == registration.handle


@pytest.mark.parametrize(
    "changes",
    [
        {"launch_id": "another-launch"},
        {"root_id": "another-root"},
        {"activation_id": "another-activation"},
    ],
)
def test_registration_rejects_wrong_identity(fake_store, changes):
    """A thread cannot be attached to a different launch, root, or activation."""
    registration = registered_activation(fake_store)
    with pytest.raises(CarrierIntegrityError):
        fake_store.register_session(
            registration.activation_id, registration.model_copy(update=changes)
        )


def test_registered_thread_cannot_be_replaced(fake_store):
    """Even the same live process cannot silently register a second vendor thread."""
    registration = registered_activation(fake_store)
    fake_store.register_session(registration.activation_id, registration)
    with pytest.raises(CarrierIntegrityError):
        fake_store.register_session(
            registration.activation_id,
            registration.model_copy(update={"thread_id": "thread-2"}),
        )


@pytest.mark.bd
def test_real_bd_session_registration(store):
    """Typed registration roundtrips through an isolated real bd database."""
    registration = registered_activation(store)
    record = store.register_session(registration.activation_id, registration)
    assert record.metadata.session_registration == registration
    assert store.register_session(registration.activation_id, registration) == record
    completion = SessionCompletion(registration=registration, turn_id="turn-1")
    completed = store.record_session_completion(registration.activation_id, completion)
    assert completed.metadata.session_completion == completion
    assert (
        store.record_session_completion(registration.activation_id, completion)
        == completed
    )


def test_dead_rpc_owner_is_recovered_without_reconnecting_or_resubmitting(tmp_path):
    """A living server whose owner was lost is terminated before transport recovery."""

    lab = AppServerLab(tmp_path)
    dispatcher = Dispatcher(lab.paths, lab.store, lab.clock, host_env=dict(os.environ))
    result = dispatcher.dispatch(
        entry_mint(crew_profile="codex-appserver", session_id=""),
        lab.profile,
        task_builder(lab.paths.worktree, lab.node),
        lambda activation: lab.workspace.prepare(activation, lab.node),
    )
    aid = result.activation.activation_id
    pipes, _ = dispatcher.take_rpc()
    try:
        receipt = read_record(lab.paths.receipt(aid), LaunchReceipt)
        write_record(
            lab.paths.receipt(aid),
            receipt.model_copy(
                update={
                    "owner": receipt.owner.model_copy(
                        update={"proc_start_time": "lost-owner"}
                    ),
                }
            ),
        )
        recovery = Recovery(lab.config, lab.paths, lab.store, lab.workspace, lab.clock)
        classification = recovery.classify(result.activation)
        assert classification.case is RecoveryCase.DEAD_WITHOUT_EXIT
        recovered = recovery.resolve(result.activation, lab.node)
        assert recovered.closed.metadata.outcome is Outcome.ERROR_TRANSPORT
        assert result.exec_count == 1
        assert not (lab.paths.activation_dir(aid) / "turn.json").exists()
    finally:
        pipes.close()
        procfs.terminate(lab.config, result.handle, lab.clock)


@pytest.mark.parametrize("after_submission", [False, True])
def test_ambiguous_turn_intent_is_recovered_without_resend(
    tmp_path, monkeypatch, after_submission
):
    """Losing the pipe owner never authorizes replay, before or after a send."""

    class OwnerLost(BaseException):
        """Injected process death bypasses normal protocol error handling."""

    lab = AppServerLab(tmp_path, "hang-after-submit")
    save = RpcSession._save
    poll = RpcClient.poll

    def crash_before(session):
        save(session)
        if session._turn.phase.value == "intent":
            raise OwnerLost()

    def crash_after(client, *args):
        result = poll(client, *args)
        records = lab.store.reads.list_activations(lab.root.root_id)
        if records:
            path = (
                lab.paths.activation_dir(records[0].activation_id)
                / "channels"
                / "artifacts"
                / "requests.jsonl"
            )
            if path.exists() and '"turn/start"' in path.read_text():
                raise OwnerLost()
        return result

    if after_submission:
        monkeypatch.setattr(RpcClient, "poll", crash_after)
    else:
        monkeypatch.setattr(RpcSession, "_save", crash_before)
    with pytest.raises(OwnerLost):
        lab.run()
    activation = lab.store.reads.list_activations(lab.root.root_id)[0]
    aid = activation.activation_id
    receipt = read_record(lab.paths.receipt(aid), LaunchReceipt)
    write_record(
        lab.paths.receipt(aid),
        receipt.model_copy(
            update={
                "owner": receipt.owner.model_copy(
                    update={"proc_start_time": "lost-owner"}
                )
            }
        ),
    )
    recovery = Recovery(lab.config, lab.paths, lab.store, lab.workspace, lab.clock)
    recovered = recovery.resolve(activation, lab.node)
    assert recovered.closed.metadata.outcome is Outcome.ERROR_TRANSPORT
    requests = (
        lab.paths.activation_dir(aid) / "channels" / "artifacts" / "requests.jsonl"
    ).read_text()
    assert requests.count('"turn/start"') == int(after_submission)
    assert recovered.closed.metadata.session_registration is not None
    if after_submission:
        submitted = next(
            json.loads(line)
            for line in requests.splitlines()
            if json.loads(line).get("method") == "turn/start"
        )
        replies = (
            (
                lab.paths.activation_dir(aid)
                / "channels"
                / "artifacts"
                / "responses.jsonl"
            )
            .read_text()
            .splitlines()
        )
        assert not any(
            json.loads(line).get("id") == submitted["id"] for line in replies
        )
        assert (
            json.loads((lab.paths.activation_dir(aid) / "turn.json").read_text())[
                "turn_id"
            ]
            is None
        )

    assert (
        json.loads((lab.paths.activation_dir(aid) / "turn.json").read_text())["phase"]
        == "intent"
    )
