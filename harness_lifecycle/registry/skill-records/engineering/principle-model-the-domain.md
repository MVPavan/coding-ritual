---
skill: principle-model-the-domain
domain: engineering
stage: Design
substage: Architecture
secondary: []
family:
aliases: []
status: active
---
# principle-model-the-domain

writing stateful logic, a growing if/else chain, or a shape assumption repeated across files.

**Boundary:** Chooses data structures and module boundaries around domain knowledge before logic; domain terms and ADRs are domain-modeling, and interface depth is codebase-design.

<!-- registry:generated traits -->
- `data-shape-first`: Settle the core types and data structures, traced against every access pattern, before writing the logic that uses them.
- `structure-over-conditionals`: Encode domain rules in a fitting data structure (state machine, typed model, lookup table, union, reducer) instead of conditionals scattered across the code.
- `knowledge-not-phase-modules`: Organise modules around one body of domain knowledge, not around execution phases such as load, validate, transform and save.
- `coherent-increment`: Make each increment land or deepen one coherent abstraction instead of spreading a new capability across callers as special-case coordination.
- `structural-dry`: Deduplicate structure such as types and data models, but tolerate a few similar statements rather than a premature abstraction.
- `no-forced-abstraction`: Keep boring code that is clear, local and unlikely to grow, adding indirection only when it removes branches, duplicated rules, invalid states or lifecycle risk.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/principle-foundational-thinking#data-shape-first** `pstack/skills/principle-foundational-thinking/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-model-the-domain#structure-over-conditionals** `pstack/skills/principle-model-the-domain/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-model-the-domain#knowledge-not-phase-modules** `pstack/skills/principle-model-the-domain/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-foundational-thinking#coherent-increment** `pstack/skills/principle-foundational-thinking/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-foundational-thinking#structural-dry** `pstack/skills/principle-foundational-thinking/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-model-the-domain#no-forced-abstraction** `pstack/skills/principle-model-the-domain/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-05` **update** (2026-11-05-principle-move:009): Owner ruling of 2026-11-05: moved from a skill folder to a file read by path; frontmatter and sidecar removed; the rule text is unchanged; the situation now li…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:176): Completes pending 2026-11-01-cursor_plugins-pstack-principles:087: the principles build (cr-r2pa.1.2) delivered no-forced-abstraction in principle-model-the-do…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:175): Completes pending 2026-11-01-cursor_plugins-pstack-principles:050: the principles build (cr-r2pa.1.2) delivered structural-dry in principle-model-the-domain, c…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:174): Completes pending 2026-11-01-cursor_plugins-pstack-principles:056: the principles build (cr-r2pa.1.2) delivered coherent-increment in principle-model-the-domai…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:173): Completes pending 2026-11-01-cursor_plugins-pstack-principles:086: the principles build (cr-r2pa.1.2) delivered knowledge-not-phase-modules in principle-model-…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:172): Completes pending 2026-11-01-cursor_plugins-pstack-principles:085: the principles build (cr-r2pa.1.2) delivered structure-over-conditionals in principle-model-…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:171): Completes pending 2026-11-01-cursor_plugins-pstack-principles:049: the principles build (cr-r2pa.1.2) delivered data-shape-first in principle-model-the-domain,…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:088): Checkpoint at 4dd1d05 for the owner's trait rulings: 3 adopt.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:087) *(superseded)*: Lands as a principle unit. AGENTS.md requires a present need for an abstraction; it does not say what indirection must remove or to keep boring local code bori…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:086) *(superseded)*: Lands as a principle unit. No holder; temporal decomposition is a common agent failure and the sign is checkable.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:085) *(superseded)*: Lands as a principle unit. No holder; our prototype skill keeps logic pure (logic-pure-module) only for prototypes.
- `2026-11-01` **adopt-merged** (2026-11-01-cursor_plugins-pstack-principles:058): Checkpoint at 4dd1d05 for the owner's trait rulings: 7 adopt, 1 reject, 1 defer.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:056) *(superseded)*: Lands as a principle unit. codebase-design asks what complexity leaves callers; it never forbids spreading a capability across them as special cases.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:050) *(superseded)*: Lands as a principle unit. AGENTS.md bans speculative abstractions; this adds what to deduplicate (types, models) and tolerates repeated statements.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:049) *(superseded)*: Lands as a principle unit. No holder; belongs with model-the-domain, whose lens is the same decision (choose the structure before the logic).
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `coherent-increment`:
  - `cursor_plugins:skill:pstack/skills/principle-foundational-thinking#coherent-increment` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `data-shape-first`:
  - `cursor_plugins:skill:pstack/skills/principle-foundational-thinking#data-shape-first` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `knowledge-not-phase-modules`:
  - `cursor_plugins:skill:pstack/skills/principle-model-the-domain#knowledge-not-phase-modules` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `no-forced-abstraction`:
  - `cursor_plugins:skill:pstack/skills/principle-model-the-domain#no-forced-abstraction` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `structural-dry`:
  - `cursor_plugins:skill:pstack/skills/principle-foundational-thinking#structural-dry` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `structure-over-conditionals`:
  - `cursor_plugins:skill:pstack/skills/principle-model-the-domain#structure-over-conditionals` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
