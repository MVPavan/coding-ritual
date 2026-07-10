# Run Notes

## Execution Summary

- Parsed `harness_lifecycle/capability_usefulness.csv`: 868 total data rows.
- Included rows: 629.
- Excluded rows: 239; written to `excluded_both_rejected.jsonl`.
- Subagent shard outputs: 11 JSONL files and 11 notes files under `shards/`.
- Merged row evaluations: 629 rows in `row_evaluations.jsonl`.
- Primary clusters: 75 in `clusters.json`.

## Counts

| Kind | Included Rows |
|---|---:|
| `skill` | 238 |
| `agent` | 108 |
| `plugin` | 42 |
| `mcp` | 9 |
| `rule` | 42 |
| `hook` | 68 |
| `command` | 122 |

| Row Verdict | Count |
|---|---:|
| `adopt` | 82 |
| `defer` | 126 |
| `merge` | 265 |
| `reject_after_review` | 113 |
| `rewrite` | 43 |

| Cluster Decision | Count |
|---|---:|
| `adapt` | 1 |
| `adopt_as_is` | 3 |
| `defer` | 17 |
| `merge` | 39 |
| `reject_after_review` | 15 |

| Priority | Count |
|---|---:|
| `P0` | 3 |
| `P1` | 12 |
| `P2` | 26 |
| `P3` | 34 |

## Assumptions And Surprises

- `bd prime` and `bd ready` could not be run because `bd` is not installed on PATH in this environment.
- The subagent API rejected explicit `service_tier=fast` for inherited `gpt-5.5`; the coordinator recorded this and included the fast-mode requirement in each worker prompt while preserving inherited model and effort.
- Several workers noted that project docs reference `my_harness/` while the live tree contains `mvp-harness/`; final overlap judgments rely primarily on live `.codex/` and `.claude/` assets plus visible repo files.
- Some CSV descriptions were placeholders or truncated; those rows remain preserved, with lower scores or defer/reject decisions where evidence was weak.
- `command` rows were processed after the known kind order, as required by the session goal.

## Verification Recorded

- Parsed CSV, shard JSONL files, merged JSONL, `clusters.json`, and final synthesis source IDs.
- Confirmed every included source ID appears in exactly one shard JSONL file and exactly one primary cluster.
- Confirmed excluded source IDs do not appear in row evaluations.
- Confirmed final synthesis source IDs all exist in row-level evaluations.

## Final Verification Evidence

- Coverage script: `PASS coverage: total=868 included=629 excluded=239 shards=11 shard_rows=629 merged=629 clusters=75 cluster_source_ids=629 final_ids=629`.
- Cluster decisions from the same script: `merge` 39, `adopt_as_is` 3, `defer` 17, `adapt` 1, `reject_after_review` 15.
- JSON parse checks passed for `clusters.json` and `shard_manifest.json`.
- JSONL parse checks passed for `excluded_both_rejected.jsonl`, `row_evaluations.jsonl`, every shard input JSONL, and every shard row-evaluation JSONL.
- Machine-local path scan over `harness_lifecycle/codex_analysis` produced no matches.
- Beads check: `bd ready` failed with `bd: command not found`; no Beads issue state was changed.
- Final `git status --short` showed only `harness_lifecycle/codex_analysis/session-goal.md` modified and new untracked analysis artifacts under `harness_lifecycle/codex_analysis/`.
