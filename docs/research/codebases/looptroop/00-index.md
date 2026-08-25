# looptroop — research registry

Repo: `reference_tools/looptroop` (submodule, pinned `7b129216`, 2026-08-24).
Local GUI orchestrator: ticket → LLM-council planning → PRD → bead-blueprint
JSONL → sequential OpenCode execution with Ralph-style retries → final tests
→ Manual QA → draft PR → human merge gate. v0.5.8, early-alpha. The only one
of the three evaluated repos that is a real workflow engine.

| Artifact | What it is | Produced by |
|---|---|---|
| [capabilities.md](capabilities.md) | Docs-first capability + architecture map @ 7b129216 | GPT-5.6-luna xhigh, 2026-08-24 |
| [../comparison-beadboard-aweb-looptroop.md](../comparison-beadboard-aweb-looptroop.md) | Two-reviewer assessment + consolidation (Sol high × Opus 5 medium) | 2026-08-24 |

## Verdict (consolidated)

**Reject as platform — the closest existing substitute for our workflow-graph
design, and it fails all four settled premises** (graph is compiled
TypeScript/XState, state is SQLite, "beads" are a private JSONL not bd,
runtime is OpenCode-only). **Adopt five mechanisms into the cr-o85 spec:**

1. Approve-what-you-read: sha256-bound human approval + approval/edit
   receipts (`artifactApproval.ts`).
2. Bounded attempt envelope: pre-attempt commit → worktree hard-reset
   preserving state dir → mandatory bounded dying-session note → fresh
   session (the physical half of "cyclic template, acyclic trace").
3. Per-phase context allowlists with ordered trim priority
   (`contextBuilder.ts`).
4. Resolved-config pinning with provenance (`locked_*` + `*_source` columns).
5. Declare-then-verify file effects (`fileEffectsAudit.ts`).

Key correction both reviewers made to the map: per-bead "gates"
(tests/lint/typecheck) are **self-reported strings**, not executed checks
(`completionChecker.ts:38-46`); real commands run only in the final-test
phase. Avoid: self-report as completion, bound sprawl (6 uncoordinated
counters, 5×10 worst-case retries — our two-iteration-layers hazard, live),
voters ranking slates containing their own draft, auto-push with conditional
`--no-verify`. Reopen if it externalizes the graph as validated data, adopts
real bd, or breaks the OpenCode lock.
