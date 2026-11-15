---
name: statechart
description: "Use to check a TLA+ model of something that moves between states, such as a product flow, a protocol or a service, and draw it as a statechart, or to read a TLA+ check's result as the shortest path to each broken rule. A runnable experiment of chosen cases is prototype; a formal check kept as a project skill is create-formal-verification-skill. Runs TLC on Java, installed per user only with the person's approval."
---

# Statechart

A statechart shows how something moves from state to state, phrased for
whoever has to judge whether that behaviour is right. This skill models it in
TLA+, has TLC visit every reachable state, and leaves a Mermaid chart with a
report giving the shortest path to each rule that breaks. It changes no product
code; on a bug it shows the path, and the code decides.

## Run

Write the model (`SPEC.tla`) and its configuration (`SPEC.cfg`) in the project's
ignored scratch folder, never among tracked files, and keep them past the task
only when the person asks for that. A model another skill keeps is run where it
lives; only `--out` goes to scratch. Then:

```sh
python3 <skill-folder>/scripts/statechart.py SPEC.tla [--config FILE] [--view FILE] [--out DIR]
```

That one command checks every rule and draws the graph.

- `--config` defaults to `SPEC.cfg` beside the spec; when that file is missing
  it stops and names `--config FILE`. `--out` defaults to `SPEC-chart` beside
  the spec and must be a new or empty folder. The results are staged next to it
  and moved in by one rename; if the folder was created, removed, replaced or
  filled in the meantime, nothing is written.
- Exit 0: every checked rule holds. Exit 1: at least one breaks. Exit 2: an
  error (arguments, configuration, spec, view, runtime, TLC stopping on an error
  or failing without naming a rule); stderr gives the reason, TLC's error
  messages only (at most 40 lines), the rules left unchecked, then
  `Nothing was written.` Exit 128+N: signal N stopped it (Ctrl-C is 130); TLC's
  whole process group is killed and the temporary folders are removed.
- The folder is written on exit 0 or 1 only, and both print the report then
  `Wrote <out>: <files>`. Files: `report.md`; `chart.mmd` and `render.json`,
  the Mermaid limits that chart needs (both absent when nothing is drawn);
  `graph.dot`, TLC's state graph the chart is drawn from; `tlc.out`, TLC's
  output on the configuration as written; `tlc-<rule>.out`, the run that found
  that rule broken when that run is not the one in `tlc.out`; `tlc-draw-<rule>.out`
  or `tlc-draw.out`, a run drawing the graph that stopped on an error.

TLC runs pinned: one worker, fixed fingerprint index and seed, liveness checked
once at the end, so the same model gives the same chart. The spec's folder is on
TLC's library path, so `EXTENDS` finds modules kept beside it. TLC parses the
spec and the configuration before it checks any state, and invalid input is
refused naming its file and line; an `ALIAS` is refused because it changes how
states print.

**Runtime.** Python 3.10 or newer, Java 11 or newer, TLC 1.7.4. The tool takes
`JAVA` and `TLA2TOOLS` when set, then the per-user install, then `java` on
`PATH`; when either is missing it stops with exit 2 and names the versions it
needs. Installing is the person's call: ask first. With their approval run
`python3 <skill-folder>/scripts/statechart.py install`, which installs per user
at pinned versions and checks every download against its pin
(`references/install.md`); or have them set `JAVA` and `TLA2TOOLS` to an
install they already have. Without approval, stop and say what is missing.

## Write the spec

- Each rule the reader accepts becomes an `INVARIANT` over what they can see:
  what appears on screen, a stored value, a message, an outcome. When no
  variable carries what a rule talks about, add one.
- Never loosen a rule, the model or its bounds so that a check passes; a break
  on the current behaviour is the finding.
- Make `Next` a disjunction of named actions, such as `Pay \/ Retry \/ Done`.
  TLC names each step after its action; one unnamed `Next` puts `Next` on
  every arrow.
- Report deadlock under a fixed name, switching to another when a rule of the model already uses that name.
  The tool calls it `NoDeadlock`; `CheckDeadlock` when a rule already has that
  name; `NoDeadlock2`, `NoDeadlock3` and so on when both are taken.
  `CHECK_DEADLOCK FALSE` turns it off.
- A correct end state has no step out, so it would count as a deadlock. Mark
  each one with an action enabled only there that leaves every variable as it
  is, for example `Done == phase = "paid" /\ UNCHANGED phase`, and label it
  in the view; the chart leaves such a step undrawn and counts it. Turning
  deadlock off works too, but then no state is checked for it: say so in the
  hand-off.
- TLC keeps exploring past a broken rule, so a model without limits never
  finishes. Keep the constants small, or bound the search with a `CONSTRAINT`.
- Temporal formulas go under `PROPERTY`. A `PROPERTY` lacking any temporal
  operator is checked in the initial states only; the report warns, and it
  belongs under `INVARIANT`. TLC decides which is which: the tool offers each
  property to TLC as an invariant on the initial states, and TLC refuses a
  temporal one. When that probe ends any other way, or runs past its time
  limit (10 s, or the check's own time plus 3 s when shorter), the report says
  it could not tell; the check's verdicts stand.

## Pick the chart

The words on states and arrows, the phases, their colours and the title are
judgment, and they live in a view file passed with `--view`: a Python module
kept apart from the model. Without one, a state is labelled by its variable
values (`x = 1, y = 0`) and an arrow by its action name. The type `state(v)`
returns decides the form: `str` gives a flat chart, `list` nested parent
states, `dict` parallel regions. Before writing a view, read
`references/view.md`: its functions, the shape of the values it receives, label
rules, merging and how to cut a busy chart down.

## Read the result

After a break the tool removes that rule and reruns TLC, repeating until none
of the remaining rules breaks; each temporal property gets a run of its own.
Every run after the first break is capped at 100,000 distinct states, and a rule
a run could not finish is listed as not checked: it can still hold or break.
`report.md` opens with the states and steps checked and the chart states and
arrows drawn; then the rules that hold, each broken rule with its shortest path
from a start, the rules not checked, a legend of marks and notes.
`references/report.md` explains each part.

## Show it

Show `chart.mmd` to the person as a `mermaid` code block. A model of more than
500 states is drawn only along its failing paths, and with no failing path
there is no `chart.mmd` and no legend; every rule is still checked, the report
still gives each path, and marks still count every model state. Shrink the model to see all of it. When the person wants an image or
the chart text is too long to read, follow `references/render.md`.

The chart is Mermaid `stateDiagram-v2` text in a fixed order: states by their
distance from a start, then by label, so a rerun gives the same text. Label
characters outside a plain set are written as Mermaid entity codes, so any text
is safe. A regions chart is one composite of parallel regions laid out left to
right, with the title in the file's front matter.

## Hand off

- Hand each chart and its Mermaid source to whoever decides whether the
  behaviour is right.
- Write one line per failure: the rule, its sentence in the reader's words, and
  the step numbers the report gives its path.
- When one mark covers several rules, say which chart state breaks which; the
  report's legend lists them.
- Hide a step only if every state stays reachable, every state with a step out
  keeps an arrow out, an arrow's steps hide all together or not at all, and the
  step lies on no failing path or loop exit. The tool refuses a view that breaks
  one of these. Name the hidden steps in the hand-off; the report counts them.
- State what the model does not cover: actors, failures, data and sizes.
- Give the command that regenerates the files, pointing `--out` at a fresh
  folder.
- Where the model stands for real code, replay each counterexample against that
  code one action at a time, as a test or a reproduction. Treat a step the code
  cannot take as a modelling error until the code shows otherwise.
