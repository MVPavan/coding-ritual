# ADR 0005 — engine facts live in a run ledger, and every run writes its knowledge down

- **Status:** Accepted
- **Date:** 2026-09-17
- **Deciders:** repo owner
- **Reviewed by:** Astra (medium) rounds 1–3 and Sol (high) rounds 1–2 at design time — five REJECTs applied into `docs/workstreams/run-ledger/roadmap.md` v6; one Sol (medium) critic per slice during the build
- **Related:** the roadmap's decisions table, `docs/workstreams/run-ledger/roadmap.md` §4 (D1–D21) — the authority for every detail this ADR states once; ADR 0001 (grants are advisory), ADR 0002 (inline instructions), ADR 0003 (argv ceiling), ADR 0004 (deterministic routing)

## Context

The engine stored every workflow fact as a bead. Three costs, measured in
this repository (roadmap §1): 233 of 616 beads were engine-written and
unreadable through `bd`; each tick paid about 1.5 s in five `bd` round trips;
and the knowledge a run produced — findings, verify output, outcomes,
signatures — was written to per-run wrapper scratch and deleted unread, so
nothing in git recorded why a change was made the way it was.

## Decision

**Engine facts move to a per-repository SQLite run ledger behind the existing
`StoreBackend` seam, and the knowledge of a run is written into the repository
by a node of the graph.** The roadmap's D1–D21 are the decision; the four that
this ADR exists to make discoverable:

1. **Two backends, one seam** (D1, D18). `bd` and `ledger` are both real. The
   backend is pinned per root at prepare, recorded as `root_backend` on the
   `phase-bridge` record so the store can be chosen before the root loads, and
   inherited by children. There is no reverse migration.
2. **bd keeps what humans read** (D7, D20). The bridge record and one
   `wf:attention` label stay in bd, projected from ledger state under a
   task-keyed lock. Claims stay bd-backed while `store` can still select bd.
3. **Nothing closes before its record is durable** (D5, D14, D19). A task
   closes only once its export is a git blob at `refs/wf/exports/<task>`;
   terminal cleanup deletes worktree, verify tree and scratch only after that;
   `wf archive` deletes refs only after a git-verified bundle.
4. **Knowledge is an executable graph contract** (D12, D21). `debrief` is a
   task node between `implement` and `review` with a static
   `docs/workstreams/**` grant, its own verifier, and `fail_code`/`fail_plan`
   edges to `triage` — so a debrief that wrote outside its directory or
   disagrees with the engine's render can never be what the ship gate signs.
   Approvals store the allow-list entry and policy that accepted them, and
   `wf ledger verify` re-verifies a task from the committed export alone.

## ADR 0003's argv ceiling applies to the bd path only

ADR 0003 measured the kernel's `execve` limit (~130 KB) because every metadata
write crossed an argv boundary into `bd`, and ruled that large payloads move to
`@file`. **That ceiling is a property of shelling out to `bd`, not of the
engine.** Ledger writes are parameterised SQL on an in-process connection:
there is no argv, so no ceiling, and the `@file` rule is not needed on that
path. ADR 0003 stands unchanged for the bd backend, which still exists.

## Consequences

- Tick cost on the ledger backend is a local transaction, which is what
  removed the admission test's wall problem.
- Two backends means every store-visible behaviour needs a contract test
  parameterised by backend factory; that suite is the cost of the seam and is
  paid deliberately until the bd backend is removed.
- `docs/workstreams/<epic>/runs/<task>/a<n>/` becomes tracked repository
  content produced by a runner. It lands in the same fast-forward as the code
  it describes, so a landing cannot carry code without its debrief.
- ADR 0001 is unchanged and load-bearing here: the debrief's grant discloses,
  and `scripts/verify-debrief.sh` — not the grant — is what contains it.
