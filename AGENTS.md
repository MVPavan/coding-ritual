# Agent Operating Guide

Always-loaded entry point — every line here costs context. Detail lives in the pointed-to docs; keep it there.
Core harness is stable; repo-specific facts live in `.codex/project/`.

## Critical guidelines

- Prioritize factual accuracy over agreement with me.
- Point out errors and unchecked assumptions in my thinking.
- When I ask you to assess something, do so critically and avoid grade inflation.
- Distinguish certain knowledge from inference from speculation.
- If unsure, say so. Never fabricate citations, data, or examples.

## Read Order

1. `AGENTS.md`, then `CONTEXT.md` (domain glossary — use its terms, flag conflicts), then `docs/adr/` if present (recorded decisions — don't re-litigate or silently undo them)
2. `.codex/project/`: `brief.md`, `repo-map.md` (folder structure + how to orient), `docs-index.md`, `verification.md`, `invariants.md`
3. `docs/research/` — when working from prior research, runtime comparisons, or provider/tooling decisions
4. `docs/workstreams/<name>/roadmap.md` (active workstream plan) + generated workstream mirrors — when a workstream exists
5. Relevant rules under `.codex/rules/`
6. `reference_harnesses/<name>/` docs — only when the task is explicitly about that reference submodule

## Coding guideline

1. Follow `.claude/rules/core/03-coding-discipline.md` — coding rules that reduce common LLM mistakes (`.codex/rules/core` is a symlink to it).
2. Use `html-artifact` only when the user asks for HTML, or when the deliverable is purely for human reading and richer structure clearly helps. Do not use it for agent prompts, README files, harness docs, or other Markdown-native repo files.

## Working Mode

Classify the task before acting.

- `small`: 1-2 files, low ambiguity, reversible. Execute directly, then self-check.
- `standard`: bounded feature, bug fix, or refactor. Short plan before coding.
- `deep`: cross-cutting, high-risk, or ambiguous. Brainstorm, plan, review, execute via subagents, capture learnings.

Lean by default. Match ceremony to scope and risk.

## Process Before Execution

- unclear or exploratory request: brainstorm first
- an approved spec plus multi-step code work: plan first
- newly written spec or plan docs: review the document before execution
- risky behavior change or fragile legacy area: test-first or characterization-first
- bug, failure, or confusing behavior: systematic-debugging before proposing fixes
- approved plan with bounded tasks: subagent-driven development
- about to claim success: verify before completion

If the user already supplied a clear, approved plan, do not re-run brainstorming.

## Execution

Approved implementation work runs through the **execution skill** (three scopes: task / phase / workstream; entry commands `/phase-execution N` and `/run-phases` in Claude Code, `$phase-execution N` in Codex). Full cycle: planning → dispatch → review → TDD/debugging as routed → verification. Phase inventory: `docs/workstreams/<name>/roadmap.md`; work-state in Beads.

## Codex And Claude

`.claude/` is the canonical harness for both tools. `.codex/` holds the Codex view of it: `.codex/skills/*` and `.codex/project` are symlinks into `.claude/`, and each skill ships `agents/openai.yaml` (`policy.allow_implicit_invocation`, the Codex twin of `disable-model-invocation`). Only Codex-native residue is real under `.codex/`: `config.toml`, `rules/default.rules`, `agents/*.toml`, `hooks.json`, — every skill, including `migrate-claude-to-codex` and `codebase-architecture-research`, lives in `.claude/skills/`. Codex is retired as the critic in this repo (2026-08-14); independent critique runs on a spawned critic subagent — see CLAUDE.md §Independent critique.

## Tools & Subagents

Unsure about a library/SDK/API/CLI (methods, signatures, config, versions)? Use official/reference docs via the `docs-researcher` agent/skill path where available; never invent APIs. Use the `research` skill for open-ended investigation — comparing providers, evaluating tooling or architecture options, gathering and weighing sources into `docs/research/`. Use brainstorming to settle scope, tradeoffs, and requirements into a spec. Tool routing details live in `.codex/project/tools.md`.

## Verification

No completion claims without fresh evidence.

1. Identify the command that proves the claim.
2. Run it.
3. Read the output and exit status.
4. Report the actual result.
5. Check `git status` before presenting completion.

Source of truth: `.codex/project/verification.md` and `.codex/project/invariants.md`.

Until the repo has real first-party code and CI, use the structural checks in `.codex/project/verification.md`.

## Learnings

Record verified, likely-to-recur patterns in `.codex/project/learnings.md` (format + rules in its header).

## Git Safety

- Stage explicit files only. No `git add .`, `git add -A`, `--no-verify`, force-push, `reset --hard`, `clean`, `restore`, or `checkout` rewrites without explicit approval.
- Small reversible commits. Do not amend unless the user asks.
- Do not overwrite unrelated user changes.
- Do not encode machine-local absolute paths in plans, prompts, docs, or rules.
- Use `scratchpad/` for throwaway work — gitignored, never commit it.

## External Submodules

Third-party **reference harness** repos are tracked as Git submodules under `reference_harnesses/`, and third-party **reference tools** under `reference_tools/` (purpose per repo TBD; same read-only rules) — see `.gitmodules`. The parent repo tracks their commit pointers only — they are read-only references, never copied into the local harness. Do not edit submodule internals unless the task is explicitly submodule-local; for upstream sync, update and stage the submodule path. Borrow only the smallest durable pattern (see `harness_learnings/reference-harness-workflow.md`).

## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Workflow, rules, agent context profiles, and the session-completion protocol live in **[`.beads/beads.md`](.beads/beads.md)**. Run `bd prime` for runtime context.
