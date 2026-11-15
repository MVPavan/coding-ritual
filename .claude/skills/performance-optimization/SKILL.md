---
name: performance-optimization
description: "Use for measured latency, throughput, memory or cost problems: profiling, explicit resource targets, or locating a cost with no change wanted. A slowness to fix end to end is the perf-issue playbook and a sustained climb of one metric the hillclimb playbook, which call this. Skip prose optimization and speculative tuning."
---

# Performance Optimization

Improve a named outcome with comparable evidence. Prose shortening and
ordinary cleanup are outside this skill. A newly introduced regression whose
cause is the main question is a bug. To fix it, route to the bug-fix playbook:
at top level return to `mvp-mode`; inside a delegated task, report that route to
the parent. For the diagnosis alone, use `systematic-debugging`.
A caller may bring any named measurable outcome through steps 1-5. The cost order
in step 4 and the recipes apply to a resource metric; a vetting question that
cannot apply is marked `n/a` with its reason.

1. Define the relevant metric, workload and target. If unclear, propose the
   measurement or ask about the consequential tradeoff before tuning code.
2. Capture a baseline with representative data, cache state, concurrency and
   environment. Repeat enough to estimate variability for the decision; use
   percentiles when the service target concerns tail latency. Record the command,
   conditions and results rather than assuming a fixed repeat count proves significance.
   Vet the baseline, and each later number you act on, as the vetting branch says.
3. Locate the material cost using existing measurements, focused instrumentation
   or profiling. Code inspection can suggest candidates; measurements determine
   whether they matter. Use `references/measurement-recipes.md` for unfamiliar
   tools and `references/frontend-performance.md` for browser performance.
4. For a resource metric, try candidates in this order, cheapest first: (1) drop
   work whose result nothing uses; (2) keep a result rather than recompute it; (3)
   do the work less often; (4) defer it; (5) move it off the path someone waits on;
   (6) run it concurrently; (7) make the operation itself cheaper.
   This order says what to try next, not when to stop. Stop on the stop condition
   your caller states; with none, when a candidate meets the target from step 1.
   Name how each candidate should move the metric, tied to the located cost, and
   claim no ceiling on a gain until a run has shown it.
   Change one attributable factor where practical. For an inseparable set, explain
   the coupling. Preserve required semantics, freshness, safety and accessibility.
   A delegate may write the one factor if its brief names that factor, its mechanism
   and its owned paths; the caller keeps the baseline and the comparison.
5. Compare under the same conditions and run applicable correctness checks. Keep
   changes whose benefit justifies their complexity; remove only your ineffective
   experimental edits, preserving other work. A result within noise is inconclusive,
   not evidence of a speedup. Record cost/latency/memory tradeoffs explicitly.
   A comparison on another surface than the baseline's is no pass. Until the stop
   condition holds, return to step 4 with the next candidate.

Keep a compact attempt record with baseline → result, decision and reason so failed
experiments are not repeated after context recovery. Persist it in the task/report
when the work needs handoff, not as an extra artifact for every tiny experiment.
When your caller keeps a decision trail, that trail is the record.

For a material recurring risk, add an economical regression guard: query counts,
bounded allocations or a controlled benchmark, using existing tooling. Scale its
cost to the risk; avoid flaky wall-clock assertions and unnecessary frameworks.
Report measured outcomes, applicable checks and limits. Performance improvement
does not excuse a correctness regression or authorize unrelated edits.

**Vetting.** Before you report, compare, freeze or act on a number (before and after, regression
claim, harness to freeze, choice between options), follow `references/vetting.md`; it is part of
this work, with no exit of its own. A rough figure the user asked for: one run will do. Count
errors, confirm the work happened, say it was one run, and vet further only if the run looks
wrong. A number that picks between options never takes that path. A diagnosis-only one does.

**Diagnosis only.** A caller wants a live capture, or someone asks where a resource cost goes, and
no change is wanted. Asked alone, this is for a cost with no failure: the cause of a failure stays
`systematic-debugging`. A caller's capture may be of a failing process (hung, leaking): gather the
evidence, name no cause, and leave the cause to the caller's whole debugging call. A named
process, or one the user plainly means, grants read-only sampling. Anything that injects code or
changes the process (memray attach, instrumentation, restart, kill) needs the user's explicit yes.
A process not named stays out. A tool needing elevated permission is a stop with what is needed,
never a reason to elevate. Run steps 1-3: step 1 names the symptom, not a target; step 2 captures
a real artifact, not a repeated baseline, by the recipes' live capture section. Steps 4 and 5 and
the regression guard do not run. Deliver the artifact path, the capture command, the reduced
finding (hot frame, retainer chain, stuck wait), its file, symbol and line or the gap, and
`located` or `hypothesis`. A missing tool or symbol, or a browser surface, stays a stated gap.
