"""Phase-5 root carrier seam coverage."""

from __future__ import annotations

from hashlib import sha256

import pytest

from tests._bdio import RESOLVED_CONFIG, instance_key, load_definition
from tests._fake_bd import FakeBd
from tests._helpers import INVALID_FIXTURES
from workflow_interpreter import load_graph
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.errors import (
    CarrierIntegrityError,
    PinnedGraphMismatchError,
)
from workflow_interpreter.bdio.roots import MAX_INSTANCE_INPUT_BYTES
from workflow_interpreter.bdio.wire import ConfigSource, InstanceInput, ResolvedSetting
from workflow_interpreter.schema.models import NodeKind


def test_instance_input_cap_is_enforced_at_root_creation(
    fake_store: WorkflowStore,
) -> None:
    """Catch a cap constant surviving while its create-root enforcement is removed."""
    with pytest.raises(CarrierIntegrityError, match="instance inputs exceed"):
        fake_store.create_root(
            instance_key=instance_key(),
            definition=load_definition(),
            resolved_config=RESOLVED_CONFIG,
            instance_inputs=(
                InstanceInput(
                    name="brief",
                    sha256=sha256(
                        ("x" * (MAX_INSTANCE_INPUT_BYTES + 1)).encode("utf-8")
                    ).hexdigest(),
                    body="x" * (MAX_INSTANCE_INPUT_BYTES + 1),
                ),
            ),
        )


def test_config_signature_is_written_and_reverified(
    fake_store: WorkflowStore,
) -> None:
    """Catch either P3 write-side pinning or parse-time signature verification."""
    root = fake_store.create_root(
        instance_key=instance_key(),
        definition=load_definition(),
        resolved_config=RESOLVED_CONFIG,
    )
    assert root.metadata.config_signature is not None
    fake_store._client._merge_metadata(root.root_id, {"config_signature": "wrong"})
    with pytest.raises(PinnedGraphMismatchError, match="config signature mismatch"):
        fake_store.reads.load_root(root.root_id)


def test_root_reuse_compares_new_instance_identity_fields(
    fake_store: WorkflowStore,
) -> None:
    """Catch P2, P8, or P11 being dropped from root reuse identity checks."""
    key = instance_key()
    definition = load_definition()
    input_body = "brief"
    inputs = (
        InstanceInput(
            name="brief",
            sha256=sha256(input_body.encode("utf-8")).hexdigest(),
            body=input_body,
        ),
    )
    fake_store.create_root(
        instance_key=key,
        definition=definition,
        resolved_config=RESOLVED_CONFIG,
        instance_inputs=inputs,
        allow_test_flags=True,
        instance_base_commit="a" * 40,
    )
    requests = (
        {"instance_inputs": ()},
        {"allow_test_flags": False},
        {"instance_base_commit": "b" * 40},
    )
    for overrides in requests:
        with pytest.raises(CarrierIntegrityError, match="already pins"):
            values: dict[str, object] = {
                "instance_key": key,
                "definition": definition,
                "resolved_config": RESOLVED_CONFIG,
                "instance_inputs": inputs,
                "allow_test_flags": True,
                "instance_base_commit": "a" * 40,
            }
            fake_store.create_root(**(values | overrides))


def test_test_flag_opt_in_reaches_both_root_read_paths(
    fake_store: WorkflowStore,
) -> None:
    """Catch either build-index or pinned-body parse reverting to hard-coded false."""
    flagged = next(
        path
        for path in INVALID_FIXTURES
        if path.name == "test_flags_require_opt_in.toml"
    )
    definition = load_graph(flagged, allow_test_flags=True)
    root = fake_store.create_root(
        instance_key=instance_key(),
        definition=definition,
        resolved_config=(
            *RESOLVED_CONFIG,
            ResolvedSetting(
                key="node.work.model",
                value="fake-model",
                source=ConfigSource.GRAPH_DEFAULT,
            ),
            ResolvedSetting(
                key="node.work.runner",
                value="fake",
                source=ConfigSource.ROLE_BINDING,
            ),
            ResolvedSetting(
                key="node.work.effort",
                value="medium",
                source=ConfigSource.ROLE_BINDING,
            ),
        ),
        allow_test_flags=True,
    )
    assert root.index.allow_test_flags is True
    assert fake_store.reads.load_root(root.root_id).index.allow_test_flags is True

    fake_store._client._merge_metadata(root.root_id, {"allow_test_flags": False})
    with pytest.raises(PinnedGraphMismatchError):
        fake_store.reads.load_root(root.root_id)


def test_create_root_refuses_a_task_node_without_instructions(
    fake_store: WorkflowStore,
) -> None:
    """ADR 0002: `create_root` is the chokepoint, so it owns the requirement.

    Enforcing anywhere else is bypassable — `tests/_bdio.py`,
    `tests/_foreman.py` and `tests/_supervisor.py` all call `create_root`
    directly, and there is no link step in the CLI.
    """
    definition = load_definition()
    stripped = definition.document.model_copy(
        update={
            "node": tuple(
                node.model_copy(update={"instructions": None})
                if node.kind is NodeKind.TASK
                else node
                for node in definition.document.node
            )
        }
    )

    with pytest.raises(CarrierIntegrityError, match="instructions"):
        fake_store.create_root(
            instance_key=instance_key(),
            definition=definition.model_copy(update={"document": stripped}),
            resolved_config=RESOLVED_CONFIG,
        )


def test_create_root_refuses_whitespace_only_instructions(
    fake_store: WorkflowStore,
) -> None:
    """Presence is not enough: blank text would satisfy a naive check."""
    definition = load_definition()
    blanked = definition.document.model_copy(
        update={
            "node": tuple(
                node.model_copy(update={"instructions": "   \n\t "})
                if node.kind is NodeKind.TASK
                else node
                for node in definition.document.node
            )
        }
    )

    with pytest.raises(CarrierIntegrityError, match="instructions"):
        fake_store.create_root(
            instance_key=instance_key(),
            definition=definition.model_copy(update={"document": blanked}),
            resolved_config=RESOLVED_CONFIG,
        )


def test_create_root_refuses_a_task_without_a_model_pin(
    fake_store: WorkflowStore,
) -> None:
    """A programmatic non-role runner needs its model pinned before creation."""
    definition = load_definition()
    unpinned = definition.document.model_copy(
        update={
            "node": tuple(
                node.model_copy(update={"runner": "claude", "model": None})
                if node.name == "implement"
                else node
                for node in definition.document.node
            )
        }
    )
    config = tuple(
        setting for setting in RESOLVED_CONFIG if setting.key != "node.implement.model"
    )

    with pytest.raises(CarrierIntegrityError, match="model"):
        fake_store.create_root(
            instance_key=instance_key(),
            definition=definition.model_copy(update={"document": unpinned}),
            resolved_config=config,
        )


def test_create_root_refuses_a_literal_runner_without_a_runner_pin(
    fake_bd: FakeBd, fake_store: WorkflowStore
) -> None:
    """A literal runner still needs the mint-time runner pin before root creation."""
    definition = load_definition()
    literal_runner = definition.document.model_copy(
        update={
            "node": tuple(
                node.model_copy(update={"runner": "claude", "model": "fake-model"})
                if node.name == "implement"
                else node
                for node in definition.document.node
            )
        }
    )
    config = tuple(
        setting for setting in RESOLVED_CONFIG if setting.key != "node.implement.runner"
    )

    with pytest.raises(CarrierIntegrityError, match="runner"):
        fake_store.create_root(
            instance_key=instance_key(),
            definition=definition.model_copy(update={"document": literal_runner}),
            resolved_config=config,
        )

    assert fake_bd.command_count("create") == 0


def test_create_root_refuses_a_role_bound_task_without_an_effort_pin(
    fake_bd: FakeBd, fake_store: WorkflowStore
) -> None:
    """A role-bound task must pin the effort supplied to its TaskSpec."""
    config = tuple(
        setting for setting in RESOLVED_CONFIG if setting.key != "node.implement.effort"
    )

    with pytest.raises(CarrierIntegrityError, match="effort"):
        fake_store.create_root(
            instance_key=instance_key(),
            definition=load_definition(),
            resolved_config=config,
        )

    assert fake_bd.command_count("create") == 0


def test_create_root_does_not_require_instructions_on_gates_or_terminals(
    fake_store: WorkflowStore,
) -> None:
    """Only a task dispatches a runner; a gate or terminal has no job to state."""
    definition = load_definition()
    assert any(node.kind is not NodeKind.TASK for node in definition.document.node), (
        "fixture must carry a non-task node for this test to mean anything"
    )

    root = fake_store.create_root(
        instance_key=instance_key(),
        definition=definition,
        resolved_config=RESOLVED_CONFIG,
    )

    assert root.root_id
