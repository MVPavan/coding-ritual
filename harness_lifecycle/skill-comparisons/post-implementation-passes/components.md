# Post-Implementation Passes — Level 3 Components

Column keys:

| Key | Skill |
|---|---|
| `SIMP` | agent-skills — `skills/code-simplification/SKILL.md` |
| `SEC` | agent-skills — `skills/security-and-hardening/SKILL.md` |

There is no "ours" column: our harness ships neither pass. Where a component has
a partial counterpart in our harness, it is named in the *Nearest thing we have*
column of the matrix and argued in the last section.

## Component inventory

### `SIMP` — code-simplification

| Component | Citation |
|---|---|
| Provenance note (adapted from the Claude Code Simplifier plugin) | `SKILL.md:8` |
| Success test: comprehension speed, not line count | `SKILL.md:12` |
| Six trigger conditions | `SKILL.md:15-21` |
| Four not-for cases, incl. "you don't understand it yet" and performance-critical code | `SKILL.md:23-28` |
| **Principle 1 — preserve behaviour exactly**, with a four-question pre-change gate | `SKILL.md:32-42` |
| **Principle 2 — follow project conventions**; read CLAUDE.md, study neighbours, match 5 named style axes | `SKILL.md:44-57` |
| "Simplification that breaks project consistency is churn" | `SKILL.md:59` |
| **Principle 3 — clarity over cleverness**, two worked pairs (ternary chain, chained reduce) | `SKILL.md:61-90` |
| **Principle 4 — maintain balance**: four over-simplification traps | `SKILL.md:92-99` |
| **Principle 5 — scope to what changed**; no drive-by refactors | `SKILL.md:101-103` |
| **Chesterton's Fence** step: six questions incl. `git blame`, plus a not-ready-yet stop | `SKILL.md:107-121` |
| Structural-complexity signal table with thresholds (3+ nesting, 50+ lines) | `SKILL.md:127-136` |
| Naming/readability signal table | `SKILL.md:138-146` |
| Comment rule: delete "what" comments, keep "why" comments | `SKILL.md:144-145` |
| Redundancy signal table (duplication ≥5 lines, dead code, needless wrappers, over-engineered patterns) | `SKILL.md:148-156` |
| One change at a time, test after each, revert on failure | `SKILL.md:157-169` |
| Refactors submitted separately from features | `SKILL.md:159` |
| **The Rule of 500** — automate past 500 lines | `SKILL.md:171` |
| Step 4 whole-diff evaluation with an explicit revert option | `SKILL.md:173-185` |
| Language-specific examples: TS/JS | `SKILL.md:189-236` |
| Language-specific examples: Python | `SKILL.md:238-271` |
| Language-specific examples: React, incl. a flagged judgment call | `SKILL.md:273-295` |
| 7-row rationalization table | `SKILL.md:297-307` |
| 7 red flags, led by "simplification that requires modifying tests" | `SKILL.md:309-317` |
| 9-item verification checklist (tests pass **unmodified**, clean diff, no weakened error handling) | `SKILL.md:319-331` |

### `SEC` — security-and-hardening

| Component | Citation |
|---|---|
| Posture: security is a constraint on every line, not a phase | `SKILL.md:10` |
| Six trigger conditions; **no not-for list** | `SKILL.md:13-20` |
| **Threat model first** — controls without a model are guesses | `SKILL.md:22-23` |
| Map trust boundaries, **including LLM output** | `SKILL.md:25` |
| Name the assets | `SKILL.md:26` |
| **STRIDE table** — six threats × ask × typical mitigation | `SKILL.md:27-36` |
| Abuse cases written next to use cases, and tested first | `SKILL.md:38` |
| "Can't name the trust boundaries → not ready to secure it" (OWASP A04) | `SKILL.md:40` |
| **Tier 1 — Always Do** (8 items incl. native audit against the committed lockfile) | `SKILL.md:44-53` |
| **Tier 2 — Ask First** (7 change classes requiring human approval) | `SKILL.md:55-63` |
| **Tier 3 — Never Do** (7 absolutes) | `SKILL.md:65-73` |
| Injection prevention (parameterized / ORM) | `SKILL.md:79-90` |
| Auth: bcrypt salt rounds, session cookie flags | `SKILL.md:92-114` |
| XSS: framework escaping, sanitize when unavoidable | `SKILL.md:116-128` |
| **Authorization ≠ authentication** — ownership check on the resource | `SKILL.md:130-148` |
| Misconfiguration: helmet, CSP directives, CORS allowlist | `SKILL.md:150-173` |
| Sensitive-data exposure: field stripping, env-var secrets | `SKILL.md:175-187` |
| **SSRF**: scheme+host allowlist, resolve ALL records, reject non-unicast, forbid redirects | `SKILL.md:189-218` |
| **Named residual TOCTOU gap** + pinned-IP / filtering-agent mitigations | `SKILL.md:220` |
| Schema validation at the route boundary | `SKILL.md:224-252` |
| File-upload safety incl. magic bytes over extension | `SKILL.md:254-270` |
| **Audit triage decision tree** — severity × reachability × fix availability | `SKILL.md:272-290` |
| Reachability questions; document + review-date on deferral | `SKILL.md:292-297` |
| **Supply chain**: find the installation boundary, stop on competing lockfiles, pin the manager | `SKILL.md:301-303` |
| **Block dependency scripts before first execution**; never blanket-approve | `SKILL.md:304` |
| Never auto-apply forced remediation | `SKILL.md:307` |
| Verify registry signatures/provenance; absence is a signal, not proof | `SKILL.md:309` |
| Review new deps, lockfile diffs, script-policy changes together; typosquats | `SKILL.md:310` |
| Rate limiting, stricter on auth endpoints | `SKILL.md:312-330` |
| Secrets file layout + `.gitignore` set | `SKILL.md:332-346` |
| Staged-diff secret grep before committing | `SKILL.md:348-352` |
| **Rotate, don't scrub** — a committed secret is compromised on push | `SKILL.md:354` |
| **LLM05** model output is untrusted input | `SKILL.md:360` |
| **LLM01** prompts can be hijacked; the system prompt is not a security boundary | `SKILL.md:361` |
| **LLM02/07** keep secrets and cross-tenant data out of prompts | `SKILL.md:362` |
| **LLM06** constrain tool/agent permissions; confirm destructive actions | `SKILL.md:363` |
| **LLM10** bound tokens, rate, and recursion depth | `SKILL.md:364` |
| **LLM08** partition RAG embeddings per tenant; validate documents before indexing | `SKILL.md:365` |
| Good/bad LLM-output handling code (parse → validate → encode) | `SKILL.md:367-382` |
| Copyable six-section review checklist | `SKILL.md:384-424` |
| 8-row rationalization table | `SKILL.md:429-441` |
| 10 red flags | `SKILL.md:442-454` |
| 9-item verification checklist | `SKILL.md:455-468` |
| Sibling reference dependency (`references/security-checklist.md`) | `SKILL.md:77`, `SKILL.md:303`, `SKILL.md:427` |

## Cross-skill matrix

`✓` present · `~` variant · `—` absent. The last column is **not** a third skill —
it records the nearest existing coverage in our harness, for the gap analysis.

| Component | SIMP | SEC | Nearest thing we have |
|---|---|---|---|
| Runs as a distinct pass over finished code | ✓ | ~ | — nothing |
| Explicit trigger list | ✓ | ✓ | — |
| Explicit **not-for** list | ✓ | — | — |
| Scoped to recently changed code | ✓ | — | `ak-guide` §3 (surgical changes) |
| Method that generates its own checks | — | ✓ | — |
| Trust-boundary mapping | — | ✓ | — |
| STRIDE (or any threat taxonomy) | — | ✓ | — |
| Abuse cases as first tests | — | ✓ | — |
| Understand-before-you-touch gate | ✓ | ~ | `ak-guide` §8 (read before you write) |
| Behaviour-preservation requirement | ✓ | ✗ (inverts it) | `ak-guide` §3 |
| Convention conformance | ✓ | — | `ak-guide` §11 |
| Thresholded signal tables | ✓ | — | `rules/python/coding-style.md` (file-size limits only) |
| Over-correction trap list | ✓ | — | — |
| Human-approval tier for risky change classes | — | ✓ | ~ plan approval / git authority (process, not risk) |
| Non-negotiable "always do" list | ~ | ✓ | `rules/python/safety.md` |
| Absolute "never do" list | ~ | ✓ | `rules/python/safety.md`, git-safety rule |
| Incremental application with a per-change test gate | ✓ | — | `test-driven-development` (loop, not pass) |
| Revert-on-failure path | ✓ | — | — |
| Automate past a size threshold (Rule of 500) | ✓ | — | — |
| Whole-diff step-back evaluation | ✓ | ~ | `verification-before-completion` (evidence, not shape) |
| Injection / parameterized queries | — | ✓ | `rules/python/safety.md`; `code-reviewer.md:40` |
| Authn vs **authz** distinction | — | ✓ | — |
| Session/cookie hardening | — | ✓ | — |
| Output encoding / XSS | — | ✓ | — |
| SSRF handling | — | ✓ | — |
| Named residual-risk disclosure (TOCTOU) | — | ✓ | — |
| Input schema validation at boundaries | — | ✓ | ~ Pydantic-at-boundaries convention |
| Secrets handling | — | ✓ | `rules/python/safety.md` |
| Secret **rotation** after exposure | — | ✓ | — |
| Dependency-audit triage | — | ✓ | — |
| Supply-chain / install-script policy | — | ✓ | — |
| LLM/agent attack surface | — | ✓ | — |
| Rate limiting / consumption bounds | — | ✓ | ~ `rules/python/safety.md` (timeouts, bounded retries, bounded concurrency) |
| Language-specific worked examples | ✓ | ✓ | n/a |
| Rationalization table | ✓ | ✓ | — |
| Red-flag list | ✓ | ✓ | — |
| Verification checklist | ✓ | ✓ | `.claude/project/verification.md` |
| Depends on an external reference file | — | ✓ | n/a |

## Shared-component differences

Only components both skills carry, or that one carries and our harness partially
covers, are argued here.

**Trigger scoping** (`SIMP` `✓` both lists vs `SEC` `✓` triggers, `—` not-for).
`SIMP:23-28` names four conditions under which running the skill is wrong,
including the self-aware "you don't understand what the code does yet" and "the
code is performance-critical and the simpler version would be measurably slower".
`SEC:13-20` names six conditions to run and none to stop. **`SIMP` is stronger**
and the difference is structural, not stylistic: a pass without a not-for list has
no natural end, which is why `SEC` reads as a build-time constraint
(`SEC:10`, "security isn't a phase") despite being bucketed and described as
hardening. Adopting `SEC` into our cycle would require inventing its scope
boundary; adopting `SIMP` would not.

**Understand-before-you-touch** (`SIMP` `✓` vs `SEC` `~`). `SIMP:107-121` makes it
a gate with six answerable questions and a hard stop ("if you can't answer these,
you're not ready to simplify"). `SEC:40` has the same shape aimed at a different
object ("if you can't name the trust boundaries for a feature, you're not ready to
secure it") but supplies no question list to get there beyond the STRIDE table.
**`SIMP`'s is more operable** — it tells you what to read; `SEC`'s tells you what
you must be able to say. Our `ak-guide` §8 states the principle for both and gates
neither.

**Behaviour with respect to behaviour.** These invert. `SIMP:32-42` forbids any
observable change and verifies it mechanically: existing tests must pass
**without modification** (`SIMP:323`), and a simplification that needs a test
edited is a red flag (`SIMP:311`). `SEC` exists to change behaviour — rejecting
input, returning 403, capping size. Its verification is therefore a review list
(`SEC:455-468`), not a diff-invariance property. **`SIMP`'s check is stronger as a
check**, because it cannot be argued with; `SEC` has no equivalent available to
it, which is intrinsic to the axis rather than a defect.

**Non-negotiable lists** (`SIMP` `~` vs `SEC` `✓`). `SIMP`'s absolutes are
embedded in its principles and red flags (never remove error handling,
`SIMP:314`; never rename to personal preference, `SIMP:313`). `SEC:44-73` is a
three-tier partition where every item is placed by *who decides*: the agent
always, the human first, or nobody ever. **`SEC` is stronger by mechanism** — the
middle tier is the part with no counterpart: our harness has approval gates for
*process* steps (plan approval, `phase-execution/SKILL.md:46`; commit authority
under the git-safety rule) but none keyed to a *risk class* of change. Adding new
auth logic or a new file-upload handler currently passes through our cycle with no
stop.

**"Always do" vs `rules/python/safety.md`.** Our safety rule and `SEC:44-53`
overlap on four items: parameterize queries, no `eval`/unsafe deserialization,
secrets via a manager not YAML/git/logs, timeouts and bounded retries on external
I/O. `SEC` adds four our rule does not have: output encoding for XSS, HTTPS for
external communication, security headers, httpOnly/secure/sameSite session
cookies, plus the native-audit-against-the-lockfile item. **Ours is stronger where
it overlaps** — it is language-specific, enforceable by our linters, and it adds
async-safety items (`no blocking I/O in async context`, bounded concurrency, never
swallow exceptions in background tasks) that `SEC` lacks. **`SEC` is broader on
web-surface controls**, all of which are irrelevant to a repo with no HTTP surface
— which is precisely why the 2026-07-15 deferral said "exclude stack-specific
bulk".

**LLM/agent attack surface** (`SEC:356-382`, nothing anywhere else). Six mapped
threats, of which four bear directly on this repo's own subject matter: model
output is untrusted input (`SEC:360`), the system prompt is not a security
boundary — enforce permissions in code (`SEC:361`), constrain tool permissions and
confirm destructive actions (`SEC:363`), bound tokens/rate/recursion depth
(`SEC:364`). Our harness touches this from one side only: `block-dangerous-
commands.sh` exists as a hook, and `source-driven-development`'s
fetched-docs-are-untrusted rule was ruled adopted via `docs-researcher`. But
nothing states the principle, and nothing applies it to our own agent surfaces.
**This is the strongest single argument in this comparison for reopening the
deferral**, and notably it is the part of `SEC` that is *not* stack-specific.

**Verification checklists** (`SIMP:319-331` vs `SEC:455-468`). `SIMP`'s nine items
are all locally checkable by running something (tests unmodified, build clean,
linter clean, diff clean). `SEC`'s nine are a mix of runnable (`native audit has
no unmitigated reachable critical/high findings`) and inspectional (`all user
input validated at system boundaries`). **`SIMP`'s is stronger as a gate**;
`SEC`'s is stronger as a review prompt. Our `.claude/project/verification.md`
plus `verification-before-completion` is the closest structure we have, and it is
evidence-shaped like `SIMP`'s — which suggests `SIMP`'s checklist would drop into
our harness with almost no adaptation, while `SEC`'s would need a home that does
not exist yet.

**Rationalization tables.** Both carry one (`SIMP:297-307`, `SEC:429-441`) and both
are well-formed — each Reality is an argument rather than a restatement. Neither
is stronger; what matters for us is where the device is missing on our side.
Our own `authoring-for-agents` skill prescribes it — a rationalization table plus
red flags is its named remedy for "knows the rule, skips it under pressure"
(`.claude/skills/authoring-for-agents/SKILL.md:30`;
`references/skill-anatomy.md:65`) — yet **none of our execution surfaces carries
one**: not `phase-execution`, `subagent-driven-development`, `run-phases`,
`implementer.md`, `test-driven-development`, or `ak-guide`. Nearly every upstream
skill across all three comparison folders that is built to survive an agent
looking for an exit uses this device, and on our side it appears only in
`brainstorming` and `idea-refine`.

---

## Round 2 extension — `SIMP` coverage re-audit

Added 2026-08-14. Verdict, ranked absorption list, and the three stale round-1
claims: [`README.md`](README.md) → *Round 2 extension*. This section is the
evidence: every `SIMP` component checked against the live consumers, one row
each.

**Ours-side citation keys** (all paths relative to repo root):

| Key | File |
|---|---|
| `AK` | `.claude/rules/core/03-ak-guidelines.md` — the ak-guide content, the ledger's named owner |
| `TE` | `.claude/skills/execution/references/task-engine.md` — *Simplification look* is `:199-205` |
| `CS` | `.claude/rules/python/coding-style.md` |
| `EX` | `.claude/skills/execution/SKILL.md` |

Established by grep over `.claude/`, not assumed: `AK` and `TE` are the **only**
two files carrying simplification behaviour. `CS` carries a large slice
incidentally. `performance-optimization`, `code-review`, and
`.claude/project/verification.md` contain no simplification content.

Round 1's matrix above has no "ours" column because at the time we shipped no
pass. `TE:199-205` was written after that, so this table replaces the *Nearest
thing we have* column with an actual coverage verdict.

### Coverage table

`✓` covered · `◐` partial (mechanism present but weaker or narrower) ·
`✗` not covered · `n/a` not applicable to this repo

| # | `SIMP` component | `SIMP` cite | Covered where | |
|---|---|---|---|---|
| 1 | Success test: comprehension speed, **not** line count | `:12` | `TE:200-201` — "would a new team member understand this faster than a simpler version?" | ✓ |
| 2 | Six trigger conditions | `:15-21` | `TE:199` supplies **one** occasion (after the final review, deep scope only). The other five — review flags readability, deep nesting / long functions / unclear names, time-pressure code, scattered logic, post-merge duplication — have no trigger anywhere | ◐ |
| 3 | Not-for: code is already clean | `:24` | `TE:205` — "skip the pass entirely when the diff is already minimal" | ✓ |
| 4 | Not-for: you don't understand it yet | `:25` | `TE:201-202` — "can't answer → don't touch" | ✓ |
| 5 | Not-for: **performance-critical and simpler is measurably slower** | `:26` | NOT COVERED — absent from `TE`, `AK`, and `.claude/skills/performance-optimization/` | ✗ |
| 6 | Not-for: module is about to be rewritten | `:27` | NOT COVERED | ✗ |
| 7 | **P1** preserve behaviour exactly | `:32-34` | `TE:203-204` — tests must pass **unmodified**; a simplification needing test edits changed behaviour, revert it | ✓ |
| 8 | P1 four-question pre-change gate | `:36-42` | ◐ — only the fourth question ("do all existing tests still pass unmodified?") survives, at `TE:203`. **Same output for every input**, **same error behaviour**, and **same side effects and ordering** (`:38-40`) are unstated — and are exactly what a passing test suite does not prove | ◐ |
| 9 | **P2** follow project conventions | `:44-46` | `AK:37` ("Match existing style, even if you'd do it differently"), `AK:94-96` ("Conformance > taste inside the codebase") | ✓ |
| 10 | P2 read CLAUDE.md / study neighbouring code | `:49-50` | `AK:81-83` — read exports, immediate callers, shared utilities; ask if unsure why code is shaped a way | ✓ |
| 11 | P2 five named style axes (imports, function declaration, naming, error handling, type depth) | `:51-57` | `CS:80-82` (import order), `CS:53-56` (naming), `CS:86-88` (error handling), `CS:8-9` (annotation depth) | ✓ |
| 12 | "Simplification that breaks project consistency is churn" | `:59` | `AK:94-96` — same claim, same force | ✓ |
| 13 | **P3 clarity over cleverness** — explicit beats compact when compact needs a mental pause | `:61-63` | NOT COVERED — `AK` §2 (`:18-28`) governs code *quantity*, never *expression*. Nearest is `CS:66` ("prefer self-documenting names over comments"), which is adjacent, not the same claim | ✗ |
| 14 | P3 worked pairs (ternary chain, chained reduce) | `:65-90` | TS examples | n/a |
| 15 | **P4 four over-simplification traps** | `:92-99` | NOT COVERED — **and counter-covered**: `AK:23` ("No abstractions for single-use code") drives trap `:98`, `AK:26` ("if you write 200 lines and it could be 50, rewrite it") drives trap `:99`. Nothing in our harness warns that simplification has a failure mode | ✗ |
| 16 | **P5** scope to what changed; no drive-by refactors | `:101-103` | `AK:30-45` — esp. `:36` ("don't refactor things that aren't broken") and `:45` ("every changed line should trace directly to the user's request"). **Ours is stronger**: `AK:39` adds a report format (`NOTICED BUT NOT TOUCHING`) that surfaces the observation without acting on it — SIMP has no such channel | ✓ |
| 17 | **Chesterton's Fence** as a gate + not-ready-yet stop | `:107-121` | `TE:201-202` (named, with `git blame`, and the hard stop) + `AK:81-83`. Six questions compressed to two; **dropped**: "are there tests that define the expected behavior?" (`:116`) and "what are the edge cases and error paths?" (`:115`) | ✓ |
| 18 | **Structural signal table with thresholds** — 3+ nesting, 50+ line functions, nested ternaries, boolean flag params, repeated conditionals | `:127-136` | NOT COVERED — `CS:38` has file-size limits (200–500 typical, 800 max) and nothing at function or nesting grain. `TE:200` asks a question with no scan list behind it | ✗ |
| 19 | Naming signal table — generic / abbreviated / misleading names | `:138-146` | ◐ — `CS:53-56` covers case conventions and bans single-letter names, but not `data`/`result`/`temp`, not `usr`/`cfg`/`evt`, and not the misleading-name case (a `get` that mutates) | ◐ |
| 20 | Comment rule: delete "what" comments, keep "why" comments | `:144-145` | `CS:61-63` — verbatim-equivalent. **Ours is stronger**: adds `CS:64-65` (document gotchas where they bite, link the ADR) and `CS:67` (no commented-out code) | ✓ |
| 21 | Redundancy: duplicated logic (≥5 lines) → extract | `:151` | `CS:47-49`. **Ours is stricter** — the threshold is 3+ lines, not 5+ | ✓ |
| 22 | Redundancy: dead code → remove after confirming | `:152` | ◐ **deliberate divergence, not a gap**: `CS:67` deletes commented-out code, `AK:41-43` removes orphans *your* change created, but `AK:38` explicitly says to *mention* unrelated dead code rather than delete it. Ours is the better-reasoned position for a delegated-work harness | ◐ |
| 23 | Redundancy: needless wrappers, over-engineered patterns (factory-for-a-factory), redundant type assertions | `:153-155` | NOT COVERED | ✗ |
| 24 | One change at a time; test after each; revert on failure | `:157-169` | `TE:203-204` | ✓ |
| 25 | **Refactors submitted separately from features** ("that PR is two PRs") | `:159` | NOT COVERED — and **structurally conflicts**: `TE:199` places the pass *inside* the scope, after the final review, so its edits land in the same diff and commit as the feature | ✗ |
| 26 | **The Rule of 500** — automate past 500 changed lines | `:171` | NOT COVERED | ✗ |
| 27 | Step 4 whole-diff evaluation, four questions, explicit revert option | `:173-185` | ◐ — `TE:200` has the step-back and one of the four questions. The revert path at `TE:204` fires only on *test failure*; SIMP's `:185` reverts when the result is simply **worse to read**, which nothing in ours triggers on | ◐ |
| 28 | Language examples: TS/JS, React | `:189-236`, `:273-295` | Python-first repo — correctly rejected in round 1 (`README:90`) | n/a |
| 29 | Language examples: Python | `:238-271` | Basic (dict comprehension, guard clauses); covered by `CS` + `ruff` (`CS:5-7`) | n/a |
| 30 | 7-row rationalization table | `:297-307` | ✗ for this axis. The **device** now exists in our execution surface (`EX:120-130`, six rows) — correcting round 1's claim at `components.md:229-233` — but every row is dispatch/review discipline; none is about simplification | ✗ |
| 31 | Red flag: simplification requiring test edits | `:311` | `TE:204` — the one SIMP leads with, and ours states it as a revert rule | ✓ |
| 32 | Red flag: "simplified" code longer and harder to follow | `:312` | NOT COVERED (see row 27 — no worse-to-read trigger) | ✗ |
| 33 | Red flag: renaming to personal preference | `:313` | `AK:94-96` | ✓ |
| 34 | Red flag: **removing error handling because it makes the code cleaner** | `:314` | NOT COVERED — and a passing suite will not catch it on any uncovered path | ✗ |
| 35 | Red flag: simplifying code you don't fully understand | `:315` | `TE:201-202` | ✓ |
| 36 | Red flag: batching many simplifications into one commit | `:316` | `TE:203` — "one simplification at a time" | ✓ |
| 37 | Red flag: refactoring outside the task's scope unasked | `:317` | `AK:30-45` | ✓ |
| 38 | Verification: all existing tests pass **without modification** | `:323` | `TE:203` | ✓ |
| 39 | Verification: build succeeds, linter/formatter clean | `:324-325` | `.claude/project/verification.md` is the harness's source of truth per `CLAUDE.md`; `CS:5-7` names the tools | ✓ |
| 40 | Verification: each simplification is a reviewable incremental change | `:326` | `TE:203` | ✓ |
| 41 | Verification: clean diff, no unrelated changes mixed in | `:327` | `AK:45` | ✓ |
| 42 | Verification: follows project conventions | `:328` | `AK:94-96`, `CS` throughout | ✓ |
| 43 | Verification: **no error handling removed or weakened** | `:329` | NOT COVERED (pairs with row 34) | ✗ |
| 44 | Verification: no dead code left behind (unused imports, unreachable branches) | `:330` | `AK:41-43` — scoped to orphans your own change created, which is the correct scope here | ✓ |
| 45 | Verification: a teammate would approve it as a net improvement | `:331` | ◐ — `TE:200-201` is the same test in "new team member" form, asked of the diff's *readability* rather than as an approval judgement | ◐ |

**Totals: 20 ✓ · 6 ◐ · 12 ✗ · 3 n/a.**

**Attribution split of the 20 covered rows** — the number that decides the
verdict:

| Owner | Rows covered |
|---|---|
| `TE:199-205` (Simplification look — **written after the 2026-07-15 ledger entry**) | 1, 3, 4, 7, 17, 24, 31, 35, 36, 38, 40 |
| `CS` (Python coding-style rule) | 11, 20, 21, 39 |
| `AK` — **the ledger's named owner** | 9, 10, 12, 16, 33, 37, 41, 42, 44 |

`AK` carries the convention cluster and the scope cluster, and nothing else.
Every mechanism with teeth — the behaviour-preservation check, the Chesterton
gate, the one-at-a-time rule, the occasion itself — is `TE`'s, and `TE` did not
exist when the entry was written.

### Shared-component differences (extension)

**Behaviour preservation — check vs gate** (`SIMP` gate + check vs ours check
only). `SIMP:36-42` runs a four-question gate *before* each change and then
verifies with tests-unmodified (`:323`). `TE:203-204` keeps only the
verification half. **Theirs is stronger, and the missing half is the
load-bearing one**: the three dropped questions (same output for every input,
same error behaviour, same side effects **and ordering**, `:38-40`) are
precisely the properties a green suite fails to prove. Our own `CS:64-65`
already treats ordering as a class of gotcha worth documenting, so the concept
is native — it is just not wired into the pass.

**The occasion** (`SIMP` six triggers vs ours one). `SIMP:15-21` fires on six
situations, most of them mid-stream. `TE:199` fires once, at the end of a
**deep-scope** run. Round 1 argued we lacked the occasion entirely
(`README:195-201`); that is now wrong, but a narrower version holds — **standard
and small work never reaches this pass at all** (`EX:34-39` routes them inline
or through the light path, and `TE:199` is explicitly deep-only). For a harness
whose default risk class is `standard`, the pass exists for a minority of the
work. **Theirs is stronger on reach; ours is stronger on discipline** — a pass
with one defined occasion and a skip condition (`TE:205`) cannot become a
perpetual-refactor licence, which six open triggers can.

**Scope discipline** (both `✓`, ours stronger). `SIMP:101-103` says default to
recently modified code and avoid drive-by refactors. `AK:30-45` says the same
and adds two mechanisms SIMP has no counterpart for: the trace-to-request test
(`AK:45`) and the `NOTICED BUT NOT TOUCHING` report format (`AK:39`), which
gives the observation somewhere to *go* instead of forcing a choice between
acting on it and dropping it. **Ours is stronger**, and this is the clearest row
where the ledger's "covered" was right for the right reason.

**Over-simplification** (`SIMP` `✓` vs ours ✗, **inverted**). The only row in
this table where our harness does not merely lack the component but pushes
against it. `SIMP:92-99` names four traps; `AK:23` and `AK:26` instruct the
behaviour behind two of them, and `AK:28` ("would a senior engineer say this is
overcomplicated? If yes, simplify") supplies a one-directional prompt with no
counter-prompt. **Theirs is stronger by existing.** The fix is small — one
clause in `AK` §2 acknowledging that abstractions can exist for testability or
extensibility, plus the trap list in `TE:199-205` — but it cannot be made by
absorbing into `TE` alone, because `AK` loads on every task while `TE:199` fires
on a minority of them.

**Rationalization table** (`SIMP` `✓` vs ours ✗ for this axis). Round 1's claim
that no execution surface carries the device (`components.md:229-233`) is stale:
`EX:120-130` carries a six-row table. The device is now proven native to our
harness, which *lowers* the cost of adding simplification rows rather than
raising it. `SIMP:297-307`'s most transferable row for us is the last —
*"I'll refactor while adding this feature" → separate refactoring from feature
work* (`:307`) — which is the same finding as row 25: our pass mixes them by
construction (`TE:199`).
