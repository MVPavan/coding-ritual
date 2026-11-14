---
name: maintain-verification-skill
description: "Use for /maintain-verification-skill when a project's verify skill that drives its real app may have drifted from the product; with no verify skill, /create-verification-skill makes one, and proving one change uses the verify skill itself. Reads every mapped feature from source, drives each one live, fixes proven drift in the skill and its map, and ends clean, changed or blocked."
disable-model-invocation: true
argument-hint: "Optional: the verify skill to maintain (default: the one found by its content)"
---

# Maintain Verification Skill

One pass keeps a project's verify skill and its feature map true to the product
as it is now. The unit of work is the feature: each one is read from source and
driven live, without proving every sentence of its file. The generator's two
references, `create-verification-skill/references/generated-skill.md` and
`create-verification-skill/references/feature-map.md`, define the skill's shape
and its map's rules; open the named section at the step that needs it.

**Scope.** Edit only the target skill's own folder: its `SKILL.md`, its
`features/` and the helpers it ships. Product code changes only when the person
asks. A fix keeps the target's fixed sections (Launch, Doctor, Drive, Evidence,
Cleanup, Helpers, Use rules); removing one is out of scope.

## Outcomes

Every pass ends in exactly one, stated in the reply:

- **clean:** every feature was covered from source and live, and nothing proven
  needs fixing. A feature with one driven case is covered; its unreachable cases
  are reported, not blocking.
- **changed:** one set of proven fixes to the skill, its helpers or its map.
- **blocked:** some feature went uncovered, or a proven fix was not safe to
  ship; say exactly what stopped it and the next action that would unblock it.

## 1. Locate the target

Use the skill the person named. Otherwise search every skills folder the
project's hosts read (Claude Code: `.claude/skills/`) for the shape in
generated-skill "How other units recognise it": a `SKILL.md` with Launch, Doctor,
Drive, Evidence and Cleanup sections beside a `features/README.md` index. A
folder name such as `verify-*` is a hint, never the test. Several matches: ask
which one.

- **None found:** stop and point to `/create-verification-skill`; never write a
  verify skill here.
- **Drive sections but no feature-map index:** stop **blocked**: "`<path>` has
  drive sections but no feature-map index; it is not a maintainable verify
  skill, and generating one would write into its folder." The person decides
  that folder's fate before any generation.

## 2. Index

Read `features/README.md` and list the files in `features/`. Fix by hand every
index line with no file, file with no line, duplicate line and line pointing at
a removed feature. Build no generated inventory.

## 3. Source

Every feature file gets a source result: a summary, its source entry points,
likely drift cited as `path:line` (or "none") and one live recipe. A sizeable,
independent feature (several modules, its own parser or migrations) gets its own
read-only helper through `delegation`, briefed by `references/source-reader.md`;
read a small one yourself. Helpers never launch or drive the product and never
edit a file. When no read-only helper can be started, or a delegated pass's
brief gives no authority to delegate, read every feature yourself and say so in
the reply. A feature with no result is a coverage gap, never a pass.

## 4. Reconcile

- Read every cited drift line yourself. Do not re-prove a feature a result
  reported clean.
- Merge overlapping recipes, then order them so one launched state serves as
  many drives as practical: read-only cases before the cases that change state.
- Sweep the commits since the revision the skill last recorded (its last proof,
  or else the last commit touching its folder; say which), or a stated window
  when it records none, for user-facing surfaces the map lacks. A last proof
  named by run ID gives its revision from that run's kept record when it still
  exists. Report one as missing only with the source path that shows it.
- Check the skill against both references as they are now. Each gap is a
  follow-up, fixed only when a drive proves it; missing Isolation blocks.

## 5. Live

Required for every feature at least once, even when its source looked clean.
Only you, the coordinator, drive the product; helpers never do.

- **Launch model.** The target's Launch section decides: a single instance kept
  running and driven one step at a time, or a new isolated session for each drive.
- **Through the helper.** Every product command goes through the target's own
  control helper. When the product uses a live service and the target lacks the
  controls of generated-skill Isolation (clean environment, refused env file,
  endpoint proved before the first write, listed commands only), do not drive:
  **blocked**, naming the missing control.
- **Doctor** before the first drive, on each fresh session and after any failed
  drive, one that confirms drift included, before the next drive. Where the
  doctor cannot see the fault (a stuck screen on a live process), return the
  product to a known starting state, or launch it again.
- **Failed drive:** one whose exit, output or state differs from its feature
  file, or that errored. Clean up what it left, whether its session hung, ended
  or is shared; on a shared instance take only this pass's residue, never the
  instance. Only its residue check (a state delta) may precede the doctor.
- **Doctor fails from drift** in the skill: fix it within Scope, restart only
  what the fix invalidated, retry once, then **blocked**. The fix restores what
  source shows the product is now; it never drops or loosens a check such as an
  identity, port or revision check.
- **Offline modes.** Each drive re-observes what the skill records an offline or
  dry-run mode skipping (generated-skill Evidence); failing that, no proof.
- **Unreachable** only with the route tried and the missing prerequisite
  (feature-map Skip reporting).
- **Not yet driven** (feature-map Layout): a feature's index line keeps the mark
  while any case is undriven; its file names each with route and prerequisite.
  Driving one writes its observed results into the file and unlists it.
- **No read view.** For each saved change, name the product command that shows
  the saved item itself (feature-map Proof by surface). A view of counts or a
  fingerprint, or the helper's own query, is not one, whatever the feature file
  calls it. With none, the feature file says so and the report lists the change
  unverified, never clean; that alone does not block a changed or blocked
  outcome. Keep such an observation as a file under the run's evidence, labelled
  a helper observation, never as the readback; when the helper only prints it,
  saving it is a harness gap: fix and re-drive, or report it.
- **Credentials.** Never print, log or keep one, generated ones included: none
  in evidence, notes, the reply or a helper diff. Output that can hold one is
  parsed inside the helper and never saved (generated-skill Evidence).
- **Missing tool.** Install one only by the recipe the target records, project
  local or per user and pinned, never system-wide; with no recipe, mark the work
  that needs it blocked and name the tool.

## 6. Triage

Classify each gap between map and product:

- **Doc drift:** the map describes the product wrongly or incompletely. Fix the
  feature file by feature-map Feature file template and Coverage, keeping every
  source citation the fix does not disprove.
- **Omitted prerequisite:** an unreachable feature needed something the map
  never mentions. That is drift: add it where its file lists preconditions
  (Gotchas, Baseline or elsewhere).
- **Harness gap:** working behaviour the helper cannot drive. Fix the helper by
  generated-skill Helpers (executable, invoked in the skill body), then check
  its Isolation, Doctor, Cleanup and Evidence credential rule still hold.
- **Product regression:** the product no longer does what it should. Report it
  outside the change; never write it into the map as expected behaviour.

Fix a failing journey only when source proves the map wrong; never loosen the
journey, its check or its expected value to make it pass. Re-drive every harness
fix live before it ships, including the launch or seed steps that use the
changed helper code.

## 7. Teardown

After every cleanup, confirm each evidence file is at the location the skill
names; a missing one fails that step. Final teardown waits until the pass's last
drive, re-drives of fixes included, and leaves the evidence in place.

## 8. Ship or stop

- **Clean:** change nothing; report the outcome and per-feature coverage.
- **Blocked:** open and ship no change and roll nothing back; report the
  coverage and each edit already made: what it changed, whether it was verified
  and the action that resumes the pass. Never hand it to `land` as verified.
- **Changed:** read every changed file whole, not only its diff, then leave the
  one set of proven doc, helper and map fixes uncommitted for `land`. Open no
  branch, commit or pull request unless the person asks for one.

## Reply

- **Outcome:** clean, changed or blocked, and for blocked what stopped it.
- **Target:** the skill's path and how it was found.
- **Coverage:** each feature, source result and live result; unreachable ones
  with route and prerequisite; unverified changes and self-read features named.
- **Changes:** each fix, its class (drift, prerequisite, harness) and the proof
  that drove it; product regressions and contract gaps reported separately.
- **Window:** the churn sweep's revision range and which reference it used.
