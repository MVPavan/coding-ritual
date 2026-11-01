---
skill: principle-test-behavior-not-implementation
domain: engineering
stage: Verification
substage: Testing
secondary: []
family: 
aliases: []
status: active
---
# principle-test-behavior-not-implementation

Apply when writing, changing or keeping any test.

**Boundary:** Judges what a test asserts and whether it earns its place; the test-first cycle is test-driven-development.

<!-- registry:generated traits -->
- `two-edit-test-judgement`: Judge every test by two imagined edits: breaking the behaviour must fail it, and restructuring the internals must not.
- `public-interface-testing`: Exercise behaviour in tests through public interfaces.
- `contract-exact-assertion`: Assert exactly what the contract promises, no less and no more, letting the contract decide whether a call, an absence, a payload or an error type is behaviour.
- `absence-positive-control`: Pair an assertion that something did not happen with a positive case showing the same test would see it happen.
- `hollow-test-forms`: Check a test for the usual hollow forms: an assertion looser than the contract, a restated constant the code never reads, or an assertion on data the test built itself.
- `behaviour-and-edge-case-tests`: Judge tests by the behaviours and edge cases they exercise, not by line coverage.
- `implementation-test-deletion`: When internals change, rewrite or delete tests that only protect the old implementation, asserting the current contract instead.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/principle-test-behavior-not-implementation#two-edit-test-judgement** `pstack/skills/principle-test-behavior-not-implementation/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-test-behavior-not-implementation#public-interface-testing** `pstack/skills/principle-test-behavior-not-implementation/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-test-behavior-not-implementation#contract-exact-assertion** `pstack/skills/principle-test-behavior-not-implementation/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-test-behavior-not-implementation#absence-positive-control** `pstack/skills/principle-test-behavior-not-implementation/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-test-behavior-not-implementation#hollow-test-forms** `pstack/skills/principle-test-behavior-not-implementation/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-foundational-thinking#behaviour-and-edge-case-tests** `pstack/skills/principle-foundational-thinking/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-migrate-callers-then-delete-legacy-apis#implementation-test-deletion** `pstack/skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-test-behavior-not-implementation#implementation-test-deletion** `pstack/skills/principle-test-behavior-not-implementation/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:200): Completes pending 2026-11-01-cursor_plugins-pstack-principles:124: the principles build (cr-r2pa.1.2) delivered implementation-test-deletion in principle-test-…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:199): Completes pending 2026-11-01-cursor_plugins-pstack-principles:072: the principles build (cr-r2pa.1.2) delivered implementation-test-deletion in principle-test-…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:198): Completes pending 2026-11-01-cursor_plugins-pstack-principles:051: the principles build (cr-r2pa.1.2) delivered behaviour-and-edge-case-tests in principle-test…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:197): Completes pending 2026-11-01-cursor_plugins-pstack-principles:123: the principles build (cr-r2pa.1.2) delivered hollow-test-forms in principle-test-behavior-no…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:196): Completes pending 2026-11-01-cursor_plugins-pstack-principles:127: the principles build (cr-r2pa.1.2) delivered absence-positive-control in principle-test-beha…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:195): Completes pending 2026-11-01-cursor_plugins-pstack-principles:126: the principles build (cr-r2pa.1.2) delivered contract-exact-assertion in principle-test-beha…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:194): Completes pending 2026-11-01-cursor_plugins-pstack-principles:125: the principles build (cr-r2pa.1.2) delivered public-interface-testing in principle-test-beha…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:193): Completes pending 2026-11-01-cursor_plugins-pstack-principles:121: the principles build (cr-r2pa.1.2) delivered two-edit-test-judgement in principle-test-behav…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:127) *(superseded)*: Lands as a principle unit. Ours lets an absence of a call be the contract but never asks for a positive control that shows the test could see the call. Round 1…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:126) *(superseded)*: Lands as a principle unit. Ours says outbound calls can be the contract; it lacks the no-less-no-more bound.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:125) *(superseded)*: Lands as a principle unit. Not delivered: coding-style.md lists it, but that is an on-demand Python project document (also_in), not shipped (D2) and not a prov…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:124) *(superseded)*: Lands as a principle unit. Consistent with preserving tests that catch distinct failures: an implementation-pinned test catches none.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:123) *(superseded)*: Lands as a principle unit. Ours covers restated source text; it misses assertions looser than the contract and assertions on test-built data.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:121) *(superseded)*: Lands as a principle unit. Round 1 split this into break-naming-validation and no-implementation-coupling and called both covered. Neither is the whole mechani…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:072) *(superseded)*: Lands as a principle unit, ruled under `test-behavior-not-implementation`. Ours preserves tests that catch distinct failures and removes a test only when cover…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:051) *(superseded)*: Lands as a principle unit. Round 1 mapped this to meaningful-behaviour-assertion, whose definition adds a stable-boundary and choreography rule upstream does n…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `absence-positive-control`:
  - `cursor_plugins:skill:pstack/skills/principle-test-behavior-not-implementation#absence-positive-control` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `behaviour-and-edge-case-tests`:
  - `cursor_plugins:skill:pstack/skills/principle-foundational-thinking#behaviour-and-edge-case-tests` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `contract-exact-assertion`:
  - `cursor_plugins:skill:pstack/skills/principle-test-behavior-not-implementation#contract-exact-assertion` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `hollow-test-forms`:
  - `cursor_plugins:skill:pstack/skills/principle-test-behavior-not-implementation#hollow-test-forms` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `implementation-test-deletion`:
  - `cursor_plugins:skill:pstack/skills/principle-migrate-callers-then-delete-legacy-apis#implementation-test-deletion` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/principle-test-behavior-not-implementation#implementation-test-deletion` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `public-interface-testing`:
  - `cursor_plugins:skill:pstack/skills/principle-test-behavior-not-implementation#public-interface-testing` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `two-edit-test-judgement`:
  - `cursor_plugins:skill:pstack/skills/principle-test-behavior-not-implementation#two-edit-test-judgement` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
