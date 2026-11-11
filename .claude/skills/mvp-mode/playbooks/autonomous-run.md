---
trigger: A request to keep working without further prompting until a stated, checkable condition holds, with no settled plan to execute.
traits: [stated-unattended-gate]
steps:
  - id: autonomous-run#1
    when: always
    actions: [{trait: exit-predicate-first}, {trait: run-limits-first}]
  - id: autonomous-run#2
    when: autonomous-run#1 fixed a checkable predicate
    actions: [{trait: unattended-isolation}, {trait: worktree-environment-proof}]   # both only when stated unattended
    calls: [{to: "skill:decision-trail", when: "extra columns seq, predicate, branch, head, tree; the first row is the baseline, before any edit; this one whole call stays open through autonomous-run#6"}]
  - id: autonomous-run#3
    when: the trail holds its baseline row, and the request is stated unattended or names a limit
    calls: [{to: "skill:wake", when: "one whole call, opened once, stays open through autonomous-run#6"}]
  - id: autonomous-run#4
    when: once per iteration, entered from autonomous-run#2, autonomous-run#3 or autonomous-run#5
    actions: [{trait: read-trail-first}, {trait: unexplained-change-stop}, {trait: bounded-background-wait}, {trait: smallest-evidenced-change}, {trait: revert-ineffective-experiments}, {trait: row-then-checkpoint}, {trait: discovery-scope-split}]
    calls: [{to: "skill:delegation", when: an attended run and the router's delegation rule sends the iteration to a subagent; told not to stage}]
  - id: autonomous-run#5
    when: after each iteration; in this order, predicate met, a limit hit, or a dead end goes to autonomous-run#6, and anything else returns to autonomous-run#4
    actions: [{trait: limit-bounded-hold}, {trait: category-pivot}]
  - id: autonomous-run#6
    when: every exit, including a closing return from the timer
    actions: [{trait: autonomous-closing-settle}, {trait: autonomous-closeout}]
  - id: autonomous-run#7
    when: an attended Met exit with this run's changes in the working tree, after autonomous-run#6
    calls: [{to: "skill:land"}]
---

# Autonomous run

For a request to keep working by yourself until a stated, checkable condition holds, with no
settled plan. One metric from one command is the hillclimb playbook. A reported defect or failing
test is bug-fix, even overnight. A plan or roadmap is `implement`, new behaviour is feature, a
focused redesign is refactoring, "stop for today" is pause-safely. A person's next message wins.

**The gates:** A run is unattended only when the request's own words say so: overnight, while I'm away, off to bed, unattended, come back by yourself, or the like. Otherwise it is attended, whatever its length.
The reply names the words it took. Never relax the predicate. The loop commits nothing, and a small
task skips no step here.

Waiting on a command: run it in the background with a finite lifetime and take the platform's completion notice, or wait in the foreground. If the runtime gives neither for what must be waited on, take the stopped-waiting exit.

**Limits** bound starting work, not running work or money. Overnight 8 hours; other unattended 4
hours; an attended run naming a limit uses it, 4 hours if it names only attempts; 30 attempts unless
named; over 24 hours only in the request's words. With a card open, a command's lifetime comes from
`admit`'s seconds left; unboundable, it does not start.

1. **The exit.** Write the predicate as a command and the result it must give. Set the limits.
   Attended with no checkable predicate: ask. Stated unattended with none: Not started.
2. **Where it runs, then the trail.** On every path, name one artifact directory outside the tree;
   the trail and each saved patch go there.
   - **Stated unattended:** one detached worktree from `HEAD`, local commands with absolute paths, no
     delegated writer, nothing written to the main tree. Uncommitted work in the checkout is not in
     the folder, and the reply says so. Prove the environment: name what the command needs, establish
     it with the project's own commands and without the parent's source (no inherited `PYTHONPATH`,
     parent venv's editable install or stale build output), make a small real change in the worktree,
     run the predicate, see it respond, put it back and prove the tree is back. It cannot be
     established or does not respond: Not started, environment. A recipe file in the artifact
     directory holds the predicate, the environment, the trail and the base tree. A run that truly
     needs the real checkout is Not started, needs the real checkout: it can run attended.
   - **Attended:** in place, under the stop below.
   - **Then the trail:** invoke `decision-trail` with extra columns `seq, predicate, branch, head,
     tree`; this one whole call stays open through step 6, with a baseline row before the first edit,
     and a bead note when Beads tracks the work.
3. **The card.** When a limit or unattended words apply, invoke `wake`; this one whole call stays
   open through step 6. `refused`: Not started, refused. When stated unattended the first checkpoint
   goes in as the card opens: `note --phase iterating --set recipe=… --set worktree=…
   --set artifacts=… --set head=… --set tree=… --set row=0 --set met=no
   --require recipe,worktree,artifacts,head,tree,row,met`.
4. **One iteration.** Read the trail's tail, compare the state (below), and retry nothing it
   rejected. An attended run may hand the change over by the router's delegation rule through
   `delegation`, told not to stage. When a card is open, `admit` immediately before the change. Make
   the smallest change the evidence justifies and check the predicate.
   `principle-sequence-verifiable-units` applies.
   - **A background command, when stated unattended:** before waiting on it, `note --set
     command=<id>`, where the id or the recipe gives its invocation and an output file in the
     artifact directory, so the command and its result can be recovered after a compaction.
   - **Not advanced:** save the candidate as a patch in the artifact directory (`git diff --binary`
     from the prior tree to the candidate's), and put that path in the row's `evidence`. Remove the
     iteration's own edits, never another's. Prove the tree equals the prior one, otherwise Stopped,
     tree changed.
   - **Then, in this order:** check the predicate on the tree as it now stands, log a row with its
     seq, and when stated unattended `note --set row=<seq> --set tree=… --set met=yes|no --unset
     command`. That `note` is the commit point: a row past it is an incomplete iteration, and a tally
     comes from the checkpoint, never from counting rows. A row describes the tree after keep or
     discard, never a rejected candidate.
   - A discovery is in scope when the predicate cannot be met without fixing it, or the request names it. Anything else goes on a `discovered-from` bead, or in the reply where no tracker exists, and is left unfixed. This grants no standing scope.
   - A step needing authority the request did not give is not taken. If the predicate can be met
     without it, log it and go on. If not: Stopped, needs authority.
5. **Hold.** In this order: predicate met, a limit (`check`, when a card is open), a dead end go to
   step 6; anything else returns to step 4. A limit stops new work even with an idea left, and the
   reply names the idea. A plateau is not a stop: change category and reread the source.
   A dead end is three iterations with no movement after a change of category, with no further approach you can state in one sentence.
6. **Close out**, every exit.
   - On a Not started exit, anything needing a card, checkpoint or artifact directory is skipped, not
     failed.
   - **A closing return** starts no work and first reconciles: the checkpoint's row must exist with
     the same tree and predicate result, row 0 being the base tree. If not: Stopped, trail and
     checkpoint disagree. Then it settles: a tree differing from the checkpoint's is a half iteration,
     left in the folder and named; a running command is named. Only then the result, from the
     checkpoint's `met`, checked on that tree: Met, otherwise Stopped, limit.
   - When a card is open, `close` and cancel, as `wake` says.
   - **Stated unattended:** write the patch from the base tree to the checkpoint's tree in the
     artifact directory and keep the folder.
   - Then the trail's audit and review: one critic, one try, 30 minutes, which may run past the
     deadline. Critic or roster unreachable: `not reviewed` with a reason, never a self-review or a
     silent substitute. Name what changed, what was discarded, each deferred discovery and anything
     still running.
7. **Land.** On an attended Met only: invoke `land`. Being called grants no commit authority, so with
   none it returns the plan. A stopped path and an unattended path never land.

**After a compaction, when stated unattended:** `show` the card and read the recipe. A `command` on
the checkpoint is the iteration in hand: its id or the recipe gives its invocation and output file.

**What brings a run back.** A command's notice, with a card open: `check`. With a checkpoint, a
notice for a command not on it is stale. With no checkpoint (attended, card only), a notice is stale
unless the run started that command for the iteration in hand. Exit 0 or 3 finishes the iteration in
hand, even past the deadline, with no `admit`, and the loop then sees the limit. Exit 4 resumes
nothing and does not reenter closeout: one line of late evidence, in the final reply if still owed,
else a short note, never a second result. The closing timer: `wake`'s `check`, then step 6, at any
time left. The critic's notice takes no card call and completes the reply; a wait that says to end
the turn does so, and the notice brings it back.

**What counts as changed**, every iteration: `git symbolic-ref -q --short HEAD || echo detached`;
`git rev-parse HEAD`; the tree, from
`T=$(mktemp -u); GIT_INDEX_FILE=$T git add -A && GIT_INDEX_FILE=$T git write-tree; rm -f "$T"`.
Each row stores the three, after any discard; when stated unattended the comparison is with the
checkpoint. Ignored files and tracker storage do not count. It cannot tell whose a change was, so
attended in place it does not run beside another writer, and it stops on its own interrupted edit.
Met with an unexplained change does not prove that change verified; `land`'s gates still apply.

| State | Exit |
|---|---|
| Predicate holds | Met, naming any unexplained change |
| `check` says a limit (card open) | Stopped, limit |
| `check` or `admit` exits 2 or 5 (card open) | Stopped, card: start nothing, name it |
| Own command still running | start nothing; its notice brings the run back |
| Branch, HEAD and tree equal the last row | next iteration |
| Any of the three differs | Stopped, tree changed: touch nothing, name what differs |
| Next evidence must be waited for, and no way to wait | Stopped, waiting |

## Reply

Each names this playbook, each skipped step with its reason, elapsed time, attempts, whether the
timer fired, delegates with their models as the vendor reports them, dollars only if the runtime
reported them (otherwise `dollars: not reported here`), anything still running. Nothing is estimated.
After step 2 it ends with the trail's Attention section, verbatim. No reply is promised after a dead
session. A stopped exit leaves changes uncommitted and named.

- **Met:** the predicate and its final output, iterations, what changed and what was discarded,
  discoveries deferred, the timer and what it survived, `land`'s commits, plan or refusal.
  **Stated unattended, instead of `land`:** the patch, the folder, and the command to take it,
  `git apply <patch>`.
- **Stopped, limit:** which limit, the checkpoint's predicate, the best next idea, any half iteration
  and running command.
- **Stopped, dead end:** what was tried, by category.
- **Stopped, needs authority:** the act, and what is done without it.
- **Stopped, tree changed:** what differs, nothing touched.
- **Stopped, card:** the command, its exit and message.
- **Stopped, trail and checkpoint disagree:** both, nothing touched, no result claimed.
- **Stopped, waiting:** what is outstanding, where its evidence will appear, that nothing will resume
  by itself, and how to continue.
- **Not started; Not started, refused; Not started, needs the real checkout; Not started,
  environment:** why, and what is needed.
