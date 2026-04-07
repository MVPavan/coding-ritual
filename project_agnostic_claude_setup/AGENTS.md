# Agent Operating Guide

This repo uses a stable agent harness plus a project overlay.

Keep the core harness stable.
Put repo-specific facts in `.claude/project/`.

## Read Order

1. `AGENTS.md`
2. `.claude/project/brief.md`
3. `.claude/project/components.md`
4. `.claude/project/docs-index.md`
5. `.claude/project/verification.md`
6. `.claude/project/invariants.md`
7. Relevant rules under `.claude/rules/`

## Working Mode

Classify the task before acting.

- `small`: 1-2 files, low ambiguity, reversible, and not cross-cutting. Execute directly, then self-check. Skip Codex criticism by default.
- `standard`: bounded feature, bug fix, or refactor with meaningful behavior or multiple decisions. Create a short plan before coding. Use Codex criticism in Claude Code if available.
- `deep`: cross-cutting, high-risk, or ambiguous work. Brainstorm requirements, write a durable plan, review the document, execute through bounded subagent tasks, and capture durable learnings.

Lean by default. Match ceremony to scope and risk.

## The 5-Step Simplification Filter

Apply this before adding process, abstractions, or tooling:

1. Question the requirement.
2. Delete what does not need to exist.
3. Simplify before optimizing.
4. Accelerate only what still matters.
5. Automate only after the process is correct.

## Default Workflow

- If requirements are unclear or the request is exploratory, brainstorm before coding.
- If work is `standard` or `deep` and changes code, write a right-sized plan before implementation.
- If the task is a bug, failure, or confusing behavior, debug before proposing fixes.
- If behavior risk is high, use test-first or characterization-first execution.
- Prefer fresh subagents per task for `standard` and `deep` execution. The coordinator stays read-mostly.
- Pass exact paths, requirements, invariants, and verification commands to workers. Do not pass raw session history.
- Keep tasks small enough to review independently and, when requested, commit independently.

## Claude and Codex

This rule applies only when running in Claude Code and the Codex plugin is available.

- `small` work: skip Codex by default unless the risk is unusual.
- `standard` and `deep` brainstorms: ask Codex to challenge framing, assumptions, and omitted constraints.
- `standard` and `deep` plans: ask Codex to pressure-test the plan before execution.
- `standard` and `deep` implementation work: run Codex review on the working tree or branch before calling the work complete.

Codex is a one-way external critic and reviewer in this setup.
Do not assume a symmetric Claude second-opinion loop exists in Codex.

## Verification

No success claims without fresh verification.

Use the exact commands in `.claude/project/verification.md`.
If `.claude/project/invariants.md` lists mechanically checkable rules, run the relevant checks before completion.

## Memory and Learnings

- Use `.claude/memory/*` only for work that spans sessions or needs task-by-task coordination.
- Add to `.claude/project/learnings.md` only after a pattern or fix has been verified and is likely to recur.
- Keep memory files concise. They are coordination surfaces, not journals.

## Safety

- Prefer explicit file staging.
- Keep commits small and reversible.
- Do not use destructive git commands without user approval.
- Do not encode machine-local absolute paths in plans, prompts, docs, or rules.
