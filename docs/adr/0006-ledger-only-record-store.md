# ADR 0006 — the ledger is the only record store; the tracker is a contractor-only port

- **Status:** Accepted
- **Date:** 2026-09-20
- **Deciders:** repo owner
- **Reviewed by:** two independent proposals (Opus 5 high, Fable 5.1 high) consolidated and cross-analysed at design time, then an Opus 5 high critic round on v1 (3 BLOCKER, 7 MAJOR, 4 MINOR, all applied); one independent critic per slice during the build
- **Related:** `docs/workstreams/store-restructure/roadmap.md` §3 and its decision table R1–R13 — the authority for every detail this ADR states once; ADR 0005 (the run ledger), whose §4 decisions this amends; ADR 0003 (argv ceiling, now bd-tracker traffic only)
- **Supersedes, in `docs/workstreams/run-ledger/roadmap.md` §4:** **D6** (attention drains by a direct label write per tick), **D7** (bd keeps the contractor record, one label and `root_backend`), **D8**'s bd half (bd-minted root ids), **D9** (task closure through a stored CLOSED), **D16** (every root reachable from the *tracker*), **D18** (backend pinned per root, with a locator), **D20** (integration claims stay in bd). Every other run-ledger decision and ADR 0001–0005 stand.

## Context

ADR 0005 put engine facts in a SQLite ledger behind the existing `StoreBackend` seam
and left bd as a second backend. Three independent reviews then reached the same
verdict in near-identical terms: `StoreBackend` is a **record-store port shaped like
bd**, asked to double as tracker portability. bd cannot evaluate the row guard, hold
signature bytes, or transact a gate close, so the ledger already implemented the port
better than bd could — while two live backends cost a locator, a factory family, a
`root_backend` pin and a backend-parameterised contract suite.

Three deferred defects were all one question — what an export *is*. The pinned export
always carried `export_oid = NULL`; `landings` was neither exported nor cleared, so
import FK-failed on any landed ledger; and the header pinned `sha256(absolute path)`, so
a committed export could not be imported into a clone elsewhere. "Rebuild from the
committed export" did not work at all.

## Decision

**The SQLite ledger is the only record store, and the tracker becomes a small
contractor-only port with a durable outbox.** R1–R13 are the decision; the five that
this ADR exists to make discoverable:

1. **One store** (R1). `LedgerStore` is the only implementation of
   `WorkflowStore`/`WorkflowReads`. The bd backend, `BackendKind`, the locator, the
   `root_backend` pin and the `backend` columns are gone. The contractor record, the
   integration-target claims and the task-brief snapshot are ledger tables
   (`contractor_records`, `claims`), so every step after the claim runs tracker-free.
2. **A four-operation tracker port** (R2, R3). `get`, `children`, `blockers`, `apply`,
   plus a declared capability set and a closed union of desired states — never a
   toggle, so a retry is one write. Only the contractor holds one. The claim is issued
   after every ledger-side refusal and immediately before the ledger transition:
   ordinary refusals never touch the tracker, ambiguity (`Unknown`) refuses admission,
   and the stranded-claim shape is detected per task rather than by a sweep.
3. **Mirror writes go through `tracker_outbox`** (R2, superseding D6), enqueued inside
   the transaction of the fact they mirror and drained after it — at the contractor's
   own write, at driver exit, or from `ledger reconcile`. Nothing durable waits on a
   tracker, and no tracker call happens inside a foreman tick or a store transaction.
4. **Closure is derived and latched** (R6, superseding D9). `closed(task)` is LANDED
   plus an export anchor, written once into `export_oid` and never recomputed;
   `retired = closed ∨ ABANDONED ∨ ABANDONED_EXTERNAL` is what cleanup, archive,
   sibling admission and the succession guard read. A stored CLOSED could only be
   written after the export bytes existed, so it could never be *in* the export.
5. **The export is facts about the task** (R5, R8). The pin columns are elided, the
   header pins a committed `repo_id` UUID, `landings` and `contractor_records` are
   carried, and a schema-derived test requires every table to be in `EXPORT_TABLES` or
   in `NON_EXPORTED` with a stated reason. Ids are minted by the ledger with the epic
   as an input under one tightened path grammar, so `PROJ-12` or `#123` can be a
   `tracker_ref` without ever reaching a refname or a worktree path.

## The cutover is a clean break

R12: no dual id scheme, no dual header, **no read shim** for the retired bead-metadata
record. A task whose old record is at PREPARED or ADMITTED is refused by name with the
remedy — the one shape a silent break would run twice — while one already LANDED or
retired is left alone. The v4→v5 migration likewise refuses rather than drop a
`tasks.state` it cannot fold into a record, which would leave a task open forever.

## Consequences

- The backend-parameterised contract suite, the locator and the canary are deleted with
  the seam; the cost ADR 0005 accepted deliberately is no longer paid.
- ADR 0003's argv ceiling now applies only to bd *tracker* traffic — `show`,
  `list_children`, `list_dependencies`, and the assignee, status, label and close writes.
- A claim-capable tracker must be reachable for PREPARED→ADMITTED; everything after
  that runs from the ledger. Offline work is `NullTracker` plus `contract … --brief`.
- A fresh clone rebuilds a closed task's ledger from the committed export at any path.
  In-flight tasks do not survive ledger deletion; checkpoint export addresses that.
  `refs/wf/exports/<task>` remains the close-time anchor, so the mirror closes at the
  moment it did before and a clone lags only until the export commit is pushed.
- bd is now one tracker among three (`BdTracker`, `FileTracker`, `NullTracker`) behind
  one conformance suite — which makes GitHub or Jira an adapter, not a migration.
