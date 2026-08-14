# Debugging Loop — Level 3 Components

Column keys:

| Key | Skill | Root |
|---|---|---|
| `SP` | superpowers — `systematic-debugging` | `reference_harnesses/superpowers/skills/systematic-debugging/` |
| `MP` | mattpocock_skills — `diagnosing-bugs` | `reference_harnesses/mattpocock_skills/skills/engineering/diagnosing-bugs/` |
| `AER` | agent-skills — `debugging-and-error-recovery` | `reference_harnesses/agent-skills/skills/debugging-and-error-recovery/` |
| `PERF` | agent-skills — `performance-optimization` | `reference_harnesses/agent-skills/skills/performance-optimization/` |
| `OURS` | ours (installed) — `systematic-debugging` | `.claude/skills/systematic-debugging/` |

Citations are relative to each skill's root unless prefixed with a repo path.
`PERF` is an adjacent capability, not a debugging-loop substitute; its rows are
grouped at the bottom of the matrix. `MP`'s `agents/openai.yaml` is excluded
(harness plumbing, per comparison scope).

## Component inventory

### `SP` — superpowers `systematic-debugging`

| Component | Citation |
|---|---|
| Iron Law: no fixes without root-cause investigation first | `SKILL.md:14-22` |
| Scope list: tests, production bugs, unexpected behavior, **performance problems**, build failures, integration issues | `SKILL.md:24-31` |
| "Use ESPECIALLY when" pressure conditions + don't-skip list | `SKILL.md:32-42` |
| Hard phase gating — complete each phase before the next | `SKILL.md:44-46` |
| P1: read error messages completely (stack traces, line numbers, codes) | `SKILL.md:52-57` |
| P1: reproduce consistently; not reproducible → gather data, don't guess | `SKILL.md:58-62` |
| P1: check recent changes (git diff, new deps, config, environment) | `SKILL.md:63-68` |
| P1: multi-component boundary instrumentation — log data in/out of every boundary, run once, then localise; worked 4-layer example | `SKILL.md:70-106` |
| P1: trace data flow to origin (pointer to tracing asset) | `SKILL.md:108-118` |
| P2: find working examples in the same codebase | `SKILL.md:122-126` |
| P2: read reference implementations completely — no skimming | `SKILL.md:128-131` |
| P2: list every difference; "that can't matter" ban | `SKILL.md:133-136` |
| P2: dependency/assumption audit | `SKILL.md:137-141` |
| P3: single written hypothesis, "I think X is the root cause because Y" | `SKILL.md:145-150` |
| P3: smallest possible test, one variable at a time | `SKILL.md:152-155` |
| P3: verify before continuing; failed → new hypothesis, never stack fixes | `SKILL.md:157-160` |
| P3: honesty rule — say "I don't understand X", ask, research | `SKILL.md:162-166` |
| P4: failing test case before the fix; links `superpowers:test-driven-development` | `SKILL.md:170-177` |
| P4: single fix, no "while I'm here" improvements | `SKILL.md:179-182` |
| P4: verify fix; links `superpowers:verification-before-completion` | `SKILL.md:184-189` |
| P4: fix counter — < 3 back to Phase 1, ≥ 3 stop | `SKILL.md:191-196` |
| Architecture escalation at 3+ failed fixes: pattern indicators, question fundamentals, discuss with human before more fixes | `SKILL.md:198-212` |
| Red-flags list — 11 rationalizing thoughts, each → STOP, return to Phase 1 | `SKILL.md:214-231` |
| Human-partner redirection signals table ("Is that not happening?", "Stop guessing") | `SKILL.md:233-242` |
| Rationalization table, 8 rows (emergency, simple issue, multiple fixes, …) | `SKILL.md:244-255` |
| Quick-reference phase/success-criteria table | `SKILL.md:257-264` |
| Environmental no-root-cause escape hatch + "95% of 'no root cause' is incomplete investigation" | `SKILL.md:266-275` |
| Backward-trace principle: fix at source, never at symptom | `root-cause-tracing.md:5-8`, `root-cause-tracing.md:154` |
| When-to-trace decision flowchart (dot) | `root-cause-tracing.md:11-31` |
| 5-step trace process with worked chain (empty `projectDir`) | `root-cause-tracing.md:32-64` |
| Stack-capture instrumentation (`new Error().stack` + context fields) | `root-cause-tracing.md:66-90` |
| `console.error`-not-logger rule in tests | `root-cause-tracing.md:85`, `root-cause-tracing.md:158` |
| Grep-capture workflow for debug output | `root-cause-tracing.md:87-95` |
| Trace-until-source loop digraph ending "Bug impossible" | `root-cause-tracing.md:130-154` |
| Defense-in-depth: validate at every layer, make the bug structurally impossible | `defense-in-depth.md:1-8` |
| Layer taxonomy: entry validation / business logic / environment guards / debug forensics | `defense-in-depth.md:22-85` |
| 4-step application incl. bypass-testing each layer | `defense-in-depth.md:87-94` |
| "All four layers were necessary" worked result | `defense-in-depth.md:96-122` |
| Wait-for-condition-not-duration principle + when-not (real timing behavior) | `condition-based-waiting.md:1-32` |
| Before/after pattern + quick-pattern table | `condition-based-waiting.md:34-57` |
| Generic `waitFor` implementation + 3 common mistakes (poll rate, no timeout, stale reads) | `condition-based-waiting.md:58-93` |
| Justified-timeout requirements: condition first, known timing, documented why | `condition-based-waiting.md:95-107` |
| Domain helpers `waitForEvent` / `waitForEventCount` / `waitForEventMatch` + real before/after | `condition-based-waiting-example.ts:20-158` |
| Test-pollution bisection: run test files one-by-one, halt at first polluter, print investigation commands | `find-polluter.sh:38-67` |
| Pre-existing-pollution skip guard | `find-polluter.sh:41-46` |
| Portability limit: `npm test` hardcoded | `find-polluter.sh:51` |
| *Meta (maintainer-facing, not runtime):* bulletproofing design log — ALWAYS/NEVER language, redundancy, anti-pattern friction | `CREATION-LOG.md:34-55`, `CREATION-LOG.md:100-103` |
| *Meta:* 4 subagent validation runs, all passed | `CREATION-LOG.md:55-75` |
| *Meta:* recall fixture + 3 pressure fixtures (emergency $15k/min; sunk-cost exhaustion; authority/social) | `test-academic.md:1-14`, `test-pressure-1.md:1-58`, `test-pressure-2.md:1-68`, `test-pressure-3.md:1-69` |

### `MP` — mattpocock `diagnosing-bugs`

| Component | Citation |
|---|---|
| Trigger includes "slow" — performance regressions in scope | `SKILL.md:3` |
| "Skip phases only when explicitly justified" sizing valve | `SKILL.md:8` |
| Orientation step: read `CONTEXT.md`, check area ADRs | `SKILL.md:10` |
| Secret redaction: `<REDACTED>`, env-var loops, quote only signal lines; ask user if redacted output insufficient | `SKILL.md:12-16` |
| "**This is the skill**" framing — the loop is the deliverable; disproportionate effort; "refuse to give up" | `SKILL.md:20-22` |
| 10-method loop-construction catalog, ordered: failing test, curl, CLI+fixture diff, headless browser, trace replay, throwaway harness, property/fuzz, bisection harness (`git bisect run`), differential run, HITL last resort | `SKILL.md:26-35` |
| "Build the right feedback loop, and the bug is 90% fixed" | `SKILL.md:37` |
| Loop tightening: faster / sharper signal / more deterministic; 2-second-deterministic bar | `SKILL.md:39-47` |
| Non-deterministic bugs → raise reproduction rate (100×, parallelise, stress, inject sleeps); "50%-flake … debuggable; 1% is not" | `SKILL.md:49-51` |
| Cannot-build-loop stop protocol: say so, list attempts, request env access / redacted artifact / instrumentation permission; **no hypothesising without a loop** | `SKILL.md:53-55` |
| Phase-1 exit criterion: one named command, already run, invocation + output shown; 4-checkbox bar — red-capable, deterministic, fast, agent-runnable | `SKILL.md:57-64` |
| Anti-anchoring tripwire: building a theory before the command exists → stop | `SKILL.md:66` |
| Phase-2 confirmation: the **user's** exact failure mode (wrong bug = wrong fix), reproducibility, symptom captured | `SKILL.md:70-76` |
| Minimisation: cut one element at a time, re-run per cut; done when every remaining element is load-bearing | `SKILL.md:78-86` |
| 3–5 **ranked** hypotheses before testing any; single-hypothesis generation anchors | `SKILL.md:90` |
| Falsifiability: mandatory prediction format; no prediction → "a vibe — discard or sharpen" | `SKILL.md:92-96` |
| Non-blocking user checkpoint on the ranked list | `SKILL.md:98` |
| Probe↔prediction mapping; one variable at a time | `SKILL.md:102` |
| Tool ladder: debugger/REPL > targeted boundary logs > never "log everything and grep" | `SKILL.md:104-108` |
| Tagged debug prefixes (`[DEBUG-a4f2]`) — cleanup becomes one grep | `SKILL.md:110` |
| Perf branch: logs are wrong for perf; baseline measurement then bisect; measure first, fix second | `SKILL.md:112` |
| Regression-test **seam gate**: test before fix only at a correct seam; shallow seam = false confidence; absent seam = the finding, flagged onward | `SKILL.md:116-120` |
| 5-step fix sequence: minimised repro → failing test → watch fail → fix → watch pass → re-run original un-minimised loop | `SKILL.md:122-128` |
| Phase-6 done checklist: repro gone, regression test or documented seam absence, grep out `[DEBUG-…]`, delete prototypes, correct hypothesis in commit/PR message | `SKILL.md:132-138` |
| Prevention post-mortem → `/improve-codebase-architecture` handoff, deliberately **after** the fix | `SKILL.md:140` |
| HITL repro script: `step`/`capture` helpers, KEY=VALUE output parsed by the agent; capture observations, leave sign-in as a step | `scripts/hitl-loop.template.sh:20-44`, `scripts/hitl-loop.template.sh:15-16` |

### `AER` — agent-skills `debugging-and-error-recovery`

| Component | Citation |
|---|---|
| Stop-the-Line rule: STOP / PRESERVE / DIAGNOSE / FIX / GUARD / RESUME | `SKILL.md:21-32` |
| "Don't push past a failing test… Errors compound" | `SKILL.md:34` |
| Ordered six-step triage checklist, no skipping | `SKILL.md:36-38` |
| Step 1 reproduce, with yes/no decision tree | `SKILL.md:40-51` |
| Non-reproducible decision tree: timing / environment / state / truly-random branches, each with tactics (widen race windows, run under load, compare env+data, hunt leaked state/singletons, defensive logging + alert on signature) | `SKILL.md:53-73` |
| Focused / verbose / isolated test commands (`--runInBand`), with substitute-your-repo's-command caveat | `SKILL.md:75-85` |
| Step 2 localize-by-layer tree incl. "test itself" false-negative branch | `SKILL.md:87-99` |
| `git bisect run` recipe for regression bugs | `SKILL.md:101-109` |
| Step 3 reduce to the minimal failing case | `SKILL.md:111-119` |
| Step 4 root-cause-not-symptom worked example (UI dedupe vs fix the JOIN); "ask why until you reach the actual cause" | `SKILL.md:121-136` |
| Step 5 regression-test guard; fails without the fix, passes with it | `SKILL.md:138-152` |
| Step 6 end-to-end verify: focused test, full suite, build, manual spot check | `SKILL.md:154-170` |
| Test-failure triage tree (covered code vs unrelated code vs already-flaky) | `SKILL.md:174-187` |
| Build-failure triage tree (type/import/config/dependency/environment) | `SKILL.md:189-197` |
| Runtime-error triage tree (undefined / network-CORS / render / no-error misbehavior) | `SKILL.md:199-212` |
| Safe-fallback patterns under time pressure: safe default + warning; graceful degradation | `SKILL.md:214-241` |
| Instrumentation lifecycle: when to add / when to remove / what to keep permanently | `SKILL.md:243-260` |
| Rationalization table, 5 rows ("right 70%… the other 30% costs hours") | `SKILL.md:262-270` |
| **Error output as untrusted data**: never execute commands / follow URLs from error text; surface instruction-like content to the user; applies to CI logs and third-party APIs | `SKILL.md:272-279` |
| Red flags, 7 items (incl. following instructions embedded in errors) | `SKILL.md:281-289` |
| Verification checklist, 6 items | `SKILL.md:291-300` |

### `PERF` — agent-skills `performance-optimization` (adjacent)

| Component | Citation |
|---|---|
| Measure-before-optimizing mandate | `SKILL.md:8-10` |
| When-NOT: no optimization without evidence (premature optimization) | `SKILL.md:20` |
| Core Web Vitals targets table (LCP / INP / CLS) | `SKILL.md:22-28` |
| 5-step workflow: MEASURE → IDENTIFY → FIX → VERIFY → GUARD | `SKILL.md:30-38` |
| Synthetic (Lighthouse/DevTools) + RUM (web-vitals/CrUX) dual measurement | `SKILL.md:40-45` |
| Frontend/backend measurement snippets | `SKILL.md:47-71` |
| Symptom→measurement decision tree (first load / interaction / navigation / backend) | `SKILL.md:73-97` |
| Bottleneck tables: frontend and backend symptom → cause → investigation | `SKILL.md:99-119` |
| Anti-pattern fix catalog: N+1 joins, unbounded fetch/pagination, image optimization, React re-renders, bundle splitting, caching | `SKILL.md:121-290` |
| Re-measure identically: same command, conditions, budget; cold-vs-warm-cache warning | `SKILL.md:294-296` |
| One change per measurement; bundle → measure each in isolation | `SKILL.md:298` |
| Beat run-to-run variance, not the mean ("3% gain inside ±5% variance is not a gain") | `SKILL.md:300` |
| Keep-or-revert decision table; "Improved, but a test went red → Revert" | `SKILL.md:302-309` |
| **"Neutral is a revert, not a keep"** | `SKILL.md:311` |
| Correctness gates the metric (a win by dropping needed work is a regression) | `SKILL.md:313` |
| Attempt ledger — log kept **and reverted** attempts (PR section or `PERF.md`) so dead ideas stay dead | `SKILL.md:315-325` |
| Performance budgets + CI enforcement (`bundlesize`, `lhci`) | `SKILL.md:327-347` |
| Rationalization table, 8 rows (sunk cost, "didn't help but doesn't hurt") | `SKILL.md:355-366` |
| Red flags, 12 items | `SKILL.md:368-380` |
| Verification checklist, 11 items | `SKILL.md:382-396` |
| Repo-shared checklist: TTFB diagnosis, frontend/backend checklists, INP field-data workflow, measurement commands, anti-pattern table | `SKILL.md:352` → `reference_harnesses/agent-skills/references/performance-checklist.md:22-153` |

### `OURS` — installed `systematic-debugging`

| Component | Citation |
|---|---|
| Trigger: bugs, failing tests, broken integrations, confusing behavior, **before proposing fixes** | `SKILL.md:3` |
| Core mandate: "Do not guess. Find the root cause first." | `SKILL.md:8` |
| Step 1: reproduce + capture the exact symptom | `SKILL.md:12` |
| Step 2: read error output, stack trace, recent changes | `SKILL.md:13` |
| Step 3: narrow the failing boundary by comparing working vs broken paths | `SKILL.md:14` |
| Step 4: one root-cause hypothesis at a time | `SKILL.md:15` |
| Step 5: smallest change or diagnostic that can **falsify** the hypothesis | `SKILL.md:16` |
| Step 6: proving test + fix only after the cause is credible | `SKILL.md:17` |
| Step 7: re-run verification; confirm the original symptom is gone | `SKILL.md:18` |
| No stacked guesses or bundled fixes | `SKILL.md:22` |
| Failed hypothesis → stop, form a new one from the evidence | `SKILL.md:23` |
| Codex-as-falsifier escalation: cross-system issues or one failed hypothesis | `SKILL.md:24` |
| Harness mount: execution engine routes unexpected test failures here | `.claude/skills/execution/SKILL.md:45` |
| Harness mount: `BLOCKED` worker status routes here before re-dispatch | `.claude/skills/execution/references/task-engine.md:92` |
| Harness mount: repeated light-path verification failure routes here | `.claude/skills/execution/references/task-engine.md:106` |
| Harness mount: workstream-mode test failure routes here; failing twice → stop and report | `.claude/skills/execution/references/workstream-mode.md:73` |
| Delegated proving-test mechanics: TDD skill owns seams + RED discipline ("bug fixes needing proof") | `.claude/skills/test-driven-development/SKILL.md:3`, `.claude/skills/test-driven-development/SKILL.md:38-54` |

## Cross-skill matrix

`✓` present · `~` variant (differs in mechanism or strength) · `—` absent.
`PERF`-native rows are grouped at the bottom.

| Component | SP | MP | AER | PERF | OURS |
|---|---|---|---|---|---|
| Root-cause-before-fix gate | ✓ `SKILL.md:14-22` | ~ `SKILL.md:55,66` (gate on loop artifact) | ✓ `SKILL.md:21-34,121-136` | — | ~ `SKILL.md:8,17` (judgment gate) |
| Phase/step sequencing with no-skip gating | ✓ `SKILL.md:44-46` | ✓ `SKILL.md:8,66,86` | ✓ `SKILL.md:38` | ~ `SKILL.md:30-38` (workflow, no gate) | ~ `SKILL.md:10-18` (numbered, ungated) |
| Reproduce-first requirement | ✓ `SKILL.md:58-62` | ✓ `SKILL.md:68-76` | ✓ `SKILL.md:40-51` | ~ `SKILL.md:33` (baseline instead) | ✓ `SKILL.md:12` |
| Feedback loop as built artifact (construction catalog + tightening) | — | ✓ `SKILL.md:20-51` | — | — | — |
| Checkable phase-exit criterion (named command, already run, red-capable) | — | ✓ `SKILL.md:57-64` | — | — | — |
| Cannot-reproduce stop protocol (ask user for env/artifact/permission) | ~ `SKILL.md:62` (gather more data) | ✓ `SKILL.md:53-55` | ~ `SKILL.md:50-51` (document + monitor) | — | — |
| Repro minimisation | ~ `SKILL.md:173-174` (at test time) | ✓ `SKILL.md:78-86` | ✓ `SKILL.md:111-119` | — | — |
| Hypothesis protocol | ~ `SKILL.md:145-150` (single) | ✓ `SKILL.md:90-96` (3–5 ranked) | — | — | ~ `SKILL.md:15` (one at a time) |
| Falsifiability requirement on hypotheses | ~ `SKILL.md:149` (causal statement) | ✓ `SKILL.md:92-96` (prediction format) | — | — | ~ `SKILL.md:16` (falsifying probe) |
| One-variable-at-a-time testing | ✓ `SKILL.md:152-155` | ✓ `SKILL.md:102` | ~ `SKILL.md:288` (red flag only) | ✓ `SKILL.md:298` | ✓ `SKILL.md:16` |
| Failed-hypothesis protocol (stop, re-derive, never stack) | ✓ `SKILL.md:157-160` | ~ `SKILL.md:90,102` (next ranked) | — | — | ✓ `SKILL.md:22-23` |
| Escalation after repeated failure → question architecture | ✓ `SKILL.md:191-212` (≥3, quantified) | ~ `SKILL.md:140` (post-fix handoff) | — | — | ~ `SKILL.md:24` (Codex after 1) |
| Cross-model falsifier escalation | — | — | — | — | ✓ `SKILL.md:24` |
| Per-boundary evidence in multi-component systems | ✓ `SKILL.md:70-106` | ~ `SKILL.md:107` (boundary logs distinguish hypotheses) | ~ `SKILL.md:87-99` (layer tree) | — | ~ `SKILL.md:14` (one line) |
| Instrumentation tool ladder (debugger > targeted logs > never log-everything) | — | ✓ `SKILL.md:104-108` | — | — | — |
| Instrumentation cleanup mechanism | — | ✓ `SKILL.md:110,136` (tag → grep) | ✓ `SKILL.md:252-260` (remove/keep rules) | — | — |
| Backward call-stack tracing to origin | ✓ `root-cause-tracing.md:32-64,130-154` | — | ~ `SKILL.md:205-207` ("where does this value come from") | — | — |
| Defense-in-depth post-fix hardening | ✓ `defense-in-depth.md:22-94` | — | — | — | — |
| Regression test before fix | ✓ `SKILL.md:170-177` | ✓ `SKILL.md:116-128` | ✓ `SKILL.md:138-152` | ~ `SKILL.md:37` (guard = monitoring/tests) | ✓ `SKILL.md:17` |
| Seam-correctness gate on the regression test | — | ✓ `SKILL.md:116-120` | — | — | ~ via TDD handoff `.claude/skills/test-driven-development/SKILL.md:38-54` |
| Test-pollution bisection (which test pollutes) | ✓ `find-polluter.sh:38-67` | — | ~ `SKILL.md:84` (`--runInBand` isolation) | — | — |
| Commit-level bisection (`git bisect`) | ~ `SKILL.md:63-68` (recent changes only) | ~ `SKILL.md:33` (harness for `bisect run`) | ✓ `SKILL.md:101-109` | — | ~ `SKILL.md:13` (recent changes only) |
| Non-reproducible/flaky-bug playbook | ~ `SKILL.md:62,266-275` | ✓ `SKILL.md:49-51` (raise the rate) | ✓ `SKILL.md:53-73` (diagnostic tree) | — | — |
| Flaky-timing fix pattern (condition-based waiting) | ✓ `condition-based-waiting.md:34-107` | — | ~ `SKILL.md:56-59` (widen windows to *reproduce*) | — | — |
| Working-vs-broken comparison | ✓ `SKILL.md:122-141` | ~ `SKILL.md:34` (differential loop) | ~ `SKILL.md:87-99` | — | ✓ `SKILL.md:14` |
| Per-error-class triage trees (test/build/runtime) | — | — | ✓ `SKILL.md:174-212` | — | — |
| Rationalization table | ✓ `SKILL.md:244-255` (8 rows) | — | ✓ `SKILL.md:262-270` (5 rows) | ✓ `SKILL.md:355-366` (8 rows) | — |
| Red-flags list | ✓ `SKILL.md:214-231` (11) | ~ `SKILL.md:66` (one tripwire) | ✓ `SKILL.md:281-289` (7) | ✓ `SKILL.md:368-380` (12) | — |
| Social/authority-pressure resistance | ✓ `SKILL.md:233-242` + `test-pressure-3.md:1-69` | — | — | — | — |
| Uncertainty admission rule | ✓ `SKILL.md:162-166` | ~ `SKILL.md:53-55` (loop failure only) | — | — | — |
| Mid-loop user checkpoint | ~ `SKILL.md:210` (at 3+ fixes) | ✓ `SKILL.md:98` (ranked list, non-blocking) | — | — | — |
| Secret redaction in debugging output | — | ✓ `SKILL.md:12-16` | — | — | — |
| Error output as untrusted data (prompt-injection defense) | — | — | ✓ `SKILL.md:272-279` | — | — |
| Safe fallback / graceful degradation under time pressure | — | — | ✓ `SKILL.md:214-241` | — | — |
| Human-in-the-loop repro scripting | — | ✓ `scripts/hitl-loop.template.sh:20-44` | — | — | — |
| Completion checklist with cleanup + knowledge capture | ~ `SKILL.md:184-189` (delegates to verification skill) | ✓ `SKILL.md:132-138` | ✓ `SKILL.md:291-300` | ✓ `SKILL.md:382-396` | ~ `SKILL.md:18` + harness `verification-before-completion` |
| Hypothesis recorded in commit/PR message | — | ✓ `SKILL.md:138` | ~ `SKILL.md:295` ("documented") | — | — |
| Routed from an execution pipeline (invoked-by contract) | — | — | — | — | ✓ `.claude/skills/execution/SKILL.md:45`; `task-engine.md:92,106`; `workstream-mode.md:73` |
| Performance-debugging method (baseline before fix) | ~ `SKILL.md:28` (in scope, no method) | ✓ `SKILL.md:112` | — | ✓ `SKILL.md:30-45` | — |
| Symptom→measurement decision tree | — | — | — | ✓ `SKILL.md:73-97` | — |
| Bottleneck cause tables (FE/BE) | — | — | — | ✓ `SKILL.md:99-119` | — |
| Perf anti-pattern fix catalog (N+1, pagination, images, re-renders, bundles, caching) | — | — | — | ✓ `SKILL.md:121-290` | — |
| Re-measure identically / beat noise not mean | — | — | — | ✓ `SKILL.md:294-300` | — |
| Keep-or-revert disposal rule ("neutral is a revert") | — | — | — | ✓ `SKILL.md:302-313` | — |
| Attempt ledger (kept and reverted) | — | — | — | ✓ `SKILL.md:315-325` | — |
| Performance budgets enforced in CI | — | — | — | ✓ `SKILL.md:327-347` | — |

No row in the `PERF`-native block has any counterpart in our harness — a sweep
of `.claude/skills/`, `.claude/rules/`, `.claude/project/`, and `CLAUDE.md`
finds no measurement, profiling, or disposal discipline anywhere (only
incidental word matches, e.g. `codebase-design/SKILL.md:16`).

## Shared-component differences

**Root-cause gate.** Four mechanisms. `SP` gates on *phase compliance* — "If
you haven't completed Phase 1, you cannot propose fixes" (`SKILL.md:20-22`) —
which is self-assessed; a model can believe Phase 1 is complete. `MP` gates on
an *artifact*: no hypothesising until a named command exists that has been
run, with its invocation and output shown (`SKILL.md:55`, `SKILL.md:57-64`) —
a transcript either contains that command or it doesn't. `AER` gates on
*sequence*: stop-the-line plus an ordered checklist (`SKILL.md:21-38`), again
self-assessed. `OURS` gates on *judgment*: "Only after the cause is credible"
(`SKILL.md:17`). `MP`'s is the strongest because it is the only gate whose
pass condition is observable from the outside; the council ruled on exactly
this axis (`harness_lifecycle/casebook/views/bucket-06.md:13`).

**Reproduction.** `SP` asks questions about the repro ("Can you trigger it
reliably?", `SKILL.md:58-62`); `AER` adds a decision tree and isolation
commands (`SKILL.md:42-51`, `SKILL.md:75-85`); `MP` makes the repro an
executable artifact that every later phase consumes — minimisation re-runs it
per cut (`SKILL.md:80`), probes run against it, the fix is verified by
re-running the original un-minimised version (`SKILL.md:128`), and cleanup
re-runs it once more (`SKILL.md:134`). `MP` strongest: reuse is what makes
the up-front cost pay off. For the *non-reproducible* sub-case the strengths
flip: `MP` raises the reproduction rate until it is debuggable
(`SKILL.md:49-51`) but never asks why it flakes; `AER`'s tree diagnoses the
flake class (timing/env/state/random) with tactics per branch
(`SKILL.md:53-73`). Operational vs diagnostic — the council absorbed `AER`'s
tree into the `MP` spine for precisely this complementarity
(`bucket-06.md:20`).

**Hypothesis protocol.** `SP` mandates a single hypothesis to prevent shotgun
fixing (`SKILL.md:145-150`); `MP` mandates 3–5 ranked hypotheses because
"single-hypothesis generation anchors on the first plausible idea"
(`SKILL.md:90`). These target different failure modes, and `MP` subsumes
`SP`'s protection: generation is plural, but testing stays one-variable-per-
probe (`SKILL.md:102`), so no shotgun. `MP` additionally demands a stated
prediction per hypothesis (`SKILL.md:92-96`) where `SP` requires only a
causal claim (`SKILL.md:149`) — a prediction is checkable before running
anything. `MP` stronger; `OURS` (`SKILL.md:15-16`) is the `SP` shape with the
falsification word but no prediction format; `AER` has no protocol at all —
its jump from localize to fix is guarded only by "ask why"
(`SKILL.md:136`).

**Escalation.** Three complementary mechanisms, not one component three ways.
`SP` counts failed fixes and circuit-breaks at 3 with named thrash indicators
and a mandatory human discussion (`SKILL.md:191-212`) — strongest *mid-loop*,
because the trigger is quantified. `MP` defers the architecture question to
the post-mortem, arguing "you have more information now than when you
started" (`SKILL.md:140`) — strongest *placement* for the recommendation, but
nothing interrupts a thrash in progress. `OURS` escalates earliest (one
failed hypothesis or a cross-system issue) to an independent model
(`SKILL.md:24`) — unique trigger and unique target, but the weakest
specification: "Codex can act as a falsifier" names no protocol for what the
falsifier receives (that lives in the harness's `use-codex` command, outside
this skill).

**Instrumentation.** `SP` is strongest at *localisation*: the per-boundary
protocol — log entry/exit at every component boundary, run once, read where
the chain breaks (`SKILL.md:70-106`) — plus stack capture at the dangerous
operation (`root-cause-tracing.md:66-90`). `MP` is strongest at *lifecycle*:
a tool ladder that prefers a breakpoint to ten logs (`SKILL.md:104-108`) and
the tag-prefix convention that makes removal a single grep, enforced by the
Phase-6 checkbox (`SKILL.md:110`, `SKILL.md:136`) — the only design in the
set where cleanup cannot be forgotten silently. `AER` is the only one that
legislates *permanent* instrumentation (error boundaries, API error logging)
as distinct from debug logging (`SKILL.md:257-260`). `OURS` has the word
"diagnostic" (`SKILL.md:16`) and nothing else.

**Minimisation.** `MP`: cut one element at a time, re-run the loop per cut,
done when every survivor is load-bearing (`SKILL.md:80-84`) — a procedure
with a testable done-condition, and the output is reused as the regression
test (`SKILL.md:82`, `SKILL.md:124`). `AER`: "remove unrelated code/config
until only the bug remains" (`SKILL.md:113-119`) — same intent, no
per-cut verification and no done-condition. `SP` minimises only at
test-writing time ("simplest possible reproduction", `SKILL.md:173-174`),
after hypothesising is already over — too late to shrink the hypothesis
space, which is the main payoff `MP` names (`SKILL.md:82`). `MP` strongest.

**Regression test.** All four debugging skills require one; the mechanisms
differ. `MP` alone gates on seam correctness — a test at a too-shallow seam
"gives false confidence", and a missing seam is itself a reportable finding
(`SKILL.md:116-120`). `SP` delegates test mechanics to its TDD skill
(`SKILL.md:177`); `OURS` does the same by composition — our TDD skill owns
seam selection (`.claude/skills/test-driven-development/SKILL.md:38-54`), so
ours reaches `MP`-grade seam discipline *only when the handoff fires*; the
debugging skill itself never says the word seam. `AER`'s inline example
(`SKILL.md:142-152`) sets the lowest bar: fails-without/passes-with, no seam
concept.

**Bisection.** Three different axes: `AER` bisects *commits*
(`git bisect run`, `SKILL.md:101-109`); `SP` bisects *test files* to find
polluters (`find-polluter.sh:38-67`); `MP` builds the harness that makes
arbitrary *states* bisectable — "boot at state X, check, repeat"
(`SKILL.md:33`). Complements, not variants of one component. Portability
differs: `AER` flags "substitute the repository's own test command"
(`SKILL.md:75-76`) where `SP`'s script hardcodes `npm test`
(`find-polluter.sh:51`).

**Pressure resistance.** `SP` fields three instruments — red flags quoting
the exact rationalizing thought (`SKILL.md:214-231`), the human-redirection
table (`SKILL.md:233-242`), and the rationalization/reality table
(`SKILL.md:244-255`) — and ships the fixtures that validated them
(`test-pressure-1.md:1-58` … `test-pressure-3.md:1-69`), with the design
rationale recorded: seeing the exact shortcut listed "creates cognitive
friction" (`CREATION-LOG.md:102`). `AER` and `PERF` each carry two tables;
`MP` carries one tripwire (`SKILL.md:66`); `OURS` carries none. `SP`
strongest by mechanism: it intercepts the thought, not just the action, and
is the only one whose resistance was adversarially tested and the tests
shipped.

**Completion/verification.** `MP`'s Phase-6 checklist is the most complete
in-skill: symptom re-verified against the original loop, instrumentation
grep-removed, prototypes deleted, and the winning hypothesis written into the
commit so the knowledge survives (`SKILL.md:132-138`). `AER` verifies
end-to-end plus suite plus build (`SKILL.md:154-170`, `SKILL.md:291-300`)
but has no cleanup teeth beyond guidance. `SP` and `OURS` both externalize
completion to a dedicated verification skill (`SKILL.md:184-189`; ours via
`verification-before-completion` and the harness's verification protocol) —
legitimate composition, but two `MP` components survive externalization as
genuine gaps in our harness: instrumentation cleanup and
hypothesis-in-commit exist nowhere on our side.

**Performance method.** `PERF` is the only full treatment; `MP`'s one
paragraph agrees with its core (baseline before fix, "measure first, fix
second", `SKILL.md:112`) and `SP` claims the territory without a method
(`SKILL.md:28`). The load-bearing, domain-neutral parts of `PERF` — identical
re-measurement (`SKILL.md:294-296`), noise-vs-mean (`SKILL.md:300`), the
keep-or-revert table with neutral-is-a-revert (`SKILL.md:302-311`),
correctness gating the metric (`SKILL.md:313`), and the attempt ledger
(`SKILL.md:315-325`) — match what the council called out when it kept the
skill scope-trimmed (`bucket-06.md:30`). None of it has a counterpart in our
harness.

**Security-boundary conduct while debugging.** Two singletons worth naming
together: `MP`'s secret redaction for everything the loop displays
(`SKILL.md:12-16`) and `AER`'s untrusted-error-output rule
(`SKILL.md:272-279`). Our harness's security skill governs *building* code at
trust boundaries, not debugging conduct — neither behavior exists on our side
today.
