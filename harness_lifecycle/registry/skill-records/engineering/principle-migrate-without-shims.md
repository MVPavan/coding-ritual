---
skill: principle-migrate-without-shims
domain: engineering
stage: Design
substage: Decomposition
secondary: []
family: 
aliases: []
status: active
---
# principle-migrate-without-shims

replacing an internal API no external user depends on, as part of a simplification in a project that can absorb a coordinated break; or running a planned rewrite or migration with declared phase boundaries.

**Boundary:** Replaces an internal API or runs a declared migration without compatibility layers; ordinary unit sequencing is principle-sequence-verifiable-units, and the plan itself is planning.

<!-- registry:generated traits -->
- `same-wave-legacy-removal`: When an internal API with no external dependants is replaced as part of a simplification, in a project that can absorb a coordinated breaking change, migrate every caller and delete the old API in the same change instead of keeping a compatibility layer.
- `migration-group-unit`: Treat an authorized migration group as one verifiable unit: only its declared interior breakage is allowed, and its boundary checks must pass before dependent work proceeds.
- `touched-area-checks`: During a migration, keep fast high-signal checks running on the areas being changed.
- `full-verification-at-completion`: At the end of a planned migration or rewrite, run full static and runtime verification, not only the checks the last change touched.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/principle-migrate-callers-then-delete-legacy-apis#same-wave-legacy-removal** `pstack/skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-outcome-oriented-execution#declared-breakage-window** `pstack/skills/principle-outcome-oriented-execution/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-outcome-oriented-execution#touched-area-checks** `pstack/skills/principle-outcome-oriented-execution/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-outcome-oriented-execution#full-verification-at-completion** `pstack/skills/principle-outcome-oriented-execution/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-05` **update** (2026-11-05-principle-move:007): Owner ruling of 2026-11-05: moved from a skill folder to a file read by path; frontmatter and sidecar removed; the rule text is unchanged; the situation now li…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:164): Completes pending 2026-11-01-cursor_plugins-pstack-principles:095: the principles build (cr-r2pa.1.2) delivered full-verification-at-completion in principle-mi…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:163): Completes pending 2026-11-01-cursor_plugins-pstack-principles:094: the principles build (cr-r2pa.1.2) delivered touched-area-checks in principle-migrate-withou…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:162): Completes pending 2026-11-01-cursor_plugins-pstack-principles:093: the principles build (cr-r2pa.1.2) delivered migration-group-unit in principle-migrate-witho…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:161): Completes pending 2026-11-01-cursor_plugins-pstack-principles:071: the principles build (cr-r2pa.1.2) delivered same-wave-legacy-removal in principle-migrate-w…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:096): Checkpoint at 4dd1d05 for the owner's trait rulings: 3 adopt.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:095) *(superseded)*: Lands as a principle unit. Round 1 matched this to applicable-checks-before-done, but upstream requires full static and runtime verification at plan completion…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:094) *(superseded)*: Lands as a principle unit. Not covered: AGENTS.md runs applicable checks and repeats them for changes (O-05 agrees), but does not keep fast checks running on t…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:093) *(superseded)*: Lands as a conflict (owner ruling), into `migration-group-unit`. Planning already names one integration boundary when tasks cannot stay green; upstream makes d…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:073): Checkpoint at 4dd1d05 for the owner's trait rulings: 2 adopt.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:071) *(superseded)*: Lands as a principle unit. Planning's expand-migrate-contract allows the contraction to trail; codebase-design preserves compatibility and operational constrai…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `full-verification-at-completion`:
  - `cursor_plugins:skill:pstack/skills/principle-outcome-oriented-execution#full-verification-at-completion` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `migration-group-unit`:
  - `cursor_plugins:skill:pstack/skills/principle-outcome-oriented-execution#declared-breakage-window` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `same-wave-legacy-removal`:
  - `cursor_plugins:skill:pstack/skills/principle-migrate-callers-then-delete-legacy-apis#same-wave-legacy-removal` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `touched-area-checks`:
  - `cursor_plugins:skill:pstack/skills/principle-outcome-oriented-execution#touched-area-checks` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
