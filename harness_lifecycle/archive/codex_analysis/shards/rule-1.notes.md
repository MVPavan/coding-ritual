# rule-1 Shard Notes

## Scope

- Evaluated all 42 rows from `harness_lifecycle/codex_analysis/shards/rule-1.input.jsonl`.
- Wrote one JSON object per row to `harness_lifecycle/codex_analysis/shards/rule-1.row_evaluations.jsonl`.
- Used CSV fields first. Supporting reads were limited to source/catalog/local-rule checks for blank descriptions, overlap, or weak/marginal rows.

## Assumptions

- `actual_usefulness_verdict: adopt` means the capability is useful as-is for the local harness, including rows already present in `ours`.
- `merge` means keep only compatible fragments after deduping against local `.codex`/`.claude` guidance.
- `rewrite` means the problem is worth solving but the source rule is too platform-specific, heavy, conflicting, or mixed-purpose to import directly.
- Chinese `zh/*` rows are treated as localization duplicates for an English-first harness, not as separate capabilities.

## Evidence Inspected

- Required context: `AGENTS.md`, `harness_lifecycle/codex_analysis/session-goal.md`, and `harness_lifecycle/codex_analysis/shards/rule-1.input.jsonl`.
- Project context: `.codex/project/brief.md`, `.codex/project/repo-map.md`, `.codex/project/docs-index.md`, `.codex/project/verification.md`, `.codex/project/invariants.md`, `.codex/rules/core/03-ak-guidelines.md`, and `harness_learnings/coding-harness-best-practices.md`.
- Local overlap: `.codex/rules/core/01-delegation.md`, `.codex/rules/core/02-knowledge-discoverability.md`, `.codex/rules/core/03-ak-guidelines.md`, `.codex/rules/python/coding-style.md`, `.codex/rules/python/testing.md`, `.codex/rules/python/safety.md`, `.claude/rules/harness-lifecycle/curation.md`, and `.codex/rules/default.rules`.
- Catalog checks: `harness_lifecycle/catalogs/everything-claude-code.json`, `harness_lifecycle/catalogs/claude-code-best-practice.json`, and `harness_lifecycle/aliases.json`.
- Read-only source spot-checks under `reference_harnesses/everything-claude-code/` and `reference_harnesses/claude-code-best-practice/` for common, Python, web, Remotion text-measurement, README, guardrail, presentation, Markdown, and zh duplicate rules.

## Weak Rows

- `rule:presentation`: actual source is specific per-deck delegation, not a generic presentation/output rule.
- `rule:readme`: actual source is a ruleset installation README, not reusable README-authoring guidance.
- `rule:commonpatterns`: thin app-pattern guidance; marginal for a meta-harness.
- `rule:measuringtext`: useful only for Remotion/video text fitting, not general HTML.
- `rule:zh*`: translations/duplicates of English rows; rejected after review as separate adoption candidates.

## Likely Cluster Relationships

- `agent-orchestration-rules`: `rule:commonagents`, `rule:core01delegation`, `rule:zhagents`.
- `development-workflow-discipline`: `rule:commondevelopmentworkflow`, `rule:zhdevelopmentworkflow`, with overlap to AK/TDD/debugging skills.
- `git-pr-workflow`: `rule:commongitworkflow`, `rule:zhgitworkflow`.
- `hooks-governance`: `rule:commonhooks`, `rule:pythonhooks`, `rule:zhhooks`.
- `security-baseline` / `python-security-safety`: `rule:commonsecurity`, `rule:pythonsecurity`, `rule:pythonsafety`, `rule:zhsecurity`, plus `rule:websecurity` as web-specific.
- `testing-baseline` / `python-testing`: `rule:commontesting`, `rule:pythontesting`, `rule:zhtesting`, plus `rule:webtesting` for visual artifact verification.
- `web-frontend-quality-rules`: `rule:webdesignquality`, `rule:webcodingstyle`, `rule:webpatterns`, with `rule:webperformance` and `rule:webtesting` adjacent.
- `ruleset-readme-docs`: `rule:readme`, `rule:zhreadme`; likely reject as harness rules.

## Issues

- `bd prime` was attempted because repo guidance says to run it, but `bd` is not installed in this shell (`bd: command not found`).
- Two non-existent template rule paths were included in an exploratory `rg --files` command and produced expected "No such file or directory" errors; no files were modified.
