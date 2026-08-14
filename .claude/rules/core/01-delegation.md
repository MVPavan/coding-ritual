# Delegation

Use delegation to reduce context pressure, not to add ceremony for its own sake.

- The coordinator owns scope classification, planning, context curation, review, and final synthesis.
- The worker owns bounded execution inside a clear file and behavior scope.
- Use a fresh worker per task.
- Do not pass raw session history to workers. Pass the exact task, files, invariants, and verification commands they need.
- Do not run multiple implementers in parallel against the same files.
- Parallel dispatch requires an explicit independence check first: each task must be understandable and completable without the others' context, with no shared files or state. Unsure → sequential.
- When parallel workers return, close the fan-out: read each summary, scan for cross-agent conflicts (did two workers touch the same code?), then run verification on the combined result and spot-check — agents make systematic errors.
- Give every background or parallel dispatch a short descriptive name so its results are attributable.
- `standard` and `deep` work defaults to coordinator plus worker. `small` work can stay inline.
