---
skill: harness-scan
domain: core
stage: Improvement
substage: Codification
secondary: []
family: 
aliases: []
status: active
---
# harness-scan

Scan a reference harness for material upstream drift and missing capabilities.

**Boundary:** Finds drift and unruled candidates in one reference harness and reports them; the decision is harness-evaluate, and the quick view across all harnesses is harness-status.

<!-- registry:generated traits -->
- `resolve-target`: Resolve the named reference harness or path, asking only when it is ambiguous.
- `drift-scan`: Run the drift scan to surface upstream changes since our pin.
- `gap-report`: Run the gap report for capabilities never ruled on, changed upstream since their ruling, or held but never ruled on.
- `material-report`: Report the material drift and useful candidates against existing equivalents.
- `upstream-review-on-pin-move`: When the submodule pointer moves, write the upstream review in the same change and regenerate the catalog at the new pin.
- `beads-followup`: Let the gap command print tracker-create lines to review by hand, never auto-running them, and only within filing authority.
- `pin-preserving-fetch`: Fetching upstream refs updates only the local cache and never moves pinned submodule commits, with a no-fetch option to skip the network when offline.
- `reject-valid`: Treat reject or defer as a valid outcome when a candidate adds no durable behavioural value.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
No adopted lineage recorded.
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
No ledger history recorded.
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
