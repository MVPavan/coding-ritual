# Tools & Subagents

## Runtimes & tooling

| Tool | Version / note | Used by |
|---|---|---|
| Bash | system | install/test scripts, hooks (~23 `.sh`) |
| Python 3 | system | hook/skill scripts only (`block-generated-edits.py`, skill scripts) |
| Node.js | ≥18 | `codex-adapter` (`scripts/codex-run.mjs`) — private, not published |
| `bd` (beads) | v1.0.5, embedded Dolt | issue tracking (see `tracking.md`) |
| `codex` CLI | present & on PATH | **retired** — do not invoke (see §Independent critique) |

No repo-wide package manager step — nothing to `npm install` or `pip install` to
work on the repo. The plugins are loaded by Claude Code / Codex, not built here.

## Independent critique

Codex is retired in this repo (2026-08-14 ruling; low quota) — do not invoke
the `codex` CLI or the codex-adapter plugin. Critique of drafts, plans, and
completed diffs runs on a **spawned critic subagent** — a fresh agent,
separate from the implementer. The user defines which model serves as critic
(ask if undefined; never assume one). Findings come back numbered
BLOCKER/MAJOR/MINOR with `file:line` plus a verdict, and the coordinator
triages them. Skip the critic for `small` tasks unless risk is unusual.
`.claude/commands/use-codex.md` is kept as a retired reference for possible
reactivation.

## Subagent / MCP routing

- **`docs-researcher`** subagent — library/SDK/API/CLI facts; never invent APIs.
- **`research`** skill — open-ended investigation: comparing providers, evaluating
  tooling or architecture options; produces a cited document under `docs/research/`.
- **`context7`** MCP (connected this session) — live docs for named libraries/SDKs;
  prefer over web search for library docs.
- **implementer / code-reviewer / spec-reviewer** — core harness agents for
  bounded build → review work (reviewers follow the `code-review` skill;
  planning lives in the `planning` skill, dispatch in `execution`).
- **claude-max / fable-max / fable-xhigh** — heaviest, most open-ended tasks.
- Use **brainstorming** to settle harness-design scope, tradeoffs, and
  requirements into a spec (investigation itself routes to the `research` skill).

> Note: `.claude/rules/python/` ships with the harness, but this repo has no
> Python application/package — only small tooling scripts. Treat those rules as
> applying to the scripts, or trim them (see adoption-report).
