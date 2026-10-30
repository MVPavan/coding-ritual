---
skill: execution
domain: engineering
stage: X
substage: Coordination
secondary: []
family: plan-execution
aliases: [phase-execution, run-phases]
status: active
---
# execution

Use to execute tracked multi-step work, a standalone plan, or a roadmap phase. Clear bounded implementation can proceed directly under AGENTS.md.

<!-- registry:generated traits -->
- `scope-selector`: Pick task, phase or workstream scope from the request and route unresolved material scope back to planning or brainstorming.
- `risk-sized-review`: Size work small, standard or deep and match inline work, delegation and independent review to that size.
- `task-loop`: Claim the exact task, implement in dependency order within owned paths, run applicable checks, and close with evidence and material limitations.
- `finding-adjudication`: Verify each incoming review finding against requirements, code and primary evidence before acting, and give each a visible disposition: fix a confirmed in-scope defect, answer an incorrect one with a retained ruling, record an out-of-scope follow-up.
- `phase-loop`: Resolve the roadmap phase's single epic, drive ready stages through the contractor that owns execution to closure, and refresh tracking between stages.
- `close-gate`: Close a phase only when it has at least one stage, every stage is closed, and its roadmap exit criterion has run with evidence recorded.
- `workstream-mode`: Run remaining phases in order only on explicit opt-in, with per-phase tracking refresh and commits only when the invocation covers them.
- `child-workflows`: Run independent graphs as admitted child workflows where collection is evidence and landing goes through the contractor, not automatic result binding.
- `context-recovery`: Stay in context while useful and, before compacting or handing off, persist scope, decisions and next work to the ledger, tracker and Git, then rebuild from those rather than from a summary.
- `stop-on-failure`: Let a failed gate, exit criterion or material blocker stop advancement and diagnose instead of re-dispatching without new evidence.
- `bounded-fix-loop`: Group compatible confirmed findings into one fix unit, re-review only the delta plus any breakage it caused, adjudicate every round, and treat a small fixed count of completed fix/re-review rounds as a ceiling rather than a target.
- `scope-base-review-package`: Review uncommitted working-tree and untracked changes against a recorded base revision by passing the authorized owned-path list, never attributing a baseline-dirty file's whole diff to the task.
- `delegated-report-recovery`: Interpret each delegated worker's status (done, done-with-concerns, needs-context, blocked) and recover by supplying context, splitting, debugging or replanning, since bare repetition is not recovery.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **superpowers:skill:skills/subagent-driven-development** `reference_harnesses/superpowers/skills/subagent-driven-development/SKILL.md` @ 44c9b2d
  - merged from: executing-plans
  - modified: absorb executing-plans as a degraded inline mode for when subagents are unavailable
- **superpowers:skill:skills/subagent-driven-development** `skills/subagent-driven-development/SKILL.md`
  - merged from: executing-plans
  - modified: absorb executing-plans as a degraded inline mode for when subagents are unavailable
- **agent-skills:skill:skills/code-simplification** `skills/code-simplification/SKILL.md` @ 7676817
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-14` **adopt** (2026-10-14-migration:125): Correction 2026-08-14 (stale-claim audit, post-implementation-passes Round 2): previous reason 'covered by ak-guide' was false — ak-guide carried 6/45 componen…
- `2026-08-12` **adopt-merged** (2026-10-14-migration:111): Adopted-merged into the execution skill's task engine (comparison: harness_lifecycle/skill-comparisons/plan-execution-engines/): bounded 5-round fix loop with …
- `2026-08-11` **adopt-merged** (2026-10-14-migration:046) *(superseded)*: The only plan executor with bounded fix loops, capability escalation and an adjudication ledger that survives compaction. Superpowers' own writing-plans names …
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [skill-comparisons/plan-execution-engines](../../../archive/skill-comparisons/plan-execution-engines/)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
