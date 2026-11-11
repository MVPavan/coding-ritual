---
name: to-plan
description: "Use when settled work needs a durable implementation plan: one roadmap phase, one standalone change, or one batch of units written box by box when a caller names that form. Turning an approved multi-phase spec into phases and their order is to-roadmap; a one-phase spec is planned here and recorded by tracker; a person's request to plan several units, or work whose open questions must be settled first, is the multi-phase-plan playbook, which calls this. Skip a plan document for clear bounded tasks."
---

# To plan

Turn settled scope into executable work at the smallest useful scale. An approved
spec is one phase or several by the spec and the owner's evidence: several only
where each has an independently checkable exit, and dependent stages alone do not
make several. Decide routine cases directly; ask only on material ambiguity.

## Route

| Situation | Path |
|---|---|
| A clear bounded task, or a roadmap phase whose row's acceptance already says enough | No plan document: say so, give a brief local sequence if useful, and continue only into implementation already authorized |
| Durable implementation plan requested or needed for handoff | Elaborate |
| Plan to be run box by box with evidence per unit, when a calling playbook names this branch or someone asks for that form | Skeleton |

Reuse recorded approvals. Ask only about material scope, dependency or authority
choices that remain open. Planning-only requests authorize planning artifacts,
not implementation; when implementation is already authorized, continue to it.

## Elaborate

Use `references/plan-format.md` for a durable plan. Read the origin, relevant
code and tests, and stage acceptance for phase work. Identify ownership boundaries,
interfaces, verification and dependencies. List known files; permit implementers
to discover internal details within that ownership. Do not invent exact symbols
or freeze a file map without evidence.

A seeded roadmap phase's task names its existing `Stage: <epic>.N`; a new one-phase
plan names `Stage: proposed <name>` and writes no Beads; after approval `tracker`
binds each to its ID. Every stage has covering tasks. Preserve this mapping because
`implement` uses it to close stages. Mark
risky changes test-first or characterization-first as appropriate.

Check requirement coverage, compatibility, unresolved decisions, integration
risks, and what nobody has named yet. A plan with material risk gets a critic
review (review skill) before approval.

No Beads write, the task or its `plan:` note, before the plan is approved;
recorded approval that covers this concrete plan counts.

Save phase plans under `docs/workstreams/<name>/plans/`, standalone plans under
`docs/plans/`, or the supplied path. Once approved, invoke `tracker` to record it:
the plan note, one epic and stages for one-phase work, binding the plan's proposed
stages to their IDs.

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

Order the tasks by `principle-sequence-verifiable-units`.

## Ready

A plan is ready when an implementer can identify acceptance, ownership and the
next ready unit; unresolved material decisions remain visible blockers.
