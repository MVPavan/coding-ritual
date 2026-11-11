---
name: to-roadmap
description: "Use when an approved multi-phase spec should become tracked work: its phases, stages with acceptance and their order, for a new workstream or extending one; tracker seeds them. A one-phase spec is to-plan, then tracker; the plan for one phase is to-plan."
---

# To roadmap

Split an approved multi-phase spec into phases and stages whose ready frontier
drives execution. One phase or several is decided from the spec and the owner's
evidence: several only where each has an independently checkable exit, and
dependent stages alone do not make several. Decide routine cases directly; ask only
on material ambiguity. One phase goes to `to-plan`, then `tracker`.

## Gather

Read the governing spec and only the relevant project constraints and current
Beads state. Confirm approval evidence; if it is missing, record the settled
decision in the spec rather than treating a draft as approved.

## Decompose

Use `references/decompose.md` for each phase's roadmap content and the approval
gate; the workstream layout and seeding are `tracker`'s. Reuse an obvious named
workstream; ask when the choice is consequential or unclear. Split
into demoable phases with checkable exits, flat stages with acceptance, and real
dependency edges. Independent subsystems need separate ownership, not necessarily
separate specs or another interview.

## Slice

Order the stages by `principle-sequence-verifiable-units`.

## Seed

No Beads write before the structure is approved; recorded approval counts. After
approval invoke `tracker` to seed or extend; nothing before. Write later phase
plans just in time, with `to-plan`, against the code those phases will
encounter.

This skill's output is tracked work. Continue into `implement` only when that is
already authorized.
