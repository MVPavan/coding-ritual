---
name: harness-evaluate
description: Use when evaluating a reference-harness capability for adoption, rejection, deferral, or synchronization. Inspection alone does not authorize adoption.
---

# Harness Evaluate

Evaluate a reference capability against the maintained shared harness. Read the
candidate's canonical source, relevant prior ledger decision and closest local
implementation. Reference repositories remain read-only evidence.

Compare behavioral gain, overlap, dependencies, context cost and maintenance.
Choose reject/defer, merge into an existing capability, a separate plugin for a
distinct dependency/domain boundary, or shared template adoption for broadly
useful low-cost guidance. Use harness-skill-compare for a substantive comparison.

Evaluation alone produces a recommendation. Record a curation decision only when
ledger changes are authorized:

```text
python3 harness_lifecycle/gap.py ledger add --repo <repo> --id <logical_id> --status <rejected|deferred> --reason <evidence>
```

Authorized adoption edits the actual canonical source. Shared policy belongs in
AGENTS.md and shared skills/project docs; Codex integration links or adapts them.
Do not duplicate semantic edits across provider directories. Inspect current sync
and publish manifests before selecting destination; template output is generated.

For template adoption, verify the initialized mvp-harness tools exist, run
`check-sync.sh` and `build-template.sh` under its mvp-plugin scripts directory,
and inspect neutrality/leak results. Obtain independent review when the broad
blast radius warrants it under shared delegation policy. New/existing plugin
implementation also requires authorization for that submodule work.

Record adoption with `--status adopted --our-id <local-id> --source-sha <ref-sha>`
and a source-backed reason only after the adopted state exists. Publication,
commits and pointer updates require their own existing authority; otherwise
report the prepared result. Borrow the smallest useful pattern.
