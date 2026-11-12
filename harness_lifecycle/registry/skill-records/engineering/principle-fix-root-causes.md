---
skill: principle-fix-root-causes
domain: engineering
stage: Building
substage: Diagnosis
secondary: []
family:
aliases: []
status: active
---
# principle-fix-root-causes

diagnosing or fixing a failure.

**Boundary:** Says where a failure's cause lies (the why-chain, the legitimate-state test, persisted state after a restart); the diagnosis procedure is systematic-debugging and fixing a reported bug end to end is the bug-fix playbook.

<!-- registry:generated traits -->
- `why-chain`: Ask why at each step of a failure until the answer is a wrong decision in the code rather than a consequence of an earlier one.
- `legitimate-state-test`: Before guarding where a symptom surfaced, decide whether the triggering state is legitimate: handle a legitimate state there, and trace an illegitimate one to what produced it.
- `persisted-state-suspect`: When a failure appears only after a restart, suspect persisted state (configuration, caches, lock files, serialized state) first.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/principle-fix-root-causes#why-chain** `pstack/skills/principle-fix-root-causes/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-fix-root-causes#legitimate-state-test** `pstack/skills/principle-fix-root-causes/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-fix-root-causes#persisted-state-suspect** `pstack/skills/principle-fix-root-causes/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-10` **adopt** (2026-11-10-renames-splits:138): Completes pending 2026-11-10-renames-splits:062: persisted-state-suspect is delivered at .claude/skills/mvp-mode/principles/fix-root-causes.md:13-14, in princi…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:137): Completes pending 2026-11-10-renames-splits:061: legitimate-state-test is delivered at .claude/skills/mvp-mode/principles/fix-root-causes.md:8-12, in principle…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:136): Completes pending 2026-11-10-renames-splits:060: why-chain is delivered at .claude/skills/mvp-mode/principles/fix-root-causes.md:6-7, in principle-fix-root-cau…
- `2026-11-10` **add** (2026-11-10-renames-splits:135): Owner rulings A and B of 2026-11-05 and I2 of 2026-11-06 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 14a U7. Restored with its three rules (B2)…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:062) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner rulings 2026-11-05 §B2 and 2026-11-06 §I2 restore `fix-root-causes` as a principle and mov…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:061) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner rulings 2026-11-05 §B2 and 2026-11-06 §I2 restore `fix-root-causes` as a principle and mov…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:060) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner rulings 2026-11-05 §B2 and 2026-11-06 §I2 restore `fix-root-causes` as a principle and mov…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-09-upstream-cursor_plugins-4dd1d05.md](../../reviews/2026-11-09-upstream-cursor_plugins-4dd1d05.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `legitimate-state-test`:
  - `cursor_plugins:skill:pstack/skills/principle-fix-root-causes#legitimate-state-test` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `persisted-state-suspect`:
  - `cursor_plugins:skill:pstack/skills/principle-fix-root-causes#persisted-state-suspect` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `why-chain`:
  - `cursor_plugins:skill:pstack/skills/principle-fix-root-causes#why-chain` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
