---
skill: review
domain: core
stage: Verification
substage: Review
secondary: [Specification, Decomposition]
family: code-review
aliases: [document-review, receiving-code-review]
status: active
---
# review

Use for a critic review of any artifact, a substantive review of code or of a spec or plan, or to verify and act on review findings. Skip routine final diff inspection; to interrogate the author instead, use grilling.

<!-- registry:generated traits -->
- `independent-critic-verdict`: A reviewer who did not author the work gives evidence-backed findings and a verdict, approving only what was verified and listing the rest as unverified.
- `severity-and-verdict`: Rate each finding by consequence and approve only with no open blocker or major, otherwise require revision, never counting preference alone as a finding. (A plan-mandated defect is still reported as major, labelled plan-mandated, for the user to decide.)
- `scope-establishment`: Fix the diff and the base it is measured from before reviewing.
- `pre-existing-edit-separation`: Separate pre-existing edits from the task's own changes using the task baseline, not filenames.
- `callers-and-evidence`: Read enough surrounding code and affected callers, treating implementer and reviewer reports as evidence to verify rather than authority.
- `mechanical-gate-precedence`: A failing mechanical verification gate returns the work unreviewed as failed verification unless the requester explicitly waives it.
- `requirements-before-quality`: Check missing, extra and misunderstood requirements before judging code quality.
- `distinct-axis-verdicts`: Report each review axis's verdict separately so one axis passing never masks another failing.
- `test-quality-judgment`: Judge tests by whether they detect meaningful failures with independent expectations, and do not treat test changes as inherently defects.
- `actionable-defects-only`: Report only actionable defects with trigger, consequence and evidence, defer formatting to configured tools, and state plainly when none are found rather than inventing findings.
- `read-only-isolation`: A read-only review preserves the checkout, index and refs, using permitted isolated facilities for any check that needs mutation.
- `verdict-contract`: Dispatched reviewers and re-reviews emit a fixed verdict output of verdict, unverified requirements, located issues and actual checks with limitations.
- `re-review-finding-tracking`: A re-review rules each prior finding addressed or not with located evidence, flags new breakage in the fix delta, and may rule a finding incorrect without demanding cosmetic edits.
- `document-review`: Check a spec or plan against repository context for internal inconsistency, missing constraints, unverifiable claims and scope bloat, editing only unambiguous wording when fixes were requested.
- `finding-adjudication`: Verify each incoming review finding against requirements, code and primary evidence before acting, and give each a visible disposition: fix a confirmed in-scope defect, answer an incorrect one with a retained ruling, record an out-of-scope follow-up.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **agent-skills:skill:skills/code-review-and-quality** `reference_harnesses/agent-skills/skills/code-review-and-quality/SKILL.md` @ 7676817
  - merged from: code-review (mattpocock)
  - merged from: requesting-code-review
  - modified: absorb mattpocock's never-rerank-across-axes rule as a reporting guarantee, and its code-smell baseline
  - modified: absorb requesting-code-review's dispatch flow and reviewer template asset
  - modified: relax mattpocock's two-parallel-subagents spine to a recommendation for large diffs; the anti-masking property it protects is preserved as a reporting rule
  - dropped: mattpocock's issue-tracker spec fetch — generalized to 'the plan, spec or issue, however this repo stores it'
- **agent-skills:skill:skills/code-review-and-quality** `skills/code-review-and-quality/SKILL.md` @ 7676817c12a1317454ae3898a0c5c1eacf5dd3d5
  - merged from: code-review (mattpocock)
  - merged from: requesting-code-review
  - modified: absorb mattpocock's never-rerank-across-axes rule as a reporting guarantee, and its code-smell baseline
  - modified: absorb requesting-code-review's dispatch flow and reviewer template asset
  - modified: relax mattpocock's two-parallel-subagents spine to a recommendation for large diffs; the anti-masking property it protects is preserved as a reporting rule
  - dropped: mattpocock's issue-tracker spec fetch — generalized to 'the plan, spec or issue, however this repo stores it'
- **mattpocock_skills:skill:skills/engineering/code-review** `skills/engineering/code-review/SKILL.md` @ 84fdeffd12f2ee307994d1eb6feb48173b6e0502
- **superpowers:skill:skills/receiving-code-review** `skills/receiving-code-review/SKILL.md` @ 44c9b2d6e889982ac18c27d05a19fefe335194e1
- **superpowers:skill:skills/requesting-code-review** `skills/requesting-code-review/SKILL.md` @ 44c9b2d6e889982ac18c27d05a19fefe335194e1
- **superpowers:skill:skills/using-git-worktrees** `skills/using-git-worktrees/SKILL.md` @ 44c9b2d
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-14` **adopt** (2026-10-14-migration:158): Adopted-in-part into code-review's read-only clause: harness-native isolation first (Agent isolation: worktree / EnterWorktree, never raw git worktree add — ph…
- `2026-08-14` **adopt** (2026-10-14-migration:156): Adopted 2026-08-14 in part into code-review (evidence: skill-comparisons/review-protocols/ round 2): the git-worktree escape hatch on the read-only rule (prohi…
- `2026-08-14` **adopt** (2026-10-14-migration:155): New standalone skill 2026-08-14 for feedback arriving outside the engine's fix loop (evidence: skill-comparisons/review-protocols/): reception order, performat…
- `2026-08-14` **adopt** (2026-10-14-migration:135): Absorbed fail-fast preflight, spec-source discovery ladder, and tooling-dedupe into the code-review skill (evidence: skill-comparisons/review-protocols/). Fowl…
- `2026-08-14` **adopt-merged** (2026-10-14-migration:124): Re-merged 2026-08-14 into the code-review skill (evidence: skill-comparisons/review-protocols/): approval philosophy, within-bucket structural lead, review-tes…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:056) *(superseded)*: The review rubric and the dispatch mechanism belong in one place. Chosen as base for its multi-axis rubric.
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [skill-comparisons/git-agent-workflow](../../../archive/skill-comparisons/git-agent-workflow/)
- [skill-comparisons/review-protocols](../../../archive/skill-comparisons/review-protocols/)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
