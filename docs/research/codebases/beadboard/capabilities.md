> Produced by GPT-5.6-luna (xhigh), docs-first with code verification, 2026-08-24.
> Repo: reference_tools/beadboard @ 9e3059d. Static read-only audit — nothing executed.
> Known corrections from the two-reviewer assessment are recorded in ../comparison-beadboard-aweb-looptroop.md (fact-conflict rulings).

# BeadBoard repository map

## Scope and evidence policy

This is a static, docs-first inspection. I did not install dependencies, start services, build, run tests, or execute BeadBoard. `WORKS-DOCUMENTED` therefore means “a visible implementation path exists,” not “runtime-tested.” [CODE package.json:10-20]

## 1. Identity

BeadBoard is a local Beads operations console: a Next.js dashboard, `bb`/`beadboard` CLI, agent coordination layer, and embedded Pi-based worker runtime. It presents Beads tasks through Social and Graph views, adds agent mail/reservations/session views, watches project state, and can launch an in-process orchestrator with worker sessions. [DOC README.md:9-13; DOC CLAUDE.md:5-9; CODE src/app/page.tsx:1-100]

Its stated product identity is still immature: README calls the `bb-pi` orchestrator “under construction”; package version is `0.1.0` and `private: true`; the roadmap says Phases 1–3 shipped, Phase 4 is partial, Phase 5 is not done, and later phases are largely incomplete. [DOC README.md:1; CODE package.json:1-8; DOC docs/plans/2026-03-05-embedded-pi-roadmap.md:10-31,180-229]

A substantial, explicitly enumerated test suite and CI smoke workflow exist, but neither was executed for this report. [CODE package.json:16-20; DOC .github/workflows/installer-smoke.yml:1-50]

License: MIT. [DOC LICENSE:1-21; CODE package.json:7]

## 2. Capability map

| Capability | What it does | Evidence | Reachability |
|---|---|---|---|
| Beads task storage | Reads issues, labels, comments, dependencies, and agent beads from Dolt first, falling back to `.beads/issues.jsonl`. | [DOC README.md:101-117; CODE src/lib/read-issues.ts:54-81; CODE src/lib/read-issues-dolt.ts:69-124] | WORKS-DOCUMENTED |
| Beads mutations | Creates, updates, closes, reopens, and comments on beads through the `bd` CLI bridge. | [DOC CLAUDE.md:88-90; CODE src/lib/mutations.ts:244-334] | WORKS-DOCUMENTED |
| REST bead API | Exposes bead read/create/update/close/reopen/comment operations. | [DOC docs/api-reference.md:1-91; CODE src/app/api/beads/[id]/route.ts, src/app/api/beads/route.ts] | WORKS-DOCUMENTED |
| Dashboard shell | Main query-driven page with Social and Graph surfaces, task/agent/epic panels, runtime console, and SSE subscriptions. | [DOC CLAUDE.md:47-64; CODE src/app/page.tsx:1-100; CODE src/components/shared/unified-shell.tsx:52-218,310-500] | WORKS-DOCUMENTED |
| Social view | Displays operational task/social activity and contextual panels. | [DOC README.md:121-126; CODE src/components/shared/unified-shell.tsx:320-353] | WORKS-DOCUMENTED |
| Dependency Graph view | Renders DAG-oriented task/dependency views using React Flow/Dagre. | [DOC README.md:182-190,273-282; CODE src/components/shared/unified-shell.tsx:320-353] | WORKS-DOCUMENTED |
| Activity/timeline feed | Uses activity history, watcher diffs, and SSE to show live activity. | [DOC docs/features/timeline.md:1-29; CODE src/lib/realtime.ts:95-190; CODE src/app/api/events/route.ts:1-154] | PARTIAL |
| Activity as a primary view | Documentation describes Activity and `/timeline`, but current navigation only accepts Social and Graph; `/timeline` redirects to `?view=activity`, which the hook does not recognize. | [DOC README.md:121-126; DOC docs/features/timeline.md:1-29; CODE next.config.ts:7-29; CODE src/hooks/use-url-state.ts:1-57,96-147; CODE src/components/shared/left-panel-new.tsx:49-52] | PARTIAL |
| Agent registration | Registers agents as Beads agent records, assigns labels, and tracks state through `bd agent`. | [DOC README.md:128-150; CODE src/lib/agent/registry.ts:194-313] | WORKS-DOCUMENTED |
| Agent liveness | Derives active/stale/evicted/idle status from heartbeat/activity timestamps. | [DOC README.md:203-207; CODE src/lib/agent/registry.ts:379-394] | PARTIAL |
| Agent activity leases | Creates ephemeral heartbeat events through `bd create ... --wisp-type heartbeat`. | [DOC README.md:128-150; CODE src/lib/agent/registry.ts:396-445] | WORKS-DOCUMENTED |
| Legacy agent mail | Sends, lists, reads, acknowledges, and routes messages by agent, role, or broadcast. | [DOC README.md:159-173; CODE src/lib/agent-mail.ts:7-12,125-135,192-436] | WORKS-DOCUMENTED |
| Reservations | Claims path scopes with TTLs, overlap detection, locks, release, and stale takeover. | [DOC README.md:175-180; CODE src/lib/agent-reservations.ts:81-132,323-477] | PARTIAL |
| Coordination protocol v1 | Defines append-only SEND/READ/ACK/RESERVE/RELEASE/TAKEOVER/HANDOFF/etc. events and projections. | [DOC docs/protocols/2026-02-28-bd-audit-coordination-schema.md:1-120; CODE src/lib/coord-schema.ts:1-115; CODE src/lib/coord-events.ts:32-72] | PARTIAL |
| Coordination projections | Reads `.beads/interactions.jsonl` and derives inbox, acknowledgements, reservations, and incursions. | [DOC docs/plans/2026-02-28-bd-only-coordination-migration-plan.md:125-247; CODE src/lib/coord-projections.ts:61-260] | UNCLEAR |
| Session feed | Groups task/epic work, liveness, communications, and incursions for the sessions UI. | [DOC docs/features/agent-sessions.md:1-130; CODE src/lib/agent-sessions.ts:1-323; CODE src/app/api/sessions/route.ts:1-70] | PARTIAL |
| Conversation drawer | Shows comments and coordination messages; supports comment, read, and acknowledge actions. | [DOC docs/features/agent-sessions.md:52-74; CODE src/components/sessions/conversation-drawer.tsx:17-55,172-196] | PARTIAL |
| Multi-project registry | Registers local projects under a user-profile registry, lists them, scans roots, and supports aggregate views. | [DOC README.md:209-214; DOC docs/plans/2026-02-13-multi-project-ui-contract.md; CODE src/lib/registry.ts:1-140; CODE src/lib/scanner.ts:1-275] | WORKS-DOCUMENTED |
| Project-scoped reads | Reads a selected project or aggregates issues while prefixing IDs and remapping dependencies. | [DOC README.md:209-214; CODE src/lib/project-scope.ts:1-104; CODE src/lib/aggregate-read.ts:1-78] | WORKS-DOCUMENTED |
| Swarm/molecule integration | Invokes `bd swarm create`, `bd mol pour`, lists swarms, and assigns/joins agents. | [DOC docs/plans/2026-02-19-swarm-page-redesign.md; DOC docs/plans/2026-02-20-swarm-view-remake-design.md; CODE src/app/api/swarm/create/route.ts; CODE src/app/api/swarm/launch/route.ts; CODE src/lib/swarm-molecules] | PARTIAL |
| Archetypes and templates | Provides built-in agent roles and workflow templates and exposes CRUD APIs. | [DOC README.md:192-201; CODE src/lib/server/beads-fs.ts:1-24,96-324] | PARTIAL |
| `bb` CLI agent commands | Supports register/list/show/activity-lease/send/inbox/read/ack/reserve/release/status. | [DOC README.md:128-180; CODE src/cli/beadboard-cli.ts:52-280] | WORKS-DOCUMENTED |
| `bb daemon` commands | Provides start/status/stop/bootstrap/bootstrap-pi/tui entry points. | [DOC README.md:217-231; CODE src/cli/beadboard-cli.ts:283-377] | PARTIAL |
| Daemon status/runtime API | Exposes runtime status, orchestrator, launch, prompt, spawn, worker status, events, and stream routes. | [DOC docs/adr/2026-03-05-bb-daemon-attachment-model.md:1-64; CODE src/app/api/runtime/status/route.ts; CODE src/app/api/runtime/launch/route.ts; CODE src/app/api/runtime/stream/route.ts:1-79] | PARTIAL |
| Embedded Pi orchestrator | Creates a project runtime, attaches an in-process Pi session, supplies custom BeadBoard tools, and prompts an orchestrator. | [DOC docs/plans/2026-03-05-embedded-pi-prd.md; CODE src/lib/bb-daemon.ts:60-219; CODE src/lib/pi-daemon-adapter.ts:50-271] | PARTIAL |
| Worker spawning | Spawns numbered Pi worker sessions with role/capability-specific tools and isolated worker-session directories. | [DOC README.md:223-231; CODE src/lib/worker-session-manager.ts:1-307] | PARTIAL |
| Worker completion | Marks a worker completed when Pi emits `agent_end` with an assistant response and no error stop reason. | [DOC docs/plans/2026-03-05-embedded-pi-prd.md; CODE src/lib/worker-session-manager.ts:377-414] | PARTIAL |
| Worker result inspection | Returns in-memory worker result summaries and optionally reads the associated bead. | [CODE src/tui/tools/bb-worker-results.ts:14-114] | WORKS-DOCUMENTED |
| Template-based team spawning | Selects a template and asynchronously spawns its members. | [DOC README.md:192-201; CODE src/tui/tools/bb-spawn-template.ts:20-141] | PARTIAL |
| Interactive Pi TUI | Runs a local Pi session with workspace, model, login, mail, presence, and Beads tools. | [DOC README.md:223-231; CODE src/tui/bb-agent-tui.ts:15-25,61-88,167-470] | WORKS-DOCUMENTED |
| Model/provider selection | Uses Pi’s model registry and exposes Anthropic, GitHub Copilot, Gemini CLI, and Antigravity login paths. | [CODE src/tui/bb-agent-tui.ts:243-351,390-470; CODE src/lib/pi-daemon-adapter.ts:50-131] | WORKS-DOCUMENTED |
| Claude/Codex/OpenCode CLI driving | A generic runner or adapters for Claude CLI, Codex CLI, or OpenCode are not visible. | [DOC README.md:217-231; CODE src/lib/embedded-runtime.ts:3-28; CODE src/lib/pi-daemon-adapter.ts:1-30] | DECLARED-ONLY |
| Realtime watcher/SSE | Watches Beads files, WAL, touch markers, templates, archetypes, and legacy mail, then emits issue/activity SSE. | [DOC README.md:203-207,284-296; CODE src/lib/watcher.ts:35-146; CODE src/app/api/events/route.ts:1-154] | PARTIAL |
| Installer/runtime manager | Provides POSIX and PowerShell wrappers, runtime metadata, start/open/status, shims, and a manifest. | [DOC install/manifest.json:1-24; DOC docs/adr/2026-03-03-global-installer-contract-and-manifest.md; CODE install/install.sh:1-81; CODE install/install.ps1:1-64; CODE install/beadboard.mjs:1-300] | PARTIAL |
| Self-update/rollback | ADRs describe update, rollback, and atomic runtime management, but CLI self-update is a placeholder. | [DOC docs/adr/2026-03-03-runtime-manager-global-install.md:7-54; CODE src/cli/beadboard-cli.ts:418-425] | DECLARED-ONLY |
| Diagnostics | `beadboard status` performs launcher-level checks; `doctor` currently returns install metadata rather than a full health diagnosis. | [DOC README.md:128-150; CODE install/beadboard.mjs:1-300; CODE src/cli/beadboard-cli.ts:405-415] | PARTIAL |

## 3. Architecture sketch

```text
Browser
  └─ Next.js unified shell
       ├─ REST APIs
       ├─ /api/events and runtime SSE
       └─ in-process singleton runtime

Next.js server
  ├─ Beads read path
  │    ├─ Dolt SQL via mysql2
  │    └─ .beads/issues.jsonl fallback
  ├─ mutation bridge
  │    └─ bd CLI
  ├─ Chokidar watcher
  │    └─ issue/activity event buses
  ├─ legacy coordination
  │    ├─ ~/.beadboard/agent/messages
  │    └─ ~/.beadboard/agent/reservations
  └─ Pi runtime
       ├─ orchestrator session
       └─ in-memory worker sessions
```

The durable project source is intended to be Beads: Dolt is primary, JSONL is fallback, and `.beads/last-touched` drives freshness notifications. [DOC README.md:101-117,284-296; CODE src/lib/read-issues.ts:54-81; CODE src/lib/watcher.ts:113-146]

Dolt uses a local SQL server, normally `127.0.0.1`, with project metadata determining connection details. [DOC .beads/config.yaml:1-6; DOC help/cli/bd-dolt-help.txt; CODE src/lib/dolt-client.ts:1-120]

Legacy mail and reservations are user-profile files rather than Beads/Dolt state. Activity history is also global user-profile JSON. [CODE src/lib/agent-mail.ts:73-95; CODE src/lib/agent-reservations.ts:81-105; CODE src/lib/activity-persistence.ts:1-37]

The newer coordination path writes audit events through `bd audit record`, while projections read `.beads/interactions.jsonl`. The repository does not show the connector that guarantees those are the same durable stream. [CODE src/lib/coord-events.ts:32-72; CODE src/lib/coord-projections.ts:61-88]

The current daemon is not a separate host-resident process. `InProcessBbDaemon`, `EmbeddedDaemon`, the Pi adapter, workers, runtime events, and lifecycle state are held in process-level singletons/maps. [CODE src/lib/bb-daemon.ts:60-219; CODE src/lib/embedded-daemon.ts:27-156; CODE src/lib/worker-session-manager.ts:78-195]

On restart, Beads/Dolt and user-profile files should remain, but runtime lifecycle, worker maps, runtime events, and in-memory launch state are lost. The source does not show restoration of BeadBoard worker state after process restart. [CODE src/lib/embedded-daemon.ts:27-156; CODE src/lib/worker-session-manager.ts:1-67; CODE src/app/api/runtime/events/route.ts:1-16]

The accepted daemon ADR describes a future user-owned daemon to which a local or remote frontend attaches; the current implementation is embedded in the Next.js process instead. [DOC docs/adr/2026-03-05-bb-daemon-attachment-model.md:1-64; CODE src/lib/bb-daemon.ts:60-219]

The practical architecture is therefore primarily single-machine and single-Next-process. Multi-project support is local filesystem aggregation; multi-machine operation is documented as a target, not demonstrated by the current runtime. [DOC README.md:301-306; CODE src/lib/project-scope.ts:1-104]

## 4. Execution and orchestration model

### Work representation

The core work unit is a Beads issue with dependency edges, comments, labels, and optional agent assignment. Agent identity is represented as a Beads agent record, commonly mapped to an ID such as `bb-<agent-name>`. [DOC README.md:9-13; DOC skills/beadboard-driver/SKILL.md; CODE src/lib/agent/registry.ts:19-49]

The coordination layer adds structured messages, acknowledgements, reservations, heartbeat/liveness, and proposed append-only protocol events. [DOC docs/agent-session-flow.md; DOC docs/protocols/2026-02-28-bd-audit-coordination-schema.md:1-120]

### Agent attachment and spawning

The external workflow expects an agent to create/register an agent bead, claim a task with `--assignee`, send coordination messages, heartbeat, reserve scopes, run evidence-producing gates, and close the bead. [DOC skills/beadboard-driver/SKILL.md; DOC docs/agent-session-flow.md]

The embedded workflow creates Pi SDK sessions inside the Next.js process. The orchestrator receives custom tools for Beads, Dolt, mail, presence, deviation records, worker dispatch, templates, and task operations. [CODE src/lib/pi-daemon-adapter.ts:50-205]

Workers are Pi sessions with capability-based tool access. Coding, implementation, testing, refactoring, debugging, CI/CD, and deployment types receive full tools; other types are read-only. [CODE src/lib/worker-session-manager.ts:1-67,197-307]

There is no visible generic command-runner abstraction for invoking arbitrary Claude, Codex, or OpenCode CLIs. The runtime backend is hard-coded to Pi. [CODE src/lib/embedded-runtime.ts:3-28; CODE src/lib/pi-daemon-adapter.ts:28-47]

### Bead claiming and completion

The single-worker tool creates a bead when no bead ID is supplied and passes the ID into the worker prompt. The prompt instructs the worker to claim, update, block, and close the bead, but these are instructions rather than an enforced state machine. [CODE src/tui/tools/bb-spawn-worker.ts:21-44,101-127; CODE src/lib/worker-session-manager.ts:310-375]

Template team spawning passes task metadata but does not create or pass a bead ID for each member. This conflicts with the documented “bead-required” workflow. [DOC README.md:223-231; CODE src/tui/tools/bb-spawn-template.ts:89-141; CODE src/lib/worker-session-manager.ts:310-375]

Worker completion is based on Pi’s `agent_end` event and an assistant message, not on bead closure, test success, file verification, or review approval. [CODE src/lib/worker-session-manager.ts:377-414]

### Loops, retries, and review rounds

The visible implementation has fire-and-forget orchestrator prompting, asynchronous worker launch, polling-based `waitForWorker`, and result inspection. It does not show a durable scheduler, automatic retry policy, review-round loop, failure recovery loop, or evidence gate that blocks completion. [CODE src/lib/pi-daemon-adapter.ts:228-271; CODE src/lib/worker-session-manager.ts:416-505; CODE src/tui/tools/bb-worker-results.ts:14-114]

Templates provide role composition, not a full workflow engine. [DOC docs/plans/2026-03-05-embedded-pi-prd.md; CODE src/tui/tools/bb-spawn-template.ts:20-141]

### Human gates

The intended human role is to inspect the dashboard, assign or override work, comment, approve deviations, and respond to blocked agents. [DOC docs/protocols/2026-02-28-agent-first-ui-decisions.md:1-35; DOC docs/plans/2026-03-05-embedded-pi-prd.md]

The source exposes runtime and coordination endpoints but does not show a complete durable approval workflow around worker completion or deviations. [CODE src/app/api/runtime/*.ts; CODE src/lib/pi-daemon-adapter.ts:135-205]

## 5. Dependencies and operational cost

Required or strongly expected components:

- Node.js 18.18+ and npm 7+. [DOC README.md:18-47]
- The external `bd` CLI on `PATH`. [DOC README.md:86-117; DOC skills/beadboard-driver/SKILL.md]
- Dolt for the preferred database-backed path; without it, JSONL fallback is used. [DOC README.md:101-117; DOC .beads/config.yaml:1-6]
- Next.js, React, TypeScript, Chokidar, mysql2, React Flow/Dagre, Radix UI, Tailwind, and Pi SDK packages. [CODE package.json:21-70]
- Pi runtime dependencies. The bootstrap path can install Pi SDK/minimatch into a managed runtime directory, creating installation side effects. [CODE src/lib/bb-pi-bootstrap.ts:1-194]
- Optional provider authentication through Pi’s supported provider mechanisms. [CODE src/tui/bb-agent-tui.ts:243-351]

The configuration surface includes project scope, registry paths, Dolt metadata/ports, user-profile state, Pi runtime directories, model/provider settings, agent labels, reservations, templates, and environment variables such as `BB_AGENT`, `BD_ACTOR`, `BB_REPO`, and `PI_CODING_AGENT_DIR`. [DOC docs/adr/2026-03-03-global-installer-contract-and-manifest.md; CODE src/lib/agent-mail.ts:73-95; CODE src/lib/pi-runtime-detection.ts:1-103; CODE skills/beadboard-driver/scripts/bb-mail-shim.mjs:1-68]

The installer has a notable split: `bin/beadboard.js` routes commands to `src/cli`, while the generated `bb` shim invokes `tools/bb.ts`, an older agent-only CLI. [CODE bin/beadboard.js:1-18; CODE install/install.sh:51-69; CODE tools/bb.ts:111-130]

## 6. Docs-versus-reality gaps

1. The project advertises Activity and `/timeline`, but current navigation accepts only Social and Graph; Activity is implemented as a contextual right panel rather than a primary center view. [DOC README.md:121-126; CODE src/hooks/use-url-state.ts:1-57; CODE src/components/activity/contextual-right-panel.tsx:24-110]

2. The migration documents say legacy `bb` coordination is being removed in favor of `bd` audit/coord.v1, but session read/ack routes still use file-backed legacy mail, while conversation UI posts coord events. [DOC docs/protocols/2026-02-28-bb-deprecation-notes.md:1-24; CODE src/app/api/sessions/[beadId]/messages/[messageId]/read/route.ts:1-18; CODE src/components/sessions/conversation-drawer.tsx:172-196]

3. Coord events are written through `bd audit record`, while projections consume `.beads/interactions.jsonl`; the repository does not prove that the current `bd` version materializes the expected file. [CODE src/lib/coord-events.ts:32-72; CODE src/lib/coord-projections.ts:61-88]

4. The watcher does not explicitly watch `.beads/interactions.jsonl`, despite coord projections depending on it. [CODE src/lib/watcher.ts:113-146]

5. The documented liveness model says stale and evicted thresholds, but `deriveLiveness` returns `idle` at 60 minutes before checking the 30-minute evicted threshold. [DOC README.md:203-207; CODE src/lib/agent/registry.ts:379-394]

6. Reservations normalize scopes for conflict checks but release searches by the original scope string, leaving a likely normalized-path release defect. [CODE src/lib/agent-reservations.ts:323-477]

7. The documented bead-required worker workflow is not applied to template-spawned workers because template members receive no bead ID. [DOC docs/plans/2026-03-05-embedded-pi-roadmap.md:151-177; CODE src/tui/tools/bb-spawn-template.ts:89-141]

8. The accepted host-resident daemon architecture is not implemented; the current daemon is in-process and stateful only within the Next.js process. [DOC docs/adr/2026-03-05-bb-daemon-attachment-model.md:1-64; CODE src/lib/bb-daemon.ts:60-219]

9. The roadmap describes agent persistence, but the visible runtime uses in-memory maps; `src/lib/agent-persistence.ts` was not visibly wired into the runtime path. [DOC docs/plans/2026-03-05-embedded-pi-roadmap.md:35-80; CODE src/lib/worker-session-manager.ts:1-67; CODE src/lib/agent-persistence.ts]

10. The installer ADR describes global update/rollback behavior, while the CLI self-update implementation is a placeholder and the package is marked private. [DOC docs/adr/2026-03-03-runtime-manager-global-install.md:7-54; CODE src/cli/beadboard-cli.ts:418-425; CODE package.json:3]

11. `bb agent heartbeat` appears in protocol/runbook material, but the implemented CLI exposes `activity-lease` rather than a heartbeat command. [DOC docs/protocols/operative-protocol-v1.md; CODE src/cli/beadboard-cli.ts:52-280]

12. API documentation payloads appear older than current route implementations in several places, including activity, projects, and sessions response shapes. [DOC docs/api-reference.md:1-283; CODE src/app/api/activity/route.ts:1-40; CODE src/app/api/projects/route.ts; CODE src/app/api/sessions/route.ts:1-70]

13. Archetype/template reads accept a project root, but save functions use `process.cwd()`, and API routes do not consistently pass project scope. [CODE src/lib/server/beads-fs.ts:1-69,340-395; CODE src/app/api/swarm/archetypes/route.ts; CODE src/app/api/swarm/templates/route.ts]

14. Activity persistence captures the history snapshot before adding the new event, so the newest event can be absent from the persisted file until a later write. [CODE src/lib/realtime.ts:95-190]

## 7. Open questions

- Does the installed/current `bd` CLI convert `bd audit record` output into `.beads/interactions.jsonl`, or are the writer and projection paths currently disconnected? Read `docs/protocols/2026-02-28-bd-audit-coordination-schema.md`, `src/lib/coord-events.ts`, `src/lib/coord-projections.ts`, and the actual `bd audit` implementation/version.

- Which coordination path is authoritative today: legacy global mail, `bd` comments, or coord.v1 audit events? Read `src/lib/agent-mail.ts`, `src/lib/agent/messaging.ts`, all session message routes, and `docs/plans/2026-02-28-bd-only-coordination-migration-plan.md`.

- Is the global `bb` shim intentionally legacy, or should it expose the full current CLI? Read `install/install.sh`, `install/install.ps1`, `bin/beadboard.js`, `tools/bb.ts`, and the installer ADRs.

- Are Pi session files restored after a Next.js restart, or is runtime persistence only planned? Read Pi SDK session-manager behavior and compare it with `src/lib/embedded-daemon.ts` and `src/lib/worker-session-manager.ts`.

- What is the intended completion contract for workers: Pi response, bead closure, tests, reviewer approval, or an evidence artifact? Read `docs/plans/2026-03-05-embedded-pi-prd.md`, the roadmap’s Phase 3/4 sections, and `src/lib/worker-session-manager.ts`.

- Should every template member receive a Beads task, or are template members intentionally ephemeral? Read `docs/plans/2026-03-05-embedded-pi-prd.md`, `src/tui/tools/bb-spawn-template.ts`, and the template definitions under `.beads/templates`.

- Is Activity intended to remain ambient, or should it become a first-class view? Read `docs/plans/2026-02-28-ux-redesign-synthesis-prd.md`, `src/hooks/use-url-state.ts`, and `src/components/shared/unified-shell.tsx`.

- Is the package intended for public npm installation despite `private: true`? Read `package.json`, `docs/adr/2026-03-03-global-install-runtime-manager.md`, and release/CI configuration.

- Which provider/model combinations are supported in headless embedded mode versus only the interactive TUI? Read the Pi SDK configuration under the managed runtime and `src/lib/pi-daemon-adapter.ts` alongside `src/tui/bb-agent-tui.ts`.


