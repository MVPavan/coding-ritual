# Repository Map

Coding Ritual builds reusable agent harnesses, curates reference patterns, and
implements a Python workflow interpreter. `AGENTS.md` owns policy;
`.repo-context/docs-index.md` routes task-specific reading.

| Area | Start here |
|---|---|
| Shared guidance and vocabulary | `.repo-context/` |
| Skills and agent definitions | `.claude/skills/`, `.claude/agents/` |
| Runtime integrations | `.claude/` hooks/settings; `.codex/` configuration, agents, hooks and skill symlinks; `.agents/` settings |
| Interpreter and tests | `workflow_interpreter/`, `tests/` |
| Graphs and runtime examples | `workflows/`, `config/` |
| Specs and decisions | `docs/specs/`, `docs/adr/` |
| Verification and session tooling | `scripts/` |
| Reference curation | `harness_lifecycle/`, `harness_learnings/` |
| Task state and lifecycle | `.beads/`; policy in `.beads/beads.md` |
| Temporary artifacts | `scratchpad/` (gitignored) |

`docs/workstreams/` is the convention for future workstream documents; it is not
currently populated. `mvp-harness/` is the distribution submodule; its plugins
live under `mvp-harness/plugins/`.
`reference_harnesses/` and `reference_tools/` are external reference submodules.
Check initialization before using their paths. The `.repo-context/` installer
migration is a separate distribution change; see `docs/usage/mvp-plugin.md`.

Python dependencies live in `pyproject.toml`; Bash handles scripts/hooks, and the
Codex bridge uses Node.js (constraints in its plugin manifest). Tool availability
and model settings come from the active runtime, not this map.
