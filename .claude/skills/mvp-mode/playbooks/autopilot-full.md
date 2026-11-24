---
trigger: A set of settled beads (a feature, several, or an epic's features) handed over to build unattended, each through one review to a merge-ready pull request, never merging.
traits: [autopilot-delivery-grant, gate-loosening-held, never-force-push, callee-bound-to-grant]
steps:
  - id: autopilot-full#1
    when: always, before any branch, commit or bead write
    actions: [{trait: settled-bead-intake}, {trait: blocked-bead-waits}, {trait: owner-sets-concurrency}, {trait: active-run-marker}]
    calls: [{to: "skill:beads", when: before the run's first bead write}]
    loads: [{path: autopilot-full/run_marker.py, when: "acquire, last in intake"}]
  - id: autopilot-full#2
    when: each feature that goes ahead, before its first edit
    actions: [{trait: fresh-trunk-branch-per-feature}, {trait: push-after-each-task}]
    calls: [{to: "skill:delegation", when: "features run in parallel: one worker per feature, in its own worktree"}]
  - id: autopilot-full#3
    when: each feature, once its branch exists
    actions: [{trait: task-loop}, {trait: unit-bead-execution}, {trait: confirmed-cause-fix}, {trait: regression-proof-and-rerun}, {trait: attempt-log}, {trait: two-failure-stop}, {trait: finding-adjudication}, {trait: no-reused-implementer}, {trait: run-owned-review-loop}]   # implement's Task loop (implement#4) without its per-unit review (implement#5)
    calls: [{to: "skill:tdd", when: risk calls for test-first or characterization}, {to: "skill:security", when: a material boundary change}, {to: "skill:systematic-debugging", when: a failure's cause is unclear}, {to: "skill:delegation", when: "a unit goes to a worker: a newly started implementer per bead"}, {to: "skill:land", when: "each build commit, after step 4's gate"}]
  - id: autopilot-full#4
    when: before every commit a feature makes, at every commit point (a build commit, a trunk merge, babysit's publish), a worker's included
    actions: [{trait: commit-time-checks}, {trait: cheap-checks-first}, {trait: committed-tree-check}, {trait: unscripted-checks-noted}, {trait: gate-file-first}]   # commit-time-checks: a script the agent runs before each commit, not a git hook (the hooks path belongs to Beads; row 2026-11-22-rejects-review:035 left the form to this build); the project's gate file names the checks
    calls: [{to: "skill:land", when: "the gate passed on a build commit or babysit's publish; a trunk merge commits by step 6's git commit --no-edit, never land"}]
    loads: [{path: autopilot-full/commit_gate.py}]
  - id: autopilot-full#5
    when: while a feature builds, a pattern shows its sketch is wrong
    actions: [{trait: scrap-on-repeated-friction}]
  - id: autopilot-full#6
    when: a feature's tasks are built and committed
    actions: [{trait: code-ready-trunk-merge}, {trait: checks-on-integrated-tree}, {trait: push-and-open-pr}]
    calls: [{to: "skill:pr", when: "the pull request's body, creating and mirroring no issue"}]
    loads: [{path: autopilot-full/commit_gate.py, when: "on the staged merge, then with --since on the merged tip"}]
  - id: autopilot-full#7
    when: a feature's pull request is open
    actions: [{trait: review-once-per-feature}, {trait: independent-user-run-verdict}, {trait: verdict-on-pr-and-bead}, {trait: verdict-reuse-on-tree}]
    calls: [{to: "skill:delegation", when: "the reviewer role, from another model family"}, {to: "skill:unslop", when: "on the verdict record's prose, before it is first posted"}, {to: "playbook:babysit", when: "drive mode within this grant, once the verdict is posted, until merge-ready"}]
  - id: autopilot-full#8
    when: a review, a check or a review thread raises a finding
    actions: [{trait: shown-problem-blocks}]
  - id: autopilot-full#9
    when: a feature's next write is one the gates hold, its branch holds a push this run did not make, or a push is rejected
    actions: [{trait: held-write-stop}, {trait: foreign-push-stop}, {trait: rejected-push-investigation}]
  - id: autopilot-full#10
    when: the owner says stop, at any point
    actions: [{trait: owner-stop-zero-writes}]
  - id: autopilot-full#11
    when: every exit
    actions: [{trait: keep-worktree-until-landed}, {trait: autopilot-closeout}]
    calls: [{to: "playbook:worktree-cleanup", when: "a feature's pull request was read back as merged during the run"}]
    loads: [{path: autopilot-full/run_marker.py, when: "release, last, only when this run took the marker"}]
---

# Autopilot-full

For a set of settled beads the owner hands over to build unattended: one
feature, several, or an epic's features. Each feature gets its own branch,
is built with the implement playbook's Task loop, passes the commit gate at
every commit, gets one independent review and is carried to a merge-ready
pull request. Nothing merges here: merging is the shipping playbook, on the
owner's word, and it can reuse this run's verdicts. Building settled work
while the owner is present is the implement playbook; driving one checkable
condition by repeated attempts is autonomous-run. `gh` is the forge command
line.

**The gates:**

- **Grant.** The owner's go on named beads authorizes, for each feature that
  goes ahead: a branch (and worktree) off trunk, commits on it, ordinary
  pushes to it, opening its pull request and writing that pull request's own
  body, comments and thread replies, posting its verdict, and the bead writes
  the steps name. Nothing else. A request to state the plan, or a question
  about it, is not a go.
- **Held for the owner.** The writes `AGENTS.md` (Authority) holds back under
  any standing grant, and also merging, closing an epic, rewriting a pushed
  branch's history, any forge write outside the grant (an issue created or
  mirrored, a workflow rerun, a bead closed after a merge), and anything that
  loosens a gate: a skipped or soft-failed test, a raised budget, an
  allowlist entry, a check removed or weakened in the gate file. A held write
  stops its feature at step 9, never the whole run.
- **No force-push**, the feature's own branch included. Trunk comes in by
  merging it into the feature's branch, pushed as an ordinary commit; rebase
  only before the branch's first push.
- **Called units stay inside this grant.** `pr` and `babysit` carry wider
  grants of their own; here each runs bound to the one above, as steps 6 and
  7 say, and a write beyond it goes to step 9.
- **Branch guard.** The run marker turns on the project's branch-guard hook
  when one is installed: while the marker exists, file-edit tool calls in any
  checkout of the repository that is on its default branch are refused. Limit:
  writes made through the shell (redirection, `tee`, `sed -i`, scripts) are
  not covered, so every write stays in the feature's worktree by discipline.

1. **Intake.** List every bead handed over (an epic: its direct features),
   then take only those with acceptance and no open material question. Invoke
   `beads` before the first bead write. A bead with an open question gets the
   `human` label and a comment naming it, and is skipped. A bead blocked by
   one still open, a feature of this run included, waits; the run builds the
   others. A feature delivered by pull request closes once that merges, so the
   waiting one starts in a later run from a trunk that holds it. A code
   blocker (a feature, task or bug) closed with no merged pull request in its
   close reason (wontfix, a duplicate, by hand) proves nothing reached trunk:
   the bead gets the `human` label and a comment naming the blocker, and is
   held; a closed decision or closed `human` bead frees it, as Beads intends.
   Judge each bead by two checks, never a guess: `bd ready --limit 0` lists it
   (inherited blocks included; the default list stops at 100), and `bd show`
   on it and its ancestors finds the blocking edges, each closed code blocker
   then read by its own id (`bd show <id> --json`, its `close_reason`); a
   feature's own child tasks are step 3's. When none can start, reply Not
   started, taking no marker. State which features are independent and the
   evidence: no blocking edge between those proposed in parallel, and the
   files each is expected to touch do not overlap. Propose parallel or one at
   a time; the owner's go sets the concurrency, because usage headroom is the
   owner's call, never guessed. With no stated choice, run one at a time. The
   owner may lower it mid-run: running work finishes its current task, then
   the rest go one at a time. Last, take the run marker:
   `python3 autopilot-full/run_marker.py acquire` (beside this file), run in
   the repository. It creates `autopilot-run` in the common git dir only when
   none exists and prints this run's id; note the id on the first bead. Exit
   4, a marker exists: another run is active or a crashed one left it, so stop
   and ask the owner, starting nothing.
2. **Branch per feature, off trunk, never stacked.** Just before a feature's
   branch, worker and claim, rerun step 1's blocker rule on its current edges
   and close reasons: it waits or is held as there. Fetch trunk and make the
   feature's branch from its tip in a worktree of its own, so the main
   checkout and anything uncommitted there stay untouched. In parallel, each
   feature also gets its own worker through `delegation`. Shared state follows
   `principle-separate-before-serializing-shared-state`: each worker writes
   only its own worktree and branch, and the coordinator alone writes the bead
   store and the run marker and fetches trunk, one write at a time. Push soon
   after the branch starts, the first time with upstream tracking (`git push
   -u origin <branch>`), and after each finished task, with a bead note as the
   resume line (branch, last pushed SHA, next task), so a lost session loses
   at most one task.
3. **Build** with implement's Task loop (its section 4) run as this step, not
   the implement playbook called whole: one bead at a time, a feature's open
   children first, one ready child at a time. Claim the bead, build in
   dependency order within owned paths, invoking `tdd` when risk calls for
   test-first and `security` for a material boundary change. When a failure's
   cause is unclear, invoke `systematic-debugging` and fix only a cause it
   confirms, prove the fix with a regression check and rerun the failing
   scenario, log each attempt, and after two failed fixes stop the feature
   with the log for the owner. Verify each finding before acting on it, run
   the checks, inspect the diff, and close each task bead with its evidence;
   the feature's own bead closes through `tracker` once its pull request
   merges, not here. `delegation` chooses implementers, a newly started one
   per bead. Implement's per-unit review (its section 5) does not run: by the
   owner's ruling of one review per feature, step 7's review replaces it. A
   bead that itself requires another review keeps it: run it as the bead
   says, or hold it at step 9 when it needs the owner. Every commit passes
   step 4, then `land`.
4. **Commit gate, at every commit point:** a build commit (step 3), a trunk
   merge (step 6) and babysit's publish (step 7). Stage the commit's paths,
   then run `python3 autopilot-full/commit_gate.py` (beside this file) from
   the worktree. It reads the project's gate file,
   `.repo-context/commit-gate.toml`, as the commit holds it, prints the range
   it judges as a `git diff` command, and runs staged-file checks first, then
   whole-project checks, cheapest first, stopping at the first failure.
   Exit 0: before committing, do each manual check it prints from the
   project's verification guide on that range; then commit through `land` (a
   trunk merge commits as step 6 says) and, right after the commit succeeds,
   note each result on the bead with the range and the new commit's SHA. A
   `SKIP` it prints (an optional tool not installed) goes in the same note.
   Exit 1: fix and rerun; never skip a check. Exit 4: the tree holds changes
   the commit would not, or the gate file differs from the staged one; stage
   them into this commit when they are this task's (a gate-file change that
   loosens it is held), otherwise stop the feature and name them. Exit 3, no
   gate file: stop at this first commit, draft the file from the project's
   verification guide (every check a script can judge as a command, the rest
   as manual entries) and wait for the owner's approval. A worker's brief
   carries this step.
5. **Friction stop.** A pattern that shows the feature's sketch is wrong
   stops that feature: the same workaround recurring, special-case branches
   piling up, type escapes, repeated deviations from the sketch. One isolated
   problem is not a pattern. Note the pattern on the bead, label it `human`,
   push what is committed and move to the next feature.
6. **Code-ready and the pull request.** Fetch trunk. When it has moved past
   the branch's base, merge it in (`git merge --no-ff --no-commit <trunk>`)
   and settle any conflict. Run step 4's gate on the staged merge, which it
   never refuses as empty, and do its manual checks before committing; then
   finish the merge as one commit of the whole index (`git commit --no-edit`,
   not `land`, whose split of uncommitted paths does not fit a merge), check
   that HEAD has two parents (the feature's previous tip and the trunk commit
   merged), and note the results on the bead with the range and the merge
   commit's SHA. With the tree clean, run the gate with `--since <trunk>` on
   the tip, then do each manual check it prints on the range it prints and
   note each result on the bead with that range and the tip's SHA. When it
   reports nothing changed since trunk, trunk already holds the feature's
   whole tree: there is nothing to ship, so stop the feature with a bead note
   saying so. Push nothing for the pull request until the gate and the manual
   checks pass; a failure is fixed by a new commit through step 4, then this
   step runs again. Push, then open the pull request with
   `gh pr create --base <trunk>` (a branch's merge-base setting can pick
   another), its body through `pr`, which creates and mirrors no issue here:
   `Closes #<n>` only for the bead's own issue when this pull request
   completes it, `Refs #<n>` for an ancestor's, and no such line when no bead
   on the chain has a mirrored issue, with a bead note saying so. Read its
   base back (`gh pr view --json baseRefName`) before any verdict: not trunk
   stops the feature and is reported.
7. **One review, then Babysit.** Invoke `delegation` for a reviewer that did
   not write the feature, from another model family, briefed to run the
   change the way a user would against its base and to return `PASS`,
   `PASS+NOTES` or `FAIL`, failing only on a problem step 8 counts. Record
   and post the verdict the way Shipping records one (its key `verdict
   <pr>@<tree sha>#<n>`, the head SHA, the base tree, the reviewer's role and
   model family, the result), on the pull request and on the bead, invoking
   `unslop` on its prose first. Each later head needs a verdict for its own
   tree: a trunk merge, a conflict fix or a minor fix gets one re-check by the
   same kind of reviewer; a wording-only change gets a re-check that only
   confirms the diff since the verdict's tree touches prose alone, recorded
   as a verdict for the new tree; new behaviour or a large new diff gets a
   full review again. Then run the babysit playbook in `drive` mode within
   this grant: no workflow rerun, no issue mirroring and no closeout write
   after a merge (each goes to step 9); each fix it publishes passes step 4 at
   its `land` and step 9's check before its push, and its head gets its
   re-check here. Merge-ready is babysit's ready read plus a usable verdict
   for the current head's tree (Shipping's rule: `PASS` or `PASS+NOTES`, or a
   `FAIL` the owner accepted under its key).
8. **Block only on a shown problem:** a failing run at the head, or a
   document line the change made wrong. A problem the base already has
   blocks only when the change copies it or newly reaches it. Every other
   finding becomes a follow-up bead linked to the feature.
9. **Held writes, foreign and rejected pushes.** When a feature's next write
   is one the gates hold, stop that feature at it, keep its branch and state,
   and list the write for the owner. Before every push, whichever step makes
   it, fetch and compare the remote tip with the SHA this run last pushed; a
   push this run did not make stops that feature and is reported. A rejected
   push also stops it: find out why (the remote moved, a hook or a rule
   refused) and report that; never force.
10. **The owner's stop**, at any point: finish no step and start none; no
    further write to a branch, the forge or the tracker, and every worker gets
    the same order. Report where each feature stands. The closeout then only
    releases the run marker; claims stay for the owner to release or resume.
11. **Close out**, on every exit. Keep each feature's worktree and branch while
    its pull request is open: review fixes land there. For a pull request read
    back as merged during the run, cleanup goes through the worktree-cleanup
    playbook; discarding unmerged work stays held for the owner. Release the
    claims this run took, leave a resume line on each unfinished bead, and
    release the run marker last, `python3 autopilot-full/run_marker.py
    release <run id>`: it removes the marker only while it holds this run's
    id. A run that did not take the marker releases nothing.

## Reply

Name each pull request by its full web address
(`https://<host>/<owner>/<repo>/pull/<n>`). Every exit lists each bead not
started at steps 1-2 and why: its blocker and its pull request if any, or
else the actual reason (no acceptance, open question, claimed, deferred).

- **Finished:** per feature, its pull request, state (merge-ready, waiting on
  a person, merged) and verdict with the tree it covers; the concurrency the
  owner set; follow-up beads.
- **Partly finished** (also when a bead waits or is held, once a feature
  started): the above for each feature that reached merge-ready, and for each
  other feature where it stopped and why: a held write waiting for the owner,
  a friction stop, an open question, a foreign or rejected push, a gate that
  would not pass, a missing gate file, nothing to ship (trunk already holds
  the feature), a pull request on the wrong base.
- **Stopped by the owner:** where each feature stands (branch, last pushed
  SHA, pull request), what was in flight, the claims still held, and that
  nothing resumes by itself.
- **Not started:** no bead was settled, no feature started because every
  settled bead waits or is held (at step 1 or 2), or a run marker already
  existed; what each bead needs.
