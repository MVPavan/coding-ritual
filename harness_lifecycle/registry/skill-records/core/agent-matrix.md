---
skill: agent-matrix
domain: core
stage: X
substage: Coordination
secondary: []
family: 
aliases: []
status: active
---
# agent-matrix

## Capability

Use when choosing or validating how a subagent is spawned — its model, effort, context mode, tools, permission mode, memory, skills, or MCP access — when a requested model or effort level may not exist, or when a spawn is supposed to guarantee an effort, tool, or permission setting.

<!-- registry:generated traits -->
- `catalog-source`: Read every selectable model, effort, capability and skill value from the single catalog file and never copy its lists into a prompt or a permanent definition.
- `validate-selection`: Validate every selected spawn dimension deterministically before spawning, rejecting any value the catalog does not declare rather than substituting a nearby one.
- `inherit-defaults`: Inherit the session model and effort defaults when none is requested.
- `layer-placement`: Separate the invocation layer's small accepted field set from the definition layer, which alone carries effort, tools, permissions, memory, skills, MCP and full model IDs.
- `three-reaches`: Route a spawn through one of three paths — the Agent tool, an ephemeral inline definition, or an independent process — by where a capability must be fixed.
- `no-definition-sprawl`: Do not create a permanent definition file per model-effort-capability combination.
- `context-modes`: Resolve fresh context versus full context deliberately, treating last-N turns and pasted summaries as unsupported substitutes for a real fork.
- `fork-overrides`: Never promise model, effort, tool or permission overrides on a fork, which inherits the parent's model, tools, prompt and history wholesale.
- `effective-tools`: Treat a declared tool list as not the effective one, accounting for the background and Bash-interaction filters, and have the child report its resolved tools when the task depends on one.
- `effort-unverified`: Record effort as requested-but-unverified, since it is definition-only and not observable from inside a child.
- `preserve-role-prompt`: Keep role behaviour in one role prompt independent of the runtime metadata applied around it at invocation.
- `report-resolution`: Report which values were selected from the catalog, accepted by the active surface, inherited, or rejected and unavailable.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
No adopted lineage recorded.
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
No ledger history recorded.
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
