# Agent Matrix Validation Requirements

## Goal

Create one Agent Matrix workflow that both Codex and Claude Code can use to
select subagent metadata from the compact catalog, reject undeclared values,
and test the runtime-specific invocation paths.

## Source Of Truth

- `docs/research/codebases/subagent-runtimes/agent-matrix-values.yaml`
- The authenticated Codex model catalog returned by `codex debug models`
- The installed Codex and Claude Code runtime versions

The static catalog defines selectable values. Live runtime inspection narrows
those values to combinations the current installation actually supports.
Record three separate support layers:

- `catalog_visible`: returned by `codex debug models`
- `tool_exposed`: advertised by the active `spawn_agent` contract
- `backend_accepted`: accepted and confirmed by child rollout metadata

Do not treat one layer as proof of another.

## Runtime Entry Points

- `.codex/skills/agent-matrix/SKILL.md` contains Codex routing instructions.
- `.claude/skills/agent-matrix/SKILL.md` contains Claude Code routing
  instructions.
- One shared deterministic script owns catalog parsing, validation, test-plan
  generation, and result coverage checks.

The runtime skill files may differ where invocation contracts differ. They must
not duplicate model, effort, capability, or skill registries from the catalog.

## Codex Coverage

### Spawn Parameters

Test every valid visible Codex model and advertised reasoning-effort pair.
Also cover:

- `fork_turns`: `none`, `all`, and a positive integer string
- `service_tier`: every catalog value on a compatible model or a documented
  rejection when the current runtime/model does not support it
- explicit role selection where a probe role is required
- invalid model, effort, and context values as negative validation cases

Before broad execution, inspect the active tool contract. Attempt catalog-visible
models that are absent from its advertised set as compatibility probes, but do
not call them tool-supported unless the backend accepts and records them.

Also test the raw spawn contract independently of the catalog:

- `task_name`: valid, blank, reserved, and invalid-character cases
- `message`: valid and blank cases
- `agent_type`: default, one configured role, unknown role, and role-pinning
- full-history rejection of every forbidden override

### Inherited Or Configured Capabilities

Do not mislabel these as direct spawn arguments:

- tool access
- sandbox mode
- approval policy
- permission profile
- web search
- MCP servers
- skill enablement

Test every declared scalar value through the configuration surface that owns
it. For structured granular approval, cover every boolean subfield at least
once. Verify all catalogued Codex skill identifiers are discoverable without
invoking every skill.

`service_tier` is configuration-tested when absent from the active spawn
schema. Record that absence as `unsupported` for per-spawn selection.

## Exhaustiveness Rule

- Model and effort: full valid cross-product based on the live model catalog.
- Other fields: every value and structured subfield at least once.
- Unrelated dimensions: no full Cartesian product.

This avoids thousands of redundant combinations while still proving that every
declared selectable value has a runtime outcome.

## Result Semantics

Every case must end in exactly one state:

- `pass`: accepted and behavior or runtime metadata confirms the expectation
- `fail`: accepted but behavior or metadata contradicts the expectation
- `unsupported`: the current runtime or selected model explicitly rejects it
- `untestable`: the runtime exposes no trustworthy observation surface
- `infra_error`: a transient rate, capacity, authentication, or concurrency
  failure prevented a support conclusion

An accepted tool call or successful process exit is insufficient when the
claim requires stronger evidence about the effective child configuration.
Run at most one bounded retry for `infra_error`; never convert it into a support
outcome.

## Safety And Non-Goals

- Keep generated test artifacts under `scratchpad/`.
- Do not change the user's global Codex or Claude configuration.
- Do not create permanent per-model agent definitions.
- Do not test dangerous filesystem writes merely to prove full-access mode.
- Validate privilege-expanding sandbox, approval, and permission values by
  strict config parsing only. Do not execute a child with expanded privilege.
- Do not test the Claude model matrix in this work; Claude owns that follow-up.

## Acceptance

- Both runtimes discover an `agent-matrix` skill.
- Claude Code reviews and updates its runtime-specific skill instructions.
- Claude review evidence records the Claude version, prompt, verdict, and
  resulting diff; a justified no-change verdict is acceptable.
- The deterministic script rejects values absent from the catalog.
- Every valid live Codex model-effort pair has an evidence-backed result.
- Every Codex capability value has an evidence-backed result or an explicit
  unsupported/untestable classification.
- A machine-readable result file and concise Markdown report are produced.

The broad matrix may run only after a tracer spawn's child rollout exposes the
effective model and effort. Otherwise stop and classify the matrix
`untestable`.
