# coding Ritual

This repo is a workspace for building and maintaining reusable agent harnesses
(Claude Code + Codex), studying strong reference harness repos, and keeping the
resulting learnings in one place. It is a meta-repo — there is no first-party
application code.

## Main Areas

- `my_harness/` — the harness plugins under active development:
  - `mvp-plugin/` — the reusable harness installer. `/mvp-plugin:adopt` copies the
    `.claude` + `.codex` setup, rules, hooks, and beads tracking into any repo.
  - `codex-adapter/` — call OpenAI Codex (`gpt-5.x`) from Claude Code via `codex exec`.
  - `code-intel/` — graph-first code intelligence plugin (serena + CBM + ast-grep).
- `harness_learnings/` — the synthesized canon, collaboration notes, and reference
  repo learnings.
- `reference_harnesses/` — third-party harness repos tracked as **git submodules**
  (read-only references).
- `.agents/skills/refresh-harness-from-reference/` — local skill for evaluating a
  new reference repo and selectively improving the local harness.
- `.claude/` + `.codex/` — the harness installed into this repo itself (rules,
  skills, agents, commands, hooks, and the `project/` overlay of repo facts).
- `.beads/` — Beads issue tracker store (see `.beads/beads.md`).

## Read First

1. `harness_learnings/coding-harness-best-practices.md`
2. `harness_learnings/claude-codex-collaboration.md`
3. `harness_learnings/reference-harness-workflow.md`
4. `.claude/project/brief.md` — repo facts for agents

## Common Workflows

### Work on the reusable harness

Start in `my_harness/mvp-plugin/` and use `harness_learnings/` as the design
reference.

### Add or update a reference repo

Follow `harness_learnings/reference-harness-workflow.md`.

### Refresh the local harness from a new reference repo

Use:

```text
Use $refresh-harness-from-reference to evaluate reference_harnesses/<repo-name> and selectively update harness_learnings plus my_harness.
```

## Reference Repo Policy

Reference repos stay under `reference_harnesses/` as git submodules — clean
external references, never copied into the local harness. Borrow only the
smallest durable pattern that improves the harness.
