# Workflow Interpreter — design spec (DRAFT for review)

Status: **draft v0.1.1 — reviewed, revision pending** — bead cr-o85.
Two-reviewer verdict (Sol xhigh + Opus 5 high, 2026-08-24): unanimous REVISE —
architecture affirmed, failure model missing; fix plan in
`scratchpad/research/three-repos/spec-review-consolidation.md`, to be applied
as v0.2. Sections §10–§12 below are user design rulings (2026-08-25) accepted
AFTER that review and normative for v0.2. Supersedes the parked idea in
`docs/ideas/workflow-graphs.md` (its "no loops in the graph format" constraint
is overturned here, with argument). Inputs: the workflow-graph brainstorm
consolidation, the omnigent/direct-CLI council ruling, and the
beadboard/aweb/looptroop assessment
(`docs/research/orchestration-decision-record.md` is the decision ledger).

## 0. Purpose and premises

One unit of work (a feature, a bug, later an ML experiment) moves through a
**workflow graph**: implement → review → (rework)* → verify → ship, with
human gates where placed. Many units run concurrently, autonomously, across
different models and agent CLIs. This spec defines the graph format, its bd
encoding, the interpreter that executes it, and the runner floor beneath it.

Settled premises (not re-litigated here):

- **P1 — bd is the only durable state.** Crash recovery = re-read bd from a
  fresh context. No SQLite, no sidecar DB, no state in chat or scratchpad.
- **P2 — the graph is data.** TOML + JSON Schema, versioned, content-hashed,
  reject-unknown-fields. Never compiled code (LoopTroop's 571-line XState
  machine is the cautionary tale), never prose (aweb's playbooks).
- **P3 — the orchestrator is model-agnostic.** Any capable model + the bd CLI
  + this spec's interpreter contract can be the foreman. Claude is merely the
  first implementation.
- **P4 — the runner floor is vendor-neutral.** claude / codex / opencode
  profiles first; one invocation contract.

## 1. Graph definition format

One graph = one TOML file under `workflows/`, validated by a JSON Schema
(`workflows/schema.json`) that **rejects unknown fields** (bd's own layers
silently drop them — the definition layer must be the opposite).

```toml
[graph]
id          = "feature-delivery"
version     = "1.0.0"
description = "One feature: plan-approved → implemented → reviewed → shipped"

[[region]]                      # regions are ordered; back-edges may not
name = "build-review"           # cross into an earlier region
mode = "bounded-cycle"          # "acyclic" | "bounded-cycle"
max_entries = 3                 # mandatory for bounded-cycle
on_exhausted = "gate:human-triage"

[[node]]
name    = "implement"           # "node", never "stage" (CONTEXT.md reserves Stage)
region  = "build-review"
runner  = "profile:implementer" # resolved at instantiation, pinned on the instance
inputs  = ["task_brief", "prior_failure_notes"]   # context allowlist — closed set
outcomes = ["done", "fail_code", "fail_plan"]

[[node]]
name    = "review"
region  = "build-review"
runner  = "profile:critic"
inputs  = ["task_brief", "diff_artifact"]         # NOT the implementer's reasoning
outcomes = ["accept", "reject"]

[[edge]]
from = "review"
on   = "reject"
to   = "implement"              # the back-edge: legal because region is bounded-cycle

[[edge]]
from = "review"
on   = "accept"
to   = "gate:ship"              # human gate node

[fallback]                      # deterministic fallback edge: any outcome not
to = "gate:human-triage"        # matched by a declared edge routes here
```

Validator (deterministic script, runs pre-instantiation and in lint sweeps):
schema-validate reject-unknown; SCC analysis — every cycle must sit inside one
`bounded-cycle` region; every `bounded-cycle` has `max_entries` ≥ 1 and an
`on_exhausted` that reaches a human gate or terminal; terminals have no exits;
no back-edge crosses regions backward; every node reachable, every declared
outcome covered by an edge or the fallback. **An unbounded loop is
unwritable**, not merely discouraged.

Outcome vocabulary is closed per node and drawn from a global enum:
`done | accept | reject | pass | fail_code | fail_plan | error_runner |
error_transport`. The distinction `fail_code` (work wrong) vs `fail_plan`
(task spec wrong) vs `error_runner`/`error_transport` (infrastructure) drives
different edges and different counters — runner failures do not consume
review-cycle budget.

## 2. Instance state in bd (cyclic template, acyclic trace)

The bd record never contains a cycle. A back-edge executes by **minting new
beads**, never reopening old ones.

- **Root bead** (type `task`, one per instance): pins `graph_id`,
  `graph_version`, `graph_content_hash`, plus the full **resolved
  configuration with provenance** — runner profiles, models, every bound,
  each tagged with its source layer (graph default / project config /
  per-instance override). A live instance can never be rerouted or re-budgeted
  by editing a file (LoopTroop's `locked_*` + `*_source` pattern).
- **Activation bead** (type `task`, child of root, one per node VISIT):
  `node`, `attempt_no`, `runner_profile`, `model`, `session_id`,
  `idempotency_key`, `pre_attempt_commit`, and on close: structured outcome,
  artifact identity, usage record. Attempts are counted by **counting
  activation beads** — structural, unfalsifiable by any agent.
- **Transition events**: append-only record of each edge taken
  (`from`, `outcome`, `to`, `activation_id`, actor). Intended carrier:
  bd **event beads** (`bd create --type event --event-payload`), which a live
  probe showed round-trips payloads — **never `bd audit record`**, which
  silently drops them. Gate: §7 probe suite must pass before this carrier is
  final; the degradation floor is plain beads + labels.
- **Gates**: bd gate beads. Human gates are closed only by humans
  (`--actor`-audited) and only with a `--reason` carrying the sha256 of the
  artifact reviewed (§5).
- **Wisps**: interpreter tick/heartbeat noise uses `--ephemeral --wisp-type`
  so high-frequency records never pollute the durable trace.

Idempotency: `idempotency_key = hash(root_id, node, attempt_no)`. Before
dispatch, the interpreter queries for an existing activation with that key;
recovery after a crash therefore re-attaches instead of double-dispatching.

## 3. The interpreter (foreman contract)

A stateless-between-ticks process. Each tick:

```text
tick:
  frontier  = derive from bd alone (bd ready + open gates + running activations)
  for each instance in frontier:
    if running activation:        check runner terminal state; if terminal → §4 completion
    elif gate open:               nothing (humans close gates)
    else:
      next_node = edge lookup (last outcome → declared edge, else fallback)
      enforce bounds (§6): count activation beads vs max_entries; no-progress check
      if bound exhausted:         materialize on_exhausted gate; stop
      mint activation bead (idempotency-checked)
      dispatch via runner floor (§4)
  write transition events; exit
```

Signals (file watchers, SSE, notifications) are **hints only**: they may wake
the interpreter early, but the frontier is always recomputed from bd — a lost
signal can never lose work (aweb's principle; BeadBoard's watcher-bus is the
anti-example). The tick is host-cron-driven; the interpreter holds no memory
between ticks, so any model, or a different model per tick, can run it.

Two-iteration-layers ruling (ratified): for graph-driven work, **the graph's
review loop replaces the execution engine's internal fix loop**. Node-internal
iteration is red-green only. Resume of a session is legal only for
`error_transport` (the transport failed); `fail_*`/`reject` always
abandon-and-reset (§5) — the failed reasoning is a liability, not an asset.

## 4. Runner floor

Per-CLI profiles (claude, codex, opencode) implementing one interface, shaped
on aweb's `Provider` (6 methods, proven on two vendors) with two amendments:

```text
Profile:
  name()
  build_command(task)          # one-shot headless invocation
  build_resume_command(session)# machine resume (transport-failure path only)
  build_resume_hint(session)   # human-pasteable reattach — recorded on gate beads
  parse_output(stream) -> Event{type, text, session_id, duration, usage?, cost?, is_error}
  session_id(events)
```

- **Danger defaults inverted**: profiles run sandboxed/read-only by default;
  write access is per-node opt-in in the graph, never a CLI default (aweb
  ships `--dangerously-*` as the default — do the opposite).
- **Unsupported option = loud error**, never a silent drop (aweb's
  `AllowedTools` on codex errors; bd's silent drops are the anti-pattern).
- **Usage/cost normalization is owned here**: every profile emits a normalized
  usage record; a profile that cannot (codex JSON omits cost) records
  `usage: unknown` explicitly — never a fabricated zero. Bounds never depend
  on cost telemetry (structural counting only), so missing telemetry degrades
  reporting, not safety.

**Completion contract (five clauses, all computed by the interpreter):**
1. Runner process terminal (exit observed, not inferred).
2. Structured outcome marker parsed from output — this is the agent's CLAIM.
3. ≥1 independent computed check per contract: verification command exit code,
   artifact hash, diff non-emptiness (claim ≠ proof; LoopTroop's self-reported
   `tests: pass` is the anti-example).
4. Artifact identity recorded: **a commit in the runner-owned worktree** —
   every attempt ends in a commit (or `no-diff` outcome); the commit sha is
   the artifact id (resolves the uncommitted-work question).
5. Declared-vs-observed effects reconciled: the runner declares touched paths;
   the interpreter diffs the worktree; surprises recorded as
   `undeclared_effect` on the activation bead.

## 5. Adopted mechanisms (from the evaluation, normative here)

1. **Hash-bound human gates.** Gate close requires the sha256 of the reviewed
   artifact; interpreter refuses the transition on mismatch
   (`StaleApproval`); approval receipt (actor, time, artifact, hash) written
   to the gate bead. Artifact edits after approval write an edit receipt and
   invalidate downstream approvals.
2. **Bounded attempt envelope.** Every activation records
   `pre_attempt_commit`. On a reject/fail edge: hard-reset the runner-owned
   worktree to it (preserving the instance-state directory), require the
   failing session to emit a bounded structured failure note before teardown
   (deterministic fallback note if it can't), abandon the session. The next
   activation gets fresh context + the notes via its `inputs` allowlist.
   Applies **only** inside runner-owned worktrees, never a shared tree; no
   auto-push; no `--no-verify` ever.
3. **Context allowlists** (§1 `inputs`): enforced at prompt assembly; unknown
   source name = hard error; ordered trim priority under token budget. The
   critic never sees the implementer's reasoning — only the artifact.
4. **Recovery taxonomy.** On startup/tick after a crash, running activations
   are classified `reconnected | preserved-unverified | abandoned`;
   `preserved-unverified` can never advance an edge until the completion
   contract re-verifies it.

## 6. Bounds — four layers, all mandatory

1. **Declared** in the graph data (`max_entries`, `on_exhausted`) — validator
   makes unbounded graphs unwritable.
2. **Counted** structurally in bd (activation beads per region per instance).
3. **Enforced** by the interpreter at each materialization, before dispatch.
4. **Audited** by a lint sweep (deterministic script) over live instances.

No-progress breakers, checked at back-edge time: artifact-hash equality with
the rejected attempt (`no_progress` → exhaust path early), finding-fingerprint
stability across review rounds. Missing telemetry for a breaker =
**fail-closed** (route to human gate, do not loop). Distinct counters for
review cycles vs runner failures vs plan invalidations (§1 vocabulary) so an
infra flake cannot silently consume the rework budget.

## 7. bd round-trip probe suite (blocking obligation)

bd's extension surfaces are lossy-by-default (two probes: formula top-level
fields; `bd audit record` payloads — both silently dropped, exit 0). Before
any bd field carries graph state, a probe writes it and reads it back on the
pinned bd version; the validator runs a canary round-trip at startup and
refuses to tick on mismatch. Fields requiring probes: event-bead
`--event-payload`, bead metadata used for pinning, labels, close-reason
structure, gate types, `--ref` bonds.

## 8. v1 scope (the proof)

One graph (`feature-delivery`), one real small feature, Claude as first
foreman (contract vendor-neutral), direct bd seeding (no formula), forced
first rejection via a test-only instance flag with a predetermined innocuous
finding. Acceptance:

1. Crash drill: kill the foreman mid-loop; a fresh zero-context session
   resumes correctly from bd alone.
2. Bound drill: `max_entries = 1` → exhaust gate opens; human closes it.
3. Human ship gate closed with hash-bound approval; receipt present.
4. Exactly one activation per idempotency key; rework artifact hash ≠
   rejected hash; reviewed hash = verified hash; no workflow state outside bd.
5. Validator rejects a deliberately unbounded and an escape-less graph.

Out of scope for v1: second graph type, concurrent instances/merge-slots,
cost enforcement, cron tick (manual tick is fine), non-Claude foreman build,
formula materialization, communication layer, graph editor, live-instance
version migration.

## 9. Open questions — dispositions

| # | Question (from brainstorm consolidation) | Disposition in this draft |
|---|---|---|
| 1 | Activation record encoding | Task beads for activations + event beads for transitions (§2), gated on §7 probes; verdicts in structured close reasons. |
| 2 | Artifact identity for uncommitted work | Commit-per-attempt in runner-owned worktree; sha is the id (§4 clause 4). |
| 3 | Cost telemetry normalization | Owned by runner profiles; `unknown` is legal; bounds never depend on it (§4). |
| 4 | Formula loop schema verification | Deferred with formula itself; v1 formula-free (§8). |
| 5 | Two-iteration-layers ruling | Ratified: graph loop replaces engine fix loop; resume only on transport failure (§3). |
| 6 | Concurrent-tick claim-lease | Deferred to S1; v1 single foreman + single execution band derived from bd query. |
| 7 | Human-gate timeout / graph-version retention | v1: gates wait indefinitely (timeout policy deferred); definitions immutable once instantiated — a change is a new version, old versions retained while any instance pins them. |
| 8 | Engine-reopen threshold | Measured after v1; reopen criteria stand in the decision record. |

## 10. Control model — three tiers (normative; supersedes any "fixed route" reading)

The foreman is a **model**, and the spec must not compile its intelligence
away. Every behavior in this document belongs to exactly one tier:

1. **Invariants — never overridable, enforced by deterministic code** (the
   validator, the supervisor wrapper, the completion checker — never the
   model's judgment): bound ceilings (§6, incl. the per-instance total
   activation ceiling); human gates require an externally verifiable
   credential; no edge advances without the computed-evidence clauses of §4;
   the bd trace is append-only; runner agents hold `bd --readonly` or no bd;
   the model selects only declared edges, never invents one.
2. **Defaults with override — the foreman may deviate, and every deviation
   writes a deviation record** (reason, alternative taken) on the activation
   bead: hard-reset vs salvage of a failed attempt (§5.2 is the DEFAULT
   policy, not a fixed route — salvage is legal when the foreman judges the
   prior work sound and the objection narrow, provided the attempt is still
   counted and the artifact still verified); retry vs replan; context
   composition within the allowlist; early escalation to a human before a
   bound forces it.
3. **Pure judgment — entirely the model's**: interpreting ambiguous
   failures; briefing workers; sequencing observations ("these two features
   will collide"); choosing when a situation warrants the tier-2 override.

Rationale (from the three-repo evidence): every evaluated system failed where
a model's claim was trusted without a check (BeadBoard's `agent_end`,
LoopTroop's self-reported gates) — so **grading stays deterministic**; and
LoopTroop's rigidity shows scripted recovery fails on messy reality — so
**deciding stays intelligent**. The interpreter contract (§3) is therefore
how-to knowledge plus guardrails, not a script: the normative command table
exists so a non-Claude foreman doesn't stumble on bd's sharp edges, not to
remove judgment.

## 11. Isolation modes (worktree optional)

Per node (overridable per instance): `isolation = "worktree" | "in-repo"`,
**default `worktree`**. In-repo mode keeps every invariant — same
verification, same attempt commits, same bounds — minus physical isolation,
with two stated consequences: (a) exactly one active execution band at a
time (two runners must never share a dirty tree); (b) reset-on-reject
touches the shared working copy, so it drops from tier 1 to tier 2 — the
foreman confirms or records a deviation before resetting a tree it does not
own, and never resets uncommitted human work.

## 12. Supervision: steer, and token-free monitoring

**Steer action** (tier 2, foreman toolkit): terminate a running activation's
process group → record the reason → mint a continuation attempt via the
profile's resume-with-instructions path (same session id). A steer whose
cause is guidance (not wrong work) closes the prior activation
`error_transport`-class (steered), not `fail_*` — it does not consume rework
budget (§6 counters). Capability facts this rests on: claude
(`--resume`/`--continue`), codex (`exec resume`), opencode (session
continuation) all accept new instructions BETWEEN turns; none supports
mid-turn input in one-shot mode — mid-turn supervision remains the recorded
omnigent reopen trigger, not a reason for new infrastructure.

**Monitoring — the polling loop spends zero model tokens.** All liveness,
progress, and staleness detection is done by deterministic code over the
supervisor wrapper's outputs; the foreman's model reads bytes only at state
transitions:

| Signal | Mechanism (deterministic, token-free) |
|---|---|
| Alive / dead | `kill -0` on the recorded pgid + the wrapper's exit file |
| Completed | exit file exists → exit code + duration, no log read needed |
| Progressing | event count + byte growth of the wrapper-captured JSONL log (claude `--output-format stream-json`, codex `--json` both emit machine-parseable event streams; a script counts events, extracts last event type/timestamp, tool-call count, token usage) |
| Stale | process alive AND no new events for `stale_after` (per-node, default e.g. 10 min) → raises a flag for the foreman |
| Runaway | wall-clock / token-usage ceilings from the node contract, checked by script |

Foreman token spend is bounded and event-driven: on **terminal** → parse the
structured outcome marker + run §4 verification (never stream the full log);
on **stale flag** → read only the last ~2KB tail to judge steer / wait /
terminate (tier 2); full-log reads are exceptional and always bounded by an
explicit byte budget. "It said it completed" is never trusted by
construction — completion is the wrapper's exit file plus §4's computed
clauses, and the §5.4 recovery taxonomy already covers died-without-exit.
The v0.2 drill set must include: a hung runner (alive, silent → stale flag →
steer), and a lying completion (marker says done, verify fails → outcome
`fail_code`, no advance).
