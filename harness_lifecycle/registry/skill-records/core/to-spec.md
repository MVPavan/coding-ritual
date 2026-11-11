---
skill: to-spec
domain: core
stage: Design
substage: Specification
secondary: []
family: spec-authoring
aliases: []
status: active
---
# to-spec

Use when decisions already settled should be written up as a durable spec for planning or another session. Skip choices still open or being compared, which are discovery.

**Boundary:** Writes decisions already settled into a durable spec and gates its approval; exploring or comparing choices still open is discovery, turning an approved multi-phase spec into tracked phases and stages is to-roadmap, a one-phase spec is to-plan then tracker, and its implementation plan is to-plan.

<!-- registry:generated traits -->
- `synthesize-settled`: When the decisions are already settled, synthesize them into a spec without reopening the discussion.
- `spec-template`: Capture the spec in a fixed skeleton: problem, solution, user stories, implementation decisions, testing decisions, out of scope and further notes.
- `spec-criteria-and-questions`: Add success-criteria and open-questions sections to the spec skeleton.
- `none-keeps-heading`: Keep every spec heading, writing None in an empty section so its absence reads as a decision.
- `testing-seam-decision`: Record in the spec which seam the feature is tested at, preferring an existing and the highest useful seam and the fewest seams.
- `no-stale-file-paths`: Keep concrete file paths out of a durable spec, ticket or brief, describing interfaces and behaviour that survive code drift.
- `no-stale-code-snippets`: Keep code snippets out of a durable spec or ticket because they go stale.
- `prototype-snippet`: Inline a prototype snippet in the spec only when it encodes a decision more precisely than prose can.
- `spec-approval-gate`: Keep a spec in draft until explicit authorization names its direction and scope, with any blocking question resolved or moved to out-of-scope first.
- `material-risk-review`: Route an artifact or change with material risk or a broad blast radius through an independent critic review before it is accepted.
- `user-perspective-framing`: Write a spec's problem and solution from the user's perspective.
- `implementation-decisions-scope`: List a spec's implementation decisions across modules, interfaces, clarifications, architecture, schema, contracts and interactions.
- `testing-decisions-contents`: Record a spec's testing decisions as what makes a good test, which modules are tested and the prior-art tests to follow.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/engineering/to-spec#synthesize-settled** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-spec#ground-in-codebase** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-spec#testing-seam-decision** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-spec#spec-template** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-spec#no-stale-file-paths** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-spec#no-stale-code-snippets** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-spec#prototype-snippet** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-spec#user-perspective-framing** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-spec#implementation-decisions-scope** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-spec#testing-decisions-contents** `skills/engineering/to-spec/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#prototype-snippet** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-11` **update** (2026-11-11-discovery:004): Owner ruling L1 of 2026-11-10 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 20 D1. Its description and the open-choice hand-back name discovery f…
- `2026-11-11` **update** (2026-11-11-tracker:014): Owner rulings M2 (2026-11-10), N2 and N3 (2026-11-11) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 27 T1a. The template names tracker as the ski…
- `2026-11-11` **update** (2026-11-10-renames-splits:158): Owner rulings M1, M4 (2026-11-10) and N1, N2 (2026-11-11) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 24 U8r. Hand-off continues into to-roadma…
- `2026-11-10` **update** (2026-11-10-renames-splits:101): Critic-18b F3. references/spec-template.md's consumer line names the epic fields as to-tickets and planning set them: a workstream's phase epics carry the spec…
- `2026-11-10` **update** (2026-11-10-renames-splits:097): Owner ruling C of 2026-11-05 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 14a U4 (plan section 5.1, R8). references/spec-template.md's consumer …
- `2026-11-10` **update** (2026-11-10-renames-splits:084): critic-17b F1: to-spec/SKILL.md:15 reads what the spec must describe, not what distinguishes the live choices, so it does not deliver scoped-context-read and c…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:081): Completes pending 2026-11-10-renames-splits:018: prototype-snippet is delivered at .claude/skills/to-spec/references/spec-template.md:60, moved unchanged with …
- `2026-11-10` **adopt** (2026-11-10-renames-splits:080): Completes pending 2026-11-10-renames-splits:010: testing-decisions-contents is delivered at .claude/skills/to-spec/references/spec-template.md:79-81, moved unc…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:079): Completes pending 2026-11-10-renames-splits:009: implementation-decisions-scope is delivered at .claude/skills/to-spec/references/spec-template.md:42-45, moved…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:078): Completes pending 2026-11-10-renames-splits:008: user-perspective-framing is delivered at .claude/skills/to-spec/references/spec-template.md:21-22, .claude/ski…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:077): Completes pending 2026-11-10-renames-splits:007: prototype-snippet is delivered at .claude/skills/to-spec/references/spec-template.md:60, moved unchanged with …
- `2026-11-10` **adopt** (2026-11-10-renames-splits:076): Completes pending 2026-11-10-renames-splits:006: no-stale-code-snippets is delivered at .claude/skills/to-spec/references/spec-template.md:58, moved unchanged …
- `2026-11-10` **adopt** (2026-11-10-renames-splits:075): Completes pending 2026-11-10-renames-splits:005: no-stale-file-paths is delivered at .claude/skills/to-spec/references/spec-template.md:58-59, moved unchanged …
- `2026-11-10` **adopt** (2026-11-10-renames-splits:074): Completes pending 2026-11-10-renames-splits:004: spec-template is delivered at .claude/skills/to-spec/SKILL.md:19-20, .claude/skills/to-spec/references/spec-te…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:073): Completes pending 2026-11-10-renames-splits:003: testing-seam-decision is delivered at .claude/skills/to-spec/references/spec-template.md:75-77, moved unchange…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:072) *(superseded)*: Completes pending 2026-11-10-renames-splits:002: scoped-context-read is delivered at .claude/skills/to-spec/SKILL.md:15, moved unchanged with the spec section …
- `2026-11-10` **adopt** (2026-11-10-renames-splits:071): Completes pending 2026-11-10-renames-splits:001: synthesize-settled is delivered at .claude/skills/to-spec/SKILL.md:12-14, moved unchanged with the spec sectio…
- `2026-11-10` **add** (2026-11-10-renames-splits:068): Owner ruling C of 2026-11-05 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 14a U3. New skill: writes decisions already settled into a durable spe…
- `2026-11-10` **adopt-merged** (2026-11-10-renames-splits:064): Checkpoint at 5beb35b after the renames-splits rulings: 10 adopt, 6 defer; adopts now land in to-spec.
- `2026-11-10` **adopt** (2026-11-10-renames-splits:018) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C: its delivery already sits in the spec template `brainstorming` hands…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:010) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `to-spec` out of `brainstorming`, which ends at decisions; the…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:009) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `to-spec` out of `brainstorming`, which ends at decisions; the…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:008) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `to-spec` out of `brainstorming`, which ends at decisions; the…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:007) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `to-spec` out of `brainstorming`, which ends at decisions; the…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:006) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `to-spec` out of `brainstorming`, which ends at decisions; the…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:005) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `to-spec` out of `brainstorming`, which ends at decisions; the…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:004) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `to-spec` out of `brainstorming`, which ends at decisions; the…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:003) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `to-spec` out of `brainstorming`, which ends at decisions; the…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:002) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `to-spec` out of `brainstorming`, which ends at decisions; the…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:001) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `to-spec` out of `brainstorming`, which ends at decisions; the…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-09-upstream-mattpocock_skills-5beb35b.md](../../reviews/2026-11-09-upstream-mattpocock_skills-5beb35b.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `implementation-decisions-scope`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#implementation-decisions-scope` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `no-stale-code-snippets`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#no-stale-code-snippets` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `no-stale-file-paths`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#no-stale-file-paths` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `prototype-snippet`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#prototype-snippet` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/engineering/to-tickets#prototype-snippet` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `scoped-context-read`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#ground-in-codebase` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-10)
- `spec-template`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#spec-template` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `synthesize-settled`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#synthesize-settled` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `testing-decisions-contents`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#testing-decisions-contents` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `testing-seam-decision`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#testing-seam-decision` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `user-perspective-framing`:
  - `mattpocock_skills:skill:skills/engineering/to-spec#user-perspective-framing` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
