# Vetting a number

Load condition: `SKILL.md`'s vetting branch fired. `principle-explain-the-number` says what
makes a number evidence; apply it by name. This is the procedure around it. Settle every
question from a run's data, never from reading the code.

- **Before the runs.** First write the claim to publish, metric and dataset in; questions
  test it. Read the measuring script: what it times, counts and skips.
- Check `uptime` and `nproc`; on a busy machine, find what is running. Load you cannot
  stop: interleave the sides and say so in the report.
- Run each side as production does: release build, flags and env, batching and
  transactions, pools, cache temperature, same versions and data.
- Choose a margin before running: what would matter to the decision, not the principle's
  noise floor.
- **What bounds it.** Profile during a separate run on the same workload; quote none of
  its timings (reads: `measurement-recipes.md`).
- A saturated load generator is what you measured, so watch it too. Number unmoved: find
  what bounds it before calling the change useless.
- Arithmetic: bytes/s against disk and network, ops/s times cost per op against cores.
  Past a limit, it measured a cache, a no-op or a defect.
- For 0 <= f < 1, removing fraction f of elapsed time cuts it at most f and speeds
  throughput at most 1/(1-f); say which a percentage is.
- Defaults alone prove nothing: it compares configurations only on a shown production
  mismatch or an avoidable limit. Limited by a setting (per-row commits, debug build,
  missing index): untuned.
- Claiming the tuned implementation or guiding an adoption: tune that side and re-measure
  before a winner, else inconclusive. Then narrowing the claim to today's settings cures
  nothing. A documented comparison of deployments as they run is a legitimate claim.
- **Did the work happen.** Count failures and non-success responses, adding a count if
  absent. Check outputs are right, not only there.
- Prove the work happened in the timed span and its result got used: lazy code, discarded
  results and timeouts give numbers for nothing.
- A frozen harness reports error and work counts for each keep-or-undo.
- **Repeats and the verdict.** A comparison takes at least 5 runs a side unless a run's
  cost is the stated reason; a floor proves no significance.
- Alternate the sides (ABAB) so warmup, caches and drift favour neither. Report median and
  range; range describes runs, so never decide from it.
- Estimate an interval for the reported difference by a method fit for the statistic and
  how the runs were sampled. Close call: rank-sum or harness statistics support; the
  interval decides. Give every reported number its unit.
- Beside a micro result, measure the whole path a user waits on at realistic sizes and
  concurrency; give the micro result as its share.
- Open with one verdict: faster or slower only if the whole interval lies beyond the
  margin on that side; no measurable difference only if wholly inside it, which
  establishes equivalence; else inconclusive, like noise.
- A result within noise (`SKILL.md` step 5) is unresolved, never equivalence: an interval
  that crosses the margin is inconclusive.
- A reported difference with no named limiter is inconclusive. So is a run whose error or
  work check could not run. An inconclusive verdict names what caused it. A simplification
  kept for its own sake claims no speedup and needs none.
