# Herdr — Luna high exploration

> Repository: https://github.com/herdrdev/herdr · pinned commit `9c96f7ddb3be2cc575a159d4d1f1d49fb10d7006` · 2026-09-24. Method: GPT-6 Luna high, static read-only, two passes; no live probes. Citations use pinned source lines. `[read]` denotes observed code or docs; `[inferred]` denotes a conclusion from them.

Question: can Herdr replace the workflow interpreter's inspector, crew profiles, and foreman dispatch while the rest stays unchanged? The test covers launch, sessions, observation, steering, inter-agent messaging, orchestration, isolation, and external control against our headless, keyed, per-turn CLI control plane. Raw two-pass reports are session-local and not committed.

## Q1 — Launch

- [read] `agent start` sends a constructed shell command to an existing shell pane and waits for agent detection; the registered agent set includes Claude and Codex. It does not select model or effort; callers supply arguments and inherited configuration. `herdr:src/app/agents.rs:145` `herdr:src/detect/mod.rs:71` `herdr:src/cli/spec.rs:403`
- [read] A separate `layout.apply` path accepts direct argv, cwd, and env, but still spawns a PTY and injects terminal/Herdr environment. This is more precise than saying every Herdr launch goes through a shell. `herdr:src/api/schema/panes.rs:202` `herdr:src/pane.rs:2271` `herdr:src/pane.rs:2537`

## Q2 — Sessions

- [read] Claude/Codex integrations capture native session references through hooks; pane snapshots retain them with launch metadata. Eligible restore creates a new shell PTY and sends a native resume command, with duplicate references suppressed. It does not preserve the old process. `herdr:src/integration/targets.rs:124` `herdr:src/persist/snapshot.rs:99` `herdr:src/persist/restore.rs:532`
- [read] Restore may wait for usable geometry/theme; a missing cwd or shell startup can produce `restore_error`. After sending a resume command, Herdr clears the plan without proving the agent accepted it. `herdr:src/app/agent_resume.rs:48` `herdr:src/app/agent_resume.rs:226`
- [inferred] This is native session relaunch, not durable recovery of one keyed workflow activation. `herdr:src/persist/restore.rs:797` `herdr:src/app/agent_resume.rs:226`

## Q3 — Observation

- [read] Foreground-process detection identifies the pane occupant; terminal buffer and OSC signals are evaluated against screen manifests. Claude/Codex hooks here provide identity, while lifecycle state chiefly comes from screens. `herdr:src/pane.rs:843` `herdr:src/pane.rs:2954` `herdr:src/detect/manifest.rs:431`
- [read] Unmatched known Claude screens can fall back to idle, while Codex can remain unknown. Transcript viewer rules can skip state updates. The published states do not include a distinct agent failure outcome. `herdr:src/detect/manifests/claude.toml:7` `herdr:src/detect/manifests/codex.toml:6` `herdr:src/detect/manifest.rs:543`
- [read] The child watcher sees process exit internally, but `pane.exited` exposes pane/workspace identifiers, not an exit code; pane reads return terminal text, not a structured turn result. `herdr:src/pane.rs:2540` `herdr:src/api/schema/events.rs:526` `herdr:src/api/schema/panes.rs:757`
- [inferred] A complete turn between observations can be missed, and screen idle is insufficient to grade an activation. `herdr:src/pane.rs:2954` `herdr:src/api/wait.rs:364`

## Q4 — Steering

- [read] `agent.prompt` validates the expected agent and sends text plus Enter through the PTY; key APIs can send interrupts. A successful call confirms input submission, not agent acceptance or task completion. `herdr:src/app/api/agents.rs:111` `herdr:src/app/api/panes.rs:1817`
- [read] `--wait` observes state, not a prompt-specific turn. An already working turn may satisfy it; failure to observe activity within the wait window can yield `agent_prompt_stalled` without proving the prompt was unsent. `herdr:src/api/wait.rs:211` `herdr:src/api/wait.rs:364` `herdr:docs/next/website/src/content/docs/agent-automation.mdx:72`

## Q5 — Inter-agent communication

- [read] No dedicated agent-addressed mailbox or handoff protocol appears in the searched socket API, agent schema, and wait paths. An external coordinator can prompt a named agent and wait on its observed state, but no inter-agent delivery receipt follows. `herdr:docs/next/website/src/content/docs/socket-api.mdx:93` `herdr:src/api/schema/agents.rs:166` `herdr:src/api/wait.rs:132`

## Q6 — Orchestration and durability

- [read] The exposed primitives cover panes, agents, prompts, waits, and worktrees; no task DAG, coordinator/worker task lifecycle, gate, or retry ledger is present in the searched control paths. Snapshots retain layout and native-session references. `herdr:src/app/agents.rs:145` `herdr:src/persist/snapshot.rs:343` `herdr:docs/next/website/src/content/docs/socket-api.mdx:93`
- [read] Events use a shared in-memory ring of 512. New subscriptions begin at the current sequence; lag causes `events_lost` and disconnect. Reconnecting and taking a snapshot recovers current state, not missing history. `herdr:src/api/event_hub.rs:1` `herdr:src/api/subscriptions.rs:282` `herdr:src/api/server.rs:849`
- [inferred] A timed-out prompt cannot be safely resent as a keyed activation, and the event sequence is not a durable caller checkpoint. `herdr:src/api/wait.rs:211` `herdr:src/api/event_hub.rs:1`

## Q7 — Isolation

- [read] Worktree APIs can create/open separate checkouts, but `agent start` does not allocate one. Processes inherit environment and installed integrations use existing provider configuration; no general per-agent home or sandbox provisioning was found in these launch paths. External sandbox wrappers are documented as a caller choice. `herdr:src/worktree.rs:239` `herdr:src/app/api/worktrees.rs:69` `herdr:src/pane.rs:166` `herdr:docs/next/website/src/content/docs/agents.mdx:53`

## Q8 — External control surface

- [read] A headless Herdr server accepts newline-delimited JSON over a local Unix socket or Windows named pipe; the CLI and bundled schema expose that surface. This checkout reports schema version 1 and protocol 22. Unix socket permissions are `0600`; no API-token check was found on the local path. `herdr:src/server/headless/bootstrap.rs:3` `herdr:src/api/server.rs:85` `herdr:docs/next/api/herdr-api.schema.json:1`
- [read] It is a Rust CLI/server with Linux, macOS, and Windows support under Apache-2.0; the server owns PTYs. `herdr:Cargo.toml:1` `herdr:Cargo.toml:54` `herdr:src/pane.rs:2537`

## FIT — our control plane

| Our requirement | Fit | Evidence |
|---|---|---|
| Foreman activation and SQLite ledger | Missing | [inferred] Pane/session snapshots do not model activations. `herdr:src/persist/snapshot.rs:99` |
| Headless CLI, one process per turn, exact model/effort and isolation | Partial | [read] Direct argv/cwd/env exists, but runs in a PTY and model/effort remain caller arguments. `herdr:src/pane.rs:2271` |
| Capture vendor session ID and resume | Partial | [read] Hooks persist native references; restore sends native resume in a new pane, without structured stream capture. `herdr:src/integration/targets.rs:124` `herdr:src/app/agent_resume.rs:226` |
| Pin input/output git trees per turn | Missing | [inferred] Worktree API has no per-turn ref/proof in the inspected path. `herdr:src/worktree.rs:239` |
| Structured exit result, final message, diff, and grading | Missing | [read] Terminal text and heuristic state; `pane.exited` has no exit code/result. `herdr:src/api/schema/events.rs:526` `herdr:src/api/schema/panes.rs:757` |
| Continuation turn without PTY typing | Missing | [read] `agent.prompt` uses PTY input and a state wait. `herdr:src/app/api/agents.rs:111` |
| Idempotent keys and crash recovery | Missing | [inferred] Snapshot restore and ephemeral event history cannot settle ambiguous prompt delivery. `herdr:src/api/event_hub.rs:1` `herdr:src/persist/restore.rs:797` |

[inferred] Native Herdr live-view/attach requires it to own the PTY process, changing our pipe-based launch and raw-stream/exit capture. A cheaper human-visibility experiment would let a Herdr pane tail our existing event log or transcript without owning the agent process; that would show logs rather than an attached agent terminal. Both options remain deferred. `herdr:src/pane.rs:2271` `herdr:src/api/schema/panes.rs:757`
