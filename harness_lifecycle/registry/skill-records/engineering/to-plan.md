---
skill: to-plan
domain: engineering
stage: Design
substage: Decomposition
secondary: []
family: plan-authoring
aliases: []
status: active
---
# to-plan

Use when settled work needs a durable implementation plan: one roadmap phase, one standalone change, or one batch of units written box by box when a caller names that form. Turning an approved multi-phase spec into phases and their order is to-roadmap; a one-phase spec is planned here and recorded by tracker; a person's request for a plan, or work whose open questions must be settled first, is the plan playbook, which calls this; a delegated worker or a calling playbook uses this directly. Skip a plan document for clear bounded tasks.

**Boundary:** Writes a durable implementation plan for settled work: one roadmap phase, one standalone change or one batch of units, and no plan document when a bounded task or a roadmap row already says enough; turning an approved multi-phase spec into phases and their order is to-roadmap, a one-phase spec is planned here and recorded by tracker, ordering the units is principle-sequence-verifiable-units, what to remove before adding is principle-subtract-before-you-add, and migrating without shims is principle-migrate-without-shims. A plan in checked form names per-unit evidence and one `implement` scope; running it is `implement`.

<!-- registry:generated traits -->
- `plan-form-by-need`: Write no plan document when a bounded task or a roadmap row's acceptance suffices; otherwise a durable plan, or its box-by-box form when a caller names it.
- `durable-plan-format`: Produce a durable plan with ownership boundaries, interfaces, verification, dependencies and known files, saved to the plans path and approval-gated.
- `plan-evidence-bound`: List known files but do not invent exact symbols or freeze a file map without evidence, leaving implementers to discover internals within their ownership.
- `test-first-marking`: Mark risky changes test-first or characterization-first in the plan.
- `no-placeholder-plan`: Reject plan placeholders such as TBD, vague error-handling notes, unnamed test behaviours, same-as-another-task references and unresolved cross-task contracts, naming concrete acceptance instead.
- `plan-self-review`: Self-review the finished plan for spec-requirement coverage, consistent names and types across tasks, and a gap-naming pass that turns unnamed seams, migrations, rollout and cleanup into tasks or explicit exclusions.
- `reviewer-rejectable-sizing`: Size each task so a reviewer could accept or reject it independently of its neighbour, folding setup, scaffolding and docs into the deliverable they serve.
- `no-stale-code-snippets`: Keep code snippets out of a durable spec or ticket because they go stale.
- `ground-in-codebase`: Explore the current state of the code before writing, so the artifact targets what actually exists.
- `per-unit-evidence-boxes`: In a plan in checked form, give each task a required Check box with a command and pass condition, and Live and Measure each as a box or a stated not-applicable reason, for a coordinator to tick only when the evidence exists.
- `named-execution-scope`: Name in the plan which one execution scope runs it, task, phase or workstream, chosen by how the work is held, and leave how that scope runs to execution.
- `plan-lint-last`: Finish a plan in checked form by running its structure lint, fixing every line, rerunning after any later edit until it exits 0, reporting the last output and that it proves structure only, and handing back a plan still failing after two rounds as not ready.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **superpowers:skill:skills/writing-plans** `reference_harnesses/superpowers/skills/writing-plans/SKILL.md` @ 44c9b2d
  - merged from: planning-and-task-breakdown
  - merged from: to-tickets
  - modified: absorb planning-and-task-breakdown's task sizing and ordering detail
  - modified: absorb to-tickets as an OUTPUT MODE (plan file / tracker tickets with native blocking links / both) — the judge overruled the member who dropped this, because that member had itself called the loss 'the highest-value loss in this ledger'
  - modified: absorb to-tickets' wide-refactor expand-then-contract rule
- **agent-skills:skill:skills/incremental-implementation** `skills/incremental-implementation/SKILL.md`
- **superpowers:skill:skills/writing-plans** `skills/writing-plans/SKILL.md`
  - merged from: planning-and-task-breakdown
  - merged from: to-tickets
  - modified: absorb planning-and-task-breakdown's task sizing and ordering detail
  - modified: absorb to-tickets as an OUTPUT MODE (plan file / tracker tickets with native blocking links / both) — the judge overruled the member who dropped this, because that member had itself called the loss 'the highest-value loss in this ledger'
  - modified: absorb to-tickets' wide-refactor expand-then-contract rule
- **mattpocock_skills:skill:skills/engineering/to-tickets#ground-in-codebase** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#vertical-slices** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#dependency-edges** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#expand-contract** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#publish-to-tracker** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#real-id-wiring** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#sub-issue-linkage** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#no-stale-code-snippets** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#brief-behavioural** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#breakdown-approval-before-publish** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/implement-spec#dependency-edges** `skills/engineering/implement-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#prefactor-first** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#blast-radius-batches** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-11` **update** (2026-11-11-plan-playbook:011): Owner ruling N4 of 2026-11-11 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md:126), plan 45 U2 (scratchpad/mvp-stack/45/plan.md): the no-document Route ro…
- `2026-11-11` **update** (2026-11-11-plan-playbook:006): Owner ruling N4 of 2026-11-11 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md:126), plan 45 U1 (scratchpad/mvp-stack/45/plan.md): the description names th…
- `2026-11-11` **update** (2026-11-11-tracker:021): Owner ruling N, R2/R3 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 27 section 5 T1b with critic-27d R1/R2 applied. The hand-off to tracker adds …
- `2026-11-11` **update** (2026-11-11-tracker:011): Owner rulings M2 (2026-11-10), N2 and N3 (2026-11-11) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 27 T1a. F6: the nearest case names a multi-ph…
- `2026-11-11` **update** (2026-11-10-renames-splits:151): Owner rulings M1, M4 (2026-11-10) and N1, N2 (2026-11-11) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 24 U8r. Name, heading and description (bo…
- `2026-11-11` **rename** (2026-11-10-renames-splits:144): Owner rulings M1, M4 (2026-11-10) and N1, N2 (2026-11-11) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 24 U8r. planning is renamed to-plan: an i…
- `2026-11-10` **update** (2026-11-10-renames-splits:100): Critic-18b correction of the U4 split (coordinator rulings F1, F2). Elaborate keeps its approval gate: no Beads write, the task or its plan: note, before the p…
- `2026-11-10` **update** (2026-11-10-renames-splits:087) *(superseded)*: Owner ruling C of 2026-11-05 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 14a U4. Route sends an approved spec needing phase/stage decomposition…
- `2026-11-10` **split** (2026-11-10-renames-splits:086): Owner ruling C of 2026-11-05 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 14a U4. Its Decompose and Slicing sections become to-tickets; referenc…
- `2026-11-09` **adopt-merged** (2026-11-09-pocock-4ae2317:162) *(superseded)*: Checkpoint at 4ae2317 for the owner's trait rulings: 2 adopt.
- `2026-11-06` **update** (2026-11-06-renames:013): Owner ruling D of 2026-11-05 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 14a U1. The Run with: contract names implement: skeleton.md's template…
- `2026-11-02` **update** (2026-11-02-pilot-2:018): Final critic of pilot 2. The lint splits lines as execution's extractor does, normalizing CRLF only and splitting on LF, and any other line separator is a prob…
- `2026-11-02` **adopt** (2026-11-02-pilot-2:011): Completes pending 2026-10-30-mattpocock_skills-5beb35b:116: blast-radius-batches is written at .claude/skills/planning/SKILL.md:83-84, read against its ruled r…
- `2026-11-02` **adopt** (2026-11-02-pilot-2:010): Completes pending 2026-10-30-mattpocock_skills-5beb35b:102: prefactor-first is written at .claude/skills/planning/SKILL.md:81-82, read against its ruled reword…
- `2026-11-02` **update** (2026-11-02-pilot-2:009): Pilot 2, ruling 14: a Skeleton branch that a calling playbook or an explicit request opts into, with evidence boxes per unit, one named execution scope and a s…
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:573) *(superseded)*: Checkpoint at 5beb35b for the owner's trait rulings: 2 adopt, 12 defer.
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:565) *(superseded)*: Checkpoint at 5beb35b for the owner's trait rulings: 13 adopt, 10 defer.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:275): HELD: planning (.claude/skills/planning/SKILL.md:33): Encoding real blocking edges is planning's job (SKILL.md:33); execution consumes the ready frontier (exec…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:121): Ours writes no Beads before the matching approval of the presented structure.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:120): Owner deferred the report's reject recommendation, to review the set later: Ours clarifies only material ambiguity and uses existing approval (decompose.md:48-…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:119): Owner deferred the report's reject recommendation, to review the set later: Ours presents the phase list, stage counts, every edge with its reason and open que…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:118): Ours deliberately pairs behavioural goals with known ownership paths (plan-format.md:27-28, SKILL.md:46-48).
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:117): Owner deferred the report's reject recommendation, to review the set later: We always track in Beads (AGENTS.md, Track durable work), so a tracker-less file-pe…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:116) *(superseded)*: Ours orders expand-migrate-contract and names an integration boundary when green cannot hold (SKILL.md:66-68) but does not size the migrate batches; blast-radi…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:115): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours sizes tasks by independent reviewability, an orthogonal crite…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:114): Owner deferred the report's reject recommendation, to review the set later: Ours's source is an approved spec document read in full (SKILL.md:26); a rule to re…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:112): Ours's plan approach is prose with no code blocks.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:111): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: our plans explicitly list known paths and ownership boundaries, wh…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:110): Owner deferred the report's reject recommendation, to review the set later: Our Beads rules (AGENTS.md, Track durable work) already give every bead a why-and-w…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:109): Owner deferred the report's reject recommendation, to review the set later: Our Beads rules (AGENTS.md, Track durable work) allow only the `human` label; agent…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:108): Ours deliberately keeps the spec as a document linked from epics (decompose.md:56-71), so there is no source issue to parent under.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:107): Ours wires edges after every bead exists, by the returned IDs.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:106): Ours deliberately tracks in Beads (AGENTS.md, Track durable work) with an approval before each write (SKILL.md:36).
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:105): Ours uses expand, migrate, contract and names an integration boundary when tasks cannot stay green.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:104): Ours wires only real edges and never chains listing order.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:103): Ours prefers independently verifiable vertical slices.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:102) *(superseded)*: Ours slices vertically and uses expand-migrate-contract (SKILL.md:66-68) but never looks for an enabling refactor first, which lowers the risk of every later s…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:101): Owner deferred the report's reject recommendation, to review the set later: ROUTED: AGENTS.md:93-94 routes domain terminology and ADRs, and AGENTS.md:26 surfac…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:100): Owner deferred the report's reject recommendation, to review the set later: ROUTED: AGENTS.md:93-94 routes domain terminology and ADRs, and AGENTS.md:26 surfac…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:099): Ours reads the relevant code and tests before elaborating and writes later plans against the code they will meet.
- `2026-08-12` **adopt-merged** (2026-10-14-migration:113): Adopted-merged into the rewritten planning skill (Elaborate mode): file-map-before-tasks, Interfaces Consumes/Produces, reviewer right-sizing test, no-placehol…
- `2026-08-12` **adopt** (2026-10-14-migration:104): Adopted-merged narrowly into the planning rewrite: expand-contract sequencing for wide refactors incl. non-green-batch integration-branch fallback, tracer-bull…
- `2026-08-12` **adopt** (2026-10-14-migration:096): Closes the 2026-07-15 deferral. Ruled a discipline by execution-disciplines/; its durable content is now distributed: vertical slicing + tracer bullets in plan…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:033) *(superseded)*: The only skill turning approved work into units executable with zero prior context. Chosen as merge base for its plan structure and required-sub-skill header.
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-06-upstream-mattpocock_skills-4ae2317.md](../../reviews/2026-11-06-upstream-mattpocock_skills-4ae2317.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `beads-native-tracking`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#publish-to-tracker` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-10)
  - `mattpocock_skills:skill:skills/engineering/to-tickets#sub-issue-linkage` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-10)
- `blast-radius-batches`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#blast-radius-batches` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-11)
- `breakdown-approval-before-publish`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#breakdown-approval-before-publish` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-10)
- `dependency-edges`:
  - `mattpocock_skills:skill:skills/engineering/implement-spec#dependency-edges` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-10)
  - `mattpocock_skills:skill:skills/engineering/to-tickets#dependency-edges` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-10)
- `expand-contract`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#expand-contract` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-11)
- `ground-in-codebase`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#ground-in-codebase` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `no-stale-code-snippets`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#no-stale-code-snippets` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `plan-evidence-bound`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#brief-behavioural` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `prefactor-first`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#prefactor-first` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-11)
- `real-id-wiring`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#real-id-wiring` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-10)
- `vertical-slices`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#vertical-slices` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-11)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
- `mattpocock_skills:skill:skills/engineering/to-tickets#domain-vocabulary` (defer): Owner deferred the report's reject recommendation, to review the set later: ROUTED: AGENTS.md:93-94 routes domain terminology and ADRs, and AGENTS.md:26 surfac…
- `mattpocock_skills:skill:skills/engineering/to-tickets#file-per-ticket` (defer): Owner deferred the report's reject recommendation, to review the set later: We always track in Beads (AGENTS.md, Track durable work), so a tracker-less file-pe…
- `mattpocock_skills:skill:skills/engineering/to-tickets#no-stale-file-paths` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: our plans explicitly list known paths and ownership boundaries, wh…
- `mattpocock_skills:skill:skills/engineering/to-tickets#read-full-source-issue` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours's source is an approved spec document read in full (SKILL.md:26); a rule to re…
- `mattpocock_skills:skill:skills/engineering/to-tickets#ready-for-agent-label` (defer): Owner deferred the report's reject recommendation, to review the set later: Our Beads rules (AGENTS.md, Track durable work) allow only the `human` label; agent…
- `mattpocock_skills:skill:skills/engineering/to-tickets#respect-area-adrs` (defer): Owner deferred the report's reject recommendation, to review the set later: ROUTED: AGENTS.md:93-94 routes domain terminology and ADRs, and AGENTS.md:26 surfac…
- `mattpocock_skills:skill:skills/engineering/to-tickets#session-sized-tickets` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours sizes tasks by independent reviewability, an orthogonal crite…
- `mattpocock_skills:skill:skills/engineering/to-tickets#ticket-breakdown-feedback` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours clarifies only material ambiguity and uses existing approval (decompose.md:48-…
- `mattpocock_skills:skill:skills/engineering/to-tickets#ticket-breakdown-preview` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours presents the phase list, stage counts, every edge with its reason and open que…
- `mattpocock_skills:skill:skills/engineering/to-tickets#ticket-template` (defer): Owner deferred the report's reject recommendation, to review the set later: Our Beads rules (AGENTS.md, Track durable work) already give every bead a why-and-w…
<!-- /registry:generated declined -->
