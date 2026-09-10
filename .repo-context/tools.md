# Tools & Subagents

## Runtimes & tooling

| Tool | Version / note | Used by |
|---|---|---|
| Bash | system | install/test scripts and hooks |
| Python | version constraint in `pyproject.toml` | workflow interpreter, tests, hooks, and tooling |
| Node.js | ≥18 | `codex-adapter` (`scripts/codex-run.mjs`) — private, not published |
| `bd` (beads) | verify installed version and resolved workspace when relevant | issue tracking (see `.beads/beads.md`) |
| `codex` CLI | availability and configuration are runtime-specific | Codex sessions and permitted delegation |

For Python tooling, package management, and data modeling, read
`.repo-context/coding-style.md`. Verification commands live in
`.repo-context/verification.md`.

## Independent critique

For worker dispatch and independent review, follow
`.repo-context/delegation.md`. Model selection follows the user or active
runtime configuration.

## Subagent / MCP routing

- **`docs-researcher`** subagent — when available and delegation is warranted,
  library/SDK/API/CLI investigation.
- **`research`** skill — open-ended investigation: comparing providers, evaluating
  tooling or architecture options; produces a cited document under `docs/research/`.
- **`context7`** MCP — if available in the active runtime, library/SDK docs.
  Otherwise use an available official documentation source.
- **`/codebase-research`** on a `reference_harnesses/*` target: the committed
  machine-generated surface inventory its L1 consumes is
  `harness_lifecycle/catalogs/<repo>.json` (see that skill's L1 step 3).
- **implementer / code-reviewer / spec-reviewer** — core harness agents for
  bounded build → review work (reviewers follow the `code-review` skill;
  planning lives in the `planning` skill, dispatch in `execution`).
- Model and effort selection follow active runtime configuration and user choices;
  this document does not establish model availability.
- Use **brainstorming** when material harness-design decisions need exploration.
