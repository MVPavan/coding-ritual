# Repository Map

Top-level layout and how to navigate.

| Path | What it is |
|---|---|
| `workflow_interpreter/` | First-party Python workflow loader, execution engine, supervisor, and runtime profiles |
| `tests/` | Interpreter unit, integration, sandbox, and live checks; selection rules in `.repo-context/verification.md` |
| `workflows/` / `config/` | Workflow graph definitions and runtime configuration examples |
| `docs/` | Specifications, ADRs, research, usage, and workstream plans |
| `scripts/` | Verification and runtime/session management tooling |
| `mvp-harness/` | Harness marketplace (git submodule); plugins live under `plugins/` |
| `mvp-harness/plugins/mvp-plugin/` | The harness as ONE dual-manifest plugin (Claude Code + Codex): `skills/` + `agents/` are build output of this repo (`/harness-publish` → `scripts/publish-plugin.sh`, `publish-manifest.txt`), `template/` is the per-repo residue `adopt` copies, `scripts/{install-harness,doctor,build-template,check-sync,smoke-codex}.sh`, `test/` |
| `mvp-harness/plugins/codex-adapter/` | Codex bridge plugin: `scripts/codex-run.mjs`, `roles/`, `commands/`, `skills/codex-runner/` |
| `mvp-harness/plugins/code-intel/` | Code-intelligence plugin: `bin/` shims, `hooks/`, `skills/graph-first/`, `test/` |
| `harness_learnings/` | Synthesized canon + best-practice docs (design reference) |
| `reference_harnesses/` | Third-party harnesses as git submodules (read-only; list in `.gitmodules`) |
| `reference_tools/` | Third-party tool repos as git submodules (read-only; not part of the harness lifecycle) |
| `harness_lifecycle/` | Reference-harness curation tooling: `scan.py` (catalog/diff/drift), `gap.py` (gap/ledger), committed `catalogs/` |
| `.agents/` | Codex/agent local settings |
| `.repo-context/` | Shared repository guidance and `CONTEXT.md` domain glossary; loading triggers live in `AGENTS.md` |
| `.claude/` | Canonical skills (each carries `agents/openai.yaml` for Codex), agent definitions, and Claude hooks/settings |
| `.codex/` | Skill symlinks into `.claude/`, plus Codex-native configuration, command rules, agents, and hooks |
| `.beads/` | Beads issue tracker store (embedded Dolt) + `beads.md` |
| `scratchpad/` | Gitignored throwaway work |
| `CLAUDE.md` / `AGENTS.md` | Always-loaded entry points (installed by the harness) |
| `README.md` | Repo overview (refreshed during adoption to match current layout) |

## Orientation

- To change shared skills or instructions: start in `.claude/` and `AGENTS.md`.
  For publishing or installation, consult `docs/usage/mvp-plugin.md`; plugin
  output lives in the `mvp-harness/` submodule.
- To work on the interpreter: use `docs/specs/workflow-interpreter.md`, relevant
  `docs/adr/`, and the affected module/tests.
- To evaluate/borrow from a reference repo: run `/harness-status` then
  `/harness-scan <repo>`, and triage candidates with the `harness-evaluate` skill;
  the deterministic tooling lives in `harness_lifecycle/` (see its README).
- Submodules are pointers only — `git submodule update --init` to populate;
  don't edit their internals.
