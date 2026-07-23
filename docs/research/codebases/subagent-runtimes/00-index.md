# Claude Code and Codex subagent internals

Research date: 2026-07-22

Locally verified versions: Claude Code 2.1.217; Codex CLI 0.144.4

Purpose: establish the source-level facts needed before designing a cross-harness agent matrix.

## Executive finding

An agent should not be modeled as one flat record containing every possible option. The two runtimes combine the same concerns at different points and with different precedence rules.

Use four conceptual layers:

1. **Role** — stable identity, delegation description, behavioral instructions.
2. **Capability policy** — tools, MCP servers, skills, permissions, isolation.
3. **Execution profile** — provider, model, reasoning/effort, service tier.
4. **Invocation** — task, context fork mode, foreground/background mode, and runtime limits.

That split is not merely aesthetic:

- In Codex 0.144.4, explicit spawn-time model/reasoning values are applied first and the named role config is applied afterward. A role file containing `model` or `model_reasoning_effort` therefore pins that value. Codex even describes it to the model as a setting that “cannot be changed.”
- In Claude Code 2.1.217, a model can be overridden on an individual Agent invocation, but the shipped Agent input contract has no per-invocation `effort`. Effort is an agent-definition value or is inherited from the session.
- Codex reapplies live runtime approval, permission-profile, and working-directory values after applying a role config. A role is not an independent permission boundary.
- Claude named subagents have first-class per-agent tool allow/deny lists, permission mode, MCP servers, skills, hooks, memory, background mode, and worktree isolation.

## Evidence labels

This report uses four labels deliberately:

- **VERIFIED — readable source:** traced in the tagged Codex Rust implementation.
- **VERIFIED — public contract:** stated by current official product documentation or shipped type declarations.
- **VERIFIED — compiled bundle:** observed in the exact Claude Code 2.1.217 executable's embedded minified JavaScript. Names are unstable; only behavior visible in the code path is reported.
- **INFERENCE:** architectural interpretation rather than a directly encoded guarantee.

Claude Code's core implementation is not published as readable source in its public repository or npm package. The deepest defensible Claude trace therefore combines the public contract, the exact npm type declarations, the exact executable's bundle, and live CLI behavior. This report does not invent a public source call graph that does not exist.

## The shortest useful comparison

| Concern | Claude Code 2.1.217 | Codex 0.144.4 |
|---|---|---|
| Definition | Markdown body plus strict YAML frontmatter | TOML role metadata plus a flattened full `ConfigToml` overlay |
| Project scope | `.claude/agents/**/*.md` | `.codex/agents/**/*.toml` |
| Invocation tool | `Agent` (`Task` remains an alias) | `spawn_agent` plus send/follow-up/wait/interrupt/list tools |
| Default named-agent context | Fresh isolated context | V1 fresh unless `fork_context`; V2 currently defaults `fork_turns` to `all` |
| Per-invocation model | Yes | Yes, unless a role pins it or V2 performs a full-history fork |
| Per-invocation effort | No field in shipped Agent input | Yes, unless a role pins it or V2 performs a full-history fork |
| Per-agent tool allow/deny | Yes | No equivalent first-class role field in 0.144.4; a role is a broad config overlay |
| Permission behavior | Parent permissions inherited; constrained frontmatter override rules | Parent turn approval and permission profile reapplied after the role |
| Persistence | Sidechain JSONL per agent ID | Separate persisted Codex thread/rollout with parent and spawn-edge metadata |
| Nested agents | Supported to documented depth 5 | V1 enforces configured depth; V2 source exposes tools at all depths and uses other capacity controls |

## Critical matrix rules

1. Keep `role_id` independent from `execution_profile_id`.
2. If the matrix owns Codex model/effort routing, omit `model` and `model_reasoning_effort` from the Codex role file.
3. Treat Claude effort as definition/session-bound, not invocation-bound.
4. Represent context policy explicitly. For Codex V2, a model/effort/role selection requires `fork_turns = "none"` or a positive turn count; the default full fork rejects those overrides.
5. Represent effective permissions, not requested permissions. Both runtimes constrain child permissions using parent/runtime state.
6. Version every adapter. Current Claude documentation and the exact 2.1.217 bundle already disagree about whether the depth limit has a latent environment override, and current Codex documentation includes agent defaults not present in the installed 0.144.4 schema.

## Report map

- [01-core-architecture.md](01-core-architecture.md) — definition, discovery, and runtime components.
- [02-runtime-lifecycle.md](02-runtime-lifecycle.md) — source-level call paths for spawning, running, messaging, and completion.
- [03-data-state-and-persistence.md](03-data-state-and-persistence.md) — metadata structures, context, identity, and durable state.
- [04-integration-and-extension-points.md](04-integration-and-extension-points.md) — exact metadata fields, precedence, capabilities, and adapter implications.
- [05-operational-model.md](05-operational-model.md) — limits, safety boundaries, lifecycle controls, and failure modes.
- [90-open-questions.md](90-open-questions.md) — verified discrepancies and questions that require runtime probes or future versions.
- [agent-matrix-values.yaml](agent-matrix-values.yaml) — compact dimension-first values: models, effort levels, context modes, capability options, and project skills for Claude and Codex.
- [agent-matrix-values-expanded-reference.yaml](agent-matrix-values-expanded-reference.yaml) — preserved expanded catalog with schemas, runtime metadata, project registries, and validation design for later reference.
- [HTML explainer](html/index.html) — compact visual comparison.

## Primary sources

- [Claude Code subagent documentation](https://code.claude.com/docs/en/sub-agents)
- [`@anthropic-ai/claude-code` 2.1.217 tarball](https://registry.npmjs.org/@anthropic-ai/claude-code/-/claude-code-2.1.217.tgz)
- [Claude Code public repository](https://github.com/anthropics/claude-code)
- [Codex `rust-v0.144.4` source tree](https://github.com/openai/codex/tree/rust-v0.144.4)
- [Codex role discovery](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/config/agent_roles.rs)
- [Codex V2 spawn handler](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs)
- [Codex agent-control spawn implementation](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/agent/control/spawn.rs)
