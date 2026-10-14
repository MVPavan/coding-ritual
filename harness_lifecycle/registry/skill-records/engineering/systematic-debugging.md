---
skill: systematic-debugging
domain: engineering
stage: Building
substage: Diagnosis
secondary: []
family: debugging
aliases: []
status: active
---
# systematic-debugging

## Capability

Use when a failure cause is unclear, an attempted fix failed, or flaky behavior needs investigation. Handle obvious localized errors with a focused reproduction and fix.

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs** `reference_harnesses/mattpocock_skills/skills/engineering/diagnosing-bugs/SKILL.md` @ 84fdeff
  - merged from: systematic-debugging
  - merged from: debugging-and-error-recovery
  - modified: absorb systematic-debugging's three-fixes escalation rule, per-boundary evidence requirement and its three technique assets
  - modified: absorb debugging-and-error-recovery's non-reproducible decision tree and bisect method
  - dropped: debugging-and-error-recovery's safe-fallback and graceful-degradation patterns — they directly contradict the find-the-root-cause gate the other two enforce. You cannot keep a hard gate and a time-pressure symptom-patch path in one skill without the gate degrading into advice
- **agent-skills:skill:skills/debugging-and-error-recovery** `skills/debugging-and-error-recovery/SKILL.md` @ 7676817
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs** `skills/engineering/diagnosing-bugs/SKILL.md` @ 84fdeff
  - merged from: systematic-debugging
  - merged from: debugging-and-error-recovery
  - modified: absorb systematic-debugging's three-fixes escalation rule, per-boundary evidence requirement and its three technique assets
  - modified: absorb debugging-and-error-recovery's non-reproducible decision tree and bisect method
  - dropped: debugging-and-error-recovery's safe-fallback and graceful-degradation patterns — they directly contradict the find-the-root-cause gate the other two enforce. You cannot keep a hard gate and a time-pressure symptom-patch path in one skill without the gate degrading into advice
- **superpowers:skill:skills/systematic-debugging** `skills/systematic-debugging/SKILL.md` @ 44c9b2d
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-14` **adopt** (2026-10-14-migration:157): Adopted-absorbed into the rebuilt systematic-debugging skill (2026-08-14, evidence: skill-comparisons/debugging-loop/, per casebook bucket-06 round-001 absorb …
- `2026-08-14` **adopt-merged** (2026-10-14-migration:136): Adopted as the SPINE of the rebuilt systematic-debugging skill (2026-08-14, evidence: skill-comparisons/debugging-loop/, implementing casebook bucket-06 round-…
- `2026-08-14` **adopt** (2026-10-14-migration:126): Re-recorded 2026-08-14, superseding the stale 2026-07-15 'covered by our workflow' claim which held only at step-name level (evidence: skill-comparisons/debugg…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:052) *(superseded)*: The only skill that makes building a reliable reproduction the skill itself, with a checkable phase-one exit: one command, already run at least once, that show…
<!-- /registry:generated history -->
