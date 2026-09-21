# Store restructure — state

Read `orchestration.md` first, then this. Update at every phase transition.

| Field | Value |
|---|---|
| Branch | `wf/store-restructure` (from `aa0adc6`) |
| Current slice | none — all slices closed, gate B passed, close-out docs done |
| Phase | DONE — merged to `main` as `0ad406b` (2026-09-21); merged-result gate: 2291 passed, 2 order-dependent flakes (pass alone), bd lane/ruff/fmt/mypy 0 |
| Last commit on branch | `266efb4` (gate B fixes `f56f59c..80e4d5b`, close-out docs `266efb4`) |
| Fix round | 0 / 3 |
| Fable gate A | SHIP WITH FIXES on `aa0adc6..b07b534`; fixes in `82e328f` |
| Fable gate B | MERGE AFTER FIXES on `82e328f..865a3d3`; blocking findings 1, 2, 3 (+5) fixed in `f56f59c..80e4d5b`; finding 4 → cr-ov7l, 10 → cr-kba4, 11 → cr-m6am; 6–8 in close-out docs |

Phases: NOT_STARTED · BRIEFED · IMPLEMENTING · REVIEWING · FIXING · CLOSED

## Slice log

| Slice | Bead | Result | Gate line | Commit range |
|---|---|---|---|---|
| S0 | cr-nwy9.7 | CLOSED | pytest 2265/2 flaky, ruff/fmt/mypy 0 | `f24db40..82e328f` |
| S1 | cr-nwy9.1 | CLOSED (+cr-p7dg, cr-ho9m) | pytest green/flaky-only, ruff/fmt/mypy 0 | `995fc08..4236f53` |
| S2 | cr-nwy9.2 | CLOSED | pytest green/flaky-only, ruff/fmt/mypy 0; 7/7 fix probes | `91ff4b7..a7165ec` |
| S3 | cr-nwy9.3 | CLOSED | pytest green/flaky-only, ruff/fmt/mypy 0; 9/9 fix probes | `5af4cf8..a228a31` |
| S4 | cr-nwy9.4 | CLOSED | pytest green/flaky-only, ruff/fmt/mypy 0; 7/7 fix probes | `98a06a7..e763b0e` |
| S5 | cr-nwy9.5 | CLOSED | pytest green/flaky-only, ruff/fmt/mypy 0; fix probes green (2 dispatches) | `a672c73..a11d255` |
| S6 | cr-nwy9.6 | CLOSED | both lanes green (lane 1 flaky-only: profiles_steer), ruff/fmt/mypy 0 | `877154e..e6f0f41` |
| S7 | cr-h498 | CLOSED | both lanes green (flaky-only), ruff/fmt/mypy 0; 7/7 fix probes | `992f694..865a3d3` |

## Open items

- From S7: the committed export path is written only for a LANDED task (`write_landed_export`); `docs/workstreams/run-ledger/roadmap.md:240`/D5 'on demand for any task' is now false — fix at close-out. Checkpoint re-export is O(activations²) bytes — bead at close-out.

- From S6: BREAKING config — `tracker` is required in ForemanConfig and `[bd]` became `[tracker.bd]` (release note must say so — check at close-out). Quiesce probe = one `bd show` per foreman CLI invocation (~50–290 ms) and reads a bd non-zero exit as 'no record' (only timeouts/unavailable refuse) — put both to Gate B. B_A_C flake fixed in the lab (frozen clock burned `stale_after`); residual product bug: a stale-terminated decide child is graded NO_DIFF and accepted as a decision — add to the flake bead. S1 wrapper-home deferral RESOLVED (`repo_hash` deleted).

- From S5 — ROADMAP AMENDMENT owed at close-out: R3 beats R4's S4 acceptance line. With a claim-capable tracker (file, bd) the tracker must be reachable for PREPARED→ADMITTED; 'runs with the tracker gone' holds only AFTER the claim. bd claim is `--assignee <actor> --status in_progress` (bd's own `--claim` uses bd's user). Stale-release fixed by supersession (claim replaces pending release row). `PhaseAdmission(actor="")` default still exists. B_A_C flake is pre-existing product race — beaded.

- From S4: `@pytest.mark.bd` test `test_real_beads_roundtrips_integration_claim_and_one_root` fails (no ledger claims surface in its wiring) — S6 deletes or rewires it. `BdFlag.CLAIM` callerless — S6. `guard.holder_retired` call site in `prepare_integration` has no end-to-end test. v4→v5 migration REFUSES a ledger with non-null `tasks.state` (by design).

- S4: user ruling 2026-09-20 — old suite is over-tested; delete obsolete/duplicate tests rather than port, write few lean tests. Applies to S5–S7 briefs too. Double LANDED write in `ExportPin.pin` left (a D3 test pins without landing). `MSG_ROW_MISSING` has a gerund typo (`ledger/constants.py:445`) — fold into the S4 fix round.

- S3 built `mint_task` but prepare does not call it yet (the contractor record is still bead metadata); **S4 must wire the mint into prepare**. S3 also added `roots.child_no` (schema v4) and a top-level `--epic` option. `WF_EPIC_SEGMENT` keeps its env name (wire change, not renamed).

- S2 added `tasks.state` (schema v3: landed/abandoned) so a rebuilt ledger can satisfy "state must be LANDED" before S4's `contractor_records` exists; S4 must fold it in.
- Guide `diagrams.md` still shows the `export_oid` close/archive/cleanup gates (~5 places) — close-out rewrite.

- S1 deferred keying the wrapper home on `repo-id` (config loads before any ledger opens; would break the inspector==foreman wrapper-root validator in every hand-written config). `ledger/paths.repo_hash` survives only for that digest. Decide at S6 whether to file a follow-up bead.
