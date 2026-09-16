"""Observation failures are advisory, while workflow authority stays fail-closed."""

import json
from pathlib import Path

import pytest

from tests._foreman import ForemanLab
from tests.test_children_process import writer_lab
from workflow_interpreter.contracts.wake import WakeCondition
from workflow_interpreter.foreman import __main__ as cli
from workflow_interpreter.foreman import heartbeat, monitor
from workflow_interpreter.foreman.decisions import admission_of
from workflow_interpreter.foreman.gates import halt_gate
from workflow_interpreter.foreman.heartbeat import DriverHeartbeat, DriverObserver
from workflow_interpreter.foreman.observation import ObservationStatus
from workflow_interpreter.foreman.refusals import append_refusal
from workflow_interpreter.foreman.tick import Foreman, TickReport
from workflow_interpreter.foreman.wake_constants import (
    OBSERVATION_STATUS,
    REFUSAL_JOURNAL,
)
from workflow_interpreter.supervisor import paths
from workflow_interpreter.supervisor.paths import HEARTBEAT_FILE, read_record


@pytest.mark.parametrize("corruption", ["heartbeat", "journal", "status"])
def test_corrupt_observation_never_blocks_run_or_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, corruption: str
) -> None:
    """Malformed advisory files cannot turn a normal gate return into a crash."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    lab.store.open_gate(root.root_id, halt_gate("test"))
    directory = lab.wiring().paths.instance_dir
    directory.mkdir(parents=True, exist_ok=True)
    names = {
        "heartbeat": HEARTBEAT_FILE,
        "journal": REFUSAL_JOURNAL,
        "status": OBSERVATION_STATUS,
    }
    if corruption == "journal":
        append_refusal(
            directory,
            gate_id="gate",
            gate_key="key",
            payload=b"p",
            signature=b"s",
            error="bad",
            reason="retained",
            path=directory,
        )
        with (directory / REFUSAL_JOURNAL).open("ab") as stream:
            stream.write(b"invalid json\n")
    else:
        (directory / names[corruption]).write_text("invalid json")
    monkeypatch.setattr(cli, "_composition", lambda _: lab.composition)
    capsys.readouterr()
    assert cli.main(["status", root.root_id]) == 0
    before = json.loads(capsys.readouterr().out)["observation"]
    result = Foreman(lab.composition).run(root.root_id, poll_s=1, max_wall_s=10)
    assert result.ticks == 1
    assert cli.main(["status", root.root_id]) == 0
    after = json.loads(capsys.readouterr().out)["observation"]
    if corruption == "heartbeat":
        assert before["durability"]["heartbeat_degraded"]
        assert after["durability"]["heartbeat_degraded"]
        assert read_record(directory / HEARTBEAT_FILE, DriverHeartbeat) is not None
    elif corruption == "journal":
        assert before["durability"]["journal_degraded"] == 1
        assert after["durability"]["journal_degraded"] == 1
        assert after["refusal_count"] == 1
        assert after["refusals"][0]["reason"] == "retained"
    else:
        assert before["durability"]["error"]
        assert after["durability"]["error"]


def test_unwritable_observation_is_returned_in_run_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Even when no diagnostic file can be written, the caller gets degradation."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    lab.store.open_gate(root.root_id, halt_gate("test"))
    original = paths.write_durable

    def full_disk(path: Path, data: bytes) -> None:
        """Fail only advisory writes, leaving the workflow store operational."""
        if path.name in (HEARTBEAT_FILE, OBSERVATION_STATUS):
            raise OSError("observation disk full")
        original(path, data)

    monkeypatch.setattr(paths, "write_durable", full_disk)
    result = Foreman(lab.composition).run(root.root_id, poll_s=1, max_wall_s=10)
    assert result.ticks == 1
    assert "observation disk full" in result.observation.error
    monkeypatch.setattr(cli, "_composition", lambda _: lab.composition)
    assert cli.main(["status", root.root_id]) == 0
    assert json.loads(capsys.readouterr().out)["root_id"] == root.root_id


@pytest.mark.parametrize("filename", ["monitor.json", "wake-state.json"])
def test_malformed_monitor_files_do_not_break_status(
    tmp_path, monkeypatch, capsys, filename
):
    """A broken optional monitor cannot hide the workflow's ordinary status."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    path = lab.wiring().paths.instance_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("invalid json")
    monkeypatch.setattr(cli, "_composition", lambda _: lab.composition)
    capsys.readouterr()
    assert cli.main(["status", root.root_id]) == 0
    assert json.loads(capsys.readouterr().out)["monitor"]["monitor_degraded"]


@pytest.mark.parametrize("reader", ["read_start_time", "read_boot_id"])
def test_unreadable_proc_is_advisory_and_stale_only(tmp_path, monkeypatch, reader):
    """Missing identity cannot refuse a driver or become a proof of its death."""

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    lab.store.open_gate(root.root_id, halt_gate("test"))
    monkeypatch.setattr(heartbeat, reader, lambda *_: None)
    result = Foreman(lab.composition).run(root.root_id, poll_s=1, max_wall_s=10)
    assert result.ticks == 1
    record = read_record(lab.wiring().paths.driver_heartbeat, DriverHeartbeat)
    assert record.identity is None
    assert record.identity_degraded
    assert result.observation.identity_degraded

    def cannot_prove(*_):
        """An absent handle must never reach the process-death proof function."""
        pytest.fail("attempted to prove death without identity")

    monkeypatch.setattr(monitor, "prove_liveness", cannot_prove)
    with heartbeat.DriverObserver(lab.composition, root.root_id) as observer:
        observer.observe(TickReport(blocked=True))
        with monitor.WakeMonitor(lab.composition, root.root_id) as poller:
            poller.poll()
            lab.clock.sleep(121)
            poller.poll()
    events = lab.store.reads.list_wake_events(root.root_id)
    assert any(event.condition is WakeCondition.HEARTBEAT_STALE for event in events)
    assert not any(event.condition is WakeCondition.DRIVER_EXIT for event in events)


def test_heartbeat_preserves_concurrent_journal_saturation(tmp_path):
    """Saving advisory diagnostics must not clear a refusal journal's cap flag."""

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    with DriverObserver(lab.composition, root.root_id) as observer:
        paths.write_record(
            lab.wiring().paths.instance_dir / OBSERVATION_STATUS,
            ObservationStatus(saturated=True),
        )
        observer.observe(TickReport(blocked=True))
    assert read_record(
        lab.wiring().paths.instance_dir / OBSERVATION_STATUS, ObservationStatus
    ).saturated


def test_child_driver_continues_with_corrupt_heartbeat(tmp_path):
    """The child-drive loop keeps its normal gate result despite corrupt diagnostics."""

    lab, owner, composition, _ = writer_lab(tmp_path)
    coordinator = lab.store.coordination_store(composition=composition)
    child = coordinator.start_child(
        owner.root_id, "one", admission_of(owner, slot="one", generation=0)
    )
    wiring = composition.for_root(child.root_id)
    with wiring.band:
        wiring.store.open_gate(child.root_id, halt_gate("test"))
    heartbeat_path = wiring.paths.driver_heartbeat
    heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
    heartbeat_path.write_text("invalid json")
    result = coordinator.drive_children(owner.root_id, 1, 0.1)
    assert result.children[0].root_id == child.root_id
    assert "malformed" not in (result.children[0].attention or "")
    assert read_record(heartbeat_path, DriverHeartbeat) is not None
