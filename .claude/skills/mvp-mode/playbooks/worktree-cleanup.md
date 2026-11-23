---
trigger: Stale Git worktrees to audit and prune.
traits: [advisory-audit-bucket, prune-on-approval-gate]   # new; the second is a variant of irreversible-only-confirmation, every removal asks
steps:
  - id: worktree-cleanup#1
    when: always
    actions: [{trait: listed-worktree-audit}, {trait: base-ref-fallback-and-fetch}, {trait: remote-push-state}, {trait: pr-state-as-merge-signal}]   # the first new
    loads: [{path: worktree-cleanup/audit.py}]
  - id: worktree-cleanup#2
    when: the audit ran
    actions: [{trait: pinned-set-cross-check}]   # new
  - id: worktree-cleanup#3
    when: a worktree has uncommitted work
    actions: [{trait: uncommitted-work-pause}]   # new; variant of unmerged-work-protection, for a worktree's uncommitted files
  - id: worktree-cleanup#4
    when: the audit left at least one candidate
    actions: [{trait: removal-proposal}]   # new
  - id: worktree-cleanup#5
    when: the owner approved named worktrees
    actions: [{trait: approved-worktree-prune}]   # new; variant of worktree-cleanup, not tied to a build and only as approved
  - id: worktree-cleanup#6
    when: every exit
    actions: [{trait: cleanup-closeout}]   # new
---

# Worktree cleanup

For stale Git worktrees to audit and prune. Git only: simulators, editor state
and package caches stay out until that tooling enters our toolchain.

**The gates:** a bucket is advice, and the owner's pinned set overrides it.
Nothing is removed without the owner's approval of that exact worktree. This
playbook deletes state with no code review behind it, so these gates are the
review.

1. **Audit.** Record `df -h` for the disk holding the worktrees. Resolve the
   base first: the branch pull requests target, else the remote default
   (`origin/HEAD`), else `main` or `master`, whichever exists, saying the base
   was guessed. Fetch it (`git fetch <remote> <branch>`). After a successful
   fetch, run `worktree-cleanup/audit.py --repo <path> --base <commit>` with
   the commit that fetch brought (`git rev-parse FETCH_HEAD`, right after it),
   naming its branch in the reply; when the fetch fails, say so and pass the
   local ref instead. It reads the paths from Git and changes nothing. Never
   add a path by hand.

   Report each worktree's push state: detached, pushed, ahead of its remote
   branch by a count (`git -C <path> rev-list --count @{upstream}..HEAD`), or
   with no remote branch. Git's ancestry reads a squash or rebase merge as
   unmerged, so where the forge can be read, a pull request it reports merged
   for an `unmerged` worktree's branch is a second merge signal, counted only
   when it merged into that same base branch of the base's repository from a
   branch of that repository (`gh pr list --repo <base's repository> --head
   <branch> --base <base branch> --state merged --json
   url,headRefOid,isCrossRepository`, `isCrossRepository` false): treat that
   worktree as `propose` when it is clean and its HEAD is that pull request's
   head commit or an ancestor of it. Without forge access, the audit's buckets
   stand.
2. **Cross-check.** Ask the owner which worktrees are pinned or in use, unless
   they already said, and take those out. Treat a recent `last` time as a reason
   to hold and ask. A clean, merged worktree can still be in use by a running
   session; the audit cannot see that, and only this list catches it.
3. **Pause on uncommitted work.** For `wip`, show `git diff` and `git diff
   --cached` from that worktree; for `scratch`, name the files. Wait for the
   owner's decision on each. Uncommitted work cannot be recovered after removal.
4. **Propose.** List each `propose` and `prunable` entry that survived steps 2
   and 3, with its branch, merge state (and the merged pull request's address
   when that was the signal), push state and last activity. Name its `ignored`
   entries, because removal deletes those too, and say so when no ref holds its
   HEAD. Show the commits of any `unmerged` or `detached` worktree the owner asks
   about before treating it as a candidate. Then wait for approval by name.
5. **Prune.** For each approved worktree or `prunable` record, run `git worktree
   remove <path>`, which on a missing directory removes only that record. Never
   run `git worktree prune`: it takes no path and removes every eligible record,
   approved or not. Without `--force`, Git refuses a worktree that has become
   dirty or holds submodules: report the refusal, and force only on approval of
   that worktree after the refusal. Branch refs stay; deleting them is a separate
   request.
6. **Close out**, on every exit. Rerun the audit and `df -h`, and record what
   changed.

## Reply

- **Pruned:** `df -h` before and after, each worktree removed, and one line of
  reason for each held back (pinned, uncommitted work, unmerged, locked, refused
  by Git).
- **Proposed, awaiting approval:** the proposal from step 4 and every held-back
  worktree with its reason; nothing was removed.
- **Nothing to prune:** the audit's buckets and why each stays.

Every reply includes the closing audit, or says why it could not run.
