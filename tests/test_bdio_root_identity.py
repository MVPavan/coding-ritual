"""§3.1 root identity — creation, reuse by key, convergence and discovery.

An instance IS its root bead: reusing a key is an identity claim, and two
roots for one key is race residue that has to converge without orphaning the
trace. Driven through the in-memory bd, whose scheduling hooks make the
concurrent creates deterministic.
"""

from __future__ import annotations

from typing import Final

import pytest

from tests._bdio import (
    RESOLVED_CONFIG,
    entry_request,
    load_definition,
)
from tests._fake_bd import FakeBd
from workflow_interpreter import GraphDefinition
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.errors import CarrierIntegrityError
from workflow_interpreter.bdio.wire import (
    ConfigSource,
    ResolvedSetting,
    WfKind,
    metadata_dict,
)

STATUS_CLOSED: Final[str] = "closed"
STATUS_OPEN: Final[str] = "open"
LOW_BEAD_ID: Final[str] = "wf-000"
"""A bead id below every id FakeBd hands out — real bd ids are not ordered by
creation time (probed), and this is how that looks deterministically."""


@pytest.fixture(scope="session")
def definition() -> GraphDefinition:
    """The §2 canonical fixture, loaded and hashed once."""
    return load_definition()


# --- root identity (§3.1) -----------------------------------------------


def test_an_instance_without_a_resolved_configuration_is_refused(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    with pytest.raises(CarrierIntegrityError, match="no resolved configuration"):
        fake_store.create_root(
            instance_key="empty", definition=definition, resolved_config=()
        )


def test_reusing_a_key_with_a_different_resolution_is_refused(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # Reuse is an identity claim: silently aliasing a different resolution
    # onto an existing instance would run it under bounds nobody resolved.
    key = "shared-key"
    fake_store.create_root(
        instance_key=key,
        definition=definition,
        resolved_config=(
            ResolvedSetting(
                key="instance.max_total_activations",
                value=20,
                source=ConfigSource.GRAPH_DEFAULT,
            ),
        ),
    )
    with pytest.raises(CarrierIntegrityError, match="resolved_config"):
        fake_store.create_root(
            instance_key=key,
            definition=definition,
            resolved_config=(
                ResolvedSetting(
                    key="instance.max_total_activations",
                    value=99,
                    source=ConfigSource.INSTANCE_OVERRIDE,
                ),
            ),
        )


def test_reusing_a_key_with_the_same_resolution_is_idempotent(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    config = (
        ResolvedSetting(
            key="instance.max_total_activations",
            value=20,
            source=ConfigSource.GRAPH_DEFAULT,
        ),
    )
    first = fake_store.create_root(
        instance_key="stable", definition=definition, resolved_config=config
    )
    second = fake_store.create_root(
        instance_key="stable", definition=definition, resolved_config=config
    )
    assert first.root_id == second.root_id


def test_concurrent_duplicate_roots_converge_on_the_lowest_bead_id(
    fake_store: WorkflowStore,
    fake_client: BdClient,
    fake_bd: FakeBd,
    definition: GraphDefinition,
) -> None:
    # Same convergence rule as §3.2 race residue: append-only, lowest id wins,
    # the loser is superseded rather than deleted.
    key = "raced"

    def interleave() -> None:
        fake_store.create_root(
            instance_key=key,
            definition=definition,
            resolved_config=(
                ResolvedSetting(
                    key="instance.max_total_activations",
                    value=20,
                    source=ConfigSource.GRAPH_DEFAULT,
                ),
            ),
        )

    fake_bd.pause_before("create", interleave)
    second = fake_store.create_root(
        instance_key=key,
        definition=definition,
        resolved_config=(
            ResolvedSetting(
                key="instance.max_total_activations",
                value=20,
                source=ConfigSource.GRAPH_DEFAULT,
            ),
        ),
    )
    roots = [
        row
        for row in fake_bd.rows.values()
        if row["metadata"].get("instance_key") == key
    ]
    assert len(roots) == 2
    live = [row for row in roots if row["metadata"].get("superseded_by") is None]
    assert [row["id"] for row in live] == [second.root_id]
    assert second.root_id == min(row["id"] for row in roots)
    losers = [row for row in roots if row["id"] != second.root_id]
    assert losers[0]["status"] == STATUS_CLOSED
    assert losers[0]["metadata"]["superseded_by"] == second.root_id


def test_a_concurrent_create_that_converges_on_another_resolution_is_refused(
    fake_store: WorkflowStore, fake_bd: FakeBd, definition: GraphDefinition
) -> None:
    # Convergence used to skip the identity check that reuse-by-key runs, so
    # the caller whose root lost the race silently inherited an instance
    # configured with a ceiling it never resolved (probed, round-2 review).
    key = "raced-mismatch"

    def interleave() -> None:
        fake_store.create_root(
            instance_key=key,
            definition=definition,
            resolved_config=(
                ResolvedSetting(
                    key="instance.max_total_activations",
                    value=20,
                    source=ConfigSource.GRAPH_DEFAULT,
                ),
            ),
        )

    fake_bd.pause_before("create", interleave)
    with pytest.raises(CarrierIntegrityError, match="resolved_config"):
        fake_store.create_root(
            instance_key=key,
            definition=definition,
            resolved_config=(
                ResolvedSetting(
                    key="instance.max_total_activations",
                    value=99,
                    source=ConfigSource.INSTANCE_OVERRIDE,
                ),
            ),
        )
    live = [
        row
        for row in fake_bd.rows.values()
        if row["metadata"].get("instance_key") == key
        and row["metadata"].get("superseded_by") is None
    ]
    assert [row["metadata"]["resolved_config"][0]["value"] for row in live] == [20]


def test_convergence_never_supersedes_the_root_that_owns_the_instance(
    fake_store: WorkflowStore,
    fake_client: BdClient,
    fake_bd: FakeBd,
    definition: GraphDefinition,
) -> None:
    # bd 1.1.0 hands out ids that are NOT ordered by creation (`wf-yd1` before
    # `wf-c7b`; probed live, round 3), so "lowest id survives" said nothing
    # about which root the instance actually ran on: a later duplicate could
    # win and close the root owning every activation and gate.
    key = "owner-vs-id"
    root = fake_store.create_root(
        instance_key=key, definition=definition, resolved_config=RESOLVED_CONFIG
    )
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    duplicate = fake_client._create_bead(
        title="wf root duplicate",
        metadata=metadata_dict(root.metadata.model_copy(update={"wf_root_id": None})),
    )
    # Give the duplicate a LOWER id than the populated root, which is exactly
    # what unordered bd ids produce half the time.
    row = fake_bd.rows.pop(duplicate.id)
    row["id"] = LOW_BEAD_ID
    fake_bd.rows[LOW_BEAD_ID] = row

    converged = fake_store.create_root(
        instance_key=key, definition=definition, resolved_config=RESOLVED_CONFIG
    )

    assert converged.root_id == root.root_id
    assert fake_client.show(root.root_id).status == STATUS_OPEN
    assert fake_bd.rows[LOW_BEAD_ID]["metadata"]["superseded_by"] == root.root_id
    assert activation.activation_id in {
        record.activation_id
        for record in fake_store.reads.list_activations(converged.root_id)
    }


def test_two_roots_that_both_own_beads_refuse_to_converge(
    fake_store: WorkflowStore,
    fake_client: BdClient,
    definition: GraphDefinition,
) -> None:
    # Converging would orphan one running instance's trace. There is no safe
    # automatic answer, so it fails toward triage (§3.1).
    key = "both-own"
    root = fake_store.create_root(
        instance_key=key, definition=definition, resolved_config=RESOLVED_CONFIG
    )
    fake_store.mint_activation(root.root_id, entry_request())
    duplicate = fake_client._create_bead(
        title="wf root duplicate",
        metadata=metadata_dict(root.metadata.model_copy(update={"wf_root_id": None})),
    )
    fake_client._merge_metadata(duplicate.id, {"wf_root_id": duplicate.id})
    fake_client._create_bead(
        title="wf event under the duplicate",
        metadata={
            "wf_kind": WfKind.EVENT.value,
            "wf_root_id": duplicate.id,
            "event_key": "k",
            "seq": 1,
        },
    )

    with pytest.raises(CarrierIntegrityError, match="more than one live root"):
        fake_store.create_root(
            instance_key=key, definition=definition, resolved_config=RESOLVED_CONFIG
        )


def test_a_configuration_identity_distinguishes_value_types(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # The signature stringified values, so the integer 1 and the string "1"
    # (and True and "True") were the same instance: a re-tick under a
    # differently TYPED resolution silently reused a root configured
    # otherwise (probed live, round 3).
    key = "typed-config"
    fake_store.create_root(
        instance_key=key,
        definition=definition,
        resolved_config=(
            ResolvedSetting(
                key="instance.max_total_activations",
                value=20,
                source=ConfigSource.GRAPH_DEFAULT,
            ),
            ResolvedSetting(
                key="node.implement.model", value=1, source=ConfigSource.GRAPH_DEFAULT
            ),
            ResolvedSetting(
                key="node.implement.isolation",
                value=True,
                source=ConfigSource.GRAPH_DEFAULT,
            ),
        ),
    )
    for typed, stringified in (("model", "1"), ("isolation", "True")):
        with pytest.raises(CarrierIntegrityError, match="resolved_config"):
            fake_store.create_root(
                instance_key=key,
                definition=definition,
                resolved_config=(
                    ResolvedSetting(
                        key="instance.max_total_activations",
                        value=20,
                        source=ConfigSource.GRAPH_DEFAULT,
                    ),
                    ResolvedSetting(
                        key="node.implement.model",
                        value=stringified if typed == "model" else 1,
                        source=ConfigSource.GRAPH_DEFAULT,
                    ),
                    ResolvedSetting(
                        key="node.implement.isolation",
                        value=stringified if typed == "isolation" else True,
                        source=ConfigSource.GRAPH_DEFAULT,
                    ),
                ),
            )


def test_a_configuration_mismatch_names_the_differing_keys(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # Two sha256 digests are unactionable; the whole resolution is unbounded.
    # The differing KEYS are both.
    key = "named-diff"
    fake_store.create_root(
        instance_key=key, definition=definition, resolved_config=RESOLVED_CONFIG
    )
    with pytest.raises(CarrierIntegrityError, match="node.implement.model") as excinfo:
        fake_store.create_root(
            instance_key=key,
            definition=definition,
            resolved_config=tuple(
                setting
                if setting.key != "node.implement.model"
                else setting.model_copy(update={"value": "other"})
                for setting in RESOLVED_CONFIG
            ),
        )
    assert "differing keys" in str(excinfo.value)


# --- the §4 read surface a stateless tick needs --------------------------


def test_roots_can_be_discovered_without_reaching_into_the_package(
    fake_store: WorkflowStore, definition: GraphDefinition
) -> None:
    # A stateless tick has to find its instances before it can load one; the
    # §4 read facade carried no root enumeration at all (probed, round 3).
    first = fake_store.create_root(
        instance_key="discover-a",
        definition=definition,
        resolved_config=RESOLVED_CONFIG,
    )
    second = fake_store.create_root(
        instance_key="discover-b",
        definition=definition,
        resolved_config=RESOLVED_CONFIG,
    )

    found = fake_store.reads.list_roots()

    assert [record.root_id for record in found] == sorted(
        {first.root_id, second.root_id}
    )


def test_a_store_can_be_built_from_configuration_alone(
    fake_store: WorkflowStore,
) -> None:
    # `BdClient` stays unexported (§0.1), so without a factory the sealed
    # boundary was also an unbuildable one (probed, round 3).
    import workflow_interpreter.bdio as package

    assert "BdClient" not in package.__all__
    assert hasattr(package.WorkflowStore, "from_config")
    for name in (
        "MintRequest",
        "GateOpenRequest",
        "EventPayload",
        "ResolvedSetting",
        "ProcessHandle",
        "ExitRecord",
        "Evidence",
        "Usage",
        "Deviation",
        "InputBinding",
        "VerifyOutcome",
        "ArtifactIdentity",
        # `Evidence` carries a `Breaker`, so a caller that can build one has to
        # be able to name one: reaching into `bdio.wire` for it (two imports
        # did) is a hole in the sealed boundary, not a workaround for it.
        "Breaker",
        "BoundSetting",
        "ConfigSource",
        "MintReason",
        "GateReason",
        "Lifecycle",
        "GateState",
        "Outcome",
    ):
        assert name in package.__all__, name
        assert hasattr(package, name), name
