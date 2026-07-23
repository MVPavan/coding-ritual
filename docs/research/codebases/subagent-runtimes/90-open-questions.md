# Open questions and version-sensitive discrepancies

## 1. Claude depth configuration contradiction

**Public contract:** the current docs say a depth-five subagent loses the Agent tool and the depth limit is fixed.

**Exact 2.1.217 bundle:** contains `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`, a `subagent_depth_cap` signal, and error text that suggests asking the user to raise the environment variable.

**Status:** unresolved. The code may be latent, internal, test-only, or gated. Do not expose it as a supported matrix option without a controlled runtime test and an explicit decision to rely on undocumented behavior.

## 2. Codex documentation versus 0.144.4 config schema

**Current OpenAI documentation:** describes `agents.default_subagent_model` and `agents.default_subagent_reasoning_effort`.

**Tagged 0.144.4 source:** `AgentsToml` does not contain those fields.

**Status:** version drift. The matrix adapter needs a versioned schema/capability probe, not one timeless Codex manifest format.

## 3. Codex V2 depth behavior

**V1 source:** checks `max_depth` and removes collaboration tools at the limit.

**V2 0.144.4 source:** tool planning always returns true for collaboration-tool depth and the handler has no V1-style check.

**Status:** verified source asymmetry in an under-development feature. Determine the intended supported contract in the exact runtime that will host the matrix before depending on nesting behavior.

## 3a. Codex custom-agent sandbox behavior

**Current documentation:** says a custom agent can override sandbox configuration.

**Tagged 0.144.4 spawn source:** applies the role layer and then reassigns the child's approval policy, approval reviewer, working directory, and permission profile from the live parent turn.

**Status:** version-sensitive behavior. For 0.144.4, treat the parent runtime boundary as effective. A newer adapter must probe or inspect its own version before assuming either rule.

## 4. Codex role-specific capability restriction

Codex role files are broad config overlays, but 0.144.4 has no Claude-style `tools`/`disallowedTools` role schema. The V2 tool description says children have the same tools. Some tools/features/MCP/skills can be affected through ConfigTOML, but a simple portable per-role tool allowlist is not established.

**Status:** design gap. A normalized `capability_policy` needs a runtime adapter that either proves an enforceable restriction or rejects/degrades it visibly.

## 5. Claude arbitrary role × effort routing

Claude definition frontmatter supports effort, and a top-level session supports `--effort`, but Agent invocation input does not expose effort in 2.1.217.

**Status:** product constraint. Decide whether the matrix compiler should:

- inherit session effort;
- generate a small set of effort-bound aliases;
- launch separate top-level sessions;
- or refuse dynamic subagent effort selection on Claude.

The answer should be policy-driven rather than hidden in naming conventions.

## 6. Effective-model observability

Claude Agent completion reports `resolvedModel` and optional `modelsUsed`. Codex exposes requested/role config in thread state and activity/telemetry, but the exact stable external event to use as the matrix audit record needs confirmation for the chosen CLI/app-server surface.

**Status:** implementation-time probe needed.

## 7. Provider-specific model aliases

Claude accepts aliases/full IDs and may run through first-party, Bedrock, Vertex, Foundry, or other supported provider paths. Codex separates model/provider/service-tier configuration and validates from its loaded catalog.

**Status:** never normalize these to one universal model enum. The matrix should use runtime-specific profile records plus capability tags and a resolved-model audit field.

## Proposed next research probes

These are intentionally not performed in this source-only pass because they can incur inference cost or depend on account policy:

1. Launch one Claude custom agent with definition effort plus invocation model and inspect `resolvedModel`, usage, and transcript metadata.
2. Test whether `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` changes behavior in 2.1.217; treat failure or server-side gating as meaningful evidence.
3. Launch Codex V2 in a controlled local/app-server session for `fork_turns = all`, `none`, and `3`; record exact events and resolved config.
4. Test a Codex role that sets sandbox/MCP/model independently and capture the effective child config after runtime overrides.
5. Define a capability-negotiation JSON contract that both adapters emit before launch.
