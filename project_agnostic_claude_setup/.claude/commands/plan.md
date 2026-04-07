---
description: Create a right-sized implementation plan from approved requirements or a clear request.
---

# Plan

Use this for `standard` or `deep` work before implementation.

## Workflow

1. Start from approved requirements or explicit assumptions.
2. If product behavior is still unclear, return to brainstorming.
3. Read local code, tests, project docs, and prior learnings before fixing the plan shape.
4. Write a durable plan under `docs/plans/`.
5. Include:
   - goal and scope
   - origin doc or assumptions
   - repo-relative file paths
   - test file paths
   - sequencing and dependencies
   - risks and invariants
   - exact verification commands or references
   - the smallest tracer-bullet step that proves the path
6. Keep the plan right-sized. Do not turn it into shell choreography unless exact commands are needed for verification.
7. If the work is `standard` or `deep` and Codex is available in Claude Code, ask Codex to critique the plan before execution.

If requirements are still unclear, return to brainstorming instead of forcing a weak plan.
