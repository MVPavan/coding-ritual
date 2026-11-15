---
skill: principle-make-operations-idempotent
domain: engineering
stage: Design
substage: Architecture
secondary: []
family:
aliases: []
status: active
---
# principle-make-operations-idempotent

designing a command, lifecycle step or loop that may crash, restart or retry.

**Boundary:** Makes state-changing operations safe to rerun and to stop partway; concurrent writers are principle-separate-before-serializing-shared-state.

<!-- registry:generated traits -->
- `convergent-operations`: Design state-changing operations to converge on the same correct end state however often they run and wherever a previous run stopped.
- `reconcile-from-state`: Derive each step from the observed current state compared with the goal, applying only the difference.
- `judgeable-leftovers`: Make everything a run leaves behind (locks, temporary files, partial records, claims) recognisable as stale by the next run, using evidence that holds wherever the run stopped.
- `interruption-point-audit`: Check a state-changing operation by asking what happens when it runs twice and when it stops at each point, and add reconciliation wherever the answer depends on leftovers.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/principle-make-operations-idempotent#convergent-operations** `pstack/skills/principle-make-operations-idempotent/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-make-operations-idempotent#reconcile-from-state** `pstack/skills/principle-make-operations-idempotent/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-make-operations-idempotent#judgeable-leftovers** `pstack/skills/principle-make-operations-idempotent/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-make-operations-idempotent#interruption-point-audit** `pstack/skills/principle-make-operations-idempotent/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-05` **update** (2026-11-05-principle-move:006): Owner ruling of 2026-11-05: moved from a skill folder to a file read by path; frontmatter and sidecar removed; the rule text is unchanged; the situation now li…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:160): Completes pending 2026-11-01-cursor_plugins-pstack-principles:069: the principles build (cr-r2pa.1.2) delivered interruption-point-audit in principle-make-oper…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:159): Completes pending 2026-11-01-cursor_plugins-pstack-principles:068: the principles build (cr-r2pa.1.2) delivered judgeable-leftovers in principle-make-operation…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:158): Completes pending 2026-11-01-cursor_plugins-pstack-principles:067: the principles build (cr-r2pa.1.2) delivered reconcile-from-state in principle-make-operatio…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:157): Completes pending 2026-11-01-cursor_plugins-pstack-principles:066: the principles build (cr-r2pa.1.2) delivered convergent-operations in principle-make-operati…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:070): Checkpoint at 4dd1d05 for the owner's trait rulings: 4 adopt.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:069) *(superseded)*: Lands as a principle unit. Round 1 folded the run-twice and stop-at-every-point questions into convergent-operations, the goal they test. They are a separately…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:068) *(superseded)*: Lands as a principle unit. No holder; stale locks and claims are a recurring cost in agent tooling.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:067) *(superseded)*: Lands as a principle unit. No holder; the method that makes convergence achievable.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:066) *(superseded)*: Lands as a principle unit. AGENTS.md retries only when repetition is safe; nothing makes our own commands, ledgers and engine loops safe to repeat. Our learnin…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `convergent-operations`:
  - `cursor_plugins:skill:pstack/skills/principle-make-operations-idempotent#convergent-operations` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `interruption-point-audit`:
  - `cursor_plugins:skill:pstack/skills/principle-make-operations-idempotent#interruption-point-audit` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `judgeable-leftovers`:
  - `cursor_plugins:skill:pstack/skills/principle-make-operations-idempotent#judgeable-leftovers` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `reconcile-from-state`:
  - `cursor_plugins:skill:pstack/skills/principle-make-operations-idempotent#reconcile-from-state` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
