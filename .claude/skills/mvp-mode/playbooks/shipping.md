---
trigger: A request to merge, land or ship open pull requests (one or a stack) once each is independently verified.
traits: [shipping-merge-grant, contiguous-verified-run, hands-off-while-landing, full-pr-url]
steps:
  - id: shipping#1
    when: always, before any write to the forge, a branch or the tracker
    actions: [{trait: stack-wide-claim}, {trait: stack-snapshot-before-writes}]
    calls: [{to: "skill:beads", when: before the run's first bead write}]
  - id: shipping#2
    when: a pull request has an earlier verdict
    actions: [{trait: verdict-reuse-on-tree}]
  - id: shipping#3
    when: each unmerged pull request from the bottom that shipping#2 left without a usable verdict
    actions: [{trait: independent-user-run-verdict}, {trait: edit-pass-before-posting}, {trait: verdict-on-pr-and-bead}]
    calls: [{to: "skill:delegation", when: "the reviewer role, briefed to run the change as a user would, against its base"}, {to: "skill:unslop", when: "on the verdict record's prose, before it is first posted"}]
  - id: shipping#4
    when: the verified run holds at least one pull request
    actions: [{trait: verdict-receipts-before-merge}, {trait: edit-pass-before-posting}, {trait: trunk-ancestor-before-merge}, {trait: direct-merge-mutation-at-verified-head}, {trait: bottom-up-merge-read-back}, {trait: pinned-lease-child-move}, {trait: bounded-background-wait}, {trait: event-wait-with-fresh-read}]
    calls: [{to: "skill:unslop", when: "on a missing receipt's prose, before it is posted from the record"}]
  - id: shipping#5
    when: every exit
    actions: [{trait: merge-evidence-bead-close}]
    calls: [{to: "skill:tracker", when: "a pull request was read back as merged"}]
---

# Shipping

For a request to merge, land or ship open pull requests, one or a stack. Each
is verified by someone who did not write it, and only the verified run from
the bottom lands. Getting pull requests merge-ready (threads, checks) is the
babysit playbook; turning working-tree changes into commits is `land`. `gh` is
the forge command line.

**The gates:**

- **Grant.** A request to ship or land authorizes merging the verified run
  and, for a stack, two acts on the next pull request once its parent lands:
  pointing its base at trunk, and a lease-pinned force push of its own branch
  (step 4), and for each pull request read back as merged, closing its bead
  and mirroring that bead alone (step 5). Nothing else: no other branch, no
  merge past the run. The writes `AGENTS.md` (Authority) holds back under any
  standing grant still wait for the owner; step 4's push goes only to the
  stack's own branch under its claim, and a shared one stops for the owner.
- **Verified run only.** From the lowest unmerged pull request upward, the run
  ends before the first one without `PASS` or `PASS+NOTES` that covers its
  current tree. That one is the ceiling. A verified pull request above the
  ceiling waits: it depends on code below it that has not landed. Check the
  ceiling again before touching each next pull request; going past it takes a
  new pass from step 1.
- **Direct merges only.** This version never queues a pull request and never
  arms auto-merge.
- **Hands off.** The run holds the stack's claim, and nobody else edits the
  stack while it runs. It writes nothing but step 4's own moves and step 5's close-out. When a merge
  fails or stalls, read why before changing anything. Limit: run one
  babysitter or shipper per stack; the claim guards the common case.
- **Scope.** Shipping handles stacks built from branches in this repository. A
  stack managed by the forge's own stacked pull-request feature is reported as
  unsupported before any verdict is posted, and a pull request whose head is in
  another repository stops before any move.

1. **Claim and snapshot.** Invoke `beads` before the first bead write. Take the
   stack's claim the way the babysit playbook does: one claim on the nearest
   bead that the beads of all its open pull requests share. No bead, or the
   claim held elsewhere, stops the run. Then record the stack from the bottom
   up: each pull request's number, head SHA, base ref, and the tip of the
   branch it sits on (its old parent tip). A pull request whose parent has
   already merged to trunk first gets step 4's move, with the merged parent's
   last head as its old parent tip, before step 2 checks its verdict.
2. **Reuse a verdict only for the same tree.** A tree that has not changed is
   code that has not changed. Reuse an earlier verdict only when its record
   names the tree it ran on, that tree equals the current head's tree (`git
   rev-parse <head>^{tree}`), and the record names the independent reviewer.
   Anything else gets a fresh verdict in step 3. After a parent's squash merge,
   a moved child keeps its tree exactly when nothing else landed between, so
   its verdict carries over then and only then.
3. **Verify.** Invoke `delegation` for a reviewer that did not write the
   change, from another model family as `delegation` requires, briefed to run
   the change the way a user would (the project's verify skill when it has one,
   otherwise its documented commands) against its base, and to return `PASS`,
   `PASS+NOTES` or `FAIL` with its evidence. Passing checks or a bot's approval
   never stand in for a verdict. The record, written to a file, carries the key
   `verdict <pr>@<tree sha>#<n>` (`n` counts verdicts for that tree), the head
   SHA, the base tree, the reviewer's identity (role and model family) and the
   result. Invoke `unslop` on the record's prose before it is first posted,
   leaving the key, SHAs, identity and result as they are. You post it on the
   reviewer's behalf, its identity attached: as a
   pull-request comment (`gh pr comment <pr> --body-file <file>`) and a bead
   comment (`bd comment <id> --file <file>`), each only when a search for the
   key finds no post there.
4. **Land bottom-up, one at a time.**
   - **Receipts.** Before merging, take the latest verdict for the current
     tree; it must be `PASS` or `PASS+NOTES`, and a pull-request comment and a
     bead comment carrying its key must both exist, on a reused verdict as on a
     fresh one. Post a missing one from the record, prepared as in step 3 (the
     `unslop` pass and the pull request's full web address; key, SHAs, identity
     and result unchanged), or stop.
   - **Trunk.** Immediately before merging, fetch trunk. When its tip is not an
     ancestor of the verified head, stop for that pull request: it needs
     updating and a fresh verdict. A child moved onto a parent's squash commit
     contains it, so a stack still passes.
   - **Merge** an open pull request whose base is trunk through the
     `mergePullRequest` mutation (`gh api graphql`), with `expectedHeadOid` set
     to the verified head and an explicit `mergeMethod` (`MERGE`, `SQUASH` or
     `REBASE`, as the repository merges). It merges at once or fails; a failure
     because trunk requires a merge queue stops the run and is reported.
   - **Read back** `state` and `baseRefName`: go on only on `MERGED` with trunk
     as its base; anything else stops the run with the state observed. Limit:
     the merge pins the head, not the base, so a base edit by someone outside
     the claim just before the merge would be reported, not prevented.
   - **Move the next pull request**, when it is in the run. Fetch; confirm its
     remote head still equals the snapshot SHA and that `git merge-base
     --is-ancestor <old parent tip> <snapshot head>` exits 0. When `git
     rev-list --merges <old parent tip>..<snapshot head>` lists anything, stop
     and report it: never rebase across merge commits. When `git log
     --format=%an <old parent tip>..<snapshot head>` shows a commit by anyone
     other than the pull request's author, or who owns the branch is unclear,
     the branch is shared: stop for the owner's authorization (`AGENTS.md`,
     Authority). In a detached
     worktree created at the snapshot head (`git worktree add --detach <dir>
     <snapshot head>`), run `git rebase --onto <fetched trunk sha> <old parent
     tip>`, push with `git push <remote> HEAD:refs/heads/<branch>
     --force-with-lease=refs/heads/<branch>:<snapshot head sha>`, then remove
     the worktree. When the forge has not already pointed its base at trunk,
     run `gh pr edit <pr> --base <trunk>`. Read back its head (the SHA you
     pushed) and its base (trunk). Any failed or mismatched write stops the run
     with the state observed. Then rerun step 2 on it, wait for its checks, and
     merge it as above.

   Waiting on a command: run it in the background with a finite lifetime and
   take the platform's completion notice, or wait in the foreground. If the
   runtime gives neither for what must be waited on, take the stopped-waiting
   exit. Wait on running checks with `gh pr checks <pr> --watch`; wait on
   anything else with a background wait of a fixed interval, and read the
   forge afresh on every notice or timeout.
5. **Close out**, on every exit. For each pull request read back as merged,
   invoke `tracker`: it closes the bead with the read-back as evidence when its
   acceptance holds, and otherwise comments the evidence and leaves it open.
   Only a bead it closed is then mirrored, by itself (`tracker`'s single-bead
   outbound); a bead left open runs nothing. Release the claim this run took.

## Reply

Name each pull request by its full web address
(`https://<host>/<owner>/<repo>/pull/<n>`), here and in every posted verdict.

- **Landed:** the run and its ceiling; for each pull request its verdict, the
  reviewer's identity, the tree and head SHA it covers, and whether it was
  reused; what merged and the read-back that confirmed it; each bead closed or
  left open and why; what the next gap needs (a verdict, a fix, a rebase).
- **Nothing landed:** the first pull request without a usable verdict and why
  (`FAIL` with its evidence, a changed tree, no bead, no reviewer), with every
  verdict given.
- **Stopped:** the step and the cause (a claim held elsewhere, a required
  merge queue, a merge that did not read back as merged on trunk, a failed or
  mismatched write, a missing verdict post, the stopped-waiting exit), the
  state observed (each pull request's head, base and state), what landed
  before it, and that nothing resumes by itself.
