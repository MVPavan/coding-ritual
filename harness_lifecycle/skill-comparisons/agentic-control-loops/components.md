# Agentic Control Loops — Level 3 Components

Column keys used in the matrix:

| Key | Surface |
|---|---|
| `DCL` | humanlayer — `plugins/design-control-loop/skills/design-control-loop/` (SKILL.md + 10 references) |
| `BIAL` | humanlayer — `plugins/build-iterated-agentic-loop/skills/build-iterated-agentic-loop/` (SKILL.md + 8 references) |
| `EXE` | ours — `.claude/skills/execution/` (SKILL.md, `references/task-engine.md`, `references/workstream-mode.md`, 2 scripts) |
| `WG` | ours — `docs/ideas/workflow-graphs.md` (draft; cited as `WG:line`) |

Paths under `DCL`/`BIAL` are relative to the skill directory; `SKILL.md` alone
means that skill's own SKILL.md.

## Component inventory

### `DCL` — design-control-loop (humanlayer)

| Component | Citation |
|---|---|
| Control-theory vocabulary: set point / sensor / controller / actuator / disturbance, taught before design | `SKILL.md:12-22`; `references/control-loop-taxonomy.md:7-19` |
| Full-loop diagram incl. measured error and controller output | `references/control-loop-taxonomy.md:30-51` |
| "Components can blur" — fused sensor+controller / controller+actuator is legitimate; do not invent separation | `references/control-loop-taxonomy.md:21-28`; `SKILL.md:115`; `references/workflow-template.yml:169-171` |
| Anti-template stance: "no fixed toolset and no template to reproduce", example is "illustration, not a blueprint" | `SKILL.md:10, 22`; `references/example-control-loop.md:78` |
| Phase A repo reconnaissance with completion criterion (package manager, install, validation, CI, existing loops) | `SKILL.md:43-56` |
| Phase B interview: set point → sensor → controller → actuator → disturbances, proposals grounded in Phase A | `SKILL.md:58-77`; design questions `references/control-loop-taxonomy.md:65-75` |
| Scope gate — directories the loop may change vs only read | `SKILL.md:64`; `references/control-loop-taxonomy.md:61` |
| Sensor trade-off checklist (stability, cost, repeatability, silent-disable risk) | `SKILL.md:66`; `references/control-loop-taxonomy.md:13` |
| Controller as the tunable part — deterministic ↔ agentic spectrum, "start simple and expect to revise" | `SKILL.md:68`; `references/control-loop-taxonomy.md:15` |
| Golden patterns established before automating, encoded into the actuator skill | `SKILL.md:72, 86` |
| Dampener (regression gate vs baseline, advisory → blocking graduation) offered, optional | `SKILL.md:75`; `references/control-loop-taxonomy.md:60`; `references/example-control-loop.md:110-114` |
| Written design captured before building | `SKILL.md:29, 77` |
| Phase C actuator-skill authoring rules (steps with completion criteria, references sibling, one source of truth, response template, name = slug) | `SKILL.md:79-93`; skeleton `references/skill-template.md:1-57`; example `references/example-skill.md` |
| Response template that becomes the PR body (fix/migration, generation, refactor variants) | `references/response-template.md:9-86`; guidelines `:97-103` |
| Phase D local-first: run sensor, controller, actuator by hand before any CI; completion criterion | `SKILL.md:95-107`; `references/control-loop-taxonomy.md:53-55`; `references/agent-runner-templates.md:7-13` |
| Phase E CI wiring as discrete sensor → controller → actuator steps, cadence choice | `SKILL.md:109-121`; `references/workflow-template.yml:173-221` |
| Memory file loaded after the controller on every run; good/bad entry rules | `SKILL.md:129`; `references/memory-template.md:1-7`; `references/workflow-template.yml:200-213` |
| `/iterate` PR-comment steering: label + hidden marker routes to owning workflow; prompt built from PR body/comments/memory; agent distils durable feedback into memory | `SKILL.md:130`; `references/agent-iteration.ts:41-55, 60-125`; `references/workflow-template.yml:31-42, 71-84, 137-167` |
| Iterate authorisation — only OWNER/MEMBER/COLLABORATOR comments starting `/iterate` | `references/workflow-template.yml:34-42` |
| Flow control — default one open PR per loop; scheduled no-op, manual bypass | `SKILL.md:136-145`; `references/workflow-template.yml:55-69` |
| Concurrency group per loop, cancel-in-progress | `references/workflow-template.yml:26-28` |
| Agent-agnostic actuator: Claude Code / Codex / OpenCode / CodeLayer run + extraction recipes; spend guards (`--max-turns`, `--max-budget-usd`) | `references/agent-runner-templates.md:17-152`, `:37` |
| PR skipped when the agent made no commits | `references/workflow-template.yml:237-240` |
| YAML validation + referenced-paths check | `SKILL.md:151` |
| Dry-run bootstrap via temporary `push` trigger | `SKILL.md:153` |
| "Iterate faster" ladder (frequency, batch, N cycles per run, parallel runs) | `SKILL.md:155` |
| Per-phase "read these references" pointers (progressive disclosure) | `SKILL.md:45, 60, 81, 97, 111, 125, 138, 149` |
| Sandbox-mode prompt rule: "do not stop and ask for feedback" | `references/prompt-template.md:32` |
| Artifact upload of agent output | `references/workflow-template.yml:268-273` |

### `BIAL` — build-iterated-agentic-loop (humanlayer)

| Component | Citation |
|---|---|
| Repo reconnaissance before questions, completion criterion | `SKILL.md:23-32` |
| Nine setup questions with repo-evidence defaults (agent, cadence, task, scope, validation, PR bound, PR metadata, response format, iteration) | `SKILL.md:34-60` |
| PR-bound rationale ("5+ unreviewed PRs in a week") and mechanism (`gh pr list --label`) | `SKILL.md:45-48` |
| Job definition triad: what are we finding / changing / how do we validate | `SKILL.md:62-85` |
| Skill-writing rules (same as DCL Phase C) | `SKILL.md:87-104` |
| Prompt authoring: repo-specific targeting in the prompt, not the skill; `Begin by using the <skill> skill` | `SKILL.md:106-119`; `references/prompt-template.md` |
| Memory file good/bad entries; "deleting it would lose future-run context" test | `SKILL.md:121-137` |
| Workflow customisation checklist | `SKILL.md:139-156` |
| YAML validation, dry-run bootstrap | `SKILL.md:158-203` |
| `/iterate` helper + footer marker | `references/agent-iteration.ts` (identical to DCL's) |
| Single agent step (no discrete sensor/controller) | `references/workflow-template.yml` (diff vs DCL: one `Run coding agent` step) |

### `EXE` — execution (ours)

| Component | Citation |
|---|---|
| Scope selector with explicit stop-and-route row | `SKILL.md:14-23` |
| bd as the single state anchor; `--actor` on every write; close with evidence | `SKILL.md:27-30` |
| Risk routing small / standard / deep; TDD, security, debugging mounted by condition | `SKILL.md:34-45` |
| Workspace + ledger contract (`scratchpad/execution/<slug>/progress.md`) | `SKILL.md:46-51`; `references/task-engine.md:26-53` |
| Discovered work becomes a real bd stage with `discovered-from` dep | `SKILL.md:52-54` |
| Return-to-planning triggers | `SKILL.md:55-58` |
| Phase loop: resolve epic by phase-id, select + claim, implement, verify, close, render | `SKILL.md:62-88` |
| Discipline gate: phase closes only with stages and all closed; exit criterion; verification-before-completion | `SKILL.md:89-96` |
| Rationalization table | `SKILL.md:121-130` |
| Roles: coordinator / implementer / spec- and code-reviewer, model pinned per dispatch | `references/task-engine.md:9-24` |
| Snapshot model: reviews packaged from working tree vs `SCOPE_BASE` | `references/task-engine.md:55-74`; `scripts/review-package.sh` |
| Task brief extraction and path-not-content dispatch | `references/task-engine.md:76-89`; `scripts/task-brief.sh` |
| Four-value status contract with recovery rules | `references/task-engine.md:90-102` |
| Light path (one implementer + coordinator verify) | `references/task-engine.md:104-113` |
| Full path: preflight batched questions, review gate, relay-verbatim, minor/plan-mandated routing | `references/task-engine.md:115-139` |
| Five-round fix loop, stronger model at rounds 4–5, breaker with adjudication matrix | `references/task-engine.md:141-184` |
| Final review with independent critic, one fix dispatch, simplification look | `references/task-engine.md:186-226` |
| Task sizing rules (one deliverable per dispatch, capped prompt/result) | `references/task-engine.md:228-237` |
| Workstream mode opt-in by invocation only; authorization recorded in ledger | `references/workstream-mode.md:3-6, 15-17` |
| Dirty-tree baseline — files dirty before the walk belong to the user | `references/workstream-mode.md:18-20` |
| Sequential phases, per-phase commit of explicit paths, no push | `references/workstream-mode.md:8-11, 34-43` |
| `/compact` + re-query bd between phases; compaction restores facts not reasoning | `references/workstream-mode.md:44-46, 60-77` |
| Enumerated auto-approvals | `references/workstream-mode.md:50-58` |
| Fail-stop rules | `references/workstream-mode.md:79-84` |

### `WG` — workflow-graphs (ours, draft)

| Component | Citation |
|---|---|
| Graphs as data, one per task type; stage = skill + agents/models + human gate + mounted disciplines | `WG:21-26` |
| Seed into beads via `bd formula`; formula *is* the format, sidecar only if needed | `WG:27-33` |
| Execution stage chooses inner shape (TDD / incremental / doubt-driven), final whole review | `WG:34-38` |
| Per-feature override of the default graph | `WG:39-41` |
| Mount many disciplines, not route one | `WG:44-47` |
| Graphs are process, roadmaps are content | `WG:48-51` |
| No loops in the graph format — iteration lives inside a stage | `WG:52-55` |
| v1 = interpreter + one graph, runtime-neutral, bd holds state | `WG:56-61` |
| Key assumption: ≥3 graph types needed or the abstraction is not worth it | `WG:69-72` |
| Not doing: workflow engine, merging disciplines into the graph | `WG:81-93` |

## Cross-skill matrix

| Component | DCL | BIAL | EXE | WG |
|---|---|---|---|---|
| Repo reconnaissance before asking | ✓ | ✓ | — | — |
| Interview / setup questions with evidence-based defaults | ✓ | ✓ | — | — |
| Set point (target state for a measurable property) | ✓ | — | — | — |
| Sensor (measurement of the repo) | ✓ | ~ (implicit in "what are we finding") | — | — |
| Controller (select next increment from measurement) | ✓ | ~ (prompt-embedded policy) | ~ (`bd ready` selects, no measurement) | ~ (stage order, not measurement) |
| Actuator = coding agent + repo-local skill | ✓ | ✓ | ~ (implementer agent + brief) | ~ (stage assignment) |
| Fused-component allowance | ✓ | — | — | — |
| Disturbance named explicitly | ✓ | — | ~ (dirty-tree baseline; "plan changed underneath you") | — |
| Dampener / regression gate vs baseline | ✓ | — | — | — |
| Scope gate (may change vs may only read) | ✓ | ✓ | ✓ (owned and forbidden files in brief) | — |
| Golden patterns established before automating | ✓ | ~ (ask about existing skills/PRs) | — | — |
| Written design captured before build | ✓ | ~ (completion criterion: every placeholder chosen) | ✓ (plan + document-review for deep) | ✓ (graph settled before seeding) |
| Local-first runnability gate | ✓ | — | — | — |
| Generated actuator skill with completion criteria | ✓ | ✓ | — | — |
| Response template → PR body / report | ✓ | ✓ | ~ (report file + status contract) | — |
| Memory carried between runs | ✓ | ✓ | ~ (ledger; written, not re-read by next unit) | — |
| Memory loaded *after* selection, deterministically | ✓ | ~ (interpolated, order unspecified) | — | — |
| Human steering channel that changes future runs (`/iterate` → memory) | ✓ | ✓ | — | — |
| Throughput bound against review capacity (open-PR cap) | ✓ | ✓ | — | — |
| Bounded fix loop with breaker | — | — | ✓ | — |
| In-loop independent review / critic | — | — | ✓ | ~ (human gate per stage) |
| Risk routing per unit | — | — | ✓ | ~ (per-stage assignment) |
| Disciplines mounted per unit (TDD / security / debugging) | — | — | ✓ | ✓ |
| Tracker as state store | — | — | ✓ | ✓ |
| Close-with-evidence | — | — | ✓ | — |
| Compaction / context-survival rules | — | — | ✓ | — |
| Unattended mode gated by explicit opt-in | ~ (schedule is the opt-in) | ~ | ✓ | — |
| Git safety (explicit staging, no force) | — (`git add -A` in iterate path) | — | ✓ | — |
| Agent-agnostic runner recipes | ✓ | ✓ | — | ~ (runtime-neutral by intent) |
| Spend guards | ✓ (`--max-turns`, `--max-budget-usd`) | ✓ | — | — |
| Dry-run bootstrap | ✓ | ✓ | — | — |
| Rationalization table | — | — | ✓ | — |
| Progressive disclosure of references per phase | ✓ | ~ (one reference list at end) | ✓ (two references by path) | — |
| Anti-template stance | ✓ | — | — | — |
| Schedule / cron trigger | ✓ | ✓ | — | — |

## Shared-component differences

**Controller / next-unit selection.** `DCL` derives the next increment from a
measurement and sizes it for review (`SKILL.md:68`); it is the explicitly
tunable part. `BIAL` folds selection into the prompt ("find high-confidence
targets", `references/prompt-template.md:13`). `EXE` selects from bd's ready
front (`SKILL.md:75-76`) — correct for planned work, blind to repo state. `WG`
fixes stage order in the graph (`WG:21-26`). Stronger for recurring work: DCL —
selection that reacts to the repo is what makes the loop converge. Stronger
for planned work: EXE — dependency order from a tracker cannot be derived from
a measurement.

**Memory / steering.** `DCL` and `BIAL` write standing feedback to a file that
is injected every run; `DCL` additionally pins the injection point (after the
controller, `SKILL.md:129`) and has the `/iterate` write-back
(`references/agent-iteration.ts:20-25`). `EXE`'s ledger is written per event
(`references/task-engine.md:34-44`) and re-read after compaction
(`:51-53`) but no later unit consumes it as guidance; the bd close reason is
the durable residue (`SKILL.md:27-30`). Stronger: DCL — it closes the loop from
human feedback to future behaviour. (Our harness has `bd remember` as the
natural equivalent, unused by EXE.)

**Scope gate.** `DCL`/`BIAL` pin may-change vs may-inspect directories at
design time (`DCL SKILL.md:64`); `EXE` pins owned and forbidden files per task
brief (`references/task-engine.md:81-85`). Equivalent strength; EXE's is
finer-grained (per task), theirs is loop-wide.

**Written design before build.** `DCL` captures the component design in prose
with a completion criterion (`SKILL.md:77`); `EXE` requires a plan plus
document-review plus human approval for deep phases (`SKILL.md:71-73`); `WG`
settles the graph before pouring it into bd (`WG:27-29`). EXE's is stronger
(reviewed, approved); DCL's is proportionate to its blast radius.

**Unattended mode.** `DCL`/`BIAL` are unattended by construction — the
schedule runs without a human present, and the actuator prompt says so
(`references/prompt-template.md:32`). `EXE` makes unattended a gated opt-in
with recorded authorization and enumerated auto-approvals
(`references/workstream-mode.md:3-6, 50-58`). Different hosts, same principle:
neither lets the agent decide on its own to go unattended.

**Response / report contract.** Theirs becomes the PR body and is templated
per task type (`DCL references/response-template.md`); ours is a short status
contract inline plus a report file (`references/task-engine.md:231-234`).
Stronger for a human reviewer: theirs. Stronger for a coordinator that must
not absorb content: ours.

**Progressive disclosure.** `DCL` names the references to read at each phase
(`SKILL.md:45, 60, 81, …`); `EXE` points at two references by path from the
routing table (`SKILL.md:37-39`). Same mechanism; DCL's is more granular. BIAL
lists references once at the end (`SKILL.md:205-214`), weaker — the agent
must guess when to read which.

**Git handling.** `DCL`'s iterate path does `git add -A` and commits
(`references/workflow-template.yml:260-263`); its runner recipe uses
`--permission-mode bypassPermissions` (`references/agent-runner-templates.md:31`).
`EXE` stages explicit paths only and never pushes (`references/workstream-mode.md:36-43`).
Ours is stronger; theirs would violate our Git Safety rules as written and
would have to be rewritten before any reuse.
