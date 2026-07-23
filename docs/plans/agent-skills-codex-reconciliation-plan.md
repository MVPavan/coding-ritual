# Agent Skills Codex Reconciliation Plan

## Goal

Extend the canonical harness capability usefulness dataset with the
`agent-skills` reference harness, deeply evaluate the affected capabilities with
Codex only, and reconcile them into the existing Codex clusters and final
recommendations. Do not turn recommendations into adoption-ledger decisions.

Origin: the user-approved request on 2026-07-15 and Beads issue `cr-77q`.

## Scope

Modify:

- `harness_lifecycle/capability_usefulness.csv`
- the canonical artifacts under `harness_lifecycle/codex_analysis/`
- Beads issue `cr-77q` and its `.beads/issues.jsonl` export

Do not modify:

- `harness_lifecycle/ledger.json`
- `harness_lifecycle/visualizations/lifecycle-overview/inventory.csv` or
  `index.html`
- `harness_lifecycle/visualizations/archive/capability-usefulness-868.html`,
  which remains the historical two-model 868-row view rather than being
  silently relabeled as Codex-only
- `harness_lifecycle/fable_analysis/`
- files inside `reference_harnesses/agent-skills/`
- reusable harness capabilities or adoption surfaces

## Baseline And Merge Semantics

- The input catalog contains 44 logical `agent-skills` capabilities.
- Canonical IDs follow the existing usefulness-dataset convention:
  `<kind>:<lowercase-alphanumeric-name>`.
- Five names already exist in the 868-row dataset and must be enriched rather
  than duplicated: `agent:codereviewer`, `agent:securityauditor`,
  `agent:testengineer`, `command:plan`, and
  `skill:testdrivendevelopment`.
- The other 39 capabilities become new canonical rows. Expected final total:
  907 rows.
- Preserve the existing 868-row order and append the 39 new rows in catalog
  order. Do not reorder the historical dataset merely for aesthetics.
- Existing historical Fable and GPT shallow judgments remain unchanged on the
  five merged rows. New-only rows use
  `fable_useful=not_evaluated`, an explicit reason, no fabricated Fable tag,
  `consensus=codex_only`, and `agree=n/a`.
- Codex supplies the shallow `gpt_*` fields for the 39 new rows and the deep
  rubric evaluation for all 44 affected canonical rows. All 44 are included in
  the deep pass even if the Codex shallow judgment is `no`.
- The 239 historical rows rejected by both earlier models stay in
  `excluded_both_rejected.jsonl`. Expected final deep-analysis count: 668.
- On the five merged CSV rows, change only `harnesses`; preserve their prior
  descriptions and shallow judgments. Their deep evaluations are replaced
  after reading the new source variants, with the provenance limitation
  recorded in `evidence_notes` and `run-notes.md`.

## Execution

### 1. Canonical dataset tracer bullet

Merge one known duplicate and one known-new capability in a deterministic
scratch transformation, then verify ID normalization, provenance, column
semantics, and stable CSV ordering. Apply the same transformation to all 44
catalog entries only after the tracer is correct.

Verification:

- every catalog capability maps to exactly one canonical ID;
- exactly five IDs existed before the merge and exactly 39 are new;
- final IDs are unique and all 44 affected rows include `agent-skills` in
  `harnesses`;
- historical Fable and GPT shallow fields are unchanged for all pre-existing
  rows, with the five enriched variants' scope recorded in the deep-analysis
  evidence.

### 2. Codex row analysis

Read the canonical source file for every affected capability and score the six
dimensions from `codex_analysis/session-goal.md`. Preserve the 624 unaffected
historical row evaluations, replace the five materially enriched evaluations,
and add 39 new evaluations.

Keep auditable incremental shard artifacts for the 39 new rows, and update the
five affected records in their existing shard inputs and outputs so every
canonical source ID still appears in exactly one current shard.

Verification:

- all row-evaluation objects satisfy the existing schema;
- scores are integers from 1 through 5 and verdicts use the allowed vocabulary;
- 668 unique included IDs appear exactly once across current shard outputs and
  in `row_evaluations.jsonl`;
- no excluded ID appears in the merged evaluations.

### 3. Cluster reconciliation

Assign each affected row to the existing cluster that represents the same
problem solved. Create a new cluster only if no existing cluster can represent
the capability without semantic distortion. Recalculate cluster membership,
counts, score averages, best sources, decisions, priorities, relationships,
and recommendations from the full 668-row evaluation set.

Regenerate:

- `clusters.json`
- `cluster_review.md`
- `final_synthesis.md`
- `run-notes.md`
- `session-board.md`
- `shard_manifest.json`

Update `session-goal.md` before the merge so its input contract explicitly
defines the Codex-only sentinel values and the rule that all 39 new rows are
included even when the shallow Codex verdict is `no`. Record the five updated
rows across their four historical shards.

For cluster aggregates, preserve the existing cluster order and qualitative
fields unless affected by new evidence. Recompute source IDs/names, kind and
verdict counts, candidate keys, source count, and average score from row data.
Rank best sources by mean six-dimension score with `source_id` as the stable
tie-breaker. Document any coordinator judgment that changes a decision,
priority, relationship, or recommendation.

Verification:

- every included ID appears in exactly one primary cluster;
- cluster metadata agrees with its source evaluations;
- every final-synthesis source ID exists in `row_evaluations.jsonl`;
- recommendations explicitly describe any change caused by `agent-skills`.

### 4. Review And completion gate

Run a requirements/spec review, then an adversarial quality review focused on
false deduplication, fabricated two-model agreement, cluster drift, stale
counts, and accidental ledger changes. Correct findings and re-run the checks.

Final evidence must include:

- CSV, JSON, and JSONL parse checks;
- deterministic coverage and cluster-integrity assertions;
- `git diff --check` with generated-CSV baseline line-ending behavior handled
  explicitly;
- machine-local-path scan over changed analysis artifacts;
- `sha256sum harness_lifecycle/ledger.json` equal to the recorded pre-run hash
  `b7cbb49a4b8fe8e0bd4e1cf6e085387ab98cd42a7e57d6ab85c3b5e833384d82`;
- fresh `bd ready` and `git status --short` output.

## Risks And Invariants

- Similar workflow names do not prove identical capability identity; canonical
  row deduplication is name-based, while semantic overlap is handled in
  clusters.
- Do not reinterpret blank historical fields or rewrite prior model judgments.
- Reference-harness files remain read-only.
- No recommendation is an adoption decision, and `ledger.json` is outside
  scope.
- Keep all stored paths repo-relative.
