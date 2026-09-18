"""The exercised protocol fixtures must match the installed versioned generator."""

import hashlib
import json
import shutil
import subprocess

import jsonschema
import pytest

from tests._appserver import FIXTURE, AppServerLab
from tests._inspector import entry_mint
from workflow_interpreter.bdio import MintReason
from workflow_interpreter.inspector.paths import write_record
from workflow_interpreter.inspector.rpc_control import INTERRUPT_FILE
from workflow_interpreter.inspector.rpc_session import RpcSession, SessionPhase
from workflow_interpreter.inspector.steer import Steerer
from workflow_interpreter.profiles.codex_rpc import RpcClient, RpcMethod
from workflow_interpreter.schema.models import Outcome


def test_committed_schemas_match_installed_generator(tmp_path):
    """Never project or hand-edit schemas; absence is the sole allowed skip."""
    binary = shutil.which("codex")
    if binary is None:
        pytest.skip("codex binary absent; cannot compare generated protocol schemas")
    version = subprocess.run(
        [binary, "--version"], capture_output=True, text=True, timeout=5, check=True
    )
    assert version.stdout.strip() == "codex-cli 0.154.0"
    target = tmp_path / "generated"
    subprocess.run(
        [binary, "app-server", "generate-json-schema", "--out", str(target)],
        capture_output=True,
        timeout=30,
        check=True,
    )
    provenance = json.loads((FIXTURE.parent / "provenance.json").read_text())
    assert set(provenance["schemas"]) == {
        path.name for path in FIXTURE.parent.glob("*.json")
    } - {"provenance.json"}
    for name, record in provenance["schemas"].items():
        assert (FIXTURE.parent / name).read_bytes() == (
            target / record["source"]
        ).read_bytes(), name
        assert (
            hashlib.sha256((FIXTURE.parent / name).read_bytes()).hexdigest()
            == record["sha256"]
        )


def closed_objects(schema):
    """Forbid undeclared fields without closing explicitly free-form config maps."""
    if isinstance(schema, list):
        return [closed_objects(value) for value in schema]
    if not isinstance(schema, dict):
        return schema
    result = {key: closed_objects(value) for key, value in schema.items()}
    if "properties" in result:
        result.setdefault("additionalProperties", False)
    return result


@pytest.mark.parametrize("scenario", ["fresh", "resume", "steer", "interrupt"])
def test_every_session_request_uses_only_generated_fields(
    tmp_path, monkeypatch, scenario
):
    """Exercise all six session requests with strict generated property sets."""
    names = {
        RpcMethod.INITIALIZE: "InitializeParams.json",
        RpcMethod.THREAD_START: "ThreadStartParams.json",
        RpcMethod.THREAD_RESUME: "ThreadResumeParams.json",
        RpcMethod.TURN_START: "TurnStartParams.json",
        RpcMethod.TURN_STEER: "TurnSteerParams.json",
        RpcMethod.TURN_INTERRUPT: "TurnInterruptParams.json",
    }
    seen = set()
    request = RpcClient.request

    def checked(client, method, params):
        schema = closed_objects(
            json.loads((FIXTURE.parent / names[method]).read_text())
        )
        jsonschema.validate(params, schema)
        if method in (RpcMethod.THREAD_START, RpcMethod.THREAD_RESUME):
            assert params["config"]["features.apps"] is False
            assert params["config"]["features.plugins"] is False
            assert params["config"]["features.multi_agent"] is False
            assert params["config"]["web_search"] == "disabled"
            assert params["config"]["mcp_servers"] == {}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({**params, "undeclaredField": True}, schema)
        seen.add(method)
        return request(client, method, params)

    monkeypatch.setattr(RpcClient, "request", checked)
    controlled = scenario in ("steer", "interrupt")
    lab = AppServerLab(
        tmp_path, "wait-control" if controlled else "complete", reuse="same-node"
    )
    original = RpcSession._frame
    submitted = []

    def frame(session, client, message):
        original(session, client, message)
        if controlled and session._phase is SessionPhase.ACTIVE and not submitted:
            activation = lab.store.reads.load_activation(session._task.activation_id)
            submitted.append(activation.activation_id)
            if scenario == "steer":
                Steerer(lab.config, lab.paths, lab.store, lab.clock).in_place(
                    activation, reason="schema check", instructions="Continue safely."
                )
            else:
                write_record(
                    lab.paths.activation_dir(activation.activation_id) / INTERRUPT_FILE,
                    activation.metadata.session_registration,
                )

    monkeypatch.setattr(RpcSession, "_frame", frame)
    first = lab.run()
    expected = {RpcMethod.INITIALIZE, RpcMethod.THREAD_START, RpcMethod.TURN_START}
    if scenario == "resume":
        aid = first.dispatch.activation.activation_id
        lab.store.close_activation(aid, Outcome.FAIL_CODE)
        lab.run(
            entry_mint(crew_profile="codex-appserver", session_id="").model_copy(
                update={
                    "mint_reason": MintReason.EDGE,
                    "predecessor_activation_id": aid,
                }
            )
        )
        expected.add(RpcMethod.THREAD_RESUME)
    elif controlled:
        expected.add(
            RpcMethod.TURN_STEER if scenario == "steer" else RpcMethod.TURN_INTERRUPT
        )
    assert seen == expected
