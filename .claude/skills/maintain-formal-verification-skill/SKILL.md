---
name: maintain-formal-verification-skill
description: "Use for /maintain-formal-verification-skill when a project's formal verify skill may no longer describe its code after changes made without it; with none, /create-formal-verification-skill makes one, and checking your own change uses the verify skill itself. Sorts every change to covered code since the sync commit, updates the model from the code, reruns, and gives each check one outcome: in sync, updated, bug or blocked."
disable-model-invocation: true
argument-hint: "Optional: the formal verify skill to maintain (default: the one found by its coverage record)"
---

# Maintain Formal Verification Skill

Each formal check speaks only for the model it keeps: once the code moves on
without it, a passing run still reads as proof of code that is gone. One pass
brings a project's formal verify skill back to its code after changes that
skipped its "Updating for an intended change" (merges, unreviewed edits, drift
over many commits). The person starts this pass; never an agent on its own
initiative. The skill's shape belongs to create-formal-verification-skill,
whose `create-formal-verification-skill/references/` files are read at the
step that names them and restated nowhere here.

**Scope.** Edit only the target skill's own folder: its model or other kept
artifacts, their configurations, `coverage.json`, `SKILL.md` and `scripts/`.
Product code changes only when the person asks, even to fix a bug this pass
finds. Never loosen a property, the model or its bounds so that a run passes;
a failure on the current code is a finding. A fix keeps the sections
`formal-verify-skill.md` "Sections" lists.

## Outcomes

Each check ends with one outcome, named in the reply:

- **in sync:** nothing since the sync commit makes the model untrue, and the
  check gives its expected verdicts.
- **updated:** the model now describes the code again, with expected verdicts.
- **bug:** the model matches the code as it stands, and the property fails on
  it: a finding about the code, never drift.
- **blocked:** the check failed to run or to be brought back in line; give the
  reason and the action that would unblock it.

A faithful update followed by a failing property is **updated and bug**.

## 1. Take stock

Use the skill the person named. Otherwise search every skills folder the
project's hosts read (Claude Code: `.claude/skills/`) by content, as
`formal-verify-skill.md` "How other units recognise it" describes; a folder
name such as `<area>-verification/` is a hint, never the test. Several
matches: ask which one. **None found: stop** and point to
`/create-formal-verification-skill`, writing no skill here; a verify skill
that drives the real app goes to `/maintain-verification-skill`.

Record the checkout's status before any edit (`git status --porcelain
--untracked-files=all`, `git diff`, a sha256 list of the target's files), so
the person's own edits stay apart from this pass's.

For each check, write down its property, its `covers` entries, its bounds and
assumptions, its `run` command and its `sync_commit`, from `coverage.json`
(`coverage-record.md` "Format"). With no recorded sync commit, take the last
commit that touched the skill's folder (`git log -1 --format=%H -- <folder>`)
and say in the reply that it was inferred. For a skill without `coverage.json`,
gather the same record from its text and write that file at step 6 by
`coverage-record.md`: per check, the guarded files and symbols and the last
confirmed commit, kept as data beside `SKILL.md`, never as prose.

Compare the skill with `formal-verify-skill.md` as it is now: its sections,
`scripts/check.py` steps 1-6 and the install recipe its Run section names.
Each gap is a follow-up in the reply, none fixed here: a runner change is a
regeneration, and each check's outcome stays about the code. The one
exception is writing `coverage.json` for a skill that lacks it.

## 2. Baseline

Run the skill's command once before any edit, exactly as its Run section
writes it, and keep the output and exit code as this pass's baseline. A
baseline pass shows only that the model as last synced still passes, nothing
about today's code. A baseline failure stays unclassified: drift or bug is
decided at step 5, after the update.

A missing tool is installed only by the per-user recipe and pins the skill
records, after the person approves, never system-wide, as root or through a
shell-profile change. Without approval or a recorded recipe, the check is
**blocked**, naming what is missing.

## 3. Sweep and sort

List every commit from the sync commit to `HEAD` that touches a covered path
(`git log -M --format='%H %s' <sync_commit>..HEAD -- <covered paths>`) and
read each one's message and diff (`git show -M <hash> -- <covered paths>`).
Moved code is still covered: search the range's whole diff (`git diff -M
<sync_commit> HEAD`) for each covered symbol, following a rename, split or
move to another file, and for new code that writes the state the model's
variables trace to. Covered edits not yet committed are reported, never
synced: a sync commit is a commit.

Sort each change into one class:

- **No effect:** nothing the model describes is touched (formatting,
  comments, a path the model does not cover).
- **Verification out of date:** the promise kept in a new shape: one
  indivisible step became two, a check or branch appeared, went or moved, a
  new route leads into the guarded state, a value's range changed. The model
  must change.
- **Promise changed on purpose:** the code now promises something else, and
  the change says so. The property must change.
- **Promise maybe broken:** the code changed and nothing in the change says
  the promise did. A failure after the update is a bug candidate.

Judge no effect against the model: the traceability table and the actions
whose code the change touches, never the commit message. A promise counts as
changed on purpose only with evidence cited from the change itself: the
commit message, a changelog entry, a doc comment or a test.

## 4. Update

Write each update from the code before the rerun, never from what would make
the run pass. Apply `create-formal-verification-skill/references/model-fidelity.md`
to every edit: its "Traceability table" and "Indivisible steps", with each
citation at the commit being checked.

Edit a property only when its promise changed on purpose: give its old and
new wording and the evidence in the reply, and update `property` and `harm`
in `coverage.json` with it. Keep the bounds unless a change invalidates them,
such as a new writer the model must hold; report any cut. A slower run is
reported, never cut back to its old time.

## 5. Rerun and judge

Judge each rerun by its exit code and the checker's own messages together, by
`tool-branches.md` (for TLC, its gate); either alone is no verdict.

- **Main run holds.** Every kept broken variant must still break its
  `must_break` property through the mechanism its guard exists for
  (`model-fidelity.md` "Broken variants"). A guard the update added or moved
  that no kept variant removes gets a new kept variant in the branch's form,
  listed in `coverage.json`: a switch in the model, never a product edit.
- **Main run fails.** Replay the counterexample on the code first, step by
  step through the real functions, by reading or with a scratch test,
  including every step a writer runs between the model's last modelled check
  and its commit (a version or citation re-check, say). A step the code
  forbids is a modelling error until shown otherwise: fix the model from the
  code, say what was wrong, and rerun. For a TLA+ model, the `statechart`
  skill gives the failing path in readable steps; name it, copy none of its
  commands. A variant's verdict means nothing while the main run fails; it is
  accepted again only from a run whose main run holds.

When the code allows every step, it is a bug: lead with a path that needs no
extra ordering, or say what ordering the path given needs. To find where it
began, replay it first on the code at the starting sync commit. If it
reproduces there, keep the introducing commit an earlier pass reported, or
trace it in older history; when neither shows it, the commit is unknown, and
a harmless commit in the window is never blamed. Only when it does not
reproduce there, search the window for the first commit after which it does.
A confirmed bug gets the commit that introduced it (or unknown, said so), its
counterexample as a few numbered steps in the code's own terms (function,
row, lock) and its harm in one sentence. Keep a cheap reproduction: a scratch
model configuration (fewer writers, a smaller bound) or a scratch test needing
no service, kept in the run's notes, never in product code or the skill, and
given or linked with its result in the reply.

## 6. Refresh the record

Refresh `coverage.json` and every mention in the skill to the commit checked:
`covers` (renamed and moved symbols included), `run`, `bounds`,
`assumptions`, `broken_variants`, the traceability table, the model's line
comments, the Run section's expected output and measured time, and each
mention of the sync commit.

`sync_commit` moves to the checked commit once the covered diff is read, the
model updated from it and the rerun gives its expected verdicts
(`coverage-record.md` "Rules"). On a confirmed bug it moves too, with the
faithful update, so the skill describes the code it checks and fails there
until a fix or an evidenced promise change. A blocked check keeps its sync
commit and the rest of its record; say so in the reply.

Then follow the refreshed skill once as its next reader would: its drift
diff, its Run command exactly as written, its exit code. Every command the
refresh changed or added runs as written before hand-over; a refreshed skill
nobody has followed is a draft.

## 7. Hand over

Leave the verification edits as one change, apart from any product fix,
which happens only when the person asks, and uncommitted for `land`: no
branch, commit or pull request unless the person asks.

## Reply

Per check:

- **Outcome**, and for blocked its reason and its sync commit left in place.
- **Commits read:** the window, each commit's class, an inferred sync commit
  said as such, covered edits left uncommitted.
- **Changes:** each verification edit and its reason (a new shape in the code,
  or a changed promise with its evidence and both wordings), any bound cut.
- **Rerun:** the verdicts and the variant that shows the check can still
  fail, or that the variant verdicts wait for a main run that holds.
- **Bugs:** commit (or unknown, and why), steps in the code's terms, harm,
  and the reproduction inline or linked with its result.
- **Gaps:** what the check still leaves out, new code it should cover, each
  contract gap as a follow-up.

Name drift and bugs apart: which failures were the verification out of date
and which were the code. A check that passed at baseline and fails after its
update: say the old pass was against a stale description.
