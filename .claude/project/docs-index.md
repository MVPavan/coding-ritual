# Docs Index

Authoritative docs and when to read them.

| Doc | Read when |
|---|---|
| `harness_learnings/coding-harness-best-practices.md` | **First** — canonical guide for harness design (principles, surfaces, scope routing) |
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
| `CONTEXT.md` | Naming anything — the domain glossary; use its terms, avoid its listed synonyms |
| `.beads/beads.md` | Beads workflow, agent context profiles, session-completion protocol |
| `.claude/rules/core/03-coding-discipline.md` | Coding rules that reduce common LLM mistakes |
| `docs/research/codebases/<repo>/luna-exploration.md` | Comparing the phase-bridge design against a cloned orchestration reference (cli-agent-orchestrator, metaswarm) — raw agent reports, unverified `file:line`, resumable sessions |
| `docs/workstreams/agent-bridge/state.md` | **Resuming the phase-bridge work** — branch/commit ledger, the seven gates, the open schema decision, known defects in committed code |

Reference-harness submodule docs under `reference_harnesses/<repo>/` are external —
read only when the task is explicitly about that reference.

| `docs/specs/2026-09-11-workflow-coordination.md` | Implementing the approved bridge, model decisions, child coordination and serialized integration scope |
| `docs/workstreams/agent-bridge/roadmap.md` | Resuming the approved six-phase workflow coordination execution |
