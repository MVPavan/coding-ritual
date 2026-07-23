# Harness Lifecycle Visualizations

Human-facing lifecycle views live here. Canonical CSV, JSON, JSONL, ledger, and
analysis files remain one level up; generated pages are review aids, not sources
of truth.

Open [`index.html`](index.html) for the local contents page.

## Current Views

| View | Purpose | Source | Regenerate |
|---|---|---|---|
| `focused-three-harnesses/index.html` | Thorough review of `agent-skills`, `mattpocock_skills`, and `superpowers` | `codex_analysis/focused-three-harnesses/` | `python3 harness_lifecycle/visualizations/focused-three-harnesses/generate.py` |
| `lifecycle-overview/index.html` | All-reference inventory, coverage, gap, and Beads overview | `catalogs/`, local harness surfaces, ledger, and Beads | `python3 harness_lifecycle/visualizations/lifecycle-overview/generate.py` |

Each generator is standard-library Python. Its HTML is self-contained, works
from `file://`, and performs no network requests. The focused generator also
writes `review-table.csv`; the lifecycle generator writes `inventory.csv`.

## Archive

`archive/capability-usefulness-868.html` is the historical 868-row Fable versus
GPT triage snapshot. It predates the Codex-only `agent-skills` expansion and is
retained only for audit context. Do not use it as the current capability count
or adoption recommendation.

## Source-Of-Truth Boundary

- `harness_lifecycle/capability_usefulness.csv` is the canonical shallow
  capability table.
- `harness_lifecycle/codex_analysis/` and `fable_analysis/` own analysis data.
- `harness_lifecycle/ledger.json` owns explicit adoption decisions.
- Nothing under `visualizations/` updates the ledger or analysis judgments.
