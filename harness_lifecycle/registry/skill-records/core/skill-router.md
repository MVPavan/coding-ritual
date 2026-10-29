---
skill: skill-router
domain: core
stage: X
substage: Coordination
secondary: []
family: skill-routing
aliases: []
status: active
---
# skill-router

## Capability

Use when unsure which skill or command fits a task, when two seem to overlap, or when the user asks what skills or commands exist, what one does, or which to use.

<!-- registry:generated traits -->
- `need-to-skill-routing`: Map a task need to the narrowest fitting skill or command, or to no skill at all.
- `narrowest-contract`: Default to the narrowest useful specialist contract, with clear bounded work needing no skill and the router treated as optional rather than a startup checklist.
- `overlap-arbitration`: Name the single owner when two skills or commands appear to overlap.
- `legacy-entrypoint-flagging`: Flag thin aliases and retired workflows so their retired steps are not recommended as automatic.
- `catalog-trust-boundary`: Treat the generated skill catalog as canonical but not proof, verifying actual runtime discovery before relying on availability.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/engineering/ask-matt** `skills/engineering/ask-matt/SKILL.md` @ 84fdeff
- **mattpocock_skills:skill:skills/in-progress/setup-ts-deep-modules** `skills/in-progress/setup-ts-deep-modules/SKILL.md` @ 84fdeffd12f2ee307994d1eb6feb48173b6e0502
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-14` **adopt** (2026-10-14-migration:143): Adopted 2026-08-14 pattern-only (evidence: skill-comparisons/harness-bootstrap/): prove-the-rules-bite (SKILL.md:79-87) — observe a guardrail fail on a deliber…
- `2026-08-14` **adopt** (2026-10-14-migration:134): Round 2 supersede: PHASE-BOUNDARIES.md deferral resolved — three borrows into execution/references/workstream-mode.md (/compact with an instruction argument; r…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [skill-comparisons/harness-bootstrap](../../../archive/skill-comparisons/harness-bootstrap/)
- [skill-comparisons/plan-execution-engines](../../../archive/skill-comparisons/plan-execution-engines/)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
