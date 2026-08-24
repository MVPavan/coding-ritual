Target(s): reference_tools/omnigent
Created: 2026-08-21

# omnigent — Research Index

## Purpose

Decide whether and how omnigent becomes part of this project's workflow
orchestration (user framing: "going to become a critical part of workflow
orchestration"). L1 establishes what it offers; the escalation path in
`capabilities.md` names the L2 questions that decision still needs.

## Evidence legend

- **documented?** — prose (README, docs, comments) claims it.
- **declared?** — a manifest, config, or schema declares it.
- Reachability ladder: `ABSENT` (no artifact found) → `PRESENT` (artifact
  located) → `WIRED` (registration/call path traced) → `SOURCE-TRACED` (full
  behavior read, `file:line` cited) → `EXERCISED` (a run demonstrated it,
  requires separate runtime authorization).
- `INFERENCE` marks interpretation, carrying the reachability of what it was
  inferred from.

## Artifact registry

| Artifact | Mode | Snapshot sha | Clean/dirty | State | Date |
|---|---|---|---|---|---|
| `capabilities.md` | L1 | `33ec5137` | clean | current | 2026-08-21 |
| `architecture/00-architecture.md` | L2 | `33ec5137` | clean | current | 2026-08-21 |
| `factory-assessment.md` | assessment (adjunct, non-contract) | `33ec5137` | clean | current | 2026-08-24 |

## Current synthesis

- Omnigent (v0.11.0.dev0, alpha) is an open-source meta-harness: one
  orchestration layer over Claude Code, Codex, Cursor, OpenCode, Hermes, Pi,
  ACP agents (incl. Devin, Grok, OpenClaw), and custom YAML agents, with a
  FastAPI server + host-runner architecture, web/mobile/desktop/VS Code/Slack
  fronts, and a headless Python SDK.
- L2 (`SOURCE-TRACED`) confirms a strict durable/ephemeral split: one SQL
  database (17 tables) is the durable authority for control-plane state,
  while all live state — runner registry, active turns, message buffers,
  SSE queues, pending approvals, scheduler timers — is process-local by
  design; recovery is reconnection + snapshot reconciliation, never replay.
- The full turn lifecycle is traced end-to-end (client event → server
  dispatch → runner buffer/turn → harness scaffold/executor → SSE back),
  including harness-specific semantics: Codex supports true mid-turn steer,
  Claude SDK deliberately buffers to the next turn; interrupt tears down and
  rebuilds vendor clients; native "turn complete" means input delivered,
  not vendor work finished.
- Multi-agent coordination is generic parent/child session machinery
  (spawn tools, inherited runner, per-turn spawn caps, optional worktrees);
  Polly's parallel-worktree, cross-vendor-review behavior is YAML/skill
  convention — the runtime does not enforce reviewer vendor separation.
- Smart routing is real and traced: local LLM judge + optional external
  `/routes:select` provider, validated/clamped selections, persisted
  `routing_decision` transcript items; overrides (session pin, agent pin,
  mid-chat) interact with no single precedence document.
- Extension contracts are genuine: third parties can register non-native
  harnesses (`omnigent.community.harness`; native harnesses rejected) and
  sandbox providers (`omnigent.sandbox_providers`); custom policy modules
  are allowlisted — but locally loaded trusted specs bypass that allowlist.
- The headless SDK can drive a full workflow loop (create/stream/tools/
  elicitations/interrupt/fork) but cannot create durable agents and has no
  general native tool-approval primitive.
- Credential-proxy + L7-egress isolation is runtime-enforced only when a
  sandbox/OSEnv is active; the default caller-process path bypasses it, and
  Kimi/Windows paths are weaker.
- Hard operational constraints (traced): single-replica server (process-local
  registries; multi-replica would double-fire scheduled tasks — leasing is
  "future work"), no SSE replay or event cursor, lossy approvals across
  restarts, per-turn-only spawn bounds.
- Docs-vs-source: README's Polly claims are convention not guarantees;
  `QUEUE_STEER_DESIGN.md` is unimplemented proposal; `openapi.json` omits
  the mounted scheduled-tasks family; MCP approval timeouts can leave stale
  pending-approval state.
- Standing verdict: architecturally credible as an orchestration substrate
  for a single-server deployment with sandboxing explicitly configured;
  the remaining unknowns are runtime behaviors (`EXERCISED`-level: replica
  behavior, native approval parity headless) and alpha-grade drift.

## Reading map

- What can omnigent do; where is everything; what to study next →
  `capabilities.md`.
- How it does it — components, turn lifecycle, state model, routing,
  extension contracts, trust boundary, docs-vs-source, ranked risks →
  `architecture/00-architecture.md`.
- Should it be our software factory; what to pilot and what not to build →
  `factory-assessment.md` (three-model design opinion; decision open).
- No deep dives exist yet for this target.

## Staleness, contradictions, and risks

- Target is alpha and fast-moving (`0.11.0.dev0`); the submodule pin
  (`33ec5137`, 2026-08-20) will drift quickly — re-check the sha before
  building on this survey.
- `openapi.json` vs source routes: resolved at L2 — the scheduled-tasks
  family is mounted in source (`server/app.py:2319-2336`); the generated
  spec is stale. Treat source, not the spec, as authoritative.
- Top risks (ranked in `architecture/00-architecture.md` §Risks): lossy
  durability boundary (approvals, in-flight turns, missed schedules);
  structural single-replica; caller-owned idempotency over the runner
  tunnel; opt-in sandbox/credential isolation; SDK gaps (no durable agent
  creation, no native-approval primitive); stale child-runner bindings;
  trusted-local policy bypass; alpha drift.
