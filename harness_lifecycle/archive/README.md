# archive

Retired lifecycle artifacts. Kept for audit context — **never** read anything
here as a current capability count, recommendation, or adoption decision.

Nothing in the live lifecycle reads this directory. The generators here are not
maintained and their hardcoded input paths no longer resolve after the move.

| Item | What it was | Superseded by |
|---|---|---|
| `codex_analysis/` | Per-row usefulness evaluation of every reference capability, sharded across Codex workers | `registry/ledger/` |
| `fable_analysis/` | The parallel Fable run of the same evaluation, plus `fable_vs_codex_diff.md` | `registry/ledger/` |
| `visualizations/focused-three-harnesses/` | Review dashboard over `codex_analysis/focused-three-harnesses/` | `registry/references/` |
| `visualizations/lifecycle-overview/` | All-harness inventory, coverage and gap dashboard | `registry/` |
| `visualizations/capability-usefulness-868.html` | 868-row Fable-vs-GPT triage page | `registry/references/` |
| `capability_usefulness-2026-08-11.csv` | Flat export of that triage | `registry/ledger/` |
| `casebook/` | Append-only curation record 2026-08-11 to 2026-08-21: sealed rounds 001–008, bucket views, `casebook.py` | `registry/ledger/` (its migration round) |
| `inventory/skill-buckets.md` | The 14-bucket taxonomy of the 84 reference skills | registry coordinates (`registry/README.md` §2) |
| `catalogs/` | Catalogs of removed submodules: claude-plugins-official, compound-engineering-plugin, everything-claude-code | — |

## Why these were retired

The analysis directories and the review pages built on them all answered one
question: *which reference capabilities are worth taking?* The registry ledger
now answers it better — one ruling per skill, reasoning attached, appended rather
than overwritten, and re-checkable against upstream by `content_hash`. Keeping
two answers to the same question means one of them is quietly wrong.

Their verdicts also predate the round-001 council consolidation and the round-002
UI scope cut, so they disagree with current rulings by design.

The dashboards were dropped separately: they were read-only review aids with no
consumer in the command surface, and their numbers went stale silently whenever
a submodule pin moved.

## Deleting

Safe to delete outright — git history preserves all of it. Retained only until
the registry has survived a second real sync round.
