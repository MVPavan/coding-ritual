# Workflow Interpreter Guide

A companion set for understanding the workflow interpreter. Written as answers to
real questions, kept so they can be re-read and revised rather than re-derived.

**This is not the spec.** The authorities are `docs/specs/workflow-interpreter.md`,
the ADRs under `docs/adr/`, and the code itself. Where this guide and the code
disagree, the code wins and the guide is wrong.

## What it describes

Branch `wf/run-ledger` at `c4e0b10` (69 commits ahead of `main`, unmerged at the time
of writing). Code citations are paths under `workflow_interpreter/` in the
`wf-run-ledger` worktree, given as `path:line`.

## Reading order

Start at 01 and stop when your question is answered. Each document stands alone.

| # | Document | Answers |
|---|---|---|
| 01 | [Components](01-components.md) | Who does what, and what the confusable pairs are |
| 02 | [Contractor](02-contractor.md) | The command the orchestrator runs |
| 03 | [Foreman](03-foreman.md) | How one decision is taken, and how often |
| 04 | [Graph and nodes](04-graph-and-nodes.md) | Node kinds, task parameters, outcomes, regions, budgets |
| 05 | [Inspector wrapper](05-wrapper.md) | How one activation is actually executed |
| 06 | [Recovery](06-recovery.md) | What happens when a wrapper dies |
| 07 | [Grading](07-grading.md) | Why a crew's claim is never proof |
| 08 | [Store and ledger](08-store.md) | The one record store: the SQLite ledger and its rules |
| 09 | [Coordination](09-coordination.md) | Decision policy and child workflows (dormant today) |
| 10 | [Assessment](10-assessment.md) | Vision versus what is built; over- and under-engineering |
| 11 | [Language and pluggability](11-language-and-pluggability.md) | The tracker port: what is swappable, and what a tracker may not decide |
| — | [Diagrams](diagrams.md) | 46 Mermaid diagrams covering the whole system |

[diagrams.md](diagrams.md) is the largest document and the most complete. The numbered
documents are prose explanations of the same material; use them when a diagram raises
a question it does not answer.

## Provenance and confidence

Everything here was read from code, not recalled. Specific claims carry a `path:line`.
Where something is inference rather than verified fact, it says so.

Two known caveats:

- Section 16.2 of [diagrams.md](diagrams.md) lists twelve **suspected** defects. They
  were read from code and never executed. Each needs a test before anyone acts on it.
- [09-coordination.md](09-coordination.md) describes machinery that no shipping graph
  exercises. It is built, not proven.

## Corrections made while writing

Recorded so the same mistakes are not repeated:

- Node parameters were once attributed to `implement` that actually belong to
  `debrief`. Per-node fields must be read against their own `[[node]]` block.
- A test-line count of ~135,000 was wrong; the real figure is ~66,800. The original
  glob had swept in vendored `.venv` tests.
- The wrapper's entry point is `foreman/inspector.py`, not a `inspector/wrapper.py`.
