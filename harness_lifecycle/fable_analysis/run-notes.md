# Run Notes — Fable analysis

## Execution summary

- Parsed `harness_lifecycle/capability_usefulness.csv`: 868 data rows.
- Included 629 (≥1 shallow "yes"); excluded 239 (both "no") → `excluded_both_rejected.jsonl`.
- 25 worker shards (~22–27 rows each; finer than codex_analysis's 11 for worker-context
  safety — comparability is by `source_id`, not shard shape).
- Merged row evaluations: 629 in `row_evaluations.jsonl`, every row provenance-stamped.
- Primary clusters: 41 in `clusters.json` (consolidation mapping recorded in
  `tools/build_clusters.py`); review in `cluster_review.md`; recommendations in
  `final_synthesis.md`; codex comparison in `fable_vs_codex_diff.md`.

## Who evaluated what (important)

| evaluator | rows | shards |
| --- | --- | --- |
| Fable 5 xhigh subagents (wave 1, 2026-07-06) | 148 | skill-7/8/9, rule-1, plugin-mcp-1/2 |
| Codex **GPT-5.6-Sol** xhigh workers (2026-07-10) | 481 | the remaining 19 shards |

The original plan was all-Fable workers. Wave 1 lost 19 of 25 shards to the Claude
session limit; a Jul 10 retry lost all 19 again (window pre-drained). The user then
directed the pivot: row evaluation by Codex GPT-5.6-Sol xhigh workers, with Fable
(the coordinator) reviewing outputs. Fable owns: shard plan, worker contract, output
review (rule-2 smoke + cross-kind spot checks), consolidation mapping, cluster
decisions, final synthesis, and this verification. Per-row `evaluated_by` records
provenance; `fable_vs_codex_diff.md` restates the caveat.

## Counts

Row verdicts (629): adopt 73 · merge 138 · rewrite 62 · defer 68 · reject_after_review 288.
Average scores: effectiveness 3.01 · instruction_quality 3.43 · clarity 4.24 ·
precision 3.28 · concision 3.42 · structural_efficiency 3.25.

Cluster decisions (41): merge 13 · adopt_as_is 8 · adapt 3 · defer 9 · reject_after_review 8.
Priorities: P0 3 (C01 review lenses, C12 security review, C24 curation stocktake) ·
P1 13 · P2 12 · P3 13.

Codex comparison (629 common rows): 48% exact verdict agreement, 72% within one
step, 107 divergences ≥3 steps.

## Assumptions and surprises

- **Session limits, twice:** wave 1 (Jul 6) and the Jul 10 retry both died on Claude
  session limits; the incremental-write instruction preserved wave-1 output files.
- **Codex usage limit too:** the GPT-5.6-Sol fan-out lost 7 shards to the ChatGPT
  usage cap (reset 10:15 UTC); the idempotent driver re-ran exactly the missing rows.
- **Model correction mid-run:** user directed `gpt-5.6-sol` (the only 5.6 variant this
  ChatGPT account accepts); a killed gpt-5.5 attempt wrote zero rows, so provenance is clean.
- **`/tmp` scratch wiped between sessions** — analysis tooling was moved into
  `fable_analysis/tools/` (repo-relative) so the audit trail survives.
- **Foreground `sleep` is blocked in this harness**: an auto-resume chained with `;`
  ran the driver immediately into the still-active limit and burned an hour of retries.
- **Stale `source_paths`** (mirror trees, upstream deletions): workers recovered by
  Glob/Grep and in one case read a deleted file from the pinned commit
  (`agent:designimplementationreviewer`).
- `skill-8.notes.md` is a coordinator-authored stub: the worker died after writing
  all 27 evaluations but before its notes (documented, not reconstructed).
- Token profile of codex workers (measured): ~1.4–1.9M input/shard, ~85–90% cached —
  the cost is per-turn context replay across ~50 tool calls, not the file reading itself.

## Verification evidence (fresh, 2026-07-10)

Deterministic checks, all PASS after the skill-8 stub:

```
PASS total==868
PASS included(629)+excluded(239)==total
PASS merged==629
PASS shard_unique_rows==629            (each included id in exactly one shard)
PASS clusters==41
PASS cluster_ids==629_unique           (each id in exactly one primary cluster)
PASS no_excluded_in_evals
PASS synthesis_best_ids_exist          (all representative ids exist in row evals)
PASS notes_files==25
COVERAGE: PASS (merge_and_verify.py)   CLUSTER COVERAGE: PASS (build_clusters.py)
```

`git status --short`: only new/modified analysis artifacts under
`harness_lifecycle/fable_analysis/` plus pre-existing unrelated changes
(`.beads/*`, `.claude/commands/use-codex.md`, `.claude/project/learnings.md`,
`codex_analysis/*` from the earlier goal run, `mvp-harness`, `reference_harnesses/agent-skills`).
Nothing committed — commits await explicit user request per repo git-safety rules.
