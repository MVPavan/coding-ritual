<!-- BD:GENERATED START -->
# Backlog (parked, vetted)
_generated from bd @ 2026-09-11T21:16:18Z — DO NOT EDIT (run: BD_RENDER=1 bash <beads-skill-dir>/scripts/bd-render-tracking.sh)_
- `cr-o85.18` phase-5: a §8.1 continuation's §5.4 precondition resets away the steered runner's uncommitted work (R1 consequence, probed)
- `cr-o85.17` phase-5: run.jsonl is runner-writable by construction, and scan_log reads a session id and usage back out of it (R7)
- `cr-o85.16` phase-5: the git config keys that name a program are pinned by name, and the name space is open (R2 residual)
- `cr-o85.15` phase-5: codex cannot pre-assign a session id, against §5.2 (probe finding 6)
- `cr-o85.12` phase-5: ProfileConfig is a frozen BaseModel, not pydantic-settings (flag 11)
- `cr-o85.10` phase-5: a bounded reviewer needs two roots, TaskSpec gives one cwd (flag 9)
- `cr-o85.9` phase-5: TaskSpec.token_budget is tokens, claude's budget flag is --max-budget-usd (flag 8)
- `cr-o85.3` bdio: two closers on one activation are last-writer-wins inside the same §0.3 cooperative window (Opus#18, r4; api.py close_activation — both closes pass the is_settled guard on their own read, and the second merge overwrites the first outcome; bd has no compare-and-set, so the residue is documented §0.3 behaviour rather than a defect; probe scratchpad/probes/p3-r4-probes/probe_a_close_merge_window.py)
- `cr-o85.2` bdio: repair_forward's own read-modify-write window can undo a write that landed between the read-back and the repair (Opus#17, r4; transitions.py:217 — decides the terminal lifecycle from the merge's read-back snapshot, then issues a SECOND bd update; a §3.2 supersede landing in between is written over by a decision taken before it existed; probe scratchpad/probes/p3-r4-probes/probe_d_repair_forward_race.py)
- `cr-o85.1` bdio: record_dispatch should refuse without a recorded §3.2 precondition trio (phase-2 test surface change)
- `cr-a0n` bdio: package modules reach into BdClient._merge_metadata / _create_bead / _close_bead
- `cr-zaj` supervisor: ExitObserver reaches PinOutcome.REFUSED indirectly
- `cr-l17` supervisor: Monitor.watch holds on INDETERMINATE with no ceiling
- `cr-too` bdio: recorded_precondition raises a raw ValidationError on an out-of-band trio
<!-- BD:GENERATED END -->

<!-- Human notes below this line are preserved across renders. Everything above is bd-generated; do not hand-edit it. -->
