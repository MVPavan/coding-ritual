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
- `answer-before-next-round`: Wait for the respondent's answers to a round before asking the next one.
- `yes-accepts-recommendation`: Word each question so that a yes accepts your recommended answer. (Delivers sealed row 2026-10-30-mattpocock_skills-5beb35b:076 whole, for a question offering a recommendation; a question after a fact stays an ordinary question; T5.)
- `importance-ordered-questions`: Order a questionnaire's questions most important first.
- `needed-item-coverage`: Finish a questionnaire only when every needed decision or fact is covered by at least one question.
- `single-idea-questions`: Make each question a single idea, never a compound one.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/productivity/grilling#map-decisions** `skills/productivity/grilling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/grilling#question-batching** `skills/productivity/grilling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/grilling#recommended-answer** `skills/productivity/grilling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/grilling#self-serve-facts** `skills/productivity/grilling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/grill-with-docs#document-during-interview** `skills/engineering/grill-with-docs/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/to-questionnaire#grill-the-send** `skills/productivity/to-questionnaire/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/to-questionnaire#gap-targeted-questions** `skills/productivity/to-questionnaire/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/to-questionnaire#absent-respondent** `skills/productivity/to-questionnaire/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/in-progress/loop-me#recommended-answer** `skills/in-progress/loop-me/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/in-progress/loop-me#answer-before-next-round** `skills/in-progress/loop-me/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/grilling#answer-before-next-round** `skills/productivity/grilling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/grilling#yes-accepts-recommendation** `skills/productivity/grilling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/to-questionnaire#importance-ordered-questions** `skills/productivity/to-questionnaire/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/to-questionnaire#needed-item-coverage** `skills/productivity/to-questionnaire/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/to-questionnaire#single-idea-questions** `skills/productivity/to-questionnaire/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-09` **adopt-merged** (2026-11-09-pocock-4ae2317:180): Checkpoint at 4ae2317 for the owner's trait rulings: 1 adopt.
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:015): Completes pending 2026-10-30-mattpocock_skills-5beb35b:393: single-idea-questions is written at .claude/skills/grilling/SKILL.md:29-31, in the sealed rewording…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:014): Completes pending 2026-10-30-mattpocock_skills-5beb35b:387: needed-item-coverage is written at .claude/skills/grilling/SKILL.md:29-31, in the sealed rewording'…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:013): Completes pending 2026-10-30-mattpocock_skills-5beb35b:389: importance-ordered-questions is written at .claude/skills/grilling/SKILL.md:29-31, in the sealed re…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:012): Completes pending 2026-10-30-mattpocock_skills-5beb35b:076: yes-accepts-recommendation is written at .claude/skills/grilling/SKILL.md:15-16, in the sealed rewo…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:011): Completes pending 2026-10-30-mattpocock_skills-5beb35b:081: answer-before-next-round is written at .claude/skills/grilling/SKILL.md:13-14, in the sealed reword…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:010): Completes pending 2026-10-30-mattpocock_skills-5beb35b:450: answer-before-next-round is written at .claude/skills/grilling/SKILL.md:13-14, in the sealed reword…
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:581): Checkpoint at 5beb35b for the owner's trait rulings: 3 adopt, 11 defer.
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:578): Checkpoint at 5beb35b for the owner's trait rulings: 6 adopt, 6 defer.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:568): Checkpoint at 5beb35b for the owner's trait rulings: 1 adopt.
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:563) *(superseded)*: Checkpoint at 5beb35b for the owner's trait rulings: 6 adopt, 4 defer.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:452): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours documents only when requested, never as an automatic by-produ…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:451): Ours includes a recommendation and its assumptions, letting the user disagree.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:450) *(superseded)*: Ours defers dependent questions and recomputes after each answer (grilling/SKILL.md:11-13, 20), but never waits for all answers to a round before asking anothe…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:443): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours stops with decisions deferred or blocked instead of requiring…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:393) *(superseded)*: Ours says nothing about question shape; a compound question gets half an answer. Carried by the same line as needed-item-coverage.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:389) *(superseded)*: Ours does not order questions; most-important-first protects the answers that matter when the respondent stops early. Carried by the same line as needed-item-c…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:387) *(superseded)*: Ours targets the knowledge gap (SKILL.md:26) but sets no completion check; covering every needed item gives one.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:386): Ours prepares a questionnaire when the necessary respondent is absent.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:384): Ours aims the questionnaire at the respondent's role and knowledge gap.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:383): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours does not force two exchanges when the recipient context and o…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:382): Ours asks the present user only for missing recipient context and desired outcome.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:196): Ours deliberately ties document writes to an explicit request (grilling SKILL.md:31-32), with the manual alias granting it (grill-with-docs SKILL.md:9-12), as …
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:082): Owner deferred the report's reject recommendation, to review the set later: AGENTS.md already says to continue independent work while a blocking answer is pend…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:081) *(superseded)*: Ours defers dependent questions and recomputes after each answer (grilling/SKILL.md:11-13, 20), but never waits for all answers to a round before asking anothe…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:080): Owner deferred the report's reject recommendation, to review the set later: Ours carries authorization forward for a step already requested and never treats th…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:079): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours explicitly does not exhaust every branch and stops once the n…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:078): Ours looks facts up itself, keeping ordinary lookups inline and delegating only bounded work.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:077): Owner deferred the report's reject recommendation, to review the set later: A fixed markdown block per question is a format recipe (S-03); U-09 leaves formatti…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:076) *(superseded)*: Ours attaches a recommendation (SKILL.md:13-14) but does not word questions for a one-word acceptance; the 1.3.1 draft rulings proposed taking it, and it cuts …
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:075): Ours attaches a recommendation with its assumptions and lets the user disagree.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:074): Ours asks a batch of independent settled-prerequisite questions and defers dependent ones.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:073): Ours maps material decisions and their prerequisites before asking.
- `2026-08-14` **adopt** (2026-10-14-migration:149): Adopted-in-part: absent-respondent questionnaire mode into grilling (two-exchange interview: who is it for / what must come back; grill the send, not the subje…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:090): Copied verbatim. Frontier rounds and non-blocking sub-agent fact-finding are genuinely absent from our grill-me, which paces at 1-3 questions and answers facts…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:023) *(superseded)*: The only adversarial design-tree exhaustion: it walks the unblocked frontier of a FORMED plan breadth-first and forbids action until every branch is visited. D…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-06-upstream-mattpocock_skills-4ae2317.md](../../reviews/2026-11-06-upstream-mattpocock_skills-4ae2317.md)
- [skill-comparisons/interaction-utilities](../../../archive/skill-comparisons/interaction-utilities/)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `absent-respondent`:
  - `mattpocock_skills:skill:skills/productivity/to-questionnaire#absent-respondent` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `answer-before-next-round`:
  - `mattpocock_skills:skill:skills/in-progress/loop-me#answer-before-next-round` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/productivity/grilling#answer-before-next-round` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `gap-targeted-questions`:
  - `mattpocock_skills:skill:skills/productivity/to-questionnaire#gap-targeted-questions` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `grill-the-send`:
  - `mattpocock_skills:skill:skills/productivity/to-questionnaire#grill-the-send` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `importance-ordered-questions`:
  - `mattpocock_skills:skill:skills/productivity/to-questionnaire#importance-ordered-questions` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `map-decisions`:
  - `mattpocock_skills:skill:skills/productivity/grilling#map-decisions` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `needed-item-coverage`:
  - `mattpocock_skills:skill:skills/productivity/to-questionnaire#needed-item-coverage` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `optional-docs`:
  - `mattpocock_skills:skill:skills/engineering/grill-with-docs#document-during-interview` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `question-batching`:
  - `mattpocock_skills:skill:skills/productivity/grilling#question-batching` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `recommended-answer`:
  - `mattpocock_skills:skill:skills/in-progress/loop-me#recommended-answer` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/productivity/grilling#recommended-answer` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `self-serve-facts`:
  - `mattpocock_skills:skill:skills/productivity/grilling#self-serve-facts` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `single-idea-questions`:
  - `mattpocock_skills:skill:skills/productivity/to-questionnaire#single-idea-questions` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `yes-accepts-recommendation`:
  - `mattpocock_skills:skill:skills/productivity/grilling#yes-accepts-recommendation` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
- `mattpocock_skills:skill:skills/in-progress/loop-me#live-spec-edits` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours documents only when requested, never as an automatic by-produ…
- `mattpocock_skills:skill:skills/in-progress/loop-me#spec-done-when-buildable` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours stops with decisions deferred or blocked instead of requiring…
- `mattpocock_skills:skill:skills/productivity/grilling#exhaustive-completion` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours explicitly does not exhaust every branch and stops once the n…
- `mattpocock_skills:skill:skills/productivity/grilling#non-blocking-lookup` (defer): Owner deferred the report's reject recommendation, to review the set later: AGENTS.md already says to continue independent work while a blocking answer is pend…
- `mattpocock_skills:skill:skills/productivity/grilling#reconfirm-before-action` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours carries authorization forward for a step already requested and never treats th…
- `mattpocock_skills:skill:skills/productivity/grilling#round-format` (defer): Owner deferred the report's reject recommendation, to review the set later: A fixed markdown block per question is a format recipe (S-03); U-09 leaves formatti…
- `mattpocock_skills:skill:skills/productivity/to-questionnaire#two-exchange-interview` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours does not force two exchanges when the recipient context and o…
<!-- /registry:generated declined -->
