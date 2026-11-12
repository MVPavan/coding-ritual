---
skill: interrogate
domain: core
stage: Verification
substage: Review
secondary: []
family:
aliases: []
status: active
---
# interrogate

Use when asked to break, attack or tear apart a change or design, or when a playbook names it: adversaries attack it and only findings a run proves survive. An ordinary or critical look is `review`; questioning the author is `grilling`; finding the cause of a known failure is `systematic-debugging`.

**Boundary:** Reports only what a run proved, where review judges by reading and reports every finding. grilling questions a person and runs nothing. prototype answers an open question before a choice, while this attacks a chosen change or design, and an adversary may build a throwaway probe without running that skill. systematic-debugging starts from a known failure and finds its cause, while this looks for failures and stops at the repro, and an unexplained finding goes back to the caller. model-council has members and a judge reach one answer or artifact, while this has no judge and no pick, and keeps every verified finding.

<!-- registry:generated traits -->
- `break-it-mandate`: Assign adversaries to try to break a change or design rather than assess it in general.
- `run-proven-finding`: Let a finding stand only when a run executed in the review shows it, so a claim nobody ran is no finding.
- `named-scope-first`: Use the scope the user names when one is given.
- `intent-restated-first`: Restate the change's intent in your own words before sending out adversaries.
- `intent-from-stated-sources`: Take a change's intent only from a stated source such as the request, a brief, a spec or a bead, never from the diff.
- `ask-or-not-run-on-intent`: Ask when the intent is unclear and someone can answer, and report the review as not run when nobody can.
- `own-output-location`: Give every candidate or adversary a separate output location, so they share no writable state.
- `dropout-proceeds-noted`: Go on with the remaining candidates or adversaries when one produces nothing, and record the dropout.
- `verified-snapshot-copy`: Give each adversary and each replay a disposable copy made from one pristine snapshot of the working state and checked against it, reporting not run when a copy cannot be made exact.
- `adversaries-by-model-or-angle`: Run one adversary per available model on one instruction to break the work or, with a single model, several whose prompts each attack something different, giving every adversary the scope and the intent.
- `run-against-real-code`: Require each finding to be demonstrated by executing something against the actual code, such as a failing test, a reproduction script or revealing command output.
- `design-proof-by-probe`: For a design or plan, prove a finding by running a prototype or probing the current tree.
- `repros-stay-in-copy`: Keep each adversary's reproduction material inside its own output location.
- `finding-repro-report`: Require each finding to carry a title, the exact command, the printed output and the output the intent requires.
- `no-findings-valid`: Accept a report with no findings as a valid result, and say so explicitly when none remain.
- `coordinator-replays-finding`: Have the coordinator verify each finding by running its command again.
- `reproduced-and-breaks-intent`: Keep a finding only if the output shows the failure and that failure breaks the stated intent.
- `three-replay-outcomes`: Sort each replayed finding into reproduced, not reproduced (dropped and stated as unreproduced, not disproved) or unreplayable (listed with no severity).
- `merge-by-root-cause`: Combine findings that share one root cause.
- `union-of-verified-findings`: Keep every verified finding across adversaries rather than selecting one adversary's list.
- `output-opens-with-intent`: Open the output with the intent restatement.
- `output-finding-fields`: For each verified finding, report its command, its output and how it breaks the intent.
- `adversary-attribution`: Name the adversaries that found each verified finding.
- `dropped-finding-accounting`: Report for each adversary how many findings were dropped and why.
- `checkout-change-check`: After each adversary returns, compare the shared checkout with the snapshot's state and report each changed path, without voiding the run, restoring anything or naming who changed it.
- `unresolved-outranks-verdict`: Give no favourable verdict while an observed failure stays unreproduced or unreplayable.
- `no-self-adversary`: Report not run rather than attack as an adversary work you wrote or a design you settled.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/interrogate#break-it-mandate** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#run-proven-finding** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#named-scope-first** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#intent-restated-first** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#intent-from-request-commits-pr** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#ask-when-intent-unclear** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#own-output-location** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#dropout-proceeds-noted** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#uncommitted-changes-seeded** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#adversary-fixed-brief** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#run-against-real-code** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#design-proof-by-probe** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#repros-stay-in-copy** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#finding-repro-report** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#no-findings-valid** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#coordinator-replays-finding** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#reproduced-and-breaks-intent** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#drop-unverified-findings** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#merge-by-root-cause** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#union-of-verified-findings** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#output-opens-with-intent** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#output-finding-fields** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#adversary-attribution** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/interrogate#dropped-finding-accounting** `pstack/skills/interrogate/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-03` **update** (2026-11-03-batch-3:154): Final critic: both scripts ran index-writing Git commands in the source without disabling hooks, so a source hook could change the work they observe. Every Git…
- `2026-11-03` **adopt** (2026-11-03-batch-3:108): Completes pending 2026-11-03-batch-3:082: dropped-finding-accounting is written at .claude/skills/interrogate/SKILL.md:83, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:107): Completes pending 2026-11-03-batch-3:081: adversary-attribution is written at .claude/skills/interrogate/SKILL.md:81, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:106): Completes pending 2026-11-03-batch-3:080: output-finding-fields is written at .claude/skills/interrogate/SKILL.md:81, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:105): Completes pending 2026-11-03-batch-3:079: output-opens-with-intent is written at .claude/skills/interrogate/SKILL.md:80, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:104): Completes pending 2026-11-03-batch-3:078: union-of-verified-findings is written at .claude/skills/interrogate/SKILL.md:70, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:103): Completes pending 2026-11-03-batch-3:076: merge-by-root-cause is written at .claude/skills/interrogate/SKILL.md:70, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:102): Completes pending 2026-11-03-batch-3:075: three-replay-outcomes is written at .claude/skills/interrogate/SKILL.md:69-72, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:101): Completes pending 2026-11-03-batch-3:074: reproduced-and-breaks-intent is written at .claude/skills/interrogate/SKILL.md:69, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:100): Completes pending 2026-11-03-batch-3:073: coordinator-replays-finding is written at .claude/skills/interrogate/SKILL.md:68, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:099): Completes pending 2026-11-03-batch-3:072: no-findings-valid is written at .claude/skills/interrogate/SKILL.md:64, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:098): Completes pending 2026-11-03-batch-3:069: finding-repro-report is written at .claude/skills/interrogate/SKILL.md:66-67, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:097): Completes pending 2026-11-03-batch-3:068: repros-stay-in-copy is written at .claude/skills/interrogate/SKILL.md:35-36, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:096): Completes pending 2026-11-03-batch-3:067: design-proof-by-probe is written at .claude/skills/interrogate/SKILL.md:62-63, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:095): Completes pending 2026-11-03-batch-3:066: run-against-real-code is written at .claude/skills/interrogate/SKILL.md:58-60, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:094): Completes pending 2026-11-03-batch-3:065: adversaries-by-model-or-angle is written at .claude/skills/interrogate/SKILL.md:20-24, read against its definition (T…
- `2026-11-03` **adopt** (2026-11-03-batch-3:093): Completes pending 2026-11-03-batch-3:063: verified-snapshot-copy is written at .claude/skills/interrogate/SKILL.md:31-33, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:092): Completes pending 2026-11-03-batch-3:062: dropout-proceeds-noted is written at .claude/skills/interrogate/SKILL.md:24-25, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:091): Completes pending 2026-11-03-batch-3:060: own-output-location is written at .claude/skills/interrogate/SKILL.md:34-35, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:090): Completes pending 2026-11-03-batch-3:058: ask-or-not-run-on-intent is written at .claude/skills/interrogate/SKILL.md:17, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:089): Completes pending 2026-11-03-batch-3:057: intent-from-stated-sources is written at .claude/skills/interrogate/SKILL.md:16, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:088): Completes pending 2026-11-03-batch-3:056: intent-restated-first is written at .claude/skills/interrogate/SKILL.md:15, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:087): Completes pending 2026-11-03-batch-3:054: named-scope-first is written at .claude/skills/interrogate/SKILL.md:13-14, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:086): Completes pending 2026-11-03-batch-3:052: run-proven-finding is written at .claude/skills/interrogate/SKILL.md:61-62, read against its definition (T5).
- `2026-11-03` **adopt** (2026-11-03-batch-3:085): Completes pending 2026-11-03-batch-3:051: break-it-mandate is written at .claude/skills/interrogate/SKILL.md:9, read against its definition (T5).
- `2026-11-03` **add** (2026-11-03-batch-3:084): New skill, owner ruling 3 of 2026-11-03: adversaries break a change or design and only a finding a run proves survives, on checked copies of one snapshot made …
- `2026-11-03` **adopt-merged** (2026-11-03-batch-3:083): Checkpoint at 4dd1d05 for the owner's trait rulings: 25 adopt, 1 defer, 6 reject.
- `2026-11-03` **adopt** (2026-11-03-batch-3:082) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md. Upstream: SKILL.md:31.
- `2026-11-03` **adopt** (2026-11-03-batch-3:081) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md. Upstream: SKILL.md:30.
- `2026-11-03` **adopt** (2026-11-03-batch-3:080) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md. Upstream: SKILL.md:30.
- `2026-11-03` **adopt** (2026-11-03-batch-3:079) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md. Upstream: SKILL.md:29.
- `2026-11-03` **adopt** (2026-11-03-batch-3:078) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md. Upstream: SKILL.md:25.
- `2026-11-03` **adopt** (2026-11-03-batch-3:076) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md. Upstream: SKILL.md:23.
- `2026-11-03` **adopt** (2026-11-03-batch-3:075) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md, into `three-replay-outcomes`. Upstream: SKILL.md:23.
- `2026-11-03` **adopt** (2026-11-03-batch-3:074) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md. Upstream: SKILL.md:23.
- `2026-11-03` **adopt** (2026-11-03-batch-3:073) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md. Upstream: SKILL.md:23.
- `2026-11-03` **adopt** (2026-11-03-batch-3:072) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md. Upstream: SKILL.md:19, 30.
- `2026-11-03` **adopt** (2026-11-03-batch-3:069) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md. Upstream: SKILL.md:19.
- `2026-11-03` **adopt** (2026-11-03-batch-3:068) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md. Upstream: SKILL.md:19.
- `2026-11-03` **adopt** (2026-11-03-batch-3:067) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md. Upstream: SKILL.md:19.
- `2026-11-03` **adopt** (2026-11-03-batch-3:066) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md. Upstream: SKILL.md:19.
- `2026-11-03` **adopt** (2026-11-03-batch-3:065) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md, into `adversaries-by-model-or-angle`. Upstream: SKILL.md:17, 19.
- `2026-11-03` **adopt** (2026-11-03-batch-3:063) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md and scripts/make-copy.sh, into `verified-snapshot-copy`. Upstream: SKILL.md:17.
- `2026-11-03` **adopt** (2026-11-03-batch-3:062) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md. Upstream: SKILL.md:17.
- `2026-11-03` **adopt** (2026-11-03-batch-3:060) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md. Upstream: SKILL.md:17.
- `2026-11-03` **adopt** (2026-11-03-batch-3:058) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md, into `ask-or-not-run-on-intent`. Upstream: SKILL.md:13.
- `2026-11-03` **adopt** (2026-11-03-batch-3:057) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md, into `intent-from-stated-sources`. Upstream: SKILL.md:13.
- `2026-11-03` **adopt** (2026-11-03-batch-3:056) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md. Upstream: SKILL.md:13.
- `2026-11-03` **adopt** (2026-11-03-batch-3:054) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md. Upstream: SKILL.md:13.
- `2026-11-03` **adopt** (2026-11-03-batch-3:052) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md. Upstream: SKILL.md:9, 19.
- `2026-11-03` **adopt** (2026-11-03-batch-3:051) *(superseded)*: Owner ruling 2026-11-03: Lands in interrogate, SKILL.md. Upstream: SKILL.md:9.
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-03-upstream-cursor_plugins-4dd1d05-batch-3.md](../../reviews/2026-11-03-upstream-cursor_plugins-4dd1d05-batch-3.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `adversaries-by-model-or-angle`:
  - `cursor_plugins:skill:pstack/skills/interrogate#adversary-fixed-brief` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `adversary-attribution`:
  - `cursor_plugins:skill:pstack/skills/interrogate#adversary-attribution` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `ask-or-not-run-on-intent`:
  - `cursor_plugins:skill:pstack/skills/interrogate#ask-when-intent-unclear` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `break-it-mandate`:
  - `cursor_plugins:skill:pstack/skills/interrogate#break-it-mandate` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `coordinator-replays-finding`:
  - `cursor_plugins:skill:pstack/skills/interrogate#coordinator-replays-finding` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `design-proof-by-probe`:
  - `cursor_plugins:skill:pstack/skills/interrogate#design-proof-by-probe` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `dropout-proceeds-noted`:
  - `cursor_plugins:skill:pstack/skills/interrogate#dropout-proceeds-noted` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `dropped-finding-accounting`:
  - `cursor_plugins:skill:pstack/skills/interrogate#dropped-finding-accounting` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `finding-repro-report`:
  - `cursor_plugins:skill:pstack/skills/interrogate#finding-repro-report` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `intent-from-stated-sources`:
  - `cursor_plugins:skill:pstack/skills/interrogate#intent-from-request-commits-pr` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `intent-restated-first`:
  - `cursor_plugins:skill:pstack/skills/interrogate#intent-restated-first` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `merge-by-root-cause`:
  - `cursor_plugins:skill:pstack/skills/interrogate#merge-by-root-cause` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `named-scope-first`:
  - `cursor_plugins:skill:pstack/skills/interrogate#named-scope-first` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `no-findings-valid`:
  - `cursor_plugins:skill:pstack/skills/interrogate#no-findings-valid` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `output-finding-fields`:
  - `cursor_plugins:skill:pstack/skills/interrogate#output-finding-fields` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `output-opens-with-intent`:
  - `cursor_plugins:skill:pstack/skills/interrogate#output-opens-with-intent` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `own-output-location`:
  - `cursor_plugins:skill:pstack/skills/interrogate#own-output-location` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `reproduced-and-breaks-intent`:
  - `cursor_plugins:skill:pstack/skills/interrogate#reproduced-and-breaks-intent` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `repros-stay-in-copy`:
  - `cursor_plugins:skill:pstack/skills/interrogate#repros-stay-in-copy` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `run-against-real-code`:
  - `cursor_plugins:skill:pstack/skills/interrogate#run-against-real-code` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `run-proven-finding`:
  - `cursor_plugins:skill:pstack/skills/interrogate#run-proven-finding` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `three-replay-outcomes`:
  - `cursor_plugins:skill:pstack/skills/interrogate#drop-unverified-findings` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `union-of-verified-findings`:
  - `cursor_plugins:skill:pstack/skills/interrogate#union-of-verified-findings` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `verified-snapshot-copy`:
  - `cursor_plugins:skill:pstack/skills/interrogate#uncommitted-changes-seeded` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
