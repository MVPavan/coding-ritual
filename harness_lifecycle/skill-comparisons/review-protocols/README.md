# Review Protocols

Bucket 7 — Review & Completion Assurance (`inventory/skill-buckets.md:130-141`).
Seven skills, three sub-families that are **not** substitutes for each other:

- **Code-review rubric & dispatch** — superpowers `requesting-code-review`,
  mattpocock `code-review`, agent-skills `code-review-and-quality`, and our
  installed `code-review` (the wave-1 skill, the prospective merge target).
- **Feedback reception** — superpowers `receiving-code-review`: the moment
  review findings *arrive at* the author, not the moment they are produced.
- **Completion gate** — superpowers `verification-before-completion` and our
  installed counterpart of the same name: the moment before saying "done".

The taxonomy already encodes this: `code-review-and-quality`[A] and
`code-review`[M] are **substitutes** (`skill-buckets.md:237`), while
`receiving-code-review` + `requesting-code-review` form a **complements**
family — two halves of one protocol (`skill-buckets.md:244`).

Sibling comparisons: `../plan-execution-engines/` (the engine that dispatches
these reviews), `../execution-disciplines/` (in-loop TDD/debugging),
`../post-implementation-passes/` (simplification/security passes).

## Level 1 — Placement

| Skill | Repo | Bucket | Triggers when |
|---|---|---|---|
| `requesting-code-review` | superpowers | 7 (also 10) | Mandatory after each task in subagent-driven development, after a major feature, before merge; optional when stuck, before refactoring, after a complex bug fix (`SKILL.md:14-22`). **Misfire risk:** the description ("Use when completing tasks … to verify work meets requirements", `SKILL.md:3`) reads like a verification skill and collides with `verification-before-completion`'s moment; the body is actually a *dispatch* flow. |
| `receiving-code-review` | superpowers | 7 | Review feedback arrives from any source, before implementing any of it — especially when unclear or technically questionable (`SKILL.md:3`). Fires on the author side, not the reviewer side. |
| `verification-before-completion` | superpowers | 7 (also 5) | About to claim complete/fixed/passing, before committing or creating PRs — including paraphrases and any expression of satisfaction (`SKILL.md:3`, `SKILL.md:106-121`). |
| `code-review` | mattpocock | 7 | User asks to review a branch/PR/WIP "since X"; the fixed point comes from the user, and the skill asks for one if unspecified (`SKILL.md:3`, `SKILL.md:19`). User-invoked shape: a review the human requests, not a gate an engine fires. |
| `code-review-and-quality` | agent-skills | 7 | "Before merging any change. … reviewing code written by yourself, another agent, or a human" (`SKILL.md:3`, `:14-20`). **Misfire risk:** fires on everything that merges; large parts of the body (review-speed SLAs `SKILL.md:249-257`, PR-splitting for human reviewers `SKILL.md:117-124`) presuppose a human team and cannot bind an agent-only flow. |
| `code-review` | **ours** | 7 (proposed — ours are outside the reference taxonomy) | Three engine-fired shapes: dispatched as spec- or quality-reviewer, dispatched for a re-review round of a fix, or applied inline by the coordinator before claiming completion (`SKILL.md:3`, `SKILL.md:13-22`). Mounted by the execution skill's task engine and by both reviewer agents. |
| `verification-before-completion` | **ours** | 7 (proposed) | Before claiming a change is complete, fixed, or ready (`SKILL.md:3`). Invoked explicitly by execution at phase exit and task completion (`execution/SKILL.md:93-94`, `:114-116`). |

**Prior decisions on compared skills.**

- `skill:skills/code-review-and-quality` — **adopted** 2026-07-15,
  `our_id: agent:agents/code-reviewer`, reason: "Covered by our spec and code
  reviewers plus adversarial Codex review …" (`ledger.json:197-206`). **Stale
  in two ways:** it predates the wave-1 `code-review` skill — the agents it
  points at are now lean shells whose entire body is "read
  `.claude/skills/code-review/SKILL.md` and follow it"
  (`agents/code-reviewer.md:11-13`, `agents/spec-reviewer.md:11-13`) — and its
  `source_content_hash` was taken at `source_sha 6bcfeb9`, before upstream's
  current text (dependency discipline, structural remedies, presumptive
  blockers) landed.
- `skill:skills/doubt-driven-development` — **adopted** 2026-08-12,
  `our_id: command:commands/use-codex` (`ledger.json:253-260`): the bucket's
  adversarial-scrutiny member was resolved in wave 2 into use-codex's
  *Critique discipline* section (`use-codex.md:67-81`) — pass-the-artifact-
  never-your-conclusion, four-class finding classification, the 3-cycle bound,
  the doubt-theater detector. It is out of scope here and cited only where the
  references' multi-model material overlaps it.
- `command:commands/review` (agent-skills) — **rejected** 2026-07-15 as a
  redundant launcher (`ledger.json:63-69`).
- **Council round-001 ruling** (`casebook/views/bucket-07.md`):
  `code-review-and-quality` chosen as merge base for its multi-axis rubric,
  absorbing mattpocock's never-rerank rule + smell baseline and
  `requesting-code-review`'s dispatch flow + reviewer template
  (`bucket-07.md:9-23`, `:47-57`); `receiving-code-review` kept standalone —
  folding it in would create the ambiguous three-mode trigger defect
  (`bucket-07.md:33-37`); `verification-before-completion` adopted as the only
  pre-claim gate (`bucket-07.md:39-43`). **This ruling PREDATES our wave-1
  `code-review` skill.** The "base" it designated was never installed as such;
  what exists today is our own skill, already mounted into the execution
  engine and both reviewer agents. The live question is therefore what to
  absorb *into ours*, not which reference to install.

## Level 2 — Capability profiles

### `requesting-code-review` (superpowers)

**Achieves** — gets completed work reviewed by a fresh subagent with curated
context before the coordinator builds on it.

**Can do**
- Trigger schedule: three mandatory and three optional review moments
  (`SKILL.md:14-22`).
- Dispatch mechanics: capture `BASE_SHA`/`HEAD_SHA`, fill a four-placeholder
  template, send to a `general-purpose` subagent (`SKILL.md:26-40`).
- Context rule: the reviewer gets "precisely crafted context … never your
  session's history" (`SKILL.md:8`), defended by a rationalization table
  (`SKILL.md:75-80`).
- A complete reviewer prompt asset: persona, read-only clause with a
  worktree escape hatch, five check areas, calibration incl. praise-first,
  Strengths/Critical/Important/Minor output, ready-to-merge verdict, DO/DON'T
  list, worked example (`code-reviewer.md:11-172`).
- Post-review policy: fix Critical immediately, Important before proceeding,
  note Minor, push back with reasoning if the reviewer is wrong
  (`SKILL.md:42-46`, `:90-93`).

**Pros** — the only reference that treats dispatch as the unit of design: its
context rule and coordinator-context rationalizations (`SKILL.md:75-80`) are
the seed our task engine's "paths, not contents" rule grew from
(`execution/references/task-engine.md:82-84`). Its template's calibration
lines (severity honesty, praise-first at `code-reviewer.md:69-74`) survive
almost verbatim in our skill (`SKILL.md:106-120`) — evidence the lineage is
real, not parallel invention.

**Cons** — single-axis: plan alignment is one section inside one blended
review (`code-reviewer.md:38-42`), so a spec verdict can be masked by quality
findings — the exact failure mattpocock's two-axis split and our
spec-before-quality rule exist to prevent. No re-review mode: after fixes it
just continues (`SKILL.md:71-72`). Assumes commits exist (`SKILL.md:27-30`),
which our conservative-git snapshot model deliberately does not
(`task-engine.md:56-60`).

### `receiving-code-review` (superpowers)

**Achieves** — makes the author process arriving review feedback by technical
verification instead of performative agreement or blind implementation.

**Can do**
- Six-step reception pattern: READ → UNDERSTAND → VERIFY → EVALUATE → RESPOND
  → IMPLEMENT (`SKILL.md:16-23`).
- Performative-agreement ban with verbatim forbidden phrases and replacement
  behaviours (`SKILL.md:29-38`, `:133-148`).
- Clarify-all-before-implementing-any gate: partial understanding of a
  multi-item review blocks *all* implementation (`SKILL.md:42-57`).
- Source-trust differentiation: human partner (trusted, still no
  performative agreement) vs external reviewer (five-check verification,
  can't-verify escape, stop-and-discuss on conflicts with prior decisions)
  (`SKILL.md:61-84`).
- YAGNI grep-check before "implementing properly" (`SKILL.md:90-96`).
- Ordered implementation: blocking → simple → complex, test each individually
  (`SKILL.md:102-111`).
- Pushback protocol both ways: when/how to push back (`SKILL.md:113-129`) and
  how to retract a wrong pushback without apology theatre (`SKILL.md:152-162`).
- GitHub thread-reply mechanics (`SKILL.md:203-205`).

**Pros** — covers a moment nothing else in this set touches: every other
skill here *produces or gates* verdicts; this one governs *consuming* them.
The clarify-all gate (`SKILL.md:42-48`) is a concrete ordering mechanism, not
a vibe. The council's keep-standalone reasoning holds (`bucket-07.md:33-37`).

**Cons** — built for human-authored feedback arriving in conversation; in our
engine the coordinator relays reviewer findings *verbatim* to a fix
dispatch (`task-engine.md:126-128`, `:143-144`), so several sections
(gratitude ban, GitHub replies) have no current firing surface. Its
"your human partner" trust rules partially conflict with our loop's
adjudicate-only-at-the-cap rule (`task-engine.md:171-172`): ours forbids the
implementer-side evaluation this skill mandates, *until the cap*.

### `verification-before-completion` (superpowers)

**Achieves** — blocks any success claim that is not backed by a fresh,
fully-read verification run in the same message.

**Can do**
- Iron Law + spirit-over-letter clause (`SKILL.md:12-20`).
- Five-step gate function ending "Skip any step = lying, not verifying"
  (`SKILL.md:24-36`).
- Claim → required-evidence table, 7 rows — incl. "Agent completed" requires
  a VCS diff, "Requirements met" requires a line-by-line checklist
  (`SKILL.md:40-48`).
- Red-flag list covering hedge words and satisfaction expressions
  (`SKILL.md:50-59`); 8-row rationalization table (`SKILL.md:61-72`).
- Key patterns with the red-green regression proof: revert the fix, the test
  MUST fail, restore, re-run (`SKILL.md:82-86`).
- Paraphrase closure: the rule applies to synonyms and implications of
  success, not just exact phrases (`SKILL.md:116-121`).

**Pros** — the strongest discipline armor in the set: rationalization table,
red flags, and paraphrase closure are exactly the pressure-tested form the
superpowers eval culture produces. The claim→evidence table turns an
abstract rule into per-claim mechanics; nothing in our harness has an
equivalent table.

**Cons** — generic by design: no hook to a repo's own verification
commands. Its agent-delegation row (`SKILL.md:47`, `:100-104`) overlaps what
our code-review skill does more precisely on the reviewer side
(do-not-trust-the-report, `code-review/SKILL.md:52-56`).

### `code-review` (mattpocock)

**Achieves** — reviews a diff since a user-supplied fixed point along two
deliberately unmerged axes — repo standards and spec fidelity — via parallel
sub-agents.

**Can do**
- Two-axis architecture with an explicit anti-masking rationale
  (`SKILL.md:6-11`, `:80-87`) and a never-merge/never-rerank aggregation rule
  (`SKILL.md:74-78`).
- Fail-fast preflight: `git rev-parse` the fixed point and confirm a
  non-empty diff *before* spawning sub-agents (`SKILL.md:23`).
- Three-dot merge-base diff + commit list captured once (`SKILL.md:21`).
- Spec-source discovery ladder: commit-message issue refs → user-supplied
  path → `docs/`/`specs/`/`.scratch/` match → ask; skip-and-report if none
  (`SKILL.md:25-32`).
- A 12-smell Fowler baseline, each *what it is* → *how to fix*
  (`SKILL.md:45-56`), bound by two rules: the repo's documented standard
  overrides the baseline, and smells are always labelled judgement calls;
  skip anything tooling enforces (`SKILL.md:40-41`).
- Sub-agent briefs with a 400-word output cap each (`SKILL.md:60-70`); the
  smell baseline is pasted in full because the sub-agent has no other access
  to it (`SKILL.md:63`).

**Pros** — the axis separation is the same insight our skill enforces as
"the two verdicts never blend" (`ours/SKILL.md:11-12`), but mattpocock adds
two mechanisms ours lacks: the preflight that fails a bad ref *before*
burning two dispatches (`SKILL.md:23`), and a *named* smell vocabulary with a
portability mechanism (paste-in-full) and an override rule — our quality
section describes defect classes but names no smells
(`ours/SKILL.md:76-104`). The spec-discovery ladder covers the ad-hoc case
our skill delegates entirely to the dispatch inputs.

**Cons** — no severity taxonomy at all (findings are only "hard violation"
vs "judgement call", `SKILL.md:64`), no verdict vocabulary, no re-review
mode, no evidence discipline for the sub-agents (nothing stops them crawling
the repo), and a hard dependency on their harness's issue-tracker doc
(`SKILL.md:13`). The council absorbed its two distinctive rules and rejected
the rest (`bucket-07.md:47-51`); this profile confirms there are exactly two
more mechanisms worth arguing over (preflight, discovery ladder).

### `code-review-and-quality` (agent-skills)

**Achieves** — a full human-team code-review handbook: five-axis rubric,
severity labels, change sizing, dependency review, and reviewer conduct.

**Can do**
- Approval philosophy: approve when the change definitely improves code
  health, even if imperfect (`SKILL.md:12`).
- Five-axis rubric — correctness, readability/simplicity, architecture,
  security, performance (`SKILL.md:22-87`) — with structural-smell teeth:
  bolted-on conditionals as design smells (`SKILL.md:48-49`), the
  complexity-relocated-vs-reduced concept-count test (`SKILL.md:60`),
  feature logic leaking into shared modules (`SKILL.md:61`).
- Structural remedies: eight named restructurings — propose the move, not
  just the problem (`SKILL.md:88-101`).
- Change sizing thresholds + four splitting strategies + the file-size watch
  (~1000 total lines as an inspection signal) (`SKILL.md:103-128`).
- Change-description standards with anti-patterns (`SKILL.md:130-138`).
- Five-step process, reviewing tests before implementation
  (`SKILL.md:140-175`).
- Five-label severity taxonomy (no-prefix Required / Critical / Nit /
  Optional / FYI) plus the lead-with-what-matters ordering rule: "If you have
  one structural problem and ten nits, the structural problem *is* the
  review" (`SKILL.md:177-191`).
- Verify-the-verification: audit the author's verification story
  (`SKILL.md:193-203`).
- Multi-model review pattern (`SKILL.md:205-229`); dead-code
  ask-before-delete (`SKILL.md:231-247`); disagreement hierarchy
  (`SKILL.md:258-267`); honesty/anti-sycophancy rules (`SKILL.md:269-277`).
- Dependency discipline: five pre-add checks and a five-rule upgrade
  workflow (changelog over version number, one dependency per change, tests
  decide, transitive/lockfile review) (`SKILL.md:279-300`).
- Copyable checklist (`SKILL.md:302-348`), 9-row rationalization table
  (`SKILL.md:354-366`), 14 red flags (`SKILL.md:368-383`), post-review
  verification incl. presumptive blockers (`SKILL.md:385-396`).

**Pros** — the widest rubric and the only member with: an approval
*philosophy*, change sizing, change-description standards, dependency
review, and the lead-with-what-matters rule. Its structural-remedy catalog
gives reviewers a vocabulary of *moves* where ours only requires "fix if not
obvious" (`ours/SKILL.md:156`). Several of its blind spots in the 2026-07-15
ledger reason are now covered upstream — the entry's hash predates this text.

**Cons** — it is a handbook, not a protocol: nothing binds *which* sections
apply to *which* dispatch (contrast our mode table, `ours/SKILL.md:13-22`),
there is no evidence discipline, no do-not-trust-the-report, no re-review
mode, and whole sections (review-speed SLAs `SKILL.md:249-257`,
human-reviewer PR splitting) target human teams. Its security axis
(`SKILL.md:64-75`) duplicates what our skill routes to the security skill
(`ours/SKILL.md:91-94`), and its sibling-reference dependencies
(`SKILL.md:349-352`) would have to come with it.

### `code-review` (ours — wave-1, merge target)

**Achieves** — one review protocol serving four dispatch modes, with
evidence discipline, spec-before-quality separation, calibrated severity,
and a re-review contract that closes the execution engine's fix loop.

**Can do**
- Mode table binding sections and inputs per dispatch: `spec` / `quality` /
  `re-review` / `inline` (`SKILL.md:13-22`).
- Evidence discipline: the diff package is read once and *is* the changed
  files; no codebase crawling except one focused check per named risk; no
  suite re-runs to confirm the implementer's report; read-only; `file:line`
  on every finding and every bare-yes check (`SKILL.md:26-48`).
- Do-not-trust-the-report, incl. "a stated rationale never downgrades a
  finding's severity" (`SKILL.md:50-56`).
- Spec axes Missing / Extra / Misunderstood + invariant commands +
  file-scope compliance (`SKILL.md:60-69`); the ⚠️ Cannot-verify-from-diff
  escalation channel (`SKILL.md:71-74`).
- Quality review with the edited-existing-tests-means-behaviour-change flag
  (`SKILL.md:81-84`), a trust-boundary lens that mounts the security skill
  (`SKILL.md:91-94`), and Python-first checks (`SKILL.md:95-100`).
- Severity calibration that *defines* Important ("the change cannot be
  trusted until fixed") and demotes coverage-breadth wishes to Minor
  (`SKILL.md:106-112`); the plan-mandated rule — the plan's authorship does
  not grade its own work (`SKILL.md:114-117`).
- Re-review mode: scope = findings list + fix diff; ADDRESSED / NOT
  ADDRESSED per finding with evidence; "attempted" is not addressed;
  out-of-scope observations are non-blocking (`SKILL.md:122-133`).
- Three machine-checkable output contracts, no preamble (`SKILL.md:134-167`).

**Pros** — the only member whose contracts are *load-bearing*: the execution
engine dispatches by its mode names (`task-engine.md:14-17`, `:121-127`),
consumes its verdict vocabulary to route the fix loop
(`task-engine.md:129-135`), and its re-review contract is what makes a
bounded five-round loop adjudicable (`task-engine.md:137-158`). Its evidence
discipline is unique in the set — no reference bounds what a reviewer may
*read or run*. Severity is calibrated by definition, not just labelled.

**Cons** — versus CRQ it has no approval philosophy, no change sizing, no
change-description or dependency-review checks, no structural-remedy
vocabulary, no lead-with-what-matters ordering, no rationalization/red-flag
armor, and no review-tests-first ordering. Versus CR-M it has no named smell
baseline, no preflight ref check (a bad SCOPE_BASE would surface only inside
a dispatched reviewer), and no spec-source discovery for inline/ad-hoc use —
inline mode assumes the workspace ledger exists (`SKILL.md:22`). Versus REQ
it carries no worked example of a finished report.

### `verification-before-completion` (ours — wave-1)

**Achieves** — makes the completion claim wait for the repo's own
verification commands, run fresh.

**Can do**
- Five-step workflow ending with `git status` before presenting completion
  (`SKILL.md:9-15`) — a step VBC-S lacks as an explicit gate.
- Pins the source of truth to `.claude/project/verification.md` and
  `invariants.md` (`SKILL.md:18`) — repo-specific, where VBC-S is generic.
- One-line trust rule: no memory, confidence, partial checks, or agent
  reports (`SKILL.md:20`).
- Invoked at named engine moments: phase exit gate and task completion
  (`execution/SKILL.md:93-94`, `:114-116`).

**Pros** — correctly repo-anchored and cheap to load (21 lines); it is the
skill-shaped mount of CLAUDE.md's Verification section (`CLAUDE.md:63-71`),
so the rule and the skill cannot drift apart without being noticed.

**Cons** — it is a pointer, not a discipline skill: no claim→evidence
table, no red-green regression proof, no red flags, no rationalization
table, no paraphrase closure, and its agent-report rule names no mechanism
(VBC-S says *check the VCS diff*, `VBC-S/SKILL.md:47`). Under pressure —
the exact condition VBC-S is armored for — a one-line "do not rely on"
gives an agent nothing to push back with.

## Verdict

**Overlap map.** Within the rubric sub-family, CRQ[A], CR-M[M], REQ[S], and
ours are substitutes for the same moment — the taxonomy already says so for
the two references (`skill-buckets.md:237`) and the council treated all
three as one merge (`bucket-07.md:9-23`). `receiving-code-review` and both
`verification-before-completion` skills are **complements** to that family
(different moments: feedback arrival, pre-claim), and the two VBC skills are
substitutes for each other. The council's round-001 ruling — CRQ as base,
absorbing mattpocock's two rules and REQ's dispatch flow — **predates our
wave-1 `code-review` skill**; its base designation is superseded by the
installed reality: ours is the skill both reviewer agents load wholesale
(`agents/code-reviewer.md:11-13`, `agents/spec-reviewer.md:11-13`) and the
task engine's review gate, fix loop, and final review are all written
against its modes and verdicts (`task-engine.md:120-135`, `:150-158`,
`:180-195`). Any merge therefore lands *into ours*, and must preserve: the
four mode names and their input contracts, the diff-package evidence
discipline (`review-package.sh` is built to feed it,
`task-engine.md:61-69`), the severity vocabulary the loop routes on, and
the re-review ADDRESSED/NOT-ADDRESSED contract. The bucket's fourth member,
`doubt-driven-development`, already resolved into use-codex's critique
discipline (`ledger.json:253-260`, `use-codex.md:67-81`) — CRQ's
multi-model pattern (`CRQ/SKILL.md:205-229`) is the same capability and
needs no second home. As evidence, not rulings: what ours **lacks** is
CRQ's judgment layer (approval philosophy, change sizing, structural
remedies, lead-with-what-matters, dependency discipline, discipline armor),
CR-M's two remaining mechanisms (fail-fast preflight, spec-source
discovery ladder — its smell baseline is the one *catalog* absent from
ours), REQ's ad-hoc trigger schedule and worked example, and VBC-S's entire
armor kit for our thin VBC (claim→evidence table, red-green proof,
paraphrase closure). What ours uniquely **has** — found in no reference —
is the mode system, the evidence budget, do-not-trust-the-report with the
rationale-never-downgrades rule, the plan-mandated severity rule, the
cannot-verify-from-diff channel, the edited-tests flag, the security-skill
lens, and the re-review contract. Finally, verified explicitly:
**`receiving-code-review` has no installed counterpart in our harness** — a
listing of `.claude/skills/` plus a grep across skills, agents, rules, and
commands for reception/performative-agreement/feedback-arrival protocol
found nothing (our `code-review` skill's feedback language is the
reviewer's side, `ours/SKILL.md:119-120`); the feedback-arrival moment is
uncovered. Adopt/reject/absorb decisions go through `harness-evaluate` and
the ledger, citing this folder.

Level 3 inventory and matrix: [`components.md`](components.md).
