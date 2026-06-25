# Repository Map

Top-level layout and how to navigate.

| Path | What it is |
|---|---|
| `my_harness/` | Harness plugins under development (the repo's real output) |
| `my_harness/mvp-plugin/` | The harness installer plugin: `scripts/install-harness.sh`, `template/` (the `.claude`+`.codex` payload), `skills/harness-adopt/`, `commands/`, `test/` (Docker from-zero install test), `vendor/codex-adapter/` |
| `my_harness/codex-adapter/` | Codex bridge plugin: `scripts/codex-run.mjs`, `roles/`, `commands/`, `skills/codex-runner/` |
| `my_harness/code-intel/` | Code-intelligence plugin: `bin/` shims, `hooks/`, `skills/graph-first/`, `test/` |
| `harness_learnings/` | Synthesized canon + best-practice docs (design reference) |
| `reference_harnesses/` | Five third-party harnesses as git submodules (read-only) |
| `.agents/` | Codex-style local skill `refresh-harness-from-reference` + settings |
| `.claude/` | Installed Claude harness: `rules/`, `skills/`, `agents/`, `commands/`, `hooks/`, `project/` overlay |
| `.codex/` | Installed Codex harness (mirror of `.claude/`, Codex-flavored) |
| `.beads/` | Beads issue tracker store (embedded Dolt) + `beads.md` |
| `scratchpad/` | Gitignored throwaway work |
| `CLAUDE.md` / `AGENTS.md` | Always-loaded entry points (installed by the harness) |
| `README.md` | Repo overview (refreshed during adoption to match current layout) |

## Orientation

- To work on the reusable harness: start in `my_harness/mvp-plugin/`, use
  `harness_learnings/` as the design reference.
- To evaluate/borrow from a reference repo: see
  `harness_learnings/reference-harness-workflow.md` and the
  `.agents/skills/refresh-harness-from-reference/` skill.
- Submodules are pointers only — `git submodule update --init` to populate;
  don't edit their internals.
