---
skill: principle-boundary-discipline
domain: engineering
stage: Design
substage: Architecture
secondary: []
family: 
aliases: []
status: active
---
# principle-boundary-discipline

Apply when wiring validation, error handling or a framework adapter.

**Boundary:** Where data is checked and trusted (boundary validation, parsing, internal trust, public types, pure core); interface shape and depth are codebase-design, and type-level rules are principle-type-system-discipline.

<!-- registry:generated traits -->
- `boundary-validation`: Concentrate validation, narrowing and error handling where data crosses a system boundary such as CLI arguments, configuration, the network or an external API.
- `parse-at-boundary`: Turn raw external input into typed domain values with a parse function at the boundary where it enters.
- `scoped-internal-trust`: Inside the system, trust data a boundary already validated and propagate errors, adding a check at an inner layer only on a failure path a defect has proven.
- `domain-not-wire-types`: Expose domain concepts across a public surface, never the transport, storage or framework types behind it.
- `pure-core-thin-shell`: Keep business logic in pure functions free of framework dependencies, leaving a thin mechanical shell that calls them.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/principle-boundary-discipline#boundary-validation** `pstack/skills/principle-boundary-discipline/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-boundary-discipline#parse-at-boundary** `pstack/skills/principle-boundary-discipline/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-type-system-discipline#parse-at-boundary** `pstack/skills/principle-type-system-discipline/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-boundary-discipline#trust-internal-types** `pstack/skills/principle-boundary-discipline/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-boundary-discipline#domain-not-wire-types** `pstack/skills/principle-boundary-discipline/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-boundary-discipline#pure-core-thin-shell** `pstack/skills/principle-boundary-discipline/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:146): Completes pending 2026-11-01-cursor_plugins-pstack-principles:009: the principles build (cr-r2pa.1.2) delivered pure-core-thin-shell in principle-boundary-disc…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:145): Completes pending 2026-11-01-cursor_plugins-pstack-principles:006: the principles build (cr-r2pa.1.2) delivered domain-not-wire-types in principle-boundary-dis…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:144): Completes pending 2026-11-01-cursor_plugins-pstack-principles:005: the principles build (cr-r2pa.1.2) delivered scoped-internal-trust in principle-boundary-dis…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:143): Completes pending 2026-11-01-cursor_plugins-pstack-principles:132: the principles build (cr-r2pa.1.2) delivered parse-at-boundary in principle-boundary-discipl…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:142): Completes pending 2026-11-01-cursor_plugins-pstack-principles:008: the principles build (cr-r2pa.1.2) delivered parse-at-boundary in principle-boundary-discipl…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:141): Completes pending 2026-11-01-cursor_plugins-pstack-principles:004: the principles build (cr-r2pa.1.2) delivered boundary-validation in principle-boundary-disci…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:134): Checkpoint at 4dd1d05 for the owner's trait rulings: 5 adopt.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:132) *(superseded)*: Lands as a principle unit, ruled under `boundary-discipline`. Owned by boundary-discipline; this principle cites it.
- `2026-11-01` **adopt-merged** (2026-11-01-cursor_plugins-pstack-principles:010): Checkpoint at 4dd1d05 for the owner's trait rulings: 5 adopt, 1 defer.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:009) *(superseded)*: Lands as a principle unit. Ours prefers pure calculations where they clarify and accepts isolated side effects; the pure-core and thin-shell split is not state…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:008) *(superseded)*: Lands as a principle unit. Ours picks Pydantic for external contracts but never says the parse happens once, at entry. Shared with type-system-discipline; one …
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:006) *(superseded)*: Lands as a principle unit. Ours keeps framework objects out of serialized contracts, the reverse direction; nothing keeps wire types out of a public API.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:005) *(superseded)*: Lands as a conflict (owner ruling), into `scoped-internal-trust`. Opposite default to the bug-fix playbook's hardening reference, which adds a business-logic c…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:004) *(superseded)*: Lands as a principle unit. Ours validates user-controlled paths and shell arguments (coding-style.md) as a security rule but never says where validation belong…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `boundary-validation`:
  - `cursor_plugins:skill:pstack/skills/principle-boundary-discipline#boundary-validation` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `domain-not-wire-types`:
  - `cursor_plugins:skill:pstack/skills/principle-boundary-discipline#domain-not-wire-types` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `parse-at-boundary`:
  - `cursor_plugins:skill:pstack/skills/principle-boundary-discipline#parse-at-boundary` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/principle-type-system-discipline#parse-at-boundary` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `pure-core-thin-shell`:
  - `cursor_plugins:skill:pstack/skills/principle-boundary-discipline#pure-core-thin-shell` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `scoped-internal-trust`:
  - `cursor_plugins:skill:pstack/skills/principle-boundary-discipline#trust-internal-types` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
