# Repository Contracts

Read the contracts affected by the change. Authority and Git safety live in
`AGENTS.md`; checks live in `.repo-context/verification.md`.

- **Valid manifests:** plugin and marketplace manifests must parse as JSON.
- **Shared skill catalog:** generated routing and `agents/openai.yaml` invocation
  policies match canonical skills; slash and shared-context references resolve.
  Check: `python3 .claude/scripts/skill-catalog.py --check`.
- **Canonical workflow pins:** `content_hash` is SHA-256 of `canonical_bytes()`
  from `workflow_interpreter/schema/loader.py`, never authored TOML. The resolved
  model uses sorted JSON keys, aliases, omitted nulls and `wf-canon-json/1`.
  Reuse this canonicalizer for pinning and verification; do not recreate it.

## Accepted decision boundaries

Consult `docs/adr/README.md` and the relevant decision before changing semantics:

| Change | Governing ADR |
|---|---|
| Declared-path exemptions versus containment | `docs/adr/0001-allowed-paths-is-advisory.md` |
| Pinned node instructions and rendering | `docs/adr/0002-node-instructions.md` |
| Payload transport and resolved shared methods | `docs/adr/0003-large-payloads-and-shared-methods.md` |
| Deterministic routing and model-gate deferral | `docs/adr/0004-deterministic-routing.md` |

The ADRs own rationale and exceptions; this index does not replace their contracts.
