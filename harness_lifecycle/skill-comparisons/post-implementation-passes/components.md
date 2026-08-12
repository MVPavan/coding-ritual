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
