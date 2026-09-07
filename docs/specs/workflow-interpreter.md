# Workflow Interpreter — design spec (v0.3, implementation-ready)

Status: **v0.3 — final after two review rounds** — bead cr-o85.
Round 1 (Sol xhigh + Opus 5 high) and round 2 (Sol high + Opus 5 medium)
both REVISE verdicts applied; consolidations in
`scratchpad/research/three-repos/spec-review-consolidation.md` and
`spec-r2-consolidation.md`. Supersedes `docs/ideas/workflow-graphs.md`.
Decision trail: `docs/research/orchestration-decision-record.md`.
Remaining pre-code obligations: the §11 **precondition probes** and the
[PROBE]-marked rows of the §4 command table — run them before writing v1
code; a failed probe triggers the named fallback, not silent adaptation.

## 0. Purpose, premises, threat model

One unit of work (a feature, a bug, later an ML experiment) moves through a
**workflow graph**: implement → review → (rework)* → ship, with human gates
where placed. Many units run concurrently and autonomously across different
models and agent CLIs. This spec defines the graph format, its bd encoding,
the interpreter (foreman) contract, the supervisor wrapper, the runner
floor, and the v1 proof.

Premises (settled):

- **P1 — three stores, one authority order.** **bd is the sole authority
  for intent and decision state** (what was decided, attempted, bounded,
  approved); **git holds artifacts** (commits, refs, worktrees); the
  **wrapper directory** (`.wf/<root_id>/` beside the repo) is an
  observation cache (handles, exit files, event logs) whose durable facts
  are mirrored into bd (§5.3) — losing it costs telemetry, never
  correctness. Reconciliation order on recovery: bd says what was intended;
  git says what exists; a bd record naming a missing commit halts the
  instance (§7.4). The graph definition is pinned into bd at instantiation
  (§3.1), so routing needs no file.
- **P2 — the graph is data.** TOML + JSON Schema, versioned,
  content-hashed, reject-unknown-fields. Never compiled code, never prose.
- **P3 — the orchestrator is model-agnostic.** Any capable model + this
  contract + the typed wrapper can be the foreman. Claude is the first
  implementation, not a dependency.
- **P4 — the runner floor is vendor-neutral.** claude / codex / opencode
  profiles first; one invocation contract.

**Threat model.** bd actor identity is unauthenticated free text;
`bd close --force`, `bd delete`, and `--set-metadata` exist. bd records are
therefore **tamper-evident, not tamper-proof**. The wrapper's sealed
surface is an IN-PROCESS convention (Python privacy is not a security
boundary — probed, phase-2 review): the threat model assumes cooperative
in-process callers; the enforcement backstop against a non-cooperative
one is the §10.6 audit sweep, which such writes remain visible to (an
out-of-band close leaves carrier state inconsistent with bd status).
An out-of-process authority holder is deferred (§14). Cheap hardening
still applies: verified-approval objects are not exported, and repair
paths re-verify the signature they hold rather than trusting carrier
state. Enforcement consequences:

1. **Write boundary (settled):** all bd writes go through a **typed
   wrapper API** — `startup_canary`, `create_root`, `mint_activation`,
   `record_dispatch`, `record_exit`, `record_evidence`,
   `close_activation`, `supersede_activation`, `open_gate`,
   `close_gate_verified`, `append_event` — which constructs every
   invocation. Bound mutation is NOT a public operation: it happens
   only inside `close_gate_verified`'s verified-rebudget path
   (phase-2 ruling; a public `update_root_bounds` was a §9 bypass). The model never emits a bd write
   string; it may issue bd **reads** freely (§4 read vocabulary). The
   wrapper never constructs `--force`, `--ignore-schema-skew`,
   `bd close --continue`, `--claim-next`, or `bd delete`.
2. Runner agents hold `bd --readonly` or no bd at all.
3. Human approval is anchored in a signed payload no agent can produce
   (§9); against a malicious foreman it is tamper-evident (the audit sweep
   detects an unverified gate close), proof only against runners.
4. The pinned-config hash on the root bead is re-verified every tick.

## 1. Control model — three tiers

The foreman is a **model**; this spec does not compile its intelligence
away.

1. **Invariants — enforced by deterministic code** (validator, typed
   wrapper, supervisor wrapper, completion checker): bound ceilings (§10);
   gate transitions require a verified signed payload (§9); no edge
   advances without §7's computed clauses; the bd trace is append-only
   (supersede, never delete); runners are bd-read-only; the model selects
   declared edges only; every dispatch passes the worktree precondition
   (§5.4).
2. **Defaults with override — the foreman may deviate; every deviation
   writes a deviation record** on the activation: reset-vs-salvage (§5.5);
   retry vs replan; context composition within the allowlist; early human
   escalation; steer (§8.1); in-repo reset confirmation (§12).
3. **Pure judgment**: interpreting ambiguous failures, briefing workers,
   cross-feature sequencing, choosing when tier-2 override is warranted.

Rationale: every evaluated system failed where a model graded its own work
— grading stays deterministic; scripted recovery fails on messy reality —
deciding stays intelligent.

## 2. Graph definition format

One graph = one TOML file under `workflows/`, validated by
`workflows/schema.json` (**additionalProperties: false** everywhere). The
canonical example is normative and ships as the validator's first passing
fixture (`workflows/feature-delivery.toml`). *Implementation note
(phase 1): the schema and fixtures live as library data under
`workflow_interpreter/` until the authoring surface lands (phase 5);
`workflows/` is the authoring location, the package copies are the
library's.* JSON-Schema validation alone is NOT sufficient — per-kind
field rules live in the semantic validator (schema-alone consumers lose
them, by design; each defect needs a citable rule id for the §10.6
sweep):

```toml
[graph]
id          = "feature-delivery"
version     = "1.0.0"
entry       = "implement"
description = "One feature: implemented → reviewed → shipped"

[instance]
max_total_activations  = 20      # counts every activation AND gate bead
test_force_first_reject = false  # schema'd; validator refuses true without --allow-test-flags

[[region]]
name         = "build-review"
mode         = "bounded-cycle"           # "acyclic" | "bounded-cycle"
entry_node   = "implement"
max_entries  = 3
on_exhausted = "triage"

[[node]]
name          = "implement"
kind          = "task"                   # task | gate | terminal
region        = "build-review"
runner        = "profile:implementer"
model         = "default"
isolation     = "worktree"               # worktree | in-repo
writes        = true                     # repo-worktree write access only
allowed_paths = ["src/**", "tests/**"]   # exemption AND writable mounts
inputs        = ["task_brief", "review_findings"]
verify        = [{ cmd = "scripts/verify-feature.sh", timeout = "10m" }]
token_budget  = 120000                   # context TRIM budget (not a runaway bound)
max_wall      = "45m"                    # universal runaway ceiling (wrapper-enforced)
stale_after   = "10m"
max_infra_retries = 2
max_steers    = 2
outcomes      = ["done", "no_diff", "fail_plan"]

[[node]]
name          = "review"
kind          = "task"
region        = "build-review"
runner        = "profile:critic"
model         = "default"
isolation     = "worktree"
writes        = false                    # findings go to $WF_ARTIFACT_DIR, not the repo
allowed_paths = []
inputs        = ["task_brief", "diff_artifact"]
verify        = [{ cmd = "scripts/verify-feature.sh", timeout = "10m" },
                 { cmd = "scripts/review-checks.sh",  timeout = "5m"  }]
                # deliberately a STRICT SUPERSET of implement's set; the
                # validator warns when a judgment node's verify ⊆ its
                # predecessor's (anti-drift cross-check would be vacuous)
token_budget  = 80000
max_wall      = "30m"
stale_after   = "10m"
max_infra_retries = 2
max_steers    = 2
outcomes      = ["accept", "reject"]

[[node]]
name      = "ship"
kind      = "gate"
gate_type = "human"
binds     = "immutable"
outcomes  = ["approve", "abandon"]

[[node]]
name      = "triage"
kind      = "gate"
gate_type = "human"
binds     = "immutable"
outcomes  = ["rebudget", "abandon"]

[[node]]
name = "shipped"
kind = "terminal"

[[node]]
name = "abandoned"
kind = "terminal"

[[edge]]
from = "implement"
on   = "done"
to   = "review"

[[edge]]
from = "implement"
on   = "fail_plan"
to   = "triage"

[[edge]]
from = "implement"
on   = "no_diff"
to   = "triage"

[[edge]]
from = "review"
on   = "reject"
to   = "implement"

[[edge]]
from = "review"
on   = "accept"
to   = "ship"

[[edge]]
from = "ship"
on   = "approve"
to   = "shipped"

[[edge]]
from = "ship"
on   = "abandon"
to   = "abandoned"

[[edge]]
from = "triage"
on   = "rebudget"
to   = "implement"

[[edge]]
from = "triage"
on   = "abandon"
to   = "abandoned"

[fallback]
to = "triage"          # per-node [node.fallback] may override

[[source]]
name          = "task_brief"
producer      = "instance"
optional      = false
trim_priority = 1

[[source]]
name          = "diff_artifact"
producer      = "node:implement"
optional      = false
trim_priority = 1

[[source]]
name          = "review_findings"
producer      = "node:review"
optional      = true                     # absent on round 1 by construction
trim_priority = 2
```

**Outcome vocabulary.** Global closed enum, two classes:

- **Graph outcomes** (edge-routed, node-declared):
  `done | no_diff | accept | reject | fail_code | fail_plan | approve |
  rebudget | abandon`.
- **System outcomes** (NEVER edge-routed; wrapper-handled per §10.2):
  `error_runner | error_transport | steered | superseded`. The validator
  **rejects** any declared edge on a system outcome. They reach the graph
  only when a cap is breached, at which point the transition is to the
  node's fallback (or the region's `on_exhausted` for round exhaustion).

An outcome a node declares but has no edge for routes to the (per-node or
global) fallback. An outcome a node does NOT declare, or an unparseable /
absent / duplicate marker, is `fail_code` (fail-closed) — never fallback
routing. `no_progress` is not an outcome: it is a wrapper-computed breaker
recorded as evidence (§10.5).

**Input binding.** At mint, each non-optional input is bound to an
immutable tuple `(producer_activation_id, artifact_ref, digest)` — the
latest CLOSED producer activation in the current region (current round
first, else most recent). A producer whose region differs from the
consumer's — including one regioned and one not — binds to its latest CLOSED
activation whatever its `round_no`: rounds are per-region counters (§10.1),
so they cannot order a foreign producer. The
binding is per-activation, and topology — not the binder — is what rules out
a producer re-running underneath a consumer mid-round: the only legal
cross-region back-edge is the human-gate `rebudget` exemption of rule 2.
Optional inputs absent on round 1 bind to nothing. Unknown source name =
hard error.

**Validator rules** (pre-instantiation + lint sweep):

1. Schema-valid, reject-unknown; exactly one `entry`; ≥1 terminal
   reachable from every node under every declared outcome and exhaustion
   path.
2. Cycle analysis runs over the EFFECTIVE transition graph (declared
   edges ∪ per-node fallback ∪ exhaustion ∪ global fallback — a
   fallback edge can close a real runtime cycle; probed, phase-1 r2).
   Exhaustion edges are modeled from a bounded-cycle region's
   `entry_node` ONLY (rounds are counted there, §10.1 — member-wide
   modeling is fail-open for reachability and fail-wrong for
   dominance; probed). Every cycle must lie within one `bounded-cycle`
   region — with exactly one exemption, encoded: a cycle EVERY
   back-edge of which is a DECLARED `rebudget` edge originating at a
   `kind = "gate"`, `gate_type = "human"` node and targeting a
   bounded-cycle region's `entry_node` (fallback-routed edges never
   qualify). No other cross-region back-edge is legal. "Back-edge" is
   graph-theoretic — an edge that closes a cycle; region declaration
   order carries ZERO semantic weight, and cross-region edges in
   acyclic flows (including from/through unregioned nodes) are legal.
   Additionally, a bounded-cycle region minus its `entry_node` must be
   acyclic — an inner cycle avoiding the entry node consumes no rounds,
   so `max_entries` would bound nothing (SCC-containment alone is
   defeatable by one edge; probed).
3. Gates and terminals: terminals have no exits; gates declare
   `gate_type`, `binds`, `outcomes`; every gate outcome is edge-covered.
4. Exactly one edge per `(from, on)`; no edges on system outcomes;
   fallback targets a gate or terminal.
5. Every `inputs` name resolves in `[[source]]`; every producer exists;
   `optional` consistent with reachability (a non-optional input whose
   producer cannot have run yet = validation error). Producibility and
   terminal-reachability run over the EFFECTIVE transition graph:
   declared edges ∪ per-node fallback ∪ region `on_exhausted` ∪ global
   fallback (declared-edges-only misses fallback bypasses — probed,
   phase-1 review). `[[source]]` fields are exactly `name`, `producer`,
   `optional`, `trim_priority` — nothing else (no `max_bytes`).
6. Every task node declares `runner`, `writes`, `outcomes`, non-empty
   `verify` (structured: `cmd`, `timeout` ≤ the node's `max_wall`,
   optional `cwd`; `cmd`/`cwd` repo-relative — a check outside the
   pinned repo cannot be provenance-hashed, §7.3), `allowed_paths`
   (entries are `<dir>/**` directory-prefix grants — no segment may
   start with `.`, so a hidden directory is never a grant — hence
   repo-relative by construction; empty ⇔ `writes = false`; a reporting
   exemption AND, with `sandbox = bwrap` (the default), the node's
   writable mount set, §6/§7.5), `token_budget`,
   `max_wall`, `stale_after`, `max_infra_retries`, `max_steers`;
   `[instance].max_total_activations` present. Acyclic regions must NOT
   declare `max_entries`/`on_exhausted`; `on_exhausted` targets a GATE
   (never a terminal — exhaustion materializes a keyed gate, §10.1/10.4);
   a region's `entry_node` is never a terminal; gates declare no
   `fallback` (their outcomes are edge-covered; a gate fallback would be
   dead config invisible to cycle analysis); every node is reachable
   from `entry` over the effective graph; every edge entering a region
   from OUTSIDE it targets that region's `entry_node` (a non-entry
   ingress would consume a round no entry-node arrival opened,
   silently shrinking `max_entries` — probed, phase-2 r3; this keeps
   §10.1's counting exact); `gate_type` is closed to `human` in v1. The wrapper executes `cmd` WITHOUT a shell (argv =
   shell-safe split, no expansion) — and the validator applies the SAME
   semantics: `shlex.split(cmd)` must succeed and be non-empty, and
   argv[0] — the provenance-hashed executable, §7.3 — must be
   repo-relative (interpreters like `bash x.sh` or `env` wrappers are
   rejected; use shebangs; later tokens are plain arguments). Validating
   with different semantics than execution was a probed bypass
   (phase-1 r3).

   *Authoring notes (learned from the validator's own fixtures):* a
   global or per-node fallback gate must not be able to route back into
   a task outside a bounded-cycle region — that closes a real runtime
   loop with no round counter and is rejected as a cycle. Inside a
   bounded-cycle region, only the `entry_node`'s artifacts may be
   non-optional inputs downstream of `on_exhausted`; other members'
   artifacts must be `optional = true` (the exhaustion path is modeled
   from `entry_node` only).
7. Warn when a judgment node's (a TASK declaring `accept`) `verify` set
   ⊆ its predecessor's — full structured comparison, one warning per
   node.
8. Version + content hash over the canonical body (below).

**Canonical body (`wf-canon-json/1`).** The pinned wire format is the
canonical JSON emission of the resolved model (sorted keys, aliases,
nulls elided) stamped `"canon": "wf-canon-json/1"`; `content_hash` =
sha256 over exactly those bytes. TOML is authoring syntax only — pinned
bytes are NEVER TOML text; reformatting the TOML does not move the hash,
any semantic edit does. The loader accepts both authored TOML and pinned
canonical JSON through the same validation pipeline. A pinned body is
accepted ONLY if the supplied bytes are byte-identical to the canonical
re-emission of the parsed document (`data == canonical_bytes(doc)`) and
the hash is computed over the supplied bytes — semantically equivalent
but non-canonical encodings (whitespace, key order, duplicates) are
rejected, never normalized (invariant 9; probed bypass, phase-1 r2).

## 3. Instance state in bd (cyclic template, acyclic trace)

A back-edge executes by **minting new beads**, never reopening old ones.
Every workflow bead: created via the typed wrapper with
`--no-inherit-labels`, carrying metadata `wf_kind = root | activation |
gate | event` and `wf_root_id = <root bead id>` (roots carry their own id)
— the discriminator + linkage every query uses.

### 3.1 Root bead (`wf_kind: root`)

Metadata: `graph_id`, `graph_version`, `graph_content_hash`, **the
canonicalized graph body** (`wf-canon-json/1` bytes per §2 rule 8 —
never TOML text; size-capped by the §11 payload probe; fallback:
a dedicated child bead or content-addressed git blob referenced by hash),
and the resolved configuration with provenance — every profile, model,
bound, isolation, each tagged `source: graph-default | role-binding |
project-config | instance-override` (instance overrides arrive as an
instantiation-time JSON validated against the schema subset;
`role-binding` is a value supplied by the foreman config's `roles` map,
which resolves a graph's `profile:<role>` runner alias to a concrete
runner and model — it ranks above a graph default and below both
project config and an instance override). The root also records its
CREATION-TIME config signature; `create_root` idempotency-by-key
compares against that signature, not the live config — a verified
rebudget mutates the live config and must never break root re-creation
recovery (probed, phase-2 r2). Minting, brief composition, input
binding, task construction, the wrapper's runtime limits and grading and
recovery all read this pinned resolution — only `allowed_paths` and
`verify`, which no resolution can express, stay the graph body's — and
the live `roles` map is consulted only at instantiation, so a role
rebound after a root exists never changes how that instance runs. The
interpreter revalidates each effective node against the §2 per-node rules
at instantiation and then executes from the pinned copy; the file is for authoring.
Hash mismatch → instance halts.

The root also carries the one fact that is written after creation:
`terminal`, the name of the terminal node routing entered, written
once when it does and never rewritten (a different terminal is
refused). The root bead is then CLOSED with reason
`outcome=terminal terminal=<name>`. It sits deliberately outside the
creation-time config signature and outside every field root
re-creation compares (`graph_content_hash`, `instance_inputs`,
`allow_test_flags`, `instance_base_commit`, the config signature), so
recording where an instance ENDED never changes its identity. A root
carrying `terminal` is SETTLED: the frontier treats it as having no
routing head, so a re-tick mints nothing, opens no dead-end halt, and
simply re-reports the terminal. Like `superseded_by`, `terminal` is a
field an OLDER binary does not know, and workflow carriers are read
`extra = "forbid"` — so an older foreman meeting a settled root fails
loud on the unknown key rather than routing an instance it cannot
tell is over. That is the intended failure, not a compatibility gap.
A settled root is also never superseded and a superseded root is never
settled: either would overwrite the other's close reason.

### 3.2 Activation beads (`wf_kind: activation`)

Minted with: `node`, `region`, `round_no`, `seq` (monotonic per-instance,
foreman-assigned — bd timestamps are second-granularity),
`predecessor_activation_id`, `idempotency_key`, bound input tuples,
`runner_profile`, `model`, an EMPTY `session_id` (the profile's
`prepare()` mints it at launch and the dispatch writes it back, §5.2),
**`intended_base_commit`** — resolved AT MINT as: the
`pre_attempt_commit` of the most recent WRITING activation at the target
node in the current region (rework edge), else the instance branch head.
Salvage (tier 2) = setting `intended_base_commit` to the rejected artifact
commit + a deviation record — expressed through a dedicated
deviation-recording API (phase 3+), NEVER as a mint parameter (mint
facts are derived; phase-2 ruling). Never derived through
`predecessor_activation_id` (on a reject edge the predecessor is the
reviewer, whose base IS the rejected commit).

Mint facts are DERIVED by the wrapper, never accepted from the caller:
`region` from the pinned graph, `round_no` and `intended_base_commit`
from recorded activations, `outcome_taken` from the recorded predecessor
close (a caller-labeled mint could dodge its cap; probed, phase-2
review). Carrier carry-forward: `pre_attempt_commit`,
`reset_verified_commit`, `pre_attempt_dirty_state` exist as optional
carrier fields from phase 2, written by the phase-3 supervisor — the
`intended_base_commit` rule consumes `pre_attempt_commit`, so it must be
recorded from the first writing activation onward.

On dispatch: the process handle (§5.3). On exit: the mirrored exit record.
On close: outcome, evidence (verify exit codes, artifact identity,
effects reconciliation, breaker flags), usage, deviations.

**Identity:** `idempotency_key = hash(root_id,
predecessor_activation_id, outcome_taken, target_node)` (entry:
`hash(root_id, "entry")`). Exactly one untransitioned head per instance;
violations fail closed to triage. **Race residue** (post-mint duplicate
despite the lock): append-only **supersede** — the loser closes
`superseded` with `superseded_by=<winner>`; winner = a COMPLETED
activation first (recorded terminal outcomes are routing truth and are
never destroyed by race residue; two completed duplicates = refuse to
triage — ruling, phase-2 r2/r3), then lowest `seq`, tie →
lexicographically lowest bead id. A supersede names a winner that
exists, shares root AND idempotency key, and wins this rule — anything
else is refused. Root convergence follows its own rule: a root that
OWNS instance beads is never superseded; converge onto the owner
regardless of bead id; both own → hard error to triage (bd ids are
unordered — probed, phase-2 r3). Superseded activations are excluded
from frontier and `round_no` counting but COUNT toward the §10.3
ceiling.

### 3.3 Transition events (`wf_kind: event`) — derived audit

Append-only `(from, outcome, to, activation_id, seq, actor)` per edge
taken. **The closed activation's outcome is the routing truth; events are
an idempotently reconstructible audit projection** — post-crash gaps are
backfilled, never corrupting. Carrier: bd event beads
(`--type event --event-payload` — native in bd 1.1.0, no config needed;
probed 2026-08-25). `--event-payload` MUST be inline JSON: the `@file`
form stores the literal string `"@file"` silently (probed). Floor: task
beads with `wf_kind: event`. Never `bd audit record` (probed lossy).

### 3.4 Gate beads (`wf_kind: gate`)

**v1 does not use native `bd gate` machinery** (its resolve/close paths
are unauthenticated and `gate create` demands blocking targets); a gate is
a plain bead whose transition happens only via
`close_gate_verified` after §9 signature verification. Deterministic gate
key from the OPENING transition: `hash(root_id, gate_node,
source_activation_id, outcome)`; exhaustion gates:
`hash(root_id, region, round_no_at_exhaustion)` — re-ticking re-finds the
same key and never re-mints (drill 6). Gate beads count toward the
instance ceiling.

Wisps: the §11 canary is the ONE permitted decision-irrelevant ephemeral
wisp. No decision-relevant datum may ever be a wisp.

## 4. Interpreter (foreman) contract

A stateless-between-ticks process run by a model. **v1 ticks are manual**;
every tick is single-flight: host `flock` on the repo path (this lock IS
the in-repo execution band, §12) + a bd-side holder record (`bd
merge-slot`; one per rig — an S1 design input).

```text
tick:
  0  flock; §11 canary (backend assertion + round-trip); verify pinned-config hash
  1  frontier from bd (reads below): open activations | open gates | last closed head
  2  open activation  → wrapper lifecycle (§5.6): exit-recorded? live? dead?
     open gate        → check for a submitted signed payload (§9); verified → take edge
     else             → edge lookup on the head's outcome (declared edge → target;
                        undeclared-but-listed → fallback)
  3  dispatchable next node → §10 pre-mint predicates → mint → dispatch (§5.2–5.3)
  4  terminal runner → §7 completion (compute, never trust)
  5  close + append transition event (backfill missing events); a route INTO
     a terminal also records `terminal` on the root and closes it (§3.1),
     which `status` reports as `terminal` + `root_state`; release lock
```

Signals are hints that may trigger a tick early; the frontier is always
recomputed from bd.

**Read vocabulary (model-issued) and wrapper write API — the command
table.** Every row pins flags; [PROBE] rows are §11 obligations. All list
reads: `--json --limit 0 --all --include-gates` (bd's default limit is
50-documented/observed-varying — never rely on it) [PROBE: `--limit 0` =
unlimited].

| Purpose | Invocation (shape) | Expect | On failure |
|---|---|---|---|
| Load roots | `bd list --json --limit 0 --metadata-field wf_kind=root` [PROBE: metadata filter+read-back] | id, metadata incl. pinned body | halt: carrier probe failed |
| Instance beads | `bd list --json --limit 0 --all --include-gates --metadata-field wf_root_id=<id>` | every activation/gate/event | halt |
| Idempotency lookup | same + `--metadata-field idempotency_key=<k>` (must include closed) | 0 or 1 bead | >1 → supersede rule |
| Round count | client-side over instance beads: distinct `round_no`, region-filtered, superseded excluded | int | fail-closed (count opens) |
| Ceiling count | client-side: ALL activation+gate beads of instance | int | fail-closed |
| Mint | wrapper: `bd create --type task --no-inherit-labels --metadata @…` (typed API only) | id | no retry without idempotency re-check |
| State/evidence/close | wrapper: `bd update --set-metadata …` / `bd close --reason <structured>` | — | halt on error |
| Event append | wrapper: `bd create --type event --event-payload @…` [PROBE: create+enumerate `-t event`] | id | floor: task bead `wf_kind=event` |
| Gate open/close | wrapper: plain bead create / close after §9 verify | — | unverified close attempt → refuse + audit flag |

**Two-iteration-layers ruling.** The graph's review loop replaces the
execution engine's internal fix loop; node-internal iteration is red-green
only. Session resume is legal only for transport failure and steer
continuations.

## 5. Dispatch lifecycle (crash-atomic)

### 5.1 States

`minted → dispatched → exit-recorded → evidence-recorded → closed`
(plus `superseded`). Each change is one typed-wrapper write; writes are
idempotent (re-applying a recorded state is a no-op).

### 5.2 Two-phase activation

Phase A: mint (state `minted`), with idempotency key, bound inputs and
`intended_base_commit` — but NO session id. Phase B: launch via the
supervisor wrapper; state `dispatched` only after the handle is durable,
and the **pre-assigned session id** (from the profile's `prepare()` —
never discovered from output) is written onto the activation by that same
transition. **Fork barrier:** the wrapper commits the launch receipt (atomic
write: temp + rename) BEFORE the child may exec; the child blocks on the
barrier until the receipt exists. An exec is also one appended line in the
activation's **exec ledger** (append-only file in the wrapper dir; drill
evidence for exactly-once).

### 5.3 Supervisor wrapper (deterministic, per activation)

One wrapper process per activation, alive for the child's lifetime.
Records in the handle (bd + wrapper dir): `{pid, pgid, host,
host_boot_id, proc_start_time, started_at, log_path, session_id}` — boot
id + start time defeat PID reuse and host reboots. Captures the runner's
machine event stream (`claude -p --output-format stream-json`,
`codex exec --json`, opencode equivalent) to `log_path`. **Owns runtime
enforcement** (this answers "who polls" under manual ticks): raises a
stale flag (file + bd metadata) when `stale_after` passes with no new
event, and TERMs the group (exit reason `stale`) if one further
`stale_after` passes with no new event; TERMs the group on `max_wall`
breach; on child exit writes
the exit file `{exit_code, ended_at, reason}` AND **mirrors the exit
record into bd as its final act** (state `exit-recorded`). The on-disk
exit file is thereafter a crash-window fallback: a missing file with a
bd exit record is still
`exit-recorded`.

### 5.4 Worktree precondition

Before exec, the wrapper asserts `HEAD == intended_base_commit` and a
clean tree in the activation's worktree — performing the idempotent reset
itself if needed — and records `reset_verified_commit`. A precondition
survives crashes; a trailing cleanup does not. (In-repo: §12.)

**Worktree record** (per instance band): path
`.wf/<root_id>/worktree`, branch `wf/<root_id>`, owner = current
activation, expected HEAD = its `intended_base_commit`; created by the
wrapper at first dispatch, removed at terminal. A `writes = false` node
(the reviewer) gets a read-only checkout at the reviewed commit; its
outputs go to `$WF_ARTIFACT_DIR`.

### 5.5 Back-edge failure handling (tier-2 default)

Default: the rejected attempt's tree state is abandoned (next dispatch's
precondition resets to the recorded `intended_base_commit`); the lesson
crosses as data — (a) intra-session failure (`fail_code`/`fail_plan` from
the node's own runner): dying-session bounded note, deterministic
fallback note if it cannot; (b) cross-node rejection: **the reviewer's
findings artifact IS the note** (source `review_findings`). Salvage
override per §3.2.

### 5.6 Recovery classification (liveness-proving)

Open activation found at tick:

1. bd exit record (or exit file) present → `exit-recorded`; proceed to §7.
2. Neither, and the process is alive (pgid + matching boot id/start time)
   → running; wrapper flags govern (§8.2).
3. Neither, process provably dead (or identity mismatch) → TERM the group
   (idempotent), close `error_transport` with `evidence:
   exit_unobserved`; fresh attempt subject to §10.2 caps. If the wrapper
   finds a commit ahead of `intended_base_commit` with no ref, it
   **pins it first** (orphan-pin fallback), preserving evidence. No edge
   ever advances on a partial artifact.

## 6. Runner floor

Profiles (claude, codex, opencode) implement:

```text
Profile:
  name()
  prepare(activation) -> session_id
  build_command(task, session_id)
  launch(cmd, launcher) -> handle          # via supervisor wrapper
  collect_terminal_envelope(handle) -> {usage, session_id, duration}
  build_resume_command(session_id, instructions, task)
  build_resume_hint(session_id)            # human-pasteable; recorded on gate beads
  parse_output(stream) -> Event{type, text, session, usage?, cost?, is_error}
```

Rules: danger defaults inverted — sandboxed/read-only unless the node
declares `writes = true` (repo worktree only); unsupported option = loud
error; usage normalization owned here (`usage: unknown` is legal telemetry).
The supervisor owns process identity, liveness and death proof, and enforces
`max_wall` independently of profile output.

The wrapper wraps every profile's argv in the bubblewrap mount bound
before exec: the checkout is read-only except the node's `allowed_paths`
grants, `channels/` and the git object/ref stores, which are writable,
while `config`, `hooks/`, `info/` and `refs/wf` are pinned read-only.
The wrapper-root `uv-cache` is also bound read-write so `UV_CACHE_DIR` and
`UV_PYTHON_INSTALL_DIR` never fall back to `$HOME` and activations reuse a warm tool cache.
Profiles neither opt in nor out. `sandbox = off` is an unsafe switch,
recorded on the close as `AuditFlag.SANDBOX_OFF`; a host without a
working `bwrap` refuses to dispatch — a halt, never an infra retry.

**Runner channels** (wrapper-provided env, writable regardless of
`writes`): `$WF_OUTCOME_FILE` — exactly one schema-validated outcome
marker (THE reserved channel; zero, duplicate, or unparseable →
`fail_code`); `$WF_ARTIFACT_DIR` — structured outputs (findings, notes);
`$WF_EFFECTS_FILE` — the declared-paths manifest (missing/unparseable →
fail-closed).

## 7. Completion contract (claim ≠ proof)

Computed by the foreman wrapper at `exit-recorded`:

1. **Terminal observed**: bd exit record (§5.3) — post-crash observable.
2. **Claim parsed**: the `$WF_OUTCOME_FILE` marker; it must name an
   outcome the node declares.
3. **Evidence computed**: ALL `verify` entries exit 0, executed by the
   wrapper with the declared timeout, **from a trusted pinned source** —
   the verify script content-hash is recorded at instantiation and
   checked before execution (a writing runner must not be able to edit
   its own examiner); a hash mismatch is `fail_code` + audit flag.
   Outcome-specific: `done` requires all checks; **`accept` requires all
   checks pass on the reviewed commit and reviewed identity = verified
   identity** (an anti-drift cross-check — the fixture additionally gives
   the reviewer checks the implementer does not run); `reject` requires
   the findings artifact to parse; `fail_plan`/`reject` claims are NOT
   overwritten by failing verify (a failing check on a failure claim is
   consistent evidence, recorded as-is). A check that ran to completion
   red is re-run ONCE at the same commit before it counts
   (`supervisor/verify.py` `RED_CHECK_RERUNS`); the recorded exit code is
   the last attempt's and `attempts` says how many ran. Timeouts and
   provenance refusals are never re-run. One rerun is what tells a flaky
   check from a red artifact — a check red twice at one commit is the
   artifact's problem (cr-o85.34.14, phase 6.5).
4. **Artifact identity** (honest naming): every writing attempt ends in a
   commit (else `no_diff`). Ordering: **git commit + ref first, bd write
   second — the bd write is the commit point**; ref
   `refs/wf/<root_id>/artifact/<activation_id>` pinned by the WRAPPER
   immediately post-exit, before any bd write (three sibling namespaces —
   see the §14 ref-namespace row). Identity recorded = commit OID + tree
   OID (git object ids — SHA-1 on current repos, named as such);
   sha256 digests are used only for mutable documents (§9).
5. **Effects reconciled**: observed = status/diff over
   `intended_base_commit..artifact_commit` + uncommitted/untracked;
   declared = `$WF_EFFECTS_FILE`; `allowed_paths` = paths exempt from
   undeclared-effect reporting.
   `undeclared_effect` = observed ∖ (declared ∪ allowed) → transition
   blocked (release: human gate accepting that exact artifact, or foreman
   discard + deviation record).
   **`allowed_paths` is NOT containment and never was** (ADR 0001). The
   union subtracts the runner's own manifest, so a runner may modify any
   path, declare it, and be graded `done`; no profile consumes
   `allowed_paths` as a sandbox restriction. A declared path outside the
   set raises the `effect_outside_allowed_paths` audit flag — recorded for
   an operator, blocking nothing. Enforcement is the §6 mount bound, one
   layer down: the grants ARE the writable mounts, so under
   `sandbox = bwrap` an `effect_outside_allowed_paths` flag is a
   should-never-fire regression signal rather than a routine report.
   The escalation needs a PHYSICAL write, not the flag: `.git` is mounted
   writable under the bound, so `git rm --cached` or `git update-index
   --cacheinfo` puts an out-of-grant path into the observed set (both the
   commit diff and `git status`) with nothing written outside the grant. So
   the close is `error_transport` with a retry-exempt `bound_violated`
   deviation, and it halts, ONLY when an out-of-grant path's working-tree
   state (blob of the file on disk, ABSENT counted as a state) differs from
   `intended_base_commit:<path>`; an equal state is an index-only forgery
   and stays with the ordinary effects gate above. Its working-tree digest is
   raw bytes, so a clean filter that changes bytes differs from its own stored
   blob by definition. A physical check that
   cannot be computed does not escalate — the halt is the strong claim
   (drill 28).

## 8. Supervision

### 8.1 Steer (tier 2)

Order matters: **persist steer intent** (reason, instructions digest) on
the activation → `terminate(handle)` (TERM → bounded wait → KILL; death
proven via the handle identity) → close `steered` → mint exactly one
continuation via `build_resume_command`. Steers are capped per node by
`max_steers` (separate from infra retries — guidance is not
infrastructure failure); both under the §10.3 ceiling. Guidance steers
never consume review rounds. An **infra retry descended from a
continuation is itself a continuation**: it resumes the same session with
the same steer text (read back from the steered activation's persisted
intent), and is refused rather than launched fresh if that intent is gone.
Capability facts: all three CLIs accept new instructions between turns;
none supports mid-turn input (mid-turn
supervision remains the omnigent reopen trigger).

### 8.2 Monitoring (zero model tokens in the loop)

The **supervisor wrapper** owns detection and enforcement (it is alive
while the child runs; the foreman may not be):

| Signal | Mechanism (token-free) | Enforcement |
|---|---|---|
| Alive/dead | pgid + boot id + start time; exit record | — |
| Completed | bd exit record / exit file | — |
| Activity | JSONL event count + byte growth (activity, not proof of progress) | — |
| Stale | no new event for `stale_after` | wrapper raises flag (file + bd); a second `stale_after` of silence → wrapper TERMs, exit reason `stale`, closed `error_runner` (one infra retry, as `max_wall`) |
| Runaway | `max_wall` wall-clock | wrapper TERMs, exit reason recorded |

The foreman's model reads bytes only at transitions: terminal → marker +
§7 (never the log); stale flag → last ~2KB tail, then wait / steer /
terminate (tier 2) — a bounded wait, since the wrapper itself TERMs the
group after one further `stale_after` of silence. Full-log reads are
exceptional and byte-budgeted.

## 9. Human gates (signed payloads)

A human decision is a **signed canonical payload**, not a bd state:
`{schema_version, graph_id, root_id, gate_key, outcome, artifact: {commit_oid,
tree_oid | sha256}, bound_mutation?, nonce}` — signed with a key whose
fingerprint is on an **allow-list pinned outside the workspace** (in the
validator's own configuration; not the repo, not the ambient keyring).
The wrapper verifies signature AND fingerprint equality (never just
`verify-tag` exit 0) before `close_gate_verified` takes the declared
edge. `rebudget` payloads carry the new bound; the wrapper records the
mutation ON THE GATE BEAD in the same write that closes it — bound
authority is the root's creation-time config ⊕ the mutations of the
instance's CLOSED rebudget gates (max per key). No root-config write
ever happens after create: per-bead writes cannot clobber each other,
so concurrent rebudgets both survive structurally (a root-metadata
merge was wholesale-replace and provably lost one — probed, phase-2
r3/r4), and the bound landing atomically with the close removes the
apply/close crash window outright. `bound_mutation` is legal IFF the
outcome is `rebudget`, its key must be in the closed bound-setting
vocabulary, and values are raise-only against the effective bound;
`schema_version` must equal the pinned payload version. Unsigned / wrong-hash / wrong-signer / replayed
nonce → refused. Nonce uniqueness is scoped PER ROOT (ruling, phase-2
review): the signed payload binds `root_id` and `gate_key`, so a
cross-root replay fails payload/root matching before the nonce is ever
consulted — per-root scope plus a mandatory gate-ownership check
(`gate.wf_root_id == root`) is sufficient and avoids cross-instance
scans. A gate bead closed by any other path is tampering: the
audit sweep halts the instance.

Artifact classes: `binds = "immutable"` — the payload names the commit
being approved (signature over the OID is the authority; the hash check
is a cross-check). `binds = "mutable"` — the document is committed at
gate-open; payload carries its file sha256; re-hash at close — computed
by the WRAPPER through an injected workspace-scoped artifact reader,
never accepted from the caller (a caller-echoed digest is no re-hash;
ruling, phase-2 review); mismatch or unreadable artifact →
`StaleApproval`, gate stays open, edit receipt recorded. Honesty note: a
foreman with write access to the allow-list could forge approvals — the
allow-list lives where the foreman cannot write, and the sweep audits it.
Gates wait indefinitely in v1.

## 10. Bounds — total by construction

All bounds are **pre-mint predicates** with explicit operators:

1. **Region rounds.** `round_no` increments on entry into the region's
   `entry_node` (initial + each back-edge arrival); infra/steer
   re-dispatches INHERIT the current `round_no`. Predicate: refuse a mint
   that would create a NEW round in region R when
   `distinct_round_no(R) ≥ max_entries` → materialize the exhaustion
   gate. Worked example (`max_entries = 3`): rounds 1, 2, 3 execute; the
   4th back-edge arrival exhausts.
2. **System-outcome caps.** `max_infra_retries = N` permits N additional
   attempts after the first per node per round (consecutive
   `error_runner`/`error_transport` closes, with backoff); `max_steers`
   caps steer continuations separately. Breach → the node's fallback
   edge. System outcomes never consume rounds; rounds never absorb infra
   noise; both consume the ceiling.
3. **Instance ceiling.** Refuse ANY mint (activation or gate) when
   `count(all activation + gate beads of the instance) ≥
   max_total_activations` — open, closed, superseded, unclassified all
   count (fail-closed) → halt gate. The halt gate is exempt from the
   PREDICATE it enforces (so it can be minted at the ceiling), NEVER
   from the count — every bead counts, no metadata flag may remove a
   bead from the count (ruling, phase-2 review). Halt-gate identity:
   key = `hash(root_id, halt_ordinal)` where the ordinal is the count
   of the root's existing halt gates; a NEW halt gate may be minted
   only when every prior one is CLOSED (one open at a time), so the
   exempt path stays bounded by human-verified closes — a static
   per-root key made the gate one-shot and wedged §10.4 re-entry
   (probed, phase-2 r3), a caller-shaped key made the exemption
   unbounded (probed, r2). `halt_reason` is metadata, mandatory. A
   CLOSED gate is never silently re-found as success: re-find applies
   to OPEN gates only (and must match the recorded gate's shape);
   a closed re-find is a loud conflict. No outcome class is exempt.
   The single auditable boundedness statement.
4. **Exhaust re-entry** only via a verified `rebudget` payload writing
   the raised bound with provenance. Exhaustion gates are unique by key
   (§3.4) — never re-minted by re-ticking.
5. **No-progress breaker** (wrapper-computed, evaluated when the NEXT
   attempt completes): identical artifact identity (tree OID) with the
   rejected attempt → record `breaker: no_progress` in evidence and route
   to the region's `on_exhausted` regardless of remaining rounds.
   Finding-fingerprint stability is advisory evidence for tier-2
   judgment only. Missing breaker evidence → fail-closed to triage.
6. **Audit sweep**: re-runs the validator + bound queries + gate-close
   verification over live instances; a violation **opens a halt gate on
   the instance**.

Honesty: these counts are tamper-evident under §0 — enforced against
runners by read-only bd, against the foreman by the sweep — not
"unfalsifiable".

## 11. bd probes

**Precondition probes — run BEFORE v1 code is written** (each with its
named fallback):

1. Metadata write→enumerate→read-back through `--json` (list + show) —
   the entire §3 encoding rests on it. Fallback: child beads carrying
   payloads in `description`, or a git-side sidecar indexed from bd
   (→ v0.4, not a patch).
2. Large metadata payload (≥64KB — the pinned graph body). Fallback:
   dedicated child bead or content-addressed git blob referenced by hash.
3. `bd config set types.custom event` → create + `bd list -t event`
   enumeration. Fallback: task beads with `wf_kind: event`.
4. `--limit 0` = unlimited on list/query; `--metadata-field` filtering;
   `--no-inherit-labels`; labels read-back; close-reason retrieval;
   timestamp granularity (expected: seconds — hence `seq`).

**PROBE RESULTS (2026-08-25, bd 1.1.0 @8e4e59d, isolated dolt-embedded
lab — GO for the §3 encoding, no fallback carriers needed):**

1. PASS — nested metadata survives create→`show --json`→`list --json`
   verbatim; `--metadata-field k=v` and `--has-metadata-key` filter
   correctly.
2. PASS — 70KB metadata value round-trips byte-identical.
3. PASS, better than assumed — `event` is a NATIVE issue type; the
   `types.custom` prerequisite is void (`bd config set types.custom` is
   not even a recognized key). Correction: `--event-payload` accepts
   inline JSON only — `@file` stores the literal string silently (§3.3).
4. PASS — `--limit 0` = unlimited; `--no-inherit-labels` works (default
   inherits); labels and `close_reason` read back via `--json`;
   timestamps are SECOND-granularity in read paths (`seq` stands).

Lab gotchas for the drill harness: a bd workspace nested inside another
repo's workspace leaks the outer project's beads into READ paths (writes
stay isolated) and ignores `bd init --prefix` — drill assertions must
select by `wf_root_id`, never by "all rows"; child ids are hierarchical
(`<parent>.1`). Evidence: `scratchpad/probes/phase0-results.md`.

**Startup canary (every tick):** backend assertion (`bd context` reports
the pinned dolt/embedded backend — any fallback/skew refuses dispatch
loudly) + one metadata round-trip written as an `--ephemeral --wisp-type`
canary (the one permitted wisp; TTL-compacted, no delete authority
needed).

Prior probe facts standing: `bd audit record` lossy (never use);
`bd bond`/`--ref` do not exist (relationships via `bd dep`/`bd link`).

## 12. Isolation modes

Per node, overridable per instance: `isolation = "worktree" | "in-repo"`,
default worktree. In-repo keeps all invariants minus physical isolation:
(a) the execution band = the §4 single-flight `flock` scoped to the repo
path — one active runner, ever; (b) provenance is recorded, not
inferred: at dispatch the wrapper snapshots dirty state
(`git stash create`, digest set stored as `pre_attempt_dirty_state`); at
reset, files matching the snapshot are the runner's and resettable,
anything else is human work → tier-2 confirmation required, never
auto-reset. An unresolvable dirty tree blocks the instance on a human,
by design. Every snapshot and attribution digest uses raw working-tree bytes.

## 13. v1 scope and drill suite

One graph (§2 fixture), one real small feature, Claude as first foreman,
manual ticks, direct bd seeding, human gates only, forced first rejection
via `test_force_first_reject` (schema'd; validator requires
`--allow-test-flags`).

**Drills.** Every drill names its injection point and a measurable
assertion (refusal or exact post-condition). Instrumentation: the exec
ledger (§5.2), wrapper dir artifacts, foreman transcript byte counts.

*Crash drills (injection points):*

1. After mint / before exec: restart → same idempotency key found, no
   second mint; **exec ledger `wc -l == 1`** across the whole drill.
2. After receipt durable / before child exec (fork barrier): child never
   started → ledger empty for that launch; relaunch appends exactly one.
3. After child exit / before bd exit-record mirror: exit file present →
   classified `exit-recorded` from the fallback path; work preserved.
4. After outcome close / before reset: next dispatch's precondition
   resets; rework runner observes `HEAD == intended_base_commit`, clean
   tree.
5. Mid-reset: precondition idempotent; rerun converges.
6. Gate ops: crash between gate-open and first notification, and between
   payload verification and edge-taking → re-tick converges, no duplicate
   gate (same key), no duplicate edge.

*Integrity drills (assertions are refusals):*

7. Unsigned close, wrong-hash payload, non-allow-listed signer, replayed
   nonce → each REFUSED; the verified payload passes; receipt records
   fingerprint. A gate bead force-closed out-of-band → audit sweep halts
   the instance.
8. StaleApproval (mutable): document edited after gate-open → close
   refused, edit receipt present.
9. Pinned graph: edit the TOML mid-instance (add an edge) → routing
   unchanged; corrupt the pinned body → halt on hash mismatch.
10. Single-flight race: two concurrent ticks → one mint survives, loser
    closed `superseded`, exec ledger total = 1.
11. Degraded backend: bd pointed at fallback/skewed store → dispatch
    refused loudly.
12. git/bd reconciliation: bd record naming a deleted commit → instance
    halts.
13. Verifier provenance: runner edits a verify script → hash mismatch →
    `fail_code` + audit flag, not a pass.

*Monitoring drills (the token-free property is measured, not assumed):*

14. Hung runner: alive, silent past `stale_after` → wrapper writes the
    stale flag with timestamp ≤ `stale_after + ε` of last event, **while
    the foreman process is not running**; foreman then reads ≤ 2KB
    (transcript byte count asserted) and steers; prior activation closed
    `steered`; exactly one continuation (ledger); session id identical;
    review rounds unchanged.
15. Lying completion: marker `done`, one verify fails → `fail_code`, no
    edge advance; verifier ran at the exact artifact commit (evidence
    records OID). Sub-cases: zero markers and two markers → `fail_code`,
    no fallback routing.
16. Wall-clock runaway: `max_wall` breach → wrapper TERMs; exit reason
    `max_wall`; closed `error_runner`; infra cap consumed.
17. Dead-without-exit: kill wrapper + child mid-run → case-3 recovery:
    `error_transport`, `evidence: exit_unobserved`, orphan commit pinned
    if present.
18. Malformed artifacts: truncated exit file, corrupt JSONL tail →
    recovery still classifies deterministically (fail toward case 3);
    no crash-loop.
19. TERM-resistant child: ignores TERM → KILL escalation with proof;
    ledger and handle consistent.
20. Normal completion audit: a clean `done` run → foreman transcript
    contains ZERO bytes of runner log (only marker + verify output).

*Functional drills:*

21. Bound drill: `max_entries = 1` → round 1 EXECUTES (worked example
    §10.1), the first back-edge arrival exhausts; gate unique across
    re-ticks; `rebudget` writes the raised bound with provenance;
    `abandon` reaches the terminal — and reaching ANY terminal settles the
    root: it records that terminal's name, closes, is reported by `status`,
    and makes the next tick a no-op (`tests/test_foreman_tick.py`
    `test_the_reached_terminal_settles_and_closes_the_root_and_a_re_tick_is_inert`,
    `tests/test_foreman_functional.py`
    `test_drill_25_halt_abandon_reaches_terminal`).
22. Infra isolation: broken CLI on a node → exactly
    `1 + max_infra_retries` attempts (ledger), `round_no` unchanged, no
    fallback shortcut before the cap, ceiling incremented per attempt.
23. No-progress: two attempts with distinct commits but identical tree
    OID, `max_entries = 3`, varied findings → routed to `on_exhausted`
    with `breaker: no_progress` recorded (not ordinary exhaustion —
    rounds remain).
24. Undeclared effect: runner touches a path outside declared ∪ allowed →
    transition blocked; released only by human accept or recorded
    discard.
25. Fallback + closed enum: a node-declared outcome with no edge →
    fallback gate; an outcome the node does not declare, and an
    unparseable marker → `fail_code`, no routing.
26. In-repo isolation: in-repo node with uncommitted human edits →
    auto-reset refused, tier-2 confirmation recorded, human work intact;
    runner's own dirty state (stash-snapshot-matched) resettable.
27. End-to-end: the forced-rejection feature run, killing the foreman at
    injection points 1–6 across the run; a fresh zero-context session
    completes it from bd + git + wrapper dir; final assertions: one
    activation per idempotency key, rework artifact ≠ rejected artifact
    (tree OID), reviewed identity = verified identity, every bead
    carries `wf_root_id`, ceiling arithmetic consistent.
28. Mount bound: a write outside the grant under the bound is refused
    (`EROFS`) and the exit grades `fail_code`, not absorbed
    (`tests/test_supervisor_sandbox_bound.py`
    `test_a_write_outside_the_grant_is_refused_and_grades_fail_code`); an
    out-of-grant path that somehow lands ON DISK differently from
    `intended_base_commit` is a BOUND VIOLATION, not a runner outcome →
    `error_transport` + `bound_violated`, retry-exempt, halt (same file,
    `test_an_effect_outside_the_grant_under_the_bound_halts_the_instance`;
    observer side in `tests/test_supervisor_exit.py`
    `test_an_effect_outside_allowed_paths_under_the_bound_is_a_bound_violation`
    and its `sandbox = off` pair). The same path forged through the index
    alone — `git rm --cached`, `git update-index --cacheinfo`, both legal
    inside an intact bound because `.git` is writable — is NOT a violation:
    the flag stays advisory and the §7.5 effects gate handles it (same
    file, `test_a_cached_removal_under_the_bound_is_not_a_bound_violation`
    and `test_a_cacheinfo_forgery_of_an_absent_path_is_not_a_violation`).

Out of scope for v1: second graph type, concurrent instances/merge-slots,
cost enforcement, cron tick, non-Claude foreman build, formula
materialization, agent-to-agent communication (hub-and-spoke ruling),
graph editor, live-instance version migration, non-human gate types.

## 14. Deferred (with triggers)

| Deferred | Trigger / owner |
|---|---|
| Concurrent instances: claim-lease, band scheduling, merge-slot one-per-rig | S1; LoopTroop's enforced band + aweb's ownership-vs-lease split |
| Out-of-process authority holder (owns BdClient + verifier + rebudget; typed ops become a real capability boundary) | when the threat model must cover adversarial in-process callers (§0.3) |
| Salvage / deviation-recording API (tier-2 intended_base override) | phase 3+; §3.2 |
| Closed resolved-config key vocabulary (beyond the 4 bound keys) | when configs are graph-resolved (phase 5) |
| Human-gate timeout policy | after v1 gate experience |
| Formula materialization | after loop-schema verification on pinned bd |
| Cost enforcement (usage records exist from v1) | when spend constrains |
| Native bd gate types (timer/gh:run/bead) | with non-human gates |
| Engine-reopen threshold | measured after v1 |
| Plugin distribution (skill + workflows/ template via /harness-publish) | bead cr-3ss, after v1 |
| §12 band-lock siting deviation: the execution band is a `flock` on `<wrapper_root>/repo-band.lock`, NOT on the repo path §4 names — a lock inside the workspace is one a `git clean -fdx` deletes. One band per wrapper root, so two wrapper roots over one repo would not exclude each other | phase 5, when the foreman resolves wrapper roots; §4, §12 (phase-3 ruling) |
| §7.4 ref namespace deviation: the wrapper writes THREE sibling namespaces, `refs/wf/<root_id>/{artifact,orphan,prereset}/<activation_id>`, not the flat `refs/wf/<root_id>/<activation_id>` §7.4 names. Only `artifact/` is the §7.4 pin, and only `artifact/` is the §12 authority to reset HEAD off a commit; `orphan/` preserves a commit §5.6 recovery could not attribute and `prereset/` preserves what a reset was about to destroy — a flat prefix made every ref the wrapper wrote for any reason a licence to destroy its commit | phase 5, if a ref-layout consumer outside the wrapper appears; §7.4, §12 (phase-3 ruling) |
| §7.4 committer-identity attribution: a runner's commits are stamped with `GIT_COMMITTER_NAME/EMAIL` carrying the activation id (`runner+<activation_id>@workflow-interpreter.invalid`), and in-repo `pin_artifact` requires that identity in ADDITION to descent from `intended_base_commit` and declaration in `$WF_EFFECTS_FILE`. It is an attribution mechanism, not an authorization one — a runner can unset the variables; what it removes is the accident of a human's commit becoming an attempt's artifact on path containment alone. The stamp is applied in ONE place, `RunnerChannels.env()`, so a profile that builds its own child environment instead of routing through it leaves every in-repo commit unattributable — `pin_artifact` refuses, and a `done` claim on a writing node with no artifact grades `fail_code` (§7.3 clause 4) | phase 4, with the first real runner profile; §6, §7.4, §12 (phase-3 ruling) |
