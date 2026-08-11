# Codex Analysis Session Board

This board is the coordinator-owned control surface for the goal run defined in
`harness_lifecycle/codex_analysis/session-goal.md`. It is not the harness
lifecycle dashboard. Keep it current during the run so the analysis can be
resumed, audited, or handed off without guessing what happened.

## Goal

Evaluate `harness_lifecycle/capability_usefulness.csv` end to end, using
parallel subagents for row-level analysis and a coordinator-owned merge,
clustering pass, final synthesis, and verification.

## Runtime Contract

Coordinator: the goal-running Codex session.

Subagents must be launched with:

- Model: same as coordinator goal session.
- Reasoning effort: same as coordinator goal session.
- Service tier / execution mode: fast mode.
- Scope: assigned source IDs only.
- Write access: unique files under `harness_lifecycle/codex_analysis/shards/` only.

Before launching workers, record the actual model, effort, and service-tier
settings here. If the tool does not expose service-tier controls, record that
fact and include the fast-mode requirement in each worker prompt.

Launch control note: the coordinator attempted to launch a worker with
`service_tier=fast`, but the subagent tool rejected it for the inherited
`gpt-5.5` model and reported that only `priority` is supported. Workers are
therefore launched with inherited model and effort, no explicit model or effort
downgrade, and the fast-mode requirement included in each worker prompt.

Incremental reconciliation note (2026-07-15): Luna reviewed the 24-skill slice
and Sol reviewed the 20 non-skill slice using inherited coordinator settings.
The collaboration surface did not expose independent model, reasoning-effort,
or service-tier overrides. Terra audited the canonical mapping and implemented
the deterministic mapping and verification checks. The coordinator retained
ownership of the CSV merge, cluster reconciliation, synthesis, and final
verification. Final code review narrowed the helper to read-only verification.

## CSV Snapshot

Snapshot from the current CSV:

| Metric | Count |
|---|---:|
| Total rows | 907 |
| Included rows | 668 |
| Excluded rows | 239 |

Included rows by kind:

| Kind | Included rows |
|---|---:|
| skill | 261 |
| command | 129 |
| agent | 109 |
| hook | 74 |
| plugin | 43 |
| rule | 43 |
| mcp | 9 |

The coordinator must recompute these counts at goal-run start. If they differ,
update this board before spawning subagents.

## Shard Plan

Initial plan based on the current CSV. Status values: `planned`, `launched`,
`complete`, `blocked`, `merged`.

Preflight and incremental reconciliation status: complete. The coordinator wrote
`excluded_both_rejected.jsonl`, `shard_manifest.json`, and scoped shard input
files under `shards/`. The historical exclusion artifact remained byte-identical.

| Shard ID | Rows | Assignment | Status | Worker settings | Output |
|---|---:|---|---|---|---|
| skill-1 | 60 | Included skill rows, first shard | complete | Worker Ohm `019f37ac-53a0-7b60-a38f-b3103fd5f5fc`; inherited model, inherited effort, fast requested in prompt; API rejected explicit `service_tier=fast` | `shards/skill-1.row_evaluations.jsonl` |
| skill-2 | 60 | Included skill rows, second shard | complete | Worker Faraday `019f37ac-545b-7b20-ad35-df5a8ce1671b`; inherited model, inherited effort, fast requested in prompt; API rejected explicit `service_tier=fast` | `shards/skill-2.row_evaluations.jsonl` |
| skill-3 | 60 | Included skill rows, third shard | complete | Worker Helmholtz `019f37ac-5503-7580-9271-83f1fd422792`; inherited model, inherited effort, fast requested in prompt; API rejected explicit `service_tier=fast` | `shards/skill-3.row_evaluations.jsonl` |
| skill-4 | 58 | Included skill rows, fourth shard | complete | Worker Singer `019f37ac-55fa-7a10-8cf7-75ea9da1bd6b`; inherited model, inherited effort, fast requested in prompt; API rejected explicit `service_tier=fast` | `shards/skill-4.row_evaluations.jsonl` |
| agent-1 | 54 | Included agent rows, first shard | complete | Worker Locke `019f37ac-56aa-7363-9e21-a99ce8733467`; inherited model, inherited effort, fast requested in prompt; API rejected explicit `service_tier=fast` | `shards/agent-1.row_evaluations.jsonl` |
| agent-2 | 54 | Included agent rows, second shard | complete | Worker Poincare `019f37ac-57d4-7303-a28e-fadeb3b0f3a3`; inherited model, inherited effort, fast requested in prompt; API rejected explicit `service_tier=fast` | `shards/agent-2.row_evaluations.jsonl` |
| plugin-mcp-1 | 51 | Included plugin and MCP rows | complete | Worker Turing `019f37b1-cc98-7e93-8ff7-7ee76ac7dfdc`; inherited model, inherited effort, fast requested in prompt; API rejected explicit `service_tier=fast` | `shards/plugin-mcp-1.row_evaluations.jsonl` |
| rule-1 | 42 | Included rule rows | complete | Worker Averroes `019f37b1-ccfc-7b91-8f5d-8240ed30c788`; inherited model, inherited effort, fast requested in prompt; API rejected explicit `service_tier=fast` | `shards/rule-1.row_evaluations.jsonl` |
| hook-1 | 68 | Included hook rows | complete | Worker Banach `019f37b1-cde8-7a91-a864-b1825ef2cf48`; inherited model, inherited effort, fast requested in prompt; API rejected explicit `service_tier=fast` | `shards/hook-1.row_evaluations.jsonl` |
| command-1 | 61 | Included command rows, first shard | complete | Worker Halley `019f37b1-cf6c-73c2-a4f4-9fe5e834af56`; inherited model, inherited effort, fast requested in prompt; API rejected explicit `service_tier=fast` | `shards/command-1.row_evaluations.jsonl` |
| command-2 | 61 | Included command rows, second shard | complete | Worker Nietzsche `019f37b2-433a-78c2-a37b-4141f2035547`; inherited model, inherited effort, fast requested in prompt; API rejected explicit `service_tier=fast` | `shards/command-2.row_evaluations.jsonl` |
| agent-skills-skills | 23 | New skill rows; existing TDD refreshed in skill-2 | complete | Luna; inherited coordinator settings | `shards/agent-skills-skills.row_evaluations.jsonl` |
| agent-skills-other | 16 | New non-skill rows; four existing rows refreshed in historical shards | complete | Sol; inherited coordinator settings | `shards/agent-skills-other.row_evaluations.jsonl` |

## Artifact Checklist

| Artifact | Owner | Status | Notes |
|---|---|---|---|
| `session-goal.md` | coordinator | ready | Goal instructions. |
| `session-board.md` | coordinator | ready | Update throughout the run. |
| `excluded_both_rejected.jsonl` | coordinator | complete | 239 historical exclusions preserved byte-identically. |
| `shard_manifest.json` | coordinator | complete | Exact 13-shard counts, source ID boundaries, and input/output paths. |
| `shards/*.input.jsonl` | coordinator | complete | Scoped rows; five existing records refreshed in their historical owners. |
| `shards/*.row_evaluations.jsonl` | subagents | complete | 13 of 13 shard JSONL files validated. |
| `shards/*.notes.md` | subagents | complete | 13 of 13 notes files present. |
| `row_evaluations.jsonl` | coordinator | complete | 668 included rows merged from validated shard JSONL files. |
| `clusters.json` | coordinator | complete | 75 primary clusters covering 668 included source IDs exactly once. |
| `cluster_review.md` | coordinator | complete | Human-readable review row for every primary cluster. |
| `final_synthesis.md` | coordinator | complete | Final recommendation table with every included source ID listed. |
| `run-notes.md` | coordinator | complete | Execution log, assumptions, counts, and verification notes. |

## Reconciliation Checks

Record final numbers here after verification:

| Check | Expected | Actual | Status |
|---|---:|---:|---|
| included + excluded == total CSV rows | 907 | 907 | pass |
| included rows == merged row evaluations | 668 | 668 | pass |
| included rows == unique shard source IDs | 668 | 668 | pass |
| included rows == unique primary cluster source IDs | 668 | 668 | pass |
| excluded rows absent from row evaluations | 239 | 239 | pass |

## Open Risks

- Explicit `service_tier=fast` was not supported for the inherited model by the
  subagent API. The coordinator recorded the rejection and included the
  fast-mode requirement in each worker prompt while preserving inherited model
  and effort.
- Cluster quality remains a judgment artifact. The coordinator reconciled the
  new candidate keys into 75 primary clusters and preserved every source ID for
  audit; no new primary cluster was necessary.
- New rows have Codex-only screening sentinels. Historical Fable judgments were
  preserved and must not be read as evaluations of the new source variants.
- Shard JSONL inputs and outputs remain intentionally gitignored local audit
  intermediates; merged canonical records and shard notes are the durable
  repository artifacts.
