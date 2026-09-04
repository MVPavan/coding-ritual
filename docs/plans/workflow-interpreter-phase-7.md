# Workflow Interpreter — phase 7 plan (v2, approved 2026-09-04)

Status: **v2 — APPROVED by the user 2026-09-04 after an Opus 5 medium critic pass (REVISE: 1
BLOCKER, 5 MAJOR, 4 MINOR; every finding re-verified against the code
before it moved the plan).** Bead: `cr-o85.34.7` (parent `cr-o85.34`).
Base: `main` at `6cc1b76` (phase 6.5 merged). Predecessor plan:
`docs/plans/workflow-interpreter-phase-6.md`; its §3 rows tagged "phase 7"
are the inventory this plan works through.

Goal: **`build-loop` — the second graph and the only one with two
regions — runs on the engine as it is: validates, binds its cross-region
inputs, has every verify script it names, and runs a scripted lifecycle
from `create` to `slice_done` on the fake-bd lab with every routing branch
exercised.** A live run (real runners, real cost) is a separate user call
after the drills are green (§2, slice D4).

Simplicity rule (kept from phase 6): nothing here adds a capability the
build-loop lifecycle does not exercise. Where the design prose
(`docs/graph-loops/build-loop.md`) names more than the loop needs today,
the reduction is a decision in §0, not a silent cut.

## 0. Decisions the user takes before slice A lands

| # | Decision | Recommendation (verified basis) |
| --- | --- | --- |
| D1 | Cross-region input binding rule | **A producer in another region binds to its latest CLOSED activation, any round.** Rounds are per-region counters (§10.1), so "current round first" is meaningful only when producer and consumer share a region; today `select_bindings` filters producers by `activation.metadata.region == node.region` unconditionally (`inputs.py:78-83`) and spec §2 says "in the current region". Same-region behaviour is unchanged. The validator needs no new rule: `non_optional_inputs_producible` already requires the producer to dominate the consumer over the effective graph (`rules_flow.py:289-325`). The binding is per-activation; topology, not the binder, rules out a producer re-running under a consumer mid-round (the only legal cross-region back-edge is the human-gate `rebudget` exemption, spec `:290-298`). |
| D2 | `InputsUnavailable` at mint or dispatch | **Halt gate, not traceback.** After D1 a validated graph raises it only when a CLOSED producer lacks evidence or a bound input no longer matches (`materialize`, `inputs.py:142-182`, reached from `supervise.py:138`) — invariant violations, the class §10.6 already sends to a halt gate. `tick()` converts both paths the way it converts an audit violation (`tick.py:300-312`), reason on the gate; the existing except tuple (`tick.py:423-430`) lists no `ValueError`, so there is no ordering conflict. |
| D3 | Second copy of the graph | **No `fixtures/build-loop.toml`.** `workflows/build-loop.toml` is the only copy; the load+validate test reads it there and pins its content hash. The feature-delivery split (`tests/_helpers.py:23-25`, "temporary until phase 5") is not extended. |
| D4 | Verify-script set | **Ship 4 scripts + reuse 1; defer 3.** `gate.sh` is `scripts/verify-feature.sh` under another name — the TOML points at the existing script. `rows-vs-names.sh` has no row-ID source in a checkout (no argument, brief not in the tree; `verify.py:297-318`) — deferred until a row-ID artifact convention exists. `review-artifact.sh` and `claims-cited.sh` inspect the reviewer's OWN findings, which go to a separate outputs ref (`workspace.py:513-539`) and are absent from the checkout — deferred to the first live run with a malformed findings file. Kept: `tests-parse.sh`, `assertion-strength.sh`, `tests-untouched.sh`, `mutate.sh`. |
| D5 | Verifier env (cr-o85.34.10) | **One variable, `WF_BASE_COMMIT`.** Today `_run_once` calls `subprocess.run` with no `env=` (`verify.py:379-387`): the script inherits the wrapper's environ and nothing `WF_*` is injected. The wrapper adds `WF_BASE_COMMIT` = the activation's `intended_base_commit`; a script that needs it and finds it unset exits 1 naming it. For a non-writing node the base equals the verified head (`mint.py:356-367`, `exit.py:551-557`), so diff-based checks are empty there BY DESIGN — see D7. No `WF_ARTIFACT_OID`: inside the verify tree `HEAD` is the artifact commit (`verify.py:141-152`) and no shipped script needs the OID. |
| D6 | cr-o85.34.17 disposition | **Close as premise-corrected; no engine change.** Re-attribution of `scratchpad/probes/phase6-live/20260904-070108-clean/git.tsv` (114,852 rows; reproduced by the critic): 78,374 rows carry a `pytest-of-*` path — the implementer running this repo's proc tests inside its worktree, under the wrapper root, so the hooksPath filter matched them — and the remaining "foreman" rows are `config` 8,074 / `rev-parse` 7,798 / `add` 2,994 / `commit` 2,958 / `init` 2,518: fixture repos (`init --quiet --initial-branch=main`, `config user.name wf test`) plus bd's own per-invocation probes (`config --get beads.role` ×361). The wrapper's real footprint: `worktree` 22, `status` 22, `commit-tree` 17. There is no per-cycle snapshot. bd is 955 foreman-side calls (≈26/min); a new P3 bead records the tick-read consolidation question with these numbers. |
| D7 | Reviewer verify sets vs the superset lint | **Reviewer nodes run the two cheap tree checks only, and the graph pins the resulting `judgment_verify_superset` warnings.** The critic loaded the v1 graph: with identical reviewer/implementer sets the warning fires (`graph_index.py:339-345`, `rules_flow.py:445-453` — `own <= predecessor` warns). Satisfying it would mean re-running `mutate.sh` (25 m) and the gate (20 m) at `review_impl` AND `critic` against the SAME commit `implement` already verified — 90 min of duplicate verification per round, and vacuous anyway because a reader's base equals its head (D5). Verify-at-producer already guarantees the reviewed commit passed the producer's checks. So `review_impl` and `critic` declare `tests-parse.sh` + `assertion-strength.sh` (meaningful on the reviewed tree, seconds), `write_tests` keeps `tests-parse.sh` alone and `review_tests` adds `assertion-strength.sh` (a strict superset, no warning), and B5 pins the one warning the validator actually emits — at `$.node[4].verify` (`critic` equals `review_impl`); `review_impl` is silent because its set is incomparable with `implement`'s, not a superset — so a drift is loud. Alternative, if the user prefers zero warnings: reviewers re-declare the implementer's set plus one extra check, at the cost above. |

## 1. What blocks build-loop today (verified 2026-09-04)

```text
foreman create workflows/build-loop.toml     ✓ validates (no ERROR finding)
└─ mint write_tests (tests, r1)              ✓ instance inputs task_brief, seam_contract
   └─ review_tests accept → mint implement   ✗ acceptance_tests: candidates filtered to region "build" → empty →
      (build, r1)                              InputsUnavailable (inputs.py:97) → not converted (tick.py:300-312) → CLI traceback
         └─ verify scripts/checks/*.sh       ✗ none of the 8 exists → pinned digest "" → FAIL_CODE (channels.py:277)
            └─ fail_code                     ✗ no node declares it, no edge carries it → DEAD_END (ADR 0004 post-condition)
```

Plus: `critic`'s instructions name `seam_contract`, `acceptance_tests`,
`test_findings` that its `inputs` do not declare; no test loads the file;
`test-author` / `test-critic` / `impl-critic` are not bound in
`config/foreman.example.toml` (`critic` is, `:59-60`); `ForemanLab` binds
only `implementer` and `critic` (`tests/_foreman.py:364-367`) and
hard-codes `task_brief` as the sole instance input (`:396-405`), so the
lab cannot even mint `write_tests`.

## 2. Slices

Dependency order A → B → C → D. Each ends gate-green; tests are written
before the implementer is dispatched (review loop v4); implementer = Opus 5
medium, one per slice; critic = a fresh Opus 5 medium reader, read-only.

### Slice A — cross-region binding + halt on unavailable inputs (0.5-1 day)

A1. Spec §2 "Input binding" gains the D1 rule: one sentence for the
    cross-region case, one clause that binding is per-activation and
    topology prevents mid-flight producer replacement. Same-region
    wording unchanged.
A2. `select_bindings` (`inputs.py:45-120`): the region filter and the
    current-round preference apply only when
    `index.nodes[producer].region == node.region`; otherwise candidates
    are every CLOSED activation of the producer node and the pick is the
    highest `seq`. `materialize` (`inputs.py:130-182`) is read for the
    same filter and fixed if it has it.
A3. D2: `tick()` catches `InputsUnavailable` from both the mint sites
    (`cases.py:178`, `:285`) and the dispatch path, opens a halt gate with
    `HALT_INPUTS.format(reason=...)` beside `HALT_AUDIT`, and returns
    `TickReport(halted=True, opened_gate=...)`.
A4. Tests: `tests/test_foreman_inputs.py` — cross-region binds the latest
    closed producer regardless of `round_no`; same-region round
    preference unchanged; optional cross-region input absent on round 1
    binds nothing. `tests/test_foreman_tick.py` — a two-region graph
    (`fixtures/valid/acyclic_cross_region.toml` or a minimal one) mints
    the cross-region consumer through `tick()` on the lab with the
    expected binding; a producer with evidence stripped halts with a
    gate, no exception.

### Slice B — the graph as the loop needs it, and a lab that can run it (0.5-1 day)

B1. `critic.inputs` += `seam_contract`, `acceptance_tests`,
    `test_findings` (already in its instructions).
B2. `fail_code` declared on all five task nodes; edges
    `write_tests --fail_code--> write_tests`,
    `review_tests --fail_code--> write_tests`,
    `implement --fail_code--> implement`,
    `review_impl --fail_code--> implement`,
    `critic --fail_code--> implement`. Legal (critic loaded B2+B3: zero
    ERRORs): every back-edge targets its region's `entry_node`; rounds
    cap them (`max_entries` 2 / 3); the §7.3 rerun-once policy (phase
    6.5) absorbs one flake before any of them fires.
B3. Reviewer early-abandon, mirroring phase 6 A3: `review_tests` and
    `review_impl` declare `fail_plan` with edges to `triage_tests` /
    `triage_build`; `review_tests.inputs` += `test_findings` and
    `review_impl.inputs` += `impl_findings` (own prior-round output,
    optional); both instruction blocks gain *"Report `fail_plan` when the
    same BLOCKER stands for a second round."*
B4. D4 + D7 verify lists. `write_tests` = `tests-parse`;
    `review_tests` = `tests-parse`, `assertion-strength` (strict superset;
    `tests-untouched` would forbid the very files this region writes).
    `implement` = `scripts/verify-feature.sh`, `tests-untouched`,
    `mutate`. `review_impl` and `critic` = `tests-parse`,
    `assertion-strength`. `rows-vs-names`, `review-artifact`,
    `claims-cited` removed everywhere.
B5. `tests/test_build_loop_graph.py`: loads `workflows/build-loop.toml`,
    asserts no ERROR and exactly one warning, `judgment_verify_superset` at
    `$.node[4].verify` (D7; the critic loaded the slice-B graph to confirm), pins `BUILD_LOOP_CONTENT_HASH` in
    `tests/_helpers.py`, and asserts the edge shape (five `fail_code`,
    two `fail_plan` edges) so a later edit that reintroduces the dead end
    fails here, not in a live run.
B6. `config/foreman.example.toml` gains `test-author` on claude (writer —
    codex cannot commit, phase 6 D5), `test-critic` and `impl-critic` on
    codex (read-only); `tests/test_foreman_example_config.py` covers them
    and instantiating build-loop against the example config no longer
    refuses with "unknown runner roles".
B7. `ForemanLab.__init__` takes `roles` and `instance_inputs`
    (defaults = today's values, so every existing drill is untouched);
    `pin_checks` already accepts arbitrary script names.

### Slice C — verifier env + four check scripts (1-2 days)

C1. D5 plumbing: `run_checks(node, tree, pinned_digests)` (`verify.py:222`),
    `_execute` (`:327`) and `_run_once` (`:379-387`) gain the base commit
    and pass `env={**os.environ, "WF_BASE_COMMIT": base}`; the caller in
    `exit.py` supplies the activation's `intended_base_commit`.
    `tests/test_supervisor_verify.py` asserts a script sees it.
    `scripts/verify-feature.sh` and `scripts/review-checks.sh` are NOT
    edited — not even their header comments: their bytes are the §7.3
    digests feature-delivery pins per instance, and a changed byte turns
    every live instance's checks into `REFUSED → fail_code`
    (`verify.py:236-247`). Their stale "no `$WF_*`" comment and
    `review-checks.sh`'s last-commit-only check (`git show --name-only
    --format= HEAD -- tests/acceptance`, `:28`, which a multi-commit
    round escapes) are a §3 row for feature-delivery.
C2. `scripts/checks/tests-parse.sh`: `uv run pytest --collect-only -q
    tests/acceptance` exits 0 and collects ≥ 1 test.
C3. `scripts/checks/assertion-strength.sh`: every test function under
    `tests/acceptance/**` contains an `assert` or `pytest.raises`; names
    each offender; ≤ 8 lines stdout.
C4. `scripts/checks/tests-untouched.sh`: `git diff --name-only
    "$WF_BASE_COMMIT" HEAD -- tests/acceptance` is empty; names each
    touched file otherwise.
C5. `scripts/checks/mutate.sh` — the one real piece of work.
    1. Copy the tree: `git archive HEAD | tar -x` into a `$TMPDIR`
       directory (no git state touched — the verify tree is itself a
       worktree of the real repo, `verify.py:145`, and `git worktree add`
       from inside it would register under the real `.git/worktrees`
       and survive a timeout kill); `trap` removes the copy; one shared
       `UV_PROJECT_ENVIRONMENT` so `uv run` resolves once.
    2. Baseline: `uv run pytest -q -x -m "not bd and not live and not
       proc"` on the copy. Red → exit 1 "baseline red" in ~1 minute, no
       mutants — `run_checks` (`verify.py:224-252`) runs every declared
       check and never short-circuits, so the script cannot assume the
       gate went green first.
    3. Sites: the changed hunks of `WF_BASE_COMMIT..HEAD` under
       `workflow_interpreter/**`; at most `N = 8`, in order of
       appearance, from a fixed operator set (`==`↔`!=`, `<`↔`<=`,
       `>`↔`>=`, `and`↔`or`, `True`↔`False`, `not` removed). Zero sites
       (no Python change) → exit 0 with one line saying so.
    4. Per mutant: re-copy, apply the one mutation, run the same pytest
       subset, record killed (first failing test NAME) or survived.
    5. Exit 1 if any mutant survives, naming site and mutation; ≤ 8
       lines stdout; full output to a PID-suffixed log.
    Site selection and editing live in `scripts/checks/mutate.py`
    (stdlib only) invoked by the `.sh`; the pinned bytes are the `.sh`
    only — cr-o85.34.11's one-file-deep pin, recorded, not fixed.
    Budget: the unit subset is ~55 s on this repo (1042 tests), so
    baseline + 8 mutants ≈ 9 min inside the 25 m timeout; C6 measures it.
C6. `tests/checks/` (`-m proc`): each script on `_project.py`'s fixture
    tree, one passing and one failing case, `WF_BASE_COMMIT` set by a
    helper; `mutate.sh` gets a fixture with a planted uncovered branch
    (survivor → exit 1, named) and one with full coverage (exit 0), and
    the test records wall time in its output.

### Slice D — drills, create, docs, and the live run (1 day + user call)

D1. Build-loop drills on `ForemanLab` (B7) with scripted children, real
    git, fake bd, `pin_checks` for the five scripts:
    - happy path: `write_tests done → review_tests accept → implement
      done → review_impl accept → critic accept → slice_gate approve →
      slice_done`; asserts `implement.inputs.acceptance_tests` binds
      `write_tests`'s activation and `critic.inputs.test_findings` binds
      `review_tests`'s.
    - tests-region rework: `review_tests reject → write_tests (r2) →
      accept → implement`; implement binds the ROUND-2 tests.
    - tests exhaustion: two rejects → `triage_tests`; `rebudget` re-enters
      `write_tests`.
    - build rework + no-progress: `review_impl reject → implement`
      identical tree → §10.5 → `triage_build`.
    - `fail_code` on `critic` routes to `implement` (B2), not a dead end.
D2. `foreman create workflows/build-loop.toml --input task_brief=…
    --input seam_contract=…` against the generated config, on the
    existing `-m bd` lab pattern.
D3. `docs/graph-loops/build-loop.md` gets a short "as shipped" section:
    graph file, the script set per node, D7's rationale, and the three
    deferred scripts with their triggers. Spec §2 sentence from A1.
D4. Live run — **user decision, not in the estimate.** Same rig recipe
    as phase 6 E2 (`scratchpad/probes/phase6-live/BASELINE.md`), a
    slice-sized task, real claude writers and codex critics; ≈ 1 h,
    ≈ $5. Filed as a bead that stays open until the user schedules it.

## 3. Deferred — recorded so nobody rediscovers them

| Item | Found by | Trigger |
| --- | --- | --- |
| `rows-vs-names.sh` | D4 | a row-ID artifact convention (e.g. `tests/acceptance/rows.tsv` committed by `write_tests`) |
| `review-artifact.sh`, `claims-cited.sh` | D4 | first live run whose findings file is malformed; needs the reviewer's pinned outputs path in the verify env |
| Reviewer nodes re-running the producer's checks (zero-warning graph) | D7 | a reviewed commit that differs from the verified one — impossible on today's engine |
| Mutant-survivor routing to the orchestrator vs implementer (build-loop.md "Routing") | this plan | a verify script can only pass/fail; a survivor is `fail_code → implement` in v1 |
| `WF_ARTIFACT_OID` and the rest of cr-o85.34.10 | D5 | first script that needs the OID |
| feature-delivery: `review-checks.sh` sees only the last commit; `verify-feature.sh` header says no `$WF_*` | C1 | next feature-delivery graph edit (a byte change re-pins both digests; declare `tests-untouched.sh` on its `implement` then) |
| Pinned dependency manifest (cr-o85.34.11) — `mutate.py` itself is now pinned by a sha256 embedded in `mutate.sh` (slice C critic, MAJOR); the general manifest stays open | C5 | first non-cooperative-runner assumption |
| Config-layering deletion + pinned-role runtime (cr-7h8, P1) | phase 6 | not a build-loop blocker; next after this epic |
| Persist `prepare()`'s session id (cr-o85.34.9) | phase 6 | next after this epic |
| Stale policy (cr-o85.34.8) | phase 6 | first live run that burns `max_wall` on a silent runner |
| Tick bd-read consolidation (new P3 from D6) | D6 | a `foreman run` latency complaint with numbers |

## 4. Beads

`cr-o85.34.7` is the epic. Children: `cr-o85.34.6` (slice A, exists),
`slice B`, `slice C` (closes the `WF_BASE_COMMIT` half of `cr-o85.34.10`,
which stays open for the rest), `slice D`, `live run (D4)`.
`cr-o85.34.17` closes under D6 with the corrected numbers; one new P3 bead
for the bd-read question.

## 5. Verification recipe (unchanged + two)

`uv run pytest -q -m "not bd and not live"` · `-m proc` · `-m bd` ·
`ruff check` · `ruff format --check` ·
`MYPYPATH=. uv run mypy --strict --explicit-package-bases workflow_interpreter/`
· `-m acceptance`. Slice C adds `tests/checks/` (inside `-m proc`); slice D
adds the build-loop drills (inside the unit set). `git status` clean before
any completion claim.

## 6. Estimate

A 0.5-1d · B 0.5-1d · C 1-2d · D 1d → **3-5 days to green drills**; the
live run is on top, at the user's call.
