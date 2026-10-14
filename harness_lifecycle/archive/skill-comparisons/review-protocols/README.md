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

---

# Round 2 (2026-08-14) — request vs reception, after `receiving-code-review` was installed

**Why the set changed.** Round 1 (above) compared seven skills and closed with
the finding that "`receiving-code-review` has no installed counterpart in our
harness … the feedback-arrival moment is uncovered" (see Verdict). That gap has
since been closed: `.claude/skills/receiving-code-review/SKILL.md` was built on
2026-08-14 from superpowers' skill. The open question is therefore narrower and
different from round 1's: **where, if anywhere, does `requesting-code-review`
(REQ) land now that both the reception side and the production side exist here?**

**Round-2 set.** REQ (unchanged upstream, re-read in full: `SKILL.md` +
`code-reviewer.md`) · `REC-O` = ours `receiving-code-review` · `CR-O` = ours
`code-review` · `TE` = `.claude/skills/execution/references/task-engine.md`,
not a skill but the engine surface that owns the review gate and fix loop, read
here as a component owner.

**Citation drift notice.** Round 1's `CR-O` inventory was taken before the
`## Preflight — mechanical gates first` section existed
(`code-review/SKILL.md:24-32`); its `CR-O` line numbers now run ~2-15 lines low.
Round-2 sections below cite the current file. Round 1's text is preserved as
written — this notice is the correction, not an edit.

## Level 1 — Placement addendum

| Skill | Repo | Bucket | Triggers when |
|---|---|---|---|
| `requesting-code-review` | superpowers | 7 (also 10) | Unchanged from round 1 (`SKILL.md:14-22`). Re-judged against our engine: its mandatory moment "after each task in subagent-driven development" (`SKILL.md:15`) is fired **by the engine, not by a skill trigger**, at `task-engine.md:118-127`. |
| `receiving-code-review` | **ours** | 7 (proposed) | Feedback arrives **outside the execution engine's fix loop** — pasted PR comments, a human critique in chat, a spawned critic's findings — before agreeing with, implementing, or dismissing any item (`SKILL.md:3`). The out-of-loop scoping is enforced in the body, not just the description (`SKILL.md:15-21`). |
| `code-review` | **ours** | 7 (proposed) | Four dispatch shapes: `spec`, `quality`, `re-review`, `inline` (`SKILL.md:17-22`); inline explicitly covers a coordinator reviewing a diff before claiming completion (`SKILL.md:3`). |
| `task-engine.md` (reference, not a skill) | **ours** | n/a — engine surface | Not trigger-fired. Consulted by `execution` when a unit routes standard or deep (`task-engine.md:3-7`); from that point the engine *procedurally* packages, dispatches, routes and re-reviews without any review-request skill being invoked (`task-engine.md:118-160`). |

## Level 2 — Capability profiles (round-2 additions)

### `receiving-code-review` (ours — built 2026-08-14)

**Achieves** — makes an author process arriving feedback by verification and
per-item disposal instead of performative agreement, silent compliance, or
silent dropping.

**Can do**
- Names the failure it exists to prevent and the only three legal end-states
  per item — implemented with its own verification, answered with evidence, or
  asked about (`SKILL.md:8-13`).
- **Route-first clause**: explicitly cedes the in-engine case to the engine —
  findings relayed verbatim, ADDRESSED/NOT ADDRESSED re-review, disagreement
  deferred to the cap — and scopes itself to feedback arriving outside that
  loop (`SKILL.md:15-21`). This is the round-1 con ("several sections have no
  firing surface in our engine") fixed by scoping rather than by deletion.
- Five-step reception order READ → UNDERSTAND → VERIFY → RESPOND → IMPLEMENT,
  with the clarify-all-before-implementing-any gate kept (`SKILL.md:23-34`).
- Performative-agreement ban with the substitute behaviours named
  (`SKILL.md:36-42`).
- Trust-by-source split: human vs spawned critic/bot, with the
  conflicts-a-recorded-decision stop and the cannot-verify escape
  (`SKILL.md:44-56`).
- Two-way pushback: evidence-based pushback and no-apology-theatre retraction
  (`SKILL.md:58-62`).
- Red flags (4) and a rationalization table (4 rows) (`SKILL.md:64-79`).

**Pros vs REQ** — owns the entire "act on feedback" half of REQ
(`REQ/SKILL.md:42-46`, `:90-93`) at far higher resolution: REQ gives four
bullets and a three-line if-reviewer-wrong list; REC-O gives an ordering gate,
a source-trust split, an end-state contract, and armor. **Cons** — deliberately
says nothing about obtaining a review; an agent that never asks for one never
reaches this skill.

### `code-review` (ours) — round-2 delta only

Round 1's profile stands. Two changes matter for this decision:

- A **preflight** section now exists (`SKILL.md:24-32`): base resolves to a
  non-empty diff/package, and the mechanical gate from
  `.claude/project/verification.md` is green, checked *before* judgment effort;
  a red gate bounces the work back as failed verification rather than into a
  review round. This closes round 1's "no preflight ref check" con and removes
  one of the last things any reference in this family had over ours.
- Ad-hoc spec-source discovery now exists too (`SKILL.md:91-96`): workspace
  brief → bead → workstream plan → commit-named doc → ask the user, with
  "never reconstruct the requirements from the diff itself".

### `task-engine.md` review gate (ours) — the component owner REQ competes with

**Achieves** — turns "get this reviewed" from an agent decision into an
unskippable procedure with packaging, dual dispatch, verbatim relay, bounded
fix rounds and a terminal adjudication.

**Can do**
- Fires review per task without any trigger: package → dispatch spec-reviewer
  **then** code-reviewer → save both reports → both verdicts required
  (`task-engine.md:118-127`).
- Curated-context dispatch as a hard rule: paths not contents, never prior-task
  history, "everything pasted stays resident in your context"
  (`task-engine.md:82-84`), restated at `:210-219`.
- Commit-free diff scoping: `SCOPE_BASE` + `review-package.sh full|fix`, because
  implementers do not commit (`task-engine.md:54-69`).
- Verbatim relay with an explicit ban on pre-judging findings
  (`task-engine.md:129-131`).
- Severity routing: Minor → ledger deferred; plan-mandated → human; Spec ❌ /
  Critical / Important / confirmed ⚠️ → fix loop (`task-engine.md:132-135`).
- Bounded fix loop (5 rounds, round-consumption rule, model escalation at 4-5)
  (`task-engine.md:137-160`) and the **breaker** — adjudicate each open finding
  only at the cap, park with a ruling or STOP, every adjudication a ledger
  entry, silent discard forbidden (`task-engine.md:161-179`). The breaker
  explicitly delegates its per-finding method to REC-O's Verify and Respond
  steps (`task-engine.md:172-174`).
- Whole-scope final review incl. deferred/parked triage and Codex
  (`task-engine.md:181-198`).

**Pros vs REQ** — every REQ dispatch mechanic exists here in a stronger form,
and as procedure rather than as a trigger an agent can rationalize past.
**Cons** — it is engine-only: work classified `small` in `CLAUDE.md` ("execute
directly, then self-check") never enters it, so nothing procedural fires for
ad-hoc work.

## Round-2 verdict

**Ownership is the whole answer.** Of REQ's 22 catalogued components
(`components.md` § `REQ`), 18 are owned outright — 7 by `TE`, 10 by `CR-O`, 1 by
`REC-O` — and the 4 remainders are the optional trigger list, the rationalization
table, and two worked examples (see the round-2 matrix). Two sub-clauses inside
otherwise-owned rows are genuinely unowned; they are the entire adoptable
residue. Two components are not merely owned but
**contradicted**: REQ's `BASE_SHA`/`HEAD_SHA` capture (`REQ/SKILL.md:26-30`)
assumes commits exist, which our snapshot model deliberately denies
(`task-engine.md:54-60`); and REQ's rationalization row "I'll just review the
diff myself instead of dispatching a reviewer" (`REQ/SKILL.md:79`) forbids
exactly what our light path *mandates* — "read the diff … then apply the
code-review skill inline" (`task-engine.md:102-106`, and `CR-O/SKILL.md:21`'s
`inline` mode). Installing REQ verbatim would import a rule that fails our own
engine.

**On the merge tension (request + reception in one skill).** The argument
against merging is not that two moments feel awkward in one description; it is
that in *our* harness the two moments belong to **different agents**. In
superpowers the requester and the receiver are the same agent — its own step 3
"Act on feedback" (`REQ/SKILL.md:42-46`) is reception text living inside the
request skill, and superpowers still split the pair into two skills that
cross-reference. In ours the coordinator requests and relays but "never
implements or fixes findings itself" (`task-engine.md:11-13`), while the
implementer receives the findings and fixes them (`task-engine.md:143-147`). A
merged skill would fire for the coordinator and then mandate implementer
behaviour, or vice versa. REC-O's route-first clause (`SKILL.md:15-21`) is
precisely the seam that keeps that separation legible; a merge would erase it
and reintroduce the ambiguous-trigger defect the council already ruled against
in round 1 (`bucket-07.md:33-37`). So the two are one *loop* but not one
*role* — and skills bind roles.

**Engine-owned vs ad-hoc-only (the crux).** Engine-owned, therefore
un-adoptable: the mandatory per-task trigger, curated-context dispatch, the
subagent-dispatch step, base/head scoping, post-review severity routing, the
push-back-if-wrong path (`TE` breaker + `REC-O`). Ad-hoc-only, i.e. the only
territory REQ could legitimately claim: the optional trigger list (stuck /
pre-refactor baseline / after complex bug fix, `REQ/SKILL.md:19-22`) and
"before merge to main" for work that never entered the engine
(`REQ/SKILL.md:17`). That residue is a *cadence* question our `CLAUDE.md`
Working Mode already answers by decision ("small: 1-2 files … Execute directly,
then self-check"), and REQ's red flag "never skip review because it's simple"
(`REQ/SKILL.md:86`) directly contradicts that recorded decision. It is a
conflict to surface, not a gap to fill.

What genuinely is *not* covered anywhere in ours: REQ's **production-readiness
check area** — migration strategy when a schema changed, backward
compatibility, documentation completeness (`code-reviewer.md:63-67`) — and the
**`git worktree` escape hatch** that makes the read-only rule constructive
(`code-reviewer.md:33-35`, vs our bare prohibition at `CR-O/SKILL.md:51-52`).
Both are single-clause additions to `CR-O`'s quality checklist, not a skill.

## Recommendation

**(c) — absorb into `code-review`; reject the rest. Do not merge into
`receiving-code-review` (a), do not install as a separate skill (b), and do not
close it as fully covered (d).**

Reasoning: (b) fails because 18 of REQ's 22 components are already owned, and
its two dispatch-mechanic components are contradicted by our snapshot model and
light path — an installed REQ would be wrong on first use. (a) fails on the
role seam argued above: the requester (coordinator) and the receiver
(implementer) are different agents in this harness, and REC-O's route-first
clause exists to keep them apart. (d) overstates: two check-area clauses have no
home in ours today.

**Take (into `.claude/skills/code-review/SKILL.md` only):**

1. **Production-readiness checks** — migration strategy when a schema changed,
   backward compatibility, documentation completeness
   (`code-reviewer.md:63-67`) → append as one bullet to *Code quality review*
   (after the Structure bullet, `SKILL.md:110-114`). Nothing in `CR-O` covers migration or
   backward compatibility today.
2. **Read-only escape hatch** — "if you need a working copy of another
   revision, `git worktree add` into a temp dir; never move HEAD on this
   checkout" (`code-reviewer.md:33-35`) → append as a half-sentence to the
   read-only bullet (`SKILL.md:51-52`), turning a prohibition into a
   prohibition-plus-alternative.

**Reject (with reason):**

| REQ component | Reason |
|---|---|
| Mandatory/optional trigger schedule (`SKILL.md:14-22`) | Engine fires review procedurally (`task-engine.md:118-127`); ad-hoc cadence is decided by `CLAUDE.md` Working Mode. |
| "Never skip review because it's simple" (`SKILL.md:86`) | **Conflicts** with `CLAUDE.md` — `small` work self-checks by design. Surface, don't adopt. |
| BASE_SHA/HEAD_SHA capture (`SKILL.md:26-30`) | Contradicted by the commit-free snapshot model (`task-engine.md:54-69`). |
| `general-purpose` subagent + 4-placeholder template (`SKILL.md:32-40`) | Superseded by named spec-/code-reviewer dispatch with mode+brief+report+package (`task-engine.md:120-127`). |
| Curated-context rule + its rationalization row (`SKILL.md:8`, `:80`) | Owned as a hard rule (`task-engine.md:82-84`, `:210-219`; `rules/core/01-delegation.md`). |
| "Don't review the diff yourself" rationalization row (`SKILL.md:79`) | **Conflicts** with the light path's mandated inline review (`task-engine.md:102-106`) and `CR-O`'s `inline` mode. |
| Post-review severity policy (`SKILL.md:42-46`) | Owned, stronger: routing at `task-engine.md:132-135`, non-abandonment at `:177-179`. |
| If-reviewer-wrong protocol (`SKILL.md:90-93`) | Owned by `REC-O:58-62` and the breaker (`task-engine.md:161-175`). |
| Reviewer persona, context sections, five check areas (minus item 1 above), calibration, praise-first, plan-deviation flagging, output format, per-issue anatomy, verdict, DO/DON'T (`code-reviewer.md:11-125`) | Owned by `CR-O` in stronger, machine-checkable form (`SKILL.md:24-32`, `:34-63`, `:73-96`, `:98-139`, `:141-161`, `:176-207`). |
| Worked dispatch example + example reviewer output (`SKILL.md:48-73`, `code-reviewer.md:136-172`) | Context cost with no behaviour change; the dispatch example is built on the rejected SHA model. |

**Ledger note (not written here — comparison is not decision).** A subsequent
`harness-evaluate` pass should record `skill:skills/requesting-code-review` as
**adopted-partial** with `our_id: skill:skills/code-review`, reason citing this
folder and the two absorbed clauses.
