---
name: refresh-harness-from-reference
description: Compare a newly added harness repo under `reference_harnesses/` against the existing reference repos, `harness_learnings/`, and `project_agnostic_claude_setup/`. Use when a new reference harness has been cloned or updated and you want to selectively absorb only the smallest durable improvements into the local learnings and reusable harness without cargo-culting whole workflows.
---

# Refresh Harness From Reference

Use this skill to evaluate a new reference harness repo and selectively improve the local harness stack.

## Core Rule

Borrow the smallest durable pattern that improves the harness.

Do not replace existing local files just because the new repo is different or more elaborate.

## Inputs

- a new repo under `reference_harnesses/`
- optionally, a specific path or repo name

If the target repo is not named, inspect `reference_harnesses/` and ask which new repo should be evaluated.

## Workflow

1. Identify the target repo and confirm it is the new or newly updated reference.
2. Run `python3 scripts/inventory_harness_repo.py <path>` on:
   - the target repo
   - each existing repo under `reference_harnesses/`
3. Read only the files needed to judge the candidate pattern.
4. Compare the candidate against:
   - `harness_learnings/coding-harness-best-practices.md`
   - `harness_learnings/harness-patterns-by-capability.md`
   - `project_agnostic_claude_setup/`
5. Classify each interesting finding:
   - `adopt` if it is clearly better and durable
   - `record-only` if it is useful as a reference but should not change the harness
   - `reject` if it is heavier, narrower, or too repo-specific
6. Update only the smallest relevant local files:
   - `harness_learnings/reference-harness-repos.md`
   - `harness_learnings/harness-patterns-by-capability.md`
   - `harness_learnings/coding-harness-best-practices.md`
   - the minimal files in `project_agnostic_claude_setup/` that actually benefit
7. Summarize:
   - what was better
   - what was adopted
   - what was deliberately rejected

## Borrowing Heuristics

- Prefer repo-agnostic workflow logic over packaging.
- Prefer smaller rules over larger prompts.
- Prefer stronger verification over louder wording.
- Prefer clearer handoffs over more agent roles.
- Prefer one durable improvement over many speculative edits.

## Guardrails

- Do not import large catalogs.
- Do not copy install instructions or UI trivia.
- Do not copy local paths, branch habits, or org-specific assumptions.
- Do not widen the harness unless the new pattern clearly improves repeated work.
- If the candidate improvement only changes phrasing, do not rewrite local files.

## Output

Produce a short decision report:

```text
Target repo:
Capabilities reviewed:
Adopted:
Recorded only:
Rejected:
Files updated:
```
