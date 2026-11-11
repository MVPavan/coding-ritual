---
skill: discovery
domain: core
stage: Intake
substage: Clarification
secondary: [Research]
family: requirements-elicitation
aliases: []
status: active
---
# discovery

Use when material scope or behavior decisions are still open and need settling, or the user requests a brainstorm. Skip a single factual lookup or one routine detail, which need no run; writing settled decisions up as a spec is to-spec.

**Boundary:** Settles open scope or behaviour questions by who can answer them (this project's code, outside sources through research, a run through prototype, a routine pick, the owner last) and writes a checked record of the answers; a single lookup or routine detail needs no run, writing settled decisions up as a durable spec is to-spec, an explicitly requested interview that challenges the owner's own plan is grilling, and decisions charted across sessions are wayfinder.

<!-- registry:generated traits -->
- `match-interaction-to-ambiguity`: Match the interaction depth to the ambiguity — return to the task, ask one focused question, or run a structured exploration — rather than over- or under-investigating.
- `scoped-context-read`: Read only the existing code, authoritative docs and constraints needed to distinguish the live choices.
- `reuse-before-new`: Name the closest existing solution before proposing a new one.
- `decision-frame`: Establish the outcome, intended user, success criteria, constraints and exclusions before committing to an approach.
- `answerer-triage`: Sort each open question by who can answer it (this project's code, cited by file and line; outside sources; a run; a routine pick; the owner) and put to the owner only what the others cannot settle.
- `options-with-tradeoffs`: Present materially different options with their tradeoffs when alternatives remain.
- `question-batching`: Batch independent questions whose prerequisites are settled and defer each dependent question until its prerequisites are answered.
- `recommended-answer`: Attach a recommended answer to each question, letting the respondent disagree. (Labels the recommendation's assumptions.)
- `yes-accepts-recommendation`: Word each question so that a yes accepts your recommended answer.
- `round-format`: Lay out each round in a fixed question-and-recommendation markdown format, one block per question. (Delivers report D's row (pending 2026-11-11-discovery:001) as one fixed block per question, in our own layout with no emoji.)
- `answer-before-next-round`: Wait for the respondent's answers to a round before asking the next one.
- `settled-stop`: Recompute the unresolved choices after each answer and stop once the needed ones are settled, deferred or blocked, without exhausting every branch.
- `self-serve-facts`: Look up available facts yourself rather than asking, leaving only the decisions to the live participant. (Through the answerer triage: code is read, outside facts go to research, a run to prototype.)
- `approval-interpretation`: Treat a clear acceptance of a concrete proposal or an explicit delegation of routine choices as usable authority, and silence as not approval.
- `observable-outcomes`: Translate vague goals such as scalable or simple into observable outcomes only when the distinction affects the design.
- `structured-divergence`: Generate only enough distinct options to expose the tradeoff, compare them on value, feasibility, cost and reversibility, test the assumption most likely to reverse the choice first, and keep rejected options with their reasons.
- `exploration-lenses`: Apply ideation lenses such as SCAMPER or Jobs-to-Be-Done selectively to unlock options, never as a mandatory quota or sequence.
- `assumption-audit`: For each candidate direction, list its assumptions as must be true (dealbreakers that kill it if wrong), should be true (important but the approach can adjust) or might be true (secondary), validate the dealbreakers before building, and leave the might-be-true ones until the core is proven.
- `mvp-scope`: Scope the first version of a chosen direction to one user job done well, sized by what can be built and tested in a time box rather than by a feature list, aimed at the riskiest assumption, with a mandatory list of what it is not doing and why, and expect it to feel incomplete to the builder.
- `judgment-frameworks`: Apply one to three comparison frameworks to sharpen a choice rather than to decorate the report.
- `decision-sequences`: Follow a decision sequence matched to the question's domain, handing its fact-finding steps to `research`.
- `inline-diagrams`: Draw a structure, flow, sequence or state question as a small inline Mermaid block, using prose for requirements and trade-offs.
- `visuals-into-spec`: Re-express an approved diagram inside the durable spec as a Mermaid block, or record what a mockup showed and decided, rather than linking disposable scratch files.
- `html-mockup-on-request`: On explicit request only, produce one self-contained offline HTML mockup under the scratch directory for what a diagram cannot carry.
- `sourced-status-record`: Write one file per run with a row per question giving its answer, its source, a confidence for each established fact and a status (established, decided, routine, proposed, open), marking a material choice decided only on the owner's quoted, dated word or a recorded delegation, and check the file with a script.
- `area-topic-filing`: Without a path from the caller, file the output under one root by the work's area and topic, reusing an existing folder before creating one, two levels at most, and never replacing an earlier run's file without authority to revise it.
- `generated-record-index`: Regenerate one index line per record (date, question, outcome) from the files themselves, never by hand.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **agent-skills:skill:skills/idea-refine** `reference_harnesses/agent-skills/skills/idea-refine/SKILL.md` @ 7676817
- **agent-skills:skill:skills/spec-driven-development** `reference_harnesses/agent-skills/skills/spec-driven-development/SKILL.md` @ 7676817
  - merged from: brainstorming
  - merged from: to-spec
  - modified: absorb brainstorming's hard design-approval gate, decomposition check and self-review
  - modified: absorb to-spec's no-interview fast path for when discussion has already settled
  - dropped: brainstorming's ~1,400-line visual-companion server bundle — heavy dependency, and prototype already covers the need
- **agent-skills:skill:skills/interview-me** `skills/interview-me/SKILL.md`
- **agent-skills:skill:skills/idea-refine** `skills/idea-refine/SKILL.md`
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
- **mattpocock_skills:skill:skills/productivity/grilling#round-format** `skills/productivity/grilling/SKILL.md` @ 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-11` **update** (2026-11-11-discovery:018): Owner ruling L1 of 2026-11-10 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 20 D4 (sections 4.4, 5): discovery lists area-topic-filing, the filin…
- `2026-11-11` **update** (2026-11-11-discovery:016): Owner ruling L1 of 2026-11-10 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 20 D3 fix (critic-35b): the refinement reference's assumption audit (…
- `2026-11-11` **adopt** (2026-11-11-discovery:014): Owner ruling L1 of 2026-11-10 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 20 D3: completes the pending rewording 2026-11-11-discovery:001. disc…
- `2026-11-11` **update** (2026-11-11-discovery:013): Owner ruling L1 of 2026-11-10 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 20 D3 (section 6): the body is rewritten as the hub. It routes first,…
- `2026-11-11` **update** (2026-11-11-discovery:012): Plan 20 D2 fix (critic-34f N4, coordinator): check_record.py reports any line starting with `|` before the table header, so a malformed earlier table or orphan…
- `2026-11-11` **update** (2026-11-11-discovery:011): Plan 20 D2 fix (critic-34d, coordinator's decision): check_record.py no longer reads fences or comments. A file is a record only when its first non-blank line …
- `2026-11-11` **update** (2026-11-11-discovery:010): Plan 20 D2 fix (critic-34b): check_record.py reads only lines outside code fences and comments, so a fenced example is neither checked, indexed nor continued b…
- `2026-11-11` **update** (2026-11-11-discovery:009): Plan 20 D2 (section 6): the deterministic part of the record rule. scripts/check_record.py checks a discovery record's header, rows, status and source forms an…
- `2026-11-11` **merge** (2026-11-11-discovery:003): Owner ruling L1 of 2026-11-10 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 20 D1. idea-refine, an alias of brainstorming, retires into discovery…
- `2026-11-11` **rename** (2026-11-11-discovery:002): Owner ruling L1 of 2026-11-10 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 20 D1. The skill brainstorming is renamed discovery, the hub that set…
- `2026-11-11` **adopt** (2026-11-11-discovery:001) *(superseded)*: Owner ruling L1 of 2026-11-10 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 20 D0: the discovery hub asks its open questions in rounds, each ques…
- `2026-11-11` **update** (2026-11-10-renames-splits:159): Owner rulings M1, M4 (2026-11-10) and N1, N2 (2026-11-11) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 24 U8r. Hand-off names to-plan.
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
- `2026-08-12` **adopt** (2026-10-14-migration:095): Revisited 2026-08-12: original content restored (philosophy/anti-patterns/tone/red-flags kept) with surgical changes only — idea-doc write to docs/ideas/<name>…
- `2026-08-11` **adopt** (2026-10-14-migration:086): Mechanics merged into brainstorming, not installed as a skill. Taken: predict-the-next-three stop test, approval-names-the-direction gate with the four near-mi…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:026) *(superseded)*: The only skill producing an approved written spec behind a hard no-implementation gate, with a six-area content model. Chosen as the merge base over to-spec be…
- `2026-08-11` **adopt** (2026-10-14-migration:024) *(superseded)*: RESTORED BY USER after the council. Both members and the judge agreed to drop it: the judge classed it product-shape ideation rather than engineering, and it w…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-11-upstream-mattpocock_skills-4ae2317-discovery.md](../../reviews/2026-11-11-upstream-mattpocock_skills-4ae2317-discovery.md)
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
- `round-format`:
  - `mattpocock_skills:skill:skills/productivity/grilling#round-format` (adopted at 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d)
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
