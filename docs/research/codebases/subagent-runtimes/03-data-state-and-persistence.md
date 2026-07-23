# Data, state, and persistence

## Identity models

### Claude Code

A Claude subagent definition has a stable `name`, but every invocation creates a separate runtime `agentId`. A caller can also assign a runtime display/addressing `name`. Completion output returns the ID for later continuation.

The runtime records agent metadata including type, parent agent, depth, spawn mode, description/name, tool-use ID, model override, worktree, and fork information. The exact 2.1.217 compiled runner writes this metadata separately from streamed sidechain messages.

Current Claude behavior lets `SendMessage` address an agent by ID or current name. A completed agent can auto-resume under the same ID; name reuse is guarded so a stale name does not silently address a newer agent.

Source: [Resume subagents](https://code.claude.com/docs/en/sub-agents#resume-subagents).

### Codex

Codex gives every child a `ThreadId`. V1 also reserves a nickname. V2 additionally reserves a canonical `AgentPath` derived from the task tree. Registry metadata contains:

- thread ID;
- canonical path;
- nickname;
- role;
- last task message.

Reservations use RAII: if spawn fails before commit, the reserved path/nickname/count is rolled back. A committed entry is added to the root-scoped agent tree.

Source: [`AgentRegistry`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/agent/registry.rs#L16-L105) and [reservation/commit](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/agent/registry.rs#L197-L353).

## Context state

### Claude named agent

The default context is isolated from the parent's transcript. It contains the agent system prompt, delegation task, environment context, CLAUDE.md hierarchy and initial git status for most agents, preloaded skill contents, and optionally a sibling roster. It does not inherit files already read, previously invoked skills, the main output style, or main auto-memory.

The child's context window is determined by its own model. This makes model routing a context-capacity choice as well as a price/capability choice.

### Claude fork

A fork receives the parent conversation history, system prompt, tools, model, and prompt cache. It does not take a named agent's model or prompt. Forks cannot fork again, although they can spawn named subagents.

Source: [Fork the current conversation](https://code.claude.com/docs/en/sub-agents#fork-the-current-conversation).

### Codex fresh child

`build_agent_spawn_config` clones the live parent turn config, base instructions, model/provider selection, reasoning settings, environment selections, and execution policy, then applies spawn/role/runtime precedence. The initial inter-agent communication is the task's first input.

Source: [`build_agent_spawn_config`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents_common.rs#L154-L191).

### Codex forked child

Codex forks from the durable parent rollout, not merely an in-memory message slice. It first materializes and flushes parent persistence. Last-N truncation is turn-aware. Fork filtering preserves selected response items and contextual state, with full-history and partial-history behavior distinguished in source.

Source: [`fork_agent`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/agent/control/spawn.rs#L428-L582).

## Persistence

### Claude

Subagent messages are stored separately from the main transcript at:

```text
~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl
```

They survive main-context compaction and Claude Code restarts when the parent session is resumed. Cleanup follows `cleanupPeriodDays`, default 30 days. Auto-compaction is recorded in the sidechain JSONL.

Source: [Resume and persistence](https://code.claude.com/docs/en/sub-agents#resume-subagents) and [Auto-compaction](https://code.claude.com/docs/en/sub-agents#auto-compaction).

### Codex

Each child is a real Codex thread with its own rollout and session source. The root thread manager records spawn edges and parent/fork IDs. The shared AgentControl inherits environment snapshots and the execution policy, enabling unloaded V2 agents to be restored from stored rollout state.

V2 residency is bounded independently from execution concurrency. When a residency slot is needed, Codex may LRU-unload a child only if it is completed/errored/interrupted, has no active turn, and has no pending mailbox items.

Sources: [`AgentControl`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/agent/control.rs#L88-L148), [`spawn_agent_internal`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/agent/control/spawn.rs#L230-L426), and [V2 residency](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/agent/control/residency.rs#L47-L149).

## What a matrix should persist

Do not make runtime IDs part of the static agent matrix. Persist these separately:

```text
Static catalog
  role_id
  capability_policy_id
  execution_profile_id
  adapter version

Invocation record
  runtime (claude | codex)
  resolved definition/role
  requested and resolved model/effort
  context policy
  runtime agentId/threadId/path
  effective permission/capability summary
  parent identity
```

**INFERENCE.** Recording both requested and resolved metadata is necessary because both runtimes may override or reject the request based on parent state, allowlists, a role pin, or context-fork rules.
