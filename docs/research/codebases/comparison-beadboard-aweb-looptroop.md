# Comparison: beadboard / aweb / looptroop — what to take, what to avoid

> Consolidated two-reviewer assessment, 2026-08-24. Members: GPT-5.6-sol (high, codex CLI) and Opus 5 (medium, subagent), blind to each other, over the three Luna-xhigh maps (per-repo capabilities.md); consolidated by the coordinator. Raw member reports + probe details: scratchpad/research/three-repos/ (session-local). Framing: usefulness judged against each repo's own ceiling, for comparison against omnigent (../omnigent/00-index.md) and the workflow-graph design (bead cr-o85).

Method note: Opus ran live probes against the pinned bd v1.1.0; Sol was
static-only. Where a probe and a reading conflicted, the probe won; where
both read source, the coordinator re-read the disputed lines before ruling.

## Platform verdicts (unanimous — treat as settled)

| Repo | Verdict | One-line reason |
|---|---|---|
| BeadBoard | **Reject as platform** (Sol: defer ≈ same posture) | bd console + Pi-only in-process launcher; completion = "model stopped talking"; coordination write path provably lossy |
| aweb | **Reject/defer as platform; steal protocol semantics** | Mature communication substrate at a layer we deliberately haven't opened; zero process-graph capability; 4-service footprint |
| LoopTroop | **Reject as platform; adopt mechanisms** | The only real workflow engine of the three — and its graph is compiled TypeScript, its state SQLite, its beads a private JSONL, its runtime OpenCode-only: all four violate settled premises |

Both reviewers independently reaffirmed, from three fresh data points, the two
pillars of our design: (1) state-machine-as-**data** (LoopTroop's 571-line
hand-written XState machine is the strongest empirical argument for it — the
one repo that needed a graph paid for it in unversionable code); (2) **bd as
sole durable state** (LoopTroop's SQLite spine and aweb's Postgres are exactly
the second-authority shape we rejected).

## Fact conflicts — ruled

1. **BeadBoard reservation release bug (map gap #6).** Opus: confirmed defect
   (raw stored vs normalized query at `:446`). Sol: stale claim — release
   normalizes. **Ruling: Sol, verified by coordinator** — both create paths
   persist `scope: normalizedScope` (`agent-reservations.ts:388,404`), so the
   `:446` exact match is consistent for anything current code wrote; only
   legacy un-normalized records would leak until TTL. Opus's adjacent finding
   stands untouched: acquisition checks exact scope match only — parent/child
   path overlap is never enforced (`:353`; `classifyOverlap` is called only by
   the read-side incursion projection).
2. **BeadBoard coord.v1 — steal or condemn.** Sol: steal the typed envelope
   schema (SEND/READ/ACK/HANDOFF + projections) with fixes. Opus [PROBE]:
   `bd audit record` silently drops `data`, `version`, caller `timestamp` and
   `actor` (closed schema, exit 0, no warning) — the entire subsystem is
   non-functional on bd v1.1.0. **Ruling: both, at different layers.** The
   envelope *vocabulary* (typed events, stable ids, append-only, projections
   not mutable inboxes) is good design and consistent with our transition-event
   plan. The *carrier* BeadBoard chose is broken. If we ever carry coordination
   events in bd, the surviving channel Opus verified is `bd create --type event
   --event-payload` (round-trips), never `bd audit record`.
3. **LoopTroop restart durability of council intermediates.** Map + Sol:
   intermediates lost, ticket errors. Opus: `tryRecoverPhaseIntermediate`
   rehydrates persisted `<pipeline>_drafts` artifacts; only a crash mid-draft
   loses data (`helpers.ts:2178-2240`, checked before the error path at
   `runner.ts:336-365`). **Ruling: Opus** — cited the recovery code path the
   others stopped short of. Corrected statement: completed council rounds
   survive restart; mid-draft crashes do not.
4. **LoopTroop retry reset — steal or avoid.** Sol avoids ("destructive
   `git reset --hard` + `clean -fd`"); Opus steals it as the physical
   realization of "cyclic template, acyclic trace". **Ruling: not actually in
   conflict — adopt with Sol's scoping.** The mechanism (pre-attempt commit →
   hard reset preserving the state dir → bounded dying-session note →
   fresh session) is correct *inside a runner-owned isolated worktree*; it is
   never applied to a shared working tree. Sol's other caveats absorbed: no
   auto-push, no conditional `--no-verify` (LoopTroop does both — avoid).

Both reviewers converged, unprompted, on the same correction to the map's
biggest overstatement: LoopTroop's per-bead "gates" (`tests/lint/typecheck/
qualitative`) are **self-reported strings**, not executed checks
(`completionChecker.ts:38-46`); real commands run only in the later final-test
phase. Treat as settled.

## Merged steal list (deduped, ranked; "smallest durable pattern" per item)

**Adopt into the cr-o85 spec now:**

1. **Approve-what-you-read human gates** [LoopTroop; both reviewers' #1].
   Human-gate close carries the sha256 of the artifact the human read; the
   interpreter refuses the transition on hash mismatch; an approval receipt
   (actor, time, artifact, hash) lands on the gate bead. Sol adds: edit
   receipts with before/after hashes + explicit downstream-invalidation
   decision. Closes a real hole: nothing in our design stopped an agent
   editing a plan between human read and human approve.
2. **Bounded attempt envelope / rollback-code-carry-lesson** [LoopTroop; both].
   Activation bead records pre-attempt commit; on a reject/fail edge inside a
   runner-owned worktree: hard-reset to it (preserving the state dir), require
   the failing session to emit a bounded structured failure note (deterministic
   fallback so it is never optional), abandon the session, next attempt =
   fresh bead + fresh context + the note. Makes "acyclic trace" physical: the
   repo returns to a known state and exactly one bounded artifact crosses the
   context boundary.
3. **aweb `Provider` interface as the runner-floor shape** [Opus #3; Sol names
   the boundary, not the interface]. Six methods (`Name/BuildCommand/
   BuildResumeCommand/BuildResumeHint/ParseOutput/SessionID`) → one normalized
   Event. Copy verbatim: human-facing resume-hint (natural human-gate reattach
   artifact) and reject-on-unsupported-option (loud capability mismatch).
   Amend before use: invert the danger default (aweb defaults to
   `--dangerously-*`), and budget the usage/cost normalization aweb skipped
   (its Codex parser extracts no usage/cost — our open question 3 is NOT
   solved by this donor).
4. **Per-node context allowlist** [LoopTroop; both]. `inputs = [...]` on each
   node in the graph TOML, enforced at prompt assembly, unknown source = hard
   error; ordered trim priority under token budget (fix Sol's noted trimmer
   weakness — LoopTroop's can exceed budget). Anti-collusion: the reviewer
   node never sees the implementer's reasoning, only the artifact.
5. **Resolved-config pinning with provenance** [LoopTroop → extends Sol's
   definition-pinning from our prior consolidation]. At instantiation, write
   every resolved setting (bounds, runner, model set) into the root bead with
   its source layer, so "why did this run use 5 rounds?" is answerable.

**Earmarked for later phases (not v1):**

6. **Wake-as-hint protocol** [aweb; Sol's #2]: signal carries ids only → fetch
   exact durable record → durably mark delivery *before* ack ("a failed
   delivery mark must not become an acknowledgment") → reconcile from durable
   state on reconnect. Re-home onto bd when the communication layer opens.
   Opus ranked it out of v1 correctly: no cross-process effects yet.
7. **Task-ownership vs resource-lease separation** [aweb]: ownership never
   expires by age; only leases expire (acquire/renew/release TTL). Feeds the
   deferred concurrent-tick/claim-lease question (prior OQ6).
8. **Execution-band mutual exclusion** [LoopTroop]: coarse-and-enforced beats
   fine-and-advisory (BeadBoard's reservations are the anti-example); scope
   the exclusion to the band that touches the working tree — planning runs
   concurrently. The starting shape for concurrent features when we open it.
9. **bd event beads for transition records** [BeadBoard usage + Opus probe]:
   `bd create --type event --event-payload` round-trips; `--ephemeral
   --wisp-type` for tick/heartbeat noise. Candidate answer to spec OQ1
   (activation/transition record encoding) — verify on pinned bd first.
10. **bd→graph operator projection** [BeadBoard; Sol]: blocker-direction
    normalization + missing-target/duplicate diagnostics as a read-only
    visualizer, later. Do NOT reuse its cycle detector as a validator (mixes
    relationship types).
11. **Recovery taxonomy** [LoopTroop]: sessions classified
    `reconnected / preserved-unverified / abandoned` at startup — "unverified"
    prevents false completion after a crash. Fold into the interpreter's
    crash-drill behavior.
12. **Declare-then-verify file effects** [LoopTroop]: node declares touched
    paths; interpreter diffs the worktree and reconciles, `undeclared_fallback`
    for surprises. General shape: agent claim = hypothesis, repo = ground truth.

## Merged avoid list (what these repos prove goes wrong)

1. Completion by prose or by self-report: BeadBoard's `agent_end` and
   LoopTroop's self-asserted gates. Our rule (both reviewers, same words):
   the structured marker is the agent's **claim**; the interpreter must
   compute at least one independent clause (exit code, artifact hash, diff)
   before writing the outcome.
2. Schema'd state on a lossy carrier: never put structured state into a bd
   surface that accepts-and-drops unknown fields. bd's extension surfaces are
   lossy-by-default in two subsystems now (formula top-level fields; audit
   records). Spec obligation: write-then-read-back probe for every bd field
   the graph relies on + a validator startup canary round-trip.
3. Workflow as compiled code (LoopTroop) or as prose playbooks (aweb) — the
   two failure poles our data-graph position was built to avoid.
4. Second durable authority next to bd (LoopTroop SQLite/XState + fake beads;
   aweb native tasks — "a strictly weaker bd"); silent Dolt→JSONL read
   fallback with no staleness signal (a foreman must refuse to dispatch on
   fallback state, loudly).
5. Unaudited bound sprawl + multiplied iteration layers: six independent
   counters (LoopTroop defaults) with no single boundedness statement; 5×10
   worst-case provider attempts per bead. Live demonstration of our
   two-iteration-layers hazard — ratify the "graph loop replaces task-engine
   fix loop" ruling in the spec. Also: council voters vote on slates that
   include their own draft — if we council-critique, exclude the author's
   ballot; danger-bypass flags as opt-out defaults; ADRs describing
   architecture that was never built (BeadBoard's host daemon).

## If only three mechanisms total (judge's pick from both lists)

1. Hash-bound approval + receipts (both reviewers' #1 — unanimous).
2. Bounded attempt envelope with worktree rollback + carried note (on both
   lists; the physical half of our core invariant).
3. aweb Provider interface (Opus) over aweb wake-protocol (Sol) for the
   **v1** slot — the runner floor is the next thing we build and has no
   specified shape; the wake protocol is earmarked for the communication
   layer, which v1 deliberately does not open. Sol's pick is not rejected,
   just re-sequenced.

## Layer verdicts vs omnigent and our design

- Content/UI layer: BeadBoard = marginal donor (projection, event beads).
- Process-graph layer: LoopTroop = the only donor, and the near-substitute
  that fails on all four settled premises; aweb & BeadBoard irrelevant.
- Runner floor: aweb Provider = the donor; omnigent remains the
  buy-don't-build option if mid-turn interactivity triggers reopen;
  LoopTroop (OpenCode-lock) and BeadBoard (Pi-lock) are anti-examples.
- Communication layer: aweb = the platform answer *when we need one*
  (reopen: multi-machine coordination, cross-org identity, >3 vendors);
  until then its protocol semantics only.
- Nobody among the four (incl. omnigent) has a validated
  workflow-graph-as-data. That slot stays ours to build.

## Actions fed into the queue

1. cr-o85 spec: incorporate steal items 1–5 as spec sections; add the bd
   round-trip-probe obligation (avoid item 2) to the validator requirements;
   record ruled facts (self-reported gates; council-round durability).
2. Ledger entries (adopt/reject/defer per repo + reopen triggers) via
   `gap.py ledger add` — pending, alongside the still-pending omnigent entry.
3. Runner floor v1: start from the aweb Provider shape with the two
   amendments (danger default inverted; usage/cost normalization owned).
