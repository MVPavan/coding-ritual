---
skill: land
domain: engineering
stage: Delivery
substage: Integration
secondary: []
family: git-mechanics
aliases: []
status: active
---
# land

Use when verified work should become commits: split, order and title them, and commit only with authority. Skip pushing, merging and pull requests, and a merge already in conflict.

**Boundary:** Turns verified changes into titled, ordered commits or a commit plan, only on finished work; a tree already in conflict is resolving-merge-conflicts, plugin releases are harness-publish, running the work is execution, and commit size and order come from principle-sequence-verifiable-units.

<!-- registry:generated traits -->
- `verified-work-only`: Refuse to land work not verified on its final form, rechecking behaviour if a closeout changed executable content, and report the gap.
- `own-path-partition`: Assign only the task's changed paths to commits, leaving and naming every other change in the tree.
- `conventional-commit-title`: Title a commit type(scope): imperative subject, no trailing period, naming the real symbol that carries the change.
- `commit-body-adds`: A commit body says what the subject cannot and never restates it.
- `commit-plan-without-authority`: Without commit authority, stage nothing and report the ordered commits with paths, titles and bodies.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:playbook:pstack/skills/poteto-mode/playbooks/opening-a-pr** `pstack/skills/poteto-mode/playbooks/opening-a-pr.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
  - merged from: reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/opening-a-pr.md
  - modified: A skill called after a code playbook's closeout on its finished exit, not a playbook of its own run at the end of every other one.
  - modified: Commit size and order are cited through principle-sequence-verifiable-units, not restated.
  - modified: Titles keep the type(scope) form and the real symbol; bodies add what the subject cannot.
  - modified: Ours: only the task's own paths are partitioned into commits and every other change is named; work not verified on its final form is refused; without commit authority it stages nothing and reports the commit plan.
  - dropped: PR description, forge, built-in PR tool, stack, readiness and babysit sections; revisit_when: we adopt a PR flow with CI.
  - dropped: Worktree recipes and hard resets, which AGENTS.md Safety governs.
  - dropped: Commit liberally, amend by default and rebase as a default.
  - dropped: The deslop and comment passes over the diff, and the writing skills it names.
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-01` **adopt-merged** (2026-11-01-batch-1:196): Plan N3 and owner ruling 2026-11-01: the playbook's Commits and Titles rules become the skill land; a playbook is ruled whole, so land's traits are our own.
- `2026-11-01` **add** (2026-11-01-batch-1:195): New skill, plan 4.1 and N5: verified changes become small ordered commits with conventional titles, or a commit plan without authority. Playbooks call it after…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
