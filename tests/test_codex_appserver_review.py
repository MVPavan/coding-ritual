"""Regression cases for reviewed app-server completion and admission boundaries."""

import hashlib
import json
import os
import tomllib
from pathlib import Path

import pytest

from tests._appserver import AppServerLab
from tests._inspector import FrozenClock
from tests.test_codex_writer_qualification import _lab
from workflow_interpreter.contracts.execution import ExecutionProfileName
from workflow_interpreter.inspector import rpc_session
from workflow_interpreter.inspector.exit import ComputedEvidence, ExitObserver
from workflow_interpreter.inspector.launch_record import LaunchReceipt
from workflow_interpreter.inspector.sandbox import SandboxMode
from workflow_interpreter.profiles.codex_appserver import CodexAppServerProfile
from workflow_interpreter.profiles.config import ProfileConfig
from workflow_interpreter.profiles.errors import TaskRefused
from workflow_interpreter.schema.models import Outcome


def test_checkout_codex_configuration_does_not_refuse_a_launch(tmp_path):
    """Tracked project config and rules are suppressed, never post-mint refusals."""
    task, _ = _lab(tmp_path, writes=True)
    checkout = Path(task.cwd)
    config = checkout / ".codex"
    (config / "rules").mkdir(parents=True)
    (config / "config.toml").write_text('model="untrusted-model"\n')
    (config / "rules" / "permit.rules").write_text("invalid rule syntax!!!")
    state = tmp_path / "private-home"
    state.mkdir()
    profile = CodexAppServerProfile(ProfileConfig(), FrozenClock(), dict(os.environ))
    task = task.model_copy(update={"vendor_state": str(state)})
    command = profile.build_command(task, "")
    assert command.env["CODEX_HOME"] == str(state)
    assert any(word.startswith("projects=") for word in command.argv)


def test_missing_transport_cannot_certify_appserver_completion(tmp_path):
    """Legacy receipt defaults cannot bypass the mandatory RPC completion proof."""
    lab = AppServerLab(tmp_path)
    result = lab.run()
    aid = result.dispatch.activation.activation_id
    receipt = lab.paths.receipt(aid)
    data = json.loads(receipt.read_text())
    del data["transport"]
    receipt.write_text(json.dumps(data))
    (receipt.parent / "session.json").unlink()
    (receipt.parent / "turn.json").unlink()
    observer = ExitObserver(
        lab.config, lab.paths, lab.git, lab.store, lab.workspace, lab.clock
    )
    graded = observer._with_sandbox_verdict(
        aid, ComputedEvidence(completion=result.observation.completion)
    )
    assert graded.outcome is Outcome.ERROR_TRANSPORT


def test_repeated_completion_does_not_extend_shutdown_deadline(tmp_path, monkeypatch):
    """Only the first valid completion starts the bounded shutdown interval."""
    original = rpc_session.RpcSession._completed
    deadlines = []

    def completed(session, completion):
        original(session, completion)
        first = session._shutdown_at
        original(session, completion)
        deadlines.append((first, session._shutdown_at))

    monkeypatch.setattr(rpc_session.RpcSession, "_completed", completed)
    AppServerLab(tmp_path).run()
    assert deadlines and all(first == second for first, second in deadlines)


def test_registration_records_a_sha256_policy_digest(tmp_path):
    """Session compatibility stores a digest, not the policy body under a false name."""

    lab = AppServerLab(tmp_path)
    result = lab.run()
    registration = lab.store.reads.load_activation(
        result.dispatch.activation.activation_id
    ).metadata.session_registration
    assert registration.policy_digest == hashlib.sha256(b"legacy").hexdigest()


def test_rpc_command_cwd_cannot_drift_from_resolved_grants(tmp_path, monkeypatch):
    """A profile cannot retarget the already planned checkout with a late cwd rewrite."""

    lab = AppServerLab(
        tmp_path, sandbox=SandboxMode.BWRAP, named=ExecutionProfileName.WRITER
    )
    build = lab.profile.build_command
    monkeypatch.setattr(
        lab.profile,
        "build_command",
        lambda task, sid: build(task, sid).model_copy(update={"cwd": str(lab.repo)}),
    )
    with pytest.raises(TaskRefused, match="cwd"):
        lab.run()
    assert not tuple(lab.paths.instance_dir.glob("*/exec-ledger.jsonl"))


def test_launch_receipt_explicitly_forbids_arbitrary_types():
    """Durable records retain the explicit schema-only model configuration."""

    assert LaunchReceipt.model_config["arbitrary_types_allowed"] is False


@pytest.mark.parametrize(
    "named", [ExecutionProfileName.WRITER, ExecutionProfileName.REVIEWER]
)
def test_dispatch_asks_profile_for_cwd_before_preparing_session(
    tmp_path, monkeypatch, named
):
    """The profile owns cwd selection before the inspector freezes the mount plan."""
    lab = AppServerLab(tmp_path, named=named, sandbox=SandboxMode.BWRAP)
    root = lab.profile._workspace_root
    prepare = lab.profile.prepare
    selected = []

    def workspace(task):
        result = root(task)
        selected.append(result)
        return result

    def prepared(activation):
        assert selected, "the launch plan re-derived cwd without asking its profile"
        return prepare(activation)

    monkeypatch.setattr(lab.profile, "_workspace_root", workspace)
    monkeypatch.setattr(lab.profile, "prepare", prepared)
    lab.run()


def test_all_distinct_project_lookup_roots_are_explicitly_untrusted(tmp_path):
    """Config lookup at process cwd or vendor-state parent cannot restore authority."""
    task, _ = _lab(tmp_path, writes=False)
    checkout = task.cwd
    cwd = tmp_path / "process-cwd"
    cwd.mkdir()
    state = tmp_path / "private-state" / "vendor"
    state.mkdir(parents=True)
    task = task.model_copy(
        update={
            "checkout_read_root": checkout,
            "cwd": str(cwd),
            "vendor_state": str(state),
        }
    )
    profile = CodexAppServerProfile(ProfileConfig(), FrozenClock(), dict(os.environ))
    command = profile.build_command(task, "")
    projects = tomllib.loads(
        next(word for word in command.argv if word.startswith("projects="))
    )["projects"]
    assert set(projects) == {checkout, str(cwd), command.cwd, str(state.parent)}
    assert all(value == {"trust_level": "untrusted"} for value in projects.values())
