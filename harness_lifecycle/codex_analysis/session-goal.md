# Goal: Analyze Harness Capability Usefulness

## Objective

Analyze `harness_lifecycle/capability_usefulness.csv` end to end and produce a complete, traceable synthesis of which external harness capabilities are worth adopting, merging, rewriting, deferring, or rejecting for this repo's Codex/Claude harness.

Do not stop at row-by-row review. Preserve every relevant row, cluster similar capabilities, re-read each cluster, and produce higher-quality merged recommendations where multiple candidates solve the same problem.

## Source Data

Primary input:

- `harness_lifecycle/capability_usefulness.csv`

Supporting inputs, when needed to understand an item beyond the CSV description:

- `harness_lifecycle/catalogs/*.json`
- `harness_lifecycle/aliases.json`
- `harness_lifecycle/ledger.json`
- Existing local harness capabilities under `.codex/`, `.claude/`, and `my_harness/`
- Reference harness submodules under `reference_harnesses/` only as read-only sources

Do not modify the source CSV during this analysis.

## Inclusion Rules

For every CSV row:

- If `fable_useful == no` and `gpt_useful == no`, exclude it from deep analysis.
- Still preserve excluded rows in an exclusion artifact so they are auditable.
- If either `fable_useful == yes` or `gpt_useful == yes`, evaluate it thoroughly.
- Never discard an included row during clustering or synthesis. Merged outputs must retain source row IDs.

Priority within each capability kind:

1. Rows where both Fable and GPT say useful.
2. Rows where Fable says useful and GPT does not.
3. Rows where GPT says useful and Fable does not.

## Capability Kind Order

Process included rows in this order:

1. `skill`
2. `agent`
3. `plugin`
4. `mcp`
5. `rule`
6. `hook`

The current CSV also contains `command` rows. Because the objective is to avoid discarding any non-rejected result, process included `command` rows after `hook` unless the human explicitly narrows scope before execution.

If any other unexpected `kind` appears, preserve it, flag it in the run notes, and process it after the known kinds.

## Per-Item Evaluation

For each included row, understand what it is and what problem it solves. Use the CSV fields first, then inspect supporting inputs when the row is ambiguous or when judging overlap with existing local capabilities requires more evidence.

Evaluate each item on these dimensions:

- `effectiveness`: How well it solves a real, reusable harness problem.
- `instruction_quality`: Whether its instructions are actionable for an agent.
- `clarity`: Whether the intended trigger, behavior, and output are easy to understand.
- `precision`: Whether it avoids vague, overbroad, or conflicting guidance.
- `concision`: Whether it gives enough detail without wasting context.
- `structural_efficiency`: Whether its shape helps routing, progressive disclosure, reuse, and maintenance.

Use a 1-5 score for each dimension:

- `1`: poor; likely harmful or too vague to use.
- `2`: weak; useful idea but unclear, bloated, or hard to operationalize.
- `3`: adequate; usable with some revision.
- `4`: strong; likely useful with minor adaptation.
- `5`: excellent; clear, precise, reusable, and structurally efficient.

Also record:

- `source_id`
- `kind`
- `category`
- `name`
- `harnesses`
- `fable_useful`
- `fable_reason`
- `fable_tag`
- `gpt_useful`
- `gpt_reason`
- `gpt_tag`
- `consensus`
- `agree`
- `description`
- `problem_solved`
- `actual_usefulness_verdict`: `adopt`, `merge`, `rewrite`, `defer`, or `reject_after_review`
- `rationale`
- `overlap_with_existing`
- `candidate_cluster_key`
- `evidence_notes`

`reject_after_review` is allowed for a row that passed the inclusion filter but proves weak after deeper analysis. It must still remain in the row-level artifact and, if clustered, in its cluster source list.

## Output Artifacts

Create all artifacts under:

- `harness_lifecycle/codex_analysis/`

Required artifacts:

1. `session-goal.md`
   - This goal file.

2. `run-notes.md`
   - Short execution log, assumptions, surprises, and verification notes.
   - Include counts by `kind`, included/excluded counts, and any unexpected kinds.

3. `excluded_both_rejected.jsonl`
   - One JSON object per row where both Fable and GPT rejected usefulness.
   - Preserve enough CSV fields to audit why the row was excluded.

4. `row_evaluations.jsonl`
   - One JSON object per included row.
   - Must contain all fields listed in "Per-Item Evaluation".
   - This is the lossless analysis record.

5. `clusters.json`
   - Cluster included rows by similar problem solved, trigger, workflow, or harness surface.
   - Preserve every source row ID in exactly one primary cluster.
   - Cross-list secondary relationships when a row meaningfully overlaps multiple clusters.

6. `cluster_review.md`
   - Human-readable review of each cluster.
   - For every cluster, identify whether one candidate is superior, multiple candidates should be merged, or the cluster should be rejected/deferred.

7. `final_synthesis.md`
   - Final table of recommended capabilities.
   - Each recommendation must link back to all source row IDs it uses.
   - Include merged or re-hierarchized capability proposals without losing the original row-level trail.

## Clustering Method

Cluster by the problem a capability solves, not only by name.

For each included row:

1. Derive a concise `problem_solved`.
2. Derive a `candidate_cluster_key` from problem, trigger, audience, and harness surface.
3. Group obvious duplicates and near-duplicates.
4. Keep separate capabilities that share vocabulary but solve different operational problems.
5. Re-read each completed cluster and decide:
   - Is one item clearly superior?
   - Are several complementary?
   - Can parts of multiple items produce a better capability?
   - Does the cluster overlap an existing local capability?
   - Should this become a skill, agent, plugin, MCP config, rule, hook, command, or ledger rejection?

Do not merge by majority vote alone. GPT/Fable usefulness labels are prioritization signals, not final truth.

## Final Synthesis Table

`final_synthesis.md` must include a table with these columns:

- `recommended_capability`
- `recommended_surface`
- `decision`
- `source_ids`
- `source_names`
- `cluster_id`
- `problem_solved`
- `why_this_is_better`
- `reuse_or_merge_plan`
- `priority`
- `risks_or_open_questions`

Decision values:

- `adopt_as_is`
- `adapt`
- `merge`
- `replace_existing`
- `defer`
- `reject_after_review`

Priority values:

- `P0`: high-leverage, should be acted on first.
- `P1`: useful and likely worth doing.
- `P2`: optional or situational.
- `P3`: weak, deferred, or only useful under narrow conditions.

## Execution Discipline

- Work kind by kind in the specified order.
- Complete the row-level evaluation before final synthesis.
- Preserve traceability from final recommendation back to source rows.
- Keep artifacts repo-relative; do not write machine-local absolute paths into docs.
- Treat reference harnesses as read-only.
- Do not edit submodule internals.
- If the analysis is interrupted, resume from the artifacts without restarting from scratch.
- Do not claim completion until the completion criteria below are met.

## Completion Criteria

The goal is complete only when:

- Every CSV row has been accounted for as either excluded or included.
- Every included row has a row-level evaluation in `row_evaluations.jsonl`.
- Every included row appears in exactly one primary cluster in `clusters.json`.
- Cluster review has been completed for every cluster.
- `final_synthesis.md` contains the final recommendation table.
- Counts reconcile:
  - `included + excluded == total CSV data rows`
  - included row count equals `row_evaluations.jsonl` line count
  - included row count equals the number of unique primary-cluster source IDs
- Fresh verification has been run and recorded in `run-notes.md`.

## Suggested Verification

At minimum, run deterministic checks that:

- Parse `capability_usefulness.csv`.
- Parse every generated JSON/JSONL artifact.
- Count total, included, excluded, evaluated, and clustered rows.
- Assert all included source IDs are unique and fully covered.
- Assert no excluded row appears in `row_evaluations.jsonl`.
- Assert every final synthesis source ID exists in row-level evaluations.

Then run the repo's structural completion checks from `.codex/project/verification.md`, including `git status`.
