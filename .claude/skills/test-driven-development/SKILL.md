---
name: test-driven-development
description: Use for risky behavior changes, bug fixes needing proof, legacy edits needing characterization, tasks marked test-first or characterization-first, or whenever tests are written or changed.
---

# Test-Driven Development

Write one test first. Watch it fail for the right reason. Write the minimum
code to pass. This skill is deliberately risk-scaled, not universal — it fires
on the triggers below, not on every code change.

## Use it when

- a bug fix needs proof
- behavior is changing in a risky area
- legacy behavior needs characterization before edits
- the plan or dispatch explicitly says `test-first` or `characterization-first`
- tests are being written or changed for any reason → the quality bar in
  `references/writing-good-tests.md` applies even outside the loop

## Discover the stack first

The cycle is universal; the commands are not. Before the first test, find how
*this* repository tests, and use its commands for every RED, GREEN, and
verification step:

- build system and test framework from the manifests (`pyproject.toml`,
  `package.json`, `Makefile`, …); prefer checked-in wrappers and the commands
  in `.claude/project/verification.md` over globally installed tools
- how to run one focused test vs the full suite
- where tests live, how files are named, what neighbouring tests do
- what CI actually runs — those commands gate merges

Never assume a default like `npm test` or bare `pytest` without checking.
If the repo has no test infrastructure at all, say so and agree the approach
with the user before inventing one.

## Where tests attach — seams

A seam is the public boundary you test at. Tests live at seams, never against
internals. Before writing tests, write down the seams under test:

- With a plan: use the task's **Test seams** field — the public observable
  boundaries the plan names for this task (the Interfaces block lists exact
  names passed between tasks, which may include internals — it is not the
  seam list). A test-first task with no Test seams field, or a needed seam
  the plan never named, is a plan gap to raise.
- Without a plan, attended: name the seams in one line and confirm with the
  user before the first test.
- Without a plan, unattended: derive seams from the public interface of the
  changed module and record them in your report.

Bounding the seams up front is what points testing effort at critical paths
instead of every edge case.

For a bug-fix reproduction test, a **correct** seam exercises the real bug
pattern as it occurred at the call site — a too-shallow seam (a single-caller
unit test when the bug needs the chain that triggered it) gives false
confidence. If no correct seam exists, that absence is itself a finding:
document and report it instead of attaching the test at a wrong seam.

## The loop — test-first path

1. Pick **one behavior**, not a whole feature slice.
2. Write a test for it at the seam, through the public interface.
3. **RED**: run the focused test; confirm it fails *for the expected reason*.
   Wrong failure (import error, typo, wrong assertion) → fix the test, back
   to RED. A test-first test that passes immediately proves nothing —
   rewrite it until it fails against current code.
4. **GREEN**: write the smallest change that makes it pass. No speculative
   structure for tests you haven't written yet.
5. Re-run the focused test, then the tests covering what you touched.
6. Refactor only while green; re-run after each refactor step.
7. Repeat, one behavior at a time. Full suite once before completion.

For bug fixes this is the **Prove-It pattern**: do not start with the fix.
Reproduce the bug as a failing test → watch it fail (bug confirmed) → fix →
watch it pass (fix proven) → full suite (no regressions). A bug fix without
a reproduction test is unproven.

## The characterization path (legacy code)

A characterization test pins current behavior before you change it — so it
**passes** against the existing code, and that passing run is the baseline,
never reported as RED. The sequence:

1. Write the test at the seam, capturing what the code does now (however
   odd); run it and record the passing baseline.
2. Where practical, prove the test can fail with a safe, reversible
   perturbation (temporarily alter a return value or input, watch it fail,
   revert). If no safe perturbation exists, say so in the report.
3. Make the intended change; the characterization tests tell you what you
   actually altered. Intended behavior changes update the test —
   deliberately and named as such — everything else stays green.

## Rules

- Do not write a whole batch of tests first — bulk tests verify *imagined*
  behavior and commit you to structure before the implementation teaches you
  anything. One test → one implementation → repeat.
- Expected values come from an independent source (hand-derived literal,
  worked example, the spec) — never recomputed the way the code computes
  them.
- Test behavior through the public interface, not implementation details.
- Do not re-run a clean suite for reassurance. Re-run after a change that
  could affect the result, not because you're nervous.
- If the test strategy is disputed, route it through an independent critique
  (spawned Opus 5 medium Claude subagent) before wider implementation.

## Red flags — stop and fix the test, not the code

- A test-first test that passed on its first run (a characterization
  baseline is supposed to pass — but then step 2 of that path applies).
- Flaky behavior: timing sleeps, order-dependence, shared state between
  tests — use deterministic time/randomness and isolated per-test state.
- A broad snapshot nobody reviews; keep snapshots narrow and review every
  change to them.
- The expected value is built by a loop, builder, or helper that shares
  logic with the code under test.
- The test breaks when you refactor but behavior hasn't changed
  (implementation-coupled).
- "All tests pass" but no test command output is in hand.
- A skipped or disabled test making the suite green.
- Reaching for a default test command without checking what the repo uses.

## Verification

**For a test-first or characterization-first run:** every behavior in scope
has a test; bug fixes have a reproduction test that failed before the fix;
the full suite passes with the repository's own command and its output is in
hand; no tests skipped or disabled; the mutation check from
`references/writing-good-tests.md` was run on new test files.

**For test work outside the loop** (this skill fired only because tests were
being written or changed): the changed tests meet the quality reference, and
the verification the task itself asked for passes. No universal
test-everything demand rides in through this skill.

| Rationalization | Reality |
| --- | --- |
| "I'll write tests after the code works" | After-the-fact tests mirror the implementation instead of specifying behavior. |
| "This is too simple to test" | If it's risky enough to trigger this skill, it's not too simple. Otherwise the skill shouldn't have fired. |
| "I tested it manually" | Manual testing doesn't persist. Tomorrow's change breaks it silently. |
| "The test passing immediately is fine, the code already existed" | Then it's a characterization test — run it against broken code once (mutate mentally at minimum) to prove it can fail. |
| "Let me run the suite again to be sure" | Re-running unchanged code adds no information — only tokens. |
