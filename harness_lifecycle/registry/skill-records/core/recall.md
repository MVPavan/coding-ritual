---
skill: recall
domain: core
stage: X
substage: Continuity
secondary: []
family:
aliases: []
status: active
---
# recall

Rebuild recent work in this project from past chats and the shared record (beads, commits) into one brief of where things stand and the next move. Use for /recall; resuming one known piece of work is session-pickup.

**Boundary:** Rebuilds recent work in this project from past chats and the shared record into one brief of where it stands and the next move; resuming one identified piece of work is session-pickup, why something was decided is why, and how it works now is how.

<!-- registry:generated traits -->
- `current-state-capsule-goal`: Rebuild recent working context into a compact statement of the present position and what comes next.
- `two-record-context-model`: Treat context as living in both the agent's own chat history and a shared record of tracker, chat, docs, source control and error reports.
- `recall-routes-away`: First rule out resuming one known chat, making a durable skill from habits and writing a human-facing work summary, since those are other tasks.
- `skip-mining-with-supplied-state`: If the user already gave paths, branch and the change, use that and do no mining.
- `lock-scope-before-search`: Fix the time window, topic and workspace before any searching, and say the locked scope to the user.
- `seven-day-default-window`: Treat recent as a real range with a default of seven days.
- `active-workspace-only-default`: Default to the current workspace and read another project's chats only when asked.
- `no-silent-narrowing`: Never quietly reduce a request for everything into a recent subset.
- `order-by-real-mtime`: Sort candidates by actual modification time, never by identifier name.
- `grep-then-read-matching-regions`: Search for the topic first, then open only chats that match and only the parts of them that bear on it.
- `exclude-current-and-noise-chats`: Leave out the current chat along with subagent, evaluation and test chats.
- `uniform-per-chat-schema`: Require from each subagent one block per chat recording topic, goal, decisions, unresolved threads, difficulties, corrections and produced artifacts.
- `finding-cited-by-source-kind`: Cite chat findings by chat identifier and shared-record findings by pull request, ticket, permalink or error-tracker issue.
- `direct-search-for-small-corpus`: With one or two chats, search directly without fanning out.
- `default-shared-record-sweep`: Search the shared record by default when a feature, file, subsystem, area or bug is named, omitting it only for activity recall with no named target.
- `one-helper-per-sizeable-source`: Give a shared-record source its own helper only when its investigation is sizeable and independent, and read small sources directly.
- `retarget-investigator-question`: Change the investigators' question from design rationale to current state, failed attempts and ongoing user reports.
- `empty-search-is-finding`: Count a search that returned nothing as a result to report, not as work to discard.
- `full-transcript-for-agent-behaviour`: When the answer depends on what an agent actually did, read the complete transcript and not a trimmed local copy.
- `brief-grouped-by-thread`: Organize a recall brief by thread and stay on the named topic.
- `brief-section-order`: Present capsule, thread status, problems and next move in that order, with further detail below or cut.
- `capped-capsule-section`: Hold the opening capsule to five bullets at most.
- `status-tagged-thread-lines-with-abandoned`: Give each thread one line with one tag from merged, open pull request, in flight, verified uncommitted, reverted, abandoned or planned, describing any other state in plain words.
- `capped-recurring-problems`: List at most five recurring problems, including persistent user symptoms and reverted fixes, so the next try starts from the last failure.
- `single-next-move`: End with the one most useful concrete next action.
- `adjacent-excluded-unless-blocking`: Leave out a neighbouring feature or ticket unless it blocks this one.
- `cut-detail-before-threads`: When a recall brief passes a screen, remove detail ahead of removing threads.
- `reply-is-the-deliverable`: Return the deliverable itself as the reply, never an account of what was done to produce it.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/recall#current-state-capsule-goal** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#two-record-context-model** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#recall-routes-away** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#skip-mining-with-supplied-state** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#lock-scope-before-search** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#seven-day-default-window** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#active-workspace-only-default** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#no-silent-narrowing** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#order-by-real-mtime** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#grep-then-read-matching-regions** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#exclude-current-and-noise-chats** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#uniform-per-chat-schema** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#finding-cited-by-source-kind** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#direct-search-for-small-corpus** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#default-shared-record-sweep** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#one-investigator-per-source** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#retarget-investigator-question** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#empty-search-is-finding** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#full-transcript-for-agent-behaviour** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#brief-grouped-by-thread** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#brief-section-order** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#capped-capsule-section** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#status-tagged-thread-lines** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#capped-recurring-problems** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#single-next-move** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#adjacent-excluded-unless-blocking** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#cut-detail-before-threads** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/recall#reply-is-the-deliverable** `pstack/skills/recall/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:030): Completes pending 2026-11-06-batch-p1:207: reply-is-the-deliverable is written at .claude/skills/recall/SKILL.md:75 (plan 61; a new unit, so no frozen wording).
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:029): Completes pending 2026-11-06-batch-p1:205: cut-detail-before-threads is written at .claude/skills/recall/SKILL.md:69-70 (plan 61; a new unit, so no frozen word…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:028): Completes pending 2026-11-06-batch-p1:204: adjacent-excluded-unless-blocking is written at .claude/skills/recall/SKILL.md:69 (plan 61; a new unit, so no frozen…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:027): Completes pending 2026-11-06-batch-p1:203: single-next-move is written at .claude/skills/recall/SKILL.md:66-67 (plan 61; a new unit, so no frozen wording).
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:026): Completes pending 2026-11-06-batch-p1:202: capped-recurring-problems is written at .claude/skills/recall/SKILL.md:62-64 (plan 61; a new unit, so no frozen word…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:025): Completes pending 2026-11-06-batch-p1:201: status-tagged-thread-lines-with-abandoned is written at .claude/skills/recall/SKILL.md:59-61 (plan 61; a new unit, s…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:024): Completes pending 2026-11-06-batch-p1:200: capped-capsule-section is written at .claude/skills/recall/SKILL.md:58 (plan 61; a new unit, so no frozen wording).
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:023): Completes pending 2026-11-06-batch-p1:199: brief-section-order is written at .claude/skills/recall/SKILL.md:54-56 (plan 61; a new unit, so no frozen wording).
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:022): Completes pending 2026-11-06-batch-p1:198: brief-grouped-by-thread is written at .claude/skills/recall/SKILL.md:54 (plan 61; a new unit, so no frozen wording).
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:021): Completes pending 2026-11-06-batch-p1:197: full-transcript-for-agent-behaviour is written at .claude/skills/recall/SKILL.md:38-40 (plan 61; a new unit, so no f…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:020): Completes pending 2026-11-06-batch-p1:194: empty-search-is-finding is written at .claude/skills/recall/SKILL.md:47 (plan 61; a new unit, so no frozen wording).
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:019): Completes pending 2026-11-06-batch-p1:192: retarget-investigator-question is written at .claude/skills/recall/SKILL.md:46-47 (plan 61; a new unit, so no frozen…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:018): Completes pending 2026-11-06-batch-p1:191: one-helper-per-sizeable-source is written at .claude/skills/recall/SKILL.md:43-46 (plan 61; a new unit, so no frozen…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:017): Completes pending 2026-11-06-batch-p1:190: default-shared-record-sweep is written at .claude/skills/recall/SKILL.md:41-43 (plan 61; a new unit, so no frozen wo…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:016): Completes pending 2026-11-06-batch-p1:187: direct-search-for-small-corpus is written at .claude/skills/recall/SKILL.md:34-36 (plan 61; a new unit, so no frozen…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:015): Completes pending 2026-11-06-batch-p1:186: finding-cited-by-source-kind is written at .claude/skills/recall/SKILL.md:70-73 (plan 61; a new unit, so no frozen w…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:014): Completes pending 2026-11-06-batch-p1:185: uniform-per-chat-schema is written at .claude/skills/recall/SKILL.md:35-38 (plan 61; a new unit, so no frozen wordin…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:013): Completes pending 2026-11-06-batch-p1:184: exclude-current-and-noise-chats is written at .claude/skills/recall/SKILL.md:34, .claude/skills/recall/references/ch…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:012): Completes pending 2026-11-06-batch-p1:183: grep-then-read-matching-regions is written at .claude/skills/recall/SKILL.md:32-34 (plan 61; a new unit, so no froze…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:011): Completes pending 2026-11-06-batch-p1:182: order-by-real-mtime is written at .claude/skills/recall/SKILL.md:31-32 (plan 61; a new unit, so no frozen wording).
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:010): Completes pending 2026-11-06-batch-p1:180: no-silent-narrowing is written at .claude/skills/recall/SKILL.md:30 (plan 61; a new unit, so no frozen wording).
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:009): Completes pending 2026-11-06-batch-p1:179: active-workspace-only-default is written at .claude/skills/recall/SKILL.md:28-29 (plan 61; a new unit, so no frozen …
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:008): Completes pending 2026-11-06-batch-p1:178: seven-day-default-window is written at .claude/skills/recall/SKILL.md:27-28 (plan 61; a new unit, so no frozen wordi…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:007): Completes pending 2026-11-06-batch-p1:177: lock-scope-before-search is written at .claude/skills/recall/SKILL.md:27-29 (plan 61; a new unit, so no frozen wordi…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:006): Completes pending 2026-11-06-batch-p1:176: skip-mining-with-supplied-state is written at .claude/skills/recall/SKILL.md:25-26 (plan 61; a new unit, so no froze…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:005): Completes pending 2026-11-06-batch-p1:175: recall-routes-away is written at .claude/skills/recall/SKILL.md:22-25 (plan 61; a new unit, so no frozen wording).
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:004): Completes pending 2026-11-06-batch-p1:173: two-record-context-model is written at .claude/skills/recall/SKILL.md:13-18 (plan 61; a new unit, so no frozen wordi…
- `2026-11-12` **adopt** (2026-11-12-batch-p1-recall:003): Completes pending 2026-11-06-batch-p1:171: current-state-capsule-goal is written at .claude/skills/recall/SKILL.md:10-11 (plan 61; a new unit, so no frozen wor…
- `2026-11-12` **add** (2026-11-12-batch-p1-recall:001): Owner ruling of 2026-11-06 §G (batch P1 as recommended; recall made a new skill) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md); owner answer of 2026-11…
- `2026-11-06` **adopt-merged** (2026-11-06-batch-p1:208): Checkpoint at 4dd1d05 for the owner's trait rulings: 31 adopt, 1 out-of-scope, 5 reject.
- `2026-11-06` **adopt** (2026-11-06-batch-p1:207) *(superseded)*: Owner ruling 2026-11-06: Prevents: A report about having recalled, in place of the recall itself. Lands in recall, the new skill the owner's ruling of 2026-11-…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:205) *(superseded)*: Owner ruling 2026-11-06: Prevents: A shortened brief that silently drops a whole thread of work. Lands in recall, the new skill the owner's ruling of 2026-11-0…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:204) *(superseded)*: Owner ruling 2026-11-06: Prevents: A brief padded with neighbouring work that does not affect this one. Lands in recall, the new skill the owner's ruling of 20…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:203) *(superseded)*: Owner ruling 2026-11-06: Prevents: A brief that ends on a list of options and no recommendation. Lands in recall, the new skill the owner's ruling of 2026-11-0…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:202) *(superseded)*: Owner ruling 2026-11-06: Prevents: A retry that repeats the last failed fix because the recall never named it. Lands in recall, the new skill the owner's rulin…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:201) *(superseded)*: Owner ruling 2026-11-06: Prevents: Thread lines with no clear status, so merged and abandoned work read the same, or a stopped thread forced under a tag that i…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:200) *(superseded)*: Owner ruling 2026-11-06: Prevents: An opening summary too long to take in at a glance. Lands in recall, the new skill the owner's ruling of 2026-11-06 creates,…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:199) *(superseded)*: Owner ruling 2026-11-06: Prevents: The next move buried under detail. Lands in recall, the new skill the owner's ruling of 2026-11-06 creates, which rebuilds r…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:198) *(superseded)*: Owner ruling 2026-11-06: Prevents: A brief told in date order that mixes threads, so the reader cannot see each one's state. Lands in recall, the new skill the…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:197) *(superseded)*: Owner ruling 2026-11-06: Prevents: A judgement of what an agent did, made from a trimmed copy that dropped the step in question. Lands in recall, the new skill…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:194) *(superseded)*: Owner ruling 2026-11-06: Prevents: A real answer lost because the search behind it found nothing. Lands in recall, the new skill the owner's ruling of 2026-11-…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:192) *(superseded)*: Owner ruling 2026-11-06: Prevents: Helpers that report why the design looks as it does when the person needs where the work stands. Lands in recall, the new sk…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:191) *(superseded)*: Owner ruling 2026-11-06: Prevents: One helper juggling every source, so a source gets skimmed or skipped, or helpers started for reads too small to need one. L…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:190) *(superseded)*: Owner ruling 2026-11-06: Prevents: A brief on a named feature that leaves out its open beads, commits and failed fixes. Lands in recall, the new skill the owne…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:187) *(superseded)*: Owner ruling 2026-11-06: Prevents: Helpers started to read one or two chats the agent could search itself. Lands in recall, the new skill the owner's ruling of…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:186) *(superseded)*: Owner ruling 2026-11-06: Prevents: A claim in the recall nobody can trace to the chat, commit or bead it came from. Lands in recall, the new skill the owner's …
- `2026-11-06` **adopt** (2026-11-06-batch-p1:185) *(superseded)*: Owner ruling 2026-11-06: Prevents: Helper reports in different shapes that cannot be merged without rereading the chats. Lands in recall, the new skill the own…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:184) *(superseded)*: Owner ruling 2026-11-06: Prevents: A recall echoing the current chat, or a helper's or a test's chat, as if it were the person's work. Lands in recall, the new…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:183) *(superseded)*: Owner ruling 2026-11-06: Prevents: Whole chats read end to end, filling the context with unrelated work. Lands in recall, the new skill the owner's ruling of 2…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:182) *(superseded)*: Owner ruling 2026-11-06: Prevents: Chats ranked by an identifier that does not follow time, so old work is read as current. Lands in recall, the new skill the …
- `2026-11-06` **adopt** (2026-11-06-batch-p1:180) *(superseded)*: Owner ruling 2026-11-06: Prevents: A request for everything quietly answered from a recent subset, so the person believes the recall is complete. Lands in reca…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:179) *(superseded)*: Owner ruling 2026-11-06: Prevents: Another project's chats, and the private details in them, pulled into this project's brief unasked. Lands in recall, the new…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:178) *(superseded)*: Owner ruling 2026-11-06: Prevents: Recent read as a few hours or as all history, so the recall misses work or drowns in it. Lands in recall, the new skill the …
- `2026-11-06` **adopt** (2026-11-06-batch-p1:177) *(superseded)*: Owner ruling 2026-11-06: Prevents: A search that drifts across topics and dates, so the recall covers something other than what was asked. Lands in recall, the…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:176) *(superseded)*: Owner ruling 2026-11-06: Prevents: Time spent mining chats for state the person already gave. Lands in recall, the new skill the owner's ruling of 2026-11-06 c…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:175) *(superseded)*: Owner ruling 2026-11-06: Prevents: A sweep across chats run when the person wanted one known piece of work resumed, which `session-pickup` does from its trail.…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:173) *(superseded)*: Owner ruling 2026-11-06: Prevents: A recall built from chats alone that misses what the tracker, commits and docs already record. Lands in recall, the new skil…
- `2026-11-06` **adopt** (2026-11-06-batch-p1:171) *(superseded)*: Owner ruling 2026-11-06: Prevents: A resumed session that rereads everything and still cannot say where the work stands or what comes next. Lands in recall, th…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-04-upstream-cursor_plugins-4dd1d05-batch-p1.md](../../reviews/2026-11-04-upstream-cursor_plugins-4dd1d05-batch-p1.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `active-workspace-only-default`:
  - `cursor_plugins:skill:pstack/skills/recall#active-workspace-only-default` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `adjacent-excluded-unless-blocking`:
  - `cursor_plugins:skill:pstack/skills/recall#adjacent-excluded-unless-blocking` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `brief-grouped-by-thread`:
  - `cursor_plugins:skill:pstack/skills/recall#brief-grouped-by-thread` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `brief-section-order`:
  - `cursor_plugins:skill:pstack/skills/recall#brief-section-order` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `capped-capsule-section`:
  - `cursor_plugins:skill:pstack/skills/recall#capped-capsule-section` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `capped-recurring-problems`:
  - `cursor_plugins:skill:pstack/skills/recall#capped-recurring-problems` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `current-state-capsule-goal`:
  - `cursor_plugins:skill:pstack/skills/recall#current-state-capsule-goal` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `cut-detail-before-threads`:
  - `cursor_plugins:skill:pstack/skills/recall#cut-detail-before-threads` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `default-shared-record-sweep`:
  - `cursor_plugins:skill:pstack/skills/recall#default-shared-record-sweep` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `direct-search-for-small-corpus`:
  - `cursor_plugins:skill:pstack/skills/recall#direct-search-for-small-corpus` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `empty-search-is-finding`:
  - `cursor_plugins:skill:pstack/skills/recall#empty-search-is-finding` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `exclude-current-and-noise-chats`:
  - `cursor_plugins:skill:pstack/skills/recall#exclude-current-and-noise-chats` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `finding-cited-by-source-kind`:
  - `cursor_plugins:skill:pstack/skills/recall#finding-cited-by-source-kind` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `full-transcript-for-agent-behaviour`:
  - `cursor_plugins:skill:pstack/skills/recall#full-transcript-for-agent-behaviour` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `grep-then-read-matching-regions`:
  - `cursor_plugins:skill:pstack/skills/recall#grep-then-read-matching-regions` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `lock-scope-before-search`:
  - `cursor_plugins:skill:pstack/skills/recall#lock-scope-before-search` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `no-silent-narrowing`:
  - `cursor_plugins:skill:pstack/skills/recall#no-silent-narrowing` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `one-helper-per-sizeable-source`:
  - `cursor_plugins:skill:pstack/skills/recall#one-investigator-per-source` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `order-by-real-mtime`:
  - `cursor_plugins:skill:pstack/skills/recall#order-by-real-mtime` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `recall-routes-away`:
  - `cursor_plugins:skill:pstack/skills/recall#recall-routes-away` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `reply-is-the-deliverable`:
  - `cursor_plugins:skill:pstack/skills/recall#reply-is-the-deliverable` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `retarget-investigator-question`:
  - `cursor_plugins:skill:pstack/skills/recall#retarget-investigator-question` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `seven-day-default-window`:
  - `cursor_plugins:skill:pstack/skills/recall#seven-day-default-window` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `single-next-move`:
  - `cursor_plugins:skill:pstack/skills/recall#single-next-move` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `skip-mining-with-supplied-state`:
  - `cursor_plugins:skill:pstack/skills/recall#skip-mining-with-supplied-state` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `status-tagged-thread-lines-with-abandoned`:
  - `cursor_plugins:skill:pstack/skills/recall#status-tagged-thread-lines` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `two-record-context-model`:
  - `cursor_plugins:skill:pstack/skills/recall#two-record-context-model` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `uniform-per-chat-schema`:
  - `cursor_plugins:skill:pstack/skills/recall#uniform-per-chat-schema` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
