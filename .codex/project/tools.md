# Tools & Subagents

## Runtimes & tooling

| Tool | Version / note | Used by |
|---|---|---|
| Bash | system | install/test scripts, hooks (~23 `.sh`) |
| Python 3 | system | hook/skill scripts only (`block-generated-edits.py`, skill scripts) |
| Node.js | ≥18 | `codex-adapter` (`scripts/codex-run.mjs`) — private, not published |
| `bd` (beads) | v1.0.5, embedded Dolt | issue tracking (see `tracking.md`) |
| `codex` CLI | present & on PATH | Codex critique/review path is available |

No repo-wide package manager step — nothing to `npm install` or `pip install` to
work on the repo. The plugins are loaded by Claude Code / Codex, not built here.

## Codex

The `codex` CLI is installed, so the Codex one-way critic path is live. Follow
`.codex/commands/use-codex.md` for which command to use. Best-effort: one retry
on capacity error, then proceed and log the skip. Skip Codex for `small` tasks.

## Subagent / MCP routing

- **`docs-researcher`** subagent — library/SDK/API/CLI facts; never invent APIs.
- **`context7`** MCP (connected this session) — live docs for named libraries/SDKs;
  prefer over web search for library docs.
- **planner / implementer / code-reviewer / spec-reviewer** — core harness agents
  for bounded plan → build → review work.
- **claude-max / fable-max / fable-xhigh** — heaviest, most open-ended tasks.
- Use **brainstorming** for open-ended harness-design tradeoffs and requirements.

> Note: `.codex/rules/python/` ships with the harness, but this repo has no
> Python application/package — only small tooling scripts. Treat those rules as
> applying to the scripts, or trim them (see adoption-report).
