# Docs Index

Task-specific pointers. Read this index for orientation, then open only the
references relevant to the task. Historical reports are evidence, not policy.

| Doc | Read when |
|---|---|
| `harness_learnings/coding-harness-best-practices.md` | Substantive harness design: principles, surfaces, scope routing |
| `harness_learnings/claude-codex-collaboration.md` | Designing how Claude and Codex divide work |
| `harness_learnings/reference-harness-workflow.md` | Adding or updating a reference repo / borrowing a pattern |
| `harness_learnings/harness-patterns-by-capability.md` | Need the source-by-source breakdown behind the canon |
| `harness_learnings/reference-harness-repos.md` | Background on each tracked reference repo |
| `harness_lifecycle/README.md` | Detecting/comparing what a reference harness ships or changed upstream (`scan.py`) |
| `harness_lifecycle/casebook/README.md` | What we already decided about a reference skill, and why — append-only, per bucket |
| `README.md` | Repo overview (areas, read-first, common workflows) |
| `mvp-harness/plugins/<plugin>/README.md` | Working inside a specific plugin |
| `mvp-harness/plugins/mvp-plugin/skills/harness-adopt/SKILL.md` | Adapting the harness overlay to a repo |
| `docs/usage/mvp-plugin.md` | How this harness is published as the mvp-plugin (dual-manifest, residue, `/harness-publish`), invariants, invocation forms |
| `workflows/README.md` | Authoring or validating workflow graph definitions |
| `docs/graph-loops/build-loop-tdd-enforcement.md` | Checking a claim about what `workflows/build-loop.toml` actually enforces — each TDD rule, its enforcement tier, and the `file:line` that holds it |
| `docs/adr/` | **Before changing interpreter semantics** — recorded decisions (`allowed_paths`, node instructions, payload storage); supersede, never silently undo |
| `docs/specs/workflow-interpreter.md` | Implementing or operating the workflow interpreter |
| `scripts/README.md` | Managing Claude/Codex remote-control sessions (`claudex-rc.sh`) — lifecycle, recovery, watchdog |
| `.repo-context/CONTEXT.md` | Interpreting or introducing domain terminology |
| `.beads/beads.md` | Beads workflow, agent context profiles, session-completion protocol |
| `.repo-context/coding-style.md` | Before writing or changing Python code: Ruff, strict mypy, Pydantic, uv |
| `.repo-context/delegation.md` | Before worker dispatch or independent critique; workflow risk labels |
| `.repo-context/brief.md` | Project purpose and scope |
| `.repo-context/verification.md` | Selecting checks for the affected component |
| `.repo-context/invariants.md` | Changing architecture, contracts, or harness packaging; read applicable constraints |
| `.repo-context/tools.md` | Selecting or troubleshooting repository tools; verify runtime availability |
| `.repo-context/learnings.md` | Investigation or unfamiliar work; search and read matching entries, verify changing claims |
| `.repo-context/tracking.md` | Locating the authoritative tracking policy and current task state |
| `.repo-context/adoption-report.md` / `code-intel.md` | Historical adoption or tooling rationale only; reassess against current repository evidence |
| `docs/research/python-tooling/ty-vs-mypy.md` | Evaluating a change to the Python type-check gate: local timing, diagnostic coverage, and migration gaps |

Reference-harness submodule docs under `reference_harnesses/<repo>/` are external —
read only when the task is explicitly about that reference.
