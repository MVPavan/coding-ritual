"""Driver observations survive process boundaries without granting authority."""

import json
from pathlib import Path

import pytest

from tests._foreman import ForemanLab
from workflow_interpreter.foreman.gates import ensure_inbox, halt_gate
from workflow_interpreter.foreman.heartbeat import DriverHeartbeat, DriverObserver
from workflow_interpreter.foreman.refusals import read_refusals
from workflow_interpreter.foreman.tick import Foreman, TickReport
from workflow_interpreter.foreman.wake_constants import DriverState
from workflow_interpreter.supervisor.paths import read_record


def test_run_always_records_start_tick_and_stop_without_monitor(tmp_path: Path) -> None:
    """Ordinary unattended runs need no monitor but leave a durable heartbeat."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    gate = lab.store.open_gate(root.root_id, halt_gate("test"))
    result = Foreman(lab.composition).run(root.root_id, poll_s=1, max_wall_s=10)
    heartbeat = read_record(lab.wiring().paths.driver_heartbeat, DriverHeartbeat)
    assert heartbeat is not None
    assert heartbeat.state is DriverState.STOPPED
    assert heartbeat.ticks == result.ticks == 1
    assert gate.gate_id in heartbeat.gates
    assert heartbeat.root_id == root.root_id
    assert heartbeat.handle.proc_start_time


def test_refusal_stops_run_and_journal_deduplicates(
    tmp_path: Path, signing_config
) -> None:
    """An invalid signed inbox is attention, not an endless healthy tick loop."""
    lab = ForemanLab(tmp_path, signing=signing_config)
    root = lab.instantiate()
    gate = lab.store.open_gate(root.root_id, halt_gate("test"))
    inbox = ensure_inbox(lab.wiring().paths, gate)
    (inbox / "payload.json").write_text("{}")
    (inbox / "payload.json.sig").write_text("invalid")
    for _ in range(2):
        result = Foreman(lab.composition).run(root.root_id, poll_s=1, max_wall_s=10)
        assert result.ticks == 1
        assert result.attention
        assert result.report.refusals
    records = read_refusals(lab.wiring().paths.instance_dir)
    assert len(records) == 1
    assert records[0].gate_id == gate.gate_id
    heartbeat = read_record(lab.wiring().paths.driver_heartbeat, DriverHeartbeat)
    assert heartbeat.refusal_count == 1


def test_observer_records_start_and_completed_ticks_and_new_generations(tmp_path: Path):
    """A hung tick leaves its starting/previous record; restart changes identity."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    with DriverObserver(lab.composition, root.root_id) as observer:
        start = read_record(lab.wiring().paths.driver_heartbeat, DriverHeartbeat)
        assert start.state is DriverState.STARTING
        assert start.ticks == 0
        observer.observe(TickReport(blocked=True))
        advanced = read_record(lab.wiring().paths.driver_heartbeat, DriverHeartbeat)
        assert advanced.state is DriverState.RUNNING
        assert advanced.ticks == 1
    with DriverObserver(lab.composition, root.root_id):
        restart = read_record(lab.wiring().paths.driver_heartbeat, DriverHeartbeat)
        assert restart.generation != start.generation


def test_refusal_is_loud_in_status_and_run_exit(
    tmp_path: Path, monkeypatch, capsys, signing_config
):
    """CLI clients receive a nonzero run result and explicit refusal detail."""
    from workflow_interpreter.foreman import __main__ as cli

    lab = ForemanLab(tmp_path, signing=signing_config)
    root = lab.instantiate()
    gate = lab.store.open_gate(root.root_id, halt_gate("test"))
    inbox = ensure_inbox(lab.wiring().paths, gate)
    (inbox / "payload.json").write_text("{}")
    (inbox / "payload.json.sig").write_text("bad")
    monkeypatch.setattr(cli, "_composition", lambda _: lab.composition)
    assert cli.main(["run", root.root_id]) != 0
    capsys.readouterr()
    assert cli.main(["status", root.root_id]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["observation"]["refusals"][0]["gate_id"] == gate.gate_id
    assert status["observation"]["heartbeat_age_s"] >= 0


def test_observer_reports_durability_failure(tmp_path: Path, monkeypatch):
    """Losing the heartbeat must not be reported as a healthy run."""
    from workflow_interpreter.foreman import heartbeat

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()

    def unwritable(*_):
        raise OSError("disk full")

    monkeypatch.setattr(heartbeat, "write_record", unwritable)
    with (
        pytest.raises(OSError, match="disk full"),
        DriverObserver(lab.composition, root.root_id),
    ):
        pytest.fail("must not start work without recording the heartbeat")


def test_log_cursor_does_not_treat_truncation_or_replacement_as_progress(tmp_path):
    """Equal offsets from distinct file generations are distinct observations."""
    from workflow_interpreter.foreman.heartbeat import log_cursor

    path = tmp_path / "run.jsonl"
    path.write_bytes(b"a" * 100)
    first = log_cursor(path, "activation-a", None)
    path.write_bytes(b"short")
    second = log_cursor(path, "activation-a", first)
    assert second.offset < first.offset
    assert second.generation == first.generation + 1
    replacement = tmp_path / "new"
    replacement.write_bytes(b"other")
    replacement.replace(path)
    third = log_cursor(path, "activation-a", second)
    assert third.generation == second.generation + 1
    assert log_cursor(path, "activation-b", third).generation == third.generation + 1


def test_phase_bridge_propagates_run_attention(tmp_path, monkeypatch):
    """Refusal attention is nonzero through the bridge's existing run adapter."""
    from tests.test_foreman_main import _bridge_adapter, _bridge_lab, _bridge_stage
    from workflow_interpreter.bridge import command
    from workflow_interpreter.foreman.tick import RunReport

    lab = _bridge_lab(tmp_path)
    lab.fake_bd.rows["stage"] = _bridge_stage("stage", description="Implement feature")
    monkeypatch.setattr(
        command.PhaseAdapter,
        "from_config",
        classmethod(lambda *_: _bridge_adapter(lab)),
    )
    monkeypatch.setattr(
        Foreman,
        "run",
        lambda *_args, **_kwargs: RunReport(
            ticks=1, report=TickReport(refusals=("bad signature",))
        ),
    )
    result = command.execute_phase_bridge(
        lab.composition, epic_id="phase", stage_id="stage", retry=False, trace=False
    )
    assert result.exit_code != 0
    assert result.report["result"]["report"]["refusals"] == ["bad signature"]


def test_journal_is_bounded_and_repeated_refusals_do_not_spend_capacity(tmp_path):
    """Distinct signed failures spend the allowance; mtime and repeats do not."""
    from workflow_interpreter.foreman.refusals import ObservationStatus, append_refusal
    from workflow_interpreter.foreman.wake_constants import OBSERVATION_STATUS

    def append(payload):
        return append_refusal(
            tmp_path,
            gate_id="gate",
            gate_key="key",
            payload=payload,
            signature=b"signature",
            error="bad",
            reason="x" * 20000,
            path=tmp_path / "refusal.json",
            limit=2,
        )

    first = append(b"first")
    assert append(b"first").identity == first.identity
    append(b"second")
    append(b"third")
    records = read_refusals(tmp_path)
    assert len(records) == 2
    assert len(records[0].reason.encode()) <= 2048
    assert all(
        len(line) <= 8192
        for line in (tmp_path / "refusals.jsonl").read_bytes().splitlines()
    )
    assert read_record(tmp_path / OBSERVATION_STATUS, ObservationStatus).saturated


def test_refusal_journal_failure_is_visible(tmp_path, monkeypatch, signing_config):
    """A readable refusal receipt cannot disguise failed durable journaling."""
    from workflow_interpreter.foreman import refusals

    lab = ForemanLab(tmp_path, signing=signing_config)
    root = lab.instantiate()
    gate = lab.store.open_gate(root.root_id, halt_gate("test"))
    inbox = ensure_inbox(lab.wiring().paths, gate)
    (inbox / "payload.json").write_text("{}")
    (inbox / "payload.json.sig").write_text("invalid")

    def fail(*_args):
        raise OSError("journal disk full")

    monkeypatch.setattr(refusals, "write_durable", fail)
    result = Foreman(lab.composition).run(root.root_id, poll_s=1, max_wall_s=10)
    assert result.attention
    assert "journal disk full" in result.report.refusals[0]
    heartbeat = read_record(lab.wiring().paths.driver_heartbeat, DriverHeartbeat)
    assert "journal disk full" in heartbeat.durability_error
