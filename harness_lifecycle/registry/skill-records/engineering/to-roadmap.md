---
skill: to-roadmap
domain: engineering
stage: Design
substage: Decomposition
secondary: []
family: plan-authoring
aliases: []
status: active
---
# to-roadmap

Use when an approved multi-phase spec should become tracked work: its phases, stages with acceptance and their order, for a new workstream or extending one; tracker seeds them. A one-phase spec is to-plan, then tracker; the plan for one phase is to-plan; a person's request to plan the work is the plan playbook, which calls this.

**Boundary:** Turns an approved multi-phase spec into phases and stages with acceptance, their order and real dependency edges, for a new workstream or extending an existing one, approved before tracker seeds them; a one-phase spec is to-plan then tracker, ordering the stages is principle-sequence-verifiable-units, writing the implementation plan for one phase or one change is to-plan, and writing the spec itself is to-spec.

<!-- registry:generated traits -->
- `decompose-phases`: Split an approved spec into demoable phases with checkable exits and flat stages that each carry acceptance.
- `breakdown-approval-before-publish`: Iterate on the ticket breakdown until the user approves it, publishing nothing before approval.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/engineering/to-tickets#prefactor-first** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#vertical-slices** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#dependency-edges** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#expand-contract** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#publish-to-tracker** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#real-id-wiring** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#sub-issue-linkage** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#blast-radius-batches** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#breakdown-approval-before-publish** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-11` **update** (2026-11-11-plan-playbook:010): Owner ruling N4 of 2026-11-11 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md:126), plan 45 U2 (scratchpad/mvp-stack/45/plan.md): a one-phase spec is rout…
- `2026-11-11` **update** (2026-11-11-implement-playbook:008): Owner ruling N4 of 2026-11-11 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md:126), plan 40 U2 (scratchpad/mvp-stack/40/plan.md): the roadmap's risk field…
- `2026-11-11` **update** (2026-11-11-tracker:008): Owner rulings M2 (2026-11-10), N2 and N3 (2026-11-11) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 27 T1a. R2: an approved multi-phase spec only…
- `2026-11-11` **update** (2026-11-10-renames-splits:152): Owner rulings M1, M4 (2026-11-10) and N1, N2 (2026-11-11) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 24 U8r. Name, heading and description (an…
- `2026-11-11` **rename** (2026-11-10-renames-splits:145): Owner rulings M1, M4 (2026-11-10) and N1, N2 (2026-11-11) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 24 U8r. to-tickets is renamed to-roadmap:…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:096): Completes pending 2026-11-10-renames-splits:020: breakdown-approval-before-publish is delivered at .claude/skills/to-tickets/SKILL.md:34, .claude/skills/to-tic…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:095) *(superseded)*: Completes pending 2026-11-10-renames-splits:019: blast-radius-batches is delivered at .claude/skills/to-tickets/SKILL.md:28-29, moved with planning's Decompose…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:094) *(superseded)*: Completes pending 2026-11-10-renames-splits:017: beads-native-tracking is delivered at .claude/skills/to-tickets/references/decompose.md:56-74, moved with plan…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:093) *(superseded)*: Completes pending 2026-11-10-renames-splits:016: real-id-wiring is delivered at .claude/skills/to-tickets/references/decompose.md:75-76, moved with planning's …
- `2026-11-10` **adopt** (2026-11-10-renames-splits:092) *(superseded)*: Completes pending 2026-11-10-renames-splits:015: beads-native-tracking is delivered at .claude/skills/to-tickets/SKILL.md:34-35, .claude/skills/to-tickets/refe…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:091) *(superseded)*: Completes pending 2026-11-10-renames-splits:014: expand-contract is delivered at .claude/skills/to-tickets/SKILL.md:27-30, moved with planning's Decompose and …
- `2026-11-10` **adopt** (2026-11-10-renames-splits:090) *(superseded)*: Completes pending 2026-11-10-renames-splits:013: dependency-edges is delivered at .claude/skills/to-tickets/SKILL.md:20-21, .claude/skills/to-tickets/reference…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:089) *(superseded)*: Completes pending 2026-11-10-renames-splits:012: vertical-slices is delivered at .claude/skills/to-tickets/SKILL.md:26, moved with planning's Decompose and Sli…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:088) *(superseded)*: Completes pending 2026-11-10-renames-splits:011: prefactor-first is delivered at .claude/skills/to-tickets/SKILL.md:26-27, moved with planning's Decompose and …
- `2026-11-10` **add** (2026-11-10-renames-splits:085): Owner ruling C of 2026-11-05 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 14a U4. New skill: splits an approved spec into tracked phases and sta…
- `2026-11-10` **adopt-merged** (2026-11-10-renames-splits:065): Checkpoint at 5beb35b after the renames-splits rulings: 13 adopt, 10 defer; adopts now land in to-tickets.
- `2026-11-10` **adopt** (2026-11-10-renames-splits:020) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `to-tickets` out of `planning`, which keeps the plan document,…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:019) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `to-tickets` out of `planning`, which keeps the plan document,…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:017) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `to-tickets` out of `planning`, which keeps the plan document,…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:016) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `to-tickets` out of `planning`, which keeps the plan document,…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:015) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `to-tickets` out of `planning`, which keeps the plan document,…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:014) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `to-tickets` out of `planning`, which keeps the plan document,…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:013) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `to-tickets` out of `planning`, which keeps the plan document,…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:012) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `to-tickets` out of `planning`, which keeps the plan document,…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:011) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `to-tickets` out of `planning`, which keeps the plan document,…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-09-upstream-mattpocock_skills-5beb35b.md](../../reviews/2026-11-09-upstream-mattpocock_skills-5beb35b.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `beads-native-tracking`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#publish-to-tracker` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-11)
  - `mattpocock_skills:skill:skills/engineering/to-tickets#sub-issue-linkage` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-11)
- `blast-radius-batches`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#blast-radius-batches` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-11)
- `breakdown-approval-before-publish`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#breakdown-approval-before-publish` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `dependency-edges`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#dependency-edges` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-11)
- `expand-contract`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#expand-contract` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-11)
- `prefactor-first`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#prefactor-first` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-11)
- `real-id-wiring`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#real-id-wiring` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-11)
- `vertical-slices`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#vertical-slices` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-11)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
