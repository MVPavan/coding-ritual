---
skill: principle-minimize-reader-load
domain: engineering
stage: Design
substage: Architecture
secondary: []
family: 
aliases: []
status: active
---
# principle-minimize-reader-load

Apply when reviewing or shaping code that is hard to trace.

**Boundary:** Judges code by the layers and state a reader must trace; module interface decisions are codebase-design.

<!-- registry:generated traits -->
- `reader-load-axes`: Judge maintainability by the layers a reader must trace and the state they must hold, not by line counts, complexity scores or architecture labels.
- `reader-load-net-test`: Before adding a layer or a piece of state, check that it removes at least as much reader load elsewhere as it adds.
- `collapse-thin-layers`: Inline layers that cost more than they save, such as one-caller wrappers, adapters with no second implementation and speculative indirection.
- `narrowest-state-scope`: Give state the narrowest scope that works: locals over fields over module state over globals.
- `derive-over-sync`: Derive a value from its source when needed instead of storing a copy that must be kept in sync.
- `invariant-at-boundary`: Name an invariant once, at the boundary that owns it, rather than in every consumer.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/principle-minimize-reader-load#reader-load-axes** `pstack/skills/principle-minimize-reader-load/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-minimize-reader-load#reader-load-net-test** `pstack/skills/principle-minimize-reader-load/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-minimize-reader-load#collapse-thin-layers** `pstack/skills/principle-minimize-reader-load/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-minimize-reader-load#narrowest-state-scope** `pstack/skills/principle-minimize-reader-load/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-minimize-reader-load#derive-over-sync** `pstack/skills/principle-minimize-reader-load/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-minimize-reader-load#invariant-at-boundary** `pstack/skills/principle-minimize-reader-load/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:170): Completes pending 2026-11-01-cursor_plugins-pstack-principles:081: the principles build (cr-r2pa.1.2) delivered invariant-at-boundary in principle-minimize-rea…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:169): Completes pending 2026-11-01-cursor_plugins-pstack-principles:080: the principles build (cr-r2pa.1.2) delivered derive-over-sync in principle-minimize-reader-l…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:168): Completes pending 2026-11-01-cursor_plugins-pstack-principles:079: the principles build (cr-r2pa.1.2) delivered narrowest-state-scope in principle-minimize-rea…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:167): Completes pending 2026-11-01-cursor_plugins-pstack-principles:075: the principles build (cr-r2pa.1.2) delivered collapse-thin-layers in principle-minimize-read…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:166): Completes pending 2026-11-01-cursor_plugins-pstack-principles:082: the principles build (cr-r2pa.1.2) delivered reader-load-net-test in principle-minimize-read…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:165): Completes pending 2026-11-01-cursor_plugins-pstack-principles:074: the principles build (cr-r2pa.1.2) delivered reader-load-axes in principle-minimize-reader-l…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:082) *(superseded)*: Lands as a principle unit. AGENTS.md asks whether a need exists now; this asks whether the layer removes at least as much reader load as it adds. Round 1 mappe…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:081) *(superseded)*: Lands as a principle unit. codebase-design counts invariants as part of the interface but does not say to name each once at the owning boundary. The definition…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:080) *(superseded)*: Lands as a principle unit. Ours keeps one owner for instruction meaning (single-source-of-truth, in authoring-for-agents) but nothing forbids storing a runtime…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:079) *(superseded)*: Lands as a principle unit. Ours freezes models by default (coding-style.md) but says nothing about where state lives. Split from round 1's state-scope-shrink, …
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:075) *(superseded)*: Lands as a principle unit. Adopted unchanged, with its cost condition. Upstream collapses layers that cost more than they save and names an adapter with no sec…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:074) *(superseded)*: Lands as a principle unit. No holder; gives review two named axes (layers to trace, state to hold) instead of taste. The timed probe is a separate row.
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `collapse-thin-layers`:
  - `cursor_plugins:skill:pstack/skills/principle-minimize-reader-load#collapse-thin-layers` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `derive-over-sync`:
  - `cursor_plugins:skill:pstack/skills/principle-minimize-reader-load#derive-over-sync` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `invariant-at-boundary`:
  - `cursor_plugins:skill:pstack/skills/principle-minimize-reader-load#invariant-at-boundary` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `narrowest-state-scope`:
  - `cursor_plugins:skill:pstack/skills/principle-minimize-reader-load#narrowest-state-scope` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `reader-load-axes`:
  - `cursor_plugins:skill:pstack/skills/principle-minimize-reader-load#reader-load-axes` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `reader-load-net-test`:
  - `cursor_plugins:skill:pstack/skills/principle-minimize-reader-load#reader-load-net-test` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
