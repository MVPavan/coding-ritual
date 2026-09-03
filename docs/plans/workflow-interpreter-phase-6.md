# Workflow Interpreter — phase 6 plan (v2, post-review)

Status: **v2 — revised after Opus 5 medium + Sol high review (both REVISE);
every review finding below was re-verified against the code before it moved
the plan.** Bead: `cr-o85.34` (parent `cr-o85`). Base: `main` at `0e19439`.

Goal: **`feature-delivery` runs unattended from `create` to its `ship` gate,
is approved by a signed payload, and runs to `shipped` — on the engine as
it is.** Build-loop moves to phase 7; the three build-loop blockers the
review found are recorded in §3 so they are not rediscovered.

Simplicity rule applied by both reviewers and kept: nothing in A-E adds a
capability this one run does not exercise.

## 0. Decisions the user takes before slice A lands

| # | Decision | Recommendation (verified basis) |
| --- | --- | --- |
| D1 | `no_diff` semantics (cr-atn) | **no committed artifact.** `exit.py:707-712` already grades exactly that; §7.4 says it. Both reviewers concur. |
| D2 | Stale runner | **`max_wall` only, this phase.** Stale is a hint the wrapper cannot act on: no exit reason exists (`supervisor/models.py:92-113`) and the watch loop cannot be terminated from the stale branch (`supervisor/run.py:276-295`) — a real change, not a `monitor.py` edit. Bead it (§3). |
| D3 | Target | **`feature-delivery` only.** 1 instance input, 2 scripts. Build-loop cannot even bind its inputs today (§3, B-1). |
| D4 | Spec text "the foreman is a model" | **Record it in ADR 0004, do not rewrite §1/§4/§13 this phase.** The ADR states: the foreman is deterministic code; runner nodes hold the intelligence; routing consumes node verdicts; model gates deferred with trigger. Spec rewrite is a phase-7 doc task. |
| D5 | **ADR 0001's own trigger fires in this phase.** `foreman run` = automatic multi-tick execution, which ADR 0001 lines 68-79 name as the point where `allowed_paths` prevention becomes blocking. Writers cannot be put on codex (codex makes `<root>/.git` read-only incl. the worktree `gitdir:` file — `tests/test_profiles_git_isolation.py:13-17` — so a codex writer cannot commit and every `done` grades `fail_code`). | **Supersede the trigger explicitly for the first proof:** ADR 0004 records that phase 6's `run` executes under ADR 0001's two assumptions (cooperative runner, human reads the cumulative diff at each gate) with writers on claude, and that cr-n2z becomes P1-blocking for any run whose gate is not human-read. This is a user ruling, not an engineering choice. |

## 1. What blocks a run today (verified 2026-09-03)

```text
foreman run <graph>             ✗ no `run`; five commands, all take an existing root_id (foreman/__main__.py:50-70)
└─ instantiate(...)             ✗ zero production callers; ONE input hard-coded as "task_brief" (foreman/resolve.py:135-175)
   └─ create_root               ✓
      ├─ mint / dispatch        ✓
      └─ grade
         └─ verify <script>     ✗ scripts/verify-feature.sh, scripts/review-checks.sh do not exist → pin "" → FAIL_CODE (channels.py:277, exit.py:623-627)
            └─ FAIL_CODE        ✗ dead-ended TWICE: frontier.py:97-113 (_dead_end) and routing.py:80-84, both keyed on "claimed ≠ computed"
               └─ open gate     ✗ an OPEN gate is never a routing head (frontier.py:184-203 requires _is_decided) → tick() returns an empty TickReport → a naive `run` spins
```

Plus: reviewer `accept` is a SUCCESS claim (`exit.py:94-96`); one red check
overwrites it to `fail_code` (`exit.py:685-692`); `review` declares no
`fail_code` → DEAD_END. So a red reviewer check is also a human halt.

## 2. Slices

Dependency order A → B → C → D → E (both reviewers confirmed the order;
root creation must wait for final verifier bytes because `create` pins
digests — `resolve.py:215-223`). Each slice ends gate-green; tests are
written before its implementer is dispatched (review loop v4).

### Slice A — computed-failure routing + reviewer early-abandon (1-2 days)

A1. Computed `fail_code` routes when the node declares it and an edge
    carries it. **Two guards, not one:** `_dead_end` at
    `frontier.py:106-112` and `route()` at `routing.py:80-84` both drop the
    `claimed_outcome is FAIL_CODE` clause; the "node declares `fail_code`"
    clause stays in both. Precise post-condition (corrects v1): declared +
    edge → route; declared + no edge → `[fallback]` (`routing.py:85-95`,
    existing behaviour); undeclared → `DEAD_END`. Tested **through
    `tick()`** on the fake-bd lab, not only through `route()`.

A2. `feature-delivery.toml`: `implement` and `review` both declare
    `fail_code`; edges `implement --fail_code--> implement` (self-edge
    inside `build-review`; valid because `implement` is the region entry,
    `rules_flow.py:168-230` — Opus and Sol both verified) and
    `review --fail_code--> implement` (build-loop.md's "gate FAIL →
    implementer"; also what fixes the red-reviewer halt above). Rounds
    still cap it: entry arrival advances the round (`mint.py:292-338`).

A3. Reviewer early-abandon (the routing decision's output; user ruling
    "a loop must be able to end early in both directions"): `review`
    declares `fail_plan`, edge `review --fail_plan--> triage`, input
    `review_findings` (its own prior-round output — `select_bindings`
    falls back to the latest prior producer, `inputs.py:87-93`; an
    optional self-source passes `rules_flow.py:298-315`; Opus and Sol both
    verified). Its `instructions` gain the condition Sol found missing:
    *"Report `fail_plan` when the same BLOCKER stands for a second round
    or the task as briefed cannot be satisfied; do not spend a round
    restating it."* Grading rule stated precisely (Sol #3): ordinary
    failing verify overwrites only SUCCESS claims, so `fail_plan` needs
    no artifact and survives red checks; **verifier provenance failure
    overwrites every claim** (`exit.py:615-627`) — that is the one
    exception and the §7 test pins both halves.

A4. Fixture parity: the same edits land in
    `workflow_interpreter/fixtures/feature-delivery.toml`
    (`test_the_authoring_copy_is_byte_identical_to_the_library_fixture`,
    `test_canonical_and_pinning.py:153`); `FEATURE_DELIVERY_CONTENT_HASH`
    re-pinned once in `tests/_helpers.py`.

A5. ADR 0004 — routing decision + D4 + D5 text. No spec body edits.

Verification: gate recipe; `tick()`-level tests for the three A1
post-conditions; `review` red-check → routes to `implement`, not a halt;
`review` round 2 receives round-1 `review_findings`; `review fail_plan`
→ `triage` with no artifact.

### Slice B — reachable instantiation + a real config (1-2 days)

B1. `instantiate(composition, toml_path, *, instance_key,
    instance_inputs: Mapping[str, Path], allow_test_flags, overrides)`.
    Per input: declared with `producer = "instance"` else
    `ResolutionError`; required-and-missing → `ResolutionError`; non-empty;
    per-input ≤ `MAX_INSTANCE_INPUT_BYTES`. **Plus the aggregate cap
    `create_root` enforces** (`roots.py:121-129`, 65,536 bytes — Sol #5);
    report it as one error before the bd write. `brief_path` removed.
    Callers updated: `tests/_foreman.py:362` (lab helper) and
    `tests/test_foreman_resolution.py:345-375`.

B2. CLI `create <graph.toml> --instance-key K --input name=path …
    [--allow-test-flags]` → prints `root_id`. `_run()` currently validates
    `args.root_id` for every command (`__main__.py:178-187`) — restructure
    so `create` is the one command without a root. `--config` moves to one
    position for all commands as part of the same edit (it is the same
    parser block; not a separate item).

B3. Config: **no checked-in live config** — `repo_root`/`wrapper_home`
    must be absolute (`config.py:59-63`) and CLAUDE.md forbids machine
    paths. Ship `config/foreman.example.toml` plus
    `scripts/make-foreman-config.sh` that renders it for the current repo
    into `scratchpad/` (gitignored). Roles for the first proof:
    **`implementer` → claude** (only profile whose runner can commit;
    D5), **`reviewer` → codex** (`writes = false` inversion keeps the
    checkout unwritable, channels writable — `codex.py:259-302`; Sol
    verified). Cross-family alternation holds: writer ≠ reviewer family.
    `signing` configured (see E1 preflight).

B4. **Dropped** (v1 B4, session id from `prepare`): `prepare()` runs
    after mint (`launch.py:722`), `record_dispatch` persists only the
    handle (`api.py:372-385`), and steer/retry copy
    `activation.metadata.session_id` (`tick.py:155`, `cases.py:415-424`)
    — deleting the pre-assignment leaves every continuation with an empty
    id. The hard-coded `"claude"` at `cases.py:177,284` stays; bead it
    with the real fix (persist `prepare()`'s id at dispatch).

B5. **Deferred** (v1 B5, delete config reflection + pinned-role runtime):
    tests require the vocabulary to track every permitted task field
    (`test_foreman_resolution.py:696-738`); one run under an unchanged
    config is deterministic without it. Stays cr-7h8.

Verification: gate recipe; `create` feature-delivery on a `/tmp` rig with
real bd (`-m bd`); `create` with a missing required input, an undeclared
input, and an over-cap input each refuse before any bd write.

### Slice C — two check scripts, self-contained (1-2 days)

C1. Verifier context, as it actually is (Sol #7, verified): `_execute`
    runs `[/proc/self/fd/N, *argv_tail]` with `cwd = resolved.run_dir`
    (the §7.3 checkout at the artifact commit) and **no `env=`** — the
    script inherits the wrapper's environment and receives no `$WF_*`
    variables (`verify.py:297-318`). The contract therefore is: *cwd is
    the checkout at the commit under test; derive everything from git in
    cwd; no arguments.* Adding a `WF_BASE_COMMIT` env is a bead, not this
    phase.

C2. Trusted bytes: only `argv[0]` is hashed (`channels.py:264-293`). A
    script that runs `pytest` executes the repo's tests — mutable by the
    runner. This phase accepts that with the D5 assumptions and records
    it in ADR 0004; "self-contained" means the script itself has no
    `source`/includes and invokes only `git`, `uv`, `ruff`, `mypy`,
    `pytest`. The pinned-dependency manifest is the §3 bead.

C3. `scripts/verify-feature.sh`: the six-command gate recipe against cwd;
    ≤ 8 lines stdout; full output to `$TMPDIR/verify-feature.log`.
    `scripts/review-checks.sh`: `verify-feature.sh` + a fail if the
    reviewed commit touches `tests/acceptance/**` (derived from
    `git log -1 --name-only HEAD`). The validator's superset rule is
    satisfied (reviewer verify ⊇ implementer verify).

C4. `tests/checks/` (`-m proc`): each script on a fixture tree that must
    pass and one that must fail; drill 13 (edit a pinned script →
    `fail_code` + `VERIFIER_PROVENANCE`) re-run against the real script.

### Slice D — `run` that stops at gates (1-2 days)

D1. `TickReport` gains one typed field, `waiting_gate: str | None`, set
    by `tick()` when nothing else advanced and `frontier.open_gates` is
    non-empty (the empty-report case in §1). `stalled` splits into
    `stalled: str | None` (real) and `contended: bool` (band lock miss at
    `tick.py:197`) — Sol #8: both were one free-text field.

D2. `foreman run <root_id> [--poll 30s] [--max-wall 8h]`:

```text
loop:
    report = tick(root_id)
    stop if report.halted or report.terminal or report.opened_gate or report.waiting_gate
    stop if report.stalled
    sleep(poll) if report.blocked or report.contended
    stop at --max-wall with stalled="run max_wall"
print status (D3) and exit 0 on gate/terminal, 1 on stalled
```

    `tick()` otherwise unchanged; **the canary stays per tick** (v1's
    "once per run" was impossible without changing `tick`; Sol #8).

D3. Gate rendering in `status` and at `run` exit: per open gate, the
    cumulative diff `git diff --stat <instance_base_commit>..<artifact_commit>`
    and the findings artifact paths, beside the existing inbox path and
    payload template (`__main__.py:234-262`).

Verification: gate recipe; on the fake-bd lab `run` reaches
`waiting_gate` at `ship` with no human input and does not spin; restart
`run` with the gate already open → returns immediately with
`waiting_gate`; kill `run` mid-loop, restart, converges (drill 27 shape).

### Slice E — the live run (1-3 days)

E1. **Preflight** (Sol E-risk #3): `close_gate_verified` raises
    `BdConfigError` when no verifier is configured (`api.py:577-578`;
    `signing: SigningConfig | None`). `create` refuses a config with
    `signing = None` unless `--allow-unsigned-gates` is passed for a lab.
    Generate the allowed-signers file and key with
    `scripts/make-foreman-config.sh`.

E2. `create` feature-delivery on a `/tmp` rig against a small real
    feature with the forced-first-rejection flag (§13 drill 27 shape).
    `run` → `waiting_gate=ship`. Read the diff. Sign. `run` → `shipped`.

E3. Record the baseline: bytes the foreman read, bd/git process counts
    per node, wall per node. These decide whether the bd reductions
    (Sol §4) are phase-7 work. Archive transcript + trace under
    `scratchpad/probes/phase6-live/`.

Verification: drills 1-6, 13, 15, 16, 21-25, 27 green; `git status`
clean.

## 3. Deferred — recorded so nobody rediscovers them

| Item | Found by | Trigger |
| --- | --- | --- |
| **build-loop cannot bind cross-region inputs.** `select_bindings` filters producers by `activation.metadata.region == node.region` (`inputs.py:82`); `implement` (build) needs `acceptance_tests` from `write_tests` (tests) → `InputsUnavailable`, which `tick()` does not convert (`tick.py:300-312`) → the CLI raises. The validator passes it (`rules_flow.py:296-325` checks dominance, not region). | Opus, verified | phase 7, first build-loop item; new bead |
| build-loop `critic` inputs (`seam_contract`, `acceptance_tests`, `test_findings`) | Sol audit | phase 7 |
| build-loop `write_tests`/`review_tests` `fail_code` edges, reviewer `fail_plan`, prior-findings inputs | this plan | phase 7 |
| build-loop's 8 check scripts; `scratchpad/mutate_graph.py` **does not exist** (not in tree or `git log --all`) — `mutate.sh` is written fresh | Opus, verified | phase 7 |
| `build-loop.toml` is referenced by no test; add a load+validate test when phase 7 starts | Opus, verified | phase 7 |
| Stale policy (§8.2): exit reason + terminable watch (`models.py:92-113`, `run.py:276-295`) | Sol, verified | first live run that burns `max_wall` on a silent runner |
| Persist `prepare()`'s session id at dispatch; then delete `cases.py:177,284` | Sol, verified | phase 7 |
| `WF_BASE_COMMIT` (and artifact OID) in the verifier env | Sol | first script that needs the base |
| Pinned verifier dependency manifest (one-file-deep pin) | Sol audit | first non-cooperative-runner assumption |
| Config-layering deletion + pinned-role runtime (cr-7h8) | both | phase 7 |
| Real `allowed_paths` enforcement (cr-n2z) | ADR 0001 | **P1 for any run whose gate is not human-read** (D5) |
| Parallel fan-in; subgraphs; model gates; open outcomes; `UNCERTAIN`; bd reductions; gate timeout | audits | unchanged from v1 (Conductor/Prefect designs to borrow) |

## 4. Beads

Existing: `cr-o85.34` (this plan), `cr-atn` (D1), `cr-7h8` (deferred),
`cr-n2z` (D5), `cr-0jd` (B1 validates roles at `create`).
New: `phase-6 A`…`E` as children of `cr-o85.34`; `ADR 0004`; and one bead
per §3 row that lacks one (cross-region binding; stale policy; session-id
persistence; verifier env; dependency manifest; build-loop phase-7 epic).

## 5. Verification recipe (unchanged)

`uv run pytest -q -m "not bd and not live"` · `-m proc` · `-m bd` ·
`ruff check` · `ruff format --check` ·
`MYPYPATH=. uv run mypy --strict --explicit-package-bases workflow_interpreter/`.
Every slice re-runs all six; the fixture hash re-pins once, in A;
`git status` clean before any completion claim.

## 6. Estimate

A 1-2d · B 1-2d · C 1-2d · D 1-2d · E 1-3d → **one unattended run to
`ship`, approved, to `shipped`: ~5-11 days.** Build-loop is phase 7,
with three of its blockers already written down.
