# Traycer — Luna high exploration

> Repository: https://github.com/traycerai/traycer · pinned commit `4eaefa779bd17959416053d196583a217ce0589a` · 2026-09-24. Method: GPT-6 Luna high, ONE static read-only pass; pass 2 skipped because the host is closed. Citations use pinned `traycer:path:line`. `[contract]` means protocol claim, `[impl]` observed client/docs code, and `[inferred]` a bounded conclusion. No live probe.

Question: can Traycer replace our foreman, inspector, and crew profiles as the control plane for keyed, headless, one-process-per-turn activations?

## T0 — Host boundary

- [impl] This open repository contains clients and a versioned client–host protocol. Releases, including the signed host binary, are built and signed in Traycer's internal repository; the agent-running host implementation is absent here. `traycer:docs/DEVELOPMENT.md:25` `traycer:docs/DEVELOPMENT.md:47`
- [impl] The repository describes its own code as MIT, but the host binary's license or separate terms are not stated in the searched README, contribution guide, and development guide. `traycer:README.md:97` `traycer:CONTRIBUTING.md:79` `traycer:docs/DEVELOPMENT.md:41`
- [impl] CLI host RPC requires stored Traycer credentials; absent credentials produce a sign-in error. The CLI's normal login uses a networked device authorization flow. A supplied or bundled host archive can avoid a registry download, but does not establish account-free operation. `traycer:clients/traycer-cli/src/internal/host-rpc.ts:52` `traycer:clients/traycer-cli/src/internal/host-rpc.ts:76` `traycer:clients/traycer-cli/src/auth/login-flow.ts:33` `traycer:clients/traycer-cli/src/installer/bundled-host.ts:6`

## Q1 — Launch

- [contract] The visible TUI path prepares command/argv, working directory, workspace folders, and harness session ID for an interactive vendor CLI in a PTY; GUI agents use SDK/JSON-RPC. Terminal harness IDs are Claude, Codex, and OpenCode; Cursor is GUI-only. `traycer:protocol/src/host/agent/shared.ts:20` `traycer:protocol/src/host/agent/shared.ts:362` `traycer:protocol/src/host/agent/tui/unary-schemas.ts:85`
- [impl] `traycer agent create` sends a host RPC with harness, model, effort, profile, and workspace choices; it mints a record, not the vendor process. Exact host argv/env construction and headless adapter execution are unknowable here. `traycer:clients/traycer-cli/src/commands/agent-create.ts:43` `traycer:clients/traycer-cli/src/commands/agent-create.ts:85`

## Q2 — Sessions

- [contract] Claude/OpenCode IDs are allocated at launch; Codex's app-server-backed ID arrives from `thread/started` and is back-filled. Stored TUI metadata includes session ID and computed launch args; later messages can resume a sleeping session. `traycer:protocol/src/host/agent/tui/unary-schemas.ts:72` `traycer:protocol/src/persistence/epic/tui-agents.ts:13` `traycer:protocol/src/host/agent/shared.ts:948`
- [inferred] Host restart and crash-recovery behavior cannot be verified without the host implementation; session metadata alone is not a per-turn recovery contract. `traycer:protocol/src/host/agent/shared.ts:955`

## Q3 — Observation

- [contract] TUI activity is a hook-driven start/stop level, also cleared by PTY exit. A Claude Stop hook sends a turn-ended broker signal; acceptance says the edge was recorded, not what the turn produced. `traycer:protocol/src/host/agent/tui/unary-schemas.ts:287` `traycer:protocol/src/host/agent/tui/unary-schemas.ts:308` `traycer:protocol/src/host/agent/tui/unary-schemas.ts:320`
- [contract] Inbox notices distinguish turn-ended, process exit, quiet, stop, error, and awaiting input. No common structured final-message/diff/exit-outcome result appears in these inspected **TUI** schemas. The separate GUI/SDK path records transcript turn events; the protocol also mentions headless A2A turns and a headless TUI Claude receiver. Those paths still depend on the closed host, and CLI access to it requires sign-in. `traycer:protocol/src/host/agent/inbox.ts:145` `traycer:protocol/src/host/agent/tui/unary-schemas.ts:287` `traycer:protocol/src/persistence/chat-transcript/row-projection.ts:123` `traycer:protocol/src/host/epic/unary-schemas.ts:2089` `traycer:protocol/src/host/agent/shared.ts:381` `traycer:clients/traycer-cli/src/internal/host-rpc.ts:76`

## Q4 — Steering

- [contract]/[impl] `agent.sendMessage` enqueues a prompt and returns immediately, optionally with a reply correlation ID; a reply is another message. The CLI calls that RPC. TUI stop sends SIGINT and keeps the PTY for later wake-up. `traycer:protocol/src/host/agent/shared.ts:1183` `traycer:clients/traycer-cli/src/commands/agent-send.ts:14` `traycer:protocol/src/host/agent/shared.ts:1260`
- [inferred] RPC acceptance does not prove that the vendor accepted a new turn or yielded a graded result. `traycer:protocol/src/host/agent/shared.ts:1183`

## Q5 — Inter-agent communication

- [contract] Agent IDs within an epic address brokered A2A messages, correlated replies, and inbox reads; cross-host receivers are rejected. Outbound tools support TUI Claude/Codex/OpenCode, but TUI inbound wake-up is Claude-only. `traycer:protocol/src/host/agent/shared.ts:372` `traycer:protocol/src/host/agent/shared.ts:400` `traycer:protocol/src/host/agent/shared.ts:420` `traycer:protocol/src/host/agent/shared.ts:1183`
- [contract] Inbox rows replay after restart/reconnect until acknowledged; older protocol versions receive compatibility acknowledgement. This is message durability, not turn idempotence. `traycer:protocol/src/host/agent/inbox.ts:288` `traycer:protocol/src/host/agent/inbox.ts:531`

## Q6 — Orchestration

- [contract] An epic holds shared tasks, artifacts, chat, and agents; child agents have parent IDs and can exchange messages. The inspected epic and agent contracts do not specify a deterministic graph-node dispatcher, activation ledger, gates, or retries. `traycer:protocol/src/host/epic/contracts.ts:1` `traycer:protocol/src/host/agent/shared.ts:589` `traycer:protocol/src/host/agent/shared.ts:1183`
- [inferred] Host-side orchestration and crash safety are unknowable from the open client/protocol source. Durable inbox replay cannot establish keyed activation recovery. `traycer:docs/DEVELOPMENT.md:25` `traycer:protocol/src/host/agent/inbox.ts:531`

## Q7 — Isolation

- [contract]/[impl] Creation accepts workspace paths and worktree bindings; CLI worktree commands exist. Per-agent model, effort, profile, and extra terminal arguments are represented. `traycer:clients/traycer-cli/src/commands/agent-create.ts:43` `traycer:protocol/src/persistence/epic/tui-agents.ts:55` `traycer:clients/traycer-cli/src/index.ts:53`
- [inferred] The inspected protocol does not establish a sandbox, per-agent home/config directory, or per-turn input/output git-tree pin; host enforcement is unknowable. `traycer:protocol/src/persistence/epic/tui-agents.ts:55`

## Q8 — External control surface

- [impl] An external process can use the CLI without the GUI; it calls a local `/rpc` WebSocket host service with stored sign-in credentials. The protocol negotiates per-method major/minor versions. The host is separately installed; Electron is not intrinsic to the CLI path. `traycer:clients/traycer-cli/src/internal/host-rpc.ts:52` `traycer:docs/DEVELOPMENT.md:33` `traycer:docs/DEVELOPMENT.md:41`
- [inferred] A public third-party SDK/stability guarantee, supported host OS matrix, host license, and fully offline runtime are unknowable from the inspected client/protocol paths. `traycer:docs/DEVELOPMENT.md:25` `traycer:docs/DEVELOPMENT.md:41`

## FIT vs our control plane

| Requirement | Fit | Evidence |
|---|---|---|
| Keyed graph-node activation and ledger | Missing in open contract; host unknowable | [inferred] Epic/agent records and durable inbox do not define a workflow ledger. `traycer:protocol/src/host/agent/inbox.ts:531` |
| Headless exact argv/model/effort, one process per turn | Partial; executor unknowable | [contract] Model/effort and prepared TUI argv exist; TUI is interactive PTY. `traycer:protocol/src/host/agent/shared.ts:20` `traycer:protocol/src/host/agent/tui/unary-schemas.ts:85` |
| Vendor session capture and later resume | Partial | [contract] IDs and sleeping-session resume are represented; host behavior is closed. `traycer:protocol/src/host/agent/tui/unary-schemas.ts:72` `traycer:protocol/src/host/agent/shared.ts:955` |
| Structured end-of-turn result and exit code | Missing in TUI contract; host unknowable | [contract] TUI hook/inbox notices lack that envelope; GUI transcript turn events exist, but host-side result delivery is closed. `traycer:protocol/src/host/agent/tui/unary-schemas.ts:287` `traycer:protocol/src/persistence/chat-transcript/row-projection.ts:123` |
| Per-turn git-tree pin | Missing in open contract; host unknowable | [inferred] Worktree binding is represented without turn-level object/ref proof. `traycer:protocol/src/persistence/epic/tui-agents.ts:55` |
| Idempotent activation and crash recovery | Unknowable | [inferred] Inbox replay/ack covers messages; host activation logic is absent. `traycer:protocol/src/host/agent/inbox.ts:531` |
| Agent messaging and delegation | Partial | [contract] A2A and child records exist, with asymmetric harness support and host locality. `traycer:protocol/src/host/agent/shared.ts:372` `traycer:protocol/src/host/agent/shared.ts:1201` |
| External headless control without GUI | Partial | [impl] CLI/RPC works outside GUI but requires sign-in and the separate closed host. `traycer:clients/traycer-cli/src/internal/host-rpc.ts:52` `traycer:docs/DEVELOPMENT.md:41` |

[inferred] **Verdict: REJECT as our control plane.** The agent-running host is closed and cannot be audited or patched here, CLI control requires sign-in, and the open protocol defines no keyed activation ledger or per-turn git-tree pin. The TUI contract lacks our result envelope, while GUI structured-turn events show that structured turns exist elsewhere in Traycer. A2A inbox replay/ack and the asymmetric capability matrix are reference material only. `traycer:docs/DEVELOPMENT.md:47` `traycer:clients/traycer-cli/src/internal/host-rpc.ts:76` `traycer:protocol/src/persistence/chat-transcript/row-projection.ts:123` `traycer:protocol/src/host/agent/inbox.ts:531`
