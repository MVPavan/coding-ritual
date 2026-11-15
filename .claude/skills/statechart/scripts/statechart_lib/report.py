"""Writing report.md: sizes, verdicts, shortest failing paths, loops, marks,
and what the reader must know to trust the chart."""

from __future__ import annotations

from . import tlc
from .chart import Chart, Path

MARK_MEANING = {
    "breaks": "every model state under the chart state breaks the rule",
    "mayBreak": "some model states under the chart state break the rule, others do not",
}
# A rule whose drawing run stopped: an unmarked state is unknown, not passing.
PARTIAL_MAY = (
    "some model states under the chart state break the rule, the others are unknown"
)


def _path_lines(
    path: Path, chart: Chart, steps: dict[tuple[str, str, str], str | None]
) -> list[str]:
    lines = []
    previous = None
    for number, (action, sid) in enumerate(path.steps, 1):
        if previous is None or action is None:
            lines.append(f"{number}. At the start: {chart.texts.get(sid, sid)}")
        else:
            label = steps.get((previous, sid, action)) or action
            lines.append(f"{number}. {label} -> {chart.texts.get(sid, sid)}")
        previous = sid
    return lines


def _legend(chart: Chart, verdicts: tlc.Verdicts) -> list[str]:
    out = ["## Legend", ""]
    for mark in ("breaks", "mayBreak"):
        rules = sorted(
            {
                r
                for node, m in chart.marks.items()
                if m == mark
                for r in chart.rules_at[node]
            }
        )
        known = [r for r in rules if r not in chart.coverage or mark == "breaks"]
        if known:
            out.append(f"- `{mark}`: {MARK_MEANING[mark]}: {', '.join(known)}.")
        if len(known) < len(rules):
            unknown = [r for r in rules if r not in known]
            out.append(f"- `{mark}`: {PARTIAL_MAY}: {', '.join(unknown)}.")
    drawn = ", drawn or not" if chart.over_budget else ""
    states = chart.model_states
    for rule, (marked, on_paths, printed, outside) in chart.coverage.items():
        only = f" ({on_paths:,} only on a failing path)" if on_paths else ""
        out.append(f"- Marks for {rule} are partial, as its run stopped on an error: {marked:,} of the "
                   f"{states:,} model states marked{only}, the other {states - marked:,} unknown; "
                   f"{printed:,} breaking state(s) printed, {outside:,} of them not in the graph.")  # fmt: skip
    whole = sorted(
        {r for n in chart.marks for r in chart.rules_at[n]} - set(chart.coverage)
    )
    if chart.marks and (whole or not chart.coverage):
        which = f" for {', '.join(whole)}" if chart.coverage else ""
        out.append(
            f"- Marks{which} count all {states:,} model states the check found{drawn}."
        )
    out.append("- `onPath`: on a shortest path to a broken rule. `repeats`: repeated forever by a "
               "counterexample to a property.")  # fmt: skip
    for group, color in sorted(chart.legend.items()):
        out.append(f"- `phase_{color}`: {group}.")
    attributed = [(n, chart.rules_at[n]) for n in chart.nodes if n in chart.rules_at]
    if attributed:
        out += ["", "Which chart state breaks which rule:", ""]
        out += [
            f"- {(': ' if chart.form == 'regions' else ' > ').join(node)}: "
            f"{', '.join(sorted(rules))}"
            for node, rules in attributed
        ]
    return out


def render(name: str, verdicts: tlc.Verdicts, chart: Chart, steps: dict[tuple[str, str, str], str | None],
           config: tlc.Config, warnings: list[str]) -> str:  # fmt: skip
    arrows = len(chart.arrows)
    out = [f"# {chart.title or name}", ""]
    if verdicts.graph_partial is None and not verdicts.marks_partial:
        checked = f"Checked {verdicts.distinct:,} states and {chart.model_steps:,} steps with TLC"
    else:  # say which run the counts come from
        added = (
            chart.model_states - chart.dot_states,
            chart.model_steps - chart.dot_steps,
        )
        paths = f" (failing paths add {added[0]:,} state(s) and {added[1]:,} step(s))" if any(
            added) else ""  # fmt: skip
        checked = (f"The graph from {verdicts.graph_from} has {chart.dot_states:,} states and "
                   f"{chart.dot_steps:,} steps{paths}")  # fmt: skip
    out.append(
        f"{checked}; drew {len(chart.nodes):,} chart states and {arrows:,} arrows."
    )
    if chart.over_budget:
        checks = "Rules not checked are listed below." if verdicts.unchecked else (
            "Every rule was still checked.")  # fmt: skip
        out.append(
            f"Drawing stopped early: the model is larger than the drawing budget, so only the failing "
            f"paths are drawn ({len(chart.nodes)} chart states). {checks}"
        )
    if verdicts.graph_partial:
        out.append(f"The drawn graph is not complete: {verdicts.graph_partial}.")
    if chart.hidden:
        hidden = ", ".join(
            f"{action} ({count})" for action, count in sorted(chart.hidden.items())
        )
        out.append(f"The view hides {sum(chart.hidden.values())} steps: {hidden}.")
    if chart.self_loops:
        out.append(
            f"{chart.self_loops} steps stay within one chart state and are not drawn."
        )
    out += ["", "## Rules that hold", ""]
    out += [f"- {rule}" for rule in verdicts.holds] or ["None."]
    out += ["", "## Rules that break", ""]
    if not verdicts.broken:
        out += ["None.", ""]
    for path in chart.paths:
        if path.kind == "deadlock":
            out += [
                f"### {path.rule}",
                "",
                "The run reaches a deadlock, a state that no step leaves:",
                "",
            ]
        elif path.kind == "initial":
            out += [f"### {path.rule}", "", "A start state that breaks it:", ""]
        elif path.kind == "property":
            out += [
                f"### {path.rule}",
                "",
                "A behaviour that never satisfies the property:",
                "",
            ]
        else:
            out += [
                f"### {path.rule}",
                "",
                "The shortest path from a start to a state that breaks it:",
                "",
            ]
        out += _path_lines(path, chart, steps)
        if path.kind == "property":
            last = len(path.steps)
            if path.loop_from:
                back = path.steps[path.loop_from - 1][1]
                label = (
                    steps.get((path.steps[-1][1], back, path.back_action or ""))
                    or path.back_action
                )
                out.append(f"\nFrom step {last}, {label} returns to step {path.loop_from}, so steps "
                           f"{path.loop_from} to {last} repeat forever.")  # fmt: skip
            else:
                out.append(f"\nThe run stops at step {last} and stays there forever.")
        out.append("")
    for rule, found in verdicts.broken.items():
        if not found.trace.steps:
            log = "tlc.out" if found.log == verdicts.first_log else f"tlc-{rule}.out"
            out += [f"### {rule}", "", ("TLC reported it broken but printed no path to a state that "
                    f"breaks it, so the chart draws none; {log} holds what TLC printed."), ""]  # fmt: skip
    if verdicts.unchecked:
        out += ["## Rules not checked", ""]
        out += [
            f"- {rule}: {why}. It can hold or break."
            for rule, why in verdicts.unchecked.items()
        ]
        out.append("")
    if chart.nodes:
        out += _legend(chart, verdicts)
    notes = list(warnings) + chart.notes
    if verdicts.empty:
        notes.append(f"TLC explored no state: {verdicts.empty}.")
    if chart.after_failure and any(
        b.kind != "property" for b in verdicts.broken.values()
    ):
        notes.append(
            "TLC keeps exploring after a broken rule, so the chart also draws what follows a failure."
        )
    for rule, times in verdicts.unprinted.items():
        notes.append(f"TLC reported {rule} broken {times} time(s) without printing the state that "
                     "breaks it, so the chart marks no state for those reports.")  # fmt: skip
    if config.representative:
        notes.append("The configuration has a VIEW or SYMMETRY: TLC keeps one representative of the "
                     "states it makes equal, so an arrow may lead to that representative state rather "
                     "than the one the step reaches.")  # fmt: skip
    if config.constrained and verdicts.deadlock_rule in verdicts.broken:
        notes.append("The model has constraints, so only the deadlock TLC reported is marked: states at "
                     "the bound have no step out without being deadlocks.")  # fmt: skip
    elif verdicts.graph_partial and verdicts.deadlock_rule in verdicts.broken:
        notes.append("The drawn graph is not complete, so only the deadlock TLC reported is marked: "
                     "a state it did not expand shows no step out.")  # fmt: skip
    if chart.beyond:
        notes.append(f"{chart.beyond} state(s) on a failing path are not in TLC's graph (past a "
                     "constraint or the bound); the chart draws them, and no other state past the bound.")  # fmt: skip
    for label, together in sorted(chart.together.items()):
        how = (
            "changes several regions at once"
            if together
            else "changes one region at a time"
        )
        notes.append(f"`{label}` {how}.")
    if notes:
        out += ([""] if out[-1] else []) + ["## Notes", ""] + [f"- {n}" for n in notes]
    return "\n".join(out).rstrip() + "\n"
