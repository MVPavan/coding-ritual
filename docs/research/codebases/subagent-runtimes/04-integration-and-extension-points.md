# Metadata, precedence, and extension points

## Claude metadata map

The current official contract documents exactly 16 frontmatter fields. Only `name` and `description` are required.

| Field | Required | Matrix layer | Definition behavior |
|---|:---:|---|---|
| `name` | Yes | Role | Unique lowercase-and-hyphen type identifier. Hooks receive it as `agent_type`; filename need not match |
| `description` | Yes | Role | Routing guidance that tells Claude when to delegate to the agent |
| `tools` | No | Capability | Allowlist resolved against subagent-available tools; omitted means inherit all. A list with no resolvable entry fails launch |
| `disallowedTools` | No | Capability | Denylist removed from either the inherited pool or the explicit `tools` pool |
| `model` | No | Execution | `sonnet`, `opus`, `haiku`, `fable`, a full model ID, or `inherit`; defaults to parent inheritance |
| `permissionMode` | No | Capability | `default`, `manual`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`, or `plan`; `manual` aliases `default` from 2.1.200. Parent policy still constrains it. Ignored for plugin agents |
| `maxTurns` | No | Invocation/lifecycle | Maximum agentic turns before the run stops |
| `skills` | No | Capability | Full skill contents preload at startup. Unlisted skills remain callable through the Skill tool when available |
| `mcpServers` | No | Capability | Configured-server references or inline server definitions. Ignored for plugin agents |
| `hooks` | No | Capability/lifecycle | Lifecycle hooks scoped to this agent. Ignored for plugin agents |
| `memory` | No | State | Persistent memory scope: `user`, `project`, or `local` |
| `background` | No | Invocation/lifecycle | `true` forces background execution. Otherwise Claude chooses; since 2.1.198 it defaults subagents to background |
| `effort` | No | Execution | `low`, `medium`, `high`, `xhigh`, or `max`, subject to model support; overrides session effort |
| `isolation` | No | Capability | `worktree` creates a temporary isolated checkout based by default on the configured default branch, not parent `HEAD`; unchanged worktrees are cleaned up automatically |
| `color` | No | Presentation | Task-list and transcript color: `red`, `blue`, `green`, `yellow`, `purple`, `orange`, `pink`, or `cyan` |
| `initialPrompt` | No | Main-session startup | Prepended first user turn only when the definition runs as the main agent via `--agent` or the `agent` setting; commands and skills are processed; ignored for subagent spawn |

The Markdown body—or `prompt` in `--agents` JSON—is separate from these 16 fields and becomes the agent's system prompt.

### Frontmatter is not the invocation schema

The Agent call selects an existing definition and supplies this run's task. In the shipped 2.1.217 declaration, it has required `description` and `prompt`, plus optional `subagent_type`, per-invocation `model`, `run_in_background`, runtime `name`, and `isolation`. It does **not** accept per-invocation `effort`, `tools`, `permissionMode`, `skills`, `mcpServers`, `hooks`, `memory`, or `maxTurns`.

Sources: [Supported frontmatter fields](https://code.claude.com/docs/en/sub-agents#supported-frontmatter-fields) and exact package `@anthropic-ai/claude-code@2.1.217`, `package/sdk-tools.d.ts:484-521`.

### Claude permission precedence

The child inherits parent permissions. Definition `permissionMode` is applied only if it does not weaken parent modes that already dominate: parent `bypassPermissions`, `acceptEdits`, and `auto` remain controlling. Background prompts surface in the main session; an agent message is never permission approval and cannot reconfigure another agent's permissions.

Source: [Permission modes](https://code.claude.com/docs/en/sub-agents#permission-modes) and [Resume subagents](https://code.claude.com/docs/en/sub-agents#resume-subagents).

### Claude model versus effort

Claude explicitly separates model resolution from effort:

```text
model = env override > invocation override > definition > parent
effort = definition > session
thinking on/off = inherited from session
```

The docs distinguish effort level from extended-thinking enablement: an agent may set an effort level, but it does not independently switch thinking on or off.

## Codex metadata map

| Field | Role file/config | V2 invocation | Effective behavior in 0.144.4 |
|---|---:|---:|---|
| `name` | Required standalone | `agent_type` | Selects role; omitted uses `default` |
| `description` | Required | No | Inserted into model-visible role guidance |
| `developer_instructions` | Required standalone | No | Becomes child behavioral instructions through config overlay |
| `nickname_candidates` | Optional | No | Used by registry nickname reservation |
| `model` | Any ConfigTOML model | Yes | Invocation applied first; role value then pins/overrides it |
| `model_reasoning_effort` | Any ConfigTOML effort | `reasoning_effort` | Invocation applied first; role value then pins/overrides it |
| `service_tier` | Any ConfigTOML tier | Yes | First supported: role, invocation, parent |
| permissions/sandbox | Broad config keys possible | No direct field | Parent live runtime approval/profile reapplied after role |
| tools/capabilities | Broad config/feature/MCP/skill settings | No per-call allowlist | No Claude-style first-class role tool allow/deny schema |
| context | No | `fork_turns` | `all` rejects role/model/effort; `none` is fresh; N is partial fork |
| `task_name` | No | Required V2 | Creates canonical task path and address |

Sources: [role parser](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/config/agent_roles.rs#L218-L315), [V2 spawn](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs#L40-L170), and [spawn precedence helpers](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents_common.rs#L154-L337).

### Codex precedence in exact execution order

For a non-full-fork V2 spawn:

```text
clone parent turn config
  -> apply requested service tier provisionally
  -> validate/apply requested model and reasoning effort
  -> apply named role Config layer
  -> resolve supported service tier: role > request > parent
  -> reapply parent approval policy, approval reviewer, cwd, permission profile
  -> construct child thread
```

The ordering has two important effects:

1. role model/reasoning is a lock, not a default;
2. role permission/cwd settings do not supersede the live parent turn's runtime boundary.

## Extension behavior

### Claude

- Agent definitions can add run-scoped MCP servers, preload skills, register lifecycle hooks, allocate persistent memory, and isolate changes in a worktree.
- Plugin-distributed agents intentionally ignore `hooks`, `mcpServers`, and `permissionMode` for security.
- A main-session agent can restrict spawnable agent types with `Agent(type)` in `tools`; inside an actual subagent, the parenthesized type restriction is ignored. Omitting/denying `Agent` prevents nested spawn.

### Codex

- Because the role remainder is a full config layer, it can carry model/provider, MCP, skills, feature, and other recognized ConfigTOML settings for the child.
- Runtime permission and cwd fields are deliberately reasserted from the spawning turn.
- V2 can hide role/model/reasoning/tier selection from the tool schema, so matrix availability must be discovered from the actual session tool, not inferred only from files.
- The tool description exposes only the first five picker-visible models, even though validation uses the loaded model catalog. Displayed choices are guidance, not the complete internal catalog.

## Recommended normalized matrix schema

This is a design implication, not an implementation proposal:

```yaml
role:
  id: research
  description: When to delegate
  instructions: Stable behavioral prompt

capability_policy:
  id: read-research
  tools: [read, search, web]
  denied_tools: [write]
  mcp: []
  skills: []
  permission_intent: read_only
  isolation: shared

execution_profile:
  id: balanced
  runtime: claude_or_codex
  model: runtime_specific_slug
  effort: medium
  service_tier: optional

invocation_policy:
  context: fresh | full_fork | last_n
  last_n: optional
  background: auto | foreground | background
  max_turns: optional
```

### Adapter rules

**Claude adapter**

- Compile role and capability policy into a `.claude/agents` definition.
- Set model in the definition only as a default; an invocation may override it.
- Effort variants cannot be selected per Agent call in the shipped 2.1.217 input. Either bind effort to a compiled definition, inherit session effort, or launch separate top-level sessions with different effort.
- Validate provider/model compatibility and available effort levels before launch.

**Codex adapter**

- Compile stable role behavior into `.codex/agents`.
- If the execution profile is chosen per invocation, do not put `model`, `model_reasoning_effort`, or `service_tier` in the role file.
- Always emit `fork_turns` explicitly in V2.
- Compute effective permissions from the parent session; do not claim the role established a stronger or different sandbox.
- Detect whether the live tool exposes metadata selectors; V2 may hide them.

## Why not generate the Cartesian product?

A role × capability × model × effort product creates aliases that encode runtime accidents as agent identities. It also breaks differently by harness:

- Claude duplicates most manifest content merely to vary effort.
- Codex role files that include model/effort turn a selectable profile into a lock.
- Changing a model slug or supported effort would require rewriting many behavioral definitions.
- Auditing effective permissions becomes harder because identity and runtime boundary are conflated.

The normalized matrix should join these dimensions at launch and retain a resolved invocation record for auditability.
