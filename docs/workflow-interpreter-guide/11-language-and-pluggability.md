# 11 — Language and pluggability: three independent recommendations

Dated 2026-09-18. Three models were given one identical brief — rebuild language
choice, crash-recovery implications, distribution, and how to make the issue tracker
pluggable — with no visibility into each other's answers. Full texts are in the session
scratchpad; this is the consolidation.

Participants: **Opus 5** (high), **Sol 5.6** (high, via Codex), **Fable 5.1** (high).

## The tally

| Agent | Greenfield choice | Rewrite now? | Confidence |
|---|---|---|---|
| Opus 5 | Python (stay); Go "defensible" | No | 85% no-rewrite; 60% Python-over-Go greenfield |
| Sol 5.6 | **Go** | No | 85% Go; 90% that overhead alone does not justify a rewrite |
| Fable 5.1 | **Go** | No — until concurrency forces it | 80% Go; 55% that a rebuild should happen at all |

**2–1 for Go on a greenfield build. 3–0 against rewriting now.** Rust was ranked second
or third by all three and chosen by none: the hard parts are OS and protocol semantics
no type system can prove, and borrow-checker friction slows LLM-assisted iteration
without buying correctness where it is at risk.

## Unanimous: the resource worry is misplaced

Sol measured it on this machine rather than estimating:

- **49 MiB** max RSS importing the foreman, store and recovery modules
- **0.32 s** cold `foreman --help`
- **0.25 CPU-seconds** before the process sleeps

Against a foreman that sleeps 30 s per tick and a `claude` process using 200–500 MB,
CPython is roughly 10–20% of one activation's footprint — and that share *falls* as
concurrency grows, because agents scale and the foreman does not. The GIL is
irrelevant: the engine waits on processes, files, locks and SQLite; it never computes.
Subprocess spawn uses `posix_spawn`/`vfork`, so spawning from a 60 MB parent costs well
under a millisecond.

Sol's summary: the measured cost was never Python dispatch, it was **1.5 s per tick in
five `bd` round trips** — a protocol problem, which the ledger correctly attacked.

## The real finding: the store seam is the wrong seam

All three reached this independently, in near-identical terms.

`StoreBackend` is a **record-store port shaped like bd**, being asked to double as
tracker portability. Sol: *"a workflow database interface disguised as tracker
portability."* Fable: beads fills two roles today, generic row store *and* human work
tracker. The evidence each cited: bd cannot evaluate the row guard, cannot store
signature bytes, cannot transact a gate close. The ledger already implements the port
better than bd can.

Their shared prescription, in five moves:

1. **SQLite becomes the only record store.** Delete the bd `StoreBackend`,
   `SelectableBackendFactory`, `RootBackendLocator`, `root_backend` pinning and the
   dual gate-write path. Opus estimates 15–20% of engine complexity, and a
   disproportionate share of the twelve suspected defects' surface.
2. **A small tracker port replaces it** — roughly `get`, `children`, `blockers`,
   `claim`, `close`, plus optional `annotate` and `flag`. Every write followed by a
   read-back, because no remote tracker is transactional.
3. **The `contractor` record moves off the bead into the ledger.** Opus's governing
   rule: *the tool must reconstruct full state with the tracker offline or wiped.* That
   single rule is what makes GitHub or Jira viable.
4. **Mint tool-local, path-safe task ids** in the ledger and map them to tracker ids.
   `PROJ-12` and `#123` cannot appear in `refs/wf/...` or worktree paths.
5. **The foreman and inspector never touch the tracker.** Only the contractor, at admit
   and close, plus the attention reconciler. Snapshot at admission so no tick blocks on
   a network.

What none of them would abstract: git, SQLite, gate signing, the evidence model, and
any tracker query language.

Sol added a detail the others did not: `apply()` should return
`Applied | Conflict | Unknown`, with `Unknown` on ambiguous network failure driving a
durable `tracker_sync_pending` outbox that reconciles later and never rolls back a
landed commit.

## Where they disagree

**1. The fork barrier under Go — same fact, opposite verdict.** Opus calls it the
strongest argument against Go: the Go runtime forbids bare `fork`, so the one component
whose correctness depends on behavior between fork and exec must be redesigned, and it
is the most safety-critical file in the system. Fable agrees on the fact and disagrees
on the valence — a re-exec'd `wf exec-shim` makes the barrier *an observable process
with its own exit code* instead of a closure between two syscalls, which it calls better
engineering. Sol takes the same line.

**2. Where claims should live.** All three agree "not the tracker", each picks a
different primitive: Opus says git-ref compare-and-swap (`git update-ref <ref> <new>
<old>`), reusing what landing already trusts, and the only option that works across
machines; Fable says the ledger's `BEGIN IMMEDIATE` plus the existing flock; Sol says
engine-side leases.

## Fable's traps, if Go is ever chosen

1. **`Pdeathsig` is tied to the parent *thread*, and Go migrates goroutines across
   threads.** Without `runtime.LockOSThread()` for the child's lifetime, the signal
   fires spuriously.
2. **`database/sql` is a connection pool.** `BEGIN IMMEDIATE` on one connection with
   the next statement on another silently breaks both the one-transaction-per-method
   invariant and the flock held on the connection. Needs `*sql.Conn` with
   `SetMaxOpenConns(1)`, or a single-connection driver.
3. **Go and Rust randomize map iteration order.** Anywhere the foreman derives a
   decision by iterating records — frontier heads, conflict detection — must sort
   explicitly. Python's insertion-ordered dicts have been hiding this. This would
   produce nondeterministic routing, the exact property the system exists to guarantee.

## A correction from the exercise

The brief stated ~135,000 lines of tests. **The real figure is ~66,800** — Sol checked
it against the repository instead of accepting the brief. The original glob had swept
in 192 vendored `.venv` test files.

This matters: Opus and Fable both leaned on the inflated number as the main
rewrite-risk argument. The test corpus is still a large executable specification, but
half the asset claimed — which, if anything, tilts slightly toward Go.

## Conclusion

**Do not decide the language now. Do the store restructuring now, in Python.**

The three disagree about Go versus Python but agree completely about the tracker seam —
and that work is language-independent, deletes 15–20% of the engine, removes the
coupling that blocks any tracker but beads, and shrinks exactly the surface a future
port would carry. It is correct under both branches of the undecided question.

Then decide the language at the concurrency fork: if adding concurrent graphs and
subgraphs forces the foreman and inspector to be restructured anyway, port then, using
the existing `proc` and acceptance tests as the oracle rather than as code to translate.
