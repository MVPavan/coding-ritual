"""Session reuse is graph-pinned, app-server-only and derived at mint."""

import re

import pytest

from tests._bdio import RESOLVED_CONFIG, entry_request, handle, make_root
from tests._helpers import VALID_FIXTURE
from workflow_interpreter import load_graph
from workflow_interpreter.bdio import CarrierIntegrityError, MintReason
from workflow_interpreter.bdio.rpc_records import (
    SessionCompletion,
    SessionRegistration,
)
from workflow_interpreter.bdio.sessions import choose_source
from workflow_interpreter.contracts.sessions import SessionReuse
from workflow_interpreter.schema.models import Outcome


def reuse_graph(tmp_path, reuse):
    """Only the test graph opts in; shipped graphs keep fresh sessions."""
    path = tmp_path / "reuse.toml"
    text = VALID_FIXTURE.read_text()
    text = re.sub(
        r"writes\s*=\s*true", f'writes = true\nsession_reuse = "{reuse}"', text, count=1
    )
    path.write_text(text)
    return load_graph(path)


@pytest.mark.parametrize("reuse", ["fresh", "same-node"])
def test_reuse_setting_refuses_non_appserver_roots(tmp_path, fake_store, reuse):
    """Even explicit fresh is an app-server setting, never ignored by exec."""
    with pytest.raises(CarrierIntegrityError, match="app-server"):
        make_root(fake_store, reuse_graph(tmp_path, reuse))


def test_reuse_choice_is_part_of_graph_identity(tmp_path):
    """Changing history policy changes the pinned content hash."""
    fresh = reuse_graph(tmp_path, "fresh")
    same = reuse_graph(tmp_path, "same-node")
    assert fresh.content_hash != same.content_hash
    assert (
        next(
            node for node in same.document.node if node.name == "implement"
        ).session_reuse
        is SessionReuse.SAME_NODE
    )


def app_root(tmp_path, store, reuse):
    """Pin the real app-server identity in this isolated test root."""
    settings = tuple(
        item.model_copy(update={"value": "codex-appserver"})
        if item.key.endswith(".runner")
        else item
        for item in RESOLVED_CONFIG
    )
    return make_root(store, reuse_graph(tmp_path, reuse), *settings)


def finish_source(store, root, outcome=None):
    """Create the immutable registration and explicit completed-turn fact."""

    activation = store.mint_activation(
        root.root_id, entry_request(runner_profile="codex-appserver", session_id="")
    ).activation
    process = handle(session_id="")
    store.record_dispatch(activation.activation_id, process, launch_id="launch-1")
    registration = SessionRegistration(
        root_id=root.root_id,
        activation_id=activation.activation_id,
        launch_id="launch-1",
        handle=process,
        thread_id="thread-1",
        model=activation.metadata.model,
        effort="medium",
        policy_digest="legacy",
        state_path="/state/node",
    )
    store.register_session(activation.activation_id, registration)
    store.record_session_completion(
        activation.activation_id,
        SessionCompletion(registration=registration, turn_id="turn-1"),
    )
    store.close_activation(activation.activation_id, outcome or Outcome.FAIL_CODE)
    return registration


@pytest.mark.parametrize("reuse", ["fresh", "same-node"])
def test_reentry_binds_history_only_when_the_graph_opts_in(tmp_path, fake_store, reuse):
    """The caller's session string cannot select arbitrary history."""

    root = app_root(tmp_path, fake_store, reuse)
    source = finish_source(fake_store, root)
    request = entry_request(
        runner_profile="codex-appserver", session_id="caller-invented"
    ).model_copy(
        update={
            "mint_reason": MintReason.EDGE,
            "predecessor_activation_id": source.activation_id,
        }
    )
    minted = fake_store.mint_activation(root.root_id, request).activation
    if reuse == "same-node":
        assert minted.metadata.session_reuse_source == source
        assert minted.metadata.session_id == source.thread_id
    else:
        assert minted.metadata.session_reuse_source is None
        assert minted.metadata.session_id == ""
    assert fake_store.mint_activation(root.root_id, request).activation == minted


@pytest.mark.parametrize(
    "field,value",
    [
        ("model", "other"),
        ("effort", "high"),
        ("policy_digest", "different"),
        ("root_id", "other-root"),
    ],
)
def test_incompatible_registered_history_is_not_selected(
    tmp_path, fake_store, field, value
):
    """Only completed history with the same pinned authority may cross rounds."""

    root = app_root(tmp_path, fake_store, "same-node")
    registration = finish_source(fake_store, root)
    source = fake_store.reads.load_activation(registration.activation_id)
    changed = registration.model_copy(update={field: value})
    source = source.model_copy(
        update={
            "metadata": source.metadata.model_copy(
                update={
                    "session_registration": changed,
                    "session_completion": source.metadata.session_completion.model_copy(
                        update={"registration": changed}
                    ),
                }
            )
        }
    )
    request = entry_request(runner_profile="codex-appserver", session_id="").model_copy(
        update={
            "mint_reason": MintReason.EDGE,
            "predecessor_activation_id": registration.activation_id,
        }
    )
    assert choose_source(root, request, [source]) is None


def test_infra_retry_of_deliberate_steer_keeps_its_bound_session(tmp_path, fake_store):
    """Fresh defaults cannot erase §8.1 deliberate continuation after a crash."""

    root = app_root(tmp_path, fake_store, "fresh")
    source = finish_source(fake_store, root, Outcome.STEERED)
    continuation = fake_store.mint_activation(
        root.root_id,
        entry_request(
            runner_profile="codex-appserver", session_id=source.thread_id
        ).model_copy(
            update={
                "mint_reason": MintReason.STEER_CONTINUATION,
                "predecessor_activation_id": source.activation_id,
            }
        ),
    ).activation
    fake_store.close_activation(continuation.activation_id, Outcome.ERROR_TRANSPORT)
    retry = fake_store.mint_activation(
        root.root_id,
        entry_request(
            runner_profile="codex-appserver", session_id=source.thread_id
        ).model_copy(
            update={
                "mint_reason": MintReason.INFRA_RETRY,
                "predecessor_activation_id": continuation.activation_id,
            }
        ),
    ).activation
    assert retry.metadata.session_reuse_source == source
    assert retry.metadata.session_id == source.thread_id
