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

## Capability

Use for a critic review of any artifact, a substantive review of code or of a spec or plan, or to verify and act on review findings. Skip routine final diff inspection; to interrogate the author instead, use grilling.

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
