# Tools & Subagents

## Runtimes & tooling

| Tool | Version / note | Used by |
|---|---|---|
| Bash | system | install/test scripts, hooks (~23 `.sh`) |
| Python | version constraint in `pyproject.toml` | workflow interpreter, tests, hooks, and tooling |
| Node.js | ≥18 | `codex-adapter` (`scripts/codex-run.mjs`) — private, not published |
| `bd` (beads) | v1.0.5, embedded Dolt | issue tracking (see `tracking.md`) |
| `codex` CLI | availability and configuration are runtime-specific | Codex sessions and permitted delegation |

For Python tooling, package management, and data modeling, read
`.claude/project/coding-style.md`. Verification commands live in
`.claude/project/verification.md`.

## Independent critique

For worker dispatch and independent review, follow
`.claude/project/delegation.md`. Model selection follows the user or active
runtime configuration.

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
