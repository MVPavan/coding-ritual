# Spec scope — a spec's tickets on one integration branch

Enter only for a request to implement a spec as a whole whose tickets already
exist in Beads with blocking edges. An explicit workstream request, a named
phase or a bounded task keeps its own scope. A spec seeded as a workstream
(epics anchored on a roadmap) runs under the Workstream or Phase scope: say
which request is due (run all remaining phases, or a named phase) and ask
nothing else. A spec whose tickets are one epic with stages and edges runs
here if its work is significant (step 3), else as task scope in the current
checkout with no worktree. No tickets yet, or none with edges, is `to-roadmap`
(several phases) or `to-plan` then `tracker` (one phase).

## Setup

1. Read the spec and its epic's tickets (`bd children <epic>`, `bd show <id>`).
   The tracker graph orders the work, not the listing. Where a real ordering
   between two tickets has no blocking edge, add it (`bd dep add <needs>
   <needed> --actor "<coding-agent>:<unique-id>"`) before running either;
   never fall back to listing order.
2. Use one integration branch for the whole spec; every ticket lands on it and
   nowhere else. Before any work, save the run record in the workspace ledger
   (`scratchpad/implement/<slug>/progress.md`; see `SKILL.md` Workspace and
   `task-engine.md`): spec and epic ids, base branch and starting SHA,
   integration branch, worktree path. Point the epic at it:
   `bd note <epic> "spec run: scratchpad/implement/<slug>/progress.md"
   --actor "<coding-agent>:<unique-id>"`. On resume, load that record and
   validate it (the worktree exists at its path, on the integration branch)
   before setup; never record today's base in its place.
3. A worktree is only for a significant change. A spec's work usually is one,
   so it runs in one worktree on the integration branch; a ticket inside it,
   however small, gets no worktree of its own. A spec whose whole work is a
   small change is not this scope: run its tickets as task scope in the
   current checkout.
4. **Base check.** Before any work in the worktree, confirm it is on the
   integration branch and that branch contains the recorded starting SHA
   (`git merge-base --is-ancestor <start-sha> HEAD`). On a mismatch, preserve
   the work already there, stop and report the expected and actual bases.
   Reset onto the base only with explicit reset authority.

## Run

5. Take tickets from the ready frontier (`bd ready --parent <epic> --json`,
   keeping direct children), one at a time, in the spec's worktree. Each runs
   through the task loop; a delegated implementer works in that worktree, and
   only one implementer runs at a time: none in parallel.
6. On this scope the spec's worktree replaces the shared checkout of
   `task-engine.md` (Dispatch): tell each worker it works in the worktree, not
   the shared checkout, and that the shared checkout's edits are not its own.
7. Landing a ticket on the integration branch is a commit. Every commit and
   merge needs commit authority. Without it, stop at verified work in the
   worktree and report what is due: the tickets verified, the commits and the
   merges not made. The run has not ended; the worktree stays.

Every stop (no commit authority, a ticket failure, a base mismatch) reports
the worktree path and the run record's path as the recovery pointer.

## Before reporting

8. **Tip merge.** Merge the base branch's tip into the integration branch, then
   rerun the checks the spec's tickets named. Without commit authority, report
   that the merge is due instead.
9. Report the integration branch, its last revision, the tickets closed with
   evidence and any left open.

## Cleanup

10. The run ends when the integration branch's work is merged, or when that
    work is preserved outside the worktree (on a branch, or in a patch under
    the workspace whose path the report gives) and reported. When it ends,
    remove the worktree (`git worktree remove <path>`, no `--force`) only if
    authority already held covers removing it: a request that covers cleanup,
    or a standing instruction. Otherwise keep it and report its path and that
    cleanup is due. Never remove a worktree whose work exists only inside it.
