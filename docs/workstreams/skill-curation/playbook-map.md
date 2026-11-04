# Playbook map: pstack's 23 playbooks, the rulings and the skills each needs

Snapshot: pstack v0.15.36 (`cursor_plugins` at `4dd1d05`), Pocock `5beb35b`,
our worktree on branch `mvp-stack`, read 2026-10-31. Bead `cr-r2pa.1.5`.
Phase 2 runs on this map: it says which playbooks to bring, what each step
needs from the units it calls, and which skills to merge or build first.

Path aliases: `P/` is `reference_harnesses/cursor_plugins/pstack/`; `PB/` is
`P/skills/poteto-mode/playbooks/`; `MP/` is
`reference_harnesses/mattpocock_skills/`; `O/` is `.claude/skills/`. A bare
`:N` in a playbook's section cites that playbook's file. Rule IDs (B3, S7,
R8, St4 …) are from `.repo-context/unit-kinds.md`.

Every recommendation, fit and merge question is a judgement. Facts are read
from the cited lines. The pstack report (`pstack-report.md`) and the boundary
study (`boundary-study.md`) were inputs; every claim taken from them was
re-read at the source, and the H9 classes were re-verified against the
callee files. Files changed while this map was written, by other tasks in
the same worktree: `systematic-debugging` is now diagnosis-only, the bug-fix
pilot draft exists at `O/mvp-mode/playbooks/bug-fix.md`, `skill-router` has
retired into `O/mvp-mode/SKILL.md`, and the rules gained St1's split of calls
from loads, B11 (a skill names a playbook only as a route back through the
router), B12 (a playbook's step list is its frontmatter) and F3 (a
playbook's references live beside it). The citations follow the current
files. Revision 2 applies critic 1e's eleven findings; revision 3 its round-2 two
(classifier promotion, the trail review without an event record).

## Summary

**17 adapt, 6 defer, 0 adopt.** No playbook can be adopted as written. Each
one, or a pstack skill it calls, picks models by per-role lines, commits
without asking or needs a Cursor-only tool; each of those conflicts with
local policy or tooling (report §4.3).

| Playbook | Recommendation | Group | In one line |
|---|---|---|---|
| Investigation | adapt | understand | Explain always, history for a motivation question, then a prose pass; live with the explain skill |
| Runtime forensics | adapt | forensics | Live capture needs a diagnosis-only branch of `performance-optimization` (B3) |
| Trace forensics | adapt | forensics | Needs no new skill; generic artifact procedure |
| Bug fix | adapt | pilot | Pilot 1, in progress |
| Perf issue | adapt | measure | Thin order around `performance-optimization` plus vetting and design |
| Hillclimb | adapt | measure | The metric loop we lack; two H9 remedies land with Perf issue |
| Feature | adapt | build | Design-first order before the build; who builds is a ruling |
| Refactoring | adapt | build | Orders parts three of our skills already hold |
| Prototype | adapt | plan | Into our `prototype` skill, not a playbook (composite test) |
| Visual parity | defer | deferred | No UI surface |
| Authoring a skill | adapt | pilot | Ours is equivalent: `harness_lifecycle/playbook.md`; its place is report decision 15 |
| Eval | adapt | eval | Promotes the S8 harness (fresh headless sessions, stream-JSON events); Claude Code candidates only for now |
| Opening a PR | adapt | land | Commits and Titles become a `land` skill; the PRs section and the rest deferred |
| Babysit | defer | deferred | No PRs, no CI |
| Shipping | defer | deferred | No PR stacks |
| Autonomous run | adapt | long-run | Exit-predicate loop; waits on the wake ruling |
| Orchestrate | defer | deferred | Cursor cloud fleet; harvest its supervision rules into `delegation` |
| Autopilot-full | defer | deferred | PR owner fleet that merges |
| Autopilot-stack | defer | deferred | Autopilot-full with overrides |
| Multi-phase plan | adapt | pilot | Pilot 2; skeleton adapted per report §4.3 |
| Session pickup | adapt | pilot | Pilot 3 |
| Pause safely | adapt | pilot | Pilot 3 |
| Worktree cleanup | adapt | housekeeping | Git half only; prune on approval |

**Top contracts by demand** (§3): `delegate` (12 live playbooks, ours
fits), `land` (7, missing), `explain-code` (6, wider), `design-first` (4,
narrower), `wake` (3, missing). Phase 2 starts with `land`, `explain-code`
with a `why` branch, a design-only sketch branch for `design-first` and
`prose-pass`: together they finish the bug-fix pilot's narrower bindings and
bring Refactoring and Investigation live (§5).

**Where this map departs from the report (J).**

1. Opening a PR: the report defers it (§5.4). Here its Commits and Titles
   rules become a `land` skill now, because six adapted playbooks end in it
   and B7 needs a closeout. Only the PR sections are deferred.
2. Prototype: the report keeps our skill and pstack's playbook side by side
   (§4.2). By the composite test (unit-kinds §2) pstack's is a skill, so it
   folds into ours and no playbook is drafted.
3. Eval moves forward, because the S8 baseline already built its two hard
   parts outside this map: candidates as fresh top-level headless sessions in
   a sandbox copy, and a transcript source in their stream-JSON tool events.
   Eval promotes that harness. Its candidates do not go through `delegation`:
   R8 bars a delegated task from starting a playbook, which is the behaviour
   S8 measures. Only the judge is a delegated critic.
4. Orchestrate: the report compares it with `execution` in the second wave.
   Here it is deferred as a playbook and its supervision rules become merge
   candidates for `delegation`.

## 1. Method

**What counts as a call.** A call is a step running or applying a named unit:
a pstack skill, another playbook, a router section (Subagents, the playbook
match), a script or reference file, or an outside unit (Cursor built-ins,
`cursor-team-kit`, cloud agents). Principle citations are listed apart, per
the brief. Tools inside an own action (`gh`, `git`, sqlite, `xcrun`, CDP)
are not units. Delegation wording ("delegate", "subagent") is a call to the
Subagents contract, which binds to our `delegation` skill.

**How every call was found.** A script extracted every unit name from the 23
files, line by line: 236 mentions. Each is mapped below as a call (152
mentions in 122 call rows), a principle (39) or a non-call with its reason
(45: routing boundaries such as "Distinct from Runtime forensics", carve-out
lines, negative mentions). No mention is unmapped and no row lacks a
mention (check 2, Appendix).

**Call kinds.** `run` (default) calls the unit; `borrow` takes part of a
playbook; `reference` cites one rule of another playbook; `load` reads or
runs a file that in our version lives beside the playbook (St1: a load is not
a call and B3 does not apply; F3). Four kinds are not demand: `handoff`
passes the deliverable to the next playbook; `select` names a procedure a
later run uses and runs nothing now; `pointer` names an artifact another unit
made; `template` sits in Multi-phase plan's skeleton, which the executing
owner runs. A call marked **local** is one our version replaces with a local
own action, not a skill.

**Fit**, ours against what the step needs, for calls and for binds:

- **same:** our unit delivers it whole;
- **narrower:** ours delivers part of it;
- **wider:** ours does more, so calling it whole (B3) does extra work or
  invites a skip;
- **conflicting:** ours contradicts the need, or a local rule does;
- **missing:** no unit of ours.

**Pocock fit** is judged separately, Pocock's candidate against the same
need, on the same scale. It shows in brackets after the candidate in §2 and
with its limitation in §3.

**H9 (B3) flags.** Each call carries the pstack class from the study's
`h9-cases.yaml` (fires, ambiguous, carve-out, reference or clean), re-read
against the callee, then the risk on our side once the call binds to our
unit. Section 4 lists every flagged call.

**Demand** (§3) counts, per contract, the adopted or adapted playbooks whose
carried steps call it (`run`, `borrow`, `reference` or `load`) or whose own
action binds to it (`own`). Hand-offs, selections, pointers, templates, local
calls and steps marked "not carried" do not count; §3.1 lists the first four
kinds' dependencies apart, with the local calls. A check asserts this (check
3, Appendix).

**Readiness** (§5) lists, per live playbook, every carried call or bind of a
demand kind whose fit is not `same` and that is not local.

**Steps.** Each table lists a step's own actions, with the skills of ours
they bind to and that binding's fit (technique lives in skills, B4); an own
action with no binding stays local to the playbook. Then its calls in order.
Rule-set playbooks (Opening a PR, Orchestrate) list their sections as steps;
a section marked "not carried" is deferred. In phase 2 each table becomes
the playbook's frontmatter step list (B12), and its loads move beside it
(F3).

The data and scripts are in the gitignored `scratchpad/mvp-stack/playbook-map/`
of the worktree; this file is self-contained.

## 2. Per playbook

### 2.1 Investigation (`PB/investigation.md`)

**Recommendation: adapt.** Read-only procedure that orders two explain calls and a prose pass (B6). It goes live as soon as the explain contract exists. The report places it in the second wave (§5.4).

- **Lacks (Cursor-only or outside pstack):** none Cursor-only; `how` and `why` read per-role model lines from `pstack-models.mdc`.
- **Overlaps ours:** `codebase-research` deep dive and its inline branch; the router's 'answer from the source' line (O/mvp-mode/SKILL.md:61), which replaced `skill-router`'s.
- **Principles named:** none named.
- **Reply contract:** `:14`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| 1 `:7` | explain how it works; for a motivation question, also its history | S `how` `:7` → **explain-code** | none (router: answer from source); codebase-research / none (missing) | wider | pstack ambiguous: step 3's recommendation table may replace how's output sections (PB/investigation.md:9; P/skills/how/SKILL.md:32-36). Ours: give the explain skill a decision branch, so the call stays whole. |
|  |  | *if a motivation question:* S `why` `:7` → **history** | none / none (missing) | missing | pstack ambiguous: why keeps its confidence separation and sources line (P/skills/why/SKILL.md:92); a how-shaped reply may drop them. Ours: the reply keeps why's required content (B3 fold rule). |
| 2 `:8` | throughput checkpoint stays one n/a line | — | | | |
| 3 `:9` | answer in how's sections, or a recommendation with a tradeoffs table for a choice | — | | | |
| 4 `:10` | prose pass on the reply | S `unslop` `:10` → **prose-pass** | none / none (missing) | missing | clean |
| after `:12` | no PR; a change re-routes to Bug fix or Feature through the user | B Bug fix `:12` → **fix-bug** (handoff) | Bug fix (pilot) / diagnosing-bugs (narrower) | same | hand-back through the user, then the router |
|  |  | B Feature `:12` → **build-feature** (handoff) | Feature (here) / implement (conflicting) | same | hand-back through the user, then the router |

### 2.2 Runtime forensics (`PB/runtime-forensics.md`)

**Recommendation: adapt.** Diagnosis-only procedure. The Python half applies: live stacks and snapshots are in our performance recipes, but no procedure orders them (report §4.2), and the one skill that holds them goes on to tune, which a diagnosis must not (B3, step 1). Live when `performance-optimization` gains a diagnosis-only branch.

- **Lacks (Cursor-only or outside pstack):** `control-ui`/`control-cli` from `cursor-team-kit`; CDP eval on a live browser or Electron process.
- **Overlaps ours:** `performance-optimization` measurement recipes; `systematic-debugging` instrumentation when no repro exists (O/systematic-debugging/SKILL.md:29-31).
- **Principles named:** `guard-the-context-window` (step 2, `:6`).
- **Reply contract:** `:11`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| 1 `:5` | capture a real artifact of the live symptom → **live-capture** (`performance-optimization (wider)`, wider: B3: the only provider of live capture is `performance-optimization`, whose core goes on to change a factor and compare (O/performance-optimization/SKILL.md:24-29), beyond a diagnosis-only request; its recipes (O/performance-optimization/references/measurement-recipes.md:21-25) are its own reference (F1). Remedy: a diagnosis-only branch (batch 2)) | X `control-skill` `:5` → **drive-surface** | none (run the CLI: own action) / none (missing) | missing | local: for our Python processes the capture is the own action above, bound to `live-capture` |
| 2 `:6` | reduce the artifact to the smoking gun; keep the reduced finding in the main thread | router Subagents `:6` → **delegate** | delegation / chief-of-staff (in-progress) (wider) | same |  |
| 3 `:7` | prove the mechanism by injecting instrumentation into the running process → **debug** (`systematic-debugging`, same: a whole call: `systematic-debugging` is diagnosis-only (O/systematic-debugging/SKILL.md:8-10)) | — | | | |
| 4 `:8` | map the finding to file, symbol and line | — | | | |
| 5 `:9` | throughput checkpoint stays one n/a line | — | | | |
| reply `:11` | no fix unless asked | B Bug fix `:11` → **fix-bug** (handoff) | Bug fix (pilot) / diagnosing-bugs (narrower) | same |  |
|  |  | B Perf issue `:11` → **fix-perf** (handoff) | Perf issue (here) / none (missing) | same |  |

### 2.3 Trace forensics (`PB/trace-forensics.md`)

**Recommendation: adapt.** Generic procedure for an artifact handed over after the fact; our recipes cover the capture formats, not this order (report §4.2).

- **Lacks (Cursor-only or outside pstack):** DevTools-specific parsers only; the rest is generic.
- **Overlaps ours:** `performance-optimization` recipes for cProfile, memray and tracemalloc (O/performance-optimization/references/measurement-recipes.md:26-33).
- **Principles named:** `guard-the-context-window` (step 1, `:7`).
- **Reply contract:** `:14`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| 1 `:7` | identify the format and load it | router Subagents `:7` → **delegate** | delegation / chief-of-staff (in-progress) (wider) | same |  |
| 2 `:8` | dump to a queryable form (sqlite) before reading | — | | | |
| 3 `:9` | narrow to the hot path, retainer chain or stuck thread | — | | | |
| 4 `:10` | attribute to source through the artifact's symbols, or say they are missing | — | | | |
| 5 `:11` | *if a paired capture exists:* diff before and after; otherwise label the strongest hypothesis | — | | | |
| 6 `:12` | hand back a cited diagnosis | B Bug fix `:12` → **fix-bug** (handoff) | Bug fix (pilot) / diagnosing-bugs (narrower) | same |  |
|  |  | B Perf issue `:12` → **fix-perf** (handoff) | Perf issue (here) / none (missing) | same |  |

### 2.4 Bug fix (`PB/bug-fix.md`)

**Recommendation: adapt.** Pilot order 1, piloted separately (report §5.3); the draft is in progress at O/mvp-mode/playbooks/bug-fix.md:32-82. Mapped here so the aggregate counts its demand.

- **Lacks (Cursor-only or outside pstack):** `control-ui`/`control-cli`; Cursor `/loop`; the `grok-4.7-xhigh-fast` bug-fix model line.
- **Overlaps ours:** `systematic-debugging` (diagnosis, now split from the fix) and `test-driven-development` test-first; the pilot draft (O/mvp-mode/playbooks/bug-fix.md:32-82); delegation is not mandatory here (report §4.3).
- **Principles named:** `sequence-verifiable-units` (step 5, `:12`).
- **Reply contract:** `:15`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| gate `:3-5` | every shipped line traces to runtime evidence; revert what a refuted hypothesis motivated → **debug** (`systematic-debugging`, same) | router Subagents `:3` → **delegate** | delegation / chief-of-staff (in-progress) (wider) | same | mandatory in pstack; adapted to AGENTS.md:42-43 (report §4.3) |
| 1 `:7` | reproduce it yourself; ask the user only with a stated reason; force the trigger → **debug** (`systematic-debugging`, same) | X `control-skill`, router `non-negotiables` `:7` → **drive-surface** | none (run the CLI: own action) / none (missing) | missing | local: for our CLI and Python surfaces, running the command is the own action |
| 2 `:8` | binary-search the cause; instrument; confirm the mechanism before design → **debug** (`systematic-debugging`, same) | S `how` `:8` → **explain-code** | none (router: answer from source); codebase-research / none (missing) | wider | clean |
|  |  | S `why` `:8` → **history** | none / none (missing) | missing | clean |
|  |  | *if a long or stubborn hunt:* X `/loop` `:8` → **wake** | none (platform tools) / chief-of-staff (in-progress) (narrower) | missing |  |
| 3 `:9` | plan the fix with a specific scope | *if the fix crosses a function boundary:* S `architect` `:9` → **design-first** | codebase-design / codebase-design (narrower) | narrower | pstack ambiguous: does the delegate run architect's Phase D (P/skills/architect/SKILL.md:51)? Ours: clean only if the sketch branch stays design-only and step 3's delegate implements against the sketch (ruling 5). |
|  |  | router Subagents `:9` → **delegate** | delegation / chief-of-staff (in-progress) (wider) | same |  |
| 4 `:10` | verify on the same surface: the original repro passes; inconclusive is not a pass (the pilot's own Rerun step) | — | | | |
| 5 `:11-12` | failing repro lands before the fix in history (B8: needs commit authority) | *if a cheap local test exists:* S `tdd` `:11` → **test-first** | test-driven-development / tdd (wider) | same | carve-out on both sides: tdd says do not force an impractical test (P/skills/tdd/SKILL.md:11); ours proves the regression when feasible (O/test-driven-development/SKILL.md:35-37) |
| 6 `:13` |  | B Opening a PR `:13` → **land** | none (AGENTS.md rules) / pr (narrower) | missing | clean |

### 2.5 Perf issue (`PB/perf-issue.md`)

**Recommendation: adapt.** A thin order around `performance-optimization` plus vetting, design, delegation and an artifact comparison: the parts report §4.2 found missing.

- **Lacks (Cursor-only or outside pstack):** `control-ui`/`control-cli`; the perf-issue model line.
- **Overlaps ours:** `performance-optimization` (procedure skill, a known mixed-role deviation).
- **Principles named:** `sequence-verifiable-units` (step 3, `:18`).
- **Reply contract:** `:25`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| 1 `:5` | capture a baseline trace; vet every later number → **perf-procedure** (`performance-optimization`, same: one whole call spans steps 1, 2 and 4) | X `control-skill` `:5` → **drive-surface** | none (run the CLI: own action) / none (missing) | missing | local: running the command or test is the own action for our surfaces |
|  |  | S `benchmark-checklist` `:5` → **vet-measurement** | performance-optimization / none (missing) | narrower | clean |
| 2 `:6-16` | ground hypotheses; try the seven mantras cheapest first; stop when one meets the target → **perf-procedure** (`performance-optimization`, narrower: lacks the seven mantras (batch 2)) | S `how` `:6` → **explain-code** | none (router: answer from source); codebase-research / none (missing) | wider | clean |
| 3 `:17-18` | plan from the trace; review the diff; capture a post-fix trace → **review-diff** (`review; delegation`, same) | *if crosses a function boundary:* S `architect` `:17` → **design-first** | codebase-design / codebase-design (narrower) | narrower | pstack ambiguous: Phase D, as Bug fix. Ours: clean on the same condition; step 3's delegate implements against the sketch |
|  |  | router Subagents `:17` → **delegate** | delegation / chief-of-staff (in-progress) (wider) | same |  |
| 4 `:19` | compare the before and after artifacts; inconclusive is not a pass → **perf-procedure** (`performance-optimization`, same) | — | | | |
| 5 `:20` | cite the measurement in the PR (ours: the report or commit body) | — | | | |
| 6 `:21` |  | B Opening a PR `:21` → **land** | none (AGENTS.md rules) / pr (narrower) | missing | clean |

### 2.6 Hillclimb (`PB/hillclimb.md`)

**Recommendation: adapt.** The loop our attempt record lacks: a frozen harness, a stop predicate with a floor, and pushing past a plateau (report §4.2). Write it with Perf issue: both borrow the mantras.

- **Lacks (Cursor-only or outside pstack):** Cursor `/loop` through Autonomous run's wake; the hillclimb model line.
- **Overlaps ours:** `performance-optimization` steps 4-5 and its attempt record (O/performance-optimization/SKILL.md:23-32).
- **Principles named:** `prove-it-works` (step gate, `:5`); `build-the-lever` (step 2, `:8`); `guard-the-context-window` (step 5, `:12`); `separate-before-serializing-shared-state` (step 5, `:12`); `sequence-verifiable-units` (step 5, `:16`); `laziness-protocol` (step 6, `:17`).
- **Reply contract:** `:21`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| gate `:5` | one change, one measurement, keep or revert; no win from inspection | — | | | |
| 1 `:7` | realistic workload dimensions; one metric; a stop predicate with a floor on attempts → **perf-procedure** (`performance-optimization`, same) | S `how` `:7` → **explain-code** | none (router: answer from source); codebase-research / none (missing) | wider | clean |
| 2 `:8` | build the harness, prove it separates cases, freeze it; record baseline and a green gate | S `benchmark-checklist` `:8` → **vet-measurement** | performance-optimization / none (missing) | narrower | clean |
| 3 `:9` | read the log before each attempt | S `show-me-your-work` `:9` → **decision-trail** | none (attempt record; Beads notes) / none (missing) | narrower | pstack FIRES, override: its own columns replace the fixed header (P/skills/show-me-your-work/SKILL.md:15-22). Remedy: the trail skill takes caller columns. |
| 4 `:10` | ground each hypothesis in a named mechanism → **perf-procedure** (`performance-optimization`, narrower: lacks the seven mantras (batch 2)) | B Perf issue `:10` → **fix-perf** (borrow) | Perf issue (here) / none (missing) | same | pstack FIRES, skip (playbook to playbook): the mantra order without its stop rule. Remedy: the mantras move into `performance-optimization` as an ordered list both callers use. |
| 5 `:11-16` | loop: measure with the frozen harness, gate, keep or revert in full; one commit per accepted fix (B8) → **perf-procedure** (`performance-optimization`, same: one attempt per iteration; the loop is Hillclimb's own) | router Subagents `:12` → **delegate** | delegation / chief-of-staff (in-progress) (wider) | same |  |
|  |  | *if the run is unattended:* B Autonomous run `:16` → **wake** (borrow) | none (platform tools) / chief-of-staff (in-progress) (narrower) | missing | pstack FIRES, skip: the wake without the stop rule. Remedy: call the wake contract directly, not the playbook. |
| 6 `:17` | push past the first plateau; correctness and simplicity outrank the number | — | | | |
| 7 `:18` | stop at the predicate, or when ideas are marginal; never relax it | — | | | |
| 8 `:19` | accepted commits stacked in order | B Opening a PR `:19` → **land** | none (AGENTS.md rules) / pr (narrower) | missing | clean |

### 2.7 Feature (`PB/feature.md`)

**Recommendation: adapt.** Adds the design-first order before building that `execution`'s task loop lacks (report §4.2). Which unit runs the build is an owner ruling.

- **Lacks (Cursor-only or outside pstack):** the feature model line; arena runner model lines.
- **Overlaps ours:** `execution` task loop (O/execution/SKILL.md:36-52); the `feature-delivery` graph.
- **Principles named:** `separate-before-serializing-shared-state` (step 3, `:10`); `model-the-domain` (step 4, `:12`); `laziness-protocol` (step 4, `:12`); `sequence-verifiable-units` (step 6, `:15`).
- **Reply contract:** `:21`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| 1 `:5` |  | S `how` `:5` → **explain-code** | none (router: answer from source); codebase-research / none (missing) | wider | clean |
| 2 `:6` |  | S `architect` `:6` → **design-first** | codebase-design / codebase-design (narrower) | narrower | pstack ambiguous: step 4 delegates the code; Phase D unstated. Ours: clean if the sketch branch is design-only; step 4 implements against the sketch |
| 3 `:7-11` | throughput checkpoint as four todos; n/a items keep a reason | — | | | |
| 4 `:12` | brief names a data shape and success criteria; review separation is mandatory; port shared-primitive fixes to every consumer → **review-diff** (`review; delegation`, same) | router Subagents `:12` → **delegate** | delegation / chief-of-staff (in-progress) (wider) | same | pstack mandatory; ours by risk label (O/execution/SKILL.md:23-29) |
|  |  | *if several valid shapes:* S `arena` `:12` → **candidates-judge** | model-council / none (missing) | conflicting | pstack clean (arena whole). Ours: `model-council` lacks pick and graft and runs only on explicit request (O/model-council/SKILL.md:3). |
| 5 `:13` | verify on the matching surface; inconclusive is not a pass | — | | | |
| 6 `:14-15` | rebase into small ordered commits (B8) → **land** (`none (AGENTS.md rules)`, missing) | — | | | |
| 7 `:16` |  | *if the design is contested:* S `interrogate` `:16` → **adversarial-review** | review / code-review (narrower) | narrower | clean |
| 8 `:17` |  | B Opening a PR `:17` → **land** | none (AGENTS.md rules) / pr (narrower) | missing | clean |

### 2.8 Refactoring (`PB/refactoring.md`)

**Recommendation: adapt.** The parts exist in three skills; nothing orders them (report §4.2). The order is the value.

- **Lacks (Cursor-only or outside pstack):** control skills for smoke runs; the refactoring model line.
- **Overlaps ours:** `test-driven-development` characterization; `planning` expand, migrate, contract (O/planning/SKILL.md:64-70); `improve-codebase-architecture` finds candidates.
- **Principles named:** `model-the-domain` (step 2, `:8`); `foundational-thinking` (step 3, `:9`); `redesign-from-first-principles` (step 3, `:9`); `subtract-before-you-add` (step 4, `:10`); `laziness-protocol` (step 4, `:10`); `migrate-callers-then-delete-legacy-apis` (step 5, `:11`); `prove-it-works` (step 6, `:12`); `minimize-reader-load` (step 7, `:13`); `sequence-verifiable-units` (step 8, `:14`).
- **Reply contract:** `:16`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| 1 `:7` | pin the behaviour contract before any move; type check and lint are not a pin → **characterize** (`test-driven-development`, same) | S `how` `:7` → **explain-code** | none (router: answer from source); codebase-research / none (missing) | wider | clean |
| 2 `:8` | name the missing structure; the reshape must delete branches | — | | | |
| 3 `:9` | name the target shape | *if the target crosses a function boundary:* S `architect` `:9` → **design-first** | codebase-design / codebase-design (narrower) | narrower | pstack ambiguous: step 5 moves the code; Phase D unstated. Ours: clean if the sketch branch is design-only; step 5 moves the code against the sketch |
| 4 `:10` | subtract first; revert speculative cleanup | — | | | |
| 5 `:11` | small green steps; migrate callers and delete in one wave; spot-check renames | router Subagents `:11` → **delegate** | delegation / chief-of-staff (in-progress) (wider) | same |  |
| 6 `:12` | prove behaviour unchanged on the real artifact; equivalence check for larger moves | X `control-skill` `:12` → **drive-surface** | none (run the CLI: own action) / none (missing) | missing | local: running the command or test is the own action for our surfaces |
| 7 `:13` | keep only if reader load drops; else revert | — | | | |
| 8 `:14` | subtraction commit, reshape, follow-ons (B8) | B Opening a PR `:14` → **land** | none (AGENTS.md rules) / pr (narrower) | missing | clean |

### 2.9 Prototype (`PB/prototype.md`)

**Recommendation: adapt.** Adapt into our `prototype` skill, not a playbook. Composite test (unit-kinds §2): remove the three calls and the technique still yields the decision, so it is a skill; ours exists (S1). Deltas to fold in: variants behind one switcher, and a recommendation with tradeoffs.

- **Lacks (Cursor-only or outside pstack):** control skill screenshots; the moodboard step is UI tooling.
- **Overlaps ours:** `prototype` skill (O/prototype/SKILL.md:8-28); Pocock `prototype`.
- **Principles named:** `laziness-protocol` (step intro, `:5`, inverted); `exhaust-the-design-space` (step 4, `:10`).
- **Reply contract:** `:14`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| 1 `:7` | name the decision; no decision, no prototype | — | | | |
| 2 `:8` | *if the design space is open:* gather references; let the user pick directions | — | | | |
| 3 `:9` | build throwaway in a scratch dir; no tests or abstractions | — | | | |
| 4 `:10` | *if comparing alternatives:* variants behind one switcher | — | | | |
| 5 `:11` | observe the thing being decided; the observation is the test | *if a visual decision:* X `control-skill` `:11` → **drive-surface** | none (run the CLI: own action) / none (missing) | missing | local: a CLI or logic prototype is observed by running it; a visual one waits for a UI surface |
| 6 `:12` | present alternatives, tradeoffs and a recommendation | B Feature `:12` → **build-feature** (handoff) | Feature (here) / implement (conflicting) | same |  |
|  |  | S `architect` `:12` → **design-first** (handoff) | codebase-design / codebase-design (narrower) | narrower |  |

### 2.10 Visual parity (`PB/visual-parity.md`)

**Recommendation: defer.** Every step needs a UI, an image-diff harness and a control skill.
`revisit_when`: a UI surface enters scope (report decision 14).

- **Lacks (Cursor-only or outside pstack):** `control-ui`; Cursor `/loop`; a PR flow.
- **Overlaps ours:** none.
- **Principles named:** `separate-before-serializing-shared-state` (step 3, `:7`).
- **Reply contract:** `:11`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| 1 `:5` | baseline harness before any migration | — | | | |
| 2 `:6` | no harness or baseline edits | — | | | |
| 3 `:7` | one component at a time, one owner per worktree | — | | | |
| 4 `:8` | image-diff each component; nonzero is a fail | X `control-skill` `:8` → **drive-surface** | none (run the CLI: own action) / none (missing) | missing |  |
|  |  | X `/loop` `:8` → **wake** | none (platform tools) / chief-of-staff (in-progress) (narrower) | missing |  |
| 5 `:9` |  | B Opening a PR `:9` → **land** | none (AGENTS.md rules) / pr (narrower) | missing | clean |

### 2.11 Authoring a skill (`PB/authoring-a-skill.md`)

**Recommendation: adapt.** Equivalent already exists: `harness_lifecycle/playbook.md` §2 with `authoring-for-agents` (report §4.2). Adapt means no new file: ours is the playbook. Where it lives and whether the shipped router lists it is report decision 15 (open; B1, R3).

- **Lacks (Cursor-only or outside pstack):** Cursor's built-in `create-skill`; PR delivery.
- **Overlaps ours:** `harness_lifecycle/playbook.md` §2; `authoring-for-agents`; `skill-catalog.py --check`.
- **Principles named:** `encode-lessons-in-structure` (step after, `:10`).
- **Reply contract:** `:12`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| 1 `:5` |  | X `create-skill` `:5` → **skill-authoring** | authoring-for-agents / writing-for-agents (narrower) | same |  |
| 2 `:6` | validate frontmatter, referenced files, cross-skill links (ours: the Verify row, harness_lifecycle/playbook.md:25) → **skill-delivery** (`harness_lifecycle/playbook.md`, same) | — | | | |
| 3 `:7` | *if structural change:* test cases | — | | | |
| 4 `:8` |  | B Opening a PR `:8` → **land** | none (AGENTS.md rules) / pr (narrower) | narrower | clean; ours delivers by merge (harness_lifecycle/playbook.md:26) |

### 2.12 Eval (`PB/eval.md`)

**Recommendation: adapt.** Evaluation is our gap (report §4.2). The S8 baseline already built its two hard parts outside this map: candidates as fresh top-level headless sessions in a sandbox copy, and a transcript source in their stream-JSON tool events. Adapt means promoting that harness into the playbook's references (F3), not routing candidates through `delegation`: R8 bars a delegated task from starting a playbook, which is the behaviour S8 measures.

- **Lacks (Cursor-only or outside pstack):** Cursor `agent-transcripts/`; per-family model lines for candidates and judge; a headless runner and event stream for any vendor but Claude Code.
- **Overlaps ours:** `model-council` (members, then a judge); `harness-evaluate` judges adoption, not behaviour.
- **Principles named:** none named.
- **Reply contract:** `:25`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| gate `:5-13` | seven blinding rules | — | | | |
| 1 `:17` | frame the variant; a 3-6 item rubric for the judge only | — | | | |
| 2 `:18` | sanitized per-candidate environments: a fresh sandbox copy per run, variant installed, normal discovery surface | — | | | |
| 3 `:19` | one organic prompt | — | | | |
| 4 `:20` | N candidates, each a fresh top-level session in its own sandbox, same prompt | S `arena`, router Subagents `:20` → **candidate-run** (load) | S8 runner (scratch) / none (missing) | narrower | pstack FIRES, skip: arena Phase B only (arena opens six phase todos, P/skills/arena/SKILL.md:9). Ours: bound to `candidate-run`, not `model-council` or `delegation`, so no partial call remains. R8 does not apply: a candidate is a top-level session, not a delegated task; Claude Code only: other vendors need their own headless runner |
| 5 `:21` | one blinded judge on a different family | S `arena` `:21` → **delegate** | delegation / chief-of-staff (in-progress) (wider) | same | pstack FIRES, skip, with step 4: arena Phase C only. Ours: the judge is a `delegation` critic whose brief holds the rubric and sanitized labels, so no `model-council` judge brief is overridden (O/model-council/SKILL.md:23-25); a different family per the roster |
| 6 `:22` | grade chain-following from the files each candidate read, never self-report; never read other projects' chats | X `transcripts` `:22` → **run-events** | stream-JSON events (Claude Code only) / none (missing) | narrower | the chain check is available for Claude Code candidates only, and only once the classifier counts successful reads matched to their results (ruling 10); unavailable for any other vendor until its event stream is verified |
| 7 `:23` | read every output; compare with the judge; synthesize | — | | | |

### 2.13 Opening a PR (`PB/opening-a-pr.md`)

**Recommendation: adapt.** Split it. Commits and Titles become a `land` skill: by the composite test its rules still produce commits with the calls removed, and six adapted playbooks end in it. Differs from report §5.4 (defer all): without it no code playbook has a closeout (B7). The PRs section (its diff cleanup, comment pass and writing calls), Descriptions, Forge, Readiness, Size and Babysit are deferred until a PR flow exists.
`revisit_when`: PR sections: we adopt a PR flow with CI.

- **Lacks (Cursor-only or outside pstack):** `deslop` from `cursor-team-kit`; the built-in PR tool; the Origin forge; Bugbot.
- **Overlaps ours:** AGENTS.md staging and commit rules (AGENTS.md:62-65); our conventional-commit practice.
- **Principles named:** none named.
- **Reply contract:** none (B5 gap).

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| Worktree `:5` (not carried) | work in a worktree off main; `git reset --hard` between delegates (conflicts with AGENTS.md:62-64) | — | | | |
| Commits `:7` | commit liberally; rebase into small ordered commits; amend when it belongs (B8; amend only on request, AGENTS.md:64-65) → **land** (`none (AGENTS.md rules)`, missing) | — | | | |
| PRs `:9` (not carried) | cleanup and writing before a PR; deferred with the PR flow, its calls kept as coverage | X `deslop` `:9` → **deslop** | none / none (missing) | missing |  |
|  |  | S `no-comments` `:9` → **comment-pass** | none / none (missing) | missing | clean |
|  |  | S `technical-writing` `:9` → **tech-writing** | authoring-for-agents / pr; writing-for-agents (narrower) | narrower | carve-out: every layer except Diátaxis is the callee's own PR rule (P/skills/technical-writing/SKILL.md:94) |
|  |  | S `unslop` `:9` → **prose-pass** | none / none (missing) | missing | clean |
| Titles `:11` | Conventional Commits title naming a real symbol → **land** (`none (AGENTS.md rules)`, missing) | — | | | |
| Descriptions `:13-22` (not carried) | PR body sections: Why, What changed, Scope, Tradeoffs, Blast Radius, Verification | — | | | |
| Forge `:24` (not carried) | `gh` default, Origin when present | — | | | |
| Built-in PR tool `:26` (not carried) | use the run's PR tool when it has one | — | | | |
| Size and stacks `:28` (not carried) | five narrow PRs over one; stack by base branch | B Shipping `:28` → **ship-stack** (reference) | none (AGENTS.md merge rule) / none (missing) | missing | reference: borrows Shipping's step 4 |
| Readiness `:30` (not carried) | open ready, never draft | — | | | |
| Babysit `:32-34` (not carried) | post the URL and keep building; no babysit per PR | *if the user asks after the stack exists:* B Babysit `:32` → **pr-watch** | none / none (missing) | missing |  |

### 2.14 Babysit (`PB/babysit.md`)

**Recommendation: defer.** Needs PRs, CI and review bots; we have no CI (.repo-context/verification.md:8-9). Borrowable trait: classify a failure before any retry (step 7).
`revisit_when`: we adopt a PR flow with CI.

- **Lacks (Cursor-only or outside pstack):** Bugbot; `watch-pr`; Cursor `/loop`; Origin; Cursor's built-in babysit skill.
- **Overlaps ours:** none.
- **Principles named:** none named.
- **Reply contract:** none (B5 gap).

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| 1 `:7` | declare the mode; resolve the forge | — | | | |
| 2 `:8` | work the merge frontier only | — | | | |
| 3 `:9` | one babysitter per stack | — | | | |
| 4 `:10` | never mutate stack topology | — | | | |
| 5 `:11` | conflicts, then threads, then CI | — | | | |
| 6 `:12-18` | trust the forge's verdict; stop conditions per forge | script `watch-pr` `:12` → **pr-watch** | none / none (missing) | missing |  |
|  |  | X `/loop` `:12` → **wake** | none (platform tools) / chief-of-staff (in-progress) (narrower) | missing |  |
| 7 `:19` | classify CI before any retrigger; one retry | — | | | |
| 8 `:20` | fix real findings red-first in the owning PR | ref `bugbot-triage`, X `bugbot` `:20` → **bugbot-triage** | review (feedback) / none (missing) | narrower |  |
| 9 `:21-23` | stop at the human's line; babysitting never authorizes merging | *if an explicit merge request:* B Shipping `:21` → **ship-stack** (handoff) | none (AGENTS.md merge rule) / none (missing) | missing |  |
|  |  | ref `bugbot-triage` `:21` → **bugbot-triage** | review (feedback) / none (missing) | narrower | offer dismissal patterns to the shared rubric |

### 2.15 Shipping (`PB/shipping.md`)

**Recommendation: defer.** Bottom-up landing of a PR stack with cloud verifiers. Borrowable trait: reuse a verdict across rebases by `git patch-id` (step 3).
`revisit_when`: we adopt a PR flow with CI.

- **Lacks (Cursor-only or outside pstack):** Cursor cloud agents; `control-ui`/`control-cli`; `watch-pr`; Cursor `/loop`; Origin.
- **Overlaps ours:** AGENTS.md merge rule (AGENTS.md:66-68).
- **Principles named:** none named.
- **Reply contract:** `:12`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| 1 `:5` | resolve the forge; one non-author verifier per PR | X `cloud-agent` `:5` → **delegate** | delegation / chief-of-staff (in-progress) (wider) | narrower | a Cursor cloud agent per PR |
|  |  | X `control-skill` `:5` → **drive-surface** | none (run the CLI: own action) / none (missing) | missing |  |
| 2 `:6` | land only the contiguous verified run | — | | | |
| 3 `:7` | re-check verdicts by `git patch-id` | — | | | |
| 4 `:8` | land bottom-up; read each merge back | — | | | |
| 5 `:9` | leave the stack alone while it lands | B Babysit, script `watch-pr` `:9` → **pr-watch** (reference) | none / none (missing) | missing | reference: Babysit's watcher script |
|  |  | X `/loop` `:9` → **wake** | none (platform tools) / chief-of-staff (in-progress) (narrower) | missing |  |
| 6 `:10` | stop at the ceiling | — | | | |

### 2.16 Autonomous run (`PB/autonomous-run.md`)

**Recommendation: adapt.** The exit-predicate loop is missing; `run-phases` walks a roadmap instead (report §4.2). Step 4's 'fix discoveries yourself, don't ask' must adapt to AGENTS.md:9-12: in-scope fixes proceed, others become discovered-from beads.

- **Lacks (Cursor-only or outside pstack):** Cursor `/loop`; `AskQuestion`.
- **Overlaps ours:** `run-phases` and `execution` workstream mode (O/execution/references/workstream-mode.md:13-26).
- **Principles named:** `sequence-verifiable-units` (step 3, `:8`).
- **Reply contract:** `:13`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| 1 `:5` | state the exit condition as a checkable predicate | — | | | |
| 2 `:6` | event watcher with a heartbeat fallback, or a fixed heartbeat | X `/loop` `:6` → **wake** | none (platform tools) / chief-of-staff (in-progress) (narrower) | missing |  |
|  |  | router Subagents `:6` → **delegate** | delegation / chief-of-staff (in-progress) (wider) | same | a watcher subagent |
| 3 `:7-8` | smallest evidenced change per iteration; commit if it advanced (B8); discard what did not help | — | | | |
| 4 `:9` | fix supporting discoveries yourself; surface only irreversible or preference calls | router `poteto-mode` `:9` → **route** | mvp-mode / ask-matt (narrower) | same | conflicting rule: AGENTS.md:11-12 makes scope expansion an authorization gate |
| 5 `:10` | one row per iteration | S `show-me-your-work` `:10` → **decision-trail** | none (attempt record; Beads notes) / none (missing) | narrower | clean |
| 6 `:11` | stop only at the predicate; a plateau is not a stop | — | | | |

### 2.17 Orchestrate (`PB/orchestrate.md`)

**Recommendation: defer.** Built on Cursor cloud VMs, the Project tracker and PR subscriptions; ours runs programs through `execution` and the engine. Harvest the Supervision rules (kickoff names its evidence, read the diff not the summary, retry by cause) as phase-2 merge candidates for `delegation`.
`revisit_when`: a multi-day program runs outside the workflow engine.

- **Lacks (Cursor-only or outside pstack):** Cursor cloud agents (`environment: "cloud"`); Project tracker and store; PR and CI subscriptions.
- **Overlaps ours:** `execution` phase loop, contractor and child workflows (O/execution/SKILL.md:56-104); `delegation` dispatch and collect.
- **Principles named:** none named.
- **Reply contract:** `:25`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| intro `:5` | your own tools only; no scripts, no polling, never relay status | X `project-store` `:5` → **program-state** | Beads; run ledger / chief-of-staff wiki (narrower) | narrower |  |
|  |  | router Subagents `:5` → **delegate** | delegation / chief-of-staff (in-progress) (wider) | same |  |
| Topology `:9-14` | one owner per PR; fresh worker per task; sub-coordinators to three levels; fork for built state; non-author verifier; start with one unit | X `cloud-agent`, router Subagents `:10` → **delegate** | delegation / chief-of-staff (in-progress) (wider) | narrower | a cloud VM per worker |
| Supervision `:18-23` | kickoff names its evidence; read the diff; send back drift; check live state; replace stalls, retry by cause; ask only real decisions | — | | | |

### 2.18 Autopilot-full (`PB/autopilot-full.md`)

**Recommendation: defer.** A per-PR owner fleet that merges; needs PRs, CI, cloud agents and a swarm. Our independent child workflows cover only part (O/execution/SKILL.md:93-104).
`revisit_when`: we adopt a PR flow with CI.

- **Lacks (Cursor-only or outside pstack):** Cursor cloud agents; `deslop`; `control-ui`/`control-cli`; Cursor `/loop 1h`; Origin.
- **Overlaps ours:** `execution` independent child workflows.
- **Principles named:** none named.
- **Reply contract:** `:25`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| intro `:5` | a verdict covers one patch; a full swarm runs once | B Shipping `:5` → **ship-stack** (reference) | none (AGENTS.md merge rule) / none (missing) | missing | reference: Shipping's patch-id rule |
| 1 `:7` | the operator's gates first; a request to state the plan is not a go | — | | | |
| 2 `:8-12` | owner builds, opens, proves, babysits, merges; push before the next unit; force-push only own branch | X `cloud-agent` `:8` → **delegate** | delegation / chief-of-staff (in-progress) (wider) | narrower |  |
|  |  | B Opening a PR `:8` → **land** | none (AGENTS.md rules) / pr (narrower) | missing | carve-out: the owner may babysit (PB/opening-a-pr.md:34) |
|  |  | B Babysit `:8` → **pr-watch** | none / none (missing) | missing | carve-out: the owner may rebase (PB/babysit.md:10) |
|  |  | X `deslop` `:10` → **deslop** | none / none (missing) | missing |  |
|  |  | S `no-comments` `:10` → **comment-pass** | none / none (missing) | missing | clean |
|  |  | S `show-me-your-work` `:12` → **decision-trail** | none (attempt record; Beads notes) / none (missing) | narrower | clean: location is a parameter (P/skills/show-me-your-work/SKILL.md:46) |
| 3 `:13` | owners in parallel off trunk, never stacked | — | | | |
| 4 `:14-16` | block only on a shown problem | S `swarm` `:14` → **fan-out** | execution children / none (missing) | narrower | clean |
|  |  | X `control-skill` `:14` → **drive-surface** | none (run the CLI: own action) / none (missing) | missing |  |
| 5 `:17-19` | merge only what was verified on the trunk it lands on | — | | | |
| 6 `:20-22` | countersign gate loosening; hourly audit by side effects | X `/loop` `:22` → **wake** | none (platform tools) / chief-of-staff (in-progress) (narrower) | missing |  |
|  |  | S `ketchup` `:22` → **catch-up** | teach / none (missing) | narrower | clean |
| 7 `:23` | stand down on the operator's stop | — | | | |
| reply `:25` |  | S `ketchup` `:25` → **catch-up** | teach / none (missing) | narrower | clean |

### 2.19 Autopilot-stack (`PB/autopilot-stack.md`)

**Recommendation: defer.** Autopilot-full with two overrides.
`revisit_when`: Autopilot-full is adopted.

- **Lacks (Cursor-only or outside pstack):** everything Autopilot-full lacks.
- **Overlaps ours:** none.
- **Principles named:** none named.
- **Reply contract:** `:8`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| intro `:3` |  | B Autopilot-full `:3` → **autopilot** | none / none (missing) | missing | pstack FIRES, override (playbook to playbook): replaces its step 5 and excepts steps 2-3. Remedy: make merge a conditional branch of Autopilot-full. |
| 1 `:5` | stop at verified; nobody pushes after the hand-off | — | | | |
| 2 `:6` | stack a PR only on a PR it builds on | B Opening a PR `:6` → **land** (reference) | none (AGENTS.md rules) / pr (narrower) | missing | reference: its Size and stacks section |

### 2.20 Multi-phase plan (`PB/multi-phase-plan.md`)

**Recommendation: adapt.** Pilot order 2 (report §5.4). Its skeleton's go gate, owner fan-out, lanes and swarm are replaced by the §4.3 adaptations; the template rows below are recorded for completeness and not carried.

- **Lacks (Cursor-only or outside pstack):** `check-plan.mjs`; `poteto-agent`; ten `swarm` lanes through control skills on cloud VMs; Cursor `/loop 1h`; Bugbot; Origin; `deslop`.
- **Overlaps ours:** `planning` Decompose and Elaborate (O/planning/SKILL.md:24-62).
- **Principles named:** `never-block-on-the-human` (step 2, `:6`); `guard-the-context-window` (step 3, `:7`); `sequence-verifiable-units` (step 4, `:8`); `encode-lessons-in-structure` (step 6, `:10`); `prove-it-works` (step rule, `:13`).
- **Reply contract:** `:155`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| gate `:3` | the plan is the deliverable; do not implement | — | | | |
| 1 `:5` | *if one or two files with an obvious approach:* skip the plan, say so, stop | — | | | |
| 2 `:6` | settle open questions by prototype; ask only what no run settles (adapted, report §4.3) | B Prototype `:6` → **prototype** | prototype / prototype (wider) | same | pstack FIRES, override: keeps the evidence instead of Prototype's hand-off (PB/prototype.md:12). Ours: clean, since our prototype records the outcome in the task or report (O/prototype/SKILL.md:24-26). |
| 3 `:7` | explorers return pointers, conventions, test commands; no dumps | router `poteto-agent`, router Subagents `:7` → **delegate** | delegation / chief-of-staff (in-progress) (wider) | same | explorer role |
| 4 `:8` | fill the fixed skeleton; one section per PR; name the execution procedure → **plan** (`planning`, narrower: the skeleton branch is pilot 2's) | B Autopilot-full, B Autopilot-stack, B Orchestrate `:8` → **execute-plan** (select) | execution / implement-spec (wider) | same | a selection, not a call: the plan names one compatible `execution` scope (report §4.3); it runs later, on the operator's go, through the router |
| 5 `:9` | one Diátaxis mode in the body; no long dashes | S `technical-writing` `:9` → **tech-writing** | authoring-for-agents / pr; writing-for-agents (narrower) | narrower | pstack ambiguous: how-to body with explanation appendices in one file against one document, one mode (P/skills/technical-writing/SKILL.md:32) |
|  |  | S `unslop` `:9` → **prose-pass** | none / none (missing) | missing | clean |
| 6 `:10` | fix every line the lint prints | script `check-plan` `:10` → **plan-lint** (load) | none / none (missing) | missing |  |
| 7 `:11` | hand back the plan path and lint output; stop (go gate adapted, report §4.3) | — | | | |
| rule `:13-15` (not carried) | unit, live and perf boxes per PR (adapted: evidence from applicable checks, report §4.3) | S `swarm` `:13` → **fan-out** (template) | execution children / none (missing) | narrower | not carried (§4.3) |
|  |  | X `control-skill` `:13-15` → **drive-surface** (template) | none (run the CLI: own action) / none (missing) | missing | not carried |
| template `:17-153` (not carried) | the skeleton the executing owner runs | S `swarm` `:37` → **fan-out** (template) | execution children / none (missing) | narrower | re-read list; not carried |
|  |  | X `control-skill` `:38` → **drive-surface** (template) | none (run the CLI: own action) / none (missing) | missing | re-read list; not carried |
|  |  | B Opening a PR `:39` → **land** (template) | none (AGENTS.md rules) / pr (narrower) | missing | re-read list |
|  |  | X `/loop` `:41` → **wake** (template) | none (platform tools) / chief-of-staff (in-progress) (narrower) | missing | not carried |
|  |  | router Subagents `:45-47` → **delegate** (template) | delegation / chief-of-staff (in-progress) (wider) | same | one owner per PR; not carried as mandatory |
|  |  | X `built-in-pr-tool`, B Opening a PR `:57` → **land** (template) | none (AGENTS.md rules) / pr (narrower) | missing |  |
|  |  | X `deslop` `:59` → **deslop** (template) | none / none (missing) | missing |  |
|  |  | S `no-comments` `:59` → **comment-pass** (template) | none / none (missing) | missing |  |
|  |  | ref `bugbot-triage`, X `bugbot` `:60` → **bugbot-triage** (template) | review (feedback) / none (missing) | narrower |  |
|  |  | S `swarm` `:65` → **fan-out** (template) | execution children / none (missing) | narrower | not carried |
|  |  | B Shipping `:66-67` → **ship-stack** (template) | none (AGENTS.md merge rule) / none (missing) | missing |  |
|  |  | X `cloud-agent`, X `control-skill` `:71-75` → **drive-surface** (template) | none (run the CLI: own action) / none (missing) | missing |  |
|  |  | X `bugbot` `:129` → **bugbot-triage** (template) | review (feedback) / none (missing) | narrower |  |
|  |  | S `how` `:152` → **explain-code** (template) | none (router: answer from source); codebase-research / none (missing) | wider | reading list for owners |
|  |  | S `interrogate` `:152` → **adversarial-review** (template) | review / code-review (narrower) | narrower | reading list for owners |
|  |  | S `show-me-your-work` `:152` → **decision-trail** (template) | none (attempt record; Beads notes) / none (missing) | narrower | reading list for owners |

### 2.21 Session pickup (`PB/session-pickup.md`)

**Recommendation: adapt.** Pilot order 3 with Pause safely (report §5.4). Small step gaps; the value is one pickup procedure where today five files hold it.

- **Lacks (Cursor-only or outside pstack):** Cursor `agent-transcripts/` and cloud-agent URLs.
- **Overlaps ours:** AGENTS.md resume line (AGENTS.md:88-90); `beads` session start; `execution` workstream and task-engine recovery.
- **Principles named:** `guard-the-context-window` (step 1, `:5`); `prove-it-works` (step 5, `:9`).
- **Reply contract:** `:11`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| 1 `:5` | locate the trail; metadata and last messages first; never across projects → **session-trail** (`beads; execution recovery`, narrower: pilot 3: five files hold it today) | X `transcripts` `:5` → **transcripts** | none (Beads, handoff, Git) / handoff (narrower) | missing | local: ours: read Beads, the handoff, the ledger and Git |
|  |  | *if a long transcript:* router Subagents `:5` → **delegate** | delegation / chief-of-staff (in-progress) (wider) | same |  |
| 2 `:6` | reconstruct state; reuse the trail, verify consequential claims (adapted, report §4.3) → **session-trail** (`beads; execution recovery`, narrower: pilot 3) | — | | | |
| 3 `:7` | diff done against pending; name the resume point | — | | | |
| 4 `:8` | pick a verdict among four | router `poteto-mode` `:8` → **route** | mvp-mode / ask-matt (narrower) | same |  |
| 5 `:9` | verify inherited claims on the real artifact | — | | | |

### 2.22 Pause safely (`PB/pause-safely.md`)

**Recommendation: adapt.** Pilot order 3. The `wip:` commit is adapted to commit authority (report decision 13).

- **Lacks (Cursor-only or outside pstack):** `/tmp` resume file for Cursor compaction; Cursor restarts.
- **Overlaps ours:** `beads` pause (unclaim plus a resume note, O/beads/references/prime.md:87); workstream-mode persistence.
- **Principles named:** none named.
- **Reply contract:** `:10`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| 1 `:5` | stop at a safe boundary; cancel nested subagents | — | | | |
| 2 `:6` | no irreversible action to pause | — | | | |
| 3 `:7` | one `wip:` commit (conflicts with AGENTS.md:64; decision 13) | — | | | |
| 4 `:8` | resume note off-context; point at a trail instead of duplicating it → **session-trail** (`beads; execution recovery`, narrower: pilot 3) | *if a trail exists:* S `show-me-your-work` `:8` → **decision-trail** (pointer) | none (attempt record; Beads notes) / none (missing) | same | clean: a path to an existing trail, neither a call nor a load (St1) |

### 2.23 Worktree cleanup (`PB/worktree-cleanup.md`)

**Recommendation: adapt.** Adapt the Git half; defer simulators and Cursor caches. 'Clean and merged proceeds' becomes 'propose, prune on approval' (AGENTS.md:11-12; report §5.4).
`revisit_when`: simulator step: that tooling enters our toolchain.

- **Lacks (Cursor-only or outside pstack):** `worktree-audit.sh`; Cursor chat transcripts and the pinned-chat sidebar; `xcrun`; Cursor caches.
- **Overlaps ours:** none; the engine prunes only its own worktrees (report §4.2).
- **Principles named:** `build-the-lever` (step 1, `:3`); `encode-lessons-in-structure` (step 1, `:3`); `prove-it-works` (step 2, `:4`); `guard-the-context-window` (step 3, `:5`).
- **Reply contract:** `:12`.

| Step | Own actions (binds to ours) | Call → contract | Ours / Pocock | Fit | H9 and notes |
|---|---|---|---|---|---|
| 1 `:3` | record `df -h`; audit from `git worktree list`, never hand-typed paths | script `worktree-audit` `:3` → **worktree-audit** (load) | none / none (missing) | missing |  |
| 2 `:4` | the bucket is advice; the pinned set wins | — | | | |
| 3 `:5` | verify usage before deleting | router Subagents `:5` → **delegate** | delegation / chief-of-staff (in-progress) (wider) | same |  |
| 4 `:6` | pause on uncommitted work; show the diff | — | | | |
| 5 `:7` | prune the confirmed set; confirm with `df -h` | — | | | |
| 6 `:8` (not carried) | simulators and caches (deferred) | — | | | |

## 3. Skills needed

Every callee contract, ranked by live demand: the number of adopted or adapted
playbooks that need it, counted as the method states (§1). "(own)" marks a
playbook whose own action binds to the contract rather than calling it. Ties
are alphabetical. Contracts that only deferred playbooks need are at the end,
with demand 0. The Pocock column gives the candidate, then its own fit and
limitation.

Reading the ranking (J):

- `delegate` tops it but needs no new skill: ours fits. What changes is the
  wording of every adapted step, from "delegate with model X" to "delegate
  by the local rule, through `delegation`".
- `land`, `explain-code`, `design-first` and `prose-pass` are the first
  real work: high demand, and ours is missing, wider or narrower.
- `wake` ranks fifth but serves only conditional branches; it waits on its
  ruling (batch 4).
- `debug`, `perf-procedure`, `characterize`, `test-first`, `plan`,
  `session-trail` and `skill-authoring` already exist in ours; their merge
  questions belong to the pilots or to Pocock's phase-2 deliveries.

| # | Contract | pstack kind | Need (one line) | Live demand | Playbooks (adopt/adapt) | Deferred | pstack | Ours | Pocock | Merge question for phase 2 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **delegate** | router | hand a scoped job to a fresh subagent, then review its result yourself | 12 | Autonomous run, Bug fix, Eval, Feature, Hillclimb, Multi-phase plan, Perf issue, Refactoring, Runtime forensics, Session pickup, Trace forensics, Worktree cleanup | Autopilot-full, Orchestrate, Shipping | router Subagents section, `poteto-agent` (P/skills/poteto-mode/SKILL.md:94-102) | `delegation` roles and dispatch (O/delegation/SKILL.md:13-24, :37-49) | `chief-of-staff`, in-progress: all work in subagents (MP/skills/in-progress/chief-of-staff/SKILL.md:18-24); fit wider: makes all work subagent work and adds schedules and a wiki (MP/skills/in-progress/chief-of-staff/SKILL.md:14-38); manual-only (:4) | None for the call itself. pstack makes delegation mandatory with a model per role; ours delegates by AGENTS.md:42-43 and the roster. Adapted steps say 'delegate by the local rule' (report §4.3). |
| 2 | **land** | playbook | turn verified work into small ordered commits with conventional titles, then (with a PR flow) a PR | 7 | Authoring a skill, Bug fix, Feature, Hillclimb, Opening a PR (own), Perf issue, Refactoring | Autopilot-full, Autopilot-stack, Visual parity | Opening a PR, a rule set (PB/opening-a-pr.md:5-34) | AGENTS.md commit and staging rules (AGENTS.md:62-65); curation delivery by merge (harness_lifecycle/playbook.md:26) | `pr` PR body template (MP/skills/engineering/pr/SKILL.md:12-14); fit narrower: a PR-body template (MP/skills/engineering/pr/SKILL.md:12-33); no commit preparation or titles | A `land` skill (composite test: its rules still produce commits with the calls removed) whose PR branch is deferred? Every code playbook ends in it. |
| 3 | **explain-code** | skill | a cited explanation of how the affected code works, enough to change it safely | 6 | Bug fix, Feature, Hillclimb, Investigation, Perf issue, Refactoring | — | `how` (P/skills/how/SKILL.md:9-36) | no skill: the router says answer from the source (O/mvp-mode/SKILL.md:61); `codebase-research` deep dive for a durable report, whose inline branch answers a bounded question (O/codebase-research/SKILL.md:99-101, :152-162); router-only and aimed at external codebases (:3-4) | none; fit missing: no explain skill | New explain skill, or a local-code branch of `codebase-research`? It must be model-invocable (S7) and carry a decision branch with a tradeoffs table (Investigation's H9 seam). |
| 4 | **design-first** | skill | settle the types, signatures and module shape before code that crosses a function boundary | 4 | Bug fix, Feature, Perf issue, Refactoring | — | `architect`: ground, sketch by arena, opt-in agree, implement against the sketch, scrap (P/skills/architect/SKILL.md:21-77) | `codebase-design`: interface and depth checks; design-it-twice optional (O/codebase-design/SKILL.md:24-41) | `codebase-design` vocabulary and testability rules (MP/skills/engineering/codebase-design/SKILL.md:10-104); fit narrower: vocabulary and depth rules (MP/skills/engineering/codebase-design/SKILL.md:8-28); no sketch deliverable | Recommended: `codebase-design` gains a design-only sketch branch whose deliverable is the types, signatures and module shape; the calling playbook's next step implements against it and revises the sketch first if the code must diverge. No implement branch: that would recreate architect's Phase D seam (H9) on four edges (Bug fix 3, Perf issue 3, Feature 2, Refactoring 3). Design-it-twice stays optional (report §4.3). |
| 5 | **wake** | external | wake the run on an event or a heartbeat while it waits | 3 | Autonomous run, Bug fix, Hillclimb | Autopilot-full, Babysit, Shipping, Visual parity | Cursor `/loop` (PB/autonomous-run.md:6) | none; Claude Code's built-in loop and wakeups are platform tools, not units | `chief-of-staff` suggests schedules (MP/skills/in-progress/chief-of-staff/SKILL.md:14-16); fit narrower: suggests schedules where the harness permits (MP/skills/in-progress/chief-of-staff/SKILL.md:14-16); no wake mechanism | Owner ruling: platform tool per vendor, or the workflow engine's own wake? |
| 6 | **debug** | skill | reproduce the failure and diagnose its cause, with a status (confirmed, provisional, unresolved) | 2 | Bug fix (own), Runtime forensics (own) | — | own actions in Bug fix (PB/bug-fix.md:7-8) | `systematic-debugging`, now diagnosis-only (O/systematic-debugging/SKILL.md:8-27, :40-55); the bug-fix pilot owns the fix (O/mvp-mode/playbooks/bug-fix.md:42-68) | `diagnosing-bugs` feedback-loop phases (MP/skills/engineering/diagnosing-bugs/SKILL.md:18-35); fit wider: `diagnosing-bugs` goes on to the fix and a regression test (MP/skills/engineering/diagnosing-bugs/SKILL.md:114-126); ours is diagnosis-only | Settled by the bug-fix pilot (in progress in the worktree). |
| 7 | **decision-trail** | skill | an append-only log of decisions with evidence, read before each attempt; at the end, an audit against the run, an independent review and an Attention section (lifecycle in §3.2) | 2 | Autonomous run, Hillclimb | Autopilot-full | `show-me-your-work`: log (P/skills/show-me-your-work/SKILL.md:9-53), transcript audit (:55-63), cross-model review and Attention section (:65-74) | `performance-optimization` attempt record (O/performance-optimization/SKILL.md:30-32); Beads notes (O/beads/references/prime.md:87) | none; fit missing: no trail skill | Recommended: a new trail skill that takes caller columns (Hillclimb's H9 remedy) and keeps the audit, the review and the Attention section as adapted in §3.2; without a verified event record the review is an evidence-pointer review that names transcript coverage and unlogged-fork detection as unavailable under Attention. A Beads note points at the trail. Beads notes alone would drop the audit and the review. |
| 8 | **history** | skill | the motivation or regression history behind code, from git, tracker and docs | 2 | Bug fix, Investigation | — | `why` (P/skills/why/SKILL.md:1-5) | none; `research` weighs outside sources for a decision (O/research/SKILL.md:1-4) | none; fit missing: no history skill | A `why` branch of the explain skill (git log, Beads, ADRs), or its own skill? Keep why's confidence separation if it is reused. |
| 9 | **perf-procedure** | skill | metric, baseline, locate the cost, one factor at a time, compare under the same conditions | 2 | Hillclimb (own), Perf issue (own) | — | own actions in Perf issue and Hillclimb (PB/perf-issue.md:5-19) | `performance-optimization` (O/performance-optimization/SKILL.md:13-32) | `diagnosing-bugs` covers performance regressions (MP/skills/engineering/diagnosing-bugs/SKILL.md:1-4); fit narrower: `diagnosing-bugs` has a perf branch, measure then bisect (MP/skills/engineering/diagnosing-bugs/SKILL.md:112), inside a bug diagnosis; no tuning or comparison procedure | Do the seven mantras move into `performance-optimization` (two callers, promotion by reuse, St4)? |
| 10 | **prose-pass** | skill | remove AI tells from a reply or document a human reads | 2 | Investigation, Multi-phase plan | — | `unslop` (P/skills/unslop/SKILL.md:1-5) | none for human-facing prose; `authoring-for-agents` covers agent-facing text (O/authoring-for-agents/SKILL.md:1-4) | none (the `writing-*` skills are in-progress article drafting, MP/skills/in-progress/writing-shape/SKILL.md:1-4); fit missing: the `writing-*` skills draft articles | A user-facing prose pass: new skill, or a human-reader branch of `authoring-for-agents`' writing principles? |
| 11 | **review-diff** | skill | review a delegate's diff as the coordinator, independent of its author | 2 | Feature (own), Perf issue (own) | — | own action ('Review the diff', PB/perf-issue.md:17; review separation, PB/feature.md:12) | `review` (O/review/SKILL.md:10-17); `delegation` collect (O/delegation/SKILL.md:47-49) | `code-review` (MP/skills/engineering/code-review/SKILL.md:15-80); fit wider: always two parallel axis subagents against a fixed point (MP/skills/engineering/code-review/SKILL.md:6-23) | None: ours holds it. |
| 12 | **route** | router | match the remaining work to a playbook and run it | 2 | Autonomous run, Session pickup | — | `poteto-mode` playbook match (P/skills/poteto-mode/SKILL.md:122-150) | `mvp-mode` pick and run rules (O/mvp-mode/SKILL.md:20-43), being drafted by task 1a | `ask-matt` router (MP/skills/engineering/ask-matt/SKILL.md:1-3); fit narrower: an orientation router over flows, manual-only (MP/skills/engineering/ask-matt/SKILL.md:4-11); it runs nothing | None: the router is task 1a. |
| 13 | **session-trail** | skill | recover or leave the session state: the active bead, its notes and the handoff | 2 | Pause safely (own), Session pickup (own) | — | own actions in Session pickup and Pause safely (PB/session-pickup.md:5-7, PB/pause-safely.md:5-8) | `beads` session start, pause and close (O/beads/references/prime.md:85-87); `execution` workstream recovery (O/execution/references/workstream-mode.md:29-35) | `handoff` (MP/skills/productivity/handoff/SKILL.md:8-16); fit narrower: `handoff` writes the pause half only (MP/skills/productivity/handoff/SKILL.md:8-16); no pickup | Pilot 3 settles it (report §5.4). |
| 14 | **vet-measurement** | skill | vet each measured number (limiter, noise, errors, did the work happen) before acting on it | 2 | Hillclimb, Perf issue | — | `benchmark-checklist` (P/skills/benchmark-checklist/SKILL.md:1-5) | `performance-optimization` steps 2 and 5: variability, inconclusive within noise (O/performance-optimization/SKILL.md:15-28) | none; fit missing: no vetting procedure | A vetting branch or reference of `performance-optimization`, or its own skill (it is also asked for alone, S1)? |
| 15 | **adversarial-review** | skill | independent adversaries try to break a contested design; findings survive only with a run | 1 | Feature | — | `interrogate` (P/skills/interrogate/SKILL.md:9-27) | `review` critic: independent, severity, evidence (O/review/SKILL.md:10-25); no run-proof rule | `code-review`, standards and spec axes in parallel (MP/skills/engineering/code-review/SKILL.md:15-80); fit narrower: a two-axis diff review in parallel subagents (MP/skills/engineering/code-review/SKILL.md:6-11) whose smells are judgement calls (:38-41); no adversaries, no run-proof rule | Does `review` gain a run-proven adversarial mode, or is that a new skill? |
| 16 | **candidate-run** | script (load) | run each candidate as a fresh top-level session in its own sandbox copy, with the variant installed, the normal discovery surface and the organic prompt | 1 | Eval | — | `arena` Phase B through subagents (PB/eval.md:20) | the S8 runner: a fresh `cp -a` of a sandbox template per run, then headless `claude -p` with project settings only, no MCP servers, no session persistence, stream-JSON output (scratchpad/mvp-stack/s8/run.sh in the worktree; 22 runs in its results.md) | none; fit missing: no candidate runner | Promote the runner into `playbooks/eval/` (F3; a load, St1). Not `delegation`: a delegated task must not start a playbook (R8), and that is the behaviour under test. Add a second vendor's headless runner before cross-family candidates. |
| 17 | **candidates-judge** | skill | several candidate shapes for one build, then a pick and a graft of the best parts (Feature) | 1 | Feature | — | `arena` phases A-F (P/skills/arena/SKILL.md:9-48) | `model-council`: independent members, then a judge (O/model-council/SKILL.md:8-27); explicit request only (:3) | none; fit missing: no fan-out-and-pick skill | Feature is the only live caller (Eval binds to `candidate-run` and a `delegation` judge). Does `model-council` gain a pick-and-graft branch, and does a playbook step count as the explicit request it requires (S7, ruling 3)? |
| 18 | **characterize** | skill | pin current behaviour with a characterization test or equivalence harness before moving structure | 1 | Refactoring (own) | — | own action in Refactoring (PB/refactoring.md:7) | `test-driven-development` characterization (O/test-driven-development/SKILL.md:39-44) | `tdd` (MP/skills/engineering/tdd/SKILL.md:18-26); fit narrower: the red-green loop for new behaviour (MP/skills/engineering/tdd/SKILL.md:34-38); no characterization mode | None: ours holds it; Refactoring calls it. |
| 19 | **fix-perf** | playbook | fix a diagnosed slowness against a baseline, or borrow its mantra order | 1 | Hillclimb | — | Perf issue (PB/perf-issue.md:1-25) | Perf issue as adapted here | none; fit missing: no perf playbook | Hillclimb borrows only the mantras: move them into `performance-optimization` so both call the skill (H9 remedy). |
| 20 | **live-capture** | skill | capture and reduce an artifact of a live symptom (stacks, snapshots, contention) and stop at a cited diagnosis | 1 | Runtime forensics (own) | — | own action in Runtime forensics (PB/runtime-forensics.md:5-8) | `performance-optimization` recipes for live stacks and snapshots (O/performance-optimization/references/measurement-recipes.md:21-25), but its core goes on to change a factor and compare (O/performance-optimization/SKILL.md:24-29) | none; fit missing: no live-process capture | Recommended: a diagnosis-only branch of `performance-optimization` (condition: the caller asks for the cause, not a change), whose deliverable is the located cost with its evidence; steps 4-5 do not run on it (S4). Alternative: move the live recipes into a capture skill (F2). |
| 21 | **plan** | skill | decompose settled work into a durable plan with dependencies and evidence per unit | 1 | Multi-phase plan (own) | — | own actions in Multi-phase plan (PB/multi-phase-plan.md:4-11) | `planning` Decompose and Elaborate (O/planning/SKILL.md:24-62) | `to-spec`, `to-tickets` (MP/skills/engineering/to-tickets/SKILL.md:13-58); fit narrower: tracer-bullet tickets with blocking edges (MP/skills/engineering/to-tickets/SKILL.md:9, :25-38); no evidence boxes or execution scope | Does `planning` gain the per-unit skeleton (evidence boxes, a named execution procedure) as a branch, so the playbook calls it whole? |
| 22 | **plan-lint** | script (load) | a script that lints the plan file | 1 | Multi-phase plan | — | `check-plan.mjs` (PB/multi-phase-plan.md:10) | none | none; fit missing: no plan lint | Write a plan lint for our skeleton with `planning` (encode-lessons-in-structure). A load, not a call (St1); it lives beside its owner (F3). |
| 23 | **prototype** | playbook | settle an observable design question with a throwaway build, and record what it showed | 1 | Multi-phase plan | — | Prototype playbook (PB/prototype.md:7-14) | `prototype` skill (O/prototype/SKILL.md:8-28) | `prototype` (MP/skills/engineering/prototype/SKILL.md:6-26); fit wider: logic and UI branches (MP/skills/engineering/prototype/SKILL.md:10-17) plus a capture duty: fold the decision into real code and commit the prototype to a branch (:26) | Fold pstack's switcher and recommendation into our skill (see Prototype); Pocock waits for phase 2. |
| 24 | **run-events** | external | a workspace-scoped record of what each candidate run actually did (skills invoked, files read, edits), keyed to its run | 1 | Eval | — | Cursor `agent-transcripts/`, this workspace only (PB/eval.md:22) | the run's stream-JSON tool events, one log per run named by its run id, which is also its sandbox directory; the S8 classifier reads Skill, Read, Edit, Write and Bash inputs from them (scratchpad/mvp-stack/s8/classify.py in the worktree). As reviewed, it reads tool-use inputs only, so any input naming the playbook counts as a read: a `test -f`, a Grep for the filename and a failed Read all score as reads (critic 1e round 2) | none; fit missing: no event source | Verified as a source for headless Claude Code runs only (S8 baseline). Promote the classifier beside the runner (F3), with per-variant patterns, only once it matches each tool call to its result and counts only successful content reads and skill invocations, with false-positive checks (`test -f`, a Grep for the filename, a failed Read) that it scores as no read. That is a readiness condition of batch 0 (ruling 10); this map does not claim the classifier meets it. Until another vendor's event stream is verified, Eval's chain check is unavailable for that vendor. |
| 25 | **skill-authoring** | external | write or edit a skill to the local authoring standard | 1 | Authoring a skill | — | Cursor's built-in `create-skill` (PB/authoring-a-skill.md:5) | `authoring-for-agents` (O/authoring-for-agents/SKILL.md:11-50) | `writing-for-agents` (MP/skills/productivity/writing-for-agents/SKILL.md:1-4); fit narrower: writing guidance for agent documents (MP/skills/productivity/writing-for-agents/SKILL.md:3-8); no validation of frontmatter or links | None: ours holds it. |
| 26 | **skill-delivery** | playbook | one path for every skill change: evidence, ruling, build, verify, delivery | 1 | Authoring a skill (own) | — | Authoring a skill (PB/authoring-a-skill.md:5-8) | `harness_lifecycle/playbook.md` §2 (harness_lifecycle/playbook.md:17-26) | none; fit missing: no delivery path | Where it lives and whether the router lists it: report decision 15 (open). |
| 27 | **tech-writing** | skill | write a plan, doc or PR text to a layered style standard | 1 | Multi-phase plan | — | `technical-writing` (P/skills/technical-writing/SKILL.md:1-5) | `authoring-for-agents` for agent-facing documents (O/authoring-for-agents/SKILL.md:11-38) | `pr` for PR bodies (MP/skills/engineering/pr/SKILL.md:1-14); `writing-for-agents` (MP/skills/productivity/writing-for-agents/SKILL.md:1-4); fit narrower: `pr` writes a PR body only (MP/skills/engineering/pr/SKILL.md:12-33); `writing-for-agents` covers agent-facing documents only (MP/skills/productivity/writing-for-agents/SKILL.md:3-6) | Is a plan agent-facing (then `authoring-for-agents` owns it) or human-facing (then it needs the prose-pass skill)? |
| 28 | **test-first** | skill | a failing test first when the bug or behaviour has a cheap local test; skip otherwise | 1 | Bug fix | — | `tdd` (P/skills/tdd/SKILL.md:1-11) | `test-driven-development` test-first and characterization modes (O/test-driven-development/SKILL.md:8-44) | `tdd` (MP/skills/engineering/tdd/SKILL.md:1-38); fit wider: adds a gate: every seam is confirmed with the user before any test (MP/skills/engineering/tdd/SKILL.md:22-24) | None for the call: both sides carve out the expensive test (h9 carve-out). Pocock's tdd waits for phase 2 (CONTEXT ruling). |
| 29 | **worktree-audit** | script (load) | classify worktrees by merge state, dirt and use from `git worktree list` | 1 | Worktree cleanup | — | `worktree-audit.sh` (PB/worktree-cleanup.md:3) | none | none; fit missing: no audit script | Write our own audit script with the Git half of the playbook, in `playbooks/worktree-cleanup/` (F3); a load (St1). |
| 30 | **autopilot** | playbook | the PR-owner fleet it modifies | 0 | — | Autopilot-stack | Autopilot-full (PB/autopilot-full.md:7-25) | none | none; fit missing: no PR fleet | Deferred with Autopilot-full. |
| 31 | **bugbot-triage** | external | triage automated review comments skeptically | 0 | — | Babysit | Bugbot and `references/bugbot-triage.md` (PB/babysit.md:20) | `review` feedback mode (O/review/SKILL.md:32-34) | none; fit missing: no triage reference | Deferred: no review bots. |
| 32 | **catch-up** | skill | tell the operator what changed and what waits on them | 0 | — | Autopilot-full | `ketchup` (P/skills/ketchup/SKILL.md:1-5) | `teach` session walkthrough (O/teach/SKILL.md:15-17) | none; fit missing: no catch-up skill | Only Autopilot-full calls it (deferred). |
| 33 | **comment-pass** | skill | strip comments that do not carry a non-obvious why, before review | 0 | — | Autopilot-full | `no-comments`, which spawns the `comment-sicko` agent (P/skills/no-comments/SKILL.md:1-5) | none | none; fit missing: no comment pass | Part of the land contract or dropped; decide with land. |
| 34 | **deslop** | external | strip AI slop from a code diff before commit | 0 | — | Autopilot-full | `deslop` from `cursor-team-kit` (PB/opening-a-pr.md:9); not in pstack | none | none; fit missing: no diff cleanup | Cursor-only: out unless an equivalent is adopted with land. |
| 35 | **drive-surface** | external | drive the real surface (UI, CLI) the way a user does, to reproduce or verify | 0 | — | Autopilot-full, Shipping, Visual parity | `control-ui`, `control-cli` from `cursor-team-kit` (P/skills/poteto-mode/SKILL.md:31) | none; for our CLI and Python surfaces the step runs the command itself (.repo-context/verification.md:11-19, 'driven end to end') | none; fit missing: no surface driver | No skill for CLI surfaces: own action. Revisit when a UI surface enters scope (report decision 14). |
| 36 | **fan-out** | skill | fan N workers over a partition, drain them, return one report | 0 | — | Autopilot-full | `swarm` (P/skills/swarm/SKILL.md:9-41) | `execution` independent child workflows (O/execution/SKILL.md:93-104) | none; fit missing: no fan-out skill | Only deferred playbooks and Multi-phase plan's template call it; no phase-2 work. |
| 37 | **pr-watch** | playbook | drive a PR to merge-ready on the forge's verdict | 0 | — | Autopilot-full, Babysit, Shipping | Babysit and `watch-pr` (PB/babysit.md:7-23) | none; no CI (.repo-context/verification.md:8-9) | none; fit missing: no PR watcher | Deferred with Babysit. |
| 38 | **program-state** | external | a durable program record outside the chat | 0 | — | Orchestrate | Cursor Project tracker and store (PB/orchestrate.md:5) | Beads and the run ledger (O/execution/SKILL.md:56-91) | `chief-of-staff` wiki (MP/skills/in-progress/chief-of-staff/SKILL.md:26-30); fit narrower: a dated history wiki (MP/skills/in-progress/chief-of-staff/SKILL.md:26-45), not a program record | Deferred with Orchestrate. |
| 39 | **ship-stack** | playbook | land a verified PR stack bottom-up; reuse verdicts by `git patch-id` | 0 | — | Autopilot-full | Shipping (PB/shipping.md:5-10) | AGENTS.md merge rule (AGENTS.md:66-68) | none; fit missing: no stack landing | Deferred with Shipping. |

### 3.1 Dependencies that are not skill demand

These contracts are what a playbook hands off to, selects for a later run or
points at, and the calls our version replaces with a local own action. None
is skill demand. A hand-off target goes live with its own playbook; a
selection is checked when the later run is drafted; a local call needs no
skill for our surfaces and is revisited when a UI surface or a new vendor
enters scope.

| Contract | Kind | Live playbooks (how) | Deferred | Ours |
|---|---|---|---|---|
| **build-feature** | playbook | Investigation (handoff), Prototype (handoff) | — | Feature (here) |
| **decision-trail** | skill | Pause safely (pointer) | — | none (attempt record; Beads notes) |
| **design-first** | skill | Prototype (handoff) | — | codebase-design |
| **drive-surface** | external | Bug fix (local), Perf issue (local), Prototype (local), Refactoring (local), Runtime forensics (local) | — | none (run the CLI: own action) |
| **execute-plan** | playbook | Multi-phase plan (select) | — | execution |
| **fix-bug** | playbook | Investigation (handoff), Runtime forensics (handoff), Trace forensics (handoff) | — | Bug fix (pilot) |
| **fix-perf** | playbook | Runtime forensics (handoff), Trace forensics (handoff) | — | Perf issue (here) |
| **ship-stack** | playbook | — | Babysit | none (AGENTS.md merge rule) |
| **transcripts** | external | Session pickup (local) | — | none (Beads, handoff, Git) |

### 3.2 The decision-trail lifecycle

`show-me-your-work` is more than its log. The trail skill phase 2 writes
(ruling 9) must dispose of each of its requirements; each disposition is a
judgement (J).

| Requirement | pstack | Disposition | Dependency it brings |
|---|---|---|---|
| One TSV log, one row per decision, evidence as a pointer | `P/skills/show-me-your-work/SKILL.md:13-22` | Retain | none |
| Caller-supplied columns | Hillclimb overrides the header (`PB/hillclimb.md:9`) | Adapt: the skill takes caller columns, which is Hillclimb's H9 remedy | none |
| `start` rows mark another run's stretch | `P/skills/show-me-your-work/SKILL.md:42` | Retain: Session pickup reads them | none |
| Local by default; commit when a reviewer needs it | `P/skills/show-me-your-work/SKILL.md:44-48` | Adapt: under the gitignored `scratchpad/`; committing needs authority (B8) | none |
| Append-only; supersede, never edit | `P/skills/show-me-your-work/SKILL.md:52` | Retain | none |
| End-of-run audit against the run's transcript | `P/skills/show-me-your-work/SKILL.md:55-63` | Adapt: always check that each row's evidence resolves and that unlogged forks are gaps; walk an event record only where a workspace-scoped one exists (`run-events`, headless runs). Reject the Cursor `agent-transcripts/` path | `run-events`, conditional |
| Review of trail and transcript by another model family | `P/skills/show-me-your-work/SKILL.md:65-72` | Adapt: a critic through `delegation`; a different family by the roster when one is available; never self-review. Its inputs depend on the record: with a verified workspace-scoped event record, the trail and that record (a full trail audit); without one, the trail and the evidence each row points at (an evidence-pointer review, below) | `delegate`; `run-events` for the full audit only |
| Reply ends in an Attention section naming the reviewer | `P/skills/show-me-your-work/SKILL.md:74` | Retain as the skill's required output; the calling playbook folds it into its reply with its content intact (B3). After an evidence-pointer review it also names transcript coverage and unlogged-fork detection as unavailable | none |

**Runs without a verified event record (J).** Recommended: the
evidence-pointer review. The critic checks the trail against the evidence
pointers it cites and reports, under Attention, that transcript coverage and
unlogged-fork detection were unavailable; only a run with a verified
workspace-scoped record gets the full trail audit. Attended Hillclimb, which
has no such record today (`run-events` is verified for headless Claude Code
runs only), goes live in batch 2 on this review. Alternative: require a
verified record before any review. That keeps every review full, but blocks
attended Hillclimb in batch 2 until a record for attended runs is verified.

Pause safely only points at an existing trail (`PB/pause-safely.md:8`), so it
appears in §3.1 as a pointer and adds no demand: the live callers are
Hillclimb and Autonomous run. A Beads note can point at the trail; Beads
notes alone would drop the audit and the review.

## 4. H9 (B3) risks

Every call whose pstack class is not clean. Started from the study's
`h9-cases.yaml` and re-verified against the callee lines (for example
`P/skills/arena/SKILL.md:9`, `P/skills/architect/SKILL.md:51`,
`P/skills/show-me-your-work/SKILL.md:15-22`, `P/skills/why/SKILL.md:88`,
`P/skills/technical-writing/SKILL.md:32`, `:94`). No class moved: on
playbook-to-skill calls this matches the study's 2 fire (Eval's arena row
spans steps 4 and 5), 7 ambiguous and 2 carve-outs; on playbook-to-playbook
calls, 4 fire.

What changes once the calls bind to our units (J):

- **Disappears.** Multi-phase plan → Prototype fires in pstack (the plan
  keeps the evidence instead of Prototype's hand-off) but is clean on ours:
  our `prototype` records the outcome in the task or report
  (`O/prototype/SKILL.md:24-26`). Eval → arena disappears by rebinding: the
  candidates go to `candidate-run` and the judge to a `delegation` critic
  with the rubric, so no `model-council` core is skipped or overridden
  (`O/model-council/SKILL.md:23-25`).
- **Disappears on a condition.** The four `architect` Phase D ambiguities
  (Bug fix 3, Perf issue 3, Feature 2, Refactoring 3) do not arise if the
  `codebase-design` sketch branch stays design-only and the playbook's build
  step implements against the sketch (ruling 5). An implement branch in the
  skill would bring them back.
- **Carries over, with a remedy for phase 2.** Hillclimb → show-me-your-work
  needs a trail skill that takes caller columns (§3.2). Hillclimb's two
  borrows from playbooks resolve by calling the contract, not the playbook:
  the mantras move into `performance-optimization`, and the wake is its own
  contract.
- **New on our side.** Investigation → explain: our explain skill must hold
  the decision branch (a recommendation with a tradeoffs table) so the call
  stays whole. Calling a wider unit of ours whole is the main B3 risk in this
  map: `codebase-research` for a local question, and `performance-optimization`
  for Runtime forensics' diagnosis-only capture, whose core goes on to tune.
  Each needs a branch whose condition the caller meets (S4). Multi-phase plan
  only selects an `execution` scope for a later run, so it carries no B3 risk
  now.
- **Deferred with their playbooks.** Autopilot-stack → Autopilot-full
  (override), the reference rows of Babysit, Shipping and Opening a PR, and
  the carve-out in Opening a PR's deferred PRs section.

| Caller step | Callee | pstack class (re-verified) | Our binding |
|---|---|---|---|
| Investigation 1 `PB/investigation.md:7` | S `how` | ambiguous | step 3's recommendation table may replace how's output sections (PB/investigation.md:9; P/skills/how/SKILL.md:32-36). Ours: give the explain skill a decision branch, so the call stays whole. |
| Investigation 1 `PB/investigation.md:7` | S `why` | ambiguous | why keeps its confidence separation and sources line (P/skills/why/SKILL.md:92); a how-shaped reply may drop them. Ours: the reply keeps why's required content (B3 fold rule). |
| Bug fix 3 `PB/bug-fix.md:9` | S `architect` | ambiguous | does the delegate run architect's Phase D (P/skills/architect/SKILL.md:51)? Ours: clean only if the sketch branch stays design-only and step 3's delegate implements against the sketch (ruling 5). |
| Bug fix 5 `PB/bug-fix.md:11` | S `tdd` | carve-out on both sides | tdd says do not force an impractical test (P/skills/tdd/SKILL.md:11); ours proves the regression when feasible (O/test-driven-development/SKILL.md:35-37) |
| Perf issue 3 `PB/perf-issue.md:17` | S `architect` | ambiguous | Phase D, as Bug fix. Ours: clean on the same condition; step 3's delegate implements against the sketch |
| Hillclimb 3 `PB/hillclimb.md:9` | S `show-me-your-work` | FIRES, override | its own columns replace the fixed header (P/skills/show-me-your-work/SKILL.md:15-22). Remedy: the trail skill takes caller columns. |
| Hillclimb 4 `PB/hillclimb.md:10` | B Perf issue | FIRES, skip (playbook to playbook) | the mantra order without its stop rule. Remedy: the mantras move into `performance-optimization` as an ordered list both callers use. |
| Hillclimb 5 `PB/hillclimb.md:16` | B Autonomous run | FIRES, skip | the wake without the stop rule. Remedy: call the wake contract directly, not the playbook. |
| Feature 2 `PB/feature.md:6` | S `architect` | ambiguous | step 4 delegates the code; Phase D unstated. Ours: clean if the sketch branch is design-only; step 4 implements against the sketch |
| Refactoring 3 `PB/refactoring.md:9` | S `architect` | ambiguous | step 5 moves the code; Phase D unstated. Ours: clean if the sketch branch is design-only; step 5 moves the code against the sketch |
| Eval 4 `PB/eval.md:20` | S `arena`, router Subagents | FIRES, skip | arena Phase B only (arena opens six phase todos, P/skills/arena/SKILL.md:9). Ours: bound to `candidate-run`, not `model-council` or `delegation`, so no partial call remains. R8 does not apply: a candidate is a top-level session, not a delegated task |
| Eval 5 `PB/eval.md:21` | S `arena` | FIRES, skip, with step 4 | arena Phase C only. Ours: the judge is a `delegation` critic whose brief holds the rubric and sanitized labels, so no `model-council` judge brief is overridden (O/model-council/SKILL.md:23-25) |
| Opening a PR PRs `PB/opening-a-pr.md:9` | S `technical-writing` | carve-out | every layer except Diátaxis is the callee's own PR rule (P/skills/technical-writing/SKILL.md:94) |
| Opening a PR Size and stacks `PB/opening-a-pr.md:28` | B Shipping | reference | borrows Shipping's step 4 |
| Shipping 5 `PB/shipping.md:9` | B Babysit, script `watch-pr` | reference | Babysit's watcher script |
| Autopilot-full intro `PB/autopilot-full.md:5` | B Shipping | reference | Shipping's patch-id rule |
| Autopilot-full 2 `PB/autopilot-full.md:8` | B Opening a PR | carve-out | the owner may babysit (PB/opening-a-pr.md:34) |
| Autopilot-full 2 `PB/autopilot-full.md:8` | B Babysit | carve-out | the owner may rebase (PB/babysit.md:10) |
| Autopilot-stack intro `PB/autopilot-stack.md:3` | B Autopilot-full | FIRES, override (playbook to playbook) | replaces its step 5 and excepts steps 2-3. Remedy: make merge a conditional branch of Autopilot-full. |
| Autopilot-stack 2 `PB/autopilot-stack.md:6` | B Opening a PR | reference | its Size and stacks section |
| Multi-phase plan 2 `PB/multi-phase-plan.md:6` | B Prototype | FIRES, override | keeps the evidence instead of Prototype's hand-off (PB/prototype.md:12). Ours: clean, since our prototype records the outcome in the task or report (O/prototype/SKILL.md:24-26). |
| Multi-phase plan 5 `PB/multi-phase-plan.md:9` | S `technical-writing` | ambiguous | how-to body with explanation appendices in one file against one document, one mode (P/skills/technical-writing/SKILL.md:32) |

## 5. Phase-2 order

It starts after the bug-fix pilot. Each batch is a set of skill changes,
chosen so the most playbooks go live soonest. A playbook is live when every
carried call and bind of a demand kind fits `same` or is local, or the owner
accepts an interim binding; the generated table below lists what still
blocks each one. Pocock's deliveries join the batch that touches the same
skill (they wait for phase 2, per the rulings in force).

| Batch | Skill work | Brings live | Why this order (J) |
|---|---|---|---|
| 0 | No skill work. Loads only (F3): promote the S8 runner and classifier into Eval's references; write Worktree cleanup's audit script. Readiness condition for Eval: the classifier matches each tool call to its result and counts only successful content reads and skill invocations, and passes false-positive checks (`test -f`, a Grep for the filename, a failed Read) | Trace forensics; Eval, for Claude Code candidates (ruling 10); Worktree cleanup (Git half); pilots 2-4 as scheduled (report §5.4) | Trace forensics needs only `delegate` and hand-offs. Eval's candidate surface and transcript source already ran in the S8 baseline (22 runs); its chain check stays unavailable for other vendors until their event streams are verified |
| 1 | `land`; `explain-code` with a `why` branch and a decision branch; a design-only sketch branch in `codebase-design`; `prose-pass` | Refactoring, Investigation, Opening a PR (as `land`), Feature (with interim bindings, ruling 8); Bug fix, except its long-hunt wake branch | The four contracts with the highest live demand that ours lacks or only partly holds (§3: 7, 6, 4 and 2 playbooks; `history` rides in the explain skill). Every code playbook ends in `land` |
| 2 | `vet-measurement`; the seven mantras into `performance-optimization`; its diagnosis-only branch (`live-capture`); `decision-trail` per §3.2, whose critic runs the evidence-pointer review when a run has no verified event record (ruling 9) | Perf issue, Hillclimb (attended; under ruling 9's alternative, only once a record for attended runs is verified), Runtime forensics | All three touch `performance-optimization`; the two Hillclimb H9 remedies and Runtime forensics' B3 remedy land in one change |
| 3 | `candidates-judge` (`model-council` pick-and-graft, after ruling 3); `adversarial-review` (a run-proven mode in `review`) | Feature's arena and interrogate branches at full fit | Conditional branches with one caller each; interim bindings carry Feature until then |
| 4 | `wake`, after its ruling | Autonomous run; Hillclimb unattended; Bug fix's long-hunt branch | One ruling unblocks three conditional branches; nothing else waits on it |

Multi-phase plan's own gaps (`plan` skeleton branch, `plan-lint`,
`tech-writing`) and the Prototype skill delta belong to pilot 2, not to a
batch; it also needs `prose-pass` from batch 1. Session pickup and Pause
safely belong to pilot 3, Authoring a skill to ruling 1. Opening a PR's
`land` gap and Authoring a skill's narrower one both close with batch 1.

Blocking contracts per live playbook (generated from the data; local calls
and the §3.1 kinds excluded):

| Playbook | Blocking contracts (fit) |
|---|---|
| Investigation | explain-code (wider), history (missing), prose-pass (missing) |
| Runtime forensics | live-capture (wider) |
| Trace forensics | none |
| Bug fix | design-first (narrower), explain-code (wider), history (missing), land (missing), wake (missing) |
| Perf issue | design-first (narrower), explain-code (wider), land (missing), perf-procedure (narrower), vet-measurement (narrower) |
| Hillclimb | decision-trail (narrower), explain-code (wider), land (missing), perf-procedure (narrower), vet-measurement (narrower), wake (missing) |
| Feature | adversarial-review (narrower), candidates-judge (conflicting), design-first (narrower), explain-code (wider), land (missing) |
| Refactoring | design-first (narrower), explain-code (wider), land (missing) |
| Prototype | none |
| Authoring a skill | land (narrower) |
| Eval | candidate-run (narrower), run-events (narrower) |
| Opening a PR | land (missing) |
| Autonomous run | decision-trail (narrower), wake (missing) |
| Multi-phase plan | plan (narrower), plan-lint (missing), prose-pass (missing), tech-writing (narrower) |
| Session pickup | session-trail (narrower) |
| Pause safely | session-trail (narrower) |
| Worktree cleanup | worktree-audit (missing) |

## 6. Playbook groups

Drafts in one group are written together because they share callees, a
reply shape or an H9 remedy.

| Group | Playbooks | Written with | Shared (J) |
|---|---|---|---|
| pilot | Bug fix; Multi-phase plan; Session pickup + Pause safely; Authoring a skill | the Prototype skill delta, with Multi-phase plan | Already scheduled (report §5.4) |
| forensics | Runtime forensics, Trace forensics | the `performance-optimization` diagnosis-only branch (batch 2) | Same reply shape (a cited diagnosis, no fix), the same parse-in-a-subagent step, the same hand-backs to Bug fix and Perf issue; each names the other as its boundary |
| understand | Investigation | the explain skill (batch 1) | Its H9 seam defines the explain skill's decision branch |
| build | Feature, Refactoring | the `land` skill and the sketch branch (batch 1) | Explain, design-first, delegate, ordered commits and `land`; both implement against the sketch |
| measure | Perf issue, Hillclimb | the `performance-optimization` changes (batch 2) | The mantras, measurement vetting and the attempt record; both H9 remedies |
| eval | Eval | the S8 runner and classifier, promoted as its references | Its candidates are top-level sessions, not delegates; only the judge is delegated |
| long run | Autonomous run | the wake ruling and the trail skill | Its wake also serves Hillclimb and Bug fix |
| housekeeping | Worktree cleanup | its audit script | Deletion gate under AGENTS.md:11-12 |
| deferred | Babysit, Shipping, Autopilot-full, Autopilot-stack, Opening a PR's PR sections; Visual parity; Orchestrate | revisit together when a PR flow with CI is adopted; Visual parity when a UI surface is; Orchestrate when a program runs outside the engine | One PR lifecycle; Orchestrate's supervision rules are harvested into `delegation` meanwhile |

## 7. Owner rulings

### 7.1 Settled constraints (not rulings)

The map follows these; none needs the owner unless a policy change is wanted,
and none is proposed.

1. **Scope authority.** Autonomous run step 4 fixes in-scope discoveries; out-of-scope ones become `discovered-from` beads, never a standing scope grant (AGENTS.md:11-12).
2. **Whole calls.** Every partial call is remedied by a branch of the callee (S4) or a split, and a playbook-to-playbook borrow by calling the shared contract instead of the playbook (B3, B10). Hillclimb's two borrows follow this.
3. **Costly opt-ins.** `model-council` stays manual-only (S7) while ruling 3 is open, so Feature's "several valid shapes" branch cannot start a council by itself.
4. **Delegated tasks.** A delegate never starts a playbook (R8). Eval's candidates are top-level sessions, so Eval needs no deviation.
5. **Delegation wording.** Adapted steps delegate by the local rule and roster, never by pstack's per-role model lines (AGENTS.md:42-43; report §4.3).
6. **Authority.** Commits, amends and pushes run only with authority (B8; AGENTS.md:62-65); a stopped path still runs its closeout (B7) but gains no commit authority from it.
7. **Pocock.** Pocock deliveries wait for phase 2; the Pocock fits in this map are inputs to that phase.
8. **Shape of the drafts.** Each playbook's step list goes in its frontmatter (B12); its scripts and references move beside it (F3); a skill names a playbook only as a route back through the router (B11), which binds the Prototype skill's hand-offs.

### 7.2 Open rulings

Seventeen, each with a recommendation (J), its trade-off and what it blocks.

**Ruled 2026-11-01: all seventeen as recommended.** Ruling 1 follows pstack
report decision 15 (a): the curation playbook stays unrouted by the shipped
router, since routing it would leak a root-only line into the plugin; the
deviation is logged in `.repo-context/unit-kinds.md` §5.

| # | Ruling | Recommendation | Trade-off | Blocks |
|---|---|---|---|---|
| 1 | **Authoring a skill** placement (report decision 15) | Keep `harness_lifecycle/playbook.md` where it is as a logged B1/R3 deviation, listed by the router by path | No file move, but a playbook outside `mvp-mode/playbooks/` that the plugin excludes | the pilot |
| 2 | **Opening a PR**: Commits and Titles as a `land` skill now, the rest deferred (departs from report §5.4) | Yes | Every code playbook gains a closeout now; `land` is revised again when a PR flow arrives | batch 1 (7 playbooks) |
| 3 | **`model-council` in playbooks**: proposed S7 deviation, a playbook step whose condition holds counts as the explicit request | No: keep manual-only; Feature's branch asks the user before a council, and runs the interim binding otherwise | Cost stays opt-in; Feature's arena branch stays narrower until the user opts in | batch 3 |
| 4 | **Explain**: a new skill, or a local-code branch of `codebase-research` | A new model-invocable explain skill for local code, with `why` and decision branches; `codebase-research` stays on external codebases | One more invocable description, against widening a router-only skill aimed elsewhere and flipping its S7 status | batch 1 (6 playbooks) |
| 5 | **Design-first**: what `codebase-design` gains | A design-only sketch branch (types, signatures, module shape); the playbook's build step implements against it and revises the sketch first if the code must diverge; design-it-twice stays optional | The playbooks carry the implement-against-the-sketch action; an implement branch would recreate the Phase D seam on four edges | batch 1 (4 playbooks) |
| 6 | **Prose pass**: new skill, a branch of `authoring-for-agents`, or drop the steps | A new user-facing prose skill that cites the shared writing principles | One more skill, against mixing human-reader rules into an agent-facing standard, or losing Investigation's step 4 | batch 1 (Investigation); pilot 2 |
| 7 | **Feature's build step**: `execution`'s task scope, or its own delegation | Feature delegates the build through `delegation` with a task brief; `execution` stays the procedure plans select | No run ledger for a Feature build, against nesting a playbook-like unit in a playbook (B10, B3) | batch 1 (Feature) |
| 8 | **Feature's interim bindings** until batch 3 | Yes: design-it-twice for "several valid shapes", a `review` critic for "contested design" | Feature is live two batches sooner with weaker pick-and-graft and no run-proven adversaries | batch 1 (Feature) |
| 9 | **Decision trail**: a trail skill, or Beads notes; and the review for runs without a verified event record | A new trail skill with caller columns and the §3.2 dispositions; a Beads note points at the trail. Without a verified workspace-scoped record, the critic runs an evidence-pointer review and Attention names transcript coverage and unlogged-fork detection as unavailable; a full trail audit needs a verified record. Alternative: require a verified record before any review | One more skill and a critic per trail run, against losing the audit and the review. The evidence-pointer review lets attended Hillclimb go live with a weaker review; the alternative keeps every review full but holds attended Hillclimb out of batch 2 until a record is verified | batch 2 (Hillclimb); batch 4 (Autonomous run) |
| 10 | **Eval's interim scope** | Live with Claude Code candidates only: the S8 runner and stream-JSON events, judge through `delegation`; cross-family candidates wait for a second vendor's runner and event stream. The classifier is promoted only once it matches each tool call to its result, counts only successful content reads and skill invocations, and passes false-positive checks (`test -f`, a Grep for the filename, a failed Read) | Live in batch 0, but it cannot compare vendors, and the classifier must be fixed and checked first | batch 0 (Eval) |
| 11 | **Measurement**: vetting, the mantras and diagnosis-only capture | All three in `performance-optimization`: a vetting branch, the mantras as an ordered list, a diagnosis-only branch; vetting becomes its own skill only if it is asked for alone (S1) | A larger mixed-role skill (a known deviation), against three small skills with one or two callers each | batch 2 (3 playbooks) |
| 12 | **Wake**: per-vendor platform tools, or the workflow engine's own wake | A `wake` contract met by each vendor's platform tool in chat runs; the engine's wake only for runs the engine owns | The playbook text names the outcome, not a tool, against requiring the engine for every long run | batch 4 (3 branches) |
| 13 | **Prototype** stays a skill and gains variants behind one switcher and a recommendation with tradeoffs | Yes; its hand-offs name Feature only as a route back through the router (B11) | No Prototype playbook (departs from report §4.2) | pilot 2 |
| 14 | **Plan skeleton**: does `planning` gain the per-unit skeleton and a plan lint | Yes: a skeleton branch (evidence boxes, a named `execution` scope) with the lint as its load | `planning` grows, against a new planning skill beside it | pilot 2 |
| 15 | **`wip:` commits at a pause** (report decision 13) | No commit without commit authority: the resume note records the uncommitted state; with authority, one `wip:` commit | Edits survive only in the worktree without authority | pilot 3 |
| 16 | **Deferred set**: the six deferrals and Opening a PR's PR sections, each with its `revisit_when` (§2) | Confirm | No PR, CI or UI coverage until a revisit condition holds | nothing now |
| 17 | **Orchestrate**: defer the playbook and take its supervision rules as merge candidates for `delegation` (departs from report's second wave) | Yes | `delegation` grows by three rules; no program procedure outside the engine | nothing in the batches; phase-2 `delegation` work |

2026-11-03: owner rulings narrow ruling 3 (`model-council` stays model-invocable and runs only on an explicit request), make `interrogate` its own skill, and settle Feature's step 2 and 6 bindings; see bead `cr-r2pa.2.6` and `.repo-context/unit-kinds.md` S7.

2026-11-04: the owner's answer amends ruling 12. `wake` is a closing timer only; its callers are a stated unattended Autonomous run and Hillclimb; a request's unattended words count as the explicit request for that timer (dated S7 row, `.repo-context/unit-kinds.md`). Waiting on a command needs no `wake`, so Bug fix does not call it. Why: an event is what the platform already does; a heartbeat needs re-arming unverified on T3, spends unwatched turns and answers a problem nothing here has measured; and a shared return protocol failed review twice, in Bug fix most of all, where a confirmed cause is a gate and not an end. The ruling's point stands: playbooks name the outcome, not a tool. This map keeps its history, so these lines are stale: 52, 662 and 833 ("waits on the ruling", three callers); 849 (Bug fix's `wake`); 851 and 858 (blockers: `wake` is built); 257 and 474 (the watcher subagent is dropped); 892 now means `AGENTS.md:47-48`, and 893 `AGENTS.md:68-70`.

## Appendix: checks

Run from the worktree with the data in `scratchpad/mvp-stack/playbook-map/`.

1. **Citations** (`check_citations.py`): every `path:line` in this file
   resolves, with the aliases above; reference harnesses resolve in the main
   checkout, which holds the submodules.
2. **Coverage** (`check_coverage.py`): the 23 playbook files are re-read and
   every unit mention is matched to a call, principle or non-call row, and
   every row to a mention: 236 mentions, 0 uncovered, 0 stale. It also
   validates every bind's contract and fit.
3. **Demand** (`check_demand.py`): rebuilds this file in memory and compares
   it with the file; asserts that hand-offs, selections, pointers, templates,
   local calls and steps not carried add no demand, that a contract reached
   only by a hand-off has zero live demand (on the data and on a synthetic
   case), that readiness checks binds, and that §3's published demand matches
   a count recomputed independently of the renderer.
4. **Git status:** only the owned paths are this task's.
