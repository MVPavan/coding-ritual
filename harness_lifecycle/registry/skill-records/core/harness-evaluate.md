---
skill: harness-evaluate
domain: core
stage: Improvement
substage: Codification
secondary: []
family:
aliases: []
status: active
---
# harness-evaluate

Use when evaluating a reference-harness capability for adoption, rejection, deferral, or synchronization. Inspection alone does not authorize adoption.

**Boundary:** Decides one reference capability (adopt, reject, defer, sync); finding candidates is harness-scan, and a deep side-by-side analysis is harness-skill-compare.

<!-- registry:generated traits -->
- `read-first`: Before judging a candidate, read its canonical source, the relevant prior ledger decision and the closest local implementation, keeping reference repositories as read-only evidence.
- `decision-dimensions`: Weigh a candidate on behavioural gain, overlap, dependencies, context cost and maintenance.
- `disposition-choice`: Choose among reject or defer, merge into an existing capability, a separate plugin for a distinct dependency or domain, or shared-template adoption for broadly useful low-cost guidance.
- `recommendation-vs-record`: Treat evaluation as yielding only a recommendation and record a curation event solely under authorization, one per capability in the open round.
- `record-command`: Append a curation decision with the registry record command carrying its kind, subject, reason and evidence.
- `edit-canonical-source`: Make an authorized adoption edit the one canonical source, placing shared policy in the shared files without duplicating it across provider directories.
- `template-adoption-gate`: For template adoption, verify the initialized template tools, run the sync and template-build scripts, and inspect the neutrality and leak results.
- `material-risk-review`: Route an artifact or change with material risk or a broad blast radius through an independent critic review before it is accepted.
- `adopt-after-state-exists`: Record an adopt or adopt-merged event only after the adopted state exists, passing the adaptation as JSON for a merge, then update the skill's record.
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
