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
from tests._supervisor import ChildScript, make_config, make_repo
from workflow_interpreter.bdio import BdConfig, Outcome
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.foreman import __main__ as main_module
from workflow_interpreter.foreman.compose import Composition, ProfileResolver, Spawner
from workflow_interpreter.foreman.config import ForemanConfig
from workflow_interpreter.foreman.constants import MAX_TRANSCRIPT_BYTES
from workflow_interpreter.foreman.supervise import WrapperExit, run_wrapper
from workflow_interpreter.foreman.tick import Foreman
from workflow_interpreter.supervisor.clock import Clock
from workflow_interpreter.supervisor.errors import PreconditionRefused
from workflow_interpreter.supervisor.gitio import Git


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
    assert json.loads(text.splitlines()[-1])["dispatched"] is not None


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
                "supervise",
                root.root_id,
                activation.activation_id,
                "--config",
                str(tmp_path / "foreman.toml"),
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
            "supervise",
            "root-id",
            "activation-id",
            "--config",
            str(config),
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
