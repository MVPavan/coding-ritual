# Plan-Execution Engines

Capability family: **plan-execution** — surfaces that take an approved plan or
roadmap and loop over its units until the work is done. Compared here: our four
execution surfaces (skill, skill, command, agent) against the three upstream
engines.

Scope note: this folder covers *engines* (the loop). The disciplines that ride
inside a loop are in `../execution-disciplines/`; post-implementation passes are
in `../post-implementation-passes/`.

## Level 1 — Placement

| Skill | Repo | Bucket | Triggers when |
|---|---|---|---|
| `phase-execution` | ours | 4 Implementation & Refactoring (also 2 Planning & Work Management) | User says "start/execute/begin phase N" (`SKILL.md:14`). Effectively user-only: it needs a `docs/workstreams/<name>/roadmap.md` and a bd epic that `/prepare-phases` already seeded (`SKILL.md:19-32`). Never fires on a bare "implement this". |
| `subagent-driven-development` | ours | 4 (also 10 Orchestration) | An **approved** standard/deep plan exists and one session should coordinate rather than hold implementation context (`SKILL.md:3,8`). Dispatched by `phase-execution` step 3 for deep stages (`phase-execution/SKILL.md:57-59`), or invoked directly. |
| `run-phases` (command) | ours | *proposed* 4 (also 10) | User types `/run-phases <roadmap.md>` (`run-phases.md:19`). Pure user-invoked; a command file, so no model auto-invocation path at all. |
| `implementer` (agent) | ours | *proposed* 4 | Dispatched by a coordinator through the dispatch workflow or the SDD skill (`implementer.md:3`). Never self-triggers. |
| `subagent-driven-development` | superpowers | 4 (also 10) | "Executing implementation plans with independent tasks in the current session" (`SKILL.md:3`). Its own decision graph gates on: plan exists → tasks mostly independent → staying in this session (`SKILL.md:21-37`). |
| `executing-plans` | superpowers | 4 (also 10) | A written plan is to be executed **in a separate session with review checkpoints** (`SKILL.md:3`). The body immediately demotes itself: if subagents are available, use `subagent-driven-development` instead (`SKILL.md:14`) — so its real firing condition is "no subagent support", which the description does not say. Description would misfire in any Claude Code session. |
| `implement` | mattpocock | 4 | `disable-model-invocation: true` (`SKILL.md:4`) plus `policy.allow_implicit_invocation: false` (`agents/openai.yaml:4-5`) — human types it, never the model. Fires on "implement the spec/tickets" (`SKILL.md:3`). |

No ledger entry exists for any of the three upstream engines
(`harness_lifecycle/ledger.json` holds no `executing-plans`,
`subagent-driven-development`, or `engineering/implement` row) — this family has
never been curated. The adjacent rejection of agent-skills'
`planning-and-task-breakdown` (ledger: "whole-machine-in-one-file shape
rejected; our planning skill is one organ of a five-surface machine proven in
bodha-complete") is the closest prior ruling and is the frame this comparison
should be read against.

## Level 2 — Capability profiles

### `phase-execution` (ours)

**Achieves** — drives one roadmap phase end to end, with bd as the durable
work-state anchor and a hard gate before the phase can be called done.

**Can do**
- Resolves a phase to a bd **epic** and refuses to re-seed it (`SKILL.md:29-32`).
- Reads the ready-front from bd rather than a hand-written checklist, claiming
  stages atomically with `bd ready --parent <epic> --claim` (`SKILL.md:50-56`).
- Routes per-stage by risk: deep → SDD skill, standard → inline, `test-first` →
  TDD skill, unexpected failure → systematic-debugging (`SKILL.md:57-61`).
- Requires closing evidence in the bd `--reason` field, which is what renders
  into `progress.md` — "if it's not in bd, it's not real" (`SKILL.md:62-63`).
- Captures discovered work as a new stage with a `discovered-from` dep
  (`SKILL.md:64-65`).
- Enforces a **discipline gate**: a shell/jq predicate that every child stage is
  closed, else STOP (`SKILL.md:72-76`), then the roadmap exit criterion, then the
  verification skill (`SKILL.md:77-79`).
- Declares explicitly what it delegates vs owns (`SKILL.md:90-102`).

**Pros** — the only engine in this set whose progress lives in a queryable
external store rather than a file the controller writes; the gate at
`SKILL.md:72-76` is a machine-checkable predicate, stronger than every upstream
"all tasks complete" claim, which are all self-assertions. Delegation table
(`SKILL.md:94-102`) keeps it a thin orchestrator — the failure mode the ledger
already rejected `planning-and-task-breakdown` for.

**Cons** — it is *only* a phase driver: it has no per-task review loop of its
own, no fix-round bound, and no recovery story if context is lost mid-stage
beyond bd state. It hard-depends on `/prepare-phases` having run
(`SKILL.md:32`), so it cannot execute a plan that is not a seeded workstream —
narrower entry than any upstream engine.

### `subagent-driven-development` (ours)

**Achieves** — executes an approved plan as bounded task packets dispatched to
fresh implementers, with spec review then code review then Codex review.

**Can do**
- Names a four-role model: coordinator / implementer / spec-reviewer /
  code-reviewer (`SKILL.md:10-15`).
- Defines the task packet contents: goal, owned+forbidden files, origin doc,
  invariants, required tests, verification commands, commit policy, test-first
  flag (`SKILL.md:20-28`).
- Fixed four-value status contract from the implementer (`SKILL.md:30`).
- Ordered two-stage review (spec first, quality second), iterate until both pass
  (`SKILL.md:32-34`), then Codex review scaled to `standard` vs `deep`
  (`SKILL.md:35-37`).
- Task-sizing rules that cap the *prompt* and cap the *result* so full file
  contents never re-enter the coordinator (`SKILL.md:41-45`).
- Concrete failure recovery: 529 → wait 5s, retry once, then inline; BLOCKED →
  systematic-debugging, twice-blocked → split or inline; "fallback to inline is
  always valid" (`SKILL.md:49-52`).

**Pros** — the inline-fallback rule (`SKILL.md:52`) is the one thing no upstream
engine has, and it is what keeps the loop alive under API failure; upstream SDD
has no such escape and would stall. Explicit forbidden-files field in the packet
(`SKILL.md:22`) is a stronger scope fence than upstream's prose "stay in scope".

**Cons** — against superpowers SDD it is thin where thinness costs: no bound on
review/fix iterations ("fix and re-review until both pass", `SKILL.md:34`, is
unbounded), no ledger so nothing survives compaction, no artifact-as-file
discipline (packets are described but no mechanism keeps them out of the
coordinator's context), and no model-selection guidance beyond one sentence
(`SKILL.md:58`).

### `run-phases` (command, ours)

**Achieves** — runs every remaining phase of a workstream back to back without
human input, using `/compact` between phases for context economy.

**Can do**
- Deliberately sequential, with the reason stated: context economy, and
  sequencing must come from declared deps not the runner (`run-phases.md:13-16`).
- Picks the next phase by querying bd, not memory (`run-phases.md:25-29`).
- Names exactly what is auto-approved: deep-phase plan approval, per-phase
  commit, Codex critique (`run-phases.md:50-54`) — and treats invoking the
  command as the explicit opt-in for per-phase commits (`run-phases.md:35-36`).
- Post-compaction recovery contract: re-query `bd epic status` / `bd ready` and
  re-render before continuing (`run-phases.md:59-67`).
- Stops the whole run on a failed gate or exit criterion (`run-phases.md:73`).

**Pros** — the only surface in this set that solves *multi-phase* continuity;
upstream engines all terminate at one plan. Its auto-approval list is bounded
and enumerated, which is what makes unattended running safe rather than reckless.

**Cons** — it is a wrapper: all real discipline lives in `/phase-execution`. Its
context-recovery story depends on bd being correct; superpowers' ledger records
*commits*, which survive even a wrong tracker. And it commits per phase
(`run-phases.md:35`) — the same unprompted-commit behaviour the ledger already
rejected in agent-skills' `incremental-implementation` ("reject the source
workflow's mandatory per-slice commits") — here it is at least gated behind an
explicit user invocation.

### `implementer` (agent, ours)

**Achieves** — a bounded worker that implements one file-scoped task and reports
in a fixed format.

**Can do**
- Pins model and effort in frontmatter (`implementer.md:5-6`) and restricts tools
  to Read/Write/Edit/Bash/Grep/Glob (`implementer.md:4`).
- "You are not alone in the codebase" — do not revert work you did not make
  (`implementer.md:13`).
- Ask before coding if scope is unclear (`implementer.md:16`).
- Conditional test-first: write a failing/characterization test when dispatch
  asks or the codebase clearly needs it (`implementer.md:22`).
- Hard git prohibitions: no `git add .`/`-A`, no `--no-verify`, no amend, no
  editing forbidden files (`implementer.md:28-32`).
- Same four-value status contract as the SDD skill (`implementer.md:36-39`) and a
  seven-field report template (`implementer.md:43-51`).

**Pros** — it is a real, installed agent with enforced tool restriction; upstream
`implementer-prompt.md` is a template the controller must paste correctly every
time, so ours cannot drift per dispatch. The git prohibition block is stricter
than anything upstream ships for implementers.

**Cons** — much thinner than superpowers' implementer prompt: no self-review
rubric, no "in over your head" escalation triggers, no code-organization
guidance, no report-to-file indirection, and no TDD evidence (RED/GREEN output)
requirement. Its report is returned inline, so full detail lands in the
coordinator's context — the exact cost superpowers' report-file design avoids.

### `subagent-driven-development` (superpowers)

**Achieves** — executes a plan task-by-task with a fresh implementer, a
two-verdict task review, a bounded fix loop, and a whole-branch final review,
while keeping the controller's context clean and compaction-survivable.

**Can do**
- Worktree isolation before anything starts; never implement on main without
  consent (`SKILL.md:111-114`).
- **Plan-scoped ledger** at `<workspace>/progress.md` with its identity as line
  one; resume rules for complete tasks and mid-loop tasks; explicit statement
  that a controller that lost its place re-dispatched entire completed sequences
  (`SKILL.md:116-140`).
- Pre-flight conflict scan of the whole plan, batched into one human question
  before Task 1 (`SKILL.md:145-155`).
- Detailed model-selection policy by task class, including "always specify the
  model explicitly" and "turn count beats token price" (`SKILL.md:157-192`).
- Three shell scripts that keep artifacts out of the controller's context:
  `sdd-workspace` (per-plan git-ignored dir, `scripts/sdd-workspace:1-40`),
  `task-brief` (awk-extracts one task's text to a file,
  `scripts/task-brief:28-39`), `review-package` (commit list + stat + `-U10`
  diff to a per-range file, `scripts/review-package:32-46`).
- Dispatch composition rule with five required elements and a ban on pasting
  prior-task history — with the observed 42k-char failure cited
  (`SKILL.md:206-231`).
- Four-status handling with per-status action, and "never force the same model to
  retry without changes" (`SKILL.md:236-250`).
- Task review as a mandatory two-verdict gate; reviewer inputs are three file
  paths; a ban on pre-judging findings with the literal phrases that signal it
  (`SKILL.md:256-292`); `⚠️ Cannot verify from diff` items the controller must
  resolve itself (`SKILL.md:293-298`).
- **Bounded fix loop**: 5 rounds, rounds 1-3 resume the original implementer,
  rounds 4-5 fresh implementer one tier up; every round ends in a scoped
  re-review; ledger line per round (`SKILL.md:302-356`).
- **The breaker** at the cap: adjudicate each open finding into park / park-real
  / STOP-BLOCKED, with "adjudicate only at the cap" and "a silent discard is
  forbidden" (`SKILL.md:358-375`).
- Final whole-branch review on the most capable model, ONE fix dispatch for all
  findings (with the cost failure that motivates it), exactly one scoped
  re-review, no second wave (`SKILL.md:391-414`).
- Eight-row rationalization table covering exactly the shortcuts a controller
  takes (`SKILL.md:425-436`).
- Three prompt templates: implementer (`implementer-prompt.md`), task reviewer
  with a "do not trust the report" section and severity calibration
  (`task-reviewer-prompt.md:57-137`), scoped re-reviewer with ADDRESSED /
  NOT ADDRESSED verdicts (`re-review-prompt.md:71-92`).

**Pros** — by a wide margin the most operationally complete engine here. Three
mechanisms have no counterpart anywhere in our harness and are the reason it
wins: the ledger (compaction survival), the artifact-as-file scripts (context
economy that is enforced, not merely advised), and the bounded fix loop with a
breaker (termination guarantee our unbounded "until both pass" lacks).

**Cons** — heavy: ~500 lines plus three templates plus three scripts, and it
hard-codes its own conventions (`.superpowers/sdd/`, worktrees, `finishing-a-
development-branch`, per-task commits by the implementer) that collide with our
bd-anchored, conservative-git model. It has no external work tracker: the ledger
is a file the controller writes, so a controller that lies to its ledger has no
second source — where our bd state is written by a tool. Its "continuous
execution, do not check in" stance (`SKILL.md:17`) contradicts our
phase-execution approval gate (`phase-execution/SKILL.md:46`).

### `executing-plans` (superpowers)

**Achieves** — a minimal read-plan → todo → execute-each-task → finish loop for
harnesses without subagents.

**Can do**
- Worktree isolation (`SKILL.md:19`), critical plan review before starting with
  concerns raised to the human (`SKILL.md:20-23`).
- Todo-per-task, follow steps exactly, run the plan's verifications
  (`SKILL.md:27-31`).
- Hard stop conditions: blocker, plan gaps, unclear instruction, repeated
  verification failure — "ask rather than guess" (`SKILL.md:42-48`).
- A return-to-review trigger when the partner updates the plan or the approach
  needs rethinking (`SKILL.md:52-55`).
- Mandatory hand-off to `finishing-a-development-branch` (`SKILL.md:36-38`).

**Pros** — the only engine that states *when to go backwards* (`SKILL.md:50-55`);
our surfaces have no return-to-planning trigger short of failure. Cheap enough
that its whole content is 64 lines.

**Cons** — self-demoting (`SKILL.md:14`): in any subagent-capable harness it is
the wrong choice, so for us it is a substitute for nothing. No review of task
output at all, no fix loop, no context management, no recovery. Its only durable
idea is the revisit trigger.

### `implement` (mattpocock)

**Achieves** — a 7-line human-invoked instruction to build from a spec or
tickets and route through TDD and code review.

**Can do**
- Routes to `/tdd` "where possible, at pre-agreed seams" (`SKILL.md:9`) — the
  seam agreement is the TDD skill's gate, imported here.
- Test cadence rule: typecheck regularly, single test files regularly, full
  suite once at the end (`SKILL.md:11`).
- Routes to `/code-review` after (`SKILL.md:13`) and commits to the current
  branch (`SKILL.md:15`).

**Pros** — the cadence line (`SKILL.md:11`) is the single most useful sentence in
this file and is absent from every other engine including ours: it says when to
run *which* granularity of check. Being a pure router keeps it from duplicating
the skills it calls — the same architecture our `phase-execution` delegation
table aims at.

**Cons** — not an engine in any meaningful sense: no loop, no unit of work, no
review gate, no failure handling, no context management. Unconditional
"commit your work" (`SKILL.md:15`) violates our git-safety rule. Nothing here
substitutes for anything we have.

## Verdict

**Genuine overlap.** Only one pair truly overlaps: our
`subagent-driven-development` and superpowers'. Both are the same capability —
fresh implementer per task, review after each, dispatch hygiene — and the bucket
taxonomy already calls this family `substitutes` for the upstream members. Ours
is the thin version of theirs. `phase-execution` and `run-phases` do **not**
overlap with anything upstream: no upstream engine has a concept of a phase, a
roadmap, or a work tracker, and none runs more than one plan.

**Substitutes vs complements.** `executing-plans` and superpowers SDD are
substitutes for each other by their own decision graph (`SKILL.md:21-37`) and
`executing-plans` loses in our harness by its own admission (`SKILL.md:14`) —
adopting it would be adopting a fallback for a capability we have. mattpocock's
`implement` is a substitute for nothing; it is a router occupying the slot our
`phase-execution` delegation table occupies, and ours is strictly richer.
Our four surfaces are **complements**, correctly layered: `run-phases` (many
phases) → `phase-execution` (one phase, gate) → `subagent-driven-development`
(one plan's tasks) → `implementer` (one task). That layering is the thing this
comparison most confirms is worth keeping; upstream collapses all four into one
file, which is the shape the ledger already rejected once
(`planning-and-task-breakdown`, 2026-08-12).

**Strongest for what.** For a single plan executed to a high quality bar with a
guaranteed termination, superpowers SDD is clearly strongest, and its advantage
is mechanical, not stylistic: bounded fix loop + breaker (`SKILL.md:302-375`),
compaction-survivable ledger (`SKILL.md:116-140`), and file-based artifact
handoff (the three scripts). For multi-phase, tracker-anchored work with a
machine-checkable done-gate, ours is strongest — nothing upstream has an
equivalent of `phase-execution/SKILL.md:72-76`. For failure resilience under a
flaky API, ours wins on the inline-fallback rule
(`subagent-driven-development/SKILL.md:49-52`), which upstream lacks entirely.

**Where our harness is weakest, concretely:** (1) our review/fix loop is
unbounded (`subagent-driven-development/SKILL.md:34`) with no breaker and no
adjudication record; (2) nothing in our SDD survives a `/compact` mid-plan —
`run-phases.md:59-67` covers compaction *between phases* only, and bd stage state
does not record which fix round a task is in; (3) our dispatch has no mechanism
keeping briefs, reports, and diffs out of the coordinator's context — the rules
at `SKILL.md:41-45` are advice, where upstream's scripts make it structural.
Those three are the adoption candidates worth arguing; the rest of superpowers
SDD is convention we should not import.

Level 3 component inventory and the cross-skill matrix: [`components.md`](components.md).
