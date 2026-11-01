---
skill: principle-type-system-discipline
domain: engineering
stage: Design
substage: Architecture
secondary: []
family: 
aliases: []
status: active
---
# principle-type-system-discipline

Apply when designing types or a function signature in a typed language.

**Boundary:** Moves rules into the type checker in a typed language; where raw input becomes typed values is principle-boundary-discipline.

<!-- registry:generated traits -->
- `unrepresentable-invalid-states`: Shape types so the checker rejects impossible states, defining special cases out of existence instead of handling them.
- `exhaustive-variant-handling`: Handle every variant of a closed type so the checker reports a variant left unhandled.
- `branded-primitives`: Give semantically distinct values that share a primitive type their own types, validated once at creation and trusted afterwards.
- `schema-derived-types`: Derive types from the authoritative schema that owns a shape instead of hand-writing a parallel type.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/principle-type-system-discipline#unrepresentable-invalid-states** `pstack/skills/principle-type-system-discipline/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-type-system-discipline#exhaustive-variant-handling** `pstack/skills/principle-type-system-discipline/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-type-system-discipline#branded-primitives** `pstack/skills/principle-type-system-discipline/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-type-system-discipline#schema-derived-types** `pstack/skills/principle-type-system-discipline/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:204): Completes pending 2026-11-01-cursor_plugins-pstack-principles:133: the principles build (cr-r2pa.1.2) delivered schema-derived-types in principle-type-system-d…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:203): Completes pending 2026-11-01-cursor_plugins-pstack-principles:131: the principles build (cr-r2pa.1.2) delivered branded-primitives in principle-type-system-dis…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:202): Completes pending 2026-11-01-cursor_plugins-pstack-principles:130: the principles build (cr-r2pa.1.2) delivered exhaustive-variant-handling in principle-type-s…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:201): Completes pending 2026-11-01-cursor_plugins-pstack-principles:129: the principles build (cr-r2pa.1.2) delivered unrepresentable-invalid-states in principle-typ…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:133) *(superseded)*: Lands as a principle unit. No holder; parallel hand-written types drift.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:131) *(superseded)*: Lands as a principle unit. No holder; cheap in Python (NewType) and catches argument swaps that strict mypy otherwise accepts.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:130) *(superseded)*: Lands as a principle unit. Strict mypy reports an unhandled variant only when dispatch is written to be checked (a closed union with an exhaustiveness check); …
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:129) *(superseded)*: Lands as a principle unit. Ours enforces strict typing and closed schemas but says nothing about designing types so invalid states cannot exist. Split from rou…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `branded-primitives`:
  - `cursor_plugins:skill:pstack/skills/principle-type-system-discipline#branded-primitives` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `exhaustive-variant-handling`:
  - `cursor_plugins:skill:pstack/skills/principle-type-system-discipline#exhaustive-variant-handling` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `schema-derived-types`:
  - `cursor_plugins:skill:pstack/skills/principle-type-system-discipline#schema-derived-types` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `unrepresentable-invalid-states`:
  - `cursor_plugins:skill:pstack/skills/principle-type-system-discipline#unrepresentable-invalid-states` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
