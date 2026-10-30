---
skill: grilling
domain: core
stage: Intake
substage: Clarification
secondary: []
family: grilling
aliases: [grill-me, grill-with-docs]
status: active
---
# grilling

Use when the user explicitly requests a grilling interview to resolve or challenge material decisions. For a written critique, review the artifact directly.

**Boundary:** Interrogates the owner's plan question by question, only on explicit request; open option exploration is brainstorming, and a written critique of an artifact is review.

<!-- registry:generated traits -->
- `map-decisions`: Map the material decisions and their prerequisites before questioning.
- `question-batching`: Batch independent questions whose prerequisites are settled and defer each dependent question until its prerequisites are answered.
- `recommended-answer`: Attach a recommended answer to each question, letting the respondent disagree. (Labels the recommendation's assumptions.)
- `self-serve-facts`: Look up available facts yourself rather than asking, leaving only the decisions to the live participant. (Ordinary lookups stay inline; only bounded work is delegated.)
- `settled-stop`: Recompute the unresolved choices after each answer and stop once the needed ones are settled, deferred or blocked, without exhausting every branch.
- `absent-respondent`: When the needed respondent is absent, prepare a questionnaire for them instead of interviewing the present user about the subject.
- `grill-the-send`: Ask the present user only about the send (who it goes to and what they need back), never about the subject the recipient knows.
- `gap-targeted-questions`: Aim a questionnaire's questions at the gap between what the recipient knows and what the sender needs.
- `interview-not-authority`: Treat conducting an interview or drafting a questionnaire as neither implementation authority nor permission to send it.
- `optional-docs`: When requested, record settled domain terms and qualifying architectural decisions through domain-modeling, not as an automatic by-product of the interview.
- `decision-summary`: Produce the durable decision log in a fixed template — context, a decision table with rationale and implications, open items, a dependency map and a risk register.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/productivity/grilling** `reference_harnesses/mattpocock_skills/skills/productivity/grilling/SKILL.md` @ 84fdeff
  - merged from: grill-me
  - merged from: grill-with-docs
  - modified: absorb grill-me as a stateless invocation alias
  - modified: absorb grill-with-docs as a documenting mode that calls domain-modeling when durable vocabulary or ADRs are needed
- **mattpocock_skills:skill:skills/productivity/grilling** `skills/productivity/grilling/SKILL.md`
  - merged from: grill-me
  - merged from: grill-with-docs
  - modified: absorb grill-me as a stateless invocation alias
  - modified: absorb grill-with-docs as a documenting mode that calls domain-modeling when durable vocabulary or ADRs are needed
- **mattpocock_skills:skill:skills/productivity/to-questionnaire** `skills/productivity/to-questionnaire/SKILL.md` @ 84fdeff
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-14` **adopt** (2026-10-14-migration:149): Adopted-in-part: absent-respondent questionnaire mode into grilling (two-exchange interview: who is it for / what must come back; grill the send, not the subje…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:090): Copied verbatim. Frontier rounds and non-blocking sub-agent fact-finding are genuinely absent from our grill-me, which paces at 1-3 questions and answers facts…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:023) *(superseded)*: The only adversarial design-tree exhaustion: it walks the unblocked frontier of a FORMED plan breadth-first and forbids action until every branch is visited. D…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [skill-comparisons/interaction-utilities](../../../archive/skill-comparisons/interaction-utilities/)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
