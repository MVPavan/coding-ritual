---
name: performance-optimization
description: Use when the ask is optimization-shaped — "make this faster", "optimize", "X is slow", "why is this slow", "reduce latency / memory / cost", "profile this", "where is the time going", or a performance budget, SLO, or resource target to meet — for code that is correct but not fast or cheap enough. For was-fast-now-slow regressions with a culprit change to find, use systematic-debugging.
disable-model-invocation: true
---

# Performance Optimization

Turns a performance target into measured experiments with a strict disposal
rule: a change beats the baseline beyond run-to-run noise with the suite green,
or it is reverted. Unmeasured optimizations accrete complexity that never bought anything.

## Route first

- **Regression-shaped** — was fast, now slow: a culprit change exists → the
  **systematic-debugging skill** owns it (baseline, then bisect); it hands back
  here on a no-culprit bisect.
- **Optimization-shaped** — no defect, a target: faster, cheaper, smaller, a
  budget or SLO → this skill, from Step 1.
- **Neither evidence nor a stated target** → do not optimize. Name what you
  would measure and stop; speculative tuning is complexity with no payer.

## Step 1 — Baseline

No code change until a baseline exists: **one named command you have already
run**, whose invocation and numbers are recorded.

- **Fix the conditions and hold them**: data volume, cache state (cold or warm
  — pick one), concurrency, machine. A 100-row dev table hides the O(n²) that
  a production-shaped million rows expose.
- **Repeat the whole run** (5+ times); record median and spread across runs —
  the spread is what Step 4's verdict is judged against.
- **A service latency target is a percentile** (p95/p99), never a mean. One
  run of a service benchmark issues hundreds of requests and yields its own
  p95; the 5+ repeats give the spread on that p95.
- **Measure the user's number**: wall-clock of their workflow, their query,
  their bill — not a micro-benchmark nobody asked about.

Tool invocations and baseline-corrupting pitfalls: load `references/measurement-recipes.md`
before taking a baseline or running any profiler, EXPLAIN, or benchmark.

Done when the command, conditions, and numbers head the attempt ledger.

## Step 2 — Identify

Profile; never rank bottlenecks by reading code. Route by symptom:

```text
What is slow, big, or expensive?
├─ One endpoint or query path → per-request timing breakdown, then EXPLAIN
│                               ANALYZE the top queries by total time
├─ Every request              → system view before code: CPU vs I/O-wait vs
│                               memory pressure; pool/queue saturation;
│                               blocked event loop (one py-spy dump names it)
├─ A pipeline or batch job    → wall-clock per stage; profile the dominant one
├─ A CLI, script, test suite  → profile the whole run (py-spy record, cProfile)
├─ Memory grows over time     → allocation snapshots (memray, tracemalloc
│                               diff); growth-without-release is a leak,
│                               steady-high is footprint
├─ Intermittent spikes        → percentiles + correlation: GC, lock
│                               contention, external-dependency latency
└─ Renders in a browser       → references/frontend-performance.md
```

Done when one bottleneck carries a measured share of the total ("the JOIN is
70% of request time") — a number, not a hunch.

## Step 3 — Fix: one change per measurement

Fix the named bottleneck, nothing else. Three optimizations landed together
produce one unattributable number; if they must ship together, measure each in
isolation first. Common systems culprits:

| Pattern | Smell | Fix |
| --- | --- | --- |
| N+1 queries | query count scales with rows returned | join / eager-load / one `IN` batch |
| Unbounded fetch | no `LIMIT`; whole table into memory | paginate, stream, aggregate in the store |
| Missing index | seq scan on a large filtered table | index the selective column; re-EXPLAIN |
| Chatty external calls | serial awaits to one dependency | batch, or bounded-concurrency gather |
| Blocked event loop | sync I/O or heavy CPU in async path | `asyncio.to_thread`, worker offload |
| Hot-loop waste | recomputed pure results; list membership tests | hoist out of the loop; set/dict |
| Repeated identical work | same result recomputed or refetched per request | cache at the boundary, with an explicit invalidation and staleness story |

Done when exactly one named bottleneck changed and nothing else is in the diff.

## Step 4 — Verify: keep or revert

Re-measure **the way you measured the baseline** — same command, conditions,
repetition count. A cold baseline against a warm result measures the cache,
not your change. Beat the noise, not the mean: a 3% gain inside ±5% spread is
a different sample, not a gain.

| Result vs baseline | Action |
| --- | --- |
| Better beyond the spread, suite green | **Keep.** Commit with before/after numbers in the message. |
| Within noise | **Revert.** |
| Worse | **Revert.** |
| Improved, but a test went red | **Revert.** A regression wearing a win's clothing. |

**Neutral is a revert, not a keep.** The change is already written and
reverting feels wasteful — that is sunk cost. Kept code is maintained forever;
it must pay for itself in the measurement.

**Correctness gates the metric.** A win produced by dropping work the product
needed — a skipped validation, caching what must stay fresh, a removed await
that was load-bearing — is a regression, not a win.

**Attempt ledger** — one row per attempt, written as it happens, kept and
reverted alike. In-session: the task report when dispatched, else your reply.
Durable, always: verdicts land in the commit message; a multi-session effort
keeps the ledger in the bead tracking the work. Read it before proposing any
experiment — a reverted idea leaves no git trace.

| Idea | Baseline → result | Verdict | Why |
| --- | --- | --- | --- |
| Batch per-row lookups into one `IN` query | p95 480ms → 210ms | kept | query log: 41 queries/request → 2 |
| Cache config load | p95 480ms → 472ms | reverted | inside noise (±20ms) |
| Grow pool 10 → 50 | p95 480ms → 484ms | reverted | pool never saturated; wrong culprit |

Done when the keep-or-revert row is chosen and its ledger row is written.

## Step 5 — Guard

A win without a guard decays silently; the guard ships with the win.

- **Prefer counting guards over wall-clock asserts in CI** — queries issued
  per request, rows fetched, a leak-prone type's object count after N fixed
  cycles (tolerance band): deterministic on any machine. An N+1 regression
  fails a query-count assert where a timing test flakes.
- A wall-clock budget that must hold: `pytest-benchmark` saved baselines with
  a compare-fail threshold (a medium-size test per `.claude/rules/python/testing.md`).

Done when every box holds:

- [ ] Before/after numbers from the same command and conditions; delta beyond spread.
- [ ] Suite green; no test changed, skipped, or deleted to get there.
- [ ] Neutrals and losers reverted; every attempt in the ledger.
- [ ] Guard in place; ledger and new baseline durable (bead or commit message).
- [ ] Completion claims go through the **verification-before-completion skill**.

## Red flags — stop, return to the step you skipped

- A fix proposed before the baseline command exists.
- "Obviously faster" — if it is obvious, re-measuring is cheap; do it.
- Several changes inside one measurement.
- A win that required changing, skipping, or deleting a test.
- Optimizing a path no profile placed in the hot set.
- Re-running an experiment the ledger already shows reverted.

## Rationalizations

| Excuse | Reality |
| --- | --- |
| "It didn't help much, but it doesn't hurt" | Neutral is a revert. Kept code is paid for forever; this one earned nothing. |
| "Already written, may as well keep it" | Sunk cost. The measurement does not care what the change cost to write. |
| "The improvement is obvious, no need to re-measure" | Then re-measuring is cheap and proves it. Unmeasured wins are how neutral complexity lands. |
| "3% better on the mean" | Compare the delta to the spread. Inside it, that is sampling error. |
