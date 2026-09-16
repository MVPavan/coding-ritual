"""An isolated app-server lab using only the versioned fake executable."""

import os
import re
import shutil
import sys
from pathlib import Path

from tests._bdio import load_definition
from tests._helpers import VALID_FIXTURE
from tests._profiles import task_builder
from tests._supervisor import (
    IMPLEMENT,
    commit_all,
    entry_mint,
    head_of,
    make_config,
    make_git,
    make_paths,
    make_repo,
    make_store,
    make_workspace,
    node_of,
    pinned_config,
)
from workflow_interpreter import load_graph
from workflow_interpreter.contracts.execution import ExecutionProfileName, policy_for
from workflow_interpreter.profiles.config import ProfileConfig, RunnerName
from workflow_interpreter.profiles.registry import ProfileRegistry
from workflow_interpreter.supervisor.channels import pinned_verifier_digests
from workflow_interpreter.supervisor.clock import SystemClock
from workflow_interpreter.supervisor.run import Supervisor
from workflow_interpreter.supervisor.sandbox import SandboxMode
from workflow_interpreter.supervisor.toolchain_models import ToolchainConfig

FIXTURE = Path(__file__).parent / "fixtures" / "codex_appserver" / "server.py"


class AppServerLab:
    """Drive the real wrapper with fake RPC and an in-memory bd transport."""

    def __init__(
        self,
        tmp_path: Path,
        mode: str = "complete",
        *,
        reuse: str | None = None,
        sandbox: SandboxMode = SandboxMode.OFF,
        named: ExecutionProfileName | None = None,
        toolchain: ToolchainConfig | None = None,
        project_files: Path | None = None,
    ) -> None:
        self.repo = make_repo(tmp_path)
        if project_files is not None:
            for name in ("uv.lock", "pyproject.toml"):
                shutil.copyfile(project_files / name, self.repo / name)
            commit_all(self.repo, "pinned toolchain fixture")
        self.config = make_config(self.repo, tmp_path, fake_proc=False, sandbox=sandbox)
        if toolchain is not None:
            self.config = self.config.model_copy(update={"toolchain": toolchain})
        self.fake_bd, self.store = make_store(tmp_path, head_of(self.repo))
        settings = tuple(
            item.model_copy(update={"value": "codex-appserver"})
            if item.key.endswith(".runner")
            else item
            for item in pinned_config(self.repo)
        )
        definition = load_definition()
        if reuse is not None or named is not None:
            graph = tmp_path / "appserver.toml"
            text = VALID_FIXTURE.read_text()
            authority = (
                f'execution_profile = "{named.value}"' if named else "writes = true"
            )
            if reuse is not None:
                authority += f'\nsession_reuse = "{reuse}"'
            text = re.sub(r"writes\s*=\s*true", authority, text, count=1)
            if named is ExecutionProfileName.REVIEWER:
                text = re.sub(
                    r"allowed_paths\s*=\s*\[[^\]]*\]",
                    "allowed_paths = []",
                    text,
                    count=1,
                )
            graph.write_text(text)
            definition = load_graph(graph)
        self.root = self.store.create_root(
            instance_key="appserver-test",
            instance_base_commit=head_of(self.repo),
            definition=definition,
            resolved_config=settings,
            profiles=ProfileRegistry(ProfileConfig(), SystemClock(), dict(os.environ)),
        )
        self.paths = make_paths(self.config, self.root.root_id)
        self.clock = SystemClock()
        self.git = make_git(self.config)
        self.workspace = make_workspace(self.paths, self.git, self.clock)
        self.supervisor = Supervisor(
            self.config,
            self.paths,
            self.git,
            self.store,
            self.workspace,
            self.clock,
            host_env=dict(os.environ),
        )
        binary = tmp_path / "fake-codex"
        binary.write_text(f"#!{sys.executable}\n" + FIXTURE.read_text())
        binary.chmod(0o700)
        env = {
            **os.environ,
            "WF_RPC_TEST_MODE": mode,
            "WF_RPC_TEST_CHECKOUT": str(self.paths.worktree),
        }
        config = ProfileConfig(
            binary_overrides={RunnerName.CODEX_APPSERVER: str(binary)},
            passthrough_env=(
                "PATH",
                "HOME",
                "WF_RPC_TEST_MODE",
                "WF_RPC_TEST_CHECKOUT",
            ),
        )
        self.profile = ProfileRegistry(config, self.clock, env).profile_for(
            "codex-appserver"
        )
        self.policy = policy_for(named, self.profile.tool_network) if named else None
        self.node = node_of(self.root.definition.document, IMPLEMENT).model_copy(
            update={
                "max_wall": "2s",
                "stale_after": "1s",
                **({"writes": self.policy.writes} if self.policy else {}),
            }
        )

    def run(self, request=None):
        """Dispatch, enforce runtime limits, collect channels, and run host checks."""
        return self.supervisor.run(
            request or entry_mint(runner_profile="codex-appserver", session_id=""),
            self.node,
            self.profile,
            task_builder(self.paths.worktree, self.node, execution_policy=self.policy),
            pinned_digests=pinned_verifier_digests(self.root),
        )
