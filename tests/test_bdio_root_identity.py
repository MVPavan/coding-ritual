"""§3.1 root identity — creation, reuse by key, and discovery.

An instance IS its root row: reusing a key is an identity claim, checked
against the resolution the key was minted under. Two rows for one key is not
a state the ledger can reach — `roots.instance_key` is UNIQUE and a second
create answers with the row that exists (§3.3) — so what is left to test is
the claim itself and the residue a live instance can still carry.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from tests._bdio import (
    RESOLVED_CONFIG,
    load_definition,
    seed_row,
)
from workflow_interpreter import GraphDefinition
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.carriers import JSON_SAFE_INT_LIMIT
from workflow_interpreter.bdio.errors import CarrierIntegrityError
from workflow_interpreter.bdio.wire import (
    ConfigSource,
    ResolvedSetting,
    WfKind,
)
from workflow_interpreter.ledger.store import LedgerStore


def test_recreating_role_root_after_binding_edit_keeps_static_identity(
    tmp_path,
) -> None:
    """A role edit changes future mints without changing an existing root."""
    from tests._foreman import ForemanLab
    from tests._helpers import SHIPPED_FIXTURE
    from workflow_interpreter.contracts.sessions import SessionMode
    from workflow_interpreter.foreman.config import CrewBinding
    from workflow_interpreter.foreman.resolve import _resolved_config

    lab = ForemanLab(tmp_path, toml=SHIPPED_FIXTURE)
    root = lab.instantiate_resolved()
    edited = dict(lab.config.roles)
    edited["implementer"] = CrewBinding(
        profile="claude",
        model="changed-model",
        effort="high",
        context_cap_tokens=120000,
        session_mode=SessionMode.RESUME,
    )
    composition = replace(
        lab.composition, config=lab.config.model_copy(update={"roles": edited})
    )
    recreated = lab.store.create_root(
        instance_key="foreman-lab",
        definition=root.definition,
        resolved_config=_resolved_config(composition, root.definition, {}),
        instance_inputs=root.metadata.instance_inputs,
        instance_base_commit=root.metadata.instance_base_commit,
        profiles=lab.profiles,
    )
    assert recreated.root_id == root.root_id
    assert all(
        setting.source is not ConfigSource.ROLE_BINDING
        for setting in root.metadata.resolved_config
    )
    assert any(
        setting.key == "node.implement.execution_policy_version" and setting.value == 1
        for setting in root.metadata.resolved_config
    )
    assert all(
        setting.key != "node.implement.execution_policy"
        for setting in root.metadata.resolved_config
    )


def test_historical_role_root_reuses_key_without_losing_stored_bindings(
    tmp_path,
) -> None:
    """Pre-S4 settings remain readable for pre-S3 activation rows."""
    from tests._foreman import ForemanLab
    from workflow_interpreter.foreman.execution import resolved_node
    from workflow_interpreter.foreman.resolve import _resolved_config

    lab = ForemanLab(tmp_path)
    static = _resolved_config(lab.composition, lab.definition, {})
    historical = (
        *static,
        *(
            ResolvedSetting(
                key=f"node.{node}.{field}",
                value=value,
                source=ConfigSource.ROLE_BINDING,
            )
            for node in ("implement", "review")
            for field, value in (
                ("crew", "fake"),
                ("model", "historical-model"),
                ("effort", "medium"),
            )
        ),
    )
    old = lab.store.create_root(
        instance_key="historical",
        definition=lab.definition,
        resolved_config=historical,
        profiles=lab.profiles,
    )
    reopened = lab.store.create_root(
        instance_key="historical",
        definition=lab.definition,
        resolved_config=static,
        profiles=lab.profiles,
    )
    assert reopened.root_id == old.root_id
    assert resolved_node(reopened, "implement").model == "historical-model"


def test_role_model_wins_graph_model_and_historical_root_reuses_key(tmp_path) -> None:
    """Graph model defaults cannot override a role or change reuse identity."""
    from tests._foreman import DEFAULT_LAB_ROLES, ForemanLab
    from tests._helpers import VALID_FIXTURE, mutate, write
    from workflow_interpreter.bdio.wire import NodeSetting
    from workflow_interpreter.foreman.cases import startup_invocation
    from workflow_interpreter.foreman.config import CrewBinding
    from workflow_interpreter.foreman.resolve import _resolved_config

    fixture = write(
        tmp_path,
        mutate(
            VALID_FIXTURE.read_text(encoding="utf-8"),
            [
                (
                    'crew        = "profile:implementer"\nmodel         = "default"',
                    'crew        = "profile:implementer"\nmodel         = "graph-sonnet"',
                )
            ],
        ),
    )
    lab = ForemanLab(
        tmp_path,
        toml=fixture,
        roles={
            **DEFAULT_LAB_ROLES,
            "implementer": CrewBinding(
                profile="fake", model="role-model", effort="high"
            ),
        },
    )
    current = _resolved_config(lab.composition, lab.definition, {})
    model_key = NodeSetting.MODEL.at("implement")
    historical = (
        *(setting for setting in current if setting.key != model_key),
        ResolvedSetting(
            key=model_key, value="old-role-model", source=ConfigSource.ROLE_BINDING
        ),
    )
    old = lab.store.create_root(
        instance_key="graph-model-role",
        definition=lab.definition,
        resolved_config=historical,
        profiles=lab.profiles,
    )
    assert startup_invocation(lab.composition, old, "implement").model == "role-model"
    recreated = lab.store.create_root(
        instance_key="graph-model-role",
        definition=lab.definition,
        resolved_config=current,
        profiles=lab.profiles,
    )
    assert recreated.root_id == old.root_id


@pytest.fixture(scope="session")
def definition() -> GraphDefinition:
    """The §2 canonical fixture, loaded and hashed once."""
    return load_definition()


def _config(*overrides: ResolvedSetting) -> tuple[ResolvedSetting, ...]:
    """Keep identity fixtures executable while varying only their identity fact."""
    replaced = {setting.key for setting in overrides}
    return (
        *(setting for setting in RESOLVED_CONFIG if setting.key not in replaced),
        *overrides,
    )


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
        resolved_config=_config(
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
            resolved_config=_config(
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
    config = _config(
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


def test_a_malformed_sibling_row_blocks_neither_ownership_nor_seq(
    fake_store: WorkflowStore,
    fake_client: LedgerStore,
    definition: GraphDefinition,
) -> None:
    """Residue an instance carries must not wedge convergence or allocation.

    Ownership and `seq` are read from identity and one integer, never from a
    decoded carrier: a row whose activation metadata no longer validates is
    exactly the residue convergence exists to clean up, and a tick that
    refused to allocate a sequence beside it could not even record what it
    found (§3.1, §3.2).
    """
    key = "malformed-sibling"
    root = fake_store.create_root(
        instance_key=key, definition=definition, resolved_config=RESOLVED_CONFIG
    )
    for carried in (7, True, JSON_SAFE_INT_LIMIT + 1):
        seed_row(
            fake_client,
            "wf activation with an unreadable carrier",
            {
                "wf_kind": WfKind.ACTIVATION.value,
                "wf_root_id": root.root_id,
                "seq": carried,
            },
        )

    with pytest.raises(CarrierIntegrityError):
        fake_store.reads.instance_records(root.root_id)
    # A `bool` and an integer past the JSON-safe bound are residue too: neither
    # can be allocated from, so the successor comes from the one valid `seq`.
    assert fake_store.reads.next_instance_seq(root.root_id) == 8

    # The bound itself IS a valid `seq`, and its successor is not: allocation
    # refuses rather than hand out a number no write could carry back.
    seed_row(
        fake_client,
        "wf activation at the JSON-safe bound",
        {
            "wf_kind": WfKind.ACTIVATION.value,
            "wf_root_id": root.root_id,
            "seq": JSON_SAFE_INT_LIMIT,
        },
    )
    with pytest.raises(CarrierIntegrityError, match="seq space is exhausted"):
        fake_store.reads.next_instance_seq(root.root_id)


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
        resolved_config=_config(
            ResolvedSetting(
                key="identity.type-probe", value=1, source=ConfigSource.GRAPH_DEFAULT
            ),
        ),
    )
    for stringified in ("1", "True"):
        with pytest.raises(CarrierIntegrityError, match="resolved_config"):
            fake_store.create_root(
                instance_key=key,
                definition=definition,
                resolved_config=_config(
                    ResolvedSetting(
                        key="identity.type-probe",
                        value=stringified,
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
    model = ResolvedSetting(
        key="node.implement.model",
        value="pinned-model",
        source=ConfigSource.INSTANCE_OVERRIDE,
    )
    fake_store.create_root(
        instance_key=key, definition=definition, resolved_config=_config(model)
    )
    with pytest.raises(CarrierIntegrityError, match="node.implement.model") as excinfo:
        fake_store.create_root(
            instance_key=key,
            definition=definition,
            resolved_config=_config(model.model_copy(update={"value": "other"})),
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


def test_the_sealed_boundary_exports_every_name_a_caller_must_build(
    fake_store: WorkflowStore,
) -> None:
    # The store is constructed from a `LedgerStore` now (R1), so what the
    # boundary owes callers is the vocabulary, not a factory.
    import workflow_interpreter.bdio as package

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
