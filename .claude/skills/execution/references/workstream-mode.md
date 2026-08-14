# Workstream mode — unattended multi-phase walk

Reachable **only** when the user explicitly invoked `/run-phases` or asked to
run every remaining phase unattended. Reading this file is not the opt-in;
the user's invocation is. Without it, phase scope and its approval gates
apply.

> **Sequential by design.** One phase at a time, `/compact` between, for
> context economy — phases walk in roadmap order even when deps would allow
> parallelism. Sequencing comes from the declared deps, never from this
> runner. For genuinely independent phases, run separate phase-scope sessions.

## Preflight — once, before the first phase

- Record the walk's authorization in the workspace ledger
  (`workstream mode: authorized by user invocation <date>`), so a
  post-compaction session can prove the opt-in instead of assuming it.
- Record the **dirty-tree baseline**: `git status --porcelain` →
  `<workspace>/baseline-dirty.txt`. Files dirty *before* the walk belong to
  the user, not the walk.
- Reconcile the roadmap against bd: every roadmap phase id must match
  exactly one epic title `[<phase-id>] …`. Zero or duplicate matches → stop
  before running anything.

## The walk

1. Read the roadmap for **phase order** (the roadmap is authoritative for
   order; bd for status). Resolve the phase epics:
   `bd list -t epic -l ws-<name> --json` (legacy fallback:
   `bd list --spec <roadmap.md> --json`).
2. The next phase = first epic in roadmap order that is not closed and not
   blocked (`bd blocked`).
3. Run it through **phase scope** (SKILL.md), with the auto-approvals below.
4. After the phase passes its gate + exit criterion:
   - render: `BD_RENDER=1 bash .claude/skills/beads/scripts/bd-render-tracking.sh <name>`
   - refresh the durable mirror and commit: `bd export -o .beads/issues.jsonl`,
     then stage **only files the phase's work actually touched** (from the
     ledger and implementer reports — explicit paths, never `git add .`)
     plus the export and regenerated tracking, and commit. A file in
     `baseline-dirty.txt` may be staged only if the phase's tasks modified
     it — and then stop and ask instead, because the commit would capture
     the user's pre-existing edits. Invoking this mode is the explicit
     opt-in for per-phase commits; no push, no `bd dolt push`.
5. `/compact`, then **re-query bd** (`bd epic status --json`, `bd ready`) and
   re-render before continuing — bd is the source of truth, not conversation
   memory.
6. Continue from step 2. Stop when every phase epic is closed, or a phase
   fails its gate or exit criterion.

## Auto-approved under this mode — the complete list

- Deep-phase plan approval (phase scope step 2) — approve immediately after
  document review.
- Per-phase commit (step 4 above).
- Codex critique/review — run when available, capacity policy per `AGENTS.md`.

Nothing else is auto-approved. The task engine's breaker still stops on
load-bearing findings; the discipline gate still stops on unclosed stages.

## Context management

- Rule out continuing in the current window before reaching for compaction —
  continuing costs nothing and loses nothing; compact only when the next
  phase no longer fits.
- `/compact` between phases — never `/clear` (it kills the session). Pass an
  instruction argument stating what to preserve (e.g.
  `/compact keep phase-N decisions, open findings, and the next phase's plan`)
  so the summary keeps what the next phase needs.
- Compaction turns the primary source (the session as it happened) into a
  secondary one: it restores facts, not reasoning. Anything whose *why* must
  survive belongs in the ledger or bd before compacting.
- Within a large phase, `/compact` between stages; then re-read the workspace
  ledger and re-query bd (task-engine → *Workspace and ledger*).
- Persistent state lives in: bd (`bd epic status`, `bd ready`,
  `bd list --parent <epic> --status closed` with close reasons),
  `docs/workstreams/<name>/plans/`, and the workspace ledger.

## Failure handling

- Phase fails gate or exit criterion → stop the whole run, report, do not
  continue.
- Test failure → systematic-debugging skill; failing twice → stop and report.
- Dispatch failures (529, BLOCKED) → task-engine recovery rules.
