# skill-4 Shard Notes

## Assumptions

- Evaluated only the 58 rows in `harness_lifecycle/codex_analysis/shards/skill-4.input.jsonl`.
- Used CSV-derived fields as the primary source. Supporting inputs were inspected only where descriptions were placeholders/truncated or overlap with local harness capabilities affected the verdict.
- Treated `reference_harnesses/` as read-only and did not inspect or modify submodule internals beyond reading selected source files.
- `bd prime` was attempted for project context, but `bd` is not installed in this environment, so no Beads state was read or changed.

## Evidence Inspected

- Read `AGENTS.md`, `.codex/project/brief.md`, `.codex/project/repo-map.md`, `.codex/project/docs-index.md`, `.codex/project/verification.md`, `.codex/project/invariants.md`, `.codex/rules/core/03-ak-guidelines.md`, `.beads/beads.md`, and `harness_lifecycle/codex_analysis/session-goal.md`.
- Checked local skill overlap under `.codex/skills/` and `.claude/skills/`; direct local overlaps found for `cost-estimate` and `teach-session`.
- Inspected `harness_lifecycle/catalogs/*.json` for ambiguous rows and source metadata.
- Sampled source files for placeholder or high-ambiguity rows: `token-budget-advisor`, `inventory-demand-planning`, `production-scheduling`, `quality-nonconformance`, `click-path-audit`, `hookify-rules`, `configure-ecc`, and `frontend-design`.
- Read local `cost-estimate` and `teach-session` skills because the CSV row either had a placeholder description or direct local ownership.

## Weak Rows

- `skill:ceupdate` is the weakest row: CSV/catalog description is `|`, and the expected source path was not present in the checked reference tree. It was rejected after review for insufficient evidence.
- `skill:costestimate`, `skill:tokenbudgetadvisor`, `skill:inventorydemandplanning`, `skill:productionscheduling`, and `skill:qualitynonconformance` had placeholder CSV descriptions; source/catalog checks supplied enough context for evaluation.
- Several rows are well-written but domain-specific rather than harness-level: healthcare, manufacturing, inventory, blockchain, Cardputer/M5Stack, SEO, media-platform, and article-writing workflows.

## Likely Cluster Relationships

- `frontend-design`, `design-system`, `click-path-audit`, `test-browser`, `feature-video`, and `ui-demo` cluster around frontend quality, visual/browser verification, and UI demo evidence.
- `hookify-rules` and `writing-hookify-rules` are near-duplicates and should remain in one Hookify-specific authoring cluster.
- `teach` and `teach-session` should merge under session teaching/explanation; only `teach-session` exists locally.
- `project-flow-ops` and `qa` relate to issue/bug intake, but any useful version should be rewritten around Beads plus GitHub rather than Linear.
- Healthcare rows form two related clusters: healthcare application patterns and healthcare privacy/compliance.
- `inventory-demand-planning`, `production-scheduling`, and `quality-nonconformance` form an operations-domain playbook cluster that is not suitable for the core harness.
- `feature-video` and `ui-demo` should be reconciled as a single PR/UI demo-video workflow if retained.

## Issues

- The shard includes many `maybe` rows that are useful in other domains but weak for this repo's lean coding-harness scope. I favored `defer` for situational but plausible workflows and `reject_after_review` for product-specific, domain-specific, or non-portable rows.
- Some source descriptions in the CSV appear malformed due to YAML block scalar extraction. Catalog/source checks were used only where that materially affected evaluation.
