# Agent Matrix Codex Validation Plan

## Goal And Scope

Implement the approved Agent Matrix validation requirements in
`docs/brainstorms/2026-07-23-agent-matrix-validation-requirements.md`.

This plan covers shared skill routing, deterministic catalog validation, Codex
spawn/config probes, Claude review of the Claude-facing skill, and evidence
reporting. It does not execute Claude's full model matrix.

## Assumptions

- The compact YAML remains the static selectable-value catalog.
- The live Codex catalog is authoritative for model-effort compatibility.
- The active `spawn_agent` schema is authoritative for tool-exposed fields and
  advertised model overrides.
- Full value coverage is required; a Cartesian product across unrelated
  capability dimensions is not.
- Current local Codex behavior takes precedence over newer release notes.

## Files

Create:

- `.codex/skills/agent-matrix/SKILL.md`
- `.codex/skills/agent-matrix/agents/openai.yaml`
- `.claude/skills/agent-matrix/SKILL.md`
- `tools/agent-matrix/agent_matrix.py`
- `tools/agent-matrix/test_agent_matrix.py`

Modify only if independent runtime source or official schema evidence proves
the catalog is wrong:

- `docs/research/codebases/subagent-runtimes/agent-matrix-values.yaml`
- `docs/research/codebases/subagent-runtimes/00-index.md`

Generated runtime evidence stays under `scratchpad/agent-matrix/`.

## Execution

1. Implement the smallest parser and validator.
   - Load the compact YAML with duplicate-key rejection.
   - Resolve common and Codex-specific values.
   - Reject unknown provider, model, effort, context, capability, or skill.
   - Verify with focused unit tests.

2. Add live Codex inventory and test-plan generation.
   - Parse `codex debug models`.
   - Compare visible models with the static catalog.
   - Capture the active `spawn_agent` contract separately.
   - Label values `catalog_visible`, `tool_exposed`, and `backend_accepted`
     without conflating them.
   - Generate every valid visible model-effort pair.
   - Generate per-value config and context probe cases.
   - Verify deterministic case IDs and expected coverage counts.
   - Add equivalence-class cases for `task_name`, `message`, `agent_type`, and
     full-history override rejection.

3. Create both skill entry points.
   - Keep selection and error rules common.
   - Put Codex spawn/config routing only in the Codex skill.
   - Put Claude named-agent/fork routing only in the Claude skill.
   - Validate the Codex skill with the skill-creator validator.

4. Ask Claude Code to review and update only its skill file.
   - Provide the catalog, official Claude subagent contract, and exact edit
     boundary.
   - Inspect the resulting diff and reject unrelated changes.
   - Revalidate frontmatter and referenced paths.
   - Preserve Claude version, review prompt, verdict, and focused diff under
     `scratchpad/agent-matrix/`.
   - Verify discovery from a fresh Claude process.

5. Run a tracer-bullet Codex probe.
   - One low-cost fresh-context spawn on a visible model/effort pair.
   - One static configuration probe.
   - Locate the child rollout and confirm its first `turn_context` records the
     effective model and effort.
   - Stop broad execution as `untestable` if that evidence is unavailable.

6. Execute the Codex model-effort matrix.
   - Attempt every catalog-visible valid pair with `fork_turns: none`.
   - Distinguish tool-advertised pairs from compatibility probes for models the
     active tool contract does not advertise.
   - Use a minimal deterministic response task.
   - Record tool acceptance, terminal status, and effective model/effort from
     child rollout metadata.
   - Classify unsupported pairs without retry loops.

7. Execute context, service-tier, and capability probes.
   - Test fresh, full, and last-N context behavior.
   - Test each service-tier value by strict configuration parsing. Record
     per-spawn selection as unsupported when the active tool omits that field.
   - Test sandbox, approval, permission, web, MCP, skill, and tool inheritance
     through their owning config/debug surfaces.
   - Use parse-only probes for privilege-expanding sandbox, approval, and
     permission values.
   - Include invalid-value negative cases.

8. Produce and verify evidence.
   - Write machine-readable JSONL and a concise Markdown summary under
     `scratchpad/agent-matrix/`.
   - Check that every planned case has one terminal classification.
   - Allow one bounded retry for `infra_error`; never count it as runtime
     support.
   - Run Python compilation, unit tests, skill validation, YAML parsing, and
     repository structural checks.

## Risks

- Model access and supported efforts are account- and session-specific.
- Spawn acceptance may not prove the effective backend configuration.
- Full-history forks intentionally restrict model and effort overrides.
- Capability configs may be syntactically valid but behaviorally constrained by
  the parent sandbox or managed policy.
- Exhaustive live inference can hit rate or concurrency limits; classify these
  as `infra_error`, separately from schema rejection.
- Account-specific runtime results never mutate the static catalog without
  independent schema or source evidence.

## Verification

- `python3 -m py_compile tools/agent-matrix/agent_matrix.py`
- `python3 -m unittest tools/agent-matrix/test_agent_matrix.py`
- `python3 tools/agent-matrix/agent_matrix.py validate-skills`
- Strict YAML parse of both skill frontmatters and the catalog
- Live `codex debug models`
- Fresh Codex and Claude skill-discovery probes
- Result coverage command reports zero missing or duplicate terminal cases
- `bd ready` and final `git status`
