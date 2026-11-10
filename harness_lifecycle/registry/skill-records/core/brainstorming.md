---
skill: brainstorming
domain: core
stage: Intake
substage: Clarification
secondary: []
family: spec-authoring
aliases: [idea-refine]
status: active
---
# brainstorming

Use when material scope or behavior decisions are still open and need exploring, or the user requests brainstorming. Skip writing settled decisions up as a spec, which is to-spec; handle a single routine ambiguity directly.

**Boundary:** Explores and compares options when scope or behaviour is open and ends at decisions; writing settled decisions up as a durable spec is to-spec, and an explicitly requested interview that challenges the owner's own plan is grilling.

<!-- registry:generated traits -->
- `match-interaction-to-ambiguity`: Match the interaction depth to the ambiguity — return to the task, ask one focused question, or run a structured exploration — rather than over- or under-investigating.
- `scoped-context-read`: Read only the existing code, authoritative docs and constraints needed to distinguish the live choices.
- `reuse-before-new`: Name the closest existing solution before proposing a new one.
- `decision-frame`: Establish the outcome, intended user, success criteria, constraints and exclusions before committing to an approach.
- `options-with-tradeoffs`: Present materially different options with their tradeoffs when alternatives remain.
- `question-batching`: Batch independent questions whose prerequisites are settled and defer each dependent question until its prerequisites are answered.
- `recommended-answer`: Attach a recommended answer to each question, letting the respondent disagree. (Labels the recommendation's assumptions.)
- `settled-stop`: Recompute the unresolved choices after each answer and stop once the needed ones are settled, deferred or blocked, without exhausting every branch.
- `self-serve-facts`: Look up available facts yourself rather than asking, leaving only the decisions to the live participant.
- `approval-interpretation`: Treat a clear acceptance of a concrete proposal or an explicit delegation of routine choices as usable authority, and silence as not approval.
- `observable-outcomes`: Translate vague goals such as scalable or simple into observable outcomes only when the distinction affects the design.
- `structured-divergence`: Generate only enough distinct options to expose the tradeoff, compare them on value, feasibility, cost and reversibility, test the assumption most likely to reverse the choice first, and keep rejected options with their reasons.
- `exploration-lenses`: Apply ideation lenses such as SCAMPER or Jobs-to-Be-Done selectively to unlock options, never as a mandatory quota or sequence.
- `inline-diagrams`: Draw a structure, flow, sequence or state question as a small inline Mermaid block, using prose for requirements and trade-offs.
- `visuals-into-spec`: Re-express an approved diagram inside the durable spec as a Mermaid block, or record what a mockup showed and decided, rather than linking disposable scratch files.
- `html-mockup-on-request`: On explicit request only, produce one self-contained offline HTML mockup under the scratch directory for what a diagram cannot carry.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **agent-skills:skill:skills/spec-driven-development** `reference_harnesses/agent-skills/skills/spec-driven-development/SKILL.md` @ 7676817
  - merged from: brainstorming
  - merged from: to-spec
  - modified: absorb brainstorming's hard design-approval gate, decomposition check and self-review
  - modified: absorb to-spec's no-interview fast path for when discussion has already settled
  - dropped: brainstorming's ~1,400-line visual-companion server bundle — heavy dependency, and prototype already covers the need
- **agent-skills:skill:skills/interview-me** `skills/interview-me/SKILL.md`
- **agent-skills:skill:skills/spec-driven-development** `skills/spec-driven-development/SKILL.md`
  - merged from: brainstorming
  - merged from: to-spec
  - modified: absorb brainstorming's hard design-approval gate, decomposition check and self-review
  - modified: absorb to-spec's no-interview fast path for when discussion has already settled
  - dropped: brainstorming's ~1,400-line visual-companion server bundle — heavy dependency, and prototype already covers the need
- **superpowers:skill:skills/brainstorming** `skills/brainstorming/SKILL.md`
- **mattpocock_skills:skill:skills/engineering/to-spec#synthesize-settled** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-spec#testing-seam-decision** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-spec#spec-template** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-spec#no-stale-file-paths** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-spec#no-stale-code-snippets** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-spec#prototype-snippet** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-spec#user-perspective-framing** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-spec#implementation-decisions-scope** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-spec#testing-decisions-contents** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#prototype-snippet** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-spec#ground-in-codebase** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-10` **adopt** (2026-11-10-renames-splits:083): critic-17b F1: to-spec/SKILL.md:15 reads what the spec must describe, not what distinguishes the live choices, so it does not deliver scoped-context-read and c…
- `2026-11-10` **update** (2026-11-10-renames-splits:070): Owner ruling C of 2026-11-05 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 14a U3. It ends at decisions and hands a durable spec to to-spec; its …
- `2026-11-10` **split** (2026-11-10-renames-splits:069): Owner ruling C of 2026-11-05 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 14a U3. Its 'Record and hand off' spec section becomes to-spec; refere…
- `2026-11-06` **update** (2026-11-06-renames:014): Owner ruling D of 2026-11-05 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 14a U1. Its hand-off line names the units it continues into, planning …
- `2026-11-01` **reject** (2026-11-01-cursor_plugins-pstack-principles:028): Lands as a skill or playbook trait. Not held: the prototype skill builds a throwaway artifact when a named question calls for one (named-question), which is op…
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:564) *(superseded)*: Checkpoint at 5beb35b for the owner's trait rulings: 10 adopt, 6 defer.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:113): HELD: brainstorming: the definition puts the snippet in the spec, which brainstorming writes and planning consumes; plans stay prose (plan-format.md:43).
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:098): Ours records what makes a good test, the level tested and prior art.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:097): Ours lists modules and interfaces, architecture, schema, API contracts and clarifications.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:096): Owner deferred the report's reject recommendation, to review the set later: Ours keeps the actor-capability-benefit stories but scales them to the work (spec-t…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:095): Ours writes problem and solution from the user's perspective.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:094): Owner deferred the report's reject recommendation, to review the set later: Our Beads rules (AGENTS.md, Track durable work) allow only the `human` label; agent…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:093): Owner deferred the report's reject recommendation, to review the set later: Ours saves the spec as a file that planning passes as `--spec-id` (SKILL.md:40-41, …
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:092): Ours allows a decision-rich prototype snippet as the one exception.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:091): Ours keeps code snippets out of a spec.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:090): Ours keeps create/modify paths out of a spec.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:089): Ours's template carries every upstream section plus success criteria and open questions.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:088): Owner deferred the report's reject recommendation, to review the set later: Ours's seam is part of the spec, which needs approval naming its direction (SKILL.m…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:087): Ours records the seam, preferring an existing, high and few seams.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:086): Owner deferred the report's reject recommendation, to review the set later: ROUTED: AGENTS.md:93-94 routes domain terminology and ADRs, and AGENTS.md:26 surfac…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:085): Owner deferred the report's reject recommendation, to review the set later: ROUTED: AGENTS.md:93-94 routes domain terminology and ADRs, and AGENTS.md:26 surfac…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:084): Ours deliberately bounds reading (SKILL.md:21-23), matching AGENTS.md's 'search narrowly and read context as needed'.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:083): Ours synthesizes settled decisions without reopening the discussion.
- `2026-08-12` **adopt** (2026-10-14-migration:109): Revisited 2026-08-12: still merged into ours, not installed. Per-unit boundary questions now live in the spec template's Implementation Decisions section (temp…
- `2026-08-12` **adopt** (2026-10-14-migration:103): Revisited 2026-08-12: now the SKELETON of references/spec-template.md — Problem Statement, Solution, User Stories, Implementation Decisions, Testing Decisions,…
- `2026-08-12` **adopt-merged** (2026-10-14-migration:099): Revisited 2026-08-12: spec half only, split from its plan/tasks/implement phases (those belong to our prepare-phases/planning/phase-execution). Taken into the …
- `2026-08-11` **adopt** (2026-10-14-migration:086): Mechanics merged into brainstorming, not installed as a skill. Taken: predict-the-next-three stop test, approval-names-the-direction gate with the four near-mi…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:026) *(superseded)*: The only skill producing an approved written spec behind a hard no-implementation gate, with a six-area content model. Chosen as the merge base over to-spec be…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `implementation-decisions-scope`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#implementation-decisions-scope` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-10)
- `no-stale-code-snippets`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#no-stale-code-snippets` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-10)
- `no-stale-file-paths`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#no-stale-file-paths` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-10)
- `prototype-snippet`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#prototype-snippet` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-10)
  - `mattpocock_skills:skill:skills/engineering/to-tickets#prototype-snippet` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-10)
- `scoped-context-read`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#ground-in-codebase` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `spec-template`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#spec-template` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-10)
- `synthesize-settled`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#synthesize-settled` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-10)
- `testing-decisions-contents`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#testing-decisions-contents` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-10)
- `testing-seam-decision`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#testing-seam-decision` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-10)
- `user-perspective-framing`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#user-perspective-framing` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-10)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
- `cursor_plugins:skill:pstack/skills/principle-experience-first#throwaway-design-first` (reject): Lands as a skill or playbook trait. Not held: the prototype skill builds a throwaway artifact when a named question calls for one (named-question), which is op…
- `mattpocock_skills:skill:skills/engineering/to-spec#domain-vocabulary` (defer): Owner deferred the report's reject recommendation, to review the set later: ROUTED: AGENTS.md:93-94 routes domain terminology and ADRs, and AGENTS.md:26 surfac…
- `mattpocock_skills:skill:skills/engineering/to-spec#exhaustive-user-stories` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours keeps the actor-capability-benefit stories but scales them to the work (spec-t…
- `mattpocock_skills:skill:skills/engineering/to-spec#publish-to-tracker` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours saves the spec as a file that planning passes as `--spec-id` (SKILL.md:40-41, …
- `mattpocock_skills:skill:skills/engineering/to-spec#ready-for-agent-label` (defer): Owner deferred the report's reject recommendation, to review the set later: Our Beads rules (AGENTS.md, Track durable work) allow only the `human` label; agent…
- `mattpocock_skills:skill:skills/engineering/to-spec#respect-area-adrs` (defer): Owner deferred the report's reject recommendation, to review the set later: ROUTED: AGENTS.md:93-94 routes domain terminology and ADRs, and AGENTS.md:26 surfac…
- `mattpocock_skills:skill:skills/engineering/to-spec#seam-preconfirmation` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours's seam is part of the spec, which needs approval naming its direction (SKILL.m…
<!-- /registry:generated declined -->
