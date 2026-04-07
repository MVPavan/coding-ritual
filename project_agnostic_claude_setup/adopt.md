# Adopt This Setup

This setup is split into:
- a stable core harness
- a project-specific overlay in `.claude/project/`

After copying this setup into a target repository root, run `/adopt`.

## `/adopt` must do

1. Scan in this order:
   - root instruction files
   - README and design docs
   - manifests, CI, and test config
   - the relevant source and test layout
2. Use this authority order:
   - repo reality
   - current config and CI
   - maintained docs
   - older docs
   - explicit assumptions
3. Verify factual claims against the actual codebase where possible.
4. Write only the project overlay files under `.claude/project/`.
5. Keep all paths repo-relative.
6. Stop with an adoption report for human review.

## `/adopt` must not do

- rewrite the core rules, agents, commands, or skills unless the user asks
- copy machine-local paths from another repo
- preserve speculative or unverifiable claims as facts
- force Python defaults onto a repo whose local tooling says otherwise
- silently overwrite a stronger existing root instruction file without review

## Python-first fallback

If the target repo is Python and no stronger local conventions are found, use these as fallback verification commands:

- `ruff check .`
- `ruff format --check .`
- `mypy .`
- `pytest`

If the repo is not Python, adopt the observed local commands instead and note that the Python pack is not authoritative for that project.
