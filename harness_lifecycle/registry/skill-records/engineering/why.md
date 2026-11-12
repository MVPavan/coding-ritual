---
skill: why
domain: engineering
stage: Discovery
substage: Research
secondary: []
family:
aliases: []
status: active
---
# why

Use to answer why something in this project is the way it is (code, a document, a decision, config, a tracker record): what was decided about it, what motivated it, or which change brought a regression and for what reason, from the project's own record, cited at the strength the evidence has. How it works now is how; evidence from outside the project is research; a failure whose cause is unknown is systematic-debugging. At top level, a question that should end in that answer is the investigation playbook.

**Boundary:** One cited, read-only answer about why something in this project is the way it is, or what was decided about it, from the project's own record (git, Beads, decision records, docs). How it works now is how, evidence from outside the project is research, past agent sessions are recall once it exists, an unexplained failure is systematic-debugging, and a saved answer is the investigation playbook.

<!-- registry:generated traits -->
- `read-only-explanation`: Change nothing while explaining, not even temporary instrumentation.
- `immaterial-ambiguity-reading`: State the reading taken of a target whose ambiguity would not materially change the answer, and proceed.
- `gather-without-concluding`: Collect the evidence in full before concluding, forming no answer and picking no side while gathering.
- `code-anchor-first`: Before searching, fix the files, lines, symbols and last commits with blame and rename-following log.
- `named-record-first`: Fetch the records a seed commit names, with their comments, before searching by keyword.
- `target-derived-search-terms`: Build search terms from the target's feature name or business term, symbols, author, error strings and path, trying several wordings.
- `local-evidence-sources`: Search commit messages, Beads, decision records, docs, inline markers, changelogs, tests and co-changed files for motivation, adding another source only if it is available.
- `pickaxe-history-search`: Search history for commits whose diffs add, remove or match a string or pattern.
- `full-record-reading`: Read the complete commit message and diff, and the decision or bead discussion, behind any anchor or excerpt before relying on it.
- `record-lineage-walk`: From a record, follow its parent and duplicate links to the item that carries the motive.
- `recency-bias-check`: Trace past the latest commit, which is not authoritative, to the earlier decisions behind the current shape.
- `embedded-hypothesis-check`: Treat a guess inside the question as one candidate to test independently, then confirm or refute it with citations.
- `confidence-tiers`: Place each claim in one tier by its evidence, Direct when an author's written words state the reason, Supported when several indirect items converge, Inferred when a reasonable reading has no explicit support, and Speculative when other explanations fit equally well, phrasing the first two confidently with citations, Inferred with hedges and its reasoning chain, and Speculative as a guess.
- `adjacent-citation-gate`: Use words asserting cause, intent, achieved effect or a group decision only on Direct or Supported claims, with a specific citation beside them.
- `code-not-intent-evidence`: Never cite code or a diff as proof of its author's intent.
- `no-retrofitted-rationale`: Do not impose a tidy justification on messy history or presume the author chose correctly and reason backward.
- `consistency-is-not-intent`: Do not read a repeated pattern as a deliberate choice, since it may be copying.
- `absence-is-not-evidence`: Do not read a lack of mention as proof that something was not a concern.
- `contradiction-shown`: Show conflicting sources side by side with citations, leaving the call to the user.
- `competing-hypotheses-section`: When the record fits several stories, give each its evidence for and against, with no forced winner.
- `searched-and-unknown`: Report an unknown with exactly what was searched, where and with which terms.
- `unreachable-data-is-gap`: Report data you could not reach, through a missing tool, denied access, retention or deletion, as a coverage gap and never as a null result.
- `sources-consulted-line`: List each source searched, empty or skipped, with the reason.
- `constraints-before-change`: When a change follows, turn the findings into preserve, change, avoid and risk lists.
- `pr-discussion-pull`: For each substantive commit, read the pull request body, linked issues, comments and reviews.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/how#stated-scope-reading** `pstack/skills/how/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#stated-scope-reading** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/how#size-gated-explorers** `pstack/skills/how/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/how#explanation-sections** `pstack/skills/how/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/how#cited-flow-walkthrough** `pstack/skills/how/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/how#reconcile-by-reading** `pstack/skills/how/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#gather-without-concluding** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#code-anchor-first** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#named-record-first** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#target-derived-search-terms** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#evidence-category-fanout** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#repo-evidence-inventory** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#incident-commit-signals** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#pickaxe-history-search** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#read-whole-item** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#record-lineage-walk** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#recency-bias-check** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#embedded-hypothesis-check** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#confidence-tiers** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#adjacent-citation-gate** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#code-not-intent-evidence** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#no-retrofitted-rationale** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#consistency-is-not-intent** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#absence-is-not-evidence** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#contradiction-shown** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#competing-hypotheses-section** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#searched-and-unknown** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#unreachable-data-is-gap** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#sources-consulted-line** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#constraints-before-change** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/why#pr-discussion-pull** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-10` **update** (2026-11-10-renames-splits:131): Coordinator fix for critic-21b F1 (scratchpad/mvp-stack/critic-21b.md): a question about what was decided in this project has a present route (why) while recal…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:120): Completes pending 2026-11-10-renames-splits:032: pr-discussion-pull is written at .claude/skills/why/SKILL.md:38-39, .claude/skills/why/references/pull-request…
- `2026-11-10` **update** (2026-11-10-renames-splits:114): Owner rulings C of 2026-11-05, I1 and I4 of 2026-11-06 and K of 2026-11-10 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 14a U6. Body is the hist…
- `2026-11-10` **split** (2026-11-10-renames-splits:113): Owner rulings C of 2026-11-05, I1 and I4 of 2026-11-06 and K of 2026-11-10 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 14a U6. explain-code's c…
- `2026-11-10` **rename** (2026-11-10-renames-splits:111): Owner rulings C of 2026-11-05, I1 and I4 of 2026-11-06 and K of 2026-11-10 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 14a U6. The skill explai…
- `2026-11-10` **adopt** (2026-11-10-renames-splits:032) *(superseded)*: Owner ruling 2026-11-10 on the why sheet, as recommended: Prevents: a why answer stopping at the commit message when a linked pull request's review holds the r…
- `2026-11-01` **adopt** (2026-11-01-batch-1:266): Completes pending 2026-11-01-batch-1:047: constraints-before-change is written at .claude/skills/explain-code/references/history.md:66-67, read against its def…
- `2026-11-01` **adopt** (2026-11-01-batch-1:265): Completes pending 2026-11-01-batch-1:032: sources-consulted-line is written at .claude/skills/explain-code/references/history.md:65, read against its definitio…
- `2026-11-01` **adopt** (2026-11-01-batch-1:264): Completes pending 2026-11-01-batch-1:067: unreachable-data-is-gap is written at .claude/skills/explain-code/references/history.md:63-64, read against its defin…
- `2026-11-01` **adopt** (2026-11-01-batch-1:263): Completes pending 2026-11-01-batch-1:052: searched-and-unknown is written at .claude/skills/explain-code/references/history.md:62, read against its definition …
- `2026-11-01` **adopt** (2026-11-01-batch-1:262): Completes pending 2026-11-01-batch-1:081: competing-hypotheses-section is written at .claude/skills/explain-code/references/history.md:60-61, read against its …
- `2026-11-01` **adopt** (2026-11-01-batch-1:261): Completes pending 2026-11-01-batch-1:058: contradiction-shown is written at .claude/skills/explain-code/references/history.md:58-59, read against its definitio…
- `2026-11-01` **adopt** (2026-11-01-batch-1:260): Completes pending 2026-11-01-batch-1:056: absence-is-not-evidence is written at .claude/skills/explain-code/references/history.md:54, read against its definiti…
- `2026-11-01` **adopt** (2026-11-01-batch-1:259): Completes pending 2026-11-01-batch-1:055: consistency-is-not-intent is written at .claude/skills/explain-code/references/history.md:53, read against its defini…
- `2026-11-01` **adopt** (2026-11-01-batch-1:258): Completes pending 2026-11-01-batch-1:054: no-retrofitted-rationale is written at .claude/skills/explain-code/references/history.md:51-52, read against its defi…
- `2026-11-01` **adopt** (2026-11-01-batch-1:257): Completes pending 2026-11-01-batch-1:061: code-not-intent-evidence is written at .claude/skills/explain-code/references/history.md:50, read against its definit…
- `2026-11-01` **adopt** (2026-11-01-batch-1:256): Completes pending 2026-11-01-batch-1:050: adjacent-citation-gate is written at .claude/skills/explain-code/references/history.md:44-46, read against its defini…
- `2026-11-01` **adopt** (2026-11-01-batch-1:255): Completes pending 2026-11-01-batch-1:049: confidence-tiers is written at .claude/skills/explain-code/references/history.md:35-42, read against its definition (…
- `2026-11-01` **adopt** (2026-11-01-batch-1:254): Completes pending 2026-11-01-batch-1:057: embedded-hypothesis-check is written at .claude/skills/explain-code/references/history.md:30-31, read against its def…
- `2026-11-01` **adopt** (2026-11-01-batch-1:253): Completes pending 2026-11-01-batch-1:048: recency-bias-check is written at .claude/skills/explain-code/references/history.md:27-28, read against its definition…
- `2026-11-01` **adopt** (2026-11-01-batch-1:252): Completes pending 2026-11-01-batch-1:105: record-lineage-walk is written at .claude/skills/explain-code/references/history.md:25-26, read against its definitio…
- `2026-11-01` **adopt** (2026-11-01-batch-1:251): Completes pending 2026-11-01-batch-1:066: full-record-reading is written at .claude/skills/explain-code/references/history.md:23-24, read against its definitio…
- `2026-11-01` **adopt** (2026-11-01-batch-1:250): Completes pending 2026-11-01-batch-1:036: pickaxe-history-search is written at .claude/skills/explain-code/references/history.md:21-22, read against its defini…
- `2026-11-01` **adopt** (2026-11-01-batch-1:249): Completes pending 2026-11-01-batch-1:039: local-evidence-sources is written at .claude/skills/explain-code/references/history.md:18-20, read against its defini…
- `2026-11-01` **adopt** (2026-11-01-batch-1:248): Completes pending 2026-11-01-batch-1:035: local-evidence-sources is written at .claude/skills/explain-code/references/history.md:18-20, read against its defini…
- `2026-11-01` **adopt** (2026-11-01-batch-1:247): Completes pending 2026-11-01-batch-1:034: local-evidence-sources is written at .claude/skills/explain-code/references/history.md:18-20, read against its defini…
- `2026-11-01` **adopt** (2026-11-01-batch-1:246): Completes pending 2026-11-01-batch-1:103: target-derived-search-terms is written at .claude/skills/explain-code/references/history.md:16-17, read against its d…
- `2026-11-01` **adopt** (2026-11-01-batch-1:245): Completes pending 2026-11-01-batch-1:102: named-record-first is written at .claude/skills/explain-code/references/history.md:14-15, read against its definition…
- `2026-11-01` **adopt** (2026-11-01-batch-1:244): Completes pending 2026-11-01-batch-1:028: code-anchor-first is written at .claude/skills/explain-code/references/history.md:12-13, read against its definition …
- `2026-11-01` **adopt** (2026-11-01-batch-1:243): Completes pending 2026-11-01-batch-1:045: gather-without-concluding is written at .claude/skills/explain-code/references/history.md:9-10, read against its defi…
- `2026-11-01` **adopt** (2026-11-01-batch-1:242): Completes pending 2026-11-01-batch-1:006: reconcile-by-reading is written at .claude/skills/explain-code/SKILL.md:28-29, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:241): Completes pending 2026-11-01-batch-1:005: cited-flow-walkthrough is written at .claude/skills/explain-code/SKILL.md:37-38, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:240): Completes pending 2026-11-01-batch-1:004: explanation-sections is written at .claude/skills/explain-code/SKILL.md:33-40, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:239): Completes pending 2026-11-01-batch-1:002: angles-when-wide is written at .claude/skills/explain-code/SKILL.md:21-26, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:238): Completes pending 2026-11-01-batch-1:021: immaterial-ambiguity-reading is written at .claude/skills/explain-code/SKILL.md:18-19, read against its definition (T…
- `2026-11-01` **adopt** (2026-11-01-batch-1:237): Completes pending 2026-11-01-batch-1:001: immaterial-ambiguity-reading is written at .claude/skills/explain-code/SKILL.md:18-19, read against its definition (T…
- `2026-11-01` **add** (2026-11-01-batch-1:234): New skill, plan 4.2 and ruling 4: one cited, read-only answer about this repository's code. The how path is its core; the history and decision branches each na…
- `2026-11-01` **adopt-merged** (2026-11-01-batch-1:192): Checkpoint at 4dd1d05 for the owner's trait rulings: 26 adopt, 28 defer, 43 reject.
- `2026-11-01` **adopt-merged** (2026-11-01-batch-1:191) *(superseded)*: Checkpoint at 4dd1d05 for the owner's trait rulings: 5 adopt, 15 reject.
- `2026-11-01` **adopt** (2026-11-01-batch-1:105) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: references/sources/linear.md:21, 38.
- `2026-11-01` **adopt** (2026-11-01-batch-1:103) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: references/sources/linear.md:20, references/sources/notion.md:20-25, reference…
- `2026-11-01` **adopt** (2026-11-01-batch-1:102) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: references/sources/linear.md:19.
- `2026-11-01` **adopt** (2026-11-01-batch-1:081) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: references/synthesizer-prompt.md:80-86.
- `2026-11-01` **adopt** (2026-11-01-batch-1:067) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: SKILL.md:72, references/sources/databricks.md:12, 59, references/sources/datad…
- `2026-11-01` **adopt** (2026-11-01-batch-1:066) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md, into `full-record-reading`. Upstream: references/investigator-prompt.md:37, references/s…
- `2026-11-01` **adopt** (2026-11-01-batch-1:061) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: references/epistemics.md:71, references/investigator-prompt.md:47-48.
- `2026-11-01` **adopt** (2026-11-01-batch-1:058) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: references/epistemics.md:63, references/investigator-prompt.md:41, 78, referen…
- `2026-11-01` **adopt** (2026-11-01-batch-1:057) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: references/epistemics.md:59.
- `2026-11-01` **adopt** (2026-11-01-batch-1:056) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: references/epistemics.md:55.
- `2026-11-01` **adopt** (2026-11-01-batch-1:055) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: references/epistemics.md:55.
- `2026-11-01` **adopt** (2026-11-01-batch-1:054) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: references/epistemics.md:55.
- `2026-11-01` **adopt** (2026-11-01-batch-1:052) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: references/epistemics.md:35-37, 67, references/synthesizer-prompt.md:90-94, re…
- `2026-11-01` **adopt** (2026-11-01-batch-1:050) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: references/epistemics.md:41, references/synthesizer-prompt.md:32.
- `2026-11-01` **adopt** (2026-11-01-batch-1:049) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: references/epistemics.md:7, 11-13, 17-19, 23-25, 29-31, 43, references/synthes…
- `2026-11-01` **adopt** (2026-11-01-batch-1:048) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: SKILL.md:98.
- `2026-11-01` **adopt** (2026-11-01-batch-1:047) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: SKILL.md:94.
- `2026-11-01` **adopt** (2026-11-01-batch-1:045) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: references/investigator-prompt.md:51.
- `2026-11-01` **adopt** (2026-11-01-batch-1:039) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md, into `local-evidence-sources`. Upstream: references/sources/incident-postmortem.md:5.
- `2026-11-01` **adopt** (2026-11-01-batch-1:036) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: references/sources/code-archaeology.md:25-28.
- `2026-11-01` **adopt** (2026-11-01-batch-1:035) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md, into `local-evidence-sources`. Upstream: references/sources/code-archaeology.md:5-12, 44…
- `2026-11-01` **adopt** (2026-11-01-batch-1:034) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md, into `local-evidence-sources`. Upstream: SKILL.md:49, 60.
- `2026-11-01` **adopt** (2026-11-01-batch-1:032) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: SKILL.md:31, 70, 92, references/synthesizer-prompt.md:99-107.
- `2026-11-01` **adopt** (2026-11-01-batch-1:028) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, references/history.md. Upstream: SKILL.md:27, references/sources/code-archaeology.md:22.
- `2026-11-01` **adopt** (2026-11-01-batch-1:021) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, SKILL.md, into `immaterial-ambiguity-reading`. Upstream: SKILL.md:23.
- `2026-11-01` **adopt** (2026-11-01-batch-1:006) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, SKILL.md. Upstream: references/explainer-prompt.md:19.
- `2026-11-01` **adopt** (2026-11-01-batch-1:005) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, SKILL.md. Upstream: references/explainer-prompt.md:36-38.
- `2026-11-01` **adopt** (2026-11-01-batch-1:004) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, SKILL.md. Upstream: references/explainer-prompt.md:30, 33, 43, 46, SKILL.md:36.
- `2026-11-01` **adopt** (2026-11-01-batch-1:002) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, SKILL.md, into `angles-when-wide`. Upstream: SKILL.md:17-18, 24, references/explainer-prompt.md:19.
- `2026-11-01` **adopt** (2026-11-01-batch-1:001) *(superseded)*: Owner ruling 2026-11-01: Lands in explain-code, SKILL.md, into `immaterial-ambiguity-reading`. Upstream: SKILL.md:15.
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-09-upstream-cursor_plugins-4dd1d05.md](../../reviews/2026-11-09-upstream-cursor_plugins-4dd1d05.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `absence-is-not-evidence`:
  - `cursor_plugins:skill:pstack/skills/why#absence-is-not-evidence` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `adjacent-citation-gate`:
  - `cursor_plugins:skill:pstack/skills/why#adjacent-citation-gate` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `angles-when-wide`:
  - `cursor_plugins:skill:pstack/skills/how#size-gated-explorers` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe; withdrawn 2026-11-10)
- `cited-flow-walkthrough`:
  - `cursor_plugins:skill:pstack/skills/how#cited-flow-walkthrough` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe; withdrawn 2026-11-10)
- `code-anchor-first`:
  - `cursor_plugins:skill:pstack/skills/why#code-anchor-first` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `code-not-intent-evidence`:
  - `cursor_plugins:skill:pstack/skills/why#code-not-intent-evidence` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `competing-hypotheses-section`:
  - `cursor_plugins:skill:pstack/skills/why#competing-hypotheses-section` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `confidence-tiers`:
  - `cursor_plugins:skill:pstack/skills/why#confidence-tiers` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `consistency-is-not-intent`:
  - `cursor_plugins:skill:pstack/skills/why#consistency-is-not-intent` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `constraints-before-change`:
  - `cursor_plugins:skill:pstack/skills/why#constraints-before-change` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `contradiction-shown`:
  - `cursor_plugins:skill:pstack/skills/why#contradiction-shown` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `embedded-hypothesis-check`:
  - `cursor_plugins:skill:pstack/skills/why#embedded-hypothesis-check` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `explanation-sections`:
  - `cursor_plugins:skill:pstack/skills/how#explanation-sections` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe; withdrawn 2026-11-10)
- `full-record-reading`:
  - `cursor_plugins:skill:pstack/skills/why#read-whole-item` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `gather-without-concluding`:
  - `cursor_plugins:skill:pstack/skills/why#gather-without-concluding` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `immaterial-ambiguity-reading`:
  - `cursor_plugins:skill:pstack/skills/how#stated-scope-reading` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/why#stated-scope-reading` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `local-evidence-sources`:
  - `cursor_plugins:skill:pstack/skills/why#evidence-category-fanout` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/why#incident-commit-signals` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/why#repo-evidence-inventory` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `named-record-first`:
  - `cursor_plugins:skill:pstack/skills/why#named-record-first` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `no-retrofitted-rationale`:
  - `cursor_plugins:skill:pstack/skills/why#no-retrofitted-rationale` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `pickaxe-history-search`:
  - `cursor_plugins:skill:pstack/skills/why#pickaxe-history-search` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `pr-discussion-pull`:
  - `cursor_plugins:skill:pstack/skills/why#pr-discussion-pull` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `recency-bias-check`:
  - `cursor_plugins:skill:pstack/skills/why#recency-bias-check` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `reconcile-by-reading`:
  - `cursor_plugins:skill:pstack/skills/how#reconcile-by-reading` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe; withdrawn 2026-11-10)
- `record-lineage-walk`:
  - `cursor_plugins:skill:pstack/skills/why#record-lineage-walk` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `searched-and-unknown`:
  - `cursor_plugins:skill:pstack/skills/why#searched-and-unknown` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `sources-consulted-line`:
  - `cursor_plugins:skill:pstack/skills/why#sources-consulted-line` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `target-derived-search-terms`:
  - `cursor_plugins:skill:pstack/skills/why#target-derived-search-terms` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `unreachable-data-is-gap`:
  - `cursor_plugins:skill:pstack/skills/why#unreachable-data-is-gap` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
