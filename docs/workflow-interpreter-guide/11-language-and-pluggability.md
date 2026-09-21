# 11 — Language and pluggability

The ledger is the record store ([08](08-store.md)). This chapter is the other seam: the
**tracker** — what humans read, and the one thing swappable for somebody else's service.

## The port

Four operations, a capability set, and a closed union of desired states
(`tracker/port.py`). Only the **contractor** holds one: the foreman, the inspector and
the crew never import `tracker/`, because a tracker call on the run loop is a run that
stops when somebody else's service does.

```python
class TrackerPort(Protocol):
    kind: TrackerKind
    capabilities: frozenset[TrackerCapability]   # CHILDREN BLOCKERS CLAIM CLOSE ANNOTATE FLAG
    def get(self, ref: TrackerRef) -> WorkItem | None: ...
    def children(self, ref: TrackerRef) -> tuple[WorkItem, ...]: ...
    def blockers(self, ref: TrackerRef) -> tuple[Blocker, ...]: ...
    def apply(self, intent: TrackerIntent) -> TrackerResult: ...
```

There is deliberately no `list`: the one sweep that would have needed it — finding tasks
stranded in the claim window below — is answered per task from the ledger.

`TrackerIntent` is a **state**, never a toggle, so re-applying it is one write and not
two: `Claim(actor, held=…)`, `Close(reason)`, `SetFlag(flag, on)`, `Annotate(key, text)`
(defined, no caller emits one today). `apply` answers `Applied(observed)` — written and
read back — or `Conflict(observed)`, the tracker disagreeing, which never rolls back a
landed commit, or `Unknown(reason)`, which goes to the outbox. Reads raise
`TrackerUnavailable` (retryable) or `TrackerRefused` (permanent).

## The three implementations

`tracker.backend` in the foreman configuration picks one, through the single
construction site `tracker_for` (`contractor/tracker_wiring.py`); `tasks.tracker_ref`
and `tasks.tracker_kind` record which tracker a task's foreign id belongs to.

| Backend | Capabilities | Notes |
|---|---|---|
| `BdTracker` | all but `ANNOTATE` | claim is `bd update --assignee <actor> --status in_progress`, **not** bd's own `--claim`, which binds the row to bd's user identity and refuses a row assigned to anyone else |
| `FileTracker` | all six by default | one JSON document; the tracker a repository with no issue service actually wants, and the one a test can drive to every answer the port can give |
| `NullTracker` | none | every intent `Applied(observed=None)`. A run with no tracker is not degraded, it is a run with no mirror — it owes only the brief, as `contract … --brief <file>` |

An absent capability is not an error: callers branch on `capabilities`, never on a
failure. A tracker with no `BLOCKERS` records `blockers_checked=false` and proceeds
unless `tracker.blockers_required` is set — either way the trace can tell "nothing
blocked it" from "nobody asked".

## Where the tracker is touched, and nowhere else

| When | Call |
|---|---|
| prepare | `get` → the `WorkItem`, whose brief is snapshotted onto the record; `children` validates the selected stage; `blockers` |
| admit | `apply(Claim)` immediately before the ledger transition |
| close, abandon, attention | `apply(Close)` / `apply(SetFlag)` through the outbox |

Everything after prepare is answered from the ledger — the record and its brief snapshot
— which is what makes a retry, a recovery and a landing possible with the tracker gone.

## Claim first, then admit

Every ledger-side refusal runs first (`contractor/admission.py`) — selected stage,
`_refuse_other_admission`, HEAD and policy checks — *then* the tracker `Claim`, *then*
the `contractor_records` transition to ADMITTED under `BEGIN IMMEDIATE`. Ordinary
refusals never touch the tracker, and the call still precedes the transaction, so no
I/O sits inside one. What that costs, and it is worth knowing before you operate this:

- **A claim-capable tracker must be reachable for PREPARED→ADMITTED.** `Unknown`
  refuses admission: a task whose tracker may or may not hold it for this actor is not
  one a second session can be told about. Offline work is `NullTracker`.
- **A `Conflict` that observed a CLOSED item** retires the record as
  ABANDONED_EXTERNAL rather than waiting for a claim nobody will grant — the same
  retirement `phase abandon` performs, decided by somebody else.
- **The crash window has one shape:** a `contractor_records` row at PREPARED plus an
  item claimed by us. Detection is per task, never a sweep — the next `contract` on that
  task, or `ledger reconcile <task>`, releases it through the same
  `release_stranded_claim`. A ledger-side refusal *after* the claim releases it at once;
  only a crash leaves it.

## The outbox

`tracker_outbox` holds intents awaiting a tracker that can answer, and is what makes
the tracker a mirror rather than a dependency. Three properties it exists to give:

1. **Nothing durable waits on a tracker.** A landed, exported, pinned task is closed
   whatever bd says; `Unknown` leaves a row and the process exits.
2. **One pending row per desired state**, keyed by `intent_key`. A second enqueue
   replaces the pending one, so a drain is always repeatable.
3. **No window between a fact and its mirror row.** An enqueue that follows a ledger
   fact happens *inside that fact's transaction*. It is not exported: it records what
   *this checkout* still owes, which is neither a fact about the task nor true in a
   clone.

Three drain points, and none of them is a foreman tick:

- **immediately after the fact**, when the contractor mirrors one (`adapter.mirror`);
- **at driver exit** (`drain_at_exit`) — every driver, not only `contract`. It runs from
  a `finally`, bounded and non-fatal, so a mirror failure cannot replace the run's own
  exit status; unapplied rows stay pending;
- **`ledger reconcile <task>`**, a human asking for the mirror to be caught up.

A drained `Conflict` retires its row and is logged `wf.tracker.mirror_conflicted`: the
tracker answered, and re-sending the same state would not change the answer.

The one derived label is `wf:attention` (`ledger/reconcile.py`), present iff a
non-terminal root of the task has an OPEN gate. Every transaction that can change that
predicate journals a `projections` row; the reconciler recomputes, enqueues one
`SetFlag` and acks, under a task-keyed lock.

## Adding a tracker

Implement the four operations, declare `capabilities` honestly, read back every write
and return `Applied`/`Conflict`/`Unknown` — `Unknown` only when the outcome is genuinely
ambiguous, because it is the one answer that refuses an admission. Then run
`tests/test_tracker_port.py`: the same landing rig runs against null, file and bd, and
what changes between the three is the port and nothing else. Deliberately **not**
abstracted: git, SQLite, gate signing, the evidence model, any tracker query language.

## Language

Python, deferred rather than settled. Three independent reviews in 2026-09 split 2–1 for
Go on a greenfield build and 3–0 against rewriting now: the measured cost was never
CPython (≈49 MiB RSS, 0.25 CPU-seconds) but the five `bd` round trips per tick, which
the ledger removed. Decide at the concurrency fork, with the process and acceptance
tests as the oracle rather than as code to translate. Traps for that day: `Pdeathsig`
binds to the parent *thread*; `database/sql` is a connection pool, breaking both the
one-transaction-per-method rule and the flock; Go randomises map iteration order where
the foreman decides by iterating records.
