"""Session reuse is graph-pinned, app-server-only and derived at mint."""

import hashlib
import json
import re

import pytest

from tests._appserver import AppServerLab
from tests._bdio import RESOLVED_CONFIG, entry_request, handle, make_root
from tests._foreman import ForemanLab
from tests._helpers import VALID_FIXTURE
from tests._inspector import entry_mint
from workflow_interpreter import GraphValidationError, load_graph
from workflow_interpreter.bdio import (
    CarrierIntegrityError,
    ConfigSource,
    MintReason,
    ResolvedSetting,
)
from workflow_interpreter.bdio.rpc_records import (
    SessionCompletion,
    SessionRegistration,
)
from workflow_interpreter.bdio.sessions import choose_source
from workflow_interpreter.contracts.codex import CODEX_VERSION
from workflow_interpreter.contracts.execution import EXECUTION_POLICY_KEY
from workflow_interpreter.contracts.sessions import (
    MSG_SESSION_MODE_CONFLICT,
    SessionMode,
    SessionReuse,
)
from workflow_interpreter.foreman.config import CrewBinding
from workflow_interpreter.foreman.execution import resolved_node
from workflow_interpreter.inspector.models import SteerIntent
from workflow_interpreter.inspector.paths import write_record
from workflow_interpreter.inspector.rpc_state import state_for
from workflow_interpreter.schema.loader import canonical_bytes, load_pinned_body
from workflow_interpreter.schema.models import Outcome


def reuse_graph(tmp_path, reuse):
    """Only the test graph opts in; shipped graphs keep fresh sessions."""
    path = tmp_path / "reuse.toml"
    text = VALID_FIXTURE.read_text()
    mode = "resume" if reuse == "same-node" else reuse
    text = re.sub(
        r"writes\s*=\s*true", f'writes = true\nsession_mode = "{mode}"', text, count=1
    )
    path.write_text(text)
    return load_graph(path)


def legacy_pinned_graph(tmp_path):
    """Build the old canonical spelling through the pinned-body boundary."""
    modern = canonical_bytes(reuse_graph(tmp_path, "resume").document)
    legacy = modern.replace(b'"session_mode":"resume"', b'"session_reuse":"same-node"')
    assert legacy != modern
    return load_pinned_body(legacy)


def test_authored_session_reuse_is_rejected_but_legacy_pin_decodes(tmp_path):
    """Only immutable old bodies retain session_reuse compatibility."""
    legacy_path = tmp_path / "legacy.toml"
    legacy_path.write_text(
        re.sub(
            r"writes\s*=\s*true",
            'writes = true\nsession_reuse = "same-node"',
            VALID_FIXTURE.read_text(),
            count=1,
        )
    )
    with pytest.raises(GraphValidationError, match="author session_mode instead"):
        load_graph(legacy_path)

    legacy = legacy_pinned_graph(tmp_path)
    node = next(item for item in legacy.document.node if item.name == "implement")
    assert node.session_reuse is SessionReuse.SAME_NODE
    assert node.session_mode is SessionMode.RESUME
    body = canonical_bytes(legacy.document).decode()
    assert '"session_reuse":"same-node"' in body
    assert '"session_mode"' not in body

    conflict = canonical_bytes(reuse_graph(tmp_path, "resume").document).replace(
        b'"session_mode":"resume"',
        b'"session_mode":"resume","session_reuse":"same-node"',
    )
    with pytest.raises(GraphValidationError, match=MSG_SESSION_MODE_CONFLICT):
        load_pinned_body(conflict)


def test_legacy_appserver_graph_resolves_pins_and_instantiates(tmp_path):
    """A legacy pin becomes one effective resume authority at execution."""
    roles = {
        "implementer": CrewBinding(
            profile="codex-appserver", model="fake", effort="medium"
        ),
        "critic": CrewBinding(profile="fake", model="fake", effort="medium"),
        "scribe": CrewBinding(profile="fake", model="fake", effort="medium"),
    }
    lab = ForemanLab(tmp_path, roles=roles)
    lab.definition = legacy_pinned_graph(tmp_path)

    root = lab.instantiate()

    settings = {item.key: item.value for item in root.metadata.resolved_config}
    assert settings["node.implement.session_mode"] == SessionMode.RESUME
    assert resolved_node(root, "implement").node.session_mode is SessionMode.RESUME


def app_root(tmp_path, store, reuse):
    """Pin the real app-server identity in this isolated test root."""
    settings = tuple(
        item.model_copy(update={"value": "codex-appserver"})
        if item.key.endswith(".crew")
        else item
        for item in RESOLVED_CONFIG
    )
    mode = "resume" if reuse == "same-node" else reuse
    return make_root(
        store,
        reuse_graph(tmp_path, reuse),
        *settings,
        ResolvedSetting(
            key="node.implement.session_mode",
            value=mode,
            source=ConfigSource.GRAPH_DEFAULT,
        ),
    )


def exec_root(tmp_path, store):
    """Pin a resumable exec crew without app-server registrations."""
    return make_root(
        store,
        reuse_graph(tmp_path, "resume"),
        ResolvedSetting(
            key="node.implement.crew",
            value="codex",
            source=ConfigSource.ROLE_BINDING,
        ),
        ResolvedSetting(
            key="node.implement.session_mode",
            value="resume",
            source=ConfigSource.GRAPH_DEFAULT,
        ),
    )


def finish_source(store, root, outcome=None):
    """Create the immutable registration and explicit completed-turn fact."""

    activation = store.mint_activation(
        root.root_id, entry_request(crew_profile="codex-appserver", session_id="")
    ).activation
    process = handle(session_id="")
    store.record_dispatch(activation.activation_id, process, launch_id="launch-1")
    registration = SessionRegistration(
        root_id=root.root_id,
        activation_id=activation.activation_id,
        launch_id="launch-1",
        handle=process,
        thread_id="thread-1",
        crew_profile="codex-appserver",
        crew_version=CODEX_VERSION,
        model=activation.metadata.model,
        effort="medium",
        policy_digest="c49fea7425fa7f8699897a97c159c6690267d9003bb78c53fafa8fc15c325d84",
        state_path="/state/node",
    )
    store.register_session(activation.activation_id, registration)
    store.record_session_completion(
        activation.activation_id,
        SessionCompletion(registration=registration, turn_id="turn-1"),
    )
    store.close_activation(activation.activation_id, outcome or Outcome.FAIL_CODE)
    return registration


@pytest.mark.parametrize("mode", ["fresh", "resume"])
def test_reentry_binds_history_only_when_session_mode_opts_in(
    tmp_path, fake_store, mode
):
    """The caller's session string cannot select arbitrary history."""

    root = app_root(tmp_path, fake_store, mode)
    source = finish_source(fake_store, root)
    request = entry_request(
        crew_profile="codex-appserver", session_id="caller-invented"
    ).model_copy(
        update={
            "mint_reason": MintReason.EDGE,
            "predecessor_activation_id": source.activation_id,
        }
    )
    minted = fake_store.mint_activation(root.root_id, request).activation
    if mode == "resume":
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
        ("crew_profile", "other-crew"),
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
    request = entry_request(crew_profile="codex-appserver", session_id="").model_copy(
        update={
            "mint_reason": MintReason.EDGE,
            "predecessor_activation_id": registration.activation_id,
        }
    )
    assert choose_source(root, request, [source]).source is None


def test_newest_eligible_fresh_session_supersedes_older_resumed_history(
    tmp_path, fake_store
):
    """A fresh activation between resumes becomes the next resume source."""
    root = app_root(tmp_path, fake_store, "same-node")
    old_registration = finish_source(fake_store, root)
    old = fake_store.reads.load_activation(old_registration.activation_id)
    fresh_registration = old_registration.model_copy(
        update={"activation_id": "fresh-source", "thread_id": "thread-fresh"}
    )
    assert old.metadata.session_completion is not None
    fresh = old.model_copy(
        update={
            "id": "fresh-source",
            "metadata": old.metadata.model_copy(
                update={
                    "seq": old.metadata.seq + 1,
                    "session_registration": fresh_registration,
                    "session_completion": old.metadata.session_completion.model_copy(
                        update={"registration": fresh_registration}
                    ),
                    "session_source_activation_id": None,
                    "source_session_id": None,
                    "session_reuse_source": None,
                }
            ),
        }
    )
    request = entry_request(crew_profile="codex-appserver").model_copy(
        update={
            "session_mode": SessionMode.RESUME,
            "mint_reason": MintReason.EDGE,
            "predecessor_activation_id": fresh.activation_id,
        }
    )

    choice = choose_source(root, request, [old, fresh])

    assert choice.source == fresh_registration


def test_plain_resume_skips_crashed_and_abandoned_unregistered_sources(
    tmp_path, fake_store
):
    """Only a successful terminal exec turn can supply resume history."""
    root = exec_root(tmp_path, fake_store)
    minted = fake_store.mint_activation(
        root.root_id, entry_request(crew_profile="codex")
    ).activation
    dispatched = fake_store.record_dispatch(
        minted.activation_id, handle(session_id="thread-good")
    )
    good = fake_store.close_activation(dispatched.activation_id, Outcome.FAIL_CODE)
    request = entry_request(crew_profile="codex").model_copy(
        update={
            "session_mode": SessionMode.RESUME,
            "mint_reason": MintReason.EDGE,
            "predecessor_activation_id": "bad-source",
        }
    )

    for offset, outcome in enumerate(
        (Outcome.ERROR_TRANSPORT, Outcome.ABANDON), start=1
    ):
        bad = good.model_copy(
            update={
                "id": "bad-source",
                "metadata": good.metadata.model_copy(
                    update={
                        "seq": good.metadata.seq + offset,
                        "session_id": "thread-bad",
                        "outcome": outcome,
                    }
                ),
            }
        )
        choice = choose_source(root, request, [good, bad])
        assert choice.source_activation_id == good.activation_id
        assert choice.source_session_id == "thread-good"
        assert choose_source(root, request, [bad]).source_activation_id is None


def test_infra_retry_of_deliberate_steer_keeps_its_bound_session(tmp_path, fake_store):
    """Fresh defaults cannot erase §8.1 deliberate continuation after a crash."""

    root = app_root(tmp_path, fake_store, "fresh")
    source = finish_source(fake_store, root, Outcome.STEERED)
    continuation = fake_store.mint_activation(
        root.root_id,
        entry_request(
            crew_profile="codex-appserver", session_id=source.thread_id
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
            crew_profile="codex-appserver", session_id=source.thread_id
        ).model_copy(
            update={
                "mint_reason": MintReason.INFRA_RETRY,
                "predecessor_activation_id": continuation.activation_id,
            }
        ),
    ).activation
    assert retry.metadata.session_reuse_source == source
    assert retry.metadata.session_id == source.thread_id


@pytest.mark.parametrize("reason", [MintReason.EDGE, MintReason.STEER_CONTINUATION])
def test_version_mismatch_is_a_logged_fresh_decision(
    tmp_path, fake_store, capsys, reason
):
    """A CLI bump changes history eligibility, never wedges deliberate continuation."""
    root = app_root(tmp_path, fake_store, "same-node")
    source_outcome = (
        Outcome.STEERED
        if reason is MintReason.STEER_CONTINUATION
        else Outcome.FAIL_CODE
    )
    registration = finish_source(fake_store, root, source_outcome)
    source = fake_store.reads.load_activation(registration.activation_id)
    old = registration.model_copy(update={"crew_version": "0.153.0"})
    source = source.model_copy(
        update={
            "metadata": source.metadata.model_copy(
                update={
                    "session_registration": old,
                    "session_completion": source.metadata.session_completion.model_copy(
                        update={"registration": old}
                    ),
                }
            )
        }
    )
    request = entry_request(crew_profile="codex-appserver").model_copy(
        update={
            "mint_reason": reason,
            "predecessor_activation_id": registration.activation_id,
        }
    )
    assert choose_source(root, request, [source]).source is None
    captured = capsys.readouterr()
    assert "version_mismatch" in captured.out + captured.err


def test_same_node_without_eligible_history_gets_distinct_private_state(tmp_path):
    """A rejected source cannot leave its config or history in a fresh server home."""

    lab = AppServerLab(tmp_path, reuse="same-node")
    first = lab.store.mint_activation(
        lab.root.root_id, entry_mint(crew_profile="codex-appserver", session_id="")
    ).activation
    old = state_for(lab.paths, lab.root, first)
    (old / "prior-state").write_text("must not be reused")
    lab.store.close_activation(first.activation_id, Outcome.ERROR_TRANSPORT)
    second = lab.store.mint_activation(
        lab.root.root_id,
        entry_mint(crew_profile="codex-appserver", session_id="").model_copy(
            update={
                "mint_reason": MintReason.INFRA_RETRY,
                "predecessor_activation_id": first.activation_id,
            }
        ),
    ).activation
    assert second.metadata.session_reuse_source is None
    new = state_for(lab.paths, lab.root, second)
    assert new != old
    assert not (new / "prior-state").exists()


def test_version_bump_deliberate_continuation_can_dispatch_fresh(tmp_path):
    """The logged fresh decision must work at launch, not only at mint."""

    lab = AppServerLab(tmp_path)
    first = lab.run()
    aid = first.dispatch.activation.activation_id
    old = lab.store.reads.load_activation(aid).metadata.session_registration.model_copy(
        update={"crew_version": "0.153.0"}
    )
    lab.store._client._merge_metadata(
        aid,
        {
            "session_registration": old.model_dump(mode="json"),
            "session_completion": None,
        },
    )
    lab.store.close_activation(aid, Outcome.STEERED)
    request = entry_mint(crew_profile="codex-appserver", session_id="").model_copy(
        update={
            "mint_reason": MintReason.STEER_CONTINUATION,
            "predecessor_activation_id": aid,
        }
    )
    write_record(
        lab.paths.steer_intent(aid),
        SteerIntent(
            activation_id=aid,
            reason="version bump",
            instructions="fresh instructions",
            instructions_digest=hashlib.sha256(b"fresh instructions").hexdigest(),
            requested_at="test",
            continuation=request,
        ),
    )
    second = lab.run(request)
    assert second.observation.completion.outcome is Outcome.NO_DIFF
    meta = lab.store.reads.load_activation(
        second.dispatch.activation.activation_id
    ).metadata
    assert meta.session_reuse_source is None
    assert meta.session_registration.state_path != old.state_path
    requests = [
        json.loads(line)
        for line in (
            lab.paths.channels_dir(second.dispatch.activation.activation_id)
            / "artifacts"
            / "requests.jsonl"
        )
        .read_text()
        .splitlines()
    ]
    assert any(item["method"] == "thread/start" for item in requests)
    assert all(item["method"] != "thread/resume" for item in requests)
    turn = next(item for item in requests if item["method"] == "turn/start")
    assert "fresh instructions" in turn["params"]["input"][0]["text"]


def test_non_string_pinned_policy_is_a_carrier_integrity_error(tmp_path, fake_store):
    """Malformed durable policy data cannot become a session compatibility key."""
    root = app_root(tmp_path, fake_store, "same-node")
    broken = root.model_copy(
        update={
            "metadata": root.metadata.model_copy(
                update={
                    "resolved_config": (
                        *root.metadata.resolved_config,
                        ResolvedSetting(
                            key=EXECUTION_POLICY_KEY.format(node="implement"),
                            value=42,
                            source=ConfigSource.PROJECT_CONFIG,
                        ),
                    ),
                }
            )
        }
    )
    with pytest.raises(CarrierIntegrityError, match="session"):
        choose_source(broken, entry_request(crew_profile="codex-appserver"), ())
