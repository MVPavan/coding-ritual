---
name: document-review
description: Use when a spec or plan document exists and needs a focused review for gaps, scope bloat, missing constraints, or risky assumptions. To interrogate the author about the plan instead, use grilling.
---

# Document Review

Review the document itself before using it as a source of truth.

## Workflow

1. Read the document and classify it as spec or plan.
2. Check it against current repo context and any authoritative project docs.
3. Look for:
   - internal inconsistency
   - missing constraints or unverifiable claims
   - scope bloat
   - missing tests or verification
   - security, data, or performance risks when relevant
4. Fix obvious wording or structure issues inline when the correction is unambiguous.
5. Surface decision-level issues instead of silently rewriting intent.
6. For standard/deep documents, get an independent critique from a spawned Opus 5 medium Claude subagent — once per document unless it is unusually risky.
