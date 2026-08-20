# Workflow Graphs

Status: parked — captured from discussion 2026-08-12, not yet refined through an
idea-refine/brainstorming session. Revisit after the lifecycle-skills wave
(buckets 2/4/5/6/7) lands.

Related (2026-08-19): humanlayer's `design-control-loop` was compared against
this draft in `harness_lifecycle/skill-comparisons/agentic-control-loops/README.md`
(§Orchestrator analysis). It agrees with every constraint below and adds a
measurement-driven loop shape (set point → sensor → controller → actuator,
scheduled) that would be a candidate *second graph type* if this idea resumes.

## Problem Statement

The harness's SDLC pipeline (brainstorm → prepare-phases → planning →
phase-execution → review) is hardcoded in prose across several skills and
commands. There is exactly one arc, frozen in the files; a different kind of
work (research, architecture improvement) cannot get a different arc without
editing skills. Orchestration choices — which models run a stage, where the
human gates are, which disciplines apply — are invisible and unconfigurable.

## Recommended Direction

Make the pipeline **data**: per-task-type workflow graphs, interpreted by the
agent, with beads as the only state store.

1. **Graphs as data.** One definition file per task type (feature
   implementation, research, architecture improvement, …). A graph is a
   sequence of stages with: the stage's skill, which agents/models run it
   (e.g. brainstorm via model-council with named members, consolidation by a
   judge model), the human review gate after it, and which execution
   disciplines mount.
2. **Seed into beads.** Once a graph is settled for a piece of work, pour it
   into beads so the tracker drives execution and closure — `bd formula`
   (TOML/JSON formulas in `.beads/formulas/`, cooked into protos, poured into
   work) is the native substrate. Prefer the graph format *being* a beads
   formula over inventing a parallel YAML; add a sidecar only for what
   formulas cannot express. Formula expressiveness is unverified — check
   `bd formula show` + upstream docs during the spec.
3. **Execution stage chooses its inner shape per task**: TDD (variant: a
   critic agent writes the test, implementer satisfies it), incremental
   (per-slice review), doubt-driven (per-doubt external review) — looped until
   the plan is done, then a final whole review by two models (or one
   higher-end model).
4. **Per-feature override.** Default graphs per task type; any feature/task
   may customize its graph before seeding.

### Design constraints agreed in discussion

- **Mount many, not route one.** Disciplines compose (incremental + TDD +
  source-verification can all apply to one task). The execution stage selects
  a *set* of mounted disciplines, never one-of-N. source-driven and
  doubt-driven are riding rules, not alternatives to TDD/incremental.
- **Graphs are process, roadmaps are content.** The graph answers "how does
  one unit of work move through stages"; prepare-phases/roadmaps answer "what
  are the units and their order". A roadmap phase runs *through* a graph; the
  graph does not absorb decomposition.
- **No loops in the graph format.** Iteration (review-until-accepted, fix
  loops, red-green) lives inside a stage, owned by skills. The graph carries
  only sequence + gates + assignments — otherwise it becomes a programming
  language / workflow engine.
- **v1 = interpreter + one graph.** phase-execution/run-phases refactor into
  the graph interpreter plus the default feature-implementation graph as
  data. Their proven plumbing (bd ready --claim loop, all-stages-closed gate,
  compaction recovery via bd re-query, render script) survives unchanged.
  Runtime-neutral: the model interprets the graph; bd holds state; no new
  runtime code.

## Key Assumptions

- bd formulas can express (or be extended with a sidecar to express) stage
  sequence, gate markers, and agent/model/discipline assignment. **Unverified.**
- The lifecycle-skills wave lands first; its outputs (planning rewrite
  content, bounded fix loop, final whole-phase review, discipline set) become
  the nodes this graph wires together.
- Multiple task-type graphs are actually needed (≥3: feature, research,
  architecture). If only the feature graph ever gets used, the abstraction
  was not worth it.

## MVP Scope

- One graph: feature implementation, reproducing today's proven chain as data.
- The interpreter behavior folded into the (merged) execution skill.
- Seeding via bd formula pour; human gates honored; prove end-to-end on one
  real phase before writing any second graph.

## Not Doing

- A workflow runtime/engine with loop semantics, conditionals, or its own
  state — the model interprets, bd stores.
- Retiring prepare-phases' decomposition function (only its packaging may
  change).
- Merging the discipline skills (TDD, systematic-debugging,
  verification-before-completion) into the graph — they stay separate,
  mounted by pointer.
- Parallel graph format alongside bd formulas unless formulas prove
  inexpressive.
