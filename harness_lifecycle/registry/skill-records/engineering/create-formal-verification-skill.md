---
skill: create-formal-verification-skill
domain: engineering
stage: Improvement
substage: Codification
secondary: [Testing]
family:
aliases: []
status: active
---
# create-formal-verification-skill

Use for /create-formal-verification-skill when a promise whose breaking harms users and that tests rarely reach needs checking across every case in a stated scope; keeping an existing formal check current is maintain-formal-verification-skill, and driving the real app is create-verification-skill. Picks the strongest such promise, checks one property with the tool its question needs, and leaves a project skill that reruns the check, with a coverage and sync record, proven against a planted break.

**Boundary:** Generates a project skill that checks one high-harm, rarely tested promise across every case in a stated scope with the formal tool its question needs, with a coverage and sync record, proven against a planted break; driving the real app is create-verification-skill, checking or drawing one TLA+ model is statechart, and keeping a formal check current is maintain-formal-verification-skill.

<!-- registry:generated traits -->
- `formal-check-left-as-skill`: Verify one property and leave a project skill that lets a later agent check changes against it.
- `result-trusted-without-the-language`: Make the result something the person can trust and act on without learning the verification language.
- `named-scope-first`: Use the scope the user names when one is given.
- `harmful-rarely-tested-promise`: Pick as the target a promise the code makes whose breaking harms users and that tests rarely reach.
- `strongest-target-not-easiest`: Choose the strongest such target, not the easiest to verify.
- `domain-vocabulary`: Use the project's established domain vocabulary throughout what you write.
- `verification-tool-by-question`: Pick the cheapest tool that answers the question: a model checker over a small design model for bad event orderings, a code-level verifier for behaviour on every input, and a proof for properties no bound can settle.
- `generated-input-fallback`: When no verifier supports the language, say so and exercise the real code with generated inputs rather than a hand-written model of it.
- `installable-tool-preference`: Prefer a verification tool the project's developers are able to install and run, and explain the choice to the person.
- `generated-check-catches-planted-break`: Follow the generated skill once against a throwaway edit to real code that violates the property, confirm it catches the break, then remove the edit and confirm the check is back to its earlier state.
- `fix-skill-not-scratch-break`: When the skill misses a planted break or a step fails, fix the skill or the verification, never the planted break.
- `verification-handoff-report`: Tell the person what was verified, with which tool and why, the bounds, the findings in plain words, the command to run it and what it leaves uncovered.
- `adjacent-target-only-if-close`: Suggest a second target only when a close one turned up.
- `traceable-to-code`: Make every part of a verification model or proof point to code a reviewer can open. (Written in references/model-fidelity.md, decision 4's shared reference, owned here and read by maintain-formal-verification-skill without restating it; that unit's adopt of the same ID is completed in round 2026-11-15-maintain-formal-verification-skill (P2 :457).)
- `atomicity-fidelity`: Treat as one indivisible step in the verification only what is one indivisible step in the code. (Written in references/model-fidelity.md, decision 4's shared reference, owned here and read by maintain-formal-verification-skill without restating it; that unit's adopt of the same ID is completed in round 2026-11-15-maintain-formal-verification-skill (P2 :458).)
- `property-fails-on-broken-variant`: Show each property failing on a deliberately broken variant of the code it guards, after first writing it and after each update. (Written in references/model-fidelity.md, decision 4's shared reference, owned here; maintain-formal-verification-skill's adopt of the same ID is completed in round 2026-11-15-maintain-formal-verification-skill (P2 :461). Blind ruling, after critic-90d F1: a variant counts only by its named property breaking, never by any failure, and means nothing while the main run fails (references/tool-branches.md, "The TLC gate"). Q1 move (owner rulings of 2026-11-15, item 1): when a confirmed bug moves the sync commit, variant verdicts are accepted only from a later run whose main run holds (references/model-fidelity.md:64-66).)
- `coverage-and-sync-record`: Record, per check, the files and functions it guards and the last commit it was confirmed against, so drift shows.
- `sync-commit-advanced-after-match`: Move the recorded sync commit forward only after confirming the verification matches the code at the new commit. (Q1 move (owner rulings of 2026-11-15, item 1): references/coverage-record.md Rules lets a maintain pass move sync_commit and covers on a confirmed bug, with the faithful model update, so the verification still matches the code, which then fails there (references/coverage-record.md:51-58; references/formal-verify-skill.md:76-80).)
- `plain-property-and-harm`: State the property and the harm of breaking it in one plain sentence each.
- `cheap-rerun`: Make the check rerunnable with a single command, a pinned tool version and a short running time.
- `verify-skill-capabilities`: Let the next agent learn from the skill alone whether a change touches verified code, how to run the check, how to tell a real bug from a modelling error and how to update the verification for an intended change.
- `counterexample-as-code-steps`: Describe a counterexample as a few steps phrased in the code's own terms.
- `verified-scope-statement`: Say what the verification covers, the bounds and assumptions it holds under, and what it leaves out.
- `companion-tool-by-name`: When the check is a state-machine model, such as a TLA+ check, point the generated skill at a named companion tool for reading results, copying none of its commands, options or paths.
- `existing-formal-skill-stops`: Before generating a formal check, search every skills folder the project's hosts read for a formal verify skill, known by its coverage record, as an older skill that runs a kept model or proof, or as an occupied target folder, and stop without writing when one covers the area or cannot be ruled out, pointing to the formal maintenance unit.
- `generator-started-by-person`: Run the skill generator only when the person starts it: manual-only in its frontmatter and its sidecar, reached through setup, help or a router line, never by the model on its own. (Reused (decision 1): manual-only in its frontmatter and its sidecar, reached through its mvp-mode router row; the definition is generic to a skill generator (plan 83 §5).)
- `generated-skill-left-uncommitted`: Leave the generated skill and its map uncommitted unless the person asks for a commit, which the commit skill then makes. (Reused (decision 10, Q2 of plan 77): the formal verify skill it writes stays uncommitted unless the person asks, and land makes the commit (SKILL.md "6. Hand off"). It has no feature map; the definition's "and its map" covers its coverage.json, which stays uncommitted with it.)
- `handover-points-to-maintenance`: At handover, tell the person that keeping the generated skill current as the product changes is the maintenance unit's job. (Reused (decision 11): the hand-off names /maintain-formal-verification-skill as a slash pointer (SKILL.md "6. Hand off"), true now that the unit exists; skill-catalog.py --check proves it resolves.)
- `formal-coverage-data-file`: Keep a formal verify skill's coverage and sync record in one small data file of a versioned format beside its skill file, never as prose inside the skill, so its check script, the maintenance unit and freshness checks read the same record.
- `formal-skill-recognised-by-record`: Define the shape a formal verify skill is recognised by, a skill file beside a coverage data file whose format field names the formal coverage format, so other units find it by content, not by name, in every skills folder the project's hosts read.
- `single-source-of-truth`: Keep each meaning in one authoritative place so changing it is a one-place edit. (Reused (decision 4): references/model-fidelity.md is the one home of the model-fidelity rules, which maintain-formal-verification-skill reads and never restates. Not claimed: feature-map-owns-shared-rule and shared-reference-home (plan 83 §5).)
- `checker-install-approved-per-user`: Install a missing model checker or its runtime only after the person approves it, and then per user under their home folder, never system-wide, as root or through a shell-profile change; without approval, stop and name what is missing. (Held: statechart owns it; for TLC this unit asks first and follows statechart's references/install.md once approved, stopping and naming what is missing otherwise (SKILL.md "2. Choose the tool").)
- `check-never-weakened-to-pass`: When a check fails on the current product, report the failure and never weaken the check or its model to make it pass. (Held (decision 3, a short guardrail restated per unit): a failing check on the current code is a finding, and the property, the model and the bounds are never loosened until it passes (SKILL.md "3. Build the check").)
- `generated-skill-run-once`: Follow a generated skill end to end once, as its next reader would, before handing it over, counting an unrun skill as a draft. (Held (decision 3): the generated skill is followed once by a cold agent on a planted break before hand-off, and an unfollowed one is a draft (SKILL.md "5. Prove it on a planted break").)
- `verification-only-edits`: During a verification pass, edit only the verification skill's own files and never product code unless asked. (Held at references/formal-verify-skill.md "Reading a failure" (coordinator's ruling, round 2): the generated skill's own verification pass reports a real bug and leaves product code alone unless the person asks.)
- `generator-edits-own-output-only`: Edit only the generated skill's folder and any scaffolding the run labels, leaving a fix to product code to the person's authority. (Held (coordinator's ruling, round 2): this run writes the new skill folder and only step 5's reversible planted edit besides, and product code otherwise changes only when the person asks (SKILL.md Scope); the planted edit is the run's labelled scaffolding, removed and checked against the baseline.)
- `verdict-from-exit-and-messages`: Count a checker run as a verdict only when its exit code and its own completion and violation messages agree, with every rule checked where the checker checks all reachable states and no option that hides a violation.
- `cold-agent-reader`: Write a generated skill for an agent that meets the project cold, in the middle of a task, rather than for a person. (Reused (blind ruling): SKILL.md step 4 applies create-verification-skill's references/generated-skill.md "Writing rules", which state it, to the formal skill it writes; the proof follows that skill as a cold agent.)
- `real-code-names`: Use real names from the actual code, never invented placeholders. (Reused (blind ruling): applied through generated-skill.md's "Writing rules"; domain-vocabulary carries the project's names in the model and the property.)
- `registering-generated-frontmatter`: Give a generated skill frontmatter naming what it covers and when to use it, so it registers. (Reused (blind ruling): generated-skill.md's "Frontmatter", with the formal name <area>-verification and its own description (references/formal-verify-skill.md).)
- `pre-existing-edit-separation`: Separate pre-existing edits from the task's own changes using the task baseline, not filenames. (Reused (blind ruling): before the planted edit it records the product checkout's status, diff and the generated skill's hash list as the baseline, never clears the person's changes, and proves the restoration against that baseline.)
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#formal-check-left-as-skill** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#result-trusted-without-the-language** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#named-scope-first** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#harmful-rarely-tested-promise** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#strongest-target-not-easiest** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#verification-tool-by-question** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#generated-input-fallback** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#installable-tool-preference** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#traceable-to-code** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#atomicity-fidelity** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#domain-vocabulary** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#property-fails-on-broken-variant** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#verified-scope-statement** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#plain-property-and-harm** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#counterexample-as-code-steps** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#cheap-rerun** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#coverage-and-sync-record** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#verify-skill-capabilities** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#sync-commit-advanced-after-match** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#companion-tool-by-name** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#generated-check-catches-planted-break** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#fix-skill-not-scratch-break** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#verification-handoff-report** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#adjacent-target-only-if-close** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-15` **update** (2026-11-15-maintain-formal-verification-skill:025): Bead cr-r2pa.2.28.5, plan 92 §4 and the build report's exact lines: the stop rule and the hand-off now name /maintain-formal-verification-skill as a slash poin…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:101): Completes pending 2026-11-13-batch-p2:441: adjacent-target-only-if-close is written at .claude/skills/create-formal-verification-skill/SKILL.md:125-126, in its…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:100): Completes pending 2026-11-13-batch-p2:440: verification-handoff-report is written at .claude/skills/create-formal-verification-skill/SKILL.md:130-143, in its r…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:099): Completes pending 2026-11-13-batch-p2:439: fix-skill-not-scratch-break is written at .claude/skills/create-formal-verification-skill/SKILL.md:118-119, in its r…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:098): Completes pending 2026-11-13-batch-p2:437: generated-check-catches-planted-break is written at .claude/skills/create-formal-verification-skill/SKILL.md:97-116,…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:097): Completes pending 2026-11-13-batch-p2:436: companion-tool-by-name is written at .claude/skills/create-formal-verification-skill/references/formal-verify-skill.…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:096): Completes pending 2026-11-13-batch-p2:434: sync-commit-advanced-after-match is written at .claude/skills/create-formal-verification-skill/references/coverage-r…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:095): Completes pending 2026-11-13-batch-p2:433: verify-skill-capabilities is written at .claude/skills/create-formal-verification-skill/references/formal-verify-ski…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:094): Completes pending 2026-11-13-batch-p2:431: coverage-and-sync-record is written at .claude/skills/create-formal-verification-skill/references/coverage-record.md…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:093): Completes pending 2026-11-13-batch-p2:430: cheap-rerun is written at .claude/skills/create-formal-verification-skill/references/formal-verify-skill.md:27-29, i…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:092): Completes pending 2026-11-13-batch-p2:429: counterexample-as-code-steps is written at .claude/skills/create-formal-verification-skill/references/formal-verify-…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:091): Completes pending 2026-11-13-batch-p2:428: plain-property-and-harm is written at .claude/skills/create-formal-verification-skill/references/coverage-record.md:…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:090): Completes pending 2026-11-13-batch-p2:427: verified-scope-statement is written at .claude/skills/create-formal-verification-skill/references/formal-verify-skil…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:089): Completes pending 2026-11-13-batch-p2:424: property-fails-on-broken-variant is written at .claude/skills/create-formal-verification-skill/references/model-fide…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:088): Completes pending 2026-11-13-batch-p2:423: domain-vocabulary is written at .claude/skills/create-formal-verification-skill/SKILL.md:45-46, in its ruled words (…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:087): Completes pending 2026-11-13-batch-p2:422: atomicity-fidelity is written at .claude/skills/create-formal-verification-skill/references/model-fidelity.md:32-37 …
- `2026-11-14` **adopt** (2026-11-14-formal-pair:086): Completes pending 2026-11-13-batch-p2:421: traceable-to-code is written at .claude/skills/create-formal-verification-skill/references/model-fidelity.md:12-28 (…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:085): Completes pending 2026-11-13-batch-p2:420: installable-tool-preference is written at .claude/skills/create-formal-verification-skill/SKILL.md:63-64, in its rul…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:084): Completes pending 2026-11-13-batch-p2:419: generated-input-fallback is written at .claude/skills/create-formal-verification-skill/SKILL.md:59-61 (restated at .…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:083): Completes pending 2026-11-13-batch-p2:418: verification-tool-by-question is written at .claude/skills/create-formal-verification-skill/SKILL.md:50-57 (restated…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:082): Completes pending 2026-11-13-batch-p2:417: strongest-target-not-easiest is written at .claude/skills/create-formal-verification-skill/SKILL.md:41-43, in its ru…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:081): Completes pending 2026-11-13-batch-p2:416: harmful-rarely-tested-promise is written at .claude/skills/create-formal-verification-skill/SKILL.md:34-39, in its r…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:080): Completes pending 2026-11-13-batch-p2:415: named-scope-first is written at .claude/skills/create-formal-verification-skill/SKILL.md:34, in its ruled words (pla…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:079): Completes pending 2026-11-13-batch-p2:413: result-trusted-without-the-language is written at .claude/skills/create-formal-verification-skill/SKILL.md:15-18, in…
- `2026-11-14` **adopt** (2026-11-14-formal-pair:078): Completes pending 2026-11-13-batch-p2:411: formal-check-left-as-skill is written at .claude/skills/create-formal-verification-skill/SKILL.md:10-13, in its rule…
- `2026-11-14` **add** (2026-11-14-formal-pair:002): Bead cr-r2pa.2.28.4, plan 83 (with its Round 2 table). New manual skill (decision 1: manual-only in frontmatter and sidecar, reached through its mvp-mode route…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:442): Checkpoint at 2776ddd for the owner's trait rulings: 31 adopt.
- `2026-11-13` **adopt** (2026-11-13-batch-p2:441) *(superseded)*: Owner ruling 2026-11-13: Prevents: A hand-off padded with distant targets. Lands in create-formal-verification-skill, SKILL.md, a new skill per the owner's rul…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:440) *(superseded)*: Owner ruling 2026-11-13: Prevents: A person who cannot tell what was verified, under which bounds, or how to rerun it. Lands in create-formal-verification-skil…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:439) *(superseded)*: Owner ruling 2026-11-13: Prevents: A planted break edited until the check passes, hiding a check that cannot catch it. Lands in create-formal-verification-skil…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:437) *(superseded)*: Owner ruling 2026-11-13: Prevents: A generated check handed over without proof it catches the break it guards against. Lands in create-formal-verification-skil…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:436) *(superseded)*: Owner ruling 2026-11-13: Prevents: A generated skill that copies another unit's commands and breaks when that unit changes. Lands in create-formal-verification…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:434) *(superseded)*: Owner ruling 2026-11-13: Prevents: A sync commit moved forward over code the verification no longer describes. Lands in create-formal-verification-skill, SKILL…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:433) *(superseded)*: Owner ruling 2026-11-13: Prevents: A generated skill that leaves the next agent unable to run, read or update the check. Lands in create-formal-verification-sk…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:431) *(superseded)*: Owner ruling 2026-11-13: Prevents: Code drifting from its verification without anyone noticing. Lands in create-formal-verification-skill, SKILL.md, a new skil…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:430) *(superseded)*: Owner ruling 2026-11-13: Prevents: A check too slow or fiddly for the next agent to run on each change. Lands in create-formal-verification-skill, SKILL.md, a …
- `2026-11-13` **adopt** (2026-11-13-batch-p2:429) *(superseded)*: Owner ruling 2026-11-13: Prevents: A counterexample in the tool's terms that nobody maps back to the code. Lands in create-formal-verification-skill, SKILL.md,…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:428) *(superseded)*: Owner ruling 2026-11-13: Prevents: A property and its stakes that nobody without the tool can read. Lands in create-formal-verification-skill, SKILL.md, a new …
- `2026-11-13` **adopt** (2026-11-13-batch-p2:427) *(superseded)*: Owner ruling 2026-11-13: Prevents: A pass read as covering more than its model or bound. Lands in create-formal-verification-skill, SKILL.md, a new skill per t…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:424) *(superseded)*: Owner ruling 2026-11-13: Prevents: A property that can never fail, passing and proving nothing. Lands in create-formal-verification-skill, SKILL.md, a new skil…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:423) *(superseded)*: Owner ruling 2026-11-13: Prevents: A verification written in names the project does not use. Lands in create-formal-verification-skill, SKILL.md, a new skill p…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:422) *(superseded)*: Owner ruling 2026-11-13: Prevents: A model that hides a race by treating two steps of the code as one. Lands in create-formal-verification-skill, SKILL.md, a n…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:421) *(superseded)*: Owner ruling 2026-11-13: Prevents: A model a reviewer cannot match to the code it claims to describe. Lands in create-formal-verification-skill, SKILL.md, a ne…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:420) *(superseded)*: Owner ruling 2026-11-13: Prevents: A check only its author can run. Lands in create-formal-verification-skill, SKILL.md, a new skill per the owner's ruling of …
- `2026-11-13` **adopt** (2026-11-13-batch-p2:419) *(superseded)*: Owner ruling 2026-11-13: Prevents: A hand-written model of a function standing in for the function when no verifier supports its language. Lands in create-form…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:418) *(superseded)*: Owner ruling 2026-11-13: Prevents: A heavy tool used where a lighter one answers the question, or a tool that cannot answer it. Lands in create-formal-verifica…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:417) *(superseded)*: Owner ruling 2026-11-13: Prevents: A target chosen because it was easy to verify, not because it mattered. Lands in create-formal-verification-skill, SKILL.md,…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:416) *(superseded)*: Owner ruling 2026-11-13: Prevents: Effort spent verifying code whose failure costs little or that tests already reach. Lands in create-formal-verification-skil…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:415) *(superseded)*: Owner ruling 2026-11-13: Prevents: A target chosen elsewhere when the person named the area or the bug. Lands in create-formal-verification-skill, SKILL.md, a …
- `2026-11-13` **adopt** (2026-11-13-batch-p2:413) *(superseded)*: Owner ruling 2026-11-13: Prevents: A result the person cannot act on without learning the verification language. Lands in create-formal-verification-skill, SKI…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:411) *(superseded)*: Owner ruling 2026-11-13: Prevents: A one-off proof nobody can rerun when the code changes. Lands in create-formal-verification-skill, SKILL.md, a new skill per…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-12-upstream-cursor_plugins-2776ddd-batch-p2.md](../../reviews/2026-11-12-upstream-cursor_plugins-2776ddd-batch-p2.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `adjacent-target-only-if-close`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#adjacent-target-only-if-close` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `atomicity-fidelity`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#atomicity-fidelity` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `cheap-rerun`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#cheap-rerun` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `companion-tool-by-name`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#companion-tool-by-name` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `counterexample-as-code-steps`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#counterexample-as-code-steps` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `coverage-and-sync-record`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#coverage-and-sync-record` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `domain-vocabulary`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#domain-vocabulary` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `fix-skill-not-scratch-break`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#fix-skill-not-scratch-break` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `formal-check-left-as-skill`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#formal-check-left-as-skill` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `generated-check-catches-planted-break`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#generated-check-catches-planted-break` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `generated-input-fallback`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#generated-input-fallback` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `harmful-rarely-tested-promise`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#harmful-rarely-tested-promise` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `installable-tool-preference`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#installable-tool-preference` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `named-scope-first`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#named-scope-first` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `plain-property-and-harm`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#plain-property-and-harm` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `property-fails-on-broken-variant`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#property-fails-on-broken-variant` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `result-trusted-without-the-language`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#result-trusted-without-the-language` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `strongest-target-not-easiest`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#strongest-target-not-easiest` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `sync-commit-advanced-after-match`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#sync-commit-advanced-after-match` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `traceable-to-code`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#traceable-to-code` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `verification-handoff-report`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#verification-handoff-report` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `verification-tool-by-question`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#verification-tool-by-question` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `verified-scope-statement`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#verified-scope-statement` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `verify-skill-capabilities`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#verify-skill-capabilities` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
