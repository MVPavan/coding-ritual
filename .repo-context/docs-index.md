# Reading Index

Read only relevant rows; this is not a checklist. Paths are repo-relative.
Archived research is evidence, not operating policy.

## Shared guidance

| Need | Source |
|---|---|
| Orientation | `.repo-context/repo-map.md` |
| Domain terminology | `.repo-context/CONTEXT.md` |
| Python conventions | `.repo-context/coding-style.md` |
| Checks and prerequisites | `.repo-context/verification.md` |
| Architecture/contracts | `.repo-context/invariants.md`, `docs/adr/README.md` |
| Investigation | Search `.repo-context/learnings.md`; open matching evidence |
| Tracking and closeout | `.beads/beads.md` |

## Component work

| Need | Source |
|---|---|
| Interpreter behavior | `docs/specs/workflow-interpreter.md`; relevant accepted ADRs |
| Graph authoring | `workflows/README.md` |
| Build-loop enforcement | `docs/graph-loops/build-loop-tdd-enforcement.md` |
| Remote-control sessions | `scripts/README.md` |
| Harness design | `harness_learnings/coding-harness-best-practices.md` |
| Cross-runtime collaboration | `harness_learnings/claude-codex-collaboration.md` |
| Reference curation | `harness_lifecycle/README.md`; rulings in `harness_lifecycle/casebook/README.md` |
| Reference adoption/updates | `harness_learnings/reference-harness-workflow.md` |
| Reference comparisons | `harness_learnings/harness-patterns-by-capability.md`, `harness_learnings/reference-harness-repos.md` |
| Publication and installation | `docs/usage/mvp-plugin.md`; initialized plugin's README |
| Python checker decision | `docs/research/python-tooling/ty-vs-mypy.md` |

External inventories for `/codebase-research` live in
`harness_lifecycle/catalogs/<repo>.json`. Historical adoption, code-intelligence,
and incident evidence lives in `docs/research/repo-context-history/`; read it
only for relevant investigation and revalidate changing claims.
