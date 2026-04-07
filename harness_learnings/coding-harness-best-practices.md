# Coding Harness Best Practices

## Purpose

This file is the canonical guide for building a lean coding harness that works across projects. It focuses on stable load-bearing surfaces: instructions, rules, workflows, verification, review, and continuity.

## Core Principles

- Lean by default.
- Evidence over claims.
- Escalate ceremony with scope and risk.
- Prefer explicit constraints over vague advice.
- Preserve knowledge that compounds.

## The 5-Step Simplification Filter

Use this before adding rules, skills, hooks, agents, or automation:

1. Question the requirement.
2. Delete unnecessary steps.
3. Simplify before optimizing.
4. Accelerate only what still matters.
5. Automate only after the process is correct.

## Minimal Surfaces

- Root instruction file: one short file with repo purpose, structure, constraints, and exact verification commands.
- Rules: small always-on guardrails for safety, testing, and invariants.
- Skills or commands: only for repeated workflows.
- Agents or subagents: only for bounded work with clear handoffs.
- Hooks: only for fast mechanical checks.
- Project overlay or learnings docs: only for durable repo facts and verified patterns.

## Scope Routing

- `small`: direct execution plus self-check.
- `standard`: brief plan, implementation, verification.
- `deep`: requirements, plan, review, execution loop, learning capture.

Do not force all work through the deepest path.

## Core Workflow

- If requirements are unclear, brainstorm before coding.
- If the task is a bug or failure, debug before proposing fixes.
- If work changes behavior with real risk, prefer test-first or characterization-first execution.
- If work is `standard` or `deep`, plan before implementation.
- If work is large enough to benefit from isolation, execute through bounded subagent tasks.
- Verify before any completion claim.

## Non-Negotiables

- Keep the project brief short and exact.
- Use repo-relative paths only.
- Keep tasks small enough to verify independently.
- Keep commits small and reversible.
- Run the same verification commands a maintainer would trust.
- Use specialist review only when the risk justifies it.

## What Good Rules Look Like

- short
- specific
- checkable
- stable across sessions

Avoid giant prompt files that mix style, architecture, workflow, and transient project state.

## Memory and Knowledge

- Use memory only for multi-session continuity or coordinated execution.
- Capture durable learnings only after a verified fix or repeated pattern.
- Make long-lived docs discoverable from the root instruction file or docs index.
- Protect plans, requirements, and learnings from cleanup drift.

## Automation

- Automate mechanical checks, not judgment.
- Keep hooks fast and safe.
- Prefer scripts for deterministic classification, normalization, or validation.
- Treat tools and integrations as a budget, not a trophy.

## Source Bias

This canon is synthesized primarily from:
- Compound Engineering for decision workflows and discoverability
- Superpowers for execution discipline and verification rigor
- Everything Claude Code for Python review and layered rules
- Matt Pocock Skills for TDD, questioning, and interface pressure

Use `harness-patterns-by-capability.md` when you need the source-by-source breakdown.
