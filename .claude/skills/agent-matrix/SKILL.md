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
3. Run the shared deterministic validator (requires PyYAML; use `uv run`):

   ```bash
   uv run python tools/agent-matrix/agent_matrix.py validate-selection \
     --provider claude \
     --model <model> \
     --effort <effort> \
     --context <fresh|full>
   ```

4. If no model or effort is requested, inherit the current session defaults.
5. Reject undeclared values. Do not silently substitute a nearby value.

## Know Which Layer A Value Belongs To

Claude splits the catalog across two surfaces. Catalog membership alone does
not make a value usable at invocation time.

**Invocation layer** — the live Agent tool. Verified on Claude Code `2.1.220`,
it accepts only `subagent_type`, `prompt`, `description`, `model`,
`run_in_background`, and `isolation`. Its `model` field is a short-alias enum:
`sonnet | opus | haiku | fable`. Full model IDs and `inherit` are rejected with
`InputValidationError`, not silently coerced.

**Definition layer** — `.claude/agents/<name>.md` frontmatter, or an ephemeral
`--agents` definition. This is the only place `tools`, `disallowedTools`,
`permissionMode`, `memory`, `skills`, `mcpServers`, `hooks`, and `effort` can be
set, and the only place full model IDs such as `claude-opus-4-8` work.

An invocation-time `model` overrides the definition's model. Never promise an
effort, tool, permission, skill, or MCP change through the Agent tool alone —
that requires a definition.

## Choose Context

- Fresh context: invoke a named subagent. It receives its own system prompt and
  the delegation message, not the parent conversation history. Verified.
- Full context: a fork, which inherits the whole conversation, system prompt,
  tools, and model. Two distinct paths, and they are not interchangeable:
  - **`/subtask`** — the user starts it, works on `2.1.212+` regardless of any
    env var. This is the reliable path.
  - **`subagent_type: fork`** — Claude spawning a fork itself. Gated behind
    fork mode (`CLAUDE_CODE_FORK_SUBAGENT=1`, or a staged rollout), and
    experimental. With fork mode off, the type is absent from the agent
    registry and the spawn fails with `Agent type 'fork' not found` (observed
    on `2.1.220`).

  So report full context as *available to the user via `/subtask`* but
  *unavailable to Claude* unless `fork` appears in the session's agent list.
  Never substitute a fresh subagent with a pasted summary for either.
  Note that fork mode also forces every subagent into the background.
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

All of these are definition-layer fields. Resolve tools against the parent pool
and Claude's named-subagent filters. Background subagents have a smaller
built-in tool set. Reject a tool list when none of its entries resolves to an
available tool.

**A declared tool list is not the effective tool list.** Two separate filters
apply, and only one is documented:

- *Documented:* subagents run in the background by default, and a background
  subagent keeps only a fixed built-in set — the catalog's
  `background_builtin_values`. Every other built-in is removed silently, even
  when named in `tools`, so one definition resolves differently in foreground
  and background.
- *Undocumented, observed on `2.1.220`:* when `Bash` appears in a definition's
  `tools`, `Grep` and `Glob` are dropped from the child's resolved set. The
  child cannot call them. Reproduced on three definitions across two models;
  the same lists without `Bash` kept both tools. The docs do not describe this,
  and `Grep`/`Glob`/`Bash` all survive the documented background filter.

Treat requested and effective capability as separate evidence, and confirm the
effective set from inside the child when it matters.

`effort` accepts `low`, `medium`, `high`, `xhigh`, `max` — available levels
depend on the model, and it is definition-only, with no invocation-time
equivalent. It is not observable from within a child, so record it as
requested-but-unverified, never as confirmed.

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
