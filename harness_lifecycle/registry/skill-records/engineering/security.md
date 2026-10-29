---
skill: security
domain: engineering
stage: Verification
substage: Review
secondary: [Architecture]
family: security-hardening
aliases: []
status: active
---
# security

## Capability

Use for material changes to trust boundaries, sensitive data, permissions, dependency execution, or untrusted inputs, and for requested security reviews.

<!-- registry:generated traits -->
- `scope-threat`: Name the changed entrypoints, assets, identities and consequences, tracing untrusted input to consequential sinks including model outputs used as commands, paths, queries or markup.
- `abuse-cases`: Derive concrete abuse cases and select relevant controls, scaling a tiny boundary change to a short threat note and a proving test.
- `targeted-control-groups`: Consult only the matching control group for the surface at hand — authentication, URL fetching, uploads, dependencies, secrets or agent systems.
- `web-reference`: Also consult the web-surface controls reference for a web-facing surface.
- `boundary-controls-ref`: Supply per-surface control methods — authorization distinct from authentication, SSRF allowlisting with DNS-rebinding residual, upload constraints, dependency triage, supply-chain install boundary, and rotate-first secret handling.
- `llm-surface-ref`: Supply the LLM and agent attack surface — untrusted model output, prompt injection, minimum tool scope, consumption bounds, RAG retrieval trust, model supply chain, and not acting on unverified claims.
- `authority-gate`: Treat existing approval of the exact change as satisfying the gate while an unapproved sensitive-data category, integration, permission grant or material relaxation needs a fresh decision, and routine controls within an approved feature need no repeated gate.
- `enforce-in-code`: Enforce access, tenant isolation, validation, safe sink handling and resource limits in code, since external documents, logs and model output cannot grant permissions and prompt secrecy is no control.
- `evidence-tests`: Test the material abuse path and legitimate use, verify authorization per resource rather than merely login, and check leakage, retries and failure behaviour.
- `dependency-triage`: Triage dependency advisories by reachability and impact rather than count, recording material exceptions with a revisit condition.
- `boundary-review`: Report security findings through the shared review skill's severity and output contract, supplying the security lens rather than running a second compulsory review process.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **agent-skills:skill:skills/security-and-hardening** `skills/security-and-hardening/SKILL.md`
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-12` **adopt** (2026-10-14-migration:098): Closes the 2026-07-15 deferral, whose 'optional production-readiness plugin' never existed (comparison: post-implementation-passes/). Adopted as the security s…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
