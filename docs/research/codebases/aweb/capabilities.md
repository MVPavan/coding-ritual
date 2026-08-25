> Produced by GPT-5.6-luna (xhigh), docs-first with code verification, 2026-08-24.
> Repo: reference_tools/aweb @ da5854cf. Static read-only audit — nothing executed.
> Known corrections from the two-reviewer assessment are recorded in ../comparison-beadboard-aweb-looptroop.md (fact-conflict rulings).

# aweb — docs-first capability and architecture map

This is a static, read-only repository audit. No installs, builds, tests, services, or `aw` commands were run. “WORKS-DOCUMENTED” means the documentation and visible implementation align; it is not live execution proof.

## 1. Identity

aweb is a self-hostable coordination layer for independently running AI agents. Its core promise is durable mail/chat, wake events, presence, and shared coordination state across sessions, runtimes, and machines. It explicitly does not own agent definitions, homes, worktrees, processes, or long-term runtime lifecycle. [DOC README.md:3-26]

The repository is a monorepo containing:

- `server/`: FastAPI coordination service and MCP mount.
- `awid/`: identity, address, namespace, team, certificate, and key-history registry.
- `cli/go/`: `aw` Go CLI and client library.
- `channel-core/`, `channel/`, `pi-extension/`: event delivery and runtime integrations.
- `naapp/`, `naapp-lib/`: optional Native Agentic App framework and bundled apps.
- `packages/`: Hermes, Codex, Claude, and other packaging/adapters.
- `docs/`, `test-vectors/`, and `scripts/`: contracts, fixtures, generated references, and verification tooling. [DOC README.md:195-207]

Maturity signals:

| Component | Version/status | Evidence |
|---|---:|---|
| aweb server | `1.27.4`, Python `>=3.12`, Beta classifier | [CODE server/pyproject.toml:1-18] |
| AWID | `0.5.19`, Python `>=3.12` | [CODE awid/pyproject.toml:1-24] |
| Claude channel | `1.7.7` | [CODE channel/package.json:1-4] |
| Pi extension | `0.3.8` | [CODE pi-extension/package.json:1-4] |
| Library/Folio apps | `0.1.0`, Alpha classifier | [CODE naapp/library/pyproject.toml:1-13; naapp/folio/pyproject.toml:1-13] |
| A2A, app registry/events, mutation hooks, session leases | Shipped experimental surfaces | [DOC docs/README.md:151-172; docs/a2a.md:1-4] |
| Repository activity | Multiple release, feature, test, and documentation commits on 2026-08-21/22 | [CODE `.git` history] |
| Tests | Broad declared unit, integration, E2E, Docker, release, federation, OATS, channel, CLI, and MCP suites; not run for this audit | [CODE Makefile:104-180; Makefile:249-350] |

The repository and its major packages declare the MIT license. [DOC README.md:218-220; CODE server/pyproject.toml:1-7; awid/pyproject.toml:1-7]

## 2. Capability map

| Capability | What it does | Evidence | Reachability |
|---|---|---|---|
| Core `aw` CLI | Bootstrap, workspace setup, identity, teams, mail, chat, events, tasks, locks, roles, diagnostics, plugins, A2A, blueprints, sessions, completion, versioning | [DOC docs/cli-command-reference.md] | WORKS-DOCUMENTED |
| Local diagnostics | `aw check`, granular `aw doctor` checks, support bundles, local/offline/online validation | [DOC docs/support-tools.md; docs/cli-command-reference.md] | WORKS-DOCUMENTED |
| AWID identity registry | Namespaces, `did:aw`, `did:key`, addresses, key history, identity registration/rotation, verification | [DOC docs/awid-sot.md:28-391] | WORKS-DOCUMENTED |
| AWID teams and certificates | Team creation, invitations, membership certificates, revocation, certificate verification, cross-namespace membership | [DOC docs/awid-sot.md:392-756] | WORKS-DOCUMENTED |
| Hosted/BYOT/local identity | Hosted custodial and self-custodial modes, local identities, global identities, multiple team memberships, address routing | [DOC docs/aweb-sot.md; docs/awid-sot.md; docs/current-limitations.md:28-45] | WORKS-DOCUMENTED |
| Signed authentication and trust | Ed25519 request signatures, team-certificate auth, identity-only auth, grants, v1/v2 signed envelopes, timestamps, revocation checks, TOFU pinning | [DOC docs/aweb-sot.md:auth sections; docs/trust-model.md; docs/identity.md] | WORKS-DOCUMENTED |
| Optional E2E encryption | Local X25519 keyring, E2E mail/chat mode, fail-closed encrypted delivery | [DOC docs/configuration.md:143-188; docs/identity.md; docs/receiving-events.md] | PARTIAL |
| Team lifecycle | Invite, join, leave, switch, add/remove members, certificate fetch/reissue, team administration | [DOC docs/cli-command-reference.md; docs/create-and-run-team.md] | WORKS-DOCUMENTED |
| Durable mail | Send, inbox, show by message/conversation, reply, exact acknowledgement, plaintext or encrypted content | [DOC docs/mail-and-chat.md; docs/aweb-sot.md] | WORKS-DOCUMENTED |
| Durable chat | Chat sessions, participants, history, pending conversations, send, read receipts, waits, exact session replies | [DOC docs/mail-and-chat.md; docs/cli-command-reference.md; packages/hermes-aweb-platform/README.md] | WORKS-DOCUMENTED |
| Wake/event stream | SSE event stream, initial actionable snapshot, mail/chat/task/control/app wake signals, keepalives | [DOC docs/receiving-events.md:11-107; CODE server/src/aweb/api.py:513-533] | WORKS-DOCUMENTED |
| Event reconnect and catch-up | Redis pub/sub reconnect, Postgres state polling, adapter-specific deduplication and delivery marks | [DOC docs/orchestrator-integration.md:163-228; CODE server/src/aweb/events.py:413-419] | PARTIAL |
| Presence and heartbeat | Agent presence, last activity, workspace status, heartbeat TTL, peer discovery | [DOC docs/aweb-sot.md; docs/cli-command-reference.md] | WORKS-DOCUMENTED |
| Contacts and routing | Contact management, open/team-and-contacts delivery policy, global first-contact routing, stored conversation continuation | [DOC docs/aweb-sot.md; docs/cli-command-reference.md] | WORKS-DOCUMENTED |
| Control signals | Interrupt, pause, resume, and other control notifications | [DOC docs/cli-command-reference.md; docs/receiving-events.md] | WORKS-DOCUMENTED |
| Native task queue | Optional tasks with title, description, priority, type, status, assignee, dependencies, comments, ready/active/blocked views | [DOC docs/tasks-and-work.md:9-87; docs/aweb-sot.md] | WORKS-DOCUMENTED |
| Claims and ownership | Assignment plus `in_progress` status, claim age bands, claimant activity, explicit review; no automatic expiry/release | [DOC docs/tasks-and-work.md:33-55] | WORKS-DOCUMENTED |
| Roles and instructions | Shared versioned operating instructions, roles, role names, history, activation/reset | [DOC docs/roles-instructions-locks.md:8-63] | WORKS-DOCUMENTED |
| Locks and reservations | Short-TTL resource locks separate from task ownership; acquire, renew, release, revoke, inspect | [DOC docs/roles-instructions-locks.md:65-92; docs/aweb-sot.md] | WORKS-DOCUMENTED |
| Agent/workspace/repository projections | Runtime metadata, workspaces, repositories, agent status, connect/reconnect, retirement state | [DOC docs/orchestrator-integration.md:20-53; CODE server/src/aweb/api.py:513-533] | WORKS-DOCUMENTED |
| REST/FastAPI server | Agent, app, connect, chat, dashboard, claims, contacts, conversations, events, federation, grants, messages, reservations, leases, roles, tasks, workspaces, and repository routes | [DOC docs/aweb-sot.md; CODE server/src/aweb/api.py:513-533] | WORKS-DOCUMENTED |
| Health/OpenAPI surface | `/health`; FastAPI-generated REST documentation; service health checks | [DOC server/README.md:20-32; docs/README.md:188-204; CODE server/src/aweb/api.py:407-511] | WORKS-DOCUMENTED |
| MCP server | Streamable HTTP MCP mount at `/mcp/`; tools for identity display, mail, chat, tasks, work, roles, instructions, contacts, presence, heartbeat, workspace status | [DOC docs/aweb-sot.md:MCP section; DOC server/README.md:6-13; CODE server/src/aweb/api.py:90-101] | WORKS-DOCUMENTED |
| Dashboard API | JWT-protected external dashboard-oriented reads for tasks, claims, events, roles, and status; no core dashboard application is included | [DOC docs/aweb-sot.md:dashboard section] | PARTIAL |
| `aw run` launcher | Event-aware local loop for Claude and Codex, prompt dispatch, optional work autofeed, model/flag forwarding, session continuation, bounded run count | [DOC docs/aw-run.md:1-126; CODE cli/go/run/loop.go:141-275] | PARTIAL |
| Claude Code channel | One-way inbound delivery of mail/chat/tasks/control into Claude; outbound actions use `aw` CLI | [DOC channel/README.md:1-27; CODE channel-core/src/channel.ts:542-625] | WORKS-DOCUMENTED |
| Pi extension | Real-time Pi wakeups, sender verification, chat/mail/control handling, bundled skills, CLI-based outbound actions | [DOC pi-extension/README.md; docs/receiving-events.md:167-189] | WORKS-DOCUMENTED |
| Headless/custom runtimes | Raw SSE or CLI polling integration; consumer must fetch durable state and implement action idempotency | [DOC README.md:175-193; docs/orchestrator-integration.md:163-228] | WORKS-DOCUMENTED |
| Agent home/profile materialization | Creates independent homes, `.aw` state, profile files, instruction files, and optional worktrees; supports profile/blueprint references | [DOC docs/running-agents.md; docs/profiles-and-blueprints.md] | WORKS-DOCUMENTED |
| Runtime launch orchestration | `aw team admin up` can launch Claude Code and Pi using tmux; Codex and `local-shell` can be materialized but must start manually | [DOC docs/current-limitations.md:13-18; CODE cli/go/cmd/aw/team_up.go:308-318] | PARTIAL |
| Codex/Claude skills packaging | Canonical coordination, messaging, team-membership, bootstrap, and identity skills packaged for Codex, Claude Code, Claude.ai, and Pi | [DOC packages/codex-plugin/README.md; packages/claude-skills/README.md; pi-extension/package.json:21-30] | WORKS-DOCUMENTED |
| Harness-neutral resource packs | Shared roles, instructions, review-loop, handoff, and company-surface resources; deliberately does not create identities, worktrees, or runtime files | [DOC resource-packs/coord-workflows/README.md; resource-packs/company-surfaces/README.md] | WORKS-DOCUMENTED |
| Hermes gateway adapter | Prototype platform adapter that consumes `aw events`, fetches exact bodies, injects Hermes events, replies, and acknowledges after presentation | [DOC packages/hermes-aweb-platform/README.md] | PARTIAL |
| A2A interoperability | A2A Agent Cards, JSON-RPC gateway, send/status/cancel/card/publish CLI, AWID publication and delegation assertions | [DOC docs/a2a.md:1-51; docs/a2a.md:395-453] | PARTIAL |
| A2A durability | Underlying bridged aweb mail is durable, but the gateway’s own task/poll state is in memory and is lost on restart | [DOC docs/a2a.md:422-440] | PARTIAL |
| App manifests | Manifest-driven operations mapped to canonical `aw` verbs or signed raw HTTP; app registry stores declarations and scopes | [DOC docs/app-manifest.md; docs/app-registry.md] | PARTIAL |
| App-emitted events | App event emitters, subscriptions, SSE delivery, event metadata, agent/team subscription scope | [DOC docs/app-events.md; CODE server/src/aweb/routes/apps.py; server/src/aweb/app_events.py] | PARTIAL |
| Library profiles/blueprints | Public blueprint catalog, private team shelf, versions, bindings, materialization, publishing, proposals | [DOC naapp/library/README.md:1-42; CODE naapp/library/src/library/api.py:280-533] | PARTIAL |
| Folio documents/presentations | Team-cert-authored append-only Markdown documents, versions, themes, no-login presentation links, optional Cloudflare Stream media | [DOC naapp/folio/README.md:1-120] | WORKS-DOCUMENTED |
| Blueprint search | Intended public profile discovery command | [DOC docs/current-limitations.md:20-26] | DECLARED-ONLY |
| Beads integration | No Beads adapter or `bd` task provider; native tasks are optional and the launcher explicitly excludes bead-specific dispatch | [DOC docs/tasks-and-work.md:9-16; CODE cli/go/cmd/aw/run.go:78] | PARTIAL |
| OpenCode integration | No visible OpenCode launcher or adapter; generic SSE/CLI integration remains possible | [DOC docs/aw-run.md:39-51; docs/orchestrator-integration.md:10-18] | DECLARED-ONLY |

## 3. Architecture sketch

```text
Existing agent/runtime
    │
    ├── aw CLI ─────────────── signed HTTP ──────────────┐
    ├── Claude channel / Pi / Hermes adapters             │
    ├── custom SSE/polling consumer                       │
    └── MCP client ───── Streamable HTTP /mcp/ ──────────┤
                                                        ▼
                                             aweb FastAPI service
                                                        │
                   ┌────────────────────────────────────┼────────────────────────┐
                   │                                    │                        │
             PostgreSQL                            Redis                  AWID registry
          durable coordination                  cache/pubsub/TTL        identity authority
                   │                                    │                        │
       tasks, messages, chats,                 wake signals,              identities,
       agents, workspaces,                     presence, cache,           namespaces,
       claims, locks, roles,                   rate-limit backend         teams, certs,
       instructions, outboxes                                             key history
```

The aweb server owns coordination state. AWID owns public identity and membership authority. The CLI and runtime adapters are clients. Orchestrators remain responsible for agent processes, homes, worktrees, provider choice, and session UX. [DOC README.md:15-26; docs/orchestrator-integration.md:10-33]

### Protocol and service boundaries

- CLI and adapters use signed HTTP requests to aweb and AWID. [DOC docs/aweb-sot.md; docs/awid-sot.md]
- Runtime wakeups use SSE. The event is a signal containing identifiers; durable mail/chat content is fetched separately. [DOC docs/receiving-events.md:11-107]
- MCP is mounted as a FastAPI sub-application at `/mcp/`. [CODE server/src/aweb/api.py:90-101]
- AWID is accessed as an HTTP registry by the aweb server and CLI. The aweb server does not write identity authority or hold private identity/controller keys. [DOC README.md:19-22; docs/awid-sot.md:28-133]
- Redis pub/sub carries low-latency signals but is intentionally not the durable queue. [CODE server/src/aweb/events.py:413-419]
- A2A uses ordinary JSON-RPC gateway semantics and maps inbound A2A work to durable aweb mail. [DOC docs/a2a.md:422-440]

### Durable and local state

| State | Location | Durability/authority |
|---|---|---|
| Mail, chat, read receipts, agents, workspaces, tasks, comments, dependencies, claims, roles, instructions, locks, app registry, grants, leases, federation, lifecycle outboxes | PostgreSQL `aweb` schema | Primary durable aweb state | [DOC docs/aweb-sot.md:DB schema section] |
| Identity logs, namespaces, addresses, teams, certificates, revocations, A2A publication assertions | AWID PostgreSQL schema/service | Primary identity and membership authority | [DOC docs/awid-sot.md:757-828] |
| Redis cache, pub/sub, presence and rate-limit support | Redis | Ephemeral/cache/infrastructure state | [DOC docs/aweb-sot.md; server/README.md:69-80] |
| Local identity, signing key, team certificates, workspace binding, encryption keyring, profile, context | `.aw/` in each agent/worktree | Agent-local credential and runtime state | [DOC docs/configuration.md:40-203] |
| AWID controller keys | `~/.awid/` | Operator/controller private state | [DOC docs/configuration.md:16-25; docs/awid-sot.md] |
| CLI support, run, TOFU, and adapter state | `~/.config/aw/` | Local consumer state | [DOC docs/configuration.md:27-38] |
| Channel delivery marks and undelivered diagnostics | `~/.config/aw/channel-delivered-ids.json`, related files | Adapter-local persistent dedupe/diagnostics | [CODE channel-core/src/channel.ts:21-29; :211-224] |
| A2A gateway task/poll state | Gateway process memory | Lost on gateway restart; underlying aweb message remains durable | [DOC docs/a2a.md:422-440] |

### Crash and restart behavior

Aweb schedules lifecycle and federation outbox replay at startup and on request middleware. Standalone mode initializes Redis, the database, AWID client, MCP, and replay tasks; embedded/library mode uses caller-owned connections. [CODE server/src/aweb/api.py:227-340]

Redis pub/sub messages can be lost during reconnect. Consumers are expected to obtain a fresh snapshot and/or poll durable Postgres state. [CODE server/src/aweb/events.py:413-419] The raw event stream has no resumable server cursor, SSE `id`, or `Last-Event-ID`; `aw run` only adds bounded in-memory deduplication. [DOC docs/orchestrator-integration.md:171-187]

Channel Core persists delivery marks locally and uses cross-process locking. [CODE channel-core/src/channel.ts:211-224] A provider loop’s run/session state is process-local; continuation depends on the provider session ID being reported and retained by the loop. [CODE cli/go/run/loop.go:335-375]

### Single- versus multi-machine model

A local Docker Compose deployment runs aweb, AWID, PostgreSQL, and Redis together. [DOC README.md:145-160; server/README.md:20-32] In the multi-machine model, independent agent homes and runtime processes connect to a shared aweb origin; AWID and DNS-backed routing provide global identity/addressability. [DOC docs/self-hosting-guide.md:131-311; docs/orchestrator-integration.md:13-18]

There is no built-in remote process supervisor or unified provisioning service. Runtime launch helpers are local and tmux-based; an external orchestrator must retain the mapping between its agent instance and aweb identity/workspace. [DOC docs/orchestrator-integration.md:10-18,35-80; CODE cli/go/cmd/aw/team_up.go:321-330]

## 4. Execution and orchestration model

### Work representation

aweb’s native work object is an optional task, not a Bead. A task has descriptive fields, status, assignee, dependencies, comments, and a claim signal. `aw work ready`, `active`, and `blocked` provide shared views. [DOC docs/tasks-and-work.md:9-87]

The ownership convention is assignment plus `in_progress`; there is no separate claim mutation in the user-facing CLI. Claims age into neutral review bands but do not expire automatically. [DOC docs/tasks-and-work.md:33-55]

External task providers are explicitly allowed. The orchestrator owns the task provider, and aweb messaging does not require the native task queue. [DOC docs/tasks-and-work.md:9-16; docs/orchestrator-integration.md:10-18]

### Agent creation, attachment, and runtime ownership

There are two distinct paths:

1. An existing agent directory is initialized or joined with `aw init`, `aw team invite`, `aw team join`, and `aw workspace connect`.
2. `aw team admin create/add` materializes agent homes, profiles, instructions, `.aw` state, and optional worktrees; `aw team admin up` launches supported runtimes. [DOC README.md:43-90; docs/create-and-run-team.md; docs/running-agents.md]

The orchestrator remains the owner of definitions, instances, homes, worktrees, processes, runtime choice, and task provider. There is explicitly no unified provisioning API. [DOC docs/orchestrator-integration.md:8-18]

The launch helper currently supports Claude Code and Pi only. Codex and `local-shell` can be materialized but must be started manually. [DOC docs/current-limitations.md:13-18; CODE cli/go/cmd/aw/team_up.go:308-318]

### Provider invocation

| Provider | Actual invocation | Session/model behavior |
|---|---|---|
| Claude | `claude -p --output-format stream-json --verbose --include-partial-messages`; defaults to `--dangerously-skip-permissions`; supports `--continue`, `--resume`, `--allowedTools`, `--model` | [CODE cli/go/run/provider_claude.go:13-55] |
| Codex | `codex exec --skip-git-repo-check`; defaults to `--dangerously-bypass-approvals-and-sandbox`; uses `--json`, `resume`, `--image`, and `-m` | [CODE cli/go/run/provider_codex.go:32-74] |
| Pi | Not driven by `aw run`; Pi owns its runtime/model process and receives aweb wakeups through the extension | [DOC docs/receiving-events.md:167-189; pi-extension/README.md] |
| Custom/headless | Consumer owns its process and reads SSE or polls through CLI/API | [DOC docs/orchestrator-integration.md:163-228] |

`aw run` has only Claude and Codex providers in its provider factory. [CODE cli/go/run/provider.go:9-17] `--model` is forwarded to the selected provider; there is no repository-level model registry or model scheduler. [DOC docs/aw-run.md:39-51; CODE cli/go/run/provider_claude.go:38-40; provider_codex.go:58-60]

### Loop, retry, and wake behavior

The `aw run` loop:

1. Starts the event bus.
2. Waits for an initial prompt or event.
3. Builds a prompt from mail/chat/work context.
4. Invokes the provider.
5. Runs post-delivery finalization.
6. Waits for the next event or exits at `--max-runs`, user stop, provider error, or session termination. [CODE cli/go/run/loop.go:141-275]

The event bus retries transient stream failures with bounded backoff, deduplicates recent events in memory, and fails fast on authentication errors. [CODE cli/go/run/eventbus.go:146-315] The raw `aw events stream` command itself does not reconnect. [DOC docs/orchestrator-integration.md:171-177]

Runtime adapters fetch exact durable message/chat records before presentation and acknowledge only after their presentation point. [DOC docs/receiving-events.md:66-130; CODE channel-core/src/channel.ts:575-625]

### Completion and human gates

Task completion is explicit. The guidance says to close only after verification, with a reason containing evidence; blocked work remains open with a handoff. There is no visible semantic completion evaluator or automatic task close. [DOC docs/tasks-and-work.md:91-110]

Claims are not auto-released, locks are manual TTL reservations, and roles/instructions are guidance rather than authority. [DOC docs/tasks-and-work.md:44-55; docs/roles-instructions-locks.md:33-46,65-92]

The bundled review loop is a human/coordinator workflow: developer records validation, reviewer checks against the task/SOT, developer fixes and reruns gates, reviewer accepts, and coordinator closes or sequences work. It is a resource-pack playbook, not a server-side review engine. [DOC resource-packs/coord-workflows/resources/playbooks/review-loop.md]

Human/authority gates include team invitation/certificate operations, support for human authority claims, explicit task close, reviewer acceptance, and optional provider safety mode via `--trip-on-danger`. [DOC docs/current-limitations.md:28-38; docs/aw-run.md:68-80]

## 5. Dependencies and operational cost

### Core runtime

The aweb server requires Python `>=3.12`, FastAPI/Uvicorn, Pydantic, `pgdbm`, PostgreSQL access, Redis, cryptographic libraries, HTTP clients, and the AWID service package. [CODE server/pyproject.toml:1-75]

AWID is another Python `>=3.12` service using FastAPI, `pgdbm`, PostgreSQL, Redis, DNS/public-suffix handling, HTTP, and NaCl cryptography. [CODE awid/pyproject.toml:1-54]

The CLI is Go `1.24.13` and uses Cobra, PTY/terminal libraries, YAML, JCS, base58, and networking dependencies. [CODE cli/go/go.mod:1-20]

The Node runtime surfaces require Node/npm. Channel Core uses TypeScript, Ed25519/hash libraries, YAML, file locking, and TLD parsing. [CODE channel-core/package.json:1-35] The Pi extension depends on the `aw` package and the Pi coding-agent runtime. [CODE pi-extension/package.json:21-45]

### Deployment footprint

The documented self-hosted minimum is four Compose services:

- aweb;
- AWID;
- PostgreSQL;
- Redis. [DOC README.md:145-160; server/README.md:20-32]

Required/important configuration includes:

- `DATABASE_URL` or `AWEB_DATABASE_URL`;
- `REDIS_URL` or `AWEB_REDIS_URL`;
- `AWID_REGISTRY_URL`;
- shared `AWID_SERVICE_TOKEN` of at least 32 bytes;
- host/port settings;
- optional dashboard JWT secret. [DOC server/README.md:69-83]

Global/BYOT identity adds DNS/domain/controller setup and certificate management. [DOC docs/self-hosting-guide.md:193-311; docs/awid-sot.md:134-228]

Operationally, the system requires persistent Postgres backups and Redis availability, although Redis pub/sub loss is tolerated through durable-state catch-up. Garbage collection is scheduled externally rather than being an automatic core service. [DOC docs/aweb-sot.md:GC/configuration sections]

Optional cost/footprint:

- tmux for `aw team admin up`. [CODE cli/go/cmd/aw/team_up.go:321-330]
- Installed Claude or Codex CLIs for `aw run`.
- Pi runtime for the Pi extension.
- Hermes for the Hermes adapter.
- Cloudflare Stream credentials if Folio video is enabled. [DOC naapp/folio/README.md:25-50]
- Docker for full E2E and self-host tests. [DOC Makefile:326-390]

The repository declares an extensive verification and release system, including locked Python suites, Go tests, Node tests, source-inventory checks, protocol vectors, federation harnesses, A2A tests, OATS, Docker E2E, and exact-publish checks. None were executed in this audit. [CODE Makefile:108-180,249-350,439-481]

## 6. Docs-versus-reality gaps

1. **Library README is materially stale relative to its source.** The README describes a scaffold whose public catalog is empty and whose team writes are `501` stubs. The current API exposes public blueprint reads, shelf/profile operations, publishing, materialization, bindings, tags, and proposals; the repository layer persists blueprint/profile data. [DOC naapp/library/README.md:16-22; CODE naapp/library/src/library/api.py:280-533; naapp/library/src/library/repository.py:114-193]  
   This is the clearest documentation/reality contradiction in the repository.

2. **The core SOT inventories are explicitly not fully authoritative at the mechanical inventory level.** The README says the hand-maintained route/schema inventories carry accuracy notices pending source reconciliation, while the CLI reference is generated from live Cobra help. [DOC README.md:209-216]  
   A deeper consumer should treat source routes, migrations, and generated references as the final reconciliation set.

3. **The Claude channel release notes lag its package manifest.** `channel/package.json` reports `1.7.7`, while the top changelog heading is `1.7.6`. [CODE channel/package.json:1-4; DOC channel/CHANGELOG.md:1-8]  
   This may be intentional pending release-note publication, but it is a release-documentation drift signal.

4. **A2A durability is intentionally weaker than the surrounding aweb durability model.** The bridge’s mail is durable, but gateway task/poll state is process-memory-only. The documentation states this directly; it should not be treated as an implementation accident or as a durable task queue. [DOC docs/a2a.md:422-440]

5. **Event delivery is at-least-once/reconciliation-oriented, not cursor-based.** The lack of SSE cursors and the bounded in-memory `aw run` dedupe are documented, but consumers needing exactly-once tool effects must build their own action journal and idempotency keys. [DOC docs/orchestrator-integration.md:171-228]

6. **Runtime support is deliberately asymmetric.** Materialization supports more runtime kinds than the local launcher. Claude/Pi launch automatically; Codex/local-shell require manual startup. [DOC docs/current-limitations.md:13-18; CODE cli/go/cmd/aw/team_up.go:308-318]

7. **Beads and OpenCode are not hidden capabilities.** The repository contains no visible Beads adapter and explicitly excludes bead-specific dispatch. The provider launcher supports only Claude and Codex; other runtimes must use the generic integration seam. [DOC docs/tasks-and-work.md:9-16; CODE cli/go/cmd/aw/run.go:78; CODE cli/go/run/provider.go:9-17]

8. **Hosted-service claims are not locally verifiable from this audit.** README references `app.aweb.ai`, `api.awid.ai`, and `library.aweb.ai`, but no live service or network behavior was checked. [DOC README.md:11-13; docs/current-limitations.md:20-26]

## 7. Open questions for a deeper pass

- Which exact published version does the Go CLI currently represent? Read `scripts/cli-release-version.sh`, `scripts/check-cli-release-version-test.sh`, `cli/go/.goreleaser.yaml`, and the tag/release workflow. The source npm wrapper intentionally contains `0.0.0` placeholders. [CODE cli/go/npm/aw/package.json:1-27; scripts/cli-release-version.sh:9-71]

- Is `naapp/library/README.md` awaiting a status update, or is its richer API intentionally unreleased? Read the Library CI/release workflow, deployment configuration, and current tests beside `naapp/library/src/library/api.py` and `repository.py`.

- Which aweb SOT tables are generated versus manually maintained, and what is the current authoritative route/schema reconciliation procedure? Read `scripts/check_sot_source_inventories.py`, `server/src/aweb/migrations/aweb/`, `server/src/aweb/api.py`, and `docs/aweb-sot.md`.

- What federation behavior is enabled by default in production, and which routes are only harness-tested? Read `server/src/aweb/federation/`, `docs/federation-error-reference.md`, `docs/self-hosting-guide.md:311-372`, and the federation E2E harness.

- What is the intended persistence roadmap for A2A gateway task state? Read `packages`/gateway source, `docs/a2a.md:548-580`, and `Makefile` A2A gateway E2E targets.

- What external dashboard implementation consumes the dashboard API, and which JWT claims/routes are stable? Read dashboard route modules under `server/src/aweb/routes/`, dashboard-related deployment files, and `docs/aweb-sot.md`.

- Are Library and Folio part of the supported aweb release boundary or merely bundled reference apps? Read `docs/oss-boundary.md`, `docs/e2e-library-stack.md`, each app’s Docker/CI configuration, and the release scripts.

- What is the supported adapter contract for a new runtime such as OpenCode? Read `docs/runtime-support.md`, `docs/receiving-events.md`, `channel-core/README.md`, and the runtime resource-pack adapters.


