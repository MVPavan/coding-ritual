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
| `README.md` | Repo overview (areas, read-first, common workflows) |
| `mvp-harness/plugins/<plugin>/README.md` | Working inside a specific plugin |
| `mvp-harness/plugins/mvp-plugin/skills/harness-adopt/SKILL.md` | Adapting the harness overlay to a repo |
| `scripts/README.md` | Managing Claude/Codex remote-control sessions (`claudex-rc.sh`) — lifecycle, recovery, watchdog |
| `.beads/beads.md` | Beads workflow, agent context profiles, session-completion protocol |
| `.claude/rules/core/03-ak-guidelines.md` | Coding rules that reduce common LLM mistakes |

Reference-harness submodule docs under `reference_harnesses/<repo>/` are external —
read only when the task is explicitly about that reference.
