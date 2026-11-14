# Reading `report.md`

The report is the text half of a check, in the order below. Sections that do
not apply are left out.

## Summary

The first line counts the states and steps TLC checked and the chart states and
arrows drawn. Lines after it, when they apply:

- **Drawing stopped early.** The model has more than 500 states, so only the
  failing paths are drawn; every rule was still checked.
- **The drawn graph is not complete.** The graph came from a run that hit the
  bound or an error, named in the line.
- **The view hides N steps**, per action, and **N steps stay within one chart
  state**: steps left out of the chart, counted.

## Rules

- **Rules that hold** lists them, or says none.
- **Rules that break** gives each rule a numbered path from a start:
  `1. At the start: <state>`, then `n. <step> -> <state>`, in the view's words.
  For an invariant or a deadlock it is the shortest path to a breaking state;
  for a property an initial state already breaks, that one start state.
  For a temporal property it is a run that never satisfies it, ending with
  which steps repeat forever ("From step 6, ... returns to step 3") or where it
  stops and stays.
- **Rules not checked** names each rule a run could not finish and why: the run
  stopped at the bound of 100,000 distinct states, or on an error. Such a rule
  can hold or break, and it carries no mark in the chart. To check it, remove
  the breaking rules from the configuration, or make the model smaller.

## Marks and legend

A chart state gets the mark `breaks` when every model state under it breaks a
rule, and `mayBreak` when only some do. Marks count every model state the check
found, drawn or not, so a chart cut at the drawing budget marks what the whole
model would; the legend says so. In a regions chart each region's label
is a chart state, and a model state is a combination of labels, one per region.
A label is marked first when every combination it appears in can break a rule;
then, for each breaking combination with none of its labels marked, all its
labels are marked. A label whose every breaking combination already holds a
marked label stays plain.

TLC names one broken invariant per state, so the tool gives each broken
invariant a run of its own to find every state that breaks it.

The legend names the rules behind each mark, `onPath` (a state on a shortest
path to a broken rule), `repeats` (a state a property's counterexample repeats
forever) and each `phase_<colour>` with its phase. When a mark stands for more
than one rule, "Which chart state breaks which rule" pairs them. With no chart
state drawn there is no legend.

With deadlock checked, no constraints and a complete graph, every state with no
step out is marked as a deadlock; the graph then comes from a run that checks
no deadlock, so it expands every state. With a `CONSTRAINT` or
`ACTION_CONSTRAINT`, states at the bound also have no step out without being
deadlocks, and in a graph cut short by the bound or an error some states were
never expanded; in both cases only the deadlock TLC reported is marked, and a
note says so.

## Notes

- A `PROPERTY` lacking a temporal operator, checked in the initial states only,
  or one TLC neither refused nor checked as an invariant within the probe's
  time limit, so the tool cannot tell.
- Regions redrawn as nested states, with the reason; or, past the drawing
  budget, regions drawn without the conditions on their steps.
- An empty model: no state meets the initial condition, or every initial state
  lies outside the constraints.
- States after a failure: TLC explores past a broken rule, so the chart shows
  where the behaviour goes next.
- `VIEW` or `SYMMETRY`: TLC keeps one representative of states it treats as the
  same, so an arrow may point at that representative rather than the state the
  step reaches.
- States beyond a constraint or the bound: when a failing path ends past one,
  the chart draws that path's states and no other state past the bound.
- Per step label in a regions chart, whether it changes several regions at once
  or one at a time.

## Raw output

`tlc.out` is TLC's tool-mode output on the configuration as written;
`tlc-<rule>.out` is the output of the later run that found that rule broken;
`tlc-draw-<rule>.out` and `tlc-draw.out` are runs drawing the graph that
stopped on an error, which the summary names.
Read them when a path in the report looks wrong; `graph.dot` is the state graph
the chart was drawn from.
