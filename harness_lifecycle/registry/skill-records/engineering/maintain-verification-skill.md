---
skill: maintain-verification-skill
domain: engineering
stage: Improvement
substage: Codification
secondary: [Testing]
family:
aliases: []
status: active
---
# maintain-verification-skill

Use for /maintain-verification-skill when a project's verify skill that drives its real app may have drifted from the product; with no verify skill, /create-verification-skill makes one, and proving one change uses the verify skill itself. Reads every mapped feature from source, drives each one live, fixes proven drift in the skill and its map, and ends clean, changed or blocked.

**Boundary:** Keeps an existing verify skill and its feature map true to the real app by reading every feature from source and driving each live, fixing only proven drift; generating one is create-verification-skill, judging a change by reading is review, and running a project's invariant checks is check-invariants.

<!-- registry:generated traits -->
- `target-found-by-content`: Find the verification skill to maintain by what it does, not by a fixed name, or use the one the person named.
- `no-target-points-to-create`: When no verification skill exists, stop and point to the unit that creates one rather than inventing one.
- `verification-only-edits`: During a verification pass, edit only the verification skill's own files and never product code unless asked.
- `index-hygiene`: Compare the map index with its feature files and fix missing, extra, duplicate or dead entries by hand, building no generated inventory.
- `source-reader-per-sizeable-feature`: Give a feature's source reading its own read-only helper only when it is sizeable and independent, reading small ones directly.
- `source-reader-return-shape`: Have each source reader return the feature summary, its source entry points, likely drift with citations or none, and one short live recipe. (Its sealed row lands in SKILL.md; it is written in references/source-reader.md, the reader brief SKILL.md step 3 loads, and restated there. The brief also says a citation names the line that holds the claim and a guess is marked as a guess, never cited as drift: this trait's citation requirement with AGENTS.md's certainty policy (certainty-labelling), so neither is a trait of its own (critic-85e).)
- `source-readers-never-drive`: Keep source readers from driving the product or editing files.
- `missing-result-not-pass`: In coverage work, require a result for every required slice and count a missing one as a gap, never a pass.
- `merge-recipes-few-states`: Merge overlapping live recipes into as few product states as practical.
- `spot-check-cited-drift`: Check the drift readers cited, without re-proving what they reported clean.
- `churn-sweep-with-source-path`: Sweep recent changes for user-facing surfaces the map lacks, and cite the source file that shows one before reporting it absent.
- `every-feature-source-and-live`: Cover each feature both from its source and live at least once, even when the source reading looks clean, without testing every sentence.
- `coordinator-only-driving`: Leave all driving of the product to the coordinator.
- `launch-model-from-skill`: Follow the target skill's launch section to choose one long-lived instance or a fresh isolated session per drive.
- `doctor-at-fixed-points`: Run the doctor check before the first drive, on each fresh session and after any failed drive, resetting or relaunching where it cannot see the fault.
- `failed-drive-residue-cleanup`: Clean up what a failed drive left, whether its session hung, ended or is shared, taking only that residue from a shared instance.
- `drift-doctor-fix-retry-once`: Treat a doctor failure caused by skill drift as drift: fix it within scope, restart only what the fix invalidated and retry once before declaring blocked.
- `unreachable-with-route-and-prerequisite`: Report a feature as unreachable only with the route tried and the prerequisite that was missing.
- `map-drift-or-regression`: Classify a gap between map and product as doc drift to fix or a product regression to report outside the change, never hiding a regression in the docs.
- `harness-gap-fix`: Fix working behaviour the harness cannot drive as a harness gap, under the same runnable-and-documented helper rule.
- `omitted-prerequisite-is-drift`: Count a prerequisite the map fails to mention as drift.
- `harness-fix-redriven`: Drive any harness fix live again before it ships.
- `evidence-checked-after-cleanup`: After cleanup, confirm the captured evidence still exists where the skill says it is, and fail the step if it does not.
- `final-teardown-after-last-drive`: Tear down only after the run's last drive, re-proofs included, leaving the evidence in place.
- `one-pass-outcome`: End each pass with exactly one outcome, clean, changes or blocked, a blocked pass saying exactly what stopped it.
- `no-change-outcome-report`: When a pass is clean or blocked, open no change and report the outcome and coverage honestly.
- `one-change-of-proven-fixes`: Gather a pass's proven fixes to docs, harness and map into one change, opening a pull request for it only with authority to do so.
- `reread-changed-files-whole`: Read each changed file in full, not only its diff, before shipping the change.
- `check-never-weakened-to-pass`: When a check fails on the current product, report the failure and never weaken the check or its model to make it pass. (Reused for the maintenance pass (R3, a short guardrail restated per unit): a failing journey is fixed only when source proves the map wrong, never by loosening the journey, its check or its expected value (SKILL.md step 6).)
- `live-service-isolation`: When the product uses a live service, run every command of a generated skill from a clean environment holding only the run's own values, refuse a project env file, prove before the first write that the endpoint is the run's own (its address, data folder, a marker the run planted, a sign-in with credentials the run made), and run only the commands the skill lists. (Reused for the maintenance pass (ruling A): every product command goes through the target's own helper; when the product uses a live service and the target lacks the generated-skill Isolation controls, the pass does not drive and stops blocked, naming the missing control (SKILL.md step 5).)
- `dry-run-skips-observed`: When a generated skill relies on a dry-run or offline mode, record step by step what the proof run observed that mode skip, running without a network or tracing connections, never trusting the mode by its name. (Reused for the maintenance pass (Q1): each drive re-observes what the skill records an offline or dry-run mode skipping, by generated-skill Evidence, and a drive without that observation is no proof (SKILL.md step 5).)
- `undriven-feature-marked`: Mark a seeded feature the proof run did not drive as not yet driven, in its file and on its index line, giving its results as what to assert, never as values nobody observed. (Reused for the maintenance pass (ruling B, with the coordinator's ruling on cases): a feature keeps its index mark while any of its cases is undriven, its file naming each such case with route and prerequisite; driving a case writes its observed results there and takes it off the list (SKILL.md step 5).)
- `change-proven-by-second-read`: Prove a change persisted by reading it back through a separate read-only view, such as reopening the item from the list, not by its save confirmation. (Reused for the maintenance pass (ruling C, blind delta 88): each saved change names the product command that shows the saved item itself; a view of counts or a fingerprint, or the helper's own query, is not one (SKILL.md step 5, loading feature-map Proof by surface).)
- `unreadable-change-unverified`: When the product has no read-only way to read a change back, say so in the feature file and report the change as unverified, not proven. (Reused for the maintenance pass (ruling C), unconditionally: with no read-only product view, the feature file says so and the coverage report lists the change unverified, never clean; a helper's own query is kept only as a labelled helper observation (SKILL.md step 5 and Reply).)
- `credentials-never-captured`: Never print, log or keep a credential a generated skill uses, one the run generated included, and parse tool output that can hold one (resolved service config, container inspection, a connection string) inside the helper without saving it. (Reused for the maintenance pass (ruling D): no credential, generated ones included, in evidence, notes, the reply or a helper diff; output that can hold one is parsed inside the helper and never saved, and the rule is rechecked after a harness fix (SKILL.md steps 5 and 6).)
- `generated-skill-left-uncommitted`: Leave the generated skill and its map uncommitted unless the person asks for a commit, which the commit skill then makes. (Reused for the maintenance pass (R10): the one set of proven fixes stays uncommitted for land, with no branch, commit or pull request unless the person asks (SKILL.md step 8).)
- `generator-started-by-person`: Run the skill generator only when the person starts it: manual-only in its frontmatter and its sidecar, reached through setup, help or a router line, never by the model on its own. (Reused for the maintenance pass (R1): manual-only in its frontmatter and its sidecar, reached through the mvp-mode router line; the definition names the generator, and critic-85e accepted the same activation mechanism as reuse.)
- `installed-recipe-or-blocked`: In a maintenance pass, install a missing tool only by the recipe the target skill records, project-local or per user and pinned, never system-wide; with none recorded, mark the work that needs the tool blocked and name it.
- `contract-gaps-reported`: In a maintenance pass, check the maintained skill against the current shared contracts and report each gap as a follow-up, fixing one only when a drive proves it; a missing live-service isolation control blocks the pass instead.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#every-feature-source-and-live** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#one-pass-outcome** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#no-change-outcome-report** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#one-pr-of-proven-fixes** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#verification-only-edits** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#map-drift-or-regression** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#harness-gap-fix** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#target-found-by-content** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#no-target-points-to-create** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#index-hygiene** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#per-feature-source-readers** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#source-reader-return-shape** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#source-readers-never-drive** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#missing-result-not-pass** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#merge-recipes-few-states** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#spot-check-cited-drift** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#churn-sweep-with-source-path** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#coordinator-only-driving** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#launch-model-from-skill** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#doctor-at-fixed-points** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#evidence-checked-after-cleanup** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#failed-drive-residue-cleanup** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#drift-doctor-fix-retry-once** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#unreachable-with-route-and-prerequisite** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#omitted-prerequisite-is-drift** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#harness-fix-redriven** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#final-teardown-after-last-drive** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-verification-skill#reread-changed-files-whole** `pstack/skills/maintain-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/create-formal-verification-skill#verification-only-edits** `pstack/skills/create-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#verification-only-edits** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#target-found-by-content** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
- **cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#no-target-points-to-create** `pstack/skills/maintain-formal-verification-skill/SKILL.md` @ 2776ddd2355d6d6c8747d3964600f28daf62f049
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:033): Completes pending 2026-11-13-batch-p2:448: no-target-points-to-create is written at .claude/skills/maintain-verification-skill/SKILL.md:42-43, in its ruled wor…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:032): Completes pending 2026-11-13-batch-p2:446: target-found-by-content is written at .claude/skills/maintain-verification-skill/SKILL.md:35-39, in its ruled words …
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:031): Completes pending 2026-11-13-batch-p2:444: verification-only-edits is written at .claude/skills/maintain-verification-skill/SKILL.md:17-19, in its ruled words …
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:030): Completes pending 2026-11-13-batch-p2:426: verification-only-edits is written at .claude/skills/maintain-verification-skill/SKILL.md:17-19, in its ruled words …
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:029): Completes pending 2026-11-13-batch-p2:408: reread-changed-files-whole is written at .claude/skills/maintain-verification-skill/SKILL.md:159, in its ruled words…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:028): Completes pending 2026-11-13-batch-p2:407: final-teardown-after-last-drive is written at .claude/skills/maintain-verification-skill/SKILL.md:150-151, in its ru…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:027): Completes pending 2026-11-13-batch-p2:406: harness-fix-redriven is written at .claude/skills/maintain-verification-skill/SKILL.md:143-145, in its ruled words (…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:026): Completes pending 2026-11-13-batch-p2:405: omitted-prerequisite-is-drift is written at .claude/skills/maintain-verification-skill/SKILL.md:133-134, in its rule…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:025): Completes pending 2026-11-13-batch-p2:404: unreachable-with-route-and-prerequisite is written at .claude/skills/maintain-verification-skill/SKILL.md:106-107, i…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:024): Completes pending 2026-11-13-batch-p2:403: drift-doctor-fix-retry-once is written at .claude/skills/maintain-verification-skill/SKILL.md:100-103, in its ruled …
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:023): Completes pending 2026-11-13-batch-p2:402: failed-drive-residue-cleanup is written at .claude/skills/maintain-verification-skill/SKILL.md:96-99, in its ruled w…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:022): Completes pending 2026-11-13-batch-p2:401: evidence-checked-after-cleanup is written at .claude/skills/maintain-verification-skill/SKILL.md:149-150, in its rul…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:021): Completes pending 2026-11-13-batch-p2:400: doctor-at-fixed-points is written at .claude/skills/maintain-verification-skill/SKILL.md:92-95, in its ruled words (…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:020): Completes pending 2026-11-13-batch-p2:399: launch-model-from-skill is written at .claude/skills/maintain-verification-skill/SKILL.md:85-86, in its ruled words …
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:019): Completes pending 2026-11-13-batch-p2:398: coordinator-only-driving is written at .claude/skills/maintain-verification-skill/SKILL.md:83 (restated at .claude/s…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:018): Completes pending 2026-11-13-batch-p2:397: churn-sweep-with-source-path is written at .claude/skills/maintain-verification-skill/SKILL.md:72-76, in its ruled w…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:017): Completes pending 2026-11-13-batch-p2:396: spot-check-cited-drift is written at .claude/skills/maintain-verification-skill/SKILL.md:68-69, in its ruled words (…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:016): Completes pending 2026-11-13-batch-p2:395: merge-recipes-few-states is written at .claude/skills/maintain-verification-skill/SKILL.md:70-71, in its ruled words…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:015): Completes pending 2026-11-13-batch-p2:394: missing-result-not-pass is written at .claude/skills/maintain-verification-skill/SKILL.md:64, in its ruled words (pl…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:014): Completes pending 2026-11-13-batch-p2:393: source-readers-never-drive is written at .claude/skills/maintain-verification-skill/references/source-reader.md:17-1…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:013): Completes pending 2026-11-13-batch-p2:392: source-reader-return-shape is written at .claude/skills/maintain-verification-skill/references/source-reader.md:21-3…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:012): Completes pending 2026-11-13-batch-p2:391: source-reader-per-sizeable-feature is written at .claude/skills/maintain-verification-skill/SKILL.md:58-63 (restated…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:011): Completes pending 2026-11-13-batch-p2:390: index-hygiene is written at .claude/skills/maintain-verification-skill/SKILL.md:51-53, in its ruled words (plan 82).
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:010): Completes pending 2026-11-13-batch-p2:389: no-target-points-to-create is written at .claude/skills/maintain-verification-skill/SKILL.md:42-43, in its ruled wor…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:009): Completes pending 2026-11-13-batch-p2:387: target-found-by-content is written at .claude/skills/maintain-verification-skill/SKILL.md:35-39, in its ruled words …
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:008): Completes pending 2026-11-13-batch-p2:386: harness-gap-fix is written at .claude/skills/maintain-verification-skill/SKILL.md:136-138, in its ruled words (plan …
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:007): Completes pending 2026-11-13-batch-p2:385: map-drift-or-regression is written at .claude/skills/maintain-verification-skill/SKILL.md:130-140, in its ruled word…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:006): Completes pending 2026-11-13-batch-p2:384: verification-only-edits is written at .claude/skills/maintain-verification-skill/SKILL.md:17-19, in its ruled words …
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:005): Completes pending 2026-11-13-batch-p2:383: one-change-of-proven-fixes is written at .claude/skills/maintain-verification-skill/SKILL.md:160-161, in its ruled w…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:004): Completes pending 2026-11-13-batch-p2:382: no-change-outcome-report is written at .claude/skills/maintain-verification-skill/SKILL.md:155-158, in its ruled wor…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:003): Completes pending 2026-11-13-batch-p2:381: one-pass-outcome is written at .claude/skills/maintain-verification-skill/SKILL.md:24-31, in its ruled words (plan 8…
- `2026-11-14` **adopt** (2026-11-14-maintain-verification-skill:002): Completes pending 2026-11-13-batch-p2:380: every-feature-source-and-live is written at .claude/skills/maintain-verification-skill/SKILL.md:82, in its ruled wor…
- `2026-11-14` **add** (2026-11-14-maintain-verification-skill:001): Owner rulings of 2026-11-14 on the verification units (decisions 1-11, 13 and 15 as recommended, cited R1-R15; scratchpad/mvp-stack/owner-rulings-2026-11-13.md…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:448) *(superseded)*: Owner ruling 2026-11-13: Prevents: A maintenance pass that invents a verification skill instead of creating one properly. Lands in maintain-verification-skill,…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:446) *(superseded)*: Owner ruling 2026-11-13: Prevents: A pass that maintains the wrong skill, or none, because it looked for a name. Lands in maintain-verification-skill, SKILL.md…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:444) *(superseded)*: Owner ruling 2026-11-13: Prevents: A verification pass that changes the product to make its own checks pass. Lands in maintain-verification-skill, SKILL.md, a …
- `2026-11-13` **adopt** (2026-11-13-batch-p2:426) *(superseded)*: Owner ruling 2026-11-13: Prevents: A verification pass that changes the product to make its own checks pass. Lands in maintain-verification-skill, SKILL.md, a …
- `2026-11-13` **adopt-merged** (2026-11-13-batch-p2:410): Checkpoint at 2776ddd for the owner's trait rulings: 29 adopt, 1 reject.
- `2026-11-13` **adopt** (2026-11-13-batch-p2:408) *(superseded)*: Owner ruling 2026-11-13: Prevents: A corrected recipe that contradicts an unchanged prerequisite or gotcha in the same feature file, which the diff never shows…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:407) *(superseded)*: Owner ruling 2026-11-13: Prevents: A teardown that ends the instance a re-proof still needed. Lands in maintain-verification-skill, SKILL.md, a new skill per t…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:406) *(superseded)*: Owner ruling 2026-11-13: Prevents: A harness fix shipped untested that breaks the next run. Lands in maintain-verification-skill, SKILL.md, a new skill per the…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:405) *(superseded)*: Owner ruling 2026-11-13: Prevents: A missing setup step worked around in one run and left out of the map for the next. Lands in maintain-verification-skill, SK…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:404) *(superseded)*: Owner ruling 2026-11-13: Prevents: A feature skipped as unreachable with nothing to show anyone tried. Lands in maintain-verification-skill, SKILL.md, a new sk…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:403) *(superseded)*: Owner ruling 2026-11-13: Prevents: A pass declared blocked by an outdated doctor step it could have fixed. Lands in maintain-verification-skill, SKILL.md, a ne…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:402) *(superseded)*: Owner ruling 2026-11-13: Prevents: Leftovers from one failed drive that make the next drive fail. Lands in maintain-verification-skill, SKILL.md, a new skill p…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:401) *(superseded)*: Owner ruling 2026-11-13: Prevents: A pass whose cleanup removed the proof it reports. Lands in maintain-verification-skill, SKILL.md, a new skill per the owner…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:400) *(superseded)*: Owner ruling 2026-11-13: Prevents: A failed drive blamed on the product when the instance was already broken. Lands in maintain-verification-skill, SKILL.md, a…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:399) *(superseded)*: Owner ruling 2026-11-13: Prevents: A maintenance pass that launches the product differently from the skill it is checking. Lands in maintain-verification-skill…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:398) *(superseded)*: Owner ruling 2026-11-13: Prevents: Helpers driving one product instance at once and producing proof nobody can trust. Lands in maintain-verification-skill, SKI…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:397) *(superseded)*: Owner ruling 2026-11-13: Prevents: New features never added to the map, so they are never verified. Lands in maintain-verification-skill, SKILL.md, a new skill…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:396) *(superseded)*: Owner ruling 2026-11-13: Prevents: Drift fixed on a reader's word alone, or effort spent re-reading clean features. Lands in maintain-verification-skill, SKILL…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:395) *(superseded)*: Owner ruling 2026-11-13: Prevents: A live pass that relaunches and resets far more than the features need. Lands in maintain-verification-skill, SKILL.md, a ne…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:394) *(superseded)*: Owner ruling 2026-11-13: Prevents: A pass that moves on while some features have no reading. Lands in maintain-verification-skill, SKILL.md, a new skill per th…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:393) *(superseded)*: Owner ruling 2026-11-13: Prevents: Several readers driving one instance at once and corrupting each other's results. Lands in maintain-verification-skill, SKIL…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:392) *(superseded)*: Owner ruling 2026-11-13: Prevents: Reader results in different shapes, with drift claims nobody can check. Lands in maintain-verification-skill, SKILL.md, a ne…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:391) *(superseded)*: Owner ruling 2026-11-13: Prevents: Features judged current from the map alone, with nobody reading the source behind them. Lands in maintain-verification-skill…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:390) *(superseded)*: Owner ruling 2026-11-13: Prevents: An index that lists features that are gone and misses ones that exist. Lands in maintain-verification-skill, SKILL.md, a new…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:389) *(superseded)*: Owner ruling 2026-11-13: Prevents: A maintenance pass that invents a verification skill instead of creating one properly. Lands in maintain-verification-skill,…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:387) *(superseded)*: Owner ruling 2026-11-13: Prevents: A pass that maintains the wrong skill, or none, because it looked for a name. Lands in maintain-verification-skill, SKILL.md…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:386) *(superseded)*: Owner ruling 2026-11-13: Prevents: A feature marked unverifiable when only the harness was missing a step. Lands in maintain-verification-skill, SKILL.md, a ne…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:385) *(superseded)*: Owner ruling 2026-11-13: Prevents: A broken feature hidden by editing the map to describe the broken behaviour. Lands in maintain-verification-skill, SKILL.md,…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:384) *(superseded)*: Owner ruling 2026-11-13: Prevents: A maintenance pass that changes the product to make its own checks pass. Lands in maintain-verification-skill, SKILL.md, a n…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:383) *(superseded)*: Owner ruling 2026-11-13: Prevents: A pass's fixes scattered or mixed with unproven edits. Lands in maintain-verification-skill, SKILL.md, a new skill per the o…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:382) *(superseded)*: Owner ruling 2026-11-13: Prevents: An empty change opened for a clean pass, or a blocked pass reported as clean. Lands in maintain-verification-skill, SKILL.md…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:381) *(superseded)*: Owner ruling 2026-11-13: Prevents: A pass that ends without saying whether the skill can be trusted, or blocked with no cause given. Lands in maintain-verifica…
- `2026-11-13` **adopt** (2026-11-13-batch-p2:380) *(superseded)*: Owner ruling 2026-11-13: Prevents: A verification skill reported current when some features were only read about, never driven. Lands in maintain-verification-…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-12-upstream-cursor_plugins-2776ddd-batch-p2.md](../../reviews/2026-11-12-upstream-cursor_plugins-2776ddd-batch-p2.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `churn-sweep-with-source-path`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#churn-sweep-with-source-path` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `coordinator-only-driving`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#coordinator-only-driving` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `doctor-at-fixed-points`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#doctor-at-fixed-points` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `drift-doctor-fix-retry-once`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#drift-doctor-fix-retry-once` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `every-feature-source-and-live`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#every-feature-source-and-live` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `evidence-checked-after-cleanup`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#evidence-checked-after-cleanup` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `failed-drive-residue-cleanup`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#failed-drive-residue-cleanup` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `final-teardown-after-last-drive`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#final-teardown-after-last-drive` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `harness-fix-redriven`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#harness-fix-redriven` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `harness-gap-fix`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#harness-gap-fix` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `index-hygiene`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#index-hygiene` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `launch-model-from-skill`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#launch-model-from-skill` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `map-drift-or-regression`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#map-drift-or-regression` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `merge-recipes-few-states`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#merge-recipes-few-states` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `missing-result-not-pass`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#missing-result-not-pass` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `no-change-outcome-report`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#no-change-outcome-report` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `no-target-points-to-create`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#no-target-points-to-create` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#no-target-points-to-create` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `omitted-prerequisite-is-drift`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#omitted-prerequisite-is-drift` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `one-change-of-proven-fixes`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#one-pr-of-proven-fixes` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `one-pass-outcome`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#one-pass-outcome` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `reread-changed-files-whole`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#reread-changed-files-whole` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `source-reader-per-sizeable-feature`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#per-feature-source-readers` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `source-reader-return-shape`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#source-reader-return-shape` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `source-readers-never-drive`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#source-readers-never-drive` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `spot-check-cited-drift`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#spot-check-cited-drift` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `target-found-by-content`:
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#target-found-by-content` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#target-found-by-content` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `unreachable-with-route-and-prerequisite`:
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#unreachable-with-route-and-prerequisite` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
- `verification-only-edits`:
  - `cursor_plugins:skill:pstack/skills/create-formal-verification-skill#verification-only-edits` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
  - `cursor_plugins:skill:pstack/skills/maintain-formal-verification-skill#verification-only-edits` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
  - `cursor_plugins:skill:pstack/skills/maintain-verification-skill#verification-only-edits` (adopted at 2776ddd2355d6d6c8747d3964600f28daf62f049)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
