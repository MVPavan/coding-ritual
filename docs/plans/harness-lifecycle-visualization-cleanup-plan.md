# Harness Lifecycle Visualization Cleanup Plan

## Goal

Consolidate presentation artifacts under `harness_lifecycle/visualizations/`
and create a self-contained dashboard for thorough review of the focused
`agent-skills`, `mattpocock_skills`, and `superpowers` synthesis.

Origin: user request on 2026-07-15 and Beads issue `cr-m3q`.

## Scope

Move the visualization stack out of the `harness_lifecycle/` root:

- `dashboard.py`, `dashboard.html`, `dashboard.csv`, and
  `dashboard-note.html` become the regenerable lifecycle overview under
  `visualizations/lifecycle-overview/`.
- `capability_usefulness.html` becomes an explicitly historical artifact under
  `visualizations/archive/`; it remains the 868-row dual-model snapshot and is
  not relabeled as current.

Create:

- `visualizations/index.html` and `visualizations/README.md`
- `visualizations/focused-three-harnesses/generate.py`
- `visualizations/focused-three-harnesses/index.html`
- `visualizations/focused-three-harnesses/review-table.csv`

Keep canonical lifecycle inputs at their current paths:

- `capability_usefulness.csv`
- `catalogs/`, `codex_analysis/`, and `fable_analysis/`
- `aliases.json`, `ledger.json`, `scan.py`, and `gap.py`

Do not change capability judgments, cluster recommendations, exclusions, or
ledger decisions.

## Execution

### 1. Preserve And Relocate Existing Visualizations

Move existing files without discarding their current working-tree content.
Update the lifecycle generator's imports, data roots, output defaults, note
path, visible regeneration command, and CSV filename for its new location.

Verification:

- no visualization HTML, dashboard backing CSV, note fragment, or dashboard
  generator remains directly under `harness_lifecycle/`;
- the moved generator still reads canonical catalogs, ledger, Beads, and local
  harness sources from their existing locations;
- regeneration produces `index.html` and `inventory.csv` in the lifecycle
  overview folder.

### 2. Focused Review Dashboard Tracer Bullet

Read `codex_analysis/focused-three-harnesses/scope.json`, `clusters.json`, and
`row_evaluations.jsonl`. Assert the verified 97 unique rows, 94 included rows,
three exclusions, and 30 clusters before rendering anything.

Render a standalone dashboard-preset HTML artifact with:

- KPI tiles for scope and recommendation totals;
- inline SVG charts for decisions, priorities, source repositories, kinds,
  row verdicts, and cluster sizes;
- a visible review shortlist for P1, adapt, defer, and rejected clusters;
- search plus decision, priority, and source-harness filters;
- an expandable complete table containing all 30 clusters, all 94 source IDs,
  recommendations, merge/adaptation plan, scores, and risks;
- explicit display of the three prior exclusions;
- a deterministic `review-table.csv` with one row per focused cluster.

The HTML must use inline CSS and JavaScript, system fonts, no network fetches,
dark-mode support, mobile single-column behavior, and useful no-JavaScript
content.

### 3. Navigation And Documentation

Create a small visualization index that labels the focused dashboard as the
current review surface, the lifecycle overview as the inventory surface, and
the 868-row capability triage as historical. Add regeneration commands and
source-of-truth boundaries to `visualizations/README.md` and
`harness_lifecycle/README.md`.

Update live documentation references affected by the moves. Preserve
historical analytical evidence unless it functions as an operational path.

### 4. Review And Verification

Run spec review, code-quality review, and visual inspection. Verify:

- both Python generators compile and run successfully;
- focused counts and source coverage match the existing read-only verifier;
- generated HTML contains viewport metadata, inline CSS/JS, dark-mode and
  mobile rules, no external URLs, and the complete 30-cluster table;
- generated CSV has 30 unique cluster rows and stable columns;
- lifecycle overview generation still succeeds in its new path;
- JSON/JSONL source artifacts and ledger hashes remain unchanged;
- moved historical HTML is byte-identical to its pre-move content;
- no machine-local paths or trailing whitespace are introduced;
- reference submodules remain clean and `git status` is inspected.

## Risks And Invariants

- The worktree already contains user-owned lifecycle changes. Moves must retain
  them rather than regenerating from an older Git version.
- The focused dashboard is a review aid, not a new source of truth. Its source
  remains the verified focused synthesis JSON/JSONL bundle.
- The historical capability HTML must not be mistaken for the current 907-row
  Codex-only-expanded CSV.
- Generated HTML must remain usable from `file://` with JavaScript disabled;
  filters and search are progressive enhancement.
- Cleanup applies only to presentation artifacts; canonical data and analysis
  directories stay stable.
