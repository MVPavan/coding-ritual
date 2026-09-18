# Store restructure — design and plan

Status: DRAFT v2 (v1 consolidated from two independent proposals — Opus 5 high and
Fable 5.1 high — on the same brief at `d20a728`, validated against code, then
cross-analysed by Fable 5.1 high with both proposals and the consolidation in hand.
v2 applies the Opus 5 high critic round on v1 + epic `cr-nwy9`: 3 BLOCKER, 7 MAJOR,
4 MINOR, all verified — closure latched not recomputed; clone test retargeted off
archive; D5's guard kept through S1; mirror closes on the ref; child root format
restored; D6/D9/D16 listed as superseded; epic string under the same grammar; abandoned
tasks retire.)
Owner: workflow-interpreter engine.
Supersedes, in `docs/workstreams/run-ledger/roadmap.md` §4: D6 (drain point), D7, D8
(bd half), D9 (closure through CLOSED), D16 (reachability), D18, D20. Keeps every
other run-ledger decision, ADR 0001–0005.
Guide chapters to rewrite when this lands: `docs/workflow-interpreter-guide/08-store.md`,
`11-language-and-pluggability.md`.

## 1. Problem

`StoreBackend` (`workflow_interpreter/bdio/backend.py`) is a record-store port shaped
like bd, asked to double as tracker portability. bd cannot evaluate the row guard, hold
signature bytes, or transact a gate close; the ledger already implements the port
better than bd can. Two backends are live, pinned per root, with a locator, a factory
family and a parameterised contract suite holding them together.

Three defects were deferred into this work because each is a question about what an
export *is*:

1. The pinned export always carries `tasks.export_oid = NULL` — the oid is the hash of
   the file that would contain it (`bridge/journal.py:168` runs after the write). A
   rebuilt ledger can never archive; terminal cleanup defers forever (`cr-p7dg`).
2. `landings` is neither exported nor cleared; import FK-fails on any landed ledger and
   D17's fallback is lost on rebuild (`cr-ho9m`).
3. The export header pins `repo_hash = sha256(absolute path)` (`ledger/paths.py:33-37`)
   and re-checks it on import — a committed export cannot be imported into a clone at
   another path. "Rebuild from the committed export" does not work today at all.

And one structural conflict found only in cross-analysis: the bridge record's CLOSED
state is written *after* the export (`bridge/landing.py:600-611`), so CLOSED can never
be *in* the export. Moving the record into an exported ledger table — which both
proposals do — either violates D5 ("never closable before the record is durable") or
loses the record on rebuild. §3.5 resolves it.

## 2. Terms

This roadmap is written in the names the code has at `d20a728`. S0 renames the four
actors to one story — **contractor** (phase bridge: takes one task from the tracker,
owns it to a landed commit, closes it), **foreman** (unchanged: one decision per tick,
never does the work), **inspector** (supervisor: contains each activation, watches,
records the exit, grades the claim), **crew** (runner: the vendor CLI). After S0, read
bridge → contractor, supervisor → inspector, runner → crew throughout.

- **Record store** — the ledger. Every fact the engine decides on.
- **Tracker** — bd, GitHub Issues, Jira, a plain file, or nothing. What humans read:
  title, brief, status, one attention flag, one closing comment.
- **Mirror** — the tracker's copy of a ledger fact, written after commit via the outbox.
- **Outbox** — `tracker_outbox` table: intents awaiting a tracker that can answer.
- **Anchor** — where an export's bytes are durable: `HEAD:.wf/export/<task>.jsonl`
  (survives a clone) or `refs/wf/exports/<task>` (local, survives `git clean`).
- **Derived closed** — `closed(task)` computed from LANDED plus a resolving anchor;
  never a stored state.

## 3. Architecture

### 3.1 The line

```
bridge · foreman · supervisor ──▶ SQLite ledger (.wf/ledger.db, gitignored)
                                       │ export: task facts only
                                       ▼
                             .wf/export/<task>.jsonl  (committed)
                                       ▲  rebuild, any clone, any path
bridge only ──▶ TrackerPort ──▶ bd | GitHub | Jira | file | null
                (outbox, after commit; never inside a transaction)
```

The ledger is the truth, the export is its durable form, the tracker is a mirror.

### 3.2 Record store

`LedgerStore` is the only implementation. `WorkflowStore`/`WorkflowReads` stay as the
typed surface. New tables: `bridge_records`, `claims`, `tracker_outbox`. Deleted:
`bdio/client.py`, `foreman/locator.py`, the factory/locator family in
`bdio/backend.py`, `BackendKind`, `root_backend`, the `backend` columns,
`LedgerClaimUnsupported`, `_assert_no_landings`, the backend-parameterised suite,
`bdio/canary.py`; `BdClient` construction in `foreman/__main__.py`,
`ledger/__main__.py`, `costs/__main__.py:103`.

### 3.3 Tracker port

```python
class TrackerPort(Protocol):
    capabilities: frozenset[TrackerCapability]   # CHILDREN BLOCKERS CLAIM CLOSE ANNOTATE FLAG
    def get(self, ref: TrackerRef) -> WorkItem | None: ...
    def children(self, ref: TrackerRef) -> tuple[WorkItem, ...]: ...
    def blockers(self, ref: TrackerRef) -> tuple[Blocker, ...]: ...
    def apply(self, intent: TrackerIntent) -> Applied | Conflict | Unknown: ...
```

`TrackerIntent` is a closed union of desired states — `Claim(actor)`, `Close(reason)`,
`SetFlag(flag, on)`, `Annotate(key, text)` — never a toggle, so a retry is safe.
`Applied(observed)` is written and read back. `Conflict(observed)` is the tracker
disagreeing; the caller decides and never rolls back a landed commit. `Unknown(reason)`
goes to the outbox. Reads raise `TrackerUnavailable` (retryable) or `TrackerRefused`
(permanent). `NullTracker` declares no capabilities; every run still completes.

Where the tracker is touched — nowhere else:

| When | Call | Required |
|---|---|---|
| prepare | `get` → title, brief, status, parent snapshotted into the record | yes, unless `NullTracker` with `--brief` |
| prepare | `children`, `blockers` | capabilities; absent → explicit stage, `blockers_checked=false` |
| admit | `apply(Claim)` **before** the ledger transition (§3.4) | when `CLAIM` declared |
| close | `apply(Close)` via outbox, once `closed()` derives true on the ref anchor (R7) | capability |
| attention | `apply(SetFlag)` via outbox from the reconciler | capability |
| abandon | `apply(Close)` via outbox from `wf phase abandon` | capability |

### 3.4 Admission: claim first, then admit

Order: every ledger-side refusal check first (`_selected_stage`,
`_refuse_other_admission`, HEAD and policy checks, `bridge/admission.py:185-257`) →
tracker `Claim` → ledger `bridge_records` transition to ADMITTED under
`BEGIN IMMEDIATE`. The claim is issued last before the transaction so that ordinary
refusals never touch the tracker and `bd ready` is not churned; the tracker call still
precedes the transaction, so no I/O sits inside one. `Unknown` on the claim refuses
admission — ambiguity refuses; offline work is `NullTracker` or an explicit
`tracker_optional`.

The only failures left inside the window are a crash and a concurrent-admit race. Both
leave the same shape: a `bridge_records` row at PREPARED (a ledger row, written at
prepare) and a tracker item in progress by this actor. Detection is per task, not a
sweep: the next contractor invocation on that task, or `wf ledger reconcile <task>`,
sees PREPARED + claimed-by-us and enqueues the release. The port gains no `list`.

### 3.5 Derived closed — a latch, not a recomputation

`bridge_records` **is** exported, with state at most LANDED. Nothing writes CLOSED.
`tasks.export_oid` stays, as the **latch**: set once, never cleared, never exported.

```text
closed(task):
    if tasks.export_oid is set:            return True        # the latch
    if state != LANDED:                     return False
    oid = anchor_oid(task)                  # reverify's _anchor_oid, same precedence:
    if oid is None:                         return False      #   HEAD blob first, ref fallback
    if blob_hash(.wf/export/<task>.jsonl) != oid: return False
    tasks.export_oid = oid                  # derive once, latch
    return True
```

Why a latch: a live re-export is a function of mutable state — the header carries
`schema_version` (`ledger/export.py:135`) and `projections` is exported — so one
migration or one attention drain would flip every closed task back to open. Today's
`export_oid is None` is monotonic; `closed()` keeps that property and adds only the
rebuild path. The on-disk file, not a re-export, is hashed, exactly as
`reverify._pin_check` does; `closed()` and `wf ledger verify` share `_anchor_oid`, so a
stale committed blob that no longer matches the file is "not closed" to both, and the
orchestrator recommits.

Consumers that read `closed()` after S2, replacing four different predicates today:
terminal cleanup (`foreman/tick.py:754`), archive (`ledger/archive.py:75`),
`adapter.close`'s refusal (`bridge/adapter.py:234`), the succession guard
(`bridge/adapter.py:304`, today `state is CLOSED`, dead once nothing writes CLOSED),
and, after S4, sibling admission (`bridge/admission.py:252`, today the *bead's*
status).

`retired(task) = closed(task) ∨ state == ABANDONED`. Cleanup and archive read
`retired`; nothing else does. An abandoned task otherwise defers forever.

The tracker `Close` intent drains on the **ref** anchor — the same moment the bead
closes today. v1 drained on the committed anchor; that left every sibling stage refused
by `_refuse_other_admission` until the orchestrator committed. A fresh clone lags until
the export commit is pushed; accepted, and `wf ledger verify` names which anchor answered.

Both tests hold at once: a crash between export and pin leaves the task open to
succession, sibling admission, cleanup and archive; a ledger rebuilt in a fresh clone
from the committed file derives `closed()` on first ask, latches, and terminal cleanup
proceeds. Archive is **not** clone-portable and never was — it bundles `refs/wf/<root>/*`
(D19, `ledger/archive.py:94`), which a default clone does not fetch.

### 3.6 Export: facts about the task, never about the file or the machine

- `export_oid` and `exported_at` are elided from the exported `tasks` row (`_insert`
  already inserts only present columns, `ledger/export.py:542-544`). The column stays
  as the closed-latch (§3.5); `wf ledger pin-export <task>` recovers the crash between
  write and pin. `PhaseBridgeRecord.export_oid` is dropped **in S2**, not S1 — it is
  the sole input to D5's refusal at `bridge/adapter.py:234` until `closed()` exists.
- `landings` joins `EXPORT_TABLES` after `TASKS` so `_row`'s whitelist and `_clear`'s
  reverse order cover it; it has no `seq` (`bridge/journal.py:44-49`), so it cannot ride
  `ROW_TABLES`' `(seq, table)` emission and gets its own emission branch beside
  `_auxiliary_rows`, ordered `(attempt, phase)`. `bridge_records` (S4) is handled the
  same way.
- Header carries `repo_id` — a UUID written once to a committed `.wf/repo-id`, mirrored
  in `meta`. `wrapper_root` stays as a database-only check.
- A schema-derived test over **every** table in the schema, not only those reachable
  from `tasks` (S4's `claims` is keyed by target, not task): each is in
  `EXPORT_TABLES` or in an explicit `NON_EXPORTED` set with a stated reason
  (`meta`, `restore_pending`, `tracker_outbox`, `claims`, the four
  `DERIVED_ACTIVATION_TABLES`).
- Restore semantics unchanged: parse before the fence, one exclusive fence, one
  transaction, whole-state rebuild.

### 3.7 Identity

`task_id` is minted by the ledger at prepare; `tasks.tracker_ref` + `tracker_kind` hold
the foreign id, UNIQUE. Epic is an **input** at mint (registered slug or the tracker's
parent), written to `tasks.epic_id` directly; `epic_segment()` is deleted and
`RunIdentity.run_directory` reads the column. Today `ledger/tasks.py:52` and
`ledger/store.py:720` write `epic_id` *from* `epic_segment(task_id)`, so "read the
column" alone would read a parse.

Grammar: `SAFE_COMPONENT_PATTERN` and `foreman/identifiers.py:8` are one regex; it
must additionally reject `..` anywhere and a component ending in `.lock`. Verified:
both pass the regex today and `git check-ref-format` refuses both under
`refs/wf/exports/<task>`. The id reaches `refs/wf/<root>/…`, worktree paths, the
`docs/workstreams/<epic>/runs/<task>/a<n>` grant boundary and `WF_TASK_ID`, which
`verify-debrief.sh` re-expands as a POSIX glob — an identity bug there is a containment
bug.

**The epic string is under the same grammar.** Today `WF_EPIC_SEGMENT` is derived from
a `SafeComponent` id and so is constrained for free; as an input it is a second free
path component on the same containment boundary (`scripts/verify-debrief.sh:67`).
`RunIdentity` gains `epic_id: SafeComponent`, supplied at every construction site; the
lazy `LedgerStore._ensure_task` path (`ledger/store.py:713-724`, `INSERT OR IGNORE`
for runs that never ran a prepare) requires it on the carrier and refuses without it.

Attempt is an input carried on the root carrier from `run_identity`, never
`COUNT(roots)+1` (`ledger/store.py:735-738`). The count is today the **only** thing
keeping two roots of one task distinct — D16's decision and replacement roots inherit
`task_id` — so removing it needs the child format D8 named and `rowmap.py:94` never
built: attempt roots are `<task>-a<n>`; non-attempt roots under that attempt are
`<task>-a<n>-c<m>` with `m` minted per attempt and `parent_root_id` set. `create`'s
natural-key short-circuit (`ledger/store.py:270`) is checked against the new key so a
second root can neither collide nor silently resolve to the first.

### 3.8 Bridge lifecycle and the three verbs

The bridge closes on its own only when the graph reaches `shipped`. Otherwise it hands
back with the record ADMITTED and the orchestrator has three verbs — **continue**
(after signing a gate), **retry** (`--retry`, attempt+1), **abandon** (new
`wf phase abandon <task> --reason`, record → ABANDONED, outbox `Close`). An abandoned
task is `retired` (§3.5): cleanup and archive proceed on what exists; succession is
refused. There is no override that lands an unshipped task. A bead closed externally
mid-run surfaces as `Conflict` at the next tracker contact and the record is marked
ABANDONED_EXTERNAL — never guessed.

### 3.9 Ledger loss

The ledger is per-checkout working state. Closed tasks rebuild from the committed
export in any clone. In-flight tasks do **not** survive ledger deletion in this epic:
their rows exist only in the ledger until close; the evidence in `refs/wf/*` and the
wrapper home survives, recovery refuses the ownerless evidence, and the orchestrator
retries. A crash is not a delete — `BEGIN IMMEDIATE` per method leaves committed rows
intact. Checkpoint export per activation close is S7 (R10).

## 4. Decisions

| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| R1 | The ledger is the only record store; `StoreBackend` becomes `LedgerStore`'s own surface | keep the protocol with one implementation | a port with one implementation that no tracker can satisfy is ceremony |
| R2 | Tracker port: four operations, capability set, intent union, outbox; bridge-only | seven direct methods; a tracker call inside the close transaction | intents are idempotent by construction, which is what makes retry safe; invariant: no I/O in a store method |
| R3 | Claim in the tracker after every ledger-side refusal check and immediately before the ledger admit; `Unknown` refuses; the crash window is detected per task from the PREPARED row | drain after admit; claim only in the ledger; claim first of all; a tracker `list` sweep | `bd ready` must be exact for a second session; ordinary refusals must not churn it; ambiguity refuses; the port stays four operations |
| R4 | Bridge record, claims and the task-brief snapshot move to the ledger | record stays in bead metadata (D7) | admission must run with the tracker unreachable; `command.py:333` re-reads the brief today |
| R5 | Export elides the pin and drops the record's copy; `landings` exported; `repo_id` header; schema-derived completeness | `export_pins` table; keep `repo_hash`; hand-listed tables | no schema change for the pin; the record copy is the back door; path digest is not portable; the third hand-list is one table from a fourth defect |
| R6 | `closed()` is a latch: `export_oid` set, else derived once from the on-disk export against reverify's `_anchor_oid` and written; `bridge_records` exported with state ≤ LANDED; `retired = closed ∨ ABANDONED` for cleanup and archive; supersedes D9 | store CLOSED (either exported → violates D5, or not → lost on rebuild); recompute from a live re-export (v1: non-monotonic under a schema bump or a `projections` write) | the only rule under which crash-before-pin stays open, rebuild-in-clone reads closed, and a migration cannot reopen a closed task |
| R7 | Tracker `Close` drains on the ref anchor — the moment the bead closes today | drain on the committed anchor (v1) | sibling admission reads the bead's status (`admission.py:252`); draining on the commit refused every sibling until the orchestrator committed. A clone lags until push; accepted |
| R8 | Ids minted by the ledger with epic as an input under the same grammar; `epic_segment` deleted; `RunIdentity` carries `epic_id`; grammar tightened; child roots `<task>-a<n>-c<m>` | sanitise the tracker id and read `epic_id` (circular today); mint `<slug>.<n>` to keep the parse valid; attempt-from-carrier with no child format (v1: two roots of one task collide) | the column must be independent of the id; the epic is a path component too; two id forms git refuses pass the regex; the count was the only root-id uniqueness |
| R9 | Missing `BLOCKERS` records `blockers_checked=false` and proceeds; a per-tracker config flag turns it into a refusal | always refuse | an absent capability is not liveness ambiguity; the flag is recorded on the record either way so the trace shows which policy applied |
| R10 | In-flight tasks do not survive ledger deletion until S7; checkpoint export is the final slice, after the one export is right | checkpoint inside S1–S2 | a second kind of export in the same epic that redefines the first is how a third circularity is born |
| R11 | Claims stay ledger-local CAS | git-ref CAS | one ledger per repository (`foreman/config.py:23` refuses linked worktrees); a claim outliving the ledger is one nobody can see |
| R12 | Clean break with quiesce; no compatibility layer | dual id schemes, dual headers | no live ledger, no committed export exists; in-flight bead-metadata records are the only migration surface |
| R13 | Superseded run-ledger decisions, stated: **D6** — attention still drains before the driver exits, but through the outbox at driver exit rather than a direct label write per tick; **D9** — task closure is `closed()`, not a stored CLOSED; **D16** — every root is reachable from the ledger's `tasks` row; `tracker_ref` may be NULL under `NullTracker`, so "reachable from the tracker" becomes "reachable from the tracker when one is configured" | leave them implicit | a decision the roadmap undoes without saying so is the next reviewer's blocker |

## 5. Lifecycle of one task

```
prepare   tracker.get → snapshot → mint task_id (epic as input) → bridge_records PREPARED
admit     tracker.apply(Claim) → ledger ADMITTED (BEGIN IMMEDIATE) → root minted
run       foreman ticks; zero tracker calls; gates signed; attention via outbox
land      CAS fast-forward → LANDED → export (task facts only) → pin ref
closed    derived: LANDED ∧ anchor; cleanup/archive/successor proceed on either anchor
mirror    orchestrator commits .wf/export/<task>.jsonl → reconcile drains Close → bead closed
```

## 6. Slices

Loop as the engine bundle: implementer writes, Opus medium iterates to convergence
(≤3 rounds), independent critic signs off, canonical gate green after every slice.
Each slice lands on `wf/store-restructure`; the branch merges as one. Strictly
ordered — S0 first so every later slice is written in the new names, S2 needs S1's
anchor rules, S4 needs S3's minted ids, S6 deletes the seam, S7 last.

| Slice | Delivers | Acceptance |
|---|---|---|
| S0 rename | the four actors renamed to one story: phase bridge → **contractor**, foreman stays, supervisor → **inspector**, runner → **crew**. `git mv` of `bridge/` and `supervisor/`; identifiers, CLI subcommands (`phase-bridge` → `contract`, `supervise` → `inspect`), the `runner` config key and workflow TOMLs, `wf.supervise.*` log events, test names, `CONTEXT.md`, the guide, the diagrams, this roadmap. ADRs 0001–0005 **and** `docs/workstreams/run-ledger/roadmap.md` get one naming note each, not a rewrite — they record decisions in the vocabulary they were made in and cite `file:line` in it. Measured at `d20a728`: 361 files, ~3,300 occurrences. The bead-metadata key `phase_bridge` is renamed without a read shim: nothing is in flight and S4 retires the key | `grep -rniE "phase.?bridge\|supervisor\|\brunner\b" workflow_interpreter tests docs` returns only the naming notes and `CONTEXT.md`'s "formerly" line; canonical gate green; `wf contract --help` and `wf inspect --help` work; the diagrams render |
| S1 export integrity | `export_oid`/`exported_at` elided from the exported row; `PhaseBridgeRecord.export_oid` **kept** (D5's guard until S2); `wf ledger pin-export`; `landings` in `EXPORT_TABLES` with its own emission branch, `_assert_no_landings` deleted; `.wf/repo-id` header, `wrapper_root` database-only; completeness test over every schema table | export → close → re-export is byte-identical and hashes to the pinned blob; import succeeds in a fresh clone at a different path; a landed task round-trips and D17's fallback reads the restored row; the completeness test fails when any new table is added to neither set; `adapter.close` still refuses without the record oid; closes `cr-p7dg` and `cr-ho9m` |
| S2 derived closed | `closed()` and `retired()` in `ledger/` per §3.5 (latch on `export_oid`, on-disk hash against the shared `_anchor_oid`); consumers switched: `tick.py:754`, `archive.py:75`, `adapter.close` (`adapter.py:234`), the succession guard (`adapter.py:304`); `PhaseBridgeRecord.export_oid` dropped now; CLOSED removed from the producer side, kept read-compatible like LANDING; tracker `Close` on the ref anchor | crash injected between export and pin: succession refused, cleanup defers, archive refuses; a shipped task refuses `--retry`; ledger rebuilt from the committed file in a fresh clone: `wf ledger verify` passes and terminal cleanup proceeds (archive is not clone-portable, D19); a schema-version bump does not reopen a closed task; no producer writes CLOSED |
| S3 identity | ledger-minted `task_id`, `tracker_ref`/`tracker_kind`, epic as mint input under the same grammar, `RunIdentity.epic_id`, `_ensure_task` refuses without it, `epic_segment` deleted, grammar rejects `..` and `.lock`, attempt from the carrier, child roots `<task>-a<n>-c<m>` with `parent_root_id` | `PROJ-12` mints a task id that yields a valid refname, worktree path, run directory and `WF_*`; `a..b` and `foo.lock` as task or epic are refused by name before any ref is written; a decision root and a replacement root under attempt 1 mint `-a1-c1` and `-a1-c2`, and attempt 2's root is `-a2`; `grep epic_segment` empty |
| S4 bridge in the ledger | `bridge_records` (exported, own emission branch), `claims` (non-exported), brief snapshot; the five adapter transitions become ledger transactions with a version guard; `_refuse_other_admission` as a ledger query on `closed()`; `wf phase abandon` → ABANDONED, `retired`; `LedgerClaimUnsupported` gone | with `.beads/` deleted after prepare: admit, land, `wf ledger show`, archive succeed; two attempts on one target serialise on the ledger claim; abandon unblocks sibling admission and the abandoned task's worktree is cleaned; a retry admits from the snapshot without a tracker read |
| S5 tracker port | `tracker/` package: port, intents, `NullTracker`, `FileTracker`, `BdTracker`, `tracker_outbox` and drain (at driver exit, D6), claim placed per §3.4, PREPARED-plus-claimed detection, external-close detection, reconciler through `SetFlag`; one conformance suite | the same rig lands against null, file and bd; forced `Unknown` on `Close` leaves the landing intact and one pending row; `Unknown` on `Claim` refuses admit; a ledger refusal after the claim releases it; a crash after the claim is released on the next invocation; a bead closed mid-run marks the record ABANDONED_EXTERNAL; zero tracker calls inside any foreman tick and the outbox drained before the driver exits (counting tracker) |
| S6 cutover | quiesce check (no bead-metadata record at PREPARED/ADMITTED); delete the seam (§3.2); `costs` on the ledger only with a release note; guide 08 and 11 rewritten; ADR 0006 | `grep -rn BackendKind workflow_interpreter/` empty; `bdio/client.py` and `foreman/locator.py` gone; canonical gate green; a full prepare → admit → land → close → commit → reconcile cycle closes the bead exactly once |
| S7 checkpoint export | `cr-h498`, promoted from follow-up to final slice: an export at every activation close, pinned to a local ref and never committed, so a deleted ledger rebuilds to the last checkpoint and recovery resumes; `closed()` distinguishes a checkpoint anchor from a close anchor | delete `.wf/ledger.db` mid-run, rebuild, recovery resumes the in-flight root from the last activation close without a retry; a task with only checkpoint anchors is never `closed()`; canonical gate green |

Estimate, in AI execution plus review time: six and a half days across eight slices.
S0 is half a day, mechanical; S1 and S5 are the largest; S2 is the one that must not
be rushed; S7 is small once S2's anchor rule exists. How the epic is run — roles,
reports, the two Fable gates, close-out — is `orchestration.md`; live position is
`state.md`.

## 7. Risks and open questions

- **R6 is the highest-risk decision.** Everything durable keys off "closed". The
  evidence that retires it: crash-before-pin stays open to every consumer, a clone
  rebuild derives closed and latches, and a schema bump reopens nothing — all in S2.
- **R7 reversed in v2** (ref anchor, not committed): the v1 form refused every sibling
  stage until the orchestrator committed. If a global "closed only when in history"
  is ever wanted, it is a second intent after the export commit, not a change to R7.
- **Two repository identities.** `repo_hash` also names the wrapper home
  (`foreman/config.py:93-98`). A moved checkout keeps its exports and loses its wrapper
  home. Settle in S1 whether the wrapper root keys on `repo_id`; recommended yes.
- **`projections` in `EXPORT_TABLES`** exists for "whatever label bd last carried".
  With `NullTracker` there is no label. Left in; own slice if it changes.
- **Attempt drift is verified in mechanism, not in occurrence** — `rowmap.py` has no
  child format, so no ledger root today is anything but `<task>-a<n>`. S3 fixes the
  mechanism regardless.
- **The numbered invariants in the design brief were the brief's own**, distilled from
  ADR 0005 and the guide; they are not a repo list. Where a decision leans on one, the
  reason column says why in its own words.
