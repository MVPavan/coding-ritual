# skill-3 Notes

## Assumptions

- Evaluated only the 60 rows in `harness_lifecycle/codex_analysis/shards/skill-3.input.jsonl`.
- Used input JSONL fields as primary evidence. Supporting evidence was limited to local overlap checks and ambiguous placeholder descriptions.
- Treated `in_ours: yes` rows as already-adopted or merge-needed depending on whether the capability exists in the Codex side, Claude side, or mvp-harness only.
- Did not inspect or modify `reference_harnesses/`; submodules remain read-only.

## Evidence Inspected

- `AGENTS.md`
- `.codex/project/brief.md`
- `.codex/project/repo-map.md`
- `.codex/project/docs-index.md`
- `.codex/project/verification.md`
- `.codex/project/invariants.md`
- `.codex/rules/core/03-ak-guidelines.md`
- `harness_learnings/coding-harness-best-practices.md`
- `harness_lifecycle/codex_analysis/session-goal.md`
- `harness_lifecycle/codex_analysis/shards/skill-3.input.jsonl`
- Local skill inventory under `.codex/skills/`, `.claude/skills/`, `.agents/`, and `mvp-harness/`
- Targeted local files for overlap: `deep-research`, `prepare-phases`, `migrate-claude-to-codex`, `grill-me`, `test-driven-development`, `subagent-driven-development`, `harness-adopt`, `harness-evaluate`, and `refresh-harness-from-reference`
- Targeted catalog snippets for placeholder rows `prompt-optimizer` and `blueprint`

## Weak Rows

- `skill:promptoptimizer` and `skill:blueprint` have `>-` placeholder descriptions in both the shard input and supporting catalog snippets; both need rewrite/recovery before adoption.
- `skill:lfg`, `skill:implement`, and `skill:teambuilder` are too thin to add value over local planning/execution skills.
- `skill:datascraperagent` is an application template rather than a harness lifecycle capability.
- `skill:aifirstengineering` is a broad team operating model and is less actionable than existing local harness best practices.
- `skill:todocreate` and `skill:todoresolve` conflict with the repo's Beads-first durable tracking model.

## Likely Cluster Relationships

- Autonomous agent operations: `skill:autonomousagentharness`, `skill:continuousagentloop`, `skill:enterpriseagentops`, with looser ties to `skill:ralphinhorfcpipeline`.
- Browser and UI verification: `skill:browserqa` and `skill:e2etesting`.
- Design pressure and validation: `skill:grillwithdocs`, `skill:grilling`, `skill:productlens`, `skill:prototype`, `skill:designaninterface`, and `skill:requestrefactorplan`.
- Harness lifecycle/meta: `skill:harnessadopt`, `skill:harnessevaluate`, `skill:migrateclaudetocodex`, `skill:preparephases`, and `skill:refreshharnessfromreference`.
- Work tracking: `skill:decisionmapping`, `skill:todocreate`, `skill:todoresolve`, `skill:todotriage`, `skill:toprd`.
- MCP/tool packaging: `skill:buildmcpb`, `skill:buildmcpapp`, and possibly `skill:agentnativearchitecture`.
- HTML/artifact outputs: `skill:playground`, `skill:frontendslides`, `skill:projectartifact`.

## Issues

- `bd prime` could not be run because `bd` is not installed in the environment (`command not found`).
- `my_harness/` is referenced by project docs, but the current tree uses `mvp-harness/`; evaluations used actual current paths where overlap evidence was needed.
- Several source descriptions are truncated in the shard input (`ce:ideate`, `claude-permissions-optimizer`, `project-artifact`, `ce-slack-research`, `build-mcp-app`), so scores emphasize visible trigger/behavior only.
