---
skill: improve-codebase-architecture
domain: engineering
stage: Operations
substage: Maintenance
secondary: []
family: architecture-audit
aliases: []
status: active
---
# improve-codebase-architecture

Find evidence-backed architecture improvements within a named area or requested codebase survey.

<!-- registry:generated traits -->
- `scope-by-evidence`: Scope the audit to a named module or pain point, otherwise to the hot spots in recent change history. (Also weighs actual maintenance and test friction when choosing areas.)
- `friction-signals`: Surface architectural friction that current code actually supports rather than speculative smells.
- `candidate-comparison`: Give each candidate its files, friction, direction, benefit, migration cost, evidence and confidence, then present a concise comparison and the strongest supported recommendation.
- `optional-report`: Produce a standalone HTML report only when requested or clearly helpful, delegating presentation to the shared artifact skill and requiring any before/after diagram to show a real structural difference.
- `adr-conflict-callout`: When a candidate conflicts with a decision record, explain the new evidence that might justify revisiting it.
- `review-no-auto-followup`: Do not automatically enter a grilling loop, interview, alternative-design exercise or domain-document update after delivering the review; each happens only when requested or already authorized.
- `respect-area-adrs`: Honour the recorded architectural decisions that govern the area being changed.
- `top-candidate-recommendation`: End a candidate survey with a single top recommendation.
- `concrete-benefit-claims`: Phrase a candidate's benefits in the design vocabulary rather than generic claims such as easier to maintain.
- `domain-vocabulary`: Use the project's established domain vocabulary throughout what you write. (On improve-codebase-architecture, delivers sealed row 2026-10-30-mattpocock_skills-5beb35b:027: each candidate and its friction, where the definition says everything written; T5.)
- `read-domain-docs-first`: Read the domain glossary and the decision records near the code before exploring it.
- `rejection-decision-record`: When the user rejects an improvement candidate for a durable reason, offer a decision record so later reviews do not suggest it again, skipping ephemeral or self-evident reasons.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#scope-by-evidence** `skills/engineering/improve-codebase-architecture/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#friction-signals** `skills/engineering/improve-codebase-architecture/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#adr-conflict-callout** `skills/engineering/improve-codebase-architecture/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#respect-area-adrs** `skills/engineering/improve-codebase-architecture/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#html-architecture-report** `skills/engineering/improve-codebase-architecture/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#architecture-candidate-card** `skills/engineering/improve-codebase-architecture/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#top-candidate-recommendation** `skills/engineering/improve-codebase-architecture/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#concrete-benefit-claims** `skills/engineering/improve-codebase-architecture/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#domain-vocabulary** `skills/engineering/improve-codebase-architecture/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#read-domain-docs-first** `skills/engineering/improve-codebase-architecture/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#rejection-decision-record** `skills/engineering/improve-codebase-architecture/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-09` **adopt-merged** (2026-11-09-pocock-4ae2317:164): Checkpoint at 4ae2317 for the owner's trait rulings: 1 adopt.
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:019): Completes pending 2026-10-30-mattpocock_skills-5beb35b:039: rejection-decision-record is written at .claude/skills/improve-codebase-architecture/SKILL.md:30-32…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:018): Completes pending 2026-10-30-mattpocock_skills-5beb35b:033: read-domain-docs-first is written at .claude/skills/improve-codebase-architecture/SKILL.md:13, in t…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:017): Completes pending 2026-10-30-mattpocock_skills-5beb35b:027: domain-vocabulary is written at .claude/skills/improve-codebase-architecture/SKILL.md:20, in the se…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:016): Completes pending 2026-10-30-mattpocock_skills-5beb35b:044: concrete-benefit-claims is written at .claude/skills/improve-codebase-architecture/SKILL.md:20-22, …
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:561) *(superseded)*: Checkpoint at 5beb35b for the owner's trait rulings: 14 adopt, 15 defer.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:051): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours stops after the review and does not enter an interview automa…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:050): Ours ends with the strongest supported recommendation.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:049): Owner deferred the report's reject recommendation, to review the set later: A per-candidate category label is card formatting; the classification itself is han…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:048): Ours deliberately carries cost, evidence and confidence, which a strength badge hides (SKILL.md:18-21).
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:047): Owner deferred the report's reject recommendation, to review the set later: Ours draws a visual only when it clarifies and requires any before/after diagram to…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:046): Ours deliberately keeps the report optional and refuses a format built to fill its components (SKILL.md:25), which S-03 supports.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:045): Owner deferred the report's reject recommendation, to review the set later: Blanket conversion to bullets is a format quota; U-06 and O-06 set structure by aud…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:044) *(superseded)*: Ours asks for an expected benefit (SKILL.md:18-19) but not how to state it; a vocabulary-bound benefit is checkable where a generic claim is not.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:043): Owner deferred the report's reject recommendation, to review the set later: Ours's report file deliberately adds only the content contract and leaves presentat…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:042): Owner deferred the report's reject recommendation, to review the set later: A diagram-editing rule for an optional report adds no decision value to the review …
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:041): Owner deferred the report's reject recommendation, to review the set later: A six-word bullet cap is an invented numerical threshold (writing-principles, Pruni…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:040): Owner deferred the report's reject recommendation, to review the set later: A fixed header and legend is presentation for an optional report (SKILL.md:23-25); …
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:039) *(superseded)*: Ours has nothing that stops a rejected candidate being re-suggested; offering (not writing) an ADR keeps the review inside its authority (U-02), and domain-mod…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:038): Owner deferred the report's reject recommendation, to review the set later: Ours updates domain documents only when requested or already authorized (SKILL.md:1…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:036): Owner deferred the report's reject recommendation, to review the set later: Ours routes any HTML report through the shared artifact guidance, which keeps it of…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:035): Owner deferred the report's reject recommendation, to review the set later: Launching a viewer is a side effect beyond a review's inspection-and-report authori…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:034): Owner deferred the report's reject recommendation, to review the set later: AGENTS.md delegates only when it materially improves speed, context use or review q…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:033) *(superseded)*: Ours reads the domain terms and ADRs (SKILL.md:15) but sets no order; reading them first points the walk at the project's language and settled decisions.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:032): Ours reads the relevant ADRs and treats a conflict as needing new evidence before revisiting.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:030): Owner deferred the report's reject recommendation, to review the set later: Ours ends with a recommendation and runs no follow-up unless requested (SKILL.md:28…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:029): Ours explains the new evidence that might justify revisiting a conflicting ADR.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:028): Owner deferred the report's reject recommendation, to review the set later: Ours evaluates with codebase-design's vocabulary (SKILL.md:15-16), whose deliberate…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:027) *(superseded)*: Ours reads the domain terms (SKILL.md:15) but never says to write in them; one clause makes candidates readable against the glossary.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:026): Owner deferred the report's reject recommendation, to review the set later: Ours keeps HTML optional and uses an inline visual only when it clarifies structure…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:024): Ours reports only friction the current code supports and separates supported recommendations from hypotheses.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:023): Ours uses the named area or, for a broad survey, recent change history and actual friction.
- `2026-08-13` **adopt** (2026-10-14-migration:118): Adopted verbatim per user ruling 2026-08-13 (SKILL + HTML-REPORT; agents/openai.yaml excluded), overriding the council's demote-the-CDN-report change — user wi…
- `2026-08-11` **adopt** (2026-10-14-migration:037) *(superseded)*: The only skill that FINDS restructuring candidates rather than applying a known one, scoped by commit-history hot spots. It consumes codebase-design's vocabula…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-06-upstream-mattpocock_skills-4ae2317.md](../../reviews/2026-11-06-upstream-mattpocock_skills-4ae2317.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `adr-conflict-callout`:
  - `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#adr-conflict-callout` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `candidate-comparison`:
  - `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#architecture-candidate-card` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `concrete-benefit-claims`:
  - `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#concrete-benefit-claims` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `domain-vocabulary`:
  - `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#domain-vocabulary` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `friction-signals`:
  - `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#friction-signals` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `optional-report`:
  - `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#html-architecture-report` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `read-domain-docs-first`:
  - `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#read-domain-docs-first` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `rejection-decision-record`:
  - `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#rejection-decision-record` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `respect-area-adrs`:
  - `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#respect-area-adrs` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `scope-by-evidence`:
  - `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#scope-by-evidence` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `top-candidate-recommendation`:
  - `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#top-candidate-recommendation` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
- `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#candidate-before-after-visual` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours draws a visual only when it clarifies and requires any before/after diagram to…
- `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#candidate-constraint-interview` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours stops after the review and does not enter an interview automa…
- `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#candidate-dependency-tag` (defer): Owner deferred the report's reject recommendation, to review the set later: A per-candidate category label is card formatting; the classification itself is han…
- `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#cdn-only-scripts` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours routes any HTML report through the shared artifact guidance, which keeps it of…
- `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#compress-to-bullets` (defer): Owner deferred the report's reject recommendation, to review the set later: Blanket conversion to bullets is a format quota; U-06 and O-06 set structure by aud…
- `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#delegated-codebase-walk` (defer): Owner deferred the report's reject recommendation, to review the set later: AGENTS.md delegates only when it materially improves speed, context use or review q…
- `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#diagram-patterns` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours keeps HTML optional and uses an inline visual only when it clarifies structure…
- `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#document-during-interview` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours updates domain documents only when requested or already authorized (SKILL.md:1…
- `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#no-interfaces-yet` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours ends with a recommendation and runs no follow-up unless requested (SKILL.md:28…
- `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#open-artifact-for-user` (defer): Owner deferred the report's reject recommendation, to review the set later: Launching a viewer is a side effect beyond a review's inspection-and-report authori…
- `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#redraw-not-explain` (defer): Owner deferred the report's reject recommendation, to review the set later: A diagram-editing rule for an optional report adds no decision value to the review …
- `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#report-header-legend` (defer): Owner deferred the report's reject recommendation, to review the set later: A fixed header and legend is presentation for an optional report (SKILL.md:23-25); …
- `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#terse-card-prose` (defer): Owner deferred the report's reject recommendation, to review the set later: A six-word bullet cap is an invented numerical threshold (writing-principles, Pruni…
- `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#visual-restraint` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours's report file deliberately adds only the content contract and leaves presentat…
- `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#vocabulary-ban` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours evaluates with codebase-design's vocabulary (SKILL.md:15-16), whose deliberate…
<!-- /registry:generated declined -->
