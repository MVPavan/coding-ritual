"""Phase-5 root carrier seam coverage."""

from __future__ import annotations

from hashlib import sha256

import pytest

from tests._bdio import RESOLVED_CONFIG, instance_key, load_definition
from tests._helpers import INVALID_FIXTURES
from workflow_interpreter import load_graph
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.errors import (
    CarrierIntegrityError,
    PinnedGraphMismatchError,
)
from workflow_interpreter.bdio.roots import MAX_INSTANCE_INPUT_BYTES
from workflow_interpreter.bdio.wire import InstanceInput


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
        resolved_config=RESOLVED_CONFIG,
        allow_test_flags=True,
    )
    assert root.index.allow_test_flags is True
    assert fake_store.reads.load_root(root.root_id).index.allow_test_flags is True

    fake_store._client._merge_metadata(root.root_id, {"allow_test_flags": False})
    with pytest.raises(PinnedGraphMismatchError):
        fake_store.reads.load_root(root.root_id)
