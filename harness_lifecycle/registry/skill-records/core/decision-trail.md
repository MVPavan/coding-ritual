---
skill: decision-trail
domain: core
stage: X
substage: Continuity
secondary: []
family: handoff
aliases: []
status: active
---
# decision-trail

Use when a calling playbook names it, or when asked for a reviewable trail of a long run someone will check after stepping away: an append-only TSV of decisions with evidence pointers, closed by an audit and an independent critic. A metric climb is the hillclimb playbook, which calls this. Skip a resume note, a bead note or a short attempt record.

**Boundary:** Keeps one run's decisions as an append-only log, audits it and gets it independently reviewed; work state is beads, a plan's run is implement, a compact attempt record is performance-optimization, and reviewing other artifacts is review.

<!-- registry:generated traits -->
- `single-tsv-decision-log`: Keep one authoritative decision log as a single TSV file with one single-line row per decision.
- `evidence-pointer-cell`: Make a row's evidence cell a resolvable pointer such as a commit, pull request, file and line or artifact path, never narrative.
- `trail-six-columns`: Give every row the fixed columns ts in ISO8601, phase or workstream, the decision in one line, why, evidence, and result as an outcome or state.
- `caller-trail-columns`: Let a caller add declared columns after a trail's fixed ones, the same set on every call.
- `plain-row-wording`: Write rows the way you would tell a colleague, in concrete words, spelling a guiding principle out in place of citing it as a tag.
- `named-cell-row-helper`: Append rows through a helper that takes named cells and declared extra columns, and writes nothing when a cell is missing, unknown or undeclared.
- `decision-points-only`: Log decision points and checkpoints (a chosen fork, a finished unit with its verification, a pivot or revert with its cause, a surfaced blocker, a fixed gate), never each action or a self-evident step.
- `row-per-iteration`: Have a looping run write one row for each iteration.
- `creates-log-parent`: Have the log helper create a missing parent directory.
- `locked-single-header`: Hold an exclusive lock across reading and appending, so simultaneous first writers make one header and rows never interleave.
- `append-mode-writes`: Write the header and rows only in append mode, so a false empty-file test costs a stray header and never the rows.
- `automatic-utc-stamp`: Have the log helper stamp each row with the current UTC time so the caller supplies none.
- `cell-whitespace-strip`: Replace tabs, newlines and carriage returns in each cell with spaces.
- `numeric-safe-formula-quote`: Quote a cell starting with a character a spreadsheet parses as a formula, unless it is a plain signed number or percentage.
- `run-boundary`: Count one agent conversation with its later turns and summaries as one run, and a pickup, replacement agent or new chat as a new one.
- `start-row-triggers`: Have a run adding to a log with rows write a `start` row first, and on returning read the log's tail and write a fresh one if another run's `start` has appeared.
- `start-row-contents`: Have a `start` row name the timestamp range of the rows this run did not write and identify this run in its evidence, using the `start` phase for nothing else.
- `trail-location-rule`: Keep a trail at the caller's path, else at an ignored scratch path by slug, else in Git's own directory, and outside Git in the working folder, saying so in the reply.
- `proposed-trail-commit`: Propose committing a trail only when a reviewer needs it to trust the outcome, and commit only with authority.
- `append-only-supersede`: Never edit or delete a ledger record; correct or reverse one by appending a record that supersedes it.
- `end-of-run-audit`: Before handing back, check the log for truthfulness against what happened in the run.
- `no-cross-project-transcript-search`: Never search across project transcript folders during an audit, because that exposes unrelated private conversations.
- `audit-own-stretches`: Limit an audit to this run's row stretches, each from one of its `start` rows or the log's first row to the next `start` row of another run.
- `verified-record-row-walk`: Check each audited row against a real event only in an event record the caller names, verified and scoped to this workspace.
- `evidence-resolves-check`: Check that each audited row's pointer resolves and supports what the row says.
- `unlogged-fork-gap`: Treat a fork, pivot or abandoned path that shaped the work with no row as a gap, and add the row in the audit.
- `audit-supersedes-in-place-of-editing`: Have an audit change no row, even an invented one, and add a row superseding it with what really happened and a pointer that resolves.
- `foreign-row-on-own-evidence`: Supersede a row outside the audited stretches only when this run's own work shows it to be wrong.
- `same-family-or-unreviewed`: Have a critic from another model family review the trail before hand-back, one of the same family only with the owner's approval, and otherwise report it not reviewed, never reviewing your own run.
- `evidence-pointer-review`: Give a trail's critic the trail and the evidence each row points at, or the trail and a verified workspace-scoped record when one is named.
- `attention-scan-not-redo`: Have the trail's reviewer look for what is suboptimal or risky for the user's attention and not repeat the work.
- `trail-review-flags`: Have the trail's reviewer flag weak or absent evidence, checks skipped or claimed without proof, choices risky in hindsight, and gaps a casual read would miss.
- `attention-with-coverage`: End a reply with Attention naming the reviewer or `not reviewed` with its reason, each flag with its rows or no flags, and, after an evidence-pointer review, transcript coverage and unlogged-fork detection as unavailable.
- `script-evidence-preference`: Favour evidence generated by committed scripts over hand-made one-off evidence.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/show-me-your-work#single-tsv-decision-log** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#evidence-pointer-cell** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#trail-six-columns** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#plain-row-wording** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#positional-row-helper** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#decision-points-only** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#row-per-iteration** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#creates-log-parent** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#header-on-empty-file** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#append-mode-writes** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#automatic-utc-stamp** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#cell-whitespace-strip** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#formula-cell-quote** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#run-boundary** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#start-row-triggers** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#start-row-contents** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#local-log-default** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#commit-on-reviewer-need** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#append-only-supersede** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#end-of-run-audit** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#no-cross-project-transcript-search** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#audit-own-stretches** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#row-maps-to-real-event** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#evidence-resolves-check** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#unlogged-fork-gap** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#audit-supersedes-in-place-of-editing** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#foreign-row-on-own-evidence** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#other-family-trail-review** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#trail-and-transcript-review** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#attention-scan-not-redo** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#trail-review-flags** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#attention-section** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/show-me-your-work#script-evidence-preference** `pstack/skills/show-me-your-work/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/figure-it-out#commit-on-reviewer-need** `pstack/skills/figure-it-out/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-06` **adopt** (2026-11-06-batch-p1:258): Owner ruling 2026-11-06: `decision-trail`, which the Trail step calls, already holds its modified form: it proposes a commit and commits only with authority, a…
- `2026-11-02` **adopt** (2026-11-02-batch-2:158): Completes pending 2026-11-02-batch-2:085: script-evidence-preference is written at .claude/skills/decision-trail/SKILL.md:26-27, read against its definition (T…
- `2026-11-02` **adopt** (2026-11-02-batch-2:157): Completes pending 2026-11-02-batch-2:081: attention-with-coverage is written at .claude/skills/decision-trail/SKILL.md:67-73, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:156): Completes pending 2026-11-02-batch-2:080: trail-review-flags is written at .claude/skills/decision-trail/SKILL.md:59-60, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:155): Completes pending 2026-11-02-batch-2:078: attention-scan-not-redo is written at .claude/skills/decision-trail/SKILL.md:57-58, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:154): Completes pending 2026-11-02-batch-2:077: evidence-pointer-review is written at .claude/skills/decision-trail/SKILL.md:60-62, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:153): Completes pending 2026-11-02-batch-2:076: same-family-or-unreviewed is written at .claude/skills/decision-trail/SKILL.md:57, .claude/skills/decision-trail/SKIL…
- `2026-11-02` **adopt** (2026-11-02-batch-2:152): Completes pending 2026-11-02-batch-2:075: foreign-row-on-own-evidence is written at .claude/skills/decision-trail/SKILL.md:51-52, read against its definition (…
- `2026-11-02` **adopt** (2026-11-02-batch-2:151): Completes pending 2026-11-02-batch-2:074: audit-supersedes-in-place-of-editing is written at .claude/skills/decision-trail/SKILL.md:50-51, read against its def…
- `2026-11-02` **adopt** (2026-11-02-batch-2:150): Completes pending 2026-11-02-batch-2:073: unlogged-fork-gap is written at .claude/skills/decision-trail/SKILL.md:48-49, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:149): Completes pending 2026-11-02-batch-2:072: evidence-resolves-check is written at .claude/skills/decision-trail/SKILL.md:47, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:148): Completes pending 2026-11-02-batch-2:071: verified-record-row-walk is written at .claude/skills/decision-trail/SKILL.md:53-54, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:147): Completes pending 2026-11-02-batch-2:070: audit-own-stretches is written at .claude/skills/decision-trail/SKILL.md:43-45, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:146): Completes pending 2026-11-02-batch-2:069: no-cross-project-transcript-search is written at .claude/skills/decision-trail/SKILL.md:54-55, read against its defin…
- `2026-11-02` **adopt** (2026-11-02-batch-2:145): Completes pending 2026-11-02-batch-2:067: end-of-run-audit is written at .claude/skills/decision-trail/SKILL.md:43, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:144): Completes pending 2026-11-02-batch-2:066: append-only-supersede is written at .claude/skills/decision-trail/SKILL.md:33, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:143): Completes pending 2026-11-02-batch-2:065: proposed-trail-commit is written at .claude/skills/decision-trail/SKILL.md:15-17, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:142): Completes pending 2026-11-02-batch-2:064: trail-location-rule is written at .claude/skills/decision-trail/SKILL.md:12-15, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:141): Completes pending 2026-11-02-batch-2:063: start-row-contents is written at .claude/skills/decision-trail/SKILL.md:38-40, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:140): Completes pending 2026-11-02-batch-2:062: start-row-triggers is written at .claude/skills/decision-trail/SKILL.md:37-38, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:139): Completes pending 2026-11-02-batch-2:061: run-boundary is written at .claude/skills/decision-trail/SKILL.md:35-36, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:138): Completes pending 2026-11-02-batch-2:060: numeric-safe-formula-quote is written at .claude/skills/decision-trail/scripts/log_row.py:21-22, read against its def…
- `2026-11-02` **adopt** (2026-11-02-batch-2:137): Completes pending 2026-11-02-batch-2:059: cell-whitespace-strip is written at .claude/skills/decision-trail/scripts/log_row.py:20, read against its definition …
- `2026-11-02` **adopt** (2026-11-02-batch-2:136): Completes pending 2026-11-02-batch-2:058: automatic-utc-stamp is written at .claude/skills/decision-trail/scripts/log_row.py:52, read against its definition (T…
- `2026-11-02` **adopt** (2026-11-02-batch-2:135): Completes pending 2026-11-02-batch-2:057: append-mode-writes is written at .claude/skills/decision-trail/scripts/log_row.py:45-46, .claude/skills/decision-trai…
- `2026-11-02` **adopt** (2026-11-02-batch-2:134): Completes pending 2026-11-02-batch-2:056: locked-single-header is written at .claude/skills/decision-trail/scripts/log_row.py:46-54, read against its definitio…
- `2026-11-02` **adopt** (2026-11-02-batch-2:133): Completes pending 2026-11-02-batch-2:055: creates-log-parent is written at .claude/skills/decision-trail/scripts/log_row.py:44, read against its definition (T5…
- `2026-11-02` **adopt** (2026-11-02-batch-2:132): Completes pending 2026-11-02-batch-2:053: row-per-iteration is written at .claude/skills/decision-trail/SKILL.md:30, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:131): Completes pending 2026-11-02-batch-2:052: decision-points-only is written at .claude/skills/decision-trail/SKILL.md:28-30, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:130): Completes pending 2026-11-02-batch-2:050: named-cell-row-helper is written at .claude/skills/decision-trail/scripts/log_row.py:32-41, .claude/skills/decision-t…
- `2026-11-02` **adopt** (2026-11-02-batch-2:129): Completes pending 2026-11-02-batch-2:049: plain-row-wording is written at .claude/skills/decision-trail/SKILL.md:31-32, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:128): Completes pending 2026-11-02-batch-2:047: trail-six-columns is written at .claude/skills/decision-trail/SKILL.md:21-22, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:127): Completes pending 2026-11-02-batch-2:045: evidence-pointer-cell is written at .claude/skills/decision-trail/SKILL.md:25-26, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:126): Completes pending 2026-11-02-batch-2:044: single-tsv-decision-log is written at .claude/skills/decision-trail/SKILL.md:8-9, read against its definition (T5).
- `2026-11-02` **add** (2026-11-02-batch-2:087): New skill, plan 4.2 and MS8, map 3.2 and ruling 9: one run's decisions as an append-only TSV with evidence pointers, audited, reviewed by an independent critic…
- `2026-11-02` **adopt-merged** (2026-11-02-batch-2:086): Checkpoint at 4dd1d05 for the owner's trait rulings: 33 adopt, 9 reject.
- `2026-11-02` **adopt** (2026-11-02-batch-2:085) *(superseded)*: Owner ruling 2026-11-02: The owner chose to keep it. `AGENTS.md` already says to build a rerunnable tool when it supplies proof a reviewer needs and to keep it…
- `2026-11-02` **adopt** (2026-11-02-batch-2:081) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md, into `attention-with-coverage`. Upstream: SKILL.md:74.
- `2026-11-02` **adopt** (2026-11-02-batch-2:080) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md. Upstream: SKILL.md:69-72.
- `2026-11-02` **adopt** (2026-11-02-batch-2:078) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md. Upstream: SKILL.md:67.
- `2026-11-02` **adopt** (2026-11-02-batch-2:077) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md, into `evidence-pointer-review`. Upstream: SKILL.md:67.
- `2026-11-02` **adopt** (2026-11-02-batch-2:076) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md, into `same-family-or-unreviewed`. Upstream: SKILL.md:67. The owner confirmed it knowingly on 2026-1…
- `2026-11-02` **adopt** (2026-11-02-batch-2:075) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md. Upstream: SKILL.md:63.
- `2026-11-02` **adopt** (2026-11-02-batch-2:074) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md. Upstream: SKILL.md:63.
- `2026-11-02` **adopt** (2026-11-02-batch-2:073) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md. Upstream: SKILL.md:61.
- `2026-11-02` **adopt** (2026-11-02-batch-2:072) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md. Upstream: SKILL.md:60.
- `2026-11-02` **adopt** (2026-11-02-batch-2:071) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md, into `verified-record-row-walk`. Upstream: SKILL.md:59.
- `2026-11-02` **adopt** (2026-11-02-batch-2:070) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md. Upstream: SKILL.md:57, 63.
- `2026-11-02` **adopt** (2026-11-02-batch-2:069) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md. Upstream: SKILL.md:57.
- `2026-11-02` **adopt** (2026-11-02-batch-2:067) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md. Upstream: SKILL.md:57.
- `2026-11-02` **adopt** (2026-11-02-batch-2:066) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md. Upstream: SKILL.md:52. The whole mechanism matches: a decision log's rows are its records.
- `2026-11-02` **adopt** (2026-11-02-batch-2:065) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md, into `proposed-trail-commit`. Upstream: SKILL.md:48.
- `2026-11-02` **adopt** (2026-11-02-batch-2:064) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md, into `trail-location-rule`. Upstream: SKILL.md:46.
- `2026-11-02` **adopt** (2026-11-02-batch-2:063) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md. Upstream: SKILL.md:42.
- `2026-11-02` **adopt** (2026-11-02-batch-2:062) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md. Upstream: SKILL.md:42.
- `2026-11-02` **adopt** (2026-11-02-batch-2:061) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md. Upstream: SKILL.md:42.
- `2026-11-02` **adopt** (2026-11-02-batch-2:060) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, scripts/log_row.py, into `numeric-safe-formula-quote`. Upstream: SKILL.md:38, scripts/log.sh:26-38.
- `2026-11-02` **adopt** (2026-11-02-batch-2:059) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, scripts/log_row.py. Upstream: scripts/log.sh:26, 34.
- `2026-11-02` **adopt** (2026-11-02-batch-2:058) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, scripts/log_row.py. Upstream: scripts/log.sh:25.
- `2026-11-02` **adopt** (2026-11-02-batch-2:057) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, scripts/log_row.py. Upstream: scripts/log.sh:19-22, 40-42.
- `2026-11-02` **adopt** (2026-11-02-batch-2:056) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, scripts/log_row.py, into `locked-single-header`. Upstream: scripts/log.sh:21-23.
- `2026-11-02` **adopt** (2026-11-02-batch-2:055) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, scripts/log_row.py. Upstream: scripts/log.sh:14-17.
- `2026-11-02` **adopt** (2026-11-02-batch-2:053) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md. Upstream: SKILL.md:40.
- `2026-11-02` **adopt** (2026-11-02-batch-2:052) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md. Upstream: SKILL.md:40.
- `2026-11-02` **adopt** (2026-11-02-batch-2:050) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, scripts/log_row.py, into `named-cell-row-helper`. Upstream: SKILL.md:38, scripts/log.sh:1-9.
- `2026-11-02` **adopt** (2026-11-02-batch-2:049) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md. Upstream: SKILL.md:20, 36.
- `2026-11-02` **adopt** (2026-11-02-batch-2:047) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md. Upstream: SKILL.md:17-22, references/decision-log-template.tsv:1.
- `2026-11-02` **adopt** (2026-11-02-batch-2:045) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md. Upstream: SKILL.md:13, 21.
- `2026-11-02` **adopt** (2026-11-02-batch-2:044) *(superseded)*: Owner ruling 2026-11-02: Lands in decision-trail, SKILL.md. Upstream: SKILL.md:9, 13.
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-04-upstream-cursor_plugins-4dd1d05-batch-p1.md](../../reviews/2026-11-04-upstream-cursor_plugins-4dd1d05-batch-p1.md)
- [2026-11-02-upstream-cursor_plugins-4dd1d05-reconsider.md](../../reviews/2026-11-02-upstream-cursor_plugins-4dd1d05-reconsider.md)
- [2026-11-01-upstream-cursor_plugins-4dd1d05-batch-2.md](../../reviews/2026-11-01-upstream-cursor_plugins-4dd1d05-batch-2.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `append-mode-writes`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#append-mode-writes` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `append-only-supersede`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#append-only-supersede` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `attention-scan-not-redo`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#attention-scan-not-redo` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `attention-with-coverage`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#attention-section` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `audit-own-stretches`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#audit-own-stretches` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `audit-supersedes-in-place-of-editing`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#audit-supersedes-in-place-of-editing` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `automatic-utc-stamp`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#automatic-utc-stamp` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `cell-whitespace-strip`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#cell-whitespace-strip` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `creates-log-parent`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#creates-log-parent` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `decision-points-only`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#decision-points-only` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `end-of-run-audit`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#end-of-run-audit` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `evidence-pointer-cell`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#evidence-pointer-cell` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `evidence-pointer-review`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#trail-and-transcript-review` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `evidence-resolves-check`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#evidence-resolves-check` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `foreign-row-on-own-evidence`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#foreign-row-on-own-evidence` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `locked-single-header`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#header-on-empty-file` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `named-cell-row-helper`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#positional-row-helper` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `no-cross-project-transcript-search`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#no-cross-project-transcript-search` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `numeric-safe-formula-quote`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#formula-cell-quote` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `plain-row-wording`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#plain-row-wording` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `proposed-trail-commit`:
  - `cursor_plugins:skill:pstack/skills/figure-it-out#commit-on-reviewer-need` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#commit-on-reviewer-need` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `row-per-iteration`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#row-per-iteration` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `run-boundary`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#run-boundary` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `same-family-or-unreviewed`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#other-family-trail-review` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `script-evidence-preference`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#script-evidence-preference` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `single-tsv-decision-log`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#single-tsv-decision-log` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `start-row-contents`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#start-row-contents` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `start-row-triggers`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#start-row-triggers` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `trail-location-rule`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#local-log-default` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `trail-review-flags`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#trail-review-flags` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `trail-six-columns`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#trail-six-columns` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `unlogged-fork-gap`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#unlogged-fork-gap` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `verified-record-row-walk`:
  - `cursor_plugins:skill:pstack/skills/show-me-your-work#row-maps-to-real-event` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
