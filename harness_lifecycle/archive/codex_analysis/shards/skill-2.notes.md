# skill-2 shard notes

## Assumptions

- Evaluated only `harness_lifecycle/codex_analysis/shards/skill-2.input.jsonl`.
- Used CSV fields first; supporting inspection was limited to local `.codex/.claude` skill inventory, `AGENTS.md`, project verification/invariants docs, `.beads/beads.md`, and catalog index hits for ambiguous source/overlap checks.
- Treated `reference_harnesses/` as read-only; no submodule internals were opened or edited.
- Treated exact `in_ours`/local skill matches as adoption candidates unless a row was a weaker duplicate of an existing local capability.

## Evidence inspected

- `AGENTS.md`
- `.codex/project/brief.md`, `repo-map.md`, `docs-index.md`, `verification.md`, `invariants.md`
- `.codex/rules/core/03-ak-guidelines.md`
- `.codex/skills/` and `.claude/skills/` inventories
- `.beads/beads.md` and `bd prime` attempted; `bd` was not installed in this environment
- `harness_lifecycle/codex_analysis/session-goal.md`
- `harness_lifecycle/codex_analysis/shards/skill-2.input.jsonl`
- `harness_lifecycle/catalogs/*.json` only for source-path confirmation on selected ambiguous rows

## Weak rows

- `skill:verificationloop` was rejected after review because the row is vague and fully dominated by local `verification-before-completion` plus project verification docs.
- `skill:agenticengineering` was rejected after review because it is broad operating-model advice already covered by stronger local rules and skills.
- `skill:loopme`, `skill:writingskills`, and `skill:writingplans` are thin but have usable trigger language for stronger clusters.
- `skill:knowledgeops`, `skill:opensourcepipeline`, `skill:sessionreport`, `skill:agenteval`, and technology-specific rows were deferred where they require infrastructure, telemetry, or project-type demand not shown by this repo.

## Likely cluster relationships

- `adversarial-design-review`: `skill:grillme`, `skill:loopme`
- `agent-session-handoff`: `skill:handoff`, `skill:strategiccompact`
- `implementation-planning`: `skill:planning`, `skill:productcapability`, `skill:writingplans`
- `plugin-authoring`: `skill:pluginsettings`, `skill:pluginstructure`, with `skill:mcpintegration` adjacent
- `skill-authoring`: `skill:skillcreator`, `skill:skilldevelopment`, `skill:writinggreatskills`, `skill:writingskills`
- `harness-quality-evals`: `skill:skillcomply`, `skill:skillstocktake`, adjacent to `skill:agenteval`
- `review-feedback-discipline`: `skill:receivingcodereview`, `skill:requestingcodereview`, `skill:resolveprfeedback`, `skill:review`
- `test-first-development`: `skill:testdrivendevelopment`, `skill:tdd`, `skill:pythontesting`
- `verification-gate`: `skill:verificationbeforecompletion`, `skill:verificationloop`, with `skill:terminalops` adjacent
- `workspace-surface-audit`: `skill:workspacesurfaceaudit`, `skill:automationauditops`, adjacent to `skill:agentsort`

## Issues

- The project brief references `my_harness/`, but this checkout has `mvp-harness/`; overlap notes therefore rely on `.codex/.claude` and visible `mvp-harness/` structure.
- `bd` was not on `PATH`, so Beads runtime context could not be recovered with `bd prime`.

## agent-skills incremental provenance

- `skill:testdrivendevelopment` now also represents the `agent-skills` variant at `reference_harnesses/agent-skills/skills/test-driven-development/SKILL.md`.
- Only its `harnesses` value changed in the shard input; its historical description and Fable/GPT shallow judgments were preserved.
- The deep evaluation now accounts for the new variant's prove-it, DAMP, test-resource, browser-verification, and subagent-testing guidance while retaining the local risk-calibrated skill as canonical.
- Historical Fable evaluation predates the `agent-skills` source and must not be read as an evaluation of that newer variant.
