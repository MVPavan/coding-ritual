---
name: agent-matrix
description: Use when choosing or validating how a subagent is spawned — its model, effort, context mode, tools, permission mode, memory, skills, or MCP access — when a requested model or effort level may not exist, or when a spawn is supposed to guarantee an effort, tool, or permission setting.
---

# Agent Matrix

`docs/research/codebases/subagent-runtimes/agent-matrix-values.yaml` is the only
registry of selectable values. Read them from it; never copy its model, effort,
capability, or skill lists into a prompt or a permanent agent definition.

## Resolve a Claude invocation

1. Name the role prompt and the task.
2. Select only values the catalog declares. Reject an undeclared value instead
   of substituting a nearby one.
3. Validate deterministically before spawning:

   ```bash
   uv run python tools/agent-matrix/agent_matrix.py validate-selection \
     --provider claude --model <model> --effort <effort> --context <fresh|full>
   ```

   `--capability` and `--skill` validate the other dimensions.
4. Inherit the session defaults when no model or effort is requested.

Done when every value you will pass has been accepted by `validate-selection`
and placed in a layer that can carry it.

## Know which layer a value belongs to

Catalog membership alone does not make a value usable at spawn time.

**Invocation layer** — the live Agent tool. Verified on Claude Code `2.1.220`,
it accepts only `subagent_type`, `prompt`, `description`, `model`,
`run_in_background`, and `isolation`. Its `model` field is a short-alias enum:
`sonnet | opus | haiku | fable`. Full model IDs and `inherit` are rejected with
`InputValidationError`, not silently coerced.

**Definition layer** — `.claude/agents/<name>.md` frontmatter, or an ephemeral
`--agents <json>` definition on a `claude` run. Every capability under
`capabilities.claude` in the catalog — tools, denylist, permission mode, memory,
background, isolation, hooks — plus `skills`, `mcpServers`, `effort`, and full
model IDs, is settable only here.

An invocation-time `model` overrides the definition's model. Never promise an
effort, tool, permission, skill, or MCP change through the Agent tool alone —
that requires a definition.

Three reaches in this repo:

- **Agent tool** — `subagent_type` names a definition in `.claude/agents/`;
  `model` may override its model.
- **Ephemeral definition** — `--agents <json>` on a `claude` run, when a
  capability must be fixed before the session starts.
- **Independent process** — `claude -p --model <id> --effort <level>`, when the
  work needs its own session rather than a child turn.

Do not create a permanent definition file per model-effort-capability
combination.

## Choose context

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

## Separate requested capability from effective capability

Resolve a tool list against the parent tool pool and Claude's named-subagent
filters; reject it when none of its entries resolves to an available tool.
**A declared tool list is not the effective tool list.** Two filters apply, and
only one is documented:

- *Documented:* subagents run in the background by default, and a background
  subagent keeps only the catalog's `background_builtin_values`. Every other
  built-in is removed silently, even when named in `tools`, so one definition
  resolves differently in foreground and background.
- *Undocumented, observed on `2.1.220`:* when `Bash` appears in a definition's
  `tools`, `Grep` and `Glob` are dropped from the child's resolved set. The
  child cannot call them. Reproduced on three definitions across two models;
  the same lists without `Bash` kept both tools. The docs do not describe this,
  and `Grep`/`Glob`/`Bash` all survive the documented background filter.

When the task depends on a tool either filter can strip, have the child report
its own effective tool set before trusting the declaration.

`effort` is definition-only, with no invocation-time equivalent, and which
levels a model accepts varies by model. It is not observable from within a
child, so record it as requested-but-unverified, never as confirmed.

## Preserve role prompts

Keep detailed role behavior in one role prompt, independent of runtime
metadata. Apply model, effort, context, tools, permissions, skills, and MCP
selection around that prompt at invocation time.

Report which values were:

- selected from the static catalog
- accepted by the active Claude Code surface
- inherited rather than overridden
- rejected or unavailable
