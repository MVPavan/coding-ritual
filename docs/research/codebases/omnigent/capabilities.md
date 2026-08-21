Target(s): reference_tools/omnigent
Snapshot: 33ec5137 (clean)   Date: 2026-08-21
Mode: L1   Builds on: none

# Omnigent — capability survey (L1)

Produced by GPT-5.6-luna (high) under the codebase-research L1 contract,
independently reviewed by an Opus 5 critic (15 findings), consolidated by the
coordinator. All pointers verified against snapshot `33ec5137`.

## Intended use

Omnigent is being evaluated as a workflow-orchestration candidate: the user
expects it to become a critical part of their workflow orchestration. It
presents itself as an open-source "meta-harness" — a common orchestration
layer over Claude Code, Codex, Cursor, OpenCode, Hermes, Pi, and custom YAML
agents (`README.md:5-7`). No fitness criteria were supplied, so these are
relevance hypotheses (`INFERENCE`), not verdicts:

- It may provide a common execution and session substrate across agent
  vendors, letting workflows swap or combine harnesses without rewriting.
- It may support delegated, parallel, reviewed multi-agent workflows
  (its shipped Polly example is exactly that shape).
- It may expose enough policy, sandbox, persistence, and approval controls
  for governed automation.
- It may be drivable headlessly (Python SDK, HTTP/SSE API, Slack) as a
  component inside an existing harness rather than only as the outer shell.

## Capability map

Legend: see `00-index.md`. `PRESENT` = an implementation artifact was
located; it does not establish wiring or traced behavior. The harness-family
taxonomy used below (native / SDK / ACP / custom-YAML) is the surveyors'
grouping (`INFERENCE`); the README names harnesses individually.

| Capability | What the docs promise | Surface | documented? | declared? | Reachability | Pointer |
|---|---|---|---|---|---|---|
| Meta-harness over many agent runtimes | One orchestration layer over Claude Code, Codex, Cursor, OpenCode, Hermes, Pi, and custom agents | CLI/server | y | y | `PRESENT` | `README.md:5-7`; `pyproject.toml:379-387`; `omnigent/harness_plugins.py:652-770` |
| Multiple harness families | Native terminal wrappers, SDK executors, ACP harnesses, and custom agents can be selected or combined (`INFERENCE` on the four-way grouping) | CLI/YAML/API | y | y | `PRESENT` | `README.md:260-272,493-495`; `omnigent/harness_plugins.py:326-633`; `omnigent/inner/*_executor.py` |
| Custom YAML agents | Prompt, tools, sub-agents, reviewers, executor declared in one YAML file | YAML/CLI | y | y | `PRESENT` | `README.md:481-524`; `docs/AGENT_YAML_SPEC.md:13-194,275-376` (tools §275+, sub-agents/reviewers §343-363); `omnigent/entities/agent.py` |
| Function, MCP, and sub-agent tools | Local Python functions, MCP servers, delegated sub-agents as agent tools | YAML/tool runtime | y | y | `PRESENT` | `docs/AGENT_YAML_SPEC.md:275-376`; `omnigent/tools/` |
| Multi-agent delegation and review | Polly plans, delegates to coding agents in parallel git worktrees, routes diffs to cross-vendor reviewers | example/orchestration/API | y | y | `PRESENT` | `README.md:288-303`; `examples/polly/`; `omnigent/server/routes/_sessions/orchestration.py`; `omnigent/runner/subagent_routing.py`; child sessions in `openapi.json` |
| Smart (automatic) harness+model routing | "Auto · smart routing" lets an intelligent router pick both harness and model; configurable mid-chat; external router provider supported | UI/server/API | y | y | `PRESENT` | `CHANGELOG.md:535,558`; `omnigent/server/smart_routing.py`; `omnigent/llms/routing.py`; `omnigent/server/routing_backend.py`; `openapi.json:3360` (`RoutingDecisionData`) |
| Model and credential selection | API keys, subscriptions (Claude/ChatGPT plans), OpenAI/Anthropic-compatible gateways, Databricks profiles; per-agent defaults; mid-session `/model` switch | CLI/config | y | y | `PRESENT` | `README.md:316-349`; `pyproject.toml:59-62` (keyring), `:95-96`, `:136-293` (provider extras); `omnigent/llms/` |
| Session lifecycle control | Create, list, update, fork, attach/co-drive, interrupt, compact, switch agents | HTTP API/SDK/CLI | y | y | `PRESENT` | `openapi.json:8964-12798`; `omnigent/server/routes/sessions/`; `sdks/python-client/omnigent_client/_sessions.py:333-1195` |
| Live event streaming | SSE session streams with events and presence. Constraint: the server does **not** replay history on reconnect — clients must re-open and reconcile via `get` | SSE/API/SDK | y | y | `PRESENT` | `openapi.json:12634-12690`; `sdks/python-client/omnigent_client/_sessions.py:1158-1277` (no-replay: `:1166-1169`) |
| Cross-device session continuity | Sessions follow you across terminal, browser, phone, desktop; messages, sub-agents, terminals, files in sync | web/mobile/desktop | y | n | `PRESENT` | `README.md:28-30,238-245`; `web/`, `web/android/`, `web/ios/`, `web/electron/` |
| Multi-user collaboration | Share live sessions, co-drive, fork, invite-only accounts, OIDC sign-in | web/API/CLI/auth | y | y | `PRESENT` | `README.md:385-439`; `openapi.json:10603-10769,12746-12864`; `omnigent/server/auth.py`; `omnigent/server/routes/sharing.py` |
| First-class projects | Projects group sessions and store default session settings (host, workspace, harness, model, worktree) via a `config` field | API/UI | y | y | `PRESENT` | `CHANGELOG.md:555`; `openapi.json:8614` (`/v1/projects`); `omnigent/server/routes/projects.py`; `omnigent/stores/project_store/` |
| Hosts, runners, workspaces, worktrees | Register machines as hosts, launch runners, browse host filesystems, list worktrees | CLI/API/runner | y | y | `PRESENT` | `openapi.json:7628-8295,8824-8963`; `deploy/README.md:216-234`; `omnigent/server/routes/hosts.py`; `omnigent/runner/` |
| Session files and terminals | File upload/read/write/edit/search, terminal creation, environment shell access per session | API/web/SDK | y | y | `PRESENT` | `openapi.json:11138-12632`; `omnigent/server/routes/sessions/routes_resources.py`; `sdks/python-client/omnigent_client/_files.py` |
| Local OS sandboxing | bwrap (Linux, mandatory for native terminals), seatbelt (macOS), Job Object (Windows). Documented limitation: Windows gets process containment only — **no** filesystem/network isolation and no native terminal wrappers | native CLI/runtime | y | n | `PRESENT` | `README.md:135-144` (limits `:170-176`); `omnigent/inner/bwrap_sandbox.py`; `omnigent/inner/seatbelt_sandbox.py`; `omnigent/inner/windows_jobobject_sandbox.py` |
| Secretless credential proxy + L7 egress proxy | Agents run without raw provider secrets; credentials injected at a proxy; L7 egress control | runtime/config | y | n | `PRESENT` | `docs/AGENT_YAML_SPEC.md:241`; `README.md:174`; `CHANGELOG.md:531`; `omnigent/inner/credential_proxy.py`; `omnigent/inner/egress/` |
| Cloud sandbox execution | Disposable or server-managed Modal, Daytona, Blaxel, Islo, E2B, CoreWeave, Kubernetes, OpenShell, Boxlite, Databricks sandboxes ("managed hosts") | CLI/server | y | y | `PRESENT` | `README.md:44-52`; `pyproject.toml:159-196`; `deploy/README.md:264-304`; `omnigent/onboarding/sandboxes/`; `omnigent/server/managed_hosts.py` |
| Policy governance | Allow / block / pause-for-approval on shell, edits, spend; stacked server-wide → per-agent → per-session, stricter first | YAML/config/API/UI | y | y | `PRESENT` | `README.md:441-477`; `docs/POLICIES.md:1-21`; `openapi.json:8380-8613,10775-11090`; `omnigent/policies/` |
| Custom policy modules | Server config loads custom policy callables/factories | config/Python | y | n | `PRESENT` | `docs/POLICIES.md:27-68,409-499`; `omnigent/policies/registry.py`; `omnigent/policies/function.py` |
| Recurring scheduled agent tasks | Scheduled prompts with model, effort, workspace, host, pause/resume, run history | UI/tool/API | y | **n** — absent from `openapi.json` (0 matches; see Coverage) | `PRESENT` | `CHANGELOG.md:509-527,559-611`; `omnigent/server/routes/scheduled_tasks.py:286-418`; `omnigent/server/scheduled/`; `omnigent/tools/builtins/scheduled_tasks.py` |
| Built-in agent tool catalog | (largely undocumented in README) spawn, async inbox, timer, browser, web fetch/search ×7 engines, skills loading, conversation search, comments, agent export | tool runtime | n | n | `PRESENT` | `omnigent/tools/builtins/` (30+ modules, e.g. `spawn.py`, `async_inbox.py`, `timer.py`, `browser.py`, `web_search_*.py`, `load_skill.py`, `search_conversations.py`) |
| Voice dictation | Optional server-side streaming speech-to-text with partial/final transcripts; pluggable engines | WebSocket/extra | y | y | `PRESENT` | `CHANGELOG.md:490,529,534,537`; `pyproject.toml:224-239`; `omnigent/server/routes/dictation.py:1-31,108-163`; `omnigent/server/dictation.py:12-31,88-100` |
| Usage, cost, telemetry, tracing | Per-session usage/spend API; anonymized telemetry on by default; optional OpenTelemetry | API/config | y | y | `PRESENT` | `README.md:528-535`; `openapi.json:12866-12887`; `pyproject.toml:141-150,197-205`; `omnigent/telemetry/`; `omnigent/inner/tracing.py` |
| Headless Python client SDK | Sessions, queries, streaming, files, events, tools, elicitation, model overrides, interruption, forking, local-server management | Python SDK | y | y | `PRESENT` | `sdks/README.md:47-167`; `sdks/python-client/omnigent_client/__init__.py:29-125` |
| UI SDK | Terminal hosting, formatting, tool rendering, themes, block filtering for building fronts | Python SDK | y | y | `PRESENT` | `sdks/README.md:106-167`; `sdks/ui/omnigent_ui_sdk/__init__.py:14-43` |
| Editor/desktop/mobile clients | VS Code extension (embeds local server; sessions/diffs/send-selection documented as **out of scope** `editors/vscode/README.md:11-13`), Electron, Android, iOS | clients | y | y | `PRESENT` | `editors/vscode/README.md:3-60`; `web/electron/`; `web/android/`; `web/ios/`; `web/package.json`; `pnpm-workspace.yaml` |
| Slack conversational integration | Bot selects agent/host/workspace, starts/continues sessions, streams turns, relays approvals and questions | Slack | y | y | `PRESENT` | `integrations/slack/README.md`; `integrations/slack/pyproject.toml:5-22`; `integrations/slack/src/omnigent_slack/` |
| OpenClaw and generic ACP integration | Import OpenClaw coding agents or drive a live OpenClaw Gateway session over ACP; Devin and Grok ACP rows ship too | ACP/CLI/config | y | n | `PRESENT` | `docs/openclaw.md:14-120`; `omnigent/acp_cli_harnesses.py:83-118`; `omnigent/inner/acp_executor.py` |
| Server deployment menu | Docker/Compose, Render, Railway, Fly.io, HF Spaces, Modal, Cloudflare, Databricks Apps, Kubernetes; tunnels/Tailscale for reach. Constraint: in-memory runner registry ⇒ **single-replica** server (Cloudflare doc, general per its wording) | manifests/docs | y | y | `PRESENT` | `deploy/README.md:11-139`; `deploy/*/`; single-replica: `deploy/cloudflare/README.md:39-40` |
| Pluggable persistence and artifact stores | Postgres and SQLite first-class; artifacts on local disk, S3-compatible, Cloudflare R2, Databricks UC Volumes | server config | y | y | `PRESENT` | `deploy/README.md:135-161`; `pyproject.toml:152-157,274-293`; `omnigent/stores/artifact_store/`; `deploy/cloudflare/README.md:39-52`; `deploy/databricks/README.md:1-8` |

## Surface inventory

- **CLI:** entry points `omnigent` and `omni`, both → `omnigent.cli:main`
  (`pyproject.toml:379-387`). Source-defined groups: agent execution and
  session control (`run`, `resume`, `attach`, `import`, `session`), server
  lifecycle (`start`, `stop`, `server status`), host management, setup/login,
  upgrade/uninstall, diagnostics, integrations, sandbox create/connect
  (`omnigent/cli.py:3596-4326,4519-5022,5641-6206,7427-8080,9611-9876`;
  `omnigent/cli_sandbox.py:159-438`).
- **HTTP/API:** `openapi.json` (generated; 72 paths) declares agents,
  harnesses, hosts, runners, policies, policy registry, projects, sessions,
  child sessions, comments, permissions, MCP servers, session resources,
  sharing, usage, session SSE. **Known blind spots of this catalog:** it
  omits the entire scheduled-tasks REST family that exists in source
  (`omnigent/server/routes/scheduled_tasks.py:286-418`), and WebSocket
  surfaces (runner tunnel, terminal attach, dictation) are source-only
  (`omnigent/server/routes/runner_tunnel.py`, `terminal_attach.py`,
  `dictation.py`). Treat it as incomplete/stale, not authoritative.
- **Python SDKs:** client (`OmnigentClient`, sessions, streams, tools,
  elicitation, files, child-session helpers —
  `sdks/python-client/omnigent_client/__init__.py:29-125`) and UI SDK
  (`sdks/ui/omnigent_ui_sdk/__init__.py:14-43`).
- **Extension points:** YAML agent spec (executors, function/MCP/sub-agent
  tools §275-376, policies §377+, terminals §401+ — `docs/AGENT_YAML_SPEC.md`);
  community harness packages via the `omnigent.community.harness`
  entry-point group with collision checks (`omnigent/harness_plugins.py:48,
  111-137,827-991`); third-party sandbox providers via the
  `omnigent.sandbox_providers` entry-point group with a user-facing guide
  (`docs/extending/sandbox_providers.md:1-8`); native harness hook/bridge
  modules (`omnigent/*_native_hook.py`, `*_native_bridge.py`); skills
  (`.claude/skills/`, `examples/*/skills/`,
  `omnigent/tools/builtins/load_skill.py`); pluggable dictation engines
  (`omnigent/server/dictation.py:12-31,88-100`); custom policy modules
  (`docs/POLICIES.md:409-499`).
- **Services:** FastAPI/WebSocket server + host-side runner over a WebSocket
  tunnel (`deploy/README.md:216-234`); web SPA, Electron shell, Android/iOS,
  VS Code extension, Slack bot, dictation worker, managed-host launchers.
- **Storage:** Postgres or SQLite core DB (`deploy/README.md:141-161`);
  artifact stores local/S3/R2/UC Volumes (`omnigent/stores/artifact_store/`);
  Cloudflare deploy uses D1+R2 (`deploy/cloudflare/README.md:39-52`);
  Hindsight is optional long-term memory, not the core DB
  (`pyproject.toml:245-254`; `omnigent/tools/builtins/hindsight.py`).
- **Deploy targets:** hosting — Docker/Compose, Render, Railway, Fly.io, HF
  Spaces, Modal, Cloudflare, Databricks Apps, Kubernetes; access —
  Cloudflare quick tunnel, Tailscale (`deploy/README.md:111-139`). Managed
  sandbox providers — Modal, Daytona, Blaxel, Islo, E2B, CoreWeave,
  Kubernetes, OpenShell, Boxlite (`pyproject.toml:159-196`).

## Claims without artifacts

No documented capability was found at `ABSENT` — every README/docs claim
sampled had an implementation artifact locatable. Completeness is not
inferred from that. Three documented claims are **qualified** rather than
missing, and belong in any fitness reading:

- "**Use any model** … All first-class" (`README.md:37-38`) is bounded by
  the adapters, gateway kinds, and harness declarations actually present —
  four credential kinds, per-harness base-URL rules (`README.md:325-349`).
- Windows is a documented **degraded mode**: no native terminal wrappers, no
  bwrap/seatbelt filesystem or network isolation, no L7 egress proxy — Job
  Object containment only (`README.md:156-176`).
- The VS Code extension documents sessions, diffs, send-selection, and
  remote/embedded rendering as intentionally out of scope
  (`editors/vscode/README.md:11-13`).

## Artifacts without claims

Significant machinery present without a prominent claim in the main README:

- Community harness entry-point loading with contribution validation and
  collision checks (`omnigent/harness_plugins.py:827-991`) — mechanism
  documented in source; no user-facing guide for *harness* packages in
  `docs/` (the sibling `docs/extending/sandbox_providers.md` guide covers
  sandbox providers only).
- Built-in `open-responses`, ACP Devin, and ACP Grok harness registrations
  (`omnigent/harness_plugins.py:633-646`; `omnigent/acp_cli_harnesses.py:83-118`)
  — in the catalog, not in the README's harness list.
- The built-in tool catalog beyond the documented ones: `spawn.py`,
  `async_inbox.py`, `timer.py`, `browser.py`, seven `web_search_*` engines,
  `export_agent.py`, `search_conversations.py`, `nimble_extract.py` /
  `nimble_research.py` (+ optional `nimble` extra, `pyproject.toml:255-258`)
  (`omnigent/tools/builtins/`).
- Pluggable dictation engine registry (local/remote/fake/third-party)
  (`omnigent/server/dictation.py:12-31,88-100`) — not presented as a public
  extension surface.
- Harness capability catalog metadata (models, title generation, install,
  aliases, native providers) beyond the user-facing summary
  (`omnigent/harness_plugins.py:646-820`).

## Coverage and limits

- Read-only inspection; nothing from the target was executed (no scripts,
  CLI, tests, servers, or `--help`). The target's README/AGENTS.md were
  treated as evidence, not instructions.
- Read: README, CHANGELOG (recent), AGENTS.md, pyproject.toml, setup.py,
  package.json, pnpm-workspace.yaml, openapi.json, `omnigent/` top-level
  layout, `docs/` including `docs/extending/`, `web/`, `sdks/`,
  `integrations/`, `editors/`, `deploy/`, `.claude/skills/`, `dev/`,
  example names/configs. Excluded per triage: lockfiles, CI, vendored code,
  styling, example internals, `tests/` (except as capability evidence).
- No committed machine-generated inventory exists for `reference_tools/*`
  targets (the `harness_lifecycle/catalogs/` inventories cover
  `reference_harnesses/*` only), so the surface inventory above was built
  from the repo's own declarations. `openapi.json` is generated and was
  found **incomplete** (scheduled-tasks family absent) — flags derived from
  it are lower bounds.
- `PRESENT` is a location claim only: no wiring, call-path, concurrency,
  persistence-lifecycle, failure-mode, or security analysis was performed;
  provider combinations in the deploy docs were not validated.
- Version context: `0.11.0.dev0`, status alpha (`pyproject.toml:8`;
  README badge) — fast-moving upstream; expect drift between studies.

## Recommendation

**Escalate.** L1 cannot support a "critical part of workflow orchestration"
decision; the gap between located artifacts and traced behavior is exactly
where that decision's risk lives. Ranked L2 questions:

1. **Session/agent lifecycle for the orchestration core** — how sessions are
   created, resumed, interrupted, forked, and switched for the two or three
   harnesses we would actually use (Claude-native, claude-sdk, codex), not
   all families. The heart of the orchestration substrate.
2. **Headless embedding** — can Omnigent be driven as a component (Python
   SDK / HTTP+SSE) inside an existing harness: what the SDK can and cannot
   reach vs the web UI, given no SSE history replay on reconnect
   (`_sessions.py:1166-1169`).
3. **State and persistence model** — authoritative stores for conversations,
   sub-agents, files, scheduled runs, and runner presence; what the
   in-memory single-replica runner registry (`deploy/cloudflare/README.md:39-40`)
   costs for durability, restarts, and scale-out.
4. **Parent/child agent coordination** — how Polly-style delegation bounds,
   isolates (worktrees), reviews, and reconciles parallel children;
   `spawn.py`, `subagent_routing.py`, child-session routes.
5. **Smart routing contract** — inputs, decision persistence
   (`RoutingDecisionData`), external-router provider, and override paths;
   directly relevant to model/harness selection in our workflows.
6. **Extension contracts** — `omnigent.community.harness` (could our own
   harness register?), `omnigent.sandbox_providers`, YAML tools/MCP, policy
   modules: what is supported surface vs internal machinery.
7. **Trust and credential flow** — server / runner / host / sandbox
   boundaries, the secretless credential proxy and L7 egress proxy: what is
   actually enforced where, per platform (Windows exclusions).
8. **Delivery semantics** — SSE, WebSocket tunnels, approvals/elicitation
   under disconnects and concurrent clients; what a workflow controller can
   rely on.
