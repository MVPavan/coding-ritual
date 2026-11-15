"""statechart's chart passes, Mermaid text and report, on TLC runs recorded
from our fixture models, with view files written per test."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True  # no bytecode beside the shipped scripts
sys.path.insert(0, str(ROOT / ".claude/skills/statechart/scripts"))

from statechart_lib import chart, mermaid, report, tlc
from statechart_lib.graph import Graph, parse_dot
from statechart_lib.values import Decoder, Frozen
from statechart_lib.view import View, ViewError, load

from tests.checks.test_statechart_tlc import Replay


def draw(
    case: str, tmp_path: Path, view: str | None = None, budget: int = chart.BUDGET
) -> tuple[chart.Chart, View, tlc.Verdicts, tlc.Config]:
    replay = Replay(case)
    verdicts = replay.check()
    path = None
    if view is not None:
        path = tmp_path / "view.py"
        path.write_text(textwrap.dedent(view))
    loaded = load(path)
    decoder = Decoder()
    graph = parse_dot(verdicts.dot, decoder)
    drawn = chart.build(
        graph, loaded, verdicts, replay.config.constrained, decoder, budget
    )
    return drawn, loaded, verdicts, replay.config


def text_of(case: str, tmp_path: Path, view: str | None = None) -> tuple[str, str]:
    drawn, loaded, verdicts, config = draw(case, tmp_path, view)
    words = report.render(case, verdicts, drawn, loaded.steps, config, [])
    return mermaid.render(drawn), words


def test_default_labels_and_a_stable_draw_order(tmp_path: Path) -> None:
    drawn, _, _, _ = draw("Counter", tmp_path)
    assert drawn.nodes[:3] == [("x = 0, y = 0",), ("x = 0, y = 1",), ("x = 1, y = 0",)]
    assert text_of("Counter", tmp_path) == text_of("Counter", tmp_path)


COARSE = """
    def state(v):
        return "nothing yet" if v["x"] + v["y"] == 0 else "counting" if v["x"] + v["y"] < 3 else "full"

    def step(action, before, after):
        return {"IncX": "add one", "IncY": "add one", "Reset": "start over"}[action]
"""


def test_shared_labels_share_one_arrow_and_steps_inside_a_label_are_counted(
    tmp_path: Path,
) -> None:
    drawn, _, _, _ = draw("Counter", tmp_path, COARSE)
    arrows = {(a.source[0], a.target[0]): a.labels for a in drawn.arrows}
    assert arrows[("nothing yet", "counting")] == {"add one"}
    assert drawn.self_loops > 0
    assert "add one" in mermaid.render(drawn)
    split = COARSE.replace('"IncY": "add one"', '"IncY": "add another"')
    drawn, _, _, _ = draw("Counter", tmp_path, split)
    arrows = {(a.source[0], a.target[0]): a.labels for a in drawn.arrows}
    assert arrows[("nothing yet", "counting")] == {"add one", "add another"}
    assert "s1 --> s2 : add another or add one" in mermaid.render(drawn)


def test_marks_break_and_may_break_with_rules_per_state(tmp_path: Path) -> None:
    drawn, _, _, _ = draw("Counter", tmp_path, COARSE)
    assert drawn.marks == {
        ("full",): "mayBreak"
    }  # (3, 0) is full and breaks only XNotThree
    assert drawn.rules_at[("full",)] == {"SumSmall", "XNotThree"}
    plain, _, _, _ = draw("Counter", tmp_path)
    assert plain.marks[("x = 3, y = 3",)] == "breaks"
    assert "class s1 onPath" in mermaid.render(plain)
    _, words = text_of("Counter", tmp_path, COARSE)
    assert (
        "- `mayBreak`: some model states under the chart state break the rule, "
        in words
    )
    assert (
        "Which chart state breaks which rule:\n\n- full: SumSmall, XNotThree" in words
    )


def test_box_property_marks_every_state_breaking_it(tmp_path: Path) -> None:
    plain, _, _, _ = draw("BoxManySolo", tmp_path)
    assert plain.marks == {("x = 2",): "breaks", ("x = 3",): "breaks"}
    merged = "def state(v):\n    return 'bad' if v['x'] >= 2 else 'good'\n"
    drawn, _, _, _ = draw("BoxManySolo", tmp_path, merged)
    assert drawn.marks == {("bad",): "breaks"}
    _, words = text_of("BoxManySolo", tmp_path, merged)
    assert "mayBreak" not in words and "- bad: Small" in words


def test_states_after_a_failure_are_drawn(tmp_path: Path) -> None:
    drawn, _, _, _ = draw("Counter", tmp_path)
    assert ("x = 3, y = 3",) in drawn.nodes and len(drawn.nodes) == 16


def test_loop_states_repeat_and_the_report_describes_the_loop(tmp_path: Path) -> None:
    drawn, _, _, _ = draw("Loop", tmp_path)
    assert {n for n in drawn.nodes if "repeats" in drawn.classes[n]} == {
        ("p = idle",),
        ("p = busy",),
    }
    _, words = text_of("Loop", tmp_path)
    assert (
        "From step 2, Back returns to step 1, so steps 1 to 2 repeat forever." in words
    )
    _, stall = text_of("Stall", tmp_path)
    assert "The run stops at step 1 and stays there forever." in stall


def test_shortest_failing_path_in_reader_words(tmp_path: Path) -> None:
    _, words = text_of("Counter", tmp_path, COARSE)
    assert "### SumSmall" in words
    assert "1. At the start: nothing yet\n2. add one -> counting" in words


def test_hiding_obeys_its_rules_and_is_disclosed(tmp_path: Path) -> None:
    hide_lock = 'def step(action, before, after):\n    return None if action == "Lock" else action\n'
    drawn, _, _, _ = draw("Doors", tmp_path, hide_lock)
    assert drawn.hidden == {"Lock": 1}
    _, words = text_of("Doors", tmp_path, hide_lock)
    assert "The view hides 1 steps: Lock (1)." in words
    refusals = {
        "Reset": "no arrow out",  # (3, 3) has no other exit
        "IncY": "on a failing path",
    }
    for action, why in refusals.items():
        view = f'def step(action, before, after):\n    return None if action == "{action}" else action\n'
        with pytest.raises(ViewError, match=why):
            draw("Counter", tmp_path, view)
    unlock = 'def step(action, before, after):\n    return None if action == "Unlock" else action\n'
    with pytest.raises(ViewError, match="unreachable"):
        draw("Doors", tmp_path, unlock)
    some = """
        def state(v):
            return "low" if v["x"] + v["y"] < 2 else "high"

        def step(action, before, after):
            return None if (action, before["x"]) == ("IncY", 0) else action
    """
    with pytest.raises(ViewError, match="but not all"):
        draw("Counter", tmp_path, some)


def test_parent_level_arrow_drawn_once(tmp_path: Path) -> None:
    view = """
        def state(v):
            return ["Busy", v["phase"]] if v["phase"] in ("picking", "sending", "verifying") else [v["phase"]]

        def step(action, before, after):
            return "you cancel" if action == "Cancel" else action
    """
    drawn, _, _, _ = draw("Upload", tmp_path, view)
    cancels = [a for a in drawn.arrows if "you cancel" in a.labels]
    assert [(a.source, a.target) for a in cancels] == [(("Busy",), ("cancelled",))]
    text = mermaid.render(drawn)
    assert 'state "Busy" as' in text and text.count("you cancel") == 1


REGIONS = """
    title = 'Front door'

    def state(v):
        return {"Door": v["door"], "Lock": v["lock"]}

    def step(action, before, after):
        return action.lower()
"""


def test_regions_with_conditions_written_by_the_tool(tmp_path: Path) -> None:
    drawn, _, _, _ = draw("Doors", tmp_path, REGIONS)
    assert drawn.form == "regions" and not drawn.notes
    labels = {a.source + a.target: a.labels for a in drawn.arrows}
    assert labels[("Door", "closed", "Door", "open")] == {"open [when Lock: unlocked]"}
    assert labels[("Lock", "unlocked", "Lock", "locked")] == {
        "lock [when Door: closed]"
    }
    assert labels[("Lock", "locked", "Lock", "unlocked")] == {"unlock"}
    text = mermaid.render(drawn)
    assert text.startswith('---\ntitle: "Front door"\n---\nstateDiagram-v2')
    assert "direction LR" in text and "\n    --\n" in text
    _, words = text_of("Doors", tmp_path, REGIONS)
    assert "`open` changes one region at a time." in words


def test_step_changing_several_regions_at_once_is_noted(tmp_path: Path) -> None:
    view = 'def state(v):\n    return {"X": str(v["x"]), "Y": str(v["y"])}\n'
    drawn, _, _, _ = draw("Counter", tmp_path, view)
    assert drawn.form == "regions" and drawn.together["Reset"]
    labels = {a.source + a.target: a.labels for a in drawn.arrows}
    assert labels[("X", "3", "X", "0")] == {"Reset [when Y: 3]"}
    _, words = text_of("Counter", tmp_path, view)
    assert "`Reset` changes several regions at once." in words
    assert "`IncX` changes one region at a time." in words
    assert "- X: 3: SumSmall, XNotThree" in words


def test_unfaithful_regions_redrawn_nested_saying_why(tmp_path: Path) -> None:
    view = 'def state(v):\n    return {"A": str(v["a"]), "B": str(v["b"])}\n'
    drawn, _, _, _ = draw("Swap", tmp_path, view)
    assert drawn.form == "nested"
    assert drawn.notes == [
        (
            "Drawn as nested states, not regions: it would start at A: 0, B: 0, "
            "which the model never starts at."
        )
    ]


def test_arrow_out_of_a_loop_it_cannot_take_is_refused(tmp_path: Path) -> None:
    view = 'def state(v):\n    return "waiting" if v["p"] in ("idle", "failed") else v["p"]\n'
    with pytest.raises(ViewError, match="loop cannot take it"):
        draw("Retry", tmp_path, view)
    draw("Retry", tmp_path)  # one label per state: the loop is faithful


def test_dead_ends_marked_as_deadlocks_and_boundary_states_drawn(
    tmp_path: Path,
) -> None:
    stuck, _, _, _ = draw("Stuck", tmp_path)
    assert stuck.marks == {("n = 2",): "breaks"} and stuck.rules_at[("n = 2",)] == {
        "NoDeadlock"
    }
    fence, _, _, config = draw("Fence", tmp_path)
    assert config.constrained and fence.beyond == 1
    assert fence.marks == {("c = 4",): "breaks"}  # past the constraint, drawn
    assert ("c = 3",) not in fence.marks  # no exit at the bound, not a deadlock


def test_budget_draws_only_failing_paths_and_says_so(tmp_path: Path) -> None:
    drawn, _, _, _ = draw("Big", tmp_path)
    assert drawn.over_budget and len(drawn.nodes) == 4
    _, words = text_of("Big", tmp_path)
    assert words.splitlines()[2].startswith(
        "Checked 625 states and 1,200 steps with TLC; drew 4"
    )
    assert "Drawing stopped early" in words
    _, bounded = text_of("Big-bound", tmp_path)
    assert (
        "- Fine: the run stopped at the bound of 100 distinct states. It can hold or break."
        in bounded
    )
    assert "The drawn graph is not complete" in bounded


def test_phase_colours_and_legend(tmp_path: Path) -> None:
    view = """
        colors = {"paying": "blue", "after": "green"}

        def group(v):
            return "paying" if v["phase"] == "cart" else "after"
    """
    drawn, _, _, _ = draw("Checkout", tmp_path, view)
    text = mermaid.render(drawn)
    assert "class s1 phase_blue" in text
    assert [x for x in text.splitlines() if x.lstrip().startswith("classDef")] == [
        f"  {style}" for style in mermaid.MARK_STYLES
    ]
    _, words = text_of("Checkout", tmp_path, view)
    assert "- `phase_blue`: paying." in words and "- NoDeadlock" in words
    spanning = (
        textwrap.dedent(view)
        + '\ndef state(v):\n    return "shop" if v["phase"] != "paid" else "paid"\n'
    )
    drawn, _, _, _ = draw("Checkout", tmp_path, spanning)
    assert drawn.classes[("shop",)] == set()  # cart and failed: two groups, no colour


def test_label_text_is_escaped_for_mermaid(tmp_path: Path) -> None:
    assert mermaid.escape('say "hi": #1 <b>; {x}') == (
        "say #34;hi#34;#58; #35;1 #60;b#62;#59; #123;x#125;"
    )
    view = 'def state(v):\n    return f\'light: "{v["light"]}"\'\n'
    drawn, _, _, _ = draw("Light", tmp_path, view)
    text = mermaid.render(drawn)
    assert 'state "light#58; #34;red#34;" as s1' in text


def test_report_notes(tmp_path: Path) -> None:
    _, empty = text_of("NoInit", tmp_path)
    assert "TLC explored no state: no state satisfies the initial condition." in empty
    drawn, loaded, verdicts, _ = draw("Light", tmp_path)
    cfg = tmp_path / "Light.cfg"
    cfg.write_text("SPECIFICATION Spec\nSYMMETRY Perms\n")
    words = report.render(
        "Light", verdicts, drawn, loaded.steps, tlc.parse_config(cfg), []
    )
    assert "may lead to that representative state" in words
    assert "## Rules that hold\n\n- TypeOK\n- EventuallyGreen\n- NoDeadlock" in words


def test_break_with_no_path_printed_is_named_and_its_marks_disclosed(
    tmp_path: Path,
) -> None:
    _, words = text_of("Untraced", tmp_path)
    assert "### Low\n\nThe shortest path from a start" in words
    assert "TLC reported Low broken 1 time(s) without printing the state" in words
    assert "The drawn graph is not complete: the run drawing where Low breaks" in words
    drawn, _, _, _ = draw("UntracedStart", tmp_path)
    assert drawn.paths == [] and not drawn.marks
    _, words = text_of("UntracedStart", tmp_path)
    assert "## Rules that break\n\n### Low\n\nTLC reported it broken" in words
    assert "tlc.out holds what TLC printed" in words


def test_partial_marks_count_only_printed_states_the_graph_holds(
    tmp_path: Path,
) -> None:
    # Untraced keeps the first run's graph; Low's drawing run printed two
    # breaking states, one of them (x = 2) not in that graph, then stopped.
    drawn, loaded, verdicts, config = draw("Untraced", tmp_path)
    marked, on_paths, printed, outside = drawn.coverage["Low"]
    assert on_paths == 0
    assert verdicts.graph_from == "the first run" and drawn.model_states == 3
    assert printed == len(set(verdicts.violations["Low"])) == 2
    assert marked == sum("Low" in rules for rules in drawn.rules_at.values()) == 1
    assert outside == printed - marked == 1
    words = report.render("Untraced", verdicts, drawn, loaded.steps, config, [])
    assert words.splitlines()[2].startswith("The graph from the first run has 3 states")
    assert (f"{marked} of the 3 model states marked, the other {3 - marked} unknown; "
            f"{printed} breaking state(s) printed, {outside} of them not in the graph") in words  # fmt: skip
    assert "Marks count all" not in words and "Checked" not in words
    assert "draws what follows a failure" not in words  # no drawn step leaves x = 1


def test_partial_marks_never_claim_the_other_states_hold(tmp_path: Path) -> None:
    # x = 1, 2, 3 with y = 0 all break Low; Low's run printed only x = 1, 2.
    view = """
        def state(v):
            return "positive-y0" if v["x"] > 0 and v["y"] == 0 else "other"
    """
    drawn, loaded, verdicts, config = draw("UntracedPartial", tmp_path, view)
    assert verdicts.graph_partial is None and drawn.model_states == 8
    assert drawn.marks[("positive-y0",)] == "mayBreak"
    assert drawn.coverage == {"Low": (2, 0, 2, 0)}
    words = report.render("UntracedPartial", verdicts, drawn, loaded.steps, config, [])
    assert "others do not" not in words
    assert f"- `mayBreak`: {report.PARTIAL_MAY}: Low." in words
    assert "2 of the 8 model states marked, the other 6 unknown" in words
    assert "The drawn graph is not complete" not in words


def test_a_stopped_drawing_run_leaves_the_whole_graph_deadlocks_marked(
    tmp_path: Path,
) -> None:
    drawn, loaded, verdicts, config = draw("UntracedDeadlock", tmp_path)
    assert verdicts.graph_partial is None and set(verdicts.marks_partial) == {"Low"}
    assert verdicts.graph_from == "the rerun of the remaining rules"
    dead = {node for node, rules in drawn.rules_at.items() if "NoDeadlock" in rules}
    assert dead == {("x = 3, y = 0",), ("x = 3, y = 1",)}
    words = report.render("UntracedDeadlock", verdicts, drawn, loaded.steps, config, [])
    assert "- Marks for NoDeadlock count all 8 model states the check found." in words
    assert "only the deadlock TLC reported is marked" not in words


def test_provenance_counts_the_runs_own_graph_and_paths_apart(tmp_path: Path) -> None:
    # The first run's graph stops at the constraint; Low's path adds x = 2, y = 0.
    drawn, loaded, verdicts, config = draw("PathExtra", tmp_path)
    assert (drawn.dot_states, drawn.dot_steps) == (4, 2)
    assert drawn.model_states - drawn.dot_states == drawn.beyond == 1
    assert drawn.model_steps - drawn.dot_steps == 1
    marked, on_paths, printed, outside = drawn.coverage["Low"]
    assert marked == on_paths == printed == outside == 1  # the path's state alone
    words = report.render("PathExtra", verdicts, drawn, loaded.steps, config, [])
    assert words.splitlines()[2] == (
        "The graph from the first run has 4 states and 2 steps (failing paths add 1 "
        "state(s) and 1 step(s)); drew 5 chart states and 3 arrows."
    )
    assert ("1 of the 5 model states marked (1 only on a failing path), the other 4 "
            "unknown; 1 breaking state(s) printed, 1 of them not in the graph.") in words  # fmt: skip


def test_only_a_drawn_arrow_out_of_a_break_shows_what_follows(tmp_path: Path) -> None:
    # Safe breaks at x = 1 only; its one step out, After, goes to x = 2.
    note = "draws what follows a failure"
    drawn, loaded, verdicts, config = draw("Hidden", tmp_path)
    assert drawn.after_failure
    assert note in report.render("Hidden", verdicts, drawn, loaded.steps, config, [])
    hide = """
        def state(v):
            return "mixed" if v["x"] in {1, 3} else str(v["x"])
        def step(action, before, after):
            return None if before["x"] == 1 else action
    """
    merge = """
        def state(v):
            return "after" if v["x"] > 0 else "start"
    """
    for view, kept in ((hide, "hidden"), (merge, "self_loops")):
        drawn, loaded, verdicts, config = draw("Hidden", tmp_path, view)
        assert drawn.hidden if kept == "hidden" else drawn.self_loops
        assert not drawn.after_failure and drawn.arrows  # Return 3 -> 0 stays drawn
        words = report.render("Hidden", verdicts, drawn, loaded.steps, config, [])
        assert note not in words


def test_dead_ends_inferred_only_from_a_complete_graph(tmp_path: Path) -> None:
    drawn, _, verdicts, _ = draw("Frontier", tmp_path)
    assert drawn.marks == {("n = 1",): "breaks"}  # 2 walks on to 3
    assert verdicts.graph_partial is None and ("n = 3",) in drawn.nodes
    partial = tlc.Verdicts(
        deadlock_rule="NoDeadlock", broken=verdicts.broken, dot=verdicts.dot,
        graph_partial="the run stopped on an error",
    )  # fmt: skip
    decoder = Decoder()
    graph = parse_dot(verdicts.dot, decoder)
    del graph.steps[:]  # every state looks like a dead end
    marked = chart.build(graph, View(), partial, False, decoder)
    assert marked.marks == {("n = 1",): "breaks"}  # only the deadlock TLC reported


def test_initial_state_property_break_in_the_report(tmp_path: Path) -> None:
    drawn, _, _, _ = draw("InitialProperty", tmp_path)
    assert drawn.marks == {("x = 0",): "breaks"}
    _, words = text_of("InitialProperty", tmp_path)
    assert (
        "### Small\n\nA start state that breaks it:\n\n1. At the start: x = 0" in words
    )
    assert "stays there forever" not in words


REGION_XY = 'def state(v):\n    return {"X": str(v["x"]), "Y": str(v["y"])}\n'


def test_regions_marks_whole_labels_first_then_uncovered_combinations(
    tmp_path: Path,
) -> None:
    drawn, _, _, _ = draw("RegionMarks", tmp_path, REGION_XY)
    assert drawn.form == "regions"
    assert drawn.marks == {("X", "1"): "breaks"}  # X = 1 covers every break
    joint, _, _, _ = draw("Joint", tmp_path, REGION_XY)
    assert joint.form == "regions"
    # X = 2 breaks in every combination; (X = 1, Y = 1) is covered by no
    # marked label, so both its labels are marked; Y = 0 is left unmarked.
    assert joint.marks == {
        ("X", "2"): "breaks",
        ("X", "1"): "mayBreak",
        ("Y", "1"): "mayBreak",
    }


def test_render_limits_cover_the_chart_written(tmp_path: Path) -> None:
    size = 142  # 20,022 arrows, as dense as the budget allows near the old limit
    graph = Graph(
        {str(i): Frozen({"x": i}) for i in range(size)},
        ["0"],
        [(str(i), str(j), "Go") for i in range(size) for j in range(size) if i != j],
    )
    dense = chart.build(graph, View(), tlc.Verdicts(holds=["Ok"]), False, Decoder())
    text = mermaid.render(dense)
    limits = mermaid.limits(text)
    edges = sum(" --> " in line for line in text.splitlines())
    assert edges == size * (size - 1) + 1  # the arrows and the start
    assert (limits["maxEdges"], limits["maxTextSize"]) == (edges, len(text))
    small = mermaid.render(draw("Light", tmp_path)[0])
    assert mermaid.limits(small)["maxEdges"] == 500  # never below Mermaid's default
    assert mermaid.limits(small)["securityLevel"] == "strict"


BY_Y = 'def state(v):\n    return "y = " + str(v["y"])\n'


def test_marks_past_the_budget_count_every_model_state(tmp_path: Path) -> None:
    # Ok breaks only at (x = 2, y = 1). TLC's path reaches it through
    # (x = 2, y = 0), so the drawn states under y = 1 all break, while the
    # model's (x = 0, y = 1) and (x = 1, y = 1) keep Ok.
    drawn, loaded, verdicts, config = draw("Partial", tmp_path, BY_Y, budget=3)
    assert drawn.over_budget
    assert drawn.marks == {("y = 1",): "mayBreak"}
    words = report.render("Partial", verdicts, drawn, loaded.steps, config, [])
    assert "- Marks count all 6 model states the check found, drawn or not." in words
    regions, loaded, verdicts, config = draw("Partial", tmp_path, REGION_XY, budget=3)
    assert regions.over_budget and regions.form == "regions"
    # Y = 1 and X = 2 are each taken by states that keep Ok; the breaking
    # combination is covered by neither, so both may break. The drawn path
    # alone would mark Y = 1 `breaks` and write SetY [when X: 2].
    assert regions.marks == {("X", "2"): "mayBreak", ("Y", "1"): "mayBreak"}
    assert all(not needs for a in regions.arrows for _, needs in a.when.values())
    assert "[when" not in mermaid.render(regions)
    words = report.render("Partial", verdicts, regions, loaded.steps, config, [])
    assert "without the conditions" in words


def test_report_legend_spacing_and_no_legend_without_a_chart(tmp_path: Path) -> None:
    drawn, loaded, verdicts, config = draw("Light", tmp_path)
    words = report.render("Light", verdicts, drawn, loaded.steps, config, [])
    assert "## Rules that break\n\nNone.\n\n## Legend\n" in words
    empty = chart.Chart("flat", None)
    words = report.render("Light", verdicts, empty, {}, config, ["a warning"])
    assert "## Legend" not in words and "`onPath`" not in words
    assert "## Rules that break\n\nNone.\n\n## Notes\n\n- a warning\n" in words
