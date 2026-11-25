---
name: decision-trail
description: "Use when a calling playbook names it, or when asked for a reviewable trail of a long run someone will check after stepping away: an append-only TSV of decisions with evidence pointers, closed by an audit and an independent critic. A metric climb is the hillclimb playbook, which calls this. Skip a resume note, a bead note or a short attempt record."
---

# Decision Trail

Keep one authoritative log for a run: a single TSV file with one single-line row per
decision, audited at the end and reviewed by someone else. Deliverable: the trail and its
Attention section. When Beads tracks the work, a bead note points at the trail.

**Location.** The first that applies: the path your caller names;
`scratchpad/trails/<slug>.tsv` when `git check-ignore -q` says it is ignored;
`$(git rev-parse --git-dir)/trails/<slug>.tsv`, which never shows in status; where that
command exits non-zero, outside Git, the working folder, and the reply says so. Propose
committing a trail only when a reviewer needs it to trust the outcome, and commit only
with authority.

**Rows.** Append through this skill's `scripts/log_row.py`:
`log_row.py <file> [--extra a,b] phase=… decision=… why=… evidence=… result=… a=… b=…`
Every row has `ts` (ISO8601, stamped for you), `phase` or workstream, `decision` in one
line, `why`, `evidence`, and `result` as an outcome or state. A caller's columns come after
these through `--extra`, the same set on every call; the fixed ones never change.

- Evidence is a pointer that resolves (a commit, pull request, file and line or artifact
  path), never narrative. Prefer what a committed script produced over a hand-made
  one-off; this grants no commit authority, so with no committed script, other evidence stands.
- Log decision points and checkpoints: a chosen fork, a finished unit with its verification,
  a pivot or revert with its cause, a surfaced blocker, a fixed gate. Never each action or
  a self-evident step. A looping run writes one row per iteration and reads the tail first.
- Word rows as you would tell a colleague, concretely; spell a guiding principle out in
  place of citing it as a tag.
- Never edit or delete a row; correct or reverse one by appending a row that supersedes it.

**Runs.** One agent conversation with its later turns and summaries is one run, so
compaction alone starts nothing; a pickup, replacement agent or new chat is a new run. A
run adding to a log with rows writes a `start` row first, and on returning reads the log's
tail and writes a fresh one if another run's `start` has appeared. A `start` row gives the
`ts` span of the rows this run did not write and identifies this run in its evidence; that
phase means nothing else. So A, then B, then A assigns every row, and a pickup reads
`start` rows to see who wrote what.

**Audit before handing back.** Check the log for truthfulness against what happened. Cover
only this run's stretches, each from one of its `start` rows or the log's first row to the
next `start` row of another run.

- Each row's pointer must resolve and support what the row says.
- A fork, pivot or abandoned path that shaped the work with no row is a gap: add the row,
  from your own context, and say so if that context was compacted.
- Change no row, even an invented one: add a row superseding it with what really happened
  and a pointer that resolves. Supersede a row outside your stretches only when your own
  work shows it to be wrong.
- Check rows against real events only in an event record your caller names, verified and
  scoped to this workspace; without one, the reply says this check was unavailable. Never
  search across project transcript folders: that exposes unrelated private conversations.

**Review.** Before hand-back, a critic through `delegation`, from another model family,
scans for what is suboptimal or risky for the owner's attention and does not redo the work.
It flags weak or absent evidence, checks skipped or claimed without proof, choices risky in
hindsight, and gaps a casual read would miss; flags, no verdict. Its inputs: the trail and
the evidence each row points at (an evidence-pointer review), or, when your caller names a
verified record, the trail and that record (a full audit). With no other family, ask the
owner to approve the same family, as `delegation` says. Declined, or no agent can run,
including inside a delegated task whose brief forbids one: `not reviewed` with the reason.
Never review your own run. A delegate reports the review as owed to its parent.

**Attention.** End the reply with this section; a calling playbook's reply ends with it
verbatim on every exit after the trail opened.

- `reviewed by <model>`, `reviewed by <model>, same family, approved`, or `not reviewed`
  with its reason.
- Each flag with its rows, or `no flags`.
- After an evidence-pointer review: `transcript coverage and unlogged-fork detection unavailable`.
