---
name: interrogate
description: "Use when asked to break, attack or tear apart a change or design, or when a playbook names it: adversaries attack it and only findings a run proves survive. An ordinary or critical look is `review`; questioning the author is `grilling`; finding the cause of a known failure is `systematic-debugging`."
---

# Interrogate

Run this when someone asks to have a change or design broken, or a calling playbook names
this skill; never because a review seems important. Adversaries try to break the work; a
general assessment is a critic review. Deliverable: the report under Output. Report only,
no fixes.

**Scope and intent.** The scope is what the request names; failing that, an obvious
supplied base or the working tree, and ask only when the choice changes what gets attacked.
State the intent in your own words before dispatching anyone. Take it from the request,
brief, spec or bead, never from the diff, which shows what changed, not what was meant.
Intent unclear and someone can answer: ask. No source and nobody to ask: not run.

**Adversaries.** Dispatch each through `delegation`, which owns model checks and the family
rule, on the critic contract. One adversary per model the user names or the roster holds
for `critic` and `reviewer`. With one model, two by default, each attacking something
different: inputs, states and failure paths; the intent against the real code, callers and
assumptions. Each gets the scope and the intent and is told to break the work and prove each
finding by a run. A named objection goes to every adversary first. An adversary produces
nothing: go on and report it. Never run an adversary yourself if you wrote the work or, in a
playbook, settled the design: not run is the honest result. No model and nobody to ask, or a
same-family model declined with none left: not run. A delegate whose brief forbids
delegating reports this work as owed to its parent.

**Copies.** Adversaries never touch the shared checkout, so every run sees the same bytes:
1. Make one pristine copy, attacked by nobody: `scripts/make-copy.sh <checkout> <pristine>`.
2. Make each adversary and replay copy from it, outside the checkout:
   `scripts/make-copy.sh --expect <pristine>.state <pristine> <copy>`.
3. Add this to each brief: "Your own disposable copy is at <path>. Write and run only
   there; the shared checkout stays untouched; your report and repro material stay in your
   copy." A vendor sandbox that blocks those writes takes its writer setting pointed there
   through `delegation`, or that adversary does not run.

Commands stay in the copy: no network writes, publishing or real credentials. The scope's
base stays the review range and must be an ancestor of `HEAD` to be in the copy. The script
refuses an unmerged index; intent-to-add entries; a merge, rebase, cherry-pick, revert or
bisect in progress; sparse checkout; skip-worktree or assume-unchanged paths; a line-ending
or content filter, or `core.fileMode=false`, that leaves raw files different; a nested
repository, even an empty one; a moved submodule pointer; a source that changes during the
copy; a destination that exists or sits inside the checkout. A refusal means no copy, so
not run for that adversary, with the reason. Ignored paths and submodule contents are not
copied: the brief names any such setup, or the claim counts as no run possible.

**Checking the checkout.** After each adversary returns, run
`scripts/checkout-changes.sh <pristine>.state`, which names each changed path. Where a vendor
has no sandbox, such as T3, this check and the brief are the only protection: it detects and
nothing prevents. A change is reported, never voids a run, and nothing is restored: list the
paths and say the check cannot tell who changed them. A changed path in scope means the
proof covers the snapshot only; say so, and the caller reruns to land the new state. Exit 2
means it could not check: say that. It covers what Git tracks and untracked files not
ignored, so it cannot see ignored paths or an edit inside a submodule.

**What counts.** A run is a command executed in this review against the real code, a probe
of the current tree, or a throwaway prototype of the design. Not a run: reading code,
reasoning about it, a test written but not executed, a mock of the thing in question, or
another adversary's output. No run, no finding: such a claim gets no severity, never affects
the verdict, and goes in Dropped. Nothing to run yet: try a probe or the smallest prototype;
if neither reaches the claim, say what would be needed. No adversary managed any run: not
run, never "no verified findings". That phrase is valid only when runs happened.

**Replay.** Each finding gives its title, full setup (repro text, data, state, environment,
any timing bound), exact command, printed output and the output the intent requires. You
replay it with that setup in a fresh copy; an adversary never certifies itself.
- Reproduced, with output that breaks the stated intent: a verified finding. Findings with
  one root cause become one. Keep every verified finding from any adversary.
- Not reproduced with its setup replayed: Dropped, stated as unreproduced, not disproved.
- Cannot be replayed: listed as such, no severity.

**Verdict.** Severity follows consequence: BLOCKER, MAJOR, MINOR. Unresolved means an
observed failure unreproduced or unreplayable, and it outranks a favourable verdict.
BLOCKER or MAJOR reproduced: `REVISE`, unresolved listed. MINOR only: `APPROVE`, listed.
MINOR with unresolved, or unresolved alone: no verdict, "unresolved". Nothing reproduced or
unresolved: `APPROVE`, covering only what was attacked. Not run: no verdict, reason given.

**Output.** Intent first; Attacked (scope, adversaries with models and angles, what ran);
Findings (setup, command, output, how it breaks the intent, who found it, severity);
Objection (quoted, who raised it; tested and passed, not tested, or failed and unresolved);
Dropped (per adversary, each claim's title and why); Could not replay; Checkout check;
Verdict; Limits. Remove the copies once the caller has ruled.
