"""Protected registration and ambiguous RPC recovery, with no live vendor calls."""

import pytest

from tests._bdio import (
    RESOLVED_CONFIG,
    entry_request,
    handle,
    load_definition,
    make_root,
)
from workflow_interpreter.bdio import CarrierIntegrityError
from workflow_interpreter.bdio.rpc_records import SessionRegistration


def registered_activation(store):
    """Mint a root with explicit app-server runner pins and a dispatched identity."""
    settings = tuple(
        item.model_copy(update={"value": "codex-appserver"})
        if item.key.endswith(".runner")
        else item
        for item in RESOLVED_CONFIG
    )
    root = make_root(store, load_definition(), *settings)
    activation = store.mint_activation(
        root.root_id, entry_request(runner_profile="codex-appserver", session_id="")
    ).activation
    process = handle(session_id="")
    store.record_dispatch(activation.activation_id, process, launch_id="launch-1")
    return SessionRegistration(
        root_id=root.root_id,
        activation_id=activation.activation_id,
        launch_id="launch-1",
        handle=process,
        thread_id="thread-1",
        runner_version="0.154.0",
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


def test_dead_rpc_owner_is_recovered_without_reconnecting_or_resubmitting(tmp_path):
    """A living server whose owner was lost is terminated before transport recovery."""
    import os

    from tests._appserver import AppServerLab
    from tests._profiles import task_builder
    from tests._supervisor import entry_mint
    from workflow_interpreter.schema.models import Outcome
    from workflow_interpreter.supervisor import procfs
    from workflow_interpreter.supervisor.launch import Dispatcher
    from workflow_interpreter.supervisor.models import LaunchReceipt, RecoveryCase
    from workflow_interpreter.supervisor.paths import read_record, write_record
    from workflow_interpreter.supervisor.recover import Recovery

    lab = AppServerLab(tmp_path)
    dispatcher = Dispatcher(lab.paths, lab.store, lab.clock, host_env=dict(os.environ))
    result = dispatcher.dispatch(
        entry_mint(runner_profile="codex-appserver", session_id=""),
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
