# 08 — Store and run ledger

## Why the seam exists

Every write goes through one API: `WorkflowStore` (`bdio/api.py`). Nothing above it
names a transport. Underneath is a `StoreBackend` protocol with a deliberately tiny
surface:

**Reads:** `get_row`, `find_rows`, `identity`, `probe`, `kind`
**Writes:** `_create_row`, `_merge_metadata`, `_claim_and_merge_metadata`,
`_close_row`, `_close_gate`

Five write methods for the entire system. Minting, dispatching, grading, gates, events
and findings are all composed from those five over typed carriers stored in metadata.
That is what made a second backend possible at all.

## Two backends

| | **bd (Beads)** | **Run ledger** |
|---|---|---|
| Storage | The beads workspace | SQLite at `<repo>/.wf/ledger.db` |
| Row identity | Bead ids | `task_id` + per-task `seq` |
| Concurrency | bd's own | `BEGIN IMMEDIATE` + a `flock` fence |
| Good at | Being visible to humans and `bd` tooling | Speed, atomicity, not polluting the tracker |

The same `WorkflowReads` runs over both unchanged, because every query is expressed as
carrier filters and every carrier lives in `metadata_json`.

**One backend is pinned per root at creation and never changes.** A root is never moved
between stores.

## Choosing the backend

`RootBackendLocator` must answer *before* the root is loaded — you cannot read the root
to learn where to read the root. Three sources in order (`foreman/locator.py:1-40`):

1. **The contractor record's `root_backend`**, written at prepare — the only source that
   can answer for a root that does not exist yet.
2. **The ledger's `roots` row**, or its `tasks` row for a run with no contractor.
3. **A refusal.** A root nobody pinned could be read from the wrong store, and reading
   it from the wrong store *"would report a live run as missing."*

If the contractor record and the store disagree it refuses rather than preferring one:
*"neither answer may be preferred silently."*

## The ledger's rules

Fifteen tables: `meta`, `tasks`, `roots`, `activations`, `gates`, `nonces`,
`signatures`, `events`, `sessions`, `findings`, `artifacts`, `usage`, `landings`,
`projections`, `restore_pending`. The schema version is *derived* from the migration
list length, not declared.

**Opening is four steps in a fixed order** (`ledger/database.py:1-20`): migrate under
an **exclusive** fence; take the **shared** fence and hold it for the connection's
life; apply pragmas; verify the `repo_hash` and `wrapper_root` pins before answering
anything. The order matters because `flock` is per open file description — a second
descriptor asking for `LOCK_EX` would block on your own `LOCK_SH`.

**One store method is one transaction**, and no subprocess, file I/O or `bd` call may
happen inside one. A gate close lands its row, projected columns, the `seq` from
`tasks.next_seq`, the consumed nonce, the recorded signature and the enqueued attention
projection **together or not at all**.

**A busy writer refuses by name rather than retrying**, so contention is visible.

**Every statement is parameterised, including JSON paths.**
`json_extract(metadata_json, ?)` takes its path as a bound value, so no filter key is
ever concatenated into SQL.

## The one thing that never moves

**Claims stay in bd.** `LedgerStore._claim_and_merge_metadata` refuses outright
(`ledger/store.py:334-338`): *"a claim write is refused rather than kept in a second,
invisible table."*

So a ledger-backed run still has a bd presence — the task bead and its claims. The
ledger holds the run's mechanics; bd holds the work item. Deliberate coexistence (D20),
not a half-done migration.

## Export, import, verify, archive

- **Export** writes `.wf/export/<task>.jsonl`; the orchestrator commits it. `ExportPin`
  runs before `adapter.close`.
- **Verify** (`python -m workflow_interpreter.ledger verify TASK`) checks three trust
  anchors in order: the HEAD blob at `.wf/export/<task>.jsonl`, then
  `refs/wf/exports/<task>`.
- **Archive** bundles before deleting.

## Known wart

`bdio/backend.py:8-11` still says *"`bd` is the only backend today, and `BdClient` is
its only implementation."* `LedgerStore` is now a second implementation. The code is
correct; the comment is stale.

## Where this is going

Three independent reviews (see [11-language-and-pluggability.md](11-language-and-pluggability.md))
converged on the same verdict: `StoreBackend` is a record-store port shaped like bd,
being asked to double as tracker portability. The intended next increment makes SQLite
the only record store and replaces the bd backend with a much smaller tracker port.
