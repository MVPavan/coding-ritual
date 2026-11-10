---
name: to-tickets
description: "Use when an approved spec should be split into tracked work: phases, stages with acceptance and real dependency edges in Beads. Skip writing an implementation plan for settled work, which is planning."
---

# To tickets

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

Prefer independently verifiable vertical slices. Sequence any prefactoring that makes
the change easy before the feature slices. For a broad refactor, use
expand → migrate → contract with genuine dependencies. Size migrate batches by blast
radius and keep the build green between them. If intermediate stages cannot remain
green, name one integration boundary or atomic group explicitly.

## Seed

No Beads write before the structure is approved; recorded approval counts. Then
seed epics and stages, wire the edges and render tracking. A single-phase spec may
use one epic and a `planning` plan without creating a workstream. Write later
phase plans just in time, with `planning`, against the code those phases will
encounter.

This skill's output is tracked work. Continue into `implement` only when that is
already authorized.
