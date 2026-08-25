# Orchestration decision record — capabilities, discards, deferrals, current attempt

Status: living record, last updated 2026-08-24. Covers the full evaluation arc:
omnigent → direct-CLI council → workflow-graph brainstorm → beadboard / aweb /
looptroop assessment. Detail lives in the pointed-to docs; this file is the
decision ledger a fresh session reads first.

Sources: `docs/research/codebases/omnigent/00-index.md`,
`docs/research/codebases/comparison-beadboard-aweb-looptroop.md`, per-repo
`capabilities.md` files, `scratchpad/brainstorms/workflow-graph-cycles/
consolidation.md` (session-local), bead cr-o85.

## 1. What capabilities were available (the full menu we evaluated)

| Source | Capabilities it genuinely offers (its ceiling) |
|---|---|
| **omnigent** (`reference_tools/omnigent` @ 33ec5137, alpha) | Meta-harness over 8+ agent CLIs (Claude/Codex/Cursor/OpenCode/Hermes/Pi/ACP): durable control plane (SQL, 17 tables) + per-host runners over WS; live session supervision incl. mid-turn steer on Codex; approval relay; warm reattach; sandbox/credential-proxy when configured. NO workflow/pipeline primitive (`AgentDef.workflow` parsed, never consumed); no headless exec; 39-dep install. |
| **BeadBoard** (@ 9e3059d, v0.1.0) | Live bd dashboard (Dolt + JSONL watch, SSE); bd mutations via `bd` CLI; agents-as-beads registry; heartbeats as ephemeral event beads; agent mail; TTL path reservations; bd→DAG graph projection with anomaly diagnostics; Pi worker spawning (in-process); multi-project aggregate views. |
| **aweb** (@ da5854cf, server 1.27.4 — most mature) | Durable cross-machine agent mail/chat on Postgres; wake-on-event SSE (signal-then-exact-fetch); presence/heartbeat; TTL resource locks distinct from task ownership; cryptographic identity (AWID, teams, certificates); MCP mount; `aw run` wake loop invoking Claude/Codex via a clean 6-method `Provider` interface; optional task queue; A2A gateway. |
| **LoopTroop** (@ 7b129216, v0.5.8) | The only real workflow engine of the set: ticket → council planning (parallel drafts, anonymized vote, refine) → human-approved PRD → bead-blueprint JSONL → sequential per-bead OpenCode coding in isolated worktrees → bounded Ralph-style retries (reset to start commit + carried failure note) → executed final tests → Manual QA → draft PR → human merge. Durable XState snapshot in SQLite; startup recovery taxonomy; sha256-gated approvals; per-phase context allowlists. |
| **bd itself** (v1.1.0, pinned) | DAG-native issue graph (cycle-checked deps), molecules/bonds, gates (human/timer/gh:run/bead), formulas (DAG steps; upstream loop schema unverified locally), event beads with payload (`--event-payload` round-trips), audit records (closed schema — lossy), Dolt-backed durability. |

## 2. Why we discarded what we discarded

Settled premises doing the rejecting: (P1) bd is the ONLY durable state;
(P2) the workflow graph is DATA (versioned, hashable, schema-validated), never
code or prose; (P3) the orchestrator is model-agnostic; (P4) the runner floor
is vendor-neutral (claude/codex/opencode first).

| Discarded | Reason (which premise / which evidence) |
|---|---|
| omnigent as platform (now) | No workflow primitive at all; no headless one-shot exec; heavy install. Every current stage is prompt-in → artifact+exit-code-out, which direct CLI does in ~300 LOC/vendor. Buy-never-build if reopened. |
| BeadBoard as platform | Completion = "model stopped talking" (`worker-session-manager.ts:377-414`); Pi-only at the type level (violates P4); workers in-memory, lost on restart; coord.v1 writes through `bd audit record`, which a live probe showed silently drops all out-of-schema fields — the subsystem never worked. |
| aweb as platform | Sequences nothing by design (its "workflow" is 5 lines of prose); 4-service footprint (aweb+AWID+Postgres+Redis) at a communication layer v1 does not open; its task queue is a strictly weaker bd (violates P1). |
| LoopTroop as platform | Closest substitute in existence and fails every premise: graph is 571 lines of compiled XState (P2); SQLite spine + private bead JSONL (P1); OpenCode-locked (P4). Mechanisms extractable; platform not. |
| Completion by prose or self-report | BeadBoard's `agent_end`; LoopTroop's self-asserted `tests: pass` strings (`completionChecker.ts:38-46` — never executed). Ruling: a structured marker is the agent's CLAIM; the interpreter must compute ≥1 independent clause (exit code, artifact hash, diff) before writing an outcome. |
| Schema'd state on lossy bd surfaces | `bd audit record` drops unknown fields silently (probe); formula layer drops unknown top-level fields (prior probe). Rule: write-then-read-back probe for every bd field the graph relies on + validator startup canary. |
| Fine-grained advisory locking | BeadBoard reservations: overlap never enforced at acquisition (`src/` doesn't block `src/lib/x.ts`), conflict detector on the dead read side. Coarse-and-enforced (LoopTroop's execution band) beats fine-and-advisory. |
| Council voters ranking their own drafts; opt-out danger flags; unaudited bound sprawl (6 counters, 5×10 retry worst case); auto-push with conditional `--no-verify`; second coordination system running beside its replacement; ADR-described daemons never built | Each observed live in the evaluated repos; each maps to an existing rule (author-excluded ballots; opt-in danger; single auditable boundedness statement; git safety; pick-one-pattern). |
| ox-alpha (`opencode/x-preview-f-free`) for analysis roles | Failed 3/3 long jobs (no terminal answer / provider error / silent hang). Fine for short one-shots; retest later. |

## 3. Deferred for later stages (with reopen triggers)

| Deferred | Reopen when |
|---|---|
| omnigent adoption (buy, never build) | (a) phone mid-turn supervision of non-Claude agents; (b) cross-vendor approval relay; (c) warm reattach across days; (d) enforced sandbox + secretless credentials. Interactivity, not CLI count, is the threshold. |
| aweb service (communication layer) | Durable multi-machine coordination; cross-org agent identity; runner floor grows past ~3 vendors. Until then: steal only the protocol (wake-as-hint → fetch exact record → mark delivery BEFORE ack → reconcile from durable state). |
| Task-ownership vs resource-lease separation (aweb) + execution-band exclusion (LoopTroop) | Concurrent features / multi-foreman (S1). v1 is single-foreman, single active execution band derived from bd queries. |
| bd formula as materialization layer | After the loop schema is verified on pinned bd v1.1.0. v1 seeds beads directly, no formula. |
| bd→graph operator projection (BeadBoard) | When we want a visualizer; read-only; never its cycle detector as validator. |
| bd event beads as transition-event carrier | Adopted in principle; blocked on the round-trip probe suite (§2 lossy-surface rule). |
| Second workflow-graph type (ML experiments, research), non-Claude foreman build, cost enforcement, cron tick, formula generation, graph editor, live-instance migration | All explicitly out of v1 scope (brainstorm consolidation). |
| LoopTroop re-evaluation | It externalizes its graph as validated data, adopts real bd, or breaks the OpenCode lock. Moving fast — worth watching. |

## 4. What we are attempting now

The **cr-o85 workflow-interpreter spec + v1 proof**, drafted in
`docs/specs/workflow-interpreter.md`:

1. Three-layer factory: content (roadmaps/bd epics = WHAT) → process
   (versioned workflow graph = HOW one unit moves) → floor (uniform
   claude/codex/opencode runner profiles = WHO executes). bd is the only
   durable state; the interpreter is a stateless-between-ticks foreman any
   model can run.
2. Graph = TOML state-machine-as-data: nodes (runner-profile/model/contract/
   context-allowlist), typed outcomes, ordered regions `acyclic |
   bounded-cycle` with mandatory `max_entries` + `on_exhausted`; unbounded
   loops unwritable (SCC validation). Cyclic template, acyclic trace: every
   node visit mints a fresh activation bead; bounds counted structurally.
3. Absorbed mechanisms from this evaluation: sha256-bound human approval +
   receipts; bounded attempt envelope (pre-attempt commit → worktree reset
   preserving state dir → mandatory dying-session note → fresh session);
   per-node context allowlist; resolved-config pinning with provenance;
   declare-then-verify file effects; Provider-shaped runner profiles with
   inverted danger defaults; claim-vs-computed-evidence completion.
4. v1 proof: one `feature-delivery` graph, one real small feature, Claude as
   first foreman (contract vendor-neutral), forced rejection via test-only
   flag; drills: crash (fresh zero-context session resumes from bd alone),
   bound exhaustion (cap=1 → human gate), human ship gate.

## 5. Design rulings after the spec review (2026-08-25, user-decided)

The two-reviewer pass (Sol xhigh + Opus 5 high — unanimous REVISE:
architecture affirmed, failure model missing) pushed the draft toward full
determinism. The user pushed back: over-scripting loses the intelligence the
system exists to use. Rulings, now normative in the spec (§10–§12):

1. **Three-tier control model** (spec §10). The foreman remains a model.
   Tier 1 invariants are enforced by deterministic code and are never the
   model's to waive: bounds, signed human gates, computed evidence before
   any edge, append-only trace, read-only bd for runners. Tier 2 defaults
   (reset-vs-salvage, retry-vs-replan, context composition, early
   escalation) are the model's to override WITH a recorded deviation.
   Tier 3 is pure judgment. Why this line: all three evaluated repos failed
   where a model graded its own work (BeadBoard `agent_end`, LoopTroop
   self-reported gates) — grading stays deterministic; LoopTroop's rigidity
   shows scripted recovery fails on messy reality — deciding stays
   intelligent. The reviewers' "normative command table" is reinterpreted
   as how-to knowledge for non-Claude foremen, not a script.
2. **Worktree isolation is optional** (spec §11): per-node
   `isolation = worktree | in-repo`, default worktree; in-repo keeps all
   invariants, forces a single execution band, and demotes reset-on-reject
   to tier 2 (never reset uncommitted human work).
3. **Hard-reset is a default, not a route** (spec §10 tier 2): salvage of a
   partially-good attempt is legal with a deviation record, provided the
   attempt is counted and the artifact verified.
4. **Agent-to-agent communication: not needed; hub-and-spoke through the
   foreman wins for this factory.** Workers are one-shot; artifacts +
   structured outcomes + the next briefing carry all information, and
   hub-and-spoke is what keeps the anti-collusion context allowlists
   airtight. aweb stays rejected-as-platform with its recorded reopen
   triggers (long-lived peer agents on multiple machines / cross-org
   identity). CLI capability facts underpinning this: claude
   `--resume/--continue`, codex `exec resume`, opencode session
   continuation all accept new instructions between turns; NONE supports
   mid-turn steering in one-shot mode — that remains the omnigent reopen
   trigger. Added instead: the **steer action** (spec §12) — terminate,
   record reason, resume-with-instructions; guidance-steers don't consume
   rework budget.
5. **Monitoring is token-free by construction** (spec §12): liveness,
   completion, progress, staleness, and runaway detection are deterministic
   scripts over the supervisor wrapper's pgid/exit-file/JSONL event log
   (claude `stream-json`, codex `--json`); the foreman's model reads bytes
   only at state transitions (terminal → parse marker + verify; stale →
   ~2KB tail), never streams logs. Full design lands in spec v0.2; drills
   must cover the hung runner and the lying completion.
