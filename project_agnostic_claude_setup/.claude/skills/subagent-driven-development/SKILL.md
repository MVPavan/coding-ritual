---
name: subagent-driven-development
description: Use when executing an approved standard or deep plan through bounded tasks with implementer and review agents.
---

# Subagent-Driven Development

Use this when the work is large enough that one session should coordinate rather than hold all implementation context itself.

## Default Model

- coordinator: reads, plans, curates context, reviews, and synthesizes
- implementer: writes code inside a bounded task
- spec-reviewer: checks plan and requirement compliance
- code-reviewer: checks code quality and safety

## Workflow

1. Read the plan once and extract the tasks.
2. Build a task packet for each task:
   - goal
   - owned and forbidden files
   - origin doc or plan section
   - relevant invariants
   - required tests
   - verification commands
   - commit policy
3. Dispatch a fresh implementer per task with only that packet.
4. Require one of: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, `BLOCKED`.
5. Run spec review first.
6. Run code-quality review second.
7. Fix and re-review until both pass.
8. In Claude Code with Codex available, run Codex review before final completion for `standard` and `deep` work.

## Rules

- Do not run multiple implementers on the same files in parallel.
- Do not pass raw session history to workers.
- Keep tasks small enough to verify independently.
- Prefer a smaller worker model and a stronger planner or reviewer model.
- Re-dispatch the same worker only for follow-up fixes on the same bounded task.
- If a task blocks twice, improve context or split the task. Do not keep retrying blindly.
