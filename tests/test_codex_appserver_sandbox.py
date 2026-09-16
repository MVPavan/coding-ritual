"""No-model physical proof that vendor state is writable only outside tool sandboxes."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

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
from workflow_interpreter.profiles.codex_appserver import CodexAppServerProfile
from workflow_interpreter.profiles.config import ProfileConfig
from workflow_interpreter.supervisor.execution import resolve_grants
from workflow_interpreter.supervisor.sandbox import wrap


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
