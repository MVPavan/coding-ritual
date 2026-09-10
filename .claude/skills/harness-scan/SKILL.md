---
name: harness-scan
description: Scan a reference harness for material upstream drift and missing capabilities.
disable-model-invocation: true
---

# Harness Scan

Resolve the named reference harness or path; ask only when ambiguous.

1. Run `python3 harness_lifecycle/scan.py drift reference_harnesses/<name>`.
2. Run `python3 harness_lifecycle/gap.py gap reference_harnesses/<name>`.
3. Report material drift and useful candidates, considering existing equivalents.
   Use harness-evaluate for an authorized curation decision.

Scanning does not authorize ledger mutation or adoption. When filing follow-up
work is authorized, `gap.py gap ... --beads` supplies creation commands to review.
Record decided outcomes in the ledger only within that authority.

These commands preserve submodule pins. Drift may fetch upstream refs; use its
`--no-fetch` option when offline or network access is outside the request.
Reject/defer is a valid outcome when a candidate adds no durable behavioral value.
