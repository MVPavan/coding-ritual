# agent-1 shard notes

## Scope
- Evaluated 54 `agent` rows from `harness_lifecycle/codex_analysis/shards/agent-1.input.jsonl`.
- Wrote one row-evaluation JSON object per input row to `harness_lifecycle/codex_analysis/shards/agent-1.row_evaluations.jsonl`.
- Did not inspect or modify reference harness submodule internals.

## Assumptions
- CSV/input fields are the primary evidence; supporting local files were inspected only for overlap and repo-fit checks.
- `in_ours=yes` rows are treated as already adopted when local `.codex/agents/*.toml` or `.claude/agents/*.md` confirmed the capability.
- For near-duplicate specialists, `merge` means preserve the useful trigger/lens in a broader local skill/agent rather than add a separate agent.
- `defer` means useful only behind optional tooling/domain assumptions not present in this repo; it is not a rejection.

## Evidence inspected
- `AGENTS.md`
- `.codex/project/brief.md`, `repo-map.md`, `docs-index.md`, `verification.md`, `invariants.md`
- `.codex/rules/core/03-ak-guidelines.md`
- `harness_lifecycle/codex_analysis/session-goal.md`
- `harness_lifecycle/codex_analysis/shards/agent-1.input.jsonl`
- Local agent files: `.codex/agents/{claude-max,code-reviewer,docs-researcher,fable-max,fable-xhigh,planner,spec-reviewer}.toml` and selected `.claude/agents/*.md`
- Local skills checked for overlap: `.codex/skills/document-review/SKILL.md`, `.codex/skills/subagent-driven-development/SKILL.md`; other local skill names were taken from the repo inventory and session skill list.

## Weak or risky rows
- `agent:agentsdkverifierpy`: narrow Agent SDK applicability; deferred unless this harness grows optional OpenAI Agent SDK verification.
- `agent:docupdater`: useful intent, but referenced `/update-codemaps`, `/update-docs`, and `docs/CODEMAPS/*` conventions do not match this repo; rewrite around local project overlays.
- `agent:kieranpythonreviewer`: useful Python lens but person-named/non-portable; rewrite as project-neutral Python review guidance.
- `agent:loopoperator`: real orchestration problem but underspecified; needs explicit stall criteria, permissions, and intervention limits.
- `agent:sessionhistorian`: useful concept but requires cross-tool history access, storage, and privacy design before adoption.

## Likely cluster relationships
- `generalist-delegation-tiers`: `claude-max`, `fable-max`, `fable-xhigh`; already represented locally as compatibility agents that inherit the active Codex model.
- `docs-and-best-practices-research`: `docs-researcher` is the local canonical capability; `docs-lookup`, `framework-docs-researcher`, and `best-practices-researcher` should merge into it.
- `architecture-planning` / `architecture-critique`: `planner`, `architect`, `code-architect`, `architecture-critic`, and plan feasibility/scope review rows should reconcile with local planning/document-review flows.
- `code-review-*` lenses: many compound-engineering review agents are best preserved as conditional lenses under the existing `code-reviewer`, not as standalone agents.
- `document-review-*` lenses: adversarial, coherence, feasibility, scope, and security plan-review rows should merge into the existing document-review skill and spec-reviewer flow.
- `data-and-database-safety-review`: data integrity, data migration, database reviewer, and deployment verification rows should be one conditional data-risk review cluster.
- `security-review-and-threat-modeling`: security auditor, security lens reviewer, and security reviewer should merge into one plan/code security review cluster.
- `repo-history-and-institutional-research`: git history, learnings, repo research, code explorer, and legacy analyst rows overlap with local research/read-order practices.

## Issues
- `bd prime` could not run because `bd` is not installed in this environment.
- Pre-existing unowned changes were present before writing this shard, including `session-goal.md` and untracked coordinator artifacts; these were not touched.
- Some input descriptions are visibly truncated in the shard source; evaluations use the available CSV text and avoid inventing missing details.

## 2026-07-15 Agent-Skills Increment

- Refreshed `agent:codereviewer` and `agent:securityauditor` after reading their current `agent-skills` variants.
- Appended `agent-skills` provenance without changing historical shallow judgments or descriptions.
- Historical Fable evaluations predate this source expansion; the replacement deep evaluations state that limitation explicitly.
