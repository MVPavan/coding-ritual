# command-1 shard notes

## Scope

- Evaluated 61 included `command` rows from `harness_lifecycle/codex_analysis/shards/command-1.input.jsonl`.
- Wrote one JSON object per input row to `harness_lifecycle/codex_analysis/shards/command-1.row_evaluations.jsonl`.
- Used the shard JSONL fields first. Supporting evidence was limited to local command, skill, project, and plugin files needed for overlap checks.
- Did not read source CSV, ledger files, final/merged artifacts, or submodule internals. Did not edit any file outside this shard's two owned outputs.

## Evidence inspected

- `AGENTS.md`, `harness_lifecycle/codex_analysis/session-goal.md`, and the assigned input shard.
- `.codex/project/{brief.md,repo-map.md,docs-index.md,verification.md,invariants.md,tools.md,learnings.md}`.
- `.codex/rules/core/03-ak-guidelines.md`, `.beads/beads.md`, and `harness_learnings/coding-harness-best-practices.md`.
- Local Claude commands: `.claude/commands/{adopt.md,check-invariants.md,use-codex.md,harness-scan.md,harness-status.md,prepare-phases.md,run-phases.md}`.
- Local Codex skills used for overlap: `adopt`, `use-codex`, `check-invariants`, `prepare-phases`, `run-phases`, `phase-execution`, `planning`, `systematic-debugging`, `subagent-driven-development`, and `codebase-architecture-research`.
- Plugin command sources under `mvp-harness/plugins/{mvp-plugin,codex-adapter,code-intel}/commands/` for rows marked local.

## Assumptions

- `adopt` means keep or add the capability with little structural change. For rows already implemented locally, it means keep the local implementation as canonical.
- `merge` means the capability is useful but should be reconciled with an existing skill, command, or cluster rather than added as another standalone command.
- `rewrite` means the problem is worth solving but the row needs stronger safety gates, clearer instructions, or a Codex/Claude-neutral shape.
- `defer` means useful only for optional packs, specific team tooling, or target repos outside this lean core harness.
- `reject_after_review` was used only for rows with empty descriptions and no clear operational contract.

## Weak or risky rows

- `command:multiplan` and `command:multiworkflow` have empty descriptions and are redundant with existing planning and orchestration surfaces.
- `command:databasemigration` names an important workflow but is only a scaffold.
- `command:cleangone`, `command:commit`, `command:commitpushpr`, and `command:prppr` need explicit staging, approval, and destructive-action safeguards before adoption.
- `command:hookify` is valuable only if hook generation is reviewable, deterministic, and explicitly approved before enabling hooks.
- `command:instinctexport`, `command:instinctimport`, and `command:instinctstatus` conflict with the local split where Beads tracks work and project learnings/MEMORY hold durable knowledge.

## Likely cluster relationships

- Codex delegation cluster: `command:codex`, `command:codexcritique`, `command:codexdiagnose`, `command:codeximplement`, `command:codexresearch`, `command:codexreview`, `command:codexcheck`, and `command:usecodex`.
- Harness lifecycle cluster: `command:adopt`, `command:update`, `command:doctor`, `command:harnessscan`, and `command:harnessstatus`.
- Workstream execution cluster: `command:preparephases`, `command:runphases`, `command:rpiimplement`, `command:rpiplan`, `command:rpiresearch`, `command:prpplan`, `command:prpimplement`, and `command:plan`.
- Review/security cluster: `command:codereview`, `command:reviewpr`, `command:santaloop`, `command:security`, and `command:modernizeharden`.
- Git publishing cluster: `command:commit`, `command:commitpushpr`, `command:prppr`, `command:cleangone`, and `command:triageprs`.
- Code-intel cluster: `command:indexrepo`, `command:disableforproject`, and the code-intel meaning of `command:doctor`.
- Modernization optional pack: `command:modernizeassess`, `command:modernizebrief`, `command:modernizeextractrules`, `command:modernizepreflight`, `command:modernizestatus`, `command:modernizetransform`, and `command:modernizeuplift`.

## Issues

- `bd prime` was attempted for runtime context but failed because `bd` is not installed in this shell. No Beads writes were made.
- The project orientation docs reference `my_harness/`, but the live checkout uses `mvp-harness/`; overlap judgments used the live tree plus installed `.codex` and `.claude` assets.
- `.codex/commands/README.md` says Codex shared workflows should be Codex skills, so external command rows were generally judged as merge/rewrite candidates unless already local or clearly optional.

## 2026-07-15 Agent-Skills Increment

- Refreshed `command:plan` after reading `reference_harnesses/agent-skills/.claude/commands/plan.md`.
- Appended `agent-skills` provenance while preserving the historical shallow judgments and canonical description.
- Historical Fable evaluation predates this source variant; the deep evaluation retains `merge` and records the stronger local overlap.
