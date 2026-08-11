# skill-1 shard notes

## Scope

- Evaluated 60 included `skill` rows from `harness_lifecycle/codex_analysis/shards/skill-1.input.jsonl`.
- Wrote one JSON object per input row to `harness_lifecycle/codex_analysis/shards/skill-1.row_evaluations.jsonl`.
- Used CSV-derived input fields first. Supporting evidence was limited to local repo/project docs and local skill files for overlap or malformed-row checks.
- Did not read source CSV, ledger files, final/merged artifacts, or any non-`skill-1` shard output. Did not edit reference submodules.

## Evidence inspected

- `AGENTS.md` and required project orientation docs under `.codex/project/`.
- `.beads/beads.md`; `bd prime` was attempted for runtime context but `bd` is not installed in this runtime. No Beads writes were made.
- Local skill inventory under `.codex/skills/`, `.claude/skills/`, and `mvp-harness/plugins/*/skills/`.
- Local supporting skill files for ambiguous or key overlap rows: `.codex/skills/adopt/SKILL.md`, `.codex/skills/design-evolve/SKILL.md`, `mvp-harness/plugins/code-intel/skills/graph-first/SKILL.md`, and `mvp-harness/plugins/codex-adapter/skills/codex-runner/SKILL.md`.

## Assumptions

- `actual_usefulness_verdict=adopt` means the capability is worth keeping or adding with little structural change. For rows already present locally, it means keep the local implementation as canonical.
- `merge` means the row is useful but overlaps an existing local capability or another likely cluster and should not become a separate standalone skill without reconciliation.
- `rewrite` means the capability is useful but the row is too broad, too vague, or too provider-specific for direct adoption.
- `defer` means useful in some target repos but lower priority for the core reusable harness.

## Weak or risky rows

- `skill:designevolve`: CSV description is malformed as `>`; evaluated from the local `.codex/skills/design-evolve/SKILL.md`.
- `skill:cework`: description is too vague to operationalize without rewriting.
- `skill:agentharnessconstruction`, `skill:evalharness`, and `skill:ganstyleharness`: promising but under-specified; likely need concrete procedures, gates, and examples.
- `skill:continuouslearning` and `skill:continuouslearningv2`: potentially valuable but risky because automatic learned-skill creation can create noisy or unreviewed harness growth.
- `skill:ganstyleharness`: the cited March 2026 Anthropic paper was not independently verified in this shard.
- Domain-specific rows (`django-*`, `database-migrations`, `deployment-patterns`, `docker-patterns`, `canary-watch`) are useful but probably belong in optional project overlays, not the default harness core.

## Likely cluster relationships

- Requirements/planning/execution: `skill:brainstorming`, `skill:cebrainstorm`, `skill:ceplan`, `skill:executingplans`, `skill:cework`, and local phase/planning skills.
- Harness authoring: `skill:agentdevelopment`, `skill:commanddevelopment`, `skill:buildmcpserver`, `skill:agentharnessconstruction`, and `skill:claudeautomationrecommender`.
- Project memory/docs: `skill:architecturedecisionrecords`, `skill:cecompound`, `skill:cecompoundrefresh`, `skill:designevolve`, `skill:documentreview`, and `skill:domainmodeling`.
- Agent quality loops: `skill:agentintrospectiondebugging`, `skill:airegressiontesting`, `skill:contextbudget`, `skill:evalharness`, `skill:ganstyleharness`, and systematic verification/debugging skills.
- Git/GitHub lifecycle: `skill:finishingadevelopmentbranch`, `skill:gitcleangonebranches`, `skill:gitcommit`, `skill:gitcommitpushpr`, `skill:gitguardrailsclaudecode`, `skill:gitworktree`, and `skill:githubops`.
- Python/app-domain optional packs: `skill:djangopatterns`, `skill:djangosecurity`, `skill:djangotdd`, `skill:djangoverification`, `skill:databasemigrations`, `skill:deploymentpatterns`, and `skill:dockerpatterns`.

## Issues

- Repo orientation docs reference `my_harness/`, but the actual directory in this checkout is `mvp-harness/`. I used the actual tree for overlap checks.
- `bd prime` could not run because `bd` was not found.
