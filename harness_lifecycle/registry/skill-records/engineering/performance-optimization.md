---
skill: performance-optimization
domain: engineering
stage: Building
substage: Diagnosis
secondary: []
family: performance
aliases: []
status: active
---
# performance-optimization

Use for measured latency, throughput, memory or cost problems, profiling, or explicit resource targets. Skip prose optimization and speculative tuning.

**Boundary:** Handles measured resource problems: profile, change, re-measure against a target; an unexplained failure or flaky behaviour is systematic-debugging.

<!-- registry:generated traits -->
- `define-metric`: Define the metric, workload and target first, proposing the measurement or asking about the tradeoff before tuning code.
- `baseline`: Capture a baseline measurement before attempting a performance fix.
- `representative-baseline`: Take the baseline under representative data, cache state, concurrency and environment, repeated enough to estimate variability, with percentiles for tail-latency targets and the command and conditions recorded.
- `locate-cost`: Locate the material cost with measurements, focused instrumentation or profiling, letting code inspection only suggest candidates.
- `one-factor`: Change one attributable factor where practical, explaining the coupling for an inseparable set and preserving semantics, freshness, safety and accessibility.
- `like-for-like-comparison`: Compare a performance change against its baseline under the same conditions and run the applicable correctness checks.
- `noise-inconclusive`: Treat a measured difference within noise as inconclusive rather than as a gain or a loss.
- `benefit-justifies-complexity`: Keep a performance change only when its measured benefit justifies the complexity it adds.
- `revert-ineffective-experiments`: Remove your own ineffective experimental edits, preserving all other work.
- `attempt-ledger`: Keep a compact baseline-to-result attempt record with decision and reason so failed experiments are not repeated after context recovery.
- `regression-guard`: For a material recurring risk add an economical guard — query counts, bounded allocations or a controlled benchmark — scaled to the risk and avoiding flaky wall-clock assertions.
- `measurement-recipes`: Supply backend tool mechanics for measurement — monotonic timing, sampling and allocation profilers, query plans and N+1 counting, benchmark gating, and the host and runtime view.
- `frontend-performance`: Supply browser performance mechanics — Core Web Vitals targets, synthetic plus real-user measurement, a symptom-to-measurement tree, fix patterns and budgets.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **agent-skills:skill:skills/performance-optimization** `reference_harnesses/agent-skills/skills/performance-optimization/SKILL.md` @ 7676817
- **agent-skills:skill:skills/performance-optimization** `skills/performance-optimization/SKILL.md` @ 7676817
  - modified: drop the Core Web Vitals and browser rendering sections — out of scope with UI work removed
  - modified: keep backend, query and database optimization, the profiling method, the disposal rule and the attempt ledger
  - dropped: Core Web Vitals thresholds and frontend load-time guidance
- **agent-skills:skill:skills/performance-optimization** `skills/performance-optimization/SKILL.md` @ 7676817
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-10-31` **update** (2026-10-31-mvp-mode:008): Restates 2026-10-31-mvp-mode:005 with durable evidence (critic K2). Bug-fix pilot: a regression whose cause is the main question routes to the bug-fix playbook…
- `2026-10-31` **update** (2026-10-31-mvp-mode:005) *(superseded)*: Bug-fix pilot: a regression whose cause is the main question routes to the bug-fix playbook (through mvp-mode at top level, to the parent from a delegated task…
- `2026-08-14` **adopt** (2026-10-14-migration:129): Adopted 2026-08-14 per user ruling, superseding the 2026-07-15 deferral and modifying casebook round-002's drop-the-frontend trim: spine is generic systems-eng…
- `2026-08-11` **adopt** (2026-10-14-migration:085) *(superseded)*: STAYS ADOPTED — scope-trimmed, not dropped. It covers frontend, backend, queries and databases; only the frontend portion is out of scope. Its load-bearing con…
- `2026-08-11` **adopt** (2026-10-14-migration:053) *(superseded)*: The only skill with a disposal rule for unsuccessful work ('neutral is a revert') and an attempt ledger. Both members rejected folding it into the debugger.
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [skill-comparisons/debugging-loop](../../../archive/skill-comparisons/debugging-loop/)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
