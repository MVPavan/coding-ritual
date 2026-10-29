---
skill: authoring-for-agents
domain: core
stage: Improvement
substage: Codification
secondary: []
family: agent-doc-authoring
aliases: []
status: active
---
# authoring-for-agents

## Capability

Use when creating or changing agent instructions or their activation behavior. Skip edits that only correct spelling or formatting.

<!-- registry:generated traits -->
- `surface-choice`: Choose the right owner for an instruction — policy file, project document with a pointer, skill, manual alias, conditional reference, or an existing hook or check — and search for an existing owner first.
- `activation-boundary`: Put the activation boundary first — positive cases and the nearest misleading case to skip — and let a description select rather than duplicate the workflow.
- `inline-vs-disclose`: Inline what every branch needs and disclose branch-specific material behind a conditional pointer. (An unconditional read saves no context.)
- `outputs-and-authority`: State outputs, material invariants, authority boundaries and stop conditions explicitly.
- `one-effective-instruction`: Prefer one effective instruction over repeated prohibitions or ritual steps, treating wording techniques as hypotheses rather than laws.
- `context-pointers`: Write a pointer that names the material and the condition for reaching it, front-loading the trigger. (Also distinguishes the nearest competing workflow.)
- `two-loads`: Weigh always-loaded context cost on the agent against cognitive load on the human. (Judges savings by the full read path rather than entrypoint length.)
- `completion-criteria-clarity`: End each step on an observable, checkable done-or-not-done criterion that resists premature completion.
- `precision-and-discretion`: Match prescription to fragility: exact recipes for deterministic operations, judgment for context-dependent choices.
- `single-source-of-truth`: Keep each meaning in one authoritative place so changing it is a one-place edit.
- `environment-as-cache`: Point to authoritative commands and lookups instead of copying volatile facts the agent can find itself.
- `no-op-deletion`: Delete instructions the model already follows by default.
- `unsupported-claim-removal`: Remove unsupported claims and invented thresholds from instructions.
- `skill-packaging`: Keep one canonical directory per workflow with a SKILL.md, adding references only for substantial conditional material and scripts for reusable mechanical work.
- `invocation-mode`: Choose model-invoked or user-invoked activation, setting the disable-model-invocation flag for manual workflows.
- `invocation-sidecar-sync`: Pair the manual-invocation flag with the provider's implicit-invocation policy and regenerate the catalog and sidecars together after metadata edits.
- `compatibility-alias`: Keep a manual or legacy entrypoint as a thin pointer that delegates to the canonical owner, not as an independent workflow others auto-activate.
- `verification`: Inspect the diff for lost contracts, scale fresh-context and pressure trials to behavioural risk, and report unavailable behavioural checks as a limit instead of manufacturing evidence.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **superpowers:skill:skills/writing-skills** `reference_harnesses/superpowers/skills/writing-skills/SKILL.md` @ 44c9b2d
  - merged from: writing-for-agents
  - modified: absorb the information ladder, the two-loads model, pointer wording, the no-op test and negation scoping — the vocabulary for deciding what goes where
- **agent-skills:doc:docs/skill-anatomy.md**
- **mattpocock_skills:skill:skills/productivity/writing-for-agents** `skills/productivity/writing-for-agents/SKILL.md`
- **superpowers:skill:skills/writing-skills** `skills/writing-skills/SKILL.md`
  - merged from: writing-for-agents
  - modified: absorb the information ladder, the two-loads model, pointer wording, the no-op test and negation scoping — the vocabulary for deciding what goes where
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-12` **adopt-merged** (2026-10-14-migration:114): Adopted as one third of authoring-for-agents: Match-the-Form-to-the-Failure table, description-never-summarizes-workflow rule, rationalization tables/red flags…
- `2026-08-12` **adopt** (2026-10-14-migration:108): Adopted as the writing-theory core of authoring-for-agents (references/writing-principles.md): context pointers, the two loads, information hierarchy/progressi…
- `2026-08-12` **adopt** (2026-10-14-migration:091): Adopted as the structural contract in authoring-for-agents references/skill-anatomy.md: layout, frontmatter rules, recommended body pattern, supporting-file th…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:077) *(superseded)*: The only empirical method for proving a document actually changes behaviour. Chosen as base for that testing loop.
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
