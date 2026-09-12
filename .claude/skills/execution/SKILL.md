---
name: execution
description: Use when approved work is ready to be built — a bd task or standalone plan to implement, a phase of a workstream roadmap to run, or an explicit request to walk every remaining phase. Trigger on execute/implement/build/"start phase" phrases for planned work. If no approved plan or roadmap exists yet, use planning first; if scope or behaviour is still unsettled, brainstorming.
---

# Execution

One engine, three scopes. Work-state lives in **beads** (epic = phase, flat task
= stage); tracking files are bd-generated. This skill owns the loop — selecting
the next unit, dispatching or implementing it, gating completion. It delegates
planning, test-first work, debugging, review protocol, and completion proof to
their own skills.

## Scope selector — take the first matching row

| Situation | Scope |
| --- | --- |
| User explicitly invoked `/run-phases` or asked to run every remaining phase without stopping | **workstream** — read `references/workstream-mode.md`. Its auto-approvals are reachable only from this row. |
| "Start/execute/begin phase N" of an existing roadmap | **phase** |
| A bd **epic** with stage children but no `ws-` label (planning's single-phase exit) | **task** — epic variant: drive the stages, close the epic through the same gate as a phase |
| A bd task carrying a `plan:` note, or an approved standalone plan | **task** |
| A bd task labelled `ready-for-agent` with no plan file | **task** — the bd record (description + acceptance + notes) is the work packet |
| None of the above | **stop** — invoke planning (no approved plan) or brainstorming (behaviour unsettled); do not improvise a route |

## Shared spine (every scope)

- **bd is the anchor.** `--actor "<runtime>:<session>"` (Claude Code:
  `cc:${CLAUDE_CODE_SESSION_ID:0:8}`; Codex: `codex:<thread>`) on every bd write. Close with evidence:
  `bd close <id> --reason "<verification evidence>" --actor "…"` — the reason
  is what renders into progress views; if it's not in bd, it's not real.
- **Risk comes from**: the roadmap row (phase scope — each phase states its
  own risk; default `standard`), or the Working Mode classification in
  `CLAUDE.md` (task scope).
- **Route each unit by risk:**
  - **small** → implement inline, self-check.
  - **standard** → light dispatch: one implementer + coordinator verification
    (`references/task-engine.md` → *Light path*).
  - **deep** → full engine: reviewers, bounded fix loop
    (`references/task-engine.md` → *Full path*).
  - Marked **test-first** → the implementer follows the
    **test-driven-development skill**.
  - Touches a **trust boundary** (untrusted input, authn/authz, secrets,
    uploads/webhooks, external integrations, LLM/agent features) → follow
    the **security skill** before implementation; its Ask-First gate applies.
  - Unexpected test failure → **systematic-debugging skill** before retrying.
- **Workspace** for working artifacts (briefs, reports, review packages,
  snapshots, the progress ledger): `scratchpad/execution/<slug>/` where slug =
  `<workstream>-<phase-id>` for phase work or the plan path with `/` → `-`
  for standalone work — never a bare basename (two workstreams both have a
  `plans/setup.md`). Gitignored, never committed. Contract in
  `references/task-engine.md` → *Workspace and ledger*.
- **Discovered durable work** — create a real stage, never a note that
  vanishes with the turn:
  `bd create "<title>" --parent <epic> -t task --description "<why>" --acceptance "<checkable>" --deps discovered-from:<stage-id> --actor "…" -q`
- **Return to planning** when either trigger fires: the plan or roadmap text
  changed underneath you, or the approach a unit assumes no longer fits what
  the code shows. Stop the loop, say which trigger fired, and invoke the
  planning skill (or brainstorming if behaviour itself is now unsettled).

## Phase scope

1. **Load context.** Resolve the roadmap (`--roadmap` or ask). Read the phase
   section: deliverables, spec references, exit criterion, risk. Resolve the
   phase epic by the bracketed phase-id join key:
   `bd list -t epic -l ws-<name> --json` → exactly one epic whose title starts
   `[<phase-id>]` (legacy fallback: `bd list --spec <roadmap.md> --json`).
   Zero or multiple matches → stop and report the mismatch; never re-seed —
   the epic exists from planning's Decompose. Confirm it is not closed. Check
   `bd blocked` / `bd dep tree <epic>`. Present deliverables, risk, and the
   ready stages.
2. **Plan (deep phases only).** Invoke the **planning skill** (Elaborate) →
   `docs/workstreams/<name>/plans/<phase>.md`; then the **document-review
   skill** on the plan; then present for approval. Do not proceed without it.
3. **Execute stages** — loop until no ready direct-child stage remains:
   - **Select a ready direct child, then call the bridge:** select the stage by
     judgment; its parent relationship, not its id shape, determines membership
     and the bridge validates that choice. Run
     `uv run python -m workflow_interpreter.foreman --config <foreman-config.toml> phase-bridge <epic_id> <stage_id>`.
     **Do not claim it:** the bridge claims atomically. Add `--retry` to mint a
     new attempt for an unfinished stage, or `--trace` to render current
     evidence read-only without running anything.
   - **Stage ↔ plan-task mapping (deep phases):** a claimed stage means
     executing exactly the plan tasks whose `Stage:` field names it, in their
     declared dependency order. A plan task naming no existing stage, or a
     stage no task names, is a plan defect — return to planning. Standard
     phases have no plan: implement the stage from the roadmap row's Spec
     Reference.
   - **Act on the one JSON object it prints; `state` is a fact, not an
     instruction.** The bridge never selects the next stage or decides whether
     to continue. `phase-exhausted` (exit 0) means every direct child is
     closed: go to step 4, without selecting another stage. `blocked` (exit
     0) names the open work preventing this stage: clear it or select another
     ready stage. `result` (exit 0) carries the result of a stage that ran: the
     bridge closes the stage as part of landing, so do not close it; render via
     the beads skill's `scripts/bd-render-tracking.sh` if it exists
     (`BD_RENDER=1 bash <beads-skill-dir>/scripts/bd-render-tracking.sh <name>`),
     else report the missing renderer; then continue the loop. `refused` (exit
     2) means an invalid request — not a direct child,
     empty description, no configured graph, detached or dirty coordinator, or
     ineligible `--retry`: fix the reported `reason`; never re-run unchanged.
     Exit 1 is a crash: report it, not a state.
4. **Exit — the discipline gate.** A phase closes only when it has stages and
   every one is closed. `bd list --parent` hides closed children by default, so
   count with `--all` or the gate can never pass:
   `n=$(bd list --parent <epic> --all --json | jq 'length'); u=$(bd list --parent <epic> --all --json | jq '[.[]|select(.status!="closed")]|length'); [ "$n" -gt 0 ] && [ "$u" -eq 0 ]`.
   On failure print the unclosed stages
   (`bd list --parent <epic> --all --json | jq -r '.[]|select(.status!="closed")|.id+" "+.status'`)
   and **STOP**. Then run the roadmap's exit criterion, then the
   **verification-before-completion skill**. Close the epic with the
   exit-criterion evidence.
   Worked both directions: `cr-o85.33` fully closed → `n=12 u=0` → gate passes;
   `cr-o85.34` partially closed → `n=30 u=5` → gate fails and names the 5.
5. **Report.** Re-render, `git status` (do not commit unless asked or under
   workstream scope), summarize: built, test results, open items, parked
   findings from the ledger.

## Independent child workflows

When the selected work calls for parallel independent graphs, the orchestrator chooses the graphs, role/model configuration and task inputs. Use an admitted coordination owner with finite capacity, then the normal `children admit`, `drive`, `status` and `collect` commands documented in `docs/usage/children.md`. The runtime routes declared outcomes and bounded loops; consult the LLM only at a declared decision or unresolved attention state. Collection is evidence, not stage closure.

Select the required receipt set explicitly and use `integration prepare`, then the existing `phase-bridge` command for fresh combined review, checks, ship approval and landing; see `docs/usage/phase-bridge.md`. Do not invent child dependencies or automatic result binding. A changed graph/model uses the trusted `children replace` operation; ordinary model decisions retain admitted pins and cannot bypass human gates or pending landing recovery.

## Task scope

For a bd task or single-phase epic (with a `plan:` note, `ready-for-agent`
label, or a plan the user hands over directly).

1. Read the plan if one exists, and the bd record (`bd show <id>`). Claim it
   (`bd update <id> --claim --actor "…"`). For a planless `ready-for-agent`
   task, the bd description + acceptance + notes are the work packet — route
   by Working Mode; if they are too thin to act on, return to planning.
2. Execute the plan's tasks in dependency order (the plan's `Dependencies`
   fields, not listing order), routed by risk exactly as in the shared spine.
   **Epic variant:** claim stages and map plan tasks to them exactly as phase
   scope step 3; close each stage as its tasks complete and its acceptance
   holds.
3. When every task is done: run the plan's verifications, then the final
   review (`references/task-engine.md` → *Final review* — it applies to
   inline-built work too), then the **verification-before-completion skill**.
4. Close the bd record with evidence. **Epic variant:** the epic closes only
   through the same discipline gate as phase scope step 4.

## Rationalizations

| Excuse | Reality |
| --- | --- |
| "I'll fix the findings myself, dispatching is overhead" | Controller fixes skip review and pollute coordination context. Re-dispatch the implementer. |
| "One more fix round will converge" | Past the cap rounds don't converge — the failure is structural. Adjudicate and route. |
| "The fix was small, skip the re-review" | Unreviewed fixes are how regressions land. Every round ends with a scoped re-review. |
| "This finding is obviously wrong, drop it" | Adjudication happens only at the cap, and every ruling is a ledger entry. Silent discards are forbidden. |
| "Close enough on spec" | A spec gap is open work. Fix it or hit the cap and adjudicate — the only exits. |
| "I'll close the stage now and verify later" | A close without evidence in `--reason` is a lie the tracker repeats forever. |

## Rules

- Never mark a phase done without the gate *and* the exit criterion.
- Never proceed past a deep-phase plan without user approval (auto-approved
  only under workstream scope, per its enumerated list).
- Never hand-edit generated tracking files — update bd, then render.
- Independent-critique steps run on a spawned critic subagent, separate
  from the implementer (see CLAUDE.md §Independent critique) — never
  skipped silently.
- If a stage blocks or fails verification, stop and report. Do not edit
  submodule internals.
