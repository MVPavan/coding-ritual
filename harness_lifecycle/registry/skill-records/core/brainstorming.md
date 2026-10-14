---
skill: brainstorming
domain: core
stage: Intake
substage: Clarification
secondary: [Specification]
family: spec-authoring
aliases: [idea-refine]
status: active
---
# brainstorming

## Capability

Use when material scope or behavior decisions need exploration, or the user requests brainstorming. Handle a single routine ambiguity directly.

<!-- registry:generated lineage -->
- **agent-skills:skill:skills/spec-driven-development** `reference_harnesses/agent-skills/skills/spec-driven-development/SKILL.md` @ 7676817
  - merged from: brainstorming
  - merged from: to-spec
  - modified: absorb brainstorming's hard design-approval gate, decomposition check and self-review
  - modified: absorb to-spec's no-interview fast path for when discussion has already settled
  - dropped: brainstorming's ~1,400-line visual-companion server bundle — heavy dependency, and prototype already covers the need
- **agent-skills:skill:skills/interview-me** `skills/interview-me/SKILL.md`
- **agent-skills:skill:skills/spec-driven-development** `skills/spec-driven-development/SKILL.md`
  - merged from: brainstorming
  - merged from: to-spec
  - modified: absorb brainstorming's hard design-approval gate, decomposition check and self-review
  - modified: absorb to-spec's no-interview fast path for when discussion has already settled
  - dropped: brainstorming's ~1,400-line visual-companion server bundle — heavy dependency, and prototype already covers the need
- **mattpocock_skills:skill:skills/engineering/to-spec** `skills/engineering/to-spec/SKILL.md`
- **superpowers:skill:skills/brainstorming** `skills/brainstorming/SKILL.md`
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-12` **adopt** (2026-10-14-migration:109): Revisited 2026-08-12: still merged into ours, not installed. Per-unit boundary questions now live in the spec template's Implementation Decisions section (temp…
- `2026-08-12` **adopt** (2026-10-14-migration:103): Revisited 2026-08-12: now the SKELETON of references/spec-template.md — Problem Statement, Solution, User Stories, Implementation Decisions, Testing Decisions,…
- `2026-08-12` **adopt-merged** (2026-10-14-migration:099): Revisited 2026-08-12: spec half only, split from its plan/tasks/implement phases (those belong to our prepare-phases/planning/phase-execution). Taken into the …
- `2026-08-11` **adopt** (2026-10-14-migration:086): Mechanics merged into brainstorming, not installed as a skill. Taken: predict-the-next-three stop test, approval-names-the-direction gate with the four near-mi…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:026) *(superseded)*: The only skill producing an approved written spec behind a hard no-implementation gate, with a six-area content model. Chosen as the merge base over to-spec be…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->
