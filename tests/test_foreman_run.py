"""Phase-6 slice D: the unattended `run` loop and what it renders at a gate.

`run` is the first caller that ticks more than once without a human between
the ticks, so every stop condition here is really the question "can this loop
end?": an OPEN gate is never a routing head (`frontier.py`'s `candidates_g`
requires a decided gate), so before `waiting_gate` existed a `tick()` against
an open `ship` returned a wholly default report and any loop over it spun.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests._bdio import make_root
from tests._foreman import ForemanLab, LockedPersistentBd
from tests._helpers import undeclared_fail_code_graph
from tests._supervisor import (
    FAILING_SCRIPT,
    VERIFY_SCRIPT,
    ChildScript,
)
from workflow_interpreter.foreman import __main__ as main_module
from workflow_interpreter.foreman.constants import RUN_MAX_WALL
from workflow_interpreter.foreman.tick import RunReport
from workflow_interpreter.supervisor.band import BandLock

# implement dispatch, implement settle, review dispatch, review settle, and
# the routed tick that opens `ship`: the whole unattended lifecycle of the
# shipped feature-delivery graph, with no human input anywhere in it.
TICKS_TO_SHIP = 5

FINDINGS_FILE = "review.md"

# The lab's clock is the SUPERVISOR's clock too, and its watch loop sleeps on
# it once a second while a child runs, so a run's own polls are counted by an
# interval nothing else uses rather than by the length of `clock.sleeps`.
POLL_S = 7.0

IMPLEMENT_SCRIPT = ChildScript(
    marker='{"outcome":"done"}\n',
    effects='{"paths":["src/feature.py"]}',
    write_path="src/feature.py",
    write_body="value = 3\n",
    commit=True,
)
REVIEW_SCRIPT_ACCEPT = ChildScript(
    marker='{"outcome":"accept"}\n',
    effects='{"paths":[]}',
    artifact_path=FINDINGS_FILE,
    artifact_body="no blockers",
)


def _unattended(lab: ForemanLab) -> ForemanLab:
    """Bind one script per node so the whole run needs no per-tick queueing."""
    lab.profiles.bind_node("implement", IMPLEMENT_SCRIPT)
    lab.profiles.bind_node("review", REVIEW_SCRIPT_ACCEPT)
    return lab


def _run(
    lab: ForemanLab, *, poll_s: float = POLL_S, max_wall_s: float = 3600.0
) -> RunReport:
    """Run the lab's foreman to its next stop with no real sleeping."""
    assert lab.root is not None
    return lab.foreman.run(lab.root.root_id, poll_s=poll_s, max_wall_s=max_wall_s)


def _report_line(transcript: str, marker: str) -> dict[str, Any]:
    """Select the one emitted JSON report out of a structlog-mixed capture."""
    line = next(line for line in transcript.splitlines() if marker in line)
    parsed = json.loads(line)
    assert isinstance(parsed, dict)
    return parsed


def _drive_to_ship(lab: ForemanLab) -> str:
    """Tick the lab to its open `ship` gate and return that gate's id."""
    for _ in range(TICKS_TO_SHIP - 1):
        lab.tick()
    gate_id = lab.tick().opened_gate
    assert gate_id is not None
    assert lab.store.reads.load_gate(gate_id).metadata.gate_node == "ship"
    return gate_id


def test_a_tick_against_an_open_gate_reports_the_gate_it_waits_on(
    tmp_path: Path,
) -> None:
    """The empty-report case: an open `ship` is a human, not a dead loop."""
    lab = _unattended(ForemanLab(tmp_path))
    lab.instantiate()
    gate_id = _drive_to_ship(lab)

    report = lab.tick()

    assert report.waiting_gate == gate_id
    assert report.model_dump(exclude={"waiting_gate"}) == {
        "blocked": False,
        "halted": False,
        "stalled": None,
        "contended": False,
        "dispatched": None,
        "settled": None,
        "opened_gate": None,
        "closed_gates": (),
        "refusals": (),
        "events_backfilled": 0,
        "terminal": False,
    }


def test_run_reaches_the_ship_gate_unattended_in_a_bounded_tick_count(
    tmp_path: Path,
) -> None:
    """Zero human input from `create` to the gate a human must answer."""
    lab = _unattended(ForemanLab(tmp_path))
    lab.instantiate()

    result = _run(lab)

    assert result.ticks == TICKS_TO_SHIP
    assert result.report.opened_gate is not None
    gate = lab.store.reads.load_gate(result.report.opened_gate)
    assert gate.metadata.gate_node == "ship"
    assert result.report.stalled is None
    assert lab.clock.sleeps.count(POLL_S) == 0


def test_run_returns_immediately_when_the_gate_is_already_open(
    tmp_path: Path,
) -> None:
    """A restarted `run` reports the wait rather than spinning on it."""
    lab = _unattended(ForemanLab(tmp_path))
    lab.instantiate()
    gate_id = _run(lab).report.opened_gate

    result = _run(lab)

    assert result.ticks == 1
    assert result.report.waiting_gate == gate_id
    assert result.report.opened_gate is None


def test_a_band_miss_is_contended_and_run_polls_past_it(tmp_path: Path) -> None:
    """A lock miss is transient; only a real stall may end the loop."""
    lab = _unattended(ForemanLab(tmp_path))
    lab.instantiate()
    held = BandLock(lab.wiring().paths.band_lock)
    held.acquire()
    try:
        contended = lab.tick()

        assert contended.contended is True
        assert contended.stalled is None

        lab.clock.on_sleep.append(held.release)
        result = _run(lab)
    finally:
        held.release()

    assert lab.clock.sleeps.count(POLL_S) == 1
    assert result.ticks == TICKS_TO_SHIP + 1
    assert result.report.opened_gate is not None


def test_run_stops_at_its_max_wall_with_a_stalled_report(tmp_path: Path) -> None:
    """The wall is the loop's only bound when nothing else can end it."""
    lab = _unattended(ForemanLab(tmp_path))
    lab.instantiate()
    held = BandLock(lab.wiring().paths.band_lock)
    held.acquire()
    try:
        result = _run(lab, poll_s=60.0, max_wall_s=100.0)
    finally:
        held.release()

    assert result.report.stalled == RUN_MAX_WALL
    assert result.ticks == 3
    assert lab.clock.sleeps == [60.0, 60.0]  # nothing else could sleep: no tick ran


def test_a_restarted_foreman_converges_on_the_same_gate(tmp_path: Path) -> None:
    """Drill 27 shape: kill `run` at the gate, rebuild, run again."""
    state = tmp_path / "persistent-bd.json"

    def persistent(workspace: str) -> LockedPersistentBd:
        return LockedPersistentBd(workspace, state)

    lab = _unattended(ForemanLab(tmp_path, bd_factory=persistent))
    root = lab.instantiate()
    gate_id = _run(lab).report.opened_gate
    assert gate_id is not None
    activations = len(lab.store.reads.list_activations(root.root_id))

    lab.rebuild()
    _unattended(lab)
    result = _run(lab)

    assert result.ticks == 1
    assert result.report.waiting_gate == gate_id
    assert [gate["id"] for gate in lab.beads("gate")] == [gate_id]
    assert len(lab.store.reads.list_activations(root.root_id)) == activations


def test_gate_rendering_carries_the_cumulative_diff_and_the_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What a §9 approver reads before signing: the diff, and where to look."""
    lab = _unattended(ForemanLab(tmp_path))
    root = lab.instantiate()
    gate_id = _run(lab).report.opened_gate
    assert gate_id is not None
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)

    _, status = lab.transcript(lambda: main_module.main(["status", root.root_id]))
    _, rerun = lab.transcript(
        lambda: main_module.main(["run", root.root_id, "--poll", "0"])
    )

    for transcript, marker in ((status, '"root_id"'), (rerun, '"ticks"')):
        entry = next(
            gate
            for gate in _report_line(transcript, marker)["open_gates"]
            if gate["gate_id"] == gate_id
        )
        assert "src/feature.py" in entry["diff_stat"]
        assert entry["findings"] == [FINDINGS_FILE]

    halted = ForemanLab(tmp_path / "halt", toml=undeclared_fail_code_graph(tmp_path))
    halted.pin_checks({VERIFY_SCRIPT: FAILING_SCRIPT})
    halt_root = halted.instantiate()
    _unattended(halted)
    halt_gate_id = _run(halted).report.opened_gate
    monkeypatch.setattr(main_module, "_composition", lambda _: halted.composition)

    _, halt_status = halted.transcript(
        lambda: main_module.main(["status", halt_root.root_id])
    )

    halt_entry = next(
        gate
        for gate in _report_line(halt_status, '"root_id"')["open_gates"]
        if gate["gate_id"] == halt_gate_id
    )
    assert halt_entry["diff_stat"] == "(no artifact)"


def test_the_run_command_exits_zero_at_a_gate_and_one_on_a_stall(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The CLI's only two answers: a human is needed, or the loop broke."""
    lab = _unattended(ForemanLab(tmp_path))
    root = lab.instantiate()
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)
    codes: list[int] = []

    _, transcript = lab.transcript(
        lambda: codes.append(
            # A generous wall: the lab clock advances by the SUPERVISOR's own
            # watch-loop sleeps, so a one-second wall would trip on the first
            # dispatch rather than on anything this test is about.
            main_module.main(["run", root.root_id, "--poll", "0", "--max-wall", "3600"])
        )
    )

    assert codes == [0]
    assert _report_line(transcript, '"ticks"')["ticks"] == TICKS_TO_SHIP

    # A root nothing instantiated: with no pinned base commit there is no
    # instance branch to mint against, which `tick()` converts to a stall
    # rather than to a traceback.
    orphan = make_root(lab.store, lab.definition)
    _, stalled = lab.transcript(
        lambda: codes.append(main_module.main(["run", orphan.root_id, "--poll", "0"]))
    )

    assert codes == [0, 1]
    assert "instance base commit is missing" in stalled


def test_the_reported_gate_inbox_exists_as_soon_as_the_gate_opens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """cr-o85.34.16: `status` names a directory the approver can write into.

    Nothing but the tick that opens the gate knows the inbox is needed, and
    `scripts/approve-gate.sh` refuses a missing one, so an absent directory
    made every approval start with a hand-run `mkdir -p`.
    """
    lab = _unattended(ForemanLab(tmp_path))
    root = lab.instantiate()
    gate_id = _drive_to_ship(lab)
    monkeypatch.setattr(main_module, "_composition", lambda _: lab.composition)

    _, status = lab.transcript(lambda: main_module.main(["status", root.root_id]))

    entry = next(
        gate
        for gate in _report_line(status, '"root_id"')["open_gates"]
        if gate["gate_id"] == gate_id
    )
    assert Path(entry["inbox"]).is_dir()
