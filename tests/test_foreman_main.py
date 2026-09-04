"""C2b CLI entrypoint and stale-tail integration contracts."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

from tests._bdio import entry_request, handle, load_definition, make_root
from tests._foreman import ForemanLab
from tests._helpers import VALID_FIXTURE, mutate
from tests._supervisor import VERIFY_SCRIPT, ChildScript, make_config, make_repo
from workflow_interpreter.bdio import BdConfig, Outcome
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.config import SigningConfig
from workflow_interpreter.foreman import __main__ as main_module
from workflow_interpreter.foreman.compose import Composition, ProfileResolver, Spawner
from workflow_interpreter.foreman.config import ForemanConfig
from workflow_interpreter.foreman.constants import MAX_TRANSCRIPT_BYTES
from workflow_interpreter.foreman.supervise import WrapperExit, run_wrapper
from workflow_interpreter.foreman.tick import Foreman
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
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
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
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
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
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
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
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation

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
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
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
    """One `--config` position for all six commands, including `supervise`."""
    parser = main_module._parser()
    common = ["--config", "/tmp/foreman.toml"]
    forms = (
        ["create", "graph.toml", "--instance-key", "k", "--input", "a=b"],
        ["tick", "root"],
        ["status", "root"],
        ["supervise", "root", "activation"],
        ["inspect", "root", "activation"],
        ["steer", "root", "activation", "--reason", "r", "--instructions-file", "f"],
    )

    for form in forms:
        args = parser.parse_args(common + form)
        assert args.command == form[0]
        assert args.config == Path("/tmp/foreman.toml")


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
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
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
