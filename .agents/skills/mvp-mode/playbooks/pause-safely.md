---
trigger: An explicit request to stop work now so that a later session can resume it.
traits: [explicit-pause-only, no-irreversible-pause]   # new; the second a variant of irreversible-only-confirmation
steps:
  - id: pause-safely#1
    when: always
    actions: [{trait: safe-boundary-stop}]   # new
  - id: pause-safely#2
    when: a playbook run is open and pause-safely#1 reached a stop
    actions: [{trait: running-playbook-exit}]   # new
  - id: pause-safely#3
    when: this run left uncommitted edits, commit authority covers them, and nothing bars a commit
    actions: [{trait: authorized-wip-commit}]   # new; variant of commit-push-authority
  - id: pause-safely#4
    when: there is work to resume
    actions: [{trait: resume-note-tree-state}, {trait: checkpoint-by-work-identity}, {trait: frozen-tree-checkpoint}]   # new; the first a variant of resume-line
  - id: pause-safely#5
    when: every exit
    actions: [{trait: pause-closeout}]   # new
---

# Pause safely

For an explicit request to stop now so that a later session can resume: "stop for today",
"save this for later". "Keep going" or "going to bed, keep going" asks for no pause, and
compaction alone is none. Finished work to commit is `land`; an idea to keep is a deferred bead.

**The gates:** nothing irreversible happens in order to pause: no push, pull request, merge,
amend or rewrite, and no work destroyed. Being asked to pause grants no authority.

1. **Reach a stopping point.** Finish the atomic step under way or back out of it, and begin
   nothing else. Cancel this run's child agents by the platform's means, or wait for one you
   cannot cancel, and name any partial edit it leaves. Stop this run's background jobs, or
   name any that must finish and what it may still write. Another's process or agent is not
   yours to stop: name what you can see. When a child or job can neither be stopped nor
   waited for, skip steps 2 and 3 and let the note and the reply say so.
2. **Exit the running playbook.** Run its closeout whole, including an open trail's audit and
   review, which "begin nothing else" does not cover. The owner's explicit "don't wait"
   declines that review: `not reviewed`, with that reason. Mark what the resume needs as kept.
3. **Commit only with authority.** Authority is the owner's own words covering commits on this
   work: in this conversation, a `bd human` response, or a workflow invocation that grants
   it. Without it, commit nothing. Also commit nothing under a playbook gate that commits
   nothing (Hillclimb's) or on a frozen tree (step 4). With it, make one commit of only what
   this run changed, on the current branch: `git add` each file this run created, then
   `git commit -m "wip: <what stands>" -- <paths>`, with one body line if the tree is broken.
   Naming the paths means a path someone else already staged stays staged, and it is named. The
   command takes each named file whole, so a file also holding another's edit stays out,
   uncommitted, and is named. A refused commit leaves the edits uncommitted, and the note says
   so: `--no-verify` is no way past a hook. A `wip:` commit is never amended unasked.
4. **Leave the note.** Beyond what `AGENTS.md` asks of a handoff, it holds:
   - the work's identity: its bead ID, or else a name unique to this work, the date plus a
     short name of it; never the branch. It must be one safe filename component: only letters,
     digits, `.`, `_` and `-`, not starting with `.`. Refuse separators and traversal;
   - the time, and in Git the branch, worktree and commit, or outside Git the folder;
   - `uncommitted:` every dirty path with its expected state, present or deleted, and what its
     edits claim to do, or `none`;
   - what was verified and by which command;
   - each finished step of a running playbook, with the artifact that supports it;
   - the first action on resume, where any authority is written, and pointers to any trail,
     plan or ledger, never a copy. No secret.

   **Where it goes.** Where Beads is in use (`bd where` exits 0), pause the bead by its Pause
   rule, and the note is its resume line; with no bead, create one by the Beads rules. Bead
   notes reach a committed export, so they carry only repo-relative paths. Anything
   machine-local, and every note with no Beads, goes in a checkpoint file named for the
   identity, whose first line is `identity: <name>`, and a bead note points at it. In Git
   (`git rev-parse --git-common-dir` exits 0) that is
   `$(git rev-parse --git-common-dir)/resume/<identity>.md`, which outlives a removed worktree
   and is never committed. Outside Git it is `resume-<identity>.md` in the working folder. A
   later pause of the same work replaces its own file and no other: before replacing a file,
   establish from its bead or a stable pointer to the work, such as its plan or trail, that it
   describes this same work. A matching `identity:` line alone does not, since two works can
   share a date and short name. Otherwise leave the file and take a distinct name for this work.
   With `implement` running, also persist as its closeout (step 10) and the workstream walk's
   recovery say. A failed `bd` write falls back to the file, which says so, and so does the
   reply.

   **A frozen tree.** After a Hillclimb stop that leaves the tree untouched (an `attempt.py`
   non-zero exit or a path not meant to change), the freeze covers `.beads/` and its export. Write
   only the checkpoint file. Make no `bd` write and no export: the bead note and the unclaim
   stay pending, and the file says so with the reason.
5. **Close out**, on every exit. No child of this run may still be running unless a note
   names it. Where a note was written, read it back: in Git, `git status --short` and `HEAD`
   must match it; outside Git, each noted path must be in its expected state. Name any
   difference. Where none was written, say `no note needed`.

## Reply

Every exit that wrote a note says where it is, what is on disk and what is only in this
conversation, by path with no diffs, and the first action on resume.

- **Paused, uncommitted:** the dirty paths, which live only in this worktree and go if it goes.
- **Paused, committed:** the `wip:` commit, folded only on the owner's word; what is still dirty.
- **Paused, nothing dirty:** that no edits are left.
- **Paused, frozen tree:** the refusal or unmeant path, and the bead note, unclaim and export
  left pending, with why.
- **Not safe:** what could not stop, its state and what is needed.
- **Nothing to pause:** that no work was open, and `no note needed`.
- **Not paused:** on "keep going", one line saying `no note needed`, and the work goes on.

**Inside a playbook,** add its stopped reply where one truthfully fits, its content intact.
Where none does, say the step reached, mark proof `not reached` rather than failed, and give
its closeout's result. A reply written for an inconclusive or unavailable result does not fit
a proof that never ran. Its "every reply also" lines apply either way, and any trail's
Attention section ends the reply, verbatim.
