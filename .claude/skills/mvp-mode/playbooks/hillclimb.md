---
trigger: Sustained, attended improvement of one measurable metric against a stop predicate, with no settled plan to execute.
traits: [attended-only-gate, one-change-one-measurement]   # new
steps:
  - id: hillclimb#1
    when: always
    actions: [{trait: repro-before-climb}, {trait: stop-predicate-with-floor}]   # new
    calls: [{to: "skill:explain-code"}, {to: "skill:performance-optimization", when: this one whole call stays open through hillclimb#5; the predicate is its stop condition}]
  - id: hillclimb#2
    when: hillclimb#1 fixed the metric and predicate
    actions: [{trait: attempt-isolation-gate}, {trait: sensitivity-proof-then-freeze}, {trait: gate-green-baseline}]   # new; the last a variant of baseline-check-before-change
    calls: [{to: "skill:build-a-lever", when: no existing command emits the metric}]
    loads: [{path: hillclimb/attempt.py}]
  - id: hillclimb#3
    when: the harness is frozen
    calls: [{to: "skill:decision-trail", when: "extra columns before, after, delta, tests; this one whole call stays open through hillclimb#7"}]
  - id: hillclimb#4
    when: once per attempt, entered from hillclimb#3, hillclimb#5 or hillclimb#6
    actions: [{trait: read-trail-first}, {trait: keep-or-undo-rule}, {trait: attempt-snapshot-undo}]   # new; the last a variant of revert-ineffective-experiments
    calls: [{to: "skill:delegation", when: the router's delegation rule sends the attempt to a subagent; one factor per brief; told not to stage}]
  - id: hillclimb#5
    when: after each attempt; predicate met, or no cheap untried idea left, goes to hillclimb#7; several rejects in a row go to hillclimb#6; anything else returns to hillclimb#4
    actions: [{trait: predicate-held-stop}]   # new
  - id: hillclimb#6
    when: hillclimb#5 found several rejects in a row with the predicate unmet; returns to hillclimb#4
    actions: [{trait: plateau-pivot}]   # new
  - id: hillclimb#7
    when: every exit
    actions: [{trait: climb-closeout}]   # new; variant of build-closeout
  - id: hillclimb#8
    when: finished with one or more attempts kept and in the working tree, after hillclimb#7
    calls: [{to: "skill:land"}]
---

# Hillclimb

For sustained improvement of one measurable metric from one repeatable command against
a stop predicate, with someone attending and no settled plan. One fix is the perf-issue
playbook, a plan to run is `execution`, and a variant judged on fresh sessions is the
eval playbook.

**The gates:** attended only. A request to run unattended (overnight, while away,
self-waking) does not start: say unattended climbs wait on the wake work and offer an
attended run. This run sets no wake or schedule and goes on only while the conversation
does. One change, one measurement, then keep or undo: never stack untested changes. The
loop commits nothing, with or without commit authority.

1. **Ground.** Invoke `explain-code` on the target. Name the workload dimensions that can
   move the result and pick a case that reproduces the complaint. When none does, repair
   the case here, at most two tries, then stop with what was tried. Invoke
   `performance-optimization`; this one whole call stays open through step 5, its steps
   1-3 run across steps 1 and 2, and its steps 4 and 5 run in step 4. Settle one metric,
   which way is better, and a stop predicate: a target plus a floor on how many attempts
   run, in the user's numbers or agreed. The predicate is the skill's stop condition.
2. **Harness.** First name one artifact directory outside every worktree this climb will
   remove. Patches, the harness and measured artifacts all live there; in a snapshotted tree
   they would break undo, closeout's verify or the worktree's removal. The harness runs with
   the tree under test as its working directory. Then isolate. When a path you will change
   holds someone else's edits, or another agent or person may write anywhere in this tree
   during the climb, the whole climb runs in one detached worktree at an ignored path or
   outside the tree: a snapshot covers the whole tree, so it needs one writer across it.
   Before any baseline: run `attempt.py snapshot` here, which
   prints the tree and the index tree; `git worktree add --detach <path> HEAD`; write
   `attempt.py patch 'HEAD^{tree}' <start> <s.patch>`; then, in the worktree, `attempt.py
   replay <s.patch> <start> <index>`, with the index tree its own `snapshot` prints.
   `hillclimb/attempt.py`, beside this file, refuses a sparse tree, files whose bytes Git
   converts and a patch changing a `.gitattributes`; a refusal is a stop. A harness rebuilds
   and never trusts ignored build output. When no existing command emits the metric, invoke
   `build-a-lever`. Show that contrasting workloads separate as expected, vet the harness as
   the skill's vetting branch says, then freeze it: one command, no further change. Record
   the baseline and show the regression gate green; a red gate stops here.
3. **Open the trail.** Invoke `decision-trail` with extra columns `before, after, delta,
   tests`. This one whole call stays open through step 7. Name a trail path in the artifact
   directory, or anywhere else closeout will not remove and no snapshot sees. Each row's decision is the change, why
   the hypothesis, evidence the patch, and result `kept`, `kept, simplification` or `undone`.
4. **Attempt.** Read the trail first and retry nothing it already rejected. Choose one
   change by the skill's step 4. By the router's delegation rule, hand it over through
   `delegation`, one factor per brief, told not to stage. Around the edit: `attempt.py
   snapshot`, edit, `snapshot` again, `attempt.py patch <start> <end> <a.patch>`. List its paths
   with `git apply --numstat <a.patch>`: a path you did not mean to change is a stop, before
   keeping or undoing, since another's edit between the two snapshots looks like part of the
   attempt. Measure with the frozen command and run the gate. `principle-subtract-before-you-add` applies, and
   `principle-sequence-verifiable-units` applies between attempts. Keep a win: the metric
   moved past noise with the gate green. Also keep a demonstrated simplification
   when the metric does not materially worsen and correctness holds, logged as `kept,
   simplification`, never as a speedup. Otherwise undo in full; a win that breaks behaviour
   fails the gate. Only `attempt.py undo <a.patch> <start> <index>` undoes. It proves the
   result first and refuses with nothing changed, then reverses and verifies. A failure during
   the real reverse (an ignored file blocking a directory, a write error) may leave part of it
   applied and exits 1. Either exit is a stop, and the tree stays untouched from then on. Log
   the row either way.
5. **Hold the predicate.** After each attempt: predicate met, or no cheap untried idea
   left, goes to step 7; several rejects in a row go to step 6; anything else returns to
   step 4. Never relax the predicate, never quit while a cheap untried hypothesis remains,
   and when stuck say so rather than spin. Close the skill's attempt record and any
   regression guard before its call ends.
6. **Pivot.** With several rejects in a row and the predicate unmet: change category,
   combine near-misses and reread the source before concluding. Then return to step 4.
7. **Close out**, on every exit. After a non-zero exit from `attempt.py`, or a path you
   did not mean to change, change no file: name the state and the patches. Otherwise, when
   isolated, write the patch from the first tree to the last and put it on the main working
   tree with plain `git apply`. If that refuses, or a kept path now holds someone else's
   edits, stop: name the patch and the worktree and take nothing further. Otherwise reverse
   both patches in the worktree with `attempt.py undo`, ending at `HEAD`'s tree, and run `git
   worktree remove` without forcing it. Confirm the tree holds only kept attempts, and name
   the kept patches and the harness. When step 3 opened the trail, its audit and review run
   now. A stopped run leaves kept attempts uncommitted and named, and gains no authority.
8. **Land.** Only when finished with one or more attempts kept and in the working tree,
   after step 7: invoke `land`, passing the kept attempts in order.
   `principle-sequence-verifiable-units` applies. No stopped path lands.

## Reply

- **Finished:** metric and target, whether the predicate held, baseline to final with the
  percent delta, attempts kept and undone, each kept fix on one line, trail path, the best
  next idea, and `land`'s commits or plan, or its refusal and the gap it named. Attempts
  whose paths overlap or depend on each other can collapse into one commit, while the
  trail keeps their order: name any that did.
- **Stopped:** where, the kept attempts uncommitted with their patches, and what is needed.
- **Stopped, undo unavailable or an unmeant path:** the refusal, failure, mismatch or path, the
  tree's state, perhaps partly applied, and the patches, with the tree untouched further.
- **Stopped, not brought back:** the patch and the worktree, both kept.
- **Not started, unattended:** that unattended climbs wait on the wake work, and an offer of
  an attended run.
- **Not started, no reproducing case:** what was tried.

Every reply after step 3 ends with the trail's Attention section, verbatim.
