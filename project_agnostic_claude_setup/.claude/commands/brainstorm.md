---
description: Clarify requirements for standard or deep work before planning or implementation.
---

# Brainstorm

Use this for `standard` or `deep` work when the request is ambiguous, exploratory, or under-specified.

## Workflow

1. Read `AGENTS.md`, `.claude/project/brief.md`, and `.claude/project/docs-index.md`.
2. Scan only enough repo context to confirm what already exists and what constraints are real.
3. Ask one question at a time until the problem, scope, and success criteria are clear.
4. Pressure-test the request:
   - is this the right problem
   - is reuse or extension enough
   - what should stay out of scope
5. Offer 2-3 approaches only when the choice is real.
6. Recommend one direction and explain why.
7. If the decisions are durable, write or update a requirements doc under `docs/brainstorms/`.
8. Review that document before using it as planning input.
9. If running in Claude Code with Codex available and the work is `standard` or `deep`, ask Codex to critique the framing before finalizing.

Do not write code in this command.
