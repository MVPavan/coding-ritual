---
skill: execution
domain: engineering
stage: Building
substage: Implementation
secondary: []
family: plan-execution
aliases: [phase-execution, run-phases]
status: active
---
# execution

## Capability

Use to execute tracked multi-step work, a standalone plan, or a roadmap phase. Clear bounded implementation can proceed directly under AGENTS.md.

<!-- registry:generated lineage -->
- **superpowers:skill:skills/subagent-driven-development** `reference_harnesses/superpowers/skills/subagent-driven-development/SKILL.md` @ 44c9b2d
  - merged from: executing-plans
  - modified: absorb executing-plans as a degraded inline mode for when subagents are unavailable
- **superpowers:skill:skills/subagent-driven-development** `skills/subagent-driven-development/SKILL.md`
  - merged from: executing-plans
  - modified: absorb executing-plans as a degraded inline mode for when subagents are unavailable
- **agent-skills:skill:skills/code-simplification** `skills/code-simplification/SKILL.md` @ 7676817
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-14` **adopt** (2026-10-14-migration:125): Correction 2026-08-14 (stale-claim audit, post-implementation-passes Round 2): previous reason 'covered by ak-guide' was false — ak-guide carried 6/45 componen…
- `2026-08-12` **adopt-merged** (2026-10-14-migration:111): Adopted-merged into the execution skill's task engine (comparison: harness_lifecycle/skill-comparisons/plan-execution-engines/): bounded 5-round fix loop with …
- `2026-08-11` **adopt-merged** (2026-10-14-migration:046) *(superseded)*: The only plan executor with bounded fix loops, capability escalation and an adjudication ledger that survives compaction. Superpowers' own writing-plans names …
<!-- /registry:generated history -->
