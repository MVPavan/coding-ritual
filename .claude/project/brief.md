# Project Brief

**coding Ritual** is a meta-repository — a workspace for building and maintaining
reusable agent harnesses (Claude Code + Codex), studying strong third-party
reference harnesses, and consolidating the resulting learnings in one place.
It is **not** an application; there is no first-party product code and no CI.

## What lives here

- `my_harness/` — the harness plugins under active development:
  - `mvp-plugin/` — the reusable harness installer (`/mvp-plugin:adopt` copies the
    `.claude` + `.codex` setup, rules, hooks, and beads tracking into any repo).
    This repo was itself adopted with it.
  - `codex-adapter/` — calls OpenAI Codex (`gpt-5.x`) from Claude Code via `codex exec`.
  - `code-intel/` — graph-first code intelligence plugin (serena + CBM + ast-grep).
- `harness_learnings/` — the synthesized canon and best-practice docs.
- `reference_harnesses/` — five third-party harness repos as **git submodules**
  (read-only references; never copied into the local harness).

## Stack

Markdown-dominant (~267 `.md`) with Bash (~23 `.sh`), plus small amounts of
Python 3 (hook/skill scripts only) and Node ≥18 (`codex-adapter` `.mjs`).
No package to build or publish; no test/lint pipeline for the repo as a whole.

## Constraints / non-negotiables

- Repo-relative paths only — never commit machine-local absolute paths.
- Reference repos stay as submodules under `reference_harnesses/`; never copy
  them in, and don't edit submodule internals except to bump the pointer.
- Borrow only the smallest durable pattern that improves the harness.
- Plugin manifests (`plugin.json`, `marketplace.json`) must stay valid JSON.
- `scratchpad/` is gitignored throwaway — never commit it.
