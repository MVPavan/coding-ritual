# agent-2 Shard Notes

## Scope

- Evaluated 54 assigned `agent` rows from `harness_lifecycle/codex_analysis/shards/agent-2.input.jsonl`.
- Wrote exactly one row-level JSON object per input row to `harness_lifecycle/codex_analysis/shards/agent-2.row_evaluations.jsonl`.
- Did not edit coordinator-owned artifacts, source CSV/catalog/ledger files, or reference harness submodules.

## Assumptions

- CSV/shard fields are the primary evidence. Supporting files were inspected only where descriptions were truncated, empty, placeholder-only, or where local overlap changed the verdict.
- `merge` means preserve the useful behavior but fold it into an existing local skill/agent/workflow or into a candidate cluster; it does not imply adopting a separate agent file.
- `adopt` is used only where the capability is already local and strong, or where the inspected reference body is directly useful for this harness with minor adaptation.
- Scores measure usefulness for this repo's reusable Codex/Claude harness, not whether the source agent might be excellent in a different domain.

## Evidence Inspected

- Required files: `AGENTS.md`, `harness_lifecycle/codex_analysis/session-goal.md`, and the agent-2 input JSONL.
- Repo context: `.codex/project/brief.md`, `.codex/project/repo-map.md`, `.codex/project/docs-index.md`, `.codex/project/verification.md`, `.codex/project/invariants.md`, `.codex/rules/core/03-ak-guidelines.md`, `.beads/beads.md`, and `harness_learnings/coding-harness-best-practices.md`.
- Local overlap: `.codex/agents/spec-reviewer.toml`, `.codex/agents/implementer.toml`, `.codex/agents/code-reviewer.toml`, `.codex/agents/docs-researcher.toml`, `.codex/skills/test-driven-development/SKILL.md`, `.codex/skills/subagent-driven-development/SKILL.md`, `.codex/skills/document-review/SKILL.md`, `.codex/skills/planning/SKILL.md`, `.codex/skills/brainstorming/SKILL.md`, `.codex/skills/systematic-debugging/SKILL.md`, `.codex/skills/verification-before-completion/SKILL.md`, `.codex/skills/use-codex/SKILL.md`, `.codex/skills/codebase-architecture-research/SKILL.md`, and `.codex/skills/html-artifact/SKILL.md`.
- Supporting catalogs: `harness_lifecycle/catalogs/*.json` for exact source names, descriptions, and canonical paths.
- Reference bodies for ambiguous placeholder rows: `reference_harnesses/claude-plugins-official/plugins/plugin-dev/agents/agent-creator.md`, `plugin-validator.md`, `skill-reviewer.md`, plus `plugins/skill-creator/skills/skill-creator/agents/analyzer.md`, `comparator.md`, and `grader.md`.

## Weak Or Risky Rows

- Empty or placeholder catalog descriptions: `agent:analyzer`, `agent:comparator`, `agent:grader`, `agent:agentcreator`, `agent:pluginvalidator`, and `agent:skillreviewer`. Reference bodies clarified them; `plugin-validator` and `skill-reviewer` scored much higher than their CSV descriptions implied.
- Generic persona rows: `agent:seniorsoftwareengineer` and `agent:technicalctoadvisor` add little over existing AGENTS/rules/planning/review guidance.
- Domain/toolchain-specific rows rejected or deferred for fit: healthcare, SEO, Figma visual sync, PyTorch, data migrations, and web E2E. These may be strong in domain repos but are not core harness capabilities here.
- The GAN planner/generator/evaluator trio is an interesting feedback-loop pattern, but the generator/planner duplicate local implementer/planning flows and are too app-centric.

## Likely Cluster Relationships

- `test-first-and-characterization-testing`: `tdd-guide` and `test-engineer` should merge into the existing TDD skill rather than become separate agents.
- `cli-agent-readiness` and `agent-native-cli-readiness`: likely adjacent clusters; coordinator may merge them if the final recommendation is a single agent/tooling-readiness review lens.
- `document-review-design-product-lenses`, `requirements-flow-and-spec-review`, and `requirements-prd-planning`: all extend requirements/planning review, but solve different review moments.
- `harness-docs-drift-review`: the five Claude workflow drift agents should collapse into one parameterized docs-drift workflow using docs-researcher/use-codex.
- `open-source-release-prep`: forker, sanitizer, and packager should be reviewed together; sanitizer is the highest-value component.
- `skill-eval-benchmark-analysis`: analyzer, comparator, and grader are complementary parts of a possible future skill-eval harness.
- `prompt-authoring-agent-and-skill-development`, `plugin-validation`, and `skill-quality-review` are related plugin/skill authoring capabilities; plugin-validator and skill-reviewer are the strongest direct candidates.

## Issues And Concerns

- Several source rows are thin enough that row-level scores depend heavily on inspected reference bodies; the merged synthesis should preserve that caveat.
- Some rows from external harnesses assume Claude Code plugin file formats and should be adapted before Codex-native adoption.
- Local repo already has strong lean-workflow guidance; adopting duplicate persona agents would increase routing/context cost without clear benefit.

## 2026-07-15 Agent-Skills Increment

- Refreshed `agent:testengineer` after reading `reference_harnesses/agent-skills/agents/test-engineer.md`.
- Appended `agent-skills` provenance without changing historical shallow judgments or the canonical description.
- Historical Fable evaluation predates the broader source variant; the deep evaluation now records that limitation.
