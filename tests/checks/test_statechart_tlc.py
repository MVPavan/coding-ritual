"""statechart's TLC layer: configuration, pinned runs, messages and the
rule loop, replayed from what the real jar printed for our fixture models."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True  # no bytecode beside the shipped scripts
sys.path.insert(0, str(ROOT / ".claude/skills/statechart/scripts"))

from statechart_lib import tlc

FIXTURES = ROOT / "tests/fixtures/statechart"
MODELS = FIXTURES / "models"


class Replay:
    """A runner that hands back the recorded runs of one case, in order,
    failing when the check asks for a run the recording did not make."""

    def __init__(self, case: str) -> None:
        data = json.loads((FIXTURES / "recorded" / f"{case}.json").read_text())
        self.runs: list[dict[str, object]] = data["runs"]
        self.spec = MODELS / data["spec"]
        self.bound: int = data["bound"]
        self.config = tlc.parse_config(self.spec.with_suffix(".cfg"))
        self.asked: list[tlc.Request] = []
        self.levels: dict[str, str] = {}

    def __call__(self, request: tlc.Request) -> tlc.Result:
        run = self.runs[len(self.asked)]
        assert run["request"] == request.describe()
        self.asked.append(request)
        return tlc.Result(int(str(run["code"])), str(run["output"]), str(run["dot"]))

    def check(self) -> tlc.Verdicts:
        verdicts = tlc.check(self.config, self, self.bound)
        self.levels = tlc.property_levels(self.config, self)
        assert len(self.asked) == len(self.runs)
        return verdicts


def test_runs_are_pinned_and_find_sibling_modules(tmp_path: Path) -> None:
    spec = MODELS / "sib/UsesHelper.tla"
    config = tlc.parse_config(spec.with_suffix(".cfg"))
    runner = tlc.JavaRunner("java", Path("t.jar"), spec, config, tmp_path)
    command = runner.command(tlc.Request((), (), False, bounded=True), tmp_path)
    joined = " ".join(command)
    assert "-workers 1 -fp 0 -seed 0 -lncheck final" in joined
    assert f"-DTLA-Library={spec.parent}" in command
    assert "-deadlock" in command and "-continue" not in command
    wrapper = (tmp_path / f"{tlc.BOUND_MODULE}.tla").read_text()
    assert (
        "EXTENDS UsesHelper, Naturals, TLC" in wrapper
        and 'TLCGet("distinct") < 100000' in wrapper
    )
    assert f"CONSTRAINT {tlc.BOUND_OP}" in (tmp_path / "rules.cfg").read_text()


def test_configuration_rules_and_settings_are_read() -> None:
    config = tlc.parse_config(MODELS / "Counter.cfg")
    assert config.invariants == ("TypeOK", "SumSmall", "XNotThree")
    assert config.check_deadlock and not config.constrained
    assert config.kept.strip() == "SPECIFICATION Spec"
    assert tlc.parse_config(MODELS / "Fence.cfg").constrained
    assert not tlc.parse_config(MODELS / "Big.cfg").check_deadlock


@pytest.mark.parametrize(
    ("text", "where"),
    [
        ("Spec\nINIT Init\n", ":1: expected a keyword"),
        ("INIT Init\nINVARIANT Ok {x}\n", ":2: '{' is not a rule name"),
        ("INIT Init\n\nCHECK_DEADLOCK maybe\n", ":3: CHECK_DEADLOCK takes"),
        ("INIT Init\nALIAS A\n", ":2: ALIAS changes how TLC prints"),
    ],
)
def test_invalid_configuration_refused_with_file_and_line(
    tmp_path: Path, text: str, where: str
) -> None:
    path = tmp_path / "M.cfg"
    path.write_text(text)
    with pytest.raises(tlc.InputError, match=where):
        tlc.parse_config(path)


@pytest.mark.parametrize(
    ("case", "where"),
    [("Bad", "Bad.tla:5:20"), ("Undef", "Undef.tla:5:18"), ("Ghost", "Ghost.cfg:2")],
)
def test_invalid_spec_refused_before_any_check(case: str, where: str) -> None:
    with pytest.raises(tlc.InputError, match=where):
        Replay(case).check()


def test_holding_model_gets_every_verdict_from_one_run() -> None:
    verdicts = Replay("Light").check()
    assert verdicts.holds == ["TypeOK", "EventuallyGreen", "NoDeadlock"]
    assert not verdicts.broken and not verdicts.unchecked


def test_each_broken_rule_dropped_and_rerun_until_none_breaks() -> None:
    replay = Replay("Counter")
    verdicts = replay.check()
    assert set(verdicts.broken) == {"SumSmall", "XNotThree"}
    assert verdicts.holds == ["TypeOK", "NoDeadlock"]
    assert [r.as_written for r in replay.asked] == [True, False, False, False, False]
    assert all(r.bounded for r in replay.asked[1:])
    # One run per broken invariant keeps going past every state breaking it,
    # as TLC names only one broken invariant per state.
    assert [r.invariants for r in replay.asked if r.keep_going] == [
        ("XNotThree",),  # found first: x = 3 is nearer the start
        ("SumSmall",),
    ]
    assert len(verdicts.violations["SumSmall"]) == 6
    assert len(verdicts.violations["XNotThree"]) == 4
    trace = verdicts.broken["SumSmall"].trace
    assert len(trace.steps) == 5 and trace.steps[0].action is None


def test_deadlock_named_and_renamed_when_a_rule_has_the_name() -> None:
    assert set(Replay("Stuck").check().broken) == {"NoDeadlock"}
    named = Replay("Named").check()
    assert set(named.broken) == {"CheckDeadlock"} and named.holds == ["NoDeadlock"]
    assert "NoDeadlock" not in Replay("Checkout").check().broken


def test_temporal_properties_get_runs_of_their_own() -> None:
    replay = Replay("InitOnly")
    verdicts = replay.check()
    checks = [r.properties for r in replay.asked[1:] if not r.probe]
    assert checks == [("Small",), ("Wrapped",)]
    assert verdicts.holds == ["Small"] and set(verdicts.broken) == {"Wrapped"}


def test_liveness_counterexample_loop_and_stutter() -> None:
    loop = Replay("Loop").check().broken["EventuallyDone"].trace
    assert (loop.back_to, loop.back_action, loop.stutters) == (1, "Back", False)
    stall = Replay("Stall").check().broken["EventuallyDone"].trace
    assert stall.stutters and stall.back_to is None


def test_reruns_after_a_break_stop_at_the_bound() -> None:
    verdicts = Replay("Big-bound").check()
    assert set(verdicts.broken) == {"Small"}
    assert verdicts.unchecked == {
        "Fine": "the run stopped at the bound of 100 distinct states"
    }
    assert verdicts.graph_partial
    assert Replay("Big").check().holds == ["Fine"]


def test_checker_error_stops_with_its_messages_and_unchecked_rules() -> None:
    with pytest.raises(tlc.CheckError) as stopped:
        Replay("DivZero").check()
    assert "unchecked: NoDeadlock" in str(stopped.value)
    assert "The second argument of \\div is 0." in stopped.value.excerpt
    assert "Parsing file" not in stopped.value.excerpt


def test_break_without_a_named_rule_is_an_error_with_the_output_tail() -> None:
    with pytest.raises(tlc.CheckError, match="without naming a broken rule") as stopped:
        Replay("Asrt").check()
    assert "x got too big" in stopped.value.excerpt
    request = tlc.Request(("Ok",), (), True)
    assert tlc.judge(tlc.Result(12, "no message\n", ""), request).kind == "unnamed"


def test_continue_run_exit_zero_is_never_a_verdict() -> None:
    graph_run = Replay("Counter").runs[-1]
    assert graph_run["code"] == 0  # TLC exits 0 under -continue despite violations
    request = tlc.Request(("SumSmall",), (), False, keep_going=True)
    outcome = tlc.judge(tlc.Result(0, str(graph_run["output"]), ""), request)
    assert outcome.kind == "holds" and outcome.violations["SumSmall"]


def test_empty_model_says_why() -> None:
    assert Replay("NoInit").check().empty == "no state satisfies the initial condition"
    assert (
        Replay("Outside").check().empty
        == "every initial state lies outside the constraints"
    )


# Recorded from the real jar: TLC refuses a temporal property as an invariant
# (message 2146) and checks a state predicate on the initial states.
@pytest.mark.parametrize(
    ("case", "levels"),
    [
        ("Light", {}),  # <>
        ("Temporals", {}),  # a [] under a LET; an operator whose body is temporal
        ("Loop", {}),
        ("InitOnly", {"Small": "initial"}),  # Wrapped names a temporal operator
        ("InitialProperty", {"Small": "initial"}),  # breaks in the initial state
        ("InitialWarning", {"Small": "initial", "Indented": "initial"}),
        ("UnusedTemporal", {"Small": "initial"}),  # an unused temporal LET
        ("TrailingTheorem", {"Small": "initial"}),
        ("UnusedArgument", {"Small": "initial"}),  # a LET ignoring its argument
        ("TopArgument", {"Small": "initial"}),
        ("CompactInfix", {"Small": "initial"}),  # a++b == []TRUE follows
        ("MultilineHead", {"Small": "initial"}),  # Unused\n  == []TRUE follows
        ("SameLine", {"Small": "initial"}),  # Unused == []TRUE on Small's line
        ("InitSlowRepeat", {"Small": "unsure"}),  # the probe ran out of time
        ("BoxFirst", {}),
        ("BoxLater", {}),
    ],
)
def test_tlc_decides_each_property_level(case: str, levels: dict[str, str]) -> None:
    replay = Replay(case)
    verdicts = replay.check()
    assert replay.levels == levels
    probes = [r for r in replay.asked if r.probe]
    assert [r.invariants for r in probes] == [(p,) for p in replay.config.properties]
    assert all(r.bounded and not r.properties for r in probes)
    assert all(r.timeout == tlc.PROBE_SECONDS for r in probes)
    if case in ("UnusedTemporal", "TrailingTheorem", "UnusedArgument", "TopArgument",
                "CompactInfix", "MultilineHead", "SameLine"):  # fmt: skip
        assert "Small" in verdicts.holds  # though x = 1 is reachable


def test_property_level_unsure_on_any_other_probe_outcome(tmp_path: Path) -> None:
    config = tlc.parse_config(MODELS / "UnusedTemporal.cfg")
    for code in (75, 151, 255):  # an evaluation error, a refused name, a crash

        def runner(_: tlc.Request, code: int = code) -> tlc.Result:
            return tlc.Result(code, "", "")

        assert tlc.property_levels(config, runner) == {"Small": "unsure"}
    java = tlc.JavaRunner(
        "java", Path("t.jar"), MODELS / "UnusedTemporal.tla", config, tmp_path
    )
    probe = tlc.Request(("Small",), (), False, bounded=True, probe=True)
    command = java.command(probe, tmp_path)
    assert "-deadlock" in command
    rules = (tmp_path / "rules.cfg").read_text()
    assert "INVARIANTS Small" in rules and "PROPERT" not in rules
    assert f"CONSTRAINT {tlc.BOUND_OP}" in rules and "INIT Init" in rules
    wrapper = (tmp_path / f"{tlc.BOUND_MODULE}.tla").read_text()
    assert 'TLCGet("distinct") < 0' in wrapper  # TLC refuses a constant FALSE


def test_deadlock_rule_name_is_unused_by_every_configured_rule(tmp_path: Path) -> None:
    path = tmp_path / "M.cfg"
    path.write_text("INIT Init\nINVARIANTS NoDeadlock CheckDeadlock NoDeadlock2\n")
    assert tlc.deadlock_name(tlc.parse_config(path)) == "NoDeadlock3"
    verdicts = Replay("Collision").check()
    assert verdicts.deadlock_rule == "NoDeadlock2"
    assert {r: (b.kind, len(b.trace.steps)) for r, b in verdicts.broken.items()} == {
        "CheckDeadlock": ("invariant", 2),
        "NoDeadlock": ("invariant", 3),
        "NoDeadlock2": ("deadlock", 3),
    }


def test_initial_state_property_break_is_named() -> None:
    verdicts = Replay("InitialProperty").check()
    found = verdicts.broken["Small"]
    assert found.kind == "initial" and len(found.trace.steps) == 1
    assert found.trace.steps[0].text.strip() == "x = 0"
    assert verdicts.holds == ["NoDeadlock"]


def test_error_in_a_drawing_run_is_kept_and_the_graph_marked_incomplete() -> None:
    verdicts = Replay("AfterError").check()
    assert set(verdicts.broken) == {"Small"}
    assert verdicts.graph_partial is not None
    assert verdicts.graph_partial.endswith("The second argument of \\div is 0")
    assert "\\div is 0" in verdicts.logs["tlc-draw-Small.out"]


def test_configuration_strings_and_nested_comments_survive_first_run_and_reruns(
    tmp_path: Path,
) -> None:
    config = tlc.parse_config(MODELS / "Quoted.cfg")
    assert config.invariants == ("Small", "Named")
    assert 'CONSTANT A = "INVARIANT (* \\\\* *)"' in config.kept
    runner = tlc.JavaRunner(
        "java", Path("t.jar"), MODELS / "Quoted.tla", config, tmp_path
    )
    runner.command(tlc.Request(("Named",), (), True, bounded=True), tmp_path)
    assert tlc.parse_config(tmp_path / "rules.cfg").invariants == ("Named",)
    replay = Replay("Quoted")
    verdicts = replay.check()
    assert set(verdicts.broken) == {"Small", "NoDeadlock"} and "Named" in verdicts.holds
    assert not replay.asked[0].bounded and replay.asked[1].bounded


def test_empty_model_only_from_a_successful_run() -> None:
    verdicts = Replay("StartBad").check()
    assert verdicts.empty is None and verdicts.distinct == 3


def test_box_property_tlc_checks_as_an_invariant_breaks_as_itself() -> None:
    # TLC checks PROPERTY [](x = 0) as an invariant: "Invariant Small is violated".
    replay = Replay("BoxFirst")
    verdicts = replay.check()
    assert {r: (b.kind, len(b.trace.steps)) for r, b in verdicts.broken.items()} == {
        "Small": ("invariant", 2)
    }
    assert verdicts.holds == ["NoDeadlock"]
    assert not any("Small" in r.invariants for r in replay.asked if not r.probe)
    replay = Replay("BoxLater")  # Inv first; Small breaks in its own run
    verdicts = replay.check()
    assert {r: (b.kind, len(b.trace.steps)) for r, b in verdicts.broken.items()} == {
        "Inv": ("invariant", 2),
        "Small": ("invariant", 3),
    }
    assert verdicts.holds == ["NoDeadlock"] and not verdicts.unchecked
    assert not any("Small" in r.invariants for r in replay.asked if not r.probe)


def test_broken_box_property_drawn_at_every_state_breaking_it() -> None:
    # Small == [](x < 2) breaks at x = 2 and x = 3; its -continue drawing run
    # keeps it a PROPERTY, never an INVARIANT, and collects both.
    replay = Replay("BoxManySolo")
    verdicts = replay.check()
    assert {r: (b.kind, len(b.trace.steps)) for r, b in verdicts.broken.items()} == {
        "Small": ("invariant", 3)
    }
    assert verdicts.holds == ["NoDeadlock"] and verdicts.graph_partial is None
    drawing = [r for r in replay.asked if r.keep_going]
    assert drawing == [
        tlc.Request((), ("Small",), False, keep_going=True, bounded=True)
    ]
    assert sorted(t.strip() for t in verdicts.violations["Small"]) == ["x = 2", "x = 3"]
    assert verdicts.distinct == 4
    assert not any("Small" in r.invariants for r in replay.asked if not r.probe)
    for case, marked in (("BoxFirst", ["x = 1"]), ("BoxLater", ["x = 2"])):
        verdicts = Replay(case).check()
        assert sorted(t.strip() for t in verdicts.violations["Small"]) == marked


def test_probe_time_limit_is_finite_and_kills_its_process_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert tlc.probe_limit(0.9) == 0.9 + tlc.PROBE_MARGIN
    assert tlc.probe_limit(3600.0) == tlc.PROBE_SECONDS
    config = tlc.parse_config(MODELS / "InitialWarning.cfg")
    asked: list[tlc.Request] = []

    def runner(request: tlc.Request) -> tlc.Result:
        asked.append(request)
        return tlc.Result(0, "", "")

    tlc.property_levels(config, runner, 1.5)
    assert [r.timeout for r in asked] == [1.5, 1.5]
    # A probe past its limit: the whole group is killed and reaped, never waited on.
    java = tlc.JavaRunner("java", Path("t.jar"), MODELS / "Light.tla", config, tmp_path)
    pids = tmp_path / "pids"
    script = (
        "import os, subprocess, sys, time\n"
        "child = subprocess.Popen(['sleep', '60'])\n"
        f"open({str(pids)!r}, 'w').write(f'{{os.getpid()}} {{child.pid}}')\n"
        "time.sleep(60)\n"
    )
    monkeypatch.setattr(java, "command", lambda *_: [sys.executable, "-c", script])
    started = time.monotonic()
    result = java(
        tlc.Request(("Small",), (), False, bounded=True, probe=True, timeout=2)
    )
    assert time.monotonic() - started < 10
    assert result.code < 0 and java.process is None
    for pid in map(int, pids.read_text().split()):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and _alive(pid):
            time.sleep(0.05)
        assert not _alive(pid)


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    stat = Path(f"/proc/{pid}/stat")
    try:
        return stat.read_text().rsplit(")", 1)[1].split()[0] != "Z"  # a zombie is gone
    except OSError:
        return False
