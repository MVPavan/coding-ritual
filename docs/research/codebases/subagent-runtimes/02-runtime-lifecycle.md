# Runtime lifecycle

## Claude Code named-subagent path

The following sequence combines the official contract with the exact 2.1.217 compiled runner.

1. **Selection.** Claude calls the `Agent` tool with `prompt`, a short `description`, and optionally `subagent_type`, `model`, `run_in_background`, `name`, and `isolation`. `Task` is retained as an alias for existing definitions and permission rules.
2. **Definition resolution.** The runtime resolves the named agent from managed, CLI, project, user, plugin, or built-in definitions. With no type it uses the general-purpose behavior. A fork is a distinct path rather than a normal named definition.
3. **Model resolution.** Current documented precedence is `CLAUDE_CODE_SUBAGENT_MODEL`, invocation `model`, definition `model`, then parent model. Disallowed values fall back rather than bypassing the organization's model allowlist.
4. **Context selection.** A named subagent starts fresh. A fork receives parent history/system/tools/model and shares the parent's prompt cache.
5. **Permission derivation.** The child begins from the parent tool-permission context. A definition's permission mode can narrow/change it only within documented parent-mode constraints. Background permission prompts are routed back to the main session.
6. **Startup hooks.** The compiled runner invokes `SubagentStart`, collects additional hook context, and registers definition-scoped hooks.
7. **MCP attachment.** Definition-scoped MCP servers are resolved. Named server references reuse configured connections; inline dynamic servers are connected for the run. Managed, strict, safe/bare, remote, and enterprise policies can block these additions.
8. **Tool resolution.** The runtime resolves the subagent-available inherited pool through the definition's allow/deny rules, filters scoped MCP tools through the same denial policy, and constructs the final set. If an explicitly configured tool list resolves to nothing on a new invocation, 2.1.217 refuses to launch and reports why.
9. **Prompt assembly.** The child receives its own system prompt plus environment material, the delegation task, CLAUDE.md and git-status material except for built-in Explore/Plan, preloaded skill content, and an optional named-sibling roster.
10. **Child context construction.** The runner creates a separate child tool-use context carrying the resolved tools, model, thinking configuration, MCP clients, message state, abort controller, hooks, and agent identity.
11. **Model/tool loop.** The runner streams the normal agentic loop until completion, cancellation, API failure, or `maxTurns`. Messages are written to a sidechain transcript as they arrive.
12. **Finalization.** It computes usage/tool statistics, scans the final report for instruction-shaped output, returns a foreground result or emits a background completion, runs `SubagentStop`, and cleans up dynamic MCP connections, hooks, caches, file state, and transient context.

Official sources: [model selection](https://code.claude.com/docs/en/sub-agents#choose-a-model), [capabilities](https://code.claude.com/docs/en/sub-agents#control-subagent-capabilities), [startup context](https://code.claude.com/docs/en/sub-agents#what-loads-at-startup), and [foreground/background execution](https://code.claude.com/docs/en/sub-agents#run-subagents-in-foreground-or-background).

### Claude invocation and completion contract

**VERIFIED — shipped type declarations.** `package/sdk-tools.d.ts:484-521` in the exact [`@anthropic-ai/claude-code@2.1.217` tarball](https://registry.npmjs.org/@anthropic-ai/claude-code/-/claude-code-2.1.217.tgz) defines the Agent input with:

- required `description` and `prompt`;
- optional `subagent_type`;
- optional `model` restricted by the declared SDK contract to `sonnet | opus | haiku | fable` and documented as taking precedence over frontmatter;
- optional `run_in_background`, `name`, and `isolation`;
- deprecated ignored `mode` and deprecated `team_name`.

The completion output at `package/sdk-tools.d.ts:99-200` includes `agentId`, `agentType`, text content, `resolvedModel`, optional `modelsUsed`, duration, tool count, token usage, optional detailed tool stats, original prompt, and optional worktree path. Separate output shapes report an async launch or a remote launch.

Notably absent from the invocation type: `effort`, arbitrary permission mode, tool overrides, skills, hooks, MCP servers, memory, and max turns. Those are definition/session concerns.

## Codex V2 spawn path

This is the direct readable-source call chain in tag `rust-v0.144.4`.

### 1. Tool schema

`spawn_agent_common_properties_v2` exposes `message`, `agent_type`, `fork_turns`, `model`, `reasoning_effort`, and `service_tier`; the surrounding V2 tool adds required `task_name`. `fork_turns` defaults to `all` and accepts `none`, `all`, or a positive integer string.

Source: [`spawn_agent_common_properties_v2`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents_spec.rs#L595-L635).

### 2. Parse and derive child config

`handle_spawn_agent` parses the arguments, normalizes `agent_type`, constructs the task message, computes the child depth, and clones the parent turn into a child spawn config through `build_agent_spawn_config`.

Source: [`handle_spawn_agent`, first half](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs#L40-L93).

### 3. Resolve fork and metadata precedence

- Full-history fork rejects `agent_type`, `model`, and `reasoning_effort`.
- Otherwise explicit model and effort are validated and applied.
- The named role config is applied next, so values present in the role overlay win over explicit spawn values.
- Service tier is resolved separately: supported role config value, then supported spawn request, then parent.
- Finally, the parent turn's approval policy, approval reviewer, working directory, and permission profile are reapplied.

Sources: [`handle_spawn_agent`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs#L67-L128) and [`multi_agents_common`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents_common.rs#L154-L337).

### 4. Establish identity and communication

The handler builds a `SessionSource::SubAgent` carrying parent thread, depth, role, task name, and canonical task path. It creates an inter-agent communication envelope from the parent's path to the new path and delegates to the shared root `AgentControl`.

The V2 user-facing identity is path-based: a child of `/root/task1` named `task_3` becomes `/root/task1/task_3`. Relative addressing works within a branch; canonical addressing works across branches.

### 5. Reserve capacity and instantiate/fork thread

`AgentControl::spawn_agent_internal`:

1. resolves the effective multi-agent version;
2. checks execution capacity;
3. reserves V2 residency or a V1 spawn slot;
4. reserves path/nickname metadata;
5. either creates a fresh thread or calls the fork path;
6. passes the same root-scoped `AgentControl` into the child;
7. commits the registry reservation;
8. emits the thread-created event and records the parent/child spawn edge;
9. submits the initial inter-agent communication to trigger the child's turn.

Source: [`spawn_agent_internal`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/agent/control/spawn.rs#L230-L426).

### 6. Fork path

For a fork, Codex flushes the parent rollout, reloads stored history, optionally truncates it to the last N user turns, filters it to fork-safe rollout items, strips V2 usage-hint messages, and creates a child thread with `InitialHistory::Forked` plus parent/fork metadata. Full-history forks preserve reference context that partial forks do not.

Source: [`fork_agent`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/agent/control/spawn.rs#L428-L582).

### 7. Result and ongoing communication

The spawn handler returns immediately with thread ID, task path, and optional nickname. It emits activity/telemetry separately. Follow-up and send-message operations target the registered thread/path and can trigger another turn. V2 final results are delivered through the inter-agent communication layer; V1 uses a completion watcher to send a completed status back to the parent.

## Codex V1 differences

V1's spawn schema uses `fork_context: bool`, defaulting to fresh context. V1 checks `max_depth` in the spawn handler and hides collaboration tools once the next depth would exceed the limit. It uses numeric thread IDs/nicknames rather than the V2 canonical task-path protocol.

Sources: [V1 spawn handler](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents/spawn.rs#L45-L223) and [tool depth gating](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/spec_plan.rs#L339-L352).

## The V2 full-fork trap

The 0.144.4 V2 parser treats an omitted or blank `fork_turns` as `all`. Full-history fork then rejects role/model/reasoning overrides. Therefore this apparently reasonable request is internally contradictory:

```json
{
  "task_name": "research_api",
  "agent_type": "researcher",
  "model": "gpt-5.6-terra",
  "reasoning_effort": "high",
  "message": "Trace the API"
}
```

To select that profile, the caller must also pass:

```json
{ "fork_turns": "none" }
```

or a positive string such as `"3"`. A matrix adapter must make context mode explicit; it cannot silently rely on the V2 default.
