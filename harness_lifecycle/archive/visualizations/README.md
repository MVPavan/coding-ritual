# Harness Lifecycle Visualizations

Human-facing lifecycle views live here. Canonical CSV, JSON, JSONL, ledger, and
analysis files remain one level up; generated pages are review aids, not sources
of truth.

Open [`index.html`](index.html) for the local contents page.

## Current Views

| View | Purpose | Source | Regenerate |
|---|---|---|---|
| `lifecycle-overview/index.html` | All-reference inventory, coverage, gap, and Beads overview | `catalogs/`, local harness surfaces, ledger, and Beads | `python3 harness_lifecycle/visualizations/lifecycle-overview/generate.py` |

The generator is standard-library Python. Its HTML is self-contained, works from
`file://`, and performs no network requests. It also writes `inventory.csv`.

## What used to be here

`focused-three-harnesses/` and the 868-row triage snapshot moved to
[`../archive/`](../archive/). Both answered "which reference skills should we
take?" — a question the [casebook](../casebook/README.md) now answers with
current verdicts and their reasoning. They are kept for audit context only; do
not read either as a current recommendation.

## Source-Of-Truth Boundary

- `harness_lifecycle/inventory/*.csv` is the canonical per-kind capability table.
- `harness_lifecycle/casebook/` owns per-skill adopt/reject rulings and history.
- `harness_lifecycle/ledger.json` owns explicit gap-report adoption decisions.
- Nothing under `visualizations/` updates the ledger or analysis judgments.
