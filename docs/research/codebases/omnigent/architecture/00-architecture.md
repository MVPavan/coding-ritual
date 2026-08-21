Target(s): reference_tools/omnigent
Snapshot: 33ec5137 (clean)   Date: 2026-08-21
Mode: L2   Builds on: capabilities.md @ 33ec5137

# Omnigent — architecture map (L2)

Produced by three parallel GPT-5.6-luna (high) source tracers (A: lifecycle +
multi-agent coordination; B: state + delivery; C: routing + extension +
trust), coordinated and consolidated with an Opus 5 critic review. Evidence
legend: `00-index.md`. All `SOURCE-TRACED` claims cite `file:line` at this
snapshot; nothing was executed (`EXERCISED` never claimed).

## Questions

From L1's escalation: (1) session/agent lifecycle for the harnesses we would
use; (2) headless embedding via SDK/HTTP; (3) state and persistence vs the
in-memory runner registry; (4) parent/child coordination; (5) the smart
routing contract; (6) extension contracts; (7) trust and credential flow;
(8) delivery semantics under disconnects.

## Thesis

`INFERENCE` (rests on the traces below): Omnigent is built on a strict
**durable-control-plane / ephemeral-execution split**. One SQL database
(17 tables, Alembic-managed — `omnigent/db/db_models.py`, count confirmed at
this snapshot; artifact *bytes* live separately in local/S3/Volume stores)
is the only durable authority for control-plane state — conversations,
items, child-session hierarchy, metadata/bindings, policies, ACLs, projects,
hosts, scheduled tasks and runs. Everything *live* is deliberately
process-local and non-durable: the runner registry, active turns and message
buffers, SSE subscriber queues, pending-approval futures, scheduler timers.
Recovery is by reconnection plus snapshot reconciliation, never by replay.
Harness heterogeneity is absorbed at two boundaries — per-harness
executor/harness adapter pairs in `omnigent/inner/` beneath a common
runner/scaffold protocol — and capability differences (steer vs buffer,
interrupt semantics, native terminal ownership) are allowed to leak through
rather than papered over. Multi-agent orchestration is generic parent/child
session machinery plus policy bounds; the celebrated workflow behaviors
(parallel worktrees, cross-vendor review) are YAML/skill *convention* layered
on top, not runtime guarantees.

## Component map

Dependency direction is downward; `entities`/`spec` are shared contracts.

| Component | Responsibility | Key evidence |
|---|---|---|
| `omnigent/cli.py` (+`chat.py`, `repl/`) | `omnigent`/`omni` entry; dispatches REPL vs native wrapper vs server/daemon modes | `cli.py:7036-7064,6780-6901` |
| `omnigent/server/` | FastAPI control plane: session routes, orchestration, routing backend, registries, scheduled tasks, auth/sharing | `server/app.py:1077-1093,2652-2665` |
| `omnigent/runner/` | Host-side agent process: turn loop, buffers, tool dispatch, native terminal registry, WS tunnel to server | `runner/app.py:6678-6760`; `runner/resource_registry.py:907-1006` |
| `omnigent/runtime/` | Execution engine library ("the server is its primary host, but it can also be … embedded", `runtime/README.md:5`): scaffold, session streams, prompt, policies | `runtime/harnesses/_scaffold.py:1225-1290` |
| `omnigent/inner/` | Per-harness executor+harness pairs (claude/codex/cursor/… × sdk/native/acp), sandboxes (bwrap/seatbelt/JobObject), credential proxy, L7 egress | `inner/claude_sdk_executor.py`; `inner/credential_proxy.py:146-220` |
| `omnigent/stores/` + `db/` | SQLAlchemy stores over the 17-table schema; artifact stores (local/S3/UC Volumes) | `db/db_models.py:746-915`; `stores/artifact_store/local.py:10-40` |
| `omnigent/policies/` | Policy registry, function policies, builtins (safety/cost/orchestration) | `policies/registry.py:92-169` |
| `omnigent/entities/`, `omnigent/spec/` | Shared domain models; YAML agent-spec parser/validator | `spec/parser.py:166-312` |
| `omnigent/tools/` | Built-in tools (spawn, skills, web, timer…), ToolManager server/client/user-code split | `tools/manager.py:676-830` |
| `sdks/`, `web/`, `integrations/`, `editors/` | Headless Python client + UI SDK; SPA/Electron/mobile; Slack; VS Code | `sdks/python-client/omnigent_client/_client.py:22-90` |

## Capability realization matrix

Consolidated from the three tracers; each row upgraded from L1's `PRESENT`.
The documented?/declared? flags are carried in L1's capability map and are
unchanged by this run except where Docs vs source below revises them.

| Capability | Public surface | Registration/entry | Core path | State & integration | Reachability |
|---|---|---|---|---|---|
| Session lifecycle + harness switch | `run`/`resume`/`attach`, REPL, native wrappers | CLI dispatch; sessions create/fork/switch routes | `cli.py:6780-6901`; `chat.py:1551-1645`; `server/routes/sessions/routes_core.py:1990-2124,2215-2291` | conversation store, runner binding, tmux terminals, SDK client cache | `SOURCE-TRACED` |
| One-message runtime lifecycle | session adapter | `POST /v1/sessions/{id}/events` → runner event endpoint → scaffold | `repl/_repl.py:2270-2323`; `server/routes/sessions/routes_events.py:1687-1717`; `runner/app.py:6678-6760`; `runtime/harnesses/_scaffold.py:1225-1290` | history, buffers, live response ids, SSE status | `SOURCE-TRACED` |
| Interrupt vs steer | REPL cancel; mid-turn message | server interrupt route; executor enqueue | `server/routes/sessions/routes_events.py:725-751`; `runner/app.py:5124-5225`; `inner/codex_native_executor.py:79-125` | interrupt fence, buffers, vendor bridge/thread | `SOURCE-TRACED` |
| Parent/child multi-agent | `sys_session_send`/`sys_session_create` | runner tool dispatch; child-session route | `runner/tool_dispatch.py:1720-1826,2283-2316`; `server/routes/_sessions/orchestration.py:7827-7954,2226-2317` | parent/root ids, inherited runner, per-turn `spawn_bounds`, optional worktree | `SOURCE-TRACED` |
| Authoritative state | all domain APIs | store construction at boot (Docker entrypoint traced; other deploys not verified) | `deploy/docker/entrypoint.py:355-398`; `db/db_models.py:746-915`; `db/utils.py:229-294` | SQL durable; artifacts local/S3/Volume; live state in-memory | `SOURCE-TRACED` |
| Runner presence/recovery | `WS /v1/runners/{id}/tunnel` | process-local `TunnelRegistry`/`HostRegistry` | `server/routes/runner_tunnel.py:345-494`; `runner/transports/ws_tunnel/registry.py:196-349`; `server/app.py:2525-2605` | newest-wins reconnect; DB bindings survive; in-flight requests don't | `SOURCE-TRACED` |
| SSE + WS delivery | `GET /v1/sessions/{id}/stream`; tunnel; terminal attach | sessions router; app mounts | `runtime/session_stream.py:39-119`; `server/routes/_sessions/helpers.py:7481-7515`; `server/_runner_ws_tunnel.py:255-298` | bounded 1024 queues, overflow sentinel, no replay, snapshot+dedupe | `SOURCE-TRACED` |
| Approvals/elicitation | approval event; resolve URL; SSE card | orchestration + elicitation routes; runner futures | `server/routes/_sessions/orchestration.py:6334-6489,1633-1747`; `runner/pending_approvals.py:83-202`; `runner/app.py:7017-7033` | definitions DB-backed; pending futures in-memory; ancestor fan-out | `SOURCE-TRACED` |
| Scheduled tasks | `/v1/scheduled-tasks` CRUD/run/history | mounted when store exists (`server/app.py:2319-2336`) | `server/scheduled/scheduler.py:136-158,247-312`; `server/scheduled/fire.py:216-469` | rows durable; timers process-local; no missed-fire replay, no lease | `SOURCE-TRACED` |
| Smart routing (local + external) | `routing:` config; "auto" harness | CLI builds routing clients | `cli.py:250-389`; `server/smart_routing.py:485-656,1801-1934,2244-2406`; `server/routing_backend.py:92-182` | live runner catalogs; validated/clamped selections; fallback local judge | `SOURCE-TRACED` |
| Routing overrides + persistence | session PATCH, `/model`, agent spec | conversation override fields | `entities/conversation.py:99-113,561-624`; `server/routes/_sessions/helpers.py:1772-1879,2129-2167,5976-6065` | persisted `model_override`/`harness_override`; `routing_decision` items + SSE | `SOURCE-TRACED` |
| Community harness plugins | Python entry point | `omnigent.community.harness` | `harness_plugins.py:827-835,883-954,957-992` | namespace-enforced; native harnesses rejected; collisions skipped | `SOURCE-TRACED` |
| Sandbox provider plugins | Python entry point | `omnigent.sandbox_providers` | `onboarding/sandboxes/registry.py:92-108,185-268,287-318` | launcher class contract, `omnigent.community.sandbox` namespace | `SOURCE-TRACED` |
| YAML tools/MCP/sub-agents | agent YAML + `tools/` tree | spec parser → ToolManager | `spec/parser.py:2493-2745,2879-2945`; `tools/manager.py:676-865` | server/client/user-code partitions; MCP execution delegated to runner | `SOURCE-TRACED` |
| Custom policy modules | `policy_modules` config; policy API | `POLICY_REGISTRY` allowlist | `policies/registry.py:92-317`; `policies/function.py:256-343` | fail-closed evaluation; trusted-local-spec bypass | `SOURCE-TRACED` |
| Headless SDK loop | Python SDK | `POST /v1/sessions` + session routes | `sdks/python-client/omnigent_client/_sessions.py:364-505,635-1158`; `_sessions_chat.py:636-761,995-1027` | full loop incl. tools + elicitations; **no durable agent creation** | `SOURCE-TRACED` |
| Credential proxy + L7 egress | sandbox/OSEnv config | `prepare_credential_proxy_runtime`; `create_os_environment` | `inner/credential_proxy.py:146-369`; `inner/os_env.py:449-542,683-801`; `inner/egress/proxy.py:373-423,969-1253` | parent-held secrets, synthetic env, deny-by-default rules, IP pinning | `SOURCE-TRACED` (configuration-dependent) |

## Runtime lifecycle

One message, end to end (`SOURCE-TRACED`, anchors in the matrix): client
POSTs a `message` event → server validates, resolves or wakes the bound
runner, heals stale bindings, dispatches (`routes_events.py:1292-1535`) →
runner serializes ingestion per session; if a turn is active the message is
buffered (and possibly injected mid-turn), else history loads and
`_run_turn_bg` starts (`runner/app.py:6612-6760`) → setup resolves
agent/spec/harness, builds env/instructions/tools (`runner/app.py:5683-5865`)
→ harness scaffold allocates a response context, runs the executor, emits
lifecycle/output events (`_scaffold.py:1424-1515`) → runner publishes
output/status, consumes injections, appends history (`runner/app.py:6321-6353`)
→ turn end clears markers, publishes idle/failed/cancelled, drains buffered
continuations — native FIFO one-at-a-time, SDK coalesced into one
continuation history (`runner/app.py:5000-5072,5324-5382`). Clean REPL exit
leaves daemon-owned runners for idle-reap; session deletion cleans resources
and optionally a server-created worktree (`routes_events.py:1937-2035`).

Two semantics worth internalizing:

- **Steer ≠ interrupt** (`INFERENCE` from traced paths): steer preserves the
  vendor turn where supported (Codex `turn/steer`,
  `inner/codex_executor.py:2755-2783`); interrupt fences the Omnigent turn
  and tears down/reboots the vendor client (Claude SDK closes and rebuilds
  with full history, `inner/claude_sdk_executor.py:1844-1885`).
- **Native turn completion is input-delivery completion**: for native
  wrappers, `run_turn` yields after the text is injected into tmux — vendor
  work can outlive the Omnigent turn marker
  (`inner/claude_native_executor.py:113-169`; `runner/app.py:5341-5378`).

## Data and state

- **Durable (SQL):** conversations + items (single-table, `type` +
  JSON `data`), child hierarchy via `parent_conversation_id`
  (`kind="sub_agent"` derived), metadata (runner/host binding, live-status
  mirror, pending-elicitation count), files (metadata only), policies, ACLs,
  comments, hosts, projects, scheduled tasks/runs
  (`db/db_models.py:308-1585`). SQLite gets WAL/busy-timeout config;
  Postgres/Lakebase pooled engines; Cloudflare D1 is a SQLite-family dialect
  without the local PRAGMA path (`db/utils.py:217-294,824-854`).
- **Artifact bytes:** local flat files by default; S3-compatible or
  Databricks Volumes by config — local artifacts are *not* replica-safe
  while their metadata rows are (`stores/artifact_store/local.py:10-40`;
  `deploy/docker/entrypoint.py:241-261`).
- **Ephemeral (process-local, by design — confirmed by the target's own
  `server/DBSPEC.md:13-24`):** runner registry, host liveness, active turns
  and message buffers (`_active_turns`, `_session_message_buffers` in
  `runner/app.py`, named by `server/DBSPEC.md:19-22`), SSE subscriber queues,
  pending-approval futures and
  elicitation indexes, scheduler timers. Only a coarse
  `live_status`/`pending_elicitation_count` mirror is persisted.
- **Recovery model:** runners reconnect with jittered backoff; the server
  reloads DB-bound conversations and restarts relays on reconnect
  (`server/app.py:2525-2605`); session relays tolerate tunnel loss within a
  grace window before publishing durable `runner_disconnected`
  (`orchestration.py:5607-5699`). SSE reconnect = fresh stream + snapshot +
  dedupe by item id; there is no event cursor or sequence number, and
  cross-producer ordering has no explicit total-order contract beyond
  publish arrival order (`INFERENCE`; `runtime/session_stream.py:81-119`).

## Docs vs source

Primary deliverable. Discrepancies found:

1. **README's Polly claims are convention, not runtime guarantees.** Parallel
   worktrees and different-vendor reviewers (`README.md:288-291`) are
   prescribed by Polly's skills (`examples/polly/skills/fanout/SKILL.md:11-46`,
   `cross-review/SKILL.md:23-47`); the runtime enforces only child ownership,
   per-turn spawn caps, and configured policies
   (`runner/tool_dispatch.py:1720-1826`). No runtime check that a reviewer's
   vendor differs or that it sees only a diff.
2. **`docs/QUEUE_STEER_DESIGN.md` is proposal text, not implementation.** The
   client queue (edit/delete/reorder) does not exist — the REPL posts
   immediately (`repl/_repl.py:2270-2295`); and its "SDK live injection"
   table row does not hold for Claude SDK, whose enqueue deliberately returns
   `False` → buffered next-turn delivery
   (`inner/claude_sdk_executor.py:1876-1885`).
3. **`openapi.json` omits the entire mounted scheduled-tasks family**
   (`server/routes/scheduled_tasks.py:172-200` vs zero matches in the spec;
   mounted at `server/app.py:2319-2336`) — generated-spec drift, confirming
   L1's finding from the source side.
4. **Secretless credential isolation is conditional.** Docs describe
   secretless operation generally; the proxy/egress path only exists when an
   active sandbox/OSEnv starts it — default caller-process execution has no
   such isolation (`inner/credential_proxy.py:1-25`; `inner/os_env.py:683-801`;
   `inner/codex_executor.py:155-168`).
5. **Sandbox-provider docs vs registry: no material discrepancy** — the
   registry's acceptance test is `SandboxHostLauncher` subclasses
   (`onboarding/sandboxes/registry.py:287-318`), which is nominally narrower
   than the docs' `SandboxLifecycle` framing, but `SandboxHostLauncher`
   subclasses `SandboxLifecycle` (`onboarding/sandboxes/base.py:794,842`) and
   both documented launcher families pass. The docs' managed lifecycle
   sequence (`prepare → provision → start_host`) describes the broader
   server path, not the registry contract (`INFERENCE`;
   `docs/extending/sandbox_providers.md:9-18,125-138`).
6. **Inline MCP declarations without `command` or `url` are silently
   skipped** by the spec parser (`spec/parser.py:2493-2617`), leaving
   managed-service-only declarations unresolved at that layer with no
   documented promise either way.
7. **Harness switching is narrower than "switch harness" reads:** idle-only,
   top-level-only, bindable built-in agents only
   (`routes_core.py:2221-2277`).
8. **Community-harness contribution fields are unevenly validated** — module
   paths are namespace-checked, but `native_providers`, `install_specs`,
   `materialize_agent_spec`, `bridge_dir` are outside `_community_paths`
   validation, and no user-facing docs exist for the group
   (`harness_plugins.py:842-847,883-903`).
9. **MCP approval timeout suppresses its resolution event** — the generic
   helper promises a resolved event on every exit; the MCP callback passes a
   no-op publisher, so timeout/cancel can leave the pending-approval badge
   stale (`runner/pending_approvals.py:145-157`;
   `runner/mcp_manager.py:310-323`).
10. **Polly's policy paths are legacy aliases** (`omnigent.inner.nessie.policies.*`
   re-exports `omnigent.policies.builtins.orchestration`;
   `inner/nessie/policies.py:1-12`).
11. **Changelog describes the Claude-SDK steering fix at outcome level**;
    the mechanism is buffering + full-history continuation, not live
    injection (`CHANGELOG.md:352-353` vs
    `inner/claude_sdk_executor.py:1876-1885`).
12. No discrepancy found (checked): CLI `attach`/`resume` docs, Cloudflare
    D1/R2 claims, single-replica statement (matches process-local
    registries), SDK `create_from_agent_id` semantics, sandbox namespace
    requirement.

## Risks and open questions

Ranked for the workflow-orchestration decision:

1. **Durability boundary:** server restart loses pending-approval futures,
   in-flight tunnel requests, and SSE backlogs; scheduled misses are never
   replayed; a stale `running` run row heals only lazily on read. Runners
   reconnect, but a workflow controller must treat approvals and in-flight
   turns as lossy — an in-flight approval likely cannot be recovered after
   restart unless the runner/harness reissues it (`INFERENCE`;
   `runner/pending_approvals.py:1-25`; `server/scheduled/scheduler.py:9-18`).
   Related smaller cuts of the same boundary: a scheduler startup failure
   leaves recurring execution unstarted with no periodic repair
   (`server/app.py:1290-1300`), and the schema deliberately omits several DB
   foreign keys, leaving cascade cleanup app-owned
   (`db/db_models.py:1451-1453,1546-1550`).
2. **Single-replica is structural**, not just a Cloudflare note: process-local
   `TunnelRegistry`/`HostRegistry`, and multi-replica scheduling would
   double-fire (leasing explicitly future work,
   `server/scheduled/fire.py:38-42,82-90`).
3. **Idempotency is the caller's job:** tunnel HTTP has no ack/retry
   protocol; retry after a lost response may duplicate a side-effecting
   request (`INFERENCE`; `runner/transports/ws_tunnel/registry.py:712-757`).
4. **Sandbox/credential isolation is opt-in** — the default caller-process
   path bypasses proxy and egress control entirely; Kimi and Windows paths
   are weaker (`inner/kimi_executor.py:74-110`; `inner/os_env.py:505-542`).
5. **SDK gaps for full headless control:** no durable agent creation, no
   general native tool-approval primitive (elicitations only)
   (`_sessions.py:364-505`; `_sessions_chat.py:995-1027`).
6. **Child-runner bindings can go stale:** a child's runner id is copied
   once at creation; after parent runner relaunch, healing walks ancestors
   and native children need explicit reinitialization — child-session
   survivability across parent churn depends on that healing path
   (`server/routes/_sessions/orchestration.py:2226-2317`).
7. **Policy governance has a trusted-local bypass:** locally loaded trusted
   specs skip policy-registry membership (API/bundle paths enforce it), and
   duplicate policy handlers merge by dict key with no rejection — later
   modules may silently overwrite earlier metadata (`INFERENCE` on the
   overwrite; `policies/registry.py:92-227`).
8. **Spawn bounds are per-turn**, not global live-child limits; cross-turn
   accumulation is unbounded by the shipped policy
   (`policies/builtins/orchestration.py:428-437`).
9. **No single routing-precedence document** — session pin, agent pin,
   native pane state, and child routing interact; the persisted
   `routing_decision` item (with `router_source`) is the only reliable
   record of what actually happened. Cross-provider-family forks also drop
   provider-bound model settings and native session ids
   (`server/routes/sessions/routes_core.py:2085-2124`).
10. **Alpha drift:** v0.11.0.dev0; several traced areas carry "future work"
    markers; expect churn against this snapshot.

## Coverage

| Dimension / capability | Disposition | Why |
|---|---|---|
| Components and boundaries | traced | orientation + all three tracers cover cli/server/runner/runtime/inner/stores/policies |
| Runtime lifecycle | traced | A2 end-to-end path, plus interrupt/steer variants |
| Data, state, persistence | traced | B1/B2: schema, engines, artifact stores, ephemeral boundaries, recovery |
| Integration and extension | traced | C2/C3: entry-point groups, YAML tools, policies, SDK↔route mapping |
| Trust and credential flow | sampled | proxy/egress mechanisms traced end-to-end, but per-platform/per-harness enforcement wiring only sampled (Codex/Claude/Pi/ACP/Qwen/Goose/Kimi); not statically proven for every combination |
| Operational model | sampled | delivery guarantees, scheduling, restart behavior traced; deploy-target matrix and scaling behavior not validated per provider |
| Claude/Codex harness paths | traced | native + SDK lifecycle, interrupt, steer |
| Other harnesses (cursor/goose/kimi/qwen/…) | sampled | executor wiring sampled for OSEnv acceptance only; lifecycle not traced per harness |
| Cloud sandbox launchers | sampled | registry + contract traced; individual provider launchers unread |
| Collaboration (share/co-drive), cross-device sync | excluded | not in authorized questions; UI-heavy, low decision weight |
| Slack, dictation, VS Code, web SPA internals | excluded | client shells over traced APIs; no orchestration semantics |
| Usage/cost/telemetry internals | excluded | surface confirmed at L1; internals not decision-critical yet |
| Native approval parity via SDK | unresolved | statically unclear how far native tool approvals can be driven headlessly |
| Multi-replica behavior beyond scheduler/registry | unresolved | needs runtime probing (`EXERCISED`) or deeper deploy-layer reading |

## Read next

For a future agent, in order:

1. `omnigent/runner/app.py` — the turn loop, buffers, drain semantics; most
   orchestration behavior lives here.
2. `omnigent/server/routes/_sessions/orchestration.py` — child sessions,
   relays, approvals, routing glue (very large; navigate by the anchors above).
3. `omnigent/runner/tool_dispatch.py` — spawn/send machinery.
4. `omnigent/server/smart_routing.py` + `routing_backend.py` — routing.
5. `omnigent/db/db_models.py` + `server/DBSPEC.md` — the durable truth.
6. `omnigent/harness_plugins.py` + `onboarding/sandboxes/registry.py` —
   extension contracts.
7. `omnigent/inner/os_env.py` + `inner/egress/proxy.py` — the real trust
   boundary.

Do not over-index on: `docs/QUEUE_STEER_DESIGN.md` (proposal, partially
contradicted by source), `openapi.json` (generated, missing mounted routes),
`omnigent/inner/nessie/` (legacy alias shims), `designs/` (aspirational),
`setup.py` (pyproject is authoritative), the dropped-`tasks`-table DBOS
history in `server/DBSPEC.md` (removed machinery).
