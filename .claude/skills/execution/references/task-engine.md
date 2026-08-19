# Task engine — dispatched execution

Consulted from `execution` when a unit routes **standard** (Light path) or
**deep** (Full path), or whenever the coordinator should not hold
implementation context. The coordinator coordinates; fresh workers implement;
reviewers gate. Inline fallback stays valid when delegation itself fails —
delegation is the default, not a fetish.

## Roles

- **coordinator** (this session): curates context, dispatches, tracks the
  ledger, adjudicates at the cap. Does not implement or fix findings itself,
  except under the two named delegation-failure fallbacks in *Status
  handling* below (blocked twice; 529/timeout after the retry).
- **implementer** (agent): one bounded task per dispatch.
- **spec-reviewer / code-reviewer** (agents): both follow the **code-review
  skill**. Initial reviews are role-separated; **re-reviews go to the
  code-reviewer, whose re-review mode covers spec and quality findings alike**
  (the skill says so).

Specify the model explicitly on every dispatch — an omitted model silently
inherits the session's. Implementer as pinned in its agent file; initial
reviewers strong; scoped re-reviews of small fix diffs may take a cheaper
tier. Prefer fewer turns over cheaper tokens.

## Workspace and ledger

Create `scratchpad/execution/<slug>/` (slug rule in SKILL.md). It holds task
briefs, implementer report files, review packages, snapshots, saved review
findings, and `progress.md` — the ledger. bd remains the truth at stage
grain; the ledger records what bd cannot: fix-round position, snapshot
labels, parked rulings, deferred minors.

`progress.md` line 1 is its identity: `# <plan path> — <epic/task id> — SCOPE_BASE <sha7>`.
Append one line per event:

```text
Task 3: dispatched (brief task-3-brief.md, report task-3-report.md)
Task 3: review r0 — 1 critical, 2 important, 1 minor (findings review-t3-r0-findings.md, package review-t3-r0.diff)
Task 3: minor (deferred): <one-liner>
Task 3: fix round 2/5 (2 addressed, 1 open — <one-liners>; snapshot t3-r2)
Task 3: parked — <finding> — ruling: <why the code stands>
Task 3: complete (review clean | 2 parked)
```

**Save every review verbatim**: when a reviewer returns, write its full
report to `review-<task>-r<round>-findings.md` before acting on it. The open
findings list, round number, and snapshot labels must be recoverable from
files alone.

**After any compaction:** re-read `progress.md`, the latest findings file,
and re-query bd + `git status` before dispatching anything. A coordinator
that lost its place re-dispatches completed work.

## Diffs without commits — the snapshot model

Implementers do not commit (conservative git), so reviews are packaged from
the **working tree**, not from commit ranges:

- `SCOPE_BASE` = `git rev-parse HEAD` recorded once in the ledger when the
  scope starts. It rarely advances; all tracked changes since it — committed
  or not — are the work under review.
- `<execution-skill-dir>/scripts/review-package.sh full <SCOPE_BASE> <workspace> <label> [paths…]`
  → one file with `git status`, `git diff <SCOPE_BASE> -- <paths>` (tracked,
  staged or not), and the full content of untracked files under the paths.
  It also snapshots those files to `snap-<label>/`.
- Fix rounds: `<execution-skill-dir>/scripts/review-package.sh fix <SCOPE_BASE> <prev-label> <workspace> <label> [paths…]`
  → the diff between the previous snapshot and now — exactly what changed
  since the last review. Record the label in the ledger.

For dispatched (full-path) reviews the package never enters the
coordinator's context — pass its path. The coordinator reads a package
itself only where this document says so: the light path's inline
code-review and the final Simplification look.

## Dispatching a task

1. **Extract the brief**:
   `bash <execution-skill-dir>/scripts/task-brief.sh <plan> <N> <workspace>`
   writes `task-<N>-brief.md` (plan preamble — Origin/Goal/Out of
   scope/Constraints — plus the task section). For work with no plan file,
   write the packet to the brief file yourself: goal, owned **and forbidden**
   files, origin doc section, invariants, required tests, verification
   commands, commit policy, test-first flag, trust-boundary flag (routes the
   implementer through the security skill).
2. **Dispatch a fresh implementer** with paths, not contents: the brief path,
   a report-file path (`task-<N>-report.md`), and the constraints line. Never
   paste prior-task history or full files into the dispatch — everything
   pasted stays resident in your context for the rest of the session.
3. **Status handling** — require one of the four values:
   - `DONE` → confirm the report file exists and names verification commands
     and output, then verify/review per path below.
   - `DONE_WITH_CONCERNS` → read the concerns from the report **first**;
     resolve each (answer it, ledger it as accepted, or dispatch a fix)
     before any review. Concerns are not noise to forward.
   - `NEEDS_CONTEXT` → answer from the plan/spec, re-dispatch the same task.
   - `BLOCKED` → **systematic-debugging skill**, then: missing context →
     supply it; task too big → split it; the plan itself is wrong → return
     to planning. Blocked twice → split smaller or implement inline.
   - 529 / timeout / API overload → wait 5s, retry once, then implement
     inline.
   - Never force the same model to retry with an unchanged prompt.

## Light path (standard units)

1. Brief → dispatch one implementer → status handling as above.
2. Coordinator verifies: run the unit's verification commands yourself and
   read the diff (`review-package.sh full`, then apply the **code-review
   skill** inline — both sections, abbreviated to the changed surface).
3. Verification fails → one re-dispatch with the specific failure; failing
   again → systematic-debugging skill. No multi-round loop on the light path.
4. Close the unit with evidence. The independent critique happens at the
   scope's final review, not per unit.

## Full path (deep units)

**Preflight (once per plan, before Task 1):** scan the plan against the
binding constraints and `.claude/project/invariants.md`. Contradictions and
ambiguities become **one batched question** to the user now — not N
interruptions mid-loop. Under workstream mode, a blocking contradiction is a
plan defect: stop the run.

### Review gate (per task)

1. Package: `review-package.sh full <SCOPE_BASE> <workspace> t<N>-r0 [owned paths]`.
2. **Dispatch spec-reviewer, then code-reviewer**, each with: mode, brief
   path, report path, package path, and the plan's global constraints copied
   verbatim. The protocol lives in the **code-review skill** — do not restate
   it in the dispatch. Save each returned report to its findings file. Both
   verdicts are required — a task is never complete with one missing.
3. **Relay findings verbatim.** Never annotate a finding with "probably
   fine", "seems pedantic", or "optional" — pre-judging corrupts the loop.
   Adjudication happens only at the cap.
4. Route the results:
   - **Minor** → ledger as `minor (deferred)`. Never enters the fix loop; the
     final review triages them.
   - **Plan-mandated** (the plan's text requires the flagged behaviour) → the
     human decides. Present the finding and the plan text.
   - Spec ❌, Critical, Important, or a confirmed ⚠️ item → the fix loop.

### The fix loop — five rounds maximum

A round = one fix dispatch + one scoped re-review. **A round is consumed only
when a valid fix report exists and its re-review ran.** `BLOCKED`,
`NEEDS_CONTEXT`, 529/timeout, or a missing/incomplete fix report are recovery
events (handled per *Status handling*), not rounds.

- **Rounds 1–3**: re-dispatch the implementer with the open findings verbatim
  plus the brief and report paths — the report file is the persistent memory
  across dispatches.
- **Rounds 4–5**: fresh implementer on a **stronger model**, with brief path,
  report path, open findings, and the framing: "A prior implementer attempted
  this task N times; you own it now. Read the report file for what was
  tried." Three failed resumes usually means the implementer cannot see its
  own problem.
- **Every round**: the fix report must name the covering tests, the command
  run, and its output before you dispatch the re-review. Then package the fix
  delta only — `review-package.sh fix <SCOPE_BASE> <prev-label> <workspace> t<N>-r<R>` —
  and dispatch the **code-reviewer** in re-review mode with the findings
  list, brief, report, and package paths. New Critical/Important breakage in
  the fix diff joins the open findings; out-of-scope observations go to the
  ledger as deferred minors — they never extend the loop.
- **Every round**: save the re-review to its findings file and append the
  ledger line (with the snapshot label).

**The breaker.** If round 5 still leaves findings open, stop dispatching and
adjudicate each open finding yourself — you hold the plan and cross-task
context the reviewer lacks:

- Reviewer wrong or contestable → park with a ruling for why the code stands.
- Real but nothing builds on it → park with a ruling saying real-and-deferred.
- Real and load-bearing (a later unit builds on it, or it reveals a plan
  defect) → **STOP**: ledger `BLOCKED — <reason>`, report to the user with
  the finding, the plan text, and the fix history.

Adjudicate only at the cap — earlier is pre-judging with a different name.
Rule on each open finding only after verifying it against the code and
answering it with evidence (the receiving-code-review skill's Verify and
Respond steps).
Every adjudication is a ledger entry; a silent discard is forbidden.

A task completes when both verdicts are clean or every open finding is parked
with a ruling at the cap. Never move on with open Critical/Important findings
that are neither fixed nor parked.

## Final review

After all units are complete (this applies to inline- and light-path work
too):

1. Package the whole scope:
   `review-package.sh full <SCOPE_BASE> <workspace> final`.
2. Dispatch the code-reviewer on the strongest available model, pointing it
   at the package **and the ledger's deferred-minor and parked lines** so
   they are triaged — fixed, or explicitly accepted — rather than lost.
3. **Independent critique**: spawn a fresh critic subagent (separate from
   the implementer; model per CLAUDE.md §Independent critique) on the
   packaged scope — pass the package path and the ledger's deferred/parked
   lines, never your conclusions.
4. Findings → **ONE** fix dispatch carrying the complete list (never one
   fixer per finding — each rebuilds context and re-runs suites), then
   exactly one scoped re-review (`review-package.sh fix … final-fix`).
   Residual findings get the breaker's adjudication matrix: park with a
   ruling, or STOP on load-bearing ones and report to the user. No second
   fix wave.
5. **Simplification look (deep scope only).** Read the final diff and ask:
   would a new team member understand this faster than a simpler version?
   Before touching anything, answer why the code is the way it is
   (Chesterton's Fence — `git blame` if needed; can't answer → don't touch).
   One simplification at a time, existing tests must pass **unmodified** —
   a simplification that requires editing tests changed behaviour: revert it.
   Behaviour includes **side effects and ordering**, which tests routinely
   don't assert — check those by reading, not by the suite alone.
   Scan for concrete signals, not vague smells: 3+ nesting levels, 50+ line
   functions, nested ternaries, boolean flag parameters, repeated
   conditionals. Clarity beats cleverness — explicit code wins over compact
   code that needs a mental pause. Guard against the pass's own failure
   mode, over-simplification: don't remove abstractions that exist for
   testability or extensibility, and don't optimize for line count. Removed
   or weakened error handling "because it's cleaner" is a red flag, not a
   simplification. A refactor that would touch 500+ lines gets automation
   (codemod, sed, AST transform), never hand edits.
   Skip the pass entirely when the diff is already minimal.

Carry parked-finding summaries into the bd close `--reason`. The workspace is
disposable after the epic/task closes.

## Task sizing

- One deliverable per dispatch — never bundle.
- Cap the prompt: only the files and spec sections the task needs.
- Cap the result: short status contract inline (status, one-line summary,
  files changed, concerns one-liner, report path); detail goes to the report
  file. Full file contents never enter the coordinator.
- No parallel implementers on the same files. No raw session history to
  workers. Fanning out at all requires the independence test in
  `.claude/rules/core/01-delegation.md` to pass first.
