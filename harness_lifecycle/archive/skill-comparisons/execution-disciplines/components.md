# Execution Disciplines — Level 3 Components

Column keys:

| Key | Skill |
|---|---|
| `TDD⁰` | ours — `.claude/skills/test-driven-development/SKILL.md` |
| `TDDˢ` | superpowers — `skills/test-driven-development/` (SKILL.md + writing-good-tests.md) |
| `TDDᵃ` | agent-skills — `skills/test-driven-development/SKILL.md` |
| `TDDᵐ` | mattpocock — `skills/engineering/tdd/` (SKILL.md + tests.md + mocking.md) |
| `SRC` | agent-skills — `skills/source-driven-development/SKILL.md` |
| `DBT` | agent-skills — `skills/doubt-driven-development/SKILL.md` |
| `INC` | agent-skills — `skills/incremental-implementation/SKILL.md` |

## Component inventory

### `TDD⁰` — test-driven-development (ours)

| Component | Citation |
|---|---|
| Risk-scoped trigger list (bug proof / risky change / legacy / dispatch flag) | `SKILL.md:10-15` |
| One behaviour per cycle, not a feature slice | `SKILL.md:19` |
| Test through a public interface where possible | `SKILL.md:20` |
| Confirm the failure is **for the expected reason** | `SKILL.md:21` |
| Smallest change to pass | `SKILL.md:22` |
| Refactor only while green | `SKILL.md:24` |
| Ban on batch-writing tests first | `SKILL.md:29` |
| Behaviour over implementation detail (whole test-quality rubric) | `SKILL.md:30` |
| Characterization test acceptable for legacy before the fix | `SKILL.md:31` |
| Disputed test *strategy* → Codex critique before wider implementation | `SKILL.md:32` |

### `TDDˢ` — test-driven-development (superpowers)

| Component | Citation |
|---|---|
| Core principle: didn't watch it fail → don't know it tests the right thing | `SKILL.md:12` |
| "Violating the letter is violating the spirit" | `SKILL.md:14` |
| Universal application + 3 exceptions requiring the human's permission | `SKILL.md:18-29` |
| **The Iron Law** — no production code without a failing test | `SKILL.md:31-35` |
| Delete-don't-adapt: no keeping as reference, no looking at it | `SKILL.md:37-45` |
| Red-green-refactor state machine incl. wrong-failure edge | `SKILL.md:49-69` |
| Good/Bad test pair (real behaviour vs mock-driven) | `SKILL.md:75-106` |
| RED requirements: one behaviour, clear name, real code | `SKILL.md:108-111` |
| **Mandatory verify-RED** with 3 confirmations + passes/errors branches | `SKILL.md:113-128` |
| Good/Bad minimal-implementation pair (YAGNI) | `SKILL.md:134-166` |
| **Mandatory verify-GREEN** incl. output pristine; fix code not test | `SKILL.md:168-183` |
| REFACTOR only after green, no new behaviour | `SKILL.md:185-192` |
| Good-test quality table (minimal / clear / shows intent) | `SKILL.md:200-204` |
| 10-row rationalization table with argued Realities | `SKILL.md:212-226` |
| 13-item red-flag list → "delete code, start over" | `SKILL.md:228-244` |
| Worked bug-fix example (RED/verify/GREEN/verify/REFACTOR) | `SKILL.md:246-281` |
| 8-item verification checklist + "can't check all boxes → you skipped TDD" | `SKILL.md:283-296` |
| When-stuck table mapping symptom → design diagnosis | `SKILL.md:298-305` |
| Debugging integration: never fix a bug without a test | `SKILL.md:307-311` |
| **Name the break** before writing the body; bug vs decision | `writing-good-tests.md:20-30` |
| Derive expectations independently; mirror-assertion ban | `writing-good-tests.md:32-39` |
| **Change-detector ban** (fires on redesign, sleeps through bugs) | `writing-good-tests.md:41-46` |
| Behaviour not text: run artifacts, never grep source; agent docs tested via consumer behaviour | `writing-good-tests.md:48-55` |
| Your code not the framework; boundary rule for constructors/getters | `writing-good-tests.md:57-64` |
| **Gate function** before the test body | `writing-good-tests.md:66-79` |
| Mock earns no assertions | `writing-good-tests.md:83-94` |
| Mock at the right level (learn side effects first) | `writing-good-tests.md:99-112` |
| Make doubles specific; per-branch fixtures | `writing-good-tests.md:114-119` |
| Mirror real data completely (partial mocks fail silently) | `writing-good-tests.md:121-125` |
| Production classes carry production methods only | `writing-good-tests.md:127-131` |
| Prefer real components when mock setup outgrows the test | `writing-good-tests.md:133-136` |
| **Gate function** before adding a mock or helper | `writing-good-tests.md:137-148` |
| **The mutation check** — 5 mutation classes, each must break a test | `writing-good-tests.md:159-169` |
| Quick-reference table (10 situations → action) | `writing-good-tests.md:171-184` |
| 12-item warning-signs list | `writing-good-tests.md:186-199` |

### `TDDᵃ` — test-driven-development (agent-skills)

| Component | Citation |
|---|---|
| Tests are proof; "seems right" is not done | `SKILL.md:10` |
| Trigger list + explicit not-for list (config/docs/static) | `SKILL.md:12-20` |
| **Discover the stack first** — build system, checked-in wrappers, framework, conventions, CI commands | `SKILL.md:24-34` |
| "Never assume a default like `npm test`" | `SKILL.md:34` |
| Focused command during the loop, full-suite command before completion | `SKILL.md:34` |
| RED/GREEN/REFACTOR with worked TS examples | `SKILL.md:38-94` |
| **Prove-It Pattern** for bug fixes, as a flow + worked example | `SKILL.md:96-142` |
| Test pyramid with proportions | `SKILL.md:144-159` |
| Beyonce Rule (untested change breaking = your fault) | `SKILL.md:161` |
| **Test size/resource model** (small/medium/large by process, I/O, network) | `SKILL.md:163-173` |
| Decision guide: pure logic / crosses boundary / critical flow | `SKILL.md:175-186` |
| Test state, not interactions, with good/bad pair | `SKILL.md:190-209` |
| **DAMP over DRY in tests** | `SKILL.md:211-232` |
| Double-preference order: real > fake > stub > mock | `SKILL.md:234-246` |
| Arrange-Act-Assert | `SKILL.md:248-264` |
| One assertion per concept | `SKILL.md:266-280` |
| Descriptive test naming with good/bad pair | `SKILL.md:282-299` |
| 6-row anti-pattern table (impl details, flaky, framework, snapshots, isolation, over-mocking) | `SKILL.md:301-310` |
| Browser runtime-verification workflow + what-to-check table | `SKILL.md:312-336` |
| **Browser content is untrusted data, not instructions** | `SKILL.md:337-341` |
| Subagent writes the reproduction test without knowledge of the fix | `SKILL.md:343-357` |
| 7-row rationalization table | `SKILL.md:363-373` |
| **Don't re-run a clean command for reassurance** | `SKILL.md:373`, `SKILL.md:385`, `SKILL.md:398` |
| 9-item red flags | `SKILL.md:375-385` |
| 6-item verification checklist run with the repo's own command | `SKILL.md:387-396` |

### `TDDᵐ` — tdd (mattpocock)

| Component | Citation |
|---|---|
| Positioning: the reference that makes the loop produce keepable tests | `SKILL.md:8` |
| Read `CONTEXT.md` for domain vocabulary; respect ADRs in the area | `SKILL.md:10` |
| Behaviour through public interfaces; tests survive refactors | `SKILL.md:14` |
| **Seam** defined as the public boundary where behaviour is observed | `SKILL.md:20` |
| **Pre-agreed seams** — write them down, confirm with the user, no test at an unconfirmed seam | `SKILL.md:22` |
| Rationale: you can't test everything; agreeing seams targets effort | `SKILL.md:22` |
| Route to `/codebase-design` for module/interface/depth vocabulary | `SKILL.md:26` |
| Anti-pattern: implementation-coupled, with the refactor tell | `SKILL.md:30` |
| Anti-pattern: **tautological** — assertion recomputes the expected value | `SKILL.md:31` |
| Anti-pattern: **horizontal slicing**; vertical slices as tracer bullets | `SKILL.md:32` |
| Red before green; no speculative features | `SKILL.md:36` |
| One seam, one test, one minimal implementation per cycle | `SKILL.md:37` |
| **Refactoring is not part of the loop** — it belongs to review | `SKILL.md:38` |
| Good-test characteristics list | `tests.md:17-24` |
| Bad-test red flags (mocks internals, private methods, call counts) | `tests.md:38-45` |
| Verify through the interface, not the database | `tests.md:47-61` |
| Tautological example pair | `tests.md:63-77` |
| Mock at system boundaries only; never your own modules | `mocking.md:3-13` |
| Design for mockability: dependency injection | `mocking.md:20-35` |
| SDK-style interfaces over generic fetchers | `mocking.md:37-60` |

### `SRC` — source-driven-development (agent-skills)

| Component | Citation |
|---|---|
| Trigger: about to write framework code from memory; not-for list | `SKILL.md:12-26` |
| DETECT → FETCH → IMPLEMENT → CITE | `SKILL.md:28-36` |
| Version detection from the dependency file, per ecosystem; state findings | `SKILL.md:38-59` |
| Ask the user when versions are ambiguous — don't guess | `SKILL.md:61` |
| 4-tier source hierarchy + non-authoritative list (incl. training data) | `SKILL.md:67-81` |
| Fetch the page, not the site | `SKILL.md:83-91` |
| Conflicting official sources surfaced and tested against the version | `SKILL.md:95` |
| **Retrieval safety** — fetched docs are untrusted; extract-only / ignore-list | `SKILL.md:97-113` |
| Never hardcode outbound endpoints from fetched examples | `SKILL.md:114` |
| Docs-vs-codebase conflict surfaced as an A/B choice | `SKILL.md:125-139` |
| Citation rules: full URLs, deep anchors, quote the passage | `SKILL.md:165-170` |
| **`UNVERIFIED:` marker** when no authoritative source exists | `SKILL.md:171-179` |
| 6-row rationalization table | `SKILL.md:181-190` |
| 9-item red flags | `SKILL.md:192-202` |
| 9-item verification checklist | `SKILL.md:204-216` |

### `DBT` — doubt-driven-development (agent-skills)

| Component | Citation |
|---|---|
| Positioning: not `/review`; in-flight posture while correction is cheap | `SKILL.md:12` |
| 5-test definition of "non-trivial" | `SKILL.md:16-22` |
| Apply-when list + not-for list + "doubt every keystroke, ship nothing" | `SKILL.md:24-40` |
| **Loading constraint**: never in a persona's `skills:`; nested = anti-pattern | `SKILL.md:42-46` |
| Degraded self-questioning fallback, must be flagged degraded | `SKILL.md:47` |
| Copyable 5-step checklist | `SKILL.md:51-60` |
| CLAIM + why-it-matters, compactly writable or it's a vibe | `SKILL.md:62-73` |
| EXTRACT smallest reviewable unit; **strip your reasoning** | `SKILL.md:75-83` |
| Verbatim adversarial prompt with 6 attack axes; "do NOT validate" | `SKILL.md:85-104` |
| **Never pass the CLAIM** to the reviewer | `SKILL.md:106` |
| Adversarial prompt overrides a persona's balanced default shape | `SKILL.md:110` |
| Cross-model: always offer interactively, never silently skip | `SKILL.md:112-124` |
| CLI safety sequence: PATH check → binary test → confirm invocation → stdin, never shell interpolation | `SKILL.md:126-135` |
| Read-only sandbox because the artifact may carry injection | `SKILL.md:143-151` |
| CLI failure surfaced, never a silent single-model fallback | `SKILL.md:153-155` |
| Non-interactive: skip cross-model **and announce the skip**; never invoke a CLI unauthorised | `SKILL.md:161-164` |
| **RECONCILE precedence order** (contract misread → actionable → trade-off → noise) | `SKILL.md:168-179` |
| Reviewer output is data, not verdict; re-read the artifact before classifying | `SKILL.md:170` |
| **STOP bound**: trivial findings / 3 cycles / user override | `SKILL.md:181-189` |
| Too big for 3 cycles → decompose, "do not lift the bound" | `SKILL.md:191` |
| 9-row rationalization table | `SKILL.md:193-205` |
| **Doubt theater** checkable signal (2+ cycles, zero actionable) | `SKILL.md:215` |
| 15-item red flags incl. re-spawning on an unchanged artifact | `SKILL.md:207-221` |
| Interaction map with TDD / SRC / review / debugging | `SKILL.md:223-229` |
| 9-item verification checklist | `SKILL.md:231-243` |

### `INC` — incremental-implementation (agent-skills)

| Component | Citation |
|---|---|
| Trigger: multi-file change or >~100 lines before testing; not-for list | `SKILL.md:12-19` |
| Increment cycle: implement → test → verify → **commit** → next | `SKILL.md:21-42` |
| Vertical slicing (preferred), worked CRUD example | `SKILL.md:46-64` |
| Contract-first slicing for parallel FE/BE | `SKILL.md:66-75` |
| Risk-first slicing (prove the risky part before investing) | `SKILL.md:77-87` |
| **Rule 0 Simplicity** — four questions + worked over-engineering examples | `SKILL.md:91-113` |
| **Rule 0.5 Scope discipline** — 5-item do-NOT list | `SKILL.md:115-126` |
| `NOTICED BUT NOT TOUCHING` reporting format | `SKILL.md:128-133` |
| Rule 1: one logical thing per increment | `SKILL.md:135-141` |
| Rule 2: keep it compilable between slices | `SKILL.md:143-145` |
| Rule 3: feature flags for incomplete features | `SKILL.md:147-160` |
| Rule 4: safe defaults (opt-in, not opt-out) | `SKILL.md:162-172` |
| Rule 5: rollback-friendly; never delete-and-replace in one commit | `SKILL.md:174-181` |
| Directing-an-agent template with explicit out-of-scope | `SKILL.md:183-197` |
| Increment checklist run with **the repo's own commands** (defers to `TDDᵃ`'s stack discovery) | `SKILL.md:199-211` |
| Don't re-run a clean command for reassurance | `SKILL.md:211`, `SKILL.md:222` |
| 6-row rationalization table | `SKILL.md:213-222` |
| 10-item red flags | `SKILL.md:224-235` |
| Task-completion verification incl. "no uncommitted changes remain" | `SKILL.md:237-245` |
| Defers the final bar to a project Definition of Done | `SKILL.md:247-249` |

## Cross-skill matrix — the `tdd` family

`✓` present · `~` variant · `—` absent

| Component | TDD⁰ | TDDˢ | TDDᵃ | TDDᵐ |
|---|---|---|---|---|
| Test-first stated as the rule | ✓ | ✓ | ✓ | ✓ |
| Application scope | ~ risk-scoped | ~ universal | ~ near-universal | ~ user/seam-led |
| Hard enforcement (delete code written first) | — | ✓ | — | — |
| Watch it fail | ✓ | ✓ | ✓ | ✓ |
| Fail **for the expected reason** | ✓ | ✓ | ~ | — |
| Minimal implementation to pass | ✓ | ✓ | ✓ | ✓ |
| Refactor inside the loop | ✓ | ✓ | ✓ | ✗ (explicitly moved to review) |
| One behaviour per cycle | ✓ | ✓ | ~ | ✓ |
| Ban on batch/horizontal test writing | ✓ | — | — | ✓ |
| Characterization tests for legacy | ✓ | ~ | — | — |
| Bug-fix reproduction pattern | ~ | ✓ | ✓ | — |
| **Stack/command discovery** | — | — | ✓ | — |
| Focused-vs-full-suite cadence | ~ | — | ✓ | — |
| Public-interface / seam targeting | ~ | ~ | ~ | ✓ |
| **Pre-agreed, human-confirmed seams** | — | — | — | ✓ |
| Test-quality rubric beyond one line | — | ✓ | ✓ | ✓ |
| Tautology / mirror-assertion ban | — | ✓ | — | ✓ |
| Change-detector ban | — | ✓ | — | — |
| Name-the-break gate before writing | — | ✓ | — | — |
| **Mutation check** | — | ✓ | — | — |
| Mocking guidance | — | ✓ | ✓ | ✓ |
| Mock-level / side-effect learning rule | — | ✓ | ~ | ~ |
| Double-preference ordering | — | ~ | ✓ | ~ |
| Test-pyramid / size model | — | — | ✓ | — |
| DAMP-over-DRY in tests | — | — | ✓ | — |
| Naming guidance | — | ✓ | ✓ | ~ |
| Anti-pattern table | — | ✓ | ✓ | ✓ |
| Rationalization table | — | ✓ | ✓ | — |
| Red-flag list | — | ✓ | ✓ | ~ |
| Verification checklist | — | ✓ | ✓ | — |
| When-stuck → design diagnosis | — | ✓ | — | ~ |
| Output-pristine requirement | — | ✓ | — | — |
| Don't re-run a clean suite | — | — | ✓ | — |
| Untrusted-input boundary (browser/docs) | — | ~ | ✓ | — |
| Subagent-written reproduction test | — | — | ✓ | — |
| Domain-vocabulary / ADR alignment | — | — | — | ✓ |
| External critique of test *strategy* | ✓ | — | — | — |
| Worked example transcript | — | ✓ | ✓ | ✓ |

## Cross-skill matrix — non-TDD disciplines

Rows are the merged set of discipline-level components; `TDD⁰` is included as the
"ours" column since it is our only installed member of this group.

| Component | TDD⁰ | SRC | DBT | INC |
|---|---|---|---|---|
| Explicit trigger + explicit not-for list | ~ | ✓ | ✓ | ✓ |
| Self-limiting clause (don't apply everywhere) | ✓ | ✓ | ✓ | ✓ |
| Named multi-step process | ✓ | ✓ | ✓ | ✓ |
| Copyable checklist for the process | — | — | ✓ | ~ |
| Bounded loop with a cycle cap | — | — | ✓ | — |
| Decompose-instead-of-lifting-the-bound rule | — | — | ✓ | ~ |
| Adversarial/independent second opinion | ~ | — | ✓ | — |
| Rule against biasing the reviewer | — | — | ✓ | — |
| Finding-classification precedence | — | ~ | ✓ | — |
| Self-deception detector | — | — | ✓ | — |
| Untrusted-external-content boundary | — | ✓ | ~ | — |
| Citation / provenance requirement | — | ✓ | — | — |
| Explicit "I could not verify this" marker | — | ✓ | — | ~ |
| Surface-the-conflict-don't-pick rule | — | ✓ | — | ~ |
| Simplicity check on written code | — | — | — | ✓ |
| Scope-discipline do-NOT list | — | — | — | ✓ |
| Noticed-but-not-touching reporting format | — | — | — | ✓ |
| Keep the tree buildable between steps | ~ | — | — | ✓ |
| Commit cadence rule | — | — | — | ✓ |
| Rollback-friendliness / revertability | — | — | — | ✓ |
| Feature flags for incomplete work | — | — | — | ✓ |
| Repo's-own-commands verification | — | — | — | ✓ |
| Don't re-run a clean command | — | — | — | ✓ |
| Loading/orchestration constraint | — | — | ✓ | — |
| Interaction map with sibling skills | ~ | ~ | ✓ | ~ |
| Rationalization table | — | ✓ | ✓ | ✓ |
| Red-flag list | — | ✓ | ✓ | ✓ |
| Verification checklist | — | ✓ | ✓ | ✓ |

## Shared-component differences

### Within the `tdd` family

**Application scope** (all four `~`). Ours fires on four named risk conditions
(`TDD⁰:10-15`). `TDDˢ:18-28` fires always, with three exceptions each needing the
human's permission. `TDDᵃ:12-20` fires on any behavioural change, excluding only
non-behavioural edits. `TDDᵐ:3` fires on user intent, but `TDDᵐ:22`'s
unconfirmed-seam rule means it cannot proceed without a human either way.
**Ours is the only one compatible with a risk-scaled engine** — `phase-execution`
routes to TDD only for stages marked test-first (`phase-execution/SKILL.md:60`),
which `TDDˢ`'s Iron Law would treat as a rationalization. `TDDˢ` is strongest
where the risk is an agent talking itself out of testing; ours is strongest where
the risk is ceremony on low-risk work.

**Fail for the expected reason** (`TDDᵃ` `~`). `TDD⁰:21` and `TDDˢ:113-128` both
require confirming *why* it failed, and `TDDˢ` enumerates the three checks and
both branches (passes → you're testing existing behaviour; errors → fix and
re-run). `TDDᵃ:51` only requires that it fail ("a test that passes immediately
proves nothing"), and its red flags note the risk (`TDDᵃ:380`) without a check
step. **`TDDˢ` is strongest** — it is the only one that turns the check into
branching instructions rather than an assertion.

**Refactor inside the loop** (`TDDᵐ` contradicts the other three). `TDD⁰:24`,
`TDDˢ:185-192`, `TDDᵃ:85-94` all put REFACTOR in the cycle, gated on green.
`TDDᵐ:38` removes it: "refactoring is not part of the loop — it belongs to the
review stage". This is a real design disagreement, not a wording difference. **The
three-way majority is stronger for a single agent session**: deferring refactor to
review means shipping the minimal implementation into a review queue, which only
works if a review stage reliably follows — mattpocock has one (`/code-review`,
`implement/SKILL.md:13`), and in our harness the equivalent gate exists only for
`deep` stages. Adopting `TDDᵐ:38` would silently drop refactoring on every
`standard` stage.

**Ban on batch test writing** (`TDD⁰` `✓`, `TDDᵐ` `✓`). `TDD⁰:29` states it as a
one-line rule. `TDDᵐ:32` names it (**horizontal slicing**), gives three distinct
harms (tests verify *imagined* behaviour; you test shape not behaviour; you commit
to test structure before understanding the implementation), and supplies the
remedy vocabulary (vertical slices as tracer bullets). **`TDDᵐ` is stronger** —
same rule, but an agent can recognise the violation from the description, which is
what a rule in an agent-consumed doc has to do.

**Test-quality rubric** (`TDD⁰` `—` vs three `✓`). `TDD⁰:30` is one clause. The
other three each carry a full apparatus, and they attack different failure modes:
`TDDˢ`/`writing-good-tests.md` attacks tests that *cannot fail* (name-the-break
gate `:66-79`, mirror-assertion ban `:32-39`, change-detector ban `:41-46`,
mutation check `:159-169`); `TDDᵃ:188-310` attacks tests that break on refactor
and tests at the wrong level (state-not-interactions, pyramid, DAMP);
`TDDᵐ:28-32` + `tests.md` attacks the same three in compressed form.
**`TDDˢ` is strongest on this axis and by a clear mechanism**: the mutation check
is the only component in the entire comparison that *detects* a worthless test
after it is written, rather than describing how to avoid writing one. `TDDᵐ` is
strongest per line. Ours has nothing.

**Mocking guidance** (`TDDˢ` `✓`, `TDDᵃ` `~`, `TDDᵐ` `✓`). `TDDᵐ/mocking.md:3-13`
gives a boundary list (mock external APIs, DBs, time, filesystem; never your own
modules) plus design-for-mockability. `TDDᵃ:234-246` gives a preference *ordering*
(real > fake > stub > mock) with the condition for descending it.
`writing-good-tests.md:99-132` gives the operational rules the other two lack:
learn the real method's side effects before replacing it, mirror the complete real
structure (partial mocks fail silently), keep test-only cleanup out of production
classes, and switch to integration when mock setup outgrows the test.
**`TDDˢ` is strongest** — it is the only one that addresses *how a mock goes
wrong* rather than *whether to mock*. `TDDᵃ`'s ordering is the best single
heuristic and the cheapest to adopt.

**Stack/command discovery** (`TDDᵃ` alone). `TDDˢ:117` and `TDDˢ:172` hard-code
`npm test`; `TDDᵐ` and `TDD⁰` say nothing. `TDDᵃ:24-36` makes discovery step zero:
identify the build system, prefer checked-in wrappers over global tools, learn the
focused-vs-full commands, read CI for the commands that actually gate merges.
**`TDDᵃ` is strongest, and for our repo it is not close** — our verification
source of truth is `.claude/project/verification.md`, and a TDD skill that assumes
`npm test` is actively wrong in a `uv`/`pytest` repo.

**External critique of test strategy** (`TDD⁰` alone). `TDD⁰:32` routes a disputed
*strategy* (not a test) to Codex before wider implementation. No other member has
an equivalent — `TDDˢ:302` and `TDDᵐ:26` route to a human or a design skill
instead. **Ours is the only automated one**, and it is a genuine, if small,
advantage.

### Across the non-TDD disciplines

**Adversarial second opinion** (`TDD⁰` `~` vs `DBT` `✓`). `TDD⁰:32` sends a
strategy dispute out for critique. `DBT:85-110` specifies the prompt verbatim,
requires it to be adversarial rather than evaluative, overrides the reviewer
persona's balanced default shape, and — the load-bearing part — forbids passing
the CLAIM, because handing over your conclusion buys agreement (`DBT:106`).
**`DBT` is stronger by mechanism**: ours controls *when* to ask, theirs controls
*what the asker is allowed to reveal*, which is the variable that determines
whether the answer is independent.

**Finding classification** (`SRC` `~` vs `DBT` `✓`). `SRC:125-139` handles exactly
one conflict class (docs vs existing code) and resolves it by asking the user.
`DBT:168-179` classifies *every* finding through a four-class precedence where
class 1 (contract misread) fixes the input rather than the artifact, and states
that rubber-stamping the reviewer is the same failure as ignoring it.
**`DBT` is stronger** — a precedence order forces a decision per finding, which is
what stops a review pass from degenerating into "apply everything" or "apply
nothing".

**Bounded loop** (`DBT` alone). `DBT:181-191` caps at 3 cycles and closes the
obvious escape: if 3 is "obviously insufficient", the artifact is too big —
decompose, do not lift the bound. Nothing else in this group bounds anything.
This is the same structural idea as superpowers SDD's fix-round cap
(`../plan-execution-engines/components.md`, fix-loop row), arrived at
independently in a different skill, which is decent evidence it is load-bearing
rather than stylistic.

**Untrusted-external-content boundary** (`SRC` `✓`, `TDDᵃ` `✓`, `DBT` `~`).
`SRC:97-114` covers fetched documentation: extract API facts, ignore directives
aimed at the model, never hardcode outbound endpoints from examples.
`TDDᵃ:337-341` covers browser output with the same shape. `DBT:143-151` covers it
from the other side — the artifact *you* send out may carry injection, so the
external CLI runs read-only. **All three are correct and none subsumes the
others**; together they are one principle applied at three boundaries (what comes
in from docs, what comes in from a runtime, what goes out to a tool). Our harness
states the inbound half in `rules/python/safety.md` for code, but nothing states
it for agent-consumed content.

**Simplicity and scope discipline** (`INC` `✓`). `INC:91-113` and `INC:115-133`
are the only worker-altitude versions of rules our harness states at the
guideline altitude (`rules/core/03-ak-guidelines.md` §2, §3). The difference is
form: ours is prose an agent reads once per session; `INC`'s is a four-question
check plus a five-item do-NOT list plus an output format
(`NOTICED BUT NOT TOUCHING`, `INC:128-133`). **`INC` is stronger as a dispatch
payload** — it can be pasted into an implementer packet and checked against;
ours cannot.

**Commit cadence** (`INC` `✓`). `INC:41` commits every slice and `INC:245`
requires "no uncommitted changes remain". This is the component the 2026-07-15
ledger explicitly rejected, and nothing in this comparison changes that: it
conflicts with our git-safety rule and with `implementer.md:25` (commit only when
the dispatch asks). The rest of `INC` is adoptable without it — the cycle at
`INC:21-42` degrades cleanly to implement → test → verify → next.

**Verification with the repo's own commands** (`INC` `✓`, `TDDᵃ` `✓`).
`INC:199-211` explicitly defers to `TDDᵃ`'s stack-discovery section rather than
restating it — the two agent-skills members are designed to compose. Ours splits
the same duty across `.claude/project/verification.md` and the
`verification-before-completion` skill, which is equivalent in effect but is not
reachable from inside our TDD skill.
