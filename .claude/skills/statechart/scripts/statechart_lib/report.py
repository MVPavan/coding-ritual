"""Writing report.md: sizes, verdicts, shortest failing paths, loops, marks,
and what the reader must know to trust the chart."""

from __future__ import annotations

from . import tlc
from .chart import Chart, Path

MARK_MEANING = {
    "breaks": "every model state under the chart state breaks the rule",
    "mayBreak": "some model states under the chart state break the rule, others do not",
}


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


def _legend(chart: Chart) -> list[str]:
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
        if rules:
            out.append(f"- `{mark}`: {MARK_MEANING[mark]}: {', '.join(rules)}.")
    if chart.marks:
        drawn = ", drawn or not" if chart.over_budget else ""
        out.append(
            f"- Marks count all {chart.model_states:,} model states the check found{drawn}."
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
    out.append(
        f"Checked {verdicts.distinct:,} states and {chart.model_steps:,} steps with TLC; "
        f"drew {len(chart.nodes):,} chart states and {arrows:,} arrows."
    )
    if chart.over_budget:
        out.append(
            f"Drawing stopped early: the model is larger than the drawing budget, so only the failing "
            f"paths are drawn ({len(chart.nodes)} chart states). Every rule was still checked."
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
    if verdicts.unchecked:
        out += ["## Rules not checked", ""]
        out += [
            f"- {rule}: {why}. It can hold or break."
            for rule, why in verdicts.unchecked.items()
        ]
        out.append("")
    if chart.nodes:
        out += _legend(chart)
    notes = list(warnings) + chart.notes
    if verdicts.empty:
        notes.append(f"TLC explored no state: {verdicts.empty}.")
    if any(b.kind != "property" for b in verdicts.broken.values()):
        notes.append(
            "TLC keeps exploring after a broken rule, so the chart also draws what follows a failure."
        )
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
