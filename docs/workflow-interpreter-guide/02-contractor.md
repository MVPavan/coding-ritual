# 02 — Contractor

The command the LLM orchestrator runs. One work item in, one JSON result out.

```
foreman contract <epic_id> <stage_id> [--retry] [--retry-landing] [--trace] [--monitored]
```

Two positional arguments, four flags. That is the entire surface.

## What one call does, in order

1. **Selects and validates.** The stage must be a direct child of the epic. Then
   `repair_contractor_successor` heals any half-finished replacement lineage.
2. **Checks phase state.** Every direct stage closed and this one has no record →
   `phase-exhausted`. Open blocking dependencies → `blocked` with their ids. Another
   unclosed stage already holding a record → also blocked.
3. **Admits.** Reads the task brief from the bead description, pins the verification
   policy, captures the coordinator's `HEAD` as the expected base, instantiates the
   graph as a root, writes the `contractor` record onto the bead.
4. **Runs.** Calls `Foreman.run` and **blocks** until it stops — poll 30 s, wall
   limit 8 h. The call is long-lived, not fire-and-forget.
5. **Lands, only if the run ended at `shipped`.** Verifies exactly one closed,
   immutable, approved ship gate; fast-forwards the target ref by compare-and-swap;
   journals intent and receipt; writes the export.

## The other five things it can do

1. **`--trace`** — read-only. Blocking ids, stage closure, gate evidence, landing
   intent and the stored record, without admitting or running anything. The
   orchestrator's "what is the state of this stage?" call.
2. **Resume an admitted stage.** A second plain call on an `admitted` record resumes
   the existing root. The coordinator's `HEAD` must not have moved, or it refuses
   with `branch-moved` (`contractor/command.py:312-318`).
3. **Land an already-shipped stage.** A plain call on a record whose root reached
   `shipped` goes straight to landing, skipping the run.
4. **`--retry`** — attempt n+1: new root, new instance key, previous attempt recorded
   in `previous_attempts`. Refused on a coordinated root.
5. **`--retry-landing`** — retries landing alone against a stored pending intent.
   Refuses without one; cannot combine with an ordinary retry.

`--monitored` changes only how progress is reported, not the decision path.

## What comes back

One JSON object with a state and a distinct exit code. Six states:
`phase-exhausted`, `blocked`, `result`, `completed`, `recovered`, `refused`.

- `completed` is the only one meaning the work landed.
- `result` means the run stopped for a reason the orchestrator must read — usually an
  open gate.
- `refused` carries a `reason`, and for landing failures a `disposition` of
  `human-attention`.

## Stages within an epic are serial

Confirmed at `contractor/admission.py:240-257`. `_refuse_other_admission` walks every
direct child of the epic; if any *other* stage carries a `contractor` record and is
not closed, admission is refused as `blocked`, naming that stage.

Three consequences:

1. **Dependencies are a separate check.** Even with zero declared dependencies
   between two stages, the second cannot be admitted while the first is unfinished.
2. **The reason is git, not the graph.** Admission pins `expected_base_commit` from
   the coordinator's `HEAD`, and landing fast-forwards from that base. Two stages
   admitted at the same base would each land onto a ref the other moved.
   Serialization is how fast-forward-only stays true.
3. **The limit is per epic.** Two different epics can each have an unfinished stage.

Parallel stages would need a different landing story — per-stage integration branches
with a merge step, or a rebasing landing queue. The dormant coordination machinery in
[09-coordination.md](09-coordination.md) is the likely home for that.

## What it deliberately does not do

- Never decides what node runs next. That is entirely the foreman's.
- Never launches an agent or touches a worktree.
- Never approves a gate; it only verifies that a human already did.
- Does not clean up after a landed run — an explicit `foreman tick ROOT` is still
  needed, because the export that unblocks cleanup is written after `Foreman.run`
  returns and nothing ticks the root again.
