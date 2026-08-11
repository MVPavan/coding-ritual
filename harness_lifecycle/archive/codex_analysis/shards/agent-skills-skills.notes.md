# agent-skills skills shard notes

## Scope and method

- Evaluated the 24 `skill` capabilities in `harness_lifecycle/catalogs/agent-skills.json` against the six-dimension rubric in `harness_lifecycle/codex_analysis/session-goal.md`.
- Read every canonical `SKILL.md` under `reference_harnesses/agent-skills/skills/`; also read all supporting `idea-refine` references and its initializer script.
- Preserved name-based canonical identity: 23 capabilities are new rows in this shard, while `test-driven-development` enriches the existing `skill:testdrivendevelopment` row in `skill-2`.
- This expansion is Codex-only. New rows use the explicit `not_evaluated`, `codex_only`, and `n/a` sentinels and do not imply a Fable judgment.
- Semantic overlap was reconciled through candidate cluster keys rather than false canonical deduplication.

## Results

- New canonical rows: 23.
- Codex shallow usefulness: 22 `yes`, 1 `no` (`using-agent-skills`).
- Deep verdicts across all 24 affected skills: 17 `merge`, 4 `defer`, 1 `rewrite`, 1 `reject_after_review`, and the provenance-enriched TDD row's retained `adopt` verdict in `skill-2`.
- No new primary cluster is required. The affected skills fit existing clusters C001, C002, C010, C013, C016, C018, C020, C022, C027, C028, C030, C032, C033, C035, C041, C050, C052, C056, and C071.

## Recommendation effects

- Strengthen phased execution with thin vertical and risk-first slices.
- Broaden cited research into version-aware official-documentation lookup.
- Keep adversarial review selective and bounded; do not adopt mandatory cross-model cycles.
- Add intent elicitation to product discovery without the source's rigid confidence gate.
- Promote the security/privacy cluster based on stronger threat-model, LLM-output, SSRF, and supply-chain material.
- Treat CI, observability, performance, and launch guidance as optional application/operations capabilities rather than default harness context.

## Material concerns

- `git-workflow-and-versioning` recommends `git reset --hard HEAD`, conflicting with repository Git safety.
- Planning and specification skills prescribe `tasks/plan.md` and `tasks/todo.md`, conflicting with Beads-backed durable tracking.
- `doubt-driven-development` mandates a cross-model offer on every interactive cycle and embeds provider-specific CLI mechanics.
- `interview-me` rejects ordinary confirmations and uses a subjective 95-percent confidence gate.
- Several broad skills are application-stack specific despite generic triggers. The 24 source skills total 6,951 lines, so default-context cost is a recurring weakness.
- `using-agent-skills` duplicates native skill trigger rules and the always-loaded project guide; it is rejected after review.

## Evidence boundary

- Reference submodule files were read only.
- No ledger, dashboard, Fable-analysis, adoption, or reusable-harness files were changed by this shard.
