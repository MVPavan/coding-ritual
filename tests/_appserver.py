"""An isolated app-server lab using only the versioned fake executable."""

import os
import sys
from pathlib import Path

from tests._bdio import load_definition
from tests._profiles import task_builder
from tests._supervisor import (
    IMPLEMENT,
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
from workflow_interpreter.profiles.config import ProfileConfig, RunnerName
from workflow_interpreter.profiles.registry import ProfileRegistry
from workflow_interpreter.supervisor.channels import pinned_verifier_digests
from workflow_interpreter.supervisor.clock import SystemClock
from workflow_interpreter.supervisor.run import Supervisor
from workflow_interpreter.supervisor.sandbox import SandboxMode

FIXTURE = Path(__file__).parent / "fixtures" / "codex_appserver" / "server.py"


class AppServerLab:
    """Drive the real wrapper with fake RPC and an in-memory bd transport."""

    def __init__(self, tmp_path: Path, mode: str = "complete") -> None:
        self.repo = make_repo(tmp_path)
        self.config = make_config(
            self.repo, tmp_path, fake_proc=False, sandbox=SandboxMode.OFF
        )
        self.fake_bd, self.store = make_store(tmp_path, head_of(self.repo))
        settings = tuple(
            item.model_copy(update={"value": "codex-appserver"})
            if item.key.endswith(".runner")
            else item
            for item in pinned_config(self.repo)
        )
        self.root = self.store.create_root(
            instance_key="appserver-test",
            definition=load_definition(),
            resolved_config=settings,
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
        env = {**os.environ, "WF_RPC_TEST_MODE": mode}
        config = ProfileConfig(
            binary_overrides={RunnerName.CODEX_APPSERVER: str(binary)},
            passthrough_env=("PATH", "HOME", "WF_RPC_TEST_MODE"),
        )
        self.profile = ProfileRegistry(config, self.clock, env).profile_for(
            "codex-appserver"
        )
        self.node = node_of(self.root.definition.document, IMPLEMENT).model_copy(
            update={"max_wall": "2s", "stale_after": "1s"}
        )

    def run(self):
        """Dispatch, enforce runtime limits, collect channels, and run host checks."""
        return self.supervisor.run(
            entry_mint(runner_profile="codex-appserver", session_id=""),
            self.node,
            self.profile,
            task_builder(self.paths.worktree, self.node),
            pinned_digests=pinned_verifier_digests(self.root),
        )
