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

designing types or a function signature in a typed language.

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
- **cursor_plugins:skill:pstack/skills/typescript-best-practices#branded-primitives** `pstack/skills/typescript-best-practices/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/typescript-best-practices#unrepresentable-invalid-states** `pstack/skills/typescript-best-practices/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/typescript-best-practices#brand-only-on-confusion-risk** `pstack/skills/typescript-best-practices/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/typescript-best-practices#simplest-total-type** `pstack/skills/typescript-best-practices/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/typescript-best-practices#weaken-result-alternative** `pstack/skills/typescript-best-practices/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/typescript-best-practices#one-schema-validates-and-types** `pstack/skills/typescript-best-practices/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/typescript-best-practices#guards-must-verify** `pstack/skills/typescript-best-practices/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe (pending cr-r2pa.2.18)
- **cursor_plugins:skill:pstack/skills/typescript-best-practices#exhaustive-variant-handling** `pstack/skills/typescript-best-practices/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/typescript-best-practices#schema-derived-types** `pstack/skills/typescript-best-practices/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-06` **adopt-merged** (2026-11-06-batch-p1:141): Checkpoint at 4dd1d05 for the owner's trait rulings: 9 adopt, 41 defer, 3 reject.
- `2026-11-06` **adopt** (2026-11-06-batch-p1:132): Owner ruling 2026-11-06: The principle derives a type from the authoritative schema that owns its shape instead of hand-writing a parallel one.
- `2026-11-06` **adopt** (2026-11-06-batch-p1:123): Owner ruling 2026-11-06: The principle handles every variant of a closed type so the checker reports one left unhandled; the never assignment is how TypeScript…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:120): Owner ruling 2026-11-06: Prevents: A check named as if it proves a type when it does not, so the bug hides behind the name. Lands in principle-type-system-disc…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:107): Owner ruling 2026-11-06: Prevents: A schema, a type and a guard that drift apart, each trusted by different callers. Lands in principle-type-system-discipline,…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:102): Owner ruling 2026-11-06: Prevents: An input type tightened where returning nothing would have been simpler for every caller. Lands in principle-type-system-dis…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:101): Owner ruling 2026-11-06: Prevents: Stronger types added everywhere, with wrappers that serve no operation. Lands in principle-type-system-discipline, SKILL.md,…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:099): Owner ruling 2026-11-06: Prevents: Own types added by reflex, which add friction and catch nothing. Lands in principle-type-system-discipline, SKILL.md, as a n…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:094): Owner ruling 2026-11-06: The principle shapes types so the checker rejects impossible states and defines special cases out of existence.
- `2026-11-06` **adopt** (2026-11-06-batch-p1:091): Owner ruling 2026-11-06: The principle gives values that share a primitive their own types, validated once when created and trusted afterwards; the brand synta…
- `2026-11-05` **update** (2026-11-05-principle-move:015): Owner ruling of 2026-11-05: moved from a skill folder to a file read by path; frontmatter and sidecar removed; the rule text is unchanged; the situation now li…
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
- [2026-11-04-upstream-cursor_plugins-4dd1d05-batch-p1.md](../../reviews/2026-11-04-upstream-cursor_plugins-4dd1d05-batch-p1.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `branded-primitives`:
  - `cursor_plugins:skill:pstack/skills/principle-type-system-discipline#branded-primitives` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/typescript-best-practices#branded-primitives` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `exhaustive-variant-handling`:
  - `cursor_plugins:skill:pstack/skills/principle-type-system-discipline#exhaustive-variant-handling` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/typescript-best-practices#exhaustive-variant-handling` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `schema-derived-types`:
  - `cursor_plugins:skill:pstack/skills/principle-type-system-discipline#schema-derived-types` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/typescript-best-practices#schema-derived-types` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `unrepresentable-invalid-states`:
  - `cursor_plugins:skill:pstack/skills/principle-type-system-discipline#unrepresentable-invalid-states` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/typescript-best-practices#unrepresentable-invalid-states` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
