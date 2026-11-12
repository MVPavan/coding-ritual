---
trigger: "Settled, tracked work to build: a bead with acceptance, a standalone plan, a roadmap phase, all remaining phases, or a spec whose tickets are in Beads with blocking edges."
traits: [stop-on-failure]
steps:
  - id: implement#1
    when: always
    actions: [{trait: scope-selector}, {trait: risk-sized-review}]
    calls: [{to: "skill:discovery", when: material scope or behaviour is unresolved; nothing else starts}]
  - id: implement#2
    when: the units will span sessions and have no beads, or the scope is Phase or Workstream
    calls: [{to: "skill:tracker", when: "unit beads for units that will span sessions; each phase's epic by its lookup and defect rule"}]
  - id: implement#3
    when: Spec scope
    actions: [{trait: dependency-edges}, {trait: single-integration-branch}, {trait: worktree-per-significant-change}, {trait: worktree-base-verify}]
    loads: [{path: implement/spec-run.md, when: "its Setup, steps 1-4"}]
  - id: implement#4
    when: Task scope, each Spec ticket, and each coordinator-run stage from implement#6
    actions: [{trait: task-loop}, {trait: unit-bead-execution}, {trait: confirmed-cause-fix}, {trait: regression-proof-and-rerun}, {trait: attempt-log}, {trait: two-failure-stop}, {trait: finding-adjudication}]
    calls: [{to: "skill:tdd", when: risk calls for test-first or characterization}, {to: "skill:security", when: a material boundary change}, {to: "skill:systematic-debugging", when: a failure's cause is unclear}, {to: "skill:delegation", when: the router's delegation rule sends a unit to a worker}, {to: "skill:tracker", when: "a one-phase epic: its stage mapping and close gate"}, {to: "skill:land", when: "Spec scope: landing a ticket on the integration branch"}]
    loads: [{path: implement/task-engine.md, when: delegated units or multi-round review}]
  - id: implement#5
    when: "around each implement#4 run that delegates a unit or whose requirements or unresolved risk require independent review: a required brief review before it implements, the implementation review and fix rounds before it closes the unit or invokes land"
    actions: [{trait: bounded-fix-loop}, {trait: scope-base-review-package}, {trait: delegated-report-recovery}]
    calls: [{to: "skill:review"}]
    loads: [{path: implement/task-engine.md}]
  - id: implement#6
    when: Phase scope, or each phase implement#8 selects
    actions: [{trait: phase-loop}]
    calls: [{to: "skill:to-plan", when: a deep phase whose packet needs a plan}, {to: "skill:tracker", when: "the phase's epic, rendering after a stage or before a contractor call that coordinator writes precede, and the close gate"}, {to: "skill:land", when: "the handoff commits: a coordinator-run stage's, the bookkeeping after a contractor result, and any coordinator writes before a contractor call"}]
  - id: implement#7
    when: the coordinator runs independent graphs in parallel
    actions: [{trait: child-workflows}]
  - id: implement#8
    when: Workstream scope, an explicit request or /implement all phases
    actions: [{trait: workstream-mode}, {trait: context-recovery}]
    calls: [{to: "skill:tracker", when: render at each phase exit}, {to: "skill:land", when: "the per-phase commit, only when the invocation covers it; without it the walk stops at the phase end"}]
    loads: [{path: implement/workstream-mode.md}]
  - id: implement#9
    when: Spec scope, after its tickets
    actions: [{trait: pre-report-base-merge}, {trait: worktree-cleanup}]
    loads: [{path: implement/spec-run.md, when: "steps 8-10"}]
  - id: implement#10
    when: every exit
    actions: [{trait: implement-closeout}]   # new; variant of build-closeout
  - id: implement#11
    when: finished and verified, after implement#10, with this run's changes still uncommitted
    calls: [{to: "skill:land"}]
---

# Implement

For settled, tracked work to build: a bead with acceptance, a standalone plan, a
roadmap phase, all remaining phases, or a spec whose tickets are in Beads with
blocking edges. Work with no settled plan is the feature, refactoring or bug-fix
playbook. Unsettled units or questions, or a plan still to write, return to
`mvp-mode`'s planning route.

Execute authorized work through acceptance, verification and recovery. Beads owns
durable task state; a plan document is not a prerequisite for a clear task.

**The gates:** Carry authorization through necessary fixes; a review finding cannot authorize
scope expansion. Follow the delegation policy in `AGENTS.md`.
Risk labels: `small` is bounded, low-risk work; `standard` is a bounded behavior
change; `deep` is cross-cutting, high-risk, or materially unresolved work.
Small work stays inline. Standard work may stay inline or use one bounded worker
when beneficial. Deep work needs risk-appropriate independent review; separate
spec and quality reviewers only when the task requires them or the risks justify
both. Use configured models/effort; if dispatch is unavailable, continue useful
local work and state any required review that remains unperformed.

If the governing plan changes or code invalidates the chosen approach, reconcile
before dependent work continues. Preserve completed work on failure. An unresolved
stage or failed phase exit blocks phase completion and any dependent phase.
Commits, publication and broader work retain their existing authorization gates.

Workspace: `scratchpad/implement/<slug>/`, with a slug that distinguishes full
plan/workstream paths. Capture the starting revision and dirty-file baseline;
pre-existing edits are not automatically part of the task.

## 1. Scope

| Request | Scope |
|---|---|
| Explicit run-all-remaining-phases request or `/implement all phases` | Workstream; step 8 reads `implement/workstream-mode.md` |
| Implement a spec as a whole, its tickets in Beads with blocking edges | Spec; steps 3 and 9 read `implement/spec-run.md`. An explicit workstream request, a named phase or a bounded task keeps its own scope. A spec seeded as a workstream (epics anchored on a roadmap) runs under the Workstream or Phase scope: say which request is due and ask nothing else. A spec whose tickets are one epic with stages and edges runs here if its work is significant, else as Task in the current checkout |
| Execute a named roadmap phase | Phase |
| Task, standalone plan, or single-phase epic | Task, in the current checkout with no worktree |
| A bead with acceptance and no plan | Task; the bead is the packet |
| Material scope/behavior unresolved | Resolve that gap through `discovery`; nothing else starts (Not started, scope unresolved) |

A step whose scope does not apply stays in the list as `skip: <reason>`.

## 2. Track

Units that will span sessions but have no beads get them from `tracker` first
(step 4's child rule says the same). For Phase or Workstream scope, find each
phase's epic with `tracker` (its lookup and defect rule) before step 6 or step 8.

## 3. Spec setup

Spec scope only. Read `implement/spec-run.md` and run its Setup, steps 1-4: a
blocking edge for every real ordering that has none, one integration branch and
its run record, one worktree for a significant change, and the base check before
any work.

## 4. Task loop

For Task scope, each Spec ticket (in the spec's worktree, `implement/spec-run.md`
steps 5-7) and each coordinator-run stage that step 6 sends here.

**A bead with open children** runs them first. Holding its claim on resume,
unclaim it with a resume note. Claim one ready direct child at a time
(`bd ready --parent <id> --json`, keeping `parent == <id>`), run it through this
loop and close it with evidence. Claim the parent only once every child is closed,
for its aggregate verification and close. Children open but none ready: stop and
report which waits on what. Units that will span sessions but have no beads get
them from `tracker` first.

1. Read the request, existing plan if any, and Beads description/acceptance.
   Claim the exact task with `--actor "<coding-agent>:<unique-id>"`.
2. Implement in dependency order, within owned paths. Use test-first or
   characterization when risk calls for it; apply security to material boundary
   changes. When a failure's cause is unclear, use `systematic-debugging` and fix
   only a cause it confirms: prove the fix with a regression check when one is
   feasible, rerun the original failing scenario, log each attempt (hypothesis,
   change, result), and after two failed fixes stop and return the log to the
   task owner. Hardening other boundaries the defect exposes is the bug-fix
   playbook's step, and so is a top-level request to fix a bug: at top level
   return to `mvp-mode`; inside a delegated task, report that route to the parent.
3. Validate findings as they arrive. Fix confirmed in-scope defects, answer
   incorrect findings with evidence, and record unresolved decisions. Do not
   spend fix rounds implementing unverified feedback.
4. Run applicable project/plan checks and inspect the scoped final diff. Reuse
   valid evidence while its code, inputs and environment remain applicable.
   Small work needs no mandatory reviewer pair. Independent review is driven by
   explicit requirements or unresolved risk, not the act of closing a task.
5. Close with evidence and material limitations in `--reason`; report the result.
   Create durable follow-up work for discoveries outside scope, linked to origin.

For a one-phase epic, map plan tasks to its stage IDs (bound by `tracker`), run its
acceptance, then close it by `tracker`'s close gate with that evidence.

When the router's delegation rule sends a unit to a worker, invoke `delegation`;
for a delegated unit, read `implement/task-engine.md` for its brief, dispatch and
report statuses. Spec scope: landing a ticket on the integration branch is a
commit, so invoke `land` for it (`implement/spec-run.md` step 7).

## 5. Review loop

When step 4 delegates a unit, or the requirements or unresolved risk require
independent review. This step wraps each such step-4 run, every Spec ticket and
coordinator-run stage included: a required brief review comes before step 4
implements, and the implementation review and its fix rounds finish before step 4
closes the unit or invokes `land`; then step 4 resumes at its close. Small work
keeps step 4's rule: no mandatory reviewer. A required review that cannot run
leaves the unit open and the run ends **Changed, verification incomplete**.
For delegated units or multi-round review, read `implement/task-engine.md`.
It holds the scoped snapshots, the review paths, the bounded fix loop and the
final review. Invoke `review` for each independent review.

## 6. Phase loop

For Phase scope, and for each phase step 8 selects. Inside this loop, "step N"
names the loop's own numbered steps.

1. Resolve the supplied or unambiguous roadmap and read this phase's deliverables,
   spec references, acceptance, risk and exit criterion. Find the phase's epic with
   `tracker` (its lookup and defect rule).
2. Confirm the epic is not already closed, check blockers and claim the phase.
   Elaborate a deep phase through `to-plan` when its packet
   needs a plan; reuse approval covering this work rather than pausing again.
3. Select a ready direct child from `bd ready --parent <epic> --json`, keeping
   only beads whose `parent` is the epic (the query returns every descendant).
   Match deep-phase `Stage:` plan tasks to stage IDs and dependency order first;
   correct missing or unmatched mappings. A stage with unit beads (any children,
   open or closed: `bd list --parent <stage> --all --json`) takes step 4; any
   other takes step 5.
4. **Stage with unit beads:** never call the contractor for it. First read its
   trace, read-only: step 5's command with `--trace`. Proceed only on `state`
   `result` with `relation` and `relation_error` null. `blocked`, `refused` or
   unreadable output stops or enters step 6's recovery; an empty `blocking_ids`
   does not clear `blocked` (an unfinished admitted sibling blocks with an empty
   list). A non-null `relation` means the contractor already admitted this stage:
   run none of its units by hand; stop and report the recovery case. Otherwise
   release the phase claim with a resume note, run the stage through the Task loop
   (its child rule drains the units), verify the stage's aggregate acceptance and
   close it. Render through `tracker` where authorized and refresh the Beads
   export: every write comes before the handoff. Then hand off: invoke `land`
   (commit authority checked by `land`, `land/SKILL.md:49`) for the stage's
   verified owned changes and tracked bookkeeping
   (the Beads export and rendered tracking too) and return to step 3, confirming
   `git status` is clean immediately before the next contractor call; without it,
   preserve the work and stop with a precise handoff (stage, files, checks, the
   commit due), never stashing, discarding or reporting it as a contractor result.
   The contractor refuses a checkout with any dirt beyond its own stage's
   `.wf/export/<stage>.jsonl` and `.wf/repo-id` (`refused`, "coordinator checkout
   is not clean"); on resume, uncommitted work of a closed coordinator stage is
   that handoff, still owed, in the same order.
5. Call the contractor. Immediately before each call `git status` must be clean.
   If coordinator writes since the last handoff left it dirty (the claim's Beads
   export, a plan from `to-plan`, corrected mappings, a newly minted
   `.wf/repo-id`), hand them off first in step 4's order: render where
   authorized and refresh the export, then `land` them by path. Without commit
   authority, preserve the work and stop with step 4's handoff.
   `uv run python -m workflow_interpreter.foreman --config <foreman-config.toml> contract <epic_id> <stage_id>`.
   The contractor claims atomically and owns execution through closure; do not
   claim or close the stage separately.
6. Read the contractor's one JSON result. `phase-exhausted` means proceed to
   the close gate; `blocked` names work to clear or bypass with another ready
   stage; `result` means the stage landed and closed; hand off before the next
   stage in step 4's order. Render through `tracker` where authorized and refresh
   the Beads export, then invoke `land` for the bookkeeping (the rendered
   tracking, the Beads export, this stage's `.wf/export/<stage>.jsonl` and a newly
   minted `.wf/repo-id` still owed, staged by path) and return to step 3,
   confirming `git status` is clean immediately before the next contractor call.
   Landing leaves that export in the checkout, so the commit is due even with
   nothing rendered. Without commit authority, preserve the work and stop with
   step 4's handoff. On resume, a closed contractor stage's uncommitted
   bookkeeping is that handoff, still owed, in the same order. `refused` (exit 2)
   names an invalid request: fix its reason before retrying; exit 1 is a crash to report. Use
   `--trace` for read-only evidence, and `--retry` only to mint an eligible new
   attempt. Never edit generated tracking by hand.
7. **Close:** reclaim the phase if step 4 released it, run the roadmap exit
   criterion, then close by `tracker`'s close gate with its evidence.

## 7. Child workflows

The `docs/usage/` documents named here are this project's; read them when present.

For parallel independent graphs, the orchestrator chooses inputs, models and
an admitted coordination owner; the foreman makes one declared decision per
tick, the inspector contains activations, and the crew runs its vendor CLI.
Follow `docs/usage/children.md` for bounded `admit`,
`drive`, `status` and `collect`. Collection is evidence, not stage closure.
Select receipts with `integration prepare`, then use the contractor's `contract`
command for combined review, checks and landing (`docs/usage/contractor.md`).
Replace a changed graph/model through trusted `children replace`; ordinary
decisions retain admitted pins and human gates. Do not invent child dependencies
or automatic result binding.

## 8. Workstream walk

Workstream scope only: an explicit request to run the remaining phases or
`/implement all phases`. Read `implement/workstream-mode.md` and follow its
preflight, walk and recovery; each phase runs through step 6. Render tracking at
each phase exit through `tracker`. Make the per-phase commit through `land`, and
only when the invocation covers it; when it does not, or the user said not to
commit, stop at that phase's end with the handoff (Stopped, no commit authority).

## 9. Spec finish

Spec scope, after its tickets: run `implement/spec-run.md` steps 8-10, the tip
merge and its checks, the report, and the cleanup. The merges stay this step's
own actions, since `land` makes no merge.

## 10. Close out

On every exit, finished or stopped. Close finished beads with evidence and
material limitations in `--reason`; create follow-up work for discoveries outside
scope, linked to origin (`discovered-from`). Unclaim the rest, each with a resume
line. Persist the workspace ledger (`progress.md`: review rounds, evidence,
snapshot labels, finding dispositions) so a later session resumes from it. On
Spec scope, report the worktree path and the run record's path as the recovery
pointer.

## 11. Land

Only when finished and verified, after step 10, with this run's changes still
uncommitted: invoke `land`. No stopped or unverified path lands. Every commit in
this playbook goes through `land` (steps 4, 6, 8 and here); `land` refuses
unverified work and, without commit authority, returns a commit plan.

## Reply

- **Finished:** the scope, the beads closed with their evidence, the checks run,
  and `land`'s commits or plan, or its refusal and the gap it named.
- **Stopped, blocked:** what waits on what: open children with none ready, or
  unfinished work with no eligible phase and its blocking dependencies.
- **Changed, verification incomplete:** a required check or independent review
  could not run (dispatch or its environment unavailable). The units changed and
  verified, the checks run, the requirement still missing and why, the evidence
  it still needs, and where the work is preserved; its beads stay open, step 10
  runs and step 11 does not.
- **Stopped, no commit authority:** the stage, phase or tickets, the files, the
  checks, and the commits or merges due.
- **Stopped, failure:** the attempt log and the failed gate (a stage, a phase
  gate or an exit criterion).
- **Stopped, base mismatch:** the expected and actual bases, the worktree path
  and the run record's path.
- **Not started, scope unresolved:** the gap and its route (`discovery`, or
  `mvp-mode`'s planning route).

Every reply also names the Implement playbook, the scope, the steps skipped and
what the closeout left (beads unclaimed with resume lines, the ledger, any
worktree).
