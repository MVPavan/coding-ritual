# Build loop — orchestration graph (v4.1)

**Audience: the orchestrator only.** Deliberately NOT a rule under
`.claude/rules/` and deliberately NOT listed in `.claude/project/docs-index.md` —
loading this into every agent's context is the exact cost this protocol exists to
avoid. Workers receive the parts that apply to them, in their brief.

Supersedes nothing in `docs/specs/workflow-interpreter.md`. That spec describes a
program that runs graphs; this describes the human-driven graph we run *now*, by
hand, to build it. Provenance: adopted with the user 2026-08-29 after the phase-5
token audit. Evidence for every claim is in `scratchpad/probes/PHASE5-STATE-OF-PLAY.md`
(machine-local; `scratchpad/` is gitignored).

## The graph

```text
PLAN (once per phase)
└─ Fable(C) drafts ⟳ Sol xhigh(O) ≤3 ⟳ Opus high(C) ≤2 ──▶ user approves ──▶ frozen
   └─ slices cut by DEPENDENCY LAYER: repairs → seams → pure core → I/O → integration

PER SLICE   (only if the plan names the slice's public seam — see Seam rule)
│
├─ 1. Sonnet(C)  ──▶ tests/  acceptance tests, one per spec row ID
│                    reuses tests/_foreman.py, _supervisor.py, _profiles.py …
├─ 2. Sol(O)     ──▶ reviews the TESTS: rows-vs-names + assertion strength  [1 pass]
│                    (as shipped: rows-vs-names is deferred; tests-parse +
│                     assertion-strength ship)
├─ 3. orchestrator ──▶ grep row-IDs vs test names        ← contract completeness, free
│
├─ 4. Terra(O)   ──▶ implement: "make these pass, do not edit tests/"
│                    runs TARGETED tests only; never the full gate
│                    MAY edit its own unit tests
│
├─ 5. scripts/verify.sh        ← deterministic, zero model tokens
│      └─ emits ~8 lines + a ROUTE (see Routing)
│
├─ 6. Sonnet(C)  ──▶ reviews the IMPLEMENTATION  [1 pass, only on green, no survivors]
├─ 7. Sol(O)     ──▶ critic                      [1 pass, after convergence]
└─ 8. orchestrator ──▶ verify only NEW blocker/major claims by hand

PER PHASE
├─ drills — spec §13 scenarios as e2e code, real bd under flock, real git,
│           real processes, crash + restart
└─ sign-off — Opus high(C) + Sol xhigh(O), both must agree ──▶ user
```

## Slices and the seam rule

A slice is **a set of modules buildable and gateable together whose dependencies
are already in the tree** — cut by dependency layer, never by feature. Phase 5:
A repairs → B seams → C1 pure core → C2a/C2b I/O → D integration.

**Seam rule.** Write acceptance tests before the implementer **iff the plan names
the slice's public seam.** Otherwise the slice's first job is to freeze the seam
and its tests follow. Slice A failed exactly here: forward references to
`foreman/supervise.py` blocked the implementer on five rows.

## Cross-family alternation

Claude(C) ↔ OpenAI(O) at every hand-off. Two families and four roles means not
all pairs can alternate, so they rank:

| Edge | Strength |
|---|---|
| test-writer ≠ implementer | hard — the shared-misunderstanding defect class |
| test-reviewer ≠ test-writer | hard — otherwise the contract is unchecked |
| impl-reviewer ≠ implementer | hard |
| impl-reviewer ≠ test-writer | soft; accepted violation |

**Family is the constraint; effort and model size are free.** Never let
alternation drag Opus into mechanical work — an OpenAI slot can be Sol at medium.

Roster: tests Sonnet / test-review Sol / implement Terra / impl-review Sonnet /
drills Opus / sign-off Opus high + Sol xhigh. Keep Terra as implementer until
Sonnet-as-implementer has been trialled.

## verify.sh — deterministic, runs BEFORE any reviewer

Reviewing on a red gate spends a reviewer on what a script does free. Mutation
needs a green baseline, so the gate is step 1 of the mutation procedure — one
script, not two.

1. `git diff --stat tests/` must be empty for acceptance tests.
2. Gate: `uv run pytest -q -m "not bd and not live"` (963, ~33s) + `ruff check`
   + `ruff format --check` + `mypy --strict`.
3. Plant N mutants read off the diff. **One occurrence at a time**; re-copy the
   tree and baseline it green before each. Print failing test **NAMES**, never a
   count.
4. Emit ~8 lines and a route. Tracebacks go to `scratchpad/gate/<slice>-<ts>.log`,
   never to stdout — a red gate is the only path that can dump 2,000 tokens of
   traceback into the orchestrator's context, permanently.

### Routing

| Verdict | Route |
|---|---|
| gate FAIL | implementer |
| mutant survived in an ACCEPTANCE test | orchestrator — a CONTRACT gap, not a bug |
| mutant survived in a UNIT test | implementer |
| >3 failures, mypy avalanche, unfamiliar error class | diagnostician subagent → ONE paragraph |

**No standing observer agent.** A fresh observer must be onboarded to judge a
failure, and onboarding costs more than a 6-line shaped summary. Routing is the
irreducible orchestrator job because context is the only thing the orchestrator
holds that a fresh agent does not. Delegate EVIDENCE, keep ANSWERS.

**Why the orchestrator runs no gate by hand:** every reason to re-run it (full
suite vs targeted, four commands vs one, claim ≠ proof per spec §7, a fixed
reference point) requires only that something *other than the implementer* run it.
A script satisfies all four.

## What each check answers — none replaces another

| Question | Answered by |
|---|---|
| Does the code do what the tests say? | the implementer's own targeted run |
| Did anything else break; does it typecheck and lint? | the gate inside verify.sh |
| Would the tests notice if the code were WRONG? | the mutants |
| Does the system survive a real lifecycle? | drills — spec §13, real bd/git/flock |
| Was a required scenario never written at all? | rows-vs-names grep (deferred — see "As shipped") |

### Known blind spots

- **Mutation cannot catch a double that shares the code's misunderstanding.** An
  identity-function `blob_text` passes every mutant. Only executing the real
  collaborator (real git, real `ssh-keygen`) finds these.
- **Mutation cannot catch a scenario nobody wrote** — mutate the line and some
  other unit test dies, so no survivor appears. The rows-vs-names grep is the
  only cheap check for this — and the shipped graph does not run it yet, so this
  blind spot is open until the deferred script lands (see "As shipped").
- **A killed mutation proves a test CAN fail, not that it tests what its name
  claims.** Read the body.
- Reviewer claims are not evidence. A critic asserted a grep count of 1 where the
  repo has 5. Verify NEW blocker/major claims; skip re-verifying closed ones.

## Economics (why the shape is what it is)

Cost within one agent session is **quadratic in tool calls**: cumulative input ≈
N × C_final/2, because every call re-sends the whole conversation. Phase 5
measured: implementer 137k average context per call over 2,695 calls;
orchestrator 433k over 414. Health metric to watch is **average context re-sent
per call**, not token totals — investigate above 250k.

Weighted post-Terra split was implementation ~30% / assurance ~65%. About half
the assurance was earned (7 drill-found defects, 5 reviewer blockers, 2 in
already-shipped code); the other half was fix-round and re-review overhead, which
is what this loop removes.

## As shipped (phase 7)

The graph above now exists as a file the interpreter runs:
**`workflows/build-loop.toml`** (its only copy; `tests/test_build_loop_graph.py`
pins its content hash, and `tests/test_build_loop_drills.py` runs its lifecycle
on the lab). What the file declares differs from the prose above in three
recorded ways.

Which of the loop's rules that file actually ENFORCES, and by what mechanism,
is recorded per rule in `docs/graph-loops/build-loop-tdd-enforcement.md`.

**Verify set per node, exactly as the TOML declares it:**

| Node | Verify commands |
|---|---|
| `write_tests` | `scripts/checks/tests-parse.sh` |
| `review_tests` | `tests-parse.sh`, `assertion-strength.sh` |
| `implement` | `scripts/verify-feature.sh` (the gate), `tests-untouched.sh`, `mutate.sh` |
| `review_impl` | `tests-parse.sh`, `assertion-strength.sh` |
| `critic` | `tests-parse.sh`, `assertion-strength.sh` |

**Why the reviewers run only the two cheap tree checks** (plan D7): satisfying
the validator's `judgment_verify_superset` warning would mean re-running
`mutate.sh` (25 m) and the gate (20 m) at `review_impl` AND `critic` against the
same commit `implement` already verified — ~90 minutes of duplicate work per
round, and vacuous besides, since a non-writing node's base equals its verified
head, so every diff-based check there is empty by design. Verify-at-producer
already guarantees the reviewed commit passed the producer's checks. The graph
therefore carries **one pinned warning** — `judgment_verify_superset` at
`$.node[4].verify`, i.e. `critic`, whose set equals `review_impl`'s — asserted
by `tests/test_build_loop_graph.py` so that a drift becomes loud rather than
silent. (`review_impl` emits no warning: its set is incomparable with
`implement`'s, not a subset.)

**Three checks named above are deferred, with their triggers** (plan §3):

| Script | Trigger that unblocks it |
|---|---|
| `rows-vs-names.sh` | a row-ID artifact convention (e.g. a `tests/acceptance/rows.tsv` committed by `write_tests`) — a checkout carries no row IDs today, so the check has nothing to read |
| `review-artifact.sh` | the first live run whose findings file is malformed; the reviewer's own findings go to a separate outputs ref and are absent from the verify checkout |
| `claims-cited.sh` | same as above — both need the reviewer's pinned outputs path in the verify environment |

Until `rows-vs-names.sh` lands, "was a required scenario never written at all?"
stays a human question, answered by the orchestrator's own grep.

A surviving mutant is flatter than the Routing table above, too: a verify script
can only pass or fail, so in v1 `mutate.sh` going red is `fail_code → implement`,
not a route to the orchestrator (plan §3, deferred).
