# Run ledger — design and plan

Status: DRAFT v6 (build-ready for S0–S2; S3–S4 re-checked by slice critics on §3.2, §3.6, §3.7). Review log: Astra medium rounds 1–3 (REJECT ×3: export
timing vs signed landing; missing bridge writers; child/task terminal
conflation; lossy schema; projection atomicity; destructive attention flag;
mid-run rollback; split claim authority; unexecutable debrief edge;
unjournaled attention input). Sol high round 1 on v4 (REJECT: no backend
locator; per-root reconcile lock; debrief not executable; task closes before
export; bd cannot mint ids; export fencing; cross-wrapper fence; D7/D20
contradiction). Sol high round 2 on v5 (REJECT: backend persisted too late; render had no input carrier; runner could replace the fence inode; export not in git before close; verify identity from an opaque id). v6 applies those five fixes without a further round, by the owner's decision.
Owner: workflow-interpreter engine.
Spec touched: `docs/specs/workflow-interpreter.md` §3.1–§3.4 (carriers),
§5.1 (lifecycle), §5.4 (worktrees), §9 (signing), §10.4 (rebudget), §11
(recovery). Recorded decisions this plan must not undo: ADR 0001, 0002,
0004. ADR 0003's argv ceiling applies to the bd path only; the ADR this plan
adds (S4) says so.

## 1. Problem

The engine stores every workflow fact as a bead: one root bead per run, one
bead per activation, gate and wake event, all in the repository's beads
database. Three costs follow.

1. The beads tracker becomes a ledger of everything. 233 of the 616 beads in
   this repository are engine-written `wf …` beads that nobody reads through
   `bd`. They carry no label and no parent, so `bd list` cannot hide them.
2. Every foreman tick shells out to `bd` five times, about 1.5 s per tick on
   an idle host with a grown database. That is the direct cause of the flaky
   admission budget (`cr-xu34`) and of the 30 s wall in the admission test.
3. The knowledge a run produces — reviewer findings, failed verify output,
   outcomes, gate signatures — is written to the per-run wrapper directory
   and never read again. Nothing tracked in git records why a change was
   made the way it was.

## 2. Terms

| Term | Meaning |
|---|---|
| task bead | The bd issue the orchestrator created for a stage of work, e.g. `cr-0km.2`. Yours. Carries the bridge's `phase-bridge` record today and keeps it. |
| epic segment | The parent prefix of a dotted bead id (`cr-0km` for `cr-0km.2`); for an undotted task id, the task id itself. Deterministic, no bd lookup. |
| run | One attempt at one task bead through one graph. Bridge instance key: `phase-bridge:{epic}:{stage}:attempt:{n}` (`bridge/models.py:14`). |
| root | The record that owns a run or a composition child. Today a bead; after this plan a ledger row with its own terminal state and an immutable backend. |
| backend | `bd` or `ledger`, pinned per root at creation, recorded in the bridge record (`root_backend`) so the store can be chosen before the root is loaded. |
| root id | On the ledger backend `<task>-a<n>` for an attempt, `<task>-a<n>-c<m>` for a child. On the bd backend bd-minted, as today (`BdClient._create_bead` accepts bd's generated id, `bdio/client.py:404`). Both are single path-safe components (`foreman/identifiers.py:8`). |
| attach identity | The full comparison set in `bdio/roots.py:463` — graph content hash, instance inputs, `allow_test_flags`, instance base commit, config signature. Unchanged. |
| activation id | Ledger backend: `<root_id>.<node>.r<round>.<seq>`; `node`, `round_no`, `seq` also stored as columns. Uniqueness on `idempotency_key`. bd backend: bd-minted. |
| ledger | One SQLite-format database per repository holding every engine fact. |
| export | One JSONL file per task bead, git-tracked, from which that task's rows rebuild. Written by the bridge before it closes the task, and by `wf ledger export` on demand. |
| projection | A bd label write derived from ledger state, enqueued in the same transaction as the state change and reconciled per task under a task-keyed lock until read back. |
| attention label | `wf:attention` on the task bead, present iff any non-terminal ledger root of the task has an open gate. Never `bd human`, whose dismiss closes the issue. |
| fence | `<git common dir>/wf/ledger.lock`, a repository-stable `flock` shared by every ledger writer and taken exclusively by import, migration and restore. |
| wrapper root | `<wrapper_home>/<sha256(repo_root)[:16]>/`, the engine's per-repository folder outside the repo. Unchanged. |

## 3. Architecture

```text
BEADS (tracker, git-mirrored)              LEDGER (engine facts)                    FOLDERS / GIT (bulk, per machine)
epic  cr-0km                               <repo>/.wf/ledger.db  (gitignored)       <git common dir>/wf/ledger.lock   the fence
└─ task cr-0km.2                             tasks, roots, activations, gates        <wrapper_root>/cr-0km.2-a1/
   phase-bridge record (+ root_backend)      events, sessions, findings, artifacts     worktree/       deleted at terminal
   label wf:attention (projection)           usage, landings, signatures, projections  <activation>/   receipt, run.jsonl, channels/
   closed only by bridge CLOSED,           <repo>/.wf/export/cr-0km.2.jsonl (tracked)  refs/wf/<root>/artifact/…  (in git)
   after the export OID is recorded
```

### 3.1 The seam, honestly

`WorkflowStore` (`bdio/api.py`) and `WorkflowReads` (`bdio/reads.py`) are the
right seam, but bd leaks above it and the leaks are fixed first (S0):

| Leak | Where | Fix |
|---|---|---|
| `RootRecord.bead`, `ActivationRecord.bead`, `GateRecord.bead` are `BeadRecord` | `bdio/records.py:58–116` | records carry `id`, `status`, `metadata`; `bead` removed |
| raw `BeadRecord` tuples from `instance_beads`, consumed by the frontier | `bdio/reads.py:92`, `foreman/frontier.py:94–152` | typed `InstanceRecord` union; frontier reads discriminators from it |
| `.bead.status` reads | `foreman/children.py:187` | `.status` on the neutral record |
| claim beads read and written outside the seam | `bridge/integration.py:219–240` | `store.claims` on the seam, bd-backed until the bd backend is removed (D20) |
| adapter root lookups go to bd directly (`find_roots`) | `bridge/adapter.py:135–146` | `reads.roots_by_instance_key` on the injected store |
| `Composition` owns one process-wide store and loads the root through it | `foreman/compose.py:140–160` | store built per root from the backend locator (§3.2) before `load_root` |
| `WorkflowStore.__init__` and `for_root` construct `BdClient` | `bdio/api.py:127–181` | backend injected through a `StoreBackend` protocol and factory; `ForemanLab.rebuild` accepts the factory |
| bd errors escape upward | `supervisor/run.py:387` | backend-neutral `StoreError` hierarchy |

After S0 the ~230 call sites use the neutral names. The count that changes
in S0 is measured by the S0 implementer and recorded in its bead.

### 3.2 What stays in bd, and how it is kept consistent

Two kinds of bd write remain, and they are deliberately different.

**Authoritative, direct, unchanged.** The bridge's own state machine on the
task bead: `PhaseAdapter` prepare / admit / gate_red / land / close
(`bridge/adapter.py:146–218`). These run synchronously inside bridge
commands with readback, exactly as today, and are exempt from projections.
Task closure happens only here, on CLOSED, and only after the export OID
is recorded (§3.6). The bridge record gains one immutable field,
`root_backend`, written at **prepare**, before admission creates any root
or branch (`bridge/admission.py:188–197` creates the root before `admit`
persists, so admit-time is too late); a non-bridge run passes `--task` and
`--store` and the ledger `tasks` row is the locator. Resolution order:
bridge record → ledger `tasks` row → refuse. Children and replacement roots
inherit their owner's backend.

**Derived, projected, reconciled.** One label, `wf:attention`, whose desired
state is a pure function of the ledger: present iff any non-terminal ledger
root of the task has a gate in state OPEN. bd-backed roots keep today's
behaviour (no label) during coexistence.

1. Every operation that can change the predicate inserts a `projections`
   row (`task_id, generation, created_at, acked_at NULL`) in the **same**
   `BEGIN IMMEDIATE` transaction: gate open, gate close, root settlement
   (`foreman/tick.py:710`), root supersede, import. `generation` is
   assigned from `tasks.next_seq` in that transaction, so it is unique and
   ordered per task.
2. Reconciliation is serialised by a **task-keyed** lock,
   `<wrapper_root>/tasks/<task_id>.lock`, distinct from the root-keyed
   member locks in `bdio/coordination.py:397`. Under that lock the
   reconciler recomputes the desired label from the ledger now, writes
   `bd update <task> --add-label|--remove-label wf:attention`, reads the
   bead back, and only then acks every row with `generation ≤` the one it
   reconciled. Two roots of one task cannot interleave recompute and write.
3. `BdClient` gains label arguments on `UPDATE`; that is the one addition to
   its closed subcommand set (`bdio/client.py:81`), recorded as a design
   change.
4. A crash anywhere leaves unacked rows; the next driver tick or
   `wf ledger reconcile` drains them. The driver drains its task before
   exiting after final settlement. Replay is idempotent because the write
   is "set label to desired state".

### 3.3 Ledger schema

Lossless by construction: every current carrier model (`RootMetadata`,
`ActivationMetadata`, `GateMetadata`, `EventMetadata`, the bridge records,
`LandingIntent`, `LandingReceipt`) is stored whole as `metadata_json`. Indexed
columns are projections of that JSON for queries and constraints; they never
replace it. Every row carries `task_id` and a per-task `seq` from
`tasks.next_seq`, assigned in the writing transaction, which gives the export
a durable order.

```text
meta         schema_version, repo_hash, wrapper_root, created_at
tasks        task_id PK, epic_id, graph_id, backend, next_seq, export_oid, exported_at, created_at
roots        root_id PK, task_id, seq, parent_root_id, attempt, backend, instance_key UNIQUE, graph_content_hash,
             instance_inputs_json, allow_test_flags, instance_base_commit, config_signature,
             coordination_json, terminal, terminal_at, metadata_json
activations  activation_id PK, task_id, seq, root_id, node, round_no, act_seq, idempotency_key UNIQUE, lifecycle, version, metadata_json
gates        gate_id PK, task_id, seq, root_id, gate_key, state, outcome, nonce, verified_fingerprint,
             bound_key, bound_value, artifact_ref, artifact_oid, version, metadata_json,  UNIQUE(root_id, gate_key)
nonces       nonce PK, gate_id, consumed_at                                   # consumed inside the gate-close transaction
signatures   gate_id PK, payload_bytes, signature_bytes, signer_fingerprint,
             allowed_signers_entry, policy_json                               # the historical trust, not just the bytes (§3.6)
events       event_id PK, task_id, seq, root_id, activation_id, kind, event_key, payload_json, at,  UNIQUE(root_id, event_key)
sessions     activation_id PK, backend, thread_id, registered_at, completed_at
findings     activation_id, round_no, severity, text
artifacts    activation_id, kind, git_ref, oid, path_in_ref, sha256           # ref name AND immutable object id
usage        activation_id PK, tokens_in, tokens_out, cost_json
landings     task_id, attempt, phase (intent|receipt), record_json, written_at,  UNIQUE(task_id, attempt, phase)
projections  task_id, generation, created_at, acked_at,  UNIQUE(task_id, generation)
```

Atomic operations, each one transaction: mint (insert activation, check
idempotency); lifecycle transition (read, check allowed, write `version+1`);
gate close (signature verified outside, then consume nonce + set state +
write outcome + insert signature + enqueue projection); rebudget (gate close
+ bound mutation; `bounds.effective_bound` still reads config ⊕ closed
rebudget gates); settlement (terminal + enqueue projection).

### 3.4 Concurrency contract

Writers, all of them: the foreman driver (tick, gates, close, monitor,
events, reconciler), resident supervisors (dispatch, exit, evidence via
`transitions.py`), RPC session control (`supervisor/rpc_session.py`), the
bridge (admission, landings, export-before-close), the
export/import/archive CLI. `costs` is read-only.

1. One connection per process: `journal_mode=WAL`, `busy_timeout=5000`,
   `synchronous=NORMAL`.
2. A store method is one transaction. No subprocess, no file I/O, no bd call
   inside a transaction.
3. Lock order: execution locks first (root-keyed member locks, task-keyed
   reconcile lock), then the ledger transaction. The file locks stay; they
   bound execution, not storage.
4. Fence: every process that opens the database — every writer above, and
   export — holds a shared `flock` on `<git common dir>/wf/ledger.lock`
   for the life of its connection. Import, migration and restore take it
   exclusive with a bounded wait, then refuse with the holders' pids. The
   common dir is shared by every worktree of the repository and is outside
   `git clean`'s reach, so two wrapper homes over one repository contend on
   the same fence; that closes the gap `band_lock` documents for itself
   (`supervisor/paths.py:237`). `owner.json` carries only `repo_root` and is
   not a liveness source. In-repo runner sandboxes mount `.git` writable as
   a whole (`supervisor/sandbox.py:458`), so a runner could unlink the
   locked inode; the foreman creates `<common dir>/wf/` before any dispatch
   and every runner sandbox pins it read-only, in the read-only pass that
   already runs last (`sandbox.py:667`). S1 tests inode replacement from
   inside a runner for both checkout shapes.
5. Export runs under one read transaction while holding the shared fence,
   so it cannot publish a snapshot from before an exclusive restore.
6. Busy beyond the timeout is a recorded refusal on the activation, never a
   silent retry loop.

Turso's MVCC is not needed and not relied on. Driver: stdlib `sqlite3` now,
`pyturso` (same file format, same API shape) behind a spike bead after 1.0.

### 3.5 Repository identity and deletion

`meta.wrapper_root` is pinned at creation. A foreman whose `wrapper_root`
differs refuses to start, always, not only while roots are live; the
message names the pinned root. Creation itself runs under the exclusive
fence, so two first starts cannot both create. The config loader resolves
`repo_root` through `git rev-parse --git-common-dir` and refuses a worktree
path.

The database lives in the working tree's ignored `.wf/`, where `git clean
-fdx` can delete it. Accepted, with these guarantees: every task is exported
and digested before it can be closed (§3.6); restore takes the exclusive
fence and checks `meta.repo_hash` and `meta.wrapper_root` in the export
header; a deleted live database makes every live driver refuse at its next
tick with a named reason; candidate branches and `refs/wf/…` pins survive in
git.

### 3.6 Export and recovery

- **Export before close, into git.** The bridge `close` command, before it
  merges the CLOSED record, runs the export for the task under the shared
  fence, writes `<repo>/.wf/export/<task>.jsonl`, stores the same bytes as
  a git blob pinned under `refs/wf/exports/<task>` (the mechanism artifacts
  already use, `supervisor/artifact.py:29`), records that OID in
  `tasks.export_oid` and in the bridge record (`export_oid`), and only then
  closes the bead (`bridge/adapter.py:213` closes immediately after the
  metadata merge, so the OID must be in that merge). The export therefore
  survives a deleted `.wf/` before the orchestrator has committed the file.
  Terminal cleanup (§3.9) and archive are eligible only for tasks whose
  `export_oid` is set. A crash after the blob is written but before the OID
  is recorded re-runs the export at the next `close`; the file is
  overwritten, never appended.
- **Dirty main checkout.** The export file appears in the main checkout,
  exactly as `.beads/issues.jsonl` does after a bd write. The orchestrator
  commits both together.
- **`wf ledger export`** writes the same file on demand for any task,
  including refused and abandoned attempts.
- **`wf ledger import`** rebuilds from `export/*.jsonl` under the exclusive
  fence. Rows are ordered by `(task_id, seq)`; round trip is byte-identical
  (tested). The attention drain every restored task owes (§3.2) is recorded in
  a non-exported `restore_pending` table, never as a `projections` row, so the
  round trip keeps that byte identity; the reconciler drains such a row exactly
  as it drains an unacked generation.
- **Landing journal.** The bridge writes the intent file, then the
  `landings` row, before the CAS; the receipt file, then its row, after.
  Recovery reads the file first, falls back to the row if the file is
  missing, and refuses if both are missing. `UNIQUE(task_id, attempt,
  phase)` makes the fallback unambiguous. The task bead keeps only
  `landing_receipt_digest` (`bridge/models.py:76`).
- **Re-verifiable approvals.** `GateMetadata` stores fingerprint, nonce and
  payload digest (`bdio/wire.py:470–494`), and verification depends on the
  allow-list of the moment (`bdio/signing.py:464–490`). The gate-close
  transaction therefore stores, in `signatures`, the payload bytes, the
  signature bytes, the signer fingerprint, the exact `allowed_signers`
  entry (public key, principal, options) that matched, and the policy in
  force. `wf ledger verify <task>` re-verifies every approval of a task
  from the export alone, against that historical entry.

### 3.7 Debrief: an executable graph contract

The debrief becomes a task node between `implement` and `review`, so the
reviewer verifies it and the ship gate binds an artifact that already
contains it, with no change to gate binding (`foreman/gates.py:93` binds the
source's verified artifact as today).

```text
implement --done--> debrief --done-----> review --accept--> ship
                    debrief --no_diff--> review              # nothing to say; not a failure
                    debrief --fail_code-> triage             # verify red: a human decides
                    debrief --fail_plan-> triage
```

- **Outcomes** come from the closed vocabulary in `schema/models.py:93`.
  A red verifier on `done` grades as `fail_code`
  (`supervisor/exit_grade.py:254`); it routes to `triage`, never to `ship`.
  Round cap 1; the graph's node fallback stays `triage`.
- **Grant.** Grants are literal `task.allowed_paths` from the pinned node
  (`foreman/supervise.py:203`) and must match the grant regex, which
  forbids placeholders (`schema/graph_schema.json:63`). The node therefore
  declares the static, regex-valid grant `docs/workstreams/**`. Containment
  to one attempt directory is enforced by verification, not by the grant
  (ADR 0001: grants are disclosure, not containment).
- **Verify.** `scripts/verify-debrief.sh` runs in the verify tree with
  `WF_BASE_COMMIT` (`supervisor/verify.py:417`) and three new variables S4
  adds beside it, pinned from the root record, never parsed from an id:
  `WF_EPIC_SEGMENT`, `WF_TASK_ID`, `WF_ATTEMPT`. It computes the only
  permitted directory `docs/workstreams/$WF_EPIC_SEGMENT/runs/$WF_TASK_ID/a$WF_ATTEMPT/`
  and fails if `git diff --name-only $WF_BASE_COMMIT HEAD` touches anything
  else, if the three files are missing, if `findings.md` or `evidence.json`
  differ from the render input, or if `debrief.md` exceeds the size bound.
  `review`'s verify set is a strict superset and includes this script, so a
  reviewer also grades it.
- **Inputs.** The render is an **engine producer** input, `ledger_render`,
  declared in the graph schema beside the existing engine producers and
  bound through the causal routing seam exactly as `verify_failure` is
  (`foreman/inputs.py:81` skips engine producers for node binding on
  purpose). It carries findings and evidence for all rounds so far. The
  task brief is a normal input; instructions inline per ADR 0002. The final
  `accept` verdict is not in `findings.md` (it does not exist yet); it is in
  the export and on the bead.
- **Cost.** One debrief activation per implement round. The role binds a
  small model at low effort; usage is recorded like any node.

```text
docs/workstreams/<epic segment>/
  roadmap.md, plans/, state.md         # what the execution skill writes today, unchanged
  runs/<task-id>/a<n>/
    debrief.md                         # LLM-written: what happened, why, what was learned
    findings.md                        # rendered from the ledger, rounds so far
    evidence.json                      # gate signatures so far, verify results, artifact ref + oid
```

### 3.8 Attempt outcomes keep today's paths

| Path | Today | Under the ledger |
|---|---|---|
| human abandons at the ship gate (`outcomes = ["approve", "abandon"]`, `feature-delivery.toml:126`) | `abandon` edge to the `abandoned` terminal; no bridge state change; a fresh attempt is admitted through the normal path | same; gate row outcome `abandon`; root terminal `abandoned` |
| signed, then repository verification fails in landing | `GATE_RED` (`bridge/landing.py:257`); retry needs an approved ship gate and `shipped` terminal (`bridge/retry.py:43`) | same |
| shipped root whose landing has not completed | not retry-eligible: `LANDING_RECOVERABLE` (`bridge/retry.py:55`); landing recovery runs instead | same |
| target moved before landing | `BRANCH_MOVED`; recovery or a new attempt re-admitted against the current base (a preserved stale base is refused, `bridge/admission.py:188`) | same |

Root settlement (`settle_root`) happens before landing as today
(`bridge/command.py:410`). The task bead stays open or in progress through
all of these; admission's open/in-progress check (`bridge/admission.py:199`)
is necessary, and `retry.py` decides eligibility as today.

### 3.9 Retention

Measured on three run folders from September rigs: 2.9 GB, over 99 % of it
`channels/scratch`. The record per activation is under 1 MB.

- Scratch, worktree and verify tree are deleted in the same terminal cleanup
  that removes the worktree today (`foreman/tick.py:718–737`), after
  findings, outcome and evidence are in the ledger, under the existing
  disposal guards (`supervisor/toolchain_cleanup.py:45–88`: proven process
  death, pinned artifacts, clean tree). Idempotent, retried at the next tick.
  For a bridge task, cleanup additionally waits for `export_oid`.
- `wf archive <task>` requires a closed task with `export_oid` set. It
  writes a git bundle of `refs/wf/<root>/*` for every root of the task to a
  user-chosen path outside the repo, verifies the bundle, and only then
  deletes the run folders and the refs. Without a verified bundle it
  refuses. Pins of rejected or unreachable artifacts
  (`supervisor/artifact.py:29`) are therefore never lost silently.
- The gate signing key and allow-list move out of the wrapper home to a
  config-specified path (`make-foreman-config.sh` default under
  `$XDG_CONFIG_HOME/wf/signers`).

## 4. Decisions

| # | Decision | Rejected alternative | Why |
|---|---|---|---|
| D1 | Split the run ledger out of beads | keep everything in bd | bd is a tracker for humans; engine facts drown it and cost 1.5 s per tick |
| D2 | One database per repository | one file per run or task | writes are tiny and serialised; one DB gives cross-run queries and one schema |
| D3 | Tables per entity type, whole carrier in `metadata_json` plus indexed projections, per-task `seq` on every row | table per task; hand-mapped columns; "insertion order" (v4) | no dynamic DDL; lossless; a durable order the export can reproduce |
| D4 | Database at `<repo>/.wf/ledger.db`, gitignored; fence at `<git common dir>/wf/ledger.lock` | fence under the wrapper root (v3–v4) | the common dir is shared by every worktree and wrapper home over one repository, and `git clean` cannot reach it |
| D5 | One export file per task; written by the bridge before close and by `wf ledger export` on demand | one appended JSONL; export on the candidate branch (v1); orchestrator-only export after close (v4) | a task must never be closable before its record is durable |
| D6 | Attention projection enqueued in every predicate-changing transaction, reconciled under a task-keyed lock, drained before the driver exits | enqueue after commit (v2); gate changes only (v3); root-keyed member lock (v4) | no crash window; settlement changes the OR; two roots of one task cannot race |
| D7 | bd keeps the `phase-bridge` record (direct, authoritative, plus `root_backend`) and one label; claims stay bd-backed behind the seam until the bd backend is removed | zero bd writes; `bd human` flag (v2); "claims move to the ledger" (v3–v4) | the bridge record is the human-facing state machine and now the backend locator; `bd human dismiss` closes the issue |
| D8 | Deterministic ids `<task>-a<n>` and `<root>.<node>.r<n>.<seq>` on the ledger backend only; bd roots keep bd-minted ids | deterministic ids on both backends (v4) | `BdClient` has no explicit-id path (`bdio/client.py:404`) and adding one is out of scope |
| D9 | Roots have their own terminal; task closure only through bridge CLOSED; attention is the OR over open gates of the task's ledger roots | children repeat the task terminal (v1) | a child never closes a running parent or hides another child's gate |
| D10 | Artifacts store `refs/wf/<root>/artifact/…` and the object id | bare commit hashes; worktree paths | refs retain objects; oids survive ref deletion in the export |
| D11 | Findings and outcomes copied into the ledger as text | pointers to channel files | small; the channel folder is disposable |
| D12 | Debrief is a task node between `implement` and `review`; static grant `docs/workstreams/**`; containment by `verify-debrief.sh` using `WF_BASE_COMMIT` and `WF_ROOT_ID`; `fail_code`/`fail_plan` route to `triage` | debrief between `review` and `ship` with a `fail` edge and placeholder grants (v3–v4) | must be executable with today's outcome enum, grant regex, pinned-node grants and gate binding; the reviewer grades it; a broken debrief cannot be what gets signed because it never reaches `ship` |
| D13 | stdlib `sqlite3` first, `pyturso` behind a spike bead | adopt Turso now | pre-1.0, experimental MVCC, nothing here needs it |
| D14 | Scratch deleted in terminal cleanup under existing guards, and for bridge tasks only after `export_oid`; archive manual | delete on activation close; automatic pruning | reuse proven liveness guards; nothing destructive before the record is durable |
| D15 | Signing key leaves the wrapper home | keep under `~/.wf/signers` | a wrapper-home wipe must not destroy the gate key |
| D16 | `--task <bead-id>` required; decision and replacement roots inherit `task_id` and backend | anonymous runs | every root reachable from the tracker |
| D17 | Landing intent and receipt copied into the ledger, `UNIQUE(task_id, attempt, phase)`, file-then-row order and fallback | wrapper files only | wrapper deletion must not erase what recovery revalidates; fallback must be unambiguous |
| D18 | Backend pinned per root, recorded as `root_backend` on the bridge record at prepare, before any root exists; resolved before the store is built; children inherit; the `store` switch applies to new attempt roots only; no reverse migration | mid-run rollback (v2); per-root pin without a locator (v3–v4); locator written at admit (v5) | a ledger root must be loadable after the switch flips back (`foreman/compose.py:140`); admission creates the root before admit persists (`bridge/admission.py:188`) |
| D19 | Archive deletes refs only after a verified git bundle | delete refs on export (v2) | JSON does not preserve git objects |
| D20 | Integration target claims stay in bd behind the seam while `store` can still select bd; move to the ledger only when the bd backend is removed | move claims at cutover (v3) | two backends discovering claims in two stores cannot see each other's reservations (`bridge/integration.py:219`) |
| D21 | `signatures` stores the historical allow-list entry and policy with the bytes; `wf ledger verify` re-verifies from the export alone | bytes only (v4) | verification depends on the allow-list of the moment (`bdio/signing.py:464`) |

## 5. Lifecycle of one attempt

```text
step  who          does                                                        where
1     orchestrator creates epic and task beads                                 beads
2     bridge       prepare: phase-bridge record PREPARED + root_backend        beads (adapter, direct)
3     foreman      tasks row (backend) or attach; roots row <task>-a1          ledger
4     bridge       admit: phase-bridge ADMITTED with root id                   beads (adapter, direct)
5     supervisor   <task>-a1/worktree/, branch wf/<task>-a1/candidate          wrapper root
6     foreman      activation implement-r1 minted                              ledger
7     supervisor   receipt, run.jsonl, channels/; dispatch, exit, evidence     wrapper root, ledger
8     foreman      findings, artifacts (ref + oid), usage rows                 ledger
9     foreman      debrief-r1: render placed as input; node writes runs/<task>/a1/; verify-debrief   ledger, candidate branch
10    foreman      review-r1 (verify superset incl. verify-debrief) … rework rounds repeat 6–10   ledger
11    foreman      ship gate OPEN + projection row, same transaction           ledger
12    reconciler   task lock; label wf:attention added; readback; ack          beads
13    human        signs the gate
14    foreman      gate CLOSED + nonce + signature row + outcome + projection  ledger
15    reconciler   task lock; label removed; readback; ack                     beads
16    bridge       settle root (terminal + projection); intent file + row; CAS; receipt file + row   ledger, wrapper root
17    bridge       land: phase-bridge LANDED                                   beads (adapter, direct)
18    bridge       close: export under shared fence → blob pinned at refs/wf/exports/<task> → export_oid in ledger and bridge record → CLOSED, bead closed   ledger, git, beads
19    foreman      terminal cleanup under guards (needs export_digest)         wrapper root
20    orchestrator commits .wf/export/<task>.jsonl with the beads mirror       repo
21    human        wf archive <task>, later, after a verified bundle           wrapper root, refs
```

A composition child runs 3–16 and 19 with `-c<m>`, inherits the backend,
sets only its own root terminal, and never touches 17–18. Outcomes other
than a clean landing follow §3.8.

## 6. Slices

Loop as the engine bundle: implementer writes, Opus medium iterates to
convergence (≤3 rounds), independent critic signs off, seven host gates green
after every slice. Each slice lands on `wf/run-ledger`; the branch merges as
one.

| Slice | Delivers | Acceptance |
|---|---|---|
| S0 compatibility | backend-neutral records, errors, `StoreBackend` protocol and factory; per-root store construction in `Composition` from a locator; `ForemanLab.rebuild` takes the factory; frontier, children, adapter root lookups and claims behind the seam; a store-contract suite parameterised by backend factory with **logical** fault points (`after-state-commit`, `before-readback`); real-bd tests kept; leak inventory recorded | seven gates green with bd the only backend; contract suite passes on real bd and on the fake transport |
| S1 ledger reads | schema with per-task `seq` and the unique keys above; migrations; `LedgerStore` reads; fence at the git common dir with `<common dir>/wf/` created by the foreman and pinned read-only in runner sandboxes; export/import CLI ordered by `(task_id, seq)`; round-trip test | contract reads pass on ledger; export→import byte-identical; import refuses while a shared fence holder exists; a runner in both checkout shapes cannot replace the lock inode |
| S2 ledger writes | full write surface; atomic mint / transition / gate-close+nonce+signature+projection / rebudget / settlement; task-keyed reconciler with label ops on `BdClient`; ledger-specific tests: reopen, multiprocess children, supervisor + steer, crash at each logical fault point, busy timeout, fence contention, two roots of one task racing the reconciler | contract suite passes on both backends; every fault point has a test that proves reconciliation; the two-root race test proves no lost update |
| S3 cutover | `store` switch pinned per attempt root, `root_backend` on the bridge record, inheritance; foreman, supervisor, bridge, costs on the ledger; `--task` required; ledger ids; landings and signatures copy; wrapper_root pin and refusal; worktree refusal in config; signers path; export-before-close in the bridge; bd corpus reduced to adapter + claims + label reconciler | admission test has no wall problem; a rig lands a task end to end on each switch value; a ledger-backed root is resumed after the switch is set back to bd; a bd root and a ledger root contending for one integration target are serialised by the shared bd claim; a task cannot reach CLOSED without `export_oid` |
| S4 knowledge | debrief node in `feature-delivery.toml` with static grant, `verify-debrief.sh`, `WF_EPIC_SEGMENT` / `WF_TASK_ID` / `WF_ATTEMPT` in verify env, `ledger_render` engine producer; `wf ledger verify`; terminal cleanup gated on `export_oid`; `wf archive` with bundle; ADR 0005; spec §3.1–3.4, 5.1, 5.4, 9, 10.4, 11 | rig run lands code + debrief in one fast-forward; a debrief that writes outside its directory or fails its render check reaches `triage`, never `ship`; a human-abandoned attempt leaves `a1/` on its ref and `a2/` lands; `wf ledger verify` re-verifies a task from the committed export in a fresh clone after `ledger.db` and the wrapper root are deleted; archive refuses without a verified bundle |

Estimate, in AI execution plus review time: four days across five slices.
S0 and S2 are the largest.

## 7. Risks and open questions

1. S0 is a wide mechanical refactor with no behaviour change; the leak
   inventory it records is the first fact of this workstream.
2. Serial landing is inherent: two attempts or two tasks cannot both
   fast-forward from one admitted base. Unchanged policy.
3. Cross-machine visibility is lost until Turso Cloud sync or an
   equivalent. Accepted; the tracked export is readable on every clone.
4. `busy_timeout` refusals under heavy child concurrency are a new failure
   mode; S2's concurrency tests set the ceiling.
5. The debrief adds one small-model activation per implement round. If it
   proves noisy, a graph-level `debrief_every = last` option is the fallback;
   not designed here.
6. `docs/workstreams/**` as a static grant is wider than one attempt
   directory. Containment is by verification, consistent with ADR 0001, and
   the attribution record still discloses every changed path.
