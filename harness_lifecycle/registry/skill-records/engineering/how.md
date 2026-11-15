---
skill: how
domain: engineering
stage: Discovery
substage: Research
secondary: []
family:
aliases: []
status: active
---
# how

Use to explain how something in this project works now (code, a script, config, a documented process or record format), with citations, or which option fits it once the scope is settled: before changing it, at a playbook step's call, or inside a delegated task. Why it has its shape or what motivated a change is why. At top level, a question that should end in that answer is the investigation playbook; a single lookup needs neither; an external codebase is codebase-research.

**Boundary:** One cited, read-only answer about how something in this project works now, or which option fits once scope is settled. Why it has its shape is why, a report on an external codebase is codebase-research, a saved answer is the investigation playbook, outside sources are research, an unexplained failure is systematic-debugging, open scope is discovery, and a wanted change goes back through the router.

<!-- registry:generated traits -->
- `read-only-explanation`: Change nothing while explaining, not even temporary instrumentation.
- `immaterial-ambiguity-reading`: State the reading taken of a target whose ambiguity would not materially change the answer, and proceed.
- `angles-when-wide`: Answer a narrow question in one pass, and split a wide subsystem into angles through delegation by the local rule, then reconcile what comes back.
- `reconcile-by-reading`: Settle conflicting findings by reading the code itself.
- `explanation-sections`: Structure an explanation as overview, concepts, flow, file map and pitfalls, dropping any section that does not apply.
- `cited-flow-walkthrough`: Walk the flow in prose from trigger to result, naming the files and functions at each step.
- `recommendation-with-tradeoffs`: For a choice between alternatives, recommend one and show the tradeoffs in a table.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/how#stated-scope-reading** `pstack/skills/how/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/how#size-gated-explorers** `pstack/skills/how/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/how#explanation-sections** `pstack/skills/how/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/how#cited-flow-walkthrough** `pstack/skills/how/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/how#reconcile-by-reading** `pstack/skills/how/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-11` **update** (2026-11-11-discovery:022): Owner ruling L1 of 2026-11-10 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 20 D5, critic-37b F1: how's decision branch gets outside evidence fro…
- `2026-11-11` **update** (2026-11-11-discovery:006): Owner ruling L1 of 2026-11-10 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 20 D1. Its decision branch sends open scope to discovery; outside sou…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:119): Completes pending 2026-11-10-renames-splits:031: reconcile-by-reading is delivered at .claude/skills/how/SKILL.md:33-34, in how, relocated from explain-code (p…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:118): Completes pending 2026-11-10-renames-splits:030: cited-flow-walkthrough is delivered at .claude/skills/how/SKILL.md:42-43, in how, relocated from explain-code …
- `2026-11-10` **adopt** (2026-11-10-renames-splits:117): Completes pending 2026-11-10-renames-splits:029: explanation-sections is delivered at .claude/skills/how/SKILL.md:38-45, in how, relocated from explain-code (p…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:116): Completes pending 2026-11-10-renames-splits:028: angles-when-wide is delivered at .claude/skills/how/SKILL.md:25-31, in how, relocated from explain-code (plan …
- `2026-11-10` **adopt** (2026-11-10-renames-splits:115): Completes pending 2026-11-10-renames-splits:027: immaterial-ambiguity-reading is delivered at .claude/skills/how/SKILL.md:22-23, in how, relocated from explain…
- `2026-11-10` **add** (2026-11-10-renames-splits:112): Owner rulings C of 2026-11-05, I1 and I4 of 2026-11-06 and K of 2026-11-10 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 14a U6. New skill: one c…
- `2026-11-10` **adopt-merged** (2026-11-10-renames-splits:067): Checkpoint at 4dd1d05 after the renames-splits rulings: 5 adopt, 15 reject; adopts now land in how.
- `2026-11-10` **adopt** (2026-11-10-renames-splits:031) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `how` out of `explain-code`; this is part of explaining how th…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:030) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `how` out of `explain-code`; this is part of explaining how th…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:029) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `how` out of `explain-code`; this is part of explaining how th…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:028) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `how` out of `explain-code`; this is part of explaining how th…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:027) *(superseded)*: Owner rulings 2026-11-05 and 2026-11-06 (C, D, I): Relocation: owner ruling 2026-11-05 §C splits `how` out of `explain-code`; this is part of explaining how th…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-09-upstream-cursor_plugins-4dd1d05.md](../../reviews/2026-11-09-upstream-cursor_plugins-4dd1d05.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `angles-when-wide`:
  - `cursor_plugins:skill:pstack/skills/how#size-gated-explorers` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `cited-flow-walkthrough`:
  - `cursor_plugins:skill:pstack/skills/how#cited-flow-walkthrough` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `explanation-sections`:
  - `cursor_plugins:skill:pstack/skills/how#explanation-sections` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `immaterial-ambiguity-reading`:
  - `cursor_plugins:skill:pstack/skills/how#stated-scope-reading` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `reconcile-by-reading`:
  - `cursor_plugins:skill:pstack/skills/how#reconcile-by-reading` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
