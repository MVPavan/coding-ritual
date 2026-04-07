# Project-Agnostic Claude Setup

This directory is a reusable Claude Code harness with a Python-first default and a project-specific adoption layer.

It is designed to:
- stay lean by default
- support standard and deep work through planning and subagent execution
- use Codex as the default critic and reviewer for standard and deep work inside Claude Code
- keep repo-specific facts separate from the stable core harness

## How to use it

1. Copy the contents of this directory into the target repository root.
2. Keep `AGENTS.md` as the substantive instruction file.
3. Keep `CLAUDE.md` as the compatibility shim for Claude Code.
4. Run `/adopt` after the files are in the target repo.
5. Review the generated files under `.claude/project/`.
6. Start work with `/brainstorm`, `/plan`, `/dispatch`, and `/verify` as needed.

Do not nest this directory under another folder if you want Claude Code to auto-load the setup.

If the target repo already has a substantive `AGENTS.md` or `CLAUDE.md`, reconcile that file before overwriting it. This template assumes it becomes the repo's main instruction surface.

## Structure

- `AGENTS.md` — authoritative cross-tool instructions
- `CLAUDE.md` — Claude Code compatibility shim
- `adopt.md` — human-readable adoption contract
- `.claude/rules/core/` — stable universal rules
- `.claude/rules/python/` — Python-first defaults
- `.claude/project/` — the only area `/adopt` should rewrite

## Design intent

The core harness should change rarely.

Project facts should live in:
- `.claude/project/brief.md`
- `.claude/project/components.md`
- `.claude/project/verification.md`
- `.claude/project/invariants.md`
- `.claude/project/docs-index.md`
- `.claude/project/learnings.md`
- `.claude/project/adoption-report.md`

## Adoption boundaries

`/adopt` should update project facts, not core behavior.

If the target repo already has strong project-specific conventions, preserve them in the project overlay instead of rewriting the core rules to match one codebase.
