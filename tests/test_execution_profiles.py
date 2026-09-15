"""Named policy is pinned authority, independent of vendor flag spelling."""

import json
import re
from pathlib import Path

import pytest

from tests._bdio import make_root
from tests._helpers import VALID_FIXTURE
from tests._profiles import Lab
from workflow_interpreter import GraphValidationError, load_graph
from workflow_interpreter.bdio import WorkflowStore
from workflow_interpreter.foreman.errors import ResolutionError
from workflow_interpreter.foreman.execution import resolved_node
from workflow_interpreter.foreman.resolve import resolve
from workflow_interpreter.schema.loader import canonical_bytes, load_pinned_body
from workflow_interpreter.supervisor.execution import (
    ExecutionPolicy,
    ExecutionProfileName,
    ToolNetwork,
)


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
    root = make_root(fake_store, graph)
    policy = resolved_node(root, "review").execution_policy
    assert isinstance(policy, ExecutionPolicy)
    assert policy.name is ExecutionProfileName.REVIEWER
    assert not policy.writes
    assert policy.tool_network is ToolNetwork.NOT_ENFORCED


@pytest.mark.proc
@pytest.mark.parametrize("runner", ["codex", "claude"])
@pytest.mark.parametrize(
    "name", [ExecutionProfileName.WRITER, ExecutionProfileName.REVIEWER]
)
def test_named_launch_records_grants_and_network_fact(
    lab: Lab, runner: str, name: ExecutionProfileName
) -> None:
    """Both vendors launch both policies; receipts and status expose the same fact."""
    from workflow_interpreter.foreman.execution import execution_status
    from workflow_interpreter.profiles import RunnerName
    from workflow_interpreter.supervisor.models import LaunchReceipt
    from workflow_interpreter.supervisor.paths import read_record

    result = lab.run(
        RunnerName(runner),
        writes=name is ExecutionProfileName.WRITER,
        execution_profile=name,
    )
    activation_id = result.dispatch.activation.activation_id
    receipt = read_record(lab.paths.receipt(activation_id), LaunchReceipt)
    assert receipt is not None and receipt.execution_grants is not None
    grants = receipt.execution_grants
    expected = ToolNetwork.DENIED if runner == "codex" else ToolNetwork.NOT_ENFORCED
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
        if runner == "claude":
            allowed = receipt.argv[
                receipt.argv.index("--allowedTools") + 1 : receipt.argv.index(
                    "--disallowedTools"
                )
            ]
            assert "Bash" in allowed


def test_named_profile_refuses_sandbox_off(tmp_path: Path) -> None:
    """Named authority cannot be claimed without its physical outer bound."""
    from workflow_interpreter.profiles import RunnerName
    from workflow_interpreter.supervisor.errors import SandboxUnavailable
    from workflow_interpreter.supervisor.sandbox import SandboxMode

    lab = Lab(tmp_path, sandbox=SandboxMode.OFF)
    with pytest.raises(SandboxUnavailable, match="outer sandbox"):
        lab.run(RunnerName.CODEX, execution_profile=ExecutionProfileName.WRITER)


@pytest.mark.parametrize("runner", ["codex", "claude"])
@pytest.mark.parametrize(
    "name", [ExecutionProfileName.WRITER, ExecutionProfileName.REVIEWER]
)
def test_named_launch_and_resume_share_grants(
    tmp_path: Path, runner: str, name: ExecutionProfileName
) -> None:
    """Resuming changes the vendor verb, never the activation's authority."""
    from tests._profiles import make_supervisor_config, make_task, writable_roots_in
    from tests._supervisor import FrozenClock
    from workflow_interpreter.contracts.execution import policy_for
    from workflow_interpreter.profiles.claude import ClaudeProfile
    from workflow_interpreter.profiles.codex import CodexProfile
    from workflow_interpreter.profiles.config import ProfileConfig
    from workflow_interpreter.supervisor.execution import resolve_grants
    from workflow_interpreter.supervisor.sandbox import plan_for

    task = make_task(tmp_path, writes=name is ExecutionProfileName.WRITER)
    task = task.model_copy(
        update={
            "execution_profile": name,
            "execution_policy": policy_for(name, runner),
            "checkout_read_root": task.cwd,
        }
    )
    config = make_supervisor_config(tmp_path)
    plan = plan_for(
        task,
        repo_root=config.repo_root,
        wrapper_root=config.wrapper_root,
        channels_dir=Path(task.channels.outcome_file).parent,
    )
    grants = resolve_grants(task, plan, runner)
    task = task.model_copy(update={"execution_grants": grants})
    profile = (CodexProfile if runner == "codex" else ClaudeProfile)(
        ProfileConfig(), FrozenClock(), {}
    )
    session = "00000000-0000-4000-8000-000000000001"
    launch = profile.build_command(task, session)
    resume = profile.build_resume_command(session, "continue", task)
    assert launch.cwd == resume.cwd == grants.process_cwd
    if runner == "codex":
        assert writable_roots_in(launch.argv) == grants.writable_directories
        assert writable_roots_in(resume.argv) == grants.writable_directories
    else:
        assert (
            launch.argv[launch.argv.index("--tools") :]
            == (resume.argv[resume.argv.index("--tools") :])
        )


@pytest.mark.parametrize("escape", ["cache", "scratch", "channels"])
def test_named_reviewer_refuses_private_grant_escape(
    tmp_path: Path, escape: str
) -> None:
    """Checkout and wrapper records cannot become private writable roots."""
    from tests._profiles import make_supervisor_config, make_task
    from workflow_interpreter.contracts.execution import policy_for
    from workflow_interpreter.supervisor.errors import SandboxPathRefused
    from workflow_interpreter.supervisor.execution import resolve_grants
    from workflow_interpreter.supervisor.sandbox import plan_for

    task = make_task(tmp_path, writes=False)
    task = task.model_copy(
        update={
            "execution_profile": ExecutionProfileName.REVIEWER,
            "execution_policy": policy_for(ExecutionProfileName.REVIEWER, "codex"),
        }
    )
    config = make_supervisor_config(tmp_path)
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
        resolve_grants(task, plan, "codex")
