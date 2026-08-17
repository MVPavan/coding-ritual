---
name: planning
description: Use when an approved spec needs to become tracked work, when a deep phase of a roadmap needs an implementation plan before execution, or when a bounded multi-step ask needs a plan before coding. If scope or behaviour is still unsettled, use brainstorming first. Trigger it on plan phrases.
---

# Planning

Turns settled scope into tracked, executable work. Two modes: **Decompose** cuts
an approved spec into a workstream — roadmap plus seeded bd epics and stages.
**Elaborate** turns one unit of work into an implementation plan.

## Route

Take the first row that matches.

| Input state | Do |
|---|---|
| Scope or behaviour unsettled — directions still live, success undefined | the `brainstorming` skill, then return here |
| Phase of an existing roadmap, deep or risky, reached by execution | **Elaborate** |
| Phase of an existing roadmap, standard | no plan file — execution runs from the roadmap row |
| Workstream-scale work whose spec is missing or not `Status: approved` | `brainstorming` to finish the spec, then return here |
| Approved spec spanning several phases of work | **Decompose** |
| Approved spec that is one phase of work | **Decompose** — single-phase exit |
| Bounded multi-step ask, behaviour clear, no workstream needed | **Elaborate** directly |

In a multi-phase roadmap, plans are written just-in-time — one phase at a
time, when execution reaches that phase — never batch-written at decompose
time against a codebase that earlier phases will change. A single-phase spec
has no later phases to drift under it, so it elaborates immediately.

## Decompose

Mechanics — workstream layout, seeding commands, approval-gate format,
extending an existing workstream: `references/decompose.md`.

1. **Ground** — read the spec (verify `Status: approved`), then the repo's
   read order: `CLAUDE.md`, `CONTEXT.md`, `.claude/project/` (`brief.md`,
   `repo-map.md`, `invariants.md`, `verification.md`, `docs-index.md`), and
   the current board state (`docs/workstreams/status.md` if it exists, else
   `bd stats` + `bd list`).
2. **Scope-check** — three outcomes. The spec spans independent subsystems
   (separable concerns that could ship alone): back to `brainstorming` to
   split it into per-subsystem specs. One phase of work: take the
   single-phase exit below. Several dependent phases: continue.
3. **Ask** the user: new workstream, or extend an existing one. Do not assume.
4. **Roadmap** — phases as vertical slices, each ending demoable with a
   checkable exit criterion. Per phase: Goal, deliverables table with Verify
   cells, spec references, exit criterion, test focus, risk (standard/deep).
   Dependency edges — real ones only, at both grains (epic→epic, stage→stage).
5. **Approval gate** — present the phase/stage/dependency graph with risk
   labels; iterate until the user approves the structure by name. **Nothing is
   seeded before this approval.**
6. **Seed bd** — epic per phase, flat stage children, `--acceptance` copied
   from each Verify cell, real dependency edges. Render the tracking mirrors.
7. **Summarize** — phases and stages seeded, execution order, risk per phase,
   and the execution command that comes next.

**Single-phase exit** — the approval gate still applies, at the smaller
grain: present the stage list and dependencies, get approval, seed one epic
with its stages (`references/decompose.md`), then go to Elaborate. The result
executes at task scope, from the plan and its bd stages — no roadmap or
workstream is created.

## Elaborate

Plan header, the task template, standalone bd record, and the self-review
checklist: `references/plan-format.md`.

1. **Ground** — the origin is the approved spec or the phase's roadmap row;
   for phase work, read the stages' acceptance criteria from bd first. Read
   the repo read-order docs as in Decompose. Research code, tests, docs, and
   prior learnings read-only before fixing the plan's shape; follow existing
   patterns before introducing new abstractions.
2. **File map before tasks** — name every file to create or modify and each
   one's single responsibility; files that change together live together.
   Decomposition is locked here, not during task writing.
3. **Cut tasks** — each task carries create/modify/test paths, an Interfaces
   block (Consumes/Produces), verification, dependencies, and a risk note;
   mark risky behaviour changes test-first or characterization-first.
   Right-size with the reviewer test in the template. **Phase work:** every
   task names the bd stage it serves (`Stage: <epic>.N`), and every stage of
   the phase appears in the plan — closing a stage means its tasks are done
   and its acceptance holds.
4. **Self-review** — spec coverage, placeholder scan, name/type consistency,
   and the gap-naming pass: "what has nobody named?"
5. **Critique** — for standard and deep work (the repo's Working Mode
   classification), get an independent critique of the plan — a plan
   critique, not a git-diff review — from a spawned critic subagent
   (CLAUDE.md §Independent critique).
6. **Approve, save, record** — show the plan to the user for standard and
   deep work; small bounded work may proceed on stated assumptions. Save
   phase plans to `docs/workstreams/<name>/plans/<phase>.md`, standalone
   plans to `docs/plans/` (a caller- or user-specified path overrides
   either). Record the plan path in the epic's or task's **notes**
   (`plan: <path>`) — never in `--design`, which carries the roadmap.
   Standalone work with no bd record yet gets the minimal one — a single
   task created per the plan-format contract, dotted children only for
   genuinely independent units; no epic, no workstream.
7. **Hand off** — name the execution surface (phase execution resumes for
   phase work; task-scope execution for single-phase and standalone plans)
   and stop.

## Slicing and dependencies

Vertical slicing applies at the outermost unit of delivery:

- **Workstream** — the phase is the vertical slice: each phase ends demoable,
  with a checkable exit criterion. Stages inside a phase may be horizontal;
  the phase's exit criterion closes the loop above them.
- **Standalone plan** — no phase closes the loop, so the plan itself must
  slice vertically: tracer bullet first (the smallest end-to-end path that
  proves the route), then tasks that each leave the system working.
- Vertical task cuts stay the default wherever they cost nothing extra;
  horizontal is the permitted exception, not the norm.
- **Wide refactors** are the named exception to tracer bullets: sequence them
  expand → migrate-in-batches → contract, each batch its own stage blocked by
  the expand, contract blocked by every batch. When batches cannot stay green
  alone, keep the sequence on a shared integration branch, all blocking a
  final integrate-and-verify stage — green is promised only there.
- When no green split of a change exists, say so in the plan and mark those
  tasks as one atomic commit group rather than pretending each lands alone.

Dependencies recur at both grains under one rule — chain only genuine edges,
never listing order. Decompose records them in bd (durable, drives
`bd ready`); Elaborate orders tasks inside one plan.

## Rules

- This skill writes documents and bd records — never code.
- Verify `Status: approved` before decomposing; a draft spec is not a handoff.
- No bd write before its matching approval: the structure gate in Decompose,
  the plan approval in Elaborate.
- An epic's `--design` carries the roadmap — never overwrite it with a plan
  path; plan paths go in notes.
- `--actor` on every bd write; conservative git — report proposed commands, do
  not commit.
- Plans are repo-relative. No pre-written code blocks or shell choreography in
  tasks — the Interfaces block carries the contract.
- One task template — `references/plan-format.md`. Do not invent variants.
