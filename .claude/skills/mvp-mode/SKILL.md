---
name: mvp-mode
description: Use at the start of every task to pick the playbook, principle or skill that fits, and whenever unsure which unit fits, when two seem to overlap, or when asked what skills exist. A skill the user or a playbook step already named is invoked directly.
---

# MVP mode

The index from a situation to the unit that handles it. It holds routing
only; `AGENTS.md` holds policy and wins if the two disagree.

## Kinds

- **`AGENTS.md`:** policy for every task, always loaded.
- **Router:** this skill; maps a situation to the unit to load.
- **Principle:** a judgement lens for a named situation; unordered rules, no output.
- **Skill:** one job with one deliverable.
- **Playbook:** ordered steps for one kind of request, with gates, ending in a reply contract.
- **Reference:** material that one branch of one unit loads when that branch runs.
- **Project document:** repository facts and conventions for particular work.

## Pick

- The user named a playbook: run it. Otherwise run the one whose line below
  fits the task and say which; if none fits, say so and work without one.
- Apply each principle whose situation holds.
- Choose the narrowest fitting skill or command; clear bounded work often
  needs no unit beyond `AGENTS.md`.
- For a skill, use the lines below or the skills' own descriptions. When still
  unsure, or asked what exists, read `references/catalog.md`.
- Invoke a model-invocable skill through the platform's skill mechanism, never
  by reading its file, so it survives compaction and its settings apply.
  Manual (slash-only) skills are the user's to start: suggest them.
- Read a playbook at `playbooks/<name>.md` and a principle at
  `principles/<name>.md`, both in this folder. A unit citing `principle-<name>`
  means `principles/<name>.md`.
- At top level, delegate by default: hand independent work to a subagent and
  keep your own context for coordination, integration and verification. Work
  locally only when that has a clear advantage: a handful of tool calls, a
  lookup whose target you know, or work that needs this conversation's context
  or the exact text you will edit.
- Inside a delegated task, route to skills and principles only and never start
  a playbook: the parent runs it, and your brief is its step; delegate further
  only when your brief allows it.

## Running a playbook

- Copy its steps into the todo list first, before any task-specific todos.
- A step that will not run stays in the list as `skip: <reason>`.
- Run each unit a step calls whole: never skip or override its core.
- Every exit, finished or stopped early, runs the playbook's closeout, then
  gives the reply its contract names for that exit.
- The run ends at that reply; the next task picks again.

## Playbooks

One line per playbook: `` - `playbooks/<name>.md`: <the request it fits> ``.

- `playbooks/autonomous-run.md`: a request to keep working by yourself until a stated, checkable condition holds ("keep going until no call site uses the old API"); one metric from one command is hillclimb, a failing check or reported defect is bug-fix, a plan or roadmap to run is implement, and "stop for today" is pause-safely.
- `playbooks/bug-fix.md`: a reported defect, failing check or flaky test to fix with proof.
- `playbooks/eval.md`: an instruction or routing variant to try on fresh Claude Code sessions and judge from what they did, not a reference capability to weigh for adoption.
- `playbooks/feature.md`: new behaviour to design and build, with no settled plan to execute; a build whose units or questions are unsettled goes to multi-phase-plan first, and settled work to plan stays planning.
- `playbooks/hillclimb.md`: sustained improvement of one measurable metric from one repeatable command against a stop predicate, attended, or unattended when the request says so (overnight, while away), with no settled plan to execute; one fix is perf-issue, a plan to run is implement, and a variant judged on fresh sessions is eval.
- `playbooks/investigation.md`: a question about how this repository's code works, why it has its shape or which design to pick, answered from source and history; not a failure, a measurement or a captured artifact.
- `playbooks/multi-phase-plan.md`: a request to produce a plan for several independently verifiable units, or work whose open questions must be settled before planning; a request to build is feature, and an existing roadmap phase, an approved spec to split or a settled plan keeps its route (planning, implement).
- `playbooks/pause-safely.md`: an explicit request to stop now so a later session can resume ("stop for today", "save this for later"); "keep going" is no pause, finished work to commit is land, and an idea to keep is a deferred bead.
- `playbooks/perf-issue.md`: a measured or reported slowness or resource cost to fix once against a target, with no settled plan; a failure or a regression whose cause is unknown is bug-fix, and repeated climbing of one metric is hillclimb.
- `playbooks/refactoring.md`: a focused structure change that must keep behaviour unchanged, with no settled plan to execute, including a focused redesign of internals; changed behaviour is a feature; staged work across many modules goes to multi-phase-plan first when its units or questions are unsettled, and settled staged work to plan stays planning.
- `playbooks/runtime-forensics.md`: a process running now (spinning, leaking, stuck) to diagnose from a live capture, with no fix wanted; an artifact captured earlier is trace-forensics.
- `playbooks/session-pickup.md`: a request to resume work a prior session or agent left, where this conversation does not hold its state ("where were we", "pick up cr-abc"); a "continue" that it does hold just goes on, and a settled plan to run is implement.
- `playbooks/trace-forensics.md`: an artifact captured earlier (trace, profile, heap dump, core) to explain, with no fix wanted and nothing new to measure.
- `playbooks/worktree-cleanup.md`: stale Git worktrees to audit and prune.

## Principles

One line per principle: `` - `principles/<name>.md`: <the situation it applies in> ``.

- `principles/attack-the-premise.md`: two or more fixes resting on one belief have failed the same gate (test, review, eval).
- `principles/boundary-discipline.md`: wiring validation, error handling or a framework adapter.
- `principles/experience-first.md`: a product, UX or feature-scope tradeoff.
- `principles/explain-the-number.md`: before measuring, or before trusting, reporting or acting on a measured number (performance or eval).
- `principles/make-operations-idempotent.md`: designing a command, lifecycle step or loop that may crash, restart or retry.
- `principles/migrate-without-shims.md`: replacing an internal API no external user depends on, as part of a simplification in a project that can absorb a coordinated break; or running a planned rewrite or migration with declared phase boundaries.
- `principles/minimize-reader-load.md`: reviewing or shaping code that is hard to trace.
- `principles/model-the-domain.md`: writing stateful logic, a growing if/else chain, or a shape assumption repeated across files.
- `principles/redesign-from-first-principles.md`: integrating a new requirement the existing design visibly cannot hold.
- `principles/separate-before-serializing-shared-state.md`: concurrent actors (processes, agents, workers) in code or tooling being designed might write the same file, branch, key or object.
- `principles/sequence-verifiable-units.md`: multi-step work (a sweep, a migration, a run of similar edits) or stacking commits.
- `principles/subtract-before-you-add.md`: sequencing an addition, refactor or rewrite.
- `principles/test-behavior-not-implementation.md`: writing, changing or keeping any test.
- `principles/type-system-discipline.md`: designing types or a function signature in a typed language.

## Skills by situation

Only where a description alone would miss or collide.

| Situation | Route |
|---|---|
| A single lookup in the code | Answer from the source; an external codebase: `/codebase-research` |
| Interview that should also record terms and decisions | `/grill-with-docs`, only when asked; otherwise `grilling` |
| Decisions that depend on each other across sessions | `/wayfinder` |
| Survey an area for architecture improvements | `/improve-codebase-architecture` |
| Untriaged beads need decisions | `/triage`; routine tracking follows `AGENTS.md` |
| A picture of the current topic, inline | `/show-me` when asked; an ordinary table needs nothing |
| Several candidates of one artifact, then the best picked and grafted, when a person asks | `model-council`, pick-and-graft branch; two options to weigh is `codebase-design`, and two to try is `prototype` |
| A rerunnable tool would materially cut repeated work (bulk or repeated edits, a migration) or supply proof a reviewer needs that no existing check gives | `build-a-lever` |
| An interaction or architecture with no precedent in the codebase, or a product decision whose experience depends on feel | `prototype`, competing-variants branch |
