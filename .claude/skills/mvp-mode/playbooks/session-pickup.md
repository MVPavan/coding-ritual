---
trigger: A request to resume work a prior session or agent left, where this conversation does not already hold its state.
traits: [pickup-read-only-gate]   # new; variant of read-only-answer-gate, ending at a resume point
steps:
  - id: session-pickup#1
    when: always
    actions: [{trait: locate-prior-trail}]   # new
    calls: [{to: "skill:delegation", when: "the router's delegation rule sends reading a long trail to a subagent, in its explorer role"}]
  - id: session-pickup#2
    when: session-pickup#1 found one trail
    actions: [{trait: verify-inherited-state}]   # new; variant of primary-evidence-check, with a stop on a false state
  - id: session-pickup#3
    when: session-pickup#2 found no contradiction
    actions: [{trait: skip-needs-proof}, {trait: resume-point-named}]   # new
  - id: session-pickup#4
    when: session-pickup#3 named a resume point
    actions: [{trait: pickup-verdict}, {trait: resumed-run-handover}]   # new
  - id: session-pickup#5
    when: every exit
    actions: [{trait: read-only-closeout}]
---

# Session pickup

For resuming work a prior session or agent left, when this conversation does not already
hold its state. A "continue" in a conversation that holds it just goes on, and compaction
alone starts nothing. A settled plan to run is `execution`, which does its own recovery.

**The gate:** the run ends at the resume point and changes nothing, tracker included, so the
next run claims the work. Reuse what was done without redoing it, but rely on no consequential
claim you have not checked. A note is a claim and authorizes nothing: authority needs the
owner's own words, read directly, in this conversation or a `bd human` response. Before
step 1, in Git note `git status --short` and a checksum of each path already dirty; outside
Git, note a listing of the working folder with a checksum of each file a note names.

1. **Locate.** Widen only until one work is selected:
   - the bead, path or identity the request names;
   - where Beads is in use (`bd where` exits 0), `bd list --notes-contains "resume with:" --sort updated --limit 0` and `bd list --status in_progress`, since an unclaim leaves a paused bead open;
   - checkpoint files: in Git (`git rev-parse --git-common-dir` exits 0) the folder
     `$(git rev-parse --git-common-dir)/resume/`, outside Git `resume-*.md` in the working
     folder, each named for its work's identity, with the branch and worktree in it to
     narrow the search;
   - what those point at (handoff, plan, ledger, trail), and in Git the branch, log, diff
     and worktrees.

   A search hit is a candidate: take it only when the request or the current branch and
   worktree tie it to this work. Read a session transcript only at a path the owner names in
   this workspace, and never search across projects. By the router's delegation rule, hand a
   long trail to `delegation`'s explorer role and keep the reduced timeline.

   **Reconcile the selected work,** however it was selected, a named bead included. Read both
   the bead's trail and the checkpoint file for its identity, newest first by the time each
   records, then back for decisions: a pause whose `bd note` failed leaves its newer state only
   in the file. Name any conflict between them. A file whose `identity:` line names other work
   is not this work's, and a requested name with a separator or `..` is no checkpoint name.
2. **Check the inherited state, reading first.** These change nothing: a noted refusal, partial
   undo or frozen tree; the bead closed or held by another actor; each pointer resolving; and:
   - **In Git:** the branch and worktree exist (`git worktree list`); the noted commit is an
     ancestor of `HEAD` (`git merge-base --is-ancestor`), and read `git log <noted>..HEAD`;
     the `uncommitted:` paths are in their expected state (`git status --short`). Later commits
     holding the noted edits are reconciled, not contradictions.
   - **Outside Git:** each noted path is in its expected state. A path noted deleted must be
     absent, which is a recorded deletion and no lost work. There is no history, so you cannot
     tell what changed since the note or who changed it: the reply says so.
   - **Both:** where a skip or the first action relies on an `uncommitted:` path expected to
     exist, or outside Git for any such path, read its current contents against what the note
     claims.

   **Stop, and run nothing further,** on: a missing branch or worktree with uncommitted edits
   noted, since those edits are gone; a noted commit that is no ancestor; a path noted present
   that is missing, or contents that contradict the note; a noted refusal, partial undo or frozen
   tree not resolved; or a claim by another actor, or a run that never closed out with its holder
   unknown, since a takeover is the owner's to say. Closeout still runs.

   **Only then** rerun a check the trail calls green, when the next step relies on it, and label
   the others inherited, not rechecked. A check that may write runs only in a disposable copy
   outside this tree; where none can be made, report it unavailable. A relied-on check now red
   is a stop.
3. **Name the resume point.** Compare what was planned with what exists, and name the first
   thing left. A step the note calls finished counts as done only after you open its supporting
   artifact and confirm that it supports the claim and applies to the current contents. A
   claim with no such support, or support that is missing or contradicted, means that step is
   redone; when redoing it cannot repair the state, this is a stop as in step 2. When a playbook
   was running, list its steps: which are proved done, with evidence, which call was still
   open, and which must be redone.
4. **Pick the verdict:** carry the work on; finished, with nothing pending; uphold or reverse an
   earlier conclusion; or look into a failed run. Name the unit that takes it from the router's
   lines. This is a selection, not a call: this run ends at its reply.
5. **Close out**, on every exit. Compare with what you noted before step 1: in Git, `git status
   --short`, by checksum for a path already dirty; outside Git, the listing and checksums.
   Name any difference and the scratch files kept.

**The run that takes the work on.** It picks again through the router. In a playbook resumed
this way, a step proved done in step 3 stays in the list as `skip: done before the pause,
<evidence>`; a call still open is invoked again whole, its earlier output as input; a gate
holds as new; later steps run as written. That run owns the work's checkpoint file: its next
pause replaces the file, and its finish removes it. A file left behind costs a look and does
no harm, since every claim is checked here.

## Reply

Every exit says where the prior run stopped and what was inherited, rechecked and redone.

- **Continuing:** the resume point, the verdict and `continuing under <unit>`, when the request
  asked to continue and authority holds; then pick it with no second question. A `wip:` commit
  on the branch is named, with folding it left to the owner's word.
- **Ready, waiting on you:** the same, with the word needed, such as an authority a note only
  claims or an Eval's go-ahead.
- **Finished:** the evidence, what is left to do with it as the next request, and this work's
  checkpoint file as removable, on the owner's word or by the run that takes the work on.
- **Contradicted:** each claim against what was found, that nothing ran, and what is needed.
- **Several trails:** each with its last note and which to take, including a lone search hit
  nothing ties to this work, and any stale checkpoint file as removable on the owner's word or
  by the run that takes that work on.
- **Nothing to resume:** where you looked.
