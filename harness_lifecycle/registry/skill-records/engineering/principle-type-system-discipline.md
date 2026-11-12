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
- `branded-primitives`: Give semantically distinct values that share a primitive type their own types, validated once at creation and trusted afterwards. (Narrowed by sealed row 2026-11-06-batch-p1:099 (brand-only-on-confusion-risk) and the owner's amendment of 2026-11-12: a value gets its own type only where a raw value of the same primitive could really be passed in its place; T5.)
- `schema-derived-types`: Derive types from the authoritative schema that owns a shape instead of hand-writing a parallel type.
- `brand-only-on-confusion-risk`: Leave a number unbranded unless a raw number could actually be passed in its place.
- `simplest-total-type`: Keep a loose type while every operation on it is defined for all inputs, tightening it only where it forces an assertion, a cast or an impossible-case throw.
- `weaken-result-alternative`: Return a possibly absent result as the other way of making a signature total.
- `one-schema-validates-and-types`: Let one schema own validation and infer the static type from it, never keeping a schema, a parallel type and a guard that can disagree.
- `guards-must-verify`: Require a type guard to really prove what it asserts, treating a false guard as worse than a cast.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/principle-type-system-discipline#unrepresentable-invalid-states** `pstack/skills/principle-type-system-discipline/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-type-system-discipline#exhaustive-variant-handling** `pstack/skills/principle-type-system-discipline/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-type-system-discipline#branded-primitives** `pstack/skills/principle-type-system-discipline/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-type-system-discipline#schema-derived-types** `pstack/skills/principle-type-system-discipline/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/typescript-best-practices#branded-primitives** `pstack/skills/typescript-best-practices/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/typescript-best-practices#unrepresentable-invalid-states** `pstack/skills/typescript-best-practices/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/typescript-best-practices#exhaustive-variant-handling** `pstack/skills/typescript-best-practices/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/typescript-best-practices#schema-derived-types** `pstack/skills/typescript-best-practices/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/typescript-best-practices#brand-only-on-confusion-risk** `pstack/skills/typescript-best-practices/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/typescript-best-practices#simplest-total-type** `pstack/skills/typescript-best-practices/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/typescript-best-practices#weaken-result-alternative** `pstack/skills/typescript-best-practices/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/typescript-best-practices#one-schema-validates-and-types** `pstack/skills/typescript-best-practices/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/typescript-best-practices#guards-must-verify** `pstack/skills/typescript-best-practices/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-12` **adopt** (2026-11-12-batch-p1-existing:070): Completes pending 2026-11-06-batch-p1:120: guards-must-verify is written at .claude/skills/mvp-mode/principles/type-system-discipline.md:18-19, in its ruled wo…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-existing:069): Completes pending 2026-11-06-batch-p1:107: one-schema-validates-and-types is written at .claude/skills/mvp-mode/principles/type-system-discipline.md:16-17, in …
- `2026-11-12` **adopt** (2026-11-12-batch-p1-existing:068): Completes pending 2026-11-06-batch-p1:102: weaken-result-alternative is written at .claude/skills/mvp-mode/principles/type-system-discipline.md:14-15, in its r…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-existing:067): Completes pending 2026-11-06-batch-p1:101: simplest-total-type is written at .claude/skills/mvp-mode/principles/type-system-discipline.md:12-14, in its ruled w…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-existing:066): Completes pending 2026-11-06-batch-p1:099: brand-only-on-confusion-risk is written at .claude/skills/mvp-mode/principles/type-system-discipline.md:9-11, in its…
- `2026-11-12` **update** (2026-11-12-batch-p1-existing:065): Bead cr-r2pa.2.18, plan 59 slice 1: delivers 5 pending adopts of round 2026-11-06-batch-p1 (:099, :101, :102, :107, :120) into principle-type-system-discipline…
- `2026-11-06` **adopt-merged** (2026-11-06-batch-p1:141): Checkpoint at 4dd1d05 for the owner's trait rulings: 9 adopt, 41 defer, 3 reject.
- `2026-11-06` **adopt** (2026-11-06-batch-p1:132): Owner ruling 2026-11-06: The principle derives a type from the authoritative schema that owns its shape instead of hand-writing a parallel one.
- `2026-11-06` **adopt** (2026-11-06-batch-p1:123): Owner ruling 2026-11-06: The principle handles every variant of a closed type so the checker reports one left unhandled; the never assignment is how TypeScript…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:120) *(superseded)*: Owner ruling 2026-11-06: Prevents: A check named as if it proves a type when it does not, so the bug hides behind the name. Lands in principle-type-system-disc…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:107) *(superseded)*: Owner ruling 2026-11-06: Prevents: A schema, a type and a guard that drift apart, each trusted by different callers. Lands in principle-type-system-discipline,…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:102) *(superseded)*: Owner ruling 2026-11-06: Prevents: An input type tightened where returning nothing would have been simpler for every caller. Lands in principle-type-system-dis…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:101) *(superseded)*: Owner ruling 2026-11-06: Prevents: Stronger types added everywhere, with wrappers that serve no operation. Lands in principle-type-system-discipline, SKILL.md,…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:099) *(superseded)*: Owner ruling 2026-11-06: Prevents: Own types added by reflex, which add friction and catch nothing. Lands in principle-type-system-discipline, SKILL.md, as a n…
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
- `brand-only-on-confusion-risk`:
  - `cursor_plugins:skill:pstack/skills/typescript-best-practices#brand-only-on-confusion-risk` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `branded-primitives`:
  - `cursor_plugins:skill:pstack/skills/principle-type-system-discipline#branded-primitives` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/typescript-best-practices#branded-primitives` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `exhaustive-variant-handling`:
  - `cursor_plugins:skill:pstack/skills/principle-type-system-discipline#exhaustive-variant-handling` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/typescript-best-practices#exhaustive-variant-handling` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `guards-must-verify`:
  - `cursor_plugins:skill:pstack/skills/typescript-best-practices#guards-must-verify` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `one-schema-validates-and-types`:
  - `cursor_plugins:skill:pstack/skills/typescript-best-practices#one-schema-validates-and-types` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `schema-derived-types`:
  - `cursor_plugins:skill:pstack/skills/principle-type-system-discipline#schema-derived-types` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/typescript-best-practices#schema-derived-types` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `simplest-total-type`:
  - `cursor_plugins:skill:pstack/skills/typescript-best-practices#simplest-total-type` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `unrepresentable-invalid-states`:
  - `cursor_plugins:skill:pstack/skills/principle-type-system-discipline#unrepresentable-invalid-states` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/typescript-best-practices#unrepresentable-invalid-states` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `weaken-result-alternative`:
  - `cursor_plugins:skill:pstack/skills/typescript-best-practices#weaken-result-alternative` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
