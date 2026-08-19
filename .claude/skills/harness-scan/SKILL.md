---
name: harness-scan
description: Deep scan of one reference harness — what changed upstream AND what it ships that our harness doesn't — then route candidates via the harness-evaluate skill.
disable-model-invocation: true
---

# Harness Scan

Argument: a reference harness name (e.g. `superpowers`) or path under
`reference_harnesses/`. If none is given, ask which one.

## Steps

1. **What changed upstream** — `python3 harness_lifecycle/scan.py drift reference_harnesses/<name>`.
2. **What they have that we don't** — `python3 harness_lifecycle/gap.py gap reference_harnesses/<name>`
   (decisions already in the ledger are excluded automatically).
3. Present the material changes and the gap candidates. For each candidate worth
   pursuing, invoke the **harness-evaluate** skill to decide template / new-plugin /
   merge / reject.
4. To track chosen candidates as work, run the gap command with `--beads` to get
   ready-to-run `bd create` lines, and file them **only after** the user approves.

## Rules

- Read-only against the submodule; scans never move pins.
- Default to *reject/defer*: surface a candidate for adoption only if it clearly
  beats, or fills a gap in, what we already ship.
- Record every decision in the ledger (`gap.py ledger add`) so it is not re-surfaced.
