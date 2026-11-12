---
skill: principle-no-comments
domain: engineering
stage: Building
substage: Implementation
secondary: []
family:
aliases: []
status: active
---
# principle-no-comments

writing, keeping or deleting a code comment, or judging one in a review.

**Boundary:** Decides whether one code comment is kept, deleted or kept and flagged, from its keep classes; running a sweep over a scope is no-comments.

<!-- registry:generated traits -->
- `exact-proof-settles-a-protected-keep`: Refuse deleting a comment a stated exception protects, and count a comment as a settled protected keep only with that exact exception and proof within scope, proof a provisional keep of a doubtful comment does not need.
- `unsure-comment-kept-and-flagged`: When unsure whether a comment should go, keep it, bringing it back if already deleted, and flag it for a person.
- `safety-suppressions-removed`: Treat suppressions bearing on correctness or safety as findings that must be removed.
- `constraint-comment-class`: Treat comments that forbid removal, forbid rewording or require consulting someone as a distinct class.
- `unchangeable-constraint-kept`: Leave kept comments that concern things outside the team's control.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/no-comments#comment-exception-gate** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/no-comments#comment-keep-needs-proof** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/no-comments#safety-suppressions-removed** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/no-comments#ambiguous-comment-deleted** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/no-comments#constraint-comment-class** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/no-comments#unchangeable-constraint-kept** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:022): Completes pending 2026-11-06-batch-p1:081: unchangeable-constraint-kept is written at .claude/skills/mvp-mode/principles/no-comments.md:5-9 (plan 63; a new uni…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:021): Completes pending 2026-11-06-batch-p1:080: constraint-comment-class is written at .claude/skills/mvp-mode/principles/no-comments.md:14-16 (plan 63; a new unit,…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:020): Completes pending 2026-11-06-batch-p1:072: unsure-comment-kept-and-flagged is written at .claude/skills/mvp-mode/principles/no-comments.md:26-27 (plan 63; a ne…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:019): Completes pending 2026-11-06-batch-p1:070: safety-suppressions-removed is written at .claude/skills/mvp-mode/principles/no-comments.md:17-18 (plan 63; a new un…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:018): Completes pending 2026-11-06-batch-p1:068: unsure-comment-kept-and-flagged is written at .claude/skills/mvp-mode/principles/no-comments.md:26-27 (plan 63; a ne…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:017): Completes pending 2026-11-06-batch-p1:064: exact-proof-settles-a-protected-keep is written at .claude/skills/mvp-mode/principles/no-comments.md:19-25 (plan 63;…
- `2026-11-12` **add** (2026-11-12-batch-p1-no-comments:002): Owner rulings of 2026-11-05 §E (no-comments: a principle for the rules plus a manual skill for the sweep; persona dropped; when unsure, keep and flag) and §G (…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:081) *(superseded)*: Owner ruling 2026-11-06: Prevents: A warning about a vendor or platform limit removed, so the next person hits the limit unwarned. Lands in principle-no-commen…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:080) *(superseded)*: Owner ruling 2026-11-06: Prevents: A comment that carries a real constraint treated as ordinary narration. Lands in principle-no-comments, principles/no-commen…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:072) *(superseded)*: Owner ruling 2026-11-06: Prevents: A comment that held a real constraint deleted because the agent could not tell. Lands in principle-no-comments, principles/n…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:070) *(superseded)*: Owner ruling 2026-11-06: Prevents: A suppression that silences a correctness or safety check and stays because it looks like any other. Lands in principle-no-c…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:068) *(superseded)*: Owner ruling 2026-11-06: Prevents: A comment that held a real constraint deleted because nobody could prove it on the spot. Lands in principle-no-comments, pri…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:064) *(superseded)*: Owner ruling 2026-11-06: Prevents: A protected comment deleted, a doubtful one left deleted for want of proof, or a doubtful one passed off as settled. Lands i…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-04-upstream-cursor_plugins-4dd1d05-batch-p1.md](../../reviews/2026-11-04-upstream-cursor_plugins-4dd1d05-batch-p1.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `constraint-comment-class`:
  - `cursor_plugins:skill:pstack/skills/no-comments#constraint-comment-class` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `exact-proof-settles-a-protected-keep`:
  - `cursor_plugins:skill:pstack/skills/no-comments#comment-exception-gate` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `safety-suppressions-removed`:
  - `cursor_plugins:skill:pstack/skills/no-comments#safety-suppressions-removed` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `unchangeable-constraint-kept`:
  - `cursor_plugins:skill:pstack/skills/no-comments#unchangeable-constraint-kept` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `unsure-comment-kept-and-flagged`:
  - `cursor_plugins:skill:pstack/skills/no-comments#ambiguous-comment-deleted` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/no-comments#comment-keep-needs-proof` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
