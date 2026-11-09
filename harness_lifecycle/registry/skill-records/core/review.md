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

Use for a critic review of any artifact, a substantive review of code or of a spec or plan, or to verify and act on review findings. Skip routine final diff inspection; to question the author instead, use grilling.

**Boundary:** An ordinary or critical look, judged by reading, reporting every finding; to break a change and keep only run-proven findings is interrogate.

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
- `fixed-point-preflight`: Confirm the review ref resolves and the diff is non-empty before fanning out, failing fast rather than inside sub-agents.
- `spec-source-discovery`: Find the originating spec in a fixed order — commit issue references, a user-supplied path, conventional spec directories — and ask only as a last resort.
- `missing-spec-axis-skip`: When the user confirms no spec exists, skip the spec review axis and report that no spec was available.
- `two-axis-review`: Review a diff along two separate axes — conformance to the repo's documented standards and faithfulness to the originating spec.
- `standards-source-discovery`: Search the repo for every file documenting how code should be written, always including the conventional standards and contributing files.
- `cited-standard-findings`: Cite the standard's file and rule for every violation and quote the hunk for every smell.
- `spec-conformance-findings`: Report spec findings as missing or partial requirements, unrequested behaviour and wrongly implemented requirements, quoting the spec line for each.
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
- **mattpocock_skills:skill:skills/engineering/code-review#distinct-axis-verdicts** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/code-review#scope-establishment** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/code-review#skip-tool-enforced** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/code-review#two-axis-review** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/code-review#fixed-point-preflight** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/code-review#spec-source-discovery** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/code-review#standards-source-discovery** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/code-review#missing-spec-axis-skip** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/code-review#cited-standard-findings** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/code-review#spec-conformance-findings** `skills/engineering/code-review/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **cursor_plugins:skill:pstack/skills/blast-radius#breakage-beyond-callers** `pstack/skills/blast-radius/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/blast-radius#safety-fact-proved-by-run** `pstack/skills/blast-radius/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/blast-radius#evidence-ladder** `pstack/skills/blast-radius/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/blast-radius#ladder-as-far-as-cheap** `pstack/skills/blast-radius/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/blast-radius#small-real-library-script** `pstack/skills/blast-radius/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/blast-radius#failing-loud-proof** `pstack/skills/blast-radius/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/blast-radius#whole-change-including-unstated** `pstack/skills/blast-radius/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/blast-radius#change-history-pull** `pstack/skills/blast-radius/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/blast-radius#single-safety-fact-search** `pstack/skills/blast-radius/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/blast-radius#dependency-source-and-pin** `pstack/skills/blast-radius/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/blast-radius#timing-and-lifecycle-analysis** `pstack/skills/blast-radius/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/blast-radius#non-symbol-coupling-trace** `pstack/skills/blast-radius/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/blast-radius#likelihood-and-cost-per-risk** `pstack/skills/blast-radius/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/blast-radius#confirmed-and-cleared-split** `pstack/skills/blast-radius/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/blast-radius#empty-search-is-finding** `pstack/skills/blast-radius/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/blast-radius#handback-what-it-does** `pstack/skills/blast-radius/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/blast-radius#handback-safety-fact-with-grade** `pstack/skills/blast-radius/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/blast-radius#handback-risk-fields** `pstack/skills/blast-radius/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/blast-radius#handback-pre-merge-check** `pstack/skills/blast-radius/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-09` **adopt-merged** (2026-11-09-pocock-4ae2317:157): Checkpoint at 4ae2317 for the owner's trait rulings: 1 adopt.
- `2026-11-06` **adopt-merged** (2026-11-06-batch-p1:285): Checkpoint at 4dd1d05 for the owner's trait rulings: 21 adopt, 1 reject.
- `2026-11-06` **adopt** (2026-11-06-batch-p1:283): Owner ruling 2026-11-06: Prevents: A list of risks with nothing the author can run before landing. Lands in review, references/blast-radius.md, through its con…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:282): Owner ruling 2026-11-06: Prevents: A risk nobody can act on, with no location and no way to check it. Lands in review, references/blast-radius.md, through its …
- `2026-11-06` **adopt** (2026-11-06-batch-p1:281): Owner ruling 2026-11-06: Prevents: A claim of safety handed back with nothing to show how far it was checked. Lands in review, references/blast-radius.md, thro…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:280): Owner ruling 2026-11-06: Prevents: A safety claim the reader cannot place, because the change itself was never described. Lands in review, references/blast-rad…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:277): Owner ruling 2026-11-06: Prevents: A real answer lost because the search behind it found nothing. Lands in review, references/blast-radius.md, through its cond…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:276): Owner ruling 2026-11-06: Prevents: Checked-and-fine items mixed with live risks, or dropped so nobody knows they were checked. Lands in review, references/blas…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:275): Owner ruling 2026-11-06: Prevents: Every risk reading as equally alarming, so the reader cannot tell what to act on. Lands in review, references/blast-radius.m…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:274): Owner ruling 2026-11-06: Prevents: Breakage across a boundary no symbol search crosses, such as a stored field or a wire format. Lands in review, references/bl…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:273): Owner ruling 2026-11-06: Prevents: A change that is correct line by line and breaks because of when it runs. Lands in review, references/blast-radius.md, throu…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:272): Owner ruling 2026-11-06: Prevents: A claim about a library drawn from memory of a version the project does not pin. Lands in review, references/blast-radius.md…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:271): Owner ruling 2026-11-06: Prevents: A long list of maybes that takes the reviewer's time and settles nothing. Lands in review, references/blast-radius.md, throu…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:270): Owner ruling 2026-11-06: Prevents: A change judged with no idea what it was meant to do, so a gap between intent and behaviour goes unseen. Lands in review, re…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:269): Owner ruling 2026-11-06: Prevents: Reading only the changed lines and missing what the change now does differently. Lands in review, references/blast-radius.md…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:268): Owner ruling 2026-11-06: Prevents: A script that prints something and is read as proof whichever way it came out. Lands in review, references/blast-radius.md, …
- `2026-11-06` **adopt** (2026-11-06-batch-p1:267): Owner ruling 2026-11-06: Prevents: A proof run against a mock or a different version, which proves nothing about what ships. Lands in review, references/blast-…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:266): Owner ruling 2026-11-06: Prevents: Either stopping at a citation when a short script would prove it, or an expensive proof nobody needed. Lands in review, refe…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:265): Owner ruling 2026-11-06: Prevents: Every safety claim sounding equally certain, so the reader cannot tell a guess from a proof. Lands in review, references/bla…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:264): Owner ruling 2026-11-06: Prevents: A plausible safety claim accepted because it reads well, whether or not it is true. Lands in review, references/blast-radius…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:263): Owner ruling 2026-11-06: Prevents: A blast-radius answer that lists the callers a search would show and misses what actually breaks. Lands in review, reference…
- `2026-11-03` **update** (2026-11-03-batch-3:116): The seven Pocock rows land in the code reference and the verdict contract. One clause in the description changes, 'to interrogate the author' to 'to question t…
- `2026-11-03` **adopt** (2026-11-03-batch-3:115): Completes pending 2026-10-30-mattpocock_skills-5beb35b:259: spec-conformance-findings is written at .claude/skills/review/references/review-contract.md:18, rea…
- `2026-11-03` **adopt** (2026-11-03-batch-3:114): Completes pending 2026-10-30-mattpocock_skills-5beb35b:258: cited-standard-findings is written at .claude/skills/review/references/code.md:51-52, read against …
- `2026-11-03` **adopt** (2026-11-03-batch-3:113): Completes pending 2026-10-30-mattpocock_skills-5beb35b:255: missing-spec-axis-skip is written at .claude/skills/review/references/code.md:26-27, read against i…
- `2026-11-03` **adopt** (2026-11-03-batch-3:112): Completes pending 2026-10-30-mattpocock_skills-5beb35b:253: standards-source-discovery is written at .claude/skills/review/references/code.md:41-43, read again…
- `2026-11-03` **adopt** (2026-11-03-batch-3:111): Completes pending 2026-10-30-mattpocock_skills-5beb35b:252: spec-source-discovery is written at .claude/skills/review/references/code.md:23-26, read against it…
- `2026-11-03` **adopt** (2026-11-03-batch-3:110): Completes pending 2026-10-30-mattpocock_skills-5beb35b:250: fixed-point-preflight is written at .claude/skills/review/references/code.md:15-19, read against it…
- `2026-11-03` **adopt** (2026-11-03-batch-3:109): Completes pending 2026-10-30-mattpocock_skills-5beb35b:246: two-axis-review is written at .claude/skills/review/references/code.md:39-40, read against its defi…
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:571) *(superseded)*: Checkpoint at 5beb35b for the owner's trait rulings: 10 adopt, 9 defer.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:264): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours reports actionable defects only and states plainly when none …
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:263): Owner deferred the report's reject recommendation, to review the set later: Depends on the smell catalogue, which this report recommends rejecting; documented …
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:262): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours reports only actionable defects and never counts preference a…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:261): Owner deferred the report's reject recommendation, to review the set later: Ours ends each role with its own verdict (review-contract.md:16, 28) and all findin…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:260): Owner deferred the report's reject recommendation, to review the set later: A fixed word cap can suppress findings, against C-11 (ask for all findings, filter …
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:259) *(superseded)*: Ours already reports missing, extra and misunderstood requirements (review-contract.md:18); quoting the requirement line makes each finding checkable without t…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:258) *(superseded)*: Ours cites file:line, trigger and consequence for defects (code.md:39) but has no standards axis to cite yet; this goes with two-axis-review. The smell-quoting…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:257): Owner deferred the report's reject recommendation, to review the set later: Upstream needs it only to carry the smell catalogue into the standards reviewer (up…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:256): Same mechanism, deliberate split: mechanical gates own tool-enforced rules (code.md:23-24) and formatting is left to tools (code.md:41).
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:255) *(superseded)*: Ours marks spec compliance unverified when requirements are missing (code.md:20-21) and limits compliance claims (review-contract.md:22-23), but never skips th…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:254): Owner deferred the report's reject recommendation, to review the set later: A mandatory two-subagent dispatch conflicts with proportional delegation (AGENTS.md…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:253) *(superseded)*: Ours has no step that finds the documented standards a review should apply; this supplies the source for the standards axis adopted in two-axis-review.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:252) *(superseded)*: Ours only asks the requester (code.md:20-21), which is the last rung of upstream's ladder; checking the referenced bead or spec first is cheap and keeps the ne…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:251): Owner deferred the report's reject recommendation, to review the set later: Ours deliberately measures committed work as BASE..HEAD from the task's recorded ba…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:250) *(superseded)*: Ours establishes scope (code.md:11-15) but never checks it yields a diff before dispatch, so an empty or wrong base wastes a reviewer run; one sentence fails f…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:249): Ours fixes the supplied or inferred base and diff scope before reviewing.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:248): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours collects every finding with its severity and has the coordina…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:247): Ours keeps the dispatched spec and quality verdicts distinct and has a combined reviewer cover both explicitly.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:246) *(superseded)*: Ours reviews requirements before quality (code.md:33) but never judges the diff against the repository's documented standards; adding that axis to the existing…
- `2026-08-14` **adopt** (2026-10-14-migration:158): Adopted-in-part into code-review's read-only clause: harness-native isolation first (Agent isolation: worktree / EnterWorktree, never raw git worktree add — ph…
- `2026-08-14` **adopt** (2026-10-14-migration:156): Adopted 2026-08-14 in part into code-review (evidence: skill-comparisons/review-protocols/ round 2): the git-worktree escape hatch on the read-only rule (prohi…
- `2026-08-14` **adopt** (2026-10-14-migration:155): New standalone skill 2026-08-14 for feedback arriving outside the engine's fix loop (evidence: skill-comparisons/review-protocols/): reception order, performat…
- `2026-08-14` **adopt** (2026-10-14-migration:135): Absorbed fail-fast preflight, spec-source discovery ladder, and tooling-dedupe into the code-review skill (evidence: skill-comparisons/review-protocols/). Fowl…
- `2026-08-14` **adopt-merged** (2026-10-14-migration:124): Re-merged 2026-08-14 into the code-review skill (evidence: skill-comparisons/review-protocols/): approval philosophy, within-bucket structural lead, review-tes…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:056) *(superseded)*: The review rubric and the dispatch mechanism belong in one place. Chosen as base for its multi-axis rubric.
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-06-upstream-mattpocock_skills-4ae2317.md](../../reviews/2026-11-06-upstream-mattpocock_skills-4ae2317.md)
- [2026-11-04-upstream-cursor_plugins-4dd1d05-batch-p1.md](../../reviews/2026-11-04-upstream-cursor_plugins-4dd1d05-batch-p1.md)
- [skill-comparisons/git-agent-workflow](../../../archive/skill-comparisons/git-agent-workflow/)
- [skill-comparisons/review-protocols](../../../archive/skill-comparisons/review-protocols/)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `actionable-defects-only`:
  - `mattpocock_skills:skill:skills/engineering/code-review#skip-tool-enforced` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `cited-standard-findings`:
  - `mattpocock_skills:skill:skills/engineering/code-review#cited-standard-findings` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `distinct-axis-verdicts`:
  - `mattpocock_skills:skill:skills/engineering/code-review#distinct-axis-verdicts` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `fixed-point-preflight`:
  - `mattpocock_skills:skill:skills/engineering/code-review#fixed-point-preflight` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `missing-spec-axis-skip`:
  - `mattpocock_skills:skill:skills/engineering/code-review#missing-spec-axis-skip` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `scope-establishment`:
  - `mattpocock_skills:skill:skills/engineering/code-review#scope-establishment` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `spec-conformance-findings`:
  - `mattpocock_skills:skill:skills/engineering/code-review#spec-conformance-findings` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `spec-source-discovery`:
  - `mattpocock_skills:skill:skills/engineering/code-review#spec-source-discovery` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `standards-source-discovery`:
  - `mattpocock_skills:skill:skills/engineering/code-review#standards-source-discovery` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `two-axis-review`:
  - `mattpocock_skills:skill:skills/engineering/code-review#two-axis-review` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
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
