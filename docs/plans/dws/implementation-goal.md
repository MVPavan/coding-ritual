# DWS engine and CLI implementation goal

Prepared 2026-09-22. Submit this document to the goal tool to start execution;
writing it does not activate a goal. Deliver the complete engine/CLI first.
MCP implementation remains a subsequent goal.

## Objective and sources

Implement and validate Delivery A: the Python core, daemon-backed `dws` CLI,
providers, immutable evidence storage, QMD lexical retrieval, durable crawling,
concurrency controls, retention, diagnostics, backup and restore. The engine
must work without FastMCP, model inference or hosted-provider credentials.

Follow the [implementation plan](cli-engine-implementation-plan.md),
[roadmap](../../workstreams/dws/roadmap.md),
[PRD](../../brainstorms/dws/DWS_PRD.md), and
[technical design](../../brainstorms/dws/DWS_Design.md).
The owner's execution instructions below supersede conflicting older execution
preferences; the existing product and evidence guarantees still apply.

## Workspace and task scope

- Do all DWS work in the existing `/data/codes/dws` worktree on branch `dws`.
  Never create another worktree or implement in another checkout. Prefer the
  current branch; if a branch is needed, name it `DWS-<purpose>` and use this
  same worktree. Coordinate any branch switch with all running agents.
- Restrict Beads mutations to the twelve `ws-dws` epics and their descendants.
  Work on P1–P11 for this goal; P12 (`cr-w7f`) remains the later MCP delivery.
  Use parent-scoped readiness and verify parent/label ownership before claiming
  work. Do not take unrelated issues from the shared queue or alter their state.
- Preserve unrelated files and historical execution receipts. Keep DWS plans,
  reports and usage documents in DWS documentation subfolders; temporary output
  belongs in ignored `scratchpad/dws/`. Commit, push and publication require
  separate authorization under repository policy.

## Orchestrator and agent contract

- The primary agent orchestrates: scopes work, assigns owned paths, integrates
  candidates, dispositions findings, verifies acceptance, and maintains DWS
  Beads state. Delegate product implementation and fixes rather than doing them
  silently in the coordinator.
- Launch implementation workers through Codex CLI using `gpt-6-astra`, reasoning
  effort `medium`, with their working directory set to this worktree.
- Launch adversarial reviewers through Codex CLI using `gpt-5.6-sol`, as
  confirmed by the owner. Use `high` for routine reviews and `xhigh` for difficult
  architecture, durability, security or unresolved correctness questions. Record
  the chosen effort in each assignment. Do not substitute models silently.
- Use a fresh, independent, read-only reviewer for each bounded candidate.
  Give implementers a Bead, outcome, owned paths, constraints and acceptance
  checks; give reviewers the requirements, exact candidate changes and evidence.
  Every agent must preserve others' edits and create no worktree.
- Workers and reviewers are delegated leaf agents: perform the assigned work
  directly and do not spawn another orchestration layer. Return the actual
  concise result in the final response, not a link to a report that the CLI's
  final-output capture may overwrite.
- Serialize overlapping writes and freeze reviewed paths while review runs.
  Parallel work is permitted only on independent owned paths. Send justified
  findings back to the implementer, rerun affected checks, and obtain fresh
  review of material fixes before closing the task. No unverified model fallback
  or unbounded retry loop: escalate a persistent blocker with concrete evidence.

## Context-efficient orchestration

- Coordinate from compact goal state and Beads: current objective, active DWS
  issue, child/session IDs, owned paths, candidate revision, last verified
  outcome, unresolved findings, evidence pointers and next action. Recover from
  this state after interruption; do not reconstruct it by rereading transcripts.
  Beads remains the task-status authority, not a second Markdown task ledger.
- Give children bounded briefs with relevant source paths, acceptance criteria
  and decisions. Require concise delta reports: status, changed paths/revision,
  checks and results, findings/blockers, and precise evidence references. Keep
  full logs available behind those references rather than injecting them into
  the coordinator's context. Reviewers inspect the actual candidate independently.
- Prefer completion notifications or metadata-only status checks. Read new
  summaries when state changes; avoid frequent polling, repeated unchanged
  output, and routine reads of full child conversations or reasoning histories.
- Open primary evidence selectively for a material finding, contradiction,
  missing proof, unexpected change, stall/failure, or acceptance decision. Start
  with the cited file, diff hunk or log range; expand only if the decision still
  cannot be made. Do not duplicate a child's whole investigation or reread
  unchanged artifacts.
- A child's success statement is not verification. Before accepting work, match
  the candidate revision to the independent review and actual check results,
  inspect the scoped final diff/status, and resolve material findings. Later
  edits invalidate affected evidence. Preserve uncertainty in the goal state
  rather than spending context to manufacture confidence. Minimize opens and
  context use while preserving correctness, independent review and release gates.

## Python and verification policy

- Prefer end-to-end and integration tests through the real CLI/API, actual
  SQLite/files, QMD, browser and worker boundaries. Cover observable behavior,
  not private helper structure. Use isolated deterministic fixtures; separate
  live-provider smoke tests from the stable suite.
- Add focused unit tests only where they give useful coverage that integration
  tests cannot efficiently or reliably provide, such as policy boundaries or
  precise fault cases. Avoid redundant mocked tests and test-count targets.
  Preserve test-first regression/failure proof where risk warrants it.
- Use Pydantic extensively for domain records, requests/results, configuration,
  provider-normalized data and structured validation. Define each shared model
  and rule once, then reuse it across services, CLI/API and later MCP. Follow
  repository Python conventions, explicit types, uv, Ruff and strict mypy.
- Keep behavior at its owning layer so a correction has one implementation
  point. Ordinary algorithms and resource handles do not need artificial
  Pydantic wrappers. Avoid duplicate schemas, speculative abstractions and
  unrelated cleanup.

## Execution order

1. Re-read live DWS issues and Git state. Reconcile the existing package, lock
   and QMD pilot results with this branch before building on them. Their recorded
   landed commits were absent from `dws` at the readiness check; inspect exact
   source/evidence and integrate only justified DWS changes here. Do not merge
   unrelated workflow-engine work or repeat completed implementation blindly.
2. Reconcile DWS tracking references and remaining qualification limits. The
   local lock prototype does not prove actual QMD/container-volume behavior.
   Finish P1, including `cr-0km.4` image/browser qualification, `cr-0km.6`
   CLI-first documentation, then runtime inventory and contract freeze as their
   dependencies permit. Keep superseded package history intact.
3. Execute the roadmap dependencies in small, reviewable increments: evidence,
   CLI/daemon, shared runtime controls, acquisition/discovery, retrieval, durable
   crawl, operations, and release qualification. Expose usable CLI behavior as
   each slice becomes available. Write phase plans just in time within DWS.
4. For every work item: implement → integration/E2E evidence → independent
   adversarial review → implementer fixes → affected checks/review → orchestrator
   acceptance. Close only the DWS item whose criteria are satisfied. Report
   progress, actual evidence, limitations and next work without claiming skipped
   checks passed.

## Completion

Delivery A is complete when a fresh default Compose installation demonstrates
search, static/PDF/rendered fetch, exact read/retrieve, bounded crawl/status/
cancel, pin/export/GC and backup/restore through the CLI; restart and failure
tests preserve acknowledged jobs and evidence; scope and resource limits hold;
all applicable Delivery A acceptance gates and independent reviews pass; and
measured limitations and operational instructions are recorded. Leave the MCP
epic open with the stable core contracts needed for its later wrapper.
