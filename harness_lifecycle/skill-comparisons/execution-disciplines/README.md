# Execution Disciplines

Disciplines that ride *inside* an engine's loop — they constrain how each unit of
work is done, but none of them owns the loop, selects the next unit, or decides
when the work is finished. Engines are compared in
`../plan-execution-engines/`; post-implementation passes in
`../post-implementation-passes/`.

Four of the seven are the same capability (`tdd`), which is where the cross-skill
matrix in [`components.md`](components.md) does the most work.

## Level 1 — Placement

| Skill | Repo | Bucket | Triggers when |
|---|---|---|---|
| `test-driven-development` | ours | 5 Testing & Runtime Validation (also 4) | **Selective**: a bug fix needing proof, a risky behaviour change, legacy needing characterization, or the plan/dispatch says `test-first` (`SKILL.md:3`, `SKILL.md:10-15`). Deliberately not a default posture — the description scopes it to "risky". |
| `test-driven-development` | superpowers | 5 (also 4) | **Universal**: "when implementing any feature or bugfix, before writing implementation code" (`SKILL.md:3`); the body escalates this to "Always: new features, bug fixes, refactoring, behavior changes" with only three exceptions, each requiring the human's permission (`SKILL.md:18-28`). Will fire on essentially every code change. |
| `test-driven-development` | agent-skills | 5 (also 4) | **Near-universal**: "implementing any logic, fixing any bug, or changing any behavior" (`SKILL.md:3`); excludes only config, docs, and static content (`SKILL.md:20`). |
| `tdd` | mattpocock | 5 (also 4) | **User-led**: fires when the user wants test-first work, says "red-green-refactor", or wants integration tests (`SKILL.md:3`). The description reads as a preference-matcher, not a risk-matcher — but the body's seam rule (`SKILL.md:22`) means it cannot actually start without a human confirming the seams, so its real firing condition is narrower than its description. |
| `source-driven-development` | agent-skills | 4 Implementation & Refactoring | Any time framework-specific code is about to be written from memory (`SKILL.md:19`); excluded for version-independent work (`SKILL.md:22-26`). |
| `doubt-driven-development` | agent-skills | 7 Review & Completion Assurance (also 10) | A **non-trivial** decision as defined by five tests — new branching, boundary crossing, an unverifiable property, correctness depending on invisible context, irreversible blast radius (`SKILL.md:16-29`). Explicitly not for mechanical edits or one-liners (`SKILL.md:31-40`). |
| `incremental-implementation` | agent-skills | 4 | Any multi-file change, or any time >~100 lines would be written before testing (`SKILL.md:3`, `SKILL.md:13-17`). |

**Where `incremental-implementation` belongs.** Its description and its rules
(Rule 0 simplicity, Rule 0.5 scope discipline, Rule 1 one-thing, Rule 2 keep it
compilable, Rules 3-5 flags/defaults/rollback, `SKILL.md:89-181`) are pure
discipline — constraints on how a unit is built. But its increment cycle
(`SKILL.md:21-42`) *does* select the next unit and *does* define completion
(`SKILL.md:237-245`), and its slicing strategies (`SKILL.md:44-87`) are plan
decomposition, which our `planning` skill already owns. **Call it a discipline**:
the loop it describes has no reviewer, no worker, no failure handling, and no
tracker — it cannot execute a plan, only pace one. The plan-decomposition half is
misplaced in it and belongs to planning, which is exactly what the ledger already
ruled for its sibling `planning-and-task-breakdown` (2026-08-12: vertical-slicing
articulation absorbed into planning; the whole-machine shape rejected).

**Prior ledger decisions on this set.**
- agent-skills `test-driven-development` — **adopted**, 2026-07-15,
  `our_id: skill:skills/test-driven-development`, reason: "covered by the local
  behavior-first RED-GREEN-REFACTOR loop, expected-failure confirmation, minimum
  passing change, and characterization tests."
- agent-skills `source-driven-development` — **adopted**, 2026-07-15,
  `our_id: agent:agents/docs-researcher`.
- agent-skills `doubt-driven-development` — **adopted**, 2026-07-15,
  `our_id: command:commands/codex-critique`.
- agent-skills `incremental-implementation` — **deferred**, 2026-07-15: "route
  only the thin vertical-slicing pattern into planning and subagent execution;
  reject the source workflow's mandatory per-slice commits."
- No ledger entry exists for superpowers or mattpocock TDD.

Two of those adoptions look thinner under this comparison than the ledger reason
claims — see the Verdict.

## Level 2 — Capability profiles

### `test-driven-development` (ours)

**Achieves** — a one-behaviour-at-a-time red/green loop applied where behaviour
risk is real, including characterization for legacy.

**Can do**
- Names four trigger conditions, all risk-based (`SKILL.md:10-15`).
- Seven-step loop: one behaviour → public-interface test → confirm it fails **for
  the expected reason** → smallest change → re-run → refactor only while green →
  repeat (`SKILL.md:19-25`).
- Bans batch-writing tests up front (`SKILL.md:29`).
- Accepts characterization tests for legacy code (`SKILL.md:31`).
- Routes a disputed test *strategy* to Codex critique before wider work
  (`SKILL.md:32`).

**Pros** — the only one of the four that treats TDD as risk-scaled rather than
universal, which is what makes it compatible with `phase-execution`'s
`standard`/`deep` split; the only one with a strategy-critique escape hatch
(`SKILL.md:32`). At 32 lines it costs nothing to keep loaded.

**Cons** — it has no test-quality content whatsoever. "Prefer behavior over
implementation detail" (`SKILL.md:30`) is the entire rubric. It cannot tell a
tautological test from a real one, has no mocking guidance, no anti-pattern list,
no rationalization table, and no verification checklist — so an agent following
it faithfully can still produce tests that pass by construction. Against the
other three this is the decisive weakness, and it is precisely what the
2026-07-15 "covered by" ruling did not check.

### `test-driven-development` (superpowers)

**Achieves** — enforces that no production code exists without a test that was
watched failing first, and that the resulting tests can actually fail.

**Can do**
- **The Iron Law** — no production code without a failing test; code written
  first must be *deleted*, not adapted or kept as reference (`SKILL.md:31-45`).
- Red-green-refactor as a state machine including the "wrong failure → back to
  RED" edge (`SKILL.md:49-69`).
- Good/Bad worked pairs for the test (`SKILL.md:75-106`) and for the minimal
  implementation (`SKILL.md:134-164`).
- Mandatory verify-RED with the three things to confirm, plus what a
  passing-immediately test means (`SKILL.md:113-128`).
- Mandatory verify-GREEN including "output pristine" (`SKILL.md:168-183`).
- Ten-row rationalization table where each Reality is an argument, not a scold
  (`SKILL.md:212-226`) and a 13-item red-flag list whose verdict is "delete code,
  start over" (`SKILL.md:228-244`).
- Eight-item verification checklist gated on "can't check all boxes? you skipped
  TDD" (`SKILL.md:283-296`).
- When-stuck table mapping four failure symptoms to design diagnoses
  (`SKILL.md:298-305`).
- `writing-good-tests.md`: two principles — name the break, exercise the real
  thing — each with an executable **gate function** (`writing-good-tests.md:66-79`,
  `writing-good-tests.md:137-148`); mirror-assertion and change-detector bans
  (`:32-46`); "behavior, not text" for scripts and agent docs (`:48-55`); mock
  level, complete mock structure, test-only methods out of production classes
  (`:99-132`); the **mutation check** (`:159-169`); a warning-signs list (`:186-199`).

**Pros** — strongest enforcement *and* strongest test-quality content in the set.
The mutation check (`writing-good-tests.md:159-169`) and the name-the-break gate
are the only mechanisms anywhere in this comparison that can catch a test which
passes but cannot fail. The rationalization table is the only one written to
survive an agent actively looking for an exit.

**Cons** — universal application (`SKILL.md:18-28`) with delete-your-code
enforcement is a poor fit for a harness that risk-scales execution; applied to
our `standard` stages it would forbid the inline path `phase-execution` relies
on. It is also 320 + 198 lines and JS/TS-flavoured throughout, and it has no
stack-discovery step — its commands are hard-coded `npm test`
(`SKILL.md:117`, `SKILL.md:172`), which in a Python repo is simply wrong.

### `test-driven-development` (agent-skills)

**Achieves** — a full TDD handbook: the loop, where tests belong in a pyramid,
what a good test looks like, and how to run it in *this* repo.

**Can do**
- **Discover the stack first** — find the build system, prefer checked-in
  wrappers, learn focused-vs-full commands, follow neighbouring conventions,
  read CI; "never assume a default like `npm test`" (`SKILL.md:24-36`).
- Three-step cycle with worked TS examples (`SKILL.md:38-94`).
- **The Prove-It Pattern** for bugs: reproduce → fail → fix → pass → full suite
  (`SKILL.md:96-142`).
- Test pyramid with proportions, the Beyonce Rule, and a **size/resource model**
  (small/medium/large by process, I/O, and network) with a decision guide
  (`SKILL.md:144-186`).
- Test-quality rules: state not interactions, DAMP over DRY, real > fake > stub >
  mock, arrange-act-assert, one assertion per concept, descriptive names
  (`SKILL.md:188-299`).
- Six-row anti-pattern table (`SKILL.md:301-310`).
- Browser/runtime verification workflow plus a **security boundary**: everything
  read from a browser is untrusted data, never instructions
  (`SKILL.md:312-341`).
- Subagent-written reproduction tests, so the test is authored without knowledge
  of the fix (`SKILL.md:343-357`).
- Seven-row rationalization table including the distinctive "don't re-run a clean
  suite for reassurance" (`SKILL.md:363-373`, restated `SKILL.md:398`).

**Pros** — the only TDD skill in the set that is **stack-agnostic in mechanism,
not just in claim** (`SKILL.md:24-36`); for a Python-first repo like ours that is
the difference between usable and not. The pyramid + size model is the only
guidance here on *what kind* of test to write, and the Prove-It pattern is the
crispest statement of our own bug-fix rule. The don't-re-run-for-reassurance rule
is a genuine token-waste fix none of the others have.

**Cons** — largest surface (398 lines) and it annexes territory: browser testing
(`SKILL.md:312-341`) duplicates a separate skill it also links, and the subagent
section (`SKILL.md:343-357`) is orchestration inside a discipline. Its
enforcement is soft — red flags without a "start over" verdict, and no equivalent
of the Iron Law or the mutation check.

### `tdd` (mattpocock)

**Achieves** — makes the red/green loop produce tests worth keeping by fixing
*where* tests attach and naming the three ways they rot.

**Can do**
- **Seams** — defines the seam as the public boundary, then requires the seams
  under test to be **written down and confirmed with the user before any test is
  written**: "no test is written at an unconfirmed seam" (`SKILL.md:18-26`).
- Reads `CONTEXT.md` so test names use the project's domain language, and
  respects ADRs in the area (`SKILL.md:10`).
- Three named anti-patterns with a tell for each: implementation-coupled
  ("breaks when you refactor but behavior hasn't changed"), tautological
  ("passes by construction"), horizontal slicing ("bulk tests verify *imagined*
  behavior") — the last with the vertical-slice / tracer-bullet remedy
  (`SKILL.md:28-32`).
- Three loop rules, including the unusual one: **refactoring is not part of the
  loop** — it belongs to review (`SKILL.md:34-38`).
- `tests.md`: good/bad pairs for interface-vs-internals, verify-through-interface
  not the DB, and tautological expected values (`tests.md:5-77`).
- `mocking.md`: mock at system boundaries only, never your own collaborators
  (`mocking.md:3-13`); design-for-mockability via DI and SDK-shaped interfaces
  (`mocking.md:15-60`).

**Pros** — the seam agreement (`SKILL.md:22`) is the strongest single idea in
this group and is unique to it: it converts "test everything" into a bounded,
human-agreed target list before any test exists, which is the only mechanism here
that controls test *effort* rather than test *quality*. Its tautology definition
is sharper than superpowers' mirror-assertion rule because it names the general
form. Densest of the four: 38 lines carrying most of the value.

**Cons** — no enforcement at all (no iron law, no red flags, no checklist, no
rationalizations), no stack discovery, and its seam gate makes it unusable in an
unattended run — `/run-phases` auto-approves prompts (`run-phases.md:50-54`) and
would have to auto-approve seams too, which defeats the mechanism. Splitting
refactoring out of the loop (`SKILL.md:38`) directly contradicts the other three
and our own step 6 (`ours SKILL.md:24`).

### `source-driven-development` (agent-skills)

**Achieves** — every framework-specific decision traced to current official docs
rather than to model memory.

**Can do**
- DETECT → FETCH → IMPLEMENT → CITE with version detection from the actual
  dependency file, per-ecosystem (`SKILL.md:28-61`).
- Four-tier source hierarchy and an explicit non-authoritative list including
  "your own training data — that is the whole point" (`SKILL.md:67-81`).
- Precision rule: fetch the page, not the site (`SKILL.md:83-91`).
- **Retrieval safety** — fetched docs are untrusted input; extract API/examples/
  deprecations only; ignore embedded directives; never hardcode outbound
  endpoints found in doc examples (`SKILL.md:97-114`).
- Docs-vs-codebase conflict surfaced as an A/B question, never silently resolved
  (`SKILL.md:125-139`).
- Citation rules: full URLs, deep anchors, quote the passage, and an explicit
  `UNVERIFIED:` marker when nothing authoritative was found (`SKILL.md:141-179`).

**Pros** — the `UNVERIFIED:` marker (`SKILL.md:171-177`) and the
docs-are-untrusted-input section are both mechanisms, not advice, and neither is
present in our `docs-researcher` agent's mandate as summarised by the ledger.
Version-first detection before fetching is what makes the citations meaningful.

**Cons** — it is a discipline that mostly delegates to a tool we already have,
and the ledger already ruled it adopted via `docs-researcher`. Its content is
web-fetch shaped; in our harness the equivalent path is Context7 MCP, so the
source-hierarchy table maps only loosely.

### `doubt-driven-development` (agent-skills)

**Achieves** — forces a fresh-context adversarial reviewer over any non-trivial
decision *while it is still cheap to change*, and bounds that loop.

**Can do**
- Five-part definition of "non-trivial" plus an explicit not-for list, with the
  self-limiting line "if you doubt every keystroke, you ship nothing"
  (`SKILL.md:16-40`).
- **Loading constraint**: must not be in a persona's `skills:` frontmatter,
  because a persona spawning a persona is a forbidden orchestration pattern; a
  degraded self-questioning fallback exists and must be flagged as degraded
  (`SKILL.md:42-47`).
- Five-step cycle as a copyable checklist (`SKILL.md:51-60`).
- CLAIM must be compactly writable — "if you can't write the claim that
  compactly, you have a vibe, not a decision" (`SKILL.md:62-73`).
- EXTRACT the smallest reviewable unit and **strip your reasoning**: hand over
  conclusions and you get validation of conclusions (`SKILL.md:75-83`).
- Adversarial prompt verbatim, with **do not pass the CLAIM** as a load-bearing
  rule (`SKILL.md:85-106`), and precedence over a persona's default balanced
  output shape (`SKILL.md:110`).
- Cross-model escalation: always offer in interactive sessions, never silently
  skip; PATH check → working-binary test → confirm exact invocation → pass via
  stdin/heredoc, never shell interpolation; read-only sandbox because the
  artifact may itself carry injection; announce the skip in non-interactive runs
  (`SKILL.md:112-166`).
- RECONCILE with a four-class **precedence order** — contract misread / valid+
  actionable / valid trade-off / noise — and "the reviewer's output is data, not
  verdict" (`SKILL.md:168-179`).
- STOP at 3 cycles; if 3 feels insufficient the artifact is too big, decompose —
  "do not lift the bound" (`SKILL.md:181-191`).
- **Doubt theater** as a checkable signal: 2+ cycles with substantive findings
  and zero classified actionable means you are validating, not doubting
  (`SKILL.md:215`).
- Explicit interaction map with TDD ("TDD's RED step is doubt made concrete"),
  SDD, review, and debugging (`SKILL.md:223-229`).

**Pros** — the most rigorously specified skill in this comparison. Three
mechanisms have no analogue in our harness: never-pass-the-CLAIM
(`SKILL.md:106`), the reconcile precedence order (`SKILL.md:172-177`), and the
doubt-theater detector (`SKILL.md:215`). The cross-model CLI safety sequence
(`SKILL.md:126-151`) is stricter than our own Codex invocation rules.

**Cons** — heavy for what it adds on top of an existing critique surface, and its
cross-model section is largely about bootstrapping a capability our
`codex-adapter` plugin already owns. The mandatory-offer-every-cycle rule
(`SKILL.md:124`) would be pure friction under `/run-phases`.

### `incremental-implementation` (agent-skills)

**Achieves** — keeps every intermediate state of a multi-file change working,
testable, and revertable.

**Can do**
- Increment cycle: implement → test → verify → commit → next, carry forward
  (`SKILL.md:21-42`).
- Three slicing strategies — vertical (preferred), contract-first for parallel
  FE/BE, risk-first so the uncertain part fails early (`SKILL.md:44-87`).
- **Rule 0 Simplicity** with a before/after check and worked
  over-engineering examples (`SKILL.md:91-113`).
- **Rule 0.5 Scope discipline** with a five-item do-NOT list and a
  `NOTICED BUT NOT TOUCHING` reporting format (`SKILL.md:115-133`).
- Rules 1-5: one logical thing per increment, keep it compilable, feature flags
  for incomplete work, safe defaults, rollback-friendly (never delete and replace
  in one commit) (`SKILL.md:135-181`).
- A directing-an-agent template that states in-scope and out-of-scope explicitly
  (`SKILL.md:183-197`).
- Per-increment checklist run with **the repository's own commands**, deferring
  to the TDD skill's stack-discovery section (`SKILL.md:199-211`).
- Don't-re-run-for-reassurance rule (`SKILL.md:211`, `SKILL.md:222`).

**Pros** — Rules 0 and 0.5 are the sharpest statement of scope and simplicity
discipline in this whole comparison, and they are *worker-facing* — exactly the
altitude our `implementer.md` operates at. The `NOTICED BUT NOT TOUCHING` format
(`SKILL.md:128-133`) is a concrete mechanism for the "mention it, don't fix it"
rule our AK guidelines state as prose.

**Cons** — mandatory per-slice commits (`SKILL.md:41`, checklist
`SKILL.md:209`, verification `SKILL.md:245` "no uncommitted changes remain")
collide head-on with our conservative-git rule; the ledger already rejected
exactly this in 2026-07-15. Its slicing strategies belong to planning, not to
execution. And its content substantially duplicates our `ak-guide`
(simplicity-first, surgical changes) — which is the ledger's stated coverage for
`code-simplification` too.

## Verdict

**The TDD four are genuine substitutes, and none dominates.** They divide along
two axes that the family label hides:

- *Enforcement* — superpowers is far ahead (Iron Law, delete-and-restart,
  checklist gate). agent-skills and ours are advisory. mattpocock has none.
- *Test quality* — superpowers' `writing-good-tests.md` and mattpocock's
  tautology/seam framing lead; agent-skills is broad but softer; **ours has
  effectively none**.
- *Portability* — agent-skills is the only one that discovers the stack;
  superpowers hard-codes `npm test`; mattpocock is TS-flavoured; ours is
  language-neutral by being silent.
- *Effort control* — only mattpocock's pre-agreed seams bound how much testing
  happens; the other three imply "test everything that changed".

The 2026-07-15 ledger reason for adopting agent-skills TDD into ours — "covered
by the local behavior-first RED-GREEN-REFACTOR loop, expected-failure
confirmation, minimum passing change, and characterization tests" — is accurate
about the *loop* and wrong about the *rest*. Our 32-line skill has no counterpart
to stack discovery (`agent-skills:24-36`), the pyramid/size model
(`:144-186`), the Prove-It pattern (`:96-142`), the anti-pattern table
(`:301-310`), or any of `writing-good-tests.md`. That is the single largest
substantive gap this comparison found, and it is the one worth re-opening.

**Substitutes vs complements.** Within TDD: substitutes, adopt-one. Across the
rest: complements, and they stack cleanly on an engine —
`source-driven-development` constrains what you write (facts), TDD constrains
what proves it (behaviour), `incremental-implementation` constrains how much you
write at once (size), `doubt-driven-development` constrains what stands
(reasoning). `doubt-driven` says so itself (`SKILL.md:223-229`), and its claim
that "TDD's RED step is doubt made concrete" is the correct relation: for
behavioural claims TDD *is* the doubt step, so the two do not both need to fire.

**Strongest for what.** For enforcement under an agent that will rationalize:
superpowers TDD. For a polyglot repo and for knowing which *kind* of test to
write: agent-skills TDD. For bounding testing effort and for naming why a test is
worthless: mattpocock. For risk-scaled application inside a phase-based engine:
ours — but only because of what it *doesn't* demand, not because of what it
teaches.

For the non-TDD three, ours has real coverage in two cases and a real gap in one:
`source-driven-development` is genuinely covered by `docs-researcher` in
mechanism, though the `UNVERIFIED:` marker and the fetched-docs-are-untrusted
rule are not; `doubt-driven-development` is *partially* covered by
`/codex-critique` — we have the fresh-context adversarial reviewer, but not the
CLAIM-withholding rule, the reconcile precedence, the 3-cycle bound, or the
doubt-theater check, all of which are the parts that make it not-theatre;
`incremental-implementation` remains correctly deferred, but Rules 0/0.5 are
worker-altitude content our `implementer.md` visibly lacks (compare
`implementer.md:15` and `implementer.md:20-21`, two sentences, against
`incremental-implementation:91-133`).

Level 3 component inventory and the cross-skill matrix: [`components.md`](components.md).
