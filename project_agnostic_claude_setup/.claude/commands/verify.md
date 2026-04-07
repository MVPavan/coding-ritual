---
description: Run the project's adopted verification commands and report the actual status.
---

# Verify

## Arguments

- `quick` — fastest credible local confidence check
- `full` — canonical pre-completion suite
- `extended` — optional expensive checks if the project defines them

## Workflow

1. Read `.claude/project/verification.md`.
2. Select the command set for the requested level.
3. Run each category in order.
4. Stop on the first failing category, but always finish with `git status --short`.
5. Report the actual result, not the expected result.

## Output

```text
VERIFICATION: PASS | FAIL
Level:
Categories run:
First failing category:
Git:
Notes:
```

## Rules

- If the project overlay is blank and the repo is Python, use the documented Python fallback.
- If the project overlay is blank and the repo is not Python, say verification is not yet adopted.
- If the requested level is not defined, say so instead of inventing a substitute.
- No completion claims without the fresh command output.
