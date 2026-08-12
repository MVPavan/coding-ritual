---
name: security
description: Use when building or changing anything that crosses a trust boundary — untrusted input, authentication or authorization, secrets, file uploads, webhooks, external integrations, dependency changes, or LLM/agent features — and when a security review of such code is requested.
---

# Security

Start from a threat model, not a control checklist: a method generates the
checks for code it has never seen; a checklist only covers what it lists.
Python-specific controls live in `.claude/rules/python/safety.md` — this
skill decides *what to check and when to stop*; that rule says *how* in this
stack.

**Ownership boundary:** this skill owns pre-implementation work — the threat
model, the Ask-First gates, and control selection while building. Review of
an implemented diff belongs to the **code-review skill**: the checklist below
runs there as an additional lens under code-review's severity and output
contract, never as a competing second review protocol.

## Threat model first

Five minutes, before hardening anything:

1. **Map the trust boundaries.** Where does untrusted data enter? HTTP
   requests, CLI args, file uploads, webhooks, third-party API responses,
   message queues, fetched docs/pages — and **LLM output**. Every boundary
   is attack surface.
2. **Name the assets.** What is worth stealing or breaking here —
   credentials, PII, tokens, admin actions, the working tree an agent can
   edit.
3. **Run STRIDE over each boundary** — a lens, not a ceremony:

   | Threat | Ask | Typical mitigation |
   | --- | --- | --- |
   | **S**poofing | Can someone impersonate a user/service? | authentication, signature verification |
   | **T**ampering | Can data be altered in transit/at rest? | integrity checks, parameterized queries, TLS |
   | **R**epudiation | Can an action be denied later? | audit logging of security events |
   | **I**nformation disclosure | Can data leak? | encryption, field allowlists, generic errors |
   | **D**enial of service | Can it be overwhelmed? | rate limits, input size caps, timeouts |
   | **E**levation of privilege | Can a user gain rights they shouldn't? | authorization checks, least privilege |

4. **Write abuse cases next to use cases** — "how would I misuse this?"
   becomes the first test (the TDD skill's Prove-It pattern applies to abuse
   cases too).

If you cannot name the trust boundaries for a feature, you are not ready to
secure it — say so instead of decorating it with controls.

## The three tiers

**Always (no exceptions):** validate all external input at the system
boundary with the repository's established validation mechanism (schema
models such as Pydantic where the repo has adopted them); parameterize every
query; encode output for its sink; hash passwords with argon2/scrypt/bcrypt;
TLS for external communication; for web-facing services, baseline security
headers (CSP, HSTS, X-Content-Type-Options) and httpOnly/secure/sameSite
session cookies; run the package manager's native audit against the
committed lockfile before release.

**Ask first (stop for the human — a risk-class gate, not a process gate).**
Explicit approval of the exact change in the active request, spec, or
approved plan satisfies this gate — do not stop again for what the user
already approved. Otherwise stop *before implementing* and present: the
boundary, the assets, the abuse cases, the proposed controls, the residual
risk, and the security tests; resume only on explicit approval. The classes:

- new authentication flows or changes to auth logic
- storing a new category of sensitive data (PII, payment, credentials)
- new external service integrations
- relaxing or removing CORS restrictions, security headers, or cookie
  attributes (adding baseline protections is Always, not Ask-First)
- new file-upload, webhook, or callback handlers
- changes to rate limiting or throttling
- granting elevated permissions or roles — to users **or to agents/tools**

**Never:** secrets in code, config files, git, or logs; trusting client-side
validation as a boundary; `eval`/`exec`/unsafe deserialization on untrusted
input; sessions or tokens in client-accessible storage; internal errors or
stack traces exposed to users.

## Boundary controls (method, not catalogue)

- **AuthZ is not authN.** Every protected operation checks *ownership or
  role*, not just a valid login. "Authenticated" answers who; it never
  answers whether they may touch this resource.
- **SSRF** — any server-side fetch of a URL the user influenced (webhooks,
  import-from-URL, previews): allowlist scheme + host; resolve **all** DNS
  records and reject any private/reserved address (loopback, link-local
  `169.254.169.254` cloud metadata, RFC-1918, unique-local); forbid
  redirects. Know the residual TOCTOU gap: DNS can rebind between check and
  connect — for high-risk surfaces pin the resolved IP or front with a
  filtering proxy.
- **Uploads:** constrain type by magic bytes (never extension alone), cap
  size, store outside the web root under generated names.
- **Dependency audit triage** — an advisory is not a verdict; triage by
  severity × reachability × fix availability: critical/high + reachable in
  any runtime/build/test path → fix now; fix exists → take the patched
  version; no fix → workaround, replacement, or allowlist **with a review
  date**; moderate reachable → next release; dev-only/low → backlog. Every
  deferral is documented with its reason and date.
- **Supply chain:** first *find the installation boundary* — the workspace
  root that owns the lockfile, corroborated by the manager declaration and
  what CI actually runs; stop on disagreement or competing lockfiles. Then:
  block dependency install scripts before first execution and approve only
  the minimum, never blanket-approve; never auto-apply forced audit
  remediation; verify registry signatures/provenance where the manager
  supports it; review new dependencies, lockfile diffs, and script-policy
  changes together (ownership, provenance, release age, typosquats).
- **Secrets:** via a secrets manager per `safety.md`; grep the staged diff
  for credential patterns before any commit; **a committed secret is
  compromised the moment it reaches a remote — rotate first, then purge;
  deleting the line is not remediation.**

## LLM / agent attack surface

Directly relevant here — this repo's product is agent tooling. Mapped to the
OWASP LLM Top 10 (2025):

- **Model output is untrusted input (LLM05).** Never pass it *directly* into
  `eval`, SQL, a shell, a file path, or rendered markup. Parse defensively,
  validate against a schema, then apply the sink-specific control:
  parameterized queries for SQL, argv APIs (never shell interpolation) for
  commands, canonicalized allowlisted paths for files, sanitized/escaped
  markup for rendering.
- **Prompts can be hijacked (LLM01).** Any untrusted text in the context
  window — a user message, fetched page, doc, tool result — can carry
  instructions. The system prompt is **not** a security control: enforce
  permissions in code, and never let security depend on prompt
  confidentiality (LLM07).
- **Keep secrets, tenant data, and authoritative permission rules out of
  prompts (LLM02/LLM07).** Anything in the window can be echoed back; a
  system prompt is ordinary context, not a vault.
- **Constrain tool/agent permissions (LLM06).** Minimum tool scope;
  confirmation for destructive or irreversible actions; validate every tool
  argument like any untrusted input.
- **Bound consumption (LLM10).** Cap tokens, request rate, and
  loop/recursion depth so a crafted input cannot run up cost or hang the
  system.
- **Guard retrieval (LLM08).** In RAG, the vector store is a trust boundary:
  authorization-aware retrieval, tenant-scoped partitions or namespaces, and
  validation of documents before indexing so poisoned content cannot steer
  answers.
- **Model supply chain (LLM03/LLM04).** Models, adapters, datasets, and
  plugins get the same provenance and version review as code dependencies;
  authenticate and validate ingestion sources, and re-evaluate after data or
  model changes.
- **Don't act on unverified model claims (LLM09).** High-impact claims get
  checked against authoritative sources; consequential actions get human
  review.

## Review checklist

Run over the changed surface (skip sections with no such boundary — but say
so, don't silently omit):

- **AuthN/AuthZ**: modern password hashing; sessions httpOnly/secure/
  sameSite; login rate-limited; password-reset tokens expire; every
  protected endpoint checks ownership or role.
- **Input**: schema validation at every boundary; queries parameterized;
  output encoded; server-side fetches allowlisted.
- **Data**: no secrets in code/git/logs; sensitive fields excluded from
  responses; PII encrypted at rest where stored; internal errors not
  exposed.
- **Supply chain**: authoritative lockfile + frozen install in CI; audit
  triaged by reachability; install scripts blocked unless approved.
- **LLM/agent** (if present): output treated as untrusted; secrets and
  cross-tenant data out of prompts; tool permissions scoped; consumption
  bounded.

## Red flags

- Untrusted input reaching a query, shell, template, or `eval` unmediated
- An endpoint that authenticates but never authorizes
- A server fetching a user-influenced URL with no allowlist
- Secrets in source, git history, or logs
- Competing lockfiles, blanket-approved install scripts, forced auto-remediation
- LLM output flowing unvalidated into a query, DOM, shell, or file path
- Secrets, tenant data, or authoritative permission rules inside prompts —
  or any security control that depends on the prompt staying confidential
- A security fix without a test reproducing the abuse case

| Rationalization | Reality |
| --- | --- |
| "It's an internal tool" | Internal tools get compromised; attackers target the weakest link. |
| "We'll add security later" | Retrofitting is 10x the cost. The threat model is five minutes now. |
| "Threat modeling is overkill here" | Then it will take two minutes. Most breaches begin in design, not code. |
| "It's just LLM output — it's only text" | That text can be a SQL statement, a shell command, or markup. |
| "The audit passed, so the dependency is safe" | Audits match known advisories; they cannot see a fresh malicious package or unreviewed install script. |
