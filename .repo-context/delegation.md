# Delegation

Read before dispatching workers or independent reviewers.

- Use the available, permitted delegation interface and user-selected or configured
  models/effort. If unavailable, continue locally and report any required review
  that could not run; do not bypass runtime restrictions.
- Assign a bounded outcome, owned files, constraints, acceptance criteria, and
  required checks. Supply relevant context and artifact pointers, not raw session
  history. Tell workers to preserve others' edits.
- Parallel tasks must be independently understandable and completable without
  shared mutable state or overlapping writes. Otherwise sequence them. The parent
  handles different work while workers run; avoid duplicate exploration.
- Name dispatches, collect every result, inspect changed artifacts, resolve
  integration conflicts, and verify the combined result before claiming completion.

## Independent critique

Use a fresh reviewer separate from the author. Review against requirements and
evidence. Use the user-selected or configured reviewer model; ask if neither
provides a selection. The coordinator owns disposition of findings and final claims.

## Workflow risk labels

When planning or execution needs a label: `small` is bounded, low-risk work;
`standard` is a bounded behavior change; `deep` is cross-cutting, high-risk, or
materially unresolved work. Labels select paths inside those workflows, not a
mandatory pipeline for every task.
