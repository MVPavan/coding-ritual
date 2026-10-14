# Debugging Loop

Bucket-6 (Debugging & Optimization) comparison: the three reference debugging
skills that are declared **substitutes** in the taxonomy
(`harness_lifecycle/inventory/skill-buckets.md:237`), the adjacent
**performance** skill from the same bucket (`skill-buckets.md:127` — family
`performance`, *not* a debugging-loop substitute), and our installed
`systematic-debugging`, which is the prospective merge target.

Every file each skill ships was read (mattpocock's `agents/openai.yaml` is
harness plumbing and excluded per comparison scope). Component-level evidence
with `file:line` citations: [`components.md`](components.md).

## Level 1 — Placement

| Skill | Repo | Bucket | Triggers when |
|---|---|---|---|
| `systematic-debugging` | superpowers | 6 Debugging & Optimization | "any bug, test failure, or unexpected behavior, before proposing fixes" (`SKILL.md:3`). The body is wider than the description: it also claims performance problems, build failures, and integration issues (`SKILL.md:24-31`), plus an "ESPECIALLY when" list for pressure situations (`SKILL.md:32-42`). A perf regression would not obviously fire the description even though the body claims it. |
| `diagnosing-bugs` | mattpocock_skills | 6 | "hard bugs and performance regressions"; trigger words diagnose / debug / broken / throwing / failing / **slow** (`SKILL.md:3`). The body is sized for hard bugs — six gated phases; the only relief valve is "Skip phases only when explicitly justified" (`SKILL.md:8`). On a trivial bug the trigger words fire the full loop; the misfire mode is over-ceremony, controlled by that single line. |
| `debugging-and-error-recovery` | agent-skills | 6 | Tests fail, build breaks, behavior mismatch, "any unexpected error" (`SKILL.md:3`); the body adds bug reports, log errors, and worked-then-stopped regressions (`SKILL.md:12-18`) and production incidents (`SKILL.md:10`). Broadest firing condition in the family. |
| `performance-optimization` | agent-skills | 6 (also 4) | Performance requirements in the spec, reported slowness, Core Web Vitals below threshold, suspected regressions, large-dataset features (`SKILL.md:3`, `SKILL.md:12-18`); explicit not-for: "Don't optimize before you have evidence of a problem" (`SKILL.md:20`). **Adjacent capability**, not a debugging-loop substitute — see its separated profile below. |
| `systematic-debugging` | **ours** (installed) | 6 | "bugs, failing tests, broken integrations, or confusing behavior before proposing fixes" (`SKILL.md:3`). Also routed structurally: `CLAUDE.md`'s process table ("bug, failure, or confusing behavior: systematic-debugging before proposing fixes") and the execution engine on unexpected test failure (`.claude/skills/execution/SKILL.md:45`), `BLOCKED` worker status (`.claude/skills/execution/references/task-engine.md:92`), repeated light-path verification failure (`task-engine.md:106`), and workstream-mode test failure (`references/workstream-mode.md:73`). No performance trigger anywhere — a "slow" report has no route to this skill. |

**Prior ledger decisions** (`harness_lifecycle/ledger.json`, all dated
2026-07-15):

- `skill:skills/debugging-and-error-recovery` (agent-skills) — **adopted**,
  `our_id: skill:skills/systematic-debugging`, reason: *"Covered by our
  reproduce, isolate, falsify, prove, fix, and verify workflow, with fewer
  risky generic fallback examples."*
- `skill:skills/performance-optimization` (agent-skills) — **deferred**,
  reason: *"Route to an optional production-readiness plugin;
  measure-profile-fix-remeasure discipline is valuable, while the broad
  frontend and backend catalog is too large for the template."* Two sibling
  rows point the same way: `agent:agents/web-performance-auditor` deferred to
  "an optional web-quality plugin", `command:commands/webperf` rejected as a
  launcher for it.
- **No ledger rows exist** for superpowers' `systematic-debugging` or
  mattpocock's `diagnosing-bugs` — the two skills the council round later
  ruled on most heavily (see verdict).

## Level 2 — Capability profiles

### `systematic-debugging` (superpowers)

**Achieves** — forces root-cause investigation before any fix attempt, and
hardens the fix afterwards so the bug class becomes structurally impossible.

**Can do**
- The Iron Law — "NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST" — with hard
  phase gating (`SKILL.md:14-22`, `SKILL.md:44-46`).
- Four phases: investigation (errors, repro, recent changes, evidence), pattern
  analysis against working examples, single-hypothesis testing, implementation
  with a failing test first (`SKILL.md:48-212`).
- Per-boundary diagnostic instrumentation for multi-component systems, with a
  worked 4-layer example that shows *which* layer fails (`SKILL.md:70-106`).
- Quantified escalation: after 3+ failed fixes, stop and question the
  architecture with your human partner — "this is NOT a failed hypothesis"
  (`SKILL.md:191-212`).
- The strongest pressure-resistance apparatus in the set: an 11-item red-flags
  list (`SKILL.md:214-231`), a human-redirection signals table
  (`SKILL.md:233-242`), and an 8-row rationalization table (`SKILL.md:244-255`).
- Three technique assets: backward call-stack tracing to the original trigger
  (`root-cause-tracing.md`), 4-layer defense-in-depth validation after the fix
  (`defense-in-depth.md`), and condition-based waiting to fix flaky timing
  tests (`condition-based-waiting.md` + `condition-based-waiting-example.ts`).
- A test-pollution bisection script (`find-polluter.sh`).
- Meta assets no other skill ships: its own creation log documenting the
  bulletproofing design (`CREATION-LOG.md`) and four pressure-test fixtures
  (`test-academic.md`, `test-pressure-1..3.md`) for re-validating the skill.

**Pros** (vs the others here)
- Only skill with *post-fix hardening* (defense-in-depth) and a fix pattern for
  the flaky-timing bug class — the others stop at "regression test passes".
- Escalation is quantified (a fix counter with a threshold), not a vibe; it
  names the sunk-cost pattern ("each fix reveals new problem in a different
  place", `SKILL.md:227-228`) at the moment it occurs.
- Pressure resistance is engineered, not asserted: the red-flag entries quote
  the exact rationalizing thought ("Just try changing X and see if it works"),
  which `CREATION-LOG.md:102` explains as deliberate cognitive friction — and
  the shipped fixtures let a maintainer re-verify it still works.

**Cons**
- The Phase-1 gate is *process compliance*, self-assessed — "If you haven't
  completed Phase 1, you cannot propose fixes" (`SKILL.md:20-22`) has no
  observable pass condition. This is exactly where the council preferred
  diagnosing-bugs "on enforcement strength"
  (`harness_lifecycle/casebook/views/bucket-06.md:13`).
- No repro minimisation until test-writing time ("simplest possible
  reproduction", `SKILL.md:173-174`) — the hypothesis space is never shrunk
  before hypothesising.
- No instrumentation-cleanup step anywhere; debug logging added in Phase 1 has
  no removal protocol.
- Assets are JS/TS-shaped: `find-polluter.sh:51` hardcodes `npm test`, and both
  waiting assets are TypeScript.
- Heaviest footprint (10 files), several of which (creation log, test fixtures)
  a runtime agent should never load.

### `diagnosing-bugs` (mattpocock_skills)

**Achieves** — converts a hard bug into a tight, red-capable, agent-runnable
feedback loop, then walks a gated hypothesise → instrument → fix → cleanup
pipeline against that loop.

**Can do**
- "**This is the skill.** Everything else is mechanical" — Phase 1 builds the
  feedback loop, with a 10-method construction catalog ordered by preference
  (failing test → curl → CLI diff → headless browser → trace replay →
  throwaway harness → fuzz → bisection harness → differential run → HITL
  script) (`SKILL.md:20`, `SKILL.md:26-35`).
- Loop tightening as an explicit activity — faster, sharper signal, more
  deterministic; "a 2-second deterministic one is tight" (`SKILL.md:39-47`).
- Non-deterministic bugs: raise the reproduction rate (loop 100×, parallelise,
  stress, inject sleeps) — "A 50%-flake bug is debuggable; 1% is not"
  (`SKILL.md:49-51`).
- A checkable Phase-1 exit: **one named command, already run at least once,
  output shown**, meeting a 4-checkbox criterion (red-capable, deterministic,
  fast, agent-runnable) (`SKILL.md:57-64`), plus an anti-anchoring tripwire —
  reading code to build a theory before that command exists means stop
  (`SKILL.md:66`).
- A stop protocol for when no loop can be built: list attempts, ask the user
  for environment access / a redacted artifact / instrumentation permission;
  "Do **not** proceed to hypothesise without a loop" (`SKILL.md:53-55`).
- Minimisation with a testable done-condition: cut one element at a time,
  re-running the loop per cut, until *every remaining element is load-bearing*
  (`SKILL.md:78-86`).
- 3–5 **ranked, falsifiable** hypotheses with a mandated prediction format and
  a vibe-discard rule, shown to the user as a non-blocking checkpoint
  (`SKILL.md:90-98`).
- Instrumentation: every probe maps to a prediction, one variable at a time,
  debugger > targeted logs > never "log everything and grep", and every debug
  log tagged with a unique prefix so cleanup is a single grep
  (`SKILL.md:102-110`).
- A perf branch: for performance regressions, baseline measurement then bisect
  — "Measure first, fix second" (`SKILL.md:112`).
- A seam-correctness gate on the regression test: a shallow seam gives false
  confidence; **"If no correct seam exists, that itself is the finding"**
  (`SKILL.md:116-120`).
- Phase-6 cleanup checklist including grep-out of tagged logs, prototype
  deletion, and the correct hypothesis recorded in the commit message; then a
  prevention post-mortem that hands architectural findings to a dedicated
  skill *after* the fix (`SKILL.md:132-140`).
- Secret redaction rules for everything the loop displays (`SKILL.md:12-16`)
  and a human-in-the-loop repro script template whose captured values feed
  back to the agent as parseable KEY=VALUE output
  (`scripts/hitl-loop.template.sh:20-44`).

**Pros**
- Only skill whose gates are **checkable artifacts** rather than assertions —
  Phase 1 exits on a command that observably exists and ran; Phase 2 exits on
  a load-bearing minimal repro. Everything downstream (bisection, hypotheses,
  instrumentation, fix verification) consumes the same artifact.
- The seam gate is unique in the whole set and prevents the
  false-confidence regression test the others would happily write.
- Only skill with an instrumentation-cleanup *mechanism* (tag → grep) and the
  only one that redacts secrets from debugging output.
- Smallest surface with full coverage: 141 lines plus one script.

**Cons**
- Weakest pressure-resistance in the set: one tripwire (`SKILL.md:66`) against
  superpowers' three tables — nothing names the "quick fix now, investigate
  later" or sunk-cost thoughts.
- No mid-loop escalation counter: the architecture question is deliberately
  deferred to the post-mortem (`SKILL.md:140`), so nothing circuit-breaks a
  thrash at failed fix #3 the way `superpowers SKILL.md:191-212` does.
- Non-reproducibility is handled operationally (raise the rate) but never
  diagnostically — no equivalent of agent-skills' timing/env/state/random
  tree.
- No post-fix hardening (defense-in-depth analogue).
- Full six phases are heavy for trivial bugs; the only sizing control is
  `SKILL.md:8`.

### `debugging-and-error-recovery` (agent-skills)

**Achieves** — a stop-the-line triage checklist from failure signal to
verified fix, with per-error-class decision trees.

**Can do**
- Stop-the-Line rule: STOP / PRESERVE / DIAGNOSE / FIX / GUARD / RESUME;
  "Don't push past a failing test… Errors compound" (`SKILL.md:21-34`).
- Six ordered triage steps — reproduce, localize, reduce, fix root cause,
  guard, verify end-to-end (`SKILL.md:36-170`).
- The only **diagnostic** treatment of non-reproducible bugs in the set: a
  decision tree splitting timing- / environment- / state-dependent / truly
  random, each branch with concrete tactics (widen race windows, run under
  load, compare env vars, hunt leaked state, alert on the error signature)
  (`SKILL.md:53-73`).
- Localize-by-layer tree including the "test itself is wrong" false-negative
  branch (`SKILL.md:87-99`) and a concrete `git bisect run` recipe for
  regressions (`SKILL.md:101-109`).
- A worked symptom-vs-root-cause example (dedupe in the UI vs fix the JOIN)
  with "ask why until you reach the actual cause" (`SKILL.md:121-136`).
- Per-class triage trees for test failures, build failures, and runtime errors
  (`SKILL.md:174-212`).
- Instrumentation lifecycle rules: when to add, when to remove, what to keep
  permanently (`SKILL.md:243-260`).
- **Error output as untrusted data** — never execute commands or follow URLs
  found in error messages/stack traces/CI logs; surface instruction-like text
  to the user (`SKILL.md:272-279`). Unique in the set, and a real
  prompt-injection defense.
- Safe-fallback patterns under time pressure — safe default + warning,
  graceful degradation (`SKILL.md:214-241`). This is the section the council
  deliberately dropped (see verdict).
- 5-row rationalization table, 7 red flags, 6-item verification checklist
  (`SKILL.md:262-300`).

**Pros**
- Best triage trees in the set; the non-reproducible tree tells you *why* a
  bug flakes where diagnosing-bugs only makes it flake more often — the
  council absorbed exactly this piece (`bucket-06.md:20`).
- Only skill treating error text as adversarial input — a gap in all four
  others, including ours.
- `git bisect` is concrete where superpowers only says "check recent changes".

**Cons**
- The safe-fallback section hands the agent a sanctioned symptom-patch path
  inside a root-cause skill; the council's drop rationale: "You cannot keep a
  hard gate and a time-pressure symptom-patch path in one skill without the
  gate degrading into advice" (`bucket-06.md:24`).
- No hypothesis protocol at all — the jump from localize to fix is guarded
  only by "ask why", with neither superpowers' single-hypothesis rule nor
  diagnosing-bugs' ranked falsifiable set.
- No phase-exit criteria; checklist compliance is self-assessed.
- Command examples are npm-specific (flagged inline at `SKILL.md:75-76`).

### `performance-optimization` (agent-skills) — adjacent capability

**Separated deliberately: this is not a debugging-loop substitute.** Its
family is `performance` (`skill-buckets.md:127`); the debugging family lists
only the other three (`skill-buckets.md:237`). The debugging skills touch its
territory at exactly two points: diagnosing-bugs' perf branch ("baseline
measurement… then bisect. Measure first, fix second",
mattpocock `SKILL.md:112`) and superpowers listing "performance problems" in
scope with no method behind it (superpowers `SKILL.md:28`).

**Achieves** — performance work as measured experiments with a strict
keep-or-revert disposal rule, so unverified "optimizations" never accrete.

**Can do**
- Measure-first mandate with an explicit not-for (premature optimization)
  (`SKILL.md:8-20`); 5-step workflow MEASURE → IDENTIFY → FIX → VERIFY →
  GUARD (`SKILL.md:30-38`).
- Synthetic + RUM dual measurement, a symptom→measurement decision tree, and
  bottleneck tables for frontend and backend (`SKILL.md:40-119`).
- An anti-pattern fix catalog: N+1, unbounded fetching, image optimization,
  React re-renders, bundle size, caching (`SKILL.md:121-290`).
- The disposal discipline: re-measure identically (`SKILL.md:294-296`), one
  change per measurement (`SKILL.md:298`), beat run-to-run variance not the
  mean (`SKILL.md:300`), a strict keep/revert table where "Improved, but a
  test went red" is a revert (`SKILL.md:302-309`), **"Neutral is a revert,
  not a keep"** (`SKILL.md:311`), and correctness gating the metric
  (`SKILL.md:313`).
- The attempt ledger — log kept *and reverted* attempts so a dead idea is
  never re-run (`SKILL.md:315-325`).
- Performance budgets enforced in CI (`SKILL.md:327-347`); an 8-row
  rationalization table centred on sunk cost (`SKILL.md:355-366`); 12 red
  flags; an 11-item verification checklist (`SKILL.md:368-396`); plus the
  repo-shared checklist it points at
  (`references/performance-checklist.md`, via `SKILL.md:352`).

**Counterpart in our harness: none.** This was checked, not assumed: a sweep
of `.claude/skills/`, `.claude/rules/`, `.claude/project/`, and `CLAUDE.md`
for performance/profiling/benchmark/bottleneck/optimization content finds
only incidental word matches (e.g. `codebase-design/SKILL.md` mentioning
"performance characteristics" of an interface). No skill, rule, or project
doc carries baselines, profiling, noise-vs-mean comparison, keep-or-revert
disposal, or an attempt ledger. Our installed debugging skill has no
performance trigger either, so a perf regression entering the harness meets
no measurement discipline at any point.

**Pros** — the disposal rule and attempt ledger are unique in the entire
corpus; the council called this content "domain-neutral" and load-bearing
(`bucket-06.md:30`). **Cons** — roughly half the body is web-frontend catalog
(Core Web Vitals, images, bundles, React) that round-002 explicitly trimmed
as out of scope (`bucket-06.md:37-39`), and the examples are
npm/React/Express-specific.

### `systematic-debugging` (ours, installed)

**Achieves** — a seven-step root-cause loop compressed to one page, wired
into the execution engine's failure paths.

**Can do**
- Core mandate: "Do not guess. Find the root cause first" (`SKILL.md:8`).
- Seven steps: reproduce + capture exact symptom; read errors/stack/recent
  changes; narrow the failing boundary by comparing working vs broken paths;
  one root-cause hypothesis at a time; smallest falsifying change or
  diagnostic; proving test + fix only after the cause is credible; re-verify
  the original symptom is gone (`SKILL.md:12-18`).
- Rules: no stacked guesses or bundled fixes; a failed hypothesis means stop
  and re-derive from evidence (`SKILL.md:22-23`).
- **Codex-as-falsifier escalation** when the issue crosses systems or one
  hypothesis has failed (`SKILL.md:24`) — no reference skill has any
  cross-model check.
- Structural mounting no reference skill has: routed from `CLAUDE.md`'s
  process table and from three execution-engine failure paths
  (`.claude/skills/execution/SKILL.md:45`,
  `references/task-engine.md:92`, `:106`, `references/workstream-mode.md:73`).
- Deliberate delegation: the proving test hands off to our TDD skill, which
  owns seam selection and the RED discipline
  (`.claude/skills/test-driven-development/SKILL.md:3`, `:38-54`), and
  completion proof to `verification-before-completion` — consistent with the
  harness' lean-shell doctrine.

**Pros**
- Near-zero context cost (25 lines) on a skill that fires often.
- The only skill in the set that composes with an execution pipeline and a
  separately-maintained TDD skill instead of inlining everything — via that
  route it inherits seam discipline comparable to diagnosing-bugs'
  `SKILL.md:116-120`, *when the routing actually happens*.
- Cross-model falsification is a genuinely novel escalation primitive.

**Cons**
- Every gate is judgment-based — "Only after the cause is credible"
  (`SKILL.md:17`) has no observable pass condition; this is the exact axis on
  which the council preferred diagnosing-bugs (`bucket-06.md:13`).
- Missing vs mattpocock: the whole feedback-loop discipline — construction
  catalog, tightening, red-capable exit criterion, minimisation, ranked
  hypotheses with prediction format, tagged instrumentation with cleanup,
  redaction, HITL, perf branch, post-mortem handoff.
- Missing vs superpowers: all pressure-resistance apparatus, the fix-counting
  architecture escalation, per-boundary evidence protocol, and all three
  technique assets plus the polluter bisection script.
- Missing vs agent-skills: the non-reproducible decision tree, layer/error
  triage trees, `git bisect` recipe, instrumentation lifecycle rules, and the
  untrusted-error-output defense.
- No performance awareness (`SKILL.md:3` lacks a "slow" trigger), and nothing
  else in the harness supplies it.

## Verdict

The three debugging skills are one method told at three levels of enforcement,
and the taxonomy is right to call them substitutes (`skill-buckets.md:237`);
performance-optimization is a complement — different family, different
outcome, and the only carrier of measurement-disposal discipline anywhere in
the five. Strongest per axis: **diagnosing-bugs** for enforceable process (its
gates are artifacts — a named red-capable command, a load-bearing minimal
repro — not self-assessed compliance); **superpowers systematic-debugging**
for pressure resistance, quantified escalation, and post-fix hardening;
**debugging-and-error-recovery** for triage trees, `git bisect`, and the
untrusted-error-output rule; **performance-optimization** for the
neutral-is-a-revert disposal rule and attempt ledger, which have **no
counterpart in our harness at all**. The council's round-001 ruling
(`harness_lifecycle/casebook/views/bucket-06.md:9-24`) already adjudicated
the substitution: diagnosing-bugs adopted as spine — "the only skill that
makes building a reliable reproduction the skill itself, with a checkable
phase-one exit… chose this spine over the alternative on enforcement
strength" — absorbing superpowers' three-fixes escalation, per-boundary
evidence, and three technique assets, plus agent-skills' non-reproducible
tree and bisect method, while deliberately dropping agent-skills' fallback
patterns because "you cannot keep a hard gate and a time-pressure
symptom-patch path in one skill without the gate degrading into advice";
round-002 kept performance-optimization adopted, scope-trimmed
(`bucket-06.md:28-39`). The evidence in this comparison is that none of that
merge has landed: our installed skill's 25 lines contain no loop phase, no
exit criterion, no escalation counter, no technique assets, no
non-reproducible tree, and no bisect — so the 2026-07-15 ledger claim that
agent-skills' skill is "*Covered by our reproduce, isolate, falsify, prove,
fix, and verify workflow*" holds only at the level of step names, and the
ledger's "deferred" on performance-optimization now contradicts the
casebook's "STAYS ADOPTED — scope-trimmed" with nothing installed on either
reading. Reconciling ledger, casebook, and installed tree is a
harness-evaluate decision, not this document's; what this comparison
establishes is the component-level delta any merge must close, and the four
things it must preserve from ours: the execution-engine mounts, the TDD and
verification handshakes, the Codex falsifier rule, and the one-page context
cost that lets this skill fire on every failure path without weighing down
the loop that calls it.
