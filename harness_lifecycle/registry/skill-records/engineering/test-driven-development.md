---
skill: test-driven-development
domain: engineering
stage: Building
substage: Implementation
secondary: [Specification]
family: tdd
aliases: []
status: active
---
# test-driven-development

## Capability

Use for risky behavior changes, regression proof, legacy characterization, or substantive test design. Trivial test renames do not require a test-first workflow.

<!-- registry:generated lineage -->
- **superpowers:skill:skills/test-driven-development** `reference_harnesses/superpowers/skills/test-driven-development/SKILL.md` @ 44c9b2d
  - merged from: test-driven-development (agent-skills)
  - merged from: tdd (mattpocock)
  - modified: absorb agent-skills' test-stack discovery, Prove-It rule and test-size model
  - modified: absorb mattpocock's pre-agreed seams and mockability guidance
  - modified: add a characterization-test allowance for legacy code — this matches the repo's own testing rule
- **agent-skills:skill:skills/test-driven-development** `skills/test-driven-development/SKILL.md`
- **mattpocock_skills:skill:skills/engineering/tdd** `skills/engineering/tdd/SKILL.md`
- **superpowers:skill:skills/test-driven-development** `skills/test-driven-development/SKILL.md`
  - merged from: test-driven-development (agent-skills)
  - merged from: tdd (mattpocock)
  - modified: absorb agent-skills' test-stack discovery, Prove-It rule and test-size model
  - modified: absorb mattpocock's pre-agreed seams and mockability guidance
  - modified: add a characterization-test allowance for legacy code — this matches the repo's own testing rule
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-12` **adopt-merged** (2026-10-14-migration:112): Adopted-merged into the rewritten TDD skill (comparison: execution-disciplines/): writing-good-tests content — name-the-break gate, mirror-assertion/change-det…
- `2026-08-12` **adopt** (2026-10-14-migration:102): Adopted-merged (comparison: execution-disciplines/): seams as pre-agreed public test boundaries — adapted from a live human gate to the plan's new 'Test seams:…
- `2026-08-12` **adopt** (2026-10-14-migration:100): Superseding correction of the 2026-07-15 entry, whose 'covered by the local loop' claim was wrong about everything except the loop (comparison: execution-disci…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:050) *(superseded)*: The only discipline gate whose violation is recoverable only by deleting the code, with a mandatory watched-RED step. Chosen as merge base for enforcement stre…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->
