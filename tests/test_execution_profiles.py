"""Named policy is pinned authority, independent of vendor flag spelling."""

import json
import re
from pathlib import Path

import pytest

from tests._bdio import make_root
from tests._helpers import VALID_FIXTURE
from tests._inspector import FrozenClock
from tests._profiles import Lab
from workflow_interpreter import GraphValidationError, load_graph
from workflow_interpreter.bdio import WorkflowStore
from workflow_interpreter.foreman.errors import ResolutionError
from workflow_interpreter.foreman.execution import resolved_node
from workflow_interpreter.foreman.resolve import resolve
from workflow_interpreter.inspector.execution import (
    ExecutionPolicy,
    ExecutionProfileName,
    ToolNetwork,
)
from workflow_interpreter.profiles import CrewName, ProfileConfig
from workflow_interpreter.profiles.registry import ProfileRegistry
from workflow_interpreter.schema.loader import canonical_bytes, load_pinned_body


def registry() -> ProfileRegistry:
    """Construct the registered vendor profiles without discovering host state."""
    return ProfileRegistry(ProfileConfig(), FrozenClock(), {})


def named_graph(tmp_path: Path) -> Path:
    """Name the fixture's existing writer and reviewer contracts."""
    text = re.sub(
        r"writes\s*=\s*true", 'execution_profile = "writer"', VALID_FIXTURE.read_text()
    )
    text = re.sub(r"writes\s*=\s*false", 'execution_profile = "reviewer"', text)
    path = tmp_path / "named.toml"
    path.write_text(text)
    return path


def test_named_nodes_derive_writes_and_round_trip(tmp_path: Path) -> None:
    """Serialized named nodes never acquire a second writes authority."""
    graph = load_graph(named_graph(tmp_path))
    tasks = {node.name: node for node in graph.document.node}
    assert tasks["implement"].writes is True
    assert tasks["review"].writes is False
    payload = json.loads(canonical_bytes(graph.document))
    assert all("writes" not in node for node in payload["node"])
    assert (
        load_pinned_body(canonical_bytes(graph.document)).content_hash
        == graph.content_hash
    )


@pytest.mark.parametrize("extra", ["writes = true", "writes = false"])
def test_named_nodes_refuse_authored_writes(tmp_path: Path, extra: str) -> None:
    """Even a matching writes flag is a forbidden second authority."""
    path = named_graph(tmp_path)
    path.write_text(
        path.read_text().replace(
            'execution_profile = "writer"', 'execution_profile = "writer"\n' + extra
        )
    )
    with pytest.raises(GraphValidationError):
        load_graph(path)


def test_named_reviewer_refuses_checkout_grants(tmp_path: Path) -> None:
    """Named reviewers cannot compose write authority with allowed_paths."""
    path = named_graph(tmp_path)
    path.write_text(
        re.sub(
            r"allowed_paths\s*=\s*\[\]", 'allowed_paths = ["src/**"]', path.read_text()
        )
    )
    with pytest.raises(GraphValidationError):
        load_graph(path)


@pytest.mark.parametrize("project", [False, True])
def test_named_nodes_refuse_writes_overrides(tmp_path: Path, project: bool) -> None:
    """Neither configuration layer can replace a named contract's authority."""
    graph = load_graph(named_graph(tmp_path))
    override = {"node.implement.writes": True}
    with pytest.raises(ResolutionError, match="execution_profile"):
        resolve(graph, override if project else {}, {} if project else override)


def test_named_root_pins_policy_and_legacy_body_stays_unchanged(
    tmp_path: Path, fake_store: WorkflowStore
) -> None:
    """A named root persists meaning; loading legacy roots never migrates them."""
    legacy = load_graph(VALID_FIXTURE)
    before = canonical_bytes(legacy.document)
    assert canonical_bytes(load_pinned_body(before).document) == before
    graph = load_graph(named_graph(tmp_path))
    from workflow_interpreter.bdio import ConfigSource, ResolvedSetting

    root = make_root(
        fake_store,
        graph,
        *(
            ResolvedSetting(
                key=f"node.{name}.crew",
                value="claude",
                source=ConfigSource.ROLE_BINDING,
            )
            for name in ("implement", "review")
        ),
        profiles=registry(),
    )
    policy = resolved_node(root, "review").execution_policy
    assert isinstance(policy, ExecutionPolicy)
    assert policy.name is ExecutionProfileName.REVIEWER
    assert not policy.writes
    assert policy.tool_network is ToolNetwork.NOT_ENFORCED


@pytest.mark.proc
@pytest.mark.parametrize("crew", ["codex", "claude"])
@pytest.mark.parametrize(
    "name", [ExecutionProfileName.WRITER, ExecutionProfileName.REVIEWER]
)
def test_named_launch_records_grants_and_network_fact(
    lab: Lab, crew: str, name: ExecutionProfileName
) -> None:
    """Both vendors launch both policies; receipts and status expose the same fact."""
    from workflow_interpreter.foreman.execution import execution_status
    from workflow_interpreter.inspector.models import LaunchReceipt
    from workflow_interpreter.inspector.paths import read_record
    from workflow_interpreter.profiles import CrewName

    result = lab.run(
        CrewName(crew),
        writes=name is ExecutionProfileName.WRITER,
        execution_profile=name,
    )
    activation_id = result.dispatch.activation.activation_id
    receipt = read_record(lab.paths.receipt(activation_id), LaunchReceipt)
    assert receipt is not None and receipt.execution_grants is not None
    grants = receipt.execution_grants
    expected = ToolNetwork.DENIED if crew == "codex" else ToolNetwork.NOT_ENFORCED
    assert receipt.tool_network is expected
    assert grants.policy.name is name
    assert (
        execution_status(lab.paths, (activation_id,))[activation_id]["tool_network"]
        == expected.value
    )
    if name is ExecutionProfileName.REVIEWER:
        assert not grants.checkout_write_dirs and not grants.git_dirs
        assert all(
            not Path(path).is_relative_to(grants.checkout_read_root)
            for path in grants.writable_directories
        )
        if crew == "claude":
            allowed = receipt.argv[
                receipt.argv.index("--allowedTools") + 1 : receipt.argv.index(
                    "--disallowedTools"
                )
            ]
            assert "Bash" in allowed


def test_named_profile_refuses_sandbox_off(tmp_path: Path) -> None:
    """Named authority cannot be claimed without its physical outer bound."""
    from workflow_interpreter.inspector.errors import SandboxUnavailable
    from workflow_interpreter.inspector.sandbox import SandboxMode
    from workflow_interpreter.profiles import CrewName

    lab = Lab(tmp_path, sandbox=SandboxMode.OFF)
    with pytest.raises(SandboxUnavailable, match="outer sandbox"):
        lab.run(CrewName.CODEX, execution_profile=ExecutionProfileName.WRITER)


@pytest.mark.parametrize("crew", ["codex", "claude"])
@pytest.mark.parametrize(
    "name", [ExecutionProfileName.WRITER, ExecutionProfileName.REVIEWER]
)
def test_named_launch_and_resume_share_grants(
    tmp_path: Path, crew: str, name: ExecutionProfileName
) -> None:
    """Resuming changes the vendor verb, never the activation's authority."""
    from tests._inspector import FrozenClock
    from tests._profiles import make_inspector_config, make_task, writable_roots_in
    from workflow_interpreter.contracts.execution import policy_for
    from workflow_interpreter.inspector.execution import resolve_grants
    from workflow_interpreter.inspector.sandbox import plan_for
    from workflow_interpreter.profiles.claude import ClaudeProfile
    from workflow_interpreter.profiles.codex import CodexProfile
    from workflow_interpreter.profiles.config import ProfileConfig

    task = make_task(tmp_path, writes=name is ExecutionProfileName.WRITER)
    task = task.model_copy(
        update={
            "execution_profile": name,
            "execution_policy": policy_for(
                name, registry().profile_for(crew).tool_network
            ),
            "checkout_read_root": task.cwd,
        }
    )
    config = make_inspector_config(tmp_path)
    plan = plan_for(
        task,
        repo_root=config.repo_root,
        wrapper_root=config.wrapper_root,
        channels_dir=Path(task.channels.outcome_file).parent,
    )
    grants = resolve_grants(task, plan, registry().profile_for(crew))
    task = task.model_copy(update={"execution_grants": grants})
    profile = (CodexProfile if crew == "codex" else ClaudeProfile)(
        ProfileConfig(), FrozenClock(), {}
    )
    session = "00000000-0000-4000-8000-000000000001"
    launch = profile.build_command(task, session)
    resume = profile.build_resume_command(session, "continue", task)
    assert launch.cwd == resume.cwd == grants.process_cwd
    if crew == "codex":
        assert writable_roots_in(launch.argv) == grants.writable_directories
        assert writable_roots_in(resume.argv) == grants.writable_directories
    else:
        if name is ExecutionProfileName.REVIEWER:
            tools = launch.argv[
                launch.argv.index("--tools") + 1 : launch.argv.index("--allowedTools")
            ]
            assert set(tools) == {"Read", "Glob", "Grep", "Bash", "Write"}
        assert (
            launch.argv[launch.argv.index("--tools") :]
            == (resume.argv[resume.argv.index("--tools") :])
        )


@pytest.mark.parametrize("escape", ["cache", "scratch", "channels"])
def test_named_reviewer_refuses_private_grant_escape(
    tmp_path: Path, escape: str
) -> None:
    """Checkout and wrapper records cannot become private writable roots."""
    from tests._profiles import make_inspector_config, make_task
    from workflow_interpreter.contracts.execution import policy_for
    from workflow_interpreter.inspector.errors import SandboxPathRefused
    from workflow_interpreter.inspector.execution import resolve_grants
    from workflow_interpreter.inspector.sandbox import plan_for

    task = make_task(tmp_path, writes=False)
    task = task.model_copy(
        update={
            "execution_profile": ExecutionProfileName.REVIEWER,
            "execution_policy": policy_for(
                ExecutionProfileName.REVIEWER, ToolNetwork.DENIED
            ),
        }
    )
    config = make_inspector_config(tmp_path)
    plan = plan_for(
        task,
        repo_root=config.repo_root,
        wrapper_root=config.wrapper_root,
        channels_dir=Path(task.channels.outcome_file).parent,
    )
    if escape == "cache":
        plan = plan.model_copy(update={"toolchain_cache": (Path(task.cwd),)})
    else:
        protected = Path(task.channels.outcome_file).parent.parent
        field = "scratch_dir" if escape == "scratch" else "outcome_file"
        value = str(protected if escape == "scratch" else protected / "outcome.json")
        task = task.model_copy(
            update={
                "channels": task.channels.model_copy(update={field: value}),
            }
        )
    with pytest.raises(SandboxPathRefused, match="private roots"):
        resolve_grants(task, plan, registry().profile_for("codex"))


@pytest.mark.parametrize("crew", [None, "unknown-crew", ""])
def test_named_pin_requires_registered_crew(tmp_path: Path, crew: str | None) -> None:
    """A missing or unknown crew never becomes a not-enforced network fact."""
    from workflow_interpreter.bdio import CarrierIntegrityError, ConfigSource
    from workflow_interpreter.bdio.roots import pin_execution_policies
    from workflow_interpreter.bdio.wire import NodeSetting, ResolvedSetting

    graph = load_graph(named_graph(tmp_path))
    settings = tuple(
        ResolvedSetting(
            key=NodeSetting.CREW.at(node.name),
            value=crew,
            source=ConfigSource.GRAPH_DEFAULT,
        )
        for node in graph.document.node
        if node.execution_profile is not None and crew is not None
    )
    if crew is None:
        # A role chooses its registered crew when the activation is minted.
        assert pin_execution_policies(graph, settings, profiles=registry())
    else:
        with pytest.raises(CarrierIntegrityError, match="unregistered crew"):
            pin_execution_policies(graph, settings, profiles=registry())


def test_network_capability_is_declared_for_every_registered_crew() -> None:
    """Registry additions must have an explicit network capability."""
    from workflow_interpreter.profiles import CrewName
    from workflow_interpreter.profiles.registry import BUILDERS

    assert {crew: registry().profile_for(crew).tool_network for crew in BUILDERS} == {
        CrewName.CODEX: ToolNetwork.DENIED,
        CrewName.CODEX_APPSERVER: ToolNetwork.DENIED,
        CrewName.CLAUDE: ToolNetwork.NOT_ENFORCED,
        CrewName.OPENCODE: ToolNetwork.NOT_ENFORCED,
    }


@pytest.mark.parametrize(
    "field", ["checkout_write_dirs", "read_only_roots", "git_dirs", "read_only_pins"]
)
def test_named_plan_revalidates_supplied_grants(tmp_path: Path, field: str) -> None:
    """Pre-resolved grants cannot substitute unchecked roots or omit Git pins."""
    from tests._profiles import make_inspector_config, make_task
    from workflow_interpreter.contracts.execution import policy_for
    from workflow_interpreter.inspector.errors import SandboxPathRefused
    from workflow_interpreter.inspector.execution import resolve_grants
    from workflow_interpreter.inspector.sandbox import plan_for

    task = make_task(tmp_path, writes=True)
    task = task.model_copy(
        update={
            "execution_profile": ExecutionProfileName.WRITER,
            "execution_policy": policy_for(
                ExecutionProfileName.WRITER, ToolNetwork.DENIED
            ),
        }
    )
    config = make_inspector_config(tmp_path)
    kwargs = {
        "repo_root": config.repo_root,
        "wrapper_root": config.wrapper_root,
        "channels_dir": Path(task.channels.outcome_file).parent,
    }
    plan = plan_for(task, **kwargs)
    grants = resolve_grants(task, plan, registry().profile_for("codex"))
    changed = () if field == "read_only_pins" else (str(tmp_path / "unchecked"),)
    task = task.model_copy(
        update={"execution_grants": grants.model_copy(update={field: changed})}
    )
    with pytest.raises(SandboxPathRefused):
        plan_for(task, **kwargs)


def test_named_codex_in_repo_refusal_keeps_crew_error(tmp_path: Path) -> None:
    """Unsupported Codex isolation retains its actionable crew refusal."""
    from tests._profiles import make_inspector_config, make_task
    from workflow_interpreter.contracts.execution import policy_for
    from workflow_interpreter.inspector.execution import resolve_grants
    from workflow_interpreter.inspector.sandbox import plan_for
    from workflow_interpreter.profiles.errors import UnsupportedOptionError

    task = make_task(tmp_path, writes=True)
    config = make_inspector_config(tmp_path)
    task = task.model_copy(
        update={
            "cwd": str(config.repo_root),
            "checkout_read_root": str(config.repo_root),
            "execution_profile": ExecutionProfileName.WRITER,
            "execution_policy": policy_for(
                ExecutionProfileName.WRITER, ToolNetwork.DENIED
            ),
        }
    )
    plan = plan_for(
        task,
        repo_root=config.repo_root,
        wrapper_root=config.wrapper_root,
        channels_dir=Path(task.channels.outcome_file).parent,
    )
    with pytest.raises(UnsupportedOptionError, match="in-repo"):
        resolve_grants(task, plan, registry().profile_for("codex"))


def test_named_dispatch_requires_pinned_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dispatch cannot quietly derive authority when a builder forgets its pin."""
    from tests import _profiles
    from workflow_interpreter.profiles import CrewName
    from workflow_interpreter.profiles.errors import TaskRefused

    original = _profiles.task_builder

    from workflow_interpreter.inspector.launch import TaskBuilder
    from workflow_interpreter.schema.models import Node

    def unpinned(
        cwd: Path,
        node: Node,
        *,
        effort: str | None = "medium",
        execution_policy: ExecutionPolicy | None = None,
    ) -> TaskBuilder:
        """Simulate a builder that drops the persisted policy."""
        build = original(cwd, node, effort=effort, execution_policy=execution_policy)
        return lambda activation, channels: build(activation, channels).model_copy(
            update={"execution_policy": None}
        )

    monkeypatch.setattr(_profiles, "task_builder", unpinned)
    lab = Lab(tmp_path)
    with pytest.raises(TaskRefused, match="pinned policy"):
        lab.run(CrewName.CODEX, execution_profile=ExecutionProfileName.WRITER)


@pytest.mark.parametrize("mismatch", ["network", "name", "writes"])
def test_policy_mismatch_names_pinned_and_expected_contracts(
    tmp_path: Path, mismatch: str
) -> None:
    """A policy refusal describes both contracts rather than an opaque mismatch."""
    from tests._profiles import make_inspector_config, make_task
    from workflow_interpreter.contracts.execution import policy_for
    from workflow_interpreter.inspector.errors import SandboxPathRefused
    from workflow_interpreter.inspector.execution import resolve_grants
    from workflow_interpreter.inspector.sandbox import plan_for

    expected = policy_for(ExecutionProfileName.WRITER, ToolNetwork.DENIED)
    pinned = (
        policy_for(ExecutionProfileName.REVIEWER, ToolNetwork.DENIED)
        if mismatch == "name"
        else policy_for(ExecutionProfileName.WRITER, ToolNetwork.NOT_ENFORCED)
        if mismatch == "network"
        else expected
    )
    task = make_task(tmp_path, writes=True).model_copy(
        update={
            "execution_profile": ExecutionProfileName.WRITER,
            "execution_policy": pinned,
            "writes": mismatch != "writes",
        }
    )
    config = make_inspector_config(tmp_path)
    plan = plan_for(
        task,
        repo_root=config.repo_root,
        wrapper_root=config.wrapper_root,
        channels_dir=Path(task.channels.outcome_file).parent,
    )
    with pytest.raises(SandboxPathRefused) as error:
        resolve_grants(task, plan, registry().profile_for("codex"))
    assert f"pinned={pinned.model_dump_json()}" in str(error.value)
    assert f"expected={expected.model_dump_json()}" in str(error.value)


@pytest.mark.proc
def test_named_claude_reviewer_can_report_without_checkout_write(
    tmp_path: Path,
) -> None:
    """Check tool grants and run a reporting fixture inside the real outer bound."""
    import subprocess
    import sys

    from tests._inspector import FrozenClock
    from tests._profiles import host_env_with, make_inspector_config, make_task
    from workflow_interpreter.contracts.execution import policy_for
    from workflow_interpreter.inspector.execution import resolve_grants
    from workflow_interpreter.inspector.sandbox import plan_for, wrap
    from workflow_interpreter.profiles import ProfileConfig
    from workflow_interpreter.profiles.claude import ClaudeProfile

    task = make_task(tmp_path, writes=False).model_copy(
        update={
            "execution_profile": ExecutionProfileName.REVIEWER,
            "execution_policy": policy_for(
                ExecutionProfileName.REVIEWER, ToolNetwork.NOT_ENFORCED
            ),
        }
    )
    config = make_inspector_config(tmp_path)
    plan = plan_for(
        task,
        repo_root=config.repo_root,
        wrapper_root=config.wrapper_root,
        channels_dir=Path(task.channels.outcome_file).parent,
    )
    task = task.model_copy(
        update={
            "execution_grants": resolve_grants(
                task, plan, registry().profile_for("claude")
            )
        }
    )
    binary = tmp_path / "reporting-claude"
    binary.write_text(
        f"#!{sys.executable}\n"
        + """
import errno, os
from pathlib import Path
Path(os.environ["WF_OUTCOME_FILE"]).write_text('{"outcome":"accept"}')
Path(os.environ["WF_ARTIFACT_DIR"], "outcome").write_text("accept")
Path(os.environ["WF_ARTIFACT_DIR"], "findings.md").write_text("No blocking findings")
try:
    Path("forbidden.md").write_text("checkout write")
except OSError as error:
    assert error.errno in (errno.EROFS, errno.EACCES), error
else:
    raise AssertionError("reviewer wrote the checkout")
"""
    )
    binary.chmod(0o755)
    profile = ClaudeProfile(
        ProfileConfig(binary_overrides={CrewName.CLAUDE: str(binary)}),
        FrozenClock(),
        host_env_with(),
    )
    command = profile.build_command(task, "00000000-0000-4000-8000-000000000001")
    tools = command.argv[
        command.argv.index("--tools") + 1 : command.argv.index("--allowedTools")
    ]
    assert "Write" in tools and "Edit" not in tools
    allowed = command.argv[
        command.argv.index("--allowedTools") + 1 : command.argv.index(
            "--disallowedTools"
        )
    ]
    channels = task.channels
    assert set(allowed) == {
        "Read",
        "Glob",
        "Grep",
        "Bash",
        f"Edit(/{channels.artifact_dir}/**)",
        f"Edit(/{channels.outcome_file})",
        f"Edit(/{channels.effects_file})",
        f"Edit(/{channels.scratch_dir}/**)",
        f"Edit(/{task.execution_grants.private_cache}/**)",
    }
    completed = subprocess.run(
        wrap(command.argv, plan),
        check=False,
        cwd=command.cwd,
        env=dict(command.env),
        capture_output=True,
        timeout=15,
    )
    assert completed.returncode == 0, completed.stderr
    assert Path(channels.outcome_file).read_text() == '{"outcome":"accept"}'
    assert Path(channels.artifact_dir, "outcome").read_text() == "accept"
    assert (
        Path(channels.artifact_dir, "findings.md").read_text() == "No blocking findings"
    )
    assert not Path(task.cwd, "forbidden.md").exists()


def test_unknown_profile_identity_closes_dispatch_as_error_crew(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A miswired profile name becomes durable ERROR_CREW through real dispatch."""
    from tests._foreman import ForemanLab
    from tests._helpers import SHIPPED_FIXTURE
    from workflow_interpreter.bdio import Outcome

    lab = ForemanLab(tmp_path, toml=SHIPPED_FIXTURE)
    lab.instantiate()
    monkeypatch.setattr(lab.profiles.profile, "name", lambda: "unknown-crew")
    report = lab.tick()
    assert report.dispatched is not None
    activation = lab.store.reads.load_activation(report.dispatched)
    assert activation.metadata.outcome is Outcome.ERROR_CREW
    assert "unknown-crew" in activation.metadata.evidence.note
    assert activation.metadata.handle is None


@pytest.mark.parametrize("network", list(ToolNetwork))
def test_registered_fake_pins_and_launches_its_declared_network_fact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, network: ToolNetwork
) -> None:
    """A registered non-vendor crew supplies authority for the shipped graph."""
    from tests._foreman import ForemanLab
    from tests._helpers import SHIPPED_FIXTURE
    from workflow_interpreter.inspector.models import LaunchReceipt
    from workflow_interpreter.inspector.paths import read_record

    lab = ForemanLab(tmp_path, toml=SHIPPED_FIXTURE)
    monkeypatch.setattr(lab.profiles.profile, "tool_network", network)
    root = lab.instantiate_resolved()
    assert (
        root.index.nodes["implement"].execution_profile is ExecutionProfileName.WRITER
    )
    assert not any(
        item.key == "node.implement.execution_policy"
        for item in root.metadata.resolved_config
    )
    activation_id = lab.tick().dispatched
    assert activation_id is not None
    activation = lab.store.reads.load_activation(activation_id)
    assert activation.metadata.crew_profile == "fake"
    assert activation.metadata.execution_policy is not None
    assert activation.metadata.execution_policy.tool_network is network
    receipt = read_record(lab.wiring().paths.receipt(activation_id), LaunchReceipt)
    assert receipt is not None and receipt.tool_network is network


def test_new_activation_policy_uses_current_registered_crew_capability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The activation recomputes grants when a root's policy is historical."""
    from tests._foreman import ForemanLab
    from tests._helpers import SHIPPED_FIXTURE
    from workflow_interpreter.inspector.models import LaunchReceipt
    from workflow_interpreter.inspector.paths import read_record

    lab = ForemanLab(tmp_path, toml=SHIPPED_FIXTURE)
    root = lab.instantiate_resolved()
    assert not any(
        item.key == "node.implement.execution_policy"
        for item in root.metadata.resolved_config
    )
    monkeypatch.setattr(lab.profiles.profile, "tool_network", ToolNetwork.DENIED)

    activation_id = lab.tick().dispatched

    assert activation_id is not None
    activation = lab.store.reads.load_activation(activation_id)
    assert activation.metadata.execution_policy is not None
    assert activation.metadata.execution_policy.version == 1
    assert activation.metadata.execution_policy.tool_network is ToolNetwork.DENIED
    receipt = read_record(lab.wiring().paths.receipt(activation_id), LaunchReceipt)
    assert receipt is not None and receipt.tool_network is ToolNetwork.DENIED


@pytest.mark.parametrize("network", list(ToolNetwork))
def test_registry_extension_supplies_network_capability(
    tmp_path: Path, fake_store: WorkflowStore, network: ToolNetwork
) -> None:
    """Root admission accepts a registered non-vendor profile's declared fact."""
    from tests._inspector import FakeProfile

    profile = FakeProfile()
    profile.tool_network = network
    profiles = ProfileRegistry(
        ProfileConfig(), FrozenClock(), {}, builders={"fake": lambda *_: profile}
    )
    assert profiles.profile_for("profile:fake") is profile
    root = make_root(fake_store, load_graph(named_graph(tmp_path)), profiles=profiles)
    assert resolved_node(root, "implement").execution_policy.tool_network is network


def test_named_pin_requires_registry(tmp_path: Path, fake_store: WorkflowStore) -> None:
    """Root creation cannot infer capabilities without an injected registry."""
    from workflow_interpreter.bdio import CarrierIntegrityError

    with pytest.raises(CarrierIntegrityError, match="unregistered crew"):
        make_root(fake_store, load_graph(named_graph(tmp_path)))
