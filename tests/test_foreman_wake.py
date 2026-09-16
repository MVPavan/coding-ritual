"""Driver observations survive process boundaries without granting authority."""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests._foreman import ForemanLab
from tests.test_foreman_main import _bridge_adapter, _bridge_lab, _bridge_stage
from workflow_interpreter.bdio.errors import BdioError
from workflow_interpreter.bridge import command
from workflow_interpreter.contracts.wake import WakeCondition
from workflow_interpreter.foreman import __main__ as cli
from workflow_interpreter.foreman import heartbeat, refusals
from workflow_interpreter.foreman import monitor as module
from workflow_interpreter.foreman.config import WakeConfig
from workflow_interpreter.foreman.gates import ensure_inbox, halt_gate
from workflow_interpreter.foreman.heartbeat import (
    DriverHeartbeat,
    DriverObserver,
    log_cursor,
)
from workflow_interpreter.foreman.monitor import (
    WakeMonitor,
    monitor_status,
    require_monitor,
)
from workflow_interpreter.foreman.refusals import (
    ObservationStatus,
    append_refusal,
    read_refusals,
)
from workflow_interpreter.foreman.tick import Foreman, RunReport, TickReport
from workflow_interpreter.foreman.wake import HookError, MonitorUnavailable
from workflow_interpreter.foreman.wake_constants import (
    OBSERVATION_STATUS,
    REFUSAL_JOURNAL,
    WAKE_STATE,
    DriverState,
)
from workflow_interpreter.schema.models import Outcome
from workflow_interpreter.supervisor.errors import LockUnavailable
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


def test_monitor_retains_rate_limited_conditions_across_restart(tmp_path):
    """Observing a condition never discards it before durable bd delivery."""

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    for number in range(2):
        append_refusal(
            lab.wiring().paths.instance_dir,
            gate_id=f"g-{number}",
            gate_key=str(number),
            payload=b"payload",
            signature=b"signature",
            error="bad",
            reason="refused",
            path=tmp_path / "refusal.json",
        )
    with WakeMonitor(lab.composition, root.root_id) as monitor:
        state = monitor.poll()
        assert len(lab.store.reads.list_wake_events(root.root_id)) == 1
        assert sum(delivery.event_id is None for delivery in state.deliveries) == 1
    with WakeMonitor(lab.composition, root.root_id) as monitor:
        monitor.poll()
        assert len(lab.store.reads.list_wake_events(root.root_id)) == 1
        lab.clock.sleep(31)
        monitor.poll()
        assert len(lab.store.reads.list_wake_events(root.root_id)) == 2


def test_monitor_stale_episodes_reset_only_after_heartbeat_advances(tmp_path):
    """Restart during a stale episode must not mint a new fire identity."""

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    with DriverObserver(lab.composition, root.root_id) as observer:
        with WakeMonitor(lab.composition, root.root_id) as monitor:
            monitor.poll()
            lab.clock.sleep(121)
            monitor.poll()
        with WakeMonitor(lab.composition, root.root_id) as monitor:
            lab.clock.sleep(121)
            monitor.poll()
            assert len(lab.store.reads.list_wake_events(root.root_id)) == 1
            observer.observe(TickReport(blocked=True))
            monitor.poll()
            lab.clock.sleep(121)
            monitor.poll()
        events = lab.store.reads.list_wake_events(root.root_id)
        assert len(events) == 2
        assert all(event.condition is WakeCondition.HEARTBEAT_STALE for event in events)
        assert events[0].cursor != events[1].cursor


def test_only_explicit_monitored_run_requires_a_healthy_monitor(tmp_path):
    """Monitor opt-in checks a real handle and startup acknowledgment before ticks."""

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    lab.store.open_gate(root.root_id, halt_gate("test"))
    foreman = Foreman(lab.composition)
    with pytest.raises(MonitorUnavailable):
        foreman.run(root.root_id, poll_s=1, max_wall_s=10, monitored=True)
    assert not lab.store.reads.list_activations(root.root_id)
    with WakeMonitor(lab.composition, root.root_id):
        assert (
            foreman.run(root.root_id, poll_s=1, max_wall_s=10, monitored=True).ticks
            == 1
        )
    with pytest.raises(MonitorUnavailable):
        foreman.run(root.root_id, poll_s=1, max_wall_s=10, monitored=True)
    assert foreman.run(root.root_id, poll_s=1, max_wall_s=10).ticks == 1


def test_monitor_lock_prevents_two_local_owners(tmp_path):
    """Only one local process can spend a root's delivery allowance at a time."""

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    with (
        WakeMonitor(lab.composition, root.root_id),
        pytest.raises(LockUnavailable),
        WakeMonitor(lab.composition, root.root_id),
    ):
        pytest.fail("second monitor acquired the same local lock")


def configured(lab, **updates):
    """Keep the monitor's trusted config injected, independent of graph inputs."""

    return replace(
        lab.composition,
        config=lab.config.model_copy(update={"wake": WakeConfig(**updates)}),
    )


def journal_condition(lab, identity):
    """Publish a distinct refusal condition without creating a routing bead."""

    return append_refusal(
        lab.wiring().paths.instance_dir,
        gate_id=identity,
        gate_key=identity,
        payload=b"payload",
        signature=b"signature",
        error="bad",
        reason="refused",
        path=lab.wiring().paths.instance_dir / "refusal.json",
    )


def test_lifetime_cap_is_reconciled_from_bd_across_restart(tmp_path):
    """Removing an empty local cursor cannot reset already committed event usage."""

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    composition = configured(lab, lifetime_cap=1)
    journal_condition(lab, "first")
    with WakeMonitor(composition, root.root_id) as monitor:
        assert monitor.poll().cap_exhausted
    (lab.wiring().paths.instance_dir / WAKE_STATE).unlink()
    journal_condition(lab, "second")
    with WakeMonitor(composition, root.root_id) as monitor:
        lab.clock.sleep(31)
        state = monitor.poll()
        assert state.cap_exhausted and state.saturated
        assert len(state.deliveries) == 1
        assert monitor_status(composition, root.root_id)["wake_cap_exhausted"]
    assert len(lab.store.reads.list_wake_events(root.root_id)) == 1


def test_closed_gate_is_discovered_between_monitor_polls(
    tmp_path, signing_config, sign_payload
):
    """Correcting/consuming a gate before a poll does not erase its opening."""

    lab = ForemanLab(tmp_path, signing=signing_config, signer=sign_payload)
    root = lab.instantiate()
    gate = lab.store.open_gate(root.root_id, halt_gate("test"))
    inbox = ensure_inbox(lab.wiring().paths, gate)
    (inbox / "payload.json").write_text("{}")
    (inbox / "payload.json.sig").write_text("invalid")
    assert lab.tick().refusals
    lab.approve(gate.gate_id, Outcome.APPROVE)
    assert gate.gate_id in lab.tick().closed_gates
    assert not (inbox / "refusal.json").exists()
    with WakeMonitor(lab.composition, root.root_id) as monitor:
        monitor.poll()
    events = lab.store.reads.list_wake_events(root.root_id)
    assert events[0].condition is WakeCondition.GATE_OPENED
    assert events[0].cursor.identity == gate.metadata.gate_key
    with WakeMonitor(lab.composition, root.root_id) as monitor:
        lab.clock.sleep(31)
        monitor.poll()
    assert any(
        event.condition is WakeCondition.REFUSAL
        for event in lab.store.reads.list_wake_events(root.root_id)
    )


def test_journal_cursor_reset_keeps_refusal_identity(tmp_path):
    """Truncating/replaying a journal never re-fires an acknowledged refusal."""

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    journal_condition(lab, "first")
    path = lab.wiring().paths.instance_dir / REFUSAL_JOURNAL
    original = path.read_bytes()
    with WakeMonitor(lab.composition, root.root_id) as monitor:
        monitor.poll()
        path.write_bytes(b"")
        assert monitor.poll().journal_generation == 1
        path.write_bytes(original)
        journal_condition(lab, "second")
        lab.clock.sleep(31)
        monitor.poll()
    assert len(lab.store.reads.list_wake_events(root.root_id)) == 2


@pytest.mark.parametrize("after_write", [False, True])
def test_monitor_crash_around_bd_write_replays_intent_once(
    tmp_path, monkeypatch, after_write
):
    """The durable intent survives either side of the event's commit window."""

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    journal_condition(lab, "first")
    append = lab.store.append_wake_event

    def crash(*args):
        if after_write:
            append(*args)
        raise RuntimeError("crash")

    with WakeMonitor(lab.composition, root.root_id) as monitor:
        monkeypatch.setattr(lab.store, "append_wake_event", crash)
        with pytest.raises(RuntimeError, match="crash"):
            monitor.poll()
    monkeypatch.setattr(lab.store, "append_wake_event", append)
    with WakeMonitor(lab.composition, root.root_id) as monitor:
        lab.clock.sleep(31)
        state = monitor.poll()
        assert state.deliveries[0].acknowledged
    assert len(lab.store.reads.list_wake_events(root.root_id)) == 1


def test_hook_crash_before_ack_retries_same_fire_key(tmp_path, monkeypatch):
    """At-least-once external effects repeat only under the same dedupe key."""

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    journal_condition(lab, "first")
    composition = configured(lab, hook_argv=("trusted-hook",))
    calls = []

    def crash_after_effect(event, *_):
        calls.append(event.fire_key)
        if len(calls) == 1:
            raise RuntimeError("crash after external effect")

    monkeypatch.setattr(module, "run_hook", crash_after_effect)
    with (
        module.WakeMonitor(composition, root.root_id) as monitor,
        pytest.raises(RuntimeError),
    ):
        monitor.poll()
    with module.WakeMonitor(composition, root.root_id) as monitor:
        lab.clock.sleep(6)
        state = monitor.poll()
        assert state.deliveries[0].acknowledged
        assert state.deliveries[0].attempts == 2
    with module.WakeMonitor(composition, root.root_id) as monitor:
        monitor.poll()
    assert len(calls) == 2 and calls[0] == calls[1]
    assert len(lab.store.reads.list_wake_events(root.root_id)) == 1


def test_hook_attempt_cap_survives_restart(tmp_path, monkeypatch):
    """An exhausted hook stays visible and cannot retry forever across restarts."""

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    journal_condition(lab, "first")
    composition = configured(lab, hook_argv=("trusted-hook",))
    calls = []

    def failed(event, *_):
        calls.append(event.fire_key)
        raise HookError("failed")

    monkeypatch.setattr(module, "run_hook", failed)
    for _ in range(5):
        with module.WakeMonitor(composition, root.root_id) as monitor:
            lab.clock.sleep(31)
            monitor.poll()
    assert len(calls) == 3
    status = module.monitor_status(composition, root.root_id)
    assert status["exhausted_hooks"] == 1
    assert status["last_delivery_error"] == "failed"


def test_oversize_status_preserves_refusal_attention(capsys):
    """Diagnostic volume must not turn a refusal into an opaque truncated flag."""

    observation = {"refusals": [{"gate_id": "g", "reason": "bad signature"}]}
    cli._emit(json.dumps({"observation": observation, "large": "x" * 20000}))
    result = json.loads(capsys.readouterr().out)
    assert result["truncated"]
    assert result["observation"] == observation


def test_bd_failure_keeps_pending_and_does_not_call_hook(tmp_path, monkeypatch):
    """A failed durable fire cannot claim delivery or invoke its external effect."""

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    journal_condition(lab, "first")
    composition = configured(lab, hook_argv=("trusted-hook",))
    calls = []
    monkeypatch.setattr(module, "run_hook", lambda *args: calls.append(args))
    original = lab.store.append_wake_event

    def unavailable(*_):
        raise BdioError("database unavailable")

    monkeypatch.setattr(lab.store, "append_wake_event", unavailable)
    with module.WakeMonitor(composition, root.root_id) as monitor:
        state = monitor.poll()
        assert state.last_error == "database unavailable"
        assert state.deliveries[0].event_id is None
        assert not state.deliveries[0].acknowledged
        assert not calls
    monkeypatch.setattr(lab.store, "append_wake_event", original)
    with module.WakeMonitor(composition, root.root_id) as monitor:
        lab.clock.sleep(31)
        assert monitor.poll().deliveries[0].acknowledged
    assert len(calls) == 1


def test_monitor_cli_never_resolves_a_model(tmp_path, monkeypatch, capsys):
    """The independent command observes and fires without entering runner dispatch."""

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    journal_condition(lab, "first")
    monkeypatch.setattr(cli, "_composition", lambda _: lab.composition)
    sessions = []
    monkeypatch.setattr(cli.os, "getpgrp", lambda: -1)
    monkeypatch.setattr(cli.os, "setsid", lambda: sessions.append(True))

    def forbidden(*_):
        pytest.fail("monitor entered model dispatch")

    monkeypatch.setattr(lab.profiles, "profile_for", forbidden)
    monkeypatch.setattr(lab.composition.spawner, "launch", forbidden)
    assert cli.main(["monitor", root.root_id, "--max-wall", "0"]) == 0
    assert sessions == [True]
    assert len(lab.store.reads.list_wake_events(root.root_id)) == 1
    assert json.loads(capsys.readouterr().out)["health"] == "stopped"


def test_stale_monitor_ack_does_not_authorize_startup(tmp_path):
    """A live process with an old acknowledgment is not a healthy monitor."""

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    with WakeMonitor(lab.composition, root.root_id):
        lab.clock.sleep(121)
        with pytest.raises(MonitorUnavailable):
            require_monitor(lab.composition, root.root_id)


def test_terminal_and_normal_driver_stop_have_distinct_stable_fires(tmp_path):
    """Terminal and expected stop are separate observations, deduped on restart."""

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    lab.store.settle_root(root.root_id, "abandoned")
    with DriverObserver(lab.composition, root.root_id) as observer:
        observer.observe(TickReport(terminal=True, terminal_node="abandoned"))
    for _ in range(3):
        with WakeMonitor(lab.composition, root.root_id) as monitor:
            lab.clock.sleep(31)
            monitor.poll()
    events = lab.store.reads.list_wake_events(root.root_id)
    assert {event.condition for event in events} == {
        WakeCondition.ROOT_TERMINAL,
        WakeCondition.DRIVER_EXIT,
    }
    assert len(events) == 2
    assert (
        next(e for e in events if e.condition is WakeCondition.DRIVER_EXIT).detail
        == "terminal"
    )


@pytest.mark.parametrize(
    "bounds",
    [
        {"poll_s": 0},
        {"stale_s": 5},
        {"min_fire_interval_s": float("inf")},
        {"lifetime_cap": 0},
        {"hook_timeout_s": 11},
        {"hook_backoff_s": -1},
        {"hook_argv": ("bad\x00command",)},
    ],
)
def test_wake_config_rejects_invalid_bounds(bounds):
    """All operator bounds are finite, positive, and consistent before polling."""

    with pytest.raises(ValidationError):
        WakeConfig(**bounds)


def test_crash_after_hook_ack_does_not_replay(tmp_path, monkeypatch):
    """An acknowledged effect stays acknowledged even if the monitor crashes next."""

    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    journal_condition(lab, "first")
    composition = configured(lab, hook_argv=("trusted-hook",))
    calls = []
    monkeypatch.setattr(
        module, "run_hook", lambda event, *_: calls.append(event.fire_key)
    )
    with module.WakeMonitor(composition, root.root_id) as monitor:
        replace_delivery = monitor._replace

        def crash_after_ack(delivery):
            replace_delivery(delivery)
            if delivery.acknowledged:
                raise RuntimeError("crash after acknowledgment")

        monkeypatch.setattr(monitor, "_replace", crash_after_ack)
        with pytest.raises(RuntimeError):
            monitor.poll()
    with module.WakeMonitor(composition, root.root_id) as monitor:
        lab.clock.sleep(31)
        state = monitor.poll()
        assert state.deliveries[0].acknowledged
    assert len(calls) == 1


def test_oversize_durability_detail_cannot_hide_refusal(capsys):
    """When observation detail itself exceeds the CLI cap, attention survives."""
    cli._emit(
        json.dumps(
            {
                "observation": {
                    "refusals": [{"gate_id": "g", "reason": "bad signature"}],
                    "durability": {"error": "x" * 10000},
                }
            }
        )
    )
    output = capsys.readouterr().out
    assert len(output.encode()) <= 4096
    assert json.loads(output)["attention"]
