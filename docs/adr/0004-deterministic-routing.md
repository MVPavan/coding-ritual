# ADR 0004 — routing is a deterministic table lookup; the node holds the verdict

- **Status:** Accepted
- **Date:** 2026-09-03
- **Deciders:** repo owner
- **Reviewed by:** Fable 5.1 (high), GPT 5.6 (high), and the orchestrator — three independent reviews, 2026-09-03
- **Related:** ADR 0001 (`allowed_paths` is advisory); phase-6 plan `docs/plans/workflow-interpreter-phase-6.md` §0
- **Supersedes wording in:** spec §1, §4, §13 (the "the foreman is a model" text)

## Context

Phase 6 asks `feature-delivery` to run from `create` to its `ship` gate
unattended. Two things stood in the way of that, and both looked like they
wanted intelligence in the router.

1. A **computed** `fail_code` — a red verify check on an honest `done` or
   `accept` claim (`supervisor/exit.py:636-644`) — dead-ended twice: once in
   `foreman/frontier.py` `_dead_end` and once in `foreman/routing.py`
   `route()`. Both guards required the runner's *claim* to be `fail_code` as
   well as the node's declaration, so a red check always ended at a human
   halt gate, however completely the graph described what to do next.
2. A rejecting loop could only end by running out of rounds. A reviewer that
   knows the brief cannot be satisfied had no way to say so.

The proposal on the table was to put a model in the router.

## Decision

**Edge selection is a deterministic table lookup. The node that holds the
context emits the verdict; the graph decides where that verdict goes.**

1. **A computed `fail_code` routes when — and only when — the node declares
   `fail_code` and an edge carries it.** The claim is no longer part of the
   test. Declared with an edge → route; declared with no edge → the graph
   fallback (`routing.py`, unchanged); undeclared → `DEAD_END` and a halt
   gate. Both guards state the same rule, so the frontier and the router
   cannot disagree about what a head is.

2. **The verdict comes from the node with the context.** A reviewer holds the
   findings, so the reviewer emits `fail_plan`; the router never re-reads a
   diff to form an opinion. `feature-delivery` therefore declares
   `implement --fail_code--> implement`, `review --fail_code--> implement`
   and `review --fail_plan--> triage`, and gives `review` its own prior-round
   `review_findings` as an optional input.

3. **Boundedness is unchanged.** Every new edge is declared, so the bound
   proof still reads off the graph: the self-edge re-enters the region entry,
   which advances the round (`foreman/mint.py:292-338`), and `max_entries`
   caps it exactly as `review --reject--> implement` is capped.

## Rejected — a model in the router

All three reviews rejected it, and the user ruled:

- A router that obeys "declared edges only" hits **the same walls the graph
  hits**. It cannot invent a destination, so it buys nothing the table does
  not already give.
- The proposal actually hiding inside "routing needs intelligence" is
  **undeclared edges**. That deletes the boundedness proof: the reachable set
  stops being a function of the graph, so no static statement about rounds,
  ceilings or termination survives.
- "Feed the router a bounded summary" is a **model gate on every edge** —
  cost and latency on each transition, and a non-reproducible trace, in
  exchange for a decision the node above it already made with more context.

## Deferred — `gate_type = "model"`, with a trigger

A model **gate** is a different thing from a model router, and it is not
refused here. Trigger: *a graph needs a control verdict that no existing node
holds.* It is not a flag:

- It is a **second active-node lifecycle**. Gates forbid every execution
  field today (`schema/rules_nodes.py:42-81`) — no runner, verify, budget,
  wall clock, or retry policy — so a model gate needs all of that plus its
  own dispatch, grading and evidence path.
- The back-edge exemption is **human-gate only**
  (`schema/graph_index.py:145-155`); a model gate that re-enters a bounded
  cycle needs that rule lifted deliberately, not by accident.
- `route()` fails closed on gate → gate (`routing.py:101-102`), which a model
  gate sitting in front of a human gate would immediately hit.

## D4 — "the foreman is a model" (spec §1, §4, §13) is superseded

The foreman is deterministic code. The package has no LLM client and no
vendor SDK in its dependencies (`pyproject.toml`) — it shells out to runner
profiles and reads their durable evidence. The intelligence lives in the
runner nodes; routing consumes their verdicts. The spec body is not rewritten
in phase 6; this ADR is the authority until the phase-7 spec edit lands.

## D5 — phase 6 runs under ADR 0001's assumptions, deliberately

ADR 0001 defers `allowed_paths` prevention with an explicit trigger, and
`foreman run` is the first item on that list (`0001-allowed-paths-is-advisory.md:68-79`:
"automatic multi-tick execution (`foreman run`) landing"). Phase 6 lands it.

The ruling: **phase 6's first proof run executes under ADR 0001's two stated
assumptions** — a cooperative runner, and a human who reads the cumulative
diff at every gate — with writing roles on **claude**. Codex cannot be a
writer: the codex profile makes `<root>/.git` read-only including the
worktree `gitdir:` file (`tests/test_profiles_git_isolation.py:13-17`), so a
codex writer cannot commit and every `done` grades `fail_code`.

`cr-n2z` (real `allowed_paths` enforcement) is therefore **P1-blocking for
any run whose gate is not human-read**. This is a user ruling about one
supervised proof run, not an engineering claim that the gap closed.

## Consequences

- A red check is now a rework, not a human halt: the common failure of an
  unattended run is absorbed by the graph.
- `route()` no longer takes `claimed_outcome`; the claim survives in evidence
  (`Evidence.claimed_outcome`) for audit, where it belongs.
- A graph that declares `fail_code` without an edge silently falls back. That
  is existing fallback behaviour and is now the only quiet case; the loud one
  (undeclared) still halts.
- Verifier provenance remains the one verdict that overwrites *any* claim
  (`supervisor/exit.py:615-627`), including `fail_plan`.
