---
skill: maintain-formal-verification-skill
domain: engineering
stage: Improvement
substage: Codification
secondary: [Testing]
family:
aliases: []
status: active
---
# maintain-formal-verification-skill

Use for /maintain-formal-verification-skill when a project's formal verify skill may no longer describe its code after changes made without it; with none, /create-formal-verification-skill makes one, and checking your own change uses the verify skill itself. Sorts every change to covered code since the sync commit, updates the model from the code, reruns, and gives each check one outcome: in sync, updated, bug or blocked.

**Boundary:** Brings an existing formal verify skill back in line with its code after changes that skipped it, sorting every covered change, updating the model from the code and rerunning, with one outcome per check; generating one is create-formal-verification-skill, an app-driving verify skill is maintain-verification-skill, and checking or drawing one TLA+ model is statechart.

<!-- registry:generated traits -->
- `per-check-outcome`: Give each check one named outcome, in sync, updated, bug or blocked with the reason, allowing updated and bug together when an update restores fidelity and the property then fails. (Q1 move (owner rulings of 2026-11-15, item 1): a faithful update followed by a failing property is "updated and bug" (SKILL.md:38); the update is kept and the record moves with it (SKILL.md:166-170), so the skill describes the code it checks and fails there until a fix or an evidenced promise change.)
- `per-check-inventory`: Collect for each check its property, covered code, bounds and assumptions, run command and last sync commit.
- `inferred-sync-commit`: With no recorded sync commit, take the most recent commit that touched the verification files and say so.
- `baseline-check-before-change`: Before the first change of multi-step work, run its checks on the starting base and record the results, so later failures are classed as pre-existing or as regressions.
- `failure-classified-after-rerun`: Leave a baseline failure unclassified as drift or bug until the rerun-and-judge step.
- `covered-change-sweep`: Diff the covered files since the sync commit and read each commit message, following renamed, split or moved code and new writers of the guarded state.
- `four-way-change-classification`: Classify each change as no effect, verification out of date, promise changed on purpose or promise maybe broken, treating a changed promise without evidence as a bug candidate.
- `no-effect-judged-by-model`: Judge that a change has no effect against the model or harness, not the commit message.
- `intended-change-needs-evidence`: Count a promise as changed on purpose only with evidence cited from the change, such as a doc comment, tests, changelog or commit message.
- `update-from-code-before-rerun`: Write a model update from the code before rerunning, never shaped by what makes the check pass.
- `traceable-to-code`: Make every part of a verification model or proof point to code a reviewer can open. (Applied at SKILL.md:114-116 from its one home create-formal-verification-skill/references/model-fidelity.md:10-28 ("Traceability table", decision 4), each citation at the commit checked; restated nowhere here.)
- `atomicity-fidelity`: Treat as one indivisible step in the verification only what is one indivisible step in the code. (Applied at SKILL.md:114-116 from its one home create-formal-verification-skill/references/model-fidelity.md:30-37 ("Indivisible steps", decision 4); restated nowhere here.)
- `property-change-audit-trail`: Change a property only for a promise changed on purpose, recording its wording before and after and the evidence.
- `keep-bounds`: Keep the bounds unless a change makes them wrong, and report any reduction.
- `property-fails-on-broken-variant`: Show each property failing on a deliberately broken variant of the code it guards, after first writing it and after each update. (Applied at SKILL.md:129-133 from its one home create-formal-verification-skill/references/model-fidelity.md:39-56 ("Broken variants", decision 4). Q1 move (owner rulings of 2026-11-15, item 1): while the main run fails a variant's verdict means nothing and is accepted again only from a run whose main run holds (SKILL.md:141-142, the reply at SKILL.md:194; create-formal-verification-skill/references/model-fidelity.md:64-66).)
- `counterexample-replayed-on-code`: Replay each counterexample step by step against the real code, presuming a step that cannot happen to be a model error until shown otherwise. (The replay includes every step a writer runs between the model's last modelled check and its commit (SKILL.md:134-139), the proof's lesson 1 applied in the build's round 3 (92/proof-report.md).)
- `bug-report-fields`: Give a confirmed bug the commit that introduced it, its counterexample told in the code's terms and its harm in one sentence.
- `uncommitted-repro-evidence`: Put a cheap test or reproduction showing the bug in the report as evidence without committing it to product code. (Plan 92 §3a.4: the reproduction is a scratch model configuration (fewer writers, a smaller bound) or a scratch test needing no service, kept in the run's notes and given or linked with its result in the reply, never in product code or the skill (SKILL.md:153-156).)
- `verify-skill-metadata-refresh`: Update each check's covered code, commands, bounds, assumptions and sync commit in the verification skill, setting the sync commit to the one checked. (Q1 move (owner rulings of 2026-11-15, item 1): the refresh to the commit checked runs on a confirmed bug too, with the faithful update (SKILL.md:166-170; create-formal-verification-skill/references/coverage-record.md:51-58, create-formal-verification-skill/references/formal-verify-skill.md:76-80).)
- `blocked-check-sync-freeze`: Leave a blocked check's sync commit where it was, and say so.
- `per-check-report`: Report per check the outcome, commits read, each verification change with its reason, the rerun result and the break used, each bug in plain words with its commit and the coverage gaps left, saying outright which failures were drift and which were bugs.
- `stale-pass-disclosure`: For a check that passed before an update and fails after, say the old pass was against a stale description.
- `separate-verification-change`: Keep verification updates in their own change, apart from any product fix.
- `verification-only-edits`: During a verification pass, edit only the verification skill's own files and never product code unless asked. (Held (decision 3): a maintain pass edits only the target skill's own folder, and product code only when the person asks (SKILL.md:19-22).)
- `target-found-by-content`: Find the verification skill to maintain by what it does, not by a fixed name, or use the one the person named. (Held (decisions 3 and 5): the skill the person named, else every host skills folder searched by content as formal-verify-skill.md "How other units recognise it" describes; a folder name is only a hint (SKILL.md:42-46).)
- `no-target-points-to-create`: When no verification skill exists, stop and point to the unit that creates one rather than inventing one. (Held (decision 3): with none found it stops and points to /create-formal-verification-skill, writing no skill; a verify skill that drives the real app goes to /maintain-verification-skill (SKILL.md:46-48).)
- `check-never-weakened-to-pass`: When a check fails on the current product, report the failure and never weaken the check or its model to make it pass. (Held (decision 3): never loosen a property, the model or its bounds so that a run passes; a failure on the current code is a finding (SKILL.md:22-23).)
- `generated-skill-run-once`: Follow a generated skill end to end once, as its next reader would, before handing it over, counting an unrun skill as a draft. (Held (decision 3; bead cr-r2pa.2.28.6, owner rulings of 2026-11-15, item 5): the refreshed skill is followed once as its next reader would, its drift diff, Run command and exit code, and every command the refresh changed or added runs as written before hand-over; unfollowed, it is a draft (SKILL.md:173-176). The item's other half, hashing evidence and scanning for generated credentials before teardown, has no counterpart: a formal pass tears nothing down and generates no credential.)
- `generated-skill-left-uncommitted`: Leave the generated skill and its map uncommitted unless the person asks for a commit, which the commit skill then makes. (Held (decision 10): the verification edits stay one uncommitted change for land (SKILL.md:181-182); the definition's "and its map" reads as coverage.json, as create-formal-verification-skill's note says.)
- `generator-started-by-person`: Run the skill generator only when the person starts it: manual-only in its frontmatter and its sidecar, reached through setup, help or a router line, never by the model on its own. (Held (decision 1): manual-only in its frontmatter (SKILL.md:4) and sidecar, said in the body (SKILL.md:14-15) and reached through its mvp-mode router row; the definition's "skill generator" is read as the same activation rule, as accepted for maintain-verification-skill (critic-85e).)
- `installed-recipe-or-blocked`: In a maintenance pass, install a missing tool only by the recipe the target skill records, project-local or per user and pinned, never system-wide; with none recorded, mark the work that needs the tool blocked and name it. (Held (decision 6): a missing tool is installed only by the per-user recipe and pins the skill records, never system-wide; without a recorded recipe the check is blocked, naming what is missing (SKILL.md:77-80). Q4 (owner rulings of 2026-11-15, item 4): a generated formal skill now names that recipe (create-formal-verification-skill/references/formal-verify-skill.md:63-66).)
- `checker-install-approved-per-user`: Install a missing model checker or its runtime only after the person approves it, and then per user under their home folder, never system-wide, as root or through a shell-profile change; without approval, stop and name what is missing. (Held (decision 6, L2): the install waits for the person's approval and goes per user, never as root or through a shell-profile change; without approval the check is blocked, naming what is missing (SKILL.md:77-80).)
- `sync-commit-advanced-after-match`: Move the recorded sync commit forward only after confirming the verification matches the code at the new commit. (Held, adapted by Q1 move (owner rulings of 2026-11-15, item 1): sync_commit moves once the covered diff is read, the model updated from it and the rerun gives its expected verdicts, and on a confirmed bug it moves too with the faithful update, which matches the code as the definition asks; the check then fails there (SKILL.md:166-170; create-formal-verification-skill/references/coverage-record.md:51-58).)
- `pre-existing-edit-separation`: Separate pre-existing edits from the task's own changes using the task baseline, not filenames. (Held (decision 10): the checkout's status, diff and the target's hash list are recorded before any edit, so the person's own edits stay apart from this pass's (SKILL.md:50-52).)
- `coverage-and-sync-record`: Record, per check, the files and functions it guards and the last commit it was confirmed against, so drift shows. (Held (decision 7): per check the pass reads covers and sync_commit from coverage.json and refreshes them at step 6; for an older skill without the file it gathers the record from the skill's text and writes it (SKILL.md:58-61; create-formal-verification-skill/references/coverage-record.md:62-65).)
- `formal-coverage-data-file`: Keep a formal verify skill's coverage and sync record in one small data file of a versioned format beside its skill file, never as prose inside the skill, so its check script, the maintenance unit and freshness checks read the same record. (Held (decision 7): that record is written as coverage.json beside SKILL.md by coverage-record.md, kept as data, never as prose (SKILL.md:58-61).)
- `counterexample-as-code-steps`: Describe a counterexample as a few steps phrased in the code's own terms. (Held (decision 3): a confirmed bug's counterexample is given as a few numbered steps in the code's own terms (function, row, lock) (SKILL.md:151-153), in the sentence that also carries bug-report-fields.)
- `verify-skill-capabilities`: Let the next agent learn from the skill alone whether a change touches verified code, how to run the check, how to tell a real bug from a modelling error and how to update the verification for an intended change. (Held (coordinator's ruling on blind extra 3, 92/build-report.md Round 2): a maintain pass keeps the skill's fixed sections (formal-verify-skill.md "Sections") through any fix (SKILL.md:23-24) and refreshes their table, Run output and sync mentions (SKILL.md:160-164), so the next agent still learns all four from the skill alone.)
- `verdict-from-exit-and-messages`: Count a checker run as a verdict only when its exit code and its own completion and violation messages agree, with every rule checked where the checker checks all reachable states and no option that hides a violation. (Held at SKILL.md step 5 ("Judge each rerun by its exit code and the checker's own messages together", SKILL.md:126-127); the definition's remaining clauses, every rule checked where the checker checks all reachable states and no option that hides a violation, arrive through the pointer to create-formal-verification-skill/references/tool-branches.md and its TLC gate (safety rules under INVARIANT, temporal formulas only under PROPERTY, never -continue), by decision D4 (blind check Weak 2). Owner-accepted on 2026-11-15 (owner rulings of 2026-11-15, item 6).)
- `formal-contract-gaps-reported`: In a maintenance pass over a formal verify skill, compare the skill with the formal contract as it is now (its sections, its runner's steps and its recorded install recipe) and report each gap as a follow-up, fixing none, except writing the coverage record for a skill that has none. (Ours (owner rulings of 2026-11-15, item 2, Q2 report): the skill is compared with formal-verify-skill.md as it is now, its sections, check.py steps 1-6 and the install recipe its Run section names, and each gap goes to the reply as a follow-up, none fixed, except writing coverage.json for a skill that lacks it (SKILL.md:63-67).)
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#per-check-outcome** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#per-check-inventory** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#inferred-sync-commit** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#baseline-check-before-change** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#failure-classified-after-rerun** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#covered-change-sweep** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#four-way-change-classification** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#no-effect-judged-by-model** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#intended-change-needs-evidence** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#update-from-code-before-rerun** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#traceable-to-code** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#atomicity-fidelity** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#property-change-audit-trail** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#keep-bounds** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#property-fails-on-broken-variant** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#counterexample-replayed-on-code** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#bug-report-fields** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#uncommitted-repro-evidence** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#verify-skill-metadata-refresh** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#blocked-check-sync-freeze** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#per-check-report** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#stale-pass-disclosure** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#separate-verification-change** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:024): Completes pending 2026-11-13-batch-p2:470: separate-verification-change is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:180-181, in it…
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:023): Completes pending 2026-11-13-batch-p2:469: stale-pass-disclosure is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:201-202, in its ruled…
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:022): Completes pending 2026-11-13-batch-p2:468: per-check-report is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:186-201, in its ruled word…
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:021): Completes pending 2026-11-13-batch-p2:466: blocked-check-sync-freeze is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:170-171, in its r…
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:020): Completes pending 2026-11-13-batch-p2:465: verify-skill-metadata-refresh is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:160-164, in i…
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:019): Completes pending 2026-11-13-batch-p2:464: uncommitted-repro-evidence is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:153-156, in its …
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:018): Completes pending 2026-11-13-batch-p2:463: bug-report-fields is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:144-153, in its ruled wor…
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:017): Completes pending 2026-11-13-batch-p2:462: counterexample-replayed-on-code is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:134-139, in…
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:016): Completes pending 2026-11-13-batch-p2:461: property-fails-on-broken-variant is applied at .claude/skills/maintain-formal-verification-skill/SKILL.md:129-133 fr…
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:015): Completes pending 2026-11-13-batch-p2:460: keep-bounds is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:120-122, in its ruled words (pl…
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:014): Completes pending 2026-11-13-batch-p2:459: property-change-audit-trail is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:118-120, in its…
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:013): Completes pending 2026-11-13-batch-p2:458: atomicity-fidelity is applied at .claude/skills/maintain-formal-verification-skill/SKILL.md:114-116 from .claude/ski…
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:012): Completes pending 2026-11-13-batch-p2:457: traceable-to-code is applied at .claude/skills/maintain-formal-verification-skill/SKILL.md:114-116 from .claude/skil…
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:011): Completes pending 2026-11-13-batch-p2:456: update-from-code-before-rerun is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:113-114, in i…
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:010): Completes pending 2026-11-13-batch-p2:455: intended-change-needs-evidence is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:107-109, in …
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:009): Completes pending 2026-11-13-batch-p2:454: no-effect-judged-by-model is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:106-107, in its r…
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:008): Completes pending 2026-11-13-batch-p2:453: four-way-change-classification is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:93-104, in i…
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:007): Completes pending 2026-11-13-batch-p2:452: covered-change-sweep is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:84-91, in its ruled wo…
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:006): Completes pending 2026-11-13-batch-p2:451: failure-classified-after-rerun is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:74-75, in it…
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:005): Completes pending 2026-11-13-batch-p2:450: baseline-check-before-change is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:71-74, in its …
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:004): Completes pending 2026-11-13-batch-p2:449: inferred-sync-commit is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:56-58, in its ruled wo…
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:003): Completes pending 2026-11-13-batch-p2:447: per-check-inventory is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:54-56, in its ruled wor…
- `2026-11-15` **adopt** (2026-11-15-maintain-formal-verification-skill:002): Completes pending 2026-11-13-batch-p2:443: per-check-outcome is written at .claude/skills/maintain-formal-verification-skill/SKILL.md:28-38, in its ruled words…
- `2026-11-15` **add** (2026-11-15-maintain-formal-verification-skill:001): Bead cr-r2pa.2.28.5, plan 92 (with its Round 2 table). New manual skill (decision 1: manual-only in frontmatter and sidecar, reached through its mvp-mode route…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:471): Checkpoint at 2776ddd for the owner's trait rulings: 28 adopt.
- `2026-11-13` **adopt** (2026-11-13-batch-p2:470) *(superseded)*: Owner ruling 2026-11-13: Prevents: Verification updates mixed into a product fix, so neither can be reviewed alone. Lands in maintain-formal-verification-skill…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:469) *(superseded)*: Owner ruling 2026-11-13: Prevents: An old pass still trusted after it turned out to describe code that no longer exists. Lands in maintain-formal-verification-…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:468) *(superseded)*: Owner ruling 2026-11-13: Prevents: A report that does not say which failures were drift and which were bugs. Lands in maintain-formal-verification-skill, SKILL…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:466) *(superseded)*: Owner ruling 2026-11-13: Prevents: A blocked check's sync commit moved as if it had been confirmed. Lands in maintain-formal-verification-skill, SKILL.md, a ne…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:465) *(superseded)*: Owner ruling 2026-11-13: Prevents: A verification skill whose recorded coverage and commands no longer match the check. Lands in maintain-formal-verification-s…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:464) *(superseded)*: Owner ruling 2026-11-13: Prevents: A reproduction committed into product code during a verification pass. Lands in maintain-formal-verification-skill, SKILL.md…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:463) *(superseded)*: Owner ruling 2026-11-13: Prevents: A bug report nobody can trace to its commit or its harm. Lands in maintain-formal-verification-skill, SKILL.md, a new skill …
- `2026-11-13` **adopt** (2026-11-13-batch-p2:462) *(superseded)*: Owner ruling 2026-11-13: Prevents: A model error reported as a bug in the code. Lands in maintain-formal-verification-skill, SKILL.md, a new skill per the owne…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:461) *(superseded)*: Owner ruling 2026-11-13: Prevents: An updated check that can no longer fail. Lands in maintain-formal-verification-skill, SKILL.md, a new skill per the owner's…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:460) *(superseded)*: Owner ruling 2026-11-13: Prevents: Bounds shrunk until the check passes, and the shrinking never reported. Lands in maintain-formal-verification-skill, SKILL.m…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:459) *(superseded)*: Owner ruling 2026-11-13: Prevents: A property quietly rewritten with no record of why. Lands in maintain-formal-verification-skill, SKILL.md, a new skill per t…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:458) *(superseded)*: Owner ruling 2026-11-13: Prevents: An updated model that hides a race by treating two steps of the code as one. Lands in maintain-formal-verification-skill, SK…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:457) *(superseded)*: Owner ruling 2026-11-13: Prevents: An updated model a reviewer cannot match to the code it claims to describe. Lands in maintain-formal-verification-skill, SKI…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:456) *(superseded)*: Owner ruling 2026-11-13: Prevents: A model tuned to make the check pass instead of to match the code. Lands in maintain-formal-verification-skill, SKILL.md, a …
- `2026-11-13` **adopt** (2026-11-13-batch-p2:455) *(superseded)*: Owner ruling 2026-11-13: Prevents: A broken promise relabelled as an intended change. Lands in maintain-formal-verification-skill, SKILL.md, a new skill per th…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:454) *(superseded)*: Owner ruling 2026-11-13: Prevents: A change waved through on its commit message that alters what the model describes. Lands in maintain-formal-verification-ski…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:453) *(superseded)*: Owner ruling 2026-11-13: Prevents: Every change treated alike, so a broken promise is filed as drift. Lands in maintain-formal-verification-skill, SKILL.md, a …
- `2026-11-13` **adopt** (2026-11-13-batch-p2:452) *(superseded)*: Owner ruling 2026-11-13: Prevents: Changes to covered code missed because the code was renamed, moved or written from somewhere new. Lands in maintain-formal-v…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:451) *(superseded)*: Owner ruling 2026-11-13: Prevents: A baseline failure called drift or a bug before the evidence is in. Lands in maintain-formal-verification-skill, SKILL.md, a…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:450) *(superseded)*: Owner ruling 2026-11-13: Prevents: Drift and new bugs confused because nobody ran the check before changing it. Lands in maintain-formal-verification-skill, SK…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:449) *(superseded)*: Owner ruling 2026-11-13: Prevents: A pass that stops for want of a recorded sync commit, or guesses one silently. Lands in maintain-formal-verification-skill, …
- `2026-11-13` **adopt** (2026-11-13-batch-p2:447) *(superseded)*: Owner ruling 2026-11-13: Prevents: Checks maintained without knowing what each covers or how it runs. Lands in maintain-formal-verification-skill, SKILL.md, a …
- `2026-11-13` **adopt** (2026-11-13-batch-p2:443) *(superseded)*: Owner ruling 2026-11-13: Prevents: A pass that leaves the state of each check unclear. Lands in maintain-formal-verification-skill, SKILL.md, a new skill per t…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-12-upstream-cursor_plugins-2776ddd-batch-p2.md](../../reviews/2026-11-12-upstream-cursor_plugins-2776ddd-batch-p2.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `atomicity-fidelity`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#atomicity-fidelity` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `baseline-check-before-change`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#baseline-check-before-change` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `blocked-check-sync-freeze`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#blocked-check-sync-freeze` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `bug-report-fields`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#bug-report-fields` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `counterexample-replayed-on-code`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#counterexample-replayed-on-code` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `covered-change-sweep`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#covered-change-sweep` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `failure-classified-after-rerun`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#failure-classified-after-rerun` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `four-way-change-classification`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#four-way-change-classification` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `inferred-sync-commit`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#inferred-sync-commit` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `intended-change-needs-evidence`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#intended-change-needs-evidence` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `keep-bounds`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#keep-bounds` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `no-effect-judged-by-model`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#no-effect-judged-by-model` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `per-check-inventory`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#per-check-inventory` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `per-check-outcome`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#per-check-outcome` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `per-check-report`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#per-check-report` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `property-change-audit-trail`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#property-change-audit-trail` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `property-fails-on-broken-variant`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#property-fails-on-broken-variant` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `separate-verification-change`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#separate-verification-change` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `stale-pass-disclosure`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#stale-pass-disclosure` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `traceable-to-code`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#traceable-to-code` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `uncommitted-repro-evidence`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#uncommitted-repro-evidence` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `update-from-code-before-rerun`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#update-from-code-before-rerun` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `verify-skill-metadata-refresh`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#verify-skill-metadata-refresh` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
