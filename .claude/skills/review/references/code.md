# Code review

Review implemented changes against requirements and consequential risks.
Modes: `inline` or combined (requirements and quality on the supplied scope),
`spec` / `quality` (a dispatched role with its verdict contract), and `re-review`
(prior findings and new breakage in the fix delta). Dispatched reviewers and
structured re-reviews also use `review-contract.md`.

## Establish scope and evidence

Use the supplied diff/package and requirements. Infer an obvious supplied base
or working-tree scope; ask only when the choice changes what should be reviewed.
For uncommitted work, use `git diff <base> -- <owned paths>` and inspect in-scope
untracked files separately. `BASE..HEAD` covers committed work only. Distinguish
pre-existing edits using the task baseline; filenames alone do not establish ownership.

Read enough surrounding code and affected callers to evaluate concrete risks.
Treat implementer reports and reviewer claims as evidence to verify, not authority.
A package saves repeated reads but does not forbid necessary source inspection.
If requirements are missing, ask whoever requested the review; without an answer,
state that spec compliance is unverified. Never derive requirements from the diff.

A failing mechanical gate from `.repo-context/verification.md` returns the work
unreviewed as failed verification, unless the requester explicitly waives it.
Record other failing or unavailable checks with their scope and impact. Reuse
applicable check evidence; run focused additional checks when a consequential
doubt remains.
Read-only review must preserve checkout, index and refs; use permitted isolated
facilities for checks that need mutations.

## Review

Check missing, extra and misunderstood requirements before quality. Examine
correctness, error handling, compatibility, data migration, ownership and relevant
invariants. Judge tests by whether they detect meaningful failures with independent
expectations; changes to tests are not inherently defects. Apply the security
skill's relevant boundary controls for material security changes.

Report actionable defects introduced or exposed by the change, with file/line,
trigger, consequence and evidence. Separate pre-existing issues and uncertainty.
Leave formatting to configured tools; do not treat harmless warnings as defects.

End with findings, actual checks, limits and a justified verdict. Explicitly say
when no defects were found; do not invent praise or findings to fill a template.
