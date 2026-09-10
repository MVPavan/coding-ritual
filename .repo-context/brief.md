# Project Brief

**coding Ritual** is a meta-repository — a workspace for building and maintaining
reusable agent harnesses (Claude Code + Codex), studying strong third-party
reference harnesses, and consolidating the resulting learnings in one place.
It also contains the first-party Python workflow interpreter and its test suite.
Read this brief for project purpose; use `repo-map.md` for navigation.

## What lives here

- `workflow_interpreter/` and `tests/` — workflow loading, execution, supervision,
  runtime profiles, and verification.
- `workflows/`, `config/`, and `docs/` — workflow definitions, configuration,
  specifications, architectural decisions, and workstream plans.
- `.repo-context/` — shared repository guidance and domain vocabulary.
- `.claude/` — canonical shared skills, agent definitions, and Claude hooks;
  `.codex/` supplies Codex integration.
- `mvp-harness/` — the harness marketplace submodule, with plugins under `plugins/`:
  - `mvp-plugin/` — the reusable harness installer (`/mvp-plugin:adopt` copies the
    `.claude` + `.codex` setup, rules, hooks, and beads tracking into any repo).
    This repo was itself adopted with it.
  - `codex-adapter/` — bridges Claude Code to Codex via `codex exec`.
  - `code-intel/` — graph-first code intelligence plugin (serena + CBM + ast-grep).
- `harness_learnings/` — the synthesized canon and best-practice docs.
- `reference_harnesses/` and `reference_tools/` — third-party **git submodules**
  (read-only references; never copied into the local harness).

## Stack

Python for the interpreter and tooling, Markdown for harness instructions and
design documents, Bash for scripts/hooks, and Node.js for the Codex bridge.
Dependency constraints live in `pyproject.toml` and plugin manifests; applicable
checks live in `.repo-context/verification.md`.

## Constraints / non-negotiables

- Repo-relative paths only — never commit machine-local absolute paths.
- Reference repos stay as submodules; edits require the authorization described
  in `AGENTS.md`.
- Borrow only the smallest durable pattern that improves the harness.
- Plugin manifests (`plugin.json`, `marketplace.json`) must stay valid JSON.
- `scratchpad/` is gitignored throwaway — never commit it.
