# plugin-mcp-1 notes

## Scope

- Evaluated 51 assigned rows from `harness_lifecycle/codex_analysis/shards/plugin-mcp-1.input.jsonl`.
- Shard composition: plugin and MCP rows only.
- Wrote one row-level JSON object per source row to `harness_lifecycle/codex_analysis/shards/plugin-mcp-1.row_evaluations.jsonl`.

## Assumptions

- CSV/shard fields were treated as primary evidence. Most plugin rows are package-level manifests with blank descriptions, so I did not infer rich behavior unless the catalog or local harness made it clear.
- `adopt` means keep or add the capability as a direct harness surface. For rows already in the local harness, `adopt` means preserve as the current baseline rather than source a new external copy.
- Package-level plugin rows usually received `merge` when the underlying problem was useful but the better adoption unit is a local skill/agent/MCP or selected child pattern.
- Provider-specific integrations such as Asana, Linear, GitLab, Firebase, Discord, and Telegram were judged against this repo's current Beads/GitHub-centered workflow, not against hypothetical future projects.

## Evidence inspected

- Required instructions: `AGENTS.md`, `.codex/project/brief.md`, `.codex/project/repo-map.md`, `.codex/project/docs-index.md`, `.codex/project/verification.md`, `.codex/project/invariants.md`, `.codex/rules/core/03-ak-guidelines.md`, `.beads/beads.md`, and `harness_lifecycle/codex_analysis/session-goal.md`.
- Shard input: `harness_lifecycle/codex_analysis/shards/plugin-mcp-1.input.jsonl`.
- Lifecycle catalogs: `harness_lifecycle/catalogs/claude-plugins-official.json`, `harness_lifecycle/catalogs/claude-code-best-practice.json`, `harness_lifecycle/catalogs/everything-claude-code.json`, `harness_lifecycle/catalogs/compound-engineering-plugin.json`, `harness_lifecycle/catalogs/mattpocock_skills.json`, and `harness_lifecycle/catalogs/superpowers.json`.
- Local overlap evidence: `.codex/skills`, `.codex/agents`, `.claude/skills`, `.claude/agents`, `.codex/project/tools.md`, `mvp-harness/plugins/code-intel/.claude-plugin/plugin.json`, `mvp-harness/plugins/code-intel/.mcp.json`, `mvp-harness/plugins/codex-adapter/.claude-plugin/plugin.json`, and `mvp-harness/plugins/mvp-plugin/README.md`.

## Weak rows

- `plugin:cwcmakers`, `plugin:playground`, `plugin:discord`, `plugin:telegram`, and `plugin:exampleplugin` did not show a durable harness capability beyond niche/demo/messaging use.
- `plugin:explanatoryoutputstyle` and `plugin:learningoutputstyle` are mostly global style biases; local task-specific teaching is cleaner.
- `mcp:memory` and `mcp:sequentialthinking` overlap existing project memory, planning, debugging, and reasoning workflows without clear added value.
- `plugin:linear` and `plugin:asana` conflict with the repo's Beads source-of-truth policy.

## Likely cluster relationships

- `plugin:codeintel`, `plugin:serena`, `mcp:serena`, and `mcp:codebasememory` should cluster around `semantic-code-intelligence-and-memory`.
- `plugin:context7` and `mcp:context7` should cluster under `live-documentation-lookup`; the MCP row is the cleaner adoption unit.
- `plugin:playwright` and `mcp:playwright` should cluster under `browser-automation-testing`; the MCP row is the cleaner adoption unit.
- `plugin:github` and `mcp:github` should cluster under `github-workflow-integration`, with Beads remaining the local work-state source of truth.
- `plugin:claudecodesetup` and `plugin:mvpplugin` should cluster under `harness-setup-and-adoption`; the local `mvp-plugin` is the baseline.
- `plugin:skillcreator`, `plugin:plugindev`, and `plugin:exampleplugin` overlap around `plugin-skill-authoring`, but only the first two have material adoption value.
- `plugin:superpowers`, `plugin:featuredev`, and several local workflow skills overlap around disciplined feature execution; merging selected patterns is safer than adopting a large bundle.

## Issues and caveats

- `bd prime` could not run because `bd` was not on PATH in this environment. I read `.beads/beads.md` instead.
- `.codex/project/repo-map.md` references `my_harness/`, but this checkout has `mvp-harness/` instead. I used the actual `mvp-harness/` plugin files for overlap evidence.
- Several official plugin manifests are intentionally sparse in the catalogs, so scores for instruction quality and precision are conservative at the package-row level.
- No reference_harnesses submodule internals were modified.
