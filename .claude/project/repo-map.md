# Repository Map

Top-level layout and how to navigate.

| Path | What it is |
|---|---|
| `mvp-harness/` | Harness marketplace (git submodule) — the 3 plugins live under `plugins/`; the repo's real output |
| `mvp-harness/plugins/mvp-plugin/` | The harness installer plugin: `scripts/install-harness.sh`, `template/` (the dot-less `.claude`+`.codex` payload), `skills/harness-adopt/`, `commands/`, `test/` (Docker from-zero install test) |
| `mvp-harness/plugins/codex-adapter/` | Codex bridge plugin: `scripts/codex-run.mjs`, `roles/`, `commands/`, `skills/codex-runner/` |
| `mvp-harness/plugins/code-intel/` | Code-intelligence plugin: `bin/` shims, `hooks/`, `skills/graph-first/`, `test/` |
| `harness_learnings/` | Synthesized canon + best-practice docs (design reference) |
| `reference_harnesses/` | Six third-party harnesses as git submodules (read-only) |
| `harness_lifecycle/` | Reference-harness curation tooling: `scan.py` (catalog/diff/drift), `gap.py` (gap/ledger), committed `catalogs/` |
| `.agents/` | Codex/agent local settings |
| `.claude/` | Canonical harness: `rules/`, `skills/` (slash commands are slash-only skills; each skill carries `agents/openai.yaml` for Codex), `agents/`, `hooks/`, `project/` overlay |
| `.codex/` | Codex view of the same harness: `skills/*` and `project` are symlinks into `.claude/`; only Codex-native residue (`config.toml`, `rules/default.rules`, `agents/*.toml`, `hooks.json`) are real files |
| `.beads/` | Beads issue tracker store (embedded Dolt) + `beads.md` |
| `scratchpad/` | Gitignored throwaway work |
| `CLAUDE.md` / `AGENTS.md` | Always-loaded entry points (installed by the harness) |
| `README.md` | Repo overview (refreshed during adoption to match current layout) |

## Orientation

- To work on the reusable harness: start in `mvp-harness/plugins/mvp-plugin/`, use
  `harness_learnings/` as the design reference.
- To evaluate/borrow from a reference repo: run `/harness-status` then
  `/harness-scan <repo>`, and triage candidates with the `harness-evaluate` skill;
  the deterministic tooling lives in `harness_lifecycle/` (see its README).
- Submodules are pointers only — `git submodule update --init` to populate;
  don't edit their internals.
