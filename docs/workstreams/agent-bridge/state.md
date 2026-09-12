# Agent bridge execution handoff

Updated 2026-09-12. The approved six-phase [roadmap](roadmap.md) and [coordination spec](../../specs/2026-09-11-workflow-coordination.md) are implemented and verified in `wf/bridge-slice0`, based at `71fea13`. The original paused authority changes were preserved. The user authorized committing this delivery and merging it into `main` on 2026-09-12. Verification below records the development worktree results; no push or reference-repository edits are included.

Beads is the work-state authority. Completed phase epics: P0 `cr-dba`, P1 `cr-o85.39`, P2 `cr-bwo`, P3 `cr-148`, P4 `cr-3zz`, P5 `cr-thh`.

## Delivered

- Sequential bridge execution with pinned checks, authenticated ship approval, target CAS, durable receipts and forward recovery.
- Ordinary bounded model decisions, distinct doubt, whole-brief UTF-8 budgets and original-owner capacity reservations.
- Independent child graphs with admit/start/status/drive/collect/cancel/recover; no child dependency scheduler or second database.
- Explicit selected-source integration with fresh review/check/approval and serialized target authority.
- Same-graph model successors and trusted changed-graph/model successors, preserving current child/bridge identity, prior artifacts, budget and approval obligations.
- Basic and design/spec templates, normal integration/replacement CLI commands and execution-skill wiring.

## Verification

Final gates: 1583 non-live, 143 process, 25 Beads and 66 acceptance tests; Ruff/format clean (217 files), strict mypy clean (109 source files). Fable 5.1 high approved the grouped corrections and final deltas. The resumed real proof passed with eight verified Claude/Codex activations, actual child overlap, a child doubt decision, fresh combined review and landing. Fixture signatures prove test authentication, not production human approval.

See [P1](verification/P1.md), [P2](verification/P2.md), [P3](verification/P3.md), [P4](verification/P4.md) and [P5 evidence](verification/P5.md). The ignored execution workspace retains failures, receipts, backend/session proof and exact source hashes. Its `p5-runtime-evidence.json` locates the original and continued live proof; completed model work was not restarted.

## Operating boundaries and remaining backlog

Use [child operations](../../usage/children.md) and [phase bridge/integration](../../usage/phase-bridge.md). Configure one canonical Beads workspace for all drivers. Driver concurrency is session-scoped; unknown process identity leaves cancellation pending. Integration collection is evidence, not landing permission. Existing provider limitations and role bindings remain in the configuration example; the real proof covers Claude and Codex.

Broader pre-existing work remains outside this six-phase delivery: discipline composition (`cr-o85.43`) and the legacy uncoordinated checkout-lock contract (`cr-o85.44`). The design/spec graph now has a real non-coding run, but `cr-o85.45` remains open for its additional domain-specific verifier criterion. The old token-budget issue is superseded by the explicitly approved byte-budget contract; it is not a claim of exact token accounting.

The generated-board renderer limitation (`cr-tew`) remains; consult Beads instead of hand-editing generated mirrors. Any later implementation should keep bounded handoffs, use Terra for routine work, and group substantial Fable reviews. No further phase execution remains in this roadmap.
