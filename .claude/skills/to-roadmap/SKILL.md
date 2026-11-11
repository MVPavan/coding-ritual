---
name: to-roadmap
description: "Use when an approved spec should become tracked work: its phases, stages with acceptance and their order in Beads, for a new workstream or extending an existing one. Writing the implementation plan for one phase or one change is to-plan."
---

# To roadmap

Split an approved spec into tracked work whose ready frontier drives execution.

## Gather

Read the governing spec and only the relevant project constraints and current
Beads state. Confirm approval evidence; if it is missing, record the settled
decision in the spec rather than treating a draft as approved.

## Decompose

Use `references/decompose.md` for layout, join keys and seeding commands. Reuse an
obvious named workstream; ask when the choice is consequential or unclear. Split
into demoable phases with checkable exits, flat stages with acceptance, and real
dependency edges. Independent subsystems need separate ownership, not necessarily
separate specs or another interview.

## Slice

Order the stages by `principle-sequence-verifiable-units`.

## Seed

No Beads write before the structure is approved; recorded approval counts. Then
seed epics and stages, wire the edges and render tracking. A single-phase spec may
use one epic and a `to-plan` plan without creating a workstream. Write later
phase plans just in time, with `to-plan`, against the code those phases will
encounter.

This skill's output is tracked work. Continue into `implement` only when that is
already authorized.
