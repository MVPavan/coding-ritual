# agent-skills-other Row Evaluation Notes

## Scope

- Incremental Codex-only review of the 16 new non-skill canonical rows from `agent-skills`.
- Inputs: canonical files under `reference_harnesses/agent-skills/`, read only.
- Output: one 26-field deep evaluation per input row.
- Existing canonical overlaps are refreshed in their historical shards, not duplicated here.

## Provenance

- Fable did not evaluate this expansion; the explicit `not_evaluated` sentinel is preserved.
- Codex shallow judgments and deep rubric scores were derived from the current source files.
- Local comparisons used `.claude/`, `.codex/`, `mvp-harness/plugins/`, the harness-evaluate workflow, and the lean harness canon.
- No ledger status is implied by a row verdict or cluster placement.

## Cluster Placement Summary

- Code review: `command:review`.
- Safe simplification: `command:codesimplify`, `hook:simplifyignoresh`.
- Testing and verification: `command:test`.
- Planning and requirements: `command:spec`.
- Multi-review convergence: `command:ship`.
- Legacy command shims and umbrella packaging: `command:build`, `plugin:agentskills`.
- Web quality and performance: `agent:webperformanceauditor`, `command:webperf`.
- Context and cost controls: both SDD cache hooks.
- Session lifecycle: `hook:sessionstartsh`.
- Hook implementation fixtures: both `*-test.sh` rows.
- Skill authoring: `rule:skillscontributing`.

## Risks And Uncertainties

- Web-performance auditing is materially useful but situational and tool-dependent, so it is deferred rather than rejected.
- The two cache hooks are rejected because HTTP freshness does not establish prompt-response suitability.
- Test scripts remain evaluated for traceability but are rejected as non-production capabilities.
- The `simplify-ignore` mechanism has unacceptable working-tree mutation and abnormal-termination risk.
