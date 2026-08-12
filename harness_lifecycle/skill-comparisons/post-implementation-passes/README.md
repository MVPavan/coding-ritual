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
