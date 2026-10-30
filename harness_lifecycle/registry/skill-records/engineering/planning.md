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

Use when settled work needs a durable implementation plan, dependency graph, or workstream decomposition. Skip planning ceremonies for clear bounded tasks.

<!-- registry:generated traits -->
- `route-by-scale`: Route between brainstorming, a brief local sequence, elaborate, decompose, or executing from a roadmap row according to the work's scale.
- `decompose-phases`: Split an approved spec into demoable phases with checkable exits and flat stages that each carry acceptance.
- `vertical-slices`: Prefer independently verifiable vertical slices over horizontal layers.
- `expand-contract`: For a broad refactor use expand, migrate then contract with genuine dependencies, naming one integration boundary when intermediate tasks cannot stay green.
- `dependency-edges`: Encode real blocking edges in the tracker and let the ready frontier drive execution rather than listing order.
- `beads-native-tracking`: Seed epics and stages and render tracking natively in the tracker, keeping the roadmap anchor on the epics and the stage mapping that execution closes against, and writing nothing before its matching approval. (The roadmap anchor is the --spec-id and the governing spec is --design; the renderer derives the workstream from the anchor, so a plan path never goes in --design.)
- `durable-plan-format`: Produce a durable plan with ownership boundaries, interfaces, verification, dependencies and known files, saved to the plans path and approval-gated.
- `plan-evidence-bound`: List known files but do not invent exact symbols or freeze a file map without evidence, leaving implementers to discover internals within their ownership.
- `test-first-marking`: Mark risky changes test-first or characterization-first in the plan.
- `no-placeholder-plan`: Reject plan placeholders such as TBD, vague error-handling notes, unnamed test behaviours, same-as-another-task references and unresolved cross-task contracts, naming concrete acceptance instead.
- `plan-self-review`: Self-review the finished plan for spec-requirement coverage, consistent names and types across tasks, and a gap-naming pass that turns unnamed seams, migrations, rollout and cleanup into tasks or explicit exclusions.
- `reviewer-rejectable-sizing`: Size each task so a reviewer could accept or reject it independently of its neighbour, folding setup, scaffolding and docs into the deliverable they serve.
- `real-id-wiring`: Wire cross-references and dependencies with real identifiers, never placeholders.
- `no-stale-code-snippets`: Keep code snippets out of a durable spec or ticket because they go stale.
<!-- /registry:generated traits -->

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

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
