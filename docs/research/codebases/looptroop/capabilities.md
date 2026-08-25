> Produced by GPT-5.6-luna (xhigh), docs-first with code verification, 2026-08-24.
> Repo: reference_tools/looptroop @ 7b129216. Static read-only audit — nothing executed.
> Known corrections from the two-reviewer assessment are recorded in ../comparison-beadboard-aweb-looptroop.md (fact-conflict rulings).

# Identity

LoopTroop is a local GUI orchestrator for long-running AI software delivery. It turns a ticket into an interviewed plan, PRD, executable “beads,” isolated OpenCode coding sessions, verification, and a human-reviewed pull request. Its design goal is correctness and controlled context rather than fast single-agent edits. [DOC README.md:1-14,222-228; DOC package.json:2-4]

The repository is version 0.5.8, released 2026-08-23, with a current commit three commits beyond that tag. It describes itself as early-alpha software; `SECURITY.md` says it has not reached a stable release. [DOC package.json:2-4; DOC CHANGELOG.md:32-66; DOC CONTRIBUTING.md:5-11; DOC SECURITY.md:3-11; CODE git metadata]

There is a substantial visible Vitest suite and separate client/server test commands, but tests, builds, installs, the daemon, and OpenCode were not run for this read-only map. [DOC package.json:87-103; CODE tests/, server/**/__tests__/, src/**]

License: MIT. [DOC LICENSE:1-22; DOC package.json:28-29]

# Capability map

Reachability is based on visible implementation plus documentation, not live execution.

| Capability / surface | What it does | Evidence | Judgment |
|---|---|---|---|
| CLI daemon lifecycle | `open`, `start`, `stop`, `restart`, `status`, foreground mode, signed browser bootstrap links, daemon logs, readiness checks, stale-process protection. | [DOC README.md:64-76]; [CODE server/cli/cli.ts:8-179; server/cli/commands.ts:51-177,384-508] | WORKS-DOCUMENTED |
| CLI diagnostics and maintenance | `doctor`, `setup`, `clean`, JSON output, abandoned-worktree planning, optional destructive cleanup with `--apply`. | [CODE server/cli/cli.ts:8-179; server/cli/setupCommand.ts:58-97,163-276; server/cli/cleanCommand.ts:108-180] | WORKS-DOCUMENTED |
| Local HTTP control plane | Hono API for tickets, projects, beads, files, artifacts, logs, models, profiles, prompts, health, workflow actions, and shutdown. | [CODE server/app.ts:165-280; server/routes/tickets.ts:61-114; server/routes/projects.ts:203-437; server/routes/beads.ts:57-179; server/routes/files.ts:164-374] | WORKS-DOCUMENTED |
| Authentication and exposure controls | Single-use browser bootstrap nonce, session cookie or bearer token, loopback host guard, rate limits, optional token-protected remote binding. | [DOC SECURITY.md:28-60]; [CODE server/middleware/sessionAuth.ts:78-195; server/middleware/hostGuard.ts:119-206; server/middleware/rateLimit.ts:3-108; shared/appConfig.ts:39-69] | WORKS-DOCUMENTED |
| Project attachment | Validates a local Git repository, resolves its root, requires a GitHub origin, records attached projects, and exposes project/worktree management. | [DOC README.md:74-76]; [CODE server/routes/projects.ts:203-264,302-435] | WORKS-DOCUMENTED |
| Dashboard and ticket UI | Kanban board, ticket dashboard, project dialog, ticket creation, configuration, prompts editor, status/navigation views. | [DOC README.md:21-48]; [CODE src/App.tsx:214-270; src/components/kanban/KanbanBoard.tsx:134-452; src/components/ticket/TicketDashboard.tsx:182-609] | WORKS-DOCUMENTED |
| Live execution visibility | SSE status, progress, logs, artifacts, bead completion, questions, and error events; reconnects using persisted event IDs and invalidates stale client state after gaps. | [CODE server/routes/stream.ts:23-110; src/hooks/useSSE.ts:89-300] | WORKS-DOCUMENTED |
| Model/profile configuration | Selects a main implementer, council models, variants, effort settings, retry/timeouts, manual-QA behavior, and prompt overrides. | [DOC README.md:26-36,74-76]; [CODE server/routes/models.ts:29-46; server/routes/profiles.ts:76-168; src/components/config/ProfileSetup.tsx:63-291] | WORKS-DOCUMENTED |
| Relevant-file discovery | Scans the attached repository before planning and feeds relevant-file context into later phases. | [DOC README.md:232-248]; [CODE server/machines/ticketMachine.ts:157-190; server/workflow/runner.ts:93-120,304-315] | WORKS-DOCUMENTED |
| Interactive interview | Council-generated questions are presented in batches; answers, skips, edits, and approval are handled through API/UI routes. | [DOC README.md:273-279]; [CODE server/routes/tickets.ts:72-77,97; server/workflow/runner.ts:103-118,367-382] | WORKS-DOCUMENTED |
| LLM council planning | Runs independent drafts, quorum checks, anonymized voting, winner selection, and sequential refinement for interview, PRD, and bead planning. | [DOC README.md:262-270]; [CODE server/council/pipeline.ts:33-131; server/council/drafter.ts:80-103; server/workflow/runner.ts:316-493] | WORKS-DOCUMENTED |
| PRD/specification and coverage | Produces durable PRD artifacts, verifies coverage, allows bounded follow-up passes, and gates approval before bead generation. | [DOC README.md:281-285,232-248]; [CODE server/machines/ticketMachine.ts:260-321; server/workflow/runner.ts:395-451] | WORKS-DOCUMENTED |
| Bead blueprint generation | Generates lightweight Beads-methodology records containing objectives, acceptance criteria, tests, target files, dependencies, labels, and execution metadata. It is not the external Beads project. | [DOC README.md:287-300]; [CODE server/phases/beads/types.ts:3-84; server/phases/beads/expand.ts:195-282] | WORKS-DOCUMENTED |
| Bead editing and approval | Exposes bead JSONL, validates schema and duplicate IDs, supports structured/raw UI editing, approval snapshots, and approval receipts. | [CODE server/routes/beads.ts:57-179; server/phases/beads/document.ts:19-121; src/components/workspace/ApprovalView.tsx:57-153,757-823] | WORKS-DOCUMENTED |
| Execution setup planning | Generates and approves a setup plan containing environment facts, commands, permissions, and setup artifacts before coding. | [CODE server/machines/ticketMachine.ts:390-446; server/routes/tickets.ts:78-85; server/workflow/phases/executionSetupPlan/generator.ts] | WORKS-DOCUMENTED |
| Isolated worktree execution | Creates ticket worktrees under `.looptroop/worktrees/<externalId>`, keeps the active checkout separate, and preserves `.ticket` metadata during resets. | [DOC README.md:314-318]; [CODE server/storage/paths.ts:69-115; server/phases/execution/gitOps.ts:38-49,273-287] | WORKS-DOCUMENTED |
| OpenCode bead coding | Runs one selected implementer model against one runnable bead, records a start commit, streams events, validates completion, commits scoped files, and records a bead diff. | [DOC README.md:302-316]; [CODE server/workflow/phases/executionPhase.ts:318-480,632-765; server/phases/execution/executor.ts:302-582] | WORKS-DOCUMENTED |
| Completion gates | Requires a `<BEAD_STATUS>` result with `status: done` and passing `tests`, `lint`, `typecheck`, and `qualitative` checks before accepting a bead. | [CODE server/phases/execution/completionChecker.ts:17-67; server/phases/execution/executor.ts:40-55,567-582] | WORKS-DOCUMENTED |
| Ralph-style recovery | On failure or timeout, records compact failure notes, abandons the failed session, resets the worktree to the bead-start commit, and retries with fresh context. | [DOC README.md:302-312]; [CODE server/phases/execution/executor.ts:760-881; server/workflow/phases/executionPhase.ts:576-628] | WORKS-DOCUMENTED |
| Same-session continuation | Some OpenCode/provider retry and timeout cases preserve the active session for an explicit `continue` action instead of immediately wiping it. | [CODE server/phases/execution/executor.ts:404-445,704-755; server/opencode/sessionContinuation.ts; server/routes/tickets.ts:87-95] | PARTIAL |
| Final tests and Manual QA | Runs final verification, optionally generates a Manual QA checklist, accepts evidence, supports skip, drift resolution, fix beads, and improvement tickets. Manual QA is enabled by default for new configurations. | [DOC README.md:240-248,320-326; DOC CHANGELOG.md:40,66; CODE server/machines/ticketMachine.ts:465-500; server/routes/tickets.ts:106-114; src/components/workspace/ManualQAView.tsx:170-220,625-700] | WORKS-DOCUMENTED |
| Integration and candidate diff | Audits candidate files, creates a squash/integration checkpoint, records reports, and keeps `.ticket` metadata out of code diffs. | [CODE server/workflow/phases/integrationPhase.ts:108-247; server/phases/execution/gitOps.ts:261-270] | WORKS-DOCUMENTED |
| GitHub pull requests | Pushes the candidate branch, creates/updates a draft PR, waits for review, supports ready/merge/close-unmerged, verifies remote merge, and records reports. | [DOC README.md:232-248,320-326]; [CODE server/workflow/phases/pullRequestPhase.ts:1006-1027,1159-1269; server/git/github.ts:502-587] | WORKS-DOCUMENTED |
| OpenCode questions and permission interaction | Provides routes for listing, answering, or rejecting OpenCode question requests and handles permission/tool events in the adapter. | [CODE server/routes/tickets.ts:92-95; server/opencode/adapter.ts:200-369,467-562] | PARTIAL |
| Durable ticket state | Persists ticket status, XState snapshots, locked model choices, phase attempts, artifacts, errors, status history, OpenCode sessions, and execution metrics in SQLite. | [DOC README.md:248,348-360]; [CODE server/db/schema.ts:70-115,138-187,189-234; server/machines/persistence.ts:133-202,319-340] | WORKS-DOCUMENTED |
| Filesystem artifacts and logs | Stores ticket metadata, beads JSONL, setup profiles, execution logs, debug logs, AI logs, and phase-related files in the ticket worktree. | [DOC SECURITY.md:81-91]; [CODE server/ticket/metadata.ts:48-143; server/storage/paths.ts:69-115; server/log/executionLog.ts:124-202] | WORKS-DOCUMENTED |
| Crash recovery and startup reconciliation | Repairs orphan temporary files and trailing JSONL corruption, rebuilds projections, hydrates ticket actors, and reconnects or abandons persisted OpenCode sessions. | [CODE server/startup.ts:20-100,103-167; server/io/recovery.ts:23-88] | WORKS-DOCUMENTED |
| Mock mode | Supplies a mock OpenCode adapter for planning/development, but explicitly does not implement real coding, final testing, integration, PR, or cleanup execution. | [DOC .env.example]; [CODE server/opencode/factory.ts:1-19; server/workflow/runner.ts:93-150,234-300; server/workflow/phases/executionPhase.ts:341-343] | PARTIAL |
| Distribution and packaging | Provides npm, curl/PowerShell installers, Homebrew, Scoop, Bun, pnpm, Yarn, Docker, and standalone-binary release paths, with package/build/smoke scripts. | [DOC README.md:78-220]; [DOC CHANGELOG.md:46-66]; [DOC package.json:55-103] | WORKS-DOCUMENTED |

# Architecture sketch

The system is a local daemon plus browser UI. The CLI starts or controls a Node process; the daemon exposes a Hono HTTP API and serves the React application; the browser uses REST-style API calls plus ticket-scoped SSE. [DOC README.md:64-76; CODE server/createRuntime.ts:54-145; server/app.ts:165-360; server/routes/stream.ts:23-110]

The main components are:

1. A CLI and daemon supervisor. The CLI owns daemon state, logs, start/stop identity checks, signed browser bootstrap links, and cleanup. [CODE server/cli/commands.ts:45-177,384-508]

2. A Hono control plane. Routes mutate tickets and projects, approve planning artifacts, answer interview/OpenCode questions, control retry/continue/merge actions, and expose logs/artifacts. [CODE server/app.ts:214-280; server/routes/tickets.ts:61-114]

3. A React frontend. `App.tsx` switches between Kanban and ticket dashboard views and opens configuration, prompt, project, and ticket dialogs. [CODE src/App.tsx:214-270]

4. An XState ticket actor and workflow runner. The actor is the durable state machine; the runner dispatches phase handlers when states are entered. [CODE server/machines/ticketMachine.ts:51-56,157-570; server/workflow/runner.ts:304-627]

5. Phase modules. Planning, interview, PRD, beads, execution setup, coding, final testing, Manual QA, integration, pull request, and cleanup are implemented as separate phase handlers. [CODE server/workflow/runner.ts:31-82]

6. An OpenCode integration layer. LoopTroop talks to an OpenCode HTTP service through `@opencode-ai/sdk`; it can adopt an already-running server or spawn `opencode serve`. [CODE server/opencode/factory.ts:1-19; server/opencode/adapter.ts:151-197; server/opencode/supervisor.ts:117-263]

7. Git and GitHub subprocess integration. Git worktree, branch, commit, push, diff, and hook operations are performed locally; GitHub operations use `gh`/GitHub API helpers. [DOC SECURITY.md:33-40; CODE server/phases/execution/gitOps.ts:55-75,194-258; server/git/github.ts:502-587]

8. SQLite plus filesystem storage. The app registry and user settings are separate from per-project databases and per-ticket worktree artifacts. [CODE server/db/schema.ts:4-115; server/db/appDbPath.ts:4-18; server/storage/paths.ts:69-115]

Durable locations are:

- User configuration: `config.json` and `app.sqlite` under the platform-specific LoopTroop config directory. [DOC .env.example; CODE server/lib/appSettings.ts:7-14,62-123; server/db/appDbPath.ts:4-18]
- Project state: `<repo>/.looptroop/db.sqlite`. [CODE server/storage/paths.ts:69-79; server/db/project.ts:45-252]
- Ticket worktree: `<repo>/.looptroop/worktrees/<externalId>`. [CODE server/storage/paths.ts:77-87]
- Ticket metadata and runtime: `.ticket/meta/ticket.meta.json`, `.ticket/beads/<baseBranch>/.beads/issues.jsonl`, `.ticket/runtime/execution-log*.jsonl`, and setup-profile files. [CODE server/ticket/metadata.ts:48-143; server/storage/ticketQueries.ts:1252-1278; server/storage/paths.ts:85-110]
- Workflow state and artifacts: project SQLite tables including `tickets`, `phase_artifacts`, `ticket_phase_attempts`, `opencode_sessions`, status history, error occurrences, and metrics. [CODE server/db/schema.ts:70-234]

SQLite uses WAL mode, normal synchronous durability, busy timeouts, and periodic checkpointing. Filesystem writes use temporary files, fsync, rename, and parent-directory synchronization where appropriate. [CODE server/db/index.ts:19-69,110-136; server/io/atomicWrite.ts:17-62; server/io/atomicAppend.ts:9-31]

On restart, the daemon initializes databases, repairs orphan temporary files and malformed trailing JSONL, rebuilds runtime projections, loads prompt templates, checks OpenCode health, hydrates XState actors, and reconciles active OpenCode sessions. [CODE server/startup.ts:20-167]

Recovery is not uniform across all phases. Coding has an execution checkpoint artifact and can resume finalization without re-running a successful interrupted bead; otherwise an in-progress bead is reset to its recorded start commit. OpenCode sessions can be reconnected, preserved as unverified, or marked abandoned. [CODE server/workflow/phases/executionPhase.ts:357-443,632-641; server/startup.ts:44-100]

Council draft/vote/refine intermediates are process-local. After a restart, the runner explicitly emits “Council data lost after restart” and transitions the ticket to an error requiring retry. Thus the workflow snapshot and completed artifacts are durable, but all in-flight planning state is not. [CODE server/workflow/runner.ts:13-15,336-365,408-437,464-493; server/workflow/phases/state.ts:5-34]

OpenCode itself is supervised independently. An already-running service is adopted and not stopped; a LoopTroop-spawned service is restarted up to three times with backoff, then becomes degraded. [CODE server/opencode/supervisor.ts:5-35,117-184,265-327]

The architecture is fundamentally single-machine and local-first. The API defaults to loopback and remote binding requires explicit environment opt-in plus a token; the security policy calls remote control-plane exposure unsupported. There is no visible distributed queue, worker registry, or multi-machine scheduler. [DOC SECURITY.md:28-60; CODE shared/appConfig.ts:39-69; CODE server/workflow/runner.ts:17-30]

# Execution and orchestration model

## Work representation

The durable unit is a LoopTroop ticket, stored in a project database with an XState snapshot, status, current bead, model locks, error state, and phase metadata. [CODE server/db/schema.ts:70-104; server/machines/persistence.ts:133-202]

The executable work units are beads stored as branch-scoped JSONL, not records in the external `bd`/Beads system. A bead contains narrative requirements plus dependency fields, target files, validation commands, iteration number, start commit, completion state, and retry notes. [DOC README.md:287-300; CODE server/ticket/metadata.ts:128-143; server/phases/beads/types.ts:3-84]

The scheduler selects a runnable pending bead whose `blocked_by` dependencies are complete. Execution is sequential within a ticket. [CODE server/phases/execution/scheduler.ts:1-180; server/workflow/phases/executionPhase.ts:444-480]

The project execution band is deliberately limited to one active ticket per project. This is an explicit alpha limitation enforced during start, approval, retry, and continue operations. [DOC CHANGELOG.md:78; CODE server/storage/ticketQueries.ts:1122-1153; server/routes/ticketHandlers/lifecycleHandlers.ts:514-661]

## Planning sequence

The workflow is:

`ticket → relevant-file scan → interview council → interactive answers → interview coverage → PRD council → PRD coverage → beads council → beads coverage → bead expansion → human approvals → preflight → execution setup approval → coding`. [DOC README.md:232-248; CODE server/machines/ticketMachine.ts:157-446]

The council pipeline uses multiple model sessions rather than one persistent conversation:

1. Drafts are generated in parallel.
2. A quorum is required.
3. Draft context is rebuilt.
4. Models vote, with votes anonymized from the draft authors.
5. A winner is selected.
6. The winner is refined using useful information from losing drafts.

This pipeline is reused for interview, PRD, and bead planning. [DOC README.md:262-270; CODE server/council/pipeline.ts:33-131]

Human approval occurs at interview, PRD, bead, and execution-setup boundaries. Approval snapshots and hashes are recorded so later edits can be detected. [CODE server/machines/ticketMachine.ts:190-446; server/routes/tickets.ts:78-85; server/phases/beads/document.ts:19-121]

## Agent spawning and attachment

LoopTroop does not visibly spawn one local agent process per bead. It attaches to an OpenCode server through the SDK and creates sessions for phases, council members, beads, iterations, and sub-steps. Session ownership is persisted in `opencode_sessions`. [CODE server/opencode/factory.ts:1-19; server/opencode/adapter.ts:151-197; server/opencode/sessionManager.ts:72-112; server/db/schema.ts:149-164]

If the configured OpenCode endpoint is unavailable, the supervisor attempts to run:

```text
opencode serve --hostname <host> --port <port>
```

It can also adopt an externally started OpenCode server. [CODE server/opencode/supervisor.ts:168-263]

Council members and the main implementer are selected from models exposed by OpenCode’s provider catalog. The selection is validated against connected provider models, requires at least two distinct council members including the implementer, and permits at most ten. [DOC README.md:391-398; CODE server/opencode/providerCatalog.ts:80-149; server/opencode/modelValidation.ts:18-64]

There are no visible direct adapters that launch `claude`, `codex`, or an interactive `opencode` coding CLI per task. OpenCode is the agent runtime and is driven over its SDK; the `opencode` executable is used to start its server. [CODE server/opencode/factory.ts:1-19; server/opencode/adapter.ts:151-197; server/opencode/supervisor.ts:186-215]

## Coding and completion

For each bead, LoopTroop:

1. Reads the bead JSONL.
2. Finds the next runnable bead.
3. Marks it `in_progress`.
4. Records the current worktree commit as `beadStartCommit`.
5. Assembles bead-specific context.
6. Creates an OpenCode coding session.
7. Streams events and records session/AI logs.
8. Parses the completion marker.
9. Commits only allowed code paths, excluding `.ticket`.
10. Records the bead as complete and stores a code-only diff artifact.
11. Advances to the next bead or final testing.

[CODE server/workflow/phases/executionPhase.ts:444-480,497-576,632-765; server/phases/execution/gitOps.ts:44-75,194-258]

Completion is not inferred from an assistant’s prose. The response must contain a structured marker with `status: done` and all four required gates passing: tests, lint, typecheck, and qualitative. [CODE server/phases/execution/completionChecker.ts:17-67]

## Context policy

Context is phase-specific and deliberately allowlisted. Planning phases receive planning artifacts; coding receives bead data and notes; failed iterations receive compact error context and recent failure excerpts. The context builder trims lower-priority content first under a token budget. [DOC README.md:250-260; CODE server/opencode/contextBuilder.ts:6-53,163-348]

This is a context-reset design rather than a single growing conversation. The code can reuse a session for structured-output correction or an explicitly continuable provider timeout, but normal failed iterations are abandoned and restarted. [CODE server/phases/execution/executor.ts:600-755,789-849]

## Loops and retries

A failed bead iteration produces a durable failure note, attempts a context-wipe note in the same session, falls back to a deterministic note if that fails, resets the worktree to the bead-start commit, marks the bead pending for the next iteration, and abandons the failed session. [DOC README.md:302-312; CODE server/workflow/phases/executionPhase.ts:576-628; server/phases/execution/executor.ts:760-881]

The visible default profile permits five bead iterations, one structured-output retry, ten OpenCode/provider retries, and bounded timeouts. Coverage loops have separate budgets. [CODE server/db/defaults.ts:3-24]

When the retry budget is exhausted, the bead becomes an error and the ticket enters `BLOCKED_ERROR`. A human can retry or continue through explicit API actions. [CODE server/workflow/phases/executionPhase.ts:654-678; server/machines/ticketMachine.ts:548-556; server/routes/tickets.ts:87-91]

## Final delivery and human gates

After all beads complete, the workflow runs final tests. Manual QA is enabled or disabled according to the locked ticket configuration; when enabled, a user can submit evidence, skip the round, resolve workspace drift, or create fix beads/improvement tickets. [CODE server/machines/ticketMachine.ts:465-500; server/routes/tickets.ts:106-114]

Integration produces a candidate checkpoint and report. Pull-request creation pushes the branch and creates or updates a draft PR. The state then waits in `WAITING_PR_REVIEW`; merge or close-unmerged actions are separate human-triggered transitions. [CODE server/machines/ticketMachine.ts:501-546; server/workflow/phases/pullRequestPhase.ts:1006-1027,1159-1269]

# Dependencies and operational cost

Runtime requirements:

- Node.js `>=24.15.0`.
- npm `>=11.12.1`.
- Git.
- GitHub CLI (`gh`) and authenticated GitHub access for the documented PR workflow.
- OpenCode installed/configured or an OpenCode server reachable at the configured URL.
- A configured model provider inside OpenCode. [DOC README.md:107-113,212-220; DOC package.json:38-40; DOC SECURITY.md:33-40; CODE server/opencode/supervisor.ts:31-39]

Core runtime dependencies are Hono, the Hono Node server, the OpenCode SDK, Drizzle ORM, SQLite support, XState, Zod, YAML parsing, and tokenization. The frontend uses React, Vite, TanStack Query, Tailwind, CodeMirror, Radix UI, and Vitest-related tooling. [DOC package.json:105-163]

There is no visible PostgreSQL, Redis, message broker, cloud control plane, or separate worker service. SQLite and filesystem artifacts are the persistence layer; OpenCode and GitHub/model providers are the external services. [CODE package.json:105-113; server/db/schema.ts:70-234; server/opencode/adapter.ts:151-197]

Configuration is spread across:

- Environment variables for ports, config directory, database paths, remote API, OpenCode URL/mode, auth, logging, LAN behavior, and development flags. [DOC .env.example]
- User-level `config.json`, resolved with precedence `flag > environment > file > default`. [CODE server/lib/appSettings.ts:7-14,88-190]
- Profile/project/ticket settings for council members, implementer, timeouts, retry budgets, manual QA, Git hooks, and coverage limits. [CODE server/db/defaults.ts:3-24; server/db/schema.ts:47-104]
- Prompt templates and overrides. [CODE server/startup.ts:120-132; server/routes/prompts.ts:46-168]

Installation channels include npm, curl/PowerShell wrappers, Homebrew, Scoop, Bun, pnpm, Yarn Classic, Docker, and standalone binaries. The package has build, bundle, installer, published-install, container, channel, license, and read-only-install verification scripts. [DOC README.md:78-220; DOC package.json:55-103]

Operational cost is intentionally high: council planning makes multiple model calls per planning phase, bead execution can use several iterations and structured retries, and the README explicitly expects multi-hour or overnight runs. API-token usage can be substantial. [DOC README.md:302-312,363-369; CODE server/council/pipeline.ts:33-131; server/db/defaults.ts:8-19]

Disk cost also grows through per-ticket worktrees, SQLite databases, historical phase artifacts, and three JSONL log channels. Execution logs are not automatically truncated by the log writer. [CODE server/storage/paths.ts:69-115; server/log/executionLog.ts:159-202]

Security cost is significant: OpenCode is intentionally run with broad permissions, and Git worktrees isolate repository state but do not sandbox arbitrary host commands. The project recommends a disposable VM or sandbox. [DOC README.md:329-345; DOC SECURITY.md:33-60]

# Docs-vs-reality gaps

1. Detailed product documentation is outside this repository. The README and contributing guide point to the separate `LoopTroop-Website` repository for CLI, configuration, lifecycle, architecture, and installation documentation. Those pages were not treated as verified evidence here. [DOC README.md:372-389; DOC CONTRIBUTING.md:53-59]

2. “Durable workflow state” is only partially true. Ticket snapshots, approved artifacts, beads, logs, and execution checkpoints are durable, but council draft/vote/refinement intermediates live in process memory. Restarting during those phases intentionally produces `INTERMEDIATE_DATA_LOST` and requires a retry. [DOC README.md:248,348-360; CODE server/workflow/runner.ts:13-15,336-493]

3. The README’s `.ticket/** YAML artifacts` description is broader than the implementation’s concrete formats. Beads are branch-scoped `issues.jsonl`; runtime logs are JSONL; many phase artifacts are JSON strings in SQLite. [DOC README.md:348-360; CODE server/ticket/metadata.ts:128-143; server/log/executionLog.ts:159-202; server/db/schema.ts:106-115]

4. “Cross-model” does not mean direct Claude/Codex/OpenAI CLI adapters. The implementation delegates all model access to OpenCode’s provider catalog and SDK. The documentation’s provider examples therefore depend on what the connected OpenCode installation exposes; there is no visible LoopTroop-specific NVIDIA, Claude, or Codex runner. [DOC README.md:348-360; CODE server/opencode/factory.ts:1-19; server/opencode/modelValidation.ts:18-64]

5. Manual QA is documented as optional, but the current default is enabled for new profiles, projects, and tickets. Existing locked tickets preserve their previous setting. [DOC README.md:240-248,320-326; DOC CHANGELOG.md:40,66; CODE server/db/defaults.ts:3-7]

6. Mock mode is exposed in the configuration sample but is not a full execution backend. It supports planning-oriented mock transitions and explicitly rejects real coding/final-test/integration/PR execution. [DOC .env.example; CODE server/workflow/runner.ts:93-150,234-300; server/workflow/phases/executionPhase.ts:341-343]

7. The release notes report extensive published-channel smoke coverage, but those claims are repository documentation rather than a verification performed during this mapping. [DOC CHANGELOG.md:46-66; DOC .github/releases/0.5.8.md:15-27]

# Open questions

- What do the published CLI, configuration, and architecture documents add beyond the README? Read the external `LoopTroop-Website` pages named in `README.md:372-389`, especially CLI, configuration, ticket flow, system architecture, and beads.
- What exact prompt text and system rules are sent to council members, interview agents, implementers, and retry sessions? Read `server/prompts/index.ts`, `server/prompts/globalRules.ts`, and `server/prompts/templateStore.ts`.
- What are the exact PRD, interview, final-test, and Manual QA artifact schemas and file/DB ownership rules? Read `server/phases/prd/`, `server/phases/interview/`, `server/phases/finalTest/`, and `server/phases/manualQa/`.
- How exactly does the scheduler order independent beads and handle dependency cycles? Read `server/phases/execution/scheduler.ts` and the remaining execution tests.
- What commands and host facts are placed into the approved execution setup, and what shell wrappers are generated? Read `server/phases/executionSetup/` and `server/phases/executionSetupPlan/`.
- How are Git hooks, generated files, force-with-lease pushes, branch naming, and merge verification handled in all failure cases? Read `server/git/repository.ts`, `server/git/push.ts`, `server/git/github.ts`, and `server/workflow/phases/pullRequestPhase.ts`.
- Which provider capabilities, image inputs, variants, and OpenCode version ranges are actually supported? Read `server/opencode/providerCatalog.ts`, `server/opencode/types.ts`, `server/opencode/adapter.ts`, and the OpenCode SDK version in `package.json`.
- Does the production package always serve the bundled frontend correctly, and what does the standalone executable include? Read `scripts/build-server.mjs`, `scripts/build-bundle.mjs`, `server/lib/seaAssets.ts`, `Dockerfile`, and the packaging smoke scripts.
- What is the intended recovery behavior when the daemon dies during integration, PR creation, or remote merge? Read `server/startup.ts`, `server/workflow/phases/integrationPhase.ts`, `server/workflow/phases/pullRequestPhase.ts`, and the corresponding integration/retry tests.
- No live runtime behavior was verified because the requested scope prohibited installs, builds, tests, and running the tool; a deeper evaluation should execute the existing published and integration smoke paths in a disposable environment.


