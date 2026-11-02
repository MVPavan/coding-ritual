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

Use for measured latency, throughput, memory or cost problems: profiling, explicit resource targets, or locating a cost with no change wanted. A slowness to fix end to end is the perf-issue playbook and a sustained climb of one metric the hillclimb playbook, which call this. Skip prose optimization and speculative tuning.

**Boundary:** Handles measured resource problems: locate a cost, or profile, change and re-measure against a target, vetting the numbers on the way; a caller may bring another measurable outcome. What makes a number evidence is principle-explain-the-number. A standalone causal investigation of a failure, flaky behaviour or a regression is systematic-debugging; a live capture a caller asks for gathers evidence even from a failing process and leaves the cause to the caller's debugging call. An artifact captured earlier is trace-forensics.

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
- `ordered-cost-mantras`: For a resource metric, try candidates in a fixed order, cheapest first, from dropping unused work through keeping a result, doing it less, deferring it, moving it off the waited-on path and running it concurrently to making the operation cheaper.
- `caller-stop-condition`: Treat a candidate order as what to try next and stop on the caller's stated condition, or with none when a candidate meets the target.
- `mechanism-named-hypothesis`: Name how each candidate should move the metric, tied to the located cost.
- `single-factor-brief`: Let a delegate write one factor under a brief naming that factor, its mechanism and its owned paths, while the caller keeps the baseline and the comparison.
- `no-ceiling-without-run`: Claim no ceiling on a gain until a run has shown it.
- `caller-measurable-outcome`: Let a caller bring any named measurable outcome through the measure-and-compare steps, with resource-only advice conditional and inapplicable vetting questions marked not applicable with a reason.
- `located-cost-branch`: When a caller wants a live capture or someone asks where a resource goes and no change is wanted, run only the measure-and-locate steps and deliver the artifact, its command, the reduced finding, its location or the gap, and located or hypothesis.
- `run-evidence-answers`: Settle every vetting question with data from an actual run, never from reasoning about the code.
- `ballpark-path`: For a rough figure the user asked for, let one run do while still checking errors and that the work happened, saying it is one run, and applying the other checks only if the run looks wrong.
- `choice-never-ballpark`: Never let a measurement that chooses between options take the rough one-run path.
- `shipped-claim-first`: Before any run, write the exact result sentence you expect to publish, with its metric and dataset, and test the vetting questions against that sentence.
- `script-reading-first`: Read the measuring script before a run and note what it times, what it counts and what it leaves out.
- `machine-load-check`: Before measuring, check the load average and core count and find what is occupying a busy machine.
- `interleave-unstoppable-load`: When competing load cannot be stopped, run the compared sides in turn so the noise hits both equally, and disclose that in the report.
- `unreported-profile-run`: Profile and trace in a separate run whose numbers are never reported, because instrumentation distorts timing.
- `per-process-cpu-read`: Inspect CPU use per process when hunting a limiter.
- `runtime-profiler-read`: Use a language or system profiler when hunting a limiter.
- `io-wait-read`: Inspect I/O wait when hunting a limiter.
- `kernel-time-syscall-count`: Only when time is going to the kernel or I/O, count system calls in a separate run whose timing is never quoted.
- `load-generator-saturation`: Watch the load generator during a run, since a saturated generator means the result describes it and not the target.
- `limiter-before-dismissal`: When a change leaves the number unmoved, find the limiter before concluding the change has no value.
- `production-parity-sides`: Run every compared side as production runs it: release builds, flags and environment, batching and transactions, connection pools, cache temperature, and the same versions and data.
- `config-mismatch-comparison`: Treat a result as a comparison of configurations only on a demonstrated mismatch with what production would use or an avoidable limit, never because a side runs on defaults as such.
- `settings-limiter-untuned`: Treat a side whose limiter is a setting, such as per-row commits, a debug build or a missing index, as untuned.
- `tuned-claim-gate`: For a claim about the tuned implementation or an adoption choice, tune an untuned side and measure again before naming a winner, calling the verdict inconclusive if it cannot be tuned, while a documented comparison of deployments as they run stays a legitimate claim.
- `no-narrowing-for-adoption`: When someone is choosing what to adopt, do not cure an untuned comparison by narrowing the claim to today's as-shipped settings.
- `capacity-arithmetic`: Check throughput in bytes against disk and network capacity and operations per second times cost per operation against available cores, and read a result past a limit as having measured something else, for example a cache, a no-op or a defect.
- `share-bound-on-gain`: Bound a claimed gain by the fraction f of elapsed time the changed part takes: for 0 <= f < 1, elapsed-time reduction is at most f and the matching throughput speedup at most 1/(1-f), at f = 1 the model gives no finite speedup bound, and a reported percentage names which it is.
- `failure-count`: Count failures and non-success responses, adding the count when the measuring script has none, because fast rejections and slow timeouts both skew timing.
- `correct-output-check`: Check that a measured run's outputs are correct and not merely present.
- `comparison-run-floor`: Run each side of a comparison at least five times unless a run's cost is stated as the reason, treating the floor as no proof of significance.
- `alternated-sides`: Alternate the compared sides run by run so warmup, lazy initialization, caches and drift favour neither.
- `median-and-range-report`: Report the median and the range across a comparison's runs.
- `resolved-no-difference`: Choose before running the margin that would matter to the decision, estimate an interval for the reported difference by a method fit for the statistic and how the runs were sampled, and call it faster or slower only when the whole interval lies beyond the margin on that side, no measurable difference only when the whole interval lies inside the margin, and inconclusive otherwise, never deciding from the raw run range.
- `close-call-statistics`: When a comparison is close, test the gap with a rank-sum test or statistics the harness provides.
- `end-to-end-share`: Beside any micro result, measure the whole path a user waits on under realistic sizes and concurrency, and state the micro result as its share.
- `work-ran-check`: Prove the work happened inside the timed span and the code used its result, since lazy code, discarded results and timeouts can produce numbers for work that never happened.
- `one-verdict-first`: Open a measurement report with one verdict: slower, faster, inconclusive or no measurable difference.
- `measurement-unit`: State every reported number with its unit.
- `no-limiter-inconclusive`: Call a claimed difference inconclusive when its limiter cannot be named.
- `unchecked-run-inconclusive`: Call a verdict inconclusive when the error or work check could not be done.
- `inconclusive-names-gap`: Have an inconclusive verdict state which check or condition caused it.
- `harness-prints-counts`: Make a frozen harness emit error and work counts, which hands each keep-or-revert decision those two checks.
- `live-capture-consent-boundary`: A live capture may sample read-only a process the user named or plainly means, anything injecting code or changing it needs the user's explicit yes, a process not named stays out, and a tool needing elevated permission is a stop with what is needed.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **agent-skills:skill:skills/performance-optimization** `reference_harnesses/agent-skills/skills/performance-optimization/SKILL.md` @ 7676817
- **agent-skills:skill:skills/performance-optimization** `skills/performance-optimization/SKILL.md` @ 7676817
  - modified: drop the Core Web Vitals and browser rendering sections — out of scope with UI work removed
  - modified: keep backend, query and database optimization, the profiling method, the disposal rule and the attempt ledger
  - dropped: Core Web Vitals thresholds and frontend load-time guidance
- **agent-skills:skill:skills/performance-optimization** `skills/performance-optimization/SKILL.md` @ 7676817
- **cursor_plugins:skill:pstack/skills/principle-explain-the-number#noise-inconclusive** `pstack/skills/principle-explain-the-number/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#run-evidence-answers** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#ballpark-path** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#choice-never-ballpark** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#shipped-claim-first** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#script-reading-first** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#machine-load-check** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#interleave-unstoppable-load** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#unreported-profile-run** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#per-process-cpu-read** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#runtime-profiler-read** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#io-wait-read** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#syscall-count-read** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#load-generator-saturation** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#limiter-before-dismissal** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#production-parity-sides** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#defaults-compare-configurations** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#settings-limiter-untuned** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#tuned-before-winner** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#no-narrowing-for-adoption** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#capacity-arithmetic** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#share-bound-on-gain** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#failure-count** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#correct-output-check** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#five-run-floor** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#alternated-sides** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#median-and-range-report** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#within-variation-no-difference** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#close-call-statistics** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#end-to-end-share** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#work-ran-check** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#one-verdict-first** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#measurement-unit** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#no-limiter-inconclusive** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#untuned-side-inconclusive** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#unchecked-run-inconclusive** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#inconclusive-names-gap** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/benchmark-checklist#harness-prints-counts** `pstack/skills/benchmark-checklist/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-02` **update** (2026-11-02-batch-2:168): Final critic F4 and F6. A diagnosis reached without Runtime forensics met no consent rule, so the branch now holds the capture boundary (live-capture-consent-b…
- `2026-11-02` **adopt** (2026-11-02-batch-2:125): Completes pending 2026-11-02-batch-2:042: harness-prints-counts is written at .claude/skills/performance-optimization/references/vetting.md:33, read against it…
- `2026-11-02` **adopt** (2026-11-02-batch-2:124): Completes pending 2026-11-02-batch-2:039: inconclusive-names-gap is written at .claude/skills/performance-optimization/references/vetting.md:49, read against i…
- `2026-11-02` **adopt** (2026-11-02-batch-2:123): Completes pending 2026-11-02-batch-2:038: unchecked-run-inconclusive is written at .claude/skills/performance-optimization/references/vetting.md:48-49, read ag…
- `2026-11-02` **adopt** (2026-11-02-batch-2:122): Completes pending 2026-11-02-batch-2:037: tuned-claim-gate is written at .claude/skills/performance-optimization/references/vetting.md:26-28, read against its …
- `2026-11-02` **adopt** (2026-11-02-batch-2:121): Completes pending 2026-11-02-batch-2:036: no-limiter-inconclusive is written at .claude/skills/performance-optimization/references/vetting.md:48, .claude/skill…
- `2026-11-02` **adopt** (2026-11-02-batch-2:120): Completes pending 2026-11-02-batch-2:035: measurement-unit is written at .claude/skills/performance-optimization/references/vetting.md:40, read against its def…
- `2026-11-02` **adopt** (2026-11-02-batch-2:119): Completes pending 2026-11-02-batch-2:033: one-verdict-first is written at .claude/skills/performance-optimization/references/vetting.md:43-47, read against its…
- `2026-11-02` **adopt** (2026-11-02-batch-2:118): Completes pending 2026-11-02-batch-2:032: work-ran-check is written at .claude/skills/performance-optimization/references/vetting.md:31-32, read against its de…
- `2026-11-02` **adopt** (2026-11-02-batch-2:117): Completes pending 2026-11-02-batch-2:031: end-to-end-share is written at .claude/skills/performance-optimization/references/vetting.md:41-42, read against its …
- `2026-11-02` **adopt** (2026-11-02-batch-2:116): Completes pending 2026-11-02-batch-2:030: close-call-statistics is written at .claude/skills/performance-optimization/references/vetting.md:39-40, read against…
- `2026-11-02` **adopt** (2026-11-02-batch-2:115): Completes pending 2026-11-02-batch-2:029: resolved-no-difference is written at .claude/skills/performance-optimization/references/vetting.md:13-14, .claude/ski…
- `2026-11-02` **adopt** (2026-11-02-batch-2:114): Completes pending 2026-11-02-batch-2:028: median-and-range-report is written at .claude/skills/performance-optimization/references/vetting.md:36-37, read again…
- `2026-11-02` **adopt** (2026-11-02-batch-2:113): Completes pending 2026-11-02-batch-2:027: alternated-sides is written at .claude/skills/performance-optimization/references/vetting.md:36, read against its def…
- `2026-11-02` **adopt** (2026-11-02-batch-2:112): Completes pending 2026-11-02-batch-2:026: comparison-run-floor is written at .claude/skills/performance-optimization/references/vetting.md:34-35, read against …
- `2026-11-02` **adopt** (2026-11-02-batch-2:111): Completes pending 2026-11-02-batch-2:025: correct-output-check is written at .claude/skills/performance-optimization/references/vetting.md:30, read against its…
- `2026-11-02` **adopt** (2026-11-02-batch-2:110): Completes pending 2026-11-02-batch-2:024: failure-count is written at .claude/skills/performance-optimization/references/vetting.md:29-30, read against its def…
- `2026-11-02` **adopt** (2026-11-02-batch-2:109): Completes pending 2026-11-02-batch-2:023: share-bound-on-gain is written at .claude/skills/performance-optimization/references/vetting.md:21-22, read against i…
- `2026-11-02` **adopt** (2026-11-02-batch-2:108): Completes pending 2026-11-02-batch-2:022: capacity-arithmetic is written at .claude/skills/performance-optimization/references/vetting.md:19-20, read against i…
- `2026-11-02` **adopt** (2026-11-02-batch-2:107): Completes pending 2026-11-02-batch-2:021: no-narrowing-for-adoption is written at .claude/skills/performance-optimization/references/vetting.md:27-28, read aga…
- `2026-11-02` **adopt** (2026-11-02-batch-2:106): Completes pending 2026-11-02-batch-2:020: tuned-claim-gate is written at .claude/skills/performance-optimization/references/vetting.md:26-28, read against its …
- `2026-11-02` **adopt** (2026-11-02-batch-2:105): Completes pending 2026-11-02-batch-2:019: settings-limiter-untuned is written at .claude/skills/performance-optimization/references/vetting.md:24-25, read agai…
- `2026-11-02` **adopt** (2026-11-02-batch-2:104): Completes pending 2026-11-02-batch-2:018: config-mismatch-comparison is written at .claude/skills/performance-optimization/references/vetting.md:23-24, read ag…
- `2026-11-02` **adopt** (2026-11-02-batch-2:103): Completes pending 2026-11-02-batch-2:017: production-parity-sides is written at .claude/skills/performance-optimization/references/vetting.md:11-12, read again…
- `2026-11-02` **adopt** (2026-11-02-batch-2:102): Completes pending 2026-11-02-batch-2:016: limiter-before-dismissal is written at .claude/skills/performance-optimization/references/vetting.md:17-18, read agai…
- `2026-11-02` **adopt** (2026-11-02-batch-2:101): Completes pending 2026-11-02-batch-2:015: load-generator-saturation is written at .claude/skills/performance-optimization/references/vetting.md:17, read agains…
- `2026-11-02` **adopt** (2026-11-02-batch-2:100): Completes pending 2026-11-02-batch-2:014: kernel-time-syscall-count is written at .claude/skills/performance-optimization/references/measurement-recipes.md:74-…
- `2026-11-02` **adopt** (2026-11-02-batch-2:099): Completes pending 2026-11-02-batch-2:013: io-wait-read is written at .claude/skills/performance-optimization/references/measurement-recipes.md:40-41, read agai…
- `2026-11-02` **adopt** (2026-11-02-batch-2:098): Completes pending 2026-11-02-batch-2:012: runtime-profiler-read is written at .claude/skills/performance-optimization/references/measurement-recipes.md:21-33, …
- `2026-11-02` **adopt** (2026-11-02-batch-2:097): Completes pending 2026-11-02-batch-2:011: per-process-cpu-read is written at .claude/skills/performance-optimization/references/measurement-recipes.md:41, read…
- `2026-11-02` **adopt** (2026-11-02-batch-2:096): Completes pending 2026-11-02-batch-2:010: unreported-profile-run is written at .claude/skills/performance-optimization/references/vetting.md:15-16, read agains…
- `2026-11-02` **adopt** (2026-11-02-batch-2:095): Completes pending 2026-11-02-batch-2:008: interleave-unstoppable-load is written at .claude/skills/performance-optimization/references/vetting.md:9-10, read ag…
- `2026-11-02` **adopt** (2026-11-02-batch-2:094): Completes pending 2026-11-02-batch-2:007: machine-load-check is written at .claude/skills/performance-optimization/references/vetting.md:9, read against its de…
- `2026-11-02` **adopt** (2026-11-02-batch-2:093): Completes pending 2026-11-02-batch-2:006: script-reading-first is written at .claude/skills/performance-optimization/references/vetting.md:8, read against its …
- `2026-11-02` **adopt** (2026-11-02-batch-2:092): Completes pending 2026-11-02-batch-2:005: shipped-claim-first is written at .claude/skills/performance-optimization/references/vetting.md:7-8, read against its…
- `2026-11-02` **adopt** (2026-11-02-batch-2:091): Completes pending 2026-11-02-batch-2:004: choice-never-ballpark is written at .claude/skills/performance-optimization/SKILL.md:63, read against its definition …
- `2026-11-02` **adopt** (2026-11-02-batch-2:090): Completes pending 2026-11-02-batch-2:003: ballpark-path is written at .claude/skills/performance-optimization/SKILL.md:61-62, read against its definition (T5).
- `2026-11-02` **adopt** (2026-11-02-batch-2:089): Completes pending 2026-11-02-batch-2:001: run-evidence-answers is written at .claude/skills/performance-optimization/references/vetting.md:4-5, read against it…
- `2026-11-02` **update** (2026-11-02-batch-2:088): Batch 2: the ordered cost candidates, the stop condition, the mechanism and no-ceiling rules, the delegate's brief, a caller's measurable outcome, the ballpark…
- `2026-11-02` **adopt-merged** (2026-11-02-batch-2:043): Checkpoint at 4dd1d05 for the owner's trait rulings: 40 adopt, 1 defer, 1 reject.
- `2026-11-02` **adopt** (2026-11-02-batch-2:042) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:39.
- `2026-11-02` **adopt** (2026-11-02-batch-2:039) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:33.
- `2026-11-02` **adopt** (2026-11-02-batch-2:038) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:33.
- `2026-11-02` **adopt** (2026-11-02-batch-2:037) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md, into `tuned-claim-gate`. Upstream: SKILL.md:33.
- `2026-11-02` **adopt** (2026-11-02-batch-2:036) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:33.
- `2026-11-02` **adopt** (2026-11-02-batch-2:035) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:32.
- `2026-11-02` **adopt** (2026-11-02-batch-2:033) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:31.
- `2026-11-02` **adopt** (2026-11-02-batch-2:032) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:27.
- `2026-11-02` **adopt** (2026-11-02-batch-2:031) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:26.
- `2026-11-02` **adopt** (2026-11-02-batch-2:030) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:25.
- `2026-11-02` **adopt** (2026-11-02-batch-2:029) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md, into `resolved-no-difference`. Upstream: SKILL.md:25.
- `2026-11-02` **adopt** (2026-11-02-batch-2:028) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:25.
- `2026-11-02` **adopt** (2026-11-02-batch-2:027) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:25.
- `2026-11-02` **adopt** (2026-11-02-batch-2:026) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md, into `comparison-run-floor`. Upstream: SKILL.md:25.
- `2026-11-02` **adopt** (2026-11-02-batch-2:025) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:24.
- `2026-11-02` **adopt** (2026-11-02-batch-2:024) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:24.
- `2026-11-02` **adopt** (2026-11-02-batch-2:023) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:23, 26.
- `2026-11-02` **adopt** (2026-11-02-batch-2:022) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:23.
- `2026-11-02` **adopt** (2026-11-02-batch-2:021) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:22.
- `2026-11-02` **adopt** (2026-11-02-batch-2:020) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md, into `tuned-claim-gate`. Upstream: SKILL.md:22.
- `2026-11-02` **adopt** (2026-11-02-batch-2:019) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:22.
- `2026-11-02` **adopt** (2026-11-02-batch-2:018) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md, into `config-mismatch-comparison`. Upstream: SKILL.md:22.
- `2026-11-02` **adopt** (2026-11-02-batch-2:017) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:22.
- `2026-11-02` **adopt** (2026-11-02-batch-2:016) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:21.
- `2026-11-02` **adopt** (2026-11-02-batch-2:015) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:21.
- `2026-11-02` **adopt** (2026-11-02-batch-2:014) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/measurement-recipes.md, into `kernel-time-syscall-count`. Upstream: SKILL.md:21.
- `2026-11-02` **adopt** (2026-11-02-batch-2:013) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/measurement-recipes.md. Upstream: SKILL.md:21. Already there: .claude/skills/performance…
- `2026-11-02` **adopt** (2026-11-02-batch-2:012) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/measurement-recipes.md. Upstream: SKILL.md:21. Already there: .claude/skills/performance…
- `2026-11-02` **adopt** (2026-11-02-batch-2:011) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/measurement-recipes.md. Upstream: SKILL.md:21. Already there: .claude/skills/performance…
- `2026-11-02` **adopt** (2026-11-02-batch-2:010) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:21.
- `2026-11-02` **adopt** (2026-11-02-batch-2:008) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:17.
- `2026-11-02` **adopt** (2026-11-02-batch-2:007) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:17.
- `2026-11-02` **adopt** (2026-11-02-batch-2:006) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:16.
- `2026-11-02` **adopt** (2026-11-02-batch-2:005) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:15.
- `2026-11-02` **adopt** (2026-11-02-batch-2:004) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, SKILL.md. Upstream: SKILL.md:11.
- `2026-11-02` **adopt** (2026-11-02-batch-2:003) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, SKILL.md. Upstream: SKILL.md:11.
- `2026-11-02` **adopt** (2026-11-02-batch-2:001) *(superseded)*: Owner ruling 2026-11-02: Lands in performance-optimization, references/vetting.md. Upstream: SKILL.md:9.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:038): Checkpoint at 4dd1d05 for the owner's trait rulings: 6 adopt.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:033): Lands as covered. Ours treats a result within noise as inconclusive.
- `2026-10-31` **update** (2026-10-31-mvp-mode:008): Restates 2026-10-31-mvp-mode:005 with durable evidence (critic K2). Bug-fix pilot: a regression whose cause is the main question routes to the bug-fix playbook…
- `2026-10-31` **update** (2026-10-31-mvp-mode:005) *(superseded)*: Bug-fix pilot: a regression whose cause is the main question routes to the bug-fix playbook (through mvp-mode at top level, to the parent from a delegated task…
- `2026-08-14` **adopt** (2026-10-14-migration:129): Adopted 2026-08-14 per user ruling, superseding the 2026-07-15 deferral and modifying casebook round-002's drop-the-frontend trim: spine is generic systems-eng…
- `2026-08-11` **adopt** (2026-10-14-migration:085) *(superseded)*: STAYS ADOPTED — scope-trimmed, not dropped. It covers frontend, backend, queries and databases; only the frontend portion is out of scope. Its load-bearing con…
- `2026-08-11` **adopt** (2026-10-14-migration:053) *(superseded)*: The only skill with a disposal rule for unsuccessful work ('neutral is a revert') and an attempt ledger. Both members rejected folding it into the debugger.
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-01-upstream-cursor_plugins-4dd1d05-batch-2.md](../../reviews/2026-11-01-upstream-cursor_plugins-4dd1d05-batch-2.md)
- [skill-comparisons/debugging-loop](../../../archive/skill-comparisons/debugging-loop/)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `alternated-sides`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#alternated-sides` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `ballpark-path`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#ballpark-path` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `capacity-arithmetic`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#capacity-arithmetic` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `choice-never-ballpark`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#choice-never-ballpark` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `close-call-statistics`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#close-call-statistics` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `comparison-run-floor`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#five-run-floor` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `config-mismatch-comparison`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#defaults-compare-configurations` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `correct-output-check`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#correct-output-check` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `end-to-end-share`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#end-to-end-share` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `failure-count`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#failure-count` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `harness-prints-counts`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#harness-prints-counts` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `inconclusive-names-gap`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#inconclusive-names-gap` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `interleave-unstoppable-load`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#interleave-unstoppable-load` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `io-wait-read`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#io-wait-read` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `kernel-time-syscall-count`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#syscall-count-read` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `limiter-before-dismissal`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#limiter-before-dismissal` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `load-generator-saturation`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#load-generator-saturation` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `machine-load-check`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#machine-load-check` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `measurement-unit`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#measurement-unit` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `median-and-range-report`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#median-and-range-report` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `no-limiter-inconclusive`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#no-limiter-inconclusive` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `no-narrowing-for-adoption`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#no-narrowing-for-adoption` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `noise-inconclusive`:
  - `cursor_plugins:skill:pstack/skills/principle-explain-the-number#noise-inconclusive` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `one-verdict-first`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#one-verdict-first` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `per-process-cpu-read`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#per-process-cpu-read` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `production-parity-sides`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#production-parity-sides` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `resolved-no-difference`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#within-variation-no-difference` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `run-evidence-answers`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#run-evidence-answers` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `runtime-profiler-read`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#runtime-profiler-read` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `script-reading-first`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#script-reading-first` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `settings-limiter-untuned`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#settings-limiter-untuned` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `share-bound-on-gain`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#share-bound-on-gain` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `shipped-claim-first`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#shipped-claim-first` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `tuned-claim-gate`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#tuned-before-winner` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#untuned-side-inconclusive` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `unchecked-run-inconclusive`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#unchecked-run-inconclusive` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `unreported-profile-run`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#unreported-profile-run` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `work-ran-check`:
  - `cursor_plugins:skill:pstack/skills/benchmark-checklist#work-ran-check` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
