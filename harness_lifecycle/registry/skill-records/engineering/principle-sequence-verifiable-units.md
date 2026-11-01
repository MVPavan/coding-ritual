---
skill: principle-sequence-verifiable-units
domain: engineering
stage: Building
substage: Implementation
secondary: []
family: 
aliases: []
status: active
---
# principle-sequence-verifiable-units

Apply when doing multi-step work (a sweep, a migration, a run of similar edits) or stacking commits.

**Boundary:** Orders multi-step work into checked units and commits; test-first proof of one change is test-driven-development, and a declared migration group is principle-migrate-without-shims.

<!-- registry:generated traits -->
- `baseline-check-before-change`: Before the first change of multi-step work, run its checks on the starting base and record the results, so later failures are classed as pre-existing or as regressions.
- `verified-unit-sequence`: Split multi-step work into small units that each end in a checked state, and start the next only when the current one passes.
- `small-single-purpose-commits`: Keep each commit small and about one thing.
- `argument-order-commits`: Order commits so the history proves the work (failing test before fix, removal before reshape, baseline before treatment, scaffold before feature), each commit standing alone.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/principle-sequence-verifiable-units#clean-baseline-first** `pstack/skills/principle-sequence-verifiable-units/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-sequence-verifiable-units#verified-unit-sequence** `pstack/skills/principle-sequence-verifiable-units/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-foundational-thinking#small-single-purpose-commits** `pstack/skills/principle-foundational-thinking/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-sequence-verifiable-units#argument-order-commits** `pstack/skills/principle-sequence-verifiable-units/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:186): Completes pending 2026-11-01-cursor_plugins-pstack-principles:111: the principles build (cr-r2pa.1.2) delivered argument-order-commits in principle-sequence-ve…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:185): Completes pending 2026-11-01-cursor_plugins-pstack-principles:055: the principles build (cr-r2pa.1.2) delivered small-single-purpose-commits in principle-seque…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:184): Completes pending 2026-11-01-cursor_plugins-pstack-principles:109: the principles build (cr-r2pa.1.2) delivered verified-unit-sequence in principle-sequence-ve…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:183): Completes pending 2026-11-01-cursor_plugins-pstack-principles:110: the principles build (cr-r2pa.1.2) delivered baseline-check-before-change in principle-seque…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:112): Checkpoint at 4dd1d05 for the owner's trait rulings: 3 adopt.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:111) *(superseded)*: Lands as a principle unit. No holder. Applies only when commits are authorized; the principle should say so.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:110) *(superseded)*: Lands as a principle unit, into `baseline-check-before-change`. Not covered: AGENTS.md establishes the base before merging (merge-base-selection) and asks to d…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:109) *(superseded)*: Lands as a principle unit. Planning slices verifiably and execution stops on a failed gate, both at task or stage scale. A sweep of many small edits inside one…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:055) *(superseded)*: Lands as a principle unit. This row is the only ruling for the trait; sequence-verifiable-units has no row for it and is only the destination. It fits that uni…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `argument-order-commits`:
  - `cursor_plugins:skill:pstack/skills/principle-sequence-verifiable-units#argument-order-commits` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `baseline-check-before-change`:
  - `cursor_plugins:skill:pstack/skills/principle-sequence-verifiable-units#clean-baseline-first` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `small-single-purpose-commits`:
  - `cursor_plugins:skill:pstack/skills/principle-foundational-thinking#small-single-purpose-commits` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `verified-unit-sequence`:
  - `cursor_plugins:skill:pstack/skills/principle-sequence-verifiable-units#verified-unit-sequence` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
