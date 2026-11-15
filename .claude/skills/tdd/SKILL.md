---
name: tdd
description: Use for risky behavior changes, regression proof, legacy characterization, or substantive test design. Trivial test renames do not require a test-first workflow.
---

# Test-Driven Development

## Choose the mode first

| Task | Mode |
|---|---|
| New risky behavior or bug fix needing proof | Test-first |
| Preserve poorly understood existing behavior during an edit | Characterization |
| Add, rename or improve tests without changing behavior | Test quality only |

Use existing test tooling and applicable commands in project verification docs.
Read `references/writing-good-tests.md` when designing or changing substantive
tests. A trivial rename needs a focused check, not a test-first ceremony.

Choose the smallest boundary that exercises the real failure or contract. Prefer
the closest kind of test already used for that codepath. Public behavior is
usually stable; internal algorithm tests are appropriate when they
prove meaningful behavior without mirroring implementation. Use the plan's test
seams as guidance; routine seam selection needs no separate approval. Surface a
missing seam only when it materially changes scope or the evidence obtainable.
For each chosen seam, note in one line which failures it would and would not catch.

## Test-first

1. Select one behavior; write no test for a later behavior until this one passes.
   Derive expected results from the spec, a worked example or another independent
   source.
2. Run its test before the fix and confirm the intended failure, not an import or
   setup error. A passing test does not demonstrate the reported regression.
   A red forced by changing code or a fixture proves nothing yet: first diff
   against an untouched copy to confirm the change is really there.
3. Implement the owning fix, rerun the proving check and relevant affected tests.
4. Refactor while preserving the behavior and repeat checks affected by edits.

If code already changed, prove the regression against an isolated earlier version
when feasible; do not destroy existing edits to recreate RED. Keep a regression
test on the bug, with no broad fixture changes or unrelated coverage. If a bug
exposes a wider class of failures, finish its focused regression first; how far
the rest goes is for the task or its playbook to say.

When a failing test is impractical, run the closest executable check instead, such
as a script, a reproduction command, a snapshot diff or a log assertion, and report
it as a substitute, not as equal proof. An optional regression test for a bug may
be skipped when it would cost more than the risk warrants: broad harness setup,
brittle mocks, slow infrastructure, production-only state or unrelated fixture
changes. Required acceptance proof and project gates stand, new test
infrastructure is fine where that proof needs it, and proof that cannot be
obtained is reported as blocked. If before-fix failure could not be demonstrated,
say why, name the substitute check and what it establishes, and state the proof
still missing.

## Characterization

Capture current behavior and run a passing baseline before editing. When useful,
make a safe isolated perturbation to establish sensitivity. Record intentional
behavior changes in expectations; accidental differences remain regressions.
A passing characterization baseline is not RED.

## Test quality and completion

Prefer independent expectations, deterministic inputs and isolated state. For a
flaky bug, make the test as deterministic as you can and say which signal it pins.
Fakes and partial mocks are valid at appropriate boundaries if they do not
replace the behavior under test. Avoid tests whose expectations repeat the implementation.

Run checks required by the task and repository plus coverage justified by affected
behavior. A full suite or mutation trial is not mandatory for every edit; required
project gates still apply. Explain skipped, unavailable or pre-existing failing
checks. Report the check that failed before the fix with its failure, and the
passing run after it. Keep enough evidence to distinguish a demonstrated fix
from an inference.
