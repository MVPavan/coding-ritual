# Operational model and limits

## Claude Code

### Nesting and count

Current official documentation says:

- nested subagents are supported;
- depth is counted below the main session;
- a depth-five agent does not receive the Agent tool;
- the depth limit is fixed and not configurable;
- the default session spawn budget is 200 and can be raised with `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION`;
- completed agents still consume the session budget.

Source: [Spawn nested subagents and session limit](https://code.claude.com/docs/en/sub-agents#spawn-nested-subagents).

The 2.1.217 binary also contains `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` and error text telling an agent to ask the user to raise it. This conflicts with the public statement that the limit is fixed. Static bundle inspection cannot prove whether the variable is reachable, experimental, test-only, or remotely gated. The matrix must treat depth 5 as the supported contract until a controlled runtime probe proves otherwise.

### Foreground/background and permissions

As of the documented 2.1.198 behavior, subagents default to background unless Claude needs the result before continuing. A definition may set `background`, and the invocation may pass `run_in_background`. Environment/session modes can force all subagents foreground or background.

Background execution changes scheduling, not authority. Permission prompts surface in the main session. API errors are returned as actual failure state, with partial output retained when available.

### Failure modes relevant to a matrix

- unknown or duplicate definition;
- configured tool allowlist resolves to zero;
- model excluded by organization allowlist, causing inherited-model fallback;
- inline MCP blocked by managed/strict/safe/remote policy;
- max-turn termination;
- session spawn budget or depth reached;
- background agent cancelled versus stopped, which changes resumability;
- requested worktree isolation fails or is cleaned up when unchanged.

## Codex

### V1 limits

V1 uses `agents.max_threads` as a total root-tree spawn-count limit while registered threads remain active, and checks `agents.max_depth` both before spawn and when constructing the collaboration tool surface. A reservation rollback prevents a failed spawn from permanently consuming a slot.

Source: [V1 spawn](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents/spawn.rs#L45-L223), [tool gating](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/spec_plan.rs#L339-L352), and [registry reservations](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/agent/registry.rs#L79-L105).

### V2 capacity model

V2 splits two concepts:

- **execution capacity:** a root-scoped limiter counts active child turns, not merely loaded threads;
- **residency capacity:** a root-scoped LRU may unload inactive completed/errored/interrupted children to make room while retaining their durable rollout.

Source: [execution limiter](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/agent/control/execution.rs#L29-L115) and [residency](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/agent/control/residency.rs#L47-L149).

The exact 0.144.4 tool planner always exposes V2 collaboration tools regardless of configured depth, and the V2 spawn handler lacks V1's explicit maximum-depth check. That is a source observation, not a recommendation to rely on unlimited nesting: [V2 is marked under development in this version](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/features/src/lib.rs#L1035-L1048), and the host/orchestrator may impose its own limits.

### Feature state versus active session

The locally installed CLI reports the stable V1 feature enabled and V2 disabled by default. The current hosted session nevertheless exposes the V2-style collaboration schema (`task_name`, `fork_turns`, canonical paths). This proves that the hosting/orchestration surface can select a collaboration implementation independently of local default CLI flags.

An agent-matrix implementation must inspect the actual runtime tool schema or capability handshake. Reading only local `config.toml`, `.codex/agents`, or `codex features` is insufficient.

### Failure modes relevant to a matrix

- unknown role or malformed role config;
- selected model not in the loaded catalog;
- reasoning effort unsupported by the selected model;
- requested/role service tier unsupported by the resolved model;
- full-history V2 fork combined with role/model/reasoning override;
- duplicate canonical task path;
- execution/residency/spawn capacity exhausted;
- child rollout unavailable for fork/resume;
- role config rejected during full ConfigTOML deserialization;
- metadata selectors hidden from the session tool schema.

## Security interpretation

Neither agent file should be treated as a standalone security principal.

- Claude computes a child permission context under the parent/session policy and managed constraints.
- Codex reapplies the parent turn's runtime approval and permission profile after role configuration.

**INFERENCE.** The matrix may express a capability *intent* such as `read_only`, but the launcher must calculate and record the effective runtime boundary. It must fail closed when it cannot express the requested restriction; it must never report a restriction merely because it appeared in a source matrix row.

## Verification inventory

The following read-only checks anchored this report:

```bash
claude --version
claude --help
claude agents --help
codex --version
codex doctor --json
npm pack @anthropic-ai/claude-code@2.1.217
readelf -S "$(command -v claude)"
strings -a "$(command -v claude)"
git clone --branch rust-v0.144.4 --depth 1 https://github.com/openai/codex.git
```

No live subagent was spawned and no paid model inference was used for the research trace.
