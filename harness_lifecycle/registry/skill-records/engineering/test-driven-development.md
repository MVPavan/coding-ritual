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

<!-- registry:generated traits -->
- `mode-selection`: Choose test-first, characterization, or test-quality-only by the task rather than defaulting to one workflow.
- `seam-selection`: Choose the test boundary that exercises the real contract without reaching inside. (The smallest such boundary.)
- `plan-seams-no-approval`: Take test seams from the plan without separate approval, surfacing a missing seam only when it materially changes scope or the obtainable evidence.
- `red-green`: Make one test fail before implementing the change that makes it pass. (Confirms the intended failure, not a setup error, then implements the owning fix and reruns the proving check.)
- `refactor-after-green`: Refactor after each passing test, preserving behaviour and rerunning the affected checks.
- `mock-boundaries`: Use test doubles only at boundaries, never in place of the behaviour under test. (Fakes and partial mocks are valid at any boundary that preserves the contract.)
- `proof-discipline`: Keep enough before-and-after evidence to distinguish a demonstrated fix from an inference and never destroy edits to recreate RED.
- `meaningful-behaviour-assertion`: Assert meaningful results, state or boundary interactions at a stable boundary rather than internal call choreography.
- `independent-expectation`: Derive expected values from an independent source such as a spec, worked example or trusted fixture, never computing both sides with the implementation under test.
- `no-implementation-coupling`: Avoid tests coupled to the implementation's internal structure, so they survive behaviour-preserving refactors. (Asserts exact source text only when that text is the contract.)
- `deterministic-state`: Prefer deterministic inputs and isolated state, controlling time, randomness and shared state that cause nondeterminism.
- `break-naming-validation`: Before accepting substantive tests, name the specific wrong branch, missing validation or side effect they catch, confirming by a safe mutation trial rather than mental inspection when worth its cost.
<!-- /registry:generated traits -->

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

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
