# Build loop — what enforces TDD, and at which tier

Scope: `workflows/build-loop.toml` as the interpreter runs it. This records
**which rule is enforced by what**, so a claim about the loop ("the implementer
cannot edit the tests") can be checked against the mechanism that would actually
stop it, rather than against the prose that asks for it.

Companion to `docs/graph-loops/build-loop.md` (the human-driven loop and its
economics). This file is about the shipped graph only. Line references are to
the state of the tree at the commit that adds this file; when a reference goes
stale, fix the reference — the tier assignment is the durable claim.

## The tiers

Descending strength. Tier N is stronger than tier N+1 because a runner that
wants to break the rule has less room to.

| Tier | Mechanism | Why it ranks here |
|---|---|---|
| 1 | **tick / topology** — nodes, edges, regions, bounds | The runner never gets to express the violation: routing is a pure function of the pinned graph and the recorded outcome (`workflow_interpreter/foreman/routing.py:62-97`). |
| 2 | **bwrap mounts** — `allowed_paths` as real writable binds | The write fails at the kernel, whatever the runner intends (`workflow_interpreter/supervisor/sandbox.py:445-487`, applied at `launch.py:917-955`). |
| 3 | **pinned verifiers** — `tests-untouched.sh`, `assertion-strength.sh`, `mutate.sh` | Detection after the fact, but the examiner cannot be rewritten by the round it grades: the digest is pinned per node+program and the exec goes through the hashed descriptor (`workflow_interpreter/supervisor/verify.py:238-270`, `PROC_FD_TEMPLATE` at `:67`). A red check routes; it does not merely warn. |
| 4 | **prose** — node `instructions` | Asks the runner to comply. Nothing observes compliance. |

## Rules

One block per rule. "Removing the enforcement" is what actually breaks in this
repo if the mechanism is deleted — verified where noted, not inferred.

### R1 — Tests are written and accepted before any implementation runs

- **Tier:** 1
- **Enforced at:** `workflows/build-loop.toml:4` (`entry = "write_tests"`),
  `:269-271` (`review_tests --accept--> implement`). `implement` has exactly two
  in-edges from outside the build region: that accept edge, and
  `triage_build --rebudget-->` (`:350-352`).
- **Checked by:** `tests/test_build_loop_graph.py` (whole-graph edge-set
  assertions); the happy path runs live in
  `tests/test_build_loop_drills.py:190`.
- **Hole:** see "Tier-1 recovery hole" below.

### R2 — The test author cannot write implementation code

- **Tier:** 2
- **Enforced at:** `workflows/build-loop.toml:47`
  (`allowed_paths = ["tests/acceptance/**"]` for `write_tests`) → grants at
  `workflow_interpreter/supervisor/sandbox.py:477`. Everything else in the
  checkout is bound read-only (`sandbox.py:1-28` records the bind-order
  reasoning).
- **Note:** this was tier 3-and-below before phase 1 of the `allowed_paths`
  enforcement work; `docs/adr/0001-allowed-paths-is-advisory.md` records that
  `allowed_paths` used to be a *disclosure exemption* only, and what promoted it
  to a mount bound.
- **Also tier 4:** `workflows/build-loop.toml:35-37` ("Tests only. Do not write
  the implementation") — redundant with the mount, kept for the runner's benefit.

### R3 — Reviewers cannot change what they review

- **Tier:** 2
- **Enforced at:** `writes = false` on `review_tests` (`:86`), `review_impl`
  (`:159`) and `critic` (`:193`), with `allowed_paths = []`. A non-writing task
  gets no grants and no git-rw bind at all — `sandbox.py:470-476` returns the
  plan before grants are computed.
- **Also tier 4:** `:78`, `:151`, `:186` ("You have no repo write access").

### R4 — The implementer does not edit the acceptance tests it is judged by

- **Tier:** 3 (was tier 2)
- **Enforced at:** `scripts/checks/tests-untouched.sh` — `git diff --name-only
  $WF_BASE_COMMIT HEAD -- tests/acceptance` must be empty (`:30-43`); an unset
  `WF_BASE_COMMIT` is a failure, never a silent pass (`:24-27`). Declared for
  `implement` at `workflows/build-loop.toml:129`.
- **Why it left tier 2:** `implement`'s grant was widened from `tests/unit/**`
  to `tests/**` for cr-o85.34.21 — this repo's unit suite is flat under
  `tests/`, so a fix that had to touch a unit test was unreachable. The comment
  recording the trade is at `workflows/build-loop.toml:120-125`, and the widened
  grant is `:126`. The mount no longer excludes `tests/acceptance/`; the pinned
  verifier is what fails the round on any diff there.
- **Removing the enforcement:** verified by experiment — deleting the
  `tests-untouched.sh` entry from `implement`'s `verify` list leaves the graph
  **valid** (`load_graph` returns no ERROR finding and the same single
  `judgment_verify_superset` warning). Two things do break, both incidentally:
  the content-hash pin (`tests/_helpers.py:52-54`) and the drill at
  `tests/test_build_loop_drills.py:333`, which arms a failing
  `tests-untouched.sh` and asserts `fail_code → implement` — it fails because
  its armed script is never run. **Nothing asserts the rule itself.** There is no
  check that `implement`'s verify set must contain this script for the reason it
  exists.
- **Also tier 4:** `workflows/build-loop.toml:110-113` ("Do not edit, weaken,
  skip or delete any test") and `:149-150` (the impl critic is told a weakened
  test is always a BLOCKER).

### R5 — A red check reworks inside the region rather than ending the run

- **Tier:** 1
- **Enforced at:** the `fail_code` self-edges — `:246-248`, `:257-259`,
  `:289-291`, `:299-301`, `:314-316` — with the region round bound capping
  re-entry (`:10-22`).
- **Checked by:** `tests/test_build_loop_graph.py::test_every_fail_code_is_routed_to_its_region_entry`;
  live at `tests/test_build_loop_drills.py:306,333`.

### R6 — Each acceptance test must be able to fail

- **Tier:** 4, with two tier-3 heuristics underneath. **This is the weakest rule
  in the loop and the claim most often overstated.**
- **The rule as written:** `workflows/build-loop.toml:38-40` (the author must
  state, in the docstring, the concrete input and wrong output the test catches)
  and `:75-77` (the critic must judge whether each test CAN fail; a test that
  passes against an empty implementation is a BLOCKER).
- **What the scripts actually establish:**
  - `scripts/checks/assertion-strength.sh:47-50` — a test function body contains
    an `assert` statement or a `pytest.raises(`. That is a *presence* check by
    awk. It does not evaluate the assertion, does not know what the test claims
    to catch, and cannot tell `assert True` from a real constraint.
  - `scripts/checks/mutate.sh` — plants one mutation at a time on lines THIS
    round changed under `workflow_interpreter/` and fails on a survivor. This is
    the only mechanical evidence that some test notices a wrong implementation.
    Its own limits are stated in the script and in
    `docs/graph-loops/build-loop.md:122-133`: it cannot catch a scenario nobody
    wrote, it cannot catch a double that shares the code's misunderstanding, and
    a killed mutant proves a test *can* fail — never that it fails for the
    reason its name claims. Zero mutants is a verdict, not a pass, only for
    rounds that added executable Python (`mutate.sh:13-18`, `:152-161`).
- **Net:** "each test can fail" is enforced by a human/model judgement (tier 4)
  plus a syntactic presence check and a coverage-of-changed-lines check. No tier
  in this loop establishes that a test fails for the *right* reason.

### R7 — The examiner cannot be rewritten by the round it grades

- **Tier:** 3 (this is what makes tier 3 worth ranking above prose)
- **Enforced at:** `workflow_interpreter/supervisor/verify.py:238-270` — the
  digest is pinned under `cwd / argv[0]` per node
  (`supervisor/channels.py:230-243`) and the program is exec'd through the same
  descriptor that was hashed (`verify.py:67`, `:299-343`); a provenance mismatch
  is exit 126, refused rather than run. Checks run against a clean detached
  checkout of the artifact commit, not the live tree (`verify.py:1-12`).
- **One step further:** `mutate.sh` pins its own site picker by sha256
  (`scripts/checks/mutate.sh:46`, compared at `:68-71`), because `mutate.py`
  lives in the tree under test; `tests/checks/test_mutate_script.py:344` fails
  until the pin is updated in the same commit.

### R8 — The graph itself cannot drift silently

- **Tier:** 1 (pin, not prevention)
- **Enforced at:** `tests/_helpers.py:52-54` (`BUILD_LOOP_CONTENT_HASH`) asserted
  by `tests/test_build_loop_graph.py:84-89`. Any change to the graph's *meaning*
  — comments are excluded, the hash is over the canonicalized model
  (`schema/loader.py`) — turns a test red.
- **Limit:** the pin proves a change was deliberate. It does not say the change
  was correct.

## Tier-1 recovery hole (cr-5fs)

Ordering is topology on the happy path, and topology has a second exit that is
not an edge: a §10 bound refusal happens **before the mint**, so it takes no
edge at all.

- `REGION_ROUNDS` exhaustion routes through the region's `on_exhausted`
  (`workflow_interpreter/foreman/routing.py:52-59`) — correct for both regions.
- `INFRA_RETRIES` exhaustion routes through `node.fallback or
  document.fallback` (`workflow_interpreter/foreman/bounds.py:32-40`).

Before the fix, no node declared a fallback, so **every** node fell to the
document-level `[fallback] to = "triage_build"`. For a tests-region node that
meant the human's only non-abandon option was `triage_build --rebudget-->
implement` (`workflows/build-loop.toml:350-352`): a resume that reaches
`implement` without `review_tests` ever accepting. The recovery vocabulary could
not express "resume the tests region".

**Fix (cr-5fs):** node-level `fallback = { to = "triage_tests" }` on both
tests-region nodes — `workflows/build-loop.toml:61` (`write_tests`) and `:96`
(`review_tests`). Chosen over a region-aware document fallback because
`node.fallback` already exists in the schema and is already validated
(`schema/rules_references.py:160-187`), so the fix adds no runtime concept;
a region-level fallback would need a new schema field, a new node→region→document
precedence rule at four call sites, and its own validator coverage.
Regressed as a class by
`tests/test_build_loop_graph.py::test_infra_retry_exhaustion_recovers_inside_the_failing_region`,
which derives the expected target from each region's `on_exhausted` — so a new
tests-region node that omits its fallback fails the test.

**How completely this closes the hole:** the *ordering* hole is closed — no
bound refusal can now reach `implement` without passing `review_tests.accept`
first. The *vocabulary* is still coarse: `triage_tests --rebudget-->` re-enters
at `write_tests` (`:340-342`), so a human who only wanted to resume the review
re-runs the author. That is safe (it cannot skip review) but wasteful, and it is
the residual.

## Known gaps

1. **R4 is undeclared.** Nothing states that `tests-untouched.sh` is what
   replaced the narrow mount. Removing it from the verify list leaves a valid
   graph; the two tests that break, break for other reasons (see R4).
2. **R6 has no tier-1 or tier-2 backing** and its tier-3 scripts are heuristic
   (see R6).
3. **`$HOME` and `/tmp` stay writable** inside the sandbox by design — an
   accepted residual of tier 2 (`workflow_interpreter/supervisor/sandbox.py:18-20`).
   Tier 2 bounds the checkout, not the machine.
