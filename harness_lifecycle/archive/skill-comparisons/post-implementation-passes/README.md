# Post-Implementation Passes

Passes that run over code that already works — they do not produce the feature,
they take a second run at it along one axis. Both members are agent-skills'; our
harness ships **no analogue of either as a pass**, which is the point of this
comparison. Engines: `../plan-execution-engines/`. In-loop disciplines:
`../execution-disciplines/`.

There is no "ours" column here. What we do and do not have is stated explicitly
in *What our harness lacks* below and in the shared-component analysis in
[`components.md`](components.md).

## Level 1 — Placement

| Skill | Repo | Bucket | Triggers when |
|---|---|---|---|
| `code-simplification` | agent-skills | 4 Implementation & Refactoring (also 7 Review & Completion Assurance) | After a feature works and tests pass but the implementation feels heavier than needed; during review when readability is flagged; on deep nesting, long functions, unclear names, time-pressure code, scattered logic, or post-merge duplication (`SKILL.md:15-21`). Four explicit not-for cases, including "you don't understand what the code does yet" (`SKILL.md:23-28`). |
| `security-and-hardening` | agent-skills | 4 (also 7) | Anything accepting user input, auth/authz work, sensitive data storage or transmission, external integrations, uploads/webhooks/callbacks, payment or PII handling (`SKILL.md:13-20`). Note the description says "hardens code" — a pass — but every trigger is a *build-time* condition, so it fires **while** the feature is written, not only after. No not-for list at all. |

**Prior ledger decisions.**
- `code-simplification` — **adopted**, 2026-07-15, `our_id: skill:skills/ak-guide`,
  reason: "covered by AK guidance on simplicity, surgical scope, convention
  matching, read-before-write, and verifiable behavior-preserving changes." A
  related entry rejects agent-skills' `/code-simplify` command as "a thin wrapper
  around code-simplification; local AK guidance already requires minimal,
  surgical, behavior-preserving changes without another command surface."
- `security-and-hardening` — **deferred**, 2026-07-15: "route framework-neutral
  threat modeling, auth, SSRF, supply-chain, and LLM checks to an optional
  production-readiness plugin; exclude stack-specific bulk." Its sibling
  `agent:agents/security-auditor` also has a ledger row; we have no such agent
  installed (`harness_lifecycle/inventory/ours/agent.csv` lists eight agents,
  none security-facing).

Both rulings are about *coverage of content*. Neither asked whether the **pass**
— a dedicated, scheduled second run over finished code — exists in our cycle. It
does not.

## Level 2 — Capability profiles

### `code-simplification`

**Achieves** — reduces complexity in code that already works, with behaviour held
exactly constant, so the result is faster to comprehend rather than shorter.

**Can do**
- States the success test up front: "would a new team member understand this
  faster than the original?" and explicitly rejects line count as the goal
  (`SKILL.md:12`).
- Five principles: preserve behaviour exactly, with four questions to ask before
  every change (`SKILL.md:32-42`); follow project conventions, because
  "simplification that breaks project consistency is not simplification — it's
  churn" (`SKILL.md:44-59`); clarity over cleverness with two worked pairs
  (`SKILL.md:61-90`); **maintain balance**, naming four over-simplification traps
  (`SKILL.md:92-99`); scope to what changed (`SKILL.md:101-103`).
- **Chesterton's Fence** as step 1 — six questions including `git blame` for
  original context, and "if you can't answer these, you're not ready to simplify"
  (`SKILL.md:107-121`).
- Three signal tables (structural / naming / redundancy), each row a concrete
  pattern → signal → simplification, with thresholds (3+ nesting levels, 50+ line
  functions, 5+ duplicated lines) (`SKILL.md:123-156`).
- The comment rule split: delete comments explaining *what*, keep comments
  explaining *why* (`SKILL.md:144-145`).
- One-at-a-time application with a per-change test gate and revert-on-fail
  (`SKILL.md:157-169`); refactors submitted separately from features
  (`SKILL.md:159`).
- **The Rule of 500** — past 500 lines, invest in codemods/AST transforms instead
  of hand edits (`SKILL.md:171`).
- Step 4 whole-diff evaluation with an explicit revert option: "not every
  simplification attempt succeeds" (`SKILL.md:173-185`).
- Language-specific worked examples for TS/JS, Python, and React, including one
  case flagged as a judgment call not to auto-refactor (`SKILL.md:187-295`).
- Seven-row rationalization table, seven red flags led by "simplification that
  requires modifying tests to pass (you likely changed behavior)"
  (`SKILL.md:297-317`), and a nine-item verification checklist
  (`SKILL.md:319-331`).

**Pros (vs `security-and-hardening`)** — far better scoped: it says when *not* to
run (`SKILL.md:23-28`), bounds itself to recently changed code
(`SKILL.md:101-103`), and has a stop-and-revert path. Its content is
language-agnostic in structure with language examples appended, so the durable
part survives a stack change. Its behaviour-preservation gate (existing tests must
pass **without modification**, `SKILL.md:323`) is a mechanical check, not a
judgment call.

**Cons** — heavily overlaps guidance we already load on every task (AK guidelines
§2 simplicity, §3 surgical changes, §11 conventions), so as *content* the ledger's
"covered" ruling holds; its unique material is the trap list
(`SKILL.md:92-99`), Chesterton's Fence as a gate (`SKILL.md:107-121`), the
thresholded signal tables, and the Rule of 500. The TS/JS/React examples
(`SKILL.md:187-295`, ~110 lines) are dead weight for a Python-first repo.

### `security-and-hardening`

**Achieves** — hardens code touching untrusted input, identity, secrets, or
external systems, starting from a threat model rather than a control checklist.

**Can do**
- **Threat model first**: map trust boundaries (explicitly including LLM output as
  a boundary), name the assets, run STRIDE per boundary via a six-row table, and
  write abuse cases beside use cases — "if you can't name the trust boundaries for
  a feature, you're not ready to secure it" (`SKILL.md:22-40`).
- **Three-tier boundary system**: Always Do (8 non-negotiables), **Ask First**
  (7 changes requiring human approval — new auth flows, new sensitive-data
  categories, new integrations, CORS, uploads, rate limiting, privilege grants),
  Never Do (7 absolutes) (`SKILL.md:42-73`).
- OWASP prevention patterns with code: injection, auth/session cookies, XSS,
  broken access control (ownership check, not just authentication),
  misconfiguration/CSP/CORS, sensitive-data exposure (`SKILL.md:75-187`).
- **SSRF** with a working allowlist + resolve-all-records + private-range check,
  then honestly names the residual **TOCTOU gap** and the mitigations for
  high-risk surfaces (`SKILL.md:189-220`).
- Schema validation at boundaries and file-upload constraints incl. magic-byte
  checking (`SKILL.md:222-270`).
- **Dependency-audit triage decision tree** keyed on severity × reachability ×
  fix availability, with "when you defer a fix, document the reason and set a
  review date" (`SKILL.md:272-297`).
- **Supply-chain hygiene**: find the installation boundary and manager, stop on
  competing lockfiles, block dependency scripts before first execution and never
  blanket-approve, never auto-apply forced remediation, verify registry
  signatures, review lockfile diffs and typosquats together (`SKILL.md:299-310`).
- Secrets layout, a staged-diff grep, and the rotate-don't-scrub rule: a committed
  secret is compromised the moment it reaches a remote (`SKILL.md:332-354`).
- **LLM/AI attack surface** mapped to OWASP LLM Top 10 (2025): model output is
  untrusted input, the system prompt is not a security boundary, keep secrets and
  cross-tenant data out of context, constrain tool/agent permissions, bound
  consumption, partition RAG embeddings per tenant (`SKILL.md:356-382`).
- A copyable six-section review checklist (`SKILL.md:384-424`), eight
  rationalizations (`SKILL.md:429-441`), ten red flags (`SKILL.md:442-454`), and a
  nine-item verification list (`SKILL.md:455-468`).

**Pros (vs `code-simplification`)** — it is the only one of the two whose core is
a *method* rather than a catalogue: STRIDE-per-boundary (`SKILL.md:22-40`)
generates the checks for a system it has never seen, which is what makes it
survive a stack it does not have examples for. Its LLM section
(`SKILL.md:356-382`) covers a boundary our rules do not address at all, and it is
directly relevant to a repo whose product *is* agent tooling. Its Ask First tier
(`SKILL.md:54-63`) is a governance mechanism — a named set of changes that stop
for a human — which `code-simplification` has no equivalent of.

**Cons** — scope discipline is its weak point where the other's is strong: no
not-for list, and a trigger set (`SKILL.md:13-20`) broad enough to fire on most
feature work, which makes it a build-time constraint wearing a pass's
description. Roughly half its body is Express/Node/TypeScript-specific
(`SKILL.md:75-330`), the "stack-specific bulk" the 2026-07-15 deferral named. It
also leans on a sibling reference (`../../references/security-checklist.md`,
cited at `SKILL.md:77`, `:303`, `:427`) that would have to come with it.

## Verdict

**These two do not overlap each other.** Different axis, different failure mode,
different evidence: one preserves behaviour exactly and is checked by existing
tests passing unmodified (`code-simplification/SKILL.md:323`); the other
deliberately *changes* behaviour (rejecting input, adding checks) and is checked
by a boundary review (`security-and-hardening/SKILL.md:455-468`). They are
complements, and they share only their shape — a scoped pass with a
rationalization table, red flags, and a checklist.

**Which is stronger, and for what.** `code-simplification` is the better-built
*skill*: bounded, reversible, self-limiting, with a mechanical success criterion.
`security-and-hardening` is the more valuable *capability*: the cost of skipping
it is unbounded, and its threat-model method generates checks rather than listing
them. If only one entered our harness, security is the one with no substitute —
simplification duplicates guidance we already load, while nothing in our harness
performs a threat model.

**What our harness lacks — stated plainly.**

1. **No post-implementation pass exists in our cycle at all.**
   `phase-execution` runs plan → implement → gate → verify → report
   (`phase-execution/SKILL.md:23-88`); `subagent-driven-development` runs
   implement → spec review → code review → Codex review
   (`subagent-driven-development/SKILL.md:19-37`). Every one of those is a
   *judgment* step that ends in a verdict. Neither engine has a step that
   **changes code along a chosen axis after it is already correct**. Both these
   skills are that step, and we have no slot for one.

2. **No security capability of any kind.** We ship no security skill, no security
   agent (`inventory/ours/agent.csv`: eight agents, none security-facing), and no
   security command. The nearest coverage is `.claude/rules/python/safety.md`
   (parameterized queries, no `eval`, no `os.environ` in business logic, secrets
   via a manager, timeouts and bounded retries) and eleven lines of the
   `code-reviewer` agent's Python-first checks (`code-reviewer.md:30-41`). That is
   a **control list applied to Python code as it is reviewed** — it has no threat
   model, no trust-boundary mapping, no abuse cases, no authz-vs-authn
   distinction, no SSRF handling, no dependency-audit triage, no supply-chain
   policy, no secret-rotation rule, and nothing about LLM/agent attack surface.
   The 2026-07-15 deferral routed this to "an optional production-readiness
   plugin" that does not exist, so in practice the deferral is a gap.

3. **No Ask First tier.** Nothing in our harness enumerates changes that must stop
   for a human on *security* grounds. Our approval gates are process gates —
   plan approval (`phase-execution/SKILL.md:46`), commit authority (git-safety
   rule) — not risk-class gates.

4. **Simplification is guidance, not a pass.** `ak-guide` states the principles
   and is loaded on every task, which is why the ledger called
   `code-simplification` covered. But guidance loaded during construction and a
   pass run after it is working are different interventions: the pass can see the
   finished shape, and it is the only point at which "would a new team member
   understand this faster?" (`code-simplification/SKILL.md:12`) is answerable.
   What we lack is not the principles — it is the *occasion*.

5. **Concretely missing mechanisms**, none of which appear anywhere in our
   harness: STRIDE-per-boundary (`security:22-40`), the Ask First tier
   (`security:54-63`), the audit triage tree (`security:272-297`), supply-chain
   script-blocking (`security:299-310`), the LLM Top 10 mapping
   (`security:356-382`), Chesterton's Fence as a gate on touching code
   (`simplification:107-121`), the over-simplification trap list
   (`simplification:92-99`), and the Rule of 500 (`simplification:171`).

Level 3 component inventory and the cross-skill matrix: [`components.md`](components.md).

---

## Round 2 extension — `code-simplification` stale-claim re-audit

Added 2026-08-14. This folder owns the family (`code-simplification` is its
`SIMP` column), so the re-audit extends it rather than forking a new folder.

**Why re-audit.** The ledger entry reads:

> `skill:skills/code-simplification` — **adopted**, 2026-07-15,
> `our_id: skill:skills/ak-guide` — *"Covered by AK guidance on simplicity,
> surgical scope, convention matching, read-before-write, and verifiable
> behavior-preserving changes."*

That is a **family-level coverage assertion with a single named owner**, the
same claim shape that failed on `systematic-debugging`. Round 1 already
half-doubted it (`README:85-90`, `:195-201`) but argued the *occasion*, not the
components. This round checks all 45 components against the live consumers.

**The live consumers, established by grep, not assumption.** Only two files in
`.claude/` carry simplification behaviour:
`.claude/rules/core/03-ak-guidelines.md` (the ak-guide content, loaded on every
task per `CLAUDE.md`) and `.claude/skills/execution/references/task-engine.md`
→ *Simplification look* (`:199-205`). A third file carries a large slice
incidentally: `.claude/rules/python/coding-style.md`. Nothing in
`.claude/skills/performance-optimization/`, `.claude/skills/code-review/`, or
`.claude/project/verification.md` mentions simplification at all.

The full 45-row coverage table is in [`components.md`](components.md) →
*Round 2 extension*. Counts: **20 covered, 6 partial, 12 not covered, 3 N/A**
(TS/JS/React examples, correctly rejected for a Python-first repo).

### Verdict — the claim **fails as written**, for two independent reasons

**1. The attribution is wrong, and it is not a nitpick.** The ledger names
`ak-guide` as `our_id`. Measured against the actual file, `ak-guide` covers **6**
of the 45 components: convention conformance (`03-ak-guidelines.md:37`,
`:94-96`), the churn argument (`:94-96`), scope-to-what-changed (`:30-45`),
read-before-write (`:81-83`), orphan cleanup (`:41-43`), and the
rename-to-preference red flag (`:94-96`). Every other covered component is
carried by one of two files the ledger never mentions:

- **`task-engine.md:199-205`** — the Simplification look, which carries the
  success test (`:200-201`), Chesterton's Fence as a gate (`:201-202`),
  one-at-a-time with the tests-pass-unmodified check (`:203-204`), and the
  already-minimal skip (`:205`). This is the strongest coverage in the audit
  **and it did not exist on 2026-07-15** — it was written later, for the
  execution rebuild, not as a consequence of this ledger decision.
- **`.claude/rules/python/coding-style.md`** — the why-not-what comment rule
  (`:61-63`), the DRY threshold (`:47-49`, at 3+ lines *stricter* than SIMP's
  5+), naming conventions (`:53-56`), import ordering (`:80-82`), and error
  handling (`:86-88`).

So the entry was **directionally lucky rather than accurate**: it named an owner
that covers an eighth of the skill, and the file that actually covers it was
written a month later for unrelated reasons. Nothing in the harness points at
the ledger's stated owner as the place this capability lives.

**2. One component is not merely uncovered — it is counter-covered.** SIMP's
Principle 4 (`SKILL.md:92-99`) exists to name simplification's own failure mode,
and two of its four traps are *"removing 'unnecessary' abstraction — some
abstractions exist for extensibility or testability, not complexity"* (`:98`)
and *"optimizing for line count"* (`:99`). The file the ledger credits with
coverage pushes the agent directly into both: `ak-guide` §2 instructs *"No
abstractions for single-use code"* (`03-ak-guidelines.md:23`) and *"If you write
200 lines and it could be 50, rewrite it"* (`:26`) — the line-count framing SIMP
explicitly rejects at `SKILL.md:12`. On the single axis this skill exists to
guard, our named owner is the source of the risk, not the mitigation.

**What partially survives.** As a claim about the *harness* rather than about
ak-guide, "covered" holds for the durable half: behaviour preservation, scope
discipline, convention conformance, understand-before-touching, one-at-a-time
application, and the comment rule are all genuinely present with mechanisms at
least as strong as SIMP's, and in three cases stronger (our DRY threshold is
tighter, `coding-style.md:49`; our scope rule adds a report format ak-guide
calls `NOTICED BUT NOT TOUCHING`, `:39`; our dead-code stance at `:38` is a
deliberate and better-reasoned divergence). **The ledger should be corrected,
not reversed** — the decision to not install the skill still looks right; the
recorded reason does not.

### Uncovered components worth absorbing, ranked

1. **The over-simplification trap list** (`SKILL.md:92-99`) — highest value, for
   reason 2 above. This is the only item where absorbing costs nothing and *not*
   absorbing leaves an active contradiction.
2. **Side-effects and ordering in the behaviour-preservation gate**
   (`SKILL.md:40`) — our check is "tests pass unmodified" (`task-engine.md:203`),
   which is exactly the check that misses ordering and side-effect changes,
   because tests routinely do not assert them.
3. **The thresholded structural signal table** (`SKILL.md:127-136`) — 3+ nesting
   levels, 50+ line functions, nested ternaries, boolean flag params, repeated
   conditionals. Our Simplification look has a *criterion* (`:200-201`) but no
   scan list, so it asks a question with nothing to point it at.
   `coding-style.md:38` has file-size limits only — nothing at function or
   nesting grain.
4. **Clarity over cleverness as a stated principle** (`SKILL.md:61-63`) —
   ak-guide §2 governs code *quantity*, never *expression*. Nothing in our
   harness says explicit beats compact when compact needs a mental pause.
5. **"Removing error handling because it makes the code cleaner"**
   (`SKILL.md:314`, verification item `:329`) — a specific regression our
   tests-pass check will not catch on any path that is not covered.
6. **The Rule of 500** (`SKILL.md:171`) — one line, still absent, still cheap.

**Not a copy — a decision for the coordinator:** *refactors submitted separately
from features* (`SKILL.md:159`). This **conflicts with our current design**
rather than being missing from it: `task-engine.md:199` places the
Simplification look *inside* the scope, after the final review, so any
simplification it makes lands in the same diff and the same commit as the
feature. SIMP says that is two PRs. Ours is a defensible tradeoff for a
single-scope workflow, but it is an unstated one, and it should be stated.

### Natural absorption target

`.claude/skills/execution/references/task-engine.md` → **Simplification look**
(`:199-205`). It is already the live consumer, already carries four of SIMP's
components in compressed form, and already fires at the one occasion SIMP's
success test is answerable. Items 1–6 above fit in roughly eight added lines
there. Item 1 additionally wants a one-clause counterweight in
`.claude/rules/core/03-ak-guidelines.md` §2 (`:18-28`), because that is the file
generating the pressure — absorbing the trap list only into `task-engine.md`
would leave §2 pushing the wrong way on every non-deep task, which is most of
them.

**Recommendation for the coordinator: correct the ledger entry, then absorb
items 1–6 into the Simplification look.** Keep `status: adopted` (installing the
skill is still the wrong move — half of it is TS/React examples and our
mechanisms are stronger where they overlap), but rewrite the reason to name the
real owners (`task-engine.md` Simplification look + `coding-style.md` +
ak-guide) and to record what was *not* absorbed. Item 7 (refactor/feature
separation) is a design question, not an adoption: decide it, then state the
answer in `task-engine.md:199`.

### Round-1 claims this audit disproves

Flagged because they are load-bearing in the text above this line, which is left
unrewritten. All three were true when written and are now stale:

- **`README:168-175`** — *"No post-implementation pass exists in our cycle at
  all."* False since the execution rebuild: `task-engine.md:199-205` is exactly
  such a pass, scoped to deep work.
- **`components.md:229-233`** — *"none of our execution surfaces carries [a
  rationalization table]"*, listing `phase-execution`,
  `subagent-driven-development`, `run-phases`. False: those three were
  consolidated into `.claude/skills/execution/`, whose SKILL.md carries a
  six-row rationalization table at `:120-130`.
- **`README:176-188`** — *"No security capability of any kind."* False:
  `.claude/skills/security/SKILL.md` now ships threat-model-first (`:8`, `:20`),
  STRIDE over each boundary (`:31`), Ask-First gates (`:71`), and a
  rationalization table (`:185-186`). *NOTICED BUT NOT TOUCHING* — the
  `security-and-hardening` deferral is outside this audit's scope and deserves
  its own re-audit; the gap analysis at `README:176-188` and `:203-209` should
  not be cited as current.

Level 3 coverage table: [`components.md`](components.md) → *Round 2 extension*.
