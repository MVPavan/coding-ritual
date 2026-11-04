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

Use when creating or changing agent instructions or their activation behavior. Skip edits that only correct spelling or formatting.

**Boundary:** Writes or changes our own agent instructions and their triggers; judging upstream capabilities is the harness-* skills, and porting assets to Codex is migrate-claude-to-codex.

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
- `decision-relevance-pruning`: Keep only content that changes the agent's decisions, such as conventions, non-obvious failure modes, required interfaces and invariants.
- `no-op-deletion`: Delete instructions the model already follows by default.
- `unsupported-claim-removal`: Remove unsupported claims and invented thresholds from instructions.
- `skill-packaging`: Keep one canonical directory per workflow with a SKILL.md, adding references only for substantial conditional material and scripts for reusable mechanical work.
- `invocation-mode`: Choose model-invoked or user-invoked activation, setting the disable-model-invocation flag for manual workflows.
- `invocation-sidecar-sync`: Pair the manual-invocation flag with the provider's implicit-invocation policy and regenerate the catalog and sidecars together after metadata edits.
- `compatibility-alias`: Keep a manual or legacy entrypoint as a thin pointer that delegates to the canonical owner, not as an independent workflow others auto-activate.
- `verification`: Inspect the diff for lost contracts, scale fresh-context and pressure trials to behavioural risk, and report unavailable behavioural checks as a limit instead of manufacturing evidence.
- `mechanical-vs-judgement`: Classify each finding as mechanical (a fixed syntactic pattern suiting a deterministic check) or judgement (cross-file consistency suiting a standards doc).
- `extend-existing-docs-first`: Prefer extending existing pointed-to documents before writing new ones.
- `check-pointer-not-restatement`: Once a check enforces a rule, replace the instruction that restated it with a pointer to the check.
- `judgement-lesson-failure-example`: When a recurring lesson needs judgement and cannot be checked, revise the instruction it implicates and add one example of the failure, rather than repeating or emphasising the rule.
- `build-check-over-rule`: Default to building a deterministic check over writing a prose rule for any mechanical finding. (Delivers sealed row 2026-10-30-mattpocock_skills-5beb35b:463: propose a new check before a prose rule and build it where authorized, where the definition defaults to building; T5.)
- `co-location`: Keep a concept's definition, rules and caveats under one heading so reading one part brings its neighbours.
- `completion-criteria-demand`: Phrase the criterion to demand thorough work, driving the legwork latent in its wording.
- `one-trigger-per-branch`: Give each trigger branch of a pointer one trigger, collapsing synonyms.
- `pointer-identity-trim`: Cut from a pointer any identity the target's own body already carries.
- `relevance-check`: Check every line still bears on the document's task, pruning stale or irrelevant ones. (Delivers sealed row 2026-10-30-mattpocock_skills-5beb35b:545: drops lines gone stale, where the definition checks every line; T5.)
- `sharpen-before-inline`: Fix a weakly reached must-have target by sharpening its pointer's wording first, inlining it only if that fails.
- `split-by-invocation`: Split off a model-invoked skill only when a distinct leading word should trigger it or another skill must reach it. (Delivers sealed row 2026-10-30-mattpocock_skills-5beb35b:539: a distinct trigger, where the definition says a distinct leading word; T5.)
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **superpowers:skill:skills/writing-skills** `reference_harnesses/superpowers/skills/writing-skills/SKILL.md` @ 44c9b2d
  - merged from: writing-for-agents
  - modified: absorb the information ladder, the two-loads model, pointer wording, the no-op test and negation scoping — the vocabulary for deciding what goes where
- **agent-skills:doc:docs/skill-anatomy.md**
- **superpowers:skill:skills/writing-skills** `skills/writing-skills/SKILL.md`
  - merged from: writing-for-agents
  - modified: absorb the information ladder, the two-loads model, pointer wording, the no-op test and negation scoping — the vocabulary for deciding what goes where
- **mattpocock_skills:skill:skills/productivity/writing-for-agents#context-pointers** `skills/productivity/writing-for-agents/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/writing-for-agents#two-loads** `skills/productivity/writing-for-agents/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/writing-for-agents#inline-vs-disclose** `skills/productivity/writing-for-agents/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/writing-for-agents#completion-criteria-clarity** `skills/productivity/writing-for-agents/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/writing-for-agents#single-source-of-truth** `skills/productivity/writing-for-agents/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/writing-for-agents#environment-as-cache** `skills/productivity/writing-for-agents/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/writing-for-agents#no-op-deletion** `skills/productivity/writing-for-agents/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/writing-for-agents#invocation-mode** `skills/productivity/writing-for-agents/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/writing-for-agents#model-facing-description** `skills/productivity/writing-for-agents/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/writing-for-agents#human-facing-description** `skills/productivity/writing-for-agents/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.1)
- **mattpocock_skills:skill:skills/productivity/writing-for-agents#external-shared-reference** `skills/productivity/writing-for-agents/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/writing-for-agents#empirical-instruction-default-check** `skills/productivity/writing-for-agents/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/retro#mechanical-vs-judgement** `skills/engineering/retro/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/retro#extend-existing-docs-first** `skills/engineering/retro/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **cursor_plugins:skill:pstack/skills/principle-encode-lessons-in-structure#judgement-lesson-example** `pstack/skills/principle-encode-lessons-in-structure/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-encode-lessons-in-structure#structural-fix-only** `pstack/skills/principle-encode-lessons-in-structure/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **mattpocock_skills:skill:skills/engineering/retro#build-check-over-rule** `skills/engineering/retro/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/writing-for-agents#co-location** `skills/productivity/writing-for-agents/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/writing-for-agents#completion-criteria-demand** `skills/productivity/writing-for-agents/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/writing-for-agents#one-trigger-per-branch** `skills/productivity/writing-for-agents/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/writing-for-agents#pointer-identity-trim** `skills/productivity/writing-for-agents/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/writing-for-agents#relevance-check** `skills/productivity/writing-for-agents/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/writing-for-agents#sharpen-before-inline** `skills/productivity/writing-for-agents/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/writing-for-agents#split-by-invocation** `skills/productivity/writing-for-agents/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-04` **defer** (2026-11-04-pocock-pass:040): Owner ruling 2026-11-04: cancels the pending adoption and defers it to the end-of-project revision pass (cr-r2pa.3.4), which owns description wording. The trai…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:008): Completes pending 2026-10-30-mattpocock_skills-5beb35b:539: split-by-invocation is written at .claude/skills/authoring-for-agents/SKILL.md:25-27, in the sealed…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:007): Completes pending 2026-10-30-mattpocock_skills-5beb35b:550: sharpen-before-inline is written at .claude/skills/authoring-for-agents/SKILL.md:56-58, in the seal…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:006): Completes pending 2026-10-30-mattpocock_skills-5beb35b:545: relevance-check is written at .claude/skills/authoring-for-agents/references/writing-principles.md:…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:005): Completes pending 2026-10-30-mattpocock_skills-5beb35b:552: pointer-identity-trim is written at .claude/skills/authoring-for-agents/SKILL.md:34-35, in the seal…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:004): Completes pending 2026-10-30-mattpocock_skills-5beb35b:551: one-trigger-per-branch is written at .claude/skills/authoring-for-agents/references/skill-anatomy.m…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:003): Completes pending 2026-10-30-mattpocock_skills-5beb35b:538: completion-criteria-demand is written at .claude/skills/authoring-for-agents/references/writing-pri…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:002): Completes pending 2026-10-30-mattpocock_skills-5beb35b:536: co-location is written at .claude/skills/authoring-for-agents/references/writing-principles.md:12-1…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:001): Completes pending 2026-10-30-mattpocock_skills-5beb35b:463: build-check-over-rule is written at .claude/skills/authoring-for-agents/SKILL.md:20, in the sealed …
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:220): Completes pending 2026-11-01-cursor_plugins-pstack-principles:021: the principles build (cr-r2pa.1.2) delivered check-pointer-not-restatement in authoring-for-…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:219): Completes pending 2026-11-01-cursor_plugins-pstack-principles:020: the principles build (cr-r2pa.1.2) delivered judgement-lesson-failure-example in authoring-f…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:022): Checkpoint at 4dd1d05 for the owner's trait rulings: 3 adopt.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:021) *(superseded)*: Lands as a skill or playbook trait, into `check-pointer-not-restatement`. unit-kinds rule 2 already says prose only points to a check that decides the rule, bu…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:020) *(superseded)*: Lands as a skill or playbook trait, into `judgement-lesson-failure-example`. Ours prefers one effective instruction and revises the smallest instruction implic…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:588): Owner 2026-10-30 approved the list fix: ours:authoring-for-agents now lists the trait.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:587): Owner 2026-10-30 approved the list fix: ours:authoring-for-agents now lists the trait.
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:586): Checkpoint at 5beb35b for the owner's trait rulings: 19 adopt, 8 defer.
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:583): Checkpoint at 5beb35b for the owner's trait rulings: 3 adopt, 10 defer.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:559): Deliberate: ours already says a prose review cannot prove obedience (.claude/skills/authoring-for-agents/references/testing-docs.md:3-4) and sizes trials to ri…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:557): Deliberate: one surface rule covers every reader, the user-invoked case included.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:556) *(superseded)*: Ours writes every description as an activation boundary (.claude/skills/authoring-for-agents/references/skill-anatomy.md:9-12), though a manual skill's descrip…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:555): Deliberate: naming the nearest competing case keeps descriptions from competing (S-01).
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:554): Owner deferred the report's reject recommendation, to review the set later: Ours lets familiar terms compress (.claude/skills/authoring-for-agents/references/w…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:552) *(superseded)*: Ours stops a description duplicating the workflow but not restating the skill's identity; extending the same line closes it.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:551) *(superseded)*: Ours requires a concise description naming the activation boundary (.claude/skills/authoring-for-agents/references/skill-anatomy.md:9-12) but does not collapse…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:550) *(superseded)*: Ours revises the smallest implicated instruction (.claude/skills/authoring-for-agents/SKILL.md:49-50) but gives no order between rewording a pointer and inlini…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:549): Owner deferred the report's reject recommendation, to review the set later: Ours's skill-router already lists every slash-only workflow from the generated cata…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:548): Owner deferred the report's reject recommendation, to review the set later: Ours deliberately sends a convention needed for particular work to a project docume…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:547): Ours sets disable-model-invocation for manual workflows and aliases.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:546): Ours removes generic advice that adds no behaviour.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:545) *(superseded)*: Ours keeps decision-changing content but has no staleness pass; U-08 asks to remove instructions whose benefit no longer holds.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:544): Ours links authoritative commands and configuration instead of copying volatile facts.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:543): Ours avoids duplicate policy owners and searches for an existing owner before adding another.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:542): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours imposes no universal positive-first, prohibition-last-resort …
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:541): Owner deferred the report's reject recommendation, to review the set later: Ours keeps the compression point (familiar terms compress; coined labels need defin…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:539) *(superseded)*: Ours chooses the surface (.claude/skills/authoring-for-agents/SKILL.md:17-18) and the invocation mode (.claude/skills/authoring-for-agents/references/skill-ana…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:538) *(superseded)*: Ours makes criteria checkable (.claude/skills/authoring-for-agents/references/writing-principles.md:17) but not exhaustive; stating the coverage bar is what S-…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:537): Ours asks for observable conditions and checkable completion criteria.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:536) *(superseded)*: Ours avoids duplicate owners (.claude/skills/authoring-for-agents/references/writing-principles.md:11) but says nothing about one meaning scattered across a fi…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:535): Ours inlines the common contract and links branch-specific material at the branch.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:534): Ours weighs discovery context against the name a user must remember, judged by the full read path.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:533): Ours's pointer names the material and the condition for reading it, trigger first.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:472) *(superseded)*: Ours already says to search for an existing owner before adding another (.claude/skills/authoring-for-agents/SKILL.md:22); the adopt is pending only because au…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:463) *(superseded)*: Ours routes deterministic enforcement only to an existing hook or check (.claude/skills/authoring-for-agents/SKILL.md:20); proposing a new check before a prose…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:462) *(superseded)*: Ours's surface table already sends deterministic enforcement to a hook or check and conventions to a project document (.claude/skills/authoring-for-agents/SKIL…
- `2026-08-12` **adopt-merged** (2026-10-14-migration:114): Adopted as one third of authoring-for-agents: Match-the-Form-to-the-Failure table, description-never-summarizes-workflow rule, rationalization tables/red flags…
- `2026-08-12` **adopt** (2026-10-14-migration:108): Adopted as the writing-theory core of authoring-for-agents (references/writing-principles.md): context pointers, the two loads, information hierarchy/progressi…
- `2026-08-12` **adopt** (2026-10-14-migration:091): Adopted as the structural contract in authoring-for-agents references/skill-anatomy.md: layout, frontmatter rules, recommended body pattern, supporting-file th…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:077) *(superseded)*: The only empirical method for proving a document actually changes behaviour. Chosen as base for that testing loop.
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `activation-boundary`:
  - `mattpocock_skills:skill:skills/productivity/writing-for-agents#model-facing-description` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `build-check-over-rule`:
  - `mattpocock_skills:skill:skills/engineering/retro#build-check-over-rule` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `check-pointer-not-restatement`:
  - `cursor_plugins:skill:pstack/skills/principle-encode-lessons-in-structure#structural-fix-only` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `co-location`:
  - `mattpocock_skills:skill:skills/productivity/writing-for-agents#co-location` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `completion-criteria-clarity`:
  - `mattpocock_skills:skill:skills/productivity/writing-for-agents#completion-criteria-clarity` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `completion-criteria-demand`:
  - `mattpocock_skills:skill:skills/productivity/writing-for-agents#completion-criteria-demand` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `context-pointers`:
  - `mattpocock_skills:skill:skills/productivity/writing-for-agents#context-pointers` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `environment-as-cache`:
  - `mattpocock_skills:skill:skills/productivity/writing-for-agents#environment-as-cache` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `extend-existing-docs-first`:
  - `mattpocock_skills:skill:skills/engineering/retro#extend-existing-docs-first` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `inline-vs-disclose`:
  - `mattpocock_skills:skill:skills/productivity/writing-for-agents#inline-vs-disclose` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `invocation-mode`:
  - `mattpocock_skills:skill:skills/productivity/writing-for-agents#invocation-mode` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `judgement-lesson-failure-example`:
  - `cursor_plugins:skill:pstack/skills/principle-encode-lessons-in-structure#judgement-lesson-example` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `mechanical-vs-judgement`:
  - `mattpocock_skills:skill:skills/engineering/retro#mechanical-vs-judgement` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `no-op-deletion`:
  - `mattpocock_skills:skill:skills/productivity/writing-for-agents#no-op-deletion` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `one-trigger-per-branch`:
  - `mattpocock_skills:skill:skills/productivity/writing-for-agents#one-trigger-per-branch` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `pointer-identity-trim`:
  - `mattpocock_skills:skill:skills/productivity/writing-for-agents#pointer-identity-trim` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `relevance-check`:
  - `mattpocock_skills:skill:skills/productivity/writing-for-agents#relevance-check` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `sharpen-before-inline`:
  - `mattpocock_skills:skill:skills/productivity/writing-for-agents#sharpen-before-inline` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `single-source-of-truth`:
  - `mattpocock_skills:skill:skills/productivity/writing-for-agents#single-source-of-truth` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `split-by-invocation`:
  - `mattpocock_skills:skill:skills/productivity/writing-for-agents#split-by-invocation` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `surface-choice`:
  - `mattpocock_skills:skill:skills/productivity/writing-for-agents#external-shared-reference` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `two-loads`:
  - `mattpocock_skills:skill:skills/productivity/writing-for-agents#two-loads` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `verification`:
  - `mattpocock_skills:skill:skills/productivity/writing-for-agents#empirical-instruction-default-check` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
- `mattpocock_skills:skill:skills/productivity/writing-for-agents#human-facing-description` (defer): Owner ruling 2026-11-04: cancels the pending adoption and defers it to the end-of-project revision pass (cr-r2pa.3.4), which owns description wording. The trai…
- `mattpocock_skills:skill:skills/productivity/writing-for-agents#leading-words` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours keeps the compression point (familiar terms compress; coined labels need defin…
- `mattpocock_skills:skill:skills/productivity/writing-for-agents#negation-avoidance` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours imposes no universal positive-first, prohibition-last-resort …
- `mattpocock_skills:skill:skills/productivity/writing-for-agents#router-skills` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours's skill-router already lists every slash-only workflow from the generated cata…
- `mattpocock_skills:skill:skills/productivity/writing-for-agents#shared-reference-home` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours deliberately sends a convention needed for particular work to a project docume…
- `mattpocock_skills:skill:skills/productivity/writing-for-agents#triad-collapse` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours lets familiar terms compress (.claude/skills/authoring-for-agents/references/w…
<!-- /registry:generated declined -->
