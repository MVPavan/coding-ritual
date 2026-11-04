---
trigger: Sustained improvement of one measurable metric against a stop predicate, attended or stated unattended, with no settled plan to execute.
traits: [stated-unattended-gate, one-change-one-measurement]
steps:
  - id: hillclimb#1
    when: always
    actions: [{trait: repro-before-climb}, {trait: stop-predicate-with-floor}, {trait: unattended-target-from-request}, {trait: run-limits-first}]   # stop-predicate-with-floor attended, unattended-target-from-request stated unattended, limits when the request names one or it is unattended
    calls: [{to: "skill:explain-code"}, {to: "skill:performance-optimization", when: this one whole call stays open through hillclimb#5; the predicate is its stop condition}]
  - id: hillclimb#2
    when: hillclimb#1 fixed the metric and predicate
    actions: [{trait: attempt-isolation-gate}, {trait: climb-checkpoint}, {trait: worktree-environment-proof}, {trait: bounded-background-wait}, {trait: sensitivity-proof-then-freeze}, {trait: gate-green-baseline}]   # climb-checkpoint and worktree-environment-proof only when stated unattended; gate-green-baseline a variant of baseline-check-before-change
    calls: [{to: "skill:wake", when: "the request is stated unattended or names a limit; this one whole call stays open through hillclimb#7"}, {to: "skill:build-a-lever", when: no existing command emits the metric}]
    loads: [{path: hillclimb/attempt.py}, {path: hillclimb/unattended.md, when: the run is stated unattended}]
  - id: hillclimb#3
    when: the harness is frozen
    calls: [{to: "skill:decision-trail", when: "extra columns seq, before, after, delta, tests, tree, index, value; this one whole call stays open through hillclimb#7"}]
  - id: hillclimb#4
    when: once per attempt, entered from hillclimb#3, hillclimb#5 or hillclimb#6
    actions: [{trait: read-trail-first}, {trait: bounded-background-wait}, {trait: row-then-checkpoint}, {trait: keep-or-undo-rule}, {trait: attempt-snapshot-undo}]   # row-then-checkpoint writes its checkpoint only when stated unattended; attempt-snapshot-undo a variant of revert-ineffective-experiments
    calls: [{to: "skill:delegation", when: an attended climb and the router's delegation rule sends the attempt to a subagent; one factor per brief; told not to stage}]
  - id: hillclimb#5
    when: after each attempt; in this order, predicate met, a limit hit, or no cheap untried idea left goes to hillclimb#7; several rejects in a row go to hillclimb#6; anything else returns to hillclimb#4
    actions: [{trait: predicate-held-stop}, {trait: limit-bounded-hold}]   # the first with no card, the second with one
  - id: hillclimb#6
    when: hillclimb#5 found several rejects in a row with the predicate unmet; returns to hillclimb#4
    actions: [{trait: plateau-pivot}]   # new
  - id: hillclimb#7
    when: every exit, including a closing return from the timer
    actions: [{trait: climb-closeout}, {trait: climb-closing-settle}, {trait: unattended-climb-closeout}]   # the first attended, the others stated unattended
    loads: [{path: hillclimb/unattended.md, when: the run is stated unattended}]
  - id: hillclimb#8
    when: an attended climb finished with one or more attempts kept and in the working tree, after hillclimb#7
    calls: [{to: "skill:land"}]
---

# Hillclimb

For sustained improvement of one measurable metric from one repeatable command against
a stop predicate, attended or stated unattended, with no settled plan. One fix is the
perf-issue playbook, a plan to run is `execution`, and a variant judged on fresh sessions is
the eval playbook.

**The gates:** A run is unattended only when the request's own words say so: overnight, while I'm away, off to bed, unattended, come back by yourself, or the like. Otherwise it is attended, whatever its length. One change, one measurement, then keep or undo: never stack untested changes. The loop commits nothing, with or without commit authority.

Waiting on a command: run it in the background with a finite lifetime and take the platform's completion notice, or wait in the foreground. If the runtime gives neither for what must be waited on, take the stopped-waiting exit.

**Limits.** An attended climb with no limit keeps this loop: no card, no card operation. With a
limit ("for an hour") it has a card and only `check` and `admit`; every gate runs at any size, and
it does not count as away. Limits bound starting work, not running work or money: overnight 8
hours, other unattended 4 hours, an attended climb's named limit, 4 hours if it names only attempts,
30 attempts unless named, over 24 hours only in the request's words.

**Stated unattended**, read `hillclimb/unattended.md` before step 2 and again after a compaction: it
holds isolation, the environment proof, the recipe and checkpoint, recovery, the closing return and
closeout. Give `wake`, as the caller's closing step, that file's absolute path and its closing
return, so the timer's prompt carries them.

**Terminal stops, stated unattended.** On an unmeant path, or `attempt.py` refusing or failing,
write `note --set stopped=<reason>` before anything else, change no file, and go to step 7, which
closes the card. One failure is not terminal: the first `verify` of a recovery or a closing return,
which is how an incomplete attempt shows and which recovery takes. A card with `stopped` never takes
recovery: touch nothing, and reply Stopped, undo unavailable or an unmeant path, no result claimed.
With no card yet there is no marker, and on a Not started exit, closeout's steps needing a card,
checkpoint or artifact directory are skipped, not failed.

1. **Ground.** Invoke `explain-code` on the target. Name the workload dimensions that can
   move the result and pick a case that reproduces the complaint. When none does, repair
   the case here, at most two tries, then stop with what was tried. Invoke
   `performance-optimization`; this one whole call stays open through step 5, its steps
   1-3 run across steps 1 and 2, and its steps 4 and 5 run in step 4. Settle one metric,
   which way is better, and a stop predicate: a target plus a floor on how many attempts
   run, in the user's numbers or agreed. The predicate is the skill's stop condition. Stated
   unattended, the target must be in the request, none is Not started, unattended; the floor when
   unstated is 3 attempts, named in the reply.
2. **Harness.** First name one artifact directory outside every worktree this climb will remove.
   Patches, the harness and measured artifacts all live there; in a snapshotted tree they would
   break undo, closeout's verify or the worktree's removal. The harness runs with the tree under
   test as its working directory. Then isolate. When a path you will change holds someone else's
   edits, or another agent or person may write anywhere in this tree during the climb, the whole
   climb runs in one detached worktree at an ignored path or outside the tree: a snapshot covers the
   whole tree, so it needs one writer across it. Before any baseline: run `attempt.py snapshot`
   here, which prints the tree and the index tree; `git worktree add --detach <path> HEAD`; write
   `attempt.py patch 'HEAD^{tree}' <start> <s.patch>`; then, in the worktree, `attempt.py replay
   <s.patch> <start> <index>`, with the index tree its own `snapshot` prints. A stated unattended
   climb always isolates. Stated unattended or naming a limit: invoke `wake` once isolated; this one
   whole call stays open through step 7. `refused`: Not started, refused. `hillclimb/attempt.py`,
   beside this file, refuses a sparse tree, files whose bytes Git converts and a patch changing a
   `.gitattributes`; a refusal is a stop. A harness rebuilds and never trusts ignored build output.
   When no existing command emits the metric, invoke `build-a-lever`. Show that contrasting
   workloads separate as expected, vet the harness as the skill's vetting branch says, then freeze
   it: one command, no further change. Record the baseline and show the regression gate green; a red
   gate stops here.
3. **Open the trail.** Invoke `decision-trail` with extra columns `seq, before, after, delta, tests,
   tree, index, value`, filled attended too; `value` is the selected tree's, `after` the
   candidate's. This one whole call stays open through step 7. Name a trail path in the artifact
   directory, or anywhere else closeout will not remove and no snapshot sees. Each row's decision is
   the change, why the hypothesis, evidence the patch, and result `kept`, `kept, simplification` or
   `undone`.
4. **Attempt.** Read the trail first and retry nothing it already rejected. Choose one change by the
   skill's step 4. When attended, by the router's delegation rule, hand it over through
   `delegation`, one factor per brief, told not to stage. When a card is open, `admit` immediately
   before the attempt; a command's lifetime comes from its seconds left, and cut short it gives no
   measurement, so the attempt is incomplete. Around the edit: `attempt.py snapshot`, edit,
   `snapshot` again, `attempt.py patch <start> <end> <a.patch>`. List its paths with `git apply
   --numstat <a.patch>`: a path you did not mean to change is a stop, before keeping or undoing,
   since another's edit between the two snapshots looks like part of the attempt. Measure with the
   frozen command and run the gate. `principle-subtract-before-you-add` applies, and
   `principle-sequence-verifiable-units` applies between attempts. Keep a win: the metric moved past
   noise with the gate green. Also keep a demonstrated simplification when the metric does not
   materially worsen and correctness holds, logged as `kept, simplification`, never as a speedup.
   Otherwise undo in full; a win that breaks behaviour fails the gate. Only `attempt.py undo
   <a.patch> <start> <index>` undoes. It proves the result first and refuses with nothing changed,
   then reverses and verifies. A failure during the real reverse (an ignored file blocking a
   directory, a write error) may leave part of it applied and exits 1. Either exit is a stop, and
   the tree stays untouched from then on. Log the row either way, after any undo and a fresh
   snapshot, with its seq.
5. **Hold the predicate.** After each attempt, in this order: predicate met, a limit hit (`check`,
   when a card is open), or no cheap untried idea left goes to step 7; several rejects in a row go to
   step 6; anything else returns to step 4. Never relax the predicate; with no card, never quit while
   a cheap untried hypothesis remains; with one, a limit stops new work even with an idea left, and
   the reply names the idea. When stuck say so rather than spin. Close the skill's attempt record and
   any regression guard before its call ends.
6. **Pivot.** With several rejects in a row and the predicate unmet: change category,
   combine near-misses and reread the source before concluding. Then return to step 4.
7. **Close out**, on every exit. A stated unattended climb, whichever exit brought it here, takes
   the closing return and closeout in `hillclimb/unattended.md` instead of this step, and brings
   nothing back. When a card is open, `close` and cancel, as `wake` says. After a non-zero exit from
   `attempt.py`, or a path you did not mean to change, change no file: name the state and the
   patches. Otherwise, when isolated, write the patch from the first tree to the last and put it on
   the main working tree with plain `git apply`. If that refuses, or a kept path now holds someone
   else's edits, stop: name the patch and the worktree and take nothing further. Otherwise reverse
   both patches in the worktree with `attempt.py undo`, ending at `HEAD`'s tree, and run `git
   worktree remove` without forcing it. Confirm the tree holds only kept attempts, and name the kept
   patches and the harness. When step 3 opened the trail, its audit and review run now. A stopped
   run leaves kept attempts uncommitted and named, and gains no authority.
8. **Land.** Only an attended climb finished with one or more attempts kept and in the working
   tree, after step 7: invoke `land`, passing the kept attempts in order.
   `principle-sequence-verifiable-units` applies. No stopped path lands.
   A stated unattended climb never reaches this step, whatever commit authority exists.

**What brings a run back, with a card open.** A command's notice: `check`. With a checkpoint, a
notice for a command not on it is stale. With no checkpoint (attended, card only), a notice is stale
unless the run started that command for the attempt in hand. Exit 0 or 3 finishes the attempt in
hand, even past the deadline, with no `admit`, and the loop then sees the limit. Exit 4 resumes
nothing and does not reenter closeout: one line of late evidence, in the final reply if still owed,
else a short note, never a second result. The closing timer: `wake`'s `check`, then the closing
return in `hillclimb/unattended.md`, at any time left. The critic's notice takes no card call and
completes the reply.

## Reply

- **Finished:** metric and target, whether the predicate held, baseline to final with the
  percent delta, attempts kept and undone, each kept fix on one line, trail path, the best
  next idea, and `land`'s commits or plan, or its refusal and the gap it named. Attempts
  whose paths overlap or depend on each other can collapse into one commit, while the
  trail keeps their order: name any that did.
- **Stopped:** where, the kept attempts uncommitted with their patches, and what is needed.
- **Stopped, undo unavailable or an unmeant path:** the refusal, failure, mismatch or path, the
  tree's state, perhaps partly applied, and the patches, with the tree untouched further and no
  result claimed.
- **Stopped, not brought back:** the patch and the worktree, both kept.
- **Finished, unattended:** metric, target, predicate held or not on the handed-over tree, baseline
  to that tree's value, attempts kept and undone with each kept fix on one line, the patch and
  worktree paths, the command to bring it back (`git apply <patch>`), that `land` follows on request,
  the timer and what it survived, whether the review ran, and any interrupted patch with its paths.
- **Stopped, limit:** the finished reply that fits, plus which limit, and what was undone or still runs.
- **Stopped, trail and checkpoint disagree:** both, nothing touched, no result claimed.
- **Stopped, waiting:** what is outstanding, where its evidence will appear, that nothing will resume
  by itself, and how to continue.
- **Not started, refused; Not started, environment; Not started, unattended:** what is missing, and
  what to send.
- **Not started, no reproducing case:** what was tried.

Every reply names this playbook and each skipped step. With a card: elapsed time, attempts, whether
the timer fired, delegates and models as the vendor reports them, dollars only if reported (otherwise
`dollars: not reported here`), anything still running. No reply is promised after a dead session.
Every reply after step 3 ends with the trail's Attention section, verbatim.
