---
skill: no-comments
domain: core
stage: Verification
substage: Review
secondary: []
family:
aliases: []
status: active
---
# no-comments

Sweep a scope for comments that should go, judged by principle-no-comments, then fix what the sweep exposes and offer checks for real constraints. Use for /no-comments; reviewing a change for bugs or design is review.

**Boundary:** Sweeps a scope for comments that should go, fixes what the sweep exposes inside it and offers checks for real constraints; judging one comment is principle-no-comments, and reviewing a change for bugs or design is review.

<!-- registry:generated traits -->
- `merge-base-through-tree-scope`: When no scope is named, review the branch from where it left the base branch up to and including the working tree.
- `named-scope-first`: Use the scope the user names when one is given.
- `comment-pass-stays-in-bounds`: During a comment pass, change only comments, and only inside the given scope.
- `kept-code-not-guilty`: Refuse flags that treat intentionally retained code as being at fault.
- `reshape-flags-open-apart-from-comment`: Keep flags asking to restructure surprising first-party code open, whether their comments stay, go or come back.
- `suppressions-in-comment-sweep`: Include lint and type-checker suppression comments in a comment sweep.
- `thin-importance-comment-check`: Before accepting a thinly justified decision on a comment marked important, investigate its symbol's behaviour and history.
- `trivial-flag-direct-fix`: Resolve simple accepted flags at once through edits such as removing an unused path or parameter, or calling the genuine interface.
- `named-workarounds-removed`: Eliminate every workaround the findings name.
- `cheapest-enforcement-offer`: For other constraint comments, propose the least costly enforcement available in scope, whether a type, runtime check, test or CI lint.
- `encoding-approval-gate`: Apply an encoding only with approval, through the route the caller names or given by the caller in advance.
- `encode-then-delete`: When an encoding is approved, add the enforcement and then remove the comment.
- `unencoded-constraint-kept-and-reported`: Without an approved enforcement, keep a constraint comment, report the constraint as open and sketch any out-of-scope work.
- `comment-sweep-report`: Report the comments deleted, those restored on proof, those kept and flagged, the fixes, the enforcements offered and done, the constraints left unenforced and the open items.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/no-comments#merge-base-through-tree-scope** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/no-comments#named-scope-first** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/no-comments#critic-out-of-bounds-refused** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/no-comments#kept-code-not-guilty** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/no-comments#reshape-flags-stay-open** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/no-comments#missed-suppression-audit** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/no-comments#thin-importance-comment-check** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/no-comments#trivial-flag-direct-fix** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/no-comments#named-workarounds-removed** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/no-comments#cheapest-enforcement-offer** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/no-comments#encoding-approval-gate** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/no-comments#encode-then-delete** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/no-comments#unencoded-constraint-reported** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/no-comments#comment-audit-report** `pstack/skills/no-comments/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:016): Completes pending 2026-11-06-batch-p1:086: comment-sweep-report is written at .claude/skills/no-comments/SKILL.md:47-50 (plan 63; a new unit, so no frozen word…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:015): Completes pending 2026-11-06-batch-p1:085: unencoded-constraint-kept-and-reported is written at .claude/skills/no-comments/SKILL.md:45-46 (plan 63; a new unit,…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:014): Completes pending 2026-11-06-batch-p1:084: encode-then-delete is written at .claude/skills/no-comments/SKILL.md:44 (plan 63; a new unit, so no frozen wording).
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:013): Completes pending 2026-11-06-batch-p1:083: encoding-approval-gate is written at .claude/skills/no-comments/SKILL.md:42-43 (plan 63; a new unit, so no frozen wo…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:012): Completes pending 2026-11-06-batch-p1:082: cheapest-enforcement-offer is written at .claude/skills/no-comments/SKILL.md:38-41 (plan 63; a new unit, so no froze…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:011): Completes pending 2026-11-06-batch-p1:077: named-workarounds-removed is written at .claude/skills/no-comments/SKILL.md:34-36 (plan 63; a new unit, so no frozen…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:010): Completes pending 2026-11-06-batch-p1:074: trivial-flag-direct-fix is written at .claude/skills/no-comments/SKILL.md:32-33 (plan 63; a new unit, so no frozen w…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:009): Completes pending 2026-11-06-batch-p1:071: thin-importance-comment-check is written at .claude/skills/no-comments/SKILL.md:22-24 (plan 63; a new unit, so no fr…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:008): Completes pending 2026-11-06-batch-p1:069: suppressions-in-comment-sweep is written at .claude/skills/no-comments/SKILL.md:21 (plan 63; a new unit, so no froze…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:007): Completes pending 2026-11-06-batch-p1:067: reshape-flags-open-apart-from-comment is written at .claude/skills/no-comments/SKILL.md:25-29 (plan 63; a new unit, …
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:006): Completes pending 2026-11-06-batch-p1:066: kept-code-not-guilty is written at .claude/skills/no-comments/SKILL.md:30 (plan 63; a new unit, so no frozen wording…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:005): Completes pending 2026-11-06-batch-p1:063: comment-pass-stays-in-bounds is written at .claude/skills/no-comments/SKILL.md:19-20 (plan 63; a new unit, so no fro…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:004): Completes pending 2026-11-06-batch-p1:057: named-scope-first is written at .claude/skills/no-comments/SKILL.md:15 (plan 63; a new unit, so no frozen wording).
- `2026-11-12` **adopt** (2026-11-12-batch-p1-no-comments:003): Completes pending 2026-11-06-batch-p1:056: merge-base-through-tree-scope is written at .claude/skills/no-comments/SKILL.md:15-18 (plan 63; a new unit, so no fr…
- `2026-11-12` **add** (2026-11-12-batch-p1-no-comments:001): Owner rulings of 2026-11-05 §E (no-comments: a principle for the rules plus a manual skill for the sweep; persona dropped; when unsure, keep and flag) and §G (…
- `2026-11-06` **adopt-merged** (2026-11-06-batch-p1:087): Checkpoint at 4dd1d05 for the owner's trait rulings: 20 adopt, 11 reject.
- `2026-11-06` **adopt** (2026-11-06-batch-p1:086) *(superseded)*: Owner ruling 2026-11-06: Prevents: A sweep that ends with no way to see what it removed, what it left in doubt or what stays open. Lands in no-comments, the ne…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:085) *(superseded)*: Owner ruling 2026-11-06: Prevents: A real constraint lost with its comment, with no check to replace it and only a line in a report to remember it by. Lands in…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:084) *(superseded)*: Owner ruling 2026-11-06: Prevents: A constraint with no comment and no check, because the deletion came first and the check never landed. Lands in no-comments,…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:083) *(superseded)*: Owner ruling 2026-11-06: Prevents: New checks added to a repository that nobody agreed to, under cover of a comment sweep. Lands in no-comments, the new manual…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:082) *(superseded)*: Owner ruling 2026-11-06: Prevents: A constraint that stays only a comment, which nothing enforces, when a small check would hold it. Lands in no-comments, the …
- `2026-11-06` **adopt** (2026-11-06-batch-p1:077) *(superseded)*: Owner ruling 2026-11-06: Prevents: A workaround whose comment went while the workaround itself stayed. Lands in no-comments, the new manual skill for the sweep…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:074) *(superseded)*: Owner ruling 2026-11-06: Prevents: A dead path the sweep exposed, left in place and reported when one edit would have removed it. Lands in no-comments, the new…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:071) *(superseded)*: Owner ruling 2026-11-06: Prevents: A comment marked important judged on its own say-so, either way. Lands in no-comments, the new manual skill for the sweep, w…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:069) *(superseded)*: Owner ruling 2026-11-06: Prevents: A suppression left hiding a real error because the sweep read only prose comments. Lands in no-comments, the new manual skil…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:067) *(superseded)*: Owner ruling 2026-11-06: Prevents: Surprising code left as it is because a comment went and the reason to restructure went with it, or a doubtful comment left …
- `2026-11-06` **adopt** (2026-11-06-batch-p1:066) *(superseded)*: Owner ruling 2026-11-06: Prevents: A sweep that reports deliberately kept code as a defect. Lands in no-comments, the new manual skill for the sweep. Upstream:…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:063) *(superseded)*: Owner ruling 2026-11-06: Prevents: A comment sweep that rewrites code or wanders outside the files it was given. Lands in no-comments, the new manual skill for…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:057) *(superseded)*: Owner ruling 2026-11-06: Prevents: A sweep that ignores the files the person named and takes the whole branch. Lands in no-comments, the new manual skill for t…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:056) *(superseded)*: Owner ruling 2026-11-06: Prevents: A sweep run over the wrong files because nobody named any. Lands in no-comments, the new manual skill for the sweep. Upstrea…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-04-upstream-cursor_plugins-4dd1d05-batch-p1.md](../../reviews/2026-11-04-upstream-cursor_plugins-4dd1d05-batch-p1.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `cheapest-enforcement-offer`:
  - `cursor_plugins:skill:pstack/skills/no-comments#cheapest-enforcement-offer` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `comment-pass-stays-in-bounds`:
  - `cursor_plugins:skill:pstack/skills/no-comments#critic-out-of-bounds-refused` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `comment-sweep-report`:
  - `cursor_plugins:skill:pstack/skills/no-comments#comment-audit-report` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `encode-then-delete`:
  - `cursor_plugins:skill:pstack/skills/no-comments#encode-then-delete` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `encoding-approval-gate`:
  - `cursor_plugins:skill:pstack/skills/no-comments#encoding-approval-gate` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `kept-code-not-guilty`:
  - `cursor_plugins:skill:pstack/skills/no-comments#kept-code-not-guilty` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `merge-base-through-tree-scope`:
  - `cursor_plugins:skill:pstack/skills/no-comments#merge-base-through-tree-scope` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `named-scope-first`:
  - `cursor_plugins:skill:pstack/skills/no-comments#named-scope-first` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `named-workarounds-removed`:
  - `cursor_plugins:skill:pstack/skills/no-comments#named-workarounds-removed` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `reshape-flags-open-apart-from-comment`:
  - `cursor_plugins:skill:pstack/skills/no-comments#reshape-flags-stay-open` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `suppressions-in-comment-sweep`:
  - `cursor_plugins:skill:pstack/skills/no-comments#missed-suppression-audit` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `thin-importance-comment-check`:
  - `cursor_plugins:skill:pstack/skills/no-comments#thin-importance-comment-check` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `trivial-flag-direct-fix`:
  - `cursor_plugins:skill:pstack/skills/no-comments#trivial-flag-direct-fix` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `unencoded-constraint-kept-and-reported`:
  - `cursor_plugins:skill:pstack/skills/no-comments#unencoded-constraint-reported` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
