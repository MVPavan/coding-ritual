---
skill: harness-status
domain: core
stage: Improvement
substage: Codification
secondary: []
family:
aliases: []
status: active
---
# harness-status

Quick upstream-drift status across all reference_harnesses submodules — what changed since our pinned commits. Fetches upstream refs without moving pinned commits.

**Boundary:** Summarises drift across every reference harness in one table without moving pins; candidates within one harness are harness-scan.

<!-- registry:generated traits -->
- `drift-scan`: Run the drift scan to surface upstream changes since our pin. (Run for every submodule under the reference harnesses directory.)
- `summary-table`: Summarise the result as a table of repo, added, removed, material-changed and minor.
- `scan-candidates`: Flag the repos with material changes as candidates for a deeper scan.
- `pin-preserving-fetch`: Fetching upstream refs updates only the local cache and never moves pinned submodule commits, with a no-fetch option to skip the network when offline.
- `offline-continue`: On a failed fetch, note it and continue with the remaining repos.
- `concise-output`: Keep status output to the table plus a one-line recommendation, never dumping full diffs.
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
