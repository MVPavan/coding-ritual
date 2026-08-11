# Session Board — Fable X-high capability analysis

Control surface for the Fable replication of `codex_analysis`. Coordinator owns all
merged/final artifacts; workers write only their own shard files.

## Launch settings

- **Worker model / effort:** Fable 5 · xhigh · agentType `general-purpose` (Read/Grep/Glob/Write).
- **Service tier:** N/A (fast mode is Codex-only; not applicable to Fable).
- **Orchestration:** Workflow fan-out, one worker per shard, concurrency-capped (~2 waves).
- **Input:** `harness_lifecycle/capability_usefulness.csv` (868 rows) — read-only.
- **Worker contract:** deep per-row eval; inspect `source_paths`; same schema as codex.

## Preflight (done)

- total 868 · **included 629** · **excluded 239** (`excluded_both_rejected.jsonl`).
- included by kind: skill 238 · command 122 · agent 108 · hook 68 · plugin 42 · rule 42 · mcp 9.
- 629/629 rows enriched with ≥1 resolvable `source_paths` entry.
- **25 shards** (~22–27 rows each), finer than codex's 11 for worker-context safety
  (comparability is by `source_id`, not by shard). See `shard_manifest.json`.

## Phase status

| Phase | State |
| --- | --- |
| Preflight (split, exclude, shard) | ✅ done |
| Worker shape validation (5-row test) | ✅ done — schema-conformant, source files read |
| Row-eval workers wave 1 (25 shards, Jul 6) | ⚠️ session-limit killed 19; **6 shards / 148 rows landed valid** (skill-7/8/9, rule-1, plugin-mcp-1/2) |
| Row-eval workers wave 2 (19 missing shards, Jul 10) | ❌ session-limit again at launch (~08:04 UTC; window pre-drained); 0 rows landed |
| **Pivot (user-directed):** remaining 481 rows → **Codex GPT-5.6-Sol xhigh workers** (per-row `evaluated_by` provenance), Fable (coordinator, main thread) reviews outputs | ✅ 481/481 landed across 19 shards (survived one Codex usage-limit window); quality reviewed & approved |
| Merge → `row_evaluations.jsonl` + coverage verify | ✅ 629/629, COVERAGE PASS (adopt 73 · merge 138 · rewrite 62 · defer 68 · reject 288) |
| Clustering → `clusters.json` (Fable judgment) | ✅ 445 raw keys → 41 primary clusters, CLUSTER COVERAGE PASS (mapping in `tools/build_clusters.py`) |
| `cluster_review.md` (Fable) | ✅ 41 entries with decisions |
| `final_synthesis.md` (Fable) | ✅ 41 recommendations: merge 13 · adopt_as_is 8 · adapt 3 · defer 9 · reject 8; P0×3 P1×13 P2×12 P3×13 |
| `run-notes.md` + verification | ✅ all completion checks PASS (see run-notes) |
| `fable_vs_codex_diff.md` | ✅ 629 common rows: 48% exact, 72% within-1, 107 sharp divergences |

## Open risks

- Some CSV descriptions are thin/placeholder; workers fall back to source inspection
  or score lower with defer/reject where evidence is weak.
- A few `source_paths` may be stale (mirror trees); workers Glob/Grep by name as fallback.
- Cross-shard `candidate_cluster_key` naming will vary; coordinator consolidates into
  primary clusters before synthesis.
