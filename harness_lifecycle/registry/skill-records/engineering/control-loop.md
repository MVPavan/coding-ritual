---
skill: control-loop
domain: engineering
stage: X
substage: Coordination
secondary: [Maintenance]
family: agentic-control-loop
aliases: []
status: active
---
# control-loop

Use when asked to set up a recurring, scheduled loop that drives one measured property of a codebase toward a target (lint findings to zero, an old pattern gone, a threshold met) through one small pull request per run, across sessions. Driving one condition within a session is the autonomous-run playbook, climbing one metric in a session is hillclimb, and building settled beads unattended to pull requests is autopilot-full.

**Boundary:** Designs and builds one recurring, scheduled loop that drives a measured property of a codebase toward a target through one small pull request per run, then dry-runs it; driving one condition within a session is autonomous-run, climbing one metric in a session is hillclimb, building settled beads unattended is autopilot-full, and a loop's pull requests merge through shipping.

<!-- registry:generated traits -->
- `control-loop-vocabulary`: Describe a recurring improvement loop in control terms (set point, sensor, controller, actuator, disturbance, a person on the loop) and explain them to the person before designing it.
- `fused-loop-parts`: Let a loop's parts merge where one tool or agent does two jobs, building no separation the design does not have.
- `loop-charter-bead`: Track a loop as one feature bead that stays open while the loop lives, its description the charter and its notes one line per target done, skipped, failed or reopened.
- `run-task-bead-per-pr`: Give each acting run of a loop a child task bead and one pull request that names it and references the loop's issue without closing it.
- `noted-target-exclusion`: Have a loop's controller pass over a target its notes mark done or skipped, or failed twice, until a later reopened note.
- `one-open-pr-bound`: Bound a loop at one open pull request, found by its branch or label, so a run that finds one open does no work.
- `allowlisted-headless-actuator`: Run a loop's agent non-interactively on the owner's own login with an explicit tool allowlist (read and search tools, edits to the target's paths, named commands), in the permission mode that denies everything else, never one that bypasses its checks, with no settings file or hook loaded.
- `agent-spend-guard`: Cap an unattended agent's turns, and its spend where the agent offers a cap, on every run.
- `gated-script-commit`: Let a loop's run script, not its agent, stage the target's paths by name, run the commit gate and its manual checks, then commit, push the run's new branch and open the pull request.
- `loop-scope-gate`: Keep a loop to the paths it may safely change, leaving out generated, vendored or risky code, and refuse a run whose change reaches outside its target.
- `loop-run-grant`: Read the owner's go on a loop as authority, per run, for the run's task bead and notes, a branch from the base, one gated commit, an ordinary push of that branch and its pull request, and for nothing else: no force-push, no merge, every other network write held.
- `gate-loosening-held`: Hold for the owner any change that loosens a gate, such as a skipped or soft-failed test, a raised budget, an allowlist entry, or a check removed or weakened in the gate's own configuration. (Narrowed to the loop's own gate: clearing a target by silencing the sensor's tool (an ignore entry, a suppression comment, a changed tool configuration) is a loosening; the actuator skips the target and the owner decides (SKILL.md, The grant).)
- `local-first-components`: Make each part of a loop a version-controlled script and run each by hand, on its own and on real input, before any schedule exists.
- `repo-survey-before-interview`: Before asking the person design questions, read the repository's build files, validation commands, CI, existing automation and analysis tools, so each question comes with proposals grounded in what is there.
- `component-design-interview`: Design each part of an automation with the person one at a time, offering the options the repository supports with their trade-offs, recommending one and recording the answer, never mandating a choice.
- `set-point-and-scope`: Fix a loop's target as an invariant, a threshold or a direction, and pin the paths it may change and those it may only read.
- `sensor-tradeoff-choice`: Choose a loop's measurement from tooling the repository already has, weighing its stability, cost, repeatability and whether it can be switched off unnoticed.
- `reviewable-increment-controller`: Have a loop's controller choose the next increment from the measurement, ordered and capped so each run's change stays small enough to review.
- `golden-patterns-first`: Before automating a change, find in the code what a good instance of it looks like, confirm with the person which patterns to follow, and write them into the automation's instructions.
- `agreed-validation-commands`: Agree with the person, from what the repository already runs, the validation commands an automated change must pass before it is committed.
- `loop-dampener-offer`: Offer, as optional, a check that compares a loop's measurement on other changes with a baseline, so the measured problem cannot grow while the loop shrinks it.
- `cadence-by-risk`: Set a recurring job's cadence by its change's risk and the reviewer's capacity.
- `written-design-before-build`: Write the agreed design of an automation down before building it, so the person can correct it cheaply.
- `one-home-per-loop-rule`: Keep each rule of a loop in exactly one of its files (the agent's instructions, the steering file, the selection code or the run script), never repeated across them.
- `loop-actuator-instructions`: Write a loop agent's judgement (golden pattern, permitted commands, outcomes, body form) as one plain instructions file in the loop's folder that the run puts first in the prompt.
- `no-questions-unattended`: Tell an agent in an unattended run that nobody answers, so it finishes within its rules or stops the target with a reason instead of asking.
- `fix-or-skip-outcome`: Give each loop target two outcomes, fixed or skipped with a reason for the person, never cleared by silencing the measuring tool.
- `pr-body-response-template`: Give an automated change's agent a fixed form for its report that becomes the pull request body: what changed and how much, the risk, and how a reviewer can check a riskier change by hand.
- `steering-file-after-controller`: Keep a version-controlled file of the person's standing guidance for a loop (exclusions, false positives, review lessons, never one-off instructions or logs) and give it to the loop's agent after the selection on every run.
- `assembled-actuator-prompt`: Build each run's agent prompt in a fixed order: the standing instructions, then the work selected for this run, then the steering file.
- `loop-config-validation`: Before a loop runs, check that its run definition parses and that every path it names exists.
- `overlapping-run-skips`: Hold a lock for each run of a recurring job, so a run started while another holds it exits at once, changing nothing.
- `set-point-reached-stop`: End a loop's run with a note, changing nothing, when its measurement shows the target reached, its pinned configuration changed, or every remaining target excluded.
- `final-message-extraction`: Take an unattended agent's final message from its output as text for the pull request body, failing over when it is missing.
- `no-change-no-pr`: Open no pull request from a run whose agent produced no change.
- `agent-output-kept`: Keep an unattended agent's raw output with its run, so a failed run can be read afterwards.
- `one-real-dry-run`: Prove a loop before any schedule with one supervised run on real output that opens one real pull request for the person to review.
- `local-timer-on-request`: Schedule a loop only when the person asks, as a user timer or cron entry on their own machine at their cadence, leaving a CI runner as a later option.
- `tune-controller-from-output`: Start a loop's selection simple and revise it from the loop's output and the reviewer's corrections.
- `scale-up-once-tuned`: Raise a tuned loop's throughput (a more frequent cadence, a larger increment, more cycles per run) once its output is consistent.
- `completion-criteria-clarity`: End each step on an observable, checkable done-or-not-done criterion that resists premature completion. (Each step of Build a loop ends on a Done when line.)
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#control-loop-vocabulary** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#repo-survey-before-interview** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#component-design-interview** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#set-point-and-scope** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#sensor-tradeoff-choice** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#reviewable-increment-controller** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#tune-controller-from-output** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#fused-loop-parts** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#headless-agent-choice** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#golden-patterns-first** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#agreed-validation-commands** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#loop-dampener-offer** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#written-design-before-build** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#repo-local-actuator-skill** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#one-home-per-loop-rule** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#pr-body-response-template** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#fix-ignore-skip-outcomes** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#local-first-components** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#scheduled-ci-workflow** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#cadence-by-risk** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#assembled-actuator-prompt** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#no-questions-unattended** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#steering-file-after-controller** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#one-open-pr-bound** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#loop-config-validation** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#push-trigger-dry-run** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#scale-up-once-tuned** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#agent-spend-guard** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#final-message-extraction** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#no-change-no-pr** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#loop-scope-gate** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#cancel-overlapping-runs** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#completion-criteria-clarity** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#agent-output-kept** `plugins/design-control-loop/skills/design-control-loop/SKILL.md` @ 3c2629142c5d437428269b1b722b08c0b87f574d
- **humanlayer_skills:plugin:plugins/design-control-loop/design-control-loop** `plugins/design-control-loop/.claude-plugin/plugin.json` @ 3c2629142c5d437428269b1b722b08c0b87f574d
  - merged from: reference_harnesses/humanlayer_skills/plugins/design-control-loop/.claude-plugin/plugin.json (a manifest wrapping the one skill)
  - modified: The skill it wraps is adopted, adapted, as control-loop (this round's checkpoint).
  - dropped: The plugin manifest: our skill ships with the harness, not as its own plugin.
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-24` **adopt-merged** (2026-11-24-control-loop:045): Owner ruling 2026-11-22 (rejections re-review, bead cr-r2pa.3.3): the single-skill plugin wrapper of design-control-loop follows that skill's ruling, and the s…
- `2026-11-24` **adopt-merged** (2026-11-24-control-loop:044): Checkpoint at 3c26291 after this round's trait rulings (41 traits: 34 adopt, 6 of them modified, and 7 reject), owner rulings 2026-11-22 (rejections re-review,…
- `2026-11-24` **adopt** (2026-11-24-control-loop:043): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:042): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:038): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted,…
- `2026-11-24` **adopt** (2026-11-24-control-loop:037): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:036): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:035): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:034): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:031): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:030): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted,…
- `2026-11-24` **adopt** (2026-11-24-control-loop:029): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:027): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:025): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:024): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:023): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:022): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:021): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted,…
- `2026-11-24` **adopt** (2026-11-24-control-loop:020): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:019): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted,…
- `2026-11-24` **adopt** (2026-11-24-control-loop:018): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:017): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:016): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted,…
- `2026-11-24` **adopt** (2026-11-24-control-loop:015): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:014): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:013): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:012): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:011): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted,…
- `2026-11-24` **adopt** (2026-11-24-control-loop:010): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:009): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:008): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:007): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:006): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:005): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:004): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **adopt** (2026-11-24-control-loop:003): Owner rulings 2026-11-22 (rejections re-review, bead cr-r2pa.3.3) and 2026-11-24 (answers 1a, 2a and 3a on the control-loop proposal), bead cr-p3em.6. Adopted …
- `2026-11-24` **add** (2026-11-24-control-loop:001): New model-invocable skill, owner rulings of 2026-11-22 (2026-11-22-rejects-review:059: design-control-loop adopted, adapted, as this skill) and 2026-11-24 (ans…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `agent-output-kept`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#agent-output-kept` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `agent-spend-guard`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#agent-spend-guard` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `agreed-validation-commands`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#agreed-validation-commands` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `allowlisted-headless-actuator`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#headless-agent-choice` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `assembled-actuator-prompt`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#assembled-actuator-prompt` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `cadence-by-risk`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#cadence-by-risk` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `completion-criteria-clarity`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#completion-criteria-clarity` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `component-design-interview`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#component-design-interview` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `control-loop-vocabulary`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#control-loop-vocabulary` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `final-message-extraction`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#final-message-extraction` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `fix-or-skip-outcome`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#fix-ignore-skip-outcomes` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `fused-loop-parts`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#fused-loop-parts` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `golden-patterns-first`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#golden-patterns-first` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `local-first-components`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#local-first-components` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `local-timer-on-request`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#scheduled-ci-workflow` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `loop-actuator-instructions`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#repo-local-actuator-skill` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `loop-config-validation`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#loop-config-validation` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `loop-dampener-offer`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#loop-dampener-offer` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `loop-scope-gate`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#loop-scope-gate` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `no-change-no-pr`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#no-change-no-pr` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `no-questions-unattended`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#no-questions-unattended` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `one-home-per-loop-rule`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#one-home-per-loop-rule` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `one-open-pr-bound`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#one-open-pr-bound` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `one-real-dry-run`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#push-trigger-dry-run` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `overlapping-run-skips`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#cancel-overlapping-runs` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `pr-body-response-template`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#pr-body-response-template` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `repo-survey-before-interview`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#repo-survey-before-interview` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `reviewable-increment-controller`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#reviewable-increment-controller` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `scale-up-once-tuned`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#scale-up-once-tuned` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `sensor-tradeoff-choice`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#sensor-tradeoff-choice` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `set-point-and-scope`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#set-point-and-scope` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `steering-file-after-controller`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#steering-file-after-controller` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `tune-controller-from-output`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#tune-controller-from-output` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
- `written-design-before-build`:
  - `humanlayer_skills:skill:plugins/design-control-loop/skills/design-control-loop#written-design-before-build` (adopted at 3c2629142c5d437428269b1b722b08c0b87f574d)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
