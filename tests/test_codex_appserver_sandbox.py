"""No-model physical proof that vendor state is writable only outside tool sandboxes."""

import json
import os
import selectors
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from tests._appserver import AppServerLab
from tests._profiles import writable_roots_in
from tests._supervisor import FrozenClock
from tests.test_codex_writer_qualification import (
    ALLOWED,
    CODEX,
    DENIED,
    GRANTED_FILE,
    PROBE_TIMEOUT_S,
    _lab,
    _permission_config,
    _write_probe,
)
from workflow_interpreter.contracts.execution import ExecutionProfileName, policy_for
from workflow_interpreter.profiles.codex import CodexProfile
from workflow_interpreter.profiles.codex_appserver import CodexAppServerProfile
from workflow_interpreter.profiles.config import ProfileConfig
from workflow_interpreter.supervisor.execution import resolve_grants
from workflow_interpreter.supervisor.fork_launcher import ForkBarrierLauncher
from workflow_interpreter.supervisor.launch_record import LaunchReceipt
from workflow_interpreter.supervisor.paths import read_record
from workflow_interpreter.supervisor.rpc_session import RpcSession
from workflow_interpreter.supervisor.sandbox import SandboxMode, plan_for, wrap

pytest_plugins = ("tests.test_toolchain_seeding",)


@pytest.mark.proc
@pytest.mark.parametrize("writes", [False, True])
def test_vendor_state_is_read_only_to_tools_and_reviewer_checkout_stays_read_only(
    tmp_path, writes
):
    """The server retains history, but a tool command cannot rewrite it."""
    assert shutil.which(CODEX)
    assert shutil.which("bwrap")
    task, plan = _lab(tmp_path, writes=writes)
    state = Path(task.channels.outcome_file).parent.parent / "vendor-state"
    state.mkdir(mode=0o700)
    profile = CodexAppServerProfile(ProfileConfig(), FrozenClock(), dict(os.environ))
    name = ExecutionProfileName.WRITER if writes else ExecutionProfileName.REVIEWER
    task = task.model_copy(
        update={
            "execution_profile": name,
            "execution_policy": policy_for(name, profile.tool_network),
            "checkout_read_root": task.cwd,
            "toolchain_cache": str(plan.toolchain_cache[0]),
            "vendor_state": str(state),
        }
    )
    grants = resolve_grants(task, plan, profile)
    task = task.model_copy(update={"execution_grants": grants})
    plan = plan.model_copy(update={"vendor_state": (state,)})
    command = profile.build_command(task, "")
    assert str(state) not in writable_roots_in(command.argv)
    script = "\n".join(
        (
            _write_probe(state / "history", "history"),
            _write_probe(Path(task.channels.artifact_dir) / "findings", "report"),
            _write_probe(Path(task.cwd) / GRANTED_FILE, "source"),
        )
    )
    inner = (
        CODEX,
        "sandbox",
        *_permission_config(command.argv),
        "--",
        "sh",
        "-c",
        script,
    )
    result = subprocess.run(
        wrap(inner, plan),
        cwd=command.cwd,
        env={**os.environ, **command.env},
        capture_output=True,
        text=True,
        timeout=PROBE_TIMEOUT_S,
        check=False,
    )
    observed = result.stdout + result.stderr
    assert f"{DENIED}:history" in observed, observed
    assert f"{ALLOWED}:report" in observed, observed
    expected = ALLOWED if writes else DENIED
    assert f"{expected}:source" in observed, observed
    outer = subprocess.run(
        wrap(("sh", "-c", _write_probe(state / "history", "history")), plan),
        cwd=command.cwd,
        env={**os.environ, **command.env},
        capture_output=True,
        text=True,
        timeout=PROBE_TIMEOUT_S,
        check=False,
    )
    assert f"{ALLOWED}:history" in outer.stdout, outer.stderr


@pytest.mark.proc
@pytest.mark.parametrize("writes", [False, True])
def test_dispatch_fixture_under_bwrap_with_seeded_private_toolchain(
    tmp_path, writes, seed_lab, monkeypatch
):
    """Real dispatch preserves exec grants, private seeded tools, and reviewer RO."""

    name = ExecutionProfileName.WRITER if writes else ExecutionProfileName.REVIEWER
    lab = AppServerLab(
        tmp_path,
        "sandbox-probe",
        sandbox=SandboxMode.BWRAP,
        named=name,
        toolchain=seed_lab.config.toolchain,
        project_files=seed_lab.repo,
    )
    plans, tasks = [], []
    launcher_init = ForkBarrierLauncher.__init__
    session_init = RpcSession.__init__

    def launcher(self, *args, **kwargs):
        plans.append(kwargs["plan"])
        launcher_init(self, *args, **kwargs)

    def session(self, *args):
        tasks.append(args[-2])
        session_init(self, *args)

    monkeypatch.setattr(ForkBarrierLauncher, "__init__", launcher)
    monkeypatch.setattr(RpcSession, "__init__", session)
    result = lab.run()
    aid = result.dispatch.activation.activation_id
    task, plan = tasks[0], plans[0]
    receipt = read_record(lab.paths.receipt(aid), LaunchReceipt)
    assert receipt.sandbox is SandboxMode.BWRAP
    assert receipt.seed_receipts
    assert task.cwd == receipt.cwd == task.execution_grants.process_cwd
    exec_profile = CodexProfile(ProfileConfig(), FrozenClock(), dict(os.environ))
    exec_grants = resolve_grants(
        task, plan.model_copy(update={"vendor_state": ()}), exec_profile
    )
    assert task.execution_grants == exec_grants
    assert writable_roots_in(lab.profile.build_command(task, "").argv) == (
        writable_roots_in(exec_profile.build_command(task, "").argv)
    )
    exec_plan = plan_for(
        task.model_copy(update={"execution_grants": None, "vendor_state": None}),
        repo_root=lab.config.repo_root,
        wrapper_root=lab.config.wrapper_root,
        channels_dir=lab.paths.channels_dir(aid),
        binary=plan.binary,
    )
    write_fields = ("grants", "git_rw", "channels", "toolchain_cache", "vendor_state")
    actual = {path for field in write_fields for path in getattr(plan, field)}
    expected = {path for field in write_fields for path in getattr(exec_plan, field)}
    assert actual == expected | {Path(task.vendor_state)}
    assert plan.vendor_state == (Path(task.vendor_state),)
    assert str(plan.vendor_state[0]) not in task.execution_grants.writable_directories
    evidence = json.loads(
        (Path(task.channels.artifact_dir) / "sandbox-probe.json").read_text()
    )
    assert evidence == {
        "cache_seeded": True,
        "cache_writable": True,
        "checkout_writable": writes,
        "cwd": task.cwd,
    }


@pytest.mark.proc
def test_real_appserver_suppresses_project_config_without_a_model_call(tmp_path):
    """The installed pinned binary ignores project MCP/config/rules in a private home."""
    task, _ = _lab(tmp_path, writes=True)
    project = Path(task.cwd) / ".codex"
    (project / "rules").mkdir(parents=True)
    (project / "config.toml").write_text(
        'model="candidate-model"\n[mcp_servers.candidate]\ncommand="must-not-run"\n'
    )
    (project / "rules" / "candidate.rules").write_text("invalid execpolicy syntax!!!")
    state = tmp_path / "private-codex-home"
    state.mkdir()
    task = task.model_copy(update={"vendor_state": str(state)})
    profile = CodexAppServerProfile(ProfileConfig(), FrozenClock(), dict(os.environ))
    command = profile.build_command(task, "")
    process = subprocess.Popen(
        command.argv,
        cwd=command.cwd,
        env=command.env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    try:
        for message in (
            {
                "id": 1,
                "method": "initialize",
                "params": {"clientInfo": {"name": "config-probe", "version": "1"}},
            },
            {"method": "initialized"},
            {
                "id": 2,
                "method": "config/read",
                "params": {"cwd": task.cwd, "includeLayers": True},
            },
        ):
            process.stdin.write(json.dumps(message).encode() + b"\n")
        process.stdin.flush()
        buffer = b""
        result = None
        deadline = time.monotonic() + 5
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while result is None and time.monotonic() < deadline:
                if not selector.select(0.1):
                    continue
                chunk = os.read(process.stdout.fileno(), 65536)
                assert chunk, "app-server exited before configuration response"
                buffer += chunk
                assert len(buffer) < 262144
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    frame = json.loads(line)
                    if frame.get("id") == 2:
                        result = frame["result"]
        assert result is not None
        assert result["config"]["model"] != "candidate-model"
        assert "candidate" not in result["config"]["mcp_servers"]
        assert result["config"]["web_search"] == "disabled"
        for feature in (
            "apps",
            "browser_use",
            "browser_use_external",
            "computer_use",
            "image_generation",
            "multi_agent",
            "multi_agent_v2",
            "plugins",
            "remote_plugin",
            "skill_mcp_dependency_install",
            "tool_suggest",
        ):
            assert result["config"]["features"][feature] is False
        layers = [
            layer for layer in result["layers"] if layer["name"]["type"] == "project"
        ]
        assert layers and all(layer.get("disabledReason") for layer in layers)
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
        process.stdout.close()
