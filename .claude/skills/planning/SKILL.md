---
name: planning
description: "Use when settled work needs a durable implementation plan, dependency graph, or workstream decomposition: an existing roadmap phase, an approved spec to split, or a plan in a form someone names. A request to produce a plan for several units, or work whose open questions must be settled first, is the multi-phase-plan playbook, which calls this. Skip planning ceremonies for clear bounded tasks."
---

# Planning

Turn settled scope into executable work at the smallest useful scale.

## Route

| Situation | Path |
|---|---|
| Material behavior unresolved | Brainstorming for those decisions |
| Clear bounded task | Brief local sequence if useful; continue execution without a plan document |
| Durable implementation plan requested or needed for handoff | Elaborate |
| Approved spec needs phase/stage decomposition | Decompose |
| Standard phase with sufficient roadmap acceptance | Execute from its roadmap row |
| Plan to be run box by box with evidence per unit, when a calling playbook names this branch or someone asks for that form | Skeleton |

Reuse recorded approvals. Ask only about material scope, dependency or authority
choices that remain open. Planning-only requests authorize planning artifacts,
not implementation; when implementation is already authorized, continue to it.

## Decompose

Read the governing spec and only relevant project constraints and current Beads
state. Confirm approval evidence; if missing, record the settled decision in the
spec rather than treating a draft as approved.

Use `references/decompose.md` for layout, join keys and seeding commands. Reuse an
obvious named workstream; ask when the choice is consequential or unclear. Split
into demoable phases with checkable exits, flat stages with acceptance, and real
dependency edges. Independent subsystems need separate ownership, not necessarily
separate specs or an additional interview.

No Beads write before its matching approval: the structure in Decompose, the
plan in Elaborate. Recorded approval counts. Then seed epics/stages and render
tracking. A single-phase spec may use one epic
and an Elaborate plan without creating a workstream. Write later phase plans
just in time against the code those phases will encounter.

## Elaborate

Use `references/plan-format.md` for a durable plan. Read the origin, relevant
code and tests, and stage acceptance for phase work. Identify ownership boundaries,
interfaces, verification and dependencies. List known files; permit implementers
to discover internal details within that ownership. Do not invent exact symbols
or freeze a file map without evidence.

Every phase plan task names an existing `Stage: <epic>.N`; every stage has covering
tasks. Preserve this mapping because execution uses it to close stages. Mark
risky changes test-first or characterization-first as appropriate.

Check requirement coverage, compatibility, unresolved decisions, integration
risks, and what nobody has named yet. A plan with material risk gets a critic
review (review skill) before approval.

Save phase plans under `docs/workstreams/<name>/plans/`, standalone plans under
`docs/plans/`, or the supplied path. Put `plan: <path>` in Beads notes. A phase
epic's `--spec-id` holds its workstream roadmap and `--design` its governing
spec; other beads' `--spec-id` holds their spec. Neither holds a plan. Attribute
Beads writes with `--actor` and reuse existing records.

## Skeleton

Take this branch when a calling playbook names it or someone asks for a plan run box
by box with evidence per unit; an ordinary durable plan stays in Elaborate. Elaborate's
whole procedure still runs, its critic for material risk included. This branch changes
the plan's form and adds a check, not a second deliverable: write the plan as
`references/skeleton.md` lays out.

Last, run this skill's `scripts/check_plan.py <plan>` and fix every line it prints.
Only exit 0 passes; exit 3 means `## How to run this` is missing. Rerun after any later
edit, a caller's included, and report the last output. It proves structure only, never
that the evidence proves the Goal. After two rounds of fixes without exit 0, hand back
the output with the plan named as not ready.

## Slicing

Prefer independently verifiable vertical slices. Sequence any prefactoring that makes
the change easy before the feature slices. For broad refactors, use
expand → migrate → contract with genuine dependencies. Size migrate batches by blast
radius and keep the build green between them. If intermediate tasks
cannot remain green, name one integration boundary or atomic group explicitly.
A plan is ready when an implementer can identify acceptance, ownership and the
next ready unit; unresolved material decisions remain visible blockers.
