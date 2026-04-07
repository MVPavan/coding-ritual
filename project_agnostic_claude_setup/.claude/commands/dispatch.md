---
description: Execute an approved plan through bounded implementer tasks with review gates.
---

# Dispatch

Use this when a plan already exists and the work is not small enough for direct inline execution.

## Default Mode

For `standard` and `deep` work, the coordinator stays read-mostly and executes the plan through bounded tasks.

## Workflow

1. Read the plan once and extract the tasks.
2. For each task, build a packet with:
   - the task goal
   - owned and forbidden files
   - the relevant plan section or origin doc
   - relevant invariants
   - required tests
   - verification commands
   - commit policy
3. Dispatch a fresh `implementer` with only that packet.
4. If the implementer returns `NEEDS_CONTEXT` or `BLOCKED`, fix the context, raise the model, or break the task down further.
5. After implementation, run `spec-reviewer`.
6. Only after spec compliance passes, run `code-reviewer`.
7. Fix and re-review until both reviewers pass.
8. For `standard` and `deep` work in Claude Code with Codex available, run Codex review before final completion.

## Rules

- Do not run parallel implementers on the same files.
- Do not pass raw session history to workers.
- Small tasks may stay inline and skip this command.
