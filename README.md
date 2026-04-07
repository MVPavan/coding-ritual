# Coding Setup

This repo is a workspace for building and maintaining a reusable coding harness, studying strong reference harness repos, and keeping the resulting learnings in one place.

## Main Areas

- `project_agnostic_claude_setup/` — the reusable local harness template
- `harness_learnings/` — the synthesized canon, collaboration notes, and reference repo learnings
- `reference_harnesses/` — third-party harness repos tracked as references
- `.agents/skills/refresh-harness-from-reference/` — project-local skill for evaluating a new reference repo and selectively improving the local harness
- `bodha_claude_setup/` — earlier project-specific harness reference

## Read First

1. `harness_learnings/coding-harness-best-practices.md`
2. `harness_learnings/claude-codex-collaboration.md`
3. `harness_learnings/reference-harness-workflow.md`

## Common Workflows

### Work on the reusable harness

Start in `project_agnostic_claude_setup/` and use `harness_learnings/` as the design reference.

### Add or update a reference repo

Follow:

- `harness_learnings/reference-harness-workflow.md`

### Refresh the local harness from a new reference repo

Use:

```text
Use $refresh-harness-from-reference to evaluate reference_harnesses/<repo-name> and selectively update harness_learnings plus project_agnostic_claude_setup.
```

## Reference Repo Policy

Reference repos should stay under `reference_harnesses/` and be managed as submodules or other clean external references, not copied into the local harness.

Borrow only the smallest durable pattern that improves the harness.
