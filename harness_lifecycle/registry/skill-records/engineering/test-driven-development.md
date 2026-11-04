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

Use for risky behavior changes, regression proof, legacy characterization, or substantive test design. Trivial test renames do not require a test-first workflow.

**Boundary:** Runs the test-first cycle for risky behaviour changes, regression proof and characterization; ordering multi-step work and commits into checked units is principle-sequence-verifiable-units.

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
- `per-seam-note`: Give each proposed seam a one-line note on what it catches and what it misses.
- `one-test-per-cycle`: Alternate one test and its implementation at a time instead of writing all tests before any implementation.
- `behaviour-test-names`: Name each test for the behaviour that exists, not how it is achieved.
- `prove-the-red`: When forcing the red by mutating code or a fixture, diff against a pristine copy to prove the mutation landed before trusting it.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **superpowers:skill:skills/test-driven-development** `reference_harnesses/superpowers/skills/test-driven-development/SKILL.md` @ 44c9b2d
  - merged from: test-driven-development (agent-skills)
  - merged from: tdd (mattpocock)
  - modified: absorb agent-skills' test-stack discovery, Prove-It rule and test-size model
  - modified: absorb mattpocock's pre-agreed seams and mockability guidance
  - modified: add a characterization-test allowance for legacy code — this matches the repo's own testing rule
- **agent-skills:skill:skills/test-driven-development** `skills/test-driven-development/SKILL.md`
- **superpowers:skill:skills/test-driven-development** `skills/test-driven-development/SKILL.md`
  - merged from: test-driven-development (agent-skills)
  - merged from: tdd (mattpocock)
  - modified: absorb agent-skills' test-stack discovery, Prove-It rule and test-size model
  - modified: absorb mattpocock's pre-agreed seams and mockability guidance
  - modified: add a characterization-test allowance for legacy code — this matches the repo's own testing rule
- **mattpocock_skills:skill:skills/engineering/tdd#meaningful-behaviour-assertion** `skills/engineering/tdd/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/tdd#no-implementation-coupling** `skills/engineering/tdd/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/tdd#independent-expectation** `skills/engineering/tdd/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/tdd#red-green** `skills/engineering/tdd/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/tdd#system-boundary-mocks-only** `skills/engineering/tdd/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs#seam-selection** `skills/engineering/diagnosing-bugs/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/implement-spec#red-green** `skills/engineering/implement-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **cursor_plugins:skill:pstack/skills/principle-test-behavior-not-implementation#meaningful-behaviour-assertion** `pstack/skills/principle-test-behavior-not-implementation/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-test-behavior-not-implementation#independent-expectation** `pstack/skills/principle-test-behavior-not-implementation/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **mattpocock_skills:skill:skills/engineering/tdd#per-seam-note** `skills/engineering/tdd/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/tdd#one-test-per-cycle** `skills/engineering/tdd/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/tdd#behaviour-test-names** `skills/engineering/tdd/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs#prove-the-red** `skills/engineering/diagnosing-bugs/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-01` **adopt** (2026-11-01-batch-1:202): Completes pending 2026-11-01-pocock-retarget:006: prove-the-red is written at .claude/skills/test-driven-development/SKILL.md:34-35, read against its definitio…
- `2026-11-01` **adopt** (2026-11-01-batch-1:201): Completes pending 2026-10-30-mattpocock_skills-5beb35b:214: behaviour-test-names is written at .claude/skills/test-driven-development/references/writing-good-t…
- `2026-11-01` **adopt** (2026-11-01-batch-1:200): Completes pending 2026-10-30-mattpocock_skills-5beb35b:203: one-test-per-cycle is written at .claude/skills/test-driven-development/SKILL.md:29-31, read agains…
- `2026-11-01` **adopt** (2026-11-01-batch-1:199): Completes pending 2026-10-30-mattpocock_skills-5beb35b:201: per-seam-note is written at .claude/skills/test-driven-development/SKILL.md:25, read against its de…
- `2026-11-01` **update** (2026-11-01-batch-1:197): Delivers four ruled traits with their sealed rewordings: a per-seam note, one behaviour per cycle, the pristine-copy diff guard on a forced red, and test names…
- `2026-11-01` **adopt** (2026-11-01-pocock-retarget:006) *(superseded)*: Owner ruling 2026-11-01: the regression check left the diagnosis; confirming the red is test-driven-development's technique (S3, B3).
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:128): Checkpoint at 4dd1d05 for the owner's trait rulings: 8 adopt.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:122): Lands as covered. Ours derives expected values from requirements, never from the code under test.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:120): Lands as covered. writing-good-tests asserts results, state or boundary interactions, not choreography.
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:569): Checkpoint at 5beb35b for the owner's trait rulings: 10 adopt, 9 defer.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:282): POINTER: execution SKILL.md:40-41 sends each task to test-first or characterization (test-driven-development's modes) when risk calls for it, rather than alway…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:239): HELD: test-driven-development (.claude/skills/test-driven-development/SKILL.md:20-24): Choosing the test boundary is test-driven-development's rule (SKILL.md:2…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:215): Owner deferred the report's reject recommendation, to review the set later: Ours already decides real-versus-double by cost and contract for every boundary (wr…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:214) *(superseded)*: Ours says nothing about test names; behaviour names make a failure readable without the source, and one line in the test reference carries it.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:213): Owner deferred the report's reject recommendation, to review the set later: A fixed one-assertion rule constrains a context-dependent choice (S-08) and conflic…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:211): Owner deferred the report's reject recommendation, to review the set later: ROUTED: AGENTS.md:93-94 routes domain terminology and ADRs, and AGENTS.md:26 surfac…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:210): Owner deferred the report's reject recommendation, to review the set later: ROUTED: AGENTS.md:93-94 routes domain terminology and ADRs, and AGENTS.md:26 surfac…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:209): Owner deferred the report's reject recommendation, to review the set later: Ours reads its test reference only when designing or changing substantive tests (SK…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:206): Same mechanism, looser and deliberate: doubles stay at boundaries and never replace the behaviour under test (SKILL.md:48-50; writing-good-tests.md:10-12).
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:205): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours refactors inside each cycle while preserving behaviour (SKILL…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:204): Ours confirms the intended failure before the fix, then implements the owning fix and reruns the check.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:203) *(superseded)*: Ours runs the loop per selected behaviour (SKILL.md:28) but never forbids writing tests in bulk first; the difference is not stated as deliberate, so one claus…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:202): Ours derives expected values from the spec, a worked example or a trusted fixture, never from the implementation.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:201) *(superseded)*: Ours picks seams (SKILL.md:20-24) but never records what each one catches and misses; one line per seam makes the coverage gap visible to a reviewer at little …
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:200): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours deliberately takes seams from the plan without separate appro…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:199): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours lets internal algorithm tests earn their place, the same stan…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:198): Ours avoids tests that mirror implementation and keeps internal tests only where they prove behaviour.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:197): Ours asserts meaningful results, state or boundary interactions and treats internal call choreography as not the contract.
- `2026-08-12` **adopt-merged** (2026-10-14-migration:112): Adopted-merged into the rewritten TDD skill (comparison: execution-disciplines/): writing-good-tests content — name-the-break gate, mirror-assertion/change-det…
- `2026-08-12` **adopt** (2026-10-14-migration:102): Adopted-merged (comparison: execution-disciplines/): seams as pre-agreed public test boundaries — adapted from a live human gate to the plan's new 'Test seams:…
- `2026-08-12` **adopt** (2026-10-14-migration:100): Superseding correction of the 2026-07-15 entry, whose 'covered by the local loop' claim was wrong about everything except the loop (comparison: execution-disci…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:050) *(superseded)*: The only discipline gate whose violation is recoverable only by deleting the code, with a mandatory watched-RED step. Chosen as merge base for enforcement stre…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `behaviour-test-names`:
  - `mattpocock_skills:skill:skills/engineering/tdd#behaviour-test-names` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `independent-expectation`:
  - `cursor_plugins:skill:pstack/skills/principle-test-behavior-not-implementation#independent-expectation` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `mattpocock_skills:skill:skills/engineering/tdd#independent-expectation` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `meaningful-behaviour-assertion`:
  - `cursor_plugins:skill:pstack/skills/principle-test-behavior-not-implementation#meaningful-behaviour-assertion` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `mattpocock_skills:skill:skills/engineering/tdd#meaningful-behaviour-assertion` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `mock-boundaries`:
  - `mattpocock_skills:skill:skills/engineering/tdd#system-boundary-mocks-only` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `no-implementation-coupling`:
  - `mattpocock_skills:skill:skills/engineering/tdd#no-implementation-coupling` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `one-test-per-cycle`:
  - `mattpocock_skills:skill:skills/engineering/tdd#one-test-per-cycle` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `per-seam-note`:
  - `mattpocock_skills:skill:skills/engineering/tdd#per-seam-note` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `prove-the-red`:
  - `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#prove-the-red` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `red-green`:
  - `mattpocock_skills:skill:skills/engineering/implement-spec#red-green` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/engineering/tdd#red-green` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `seam-selection`:
  - `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#seam-selection` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
- `mattpocock_skills:skill:skills/engineering/tdd#domain-vocabulary` (defer): Owner deferred the report's reject recommendation, to review the set later: ROUTED: AGENTS.md:93-94 routes domain terminology and ADRs, and AGENTS.md:26 surfac…
- `mattpocock_skills:skill:skills/engineering/tdd#one-assertion-per-test` (defer): Owner deferred the report's reject recommendation, to review the set later: A fixed one-assertion rule constrains a context-dependent choice (S-08) and conflic…
- `mattpocock_skills:skill:skills/engineering/tdd#public-only-seams` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours lets internal algorithm tests earn their place, the same stan…
- `mattpocock_skills:skill:skills/engineering/tdd#refactor-outside-loop` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours refactors inside each cycle while preserving behaviour (SKILL…
- `mattpocock_skills:skill:skills/engineering/tdd#respect-area-adrs` (defer): Owner deferred the report's reject recommendation, to review the set later: ROUTED: AGENTS.md:93-94 routes domain terminology and ADRs, and AGENTS.md:26 surfac…
- `mattpocock_skills:skill:skills/engineering/tdd#rules-during-cycle` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours reads its test reference only when designing or changing substantive tests (SK…
- `mattpocock_skills:skill:skills/engineering/tdd#seam-preconfirmation` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours deliberately takes seams from the plan without separate appro…
- `mattpocock_skills:skill:skills/engineering/tdd#test-database-over-mock` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours already decides real-versus-double by cost and contract for every boundary (wr…
<!-- /registry:generated declined -->
