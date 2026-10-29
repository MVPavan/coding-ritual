---
skill: brainstorming
domain: core
stage: Intake
substage: Clarification
secondary: [Specification]
family: spec-authoring
aliases: [idea-refine]
status: active
---
# brainstorming

## Capability

Use when material scope or behavior decisions need exploration, or the user requests brainstorming. Handle a single routine ambiguity directly.

<!-- registry:generated traits -->
- `match-interaction-to-ambiguity`: Match the interaction depth to the ambiguity — return to the task, ask one focused question, or run a structured exploration — rather than over- or under-investigating.
- `synthesize-settled`: When the decisions are already settled, synthesize them into a spec without reopening the discussion.
- `scoped-context-read`: Read only the existing code, authoritative docs and constraints needed to distinguish the live choices.
- `reuse-before-new`: Name the closest existing solution before proposing a new one.
- `decision-frame`: Establish the outcome, intended user, success criteria, constraints and exclusions before committing to an approach.
- `options-with-tradeoffs`: Present materially different options with their tradeoffs when alternatives remain.
- `spec-template`: Capture the spec in a fixed skeleton: problem, solution, user stories, implementation decisions, testing decisions, out of scope and further notes.
- `spec-criteria-and-questions`: Add success-criteria and open-questions sections to the spec skeleton.
- `none-keeps-heading`: Keep every spec heading, writing None in an empty section so its absence reads as a decision.
- `testing-seam-decision`: Record in the spec which seam the feature is tested at, preferring an existing and the highest useful seam and the fewest seams.
- `no-stale-file-paths`: Keep concrete file paths out of a durable spec, ticket or brief, describing interfaces and behaviour that survive code drift.
- `no-stale-code-snippets`: Keep code snippets out of a durable spec or ticket because they go stale.
- `prototype-snippet`: Inline a prototype snippet in the spec only when it encodes a decision more precisely than prose can.
- `spec-approval-gate`: Keep a spec in draft until explicit authorization names its direction and scope, with any blocking question resolved or moved to out-of-scope first.
- `material-risk-review`: Route an artifact or change with material risk or a broad blast radius through an independent critic review before it is accepted.
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
- **mattpocock_skills:skill:skills/engineering/to-spec** `skills/engineering/to-spec/SKILL.md`
- **superpowers:skill:skills/brainstorming** `skills/brainstorming/SKILL.md`
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
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
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
