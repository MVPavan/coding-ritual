---
skill: principle-attack-the-premise
domain: engineering
stage: Building
substage: Diagnosis
secondary: []
family: 
aliases: []
status: active
---
# principle-attack-the-premise

Apply when two or more fixes resting on one belief have failed the same gate (a test, a review, an eval).

**Boundary:** A gate applied once fixes resting on one belief keep failing: name and test that belief; finding a failure's cause is systematic-debugging, and the fix loop is the bug-fix playbook.

<!-- registry:generated traits -->
- `premise-test-gate`: After two or more fixes that rest on one premise fail the same gate, write that premise as one sentence and test it with an observation that would differ were it false, before any further fix that assumes it.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/principle-attack-the-premise#premise-test-gate** `pstack/skills/principle-attack-the-premise/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:140): Completes pending 2026-11-01-cursor_plugins-pstack-principles:001: the principles build (cr-r2pa.1.2) delivered premise-test-gate in principle-attack-the-premi…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:001) *(superseded)*: Lands as a principle unit. Ours stops after two failed fixes and hands back the attempt log (bug-fix playbook step 5), and AGENTS.md says only to change approa…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `premise-test-gate`:
  - `cursor_plugins:skill:pstack/skills/principle-attack-the-premise#premise-test-gate` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
