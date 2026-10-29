---
skill: check-invariants
domain: engineering
stage: Verification
substage: Testing
secondary: []
family: 
aliases: []
status: active
---
# check-invariants

## Capability

Run mechanically checkable invariants from the project overlay and report pass or fail.

<!-- registry:generated traits -->
- `read-overlay`: Read the project's declared invariants file and run each listed check against the current tree.
- `explicit-commands-only`: Run only invariants that carry an explicit runnable command, leaving everything else unexecuted.
- `pass-fail-report`: Report a plain pass or fail result for each invariant that was run.
- `skip-aspirational`: Name and skip any invariant that is aspirational rather than mechanically checkable instead of guessing a verdict.
- `repo-relative-paths`: Present every result using repository-relative paths only.
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
