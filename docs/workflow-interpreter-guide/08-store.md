# 08 — Store and run ledger

The **record store** holds every fact the engine decides on: one SQLite ledger at
`<repo>/.wf/ledger.db`, gitignored, exported per task into git. It is the only one; the
tracker is a mirror, and chapter [11](11-language-and-pluggability.md) owns it.

`WorkflowStore` (`bdio/api.py`) is the typed write surface, `WorkflowReads` the read
one, and `LedgerStore` (`ledger/store.py`) the only implementation — nothing is pinned,
located or selected per root. **Reads:** `get_row`, `find_rows`, `probe` · **Writes:**
`_create_row`, `_merge_metadata`, `_close_row`, `_close_gate`. Minting, dispatch,
grading, gates, events and findings compose from those four over typed carriers in
`metadata_json`.

## The ledger's rules

Eighteen tables (`ledger/schema.py`), from `meta` and `tasks` through
`contractor_records`, `claims` and `tracker_outbox`. `SCHEMA_VERSION` is *derived* from
`len(MIGRATIONS)`, so a migration cannot be added without moving the version; migrations
are forward-only, and `_refuse_unfoldable_state` guards the v4→v5 fold against a
database still carrying `tasks.state`.

**Opening is four steps in a fixed order** (`ledger/database.py`): migrate under an
**exclusive** fence; take the **shared** fence and hold it for the connection's life;
apply pragmas; verify the `repo_id` and `wrapper_root` pins before answering anything.
`flock` is per open file description, so a second descriptor asking `LOCK_EX` would
block on your own `LOCK_SH`.

**One store method is one transaction**, and no subprocess, file I/O or tracker call
may happen inside one: a gate close lands its row, projected columns, the `seq` from
`tasks.next_seq`, the consumed nonce, the recorded signature and the enqueued attention
projection **together or not at all**. A busy writer refuses by name
(`LedgerBusyRefusal`) rather than retrying, and every statement is parameterised.

## `closed()` is a latch; consumers ask `retired()`

Closure is not a stored state (`ledger/closure.py`): a stored CLOSED could only be
written after the export bytes exist, so it could never be *in* the export.

```text
closed(task):
    if state != LANDED:                           return False   # the gate, first
    if tasks.export_oid is set:                   return True    # the latch
    oid = anchor_oid(task)          # HEAD:.wf/export/<task>.jsonl first, then the ref
    if oid is None or hash(.wf/export/<task>.jsonl) != oid:   return False
    tasks.export_oid = oid                        # derive once, then latch
    return True
```

The latch is what makes it monotonic: a live re-export is a function of mutable state,
so recomputing would reopen every closed task after one migration or one attention
drain. The file **on disk** is hashed, never a fresh export, and the anchor comes from
`reverify.anchor_oid` itself, so `closed()` and `ledger verify` cannot disagree.

`retired(task) = closed(task) ∨ state ∈ {ABANDONED, ABANDONED_EXTERNAL}`. Terminal
cleanup (`foreman/tick.py`), archive (`ledger/archive.py`), sibling admission
(`contractor/admission.py`) and the succession guard (`contractor/adapter.py`) read
`retired`, because an abandoned task never exports and waiting for closure would hold
its worktree, refs and siblings' admission forever.

## The three orchestrator verbs

The contractor closes on its own only when the graph reaches `shipped`; otherwise it
hands back with the record ADMITTED and there are three moves — no override lands an
unshipped task.

| Verb | Command | What it does |
|---|---|---|
| continue | sign the gate, re-invoke `contract` | the same attempt resumes |
| retry | `contract <epic> <task> --retry` | attempt + 1, from the ledger's snapshot, no tracker read; refused once the task shipped |
| abandon | `phase abandon <task> --reason …` | record → ABANDONED, outbox `Close`, task `retired`. Idempotent, and refused for a task that LANDED, derives `closed()`, or whose landing merely *began* — a journalled landing intent means the commit may already be on the target ref, and that owes recovery, not retirement |

## Export, rebuild, verify, archive — `python -m workflow_interpreter.ledger --config C`

- **`export <task>`** writes `.wf/export/<task>.jsonl` for the orchestrator to commit;
  `ExportPin` runs before `adapter.close`. Task facts only: `export_oid`/`exported_at`
  are elided (`ELIDED_TASK_COLUMNS`) as facts about the *file*, and the header pins
  `repo_id` — a UUID in the committed `.wf/repo-id` — so an export imports into a clone
  at any path. Every table is in `EXPORT_TABLES` or `NON_EXPORTED` with a stated reason,
  checked against the schema rather than a second hand-written list.
- **`pin-export <task>`** re-pins `refs/wf/exports/<task>` from the file already on disk
  — the recovery for a crash between write and pin. It never re-exports, and refuses a
  task that has not landed.
- **`import [task …]`** rebuilds from each task's newest anchor: parse before the fence,
  one exclusive fence, one transaction, whole-state rebuild. It **replaces** the
  exportable state, so a task no named anchor describes does not survive it — and it is
  how a fresh clone gets a ledger, after which `closed()` derives on the first ask.
- **`verify <task>`** re-verifies every approval from the committed export alone,
  against the two anchors it may not take from the export — the repository (`HEAD` blob
  first, the export ref second) and an operator `allowed_signers` trust root — naming
  which anchor answered.
- **`reconcile <task>`** repairs the mirror: release a claim stranded in the admission
  window, drain the task's unacked attention projections, drain its outbox — reporting
  conflicts, because the human at that command is the one who decides.
- **`archive <task> --bundle …`** refuses unless the task is `retired`, bundles
  `refs/wf/<root>/*`, verifies the bundle, then deletes run folders and refs. Not
  clone-portable: a default clone does not fetch those refs.

## Rebuilding a ledger

`.wf/ledger.db` is this checkout's working state and `git clean` may take it. Two
anchors bring a task back, and `import` prefers them in this order:

| Anchor | Where | Written | Survives |
|---|---|---|---|
| close | `HEAD:.wf/export/<task>.jsonl`, then `refs/wf/exports/<task>` | at landing, by `ExportPin` | a clone, once committed and pushed |
| checkpoint | `refs/wf/checkpoints/<task>` | at **every activation close** (`ledger/checkpoint.py`) | this checkout only — local, never committed, never pushed |

The close anchor wins wherever one exists, because it is written after the last
activation close and is therefore the newer. Same emitter, same bytes, same D3 rules;
only the namespace differs — and that is what keeps them apart, since `anchor_oid`
cannot see the checkpoint one. A task carrying nothing but checkpoints is **never**
closed, and the `tasks.export_oid` latch is elided from every export, so no rebuild sets
it. One ref per task, overwritten; the blobs it drops are unreachable and git gc takes
them, and a checkpoint that fails logs `wf.ledger.checkpoint_refused` and closes the
activation anyway.

A rebuild restores exactly `EXPORT_TABLES` and **loses** everything else — pending
`tracker_outbox` rows and held `claims`, plus `sessions`, `artifacts` and `usage`. Those
are re-derived, never guessed: `reconcile <task>` re-enqueues a `Close` the restored
`closed()` says is owed and releases a stranded claim, and the next admission re-takes
the claim through the ordinary path. So the mirror may lag a rebuild by one `reconcile`.
