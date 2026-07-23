---
name: agent-matrix
description: Select, validate, and invoke Claude Code or Codex subagents from the repository Agent Matrix catalog. Use when choosing a subagent model, effort, context mode, tool access, permission mode, capability configuration, or skill set; when rejecting undeclared values; or when testing runtime support without creating Cartesian agent-definition files.
---

# Agent Matrix

Use `docs/research/codebases/subagent-runtimes/agent-matrix-values.yaml` as the
only selectable-value registry. Never copy its model, effort, capability, or
skill lists into prompts or permanent agent definitions.

## Resolve A Claude Invocation

1. Identify the requested role prompt and task.
2. Select only values present in the catalog.
3. Run the shared deterministic validator:

   ```bash
   python3 tools/agent-matrix/agent_matrix.py validate-selection \
     --provider claude \
     --model <model> \
     --effort <effort> \
     --context <fresh|full>
   ```

4. If no model or effort is requested, inherit the current session defaults.
5. Reject undeclared values. Do not silently substitute a nearby value.

## Choose Context

- Fresh context: invoke a named subagent. It receives its own system prompt and
  the delegation message, not the parent conversation history.
- Full context: use a forked subagent through `/subtask` or the `fork` subagent
  type when that surface is available.
- Last N turns: unsupported by Claude Code. Do not pretend a prompt summary is
  equivalent to a native partial fork.

A fork inherits the parent's model, tools, system prompt, and full history.
Do not promise model, effort, tool, or permission overrides on a fork.

## Apply Claude Capabilities

Map catalog selections to Claude subagent fields:

- tool allowlist: `tools`
- tool denylist: `disallowedTools`
- permission mode: `permissionMode`
- persistent memory: `memory`
- background execution: `background`
- worktree isolation: `isolation`
- skills: `skills`
- MCP servers: `mcpServers`
- scoped hooks: `hooks`

Resolve tools against the parent pool and Claude's named-subagent filters.
Background subagents have a smaller built-in tool set. Reject a tool list when
none of its entries resolves to an available tool.

Use an invocation-time model override when the active Agent tool supports it.
Use an ephemeral `--agents` definition when the requested effort or capability
must be fixed before the session starts. Do not create a permanent file for
each model-effort-capability combination.

## Preserve Role Prompts

Keep detailed role behavior in one role prompt, independent of runtime
metadata. Apply model, effort, context, tools, permissions, skills, and MCP
selection around that prompt at invocation time.

Report which values were:

- selected from the static catalog
- accepted by the active Claude Code surface
- inherited rather than overridden
- rejected or unavailable
