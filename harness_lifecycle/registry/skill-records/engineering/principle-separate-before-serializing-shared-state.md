---
skill: principle-separate-before-serializing-shared-state
domain: engineering
stage: Design
substage: Architecture
secondary: []
family:
aliases: []
status: active
---
# principle-separate-before-serializing-shared-state

concurrent actors (processes, agents, workers) in code or tooling being designed might write the same file, branch, key or object.

**Boundary:** Removes or structurally serializes shared writes in code and tooling being designed; how agent work is divided is delegation and AGENTS.md.

<!-- registry:generated traits -->
- `concurrent-modification-test`: Before sharing state between actors, ask what a concurrent modification would do, and isolate the state unless the answer is nothing.
- `eliminate-shared-writes`: Before coordinating concurrent writers, give each its own write target (file, key, branch or directory) and merge only where results are read.
- `structural-serialization`: When one shared write target is a real invariant, serialize access by structure (lock, sequential phase, single writer, compare-and-swap), never by instruction.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/principle-foundational-thinking#concurrent-modification-test** `pstack/skills/principle-foundational-thinking/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-separate-before-serializing-shared-state#eliminate-shared-writes** `pstack/skills/principle-separate-before-serializing-shared-state/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-separate-before-serializing-shared-state#structural-serialization** `pstack/skills/principle-separate-before-serializing-shared-state/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-05` **update** (2026-11-05-principle-move:011): Owner ruling of 2026-11-05: moved from a skill folder to a file read by path; frontmatter and sidecar removed; the rule text is unchanged; the situation now li…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:182): Completes pending 2026-11-01-cursor_plugins-pstack-principles:107: the principles build (cr-r2pa.1.2) delivered structural-serialization in principle-separate-…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:181): Completes pending 2026-11-01-cursor_plugins-pstack-principles:106: the principles build (cr-r2pa.1.2) delivered eliminate-shared-writes in principle-separate-b…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:180): Completes pending 2026-11-01-cursor_plugins-pstack-principles:052: the principles build (cr-r2pa.1.2) delivered concurrent-modification-test in principle-separ…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:108): Checkpoint at 4dd1d05 for the owner's trait rulings: 2 adopt.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:107) *(superseded)*: Lands as a principle unit. No holder for code design. For our agent work, 'serialize' in AGENTS.md is enforced by the coordinator's dispatch order, which is st…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:106) *(superseded)*: Lands as a conflict (owner ruling). Opposite default: AGENTS.md serializes overlapping writes (independence-batching). Ours already separates in part (workers …
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:052) *(superseded)*: Lands as a principle unit. Round 1 mapped this to eliminate-shared-writes, which adds owned write targets and merging at reads that this source does not prescr…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `concurrent-modification-test`:
  - `cursor_plugins:skill:pstack/skills/principle-foundational-thinking#concurrent-modification-test` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `eliminate-shared-writes`:
  - `cursor_plugins:skill:pstack/skills/principle-separate-before-serializing-shared-state#eliminate-shared-writes` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `structural-serialization`:
  - `cursor_plugins:skill:pstack/skills/principle-separate-before-serializing-shared-state#structural-serialization` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
