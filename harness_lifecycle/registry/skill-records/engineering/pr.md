---
skill: pr
domain: engineering
stage: Delivery
substage: Integration
secondary: []
family:
aliases: []
status: active
---
# pr

Use when writing or revising a pull request's body: why, a visual of the change, before-and-after evidence and merge danger. Commits and their titles are land; pushing and merging are not this skill.

**Boundary:** Writes a pull request's body (why, a visual, evidence, merge danger); the commits and their titles are land, and opening or merging the PR needs publish authority.

<!-- registry:generated traits -->
- `pr-body-template`: Fill a fixed PR-body skeleton with Summary, Evidence, and Merge Danger sections.
- `evidence-before-after`: Show concrete before/after evidence that the change works, preferring screenshots, then execution-based test or console output.
- `merge-danger`: State the merge's one-way or two-way door and its blast radius.
- `no-preamble`: Open with the answer and stop when it is done, with no preamble, recap or closing pleasantry.
- `visual-form-catalog`: Offer a set of inline visual forms — pseudocode, call, component and file trees, Mermaid and whole-block — each with its own shape rules.
- `structural-diff`: Show a change as a diff against the structure the reader already holds rather than against raw source.
- `visual-placement`: Place each visual immediately after the sentence it supports and include only the detail the current question needs.
- `minimal-visual-selection`: Use the fewest and smallest visuals that make the point, never a gallery.
- `link-bulk-evidence`: Link bulky evidence, such as full logs and commit lists, from a pull request instead of pasting it into the body.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/engineering/pr#pr-body-template** `skills/engineering/pr/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/pr#evidence-before-after** `skills/engineering/pr/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/pr#merge-danger** `skills/engineering/pr/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/pr#no-preamble** `skills/engineering/pr/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **cursor_plugins:playbook:pstack/skills/poteto-mode/playbooks/opening-a-pr** `pstack/skills/poteto-mode/playbooks/opening-a-pr.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
  - merged from: reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/opening-a-pr.md
  - modified: From its Descriptions section, in our words: the body is written for a reviewer reading the diff; why the change exists, and what it leaves out when a reviewer would ask, open the Summary; short sentences; full SHAs, full run logs and checklists go in a linked artifact.
  - modified: Its six drop-when-empty sections become pr's fixed three (Summary, Evidence, Merge danger), each kept with a line when it has nothing real.
  - dropped: Its Commits and Titles sections, delivered by land (2026-11-01-batch-1:196, unchanged).
  - dropped: Forge resolution, the built-in PR tool, size and stacks, readiness and babysitting; revisit_when: we adopt a PR flow with CI.
  - dropped: Worktree recipes, the deslop and comment passes, and the writing skills it names.
- **cursor_plugins:skill:pstack/skills/technical-writing#writing-rules-cover-pr-bodies** `pstack/skills/technical-writing/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049 (pending cr-r2pa.2.13.2)
- **cursor_plugins:skill:pstack/skills/technical-writing#link-bulk-evidence** `pstack/skills/technical-writing/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/automations/benny/skills/reproduce-and-fix-issues#bug-pr-contents** `pstack/automations/benny/skills/reproduce-and-fix-issues/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049 (pending cr-r2pa.2.13.3)
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-13` **adopt** (2026-11-13-batch-p3:234): Owner ruling 2026-11-13: Prevents: A bug-fix pull request whose reviewer cannot tell what broke, why, or which tracked item it closes, so the fix is checked ag…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:472): Owner ruling 2026-11-13: completes the held row's pending adopt. pr already says this at pr/SKILL.md:59-60; traits/ours.yaml now lists `link-bulk-evidence` on …
- `2026-11-13` **adopt** (2026-11-13-batch-p2:073) *(superseded)*: Owner ruling 2026-11-13: Prevents: A body buried under pasted logs and commit lists that a reviewer has to scroll past. Lands in pr, SKILL.md:59-60. It already…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:070): Owner ruling 2026-11-13: Prevents: A body the reviewer must reread because its prose is padded, vague or reads as machine-written, which the body's short secti…
- `2026-11-12` **adopt-merged** (2026-11-12-pr:006): Owner ruling of 2026-11-05 §E (pr: new, with evidence and merge danger; cites show-me for visuals) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md:44), go…
- `2026-11-12` **adopt** (2026-11-12-pr:005): Owner ruling of 2026-11-05 §E (pr: new, with evidence and merge danger; cites show-me for visuals) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md:44), go…
- `2026-11-12` **adopt** (2026-11-12-pr:004): Owner ruling of 2026-11-05 §E (pr: new, with evidence and merge danger; cites show-me for visuals) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md:44), go…
- `2026-11-12` **adopt** (2026-11-12-pr:003): Owner ruling of 2026-11-05 §E (pr: new, with evidence and merge danger; cites show-me for visuals) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md:44), go…
- `2026-11-12` **adopt** (2026-11-12-pr:002): Owner ruling of 2026-11-05 §E (pr: new, with evidence and merge danger; cites show-me for visuals) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md:44), go…
- `2026-11-12` **add** (2026-11-12-pr:001): Owner ruling of 2026-11-05 §E (pr: new, with evidence and merge danger; cites show-me for visuals) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md:44), go…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-12-upstream-cursor_plugins-2776ddd-batch-p3.md](../../reviews/2026-11-12-upstream-cursor_plugins-2776ddd-batch-p3.md)
- [2026-11-12-upstream-cursor_plugins-2776ddd-batch-p2.md](../../reviews/2026-11-12-upstream-cursor_plugins-2776ddd-batch-p2.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `evidence-before-after`:
  - `mattpocock_skills:skill:skills/engineering/pr#evidence-before-after` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `link-bulk-evidence`:
  - `cursor_plugins:skill:pstack/skills/technical-writing#link-bulk-evidence` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `merge-danger`:
  - `mattpocock_skills:skill:skills/engineering/pr#merge-danger` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `no-preamble`:
  - `mattpocock_skills:skill:skills/engineering/pr#no-preamble` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `pr-body-template`:
  - `mattpocock_skills:skill:skills/engineering/pr#pr-body-template` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
