"""C2b CLI entrypoint and stale-tail integration contracts."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any, NoReturn, cast

import pytest

from tests._bdio import entry_request as bdio_entry_request
from tests._bdio import handle, load_definition, make_root
from tests._foreman import ForemanLab
from tests._foreman import entry_request as foreman_entry_request
from tests._helpers import (
    AMBIGUOUS_ABANDON_EDITS,
    BUILD_LOOP_GRAPH,
    VALID_FIXTURE,
    mutate,
    unnameable_abandon_graph,
)
from tests._supervisor import VERIFY_SCRIPT, ChildScript, make_config, make_repo
from tests.conftest import Signer
from workflow_interpreter.bdio import BdConfig, BdOutputError, Outcome, Usage
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.client import STATUS_CLOSED, BdClient
from workflow_interpreter.bdio.config import SigningConfig
from workflow_interpreter.bridge import (
    PhaseAdapter,
    PhaseAdapterError,
    PhaseBridgeRecord,
    RetryRefusal,
)
from workflow_interpreter.bridge import command as bridge_command_module
from workflow_interpreter.bridge import gate_view as gate_view_module
from workflow_interpreter.foreman import __main__ as main_module
from workflow_interpreter.foreman.compose import Composition, ProfileResolver, Spawner
from workflow_interpreter.foreman.config import ForemanConfig
from workflow_interpreter.foreman.constants import MAX_TRANSCRIPT_BYTES
from workflow_interpreter.foreman.gates import halt_gate
from workflow_interpreter.foreman.supervise import WrapperExit, run_wrapper
from workflow_interpreter.foreman.tick import Foreman, RunReport, TickReport
from workflow_interpreter.supervisor.clock import Clock
from workflow_interpreter.supervisor.errors import PreconditionRefused
from workflow_interpreter.supervisor.gitio import Git


def _created_root_id(transcript: str) -> str:
    """Take `create`'s one stdout line out of a merged stdout+stderr capture.

    `main` writes the whole captured stdout before the captured stderr, and
    `create` writes nothing to stdout but the root id, so the id leads the
    transcript — the log lines that follow it are stderr's (cr-o85.34.15).
    """
    return transcript.strip().splitlines()[0]


def test_module_entrypoint_is_spawnable() -> None:
    """The detached spawner's exact module command reaches its config gate."""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "workflow_interpreter.foreman",
            "supervise",
            "root-id",
            "activation-id",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "--config" in completed.stderr


def test_lab_transcript_captures_the_entrypoint_stream(tmp_path: Path) -> None:
    """Transcript assertions inspect emitted bytes, never a command return code."""
    lab = ForemanLab(tmp_path)

    def emit() -> int:
        print("stdout marker")
        print("stderr marker", file=sys.stderr)
        return 0

    byte_count, text = lab.transcript(emit)

    assert text == "stdout marker\nstderr marker\n"
    assert byte_count == len(text.encode("utf-8"))


@pytest.mark.acceptance
def test_audit_20_keeps_clean_runner_log_bytes_out_of_every_transcript(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AUDIT-20 catches a clean foreman command that reads a runner log."""
    sentinel = "audit-20-50da3ef2-runner-log"
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    lab.profiles.next_script(
        ChildScript(
            emit=sentinel,
            marker='{"outcome":"done"}\n',
            effects='{"paths":["src/feature.py"]}',
            write_path="src/feature.py",
            write_body="value = 3\n",
            commit=True,
        )
    )
    activation_id = lab.tick().dispatched
    assert activation_id is not None
    assert lab.tick().settled == activation_id
    log_path = lab.wiring().paths.log(activation_id)
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    calls = 0
    path_type = type(log_path)
    original_open: Callable[..., Any] = path_type.open

    def track_open(path: Path, *args: object, **kwargs: object) -> Any:
        nonlocal calls
        if path == log_path:
            calls += 1
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(path_type, "open", track_open)
    captures = (
        lab.transcript(lambda: main_module.main(["tick", root.root_id])),
        lab.transcript(lambda: main_module.main(["status", root.root_id])),
        lab.transcript(
            lambda: main_module.main(["inspect", root.root_id, activation_id])
        ),
    )

    assert all(byte_count <= MAX_TRANSCRIPT_BYTES for byte_count, _ in captures)
    assert all(sentinel not in transcript for _, transcript in captures)
    assert calls == 0
    assert any("verify" in transcript for _, transcript in captures)


def test_emit_truncates_an_escaped_tail_without_dropping_its_report(
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    """ANSI JSON escaping may shorten the tail, but never removes the report."""
    main_module._emit(
        json.dumps(
            {
                "tail": "\x1b" * MAX_TRANSCRIPT_BYTES,
                "tail_bytes": MAX_TRANSCRIPT_BYTES,
                "continuation": "wf-continuation",
            }
        ),
        limit=MAX_TRANSCRIPT_BYTES,
    )

    rendered = capsysbinary.readouterr().out

    assert len(rendered) <= MAX_TRANSCRIPT_BYTES
    report = json.loads(rendered)
    assert report["continuation"] == "wf-continuation"
    assert report["tail"] != ""


def test_main_caps_a_configuration_failure_on_the_combined_transcript(
    tmp_path: Path,
) -> None:
    """Configuration errors do not escape as an unbounded interpreter traceback."""
    lab = ForemanLab(tmp_path)

    byte_count, text = lab.transcript(lambda: main_module.main(["tick", "wf-root"]))

    assert byte_count <= MAX_TRANSCRIPT_BYTES
    assert "foreman configuration path is required" in text


def test_main_inspect_keeps_a_bounded_escaped_tail_inside_its_extra_allowance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inspect gets the tail allowance and retains its JSON report under it."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring()
        .store.mint_activation(root.root_id, foreman_entry_request())
        .activation
    )
    activation = lab.wiring().store.record_dispatch(activation.activation_id, handle())
    lab.go_stale(activation.activation_id, tail_bytes=b"\x1b" * 4096)
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)

    byte_count, text = lab.transcript(
        lambda: main_module.main(["inspect", root.root_id, activation.activation_id])
    )

    assert byte_count <= (MAX_TRANSCRIPT_BYTES + lab.supervisor_config.log_tail_bytes)
    report = json.loads(text)
    assert report["activation_id"] == activation.activation_id
    assert report["tail"] != ""


def test_main_tick_caps_structlog_without_dropping_its_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tick's bd and git logs share its cap while the final report survives."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)

    byte_count, text = lab.transcript(lambda: main_module.main(["tick", root.root_id]))

    assert byte_count <= MAX_TRANSCRIPT_BYTES
    report = next(line for line in text.splitlines() if '"dispatched"' in line)
    assert json.loads(report)["dispatched"] is not None


def test_main_leaves_supervise_output_in_its_redirected_wrapper_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The wrapper stream is already bounded when a reader asks for its tail."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring()
        .store.mint_activation(root.root_id, foreman_entry_request())
        .activation
    )
    marker = "wrapper diagnostic\n" * MAX_TRANSCRIPT_BYTES
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)

    def noisy_wrapper(*_args: object, **_kwargs: object) -> WrapperExit:
        print(marker, end="")
        return WrapperExit.DONE

    monkeypatch.setattr(main_module, "run_wrapper", noisy_wrapper)

    byte_count, text = lab.transcript(
        lambda: main_module.main(
            [
                "--config",
                str(tmp_path / "foreman.toml"),
                "supervise",
                root.root_id,
                activation.activation_id,
            ]
        )
    )

    assert byte_count == len(marker.encode("utf-8"))
    assert text == marker


def test_status_renders_total_input_tokens_including_cache_layers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stored 92/3/5 usage record must render total input tokens as 100."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring()
        .store.mint_activation(root.root_id, foreman_entry_request())
        .activation
    )
    lab.fake_bd.rows[activation.activation_id]["metadata"]["usage"] = Usage(
        known=True,
        input_tokens=92,
        cache_read_input_tokens=3,
        cache_creation_input_tokens=5,
    ).model_dump(mode="json", exclude_none=True)
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)

    _, transcript = lab.transcript(lambda: main_module.main(["status", root.root_id]))
    report = json.loads(
        next(line for line in transcript.splitlines() if '"root_id"' in line)
    )

    assert report["usage"]["total_input_tokens"] == 100


def test_emit_bounds_an_oversize_stalled_report_without_dropping_it(
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    """A git failure cannot turn the tick report into a bare truncation marker."""
    main_module._emit(
        json.dumps({"stalled": "x" * (MAX_TRANSCRIPT_BYTES * 2)}),
        limit=MAX_TRANSCRIPT_BYTES,
    )

    rendered = capsysbinary.readouterr().out

    assert len(rendered) <= MAX_TRANSCRIPT_BYTES
    report = json.loads(rendered)
    assert report["stalled"] != ""


def test_lab_pins_overrides_and_test_flagged_graphs(tmp_path: Path) -> None:
    """The lab preserves DRILL-27's typed resolution and opt-in across roots."""
    flagged = tmp_path / "flagged.toml"
    flagged.write_text(
        mutate(
            VALID_FIXTURE.read_text(encoding="utf-8"),
            (("test_force_first_reject = false", "test_force_first_reject = true"),),
        ),
        encoding="utf-8",
    )
    lab = ForemanLab(
        tmp_path,
        toml=flagged,
        allow_test_flags=True,
        overrides={"instance.max_total_activations": 31},
    )

    root = lab.instantiate()

    assert root.metadata.allow_test_flags is True
    setting = next(
        item
        for item in root.metadata.resolved_config
        if item.key == "instance.max_total_activations"
    )
    assert setting.value == 31


def test_module_supervise_loads_the_argv_config_before_running_the_wrapper(
    tmp_path: Path,
) -> None:
    """The detached command gets past configuration and reaches wrapper loading."""
    repo = tmp_path / "repo"
    repo.mkdir()
    wrapper_root = (
        tmp_path
        / "home"
        / hashlib.sha256(str(repo.resolve()).encode("utf-8")).hexdigest()[:16]
    )
    config = tmp_path / "foreman.toml"
    config.write_text(
        f'''repo_root = "{repo}"
wrapper_home = "{tmp_path / "home"}"
host = "host"
actor = "actor"

[bd]
workspace = "{tmp_path / "bd"}"
actor = "actor"

[supervisor]
repo_root = "{repo}"
wrapper_root = "{wrapper_root}"
host = "host"
''',
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "workflow_interpreter.foreman",
            "--config",
            str(config),
            "supervise",
            "root-id",
            "activation-id",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "configuration path is required" not in completed.stderr
    assert "bd show" in completed.stderr


def test_inspect_uses_real_store_and_workspace_but_opens_no_healthy_log(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """A healthy bd activation gates the real wrapper path's log read."""
    repo = make_repo(tmp_path)
    supervisor = make_config(repo, tmp_path)
    config = ForemanConfig(
        repo_root=repo,
        wrapper_home=tmp_path / "foreman-home",
        bd=BdConfig(workspace=tmp_path / "bd", actor="actor"),
        host="host",
        actor="actor",
        supervisor=supervisor.model_copy(
            update={
                "wrapper_root": tmp_path
                / "foreman-home"
                / hashlib.sha256(str(repo.resolve()).encode("utf-8")).hexdigest()[:16]
            }
        ),
    )
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(
        root.root_id, bdio_entry_request()
    ).activation
    composition = Composition(
        config=config,
        store=fake_store,
        supervisor_config=config.supervisor,
        git=cast(Git, object()),
        clock=cast(Clock, object()),
        profiles=cast(ProfileResolver, object()),
        spawner=cast(Spawner, object()),
    )
    paths = composition.for_root(root.root_id).paths
    paths.ensure_activation_dir(activation.activation_id)
    paths.log(activation.activation_id).write_text(
        "secret runner bytes", encoding="utf-8"
    )

    report = Foreman(composition).inspect(root.root_id, activation.activation_id)

    assert report.tail == ""
    assert report.tail_bytes == 0
    assert report.stale_flag is None


def test_wrapper_records_a_non_dirty_precondition_refusal(
    fake_store: WorkflowStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real activation closes transport with the exact refused precondition."""
    repo = make_repo(tmp_path)
    supervisor = make_config(repo, tmp_path)
    config = ForemanConfig(
        repo_root=repo,
        wrapper_home=tmp_path / "foreman-home",
        bd=BdConfig(workspace=tmp_path / "bd", actor="actor"),
        host="host",
        actor="actor",
        supervisor=supervisor.model_copy(
            update={
                "wrapper_root": tmp_path
                / "foreman-home"
                / hashlib.sha256(str(repo.resolve()).encode("utf-8")).hexdigest()[:16]
            }
        ),
    )
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(
        root.root_id, bdio_entry_request()
    ).activation

    class Profiles:
        def profile_for(self, name: str) -> object:
            return object()

    composition = Composition(
        config=config,
        store=fake_store,
        supervisor_config=config.supervisor,
        git=cast(Git, object()),
        clock=cast(Clock, object()),
        profiles=cast(ProfileResolver, Profiles()),
        spawner=cast(Spawner, object()),
    )
    wiring = composition.for_root(root.root_id)

    def refuse(*_args: object, **_kwargs: object) -> object:
        raise PreconditionRefused("worktree is not a git worktree")

    monkeypatch.setattr(wiring.supervisor, "run", refuse)

    assert (
        run_wrapper(composition, root.root_id, activation.activation_id, wiring=wiring)
        is WrapperExit.DONE
    )
    closed = fake_store.reads.load_activation(activation.activation_id)
    assert closed.metadata.outcome is Outcome.ERROR_TRANSPORT
    assert closed.metadata.evidence is not None
    assert closed.metadata.evidence.note == "worktree is not a git worktree"
    assert closed.metadata.deviations[0].kind == "precondition_refused"
    assert closed.metadata.deviations[0].reason == "worktree is not a git worktree"


def test_wrapper_rejects_a_path_traversal_identifier_before_lock_creation(
    tmp_path: Path,
) -> None:
    """The wrapper never lets a CLI identifier choose a path outside its root."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    outside = tmp_path / "outside"

    with pytest.raises(ValueError, match="invalid bead id"):
        run_wrapper(lab.composition, root.root_id, "../outside")

    assert not outside.exists()


def test_inspect_rejects_an_activation_owned_by_another_root(tmp_path: Path) -> None:
    """Direct activation loads must bind the activation to the requested root."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring()
        .store.mint_activation(root.root_id, foreman_entry_request())
        .activation
    )
    lab.fake_bd.rows[activation.activation_id]["metadata"]["wf_root_id"] = "wf-other"

    with pytest.raises(ValueError, match="does not belong to root"):
        lab.foreman.inspect(root.root_id, activation.activation_id)


def test_status_reports_an_open_transition_gate_with_its_inbox_and_template(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """cr-tl3: a human waiting on `ship` needs the same surface `halt` gets.

    `status` is the ONLY command that renders a gate's inbox path and its
    unsigned payload template, and §9 approval is exactly "drop payload.json
    and payload.json.sig into that inbox". Reporting only `open_halt` left the
    operator of a human TRANSITION gate — `ship` and `triage` in the shipped
    feature-delivery graph — with no way to learn either without recomputing
    the gate key by hand.
    """
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    lab.profiles.next_script(
        ChildScript(
            marker='{"outcome":"done"}\n',
            effects='{"paths":["src/feature.py"]}',
            write_path="src/feature.py",
            write_body="value = 3\n",
            commit=True,
        )
    )
    assert lab.tick().dispatched is not None
    lab.tick()
    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
    )
    assert lab.tick().dispatched is not None
    lab.tick()
    ship_id = lab.tick().opened_gate
    assert ship_id is not None
    ship = lab.store.reads.load_gate(ship_id)
    assert ship.metadata.gate_node == "ship"

    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    _, transcript = lab.transcript(lambda: main_module.main(["status", root.root_id]))
    # `transcript` captures structlog's stderr alongside the one emitted report,
    # so select the report line rather than parsing the whole capture.
    report = json.loads(
        next(line for line in transcript.splitlines() if '"root_id"' in line)
    )

    reported = {entry["gate_id"]: entry for entry in report["open_gates"]}
    assert ship_id in reported
    entry = reported[ship_id]
    assert entry["node"] == "ship"
    assert entry["inbox"].endswith(ship.metadata.gate_key)
    assert json.loads(entry["template"])["gate_key"] == ship.metadata.gate_key
    assert "attempt" not in entry
    assert "previous_attempts" not in entry


def test_status_renders_prior_bridge_attempt_evidence_at_an_open_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A historical bridge root still renders the stage's retry evidence."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    first = PhaseBridgeRecord.prepared(
        epic_id="phase-1",
        stage_id="stage-a",
        attempt=1,
        target_ref="refs/heads/main",
        expected_base_commit=lab.head,
    )
    record = first.next_attempt().admitted("current-root")
    lab.fake_bd.rows[root.root_id]["metadata"]["instance_key"] = first.instance_key
    lab.fake_bd.rows["stage-a"] = {
        "id": "stage-a",
        "title": "bridge stage",
        "status": "in_progress",
        "issue_type": "task",
        "metadata": {"phase_bridge": record.model_dump(by_alias=True, mode="json")},
        "parent": "phase-1",
    }
    lab.profiles.next_script(
        ChildScript(
            marker='{"outcome":"done"}\n',
            effects='{"paths":["src/feature.py"]}',
            write_path="src/feature.py",
            write_body="value = 3\n",
            commit=True,
        )
    )
    assert lab.tick().dispatched is not None
    lab.tick()
    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
    )
    assert lab.tick().dispatched is not None
    lab.tick()
    ship_id = lab.tick().opened_gate
    assert ship_id is not None

    monkeypatch.setattr(
        gate_view_module.PhaseAdapter,
        "from_config",
        classmethod(
            lambda _cls, _config: PhaseAdapter(BdClient(lab.config.bd, lab.fake_bd))
        ),
    )
    assert gate_view_module.phase_bridge_gate_view(
        first.instance_key, lab.config.bd
    ) == {
        "attempt": 2,
        "is_current_attempt": False,
        "previous_attempts": (first.instance_key,),
    }
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    _, transcript = lab.transcript(lambda: main_module.main(["status", root.root_id]))
    report = json.loads(
        next(line for line in transcript.splitlines() if '"root_id"' in line)
    )
    entry = next(item for item in report["open_gates"] if item["gate_id"] == ship_id)

    assert entry["attempt"] == 2
    assert entry["is_current_attempt"] is False
    assert entry["previous_attempts"] == [first.instance_key]


def test_status_renders_current_bridge_attempt_evidence_at_an_open_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The running bridge root renders its stage's retry evidence."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    first = PhaseBridgeRecord.prepared(
        epic_id="phase-1",
        stage_id="stage-a",
        attempt=1,
        target_ref="refs/heads/main",
        expected_base_commit=lab.head,
    )
    record = first.next_attempt().admitted(root.root_id)
    lab.fake_bd.rows[root.root_id]["metadata"]["instance_key"] = record.instance_key
    lab.fake_bd.rows["stage-a"] = {
        "id": "stage-a",
        "title": "bridge stage",
        "status": "in_progress",
        "issue_type": "task",
        "metadata": {"phase_bridge": record.model_dump(by_alias=True, mode="json")},
        "parent": "phase-1",
    }
    lab.profiles.next_script(
        ChildScript(
            marker='{"outcome":"done"}\n',
            effects='{"paths":["src/feature.py"]}',
            write_path="src/feature.py",
            write_body="value = 3\n",
            commit=True,
        )
    )
    assert lab.tick().dispatched is not None
    lab.tick()
    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
    )
    assert lab.tick().dispatched is not None
    lab.tick()
    ship_id = lab.tick().opened_gate
    assert ship_id is not None

    monkeypatch.setattr(
        gate_view_module.PhaseAdapter,
        "from_config",
        classmethod(
            lambda _cls, _config: PhaseAdapter(BdClient(lab.config.bd, lab.fake_bd))
        ),
    )
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    _, transcript = lab.transcript(lambda: main_module.main(["status", root.root_id]))
    report = json.loads(
        next(line for line in transcript.splitlines() if '"root_id"' in line)
    )
    entry = next(item for item in report["open_gates"] if item["gate_id"] == ship_id)

    assert entry["attempt"] == 2
    assert entry["is_current_attempt"] is True
    assert entry["previous_attempts"] == [first.instance_key]


def test_phase_bridge_gate_view_rejects_a_root_outside_stage_attempts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A similarly named root remains foreign unless the record names it."""
    lab = ForemanLab(tmp_path)
    record = PhaseBridgeRecord.prepared(
        epic_id="phase-1",
        stage_id="stage-a",
        attempt=1,
        target_ref="refs/heads/main",
        expected_base_commit=lab.head,
    ).next_attempt()
    lab.fake_bd.rows["stage-a"] = {
        "id": "stage-a",
        "title": "bridge stage",
        "status": "in_progress",
        "issue_type": "task",
        "metadata": {"phase_bridge": record.model_dump(by_alias=True, mode="json")},
        "parent": "phase-1",
    }
    monkeypatch.setattr(
        gate_view_module.PhaseAdapter,
        "from_config",
        classmethod(
            lambda _cls, _config: PhaseAdapter(BdClient(lab.config.bd, lab.fake_bd))
        ),
    )

    with pytest.raises(PhaseAdapterError, match="does not own root instance_key"):
        gate_view_module.phase_bridge_gate_view(
            "phase-bridge:phase-1:stage-a:attempt:3", lab.config.bd
        )


def test_status_resolves_bridge_view_once_for_an_open_halt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The duplicate halt presentation shares one root-scoped bridge read."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    record = (
        PhaseBridgeRecord.prepared(
            epic_id="phase-1",
            stage_id="stage-a",
            attempt=1,
            target_ref="refs/heads/main",
            expected_base_commit=lab.head,
        )
        .next_attempt()
        .admitted(root.root_id)
    )
    lab.fake_bd.rows[root.root_id]["metadata"]["instance_key"] = record.instance_key
    lab.fake_bd.rows["stage-a"] = {
        "id": "stage-a",
        "title": "bridge stage",
        "status": "in_progress",
        "issue_type": "task",
        "metadata": {"phase_bridge": record.model_dump(by_alias=True, mode="json")},
        "parent": "phase-1",
    }
    lab.store.open_gate(root.root_id, halt_gate("ceiling:20"))
    resolutions = 0

    def adapter_from_config(
        _cls: type[PhaseAdapter], _config: BdConfig
    ) -> PhaseAdapter:
        nonlocal resolutions
        resolutions += 1
        return PhaseAdapter(BdClient(lab.config.bd, lab.fake_bd))

    monkeypatch.setattr(
        gate_view_module.PhaseAdapter,
        "from_config",
        classmethod(adapter_from_config),
    )
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)

    _, transcript = lab.transcript(lambda: main_module.main(["status", root.root_id]))

    assert '"open_halt"' in transcript
    assert resolutions == 1


def test_status_names_the_terminal_an_instance_reached_and_its_root_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    signing_config: SigningConfig,
    sign_payload: Signer,
) -> None:
    """cr-o85.34.24: `status` must answer "is it over, and where did it end?".

    The live build-loop run reached its terminal with `status` reporting only
    activations and gates, so the operator had to read the tick log to learn
    that the instance was finished at all.
    """
    lab = ForemanLab(tmp_path, signing=signing_config, signer=sign_payload)
    root = lab.instantiate()
    assert lab.tick().dispatched is not None
    lab.tick()
    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
    )
    assert lab.tick().dispatched is not None
    lab.tick()
    ship_id = lab.tick().opened_gate
    assert ship_id is not None
    lab.approve(ship_id, Outcome.APPROVE)
    assert lab.tick().closed_gates == (ship_id,)
    assert lab.tick().terminal_node == "shipped"

    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    _, transcript = lab.transcript(lambda: main_module.main(["status", root.root_id]))
    report = json.loads(
        next(line for line in transcript.splitlines() if '"root_id"' in line)
    )

    assert report["terminal"] == "shipped"
    assert report["root_state"] == STATUS_CLOSED


def test_status_reports_no_terminal_when_the_abandoned_end_has_no_unique_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    signing_config: SigningConfig,
    sign_payload: Signer,
) -> None:
    """Two abandon edges, two terminals: the end is real but has no ONE name.

    The tick still reports `terminal`, because the instance IS over — but the
    root stays open and unsettled rather than closing on one of two guesses,
    and `status` says exactly that.
    """
    graph = unnameable_abandon_graph(
        tmp_path, AMBIGUOUS_ABANDON_EDITS, "ambiguous-abandon.toml"
    )
    lab = ForemanLab(tmp_path, toml=graph, signing=signing_config, signer=sign_payload)
    root = lab.instantiate()
    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
    )
    assert lab.tick().dispatched is not None
    lab.tick()
    halt_id = lab.tick().opened_gate
    assert halt_id is not None
    lab.approve(halt_id, Outcome.ABANDON)
    assert lab.tick().closed_gates == (halt_id,)
    report = lab.tick()
    assert report.terminal is True
    assert report.terminal_node is None

    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    _, transcript = lab.transcript(lambda: main_module.main(["status", root.root_id]))
    status = json.loads(
        next(line for line in transcript.splitlines() if '"root_id"' in line)
    )

    assert status["terminal"] is None
    assert status["root_state"] != STATUS_CLOSED


def test_status_distinguishes_a_halted_instance_from_a_settled_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A halt is a human's turn, not an end: the root stays open and unsettled."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    gate = lab.store.open_gate(root.root_id, halt_gate("ceiling:20"))
    assert lab.tick().halted is True

    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    _, transcript = lab.transcript(lambda: main_module.main(["status", root.root_id]))
    status = json.loads(
        next(line for line in transcript.splitlines() if '"root_id"' in line)
    )

    assert status["terminal"] is None
    assert status["root_state"] != STATUS_CLOSED
    assert "open_halt" in status
    assert lab.store.reads.load_root(root.root_id).metadata.terminal is None
    assert gate.gate_id in {entry["gate_id"] for entry in status["open_gates"]}


def test_create_prints_a_root_id_that_status_then_accepts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`create` is the one command that mints its own root, from a graph file."""
    lab = ForemanLab(tmp_path)
    brief = tmp_path / "brief.md"
    brief.write_text("implement the lab fixture", encoding="utf-8")
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    config = tmp_path / "foreman.toml"

    _, created = lab.transcript(
        lambda: main_module.main(
            [
                "--config",
                str(config),
                "create",
                str(VALID_FIXTURE),
                "--instance-key",
                "cli-created",
                "--input",
                f"task_brief={brief}",
                # The lab config configures no §9 verifier, which `create`
                # otherwise refuses (E1a preflight).
                "--allow-unsigned-gates",
            ]
        )
    )

    root_id = _created_root_id(created)
    root = lab.store.reads.load_root(root_id)
    assert root.metadata.instance_key == "cli-created"
    assert [item.name for item in root.metadata.instance_inputs] == ["task_brief"]

    _, reported = lab.transcript(
        lambda: main_module.main(["--config", str(config), "status", root_id])
    )
    assert f'"root_id":"{root_id}"' in reported


def test_create_reports_a_refused_instantiation_without_a_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A resolution refusal is the message, on stderr, with a failing status."""
    lab = ForemanLab(tmp_path)
    brief = tmp_path / "brief.md"
    brief.write_text("implement the lab fixture", encoding="utf-8")
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    codes: list[int] = []

    _, transcript = lab.transcript(
        lambda: codes.append(
            main_module.main(
                [
                    "--config",
                    str(tmp_path / "foreman.toml"),
                    "create",
                    str(VALID_FIXTURE),
                    "--instance-key",
                    "cli-refused",
                    "--input",
                    f"stowaway={brief}",
                    "--allow-unsigned-gates",
                ]
            )
        )
    )

    assert codes == [1]
    assert "stowaway" in transcript
    assert "Traceback" not in transcript
    assert lab.fake_bd.command_count("create") == 0


def test_config_is_accepted_before_every_subcommand() -> None:
    """One `--config` position for all commands, including `phase-bridge`."""
    parser = main_module._parser()
    common = ["--config", "/tmp/foreman.toml"]
    forms = (
        ["create", "graph.toml", "--instance-key", "k", "--input", "a=b"],
        ["tick", "root"],
        ["status", "root"],
        ["run", "root"],
        ["phase-bridge", "phase", "stage"],
        ["supervise", "root", "activation"],
        ["inspect", "root", "activation"],
        ["steer", "root", "activation", "--reason", "r", "--instructions-file", "f"],
    )

    for form in forms:
        args = parser.parse_args(common + form)
        assert args.command == form[0]
        assert args.config == Path("/tmp/foreman.toml")


def _bridge_stage(
    stage_id: str, *, status: str = "open", description: str | None = None
) -> dict[str, object]:
    """Build one direct phase child for the command's public CLI seam."""
    return {
        "id": stage_id,
        "title": "summary only",
        "description": description,
        "status": status,
        "issue_type": "task",
        "metadata": {},
        "parent": "phase",
    }


def _bridge_adapter(lab: ForemanLab) -> PhaseAdapter:
    """Keep the command's bridge adapter on the lab's real fake-bd transport."""
    return PhaseAdapter(BdClient(lab.config.bd, lab.fake_bd))


def test_phase_bridge_reports_exhaustion_before_named_stage_membership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An exhausted phase is a fact even if the caller names a stale stage id."""
    lab = ForemanLab(tmp_path)
    lab.fake_bd.rows["closed-stage"] = _bridge_stage("closed-stage", status="closed")
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    monkeypatch.setattr(
        bridge_command_module.PhaseAdapter,
        "from_config",
        classmethod(lambda _cls, _config: _bridge_adapter(lab)),
    )

    codes: list[int] = []
    _, transcript = lab.transcript(
        lambda: codes.append(main_module.main(["phase-bridge", "phase", "missing"]))
    )

    assert codes == [0]
    assert json.loads(transcript)["state"] == "phase-exhausted"


def test_phase_bridge_refuses_an_empty_stage_description_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The title never substitutes for a stage's task_brief input."""
    lab = ForemanLab(tmp_path)
    lab.fake_bd.rows["stage"] = _bridge_stage("stage", description=None)
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    monkeypatch.setattr(
        bridge_command_module.PhaseAdapter,
        "from_config",
        classmethod(lambda _cls, _config: _bridge_adapter(lab)),
    )

    codes: list[int] = []
    _, transcript = lab.transcript(
        lambda: codes.append(main_module.main(["phase-bridge", "phase", "stage"]))
    )

    report = json.loads(transcript.splitlines()[0])
    assert codes == [2]
    assert report["state"] == "refused"
    assert "description" in report["reason"]
    assert lab.fake_bd.command_count("update") == 0
    assert lab.fake_bd.command_count("create") == 0


def test_phase_bridge_refuses_without_a_configured_bridge_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A graphless foreman config cannot mint an unpinned bridge root."""
    lab = ForemanLab(tmp_path)
    lab.fake_bd.rows["stage"] = _bridge_stage("stage", description="full brief")
    composition = replace(
        lab.composition,
        config=lab.config.model_copy(update={"bridge_graph": None}),
    )
    monkeypatch.setattr(main_module, "_composition", lambda _: composition)
    monkeypatch.setattr(
        bridge_command_module.PhaseAdapter,
        "from_config",
        classmethod(lambda _cls, _config: _bridge_adapter(lab)),
    )

    codes: list[int] = []
    _, transcript = lab.transcript(
        lambda: codes.append(main_module.main(["phase-bridge", "phase", "stage"]))
    )

    report = json.loads(transcript.splitlines()[0])
    assert codes == [2]
    assert report["state"] == "refused"
    assert "bridge_graph" in report["reason"]
    assert lab.fake_bd.command_count("update") == 0
    assert lab.fake_bd.command_count("create") == 0


def test_phase_bridge_refuses_a_configured_required_input_it_cannot_supply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only task_brief is bridge-owned; another required input costs no root."""
    lab = ForemanLab(tmp_path, toml=BUILD_LOOP_GRAPH)
    lab.fake_bd.rows["stage"] = _bridge_stage("stage", description="full brief")
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    monkeypatch.setattr(
        bridge_command_module.PhaseAdapter,
        "from_config",
        classmethod(lambda _cls, _config: _bridge_adapter(lab)),
    )

    codes: list[int] = []
    _, transcript = lab.transcript(
        lambda: codes.append(main_module.main(["phase-bridge", "phase", "stage"]))
    )

    report = json.loads(transcript.splitlines()[0])
    assert codes == [2]
    assert report["state"] == "refused"
    assert "seam_contract" in report["reason"]
    assert lab.fake_bd.command_count("update") == 0
    assert lab.fake_bd.command_count("create") == 0


def test_phase_bridge_trace_is_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Trace renders absent evidence without admitting, minting, or changing refs."""
    lab = ForemanLab(tmp_path)
    lab.fake_bd.rows["stage"] = _bridge_stage("stage", description="full brief")
    before = lab.git.head_commit(cwd=lab.repo)
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    monkeypatch.setattr(
        bridge_command_module.PhaseAdapter,
        "from_config",
        classmethod(lambda _cls, _config: _bridge_adapter(lab)),
    )

    codes: list[int] = []
    _, transcript = lab.transcript(
        lambda: codes.append(
            main_module.main(["phase-bridge", "phase", "stage", "--trace"])
        )
    )

    report = json.loads(transcript)
    assert codes == [0]
    assert report["relation"] is None
    assert report["landing_intent"] is None
    assert report["receipt_digest"] is None
    assert lab.fake_bd.command_count("update") == 0
    assert lab.fake_bd.command_count("create") == 0
    assert lab.git.head_commit(cwd=lab.repo) == before


def test_phase_bridge_uses_the_run_defaults_not_the_band_wait(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bridge polling must not shorten the run before its human ship gate."""
    lab = ForemanLab(tmp_path, band_wait_s=7.0)
    lab.fake_bd.rows["stage"] = _bridge_stage("stage", description="full brief")
    calls: list[tuple[float, float]] = []
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    monkeypatch.setattr(
        bridge_command_module.PhaseAdapter,
        "from_config",
        classmethod(lambda _cls, _config: _bridge_adapter(lab)),
    )

    def run(
        _self: Foreman, _root_id: str, *, poll_s: float, max_wall_s: float
    ) -> RunReport:
        """Capture the public run boundary without advancing the lab clock."""
        calls.append((poll_s, max_wall_s))
        return RunReport(ticks=1, report=TickReport())

    monkeypatch.setattr(Foreman, "run", run)
    codes: list[int] = []

    lab.transcript(
        lambda: codes.append(main_module.main(["phase-bridge", "phase", "stage"]))
    )

    assert codes == [0]
    assert calls == [(30.0, 28_800.0)]


@pytest.mark.parametrize("trace", (False, True))
def test_phase_bridge_refuses_a_missing_stage_instead_of_crashing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, trace: bool
) -> None:
    """A bd read miss is caller input, in ordinary and trace command forms."""
    lab = ForemanLab(tmp_path)
    lab.fake_bd.rows["stage"] = _bridge_stage("stage", description="full brief")
    adapter = _bridge_adapter(lab)
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    monkeypatch.setattr(
        bridge_command_module.PhaseAdapter,
        "from_config",
        classmethod(lambda _cls, _config: adapter),
    )

    def missing(_stage_id: str) -> NoReturn:
        """Model the typed bd read failure for the caller's nonexistent id."""
        raise BdOutputError("bd show missing returned no row")

    if trace:
        monkeypatch.setattr(adapter, "blocking_dependencies", lambda _stage_id: ())
        monkeypatch.setattr(adapter, "show", missing)
    else:
        monkeypatch.setattr(adapter, "blocking_dependencies", missing)
    codes: list[int] = []
    arguments = ["phase-bridge", "phase", "missing"]
    if trace:
        arguments.append("--trace")

    _, transcript = lab.transcript(lambda: codes.append(main_module.main(arguments)))

    report = json.loads(transcript)
    assert codes == [2]
    assert report["state"] == "refused"
    assert "missing" in report["reason"]
    assert "Traceback" not in transcript


@pytest.mark.parametrize("trace", (False, True))
def test_phase_bridge_refuses_an_epic_without_stages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, trace: bool
) -> None:
    """An empty epic cannot tell a caller that its phase is exhausted."""
    lab = ForemanLab(tmp_path)
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    monkeypatch.setattr(
        bridge_command_module.PhaseAdapter,
        "from_config",
        classmethod(lambda _cls, _config: _bridge_adapter(lab)),
    )
    codes: list[int] = []
    arguments = ["phase-bridge", "phase", "missing"]
    if trace:
        arguments.append("--trace")

    _, transcript = lab.transcript(lambda: codes.append(main_module.main(arguments)))

    report = json.loads(transcript)
    assert codes == [2]
    assert report["state"] == "refused"
    assert "no stages" in report["reason"]


@pytest.mark.parametrize(
    ("guard", "reason"),
    (("detached", "detached"), ("dirty", "not clean")),
)
def test_phase_bridge_refuses_a_detached_or_dirty_coordinator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, guard: str, reason: str
) -> None:
    """The coordinator preflight refuses before any bridge or bd operation."""
    lab = ForemanLab(tmp_path)
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    if guard == "detached":
        monkeypatch.setattr(lab.git, "attached_branch_ref", lambda **_kwargs: None)
    else:
        monkeypatch.setattr(
            lab.git, "status_paths", lambda **_kwargs: (("uncommitted.txt", True),)
        )
    codes: list[int] = []

    _, transcript = lab.transcript(
        lambda: codes.append(main_module.main(["phase-bridge", "phase", "stage"]))
    )

    report = json.loads(transcript)
    assert codes == [2]
    assert report["state"] == "refused"
    assert reason in report["reason"]
    assert lab.fake_bd.calls == []


def test_phase_bridge_reports_another_open_admission_as_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sibling's unfinished admission is waiting work, not a caller refusal."""
    lab = ForemanLab(tmp_path)
    held = PhaseBridgeRecord.prepared(
        epic_id="phase",
        stage_id="other-stage",
        attempt=1,
        target_ref="refs/heads/main",
        expected_base_commit=lab.head,
    )
    lab.fake_bd.rows["stage"] = _bridge_stage("stage", description="full brief")
    lab.fake_bd.rows["other-stage"] = _bridge_stage(
        "other-stage", description="held brief"
    )
    lab.fake_bd.rows["other-stage"]["metadata"] = {
        "phase_bridge": held.model_dump(by_alias=True, mode="json")
    }
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    monkeypatch.setattr(
        bridge_command_module.PhaseAdapter,
        "from_config",
        classmethod(lambda _cls, _config: _bridge_adapter(lab)),
    )
    codes: list[int] = []

    _, transcript = lab.transcript(
        lambda: codes.append(main_module.main(["phase-bridge", "phase", "stage"]))
    )

    report = json.loads(transcript)
    assert codes == [0]
    assert report["state"] == "blocked"
    assert "other-stage" in report["reason"]
    assert report["blocking_ids"] == ["other-stage"]
    assert report["record"] is None
    assert report["result"] is None


def test_phase_bridge_reports_open_blocking_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An open blocking dependency returns its durable ids without admission."""
    lab = ForemanLab(tmp_path)
    lab.fake_bd.rows["stage"] = _bridge_stage("stage", description="full brief")
    lab.fake_bd.rows["stage"]["dependencies"] = [
        {"id": "blocking-stage", "status": "open", "dependency_type": "blocks"}
    ]
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    monkeypatch.setattr(
        bridge_command_module.PhaseAdapter,
        "from_config",
        classmethod(lambda _cls, _config: _bridge_adapter(lab)),
    )

    def unexpected_graph(_composition: Composition) -> NoReturn:
        """Make a removed dependency return fail before it can admit work."""
        raise AssertionError("blocking dependency reached graph admission")

    monkeypatch.setattr(bridge_command_module, "_bridge_graph", unexpected_graph)
    codes: list[int] = []

    _, transcript = lab.transcript(
        lambda: codes.append(main_module.main(["phase-bridge", "phase", "stage"]))
    )

    report = json.loads(transcript)
    assert codes == [0]
    assert report["state"] == "blocked"
    assert report["blocking_ids"] == ["blocking-stage"]


def test_phase_bridge_retry_mints_a_distinct_successor_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An eligible retry uses the explicit successor admission path once."""
    lab = ForemanLab(tmp_path)
    prior_root = lab.instantiate()
    lab.fake_bd.rows[prior_root.root_id]["metadata"]["terminal"] = "shipped"
    first = PhaseBridgeRecord.prepared(
        epic_id="phase",
        stage_id="stage",
        attempt=1,
        target_ref="refs/heads/main",
        expected_base_commit=lab.head,
    ).admitted(prior_root.root_id)
    lab.fake_bd.rows["stage"] = _bridge_stage("stage", description="full brief")
    lab.fake_bd.rows["stage"]["status"] = "in_progress"
    lab.fake_bd.rows["stage"]["metadata"] = {
        "phase_bridge": first.model_dump(by_alias=True, mode="json")
    }
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    monkeypatch.setattr(
        bridge_command_module.PhaseAdapter,
        "from_config",
        classmethod(lambda _cls, _config: _bridge_adapter(lab)),
    )

    codes: list[int] = []
    _, transcript = lab.transcript(
        lambda: codes.append(
            main_module.main(["phase-bridge", "phase", "stage", "--retry"])
        )
    )

    report = json.loads(transcript.splitlines()[0])
    stored = PhaseBridgeRecord.model_validate(
        lab.fake_bd.rows["stage"]["metadata"]["phase_bridge"]
    )
    assert codes == [0]
    assert report["state"] == "result"
    assert stored.attempt == 2
    assert stored.instance_key != first.instance_key
    assert stored.previous_attempts == (first.instance_key,)


@pytest.mark.parametrize("reason", tuple(RetryRefusal))
def test_phase_bridge_reports_each_retry_predicate_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reason: RetryRefusal
) -> None:
    """Every pure retry refusal is carried to the CLI without a stage write."""
    lab = ForemanLab(tmp_path)
    prior_root = lab.instantiate()
    record = PhaseBridgeRecord.prepared(
        epic_id="phase",
        stage_id="stage",
        attempt=1,
        target_ref="refs/heads/main",
        expected_base_commit=lab.head,
    ).admitted(prior_root.root_id)
    lab.fake_bd.rows["stage"] = _bridge_stage("stage", description="full brief")
    lab.fake_bd.rows["stage"]["status"] = "in_progress"
    lab.fake_bd.rows["stage"]["metadata"] = {
        "phase_bridge": record.model_dump(by_alias=True, mode="json")
    }
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    monkeypatch.setattr(
        bridge_command_module.PhaseAdapter,
        "from_config",
        classmethod(lambda _cls, _config: _bridge_adapter(lab)),
    )
    monkeypatch.setattr(
        bridge_command_module,
        "retry_refusal",
        lambda _state, _terminals, _frontier: reason,
    )
    writes = lab.fake_bd.command_count("update")

    codes: list[int] = []
    _, transcript = lab.transcript(
        lambda: codes.append(
            main_module.main(["phase-bridge", "phase", "stage", "--retry"])
        )
    )

    report = json.loads(transcript.splitlines()[0])
    assert codes == [2]
    assert report["state"] == "refused"
    assert report["reason"] == reason.value
    assert lab.fake_bd.command_count("update") == writes


def _create_argv(tmp_path: Path, brief: Path, *extra: str) -> list[str]:
    """The `create` command line every E1 preflight test shares."""
    return [
        "--config",
        str(tmp_path / "foreman.toml"),
        "create",
        str(VALID_FIXTURE),
        "--instance-key",
        "preflight",
        "--input",
        f"task_brief={brief}",
        *extra,
    ]


def _brief(tmp_path: Path) -> Path:
    """The one instance input the lab fixture declares."""
    brief = tmp_path / "brief.md"
    brief.write_text("implement the lab fixture", encoding="utf-8")
    return brief


def test_create_refuses_a_config_that_configures_no_gate_verifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A root nobody can approve is refused before bd is written (E1a).

    `close_gate_verified` raises `BdConfigError` with no verifier, which is
    discovered only once a human is already waiting at `ship`.
    """
    lab = ForemanLab(tmp_path)
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    codes: list[int] = []

    _, transcript = lab.transcript(
        lambda: codes.append(main_module.main(_create_argv(tmp_path, _brief(tmp_path))))
    )

    assert codes == [1]
    assert "allowed_signers_path" in transcript
    assert "make-foreman-config.sh" in transcript
    assert "--allow-unsigned-gates" in transcript
    assert lab.fake_bd.command_count("create") == 0


def test_create_accepts_an_unsigned_lab_config_when_the_flag_is_passed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--allow-unsigned-gates` is the lab escape hatch, and only that (E1a)."""
    lab = ForemanLab(tmp_path)
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    codes: list[int] = []

    _, transcript = lab.transcript(
        lambda: codes.append(
            main_module.main(
                _create_argv(tmp_path, _brief(tmp_path), "--allow-unsigned-gates")
            )
        )
    )

    assert codes == [0]
    root_id = _created_root_id(transcript)
    assert lab.store.reads.load_root(root_id).metadata.instance_key == "preflight"


def test_create_refuses_a_signing_config_whose_allow_list_went_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config: SigningConfig
) -> None:
    """The allow-list is read at `create`, not first at the gate (E1a)."""
    lab = ForemanLab(tmp_path, signing=signing_config)
    signing_config.allowed_signers_path.rename(tmp_path / "moved-allow-list")
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    codes: list[int] = []

    try:
        _, transcript = lab.transcript(
            lambda: codes.append(
                main_module.main(_create_argv(tmp_path, _brief(tmp_path)))
            )
        )
    finally:
        (tmp_path / "moved-allow-list").rename(signing_config.allowed_signers_path)

    assert codes == [1]
    assert str(signing_config.allowed_signers_path) in transcript
    assert lab.fake_bd.command_count("create") == 0


def test_create_proceeds_when_the_allow_list_exists_and_is_not_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config: SigningConfig
) -> None:
    """A signed-gate config is the ordinary path and passes the preflight (E1a)."""
    lab = ForemanLab(tmp_path, signing=signing_config)
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    codes: list[int] = []

    _, transcript = lab.transcript(
        lambda: codes.append(main_module.main(_create_argv(tmp_path, _brief(tmp_path))))
    )

    assert codes == [0]
    root_id = _created_root_id(transcript)
    assert lab.store.reads.load_root(root_id).metadata.instance_key == "preflight"


RED_CHECK_LINE = "the-check-said-why"
RED_CHECK = f"#!/bin/sh\necho {RED_CHECK_LINE} >&2\nexit 1\n"


def test_inspect_reports_the_red_output_of_a_fail_code_activations_checks(
    tmp_path: Path,
) -> None:
    """cr-o85.34.12: a `fail_code` used to name an exit code and nothing else.

    Live, a red `scripts/review-checks.sh` left neither `completion.json` nor
    the bead holding a byte of what it printed, so the cause had to be
    inferred. Both attempts of the rerun policy are surfaced, because the
    check is red at both.
    """
    lab = ForemanLab(tmp_path)
    lab.pin_checks({VERIFY_SCRIPT: RED_CHECK})
    root = lab.instantiate()
    lab.profiles.next_script(
        ChildScript(
            marker='{"outcome":"done"}\n',
            effects='{"paths":["src/feature.py"]}',
            write_path="src/feature.py",
            write_body="value = 2\n",
            commit=True,
        )
    )
    activation_id = lab.tick().dispatched
    assert activation_id is not None
    assert lab.tick().settled == activation_id
    settled = lab.store.reads.load_activation(activation_id)
    assert settled.metadata.outcome is Outcome.FAIL_CODE

    report = lab.foreman.inspect(root.root_id, activation_id)

    check = next(item for item in report.verify if item.cmd == VERIFY_SCRIPT)
    assert check.exit_code != 0
    assert check.attempts == 2
    assert len(check.red_tails) == 2
    assert all(RED_CHECK_LINE in tail for tail in check.red_tails)


def test_inspect_reports_no_verify_for_an_activation_that_never_completed(
    tmp_path: Path,
) -> None:
    """A read-only view of an ungraded activation is empty, never an error."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring()
        .store.mint_activation(root.root_id, foreman_entry_request())
        .activation
    )

    report = lab.foreman.inspect(root.root_id, activation.activation_id)

    assert report.verify == ()


def test_main_status_writes_the_report_alone_to_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """cr-o85.34.15: `jq` on captured stdout parses the whole stream.

    Nothing configured structlog, so its default `PrintLogger` wrote every git
    and bd line to STDOUT ahead of the report — `capsys` keeps the two streams
    apart where the lab's merged `transcript` cannot.
    """
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    # Everything the lab logged while driving the instance was written
    # before `main` configured structlog, so it is not this assertion's
    # stdout: drop it and read only what the command itself emits.
    capsys.readouterr()

    assert main_module.main(["status", root.root_id]) == 0

    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert isinstance(report, dict)
    assert report["root_id"] == root.root_id
