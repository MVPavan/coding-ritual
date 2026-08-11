# archive

Retired lifecycle artifacts. Kept for audit context — **never** read anything
here as a current capability count, recommendation, or adoption decision.

Nothing in the live lifecycle reads this directory. The generators here are not
maintained and their hardcoded input paths no longer resolve after the move.

| Item | What it was | Superseded by |
|---|---|---|
| `codex_analysis/` | Per-row usefulness evaluation of every reference capability, sharded across Codex workers | `casebook/rounds/` |
| `fable_analysis/` | The parallel Fable run of the same evaluation, plus `fable_vs_codex_diff.md` | `casebook/rounds/` |
| `visualizations/focused-three-harnesses/` | Review dashboard over `codex_analysis/focused-three-harnesses/` | `casebook/views/` |
| `visualizations/lifecycle-overview/` | All-harness inventory, coverage and gap dashboard | `gap.py`, `inventory/*.csv` |
| `visualizations/capability-usefulness-868.html` | 868-row Fable-vs-GPT triage page | `casebook/views/` |
| `capability_usefulness-2026-08-11.csv` | Flat export of that triage | `inventory/skill-buckets.csv` |

## Why these were retired

The analysis directories and the review pages built on them all answered one
question: *which reference capabilities are worth taking?* The casebook now
answers it better — one ruling per skill, reasoning attached, appended rather
than overwritten, and re-checkable against upstream by `content_hash`. Keeping
two answers to the same question means one of them is quietly wrong.

Their verdicts also predate the round-001 council consolidation and the round-002
UI scope cut, so they disagree with current rulings by design.

The dashboards were dropped separately: they were read-only review aids with no
consumer in the command surface, and their numbers went stale silently whenever
a submodule pin moved.

## Deleting

Safe to delete outright — git history preserves all of it. Retained only until
the casebook has survived a second real sync round.
