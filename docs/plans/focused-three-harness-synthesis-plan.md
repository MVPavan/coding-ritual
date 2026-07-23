# Focused Three-Harness Synthesis Plan

## Goal

Produce a Codex synthesis using only capabilities whose canonical provenance
includes `agent-skills`, `mattpocock_skills`, or `superpowers`. Preserve the
existing all-harness analysis and do not convert recommendations into adoption
ledger decisions.

Origin: user request on 2026-07-15 and Beads issue `cr-0gx`.

## Scope And Counts

The exact semicolon-delimited provenance filter yields:

- `agent-skills`: 44 canonical rows
- `mattpocock_skills`: 36 canonical rows
- `superpowers`: 19 canonical rows
- unique union: 97 canonical rows
- synthesis-eligible deep evaluations: 94 rows
- prior both-rejected exclusions: 3 rows
- occupied existing problem clusters: 30

The three explicit exclusions are `skill:migratetoshoehorn`,
`skill:setupmattpocockskills`, and `skill:setupprecommit`.

Create a separate focused bundle under
`harness_lifecycle/codex_analysis/focused-three-harnesses/` containing:

- `scope.json`
- `row_evaluations.jsonl`
- `clusters.json`
- `cluster_review.md`
- `final_synthesis.md`
- `run-notes.md`

Add a read-only verifier under `harness_lifecycle/codex_analysis/tools/`.

Do not modify:

- `harness_lifecycle/capability_usefulness.csv`
- the existing top-level all-harness artifacts in
  `harness_lifecycle/codex_analysis/`
- `harness_lifecycle/codex_analysis/excluded_both_rejected.jsonl`
- `harness_lifecycle/ledger.json`
- `harness_lifecycle/fable_analysis/`
- any reference submodule contents

## Execution

### 1. Deterministic filter

Filter exact harness tokens rather than substrings. Deduplicate by canonical
source ID, retain the order of the global deep-evaluation JSONL, and record the
97-row inventory plus the three excluded IDs in `scope.json`.

Verification:

- per-repository counts are 44, 36, and 19;
- the union is 97 IDs;
- exactly 94 IDs occur in the global deep evaluations;
- exactly three IDs occur only in the historical exclusion set;
- focused row objects are byte-for-byte equivalent as JSON objects to their
  global deep-evaluation source rows.

### 2. Focused cluster synthesis

Retain the existing primary problem-cluster assignment for each eligible row,
but remove every out-of-scope source from focused membership. Recompute all
derived fields from the 94 selected rows. Rewrite each cluster's qualitative
recommendation using only its in-scope evidence; do not copy an all-harness
decision or rationale without checking that the selected candidates support it.

Luna, Terra, and Sol each review a disjoint ten-cluster slice. They write only
their assigned scratch result. The coordinator validates schemas, reconciles
judgments, and owns the canonical focused bundle.

Every focused cluster must state:

- recommended capability and surface;
- focused decision and priority;
- problem solved;
- why the selected candidates support the recommendation;
- reuse or merge plan;
- risks or open questions;
- selection mode.

### 3. Render traceable outputs

Render `cluster_review.md` and `final_synthesis.md` from the focused cluster
objects. Every recommendation must list every selected source ID and source
name used by that recommendation. Record counts, assumptions, and exclusions
in `run-notes.md`.

### 4. Review And Verification

Run spec review followed by code-quality/adversarial review. Verify:

- 94 unique focused evaluations appear exactly once across 30 clusters;
- no source outside the three requested harnesses appears;
- the three excluded rows are recorded but not silently promoted;
- derived counts, kinds, verdicts, candidate keys, averages, and best sources
  match row data;
- rendered Markdown exactly matches focused cluster JSON;
- JSON and JSONL parse, the verifier compiles, stored paths are repo-relative,
  and focused files have no trailing whitespace;
- hashes of the canonical CSV, ledger, exclusion artifact, and existing
  all-harness synthesis artifacts remain equal to their pre-run snapshots;
- reference submodules remain clean;
- Beads closes only after fresh verification and `git status` inspection.

## Risks And Assumptions

- A shared canonical row is in scope when any requested harness appears in its
  provenance; its recommendation is still based on the canonical row-level
  evidence rather than pretending the other provenance never existed.
- Prior deep scores and row verdicts are reused; this run changes synthesis
  scope, not row-level judgments.
- Existing cluster IDs are problem-space anchors, not adoption decisions.
- The focused bundle is the requested synthesis for this scope; the top-level
  668-row synthesis remains the historical all-harness reference.
