# command-2 Notes

## Scope

- Evaluated all 61 rows from `harness_lifecycle/codex_analysis/shards/command-2.input.jsonl`.
- Wrote only the owned shard artifacts:
  - `harness_lifecycle/codex_analysis/shards/command-2.row_evaluations.jsonl`
  - `harness_lifecycle/codex_analysis/shards/command-2.notes.md`
- Did not stage, commit, or edit coordinator-owned files.

## Assumptions

- This worker should evaluate rows, not reconcile final decisions; `candidate_cluster_key` values are proposals for coordinator clustering.
- Verdicts judge the command row itself. For legacy shims, useful underlying skills may still deserve adoption via their own skill rows.
- `mvp-harness/` is treated as the local harness implementation path because `my_harness/` is referenced by docs but not present in this checkout.
- `bd prime` was attempted because repo policy requests it, but `bd` is not installed in this environment.

## Evidence Inspected

- Required inputs: `AGENTS.md`, `harness_lifecycle/codex_analysis/session-goal.md`, and the `command-2` input JSONL.
- Repo guardrails: `.codex/project/{brief,repo-map,docs-index,verification,invariants}.md`, `.codex/rules/core/03-ak-guidelines.md`, `.beads/beads.md`.
- Local overlap surfaces: `.codex/commands/README.md`, `.claude/commands/`, `.codex/skills/*` for brainstorming, planning, TDD, debugging, teach-session, verification, and Beads.
- Local code-intel evidence: `mvp-harness/plugins/code-intel/commands/setup.md` and `mvp-harness/plugins/code-intel/README.md`.
- Supporting catalogs and selected reference command bodies under `reference_harnesses/` for ambiguous or empty-description rows.

## Weak Rows

- Reject-after-review rows are mostly legacy slash-command shims that explicitly say to prefer a skill directly: `agent-sort`, `brainstorm`, `claw`, `context-budget`, `devfleet`, `docs`, `e2e`, `eval`, `execute-plan`, `orchestrate`, `prompt-optimize`, `rules-distill`, `tdd`, `verify`, and `write-plan`.
- Very weak rows with little or no transferable content: `quiz-me`, `teach-me`, `sync-tutorials`, `README`, `gan-build`, and `gan-design`.
- Ralph Loop and Hookify companion commands are only useful if those parent systems are adopted; most were deferred or rejected rather than treated as standalone capabilities.

## Likely Cluster Relationships

- `legacy-skill-command-shim` and `deprecated-skill-command-shim` should probably collapse into one final rejection cluster.
- `session-learning-memory` includes `revise-claude-md` and `learn`; it overlaps local `.codex/project/learnings.md`.
- `platform-drift-maintenance` covers Claude command/settings/skills/subagent/concepts drift workflows; `reference-workflow-research` is related but broader.
- `safe-refactor-cleanup`, `build-fix-loop`, `coverage-improvement`, `format-quality-gate`, and `docs-sync` may be better synthesized as quality and maintenance workflow improvements than separate commands.
- `multi-model-execution`, `multi-model-backend-workflow`, `model-routing`, and `agent-loop-control` overlap local `use-codex`, `subagent-driven-development`, and phase workflows.

## Issues

- `bd prime` failed with `bd: command not found`; no Beads state was changed.
- Project docs mention `my_harness/`, but this checkout contains `mvp-harness/`; overlap notes use the present path.
- Several CSV rows had empty descriptions while source command files were substantive; those were inspected before scoring.
