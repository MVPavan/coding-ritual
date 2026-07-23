---
name: agent-matrix
description: Select, validate, and invoke Codex or Claude Code subagents from the repository Agent Matrix catalog. Use when choosing a subagent model, reasoning effort, context mode, capability configuration, or skill set; when rejecting undeclared values; or when testing subagent runtime support without creating Cartesian agent-definition files.
---

# Agent Matrix

Use `docs/research/codebases/subagent-runtimes/agent-matrix-values.yaml` as the
only selectable-value registry. Never copy its model, effort, capability, or
skill lists into prompts or agent definitions.

## Resolve A Codex Invocation

1. Identify the requested role or task prompt.
2. Select only values present in the catalog.
3. Run the deterministic validator before spawning:

   ```bash
   python3 tools/agent-matrix/agent_matrix.py validate-selection \
     --provider codex \
     --model <model> \
     --effort <effort> \
     --context <fresh|full|last_n_turns>
   ```

4. Compare the static selection with `codex debug models`. Treat the live model
   catalog, active `spawn_agent` schema, and backend acceptance as separate
   evidence layers.
5. If no model or effort is requested, omit both and inherit the parent
   configuration. If a model is requested without effort, allow that model's
   live default effort.

Reject undeclared values. Do not silently substitute a nearby model, effort,
capability, skill, or context mode.

## Map To `spawn_agent`

Always set `fork_turns` explicitly:

- Fresh context: `fork_turns: "none"`
- Full parent history: `fork_turns: "all"`
- Last N turns: pass N as a positive integer string, such as `"10"`

For `fork_turns: "all"`, omit `agent_type`, `model`, and `reasoning_effort`;
full-history forks inherit them. Active surfaces may reject an override or
silently ignore it, so acceptance is not proof that it took effect. For fresh
or last-N context, pass catalog-validated `model` and `reasoning_effort` when
requested.

The active tool contract controls which fields can be sent. Do not send
`service_tier` or any other source-supported field when the current
`spawn_agent` schema omits it.

## Route Capabilities Correctly

Only role, model, reasoning effort, context, task name, and task message are
direct spawn selections in the current Codex surface.

- Sandbox mode, approval policy, permission profile, and working directory are
  parent boundaries inherited by the child.
- Skills, MCP servers, web search, tools, hooks, and other stable behavior
  belong in parent or custom-role configuration.
- Codex has no Claude-style per-spawn tool allowlist.
- Never claim a configured capability became effective without a trustworthy
  runtime observation.

Do not create one permanent agent file per matrix combination. Use a focused
role prompt plus invocation-time model, effort, and context selection.

## Test The Matrix

Generate the Codex test plan:

```bash
python3 tools/agent-matrix/agent_matrix.py plan-codex \
  --tool-model gpt-5.6-sol \
  --tool-model gpt-5.6-terra \
  --output scratchpad/agent-matrix/codex-plan.json
```

Replace the example `--tool-model` values with every model advertised by the
active `spawn_agent` schema. The planner requires this explicit evidence and
does not infer tool exposure from the broader CLI model catalog.

Run one tracer spawn first. Continue with the broad matrix only after the
child rollout's first `turn_context` confirms the effective model and effort.

Classify each case as `pass`, `fail`, `unsupported`, `untestable`, or
`infra_error`. A successful spawn return alone does not prove the effective
child configuration.
