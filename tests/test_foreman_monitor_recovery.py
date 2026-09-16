"""Monitor recovery keeps notification failures visible and bounded."""

import json
from pathlib import Path

import pytest

from tests._foreman import ForemanLab
from tests.test_bdio_wake import event_for
from tests.test_foreman_wake import journal_condition
from workflow_interpreter.bdio.errors import StoreError
from workflow_interpreter.foreman import __main__ as cli
from workflow_interpreter.foreman import monitor as module
from workflow_interpreter.foreman.heartbeat import observation_status
from workflow_interpreter.foreman.monitor import WakeMonitor, monitor_status
from workflow_interpreter.foreman.wake import MonitorUnavailable
from workflow_interpreter.foreman.wake_constants import REFUSAL_JOURNAL


def test_legacy_null_event_does_not_block_wakes(tmp_path: Path) -> None:
    """A legacy metadata-only event does not poison reconciliation or new delivery."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    legacy = lab.store.append_wake_event(root.root_id, event_for(root, "legacy"))
    lab.fake_bd.rows[legacy.id]["payload"] = None
    journal_condition(lab, "new")
    with WakeMonitor(lab.composition, root.root_id) as monitor:
        state = monitor.poll()
    assert len(lab.store.reads.list_wake_events(root.root_id)) == 1
    assert state.deliveries[0].acknowledged


def test_reconcile_failure_is_visible_across_restart(tmp_path, monkeypatch):
    """A responsive monitor still reports that it cannot reconcile delivery state."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    original = lab.store.reads.list_wake_events

    def unavailable(*_):
        """Fail only the wake reader, preserving ordinary root/status reads."""
        raise StoreError("wake reads unavailable")

    with WakeMonitor(lab.composition, root.root_id) as monitor:
        monkeypatch.setattr(lab.store.reads, "list_wake_events", unavailable)
        for _ in range(2):
            monitor.poll()
        assert (
            monitor_status(lab.composition, root.root_id)["monitor_degraded"]
            == "wake reads unavailable"
        )
    with WakeMonitor(lab.composition, root.root_id) as monitor:
        assert monitor.poll().monitor_degraded == "wake reads unavailable"
        monkeypatch.setattr(lab.store.reads, "list_wake_events", original)
        monitor.poll()
        assert not monitor_status(lab.composition, root.root_id)["monitor_degraded"]


def test_reconciled_capacity_has_its_own_refusal(tmp_path, monkeypatch):
    """Oversized recovered state is a capacity failure, not a root identity claim."""

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    for cursor in ("one", "two"):
        lab.store.append_wake_event(root.root_id, event_for(root, cursor))
    monkeypatch.setattr(module, "MAX_EVENT_CAP", 1)
    with (
        pytest.raises(MonitorUnavailable, match="capacity"),
        WakeMonitor(lab.composition, root.root_id),
    ):
        pytest.fail("reconciliation accepted more records than its bound")


def test_replaced_journal_regrowth_is_replayed_by_identity(tmp_path):
    """Replacement past the saved offset cannot erase an unseen refusal."""

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    journal_condition(lab, "first")
    path = lab.wiring().paths.instance_dir / REFUSAL_JOURNAL
    with WakeMonitor(lab.composition, root.root_id) as monitor:
        before = monitor.poll()
    with path.open("rb"):
        path.unlink()
        journal_condition(lab, "second-" + "x" * 300)
        assert path.stat().st_size > before.journal_offset
        with WakeMonitor(lab.composition, root.root_id) as monitor:
            lab.clock.sleep(31)
            after = monitor.poll()
    assert len(lab.store.reads.list_wake_events(root.root_id)) == 2
    assert after.journal_generation > before.journal_generation


def test_monitor_skips_corrupt_journal_line_and_delivers_valid_refusal(tmp_path):
    """An advisory corrupt line does not abort delivery of later readable evidence."""

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    journal_condition(lab, "valid")
    path = lab.wiring().paths.instance_dir / REFUSAL_JOURNAL
    path.write_bytes(b"invalid json\n" + path.read_bytes())
    with WakeMonitor(lab.composition, root.root_id) as monitor:
        state = monitor.poll()
    assert state.deliveries[0].acknowledged
    status = observation_status(lab.wiring().paths.instance_dir, lab.clock)
    assert status["durability"]["journal_degraded"] == 1


def test_monitor_cli_maps_lock_contention_to_refusal(tmp_path, monkeypatch, capsys):
    """A second local monitor reports contention without a traceback."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    monkeypatch.setattr(cli, "_composition", lambda _: lab.composition)
    monkeypatch.setattr(cli.os, "setsid", lambda: None)
    with WakeMonitor(lab.composition, root.root_id):
        capsys.readouterr()
        assert cli.main(["monitor", root.root_id, "--max-wall", "0"]) == 2
        output = capsys.readouterr()
        report = json.loads(output.out)
        assert report["attention"]
        assert "lock" in report["reason"].lower()
        assert "Traceback" not in output.err
