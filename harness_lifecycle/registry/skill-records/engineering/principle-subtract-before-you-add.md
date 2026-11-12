---
skill: principle-subtract-before-you-add
domain: engineering
stage: Design
substage: Decomposition
secondary: []
family:
aliases: []
status: active
---
# principle-subtract-before-you-add

sequencing an addition, refactor or rewrite.

**Boundary:** Removes what the change touches before adding; decomposing work into a plan is to-plan.

<!-- registry:generated traits -->
- `touched-scope-subtraction`: Before adding, remove the dead code, redundant validators and stubs that the change touches, and report other removals instead of making them.
- `deletion-bias`: When refactoring or tempted to add an abstraction, layer or threaded signal, prefer deleting code to adding it.
- `stub-deletion`: Delete a reference that carries no novel content instead of leaving a stub that points elsewhere.
- `single-source-of-truth`: Keep each meaning in one authoritative place so changing it is a one-place edit.
- `cut-before-polish`: Reach the minimum version before investing in its quality.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/principle-foundational-thinking#subtraction-first** `pstack/skills/principle-foundational-thinking/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-subtract-before-you-add#subtraction-first** `pstack/skills/principle-subtract-before-you-add/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-laziness-protocol#deletion-bias** `pstack/skills/principle-laziness-protocol/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-subtract-before-you-add#stub-deletion** `pstack/skills/principle-subtract-before-you-add/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-laziness-protocol#single-source-of-truth** `pstack/skills/principle-laziness-protocol/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-subtract-before-you-add#cut-before-polish** `pstack/skills/principle-subtract-before-you-add/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-05` **update** (2026-11-05-principle-move:013): Owner ruling of 2026-11-05: moved from a skill folder to a file read by path; frontmatter and sidecar removed; the rule text is unchanged; the situation now li…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:192): Completes pending 2026-11-01-cursor_plugins-pstack-principles:115: the principles build (cr-r2pa.1.2) delivered cut-before-polish in principle-subtract-before-…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:191): Completes pending 2026-11-01-cursor_plugins-pstack-principles:063: the principles build (cr-r2pa.1.2) delivered single-source-of-truth in principle-subtract-be…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:190): Completes pending 2026-11-01-cursor_plugins-pstack-principles:118: the principles build (cr-r2pa.1.2) delivered stub-deletion in principle-subtract-before-you-…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:189): Completes pending 2026-11-01-cursor_plugins-pstack-principles:062: the principles build (cr-r2pa.1.2) delivered deletion-bias in principle-subtract-before-you-…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:188): Completes pending 2026-11-01-cursor_plugins-pstack-principles:113: the principles build (cr-r2pa.1.2) delivered touched-scope-subtraction in principle-subtract…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:187): Completes pending 2026-11-01-cursor_plugins-pstack-principles:057: the principles build (cr-r2pa.1.2) delivered touched-scope-subtraction in principle-subtract…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:118) *(superseded)*: Lands as a principle unit. Compatible with our thin aliases, which keep a remembered name on purpose; a reference that only points elsewhere has no such reason.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:115) *(superseded)*: Lands as a principle unit. No holder; a sequencing rule that pairs with experience-first's polish-over-breadth (cut scope, then finish what remains).
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:113) *(superseded)*: Lands as a conflict (owner ruling), into `touched-scope-subtraction`. AGENTS.md avoids unrelated cleanup and the guide (U-04) keeps scope intact. Removing what…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:063) *(superseded)*: Lands as a principle unit. Ours holds it for instruction documents (authoring-for-agents, also_in); the definition is general, and code needs it too. Carry it …
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:062) *(superseded)*: Lands as a principle unit. Round 1 mapped this to subtraction-first, whose definition orders removal before construction; a bias toward deletion at the moment …
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:057) *(superseded)*: Lands as a conflict (owner ruling), ruled under `subtract-before-you-add`, into `touched-scope-subtraction`. Same mechanism as subtract-before-you-add's first …
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `cut-before-polish`:
  - `cursor_plugins:skill:pstack/skills/principle-subtract-before-you-add#cut-before-polish` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `deletion-bias`:
  - `cursor_plugins:skill:pstack/skills/principle-laziness-protocol#deletion-bias` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `single-source-of-truth`:
  - `cursor_plugins:skill:pstack/skills/principle-laziness-protocol#single-source-of-truth` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `stub-deletion`:
  - `cursor_plugins:skill:pstack/skills/principle-subtract-before-you-add#stub-deletion` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `touched-scope-subtraction`:
  - `cursor_plugins:skill:pstack/skills/principle-foundational-thinking#subtraction-first` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/principle-subtract-before-you-add#subtraction-first` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
