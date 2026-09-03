"""Pure contracts for composition, resolution, and root instantiation."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

from tests._bdio import entry_request, load_definition, make_root
from tests._helpers import VALID_FIXTURE
from workflow_interpreter.bdio import BdConfig
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.errors import BdConfigError
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
from workflow_interpreter.foreman.owner import OwnerConflict, OwnerRecord, ensure_owner
from workflow_interpreter.foreman.resolve import (
    ResolutionError,
    _resolved_config,
    instantiate,
    resolve,
)
from workflow_interpreter.supervisor.clock import Clock
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.gitio import Git
from workflow_interpreter.supervisor.paths import read_record, write_record


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
        profiles=cast(ProfileResolver, object()),
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
            },
        )
    }
    assert settings["node.implement.model"].value == "opus-5"
    assert settings["node.implement.model"].source.value == "instance-override"
    assert settings["node.implement.runner"].value == "operator-runner"
    assert settings["node.implement.runner"].source.value == "instance-override"

    bound_composition, _ = _instance_composition(
        fake_store,
        tmp_path / "bound",
        roles={
            "implementer": RunnerBinding(profile="bound-runner", model="bound-model"),
            "critic": RunnerBinding(profile="critic"),
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

    project_composition, _ = _instance_composition(
        fake_store,
        tmp_path / "project",
        project_config={"node.implement.model": "project-model"},
    )
    project_settings = {
        item.key: item
        for item in _resolved_config(project_composition, load_definition(), {})
    }
    assert project_settings["node.implement.model"].value == "project-model"
    assert project_settings["node.implement.model"].source.value == "project-config"


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


def test_resolve_derives_scalar_node_settings_from_the_schema() -> None:
    """Scalar schema settings can be overridden without a hand-maintained list."""
    settings = {
        item.key: item
        for item in resolve(
            load_definition(),
            {},
            {
                "node.implement.token_budget": 42,
                "node.implement.max_wall": "2m",
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
        "node.implement.max_wall": "2m",
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
                "implementer": RunnerBinding(profile="implementer"),
                "critic": RunnerBinding(profile="critic"),
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
            profiles=cast(ProfileResolver, object()),
            spawner=cast(Spawner, object()),
        ),
        git,
    )


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
        brief_path=brief,
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
        brief_path=brief,
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
            brief_path=oversized,
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
            brief_path=empty,
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
            brief_path=brief,
            allow_test_flags=False,
            overrides={},
        )
    unstaffed, _ = _instance_composition(
        fake_store,
        tmp_path / "unstaffed",
        roles={"other": RunnerBinding(profile="other")},
    )
    with pytest.raises(ResolutionError, match="unknown runner roles"):
        instantiate(
            unstaffed,
            VALID_FIXTURE,
            instance_key="unstaffed",
            brief_path=brief,
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
            brief_path=brief,
            allow_test_flags=False,
            overrides={},
        )
    assert git.updated == []


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


def test_detached_spawner_uses_a_no_shell_session_and_records_its_handle(
    fake_store: WorkflowStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Production dispatch has no terminal or shell through which to escape."""
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
    assert argv[1:4] == ("-m", "workflow_interpreter.foreman", "supervise")
    assert argv[4:] == ("root", "activation", "--config", str(config_path))
    assert kwargs["start_new_session"] is True
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert kwargs["stdout"] is kwargs["stderr"]
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

    `resolve()` derives override keys by reflection over every non-required
    scalar `Node` field, so a new string field is registered automatically
    unless it is excluded.
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
