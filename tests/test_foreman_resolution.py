"""Pure contracts for composition, resolution, and root instantiation."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Final, cast

import pytest
from pydantic import ValidationError
from structlog.testing import capture_logs

from tests._bdio import (
    IMPLEMENT,
    entry_request,
    instance_key,
    load_definition,
    make_root,
)
from tests._fake_bd import FakeBd
from tests._foreman import (
    BUILD_LOOP_INSTANCE_INPUTS,
    BUILD_LOOP_ROLES,
    FAKE_PROFILE,
    ForemanLab,
)
from tests._helpers import BUILD_LOOP_GRAPH, VALID_FIXTURE
from workflow_interpreter.bdio import BdConfig, BoundSetting, NodeSetting
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.errors import BdConfigError
from workflow_interpreter.bdio.roots import MAX_INSTANCE_INPUT_BYTES
from workflow_interpreter.foreman.compose import (
    Composition,
    DetachedSpawner,
    InstanceBranchMissing,
    ProfileResolver,
    Spawner,
    WrapperLaunch,
    instance_head,
)
from workflow_interpreter.foreman.config import ForemanConfig, RunnerBinding
from workflow_interpreter.foreman.constants import INSTANCE_BRANCH
from workflow_interpreter.foreman.errors import ResolutionError
from workflow_interpreter.foreman.execution import (
    UnresolvedRunnerError,
    resolved_node,
)
from workflow_interpreter.foreman.owner import OwnerConflict, OwnerRecord, ensure_owner
from workflow_interpreter.foreman.resolve import (
    TASK_SETTING_TYPES,
    _resolved_config,
    instantiate,
    resolve,
)
from workflow_interpreter.schema.loader import load_graph
from workflow_interpreter.schema.models import IsolationMode
from workflow_interpreter.schema.validator import PHASE_B_RULES
from workflow_interpreter.supervisor.clock import Clock
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.gitio import Git
from workflow_interpreter.supervisor.paths import read_record, write_record


class _AvailableProfiles:
    """A resolver double for pure resolution tests."""


def test_runner_binding_requires_a_pinned_model_and_effort(tmp_path: Path) -> None:
    """A role cannot leave either output-affecting setting to a vendor default."""
    repo = tmp_path / "repo"
    repo.mkdir()
    wrapper_home = tmp_path / "home"
    wrapper_root = (
        wrapper_home
        / hashlib.sha256(str(repo.resolve()).encode("utf-8")).hexdigest()[:16]
    )

    def config(binding: dict[str, str]) -> ForemanConfig:
        return ForemanConfig.model_validate(
            {
                "repo_root": repo,
                "wrapper_home": wrapper_home,
                "bd": {"workspace": tmp_path / "bd", "actor": "actor"},
                "host": "host",
                "actor": "actor",
                "supervisor": {
                    "repo_root": repo,
                    "wrapper_root": wrapper_root,
                    "host": "host",
                },
                "roles": {"implementer": binding},
            }
        )

    with pytest.raises(ValidationError, match="roles.implementer.model"):
        config({"profile": "claude", "effort": "high"})
    with pytest.raises(ValidationError, match="roles.implementer.effort"):
        config({"profile": "claude", "model": "claude-opus-4-1"})
    with pytest.raises(ValidationError, match="roles.implementer.model"):
        config({"profile": "claude", "model": "", "effort": "high"})
    with pytest.raises(ValidationError, match="roles.implementer.effort"):
        config({"profile": "claude", "model": "claude-opus-4-1", "effort": ""})
    with pytest.raises(ValidationError, match="implementer"):
        config({"profile": "claude", "model": "default", "effort": "high"})


def test_instance_head_refuses_a_missing_instance_branch(tmp_path: Path) -> None:
    """Composition's mint-base reader cannot silently use an absent ref."""

    class MissingGit:
        def ref_target(self, ref: str, *, cwd: Path) -> str | None:
            return None

    with pytest.raises(InstanceBranchMissing, match="instance branch"):
        instance_head(cast(Git, MissingGit()), tmp_path, "root")


def test_composition_for_root_shares_one_band_and_installs_head_reader(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """The per-root wiring owns one band and a root-scoped mint-base reader."""
    repo = tmp_path / "repo"
    repo.mkdir()
    wrapper_root = (
        tmp_path
        / "home"
        / hashlib.sha256(str(repo.resolve()).encode("utf-8")).hexdigest()[:16]
    )
    config = ForemanConfig(
        repo_root=repo,
        wrapper_home=tmp_path / "home",
        bd=BdConfig(workspace=tmp_path / "bd", actor="actor"),
        host="host",
        actor="actor",
        supervisor=SupervisorConfig(
            repo_root=repo, wrapper_root=wrapper_root, host="host"
        ),
    )

    class Heads:
        def ref_target(self, ref: str, *, cwd: Path) -> str | None:
            return {"refs/heads/wf/a": "a" * 40, "refs/heads/wf/b": "b" * 40}.get(ref)

    composition = Composition(
        config=config,
        store=fake_store,
        supervisor_config=config.supervisor,
        git=cast(Git, Heads()),
        clock=cast(Clock, object()),
        profiles=cast(ProfileResolver, _AvailableProfiles()),
        spawner=cast(Spawner, object()),
    )
    wiring_a = composition.for_root("a")
    wiring_b = composition.for_root("b")
    assert wiring_a.paths.root_id == "a"
    assert wiring_a.band._path == wiring_a.paths.band_lock
    assert wiring_a.band is wiring_a.workspace._band
    assert wiring_a.workspace._advance_branch is True
    assert wiring_a.branch_head_reader() == "a" * 40
    assert wiring_b.branch_head_reader() == "b" * 40


def test_composition_scopes_mint_reads_to_each_instance_branch(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """An A wiring keeps its own branch reader after B has been wired."""
    root = make_root(fake_store, load_definition())
    missing = make_root(fake_store, load_definition())
    composition, git = _instance_composition(fake_store, tmp_path)
    git.refs[INSTANCE_BRANCH.format(root_id=root.root_id)] = "a" * 40
    wiring_a = composition.for_root(root.root_id)
    composition.for_root("b")
    assert wiring_a.branch_head_reader() == "a" * 40
    wiring_missing = composition.for_root(missing.root_id)
    with pytest.raises(InstanceBranchMissing, match="instance branch"):
        wiring_missing.branch_head_reader()


def test_store_root_derivation_keeps_injected_capabilities(
    gate_store: WorkflowStore,
) -> None:
    """A root reader supplements the injected store; it never replaces it."""
    reader = lambda: "a" * 40
    derived = gate_store.for_root(branch_head_reader=reader)
    assert derived._client is gate_store._client
    assert derived._verifier is gate_store._verifier
    assert derived._artifact_reader is gate_store._artifact_reader
    assert derived._branch_head_reader is reader


def test_composition_for_root_uses_the_injected_store(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """A missing branch reader fails through the same injected minting store."""
    root = make_root(fake_store, load_definition())
    composition, _ = _instance_composition(fake_store, tmp_path)
    wiring = composition.for_root(root.root_id)
    fake_store._branch_head_reader = None
    with pytest.raises(BdConfigError, match="no branch_head_reader"):
        fake_store.mint_activation(root.root_id, entry_request())
    with pytest.raises(InstanceBranchMissing, match="instance branch"):
        wiring.supervisor._store.mint_activation(root.root_id, entry_request())


def test_task_setting_types_tracks_the_configurable_task_setting_vocabulary() -> None:
    """A renamed setting cannot leave resolution writing a key nothing reads."""
    assert set(TASK_SETTING_TYPES) == {
        *NodeSetting,
        BoundSetting.MAX_INFRA_RETRIES,
        BoundSetting.MAX_STEERS,
    }


def test_resolve_tags_defaults_and_explicit_overrides() -> None:
    """Root config records the source of each setting rather than flattening it."""
    definition = load_definition()
    settings = {
        item.key: item
        for item in resolve(definition, {}, {"node.implement.model": "chosen"})
    }
    assert settings["instance.max_total_activations"].source.value == "graph-default"
    assert settings["node.implement.model"].value == "chosen"
    assert settings["node.implement.model"].source.value == "instance-override"


def test_role_bindings_fill_only_unresolved_settings_with_their_own_source(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """A role binding cannot erase an operator's immutable root override."""
    composition, _ = _instance_composition(fake_store, tmp_path)
    settings = {
        item.key: item
        for item in _resolved_config(
            composition,
            load_definition(),
            {
                "node.implement.model": "opus-5",
                "node.implement.runner": "operator-runner",
                "node.implement.effort": "high",
            },
        )
    }
    assert settings["node.implement.model"].value == "opus-5"
    assert settings["node.implement.model"].source.value == "instance-override"
    assert settings["node.implement.runner"].value == "operator-runner"
    assert settings["node.implement.runner"].source.value == "instance-override"
    assert settings["node.implement.effort"].value == "high"
    assert settings["node.implement.effort"].source.value == "instance-override"

    bound_composition, _ = _instance_composition(
        fake_store,
        tmp_path / "bound",
        roles={
            "implementer": RunnerBinding(
                profile="bound-runner", model="bound-model", effort="high"
            ),
            "critic": RunnerBinding(profile="critic", model="critic", effort="medium"),
        },
    )
    bound_settings = {
        item.key: item
        for item in _resolved_config(bound_composition, load_definition(), {})
    }
    assert bound_settings["node.implement.runner"].value == "bound-runner"
    assert bound_settings["node.implement.runner"].source.value == "role-binding"
    assert bound_settings["node.implement.model"].value == "bound-model"
    assert bound_settings["node.implement.model"].source.value == "role-binding"
    assert bound_settings["node.implement.effort"].value == "high"
    assert bound_settings["node.implement.effort"].source.value == "role-binding"

    project_composition, _ = _instance_composition(
        fake_store,
        tmp_path / "project",
        project_config={
            "node.implement.model": "project-model",
            "node.implement.effort": "project-effort",
        },
    )
    project_settings = {
        item.key: item
        for item in _resolved_config(project_composition, load_definition(), {})
    }
    assert project_settings["node.implement.model"].value == "project-model"
    assert project_settings["node.implement.model"].source.value == "project-config"
    assert project_settings["node.implement.effort"].value == "project-effort"
    assert project_settings["node.implement.effort"].source.value == "project-config"


def test_resolve_refuses_an_unknown_override() -> None:
    """An instance cannot pin a configuration key its graph never declared."""
    with pytest.raises(ResolutionError, match="unknown override"):
        resolve(load_definition(), {}, {"node.unknown.model": "chosen"})


def test_resolve_accepts_schema_known_unset_values_and_validates_their_type() -> None:
    """An omitted graph field is still a legal typed instance override.

    The key must be one the node's KIND can carry: this asserted
    `node.ship.model` until spec §14 closed the vocabulary, and `ship` is a
    gate, which `node_fields_match_kind` forbids `model` on.
    """
    definition = load_definition()
    settings = {
        setting.key: setting
        for setting in resolve(definition, {}, {"node.review.isolation": "in-repo"})
    }
    assert settings["node.review.isolation"].value == "in-repo"
    with pytest.raises(ResolutionError, match="unsupported value"):
        resolve(definition, {}, {"instance.max_total_activations": "unlimited"})


def test_resolve_supports_explicit_task_settings() -> None:
    """`max_wall=20m` keeps the 10m verifier valid while scalars resolve."""
    settings = {
        item.key: item
        for item in resolve(
            load_definition(),
            {},
            {
                "node.implement.token_budget": 42,
                "node.implement.max_wall": "20m",
                "node.implement.stale_after": "1m",
                "node.implement.writes": True,
                "node.implement.isolation": "in-repo",
            },
        )
    }
    assert {
        key: settings[key].value
        for key in (
            "node.implement.token_budget",
            "node.implement.max_wall",
            "node.implement.stale_after",
            "node.implement.writes",
            "node.implement.isolation",
        )
    } == {
        "node.implement.token_budget": 42,
        "node.implement.max_wall": "20m",
        "node.implement.stale_after": "1m",
        "node.implement.writes": True,
        "node.implement.isolation": "in-repo",
    }


def test_resolve_records_project_region_bounds_and_rejects_unknown_keys() -> None:
    """Project config is provenance-bearing and cannot introduce new settings."""
    definition = load_definition()
    settings = {
        item.key: item
        for item in resolve(definition, {"region.build-review.max_entries": 2}, {})
    }
    assert settings["region.build-review.max_entries"].value == 2
    assert settings["region.build-review.max_entries"].source.value == "project-config"
    with pytest.raises(ResolutionError, match="unknown project"):
        resolve(definition, {"project.unrecognized": True}, {})


class _InstanceGit:
    """Minimal local git double for root creation and branch pinning."""

    def __init__(self) -> None:
        self.base = "a" * 40
        self.refs: dict[str, str] = {}
        self.updated: list[tuple[str, str]] = []
        self.commit_calls: list[str | None] = []
        self.base_exists = True

    def head_commit(self, *, cwd: Path) -> str:
        return self.base

    def commit_exists(self, commit: str, *, cwd: Path) -> bool:
        self.commit_calls.append(commit)
        return self.base_exists and commit == self.base

    def ref_target(self, ref: str, *, cwd: Path) -> str | None:
        return self.refs.get(ref)

    def update_ref(self, ref: str, commit: str, *, cwd: Path) -> None:
        self.refs[ref] = commit
        self.updated.append((ref, commit))


def _instance_composition(
    fake_store: WorkflowStore,
    tmp_path: Path,
    *,
    project_config: dict[str, str | int | bool] | None = None,
    roles: dict[str, RunnerBinding] | None = None,
    profiles: ProfileResolver | None = None,
) -> tuple[Composition, _InstanceGit]:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    wrapper_root = (
        tmp_path
        / "home"
        / hashlib.sha256(str(repo.resolve()).encode("utf-8")).hexdigest()[:16]
    )
    git = _InstanceGit()
    config = ForemanConfig(
        repo_root=repo,
        wrapper_home=tmp_path / "home",
        bd=BdConfig(workspace=tmp_path / "bd", actor="actor"),
        project_config={} if project_config is None else project_config,
        roles=(
            {
                "implementer": RunnerBinding(
                    profile="implementer", model="implementer", effort="medium"
                ),
                "critic": RunnerBinding(
                    profile="critic", model="critic", effort="medium"
                ),
            }
            if roles is None
            else roles
        ),
        host="host",
        actor="actor",
        supervisor=SupervisorConfig(
            repo_root=repo, wrapper_root=wrapper_root, host="host"
        ),
    )
    return (
        Composition(
            config=config,
            store=fake_store,
            supervisor_config=config.supervisor,
            git=cast(Git, git),
            clock=cast(Clock, object()),
            profiles=_AvailableProfiles() if profiles is None else profiles,
            spawner=cast(Spawner, object()),
        ),
        git,
    )


# Which role staffs which build-loop node, as `workflows/build-loop.toml` spells
# it. The test binds each role to a profile NAMED for it, so a root that pinned
# one role twice — or dropped one — cannot pass.
BUILD_LOOP_NODE_ROLES: Final[dict[str, str]] = {
    "write_tests": "test-author",
    "review_tests": "test-critic",
    "implement": "implementer",
    "review_impl": "impl-critic",
    "critic": "critic",
}


@pytest.mark.bd
def test_build_loop_create_pins_both_instance_inputs_and_all_five_roles(
    store: WorkflowStore, tmp_path: Path
) -> None:
    """`create workflows/build-loop.toml` with both `--input` pairs, on real bd.

    This is the D2 command minus argv parsing: `__main__._instance_inputs`
    turns `--input NAME=PATH` into exactly this mapping. It runs against the
    real backend because a root is immutable once written (§3.1) — a lossy
    write that dropped `seam_contract` or a role binding would be silent, and
    the fake bd cannot prove it did not happen.
    """
    composition, _ = _instance_composition(
        store,
        tmp_path,
        roles={
            role: RunnerBinding(profile=role, model=f"{role}-model", effort="medium")
            for role in BUILD_LOOP_ROLES
        },
    )
    inputs: dict[str, Path] = {}
    for name, body in BUILD_LOOP_INSTANCE_INPUTS.items():
        path = tmp_path / f"{name}.md"
        path.write_text(body, encoding="utf-8")
        inputs[name] = path

    root = instantiate(
        composition,
        BUILD_LOOP_GRAPH,
        instance_key=instance_key(),
        instance_inputs=inputs,
        allow_test_flags=False,
        overrides={},
    )

    reloaded = store.reads.load_root(root.root_id)
    assert {
        pinned.name: pinned.body for pinned in reloaded.metadata.instance_inputs
    } == dict(BUILD_LOOP_INSTANCE_INPUTS)
    # Body and digest travel together; comparing only one would miss a backend
    # that round-tripped the pair inconsistently.
    assert {
        pinned.name: pinned.sha256 for pinned in reloaded.metadata.instance_inputs
    } == {
        name: hashlib.sha256(body.encode("utf-8")).hexdigest()
        for name, body in BUILD_LOOP_INSTANCE_INPUTS.items()
    }
    settings = {setting.key: setting for setting in reloaded.metadata.resolved_config}
    assert {
        node: settings[f"node.{node}.runner"].value for node in BUILD_LOOP_NODE_ROLES
    } == BUILD_LOOP_NODE_ROLES


def test_instantiate_pins_project_resolution_and_creates_instance_branch(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """Instantiation pins project bounds, input bytes and the root branch."""
    composition, git = _instance_composition(
        fake_store, tmp_path, project_config={"region.build-review.max_entries": 2}
    )
    brief = tmp_path / "brief.md"
    brief.write_text("implement this", encoding="utf-8")
    root = instantiate(
        composition,
        VALID_FIXTURE,
        instance_key="instance",
        instance_inputs={"task_brief": brief},
        allow_test_flags=False,
        overrides={},
    )
    settings = {setting.key: setting for setting in root.metadata.resolved_config}
    assert settings["region.build-review.max_entries"].value == 2
    assert settings["region.build-review.max_entries"].source.value == "project-config"
    branch = INSTANCE_BRANCH.format(root_id=root.root_id)
    assert git.updated == [(branch, git.base)]
    assert root.metadata.instance_inputs[0].body == "implement this"
    assert settings["node.implement.runner"].value == "implementer"
    assert settings["node.review.runner"].value == "critic"
    assert {key for key in settings if key.startswith("verify.")}

    again = instantiate(
        composition,
        VALID_FIXTURE,
        instance_key="instance",
        instance_inputs={"task_brief": brief},
        allow_test_flags=False,
        overrides={},
    )
    assert again.root_id == root.root_id
    assert git.updated == [(branch, git.base)]


def test_instantiate_refuses_brief_source_and_runner_role_failures(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """The root cannot pin an oversized, wrongly sourced, or unstaffed instance."""
    composition, _ = _instance_composition(fake_store, tmp_path)
    brief = tmp_path / "brief.md"
    brief.write_text("brief", encoding="utf-8")
    oversized = tmp_path / "oversized.md"
    oversized.write_text("x" * 65537, encoding="utf-8")
    with pytest.raises(ResolutionError, match="byte cap"):
        instantiate(
            composition,
            VALID_FIXTURE,
            instance_key="oversized",
            instance_inputs={"task_brief": oversized},
            allow_test_flags=False,
            overrides={},
        )
    empty = tmp_path / "empty.md"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ResolutionError, match="must not be empty"):
        instantiate(
            composition,
            VALID_FIXTURE,
            instance_key="empty",
            instance_inputs={"task_brief": empty},
            allow_test_flags=False,
            overrides={},
        )
    wrong_source = tmp_path / "wrong-source.toml"
    wrong_source.write_text(
        VALID_FIXTURE.read_text(encoding="utf-8")
        .replace('producer      = "instance"', 'producer      = "node:review"', 1)
        .replace(
            'inputs        = ["task_brief", "review_findings"]',
            'inputs        = ["review_findings"]',
            1,
        )
        .replace(
            'inputs        = ["task_brief", "diff_artifact", "review_findings"]',
            'inputs        = ["diff_artifact", "review_findings"]',
            1,
        ),
        encoding="utf-8",
    )
    with pytest.raises(ResolutionError, match="producer=instance"):
        instantiate(
            composition,
            wrong_source,
            instance_key="wrong-source",
            instance_inputs={"task_brief": brief},
            allow_test_flags=False,
            overrides={},
        )
    unstaffed, _ = _instance_composition(
        fake_store,
        tmp_path / "unstaffed",
        roles={"other": RunnerBinding(profile="other", model="other", effort="medium")},
    )
    with pytest.raises(ResolutionError, match="unknown runner roles"):
        instantiate(
            unstaffed,
            VALID_FIXTURE,
            instance_key="unstaffed",
            instance_inputs={"task_brief": brief},
            allow_test_flags=False,
            overrides={},
        )


def test_instantiate_refuses_missing_base_before_creating_a_branch(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """A branch is never created from an object the repository cannot read."""
    composition, git = _instance_composition(fake_store, tmp_path)
    git.base_exists = False
    brief = tmp_path / "brief.md"
    brief.write_text("brief", encoding="utf-8")
    with pytest.raises(ResolutionError, match="base commit is missing"):
        instantiate(
            composition,
            VALID_FIXTURE,
            instance_key="missing-base",
            instance_inputs={"task_brief": brief},
            allow_test_flags=False,
            overrides={},
        )
    assert git.updated == []


def _two_instance_input_graph(tmp_path: Path) -> Path:
    """A feature-delivery variant with a second `producer = "instance"` source.

    The shipped graph declares exactly one instance input, so neither the
    sort order of the pinned tuple nor the aggregate byte cap (which only a
    second body can push past while each body stays under the per-input cap)
    is observable against it.
    """
    variant = tmp_path / "two-inputs.toml"
    variant.write_text(
        VALID_FIXTURE.read_text(encoding="utf-8").replace(
            'inputs        = ["task_brief", "review_findings"]',
            'inputs        = ["task_brief", "extra_brief", "review_findings"]',
            1,
        )
        + "\n[[source]]\n"
        'name          = "extra_brief"\n'
        'producer      = "instance"\n'
        "optional      = false\n"
        "trim_priority = 1\n",
        encoding="utf-8",
    )
    return variant


def test_instantiate_pins_every_named_instance_input_sorted_by_name(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """Each supplied input is pinned under its own name, in a stable order."""
    composition, _ = _instance_composition(fake_store, tmp_path)
    bodies = {"task_brief": "implement this", "extra_brief": "and also this"}
    paths = {}
    for name, body in bodies.items():
        path = tmp_path / f"{name}.md"
        path.write_text(body, encoding="utf-8")
        paths[name] = path

    root = instantiate(
        composition,
        _two_instance_input_graph(tmp_path),
        instance_key="two-inputs",
        instance_inputs=paths,
        allow_test_flags=False,
        overrides={},
    )

    pinned = root.metadata.instance_inputs
    assert [item.name for item in pinned] == ["extra_brief", "task_brief"]
    assert {item.name: item.body for item in pinned} == bodies
    assert [item.sha256 for item in pinned] == [
        hashlib.sha256(bodies[item.name].encode("utf-8")).hexdigest() for item in pinned
    ]


def test_instantiate_refuses_a_missing_required_input_before_any_bd_write(
    fake_store: WorkflowStore, fake_bd: FakeBd, tmp_path: Path
) -> None:
    """A required input nobody supplied names itself and creates no root."""
    composition, _ = _instance_composition(fake_store, tmp_path)
    brief = tmp_path / "brief.md"
    brief.write_text("implement this", encoding="utf-8")

    with pytest.raises(ResolutionError, match="extra_brief"):
        instantiate(
            composition,
            _two_instance_input_graph(tmp_path),
            instance_key="missing-input",
            instance_inputs={"task_brief": brief},
            allow_test_flags=False,
            overrides={},
        )

    assert fake_bd.command_count("create") == 0


def test_instantiate_refuses_an_undeclared_instance_input_name(
    fake_store: WorkflowStore, fake_bd: FakeBd, tmp_path: Path
) -> None:
    """An input the graph never declared is named and refused."""
    composition, _ = _instance_composition(fake_store, tmp_path)
    brief = tmp_path / "brief.md"
    brief.write_text("implement this", encoding="utf-8")

    with pytest.raises(ResolutionError, match="stowaway"):
        instantiate(
            composition,
            VALID_FIXTURE,
            instance_key="undeclared",
            instance_inputs={"task_brief": brief, "stowaway": brief},
            allow_test_flags=False,
            overrides={},
        )

    assert fake_bd.command_count("create") == 0


def test_instantiate_refuses_inputs_over_the_aggregate_root_cap(
    fake_store: WorkflowStore, fake_bd: FakeBd, tmp_path: Path
) -> None:
    """Two individually legal bodies still cannot exceed what `create_root` takes."""
    composition, _ = _instance_composition(fake_store, tmp_path)
    half = MAX_INSTANCE_INPUT_BYTES // 2 + 1
    paths = {}
    for name in ("task_brief", "extra_brief"):
        path = tmp_path / f"{name}.md"
        path.write_text("x" * half, encoding="utf-8")
        paths[name] = path

    with pytest.raises(ResolutionError, match="aggregate"):
        instantiate(
            composition,
            _two_instance_input_graph(tmp_path),
            instance_key="over-aggregate",
            instance_inputs=paths,
            allow_test_flags=False,
            overrides={},
        )

    assert fake_bd.command_count("create") == 0


def test_ensure_instance_branch_refuses_a_null_base_before_any_write(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """A null base is distinct from an unreadable base and cannot make a branch."""
    composition, git = _instance_composition(fake_store, tmp_path)
    original = make_root(fake_store, load_definition())
    root = original.model_copy(
        update={
            "metadata": original.metadata.model_copy(
                update={"instance_base_commit": None}
            )
        }
    )
    from workflow_interpreter.foreman.resolve import ensure_instance_branch

    with pytest.raises(ResolutionError, match="base commit is missing"):
        ensure_instance_branch(composition, root)
    assert git.commit_calls == []
    assert git.updated == []


def test_config_refuses_split_supervisor_identity_and_guards_owner_file(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """One foreman root has one repository and one durable ownership record."""
    composition, _ = _instance_composition(fake_store, tmp_path)
    config = composition.config
    with pytest.raises(ValueError, match="supervisor repo_root"):
        ForemanConfig(
            repo_root=config.repo_root,
            wrapper_home=config.wrapper_home,
            bd=config.bd,
            host=config.host,
            actor=config.actor,
            supervisor=SupervisorConfig(
                repo_root=tmp_path / "other-repository",
                wrapper_root=config.wrapper_root,
                host=config.host,
            ),
        )
    with pytest.raises(ValueError, match="supervisor wrapper_root"):
        ForemanConfig(
            repo_root=config.repo_root,
            wrapper_home=config.wrapper_home,
            bd=config.bd,
            host=config.host,
            actor=config.actor,
            supervisor=SupervisorConfig(
                repo_root=config.repo_root,
                wrapper_root=tmp_path / "other-wrapper",
                host=config.host,
            ),
        )
    assert config.owner_path == config.wrapper_root / "owner.json"
    assert ensure_owner(config).repo_root == config.repo_root.resolve()
    assert read_record(config.owner_path, OwnerRecord) == OwnerRecord(
        repo_root=config.repo_root.resolve()
    )
    write_record(
        config.owner_path, OwnerRecord(repo_root=tmp_path / "another-repository")
    )
    with pytest.raises(OwnerConflict, match="different repository"):
        ensure_owner(config)


def test_foreman_config_hashes_the_resolved_repository_path(tmp_path: Path) -> None:
    """A symlinked repository derives the same wrapper-root digest as its target."""
    real = tmp_path / "real"
    alias = tmp_path / "alias"
    real.mkdir()
    alias.symlink_to(real, target_is_directory=True)
    home = tmp_path / "home"

    def config_for(repo_root: Path) -> ForemanConfig:
        wrapper_root = (
            home / hashlib.sha256(str(real.resolve()).encode("utf-8")).hexdigest()[:16]
        )
        return ForemanConfig(
            repo_root=repo_root,
            wrapper_home=home,
            bd=BdConfig(workspace=tmp_path / "bd", actor="actor"),
            host="host",
            actor="actor",
            supervisor=SupervisorConfig(
                repo_root=repo_root, wrapper_root=wrapper_root, host="host"
            ),
        )

    alias_config = config_for(alias)
    assert alias_config.wrapper_root == config_for(real).wrapper_root
    assert ensure_owner(alias_config).repo_root == real.resolve()


def test_foreman_config_refuses_relative_identity_paths(tmp_path: Path) -> None:
    """Root identity never depends on the process working directory."""
    invalid_supervisor = SupervisorConfig(
        repo_root=tmp_path / "repo",
        wrapper_root=tmp_path / "wrapper",
        host="host",
    )
    object.__setattr__(invalid_supervisor, "wrapper_root", Path("home") / "root")
    with pytest.raises(ValueError, match="must be absolute"):
        ForemanConfig(
            repo_root=Path("repo"),
            wrapper_home=tmp_path / "home",
            bd=BdConfig(workspace=tmp_path / "bd", actor="actor"),
            host="host",
            actor="actor",
            supervisor=SupervisorConfig(
                repo_root=tmp_path / "repo",
                wrapper_root=tmp_path / "home" / "root",
                host="host",
            ),
        )
    with pytest.raises(ValueError, match="must be absolute"):
        ForemanConfig(
            repo_root=tmp_path / "repo",
            wrapper_home=Path("home"),
            bd=BdConfig(workspace=tmp_path / "bd", actor="actor"),
            host="host",
            actor="actor",
            supervisor=invalid_supervisor,
        )


def test_composition_refuses_a_different_supervisor_instance(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """Composition cannot bypass ForemanConfig's supervisor identity guard."""
    composition, _ = _instance_composition(fake_store, tmp_path)
    with pytest.raises(ValueError, match="supervisor_config"):
        Composition(
            config=composition.config,
            store=composition.store,
            supervisor_config=composition.supervisor_config.model_copy(
                update={"host": "other-host"}
            ),
            git=composition.git,
            clock=composition.clock,
            profiles=composition.profiles,
            spawner=composition.spawner,
        )


def test_detached_spawner_separates_wrapper_and_runner_logs_and_records_its_handle(
    fake_store: WorkflowStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The `supervise root activation` spawn must not send wrapper output to `run.jsonl`."""
    composition, _ = _instance_composition(fake_store, tmp_path)
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    class Started:
        pid = 42

    def start(argv: tuple[str, ...], **kwargs: object) -> Started:
        calls.append((argv, kwargs))
        return Started()

    monkeypatch.setattr("workflow_interpreter.foreman.compose.subprocess.Popen", start)
    monkeypatch.setattr(
        "workflow_interpreter.foreman.compose.procfs.read_start_time",
        lambda _config, _pid: "start",
    )
    monkeypatch.setattr(
        "workflow_interpreter.foreman.compose.procfs.read_boot_id",
        lambda _config: "boot",
    )
    config_path = tmp_path / "foreman.toml"
    DetachedSpawner(composition.supervisor_config, config_path).launch(
        WrapperLaunch(
            root_id="root",
            activation_id="activation",
            request=entry_request(),
        )
    )
    argv, kwargs = calls[0]
    assert argv[0] == sys.executable
    assert argv[1:3] == ("-m", "workflow_interpreter.foreman")
    assert argv[3:] == (
        "--config",
        str(config_path),
        "supervise",
        "root",
        "activation",
    )
    assert kwargs["start_new_session"] is True
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert kwargs["stdout"] is not kwargs["stderr"]
    assert Path(kwargs["stdout"].name).name == "wrapper.log"
    assert Path(kwargs["stderr"].name).name == "wrapper.log"
    record = composition.supervisor_config.wrapper_root / "root" / "activation"
    assert json.loads((record / "wrapper.json").read_text(encoding="utf-8")) == {
        "boot_id": "boot",
        "pid": 42,
        "start_time": "start",
    }


def test_detached_spawner_records_an_immediately_exited_wrapper(
    fake_store: WorkflowStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A launched child that exits before procfs sampling is still dispatched."""
    composition, _ = _instance_composition(fake_store, tmp_path)

    class Started:
        pid = 42

    monkeypatch.setattr(
        "workflow_interpreter.foreman.compose.subprocess.Popen",
        lambda *_args, **_kwargs: Started(),
    )
    monkeypatch.setattr(
        "workflow_interpreter.foreman.compose.procfs.read_start_time",
        lambda _config, _pid: None,
    )
    monkeypatch.setattr(
        "workflow_interpreter.foreman.compose.procfs.read_boot_id",
        lambda _config: None,
    )
    DetachedSpawner(composition.supervisor_config, tmp_path / "foreman.toml").launch(
        WrapperLaunch(root_id="root", activation_id="gone", request=entry_request())
    )
    record = composition.supervisor_config.wrapper_root / "root" / "gone"
    assert json.loads((record / "wrapper.json").read_text(encoding="utf-8")) == {
        "boot_id": None,
        "pid": 42,
        "start_time": None,
    }


def test_resolve_never_registers_instructions_as_a_configuration_key() -> None:
    """ADR 0002: a node's job is graph text, never a project-config knob.

    `resolve()` exposes only the explicit supported task-setting mapping, so
    graph text cannot become a configuration key by being added to `Node`.
    """
    with pytest.raises(ResolutionError, match="unknown override"):
        resolve(load_definition(), {}, {"node.implement.instructions": "do it"})

    keys = {item.key for item in resolve(load_definition(), {}, {})}
    assert not any(key.endswith(".instructions") for key in keys)


def test_resolve_refuses_a_field_its_node_kind_forbids() -> None:
    """Spec §14: the resolved-config vocabulary is closed to what a node can have.

    `ship` is a gate. `node_fields_match_kind` already refuses `model` on a
    gate in the graph file, so accepting `node.ship.model` as configuration
    let an instance record a fully provenance-tagged setting for a field the
    node cannot possess and nothing will ever read.
    """
    with pytest.raises(ResolutionError, match="unknown override"):
        resolve(load_definition(), {}, {"node.ship.model": "chosen"})

    with pytest.raises(ResolutionError, match="unknown project config"):
        resolve(load_definition(), {"node.ship.model": "chosen"}, {})


def test_resolve_still_offers_every_field_the_node_kind_allows() -> None:
    """Closing the vocabulary must not narrow a task node's real settings."""
    keys = {item.key for item in resolve(load_definition(), {}, {})}

    assert "node.implement.model" in keys
    assert "node.implement.runner" in keys
    assert "node.implement.isolation" in keys
    assert "node.implement.max_steers" in keys
    # A gate carries no execution field; its own `gate_type`/`binds` are
    # structural, so no gate or terminal contributes any key at all.
    assert not any(key.startswith("node.ship.") for key in keys)
    assert not any(key.startswith("node.triage.") for key in keys)
    assert not any(key.startswith("node.shipped.") for key in keys)
    assert not any(key.endswith(".region") for key in keys)


def test_resolve_refuses_a_gate_field_on_a_task_node() -> None:
    """The closure runs both ways: a task cannot be configured like a gate."""
    with pytest.raises(ResolutionError, match="unknown override"):
        resolve(load_definition(), {}, {"node.implement.gate_type": "human"})


def test_resolve_refuses_to_configure_whether_a_human_must_approve() -> None:
    """§9: `gate_type` is never read from resolved config, so accepting it
    recorded a provenance-tagged setting that silently did nothing — while
    reading as though a project had removed an approval requirement."""
    for key in ("node.ship.gate_type", "node.ship.binds"):
        with pytest.raises(ResolutionError, match="unknown override"):
            resolve(load_definition(), {}, {key: "human"})


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("node.implement.max_wall", "banana"),
        ("node.implement.stale_after", "9 minutes"),
        ("node.implement.isolation", "sandbox"),
    ],
)
def test_resolve_refuses_a_value_the_node_field_cannot_hold(
    key: str, value: str
) -> None:
    """A root is immutable, so an unusable value must never reach one.

    The scalar type check alone accepts all three — they are `str` — and the
    execution view would then raise on every tick of an instance nobody can
    repair (cr-7h8 review).
    """
    with pytest.raises(ResolutionError, match="unusable value"):
        resolve(load_definition(), {}, {key: value})

    with pytest.raises(ResolutionError, match="unusable value"):
        resolve(load_definition(), {key: value}, {})


def test_resolve_refuses_the_vendor_default_model_from_project_config() -> None:
    """A root cannot pin a model selected later by the runner CLI."""
    with pytest.raises(ResolutionError, match="vendor default"):
        resolve(load_definition(), {"node.implement.model": "default"}, {})


def test_resolve_refuses_the_vendor_default_model_from_instance_override() -> None:
    """An override cannot substitute the runner CLI's mutable default model."""
    with pytest.raises(ResolutionError, match="vendor default"):
        resolve(load_definition(), {}, {"node.implement.model": "default"})


def test_instantiate_refuses_an_unusable_override_before_writing_the_root(
    tmp_path: Path,
) -> None:
    """The refusal is at instantiation, where it is still recoverable."""
    lab = ForemanLab(tmp_path)

    with pytest.raises(ResolutionError, match="unusable value"):
        lab.instantiate_resolved({"node.implement.max_wall": "banana"})

    assert lab.store.reads.list_roots() == ()


def test_resolve_refuses_a_configured_runner_that_is_still_a_role() -> None:
    """Only the roles map resolves `profile:<role>`; config must state a profile."""
    with pytest.raises(ResolutionError, match="role.*reference|profile:"):
        resolve(
            load_definition(),
            {},
            {
                "node.implement.runner": "profile:reviewer",
                "node.implement.model": "chosen",
            },
        )


def test_resolve_refuses_a_configured_runner_without_its_model_and_effort() -> None:
    """A runner override must name the complete runner-model-effort binding."""
    with pytest.raises(ResolutionError, match="without"):
        resolve(load_definition(), {}, {"node.implement.runner": "claude"})
    with pytest.raises(ResolutionError, match="effort"):
        resolve(
            load_definition(),
            {},
            {"node.implement.runner": "claude", "node.implement.model": "opus"},
        )
    with pytest.raises(ResolutionError, match="effort"):
        resolve(
            load_definition(),
            {},
            {
                "node.implement.runner": "claude",
                "node.implement.model": "opus",
                "node.implement.effort": "",
            },
        )

    settled = {
        item.key: item
        for item in resolve(
            load_definition(),
            {},
            {
                "node.implement.runner": "claude",
                "node.implement.model": "opus",
                "node.implement.effort": "high",
            },
        )
    }
    assert settled["node.implement.runner"].value == "claude"
    assert settled["node.implement.model"].value == "opus"
    assert settled["node.implement.effort"].value == "high"


def test_resolved_node_falls_back_to_the_pinned_node(tmp_path: Path) -> None:
    """An unresolved field keeps the value the pinned graph body declares."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    pinned = root.index.nodes[IMPLEMENT]

    view = resolved_node(root, IMPLEMENT)

    assert view.runner_profile == FAKE_PROFILE
    assert view.node.max_wall == pinned.max_wall
    assert view.node.token_budget == pinned.token_budget
    # A list is outside the resolvable vocabulary, so it is never overlaid.
    assert view.node.allowed_paths == pinned.allowed_paths


def test_resolved_node_overlays_every_resolvable_execution_field(
    tmp_path: Path,
) -> None:
    """A valid 20m writer resolution replaces each pinned execution scalar (§3.1)."""
    lab = ForemanLab(
        tmp_path,
        overrides={
            "node.implement.model": "override-model",
            "node.implement.isolation": "in-repo",
            "node.implement.writes": True,
            "node.implement.token_budget": 1234,
            "node.implement.max_wall": "20m",
            "node.implement.stale_after": "3m",
            "node.implement.max_infra_retries": 3,
            "node.implement.max_steers": 4,
        },
    )
    root = lab.instantiate()

    view = resolved_node(root, IMPLEMENT)

    assert view.model == "override-model"
    assert view.node.model == "override-model"
    assert view.node.isolation is IsolationMode.IN_REPO
    assert view.node.writes is True
    assert view.node.token_budget == 1234
    assert view.node.max_wall == "20m"
    assert view.node.stale_after == "3m"
    assert view.node.max_infra_retries == 3
    assert view.node.max_steers == 4


def test_instantiate_refuses_writes_false_with_non_empty_pinned_allowed_paths(
    tmp_path: Path,
) -> None:
    """`node.implement.writes=false` cannot pin the authored non-empty paths."""
    lab = ForemanLab(tmp_path)

    with pytest.raises(ResolutionError, match="allowed_paths_well_formed"):
        lab.instantiate_resolved({"node.implement.writes": False})

    assert lab.store.reads.list_roots() == ()


def test_instantiate_refuses_max_wall_below_pinned_verify_timeout(
    tmp_path: Path,
) -> None:
    """`node.implement.max_wall=9m` cannot undercut its 10m verifier timeout."""
    lab = ForemanLab(tmp_path)

    with pytest.raises(ResolutionError, match="verify_entries_well_formed"):
        lab.instantiate_resolved({"node.implement.max_wall": "9m"})

    assert lab.store.reads.list_roots() == ()


def test_resolve_does_not_log_an_unchanged_nodes_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`node.implement.model` must not log the critic's pinned warning."""
    definition = load_graph(BUILD_LOOP_GRAPH)
    monkeypatch.setattr(
        "workflow_interpreter.foreman.resolve._EFFECTIVE_NODE_RULES", PHASE_B_RULES
    )

    with capture_logs() as captured:
        resolve(definition, {}, {"node.implement.model": "override-model"})

    assert [
        entry
        for entry in captured
        if entry["event"] == "foreman.effective_node_warning"
    ] == []


def test_resolved_node_refuses_a_root_that_never_resolved_its_role(
    tmp_path: Path,
) -> None:
    """A role reference is not a runner: an unresolved one fails loud, not late.

    `profile:<role>` names nothing a profile resolver can answer, and reading
    the live role map instead is the drift `resolved_node` exists to prevent.
    """
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    stripped = root.model_copy(
        update={
            "metadata": root.metadata.model_copy(
                update={
                    "resolved_config": tuple(
                        item
                        for item in root.metadata.resolved_config
                        if item.key != "node.implement.runner"
                    )
                }
            )
        }
    )

    with pytest.raises(UnresolvedRunnerError, match="implementer"):
        resolved_node(stripped, IMPLEMENT)
