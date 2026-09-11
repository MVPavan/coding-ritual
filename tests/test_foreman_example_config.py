"""The shipped example config must render into a config the foreman loads.

`ForemanConfig` requires absolute `repo_root`/`wrapper_home` and a
`supervisor.wrapper_root` equal to the hash-derived one, so a live config is
machine-specific and cannot be checked in. The example plus its generator are
therefore the artefact under test: rendering it here is the only thing that
proves the pair stays in step with the model.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from tests._helpers import AUTHORING_FIXTURE, BUILD_LOOP_GRAPH, runner_roles
from tests._supervisor import make_repo
from workflow_interpreter import load_graph
from workflow_interpreter.foreman.config import load_config

GENERATOR = (
    Path(__file__).resolve().parent.parent / "scripts" / "make-foreman-config.sh"
)
RENDER_TIMEOUT_S = 30.0

# Every graph `foreman create` may be pointed at. `instantiate` refuses one
# whose roles are not all bound ("unknown runner roles", `resolve.py:218`), so
# an example config that misses a role makes the graph uninstantiable.
LIVE_GRAPHS = (AUTHORING_FIXTURE, BUILD_LOOP_GRAPH)


def test_the_example_config_renders_into_a_loadable_foreman_config(
    tmp_path: Path,
) -> None:
    """The generator's output loads, and binds each graph role to a profile."""
    repo = make_repo(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    rendered = tmp_path / "foreman.toml"

    subprocess.run(
        [str(GENERATOR), str(rendered)],
        cwd=repo,
        check=True,
        capture_output=True,
        timeout=RENDER_TIMEOUT_S,
        env={"HOME": str(home), "PATH": os.environ["PATH"], "USER": "tester"},
    )
    config = load_config(rendered)

    assert config.repo_root == repo.resolve()
    assert config.wrapper_home == home / ".wf"
    assert config.wrapper_home.is_dir()
    assert config.supervisor.wrapper_root == config.wrapper_root
    assert config.actor == "wf-tester"
    assert config.bridge_graph == repo / "workflows" / "feature-delivery.toml"
    # feature-delivery names its two runner roles `implementer` and `critic`
    # (`runner = "profile:<role>"`); the reviewer role is the critic one.
    assert config.roles["implementer"].profile == "claude"
    assert config.roles["critic"].profile == "codex"
    assert config.roles["implementer"].model == "claude-opus-5"
    assert config.roles["implementer"].effort == "high"
    assert config.roles["critic"].model == "gpt-5.6-sol"
    assert config.roles["critic"].effort == "high"
    assert config.signing is not None
    # §9: a foreman that can write its own allow-list can forge approvals.
    assert not config.signing.allowed_signers_path.is_relative_to(config.bd.workspace)
    # build-loop adds `test-author`, `test-critic` and `impl-critic`; writers
    # go to claude because a codex sandbox cannot commit (phase 6 D5).
    assert config.roles["test-author"].profile == "claude"
    assert config.roles["test-critic"].profile == "codex"
    assert config.roles["impl-critic"].profile == "codex"
    assert config.roles["test-author"].model == "claude-opus-5"
    assert config.roles["test-author"].effort == "high"
    for role in ("test-critic", "impl-critic"):
        assert config.roles[role].model == "gpt-5.6-sol"
        assert config.roles[role].effort == "high"
    for graph_path in LIVE_GRAPHS:
        assert not runner_roles(load_graph(graph_path)) - set(config.roles)
