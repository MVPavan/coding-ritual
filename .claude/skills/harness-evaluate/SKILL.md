---
name: harness-evaluate
description: Use when a reference-harness capability surfaced by /harness-scan drift or gap output needs a curation decision recorded in the ledger, or when an already-adopted capability needs syncing back. Use when curating reference_harnesses/* into mvp-harness.
---

# Harness Evaluate

The judgement half of the reference-harness lifecycle. Input: one capability
(skill / command / agent / rule / hook / mcp) surfaced by `/harness-scan`. Output:
a routing decision recorded in the ledger, and — if adopted — the sync-back done.

## 1. Understand the candidate

- Read the capability's canonical file(s) under `reference_harnesses/<repo>/`.
- Read our closest equivalent (use the gap report's "similar to ours" hint, or
  search `.claude/` + `mvp-harness/plugins/`). Is it genuinely new, or a variant
  of something we already ship?

## 2. Route it — apply in order, first that fits wins (default = reject/defer)

- **Reject / defer** *(the default)*: giant catalogs, repo/org-specific assumptions,
  duplicate wording with no behavioural gain, or anything adding always-on context
  cost without clear value. Rejection is a successful outcome.
- **Merge into an existing plugin**: same job-to-be-done and same dependency
  boundary as `code-intel` or `codex-adapter`.
- **New standalone plugin**: a distinct capability with an external tool / MCP /
  binary / credential dependency, or a domain-specific workflow (the
  `codex-adapter` / `code-intel` archetype).
- **Fold into the mvp-plugin template**: only if ALL hold — useful in ~every repo,
  low/zero external dependency, small context cost, and it can live on **both** the
  `.claude` and `.codex` sides (or is declared claude-only in the sync manifest).

Produce a short comparison: what theirs does, what ours does (if any), dependencies,
context cost, overlap, and the recommended route with a one-line rationale. A
**template** route has the widest blast radius — get a Codex second opinion via
`/codex-critique` before writing.

## 3. Execute the decision

- **Reject / defer** → record only:
  `python3 harness_lifecycle/gap.py ledger add --repo <repo> --id <logical_id> --status rejected|deferred --reason "..."`
- **Adopt → template**:
  1. Edit the canonical source under `.claude/` **and** `.codex/` (never edit
     `mvp-harness/.../template/` — it is generated).
  2. `bash mvp-harness/plugins/mvp-plugin/scripts/check-sync.sh` — reconcile drift.
  3. `bash mvp-harness/plugins/mvp-plugin/scripts/build-template.sh` — must end with
     "no project/machine-specific strings".
  4. Commit mvp-harness; bump the submodule pointer in coding-ritual.
  5. Ledger: `... --status adopted --our-id <our_logical_id> --source-sha <ref commit> --reason "..."`.
- **Adopt → new / existing plugin** → implement under `mvp-harness/plugins/`, then
  ledger as adopted with the plugin as `--our-id`.

## Guardrails

- Reference harnesses are read-only inspiration — never edit submodule internals.
- No adoption without a ledger entry (so the gap report stops re-nagging).
- Borrow the smallest durable pattern; do not import whole workflows.
