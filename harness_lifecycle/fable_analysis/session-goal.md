# Goal: Analyze Harness Capability Usefulness (Fable X-high replication)

## Objective

Independently re-run the full capability-usefulness analysis of
`harness_lifecycle/capability_usefulness.csv` using **Fable 5 at xhigh reasoning
effort** as both coordinator and workers, producing a complete, traceable
synthesis of which external harness capabilities are worth adopting, merging,
rewriting, deferring, or rejecting for this repo's harness.

This is a parallel counterpart to `harness_lifecycle/codex_analysis/` (which used
Codex / GPT-5.5). The **methodology is identical** — the authoritative spec is
`harness_lifecycle/codex_analysis/session-goal.md`. This file records only the
deltas and the artifact contract, so the two analyses are directly comparable.

## Deltas from the Codex spec

- **Model:** Fable 5, xhigh effort, for every row-evaluation worker and for all
  coordinator judgment (clustering, cluster review, synthesis).
- **Output directory:** `harness_lifecycle/fable_analysis/` (not `codex_analysis/`).
- **Service tier / "fast mode":** not applicable — fast mode is a Codex-only tier.
  Fable xhigh is the effort lever; there is no tier to set.
- **Same input, same inclusion rule, same 11-shard plan, same per-item schema** as
  the Codex run, so a per-row and per-cluster Fable-vs-Codex diff is meaningful.

## Inclusion rule (unchanged)

- Exclude rows where `fable_useful == no` AND `gpt_useful == no` (audited in
  `excluded_both_rejected.jsonl`).
- Deep-analyze every row where at least one model said useful.
- Never discard an included row during clustering or synthesis; preserve source IDs.
- Total 868 · included 629 · excluded 239.

## Per-item evaluation (unchanged schema)

Each included row → one JSON object with: `source_id`, `kind`, `category`, `name`,
`harnesses`, `fable_useful`, `fable_reason`, `fable_tag`, `gpt_useful`,
`gpt_reason`, `gpt_tag`, `consensus`, `agree`, `description`, `problem_solved`,
`actual_usefulness_verdict` ∈ {adopt, merge, rewrite, defer, reject_after_review},
`rationale`, `overlap_with_existing`, `candidate_cluster_key`, `evidence_notes`,
and 1–5 scores for `effectiveness`, `instruction_quality`, `clarity`, `precision`,
`concision`, `structural_efficiency`.

Workers inspect the real source file(s) listed in each row's `source_paths` when
the CSV is ambiguous or when judging overlap with existing local capabilities.

## Artifacts (all under `harness_lifecycle/fable_analysis/`)

`session-goal.md` · `session-board.md` · `run-notes.md` ·
`excluded_both_rejected.jsonl` · `shard_manifest.json` · `shards/<id>.input.jsonl`
· `shards/<id>.row_evaluations.jsonl` · `shards/<id>.notes.md` ·
`row_evaluations.jsonl` (629) · `clusters.json` · `cluster_review.md` ·
`final_synthesis.md`. Optionally `fable_vs_codex_diff.md`.

## Completion criteria (unchanged)

`included + excluded == 868`; every included row has one eval in
`row_evaluations.jsonl`; every included id appears in exactly one primary cluster;
cluster review complete; `final_synthesis.md` recommendation table present; no
excluded id in evals; every final-synthesis source id exists in evals; fresh
verification recorded in `run-notes.md`.
