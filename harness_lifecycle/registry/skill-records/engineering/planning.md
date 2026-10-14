---
skill: planning
domain: engineering
stage: Design
substage: Decomposition
secondary: []
family: plan-authoring
aliases: []
status: active
---
# planning

## Capability

Use when settled work needs a durable implementation plan, dependency graph, or workstream decomposition. Skip planning ceremonies for clear bounded tasks.

<!-- registry:generated lineage -->
- **superpowers:skill:skills/writing-plans** `reference_harnesses/superpowers/skills/writing-plans/SKILL.md` @ 44c9b2d
  - merged from: planning-and-task-breakdown
  - merged from: to-tickets
  - modified: absorb planning-and-task-breakdown's task sizing and ordering detail
  - modified: absorb to-tickets as an OUTPUT MODE (plan file / tracker tickets with native blocking links / both) — the judge overruled the member who dropped this, because that member had itself called the loss 'the highest-value loss in this ledger'
  - modified: absorb to-tickets' wide-refactor expand-then-contract rule
- **agent-skills:skill:skills/incremental-implementation** `skills/incremental-implementation/SKILL.md`
- **mattpocock_skills:skill:skills/engineering/to-tickets** `skills/engineering/to-tickets/SKILL.md`
- **superpowers:skill:skills/writing-plans** `skills/writing-plans/SKILL.md`
  - merged from: planning-and-task-breakdown
  - merged from: to-tickets
  - modified: absorb planning-and-task-breakdown's task sizing and ordering detail
  - modified: absorb to-tickets as an OUTPUT MODE (plan file / tracker tickets with native blocking links / both) — the judge overruled the member who dropped this, because that member had itself called the loss 'the highest-value loss in this ledger'
  - modified: absorb to-tickets' wide-refactor expand-then-contract rule
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-12` **adopt-merged** (2026-10-14-migration:113): Adopted-merged into the rewritten planning skill (Elaborate mode): file-map-before-tasks, Interfaces Consumes/Produces, reviewer right-sizing test, no-placehol…
- `2026-08-12` **adopt** (2026-10-14-migration:104): Adopted-merged narrowly into the planning rewrite: expand-contract sequencing for wide refactors incl. non-green-batch integration-branch fallback, tracer-bull…
- `2026-08-12` **adopt** (2026-10-14-migration:096): Closes the 2026-07-15 deferral. Ruled a discipline by execution-disciplines/; its durable content is now distributed: vertical slicing + tracer bullets in plan…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:033) *(superseded)*: The only skill turning approved work into units executable with zero prior context. Chosen as merge base for its plan structure and required-sub-skill header.
<!-- /registry:generated history -->
