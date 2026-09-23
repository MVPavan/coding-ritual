# Tools & Subagents

## Runtimes & tooling

| Tool | Version / note | Used by |
|---|---|---|
| Bash | system | install/test scripts, hooks (~23 `.sh`) |
| Python 3 | system | hook/skill scripts only (`block-generated-edits.py`, skill scripts) |
| `bd` (beads) | v1.0.5, embedded Dolt | issue tracking (see `tracking.md`) |
| `codex` CLI | present & on PATH | the only way to run Codex from Claude Code (see §Running Codex) |

No repo-wide package manager step — nothing to `npm install` or `pip install` to
work on the repo. The plugins are loaded by Claude Code / Codex, not built here.

## Independent critique

Critique of drafts, plans, and completed diffs runs on a **spawned critic subagent** — a fresh agent,
separate from the implementer. The user defines which model serves as critic
(ask if undefined; never assume one). Findings come back numbered
BLOCKER/MAJOR/MINOR with `file:line` plus a verdict, and the coordinator
triages them. Skip the critic for `small` tasks unless risk is unusual.
The Codex-side `use-codex` workflow is parked under
`.claude/skills/in-progress/use-codex/` (not loaded) for possible reactivation.

## Running Codex

Call the **Codex CLI directly**. Never use the codex-adapter plugin
(`codex-run.mjs`, `/codex-*` skills) — it was uninstalled 2026-09-23. The
model and effort come from the user's current roster; ask if undefined.

```bash
# new run — use -s read-only for review/analysis, workspace-write to edit
codex exec -C <dir> -s workspace-write -m <model> -c model_reasoning_effort=<effort> \
  -o <answer-file> "<prompt>" 2> <log-file>
# resume — no -C/-s flags; set sandbox via -c
cd <dir> && codex exec resume <session-id> -m <model> -c sandbox_mode=workspace-write \
  -c model_reasoning_effort=<effort> -o <answer-file> "<prompt>"
```

- The session id is the first `session id:` line on stderr; `-o` writes the
  final answer to a file. Prefer resume over a fresh run for follow-ups.
- `codex exec` silently accepts bad `-c` values — see `learnings.md`.

## Subagent / MCP routing

- **`docs-researcher`** subagent — library/SDK/API/CLI facts; never invent APIs.
- **`research`** skill — open-ended investigation: comparing providers, evaluating
  tooling or architecture options; produces a cited document under `docs/research/`.
- **`context7`** MCP (connected this session) — live docs for named libraries/SDKs;
  prefer over web search for library docs.
- **`/codebase-research`** on a `reference_harnesses/*` target: the committed
  machine-generated surface inventory its L1 consumes is
  `harness_lifecycle/catalogs/<repo>.json` (see that skill's L1 step 3).
- **implementer / code-reviewer / spec-reviewer** — core harness agents for
  bounded build → review work (reviewers follow the `code-review` skill;
  planning lives in the `planning` skill, dispatch in `execution`).
- **claude-max / fable-max / fable-xhigh** — heaviest, most open-ended tasks.
- Use **brainstorming** to settle harness-design scope, tradeoffs, and
  requirements into a spec (investigation itself routes to the `research` skill).

> Note: `.claude/rules/python/` ships with the harness, but this repo has no
> Python application/package — only small tooling scripts. Treat those rules as
> applying to the scripts, or trim them (see adoption-report).
