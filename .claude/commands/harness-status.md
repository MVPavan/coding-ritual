---
description: Quick upstream-drift status across all reference_harnesses submodules — what changed since our pinned commits. Read-only (fetches, never moves pins).
---

# Harness Status

Report, per reference harness, whether upstream has material changes since our pin.

## Steps

1. For each directory under `reference_harnesses/`, run:
   `python3 harness_lifecycle/scan.py drift <dir>`
   (fetches origin, compares our pinned commit to upstream HEAD; pass `--no-fetch`
   to skip the network and use already-fetched refs.)
2. Summarise as a table: repo | added | removed | changed (material) | minor.
3. Call out repos with material changes as candidates for `/harness-scan`.

## Rules

- Read-only: never run `git submodule update` or anything that moves a pinned commit.
- If a fetch fails (offline), note it and continue with the other repos.
- Keep output to the summary table plus a one-line recommendation; do not dump full diffs.
