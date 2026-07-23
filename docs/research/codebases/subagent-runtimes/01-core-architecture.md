# Core architecture

## Claude Code

### Definition and discovery

**VERIFIED — public contract.** A custom Claude subagent is a Markdown file whose body becomes its system prompt and whose YAML frontmatter is validated as agent metadata. `name` and `description` are required. The current documented discovery precedence is:

1. managed settings;
2. session-only `--agents` JSON;
3. project `.claude/agents/` directories;
4. user `~/.claude/agents/`;
5. plugin `agents/` directories.

Project discovery walks upward from the current directory to the repository root and also considers added directories. Directories are recursive. Identity comes from frontmatter `name`, not the filename. Within nested project scopes, the closest directory wins; duplicates inside one directory tree have filesystem-order behavior and should be treated as invalid configuration.

The runtime watches existing project and user agent directories. File additions and edits become active within seconds. Creating the first agent directory after session startup still requires a restart.

Source: [Configure subagents and choose scope](https://code.claude.com/docs/en/sub-agents#configure-subagents).

### Strict definition schema

**VERIFIED — public contract and compiled bundle.** The 2.1.217 executable contains a strict object validator for agent frontmatter. Its 16 documented public fields are `name`, `description`, `tools`, `disallowedTools`, `model`, `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `effort`, `isolation`, `color`, and `initialPrompt`. Only `name` and `description` are required. The bundle additionally accepts the undocumented fields `observer` and `observerMessage`; those must be treated as internal rather than portable agent metadata.

`color` is a documented public field even though it is presentation-only. The Markdown body is behaviorally important—it becomes the agent's system prompt—but is not itself a frontmatter field.

The same bundle distinguishes reusable agent definitions from invocation data. This distinction matters: definition metadata is not simply copied verbatim into the Agent tool input.

### Runtime components visible in the compiled bundle

The embedded runner can be decomposed into these logical components even though its minified symbol names are not stable API:

```text
Agent tool handler
  -> resolve named definition or fork
  -> resolve model and context mode
  -> construct child permission context
  -> run SubagentStart hooks
  -> connect definition-scoped MCP servers
  -> resolve inherited/allowed/denied tools
  -> preload definition-scoped skills
  -> compose child system + user + environment context
  -> create child tool-use context
  -> stream the model/tool loop up to maxTurns
  -> persist sidechain messages and metadata
  -> scan/finalize result
  -> run SubagentStop and cleanup MCP/hooks/transient state
```

This is a code-path observation from the shipped bundle, not a promise that internal function boundaries or ordering names will remain stable.

### Source boundary

The public `anthropics/claude-code` repository is an issue/plugin/documentation distribution surface, not the core CLI implementation. The exact 2.1.217 npm package contains launch/install wrappers and `sdk-tools.d.ts`; the native executable contains the bundled implementation. Its embedded build metadata identifies version `2.1.217`, build time `2026-07-21T18:35:19Z`, and source revision `9963b018d22c3e6659c99e135e687870301b5c67`, but that revision's core source is not published in the public repository. Consequently:

- frontmatter and behavior claims should be anchored to official documentation;
- Agent input/output shapes can be anchored to the shipped declaration file;
- deeper implementation observations can be made from the exact executable, but should never be called readable upstream source.

## Codex

### Definition and discovery

**VERIFIED — readable source.** Codex loads agent roles from every enabled config layer in lowest-to-highest precedence order. At each layer it combines:

- role declarations under `[agents.<role>]`, optionally pointing to `config_file`; and
- standalone TOML files recursively discovered under that layer's `agents/` directory.

Standalone files require a non-empty `name`, a non-empty `description`, and `developer_instructions`. Files referenced from a named declaration can inherit the declaration name and metadata. Within a higher config layer, missing metadata fields can fall back to a lower layer's role; present fields replace lower-precedence values.

Source: [`load_agent_roles`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/config/agent_roles.rs#L19-L170) and [`parse_agent_role_file_contents`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/config/agent_roles.rs#L218-L315).

### A Codex role file is a config overlay

The parser extracts `name`, `description`, and `nickname_candidates`, then removes those three keys from the TOML value. Every remaining key is deserialized as `ConfigToml`. This makes a role file qualitatively different from Claude frontmatter: it is not a small agent-specific schema but a broad Codex configuration layer.

At spawn time, `apply_role_to_config` inserts that layer at session-flag precedence and rebuilds the child's `Config`. It preserves the caller's provider and service tier only when the role layer did not explicitly set them.

Source: [`RawAgentRoleFileToml`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/config/agent_roles.rs#L218-L315) and [`apply_role_to_config`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/agent/role.rs#L28-L117).

### Role metadata versus global agent settings

The exact 0.144.4 `[agents]` schema has four global fields plus a flattened map of roles:

- `max_threads`
- `max_depth`
- `job_max_runtime_seconds`
- `interrupt_message`
- arbitrary `[agents.<role>]` entries containing `description`, `config_file`, and `nickname_candidates`

Source: [`AgentsToml` and `AgentRoleToml`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/config/src/config_toml.rs#L681-L725).

[Current OpenAI subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents.md) also describes `default_subagent_model` and `default_subagent_reasoning_effort`; those keys are not present in the tagged 0.144.4 struct. An adapter must key off the installed/runtime version rather than assuming current documentation matches an older binary.

### Tool-surface construction

Codex renders the available role descriptions into the model-visible `spawn_agent` tool description. If the referenced role config contains `model`, `model_reasoning_effort`, or `service_tier`, the tool description identifies those settings as pinned/precedential.

Source: [`spawn_tool_spec::build`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/agent/role.rs#L217-L302).

The collaboration tool set is built per turn. V1 includes spawn, send input, resume, wait, and close tools. V2 includes spawn, send message, follow-up task, wait, interrupt, and list tools, optionally under a namespace. V2 can hide agent type/model/reasoning metadata from the model-visible spawn schema.

Source: [`add_collaboration_tools`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/spec_plan.rs#L761-L845) and [`hide_spawn_agent_metadata_options`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents_spec.rs#L595-L642).

## Architectural contrast

```text
Claude definition                         Codex definition
-----------------                         ----------------
agent-specific frontmatter                role metadata
+ Markdown system prompt                  + remaining TOML as full Config layer
        |                                         |
        v                                         v
Agent invocation selects type/model       spawn_agent selects role/model/effort
        |                                         |
        v                                         v
runtime constrains parent permissions     role overlays child Config, then runtime
and resolves tools/MCP/skills             reapplies parent turn permissions + cwd
```

**INFERENCE.** Claude's definition is closer to a capability-bearing agent manifest. Codex's definition is closer to a named configuration preset with delegation instructions. A cross-runtime matrix should not force either representation to masquerade as the other.
