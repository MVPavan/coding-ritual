# Plan-Execution Engines — Level 3 Components

Column keys used in the matrix:

| Key | Surface |
|---|---|
| `PE` | ours — `.claude/skills/phase-execution/SKILL.md` |
| `SDD⁰` | ours — `.claude/skills/subagent-driven-development/SKILL.md` |
| `RP` | ours — `.claude/commands/run-phases.md` |
| `IMP⁰` | ours — `.claude/agents/implementer.md` |
| `SDDˢ` | superpowers — `skills/subagent-driven-development/` (SKILL.md + 3 templates + 3 scripts) |
| `EP` | superpowers — `skills/executing-plans/SKILL.md` |
| `IMPᵐ` | mattpocock — `skills/engineering/implement/` |

## Component inventory

### `PE` — phase-execution (ours)

| Component | Citation |
|---|---|
| Roadmap-path input, ask-if-ambiguous | `SKILL.md:19-21` |
| Phase → bd epic resolution with legacy `spec_id` fallback; never re-seed | `SKILL.md:29-32` |
| Dependency precheck (`bd blocked`, `bd dep tree`) | `SKILL.md:33` |
| Risk classification read from the roadmap, default `standard` | `SKILL.md:34` |
| Plan step skipped for standard phases; deep phases plan + document-review + **human approval gate** | `SKILL.md:38-46` |
| Ready-front comes from bd, not a checklist | `SKILL.md:50-51` |
| Atomic select+claim (`bd ready --claim`), filtered to direct children | `SKILL.md:53-56` |
| Per-stage routing table (deep→SDD, standard→inline, test-first→TDD, failure→debugging) | `SKILL.md:57-61` |
| Close-with-evidence; the reason renders into progress.md | `SKILL.md:62-63` |
| Discovered work captured as a stage with `discovered-from` dep | `SKILL.md:64-65` |
| Render-if-available, else report the missing renderer | `SKILL.md:66-68`, `SKILL.md:84-86` |
| **Discipline gate** — jq predicate that zero child stages are unclosed, else STOP | `SKILL.md:72-76` |
| Roadmap exit criterion + verification-before-completion skill | `SKILL.md:77-79` |
| Owns/delegates declaration | `SKILL.md:90-102` |
| `--actor` on every bd write; stop-and-report on block | `SKILL.md:110` |

### `SDD⁰` — subagent-driven-development (ours)

| Component | Citation |
|---|---|
| Four-role model (coordinator / implementer / spec-reviewer / code-reviewer) | `SKILL.md:10-15` |
| Task-packet contents (8 fields incl. owned+**forbidden** files, invariants, commit policy) | `SKILL.md:20-28` |
| Test-first flag routes the implementer into the TDD skill | `SKILL.md:28` |
| Fresh implementer per task, packet only | `SKILL.md:29` |
| Four-value status contract | `SKILL.md:30` |
| BLOCKED / unexpected failure → systematic-debugging before re-dispatch | `SKILL.md:31` |
| Ordered two-stage review: spec first, quality second | `SKILL.md:32-33` |
| Fix-and-re-review loop, **unbounded** | `SKILL.md:34` |
| Codex code review scaled by risk (`standard` → `/codex-review`, `deep` → `-e xhigh`) | `SKILL.md:35-37` |
| Task sizing: one deliverable, cap the prompt, cap the result | `SKILL.md:41-45` |
| 529 recovery: wait 5s, one retry, then inline | `SKILL.md:49` |
| Twice-blocked → split smaller or inline | `SKILL.md:50` |
| **Inline fallback always valid** | `SKILL.md:52` |
| No parallel implementers on the same files | `SKILL.md:56` |
| No raw session history to workers | `SKILL.md:57` |
| Weaker worker model, stronger planner/reviewer model | `SKILL.md:58` |

### `RP` — run-phases (ours, command)

| Component | Citation |
|---|---|
| Sequential-by-design rationale; deps, not the runner, define order | `run-phases.md:13-16` |
| Next phase resolved by bd query in roadmap order | `run-phases.md:24-29` |
| Delegates each phase to `/phase-execution` with auto-approval | `run-phases.md:30-31` |
| Per-phase render + bd export + staged commit, opt-in via invoking the command | `run-phases.md:32-36` |
| `/compact` between phases (not `/clear`, which would kill the session) | `run-phases.md:37`, `run-phases.md:58` |
| Post-compaction re-query contract (bd is truth, not conversation) | `run-phases.md:38-40`, `run-phases.md:59-67` |
| Enumerated auto-approval list | `run-phases.md:50-54` |
| Intra-phase compaction between stages | `run-phases.md:69` |
| Stop-the-run on gate/exit failure | `run-phases.md:73` |
| Test failure → systematic-debugging; twice → stop | `run-phases.md:75` |

### `IMP⁰` — implementer (ours, agent)

| Component | Citation |
|---|---|
| Tool allowlist + pinned model/effort in frontmatter | `implementer.md:4-6` |
| "Not alone in the codebase" — do not revert others' work | `implementer.md:13` |
| Dispatch supplies task, owned files, verification commands, invariants | `implementer.md:14` |
| Stay in scope unless coordinator expands it | `implementer.md:15` |
| Ask before coding when unclear | `implementer.md:16` |
| Follow local patterns; minimal reversible changes | `implementer.md:20-21` |
| Conditional test-first / characterization test | `implementer.md:22` |
| Run verification commands before reporting | `implementer.md:23` |
| Self-review before reporting (one line, no rubric) | `implementer.md:24` |
| Explicit-files-only commit when asked | `implementer.md:25` |
| Git prohibition block (`git add .`/`-A`, `--no-verify`, amend, forbidden files) | `implementer.md:28-32` |
| Four-value status contract | `implementer.md:36-39` |
| Seven-field inline report template | `implementer.md:43-51` |

### `SDDˢ` — subagent-driven-development (superpowers)

| Component | Citation |
|---|---|
| Why-subagents rationale (isolated context, preserve controller context) | `SKILL.md:10` |
| Narration cap: at most one short line between tool calls | `SKILL.md:14-15` |
| **Continuous execution** — never check in between tasks | `SKILL.md:17` |
| When-to-use decision graph (plan? independent? same session?) | `SKILL.md:21-37` |
| Worktree isolation; no main/master without consent | `SKILL.md:111-114` |
| **Plan-scoped ledger** with identity first line, resume semantics, `git log` as second source | `SKILL.md:116-140` |
| `scripts/sdd-workspace` — per-plan git-ignored dir, self-ignoring `.gitignore`, single source of truth for location | `scripts/sdd-workspace:1-40` |
| Pre-flight plan conflict scan, batched into one human question | `SKILL.md:145-155` |
| Model-selection policy by task class, incl. "always specify the model" and "turn count beats token price" | `SKILL.md:157-192` |
| Context-hygiene principle: everything pasted stays resident; hand artifacts over as files | `SKILL.md:196-198` |
| BASE recorded before dispatch (never `HEAD~1`) | `SKILL.md:202-203`, `SKILL.md:238` |
| `scripts/task-brief` — awk-extracts one task's text to a file | `scripts/task-brief:28-39` |
| Five-element dispatch composition + ban on pasting prior-task history (42k-char failure cited) | `SKILL.md:206-225` |
| Report-file indirection (implementer writes detail to file, returns <15 lines) | `SKILL.md:218-220`, `implementer-prompt.md:118-135` |
| Carry a pointer to parked findings in the touched area | `SKILL.md:226-227` |
| Record implementer agent identity for resume | `SKILL.md:228-229` |
| No parallel implementers | `SKILL.md:230` |
| Four-status handling with per-status action + "never force the same model to retry" | `SKILL.md:236-250` |
| `scripts/review-package` — commits + `--stat` + `-U10` diff to a per-range file | `scripts/review-package:32-46` |
| Task review = two mandatory verdicts (spec + quality); self-review never replaces it | `SKILL.md:256-262` |
| Global-constraints block copied verbatim as the reviewer's attention lens | `SKILL.md:273-282` |
| **Anti-pre-judging rule** with the literal trigger phrases | `SKILL.md:287-292` |
| `⚠️ Cannot verify from diff` items the controller must resolve itself | `SKILL.md:293-298` |
| Minor findings ledgered as deferred, never enter the loop | `SKILL.md:309-313` |
| Plan-mandated findings escalate to the human | `SKILL.md:314-318` |
| **Bounded fix loop**: 5 rounds; 1-3 resume original, 4-5 fresh + one tier up | `SKILL.md:319-333` |
| Fix report must contain covering tests + command + output before re-review | `SKILL.md:335-341` |
| **Scoped re-review** per round; new breakage joins findings, out-of-scope goes to ledger | `SKILL.md:343-350` |
| Ledger line per fix round | `SKILL.md:352-353` |
| Controller never fixes findings itself | `SKILL.md:355-356` |
| **The breaker**: adjudicate at the cap into park / park-real / STOP-BLOCKED; silent discard forbidden | `SKILL.md:358-375` |
| Completion ledger lines (clean vs K-parked) | `SKILL.md:377-389` |
| Final whole-branch review on the most capable model, pointed at deferred/parked lines | `SKILL.md:391-402` |
| ONE fix dispatch for all final findings + exactly one scoped re-review, no second wave | `SKILL.md:404-414` |
| Workspace deletion at the end; siblings untouched | `SKILL.md:416-421` |
| Rationalization table (8 rows) | `SKILL.md:425-436` |
| Worked example transcript | `SKILL.md:438-503` |
| Implementer template: ask-before-you-begin | `implementer-prompt.md:24-30` |
| Implementer template: focused test while iterating, full suite once before commit | `implementer-prompt.md:46-47` |
| Implementer template: code-organization rules (one responsibility; report growth as DONE_WITH_CONCERNS instead of splitting) | `implementer-prompt.md:49-61` |
| Implementer template: **"in over your head"** escalation triggers + "bad work is worse than no work" | `implementer-prompt.md:63-78` |
| Implementer template: four-axis self-review rubric (completeness/quality/discipline/testing) | `implementer-prompt.md:80-105` |
| Implementer template: **TDD evidence** (RED command+output+why-expected, GREEN command+output) | `implementer-prompt.md:121-124` |
| Reviewer template: **do not trust the report**; stated rationale never downgrades severity | `task-reviewer-prompt.md:57-62` |
| Reviewer template: don't re-run the suite; focused test only on a named doubt | `task-reviewer-prompt.md:64-76` |
| Reviewer template: read-only on the checkout | `task-reviewer-prompt.md:54-55` |
| Reviewer template: diff-file-once, no codebase crawling, one focused check per named risk | `task-reviewer-prompt.md:38-52` |
| Reviewer template: spec axes missing/extra/misunderstood + ⚠️ unverifiable | `task-reviewer-prompt.md:78-90` |
| Reviewer template: severity calibration + plan-mandated labelling + acknowledge strengths | `task-reviewer-prompt.md:124-137` |
| Re-reviewer template: per-finding ADDRESSED / NOT ADDRESSED, "attempted is not addressed" | `re-review-prompt.md:71-77` |
| Re-reviewer template: out-of-scope observations do not extend the loop | `re-review-prompt.md:46-53`, `re-review-prompt.md:83-86` |

### `EP` — executing-plans (superpowers)

| Component | Citation |
|---|---|
| Announce-at-start line | `SKILL.md:12` |
| Self-demotion to `subagent-driven-development` when subagents exist | `SKILL.md:14` |
| Worktree isolation | `SKILL.md:19` |
| Critical plan review before starting; raise concerns first | `SKILL.md:20-23` |
| Todo per task; follow steps exactly; run the plan's verifications | `SKILL.md:27-31` |
| Mandatory hand-off to `finishing-a-development-branch` | `SKILL.md:36-38` |
| Stop conditions (blocker, plan gap, unclear instruction, repeated verification failure) | `SKILL.md:42-48` |
| **Return-to-review triggers** (partner updated the plan; approach needs rethinking) | `SKILL.md:52-55` |
| Never start on main/master without consent | `SKILL.md:64` |

### `IMPᵐ` — implement (mattpocock)

| Component | Citation |
|---|---|
| User-invocation lock (`disable-model-invocation` + `allow_implicit_invocation: false`) | `SKILL.md:4`, `agents/openai.yaml:4-5` |
| Route to `/tdd` at **pre-agreed seams** | `SKILL.md:9` |
| **Verification cadence**: typecheck regularly, single test files regularly, full suite once at the end | `SKILL.md:11` |
| Route to `/code-review` when done | `SKILL.md:13` |
| Commit to the current branch (unconditional) | `SKILL.md:15` |

## Cross-skill matrix

`✓` present · `~` variant (differs in mechanism or strength) · `—` absent

| Component | PE | SDD⁰ | RP | IMP⁰ | SDDˢ | EP | IMPᵐ |
|---|---|---|---|---|---|---|---|
| Entry precondition is an approved plan/roadmap | ✓ | ✓ | ✓ | — | ✓ | ✓ | ~ |
| Workspace isolation (worktree/branch) | — | — | — | — | ✓ | ✓ | — |
| Critical pre-flight review of the plan | ~ | — | — | — | ✓ | ✓ | — |
| Human approval gate before execution | ✓ | — | ~ | — | ~ | ✓ | — |
| Unit of work defined | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| Work-state in an external tracker | ✓ | — | ✓ | — | — | — | — |
| Progress record that survives compaction | ~ | — | ~ | — | ✓ | — | — |
| Fresh worker per unit | ~ | ✓ | — | n/a | ✓ | — | — |
| Worker prompt/brief construction rules | ~ | ✓ | — | — | ✓ | — | — |
| Artifact handoff as files (brief/report/diff) | — | — | — | — | ✓ | — | — |
| Model selection per role | ~ | ~ | — | ✓ | ✓ | — | — |
| Structured worker status contract | — | ✓ | — | ✓ | ✓ | — | — |
| Per-status handling policy | ~ | ~ | — | — | ✓ | — | — |
| Worker self-review rubric | — | — | — | ~ | ✓ | — | — |
| Worker escalation triggers | — | — | — | ~ | ✓ | — | — |
| TDD evidence required from the worker | — | ~ | — | ~ | ✓ | — | ~ |
| Per-unit review gate | ~ | ✓ | — | — | ✓ | — | — |
| Spec-compliance verdict separate from quality verdict | ✓ | ✓ | — | — | ✓ | — | — |
| Reviewer told not to trust the worker's report | — | — | — | — | ✓ | — | — |
| Anti-pre-judging rule for review prompts | — | — | — | — | ✓ | — | — |
| Severity calibration rubric | — | — | — | — | ✓ | — | — |
| Fix loop after review findings | — | ✓ | — | — | ✓ | — | — |
| **Bounded** fix loop with a round cap | — | — | — | — | ✓ | — | — |
| Escalation ladder inside the fix loop | — | ~ | — | — | ✓ | — | — |
| Scoped re-review of the fix diff only | — | — | — | — | ✓ | — | — |
| Adjudication/parking of unresolved findings | — | — | — | — | ✓ | — | — |
| Final whole-branch review | ~ | ✓ | — | — | ✓ | — | ✓ |
| Cross-model/independent critique | ✓ | ✓ | ✓ | — | — | — | — |
| Machine-checkable completion gate | ✓ | — | ~ | — | — | — | — |
| Exit criterion / definition of done | ✓ | — | ~ | — | ~ | ~ | — |
| Verification cadence guidance | — | — | — | ~ | ~ | — | ✓ |
| Failure recovery for infrastructure errors (529/timeout) | ~ | ✓ | ~ | — | — | — | — |
| Inline fallback when delegation fails | — | ✓ | — | — | — | — | — |
| Context management / compaction strategy | — | ~ | ✓ | — | ✓ | — | — |
| Multi-plan / multi-phase continuity | ✓ | — | ✓ | — | — | — | — |
| Discovered-work capture | ✓ | — | — | — | ~ | — | — |
| Commit policy | ~ | ~ | ✓ | ✓ | ~ | — | ~ |
| Git-safety prohibitions | ~ | — | ~ | ✓ | — | — | — |
| Parallel-worker prohibition | — | ✓ | — | — | ✓ | — | — |
| Rationalization / red-flag table | — | — | — | — | ✓ | — | — |
| Return-to-planning trigger | ~ | — | — | — | — | ✓ | — |
| Worked example transcript | — | — | — | — | ✓ | — | — |
| Explicit owns/delegates boundary | ✓ | — | ~ | — | — | ~ | ✓ |

## Shared-component differences

Only rows where implementations actually differ are argued here.

**Progress record that survives compaction** (`PE`/`RP` `~` vs `SDDˢ` `✓`).
Ours stores state in bd: stage status flips on claim (`PE:53-56`) and evidence
lands in `bd close --reason` (`PE:62-63`); `RP:59-67` then mandates re-querying
after every `/compact`. Superpowers appends lines to a plan-scoped markdown
ledger and treats `git log` as the corroborating second source
(`SDDˢ:134-140`). **Ours is stronger for phase/stage granularity** — the state is
written by a tool, is queryable, and a controller cannot silently forget to write
it, because `bd ready --claim` is described as non-skippable (`PE:53-55`).
**Theirs is stronger inside a task** — the ledger records fix-round position
(`SDDˢ:352-353`) and parked rulings (`SDDˢ:362-371`), which bd stage status
cannot express; after a mid-task compaction ours knows only "stage in_progress".
The two are complementary, and the gap in ours is sub-stage resolution.

**Fresh worker per unit** (`PE` `~`). `SDD⁰:29` and `SDDˢ` both dispatch a fresh
implementer per task. `PE` only does so transitively for **deep** stages
(`PE:57-59`); `standard` stages are implemented inline by the controller
(`PE:59`), so the context-isolation property does not hold for them. That is a
deliberate risk-scaling choice, not an oversight, but it means `PE` alone gives
no context isolation.

**Worker prompt/brief construction** (`SDD⁰` `✓` vs `SDDˢ` `✓`, different
mechanism). Ours enumerates eight packet fields (`SDD⁰:20-28`) and says to cap
the prompt (`SDD⁰:44`). Theirs extracts the task text mechanically with
`scripts/task-brief` and hands over a **path**, with a five-element dispatch
whose exact values live only in the brief (`SDDˢ:206-216`). **Theirs is
stronger**: ours relies on the controller obeying a size rule; theirs makes the
text physically unable to enter the controller's context because awk writes it to
disk. Ours is stronger on one field only — `forbidden files` (`SDD⁰:22`) has no
counterpart upstream, where scope is prose ("don't restructure things outside
your task", `implementer-prompt.md:61`).

**Model selection per role** (`PE`/`SDD⁰` `~` vs `IMP⁰`/`SDDˢ` `✓`).
`SDD⁰:58` is one sentence ("prefer a smaller worker model and a stronger
planner or reviewer model"); `IMP⁰:5-6` pins one model for one agent, which
covers the implementer role but nothing else. `SDDˢ:157-192` gives complexity
signals per task class, a fix-loop escalation rule (rounds 4-5 one tier up), a
"always specify the model explicitly, an omitted model inherits your session's"
failure note, and the counter-intuitive "turn count beats token price" caveat.
**Theirs is stronger** — it is the only version that explains the failure mode
(silent inheritance) that makes the guidance necessary.

**Per-unit review gate** (`PE` `~`, `SDD⁰` `✓`, `SDDˢ` `✓`). `PE` has no review
of its own; it inherits one only when it routes to `SDD⁰` (`PE:57-59`).
`SDD⁰:32-34` runs spec then quality as two agent invocations. `SDDˢ:256-262`
folds both verdicts into **one** reviewer reading **one** diff file, and forbids
accepting a report missing either verdict. **Theirs is stronger on cost** (one
dispatch, one diff read instead of two) and on evidence discipline (the diff file
is mandatory, `task-reviewer-prompt.md:180-182`); **ours is stronger on
separation** — a dedicated `spec-reviewer` and `code-reviewer` agent
(`SDD⁰:13-15`) cannot let one verdict's findings dilute the other's, and ours
adds an independent Codex pass (`SDD⁰:35-37`) that no upstream engine has.

**Fix loop** (`SDD⁰` `✓` unbounded vs `SDDˢ` `✓` bounded). Ours: "fix and
re-review until both pass" (`SDD⁰:34`) — no cap, no escalation inside the loop,
no record of what was decided. Theirs: five rounds, rounds 1-3 resume the same
implementer with intact context, rounds 4-5 a fresh implementer one capability
tier up with the "a prior implementer attempted this [N] times" framing
(`SDDˢ:319-333`), each round ending in a scoped re-review (`SDDˢ:343-350`), then
the breaker (`SDDˢ:358-375`). **Theirs is decisively stronger**: ours has no
termination guarantee at all, and its only escalation is `SDD⁰:50`'s
"twice-blocked → split or inline", which handles a *blocked implementer*, not a
*review that keeps finding things*. The mechanism that matters is not the number
5 — it is that the cap forces an explicit adjudication with a written ruling, so
an unresolvable finding becomes either a recorded park or a BLOCKED escalation
instead of an infinite loop or a silent drop.

**Escalation ladder inside the fix loop** (`SDD⁰` `~`). `SDD⁰:50` escalates on
implementer failure; `SDDˢ:319-333` escalates on *review persistence*. Different
trigger, and ours is missing the one that actually recurs.

**Final whole-branch review** (`PE` `~`, `SDD⁰` `✓`, `SDDˢ` `✓`, `IMPᵐ` `✓`).
`IMPᵐ:13` is a one-line route to `/code-review`. `SDD⁰:35-37` runs Codex on the
diff at the end of a plan. `PE:78` substitutes the verification skill, which
proves the exit criterion rather than reviewing the code. `SDDˢ:391-414` runs the
review on the most capable model, points it at the ledger's deferred-minor and
parked lines so they get triaged rather than lost, then allows **exactly one**
fix wave with one scoped re-review and no second wave. **Theirs is stronger**
because of the triage pointer: ours has nowhere for a deferred minor to live, so
in our loop a Minor finding is either fixed immediately or forgotten.

**Machine-checkable completion gate** (`PE` `✓`, `RP` `~`). `PE:72-76` is a
literal shell predicate whose failure prints the unclosed stages and stops.
`RP:32` inherits it rather than defining one. Nothing upstream has an equivalent:
`SDDˢ`'s completion is the controller asserting the final review is clean
(`SDDˢ:416-418`), `EP:35` is "after all tasks complete and verified". **Ours is
strongest here by a wide margin** — it is the only done-check in this set that a
lying controller cannot pass.

**Verification cadence** (`IMP⁰` `~`, `SDDˢ` `~`, `IMPᵐ` `✓`). `IMP⁰:23` says
"run the requested verification commands" — cadence is the dispatcher's problem.
`implementer-prompt.md:46-47` gives the rule inside the worker prompt: focused
test while iterating, full suite once before committing. `IMPᵐ:11` states it as
the skill's own rule and adds typechecking. **`IMPᵐ` is stronger per token** —
it is one sentence and it covers three granularities (typecheck / single file /
full suite); superpowers covers two; ours defers entirely. This is the one
component where the 15-line skill beats the 500-line one.

**Failure recovery for infrastructure errors** (`SDD⁰` `✓`, `PE`/`RP` `~`).
`SDD⁰:49-52` names the error class (529), the wait, the retry count, and the
fallback. `PE:61` and `RP:75` handle *test* failure via systematic-debugging, a
different class. `SDDˢ` has none — its four-status handling (`SDDˢ:236-250`)
covers the subagent *reporting* a problem, not the dispatch itself failing.
**Ours is stronger and uniquely so**: this is the only component in the whole
matrix where our harness has a mechanism upstream lacks entirely.

**Context management** (`RP` `✓`, `SDD⁰` `~`, `SDDˢ` `✓`). `RP:57-69` is
inter-phase: `/compact` (never `/clear`), then re-query bd. `SDD⁰:41-45` is
advice about prompt and result size. `SDDˢ:196-198` states the underlying law
("everything you paste stays resident and is re-read on every later turn") and
then enforces it with three scripts. **Theirs is stronger where they overlap**
(`SDD⁰` vs `SDDˢ`) for the reason given above — advice vs mechanism. `RP` solves
a problem neither upstream engine has, since neither spans multiple plans.

**Commit policy** — four different positions. `IMP⁰:25` commits only when the
dispatch asks, explicit files only. `RP:35-36` commits per phase and names the
invocation as the opt-in. `SDDˢ` has the implementer commit per task
(`implementer-prompt.md:38`), unconditionally. `IMPᵐ:15` commits unconditionally
at the end. **Ours is stronger on safety** — both of our commit paths are
explicitly authorised, which is what our git-safety rule requires and what the
ledger has already twice objected to upstream (`incremental-implementation`:
"reject the source workflow's mandatory per-slice commits").

**Return-to-planning trigger** (`EP` `✓`, `PE` `~`). `EP:52-55` names two
conditions for going *backwards* into review. `PE:102` mentions returning to
brainstorming if requirements are unclear, but only in the delegation list, not
as a step with a trigger. **`EP` is stronger** on this single component, and it
is the only thing in `executing-plans` that ours does not already have in a
better form.

**Discovered-work capture** (`PE` `✓`, `SDDˢ` `~`). `PE:64-65` creates a new bd
stage with a `discovered-from` dependency — durable, tracked, schedulable.
`SDDˢ:309-313` ledgers deferred minors and points the final review at them —
durable only until the workspace is deleted (`SDDˢ:416-418`). **Ours is
stronger**: our discovered work outlives the plan; theirs does not.

---

## Round 2 extension — ask-matt `PHASE-BOUNDARIES.md`

Added 2026-08-14. Rationale, placement, and verdict: [`README.md`](README.md) →
*Round 2 extension*. This section adds one upstream column and one "ours"
column; the round-1 matrix above is left untouched, because its `PE`/`SDD⁰`/`RP`
keys point at a pre-consolidation layout (remap table in the README).

New column keys:

| Key | Surface |
|---|---|
| `PB` | mattpocock — `skills/engineering/ask-matt/PHASE-BOUNDARIES.md` (+ its summary in `ask-matt/SKILL.md:61-71`) |
| `EX` | ours — `.claude/skills/execution/` (`SKILL.md` + `references/task-engine.md` + `references/workstream-mode.md`) and `.claude/commands/{phase-execution,run-phases}.md` |

Citations in this section are unprefixed within a file's own row: `PB:21` =
`PHASE-BOUNDARIES.md:21`; ours are given with a file stem, e.g.
`workstream-mode.md:62`.

### Component inventory

#### `PB` — PHASE-BOUNDARIES.md (mattpocock)

| Component | Citation |
|---|---|
| **Phase** defined as a session-internal chunk, fuzzy on purpose ("ok, we're done with that") | `PB:3` |
| **The decision belongs only at the boundary**; mid-phase there is no decision — continue or split into subagents | `PB:5` |
| Mid-phase compaction makes the agent lose the thread | `PB:5` |
| Five-option enumeration table with one-line semantics each | `PB:9-15` |
| **Ordered tree, first yes wins**, worked top to bottom | `PB:19` |
| Q1 Continue — sufficient condition A: next phase needs this one as a **primary source** | `PB:21` |
| Q1 Continue — sufficient condition B: ~150k smart zone remains for the next phase | `PB:21` |
| Q1 canonical case: grilling → implementation (wants the reasoning verbatim, not a summary) | `PB:21` |
| Q1 placement rule: "continue costs nothing and loses nothing, so rule it out before anything else" | `PB:21` |
| Q2 `/clear` — test is "is everything here disposable?"; cheapest move, old session stays resumable | `PB:23` |
| Q2 **asymmetric-cost warning** — clearing relevant context loses the *why*; reading the diff back does not return it | `PB:25` |
| Q3 `/handoff` — closed four-item clause (new harness / new directory / colleague / mid-phase side task) | `PB:27-32` |
| Q3 "that list is the whole clause"; what it buys is **portability** — nothing travelling, no handoff | `PB:34` |
| Q4 **AFK test** — scoped tightly enough to run with no steering → subagent | `PB:36` |
| Q4 canonical case: automated review | `PB:36` |
| Q5 `/compact` as the landing spot, **with an instruction argument** | `PB:38` |
| Q5 "`/compact` is the **default, not the first reach**" + the flattened-decision failure mode | `PB:40` |
| **Primary → secondary conversion**: every move except Continue pays it | `PB:44` |
| Tradeoff table: Information / Noise / Room to move, primary vs secondary | `PB:46-49` |
| Why Q1 is first — pay lossiness only when staying costs more than it saves | `PB:51` |
| Self-declared as judgement, not procedure; the value is asking **in order, at the boundary** | `PB:53-55` |
| Router-side summary of the five options + "make the decision **at** a boundary" | `ask-matt/SKILL.md:63-71` |
| Router-side smart-zone rule: don't push on degraded; compact at the nearest boundary | `ask-matt/SKILL.md:32` |
| Router-side unbroken-window rule for grilling → spec → tickets | `ask-matt/SKILL.md:30` |

#### `EX` — execution (ours) — context-move components only

Work-unit components are in the round-1 inventory. Listed here is only what
bears on the context decision.

| Component | Citation |
|---|---|
| `/compact` between phases; **`/clear` banned** ("it kills the session") | `workstream-mode.md:62` |
| `/compact` between stages **within** a large phase, then re-read ledger + re-query bd | `workstream-mode.md:63-64` |
| Enumerated locations of persistent state (bd, plans dir, workspace ledger) | `workstream-mode.md:65-67` |
| Post-compaction recovery contract: re-read `progress.md`, latest findings, re-query bd + `git status` | `task-engine.md:49-51` |
| Stated failure the contract prevents: "a coordinator that lost its place re-dispatches completed work" | `task-engine.md:51` |
| Ledger identity line + append-one-line-per-event format | `task-engine.md:32-42` |
| Every review saved verbatim to a findings file **before** acting on it | `task-engine.md:44-47` |
| Walk authorization recorded in the ledger so a post-compaction session can prove the opt-in | `workstream-mode.md:15-17` |
| Re-query bd after compaction because "bd is the source of truth, not conversation memory" | `workstream-mode.md:45-46` |
| Artifact handoff by **path**, never by content ("the package never enters the coordinator's context") | `task-engine.md:69` |
| Never paste prior-task history — "everything pasted stays resident for the rest of the session" | `task-engine.md:82-84` |
| Cap the prompt / cap the result; full file contents never enter the coordinator | `task-engine.md:213-216` |
| Route work off the coordinator by **risk** (small inline / standard light / deep full) | `SKILL.md:34-39` |
| Coordinator "should not hold implementation context" as the stated reason for dispatch | `task-engine.md:3-7` |
| Sequential-by-design phases, `/compact` between, for context economy | `workstream-mode.md:8-11` |

### Cross-skill matrix

`✓` present · `~` variant (differs in mechanism or strength) · `—` absent

| Component | PB | EX |
|---|---|---|
| Names a unit of work | ~ | ✓ |
| Unit is externally resolvable (tracker/roadmap) | — | ✓ |
| Recognises a **boundary** between units as a decision point | ✓ | ~ |
| Enumerates the available context moves | ✓ | ~ |
| Ordered decision procedure over those moves | ✓ | — |
| "Continue / do nothing" named as an option | ✓ | — |
| Criterion for *staying* (primary-source need) | ✓ | — |
| Context-budget criterion (smart zone / token headroom) | ✓ | — |
| `/clear` treated as available | ✓ | ✗ (banned) |
| Irreversibility / asymmetric-cost warning on a context move | ✓ | — |
| Portable handoff artifact (`/handoff`) — *ruled on in `../session-handoff/`, not here* | ✓ | — |
| Subagent as a context move | ✓ | ✓ |
| Selector for the subagent move | ~ (AFK) | ✓ (risk) |
| Bounds on the dispatched unit | — | ✓ |
| `/compact` as a named move | ✓ | ✓ |
| **Instruction passed to `/compact`** | ✓ | — |
| Warning against reaching for `/compact` first | ✓ | — |
| Mid-phase compaction permitted | ✗ (forbidden) | ✓ |
| Recovery contract after compaction | — | ✓ |
| Durable state enumerated for recovery | — | ✓ |
| Vocabulary for context lossiness (primary/secondary) | ✓ | — |
| Artifact-by-path discipline (keep content out of the window) | — | ✓ |
| Ban on pasting prior history into a dispatch | — | ✓ |
| Machine-checkable anything | — | ✓ |
| Self-declared as judgement rather than procedure | ✓ | — |

### Shared-component differences

**Unit of work / "phase"** (`PB` `~` vs `EX` `✓`). Same word, two objects.
`PB:3` defines a phase as a chunk of a *session*, ending when the human feels it
ended — deliberately unresolvable. `EX` defines a phase as a roadmap row bound
to a bd epic resolved by a bracketed join key (`SKILL.md:65-67`) and closed only
through a jq predicate over its children (`SKILL.md:88-95`). **Ours is stronger
for tracked work** — a lying coordinator cannot pass our gate and there is
nothing to pass in theirs. **Theirs names something ours cannot**: the seam
between grilling and implementation inside one session, which no roadmap row
segments. The practical consequence is a terminology collision: importing
`PB`'s definition would overload a word our gate depends on.

**Boundary as a decision point** (`PB` `✓` vs `EX` `~`). `PB:5` makes the
boundary the *only* legal place for the decision and forbids deciding mid-phase.
`EX` has boundaries — between phases (`workstream-mode.md:62`) and between
stages (`:63-65`) — but never frames them as a point where a choice is made;
at both, the move is already fixed to `/compact`. **Theirs is stronger as a
concept, ours as a default**: a fixed move needs no judgement and cannot be
judged wrong, which is why our unattended walk works at all. The cost is that
the fixed move is the lossy one, always.

**Enumerated moves** (`PB` `✓` vs `EX` `~`). `PB:9-15` is a five-row table.
Ours is scattered and partial: `/compact` (`workstream-mode.md:62`), `/clear`
(named only to ban it, same line), subagent dispatch (`task-engine.md` passim).
Continue and handoff are absent as concepts. **Theirs is stronger on
completeness**; two of its five rows are dead in our harness, so the honest gap
is two options wide, not five.

**Mid-phase compaction** (`PB` ✗ forbidden vs `EX` ✓ mandated). A direct
contradiction, and the most interesting row here. `PB:5` says compacting
mid-phase makes the agent lose the thread, so mid-phase you may only continue or
split into subagents. `workstream-mode.md:63-64` says to compact between stages
inside a large phase, then re-read the ledger and re-query bd;
`task-engine.md:49-51` makes that a contract with a named failure ("a
coordinator that lost its place re-dispatches completed work"). **Ours is
stronger, and the mechanism is why**: `PB` avoids the loss by not compacting,
which only works while the window holds out; we accept the loss and reconstruct
from state written outside the window — bd, `progress.md`, the findings files
(`task-engine.md:44-47`). Ours degrades gracefully; theirs has no story once the
window is genuinely full. **But `PB`'s claim is not fully answered.** Our
contract restores *position and facts*; `PB:44-49` is about losing *reasoning*,
and re-reading `progress.md` does not return why an approach was chosen.

**Criterion for staying** (`PB` `✓`, `EX` `—`). `PB:21` gives two, and the
first — the next phase needs this one as a **primary source** — is the one with
no counterpart anywhere in our harness. Ours reasons about context in one
direction only: context is cost, so shed it (`task-engine.md:3-7`, `:82-84`,
`:213-216`). The `EX` case that most resembles `PB`'s canonical yes is
planning → execution, and we deliberately resolve it the other way, handing over
a plan **file** — which is exactly the primary→secondary conversion `PB:44`
charges for, made unconsciously. **Theirs is stronger** on this component
because ours does not have it; whether ours should is a judgement, and for
dispatched work our answer is defensibly no.

**`/clear`** (`PB` `✓` available vs `EX` ✗ banned). `PB:23` calls it the
cheapest move and non-terminal, since the old session stays resumable.
`workstream-mode.md:62` bans it because "it kills the session". Within
workstream mode the ban is right for a reason `PB` never faces: our walk's
authorization (`workstream-mode.md:15-17`) and loop position live in the
session, so a clear strands an unattended run. **Neither is stronger; the scopes
differ** — but our stated reason is a general claim about `/clear` used to
justify a mode-specific need, and if the general claim is false it will be
copied outward.

**`/compact` instruction argument** (`PB` `✓`, `EX` `—`). `PB:38` passes the
next phase's intent in (`/compact we're going to QA this area`) so the summary
retains what will be needed. `workstream-mode.md:62` and `:63-64` name the
command with no argument. **Theirs is stronger**, and this is the single
cheapest borrow in the comparison: it is one clause on two existing lines, it
costs nothing, and it targets the failure `PB:40` names — a fresh session
confident about a decision the summary flattened. Our mitigation for that
failure is downstream (re-read the ledger); `PB`'s is upstream (don't flatten it
in the first place). They compose.

**Subagent selector** (`PB` `~` AFK vs `EX` `✓` risk). `PB:36` asks whether the
task can run unsteered. `SKILL.md:34-39` routes by risk class and
`task-engine.md:3-7` by whether the coordinator should hold the context, then
bounds the dispatch (`task-engine.md:212`, `:217`). **Ours is stronger overall**
— it selects *and* constrains, where `PB` only selects. **`PB` is better as a
human-facing test**: "can this run while I make coffee" is answerable
immediately; "is this standard or deep" needs a rubric.

**Vocabulary for lossiness** (`PB` `✓`, `EX` `—`). `PB:44-51` is six lines and a
three-column table naming what every context move costs. Our harness has the
*behaviours* that respond to this cost — artifact-by-path (`task-engine.md:69`),
the paste ban (`:82-84`), the caps (`:213-216`) — with no shared name for what
they are protecting. **Theirs is stronger**, and the gap is a vocabulary gap
rather than a mechanism gap: the rules exist, the concept they serve is unnamed,
which is why nothing in our harness ever weighs *keeping* context against
shedding it.

**Machine-checkability** (`PB` `—`, `EX` `✓`). `PB:53-55` disclaims it. `EX`
converts as much as it can into predicates (`SKILL.md:88-95`) and file-existence
checks (`task-engine.md:44-47`). **Ours is stronger and this is the deepest
difference between the two harnesses** — but it cuts both ways: our preference
for checkable rules is plausibly why the context decision was never written
down at all, since none of `PB`'s five questions can be checked. An unverifiable
five-question tree still beats the zero questions we currently ask.
