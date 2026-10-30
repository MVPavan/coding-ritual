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
- **superpowers:skill:skills/receiving-code-review** `skills/receiving-code-review/SKILL.md` @ 44c9b2d6e889982ac18c27d05a19fefe335194e1
- **superpowers:skill:skills/requesting-code-review** `skills/requesting-code-review/SKILL.md` @ 44c9b2d6e889982ac18c27d05a19fefe335194e1
- **superpowers:skill:skills/using-git-worktrees** `skills/using-git-worktrees/SKILL.md` @ 44c9b2d
- **mattpocock_skills:skill:skills/engineering/code-review#two-axis-review** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.8)
- **mattpocock_skills:skill:skills/engineering/code-review#distinct-axis-verdicts** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/code-review#scope-establishment** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/code-review#fixed-point-preflight** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.8)
- **mattpocock_skills:skill:skills/engineering/code-review#spec-source-discovery** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.8)
- **mattpocock_skills:skill:skills/engineering/code-review#standards-source-discovery** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.8)
- **mattpocock_skills:skill:skills/engineering/code-review#missing-spec-axis-skip** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.8)
- **mattpocock_skills:skill:skills/engineering/code-review#skip-tool-enforced** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/code-review#cited-standard-findings** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.8)
- **mattpocock_skills:skill:skills/engineering/code-review#spec-conformance-findings** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.8)
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:571): Checkpoint at 5beb35b for the owner's trait rulings: 10 adopt, 9 defer.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:264): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours reports actionable defects only and states plainly when none …
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:263): Owner deferred the report's reject recommendation, to review the set later: Depends on the smell catalogue, which this report recommends rejecting; documented …
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:262): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours reports only actionable defects and never counts preference a…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:261): Owner deferred the report's reject recommendation, to review the set later: Ours ends each role with its own verdict (review-contract.md:16, 28) and all findin…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:260): Owner deferred the report's reject recommendation, to review the set later: A fixed word cap can suppress findings, against C-11 (ask for all findings, filter …
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:259): Ours already reports missing, extra and misunderstood requirements (review-contract.md:18); quoting the requirement line makes each finding checkable without t…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:258): Ours cites file:line, trigger and consequence for defects (code.md:39) but has no standards axis to cite yet; this goes with two-axis-review. The smell-quoting…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:257): Owner deferred the report's reject recommendation, to review the set later: Upstream needs it only to carry the smell catalogue into the standards reviewer (up…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:256): Same mechanism, deliberate split: mechanical gates own tool-enforced rules (code.md:23-24) and formatting is left to tools (code.md:41).
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:255): Ours marks spec compliance unverified when requirements are missing (code.md:20-21) and limits compliance claims (review-contract.md:22-23), but never skips th…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:254): Owner deferred the report's reject recommendation, to review the set later: A mandatory two-subagent dispatch conflicts with proportional delegation (AGENTS.md…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:253): Ours has no step that finds the documented standards a review should apply; this supplies the source for the standards axis adopted in two-axis-review.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:252): Ours only asks the requester (code.md:20-21), which is the last rung of upstream's ladder; checking the referenced bead or spec first is cheap and keeps the ne…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:251): Owner deferred the report's reject recommendation, to review the set later: Ours deliberately measures committed work as BASE..HEAD from the task's recorded ba…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:250): Ours establishes scope (code.md:11-15) but never checks it yields a diff before dispatch, so an empty or wrong base wastes a reviewer run; one sentence fails f…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:249): Ours fixes the supplied or inferred base and diff scope before reviewing.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:248): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours collects every finding with its severity and has the coordina…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:247): Ours keeps the dispatched spec and quality verdicts distinct and has a combined reviewer cover both explicitly.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:246): Ours reviews requirements before quality (code.md:33) but never judges the diff against the repository's documented standards; adding that axis to the existing…
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
- `actionable-defects-only`:
  - `mattpocock_skills:skill:skills/engineering/code-review#skip-tool-enforced` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `distinct-axis-verdicts`:
  - `mattpocock_skills:skill:skills/engineering/code-review#distinct-axis-verdicts` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `scope-establishment`:
  - `mattpocock_skills:skill:skills/engineering/code-review#scope-establishment` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
- `mattpocock_skills:skill:skills/engineering/code-review#capped-reviewer-report` (defer): Owner deferred the report's reject recommendation, to review the set later: A fixed word cap can suppress findings, against C-11 (ask for all findings, filter …
- `mattpocock_skills:skill:skills/engineering/code-review#code-smell-catalog` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours reports only actionable defects and never counts preference a…
- `mattpocock_skills:skill:skills/engineering/code-review#no-cross-axis-rerank` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours collects every finding with its severity and has the coordina…
- `mattpocock_skills:skill:skills/engineering/code-review#parallel-subagents` (defer): Owner deferred the report's reject recommendation, to review the set later: A mandatory two-subagent dispatch conflicts with proportional delegation (AGENTS.md…
- `mattpocock_skills:skill:skills/engineering/code-review#per-axis-summary-line` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours ends each role with its own verdict (review-contract.md:16, 28) and all findin…
- `mattpocock_skills:skill:skills/engineering/code-review#repo-standards-over-smells` (defer): Owner deferred the report's reject recommendation, to review the set later: Depends on the smell catalogue, which this report recommends rejecting; documented …
- `mattpocock_skills:skill:skills/engineering/code-review#self-contained-subagent-brief` (defer): Owner deferred the report's reject recommendation, to review the set later: Upstream needs it only to carry the smell catalogue into the standards reviewer (up…
- `mattpocock_skills:skill:skills/engineering/code-review#smells-as-heuristics` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours reports actionable defects only and states plainly when none …
- `mattpocock_skills:skill:skills/engineering/code-review#three-dot-merge-base` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours deliberately measures committed work as BASE..HEAD from the task's recorded ba…
<!-- /registry:generated declined -->
