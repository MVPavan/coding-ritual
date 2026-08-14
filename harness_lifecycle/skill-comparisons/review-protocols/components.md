# Review Protocols — Level 3 Components

Column keys:

| Key | Skill |
|---|---|
| `REQ` | superpowers — `skills/requesting-code-review/` (SKILL.md + code-reviewer.md) |
| `REC` | superpowers — `skills/receiving-code-review/SKILL.md` |
| `VBC-S` | superpowers — `skills/verification-before-completion/SKILL.md` |
| `CR-M` | mattpocock_skills — `skills/engineering/code-review/SKILL.md` (agents/openai.yaml excluded per scope) |
| `CRQ` | agent-skills — `skills/code-review-and-quality/SKILL.md` |
| `CR-O` | **ours** — `.claude/skills/code-review/SKILL.md` |
| `VBC-O` | **ours** — `.claude/skills/verification-before-completion/SKILL.md` |

Citations are relative to each skill's directory unless prefixed.

## Component inventory

### `REQ` — requesting-code-review

| Component | Citation |
|---|---|
| Core principle: review early, review often | `SKILL.md:10` |
| Curated-context rule: reviewer never gets session history | `SKILL.md:8` |
| Mandatory triggers: after each task in subagent-driven development, after major feature, before merge | `SKILL.md:14-17` |
| Optional triggers: stuck / pre-refactor baseline / after complex bug fix | `SKILL.md:19-22` |
| BASE_SHA/HEAD_SHA capture step | `SKILL.md:26-30` |
| Dispatch a `general-purpose` subagent, fill the template, 4 placeholders | `SKILL.md:32-40` |
| Post-review policy: Critical immediately, Important before proceeding, Minor noted, push back if wrong | `SKILL.md:42-46` |
| Worked dispatch example with returned findings | `SKILL.md:48-73` |
| Rationalization table (2 rows): don't review inline as coordinator; don't hand over session history | `SKILL.md:75-80` |
| Red flags: never skip because "simple", never ignore Critical, never proceed with unfixed Important | `SKILL.md:85-89` |
| If-reviewer-wrong protocol: technical reasoning, show code/tests, request clarification | `SKILL.md:90-93` |
| Reviewer persona (Senior Code Reviewer, review-before-cascade purpose) | `code-reviewer.md:11-13` |
| Template context sections: what was implemented / requirements / git range + diff commands | `code-reviewer.md:15-31` |
| Read-only review clause with `git worktree` escape hatch for other revisions | `code-reviewer.md:33-35` |
| Five check areas: plan alignment / code quality / architecture / testing / production readiness | `code-reviewer.md:37-67` |
| Calibration: severity honesty ("Not everything is Critical") + praise-first-for-trust | `code-reviewer.md:69-74` |
| Flag plan deviations specifically; report issues with the plan itself | `code-reviewer.md:76-78` |
| Output format: Strengths / Critical / Important / Minor / Recommendations / Assessment | `code-reviewer.md:80-109` |
| Per-issue anatomy: file:line, what, why, how to fix | `code-reviewer.md:96-100` |
| Ready-to-merge verdict (Yes / No / With fixes) + reasoning | `code-reviewer.md:105-109` |
| DO/DON'T rules: no "looks good" without checking, no nitpicks-as-Critical, no feedback on unread code, no vagueness, always a clear verdict | `code-reviewer.md:111-125` |
| Example reviewer output | `code-reviewer.md:136-172` |

### `REC` — receiving-code-review

| Component | Citation |
|---|---|
| Core principle: verify before implementing; technical correctness over social comfort | `SKILL.md:13` |
| Six-step reception pattern: READ / UNDERSTAND / VERIFY / EVALUATE / RESPOND / IMPLEMENT | `SKILL.md:16-23` |
| Performative-agreement ban with named forbidden phrases and replacements | `SKILL.md:29-38` |
| Clarify-all-before-implementing-any gate (partial understanding blocks everything) | `SKILL.md:42-48` |
| Worked unclear-items example (fix 1-6, unclear on 4-5) | `SKILL.md:51-57` |
| Source-trust split: human partner trusted-after-understanding | `SKILL.md:61-65` |
| External-reviewer five-check verification before implementing | `SKILL.md:69-74` |
| Can't-verify escape: state the limitation, ask for direction | `SKILL.md:79-80` |
| Conflict with human's prior decisions → stop and discuss first | `SKILL.md:82-83` |
| YAGNI grep-check: grep for actual usage before "implementing properly" | `SKILL.md:90-96` |
| Ordered implementation: clarify → blocking → simple → complex; test each fix individually | `SKILL.md:102-111` |
| When-to-push-back list (6 conditions) + how (technical reasoning, involve human if architectural) | `SKILL.md:113-127` |
| Discomfort clause: name the tension rather than swallow the issue | `SKILL.md:129` |
| Correct-feedback acknowledgment: state the fix, zero gratitude, delete "thanks" | `SKILL.md:133-148` |
| Wrong-pushback retraction: factual correction, no apology theatre | `SKILL.md:152-162` |
| Common-mistakes table (7 rows) | `SKILL.md:166-174` |
| Four real examples (performative, verification, YAGNI, unclear-item) | `SKILL.md:178-201` |
| GitHub inline-thread reply mechanics (`gh api …/replies`, not top-level comments) | `SKILL.md:203-205` |

### `VBC-S` — verification-before-completion (superpowers)

| Component | Citation |
|---|---|
| Spirit-over-letter clause | `SKILL.md:12` |
| Iron Law: no completion claims without fresh verification evidence | `SKILL.md:16-18` |
| Fresh-in-this-message requirement | `SKILL.md:20` |
| Five-step gate function (IDENTIFY / RUN / READ / VERIFY / claim) | `SKILL.md:24-33` |
| "Skip any step = lying, not verifying" | `SKILL.md:35` |
| Claim→required-evidence table (7 rows), incl. Not-Sufficient column | `SKILL.md:40-48` |
| "Agent completed" requires VCS diff, not the agent's report | `SKILL.md:47` |
| "Requirements met" requires line-by-line checklist, not passing tests | `SKILL.md:48` |
| Red-flag list: hedge words, satisfaction expressions, pre-verification commit/PR urges | `SKILL.md:50-59` |
| Rationalization table (8 rows) | `SKILL.md:61-72` |
| Test-claim pattern (run, see N/N pass, then claim) | `SKILL.md:76-79` |
| Red-green regression proof: write → pass → revert fix → MUST FAIL → restore → pass | `SKILL.md:82-86` |
| Build ≠ linter pattern | `SKILL.md:88-92` |
| Requirements pattern: re-read plan → checklist → verify each | `SKILL.md:94-97` |
| Agent-delegation pattern: report → VCS diff → verify → report actual state | `SKILL.md:100-104` |
| When-to-apply scope: any success claim, before commit/PR/next task/delegation | `SKILL.md:106-114` |
| Paraphrase closure: applies to synonyms and implications, not exact phrases | `SKILL.md:116-121` |

### `CR-M` — code-review (mattpocock)

| Component | Citation |
|---|---|
| Two-axis architecture: Standards vs Spec | `SKILL.md:6-9` |
| Parallel sub-agents so axes don't pollute each other's context | `SKILL.md:11` |
| Harness dependency: `docs/agents/issue-tracker.md` | `SKILL.md:13` |
| Pin the fixed point; ask the user if unspecified | `SKILL.md:19` |
| Three-dot merge-base diff + commit list, captured once | `SKILL.md:21` |
| Fail-fast preflight: `git rev-parse` + non-empty diff before spawning sub-agents | `SKILL.md:23` |
| Spec-source discovery ladder: commit-message issue refs → user path → `docs/`/`specs/`/`.scratch/` → ask; skip-and-report if none | `SKILL.md:25-32` |
| Standards sources: whatever the repo documents | `SKILL.md:36` |
| Smell-baseline binding rules: repo standard overrides; always judgement calls; skip tooling-enforced | `SKILL.md:40-41` |
| 12-smell Fowler baseline, each *what* → *fix* (Mysterious Name … Refused Bequest) | `SKILL.md:45-56` |
| Standards sub-agent brief: cite the documented standard per violation; name and quote each smell; hard-vs-judgement distinction | `SKILL.md:60-64` |
| Smell baseline pasted in full into the sub-agent prompt (no other access) | `SKILL.md:63` |
| 400-word cap per sub-agent report | `SKILL.md:64`, `SKILL.md:70` |
| Spec sub-agent brief: missing/partial, scope creep, implemented-but-wrong; quote the spec line per finding | `SKILL.md:66-70` |
| Skip Spec sub-agent when no spec; note it in the report | `SKILL.md:72` |
| Aggregate verbatim under two headings; never merge or rerank findings | `SKILL.md:74-76` |
| Per-axis one-line summary; no cross-axis winner | `SKILL.md:78` |
| Why-two-axes rationale: one axis must not mask the other | `SKILL.md:80-87` |

### `CRQ` — code-review-and-quality (agent-skills)

| Component | Citation |
|---|---|
| Approval standard: approve when it definitely improves code health, even if imperfect | `SKILL.md:12` |
| Five-axis rubric: correctness / readability / architecture / security / performance | `SKILL.md:22-87` |
| Correctness checks incl. edge cases, error paths, tests-test-the-right-things | `SKILL.md:26-34` |
| Readability incl. fewer-lines test, abstractions-earn-complexity, dead-code artifacts | `SKILL.md:36-47` |
| Bolted-on-conditional and repeated-conditionals-as-missing-model design smells | `SKILL.md:48-49` |
| Architecture incl. complexity-relocated-vs-reduced concept-count test | `SKILL.md:51-60` |
| Feature-logic-in-shared-module check; explicit type boundaries | `SKILL.md:61-62` |
| Security axis (delegates depth to `security-and-hardening`) | `SKILL.md:64-75` |
| Performance axis (N+1, unbounded ops, pagination, hot paths) | `SKILL.md:77-86` |
| Structural remedies: 8 named restructuring moves; propose the move, not just the problem | `SKILL.md:88-101` |
| Change sizing thresholds (~100 / ~300 / ~1000 changed lines) | `SKILL.md:105-111` |
| File-size watch: ~1000 *total* lines inspection signal; decompose-then-add | `SKILL.md:113` |
| "One change" definition | `SKILL.md:115` |
| Splitting strategies table: stack / by file group / horizontal / vertical | `SKILL.md:117-124` |
| Large-change exceptions (deletions, automated refactors) | `SKILL.md:126` |
| Separate refactoring from feature work | `SKILL.md:128` |
| Change-description standards: imperative standalone first line + anti-pattern list | `SKILL.md:130-138` |
| Five-step process: context → tests first → implementation → categorize → verify the verification | `SKILL.md:140-203` |
| Review-tests-first step with catch-a-regression test | `SKILL.md:152-162` |
| Severity labels: no-prefix Required / Critical / Nit / Optional-Consider / FYI | `SKILL.md:177-189` |
| Lead-with-what-matters ordering: "one structural problem and ten nits — the structural problem *is* the review" | `SKILL.md:191` |
| Verify-the-verification: audit the author's verification story | `SKILL.md:193-203` |
| Multi-model review pattern (A writes, B reviews, human decides) + example review-agent prompt | `SKILL.md:205-229` |
| Dead-code hygiene: identify, list, ask before deleting | `SKILL.md:231-247` |
| Review-speed SLAs (respond within one business day; multiple rounds/day) | `SKILL.md:249-257` |
| Disagreement hierarchy: facts > style guide > engineering principles > consistency | `SKILL.md:258-266` |
| No "I'll clean it up later"; require a filed bug for deferred surrounding issues | `SKILL.md:267` |
| Honesty rules: no rubber-stamp, no softening, quantify, push back, accept override gracefully | `SKILL.md:269-277` |
| Dependency pre-add checks (5) | `SKILL.md:283-290` |
| Dependency-upgrade workflow: changelog over semver, one-per-change, tests decide, transitive graph, honest lockfile | `SKILL.md:292-299` |
| Supply-chain verdicts delegated to `security-and-hardening` | `SKILL.md:300` |
| Copyable review checklist with Approve / Request-changes verdict | `SKILL.md:302-348` |
| Sibling references: security + performance checklists | `SKILL.md:349-352` |
| Rationalization table (9 rows, incl. "AI-generated code is probably fine") | `SKILL.md:354-366` |
| Red flags (14 items) | `SKILL.md:368-383` |
| Post-review verification checklist | `SKILL.md:385-395` |
| Presumptive blockers: five structural findings that default to surface-and-propose | `SKILL.md:396` |

### `CR-O` — code-review (ours)

| Component | Citation |
|---|---|
| One protocol for dispatched agents and inline coordinator; spec judged before quality; verdicts never blend | `SKILL.md:8-11` |
| Mode table: `spec` / `quality` / `re-review` / `inline`, each with binding sections + inputs | `SKILL.md:13-22` |
| Inline mode BASE = SCOPE_BASE from the workspace ledger | `SKILL.md:22` |
| Diff-package discipline: read once, context lines ARE the files; no re-running git; fallback fetch if no package | `SKILL.md:26-31` |
| No codebase crawling; one focused check per *named* risk; cross-cutting risks legitimate | `SKILL.md:32-36` |
| Read-only on this checkout | `SKILL.md:37-38` |
| Don't re-run the suite; focused test only on a specific doubt; recommend heavy validation instead of running it; warnings in reported output are findings | `SKILL.md:39-46` |
| `file:line` on every finding and every bare-yes check | `SKILL.md:47-48` |
| Do-not-trust-the-report: implementer claims verified against the diff; rationales are claims | `SKILL.md:52-56` |
| A stated rationale never downgrades a finding's severity | `SKILL.md:55-56` |
| Spec axes: Missing / Extra / Misunderstood | `SKILL.md:62-64` |
| File-scope compliance + invariants (run the concrete command) + required tests/evidence | `SKILL.md:66-69` |
| ⚠️ Cannot-verify-from-diff channel: report with what the coordinator should check; never broaden own search | `SKILL.md:71-74` |
| Quality: correctness & design checks | `SKILL.md:78-80` |
| Edited-existing-tests-to-keep-passing = behaviour change flag | `SKILL.md:81-84` |
| Structure checks incl. flag files this change grew (ignore pre-existing size) | `SKILL.md:85-88` |
| Project-risk lens: brief.md + invariants.md | `SKILL.md:89-90` |
| Trust-boundary lens: mount the security skill's checklist under this skill's severity/output | `SKILL.md:90-94` |
| Python-first checks (mutable defaults, bare except, async blocking, unbounded retries, deserialization hazards…) | `SKILL.md:95-100` |
| Skip stylistic noise that affects neither correctness nor maintainability | `SKILL.md:102-104` |
| Severity calibration: Important *defined* (cannot be trusted until fixed, with examples); coverage-breadth = Minor | `SKILL.md:106-112` |
| Plan-mandated rule: a plan-required defect is still Important, labelled; the human decides | `SKILL.md:114-117` |
| Praise-first-for-trust | `SKILL.md:119-120` |
| Re-review mode: scope = findings list + fix diff; role boundaries lift | `SKILL.md:122-126` |
| ADDRESSED / NOT ADDRESSED per finding with `file:line` evidence; "attempted" is not addressed | `SKILL.md:126-128` |
| Fix report must name covering tests + show output; fix-diff inspected for new breakage | `SKILL.md:129-130` |
| Out-of-scope observations: non-blocking, never extend the loop | `SKILL.md:130-132` |
| No-preamble reporting: the message is the report, first line is the verdict | `SKILL.md:135-137` |
| Spec output contract (COMPLIANT \| ISSUES_FOUND + ⚠️ line) | `SKILL.md:140-148` |
| Quality output contract (APPROVE \| WARNING \| BLOCK) | `SKILL.md:150-157` |
| Re-review output contract (finding verdicts / new breakage / out-of-scope / loop verdict) | `SKILL.md:159-166` |

### `VBC-O` — verification-before-completion (ours)

| Component | Citation |
|---|---|
| Evidence-before-claims principle | `SKILL.md:7` |
| Five-step workflow: identify command → run fresh → read output+exit → report actual → `git status` before presenting | `SKILL.md:9-15` |
| Repo-pinned source of truth: `.claude/project/verification.md` + `invariants.md` | `SKILL.md:18` |
| Trust rule: no memory, confidence, partial checks, or agent reports | `SKILL.md:20` |
| (Mount, not component) Skill-shaped mirror of CLAUDE.md § Verification | repo `CLAUDE.md:63-71` |

## Cross-skill matrix

`✓` present · `~` variant (differs in mechanism or strength) · `—` absent.

### Dispatch, scoping, inputs

| Component | REQ | REC | VBC-S | CR-M | CRQ | CR-O | VBC-O |
|---|---|---|---|---|---|---|---|
| Explicit when-to-review trigger schedule | ✓ | — | — | ~ | ✓ | ~ | — |
| Fresh-subagent dispatch with curated context, never session history | ✓ | — | — | ✓ | ~ | ~ | — |
| Reviewer prompt template shipped as an asset | ✓ | — | — | ~ | ~ | — | — |
| Diff pinned to an explicit base | ✓ | — | — | ✓ | — | ✓ | — |
| Fail-fast preflight (validate ref + non-empty diff before dispatch) | — | — | — | ✓ | — | — | — |
| Spec-source discovery procedure | ~ | — | — | ✓ | ~ | — | — |
| Output/word budget on reviewer reports | — | — | — | ✓ | — | ~ | — |
| Evidence budget on reviewer *inputs* (what it may read/run) | — | — | — | — | — | ✓ | — |
| Read-only-review constraint | ✓ | — | — | — | — | ✓ | — |
| Inline self-review mode | — | — | — | — | ~ | ✓ | — |

### Axes, rubric, severity

| Component | REQ | REC | VBC-S | CR-M | CRQ | CR-O | VBC-O |
|---|---|---|---|---|---|---|---|
| Spec axis separated from quality axis | ~ | — | — | ✓ | ~ | ✓ | — |
| Never merge/rerank findings across axes | — | — | — | ✓ | — | ✓ | — |
| Missing / unrequested-extra / misunderstood spec taxonomy | ~ | — | — | ✓ | — | ✓ | — |
| Named code-smell catalog with fixes | — | — | — | ✓ | ~ | — | — |
| Repo-standard-overrides-baseline rule | — | — | — | ✓ | — | — | — |
| Skip-what-tooling-enforces / skip stylistic noise | — | — | — | ✓ | — | ~ | — |
| Structural remedies (named restructuring moves) | ~ | — | — | ~ | ✓ | ~ | — |
| Severity taxonomy with defined tiers | ✓ | — | — | — | ✓ | ✓ | — |
| Severity *calibration* (what qualifies as each tier) | ~ | — | — | — | ~ | ✓ | — |
| Lead-with-what-matters finding ordering | — | — | — | — | ✓ | — | — |
| Praise-first-for-trust | ✓ | — | — | — | — | ✓ | — |
| Plan-defect flagging (issues with the plan itself) | ✓ | — | — | — | — | ✓ | — |
| Plan-mandated severity rule (plan doesn't grade its own work) | — | — | — | — | — | ✓ | — |
| Trust-boundary → dedicated security skill lens | — | — | — | — | ✓ | ✓ | — |
| Language-specific check set | — | — | — | — | — | ✓ | — |
| Review tests before implementation | ~ | — | — | — | ✓ | — | — |
| Edited-existing-tests = behaviour-change flag | — | — | — | — | — | ✓ | — |
| Approval philosophy (improves-code-health bar) | — | — | — | — | ✓ | — | — |
| Change sizing + splitting strategies | — | — | — | — | ✓ | — | — |
| Change-description standards | — | — | — | — | ✓ | — | — |
| Dependency add/upgrade review discipline | — | — | — | — | ✓ | — | — |
| Dead-code list-and-ask hygiene | — | — | — | — | ✓ | — | — |
| Review-speed SLAs | — | — | — | — | ✓ | — | — |

### Trust, verdicts, fix rounds

| Component | REQ | REC | VBC-S | CR-M | CRQ | CR-O | VBC-O |
|---|---|---|---|---|---|---|---|
| Do-not-trust-the-implementer/author report | — | — | ~ | — | ~ | ✓ | ~ |
| Rationale-never-downgrades-severity rule | — | — | — | — | — | ✓ | — |
| `file:line` required on findings | ✓ | — | — | — | — | ✓ | — |
| Cannot-verify-from-diff escalation channel | — | ~ | — | — | — | ✓ | — |
| Machine-checkable output contract | ✓ | — | — | ~ | ~ | ✓ | — |
| No-preamble reporting rule | — | — | — | — | — | ✓ | — |
| Explicit verdict vocabulary | ✓ | — | — | — | ✓ | ✓ | — |
| Post-review severity routing (what blocks proceeding) | ✓ | — | — | — | ✓ | ~ | — |
| Re-review mode for fix rounds | — | — | — | — | — | ✓ | — |
| ADDRESSED / NOT-ADDRESSED per-finding verdicts | — | — | — | — | — | ✓ | — |
| Multi-model / cross-model review | — | — | — | — | ✓ | ~ | — |
| Disagreement-resolution protocol | ~ | ✓ | — | — | ✓ | — | — |
| Anti-sycophancy on the *giving* side | ~ | — | — | — | ✓ | ~ | — |

### Reception (author side)

| Component | REQ | REC | VBC-S | CR-M | CRQ | CR-O | VBC-O |
|---|---|---|---|---|---|---|---|
| Reception pattern (verify feedback before implementing) | — | ✓ | — | — | — | — | — |
| Performative-agreement / gratitude ban | — | ✓ | — | — | — | — | — |
| Clarify-all-before-implementing-any gate | — | ✓ | — | — | — | — | — |
| Source-trust differentiation (human vs external) | — | ✓ | — | — | — | — | — |
| YAGNI grep-check on reviewer suggestions | — | ✓ | — | — | — | — | — |
| Ordered multi-item implementation, test each individually | — | ✓ | — | — | — | — | — |
| Wrong-pushback retraction protocol | — | ✓ | — | — | — | — | — |
| GitHub thread-reply mechanics | — | ✓ | — | — | — | — | — |

### Completion gate & discipline armor

| Component | REQ | REC | VBC-S | CR-M | CRQ | CR-O | VBC-O |
|---|---|---|---|---|---|---|---|
| Iron-law completion gate (fresh evidence before any claim) | — | — | ✓ | — | — | — | ✓ |
| Stepped gate function (identify → run → read → verify) | — | — | ✓ | — | — | — | ✓ |
| Claim→required-evidence table | — | — | ✓ | — | — | — | — |
| Red-green regression proof (revert → must fail → restore) | — | — | ✓ | — | — | — | — |
| Agent-report distrust with a named mechanism (VCS diff) | — | — | ✓ | — | — | ~ | ~ |
| Satisfaction-expression / paraphrase closure | — | — | ✓ | — | — | — | — |
| Repo-pinned verification source of truth | — | — | — | — | — | ~ | ✓ |
| `git status` as an explicit completion step | — | — | ~ | — | — | — | ✓ |
| Rationalization table | ✓ | ~ | ✓ | — | ✓ | — | — |
| Red-flags list | ✓ | — | ✓ | — | ✓ | — | — |
| Worked examples | ✓ | ✓ | ~ | — | ~ | — | — |

## Shared-component differences

Mechanism-level analysis of every row where realisations differ.

**Spec/quality axis separation** — `CR-M` realises it *structurally*: two
parallel sub-agents whose reports are aggregated verbatim, never merged or
reranked (`CR-M/SKILL.md:11`, `:74-78`). `CR-O` realises it *temporally and
contractually*: spec is judged before quality, each mode binds only its own
sections, and the two verdicts "never blend" in an initial review
(`CR-O/SKILL.md:10-11`, `:13-22`) — then deliberately lifts the boundary in
re-review mode, where one reviewer verdicts everything
(`CR-O/SKILL.md:122-126`). `REQ` has only a *section* for plan alignment
inside one blended review (`REQ/code-reviewer.md:38-42`); `CRQ` folds spec
match into its correctness axis with one shared verdict
(`CRQ/SKILL.md:30`, `:345-348`). CR-O's realisation is stronger for a
dispatched pipeline: it preserves CR-M's anti-masking property (separate
verdicts) while adding the fix-round exception CR-M lacks entirely — but
CR-M's *preflight* (`CR-M/SKILL.md:23`) is a genuine mechanism neither ours
nor any other member has: it converts a bad ref or empty diff from two
wasted dispatches into one cheap local failure.

**Spec taxonomy** — `CR-M`'s spec brief (missing/partial, scope creep,
implemented-but-wrong, quote the spec line — `CR-M/SKILL.md:70`) and
`CR-O`'s Missing/Extra/Misunderstood (`CR-O/SKILL.md:62-64`) are the same
three-way taxonomy in different words. CR-O adds two mechanisms on top:
invariant checks with runnable commands (`CR-O/SKILL.md:66-69`) and the
cannot-verify-from-diff channel (`CR-O/SKILL.md:71-74`), which gives the
reviewer a *legal* answer for out-of-diff requirements instead of the two
illegal ones (silently pass it, or crawl the repo). CR-M's counterpart
quote-the-spec-line rule is worth noting: it forces per-finding evidence at
the requirement grain, where CR-O requires `file:line` of *code* but not a
quoted spec line.

**Base pinning** — three models. `REQ`: two commit SHAs, assumes per-task
commits exist (`REQ/SKILL.md:26-30`). `CR-M`: user-supplied fixed point,
three-dot so comparison is against the merge-base (`CR-M/SKILL.md:21`).
`CR-O`: `SCOPE_BASE` recorded once in the workspace ledger, packaged from
the *working tree* including untracked files
(`CR-O/SKILL.md:22`, `execution/references/task-engine.md:56-69`). Only
CR-O's model works under this repo's conservative-git rule where
implementers never commit; REQ's and CR-M's both presuppose commits. CR-M's
merge-base three-dot is the right refinement *within* a commit-based model
(avoids reviewing upstream churn), irrelevant to a snapshot model.

**Curated-context dispatch** — `REQ` states the rule and defends it with
rationalizations (`REQ/SKILL.md:8`, `:75-80`) but transmits context by
pasting into the prompt (`REQ/SKILL.md:32-40`). `CR-M` also pastes — the
smell baseline goes into the prompt in full because "the sub-agent has no
other access to it" (`CR-M/SKILL.md:63`). `CR-O`'s engine transmits *paths*,
not contents — brief path, report path, package path
(`task-engine.md:120-127`), with the protocol itself loaded by the agent
from the skill file (`agents/code-reviewer.md:11-13`). The path model is
stronger on coordinator-context economy (REQ's own stated goal) and is why
CR-O ships no prompt template: the skill *is* the template. What is lost:
CR-O has no self-contained dispatch asset usable outside the engine — REQ's
template works from any bare session.

**Severity** — `REQ` defines three tiers by example lists
(`REQ/code-reviewer.md:87-94`) plus the calibration sentence
(`code-reviewer.md:69-71`). `CRQ` has the richest *label set* — Required /
Critical / Nit / Optional / FYI — solving a different problem: telling the
author what is mandatory (`CRQ/SKILL.md:177-189`), plus the
lead-with-what-matters ordering rule (`CRQ/SKILL.md:191`) no other member
has. `CR-O` has the sharpest *boundary definition*: Important = "the change
cannot be trusted until fixed", with concrete in/out examples and an
explicit demotion of coverage-breadth wishes to Minor
(`CR-O/SKILL.md:106-112`). CR-O's realisation is stronger where it counts
for an automated loop — the Critical/Important line *routes* the fix loop
(`task-engine.md:129-135`) so its definition must be mechanical; CRQ's
FYI/Optional distinction and ordering rule are the transplantable residue.

**Post-review severity routing** — `REQ`: fix Critical immediately,
Important before proceeding, note Minor (`REQ/SKILL.md:42-46`). `CRQ`:
Critical resolved, Required resolved or explicitly deferred with
justification (`CRQ/SKILL.md:389-390`). `CR-O` itself only defines the
severities; the routing lives in the engine — Minor → ledger deferral,
plan-mandated → human, the rest → fix loop with a five-round cap and
adjudication (`task-engine.md:129-135`, `:161-176`). Same policy shape;
CR-O+engine adds what neither reference has: a *bounded* loop and a
park-with-ruling terminal state, so "note Minor for later" becomes an
auditable ledger line instead of a vanishing intention.

**Praise-first** — `REQ/code-reviewer.md:72-74` ("accurate praise helps the
implementer trust the rest of the feedback") and `CR-O/SKILL.md:119-120`
("accurate praise makes the rest of the feedback trusted") are the same
mechanism with the same rationale — direct lineage, no difference to argue.

**Plan-defect handling** — `REQ` asks the reviewer to flag deviations and
plan problems (`code-reviewer.md:76-78`); `CR-O` goes one step further with
a severity consequence: a plan-mandated defect is *still* reported Important
with a label, because "the plan's authorship does not grade its own work"
(`CR-O/SKILL.md:114-117`), and the engine routes it to the human
(`task-engine.md:133-134`). CR-O's is stronger: REQ's version relies on the
reviewer volunteering; CR-O's makes the finding non-suppressible.

**Do-not-trust-the-report** — four realisations at three different
stations. `CR-O`: the *reviewer* treats the implementer's report as
unverified claims, including design rationales (`CR-O/SKILL.md:52-56`).
`VBC-S`: the *coordinator* checks the VCS diff before believing an agent's
"success" (`VBC-S/SKILL.md:47`, `:100-104`). `CRQ`: the *reviewer* audits
the author's verification story as a process step (`CRQ/SKILL.md:193-203`).
`VBC-O`: a bare rule — "do not rely on … agent reports"
(`VBC-O/SKILL.md:20`) — with no mechanism. VBC-S's is the strongest of the
coordinator-side versions because it names the check (diff, not report);
CR-O's is the strongest reviewer-side version because of the
rationale-never-downgrades corollary (`CR-O/SKILL.md:55-56`), which closes
the specific hole where an implementer's YAGNI story talks a reviewer out
of a finding. VBC-O is the weakest realisation in the set.

**Smell/structural catalogs** — `CR-M`: 12 named Fowler smells, each
what→fix, with the repo-override and judgement-call binding rules
(`CR-M/SKILL.md:40-56`). `CRQ`: structural smells embedded in axis prose
(`CRQ/SKILL.md:48-49`, `:60-62`) plus eight named *remedies*
(`CRQ/SKILL.md:88-101`). `CR-O`: defect classes described functionally
("verbatim duplication of a logic block", `CR-O/SKILL.md:110-111`;
structure checks `:85-88`) but no named vocabulary. Mechanism difference:
CR-M's catalog is *detection*-oriented (name the smell, quote the hunk),
CRQ's remedies are *prescription*-oriented (name the move). They compose
rather than compete; CR-O currently has neither a detection vocabulary nor
a prescription vocabulary, only category descriptions.

**Skip-noise rules** — `CR-M` deduplicates against *tooling* ("skip
anything tooling already enforces", `CR-M/SKILL.md:41`); `CR-O` filters
by *impact* ("skip stylistic noise that affects neither correctness nor
maintainability", `CR-O/SKILL.md:102-104`). Different mechanisms that catch
different noise: CR-M's rule is checkable (is there a linter rule for
this?) where CR-O's is a judgement; CR-M's version also prevents
double-reporting on repos with strict ruff/mypy configs — which this repo
is (`rules/python/coding-style.md` mandates both).

**Read-only constraint** — `REQ` includes a worktree escape hatch for
inspecting other revisions (`code-reviewer.md:33-35`); `CR-O` states the
prohibition flatly (`CR-O/SKILL.md:37-38`) and, unlike REQ, embeds it in a
wider evidence budget (no crawling, no suite re-runs,
`CR-O/SKILL.md:32-46`). CR-O's is the stronger *constraint system*; REQ's
escape hatch is the one operational affordance ours dropped.

**Trigger schedules** — `REQ` enumerates review moments as its own content
(`REQ/SKILL.md:14-22`); `CRQ` enumerates merge-anchored moments
(`CRQ/SKILL.md:14-20`); `CR-O`'s moments are the engine's — review gate per
task, final review per scope (`task-engine.md:118-127`, `:180-195`) — so
the skill itself only names its dispatch shapes (`CR-O/SKILL.md:3`,
`:13-22`). Consequence, stated as fact: outside the engine, our harness has
no when-to-request-review guidance; REQ's optional triggers (stuck,
pre-refactor baseline, post-bug-fix) have no local equivalent.

**Verdict vocabularies** — `REQ`: Ready-to-merge Yes/No/With-fixes
(`code-reviewer.md:105-109`). `CRQ`: Approve / Request changes
(`CRQ/SKILL.md:345-348`). `CR-O`: three per-mode contracts — COMPLIANT |
ISSUES_FOUND, APPROVE | WARNING | BLOCK, and per-finding ADDRESSED | NOT
ADDRESSED (`CR-O/SKILL.md:140-166`). `CR-M` alone refuses a verdict beyond
per-axis summaries, by design (`CR-M/SKILL.md:78`). CR-O's is the only
vocabulary another program consumes (`task-engine.md:125-126`, `:150-158`),
which is what forces its precision.

**Multi-model review** — `CRQ` prescribes a second model as reviewer with a
prompt sketch (`CRQ/SKILL.md:205-229`). Our realisation is not in CR-O but
in the mount chain: Codex review at final scope
(`task-engine.md:188-189`) governed by use-codex's critique discipline —
artifact-not-conclusion, four-class finding classification, 3-cycle bound,
doubt-theater check (`use-codex.md:67-81`, per the doubt-driven-development
resolution, `ledger.json:253-260`). Ours is stronger: CRQ's pattern says
*use* another model; use-codex constrains *how* to keep the second opinion
from becoming validation.

**Iron-law completion gate** — `VBC-S` and `VBC-O` share the principle and
the stepped gate (`VBC-S/SKILL.md:16-36`; `VBC-O/SKILL.md:7-15`).
Divergence is armor vs anchoring. VBC-S adds everything that resists
pressure: the claim→evidence table (`:40-48`), red flags (`:50-59`), the
rationalization table (`:61-72`), red-green proof (`:82-86`), paraphrase
closure (`:116-121`). VBC-O adds everything that binds to *this* repo: the
verification.md/invariants.md pointer (`VBC-O/SKILL.md:18`) and `git
status` as a named final step (`:13`, VBC-S has it only as a red-flag
context, `VBC-S/SKILL.md:55`). Per claim class, VBC-S is stronger on six of
seven rows of its own table; VBC-O is stronger only on "which command
counts as proof here". The two are compositional, not conflicting: nothing
in VBC-S's armor contradicts VBC-O's anchoring.

**Rationalization/red-flag armor** — present in REQ, VBC-S, CRQ
(`REQ/SKILL.md:75-93`; `VBC-S/SKILL.md:50-72`; `CRQ/SKILL.md:354-383`),
variant in REC (a mistakes table, `REC/SKILL.md:166-174`), absent in CR-M,
CR-O, and VBC-O. For CR-O this is partly by design — reviewer *agents*
don't face the temptations the tables target (the coordinator does, and the
engine carries its own table, `execution/SKILL.md:120-129`) — but VBC-O
faces exactly the pressure VBC-S's tables were built for, with none of
them.

**Disagreement handling** — `REC` owns the author side (when/how to push
back, retraction — `REC/SKILL.md:113-129`, `:152-162`); `CRQ` owns the
reviewer side (hierarchy: facts > style guide > principles > consistency —
`CRQ/SKILL.md:259-266`); `REQ` gives the requester a pushback right
(`REQ/SKILL.md:90-93`). Our harness's counterpart is positional, not
argumentative: findings are relayed verbatim, disagreement is deferred to
adjudication at the cap with a mandatory ledger ruling
(`task-engine.md:126-128`, `:161-176`). Different mechanism entirely:
the references resolve disagreement by argument quality; ours resolves it
by *when* argument is allowed. The two are compatible — REC's evaluation
steps describe how to adjudicate well once the cap is reached — but no
skill of ours currently says so.
