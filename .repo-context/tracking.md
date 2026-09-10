# Issue Tracking

This repo uses **bd (beads)** for durable issue tracking.

- **Policy:** `.beads/beads.md` owns task lifecycle, attribution, and closeout.
- **Current state:** use `bd show <id>`, `bd list`, or `bd ready`; this document
  does not snapshot task counts or status.
- **Storage:** the resolved Beads workspace owns the live database;
  `.beads/issues.jsonl` is its committed review/recovery mirror, not live state.
- **Configuration:** inspect `.beads/config.yaml` and the resolved workspace
  when diagnosing tracking. Do not infer backend or sync settings from old reports.

Run `bd prime` when runtime context is missing or needs recovery.
