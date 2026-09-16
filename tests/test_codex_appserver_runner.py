"""One fixture turn per launch, with protected identity before model submission."""

import json

import pytest

from tests._appserver import AppServerLab
from workflow_interpreter.bdio.rpc_records import SessionRegistration
from workflow_interpreter.schema.models import Outcome
from workflow_interpreter.supervisor.paths import read_record


def test_registered_thread_precedes_turn_and_success_requires_completion(
    tmp_path, monkeypatch
):
    """The fake server refuses turn/start unless protected registration exists."""
    lab = AppServerLab(tmp_path)
    register = lab.store.register_session
    observed = []

    def checked(activation_id, registration):
        path = lab.paths.activation_dir(activation_id)
        assert read_record(path / "session.json", SessionRegistration) == registration
        requests = (path / "channels" / "artifacts" / "requests.jsonl").read_text()
        assert '"turn/start"' not in requests
        observed.append(registration.thread_id)
        return register(activation_id, registration)

    monkeypatch.setattr(lab.store, "register_session", checked)
    result = lab.run()
    assert observed == ["thread-1"]
    assert result.observation.completion.outcome is Outcome.NO_DIFF
    activation = lab.store.reads.load_activation(
        result.dispatch.activation.activation_id
    )
    assert activation.metadata.session_id == "thread-1"
    assert activation.metadata.handle.session_id == ""
    again = lab.run()
    assert again.dispatch.exec_count == 1
    assert again.observation is None


@pytest.mark.parametrize(
    "mode",
    [
        "exit-without-turn",
        "turn-failed",
        "wrong-thread",
        "wrong-policy",
        "wrong-home",
        "wrong-turn",
        "unknown-after-start",
        "hang-request",
        "hang-shutdown",
    ],
)
def test_incomplete_or_invalid_turn_never_grades_success(tmp_path, mode):
    """Server exit, bogus identity, and stuck RPC cannot manufacture completion."""
    lab = AppServerLab(tmp_path, mode)
    result = lab.run()
    assert result.observation.completion.outcome is Outcome.ERROR_TRANSPORT
    path = lab.paths.activation_dir(result.dispatch.activation.activation_id)
    assert json.loads((path / "turn.json").read_text())["error"]


def test_wrong_version_is_refused_before_vendor_exec(tmp_path):
    """The experimental transport does not silently run a different protocol."""
    from workflow_interpreter.profiles.errors import TaskRefused

    lab = AppServerLab(tmp_path, "wrong-version")
    with pytest.raises(TaskRefused, match="0.154.0"):
        lab.run()
    assert not tuple(lab.paths.instance_dir.glob("*/exec-ledger.jsonl"))


@pytest.mark.parametrize("corrupt", [False, True])
def test_missing_or_corrupt_launch_evidence_cannot_grade_rpc_success(tmp_path, corrupt):
    """RPC evidence is mandatory even when normal outcome files claim success."""
    from workflow_interpreter.supervisor.exit import ComputedEvidence, ExitObserver

    lab = AppServerLab(tmp_path)
    result = lab.run()
    activation_id = result.dispatch.activation.activation_id
    receipt = lab.paths.receipt(activation_id)
    if corrupt:
        receipt.write_text("broken")
    else:
        receipt.unlink()
    observer = ExitObserver(
        lab.config, lab.paths, lab.git, lab.store, lab.workspace, lab.clock
    )
    completion = observer._with_sandbox_verdict(
        activation_id,
        ComputedEvidence(completion=result.observation.completion),
    )
    assert completion.outcome is Outcome.ERROR_TRANSPORT


@pytest.mark.parametrize("fail_at", ["registration", "intent"])
def test_failure_before_turn_submission_never_sends_a_turn(
    tmp_path, monkeypatch, fail_at
):
    """Neither protected evidence nor its bd mirror can be skipped to start work."""
    from workflow_interpreter.supervisor import rpc_session

    lab = AppServerLab(tmp_path)
    original = rpc_session.write_record

    def fail_registration(*args):
        raise OSError("registration unavailable")

    def fail_intent(path, value):
        if path.name == "turn.json" and value.phase.value == "intent":
            raise OSError("intent unavailable")
        original(path, value)

    if fail_at == "registration":
        monkeypatch.setattr(lab.store, "register_session", fail_registration)
    else:
        monkeypatch.setattr(rpc_session, "write_record", fail_intent)
    result = lab.run()
    aid = result.dispatch.activation.activation_id
    requests = (
        (lab.paths.activation_dir(aid) / "channels" / "artifacts") / "requests.jsonl"
    ).read_text()
    assert '"turn/start"' not in requests
    assert result.observation.completion.outcome is Outcome.ERROR_TRANSPORT


def test_exercised_messages_match_versioned_schema_subset(tmp_path):
    """The committed fixture uses actual generated 0.154.0 field shapes."""
    import jsonschema

    from tests._appserver import FIXTURE

    lab = AppServerLab(tmp_path)
    result = lab.run()
    artifacts = (
        lab.paths.activation_dir(result.dispatch.activation.activation_id)
        / "channels"
        / "artifacts"
    )
    requests = [
        json.loads(line)
        for line in (artifacts / "requests.jsonl").read_text().splitlines()
    ]
    responses = [
        json.loads(line)
        for line in (artifacts / "responses.jsonl").read_text().splitlines()
    ]
    names = {
        "initialize": "Initialize",
        "thread/start": "ThreadStart",
        "turn/start": "TurnStart",
    }
    for request in requests:
        if request["method"] not in names:
            continue
        name = names[request["method"]]
        jsonschema.validate(
            request["params"],
            json.loads((FIXTURE.parent / f"{name}Params.json").read_text()),
        )
        reply = next(item for item in responses if item.get("id") == request["id"])
        jsonschema.validate(
            reply["result"],
            json.loads((FIXTURE.parent / f"{name}Response.json").read_text()),
        )
    completed = next(
        item for item in responses if item.get("method") == "turn/completed"
    )
    jsonschema.validate(
        completed["params"],
        json.loads((FIXTURE.parent / "TurnCompletedNotification.json").read_text()),
    )
